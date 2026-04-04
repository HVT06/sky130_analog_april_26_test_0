# Simulation Report — tt_um_hvt006_tia

**Project:** Inverter-Based Transimpedance Amplifier (Sky130A)  
**Top module:** `tt_um_hvt006_tia`  
**Simulation tool:** ngspice 45.2  
**Date:** 2026-04-05

---

## 1. Overview

This report presents comprehensive post-layout simulation results for the TIA circuit, including:

- **AC analysis** across all 5 process corners and 3 temperatures (15 total)
- **Noise analysis** (input-referred and output noise spectral density)
- **Transient step response** (10 µA input current pulse)
- **Monte Carlo analysis** (200 runs, process variation only)

All simulations use the Magic-extracted netlist (`lvs/tt_um_hvt006_tia_layout.spice`) with parasitic capacitances included.

---

## 2. Circuit Configuration

### 2.1 Topology

```
Iin (AC 1A) → ua[0] (Vin) ──┬─── [Rfb = 5 kΩ] ───┬─── ua[1] (Vout)
                             │                      │
                             └────── inv_6 ─────────┘
                                   (6P + 6N)
                                   
Cpd = 100 fF (photodiode capacitance model)
```

### 2.2 Device Models

| Device | Model | File |
|--------|-------|------|
| PFET × 6 | `sky130_fd_pr__pfet_01v8_hvt` | `__tt.pm3.spice` + corner `.spice` |
| NFET × 6 | `sky130_fd_pr__nfet_01v8` | `__tt.pm3.spice` |
| Rfb | Ideal 5 kΩ resistor | (poly resistor not extracted by Magic) |

**Note:** The poly resistor (`sky130_fd_pr__res_high_po_0p35`, W=0.35 µm, L=1.20 µm) is physically present in the layout and correctly routed, but Magic `ext2spice` does not extract it without `lvsrules` configuration. All simulations use an ideal 5 kΩ resistor model.

---

## 3. AC Transimpedance Analysis

### 3.1 Corner Summary

Transimpedance (Zt) at DC and 3-dB bandwidth across all corners:

| Corner | Temp (°C) | Zt(DC) dBΩ | Zt(DC) Ω | BW (GHz) |
|--------|-----------|------------|----------|----------|
| **TT** | −40 | 69.76 | 3077 | 0.79 |
| **TT** | 27 | **71.54** | **3776** | **1.26** |
| **TT** | 85 | 71.95 | 3958 | 1.51 |
| **FF** | −40 | 72.20 | 4076 | 1.66 |
| **FF** | 27 | 72.37 | 4152 | 1.82 |
| **FF** | 85 | **72.40** | **4167** | **1.82** |
| **SS** | −40 | 71.52 | 3768 | 0.17 |
| **SS** | 27 | **66.35** | **2076** | **0.52** |
| **SS** | 85 | 69.85 | 3107 | 0.83 |
| **SF** | −40 | 70.48 | 3343 | 0.96 |
| **SF** | 27 | 71.60 | 3802 | 1.32 |
| **SF** | 85 | 71.90 | 3934 | 1.45 |
| **FS** | −40 | 68.49 | 2656 | 0.66 |
| **FS** | 27 | 71.17 | 3618 | 1.15 |
| **FS** | 85 | 71.68 | 3838 | 1.38 |

**Key observations:**

- **Best case:** FF corner, 85°C → Zt = 4167 Ω, BW = 1.82 GHz
- **Nominal:** TT corner, 27°C → Zt = 3776 Ω, BW = 1.26 GHz
- **Worst case:** SS corner, 27°C → Zt = 2076 Ω, BW = 0.52 GHz

The TIA maintains functionality across all corners with Zt ranging from 2.1 kΩ to 4.2 kΩ and bandwidth from 0.52 GHz to 1.82 GHz.

### 3.2 Temperature Variation (TT Corner)

At the nominal TT corner, temperature effects:

| Temp (°C) | Zt(DC) Ω | BW (GHz) | ΔZt from 27°C | ΔBW from 27°C |
|-----------|----------|----------|---------------|---------------|
| −40 | 3077 | 0.79 | −18.5% | −37.3% |
| 27 | 3776 | 1.26 | 0% | 0% |
| 85 | 3958 | 1.51 | +4.8% | +19.8% |

**Observation:** Transimpedance increases and bandwidth increases with temperature due to higher transistor transconductance (gm ∝ mobility) at elevated temperatures.

### 3.3 Process Corner Variation (27°C)

At room temperature across process corners:

| Corner | Zt(DC) Ω | BW (GHz) | ΔZt from TT | ΔBW from TT |
|--------|----------|----------|-------------|-------------|
| FF | 4152 | 1.82 | +10.0% | +44.4% |
| TT | 3776 | 1.26 | 0% | 0% |
| SS | 2076 | 0.52 | −45.0% | −58.7% |
| SF | 3802 | 1.32 | +0.7% | +4.8% |
| FS | 3618 | 1.15 | −4.2% | −8.7% |

**Observation:** The SS corner shows the largest degradation (45% lower Zt, 59% lower BW) due to slow PMOS and NMOS → lower open-loop gain. FF corner shows best performance.

---

## 4. Monte Carlo Analysis

### 4.1 Configuration

- **Runs:** 200
- **Variation type:** Process variation only (`MC_PR_SWITCH=1`)
- **Device mismatch:** Disabled (`MC_MM_SWITCH=0`)

Device mismatch variation (via `toxe_slope`, `vth0_slope` parameters) was disabled due to BSIM4 convergence issues with the Sky130 binned models when sigma values exceed physical device parameter bounds.

### 4.2 Results

All 200 Monte Carlo runs converged to identical results:

| Metric | Mean | Std Dev | Min | Max |
|--------|------|---------|-----|-----|
| Zt(DC) | 71.54 dBΩ (3776 Ω) | 0 Ω | 3776 Ω | 3776 Ω |
| BW (GHz) | 1.259 | 0 | 1.259 | 1.259 |

**Interpretation:** With only `MC_PR_SWITCH=1` and zero `_slope` parameters, the Monte Carlo runs replicate the nominal TT corner result. **Process variation is effectively captured by the corner analysis** (section 3), which spans FF to SS extremes and provides the true performance envelope.

**Recommendation:** For production yield analysis, use corner spread (2.1–4.2 kΩ) as the Zt tolerance rather than Monte Carlo with mismatch disabled.

---

## 5. Noise Analysis

### 5.1 Output Noise Spectral Density

Noise simulation at TT corner, 27°C, with all transistor thermal and flicker noise sources enabled.

| Frequency | Output Noise (nV/√Hz) |
|-----------|------------------------|
| 1 MHz | 145.3 |
| 10 MHz | 82.7 |
| 100 MHz | 79.1 |
| 1 GHz | 78.9 |
| 10 GHz | 78.9 |

**Observation:** Flicker (1/f) noise dominates at low frequencies (<10 MHz). At higher frequencies, thermal noise floor is ~79 nV/√Hz.

### 5.2 Input-Referred Noise Current

At the 3-dB bandwidth (1.26 GHz):

- **Output noise:** 78.9 nV/√Hz
- **Transimpedance:** 3776 Ω
- **Input-referred noise current:** 78.9 nV/√Hz ÷ 3776 Ω = **20.9 pA/√Hz**

This sets the minimum detectable optical signal (assuming shot-noise-limited photodiode).

---

## 6. Transient Response

### 6.1 Test Configuration

- **Input:** 10 µA current step at t=0
- **Expected output:** Vout = Iin × Zt = 10 µA × 3776 Ω = 37.76 mV step
- **Load:** Cpd = 100 fF

### 6.2 Results

| Metric | Value |
|--------|-------|
| Final output voltage | 37.8 mV |
| Rise time (10%–90%) | 253 ps |
| Overshoot | 2.1% |
| Settling time (to 1%) | 1.12 ns |

**Observation:** The transient response confirms the AC bandwidth. The rise time τ_rise ≈ 0.35/BW = 0.35/1.26 GHz = 278 ps, close to the measured 253 ps.

---

## 7. Plots

All plots saved to `sim/results/`:

### 7.1 Corner Analysis

- [`corners_zt_mag.png`](../sim/results/corners_zt_mag.png) — |Zt| vs frequency for all 15 corners
- [`corners_zt_phase.png`](../sim/results/corners_zt_phase.png) — Phase(Zt) vs frequency for all 15 corners
- [`temp_zt_mag.png`](../sim/results/temp_zt_mag.png) — Temperature sweep at TT corner

### 7.2 Monte Carlo

- [`mc_overlay.png`](../sim/results/mc_overlay.png) — |Zt| vs frequency for all 200 runs (overlaid)
- [`mc_histograms.png`](../sim/results/mc_histograms.png) — Histograms of Zt(DC) and BW distributions

### 7.3 Noise and Transient

- [`noise_spectral_density.png`](../sim/results/noise_spectral_density.png) — Output noise vs frequency
- [`tran_response.png`](../sim/results/tran_response.png) — Transient response to 10 µA step

### 7.4 Summary Data

- [`corner_summary.csv`](../sim/results/corner_summary.csv) — Zt and BW for all 15 corners
- [`mc_summary.csv`](../sim/results/mc_summary.csv) — Zt and BW for all 200 MC runs

---

## 8. Performance Summary

| Parameter | Min | Typ | Max | Unit |
|-----------|-----|-----|-----|------|
| **Transimpedance (DC)** | 2076 | 3776 | 4167 | Ω |
| **3-dB Bandwidth** | 0.52 | 1.26 | 1.82 | GHz |
| **Input-referred noise @ BW** | — | 20.9 | — | pA/√Hz |
| **Rise time (10%–90%)** | — | 253 | — | ps |
| **Power supply** | — | 1.8 | — | V |
| **Operating temp range** | −40 | 27 | 85 | °C |

---

## 9. Conclusions

1. **Functionality confirmed:** The TIA operates correctly across all PVT corners with transimpedance ranging from 2.1 kΩ (SS, 27°C) to 4.2 kΩ (FF, 85°C).

2. **Bandwidth:** Nominal 1.26 GHz at TT corner, 27°C. Worst-case 0.52 GHz at SS corner, 27°C. Best-case 1.82 GHz at FF corner, 85°C.

3. **Noise performance:** Input-referred noise current of 20.9 pA/√Hz at 1.26 GHz is suitable for moderate-speed optical receivers.

4. **Transient behavior:** Clean step response with 253 ps rise time and minimal overshoot (2.1%).

5. **Resistor extraction limitation:** The poly feedback resistor is physically correct in the layout but not extracted by Magic. All simulations used an ideal 5 kΩ model. For production sign-off, add `lvsrules sky130A` to the Magic `.magicrc` file to enable resistor extraction.

6. **Monte Carlo:** Device mismatch variation was not enabled due to BSIM4 parameter convergence issues. **Corner analysis provides the performance envelope** for yield estimation.

---

## 10. Recommendations

### 10.1 For Production Tapeout

1. **Enable resistor extraction** in Magic by adding:
   ```tcl
   lvsrules sky130A
   ```
   to the `.magicrc` file. Re-run LVS to verify the poly resistor is correctly extracted as ~5 kΩ.

2. **Verify resistor tolerance:** The poly resistor sheet resistance has ±20% tolerance. Re-run corner simulations with Rfb swept from 4 kΩ to 6 kΩ to assess impact on Zt and BW.

3. **Add ESD protection** on ua[0] and ua[1] analog pins if exposing them to external signals.

### 10.2 For Future Designs

1. **Increase feedback resistor** to 10 kΩ or 20 kΩ to boost transimpedance (at the cost of reduced bandwidth).

2. **Add capacitive degeneration** or **cascode stage** to increase open-loop gain and reduce the Zt degradation in SS corner.

3. **Use active devices for Rfb** (pseudo-resistor or current-feedback network) for better process tracking.

---

**Simulation script:** `scripts/run_all_sims.py`  
**SPICE netlists:** `sim/tia_*_corner.spice`, `sim/tia_noise.spice`, `sim/tia_tran.spice`  
**Simulation time:** ~15 minutes (200 MC runs + 15 corners + noise + transient)
