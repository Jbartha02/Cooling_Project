import sys, os
_AC_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_AC_DIR, '..'))  # project root (für Fluid_CP etc.)
sys.path.insert(0, _AC_DIR)                       # ac_model/ (für config, compressor_model)

import numpy as np
import pandas as pd
from scipy.optimize import minimize, NonlinearConstraint

import Fluid_CP as FCP
from compressor_model import recip_comp_corr_SP
import config as cfg

Eh = cfg.Eh


# ── Thermodynamischer Kreislauf + Pinch — alles in einem Durchlauf ──────────



def _cycle_states(T_co, T_ev, refrigerant, c_d_mm,
                  T_si_in, T_si_out, T_so_in, T_so_out,
                  delta_T_sh=None):
    """
    Berechnet alle 5 Kreislaufzustände, Pinch-Temperaturdifferenzen, P_cool und W_comp.

    Wärmequelle (Verdampfer): fluid_so tritt bei T_so_in ein, verlässt bei T_so_out.
    Wärmesenke  (Verflüssiger): fluid_si tritt bei T_si_in ein, verlässt bei T_si_out.

    Rückgabe: dict mit
        s1, s2, s3, s4, s2s   — Kreislaufzustände (pandas Series)
        eta_is, m_dot          — Kompressorkennwerte
        P_cool, W_comp         — Leistungen [kW]
        pinch_ev               — [dT_sh_end, dT_throttle_end]  (NC1, 2 Werte)
        pinch_co               — [dT_in, dT_out, dT_dew]       (NC2, 3 Werte)
    """
    dT_sh = delta_T_sh if delta_T_sh is not None else cfg.delta_T_sh

    # Kompressor
    comp_param = (T_ev, T_co, dT_sh, 0., c_d_mm)
    eta_is, m_dot = recip_comp_corr_SP(comp_param, refrigerant, transcrit=False)

    # Zustand 1*: gesättigter Dampf am Verdampferaustritt
    s1_sat = FCP.state(["T", "x"], [T_ev, 1.0], refrigerant, Eh)
    # Zustand 1: nach Überhitzung
    if dT_sh > 0.:
        s1 = FCP.state(["T", "p"], [T_ev + dT_sh, s1_sat["p"]], refrigerant, Eh)
    else:
        s1 = s1_sat

    # Zustand 3*: gesättigte Flüssigkeit am Verflüssigungsaustritt
    s3_sat = FCP.state(["T", "x"], [T_co, 0.0], refrigerant, Eh)
    # Zustand 3: nach Unterkühlung
    s3 = FCP.state(["T", "p"], [T_co - cfg.delta_T_sc, s3_sat["p"]], refrigerant, Eh)

    # Zustand 2s: isentrope Verdichtung
    s2s = FCP.state(["p", "s"], [s3["p"], s1["s"]], refrigerant, Eh)
    # Reale Enthalpie nach Verdichtung
    h2 = s1["h"] + (s2s["h"] - s1["h"]) / eta_is
    # Zustand 2: Verdichteraustritt
    s2 = FCP.state(["p", "h"], [s3["p"], h2], refrigerant, Eh)

    # Zustand 4: nach Drossel (isenthalp)
    s4 = FCP.state(["p", "h"], [s1_sat["p"], s3["h"]], refrigerant, Eh)

    # Leistungen [kW] — h in kJ/kg, m_dot in kg/s
    P_cool = m_dot * (s1["h"] - s4["h"])
    W_comp = m_dot * (s2["h"] - s1["h"])
    

    # ── Verdampfer-Pinch (Gegenstrom, Wärmequelle = fluid_so) ────────────────
    # Wärmequelle-Eintritt (heiß) ↔ Kältemittel-Austritt (s1, überhitzt)
    dT_ev_hot = T_so_in - s1["T"]
    # Wärmequelle-Austritt (kalt) ↔ Kältemittel-Eintritt (s4 ≈ T_ev, nach Drossel)
    dT_ev_cold = T_so_out - s4["T"]

    # ── Verflüssiger-Pinch (Gegenstrom, Wärmesenke = fluid_si) ──────────────
    # Kältemittel-Austritt (s3, unterkühlt) ↔ Wärmesenke-Eintritt (T_si_in, kalt)
    dT_co_out = s3["T"] - T_si_in
    # Kältemittel-Eintritt (s2, überhitzt) ↔ Wärmesenke-Austritt (T_si_out, warm)
    dT_co_in  = s2["T"] - T_si_out

    # Zwischenpunkt: Taulinie des Kältemittels im Verflüssiger
    h_sat_dew = FCP.state(["T", "x"], [T_co, 1.0], refrigerant, Eh)["h"]
    h_si_in   = FCP.state(["T", "p"], [T_si_in,  1.0], cfg.fluid_si, Eh)["h"]
    h_si_out  = FCP.state(["T", "p"], [T_si_out, 1.0], cfg.fluid_si, Eh)["h"]
    # Interpolation: Wärmesenken-Enthalpie an der Taulinie
    h_si_dew  = h_si_out - (h_si_out - h_si_in) / (s2["h"] - s3["h"]) * (s2["h"] - h_sat_dew)
    T_si_dew  = FCP.state(["p", "h"], [1.0, h_si_dew], cfg.fluid_si, Eh)["T"]
    dT_co_dew = T_co - T_si_dew

    p_ratio = s3["p"] / s1_sat["p"]   # p_co / p_ev — Mindest-Druckverhältnis

    return {
        "s1": s1, "s2": s2, "s3": s3, "s4": s4, "s2s": s2s,
        "s1_sat": s1_sat, "s3_sat": s3_sat,
        "eta_is": eta_is, "m_dot": m_dot,
        "P_cool": P_cool, "W_comp": W_comp,
        "p_ratio": p_ratio,
        "pinch_ev": [dT_ev_hot, dT_ev_cold],
        "pinch_co": [dT_co_in,  dT_co_out, dT_co_dew],
    }


# ── COP-Optimierung für einen Betriebspunkt ─────────────────────────────────

def optimize_cop(refrigerant, c_d_mm, T_amb, T_room,
                 min_pinch=cfg.min_pinch, W_vent=0., Q_required=0.,
                 min_pressure_ratio=None, T_AC=None, delta_T_sh=None,
                 min_pinch_ev=None, min_pinch_co=None):
    """
    Optimiert T_co und T_ev für maximalen COP bei gegebenem Betriebspunkt.

    T_amb      : Außentemperatur [°C] — bestimmt Wärmesenken-Eintrittstemperatur
    T_room     : Raumtemperatur  [°C] — bestimmt Wärmequellen-Eintrittstemperatur
    W_vent     : Ventilatorleistung [kW] (wird vom COP abgezogen)
    Q_required : Mindest-Kühlleistung [kW] — 0 bedeutet kein Constraint

    Rückgabe: dict mit COP, T_co, T_ev, m_dot, W_comp_kW, P_cool_kW, success, feasible
    """
    # Wärmesenke (Verflüssiger): Kühlwasser/Kühlturm abhängig von T_amb
    T_si_in  = T_amb          # Wärmesenke-Eintritt [°C]
    T_si_out = T_amb + 6.     # Wärmesenke-Austritt [°C] (typische Spreizung 6K)
    # Wärmequelle (Verdampfer): Raumluft/-wasser
    T_so_in  = T_room         # Wärmequelle-Eintritt [°C]
    T_so_out = T_AC if T_AC is not None else cfg.T_AC

    p_ev = min_pinch_ev if min_pinch_ev is not None else min_pinch
    p_co = min_pinch_co if min_pinch_co is not None else min_pinch

    # Cache: verhindert Doppelberechnung der States für COP + Pinch-Constraints
    _cache = {}

    def _eval(param):
        key = (round(param[0], 8), round(param[1], 8))
        if key not in _cache:
            _cache.clear()
            try:
                _cache[key] = _cycle_states(
                    param[0], param[1], refrigerant, c_d_mm,
                    T_si_in, T_si_out, T_so_in, T_so_out,
                    delta_T_sh=delta_T_sh,
                )
            except Exception:
                # Ungültige Zustandskombination → große Strafe
                _cache[key] = {
                    "P_cool": 0., "W_comp": 1e6,
                    "pinch_ev": [-1e6, -1e6],
                    "pinch_co": [-1e6, -1e6, -1e6],
                    "m_dot": 0., "eta_is": 0.,
                    "p_ratio": -1e6,
                }
        return _cache[key]

    def neg_cop(param):
        r = _eval(param)
        denom = r["W_comp"] + W_vent
        return -(r["P_cool"] / denom) if denom > 0 else 1e6

    def pinch_ev(param):
        return _eval(param)["pinch_ev"]

    def pinch_co(param):
        return _eval(param)["pinch_co"]

    bounds = [
        (T_si_in + p_co, 60.),    # T_co: mind. p_co über Wärmesenke-Eintritt
        (-20., T_so_in - p_ev),   # T_ev: max. p_ev unter Wärmequelle-Eintritt
    ]
    NC1 = NonlinearConstraint(pinch_ev, [p_ev, p_ev], [np.inf, np.inf])
    NC2 = NonlinearConstraint(pinch_co, [p_co, p_co, p_co],
                                         [np.inf, np.inf, np.inf])

    constraints = [NC1, NC2]
    if min_pressure_ratio is not None:
        def pressure_ratio_con(param):
            return [_eval(param)["p_ratio"]]
        NC_pr = NonlinearConstraint(pressure_ratio_con, [min_pressure_ratio], [np.inf])
        constraints.append(NC_pr)
    if Q_required > 0.:
        def p_cool_con(param):
            return [_eval(param)["P_cool"]]
        NC3 = NonlinearConstraint(p_cool_con, [Q_required], [np.inf])
        constraints.append(NC3)

    x0 = [T_si_in + 10., T_so_in - 10.]
    result = minimize(neg_cop, x0=x0, method="SLSQP",
                      bounds=bounds, constraints=constraints)

    best = _eval(result.x)
    p_cool = round(best["P_cool"], 3)
    return {
        "refrigerant": refrigerant,
        "c_d_mm":      c_d_mm,
        "T_amb":       T_amb,
        "T_room":      T_room,
        "COP":         -result.fun if result.success else np.nan,
        "T_co":        round(result.x[0], 2),
        "T_ev":        round(result.x[1], 2),
        "m_dot":       round(best["m_dot"], 4),
        "eta_is":      round(best["eta_is"], 3),
        "W_comp_kW":   round(best["W_comp"], 3),
        "P_cool_kW":   p_cool,
        "feasible":    result.success and (p_cool >= Q_required),
        "success":     result.success,
    }


# ── Sweep über alle Refrigerants × Kompressorgrößen × Jahreszeiten ──────────

def sweep_all(W_vent=0., Q_required=0.):
    """
    48 Optimierungsläufe: 4 Jahreszeiten × 4 Kältemittel × 3 Bohrungsdurchmesser.

    W_vent     : Ventilatorleistung [kW] (gilt für alle Läufe gleich)
    Q_required : Mindest-Kühlleistung [kW] — Kombinationen darunter werden als infeasible markiert
    """
    rows = []
    total = len(cfg.design_points) * len(cfg.refrigerants) * len(cfg.compressor_diameters_mm)
    i = 0
    for dp in cfg.design_points:
        for ref in cfg.refrigerants:
            for c_d in cfg.compressor_diameters_mm:
                i += 1
                print(f"[{i:2d}/{total}] {dp['season']:6s}  {ref:10s}  D={c_d:.0f}mm", end="  ")
                r = optimize_cop(ref, c_d, dp["T_amb"], dp["T_room"],
                                 W_vent=W_vent, Q_required=Q_required)
                r["season"] = dp["season"]
                rows.append(r)
                tag = "OK" if r["feasible"] else ("LOW_Q" if r["success"] else "FAIL")
                cop_str = f"COP={r['COP']:.2f}" if r["success"] else "COP=---"
                print(f"{tag:5s}  {cop_str}  T_ev={r['T_ev']:.1f}°C  T_co={r['T_co']:.1f}°C  Q={r['P_cool_kW']:.2f}kW")

    cols = ["season", "refrigerant", "c_d_mm", "T_amb", "T_room",
            "COP", "T_co", "T_ev", "m_dot", "eta_is", "W_comp_kW", "P_cool_kW", "feasible", "success"]
    df = pd.DataFrame(rows)[cols]

    out_path = os.path.join(os.path.dirname(__file__), "cop_sweep_results.csv")
    df.to_csv(out_path, index=False)
    print(f"\nErgebnisse gespeichert: {out_path}")
    print("\n" + df.to_string(index=False))
    return df


if __name__ == "__main__":
    sweep_all(W_vent=cfg.W_vent, Q_required=5.0)   # 5 kW Mindestkühlleistung (Extremfall)
