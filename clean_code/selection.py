"""
Vergleich mehrerer Simulations-Ergebnisse.

Aufruf (aus Projektordner):
    python clean_code/selection.py <results_ordner1> [<results_ordner2> ...]

Ohne Argumente: alle results_*/ Ordner im clean_code-Verzeichnis werden verglichen.
Ausgabe: clean_code/comparison.png
"""
import sys, os
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.join(_HERE, '..')
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import clean_code.config as cfg

TOTAL_DAYS = sum(cfg.SEASON_DAYS.values())


def _label(ref, d):
    return f"{ref}\nD={int(d)}mm"


def load_folder(folder):
    """Liest Ranking-CSV und berechnet T_room_mean aus Simulations-CSVs."""
    files = os.listdir(folder)
    rank_files = [f for f in files if f.startswith("ranking_") and f.endswith(".csv")]
    if not rank_files:
        raise FileNotFoundError(f"Kein Ranking-CSV in {folder}")

    rank_df = pd.read_csv(os.path.join(folder, rank_files[0]), index_col=0)
    tag = rank_files[0].replace("ranking_", "").replace(".csv", "")

    T_means = []
    for _, row in rank_df.iterrows():
        ref = row["refrigerant"]
        d   = int(row["c_d_mm"])
        w_mean = 0.0
        ok = True
        for season, days in cfg.SEASON_DAYS.items():
            match = [f for f in files
                     if f"_{ref}_D{d}mm_{season}" in f and f.endswith(".csv")]
            if match:
                df_s = pd.read_csv(os.path.join(folder, match[0]))
                w_mean += df_s["T_room"].mean() * days / TOTAL_DAYS
            else:
                ok = False
                break
        T_means.append(w_mean if ok else float("nan"))

    rank_df["T_room_mean_year"] = T_means
    return tag, rank_df


def compare(folders):
    datasets = {}
    for folder in folders:
        tag, df = load_folder(folder)
        # Einheitliche Reihenfolge nach (Kältemittel, Durchmesser) — nicht nach Score!
        df = df.sort_values(["refrigerant", "c_d_mm"]).reset_index(drop=True)
        datasets[tag] = df

    # Kandidaten-Labels aus dem ersten (jetzt gleich sortierten) DataFrame
    first_df   = next(iter(datasets.values()))
    all_labels = [_label(r["refrigerant"], r["c_d_mm"]) for _, r in first_df.iterrows()]

    # Nur Kandidaten zeigen die in mind. einer Konfiguration PASS haben
    any_pass = np.zeros(len(all_labels), dtype=bool)
    for df in datasets.values():
        any_pass |= (df["status"] == "PASS").values
    keep_idx = np.where(any_pass)[0]

    candidates = [all_labels[i] for i in keep_idx]
    datasets   = {tag: df.iloc[keep_idx].reset_index(drop=True)
                  for tag, df in datasets.items()}

    x     = np.arange(len(candidates))
    n_cfg = len(datasets)
    bar_w = 0.8 / n_cfg
    colors = plt.rcParams["axes.prop_cycle"].by_key()["color"]

    fig, axes = plt.subplots(3, 1, figsize=(max(10, len(candidates) * 1.8), 14))
    fig.subplots_adjust(hspace=0.5)

    # ── Subplot 1: T_room Mittelwert ± Standardabweichung ────────────────────
    ax = axes[0]
    for k, (tag, df) in enumerate(datasets.items()):
        off    = (k - (n_cfg - 1) / 2) * bar_w
        means  = df["T_room_mean_year"].values
        stds   = df["T_room_std_year"].values
        passed = (df["status"] == "PASS").values

        ax.errorbar(x[passed]  + off, means[passed],  yerr=stds[passed],
                    fmt="o", capsize=5, lw=1.8, ms=7,
                    color=colors[k % len(colors)], label=tag)
        if (~passed).any():
            ax.errorbar(x[~passed] + off, means[~passed], yerr=stds[~passed],
                        fmt="x", capsize=4, lw=1.0, ms=7,
                        color=colors[k % len(colors)], alpha=0.35)

    ax.axhline(cfg.T_room_set, color="green",     lw=1.0, ls=":",  label=f"Sollwert {cfg.T_room_set}°C")
    ax.axhline(cfg.T_ON,       color="orange",    lw=0.9, ls="--", label=f"T_ON {cfg.T_ON}°C")
    ax.axhline(cfg.T_OFF,      color="steelblue", lw=0.9, ls="--", label=f"T_OFF {cfg.T_OFF}°C")
    ax.set_xticks(x)
    ax.set_xticklabels(candidates, fontsize=8)
    ax.set_ylabel("T_room [°C]")
    ax.set_title("Ø Raumtemperatur ± Standardabweichung  (Jahresschnitt, gewichtet)")
    ax.legend(fontsize=8, loc="upper right")

    # ── Subplot 2: Kompressorzyklen ───────────────────────────────────────────
    ax = axes[1]
    for k, (tag, df) in enumerate(datasets.items()):
        off    = (k - (n_cfg - 1) / 2) * bar_w
        vals   = df["n_cycles_year"].values.astype(float)
        passed = (df["status"] == "PASS").values
        bars   = ax.bar(x + off, vals, width=bar_w * 0.9,
                        color=colors[k % len(colors)], alpha=0.85, label=tag)
        for bar, p in zip(bars, passed):
            if not p:
                bar.set_hatch("//")
                bar.set_alpha(0.4)

    ax.set_xticks(x)
    ax.set_xticklabels(candidates, fontsize=8)
    ax.set_ylabel("Zyklen [/Jahr]")
    ax.set_title("Kompressor Ein/Aus-Zyklen pro Jahr  (// = FAIL)")
    ax.legend(fontsize=8, loc="upper right")

    # ── Subplot 3: Energie + Kosten ───────────────────────────────────────────
    ax   = axes[2]
    ax_c = ax.twinx()

    for k, (tag, df) in enumerate(datasets.items()):
        off    = (k - (n_cfg - 1) / 2) * bar_w
        energy = df["E_total_kWh_year"].values.astype(float)
        costs  = df["cost_CHF_year"].values.astype(float)
        passed = (df["status"] == "PASS").values

        bars = ax.bar(x + off, energy, width=bar_w * 0.9,
                      color=colors[k % len(colors)], alpha=0.75, label=tag)
        for bar, p in zip(bars, passed):
            if not p:
                bar.set_hatch("//")
                bar.set_alpha(0.35)

        ax_c.plot(x + off, costs, marker="D", ms=6, lw=0,
                  color=colors[k % len(colors)], zorder=5, label=f"{tag} [CHF]")

    # Kosten-Achse bei 0 starten damit Rauten-Höhe proportional zu CHF-Wert
    all_costs = pd.concat([df["cost_CHF_year"] for df in datasets.values()]).dropna()
    ax_c.set_ylim(0, all_costs.max() * 1.25)
    ax.set_xticks(x)
    ax.set_xticklabels(candidates, fontsize=8)
    ax.set_ylabel("Energie [kWh/Jahr]")
    ax_c.set_ylabel("Kosten [CHF/Jahr]", color="dimgray")
    ax_c.tick_params(colors="dimgray")
    ax.set_title("Jahresenergieverbrauch (Balken) + Kosten CHF (Rauten)  (// = FAIL)")
    ax.legend(fontsize=8, loc="upper left")
    ax_c.legend(fontsize=8, loc="upper right")

    # Dateiname aus Tags: comparison_tag1_vs_tag2.png
    tag_parts = "_vs_".join(datasets.keys())
    out = os.path.join(_HERE, f"comparison_{tag_parts}.png")
    fig.savefig(out, dpi=130, bbox_inches="tight")
    plt.close(fig)
    print(f"Gespeichert: {out}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        folders = sys.argv[1:]
    else:
        folders = sorted([
            os.path.join(_HERE, d) for d in os.listdir(_HERE)
            if d.startswith("results_") and os.path.isdir(os.path.join(_HERE, d))
        ])
        if not folders:
            print("Keine results_*/ Ordner gefunden.")
            print("Aufruf: python clean_code/selection.py <ordner1> [ordner2 ...]")
            sys.exit(1)
        print(f"Vergleiche: {[os.path.basename(f) for f in folders]}")

    compare(folders)
