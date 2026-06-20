"""
Performance-Map: Aufbau, Speicherung und Abfrage der COP/Q-Kennfelder.
"""
import sys, os
_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import pickle
import warnings
import numpy as np
import Fluid_CP_moist_air as Fmoist
from scipy.interpolate import RegularGridInterpolator, NearestNDInterpolator

from ac_model.ac import optimize_cop
import clean_code.config as cfg

_KEYS = ["COP_eff", "Q_AC", "W_comp", "W_vent"]


def _map_path(T_AC, delta_T_sh, min_pinch_ev, min_pinch_co):
    sh  = int(round(delta_T_sh))
    pev = int(round(min_pinch_ev))
    pco = int(round(min_pinch_co))
    tag = f"p{pev}" if pev == pco else f"pev{pev}_pco{pco}"
    return os.path.join(cfg.MAP_DIR, f"performance_maps_{T_AC:.0f}C_sh{sh}_{tag}.pkl")


def _fill_nan(grid, T_amb_grid, T_room_grid):
    valid = ~np.isnan(grid)
    if valid.all():
        return grid
    coords = np.array([
        (T_amb_grid[i], T_room_grid[j])
        for i in range(len(T_amb_grid))
        for j in range(len(T_room_grid))
        if valid[i, j]
    ])
    values = grid[valid]
    nn = NearestNDInterpolator(coords, values)
    nan_i, nan_j = np.where(~valid)
    for i, j in zip(nan_i, nan_j):
        grid[i, j] = float(nn(T_amb_grid[i], T_room_grid[j]))
    return grid


def _w_vent(P_cool_kW, T_room, T_AC):
    h_in  = Fmoist.state_moist(["T", "phi"], [T_room, 0.6])["h*"]
    h_out = Fmoist.state_moist(["T", "phi"], [T_AC,   1.0])["h*"]
    dh = h_in - h_out
    if dh <= 0:
        return 0.0
    m_dot = P_cool_kW / dh
    rho   = 1.0 / Fmoist.state_moist(["T", "phi"], [T_room, 0.6])["v*"]
    return m_dot * cfg.delta_p_fan / (rho * cfg.eta_fan) / 1000.0


def build_map(refrigerant, c_d_mm, T_AC=None, delta_T_sh=None,
              min_pinch_ev=None, min_pinch_co=None):
    T_AC_      = T_AC       if T_AC       is not None else cfg.T_AC
    dT_sh_     = delta_T_sh if delta_T_sh is not None else cfg.delta_T_sh
    p_ev_      = min_pinch_ev if min_pinch_ev is not None else cfg.min_pinch_ev
    p_co_      = min_pinch_co if min_pinch_co is not None else cfg.min_pinch_co

    n_a = len(cfg.T_amb_grid)
    n_r = len(cfg.T_room_grid)
    grids = {k: np.full((n_a, n_r), np.nan) for k in _KEYS}

    for i, T_amb in enumerate(cfg.T_amb_grid):
        for j, T_room in enumerate(cfg.T_room_grid):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                res = optimize_cop(
                    refrigerant, c_d_mm, T_amb, T_room,
                    min_pressure_ratio=cfg.min_pressure_ratio,
                    T_AC=T_AC_, delta_T_sh=dT_sh_,
                    min_pinch_ev=p_ev_, min_pinch_co=p_co_,
                )
            if not res["success"]:
                continue
            h_in    = Fmoist.state_moist(["T", "phi"], [T_room, 0.6])["h*"]
            h_out   = Fmoist.state_moist(["T", "phi"], [T_AC_,  1.0])["h*"]
            dh_fan  = h_in - h_out
            Q_fan_max = cfg.m_dot_vent_max * dh_fan if dh_fan > 0 else 0.0
            P_cool  = min(res["P_cool_kW"], Q_fan_max)
            W_comp  = res["W_comp_kW"]
            W_vent_ = _w_vent(P_cool, T_room, T_AC_)
            denom   = W_comp + W_vent_
            COP_eff = P_cool / denom if denom > 0 else 0.0

            grids["COP_eff"][i, j] = COP_eff
            grids["Q_AC"][i, j]    = P_cool
            grids["W_comp"][i, j]  = W_comp
            grids["W_vent"][i, j]  = W_vent_

    for k in _KEYS:
        grids[k] = _fill_nan(grids[k], cfg.T_amb_grid, cfg.T_room_grid)

    return {
        k: RegularGridInterpolator(
            (cfg.T_amb_grid, cfg.T_room_grid), grids[k],
            method="linear", bounds_error=False, fill_value=None,
        )
        for k in _KEYS
    }


def build_all_maps(T_AC=None, delta_T_sh=None, min_pinch_ev=None, min_pinch_co=None,
                   path=None):
    T_AC_  = T_AC       if T_AC       is not None else cfg.T_AC
    dT_sh_ = delta_T_sh if delta_T_sh is not None else cfg.delta_T_sh
    p_ev_  = min_pinch_ev if min_pinch_ev is not None else cfg.min_pinch_ev
    p_co_  = min_pinch_co if min_pinch_co is not None else cfg.min_pinch_co
    path_  = path if path else _map_path(T_AC_, dT_sh_, p_ev_, p_co_)

    os.makedirs(cfg.MAP_DIR, exist_ok=True)
    maps  = {}
    total = len(cfg.refrigerants) * len(cfg.compressor_diameters_mm)
    idx   = 0
    print(f"Baue Maps: T_AC={T_AC_}°C  sh={dT_sh_}K  pinch_ev={p_ev_}K  pinch_co={p_co_}K ...")
    for ref in cfg.refrigerants:
        maps[ref] = {}
        for c_d in cfg.compressor_diameters_mm:
            idx += 1
            print(f"  [{idx:2d}/{total}]  {ref:<10}  D={c_d:.0f}mm ... ", end="", flush=True)
            maps[ref][c_d] = build_map(ref, c_d, T_AC_, dT_sh_, p_ev_, p_co_)
            print("OK")
    with open(path_, "wb") as f:
        pickle.dump(maps, f)
    print(f"Maps gespeichert: {path_}")
    return maps


def load_maps(path=None, T_AC=None, delta_T_sh=None,
              min_pinch_ev=None, min_pinch_co=None):
    T_AC_  = T_AC       if T_AC       is not None else cfg.T_AC
    dT_sh_ = delta_T_sh if delta_T_sh is not None else cfg.delta_T_sh
    p_ev_  = min_pinch_ev if min_pinch_ev is not None else cfg.min_pinch_ev
    p_co_  = min_pinch_co if min_pinch_co is not None else cfg.min_pinch_co
    path_  = path if path else _map_path(T_AC_, dT_sh_, p_ev_, p_co_)

    if os.path.exists(path_):
        with open(path_, "rb") as f:
            return pickle.load(f)
    print(f"Keine Map gefunden unter {path_} — baue neu ...")
    return build_all_maps(T_AC_, dT_sh_, p_ev_, p_co_, path_)


def query(maps, refrigerant, c_d_mm, T_amb, T_room):
    T_a = float(np.clip(T_amb,  cfg.T_amb_grid[0],  cfg.T_amb_grid[-1]))
    T_r = float(np.clip(T_room, cfg.T_room_grid[0], cfg.T_room_grid[-1]))
    pt  = np.array([[T_a, T_r]])
    itp = maps[refrigerant][c_d_mm]
    return (
        float(itp["COP_eff"](pt)[0]),
        float(itp["Q_AC"](pt)[0]),
        float(itp["W_comp"](pt)[0]),
        float(itp["W_vent"](pt)[0]),
    )


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--T_AC",      type=float, default=cfg.T_AC)
    parser.add_argument("--sh",        type=float, default=cfg.delta_T_sh, dest="delta_T_sh")
    parser.add_argument("--pinch_ev",  type=float, default=cfg.min_pinch)
    parser.add_argument("--pinch_co",  type=float, default=cfg.min_pinch)
    parser.add_argument("--path",      type=str,   default=None)
    args = parser.parse_args()
    build_all_maps(args.T_AC, args.delta_T_sh, args.pinch_ev, args.pinch_co, args.path)
