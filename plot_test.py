"""
Freilauf-Plot: Wie heizt sich der Raum im Sommer auf ohne AC?
Szenarien: (1) keine Kühlung, (2) nur Ventilation
"""
import sys, os
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import Fluid_CP_moist_air as Fmoist
import clean_code.config as cfg
from clean_code.simulation import _step_no_flow, _step_with_flow, _vent_state

# ── Daten laden ───────────────────────────────────────────────────────────────
df_in    = pd.read_csv(cfg.CSV_5MIN)
T_amb    = df_in[cfg.season_col["summer"]].values
q_server = df_in["Server_Heating_Power_kW"].values

def _hhmm(arr):
    out = np.empty(len(arr))
    for k, t in enumerate(arr):
        h, m = str(t).split(":")
        out[k] = int(h) + int(m) / 60.
    return out

t  = _hhmm(df_in["Time"].values)
dt = float(t[1] - t[0]) * 3600.
n  = len(t)

def _T_from_z(z):
    X = max(z[1] / cfg.m_Air, 0.0)
    return (z[0] - cfg._H_A0 - X * cfg._L0) / (cfg._CP_A + X * cfg._CP_W)

# ── Szenario 1: keine Kühlung ─────────────────────────────────────────────────
T_none = np.zeros(n)
z = [cfg.h_0, cfg.mw0]
for i in range(n):
    z = _step_no_flow(z, dt, q_server[i])
    T_none[i] = _T_from_z(z)

# ── Szenario 2: nur Ventilation ───────────────────────────────────────────────
T_vent = np.zeros(n)
z = [cfg.h_0, cfg.mw0]
for i in range(n):
    h_vent, X_vent = _vent_state(T_amb[i])
    h_target  = (cfg._CP_A * cfg.T_room_set + cfg._H_A0
                 + X_vent * (cfg._L0 + cfg._CP_W * cfg.T_room_set))
    dh_to_set = h_target - h_vent
    if dh_to_set > 1e-6 and q_server[i] / dh_to_set <= cfg.m_dot_vent_max:
        m_dot_vent = q_server[i] / dh_to_set
        z = _step_with_flow(z, dt, q_server[i], m_dot_vent, h_vent, X_vent)
    else:
        z = _step_no_flow(z, dt, q_server[i])
    T_vent[i] = _T_from_z(z)

# ── Plot ──────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(12, 5))

ax.plot(t, T_amb,  color="gray",      lw=1.0, ls="--", label="T_amb (Sommer)")
ax.plot(t, T_none, color="firebrick", lw=1.8, label="Keine Kühlung")
ax.plot(t, T_vent, color="steelblue", lw=1.8, label="Nur Ventilation")
ax.axhline(cfg.T_room_set, color="green",  lw=0.8, ls=":",  label=f"Sollwert {cfg.T_room_set}°C")
ax.axhline(cfg.T_ON,       color="orange", lw=0.8, ls="--", label=f"T_ON {cfg.T_ON}°C")

ax2 = ax.twinx()
ax2.fill_between(t, q_server, alpha=0.15, color="darkorange")
ax2.set_ylabel("Serverlast [kW]", color="darkorange")
ax2.tick_params(colors="darkorange")

ax.set_xlabel("Zeit [h]")
ax.set_ylabel("Temperatur [°C]")
ax.set_title(f"Sommer-Freilauf ohne AC  |  fan={round(cfg.m_dot_vent_max*100)}")
ax.legend(loc="upper left", fontsize=9)

plt.tight_layout()
out = os.path.join(_ROOT, "freerun_summer.png")
fig.savefig(out, dpi=130, bbox_inches="tight")
plt.close(fig)
print(f"Gespeichert: {out}")
