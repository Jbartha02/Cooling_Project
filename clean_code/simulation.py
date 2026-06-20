"""
5-Minuten On/Off-Thermostat-Simulation des Serverraums.

Physik:
  - ODE-Zustand z = [h*, m_w]  (spez. Raumluft-Enthalpie, Wassermasse)
  - Ventilation: wenn Aussenluft kühler als Sollwert und Massenstrom ausreicht
  - AC: Thermostat ON/OFF mit Hysterese und Mindestzeiten
  - Kompressor läuft immer bei voller Map-Leistung Q_max (kein Drosseln)
"""
import sys, os
_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np
import pandas as pd
import Fluid_CP_moist_air as Fmoist

import clean_code.config as cfg
from clean_code.performance_map import query


# ── Hilfsfunktionen ───────────────────────────────────────────────────────────

def _hhmm_to_hours(arr):
    out = np.empty(len(arr))
    for k, t in enumerate(arr):
        h, m = str(t).split(":")
        out[k] = int(h) + int(m) / 60.
    return out


def _vent_state(T_amb, phi=cfg.phi_vent):
    s = Fmoist.state_moist(["T", "phi"], [T_amb, phi])
    return s["h*"], s["X"]


# ── Analytische Zeitschritte ──────────────────────────────────────────────────
#
# Beide Betriebsmodi (AC an / Ventilation) führen auf dieselbe lineare ODE:
#
#   dh/dt  = (q + ṁ·(h_in − h)) / m_Air
#          =  A − B·h                         mit  B = ṁ/m_Air
#                                                  A = (q + ṁ·h_in)/m_Air
#
#   dm_w/dt = ṁ·(X_in − m_w/m_Air)
#           =  C − B·m_w                       mit  C = ṁ·X_in
#
# Gleichgewichtswerte (Ableitungen = 0):
#   h_eq  = A/B = q/ṁ + h_in          ← Raumluft-Enthalpie bei stationärem Betrieb
#   mw_eq = C/B = m_Air · X_in        ← Wassermasse bei stationärem Betrieb
#
# Exakte Lösung des linearen AWP (kein Diskretisierungsfehler, kein Solver-Overhead):
#   h(t)  = h_eq  + (h₀  − h_eq ) · exp(−B·t)
#   mw(t) = mw_eq + (mw₀ − mw_eq) · exp(−B·t)
#
# Grenzfall ṁ → 0 (kein Massenstrom, z. B. AC aus):
#   dh/dt = q / m_Air  →  h(t) = h₀ + (q/m_Air)·t
#   dm_w/dt = 0         →  mw(t) = mw₀


def _step_with_flow(z, dt, q, m_dot, h_in, X_in):
    """
    Exakter Zeitschritt mit aktivem Massenstrom ṁ (AC-Betrieb oder Ventilation).

    Löst dh/dt = A − B·h und dmw/dt = C − B·mw analytisch über das Intervall dt.
    """
    h0, mw0 = z
    if m_dot < 1e-12:
        # ṁ ≈ 0: Grenzfall entspricht reinem Aufheizen (= _step_no_flow)
        return [h0 + q / cfg.m_Air * dt, mw0]

    B     = m_dot / cfg.m_Air          # Abklingrate [1/s]: Kehrwert der thermischen Zeitkonstante
    h_eq  = q / m_dot + h_in          # stationäre Enthalpie: Wärmezufuhr q wird genau durch
                                       #   Zuluft (h_in) kompensiert, wenn h_room = h_eq
    mw_eq = cfg.m_Air * X_in          # stationäre Wassermasse: Raum-X = Zuluft-X

    e = np.exp(-B * dt)                # Dämpfungsfaktor für diesen Zeitschritt
    return [h_eq  + (h0  - h_eq ) * e,
            mw_eq + (mw0 - mw_eq) * e]


def _step_no_flow(z, dt, q):
    """
    Exakter Zeitschritt ohne Massenstrom (AC aus, kein Vent): lineares Aufheizen.

    dh/dt = q/m_Air ist konstant → triviale Integration.
    dm_w/dt = 0 → Feuchtemasse bleibt konstant.
    """
    return [z[0] + q / cfg.m_Air * dt, z[1]]


# ── Hauptsimulation ───────────────────────────────────────────────────────────

def simulate(season, refrigerant, c_d_mm, maps,
             T_AC=None, csv_path=None,
             t_min_on=cfg.t_min_runtime_s,
             t_min_off=cfg.t_min_standstill_s):
    """
    5-min On/Off-Thermostatbetrieb für einen Repräsentativ-Tag.

    Parameter
    ---------
    season      : "winter" | "spring" | "summer" | "fall"
    refrigerant : "R290" | "R1234yf" | "DME"
    c_d_mm      : Kompressor-Bohrungsdurchmesser [mm]
    maps        : geladene Performance-Maps (load_maps())
    T_AC        : Verdampfer-Ausblastemperatur [°C], default cfg.T_AC
    csv_path    : Pfad zur 5-min-Profil-CSV, default cfg.CSV_5MIN

    Rückgabe
    --------
    pd.DataFrame mit Spalten:
        time, T_amb, q_server_kW, T_room, phi_room, X_room,
        vent_on, ac_on, m_dot_vent, Q_AC_kW, Q_AC_max_kW,
        m_dot_ac, W_comp_kW, fan_limited, ac_overloaded, n_cycles_cum
    """
    T_AC_    = T_AC     if T_AC     is not None else cfg.T_AC
    csv_path = csv_path if csv_path is not None else cfg.CSV_5MIN

    df_in    = pd.read_csv(csv_path)
    T_amb    = df_in[cfg.season_col[season]].values
    q_server = df_in["Server_Heating_Power_kW"].values
    time     = _hhmm_to_hours(df_in["Time"].values)
    n        = len(T_amb)
    dt       = float(time[1] - time[0]) * 3600.     # h → s

    X_AC_sat = Fmoist.state_moist(["T", "phi"], [T_AC_, 1.0])["X"]

    # Ausgabe-Arrays
    T_room_arr     = np.zeros(n)
    phi_room_arr   = np.zeros(n)
    X_room_arr     = np.zeros(n)
    vent_on_arr    = np.zeros(n, dtype=bool)
    ac_on_arr      = np.zeros(n, dtype=bool)
    m_dot_vent_arr = np.zeros(n)
    Q_AC_arr       = np.zeros(n)
    Q_AC_max_arr   = np.zeros(n)
    m_dot_ac_arr   = np.zeros(n)
    W_comp_arr     = np.zeros(n)
    fan_lim_arr    = np.zeros(n, dtype=bool)
    overload_arr   = np.zeros(n, dtype=bool)
    n_cycles_arr   = np.zeros(n, dtype=int)

    # Zustand
    z          = [cfg.h_0, cfg.mw0]
    ac_therm   = False
    t_in_state = 0.0
    n_cycles   = 0

    for i in range(n):
        h_vent, X_vent = _vent_state(T_amb[i])
        T_prev = T_room_arr[i - 1] if i > 0 else cfg.T_room_set

        # ── Ventilationsbetrieb prüfen ────────────────────────────────────────
        h_target  = (cfg._CP_A * cfg.T_room_set + cfg._H_A0
                     + X_vent * (cfg._L0 + cfg._CP_W * cfg.T_room_set))
        dh_to_set = h_target - h_vent
        if dh_to_set > 1e-6 and q_server[i] / dh_to_set <= cfg.m_dot_vent_max:
            m_dot_vent = q_server[i] / dh_to_set
            z = _step_with_flow(z, dt, q_server[i], m_dot_vent, h_vent, X_vent)
            vent_on_arr[i]    = True
            m_dot_vent_arr[i] = m_dot_vent
            t_in_state += dt

        else:
            # ── AC-Thermostatbetrieb ──────────────────────────────────────────
            _, Q_max, W_comp_rated, _ = query(maps, refrigerant, c_d_mm,
                                              T_amb[i], T_prev)
            Q_AC_max_arr[i] = Q_max

            prev_therm = ac_therm
            if ac_therm:
                if T_prev <= cfg.T_OFF and t_in_state >= t_min_on:
                    ac_therm, t_in_state = False, 0.0
            else:
                if T_prev >= cfg.T_ON and t_in_state >= t_min_off:
                    ac_therm, t_in_state = True, 0.0

            if ac_therm and not prev_therm:
                n_cycles += 1

            t_in_state += dt
            ac_on_arr[i] = ac_therm

            if ac_therm:
                X_room = max(z[1] / cfg.m_Air, 0.0)
                X_AC   = X_AC_sat if X_room > X_AC_sat else X_room
                h_AC   = cfg._CP_A*T_AC_ + cfg._H_A0 + X_AC*(cfg._L0 + cfg._CP_W*T_AC_)
                h_room = z[0]
                dh     = max(h_room - h_AC, 0.0)

                m_dot_ideal = Q_max / dh if dh > 1e-6 else 0.0
                m_dot_ac    = min(m_dot_ideal, cfg.m_dot_vent_max)
                Q_delivered = m_dot_ac * dh

                fan_lim_arr[i]  = m_dot_ac < m_dot_ideal - 1e-9
                Q_AC_arr[i]     = Q_delivered
                m_dot_ac_arr[i] = m_dot_ac
                W_comp_arr[i]   = W_comp_rated
                # Overload nur relevant wenn Raum zu warm ist (T_prev > T_overload_min).
                # Ist der Raum bereits kühler als der Schwellwert, läuft der Kompressor
                # einfach auf Maximum — ein Leistungsdefizit ist dort akzeptabel.
                overload_arr[i] = (q_server[i] > Q_max) and (T_prev > cfg.T_overload_min)

                z = _step_with_flow(z, dt, q_server[i], m_dot_ac, h_AC, X_AC)
            else:
                z = _step_no_flow(z, dt, q_server[i])

        n_cycles_arr[i] = n_cycles
        z = [z[0], max(float(z[1]), 0.0)]

        X_room        = max(z[1] / cfg.m_Air, 0.0)
        X_room_arr[i] = X_room
        T_room_arr[i] = ((z[0] - cfg._H_A0 - X_room * cfg._L0)
                         / (cfg._CP_A + X_room * cfg._CP_W))
        if 0.0 < T_room_arr[i] < 60.0:
            phi_room_arr[i] = Fmoist.state_moist(["T", "X"],
                                                  [T_room_arr[i], X_room])["phi"]
        else:
            phi_room_arr[i] = float("nan")

    return pd.DataFrame({
        "time":          time,
        "T_amb":         T_amb,
        "q_server_kW":   q_server,
        "T_room":        T_room_arr,
        "phi_room":      phi_room_arr,
        "X_room":        X_room_arr,
        "vent_on":       vent_on_arr,
        "ac_on":         ac_on_arr,
        "m_dot_vent":    m_dot_vent_arr,
        "Q_AC_kW":       Q_AC_arr,
        "Q_AC_max_kW":   Q_AC_max_arr,
        "m_dot_ac":      m_dot_ac_arr,
        "W_comp_kW":     W_comp_arr,
        "fan_limited":   fan_lim_arr,
        "ac_overloaded": overload_arr,
        "n_cycles_cum":  n_cycles_arr,
    })
