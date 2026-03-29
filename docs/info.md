<!---

This file is used to generate your project datasheet. Please fill in the information below and delete any unused
sections.

You can also include images in this folder and reference them in the markdown. Each image must be less than
512 kb in size, and the combined size of all images must be less than 1 MB.
-->

## How it works

This project implements a **common-source NMOS amplifier** on the Sky130A PDK.

**Circuit:**
- **NMOS transistor:** W = 2 µm, L = 150 nm (sky130 1.8V nfet)
- **Input:** Gate connected to analog pin `ua[0]`
- **Output:** Drain connected to analog pin `ua[1]`
- **Source:** Connected to VGND (ground rail)
- **Power:** VDPWR (1.8V) for biasing and external load

The common-source configuration provides voltage amplification. An external drain resistor (connected between `ua[1]` and VDPWR via the PCB) sets the gain:

- **Voltage gain:** A_v ≈ −g_m × R_D
- **g_m** depends on bias current: g_m = 2·I_D / (V_GS − V_th)
- Typical V_th ≈ 0.4V for sky130 nfet

For example, with R_D = 10 kΩ and I_D = 100 µA, gain ≈ −14 V/V.

## How to test

1. Connect an external load resistor (e.g., 10 kΩ) between `ua[1]` (drain) and VDPWR (1.8V).
2. Apply a DC bias voltage to `ua[0]` (gate) — start with ~0.6V to turn on the NMOS.
3. Superimpose a small AC signal (e.g., 10 mV amplitude) on the gate bias.
4. Measure the amplified, inverted AC signal at `ua[1]` (drain).
5. All digital outputs are tied to ground (unused).

**Expected behavior:**
- Below threshold (~0.4V on gate): transistor off, drain at VDPWR
- Above threshold: drain voltage drops as current flows through R_D
- Small-signal gain depends on bias point and R_D value

## External hardware

- **Load resistor:** 1 kΩ to 100 kΩ between ua[1] and VDPWR (sets gain and operating point)
- **Signal generator:** For AC input on ua[0]
- **Oscilloscope:** To measure output on ua[1]
- **DC supply or bias tee:** To set gate DC operating point on ua[0]
