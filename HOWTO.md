# How to Run & Test Different Parameters

All simulation code lives in the `clean_code/` subfolder.
Open `clean_code/config.py` and `clean_code/main.py` to configure and run.

---

## Step 1 — Adjust parameters (`clean_code/config.py`)

### Refrigeration cycle

```python
T_AC         = 5.0   # °C — evaporator outlet temperature (supply air to room)
delta_T_sh   = 5.0   # K  — superheat
min_pinch_ev = 5.0   # K  — minimum pinch evaporator
min_pinch_co = 10.0  # K  — minimum pinch condenser
```

### Fan (evaporator side)

```python
m_dot_vent_max = 1.65   # kg/s — max mass flow rate
                         # 50×50 cm at 5.5 m/s → 1.65 kg/s
                         # 40×40 cm at 5.5 m/s → 1.056 kg/s
                         # Formula: A [m²] × v [m/s] × 1.2 [kg/m³]
delta_p_fan = 100.       # Pa  — system pressure drop
eta_fan     = 0.60       # —   — fan efficiency
```

### Room & thermostat

```python
V_air      = 3 * 6 * 10  # m³ — room volume (height × width × length)
T_room_set = 15.0         # °C — temperature setpoint

T_HYST_ON  = 1.0          # K  — compressor ON  when T > setpoint + T_HYST_ON
T_HYST_OFF = 5.0          # K  — compressor OFF when T < setpoint - T_HYST_OFF

t_min_runtime_s    = 5  * 60  # s — minimum compressor on-time
t_min_standstill_s = 10 * 60  # s — minimum compressor off-time
```

### Refrigerants & compressor diameters to sweep

```python
refrigerants            = ["R290", "R1234yf", "DME"]  # remove any to skip
compressor_diameters_mm = [30., 40., 50.]              # piston diameters [mm]
```

---

## Step 2 — Choose what to run (`clean_code/main.py`)

```python
TESTS = [
    {
        "run":       True,
        "build_map": False,  # True  = rebuild performance map (~2 min)
                             # False = load existing map from disk
        "sweep":     True,   # True  = run simulation for all combos
                             # False = skip, use existing CSVs
        "plots":     True,   # True  = generate plots for top results
        "top":       3,      # number of top PASS candidates to plot
    },
]
```

Then run `clean_code/main.py` (F5 in VS Code).

The output folder name is generated automatically from your config values, e.g.:
`clean_code/results_5C_sh5_pev5_pco10_fan165/`

### When do I need `build_map: True`?

| Parameter changed                          | build_map needed? |
|--------------------------------------------|-------------------|
| `T_AC`, `delta_T_sh`, `min_pinch_ev/co`   | **YES**           |
| `m_dot_vent_max` (fan size)                | **YES**           |
| `T_room_set`, hysteresis, room size        | No                |
| `t_min_runtime_s`, `t_min_standstill_s`   | No                |

---

## Typical workflows

### A) Test a new fan size (e.g. 40×40 cm)
1. `config.py`: `m_dot_vent_max = 1.056`
2. `main.py`: `build_map: True, sweep: True, plots: True`
3. Run → new map + results saved under `results_..._fan106/`

### B) Re-plot existing results without re-simulating
1. `main.py`: `build_map: False, sweep: False, plots: True`
2. Run → only plots are regenerated

### C) Change only room/thermostat parameters
1. `config.py`: change e.g. `T_room_set` or `T_HYST_ON`
2. `main.py`: `build_map: False, sweep: True, plots: True`
3. Run → loads existing map, re-runs simulation only

### D) Compare two configurations
Run twice with different configs — each run saves to its own `results_<tag>/` folder.

---

## Output files

```
clean_code/
  maps/
    performance_maps_<tag>.pkl                        ← COP/Q lookup table
  results_<tag>/
    ranking_<tag>.csv                                 ← summary, sorted by SEER
    sim_<tag>_<refrigerant>_D<mm>_<season>.csv        ← time series per combo
    plots/
      <tag>_<refrigerant>_D<mm>_<season>.png          ← plots for top-N PASS
```

### Ranking columns

| Column               | Meaning                                           |
|----------------------|---------------------------------------------------|
| `SEER_year`          | Seasonal Energy Efficiency Ratio (higher = better)|
| `cost_CHF_year`      | Annual electricity cost [CHF]                     |
| `T_room_std_year`    | Std dev of room temperature [K] (lower = better)  |
| `n_cycles_year`      | Compressor start/stop cycles per year             |
| `n_fan_limited_year` | Timesteps where fan flow was the bottleneck       |
| `n_ac_overload_year` | Timesteps where cooling demand exceeded capacity  |
| `status`             | PASS / FAIL (overload) / FAIL (fan_limited)       |
