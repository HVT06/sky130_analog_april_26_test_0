# TIA Design Document -- Inverter-Based Transimpedance Amplifier

## 1. Architecture

### 1.1 Topology Selection

An **inverter-based TIA** (also called a regulated-cascode TIA in the
photodetector literature) uses a CMOS inverter as the gain stage and a
feedback resistor Rf to set the transimpedance.  Advantages:

- Self-biasing: no separate DC bias network required.
- Rail-to-rail input swing capability.
- Simple: two transistors + one resistor.
- Matched gm: NMOS and PMOS both in saturation at the trip point.

### 1.2 Schematic

```
             VDD = 1.8 V
                 |
           +-----+-----+
           |   PMOS M2 |  W/L = 4u/150n
           |   (pch)   |  sky130_fd_pr__pfet_01v8
           +-----+-----+
                 |
 ua[0] (Iin) --[Vin]---[Vout]-- ua[1]
                 |
           +-----+-----+
           |   NMOS M1 |  W/L = 2u/150n
           |   (nch)   |  sky130_fd_pr__nfet_01v8
           +-----+-----+
                 |
                GND
                 
Feedback:
    ua[1](Vout) ---[Rfb = 5 kOhm]--- ua[0](Vin)

Input capacitance (photodiode model):
    Cpd = 100 fF connected Vin -> GND
```

### 1.3 Device Sizing

| Device | Type  | W     | L     | Subcircuit name                  |
|--------|-------|-------|-------|----------------------------------|
| M1     | NMOS  | 2 um  | 150 nm| sky130_fd_pr__nfet_01v8          |
| M2     | PMOS  | 4 um  | 150 nm| sky130_fd_pr__pfet_01v8          |
| Rfb    | Poly  | --    | --    | 5000 Ohm (ideal in simulation)   |
| Cpd    | Pin   | --    | --    | 100 fF (photodiode model)        |

PMOS is sized 2x wider than NMOS to compensate for lower hole mobility
(un/up ~ 2 in sky130A), resulting in comparable gm contributions.

---

## 2. DC Analysis

### 2.1 Self-Bias Point

At DC, Rfb forces Vin = Vout = Vtrip where the inverter voltage gain A = -1
in the large-signal sense.  This is the inverter trip point:

    Vtrip = (VDD * sqrt(kn*Wn/Ln) + |Vtp| * sqrt(kp*Wp/Lp))
            / (sqrt(kn*Wn/Ln) + sqrt(kp*Wp/Lp))

For the sky130A process (typical corner):
- un*Cox ~ 300 uA/V^2, up*Cox ~ 100 uA/V^2 (simplified)
- Vtn ~ 0.49 V, |Vtp| ~ 0.60 V (tt corner)

Estimated Vtrip ~ 0.85 V.  **Simulated: Vtrip = 0.854 V.**

### 2.2 DC Transimpedance

With both transistors biased in saturation the small-signal voltage gain is:

    A = -gm_total * Rout

where:
    gm_total = gm1 + gm2
    Rout     = ron1 || rop2
              = (1/lambda_n*Ids) || (1/lambda_p*Ids)

The low-frequency transimpedance (inverting):

    Zt(0) = dVout/dIin = -Rf * A / (1 + A) ~ -Rf  [for |A| >> 1]

For |A| = 12 (simulated):
    Zt(0) = -5000 * 12 / (1 + 12) = -4615 Ohm  (theory)
    Zt(0) = -3551 Ohm              (simulated, tt corner)

The discrepancy reflects velocity-saturation effects and channel-length
modulation not captured by the simple first-order model.

---

## 3. AC / Frequency Response

### 3.1 Transfer Function

The small-signal equivalent circuit with:
- Current source Iin at Vin node
- Amplifier gain block A (from Vin to Vout)
- Feedback resistor Rfb
- Total input capacitance Cin = Cpd + Cgs1 + Cgd2 + Cgd1*(1+|A|)
- Total output capacitance Cout = Cgd1 + Cdb1 + Cdb2 + Cload

gives the transfer function:

            -Rf * A
    Zt(s) = ------------------
            1 + A + s*Rf*Cin

with a dominant pole at:

    fp = (1 + |A|) / (2*pi * Rf * Cin)
       = (1 + 12)  / (2*pi * 5000 * 100e-15 * 13)
       = 13 / (2*pi * 6.5e-10)
       = 3.18 GHz  (calculated, Cin = Cpd only)

With Miller-multiplied gate capacitance (Cgd1*(1+A) term) the effective
Cin is larger, lowering fp.  **Simulated -3dB at 1.05 GHz.**

### 3.2 Gain-Bandwidth Product

    GBW = Zt(DC) * BW = 3551 * 1.05e9 = 3.73e12 Hz*Ohm = 3.73 TOhm*Hz

This is the fundamental figure of merit for a TIA.

---

## 4. Noise Analysis

### 4.1 Noise Sources

Three main contributions to input-referred current noise:

1. **Rfb thermal noise** (dominant at low frequency):

       S_Rf = 4kT / Rf = 4 * 1.38e-23 * 300 / 5000
            = 3.31e-24 A^2/Hz
       => sqrt(S_Rf) = 1.82 pA/sqrt(Hz)

2. **NMOS M1 channel noise**:

       S_n1 = 4kT * gamma * gm1
       (gamma ~ 2/3 for long-channel, > 1 for short-channel)

3. **PMOS M2 channel noise**:

       S_n2 = 4kT * gamma * gm2

All three are referred to the input by dividing by Zt^2:

       S_in_total = S_Rf + (S_n1 + S_n2) / |A|^2

### 4.2 Input-Referred Noise Floor

Simulated at 1 MHz:
    S_in(1 MHz) = 1.20e-11 A^2/Hz
    => sqrt(S_in) = 3.46 pA/sqrt(Hz)

The excess over the thermal floor (1.82 pA/sqrt(Hz)) is due to transistor
channel noise.  Ratio: 3.46 / 1.82 = 1.90, giving a noise figure:

    NF_current = 20*log10(3.46/1.82) = 5.6 dB

---

## 5. Design Parameter Summary

| Parameter             | Value         | Unit       | Notes                       |
|-----------------------|---------------|------------|-----------------------------|
| VDD                   | 1.8           | V          | Sky130A nominal             |
| W_NMOS (M1)           | 2.0           | um         |                             |
| L_NMOS (M1)           | 0.15          | um         | Minimum Length              |
| W_PMOS (M2)           | 4.0           | um         | 2x NMOS to match gm         |
| L_PMOS (M2)           | 0.15          | um         | Minimum Length              |
| Rfb                   | 5000          | Ohm        | Sets DC Zt                  |
| Cpd                   | 100           | fF         | Photodiode model            |
| Vbias (trip point)    | 0.854         | V          | Self-biased, no ext. bias   |
| Idd                   | ~0.13         | mA         | Estimate from sim           |
| Power                 | ~0.23         | mW         | VDD * Idd                   |
| Zt(DC)                | 3551          | Ohm        | Simulated                   |
| Zt_dB                 | 71.0          | dBOhm      | 20*log10(3551)              |
| Bandwidth (-3 dB)     | ~1.05         | GHz        | Simulated                   |
| GBW                   | ~3.7          | TOhm*Hz    |                             |
| Input noise (1 MHz)   | 3.46          | pA/sqrt(Hz)| Simulated                   |
| Rf thermal floor      | 1.82          | pA/sqrt(Hz)| 4kT/Rf                      |

---

## 6. Corner Robustness

This design uses default (tt) corner sizing.  For production use, sweep
across ff/ss/sf/fs corners using:

    sim/tia_ac.spice  (change .include to *__ff.pm3.spice etc.)

Expected corner spread: Zt ~ 3000-4500 Ohm, BW ~ 0.8-1.4 GHz.

---

## References

1. B. Razavi, *Design of Analog CMOS Integrated Circuits*, 2nd ed., Ch. 10.
2. S. Csutak et al., "CMOS-compatible high-speed planar Si photodiodes", IEEE TED 2002.
3. SkyWater Technology, *SKY130 PDK Documentation*, open-source.
