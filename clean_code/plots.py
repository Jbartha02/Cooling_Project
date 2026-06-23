"""
Visualisierung des Tagesbetriebs (4-Subplot-Layout).
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

import clean_code.config as cfg

_PLOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plots")


def plot_day(df, season, refrigerant, c_d_mm, tag="", save=True, out_dir=None):
    """
    4-Subplot-Tagesplot.

    axes[0]: T_room, T_amb, φ_room (rechte Achse)
    axes[1]: Q_AC_kW, q_server_kW, fan_limited-Hintergrund
    axes[2]: W_comp_kW (links), m_dot_ac (rechts), COP (ganz rechts)
    axes[3]: ac_on / vent_on / fan_limited (Boolean-Stepplot)
    """
    t = df["time"].values

    fig, axes = plt.subplots(4, 1, figsize=(12, 11), sharex=True)
    fig.suptitle(f"{tag}  |  {refrigerant}  D={c_d_mm:.0f}mm  |  {season.capitalize()}",
                 fontsize=13, fontweight="bold")

    # ── ax0: Temperaturen ─────────────────────────────────────────────────────
    ax = axes[0]
    ax.plot(t, df["T_room"], color="steelblue", lw=1.5, label="T_room")
    ax.plot(t, df["T_amb"],  color="gray",      lw=1.0, ls="--", label="T_amb")
    ax.axhline(cfg.T_room_set, color="green", lw=0.8, ls=":")
    ax.axhline(cfg.T_ROOM_MIN, color="red",   lw=0.8, ls="--", alpha=0.7)
    ax.axhline(cfg.T_ROOM_MAX, color="red",   lw=0.8, ls="--", alpha=0.7)
    ax.fill_between(t, cfg.T_ROOM_MIN, cfg.T_ROOM_MAX, alpha=0.07, color="green")
    ax.set_ylabel("Temperatur [°C]")
    ax0r = ax.twinx()
    ax0r.plot(t, df["phi_room"] * 100., color="teal", lw=1.0, ls=":", alpha=0.8, label="φ_room")
    ax0r.set_ylabel("Rel. Feuchte [%]", color="teal")
    ax0r.tick_params(colors="teal")
    ax0r.set_ylim(0, 100)
    lines0, labs0 = ax.get_legend_handles_labels()
    lines0r, labs0r = ax0r.get_legend_handles_labels()
    ax.legend(lines0 + lines0r, labs0 + labs0r, loc="upper right", fontsize=8)

    # ── ax1: Kühlleistung ─────────────────────────────────────────────────────
    ax = axes[1]
    ax.plot(t, df["q_server_kW"], color="darkorange", lw=1.2, label="q_server")
    ax.plot(t, df["Q_AC_kW"],     color="steelblue",  lw=1.5, label="Q_AC")
    if "fan_limited" in df.columns:
        for i, lim in enumerate(df["fan_limited"].values):
            if lim:
                ax.axvspan(t[i], t[min(i+1, len(t)-1)], color="red", alpha=0.15)
    fl_patch = mpatches.Patch(color="red", alpha=0.3, label="fan limited")
    ax.legend(handles=[*ax.get_legend_handles_labels()[0], fl_patch],
              loc="upper right", fontsize=8)
    ax.set_ylabel("Leistung [kW]")

    # ── ax2: W_el (comp+fan) + m_dot_ac + COP_sys (aus Map) ─────────────────
    # W_el_kW  = W_comp_kW + W_fan_kW  (gesamte elektr. Aufnahme)
    # COP_eff  = aus Kennfeld interpoliert: Q_cool_max/(W_comp+W_fan) bei Vollast
    ax = axes[2]
    ax.plot(t, df["W_el_kW"],   color="#4472C4", lw=1.5, label="W_el (comp+fan)")
    ax.plot(t, df["W_comp_kW"], color="#A9C4E8", lw=1.0, ls="--", alpha=0.8, label="W_comp")
    ax.plot(t, df["W_fan_kW"],  color="#A0D0A0", lw=1.0, ls=":",  alpha=0.8, label="W_fan")
    ax.set_ylabel("Elektr. Leistung [kW]")

    m_dot = np.where(df["ac_on"].values,   df["m_dot_ac"].values,
            np.where(df["vent_on"].values, df["m_dot_vent"].values, 0.0))

    ax2r_mdot = ax.twinx()
    ax2r_mdot.plot(t, m_dot, color="#70AD47", lw=1.0, ls="--",
                   alpha=0.7, label="m_dot")
    ax2r_mdot.set_ylabel("m_dot [kg/s]", color="#70AD47")
    ax2r_mdot.tick_params(colors="#70AD47")

    ax2r_cop = ax.twinx()
    ax2r_cop.spines["right"].set_position(("axes", 1.12))
    # COP_eff aus Map: Q_cool_max / (W_comp + W_fan) bei Vollast-Betriebspunkt
    cop   = df["COP_eff"].values
    valid = np.isfinite(cop) & (df["ac_on"].values)
    ax2r_cop.plot(t[valid], cop[valid], color="crimson", lw=1.2, ls="-.", label="COP_sys")
    ax2r_cop.set_ylabel("COP_sys [-]", color="crimson")
    ax2r_cop.tick_params(colors="crimson")

    lines1, labs1 = ax.get_legend_handles_labels()
    lines2, labs2 = ax2r_mdot.get_legend_handles_labels()
    lines3, labs3 = ax2r_cop.get_legend_handles_labels()
    ax.legend(lines1 + lines2 + lines3, labs1 + labs2 + labs3,
              loc="upper right", fontsize=8)

    # ── ax3: Boolean-Flags ────────────────────────────────────────────────────
    ax = axes[3]
    ax.step(t, df["ac_on"].astype(int),       where="post", lw=1.2,
            color="steelblue", label="ac_on")
    ax.step(t, df["vent_on"].astype(int) * 2, where="post", lw=1.2,
            color="green",     label="vent_on")
    if "fan_limited" in df.columns:
        ax.step(t, df["fan_limited"].astype(int) * 3, where="post", lw=1.2,
                color="red", label="fan_limited")
    ax.set_yticks([0, 1, 2, 3])
    ax.set_yticklabels(["OFF", "AC", "VENT", "FAN_LIM"], fontsize=8)
    ax.set_xlabel("Zeit [h]")
    ax.legend(loc="upper right", fontsize=8)

    dt_h = t[1] - t[0] if len(t) > 1 else 1/12
    axes[0].set_xlim(t[0], t[-1] + dt_h)   # volle 24 h sichtbar (letzter Schritt inkl.)
    axes[-1].set_xticks(range(0, 25, 2))

    plt.tight_layout()

    if save:
        save_dir = out_dir if out_dir else _PLOT_DIR
        os.makedirs(save_dir, exist_ok=True)
        fname = os.path.join(save_dir,
                             f"{tag}_{refrigerant}_D{int(c_d_mm)}mm_{season}.png")
        fig.savefig(fname, dpi=120, bbox_inches="tight")
        plt.close(fig)
        return fname
    return fig
