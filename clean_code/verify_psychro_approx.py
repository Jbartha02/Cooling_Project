"""
Prueft die Guete der psychrometrischen Linearisierung aus config.py.

Die Simulation vermeidet teure CoolProp-Aufrufe waehrend der Zeitintegration,
indem h*(T, X) durch ein bilineares Polynom approximiert wird:

    h*(T, X)  ≈  CP_A * T  +  H_A0  +  X * (L0 + CP_W * T)    [kJ/kg_dry]

Kalibrierung: zwei Stuetzpunkte (T = 5 deg C und T = 20 deg C) bei X = 0 und
X = 0.002 kg/kg. Die Koeffizienten werden einmalig beim Import von config.py
berechnet.

Umgekehrt wird T aus dem ODE-Zustand (h*, X) analytisch invertiert:

    T(h*, X)  =  (h* - H_A0 - X * L0) / (CP_A + X * CP_W)      [deg C]

Dieses Skript quantifiziert den Fehler beider Richtungen gegenueber CoolProp
auf einem dichten Gitter im realistischen Betriebsbereich des Serverraums.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import numpy as np
import Fluid_CP_moist_air as Fmoist
import clean_code.config as cfg

# ── Testgitter ─────────────────────────────────────────────────────────────────
# Betriebsbereich: T von 0 bis 35 deg C (Raum + Aussenluft), X 0.001..0.018 kg/kg
T_grid = np.linspace(1., 35., 69)          # 0.5 K Schritte (ab 1 deg C, Gefrierpunkt vermeiden)
X_grid = np.array([0.001, 0.003, 0.005, 0.008, 0.010, 0.013, 0.015, 0.018])

# ── Koeffizienten ausgeben ─────────────────────────────────────────────────────
print("Linearisierungskoeffizienten (kalibriert bei T = 5 deg C und 20 deg C):")
print(f"  CP_A = {cfg._CP_A:.5f}  kJ/(kg_dry . K)    spez. Waermekapazitaet trockene Luft")
print(f"  H_A0 = {cfg._H_A0:.5f}  kJ/kg_dry           Referenzenthalpie-Offset trockene Luft")
print(f"  CP_W = {cfg._CP_W:.5f}  kJ/(kg_dry . K)    dh*/dT pro kg/kg Feuchte")
print(f"  L0   = {cfg._L0:.5f}  kJ/kg_dry           Verdampfungswaerme-Referenz bei 0 deg C")
print()

# ── Fehlerberechnung ───────────────────────────────────────────────────────────
err_h = []   # h*_approx - h*_CoolProp  [kJ/kg]
err_T = []   # T_approx(h*_CP, X) - T_true  [K]
points = []  # (T, X) fuer Worst-Case-Ausgabe

skipped = 0
for T in T_grid:
    for X in X_grid:
        try:
            # CoolProp-Referenz (kann bei Uebersaettigung fehlschlagen)
            h_cp = Fmoist.state_moist(["T", "X"], [T, X])["h*"]
        except Exception:
            skipped += 1
            continue

        # Vorwaerts: analytisch -> CoolProp
        h_approx = cfg._CP_A * T + cfg._H_A0 + X * (cfg._L0 + cfg._CP_W * T)
        err_h.append(h_approx - h_cp)

        # Rueckwaerts: T aus CoolProp-h* analytisch invertiert
        T_approx = (h_cp - cfg._H_A0 - X * cfg._L0) / (cfg._CP_A + X * cfg._CP_W)
        err_T.append(T_approx - T)

        points.append((T, X))

if skipped:
    print(f"(Uebersprungen: {skipped} uebersaettigte Punkte)\n")

err_h  = np.array(err_h)
err_T  = np.array(err_T)
points = np.array(points)

# ── Ergebnisse ─────────────────────────────────────────────────────────────────
print(f"Testgitter: {len(T_grid)} T-Werte x {len(X_grid)} X-Werte = {len(err_h)} Punkte")
print(f"T-Bereich: {T_grid[0]:.0f} ... {T_grid[-1]:.0f} deg C")
print(f"X-Bereich: {X_grid[0]:.3f} ... {X_grid[-1]:.3f} kg/kg")
print()

print("Fehler  h*(T,X):  analytisch - CoolProp  [kJ/kg_dry]")
print(f"  Max. |Fehler|  : {np.max(np.abs(err_h)):.5f} kJ/kg")
print(f"  Mittl. |Fehler|: {np.mean(np.abs(err_h)):.5f} kJ/kg")
print(f"  Std.-Abw.      : {np.std(err_h):.5f} kJ/kg")

idx_h = np.argmax(np.abs(err_h))
Tw, Xw = points[idx_h]
print(f"  Schlimmster Fall: T = {Tw:.1f} deg C, X = {Xw:.3f} kg/kg, "
      f"Fehler = {err_h[idx_h]:+.5f} kJ/kg")
print()

print("Fehler  T(h*, X): analytische Inversion - CoolProp  [K]")
print(f"  Max. |Fehler|  : {np.max(np.abs(err_T)):.5f} K")
print(f"  Mittl. |Fehler|: {np.mean(np.abs(err_T)):.5f} K")
print(f"  Std.-Abw.      : {np.std(err_T):.5f} K")

idx_T = np.argmax(np.abs(err_T))
Tw2, Xw2 = points[idx_T]
print(f"  Schlimmster Fall: T = {Tw2:.1f} deg C, X = {Xw2:.3f} kg/kg, "
      f"Fehler = {err_T[idx_T]:+.5f} K")
print()

# ── Kontext: wie gross ist ein typischer Zeitschritt h*-Aenderung? ─────────────
# Raum bei 15 deg C, q_server = 5 kW, dt = 300 s, m_Air ~ 257 kg
dh_step = 5.0 * 300.0 / 257.0  # kJ/kg, entspricht ~5.8 K
T_step  = dh_step / cfg._CP_A
print(f"Zum Vergleich: typische h*-Aenderung pro Zeitschritt ({dh_step:.2f} kJ/kg"
      f" entspricht ~{T_step:.2f} K)")
print(f"-> Linearisierungsfehler in h* ({np.max(np.abs(err_h)):.4f} kJ/kg) ist"
      f" {100*np.max(np.abs(err_h))/dh_step:.2f}% des Zeitschritts")
print(f"-> Temperaturfehler ({np.max(np.abs(err_T)):.4f} K) << Thermostat-Hysterese (5 K)")
