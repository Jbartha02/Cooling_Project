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
m_dot_vent_max = 0.4
delta_p_vent = 100    # [Pa] Systemwiderstand
eta_vent     = 0.60   # [-]  Ventilatorwirkungsgrad
rho_air      = 1.2    # [kg/m³] Luftdichte Raumtemperatur
W_vent = m_dot_vent_max * delta_p_vent / (rho_air * eta_vent) / 1000  # [kW] Maximal-Ventilatorleistung

#load_results = pd.read_csv("results.csv")

path = os.path.join(os.path.dirname(__file__), "Results", f"simulation_{season}_{T_AC}C_{m_dot_vent_max}kgs_results.csv")
if os.path.exists(path):
    df = pd.read_csv(path)
    ac_on      = df["ac_on"].values
    vent_on    = df["vent_on"].values
    ac_power   = df["Q_AC_kW"].values
    time       = df["time"].values

#---------Compressor----------
c_d= 0.03 # m, Durchmesser zylinder [0.03,0.04, 0.05]

#refrigerant
delta_T_sh=10. #K #superheating
delta_T_sc=5. #K #subcooling
fluid="R1234yf" # {Propane, R1234yf, Dimethyl ether}
Eh="CBar"

#source
fluid_so="air"

#sink
fluid_si="air"

#heat exchanger
min_pinch= 10 #K

# ── COP-Sweep ─────────────────────────────────────────────────────────────────
refrigerants            = ["R290", "R1234yf", "DME"]   # Projektanforderungen
compressor_diameters_mm = [30., 40., 50.]   # Bohrungsdurchmesser [mm]

# Saisonale Design-Punkte: T_amb beeinflusst Wärmesenken-Temperatur (Kühlturm)
design_points = [
    {"season": "winter", "T_amb":  5., "T_room": 15.},
    {"season": "spring", "T_amb": 12., "T_room": 15.},
    {"season": "summer", "T_amb": 25., "T_room": 15.},
    {"season": "fall",   "T_amb": 12., "T_room": 15.},
]

