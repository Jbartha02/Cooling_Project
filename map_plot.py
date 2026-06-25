"""
3D Performance-Map: R290, D=40 mm  —  COP, m_dot, Q über T_amb × T_room
Lädt COP/Q aus bestehendem Map-Pickle; m_dot wird auf dem Config-Raster nachberechnet.
"""
import sys, os
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import os
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D          # noqa: F401  (Side-effect: 3d projection)

import clean_code.config as cfg
from clean_code.performance_map import load_maps

REFRIGERANT = "R290"
C_D_MM      = 40.

# ── 1. Map laden ──────────────────────────────────────────────────────────────
_MAP_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "clean_code", "maps", "performance_maps_5C_sh5_pev5_pco10_fan106.pkl",
)
print(f"Lade Map: {_MAP_PATH}")
maps = load_maps(path=_MAP_PATH)
itp  = maps[REFRIGERANT][C_D_MM]

# ── 2. Feines Auswerteraster für glatte Oberflächen ───────────────────────────
T_amb_fine  = np.linspace(cfg.T_amb_grid[0],  cfg.T_amb_grid[-1],  60)
T_room_fine = np.linspace(cfg.T_room_grid[0], cfg.T_room_grid[-1], 40)
TA, TR = np.meshgrid(T_amb_fine, T_room_fine, indexing="ij")   # (60, 40)

pts   = np.column_stack([TA.ravel(), TR.ravel()])
Z_cop = itp["COP_eff"](pts).reshape(TA.shape)
Z_Q   = itp["Q_AC"](pts).reshape(TA.shape)

# ── 3. Plots ──────────────────────────────────────────────────────────────────
ELEV, AZIM = 25, -60

fig = plt.figure(figsize=(13, 6))
fig.suptitle(
    f"Performance-Map  {REFRIGERANT}  D = {C_D_MM:.0f} mm"
    f"  |  T_AC = {cfg.T_AC:.0f} °C  sh = {cfg.delta_T_sh:.0f} K",
    fontsize=13, fontweight="bold",
)

specs = [
    (Z_cop, "COP [-]",  "viridis"),
    (Z_Q,   "Q [kW]",   "coolwarm"),
]

for col, (Z, zlabel, cmap) in enumerate(specs, start=1):
    ax = fig.add_subplot(1, 2, col, projection="3d")
    surf = ax.plot_surface(TR, TA, Z, cmap=cmap, edgecolor="none", alpha=0.88, rcount=40, ccount=60)

    # Konturlinien am Boden projizieren
    z_floor = np.nanmin(Z) - 0.05 * (np.nanmax(Z) - np.nanmin(Z))
    ax.contourf(TR, TA, Z, zdir="z", offset=z_floor, cmap=cmap, alpha=0.35, levels=12)

    ax.set_xlabel("T_room [°C]", labelpad=6)
    ax.set_ylabel("T_amb [°C]", labelpad=6)
    ax.set_zlabel(zlabel, labelpad=6)
    ax.set_title(zlabel, fontsize=11)
    ax.view_init(elev=ELEV, azim=AZIM)
    ax.invert_yaxis()   # T_amb steigt nach vorne → Fläche steigt nach hinten

    cb = fig.colorbar(surf, ax=ax, shrink=0.45, aspect=12, pad=0.1)
    cb.set_label(zlabel, fontsize=9)

plt.tight_layout()

out_path = os.path.join(_ROOT, "map_plot_R290_D40.png")
fig.savefig(out_path, dpi=150, bbox_inches="tight")
print(f"\nGespeichert: {out_path}")
plt.show()
