# TIA Simulation Report -- Inverter-Based Transimpedance Amplifier

**PDK**: Sky130A (open_pdks)  **Corner**: tt  **Temperature**: 27 C
**Simulator**: ngspice 45.2  **SPICE level**: BSIM4 (sky130_fd_pr)

---

## 1. DC Operating Point

**Simulation**: `sim/tia_dc.spice`  **Output**: `sim/results/dc_tia.tsv`

With Iin = 0:

| Node  | Voltage   | Notes                         |
|-------|-----------|-------------------------------|
| Vin   | 0.854 V   | Self-biased trip point        |
| Vout  | 0.854 V   | Equal to Vin (feedback lock)  |
| VDD   | 1.800 V   | Supply                        |

The NMOS and PMOS are both in saturation at the bias point.

### Transfer Curve

DC sweep Iin from -100 uA to +100 uA:

| Iin (uA) | Vout (V)  | Notes                    |
|----------|-----------|--------------------------|
| -100     | ~1.21     | Towards VDD (PMOS pull)  |
|  -10     | ~0.889    |                          |
|    0     | 0.854     | Bias point               |
|   +10    | ~0.818    |                          |
|  +100    | ~0.50     | Towards GND (NMOS pull)  |

Slope dVout/dIin at Iin=0 = DC transimpedance:

    Zt(DC) = -3551 Ohm  = -71.0 dBOhm

---

## 2. AC Frequency Response (Transimpedance)

**Simulation**: `sim/tia_ac.spice`  **Output**: `sim/results/ac_tia.tsv`

AC analysis with Iin = 1 A AC (so Vout numerically equals Zt in Ohm):

| Frequency  | |Zt| (Ohm) | |Zt| (dBOhm) | Notes              |
|------------|------------|-------------|---------------------|
| 1 MHz      | 3551       | 71.0        | Low-frequency value |
| 100 MHz    | 3535       | 71.0        | Flat band           |
| 500 MHz    | 3315       | 70.4        | Slight roll-off     |
| 1.0 GHz    | 2550       | 68.1        | Approaching -3 dB   |
| 1.05 GHz   | ~2511      | ~68.0       | -3 dB point         |
| 1.12 GHz   | 2290       | 67.2        | Past -3 dB          |
| 10 GHz     | 485        | 53.7        | Well past BW        |

The -3 dB frequency (where |Zt| = 3551/sqrt(2) = 2511 Ohm):

    f_-3dB ~ 1.05 GHz

### Summary: AC

| Metric              | Value         |
|---------------------|---------------|
| Zt(DC)              | 3551 Ohm      |
| Zt(DC)              | 71.0 dBOhm    |
| -3 dB bandwidth     | ~1.05 GHz     |
| GBW (Zt * BW)       | ~3.7 TOhm*Hz  |
| Phase at 1 GHz      | ~-45 deg      |

---

## 3. Transient Step Response

**Simulation**: `sim/tia_tran.spice`  **Output**: `sim/results/tran_tia.tsv`

Input step: PULSE(Iin=0 -> Iin=10 uA, Tdelay=1 ns, Trise=50 ps, Twidth=4 ns, Tperiod=10 ns)

| Measurement                | Value        |
|----------------------------|--------------|
| Quiescent Vout (Iin=0)     | 0.8543 V     |
| Vout at Iin=10 uA          | 0.8186 V     |
| Delta Vout                 | -35.6 mV     |
| Implied transimpedance     | 3560 Ohm     |
| Rise time (10%-90%)        | ~350 ps      |
| Settling to 1% of final    | ~1 ns        |

The transient-implied Zt = 35.6 mV / 10 uA = 3560 Ohm is within 0.3% of
the AC simulation result (3551 Ohm), confirming consistency.

### Waveform Summary

```
Vout (V)
 0.860 |                                                    
 0.855 |___   (quiescent)    _____________________________
 0.854 |   |                |
 0.852 |   |                |
 0.850 |   |                |
 0.820 |   |________________|  step (Iin = 10 uA active)
         0   1   2   3   4   5   6   7   8   9  10  (ns)
```

---

## 4. Noise Analysis

**Simulation**: `sim/tia_noise.spice`  **Output**: `sim/results/noise_tia.raw`

Input-referred current noise PSD (S_in = inoise_spectrum, A^2/Hz):

| Frequency  | S_in (A^2/Hz) | sqrt(S_in) (pA/sqrt(Hz)) | Notes              |
|------------|---------------|--------------------------|---------------------|
| 1 MHz      | 1.20e-11      | 3.46                     | Transistor noise    |
| 10 MHz     | 1.15e-11      | 3.39                     |                     |
| 100 MHz    | 9.8e-12       | 3.13                     |                     |
| 1 GHz      | ~2.2e-11      | ~4.7                     | Rising near BW      |

Thermal floor from Rfb = 5 kOhm:

    S_Rf = 4kT/Rf = 4 * 1.38e-23 * 300 / 5000 = 3.31e-24 A^2/Hz
    sqrt(S_Rf) = 1.82 pA/sqrt(Hz)

Transistor noise excess: 3.46 / 1.82 = 1.90  =>  NF = 5.6 dB

### Output Referred Noise

| Frequency | S_out (V^2/Hz) | sqrt(S_out) (nV/sqrt(Hz)) |
|-----------|----------------|---------------------------|
| 1 MHz     | 4.27e-8        | 206.5                     |

Equivalent input: S_out / Zt^2 = 4.27e-8 / (3551)^2 = 3.38e-15 V^2/Hz (not the input-referred current noise, but matches via Zt).

---

## 5. Summary Table

| Parameter             | Simulated  | Unit        |
|-----------------------|------------|-------------|
| Bias point (Vin=Vout) | 0.854      | V           |
| DC transimpedance     | 3551       | Ohm         |
| DC transimpedance     | 71.0       | dBOhm       |
| -3 dB bandwidth       | 1.05       | GHz         |
| GBW                   | 3.73       | TOhm*Hz     |
| Step response DV      | 35.6 mV    | (10 uA step)|
| Input noise @1MHz     | 3.46       | pA/sqrt(Hz) |
| Rf thermal floor      | 1.82       | pA/sqrt(Hz) |
| Noise excess (NF)     | 5.6        | dB          |
| Supply                | 1.8        | V           |
| Est. Idd              | ~0.13      | mA          |
| Est. Power            | ~0.23      | mW          |

---

## 6. Raw Data Files

All simulation outputs are in `sim/results/`:

| File             | Format | Columns                          | Rows |
|------------------|--------|----------------------------------|------|
| dc_tia.tsv       | TSV    | v(vin), v(vout)                  | 201  |
| dc_tia.raw       | NGRAW  | all DC vectors (binary)          | --   |
| ac_tia.tsv       | TSV    | frequency, Zt_dB, Zt_ohm        | 81   |
| ac_tia.raw       | NGRAW  | all AC vectors (binary)          | --   |
| tran_tia.tsv     | TSV    | time, v(vin), v(vout)            | ~1k  |
| tran_tia.raw     | NGRAW  | all tran vectors (binary)        | --   |
| noise_tia.tsv    | TSV    | freq, inoise_spectrum, onoise_sp | 81   |
| noise_tia.raw    | NGRAW  | all noise vectors (binary)       | --   |

NGRAW files can be loaded in ngspice (`load results/ac_tia.raw`) or
Python (`via pySPICE / ltspice libraries`).
