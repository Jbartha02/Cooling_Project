"""
Zentralisierte Konfiguration — alle Parameter an einem Ort.
"""
import sys, os
_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np
import Fluid_CP_moist_air as Fmoist

# ── Kältemittelkreislauf ───────────────────────────────────────────────────────
T_AC           = 5.0    # °C  — Verdampfer-Ausblastemperatur
delta_T_sh     = 5.0    # K   — Überhitzung
delta_T_sc     = 5.0    # K   — Unterkühlung
min_pinch_ev   =  5.0  # K   — Mindest-Pinch Verdampfer
min_pinch_co   = 10.0  # K   — Mindest-Pinch Kondensator
min_pressure_ratio = 2.0

# ── Kompressor ─────────────────────────────────────────────────────────────────
refrigerants            = ["R290", "R1234yf", "DME"]
compressor_diameters_mm = [30., 40., 50.]
Eh                      = "CBar"
fluid_so                = "air"
fluid_si                = "air"

# ── Fan (Verdampferseite) ──────────────────────────────────────────────────────
m_dot_vent_max = 1.65   # 1.65 kg/s — 50×50 cm, v=5.5 m/s (1.056, 40x40 cm, v=5.5 m/s)
delta_p_fan    = 100.   # Pa   — Systemwiderstand
eta_fan        = 0.60   # —    — Ventilatorwirkungsgrad
rho_air        = 1.2    # kg/m³

# ── Raum ───────────────────────────────────────────────────────────────────────
V_air      = 3 * 6 * 10        # m³  (3 m × 6 m × 10 m)
T_room_set = 15.0               # °C  — Sollwert

# Asymmetrische Hysterese: früh einschalten, spät ausschalten.
# T_ON eng am Sollwert → Kompressor springt sofort an wenn Raum zu warm wird
#   → keine grossen Spikes nach oben am Mittag.
# T_OFF weit unter Sollwert → Kompressor kühlt den Raum tief runter bevor er stoppt
#   → maximale thermische Pufferkapazität für die nächste Lastspit ze.
# Kann Raum T_room < T_OFF nicht kühlen: kein Problem (T_overload_min greift),
#   Kompressor läuft einfach am Limit bis Last sinkt oder Ventilation übernimmt.
T_HYST_ON  = 1.0               # K   — Einschalt-Hysterese (enger)
T_HYST_OFF = 5.0               # K   — Ausschalt-Hysterese (weiter)
T_ON       = T_room_set + T_HYST_ON   # 16°C — Einschaltpunkt
T_OFF      = T_room_set - T_HYST_OFF  # 10°C — Ausschaltpunkt
phi_vent   = 0.6                # —   — relative Feuchte Aussenluft (Design)

# ── Thermostat-Mindestzeiten ───────────────────────────────────────────────────
t_min_runtime_s    =  5 * 60   # s — Mindest-Einschaltdauer
t_min_standstill_s = 10 * 60   # s — Mindest-Stillstandszeit

# ── Raumluft-Masse & Initialzustand ───────────────────────────────────────────
_T0   = T_room_set
_phi0 = 0.6
m_Air = V_air / Fmoist.state_moist(["T", "phi"], [_T0, _phi0])["v*"]   # kg

_X0 = Fmoist.state_moist(["T", "phi"], [_T0, _phi0])["X"]
mw0 = _X0 * m_Air
h_0 = Fmoist.state_moist(["T", "X"],  [_T0, _X0])["h*"]

X_AC_sat = Fmoist.state_moist(["T", "phi"], [T_AC, 1.0])["X"]

# ── Psychrometrische Linearisierung: h*(T,X) ≈ _CP_A·T + _H_A0 + X·(_L0 + _CP_W·T)
_h_a_5  = Fmoist.state_moist(["T", "X"], [5.0,  0.0])["h*"]
_h_a_20 = Fmoist.state_moist(["T", "X"], [20.0, 0.0])["h*"]
_CP_A   = (_h_a_20 - _h_a_5) / 15.0
_H_A0   = _h_a_5 - _CP_A * 5.0

_hw_5   = (Fmoist.state_moist(["T", "X"], [5.0,  0.002])["h*"] - _h_a_5)  / 0.002
_hw_20  = (Fmoist.state_moist(["T", "X"], [20.0, 0.002])["h*"] - _h_a_20) / 0.002
_CP_W   = (_hw_20 - _hw_5) / 15.0
_L0     = _hw_5 - _CP_W * 5.0

# ── Performance-Map-Grid ───────────────────────────────────────────────────────
T_amb_grid  = np.linspace(1.,  35., 9)    # [1, 5, 9, 13, 17, 21, 25, 29, 33, 35]°C
T_room_grid = np.linspace(10., 30., 6)    # [10, 14, 18, 22, 26, 30]°C — deckt Thermostatband ab

# ── Saison-Gewichtung ──────────────────────────────────────────────────────────
SEASON_DAYS = {"winter": 91, "spring": 91, "summer": 91, "fall": 92}

season_col = {
    "summer": "Ambient_Temp_Summer_C",
    "spring": "Ambient_Temp_Spring_C",
    "fall":   "Ambient_Temp_Fall_C",
    "winter": "Ambient_Temp_Winter_C",
}

# ── Energiekosten & Temperaturgrenzen ─────────────────────────────────────────
ELECTRICITY_PRICE_CHF_KWH = 0.25   # CHF/kWh
T_ROOM_MIN = T_OFF   # 10°C
T_ROOM_MAX = T_ON    # 20°C

# Overload-Auslösung: Unterschreitet T_room diesen Wert, ist es kein Overload
# wenn Q_max < q_server — der Kompressor kühlt einfach so viel er kann.
# Erst oberhalb dieser Grenze zählt ein Leistungsdefizit als Overload.
T_overload_min = 16.0  # °C

# ── Auto-Tag aus Config-Werten ─────────────────────────────────────────────────
TAG = (
    f"{int(T_AC)}C"
    f"_sh{int(delta_T_sh)}"
    f"_pev{int(min_pinch_ev)}"
    f"_pco{int(min_pinch_co)}"
    f"_fan{round(m_dot_vent_max * 100)}"
)

# ── Dateipfade ─────────────────────────────────────────────────────────────────
_HERE    = os.path.dirname(os.path.abspath(__file__))
CSV_5MIN = os.path.join(_HERE, '..', 'daily_profiles_5min.csv')
MAP_DIR  = os.path.join(_HERE, 'maps')
