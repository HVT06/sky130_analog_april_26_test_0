# Inverter-Based Transimpedance Amplifier (TIA) -- Sky130A

## Project Summary

| Parameter          | Value                                  |
|--------------------|----------------------------------------|
| Technology         | Sky130A (SkyWater / open_pdks)         |
| Topology           | Self-biased CMOS inverter + Rf         |
| Supply voltage     | 1.8 V                                  |
| DC transimpedance  | 3551 Ohm (71 dBOhm)                    |
| -3 dB bandwidth    | ~1.05 GHz                              |
| Bias point         | Vin = Vout = 0.854 V                   |
| Input              | ua[0] -- Iin  (photodiode current)     |
| Output             | ua[1] -- Vout (transimpedance voltage) |
| Tile               | 1x2 (161 um x 225.76 um)               |
| Top module         | tt_um_hvt006_tia                       |

---

## How It Works

The TIA converts a small input current (e.g. from a photodiode) into a
proportional output voltage.  The core circuit is a **self-biased CMOS inverter**
(NMOS M1 in series with PMOS M2) with a **feedback resistor Rf** connecting output
to input.

```
             VDD (1.8 V)
               |
              [M2 PMOS W=4u L=150n]
               |
Iin --> [Vin]--+--[Vout] --> ua[1]
  ua[0]  |     |
         |    [M1 NMOS W=2u L=150n]
         |     |
         |    GND
         |
         +----[Rfb = 5 kOhm]----+
                                 (= Vout)
```

The feedback establishes the DC bias point.  When Iin = 0 the inverter sits at
its trip point (Vin = Vout = 0.854 V) where the small-signal voltage gain
A = -gm*(ron||rop) is maximised.

The transimpedance (output voltage per unit input current) is:

    Zt(s) = -Rf * A(s) / (1 + A(s))    [low frequency]
           ~ -Rf                        [when |A| >> 1]

At low frequency |A| ~ 10-15 for this sizing, giving:

    Zt(DC) ~ -Rf * A / (1 + A) ~ -3500 Ohm

The -3 dB bandwidth is set by the dominant pole at the input node:

    f_-3dB ~ 1 / (2*pi * Rfb * (Cin * (1 + |A|) + Cout))
           ~ 1.05 GHz  (for Cin = Cpd = 100 fF)

---

## Pinout

### Analog Pins (enabled in info.yaml: analog_pins = 2)

| Pin   | Signal | Direction | Description                              |
|-------|--------|-----------|------------------------------------------|
| ua[0] | Iin    | Input     | Photodiode / AC current source input     |
| ua[1] | Vout   | Output    | Transimpedance voltage output            |

### Digital Pins (all tied LOW -- pure analog design)

| Pin          | State | Note                                    |
|--------------|-------|-----------------------------------------|
| ui_in[7:0]   | N/C   | Unused                                  |
| uo_out[7:0]  | 0     | Tied to GND in Verilog wrapper          |
| uio_*        | 0     | Tied to GND in Verilog wrapper          |

---

## How to Test

### DC Bias Verification

Apply VDD = 1.8 V, leave Iin = 0.  Measure:
- Vout should settle to ~0.85 V (self-biased)
- Supply current ~0.13 mA (Idd)

### Transimpedance Measurement

Inject a small AC current Iin at ua[0] (e.g. via a large resistor from a
signal generator, R_src >= 100 kOhm so it looks like a current source).
Measure Vout at ua[1] with an oscilloscope or VNA.

    Zt = Vout / Iin  [Ohm]

Expected: Zt ~ 3500 Ohm at 1 MHz, -3 dB at ~1 GHz.

### Photodiode Interface

Connect a reverse-biased photodiode between ua[0] and a suitable bias node.
Illumination generates Iin which drives Vout.  For a 10 uA photocurrent step
the output swing is ~35 mV.

---

## External Hardware

| Component     | Value / Type       | Purpose                               |
|---------------|--------------------|---------------------------------------|
| Photodiode    | Si PIN or APD      | Light-to-current transducer at ua[0]  |
| Bias resistor | 100 kOhm (opt.)    | AC current injection for test         |
| Decoupling    | 100 nF on VDD pin  | Supply bypassing                      |
| Load          | 50 Ohm (opt.)      | 50-Ohm measurement port at ua[1]      |

---

## Design Files

| File                     | Description                          |
|--------------------------|--------------------------------------|
| sim/tia_dc.spice         | DC operating point + transfer curve  |
| sim/tia_ac.spice         | AC frequency response (Zt vs f)      |
| sim/tia_tran.spice       | Transient step response              |
| sim/tia_noise.spice      | Input-referred noise PSD             |
| sim/results/             | Simulation output TSV and raw files  |
| gds/tt_um_hvt006_tia.gds | Layout (GDS-II format)               |
| lef/tt_um_hvt006_tia.lef | Abstract (LEF format)                |
| docs/tia_design.md       | Design equations and analysis        |
| docs/tia_report.md       | Simulation results report            |
