"""
Sweep über alle Kältemittel × Kompressor-Kombinationen.

Einfachste Nutzung: TESTS-Liste konfigurieren, dann F5 drücken.
"""
import sys, os
_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import argparse
import time as _time
import pandas as pd
from concurrent.futures import ProcessPoolExecutor, as_completed

import clean_code.config as cfg
from clean_code.performance_map import load_maps, build_all_maps
from clean_code.simulation import simulate
from clean_code.energy import season_energy, annual_summary
from clean_code.plots import plot_day

# ══════════════════════════════════════════════════════════════════════════════
#  TESTS — run=False überspringt den ganzen Test
#
#  build_map : True  → Maps neu berechnen (dauert ~2 min)
#              False → bestehende .pkl laden
#
#  sweep     : True  → Simulation neu starten, CSVs schreiben
#              False → bestehende CSVs in results_{tag}/ laden
#
#  plots     : True  → Plots für Top-N PASS erstellen / überschreiben
#              False → keine Plots
#
#  map       : Pfad zur .pkl-Datei (None = auto aus config)
#  top       : Anzahl PASS-Kandidaten für Plots
# ══════════════════════════════════════════════════════════════════════════════
TESTS = [
    {
        "run":       True,
        "tag":       cfg.TAG,
        "map":       f"clean_code/maps/performance_maps_{cfg.TAG}.pkl",
        "build_map": False,
        "sweep":     True,
        "plots":     True,
        "top":      4,
    },
]
# ══════════════════════════════════════════════════════════════════════════════

MAX_OVERLOAD_STEPS = 0
MAX_FAN_LIM_STEPS  = 0


# ── Parallel-Worker ───────────────────────────────────────────────────────────
# Muss auf Modul-Ebene stehen, damit ProcessPoolExecutor ihn auf Windows per
# "spawn" in den Child-Prozessen importieren kann.

def _run_one_combo(args):
    """
    Simuliert alle Jahreszeiten für eine (Kältemittel, Durchmesser)-Kombination.

    Läuft in einem eigenen Prozess; bekommt 'maps' per Pickle übergeben
    (RegularGridInterpolator ist pickle-fähig).  Early-Exit bei Overload/Fan-Limit
    bleibt erhalten: die Schleife bricht ab und gibt den Fail-Grund zurück.
    """
    ref, c_d, maps, out_dir, tag = args
    for season in cfg.SEASON_DAYS:
        df = simulate(season, ref, c_d, maps)
        df.to_csv(_csv_path(out_dir, tag, ref, c_d, season), index=False)
        e = season_energy(df)
        if e["n_ac_overload"] > MAX_OVERLOAD_STEPS:
            return ref, c_d, f"FAIL (overload @ {season})"
        if e["n_fan_limited"] > MAX_FAN_LIM_STEPS:
            return ref, c_d, f"FAIL (fan_limited @ {season})"
    n = len(cfg.SEASON_DAYS)
    return ref, c_d, f"{n}/{n} seasons"


def _status(yr):
    if yr["n_ac_overload_year"] > MAX_OVERLOAD_STEPS:
        return "FAIL (overload)"
    if yr["n_fan_limited_year"] > MAX_FAN_LIM_STEPS:
        return "FAIL (fan_limited)"
    return "PASS"


def _csv_path(out_dir, tag, ref, c_d, season):
    return os.path.join(out_dir, f"sim_{tag}_{ref}_D{int(c_d)}mm_{season}.csv")


def _ranking_from_csvs(out_dir, tag):
    """Rekonstruiert Ranking aus vorhandenen CSVs (ohne neue Simulation)."""
    ranking_rows = []
    for ref in cfg.refrigerants:
        for c_d in cfg.compressor_diameters_mm:
            season_dfs = {}
            fail_reason = None
            for season in cfg.SEASON_DAYS:
                p = _csv_path(out_dir, tag, ref, c_d, season)
                if os.path.exists(p):
                    season_dfs[season] = pd.read_csv(p)
                else:
                    break   # Keine CSV → Saison wurde nicht simuliert (Early-Exit)

            if not season_dfs:
                row = {"refrigerant": ref, "c_d_mm": int(c_d),
                       "status": "FAIL (no data)", **{k: float("nan") for k in
                       ["SEER_year","cost_CHF_year","E_total_kWh_year",
                        "T_room_std_year","n_cycles_year","n_fan_limited_year",
                        "n_ac_overload_year","n_T_high_year"]}}
            elif len(season_dfs) < len(cfg.SEASON_DAYS):
                # Weniger Jahreszeiten → war Early-Exit-Disqualifikation
                # Status aus vorhandenen Daten ableiten
                last_e = season_energy(list(season_dfs.values())[-1])
                if last_e["n_ac_overload"] > MAX_OVERLOAD_STEPS:
                    fail_reason = "FAIL (overload)"
                elif last_e["n_fan_limited"] > MAX_FAN_LIM_STEPS:
                    fail_reason = "FAIL (fan_limited)"
                else:
                    fail_reason = "FAIL (incomplete)"
                row = {"refrigerant": ref, "c_d_mm": int(c_d),
                       "status": fail_reason, **{k: float("nan") for k in
                       ["SEER_year","cost_CHF_year","E_total_kWh_year",
                        "T_room_std_year","n_cycles_year","n_fan_limited_year",
                        "n_ac_overload_year","n_T_high_year"]}}
            else:
                summary = annual_summary(season_dfs)
                yr = summary[summary["season"] == "YEAR"].iloc[0]
                row = {
                    "refrigerant":        ref,
                    "c_d_mm":             int(c_d),
                    "SEER_year":          yr["SEER_year"],
                    "cost_CHF_year":      yr["cost_CHF_year"],
                    "E_total_kWh_year":   yr["E_total_kWh_year"],
                    "T_room_std_year":    yr["T_room_std_year"],
                    "n_cycles_year":      yr["n_cycles_year"],
                    "n_fan_limited_year": yr["n_fan_limited_year"],
                    "n_ac_overload_year": yr["n_ac_overload_year"],
                    "n_T_high_year":      yr["n_T_high_year"],
                    "status":             _status(yr),
                }
            ranking_rows.append(row)
    return pd.DataFrame(ranking_rows)


def run_test(tag, map_path=None, build_map=False, sweep=True, plots=True, top_n=3):
    """
    Führt einen Test-Run aus.

    Ergebnisse unter clean_code/results_{tag}/
      ranking_{tag}.csv        — Rangliste
      sim_*_{season}.csv       — Zeitserie pro Kombination und Jahreszeit
      plots/                   — Plots der Top-N PASS-Kandidaten
    """
    t0 = _time.time()
    _HERE   = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(_HERE, f"results_{tag}")
    os.makedirs(out_dir, exist_ok=True)

    map_path_abs = os.path.join(_ROOT, map_path) if map_path else None

    # ── 1. Maps ───────────────────────────────────────────────────────────────
    if build_map:
        print("Baue Performance-Maps ...")
        maps = build_all_maps(path=map_path_abs)
    else:
        maps = load_maps(path=map_path_abs) if (sweep or plots) else None

    # ── 2. Sweep ──────────────────────────────────────────────────────────────
    if sweep:
        n_total = len(cfg.refrigerants) * len(cfg.compressor_diameters_mm)

        # Alle (Kältemittel, Durchmesser)-Kombos als unabhängige Tasks verpacken.
        # maps wird per Pickle in jeden Child-Prozess kopiert — einmalig pro Prozess,
        # nicht pro Task, da ProcessPoolExecutor Prozesse wiederverwendet.
        combos = [
            (ref, c_d, maps, out_dir, tag)
            for ref in cfg.refrigerants
            for c_d in cfg.compressor_diameters_mm
        ]

        done = 0
        with ProcessPoolExecutor() as ex:
            # as_completed liefert Futures in Abschluss-Reihenfolge → Echtzeit-Feedback
            futures = {ex.submit(_run_one_combo, combo): combo for combo in combos}
            for fut in as_completed(futures):
                done += 1
                ref, c_d, msg = fut.result()
                print(f"[{done}/{n_total}]  {ref}  D={c_d:.0f}mm  {msg}", flush=True)

    # ── 3. Ranking ────────────────────────────────────────────────────────────
    rank_path = os.path.join(out_dir, f"ranking_{tag}.csv")
    rank_df = _ranking_from_csvs(out_dir, tag)
    rank_df["_pass"] = (rank_df["status"] == "PASS").astype(int)
    rank_df = rank_df.sort_values(
        by=["_pass", "T_room_std_year", "n_cycles_year", "cost_CHF_year"],
        ascending=[False, True, True, True]
    ).drop(columns="_pass").reset_index(drop=True)
    rank_df.index += 1
    rank_df.to_csv(rank_path)

    # Konsolen-Tabelle
    n_total = len(cfg.refrigerants) * len(cfg.compressor_diameters_mm)
    print("\n" + "=" * 90)
    print(f"  RANKING  [{tag}]  ({n_total} Kombinationen)")
    print("=" * 90)
    print(f"  {'#':>2}  {'Kaeltemittel':<10} {'D[mm]':>5}  {'SEER':>6}  "
          f"{'Kosten':>8}  {'Zyklen':>7}  {'T_high':>7}  Status")
    print("-" * 90)
    for rank, row in rank_df.iterrows():
        seer_s  = f"{row['SEER_year']:>6.2f}"       if pd.notna(row['SEER_year'])     else "   n/a"
        cost_s  = f"{row['cost_CHF_year']:>7.0f}.-" if pd.notna(row['cost_CHF_year']) else "    n/a"
        cyc_s   = f"{row['n_cycles_year']:>7.0f}"   if pd.notna(row['n_cycles_year']) else "    n/a"
        thigh_s = f"{row['n_T_high_year']:>7.0f}"   if pd.notna(row['n_T_high_year']) else "    n/a"
        print(f"  {rank:>2}  {row['refrigerant']:<10} {row['c_d_mm']:>5}  "
              f"{seer_s}  {cost_s}  {cyc_s}  {thigh_s}  {row['status']}")
    print("=" * 90)
    print(f"Ergebnisse: {out_dir}")

    # ── 4. Plots ──────────────────────────────────────────────────────────────
    if plots:
        plot_dir  = os.path.join(out_dir, "plots")
        top_pass  = rank_df[rank_df["status"] == "PASS"].head(top_n)
        if top_pass.empty:
            print("Keine PASS-Kandidaten für Plots.")
        else:
            print(f"Erstelle Plots für Top {len(top_pass)} ...")
            for _, row in top_pass.iterrows():
                ref = row["refrigerant"]
                c_d = float(row["c_d_mm"])
                for season in cfg.SEASON_DAYS:
                    p = _csv_path(out_dir, tag, ref, c_d, season)
                    if not os.path.exists(p):
                        continue
                    df = pd.read_csv(p)
                    fname = plot_day(df, season, ref, c_d, tag=tag, save=True,
                                     out_dir=plot_dir)
                    print(f"  -> {fname}")

    elapsed = _time.time() - t0
    print(f"Fertig in {elapsed:.1f} s\n")
    return rank_df


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # ── CLI-Modus ─────────────────────────────────────────────────────────
        parser = argparse.ArgumentParser()
        parser.add_argument("--tag",       required=True)
        parser.add_argument("--map",       default=None)
        parser.add_argument("--build_map", action="store_true")
        parser.add_argument("--sweep",     action="store_true")
        parser.add_argument("--plots",     action="store_true")
        parser.add_argument("--top",       type=int, default=3)
        args = parser.parse_args()
        run_test(args.tag, map_path=args.map, build_map=args.build_map,
                 sweep=args.sweep, plots=args.plots, top_n=args.top)
    else:
        # ── Run-Button-Modus ──────────────────────────────────────────────────
        active = [t for t in TESTS if t["run"]]
        if not active:
            print("Kein Test aktiv — setze 'run': True in der TESTS-Liste.")
        for test in active:
            print(f"\n{'='*60}\n  Test: {test['tag']}\n{'='*60}")
            run_test(
                tag       = test["tag"],
                map_path  = test.get("map"),
                build_map = test.get("build_map", False),
                sweep     = test.get("sweep",     True),
                plots     = test.get("plots",     True),
                top_n     = test.get("top",       3),
            )
