"""
Energiebilanz und Jahreshochrechnung.
"""
import pandas as pd
import clean_code.config as cfg


def season_energy(df):
    """
    Tagesbilanz aus 5-min-Simulationsergebnis.

    Rückgabe: dict mit
        E_comp_kWh    — Kompressorenergie [kWh/Tag]
        E_total_kWh   — Gesamtenergie (= E_comp, Ventilatorleistung nicht separat)
        Q_cool_kWh    — Gelieferte Kühlenergie [kWh/Tag]
        n_T_low       — Schritte mit T_room < T_ROOM_MIN
        n_T_high      — Schritte mit T_room > T_ROOM_MAX
        n_fan_limited — Schritte mit Lüfter-Engpass
        n_ac_overload — Schritte mit AC-Überlast (Q_max < q_server)
        T_room_std    — Standardabweichung T_room [K]
        n_cycles      — Anzahl Kompressorzyklen am Tag
    """
    dt_h = float(df["time"].iloc[1] - df["time"].iloc[0])
    return {
        "E_comp_kWh":    float((df["W_comp_kW"] * dt_h).sum()),
        "E_total_kWh":   float((df["W_comp_kW"] * dt_h).sum()),
        "Q_cool_kWh":    float((df["Q_AC_kW"]   * dt_h).sum()),
        "n_T_low":       int((df["T_room"] < cfg.T_ROOM_MIN).sum()),
        "n_T_high":      int((df["T_room"] > cfg.T_ROOM_MAX).sum()),
        "n_fan_limited": int(df["fan_limited"].sum()) if "fan_limited" in df.columns else 0,
        "n_ac_overload": int(df["ac_overloaded"].sum()),
        "T_room_std":    float(df["T_room"].std()),
        "n_cycles":      int(df["n_cycles_cum"].iloc[-1]),
    }


def annual_summary(season_results, season_days=None):
    """
    Jahreshochrechnung aus Dict {season: DataFrame}.

    season_days: dict mit season → Anzahl repräsentativer Tage (default: cfg.SEASON_DAYS)

    Rückgabe: DataFrame mit einer Zeile pro Jahreszeit + Jahressumme (YEAR).
    """
    if season_days is None:
        season_days = cfg.SEASON_DAYS

    rows   = []
    totals = {k: 0.0 for k in ["E_comp_kWh", "E_total_kWh", "Q_cool_kWh",
                                 "n_T_low", "n_T_high", "n_fan_limited",
                                 "n_ac_overload", "n_cycles"]}
    t_std_sum  = 0.0
    total_days = 0

    for season, df in season_results.items():
        days = season_days[season]
        e    = season_energy(df)
        row  = {"season": season, "days": days}
        for k, v in e.items():
            if k == "T_room_std":
                row["T_room_std_day"] = round(v, 4)
                t_std_sum  += v * days
                total_days += days
            else:
                row[k + "_day"]  = round(v, 3)
                row[k + "_year"] = round(v * days, 2)
                totals[k]       += v * days
        row["SEER_day"] = (e["Q_cool_kWh"] / e["E_total_kWh"]
                           if e["E_total_kWh"] > 0 else float("nan"))
        rows.append(row)

    E_tot = totals["E_total_kWh"]
    Q_tot = totals["Q_cool_kWh"]
    yr    = {"season": "YEAR", "days": sum(season_days.values())}
    for k, v in totals.items():
        yr[k + "_day"]  = float("nan")
        yr[k + "_year"] = round(v, 2)
    yr["SEER_day"]        = float("nan")
    yr["SEER_year"]       = round(Q_tot / E_tot, 3) if E_tot > 0 else float("nan")
    yr["cost_CHF_year"]   = round(E_tot * cfg.ELECTRICITY_PRICE_CHF_KWH, 1)
    yr["T_room_std_day"]  = float("nan")
    yr["T_room_std_year"] = round(t_std_sum / total_days, 4) if total_days > 0 else float("nan")
    yr["n_cycles_year"]   = round(totals["n_cycles"], 1)
    rows.append(yr)

    return pd.DataFrame(rows)
