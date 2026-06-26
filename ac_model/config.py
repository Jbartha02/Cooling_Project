import sys, os
import pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# ── Season ─────────────────────────────────────────────────────────────────────
season = "summer"
season_col = {
    "summer": "Ambient_Temp_Summer_C",
    "spring": "Ambient_Temp_Spring_C",
    "fall":   "Ambient_Temp_Fall_C",
    "winter": "Ambient_Temp_Winter_C",
}
# ── AC ─────────────────────────────────────────────────────────────────────────
T_AC       = 5.

# ── Ventilation ────────────────────────────────────────────────────────────────
m_dot_vent_max = 1.5    # kg/s — maximum fan mass flow rate
delta_p_fan    = 265.   # Pa   — pressure drop across fan
eta_fan        = 0.68   # —    — fan efficiency
rho_air        = 1.2    # kg/m³
W_vent = m_dot_vent_max * delta_p_fan / (rho_air * eta_fan) / 1000  # [kW] max fan power

path = os.path.join(os.path.dirname(__file__), "Results", f"simulation_{season}_{T_AC}C_{m_dot_vent_max}kgs_results.csv")
if os.path.exists(path):
    df = pd.read_csv(path)
    ac_on      = df["ac_on"].values
    vent_on    = df["vent_on"].values
    ac_power   = df["Q_AC_kW"].values
    time       = df["time"].values

# ── Compressor ────────────────────────────────────────────────────────────────
c_d = 0.03  # m, cylinder bore diameter [0.03, 0.04, 0.05]

# ── Refrigerant ───────────────────────────────────────────────────────────────
delta_T_sh = 5.     # K — superheating
delta_T_sc = 7.     # K — subcooling
fluid = "R1234yf"   # {Propane, R1234yf, Dimethyl ether}
Eh = "CBar"

fluid_so = "air"
fluid_si = "air"

min_pinch_ev = 5.   # K — evaporator minimum pinch
min_pinch_co = 5.   # K — condenser minimum pinch
min_pinch    = min_pinch_ev  # backwards-compat alias

min_pressure_ratio = 2.0

# ── COP sweep ─────────────────────────────────────────────────────────────────
refrigerants            = ["R290", "R1234yf", "DME"]
compressor_diameters_mm = [30., 40., 50.]

# Seasonal design points: T_amb determines the condenser heat-sink temperature
design_points = [
    {"season": "winter", "T_amb":  5., "T_room": 15.},
    {"season": "spring", "T_amb": 12., "T_room": 15.},
    {"season": "summer", "T_amb": 25., "T_room": 15.},
    {"season": "fall",   "T_amb": 12., "T_room": 15.},
]

