# Ring-Oscillator PLL — Sky130A

## Project Summary

| Parameter          | Value                                           |
|--------------------|-------------------------------------------------|
| Technology         | Sky130A (SkyWater / open_pdks)                   |
| Topology           | Type-II charge-pump PLL with ring VCO            |
| Supply voltage     | 1.8 V                                            |
| Reference clock    | 100 MHz (on ua[0])                               |
| VCO range          | 50–500 MHz (5-stage current-starved ring)        |
| Lock frequency     | 400 MHz (N=4)                                    |
| Loop bandwidth     | ~7.2 MHz, ζ ≈ 0.9                                |
| Lock time          | < 500 ns                                         |
| Tile               | 1×2 (161 µm × 225.76 µm)                        |
| Top module         | tt_um_pll_sky130                                 |

---

## How it works

The PLL locks an on-chip 5-stage current-starved ring VCO to an external
reference clock.  The loop consists of:

1. **Phase-Frequency Detector (PFD)** — Two resettable D flip-flops
   (sky130_fd_sc_hd__dfrtp_1) with a NAND reset gate and a 3-inverter
   dead-zone delay chain.  Generates UP/DN pulses proportional to the
   phase error between ref_clk and div_clk.

2. **Charge Pump (CP)** — 10 µA matched current sources (PMOS pull-up,
   NMOS pull-down) switched by UP/DN signals.  Pumps current into or
   out of the loop filter.

3. **Loop Filter** — Second-order passive filter:
   - R = 4.7 kΩ (poly high-ohm resistor, xhrpoly)
   - C1 = 10 pF (NMOS gate MOSCAP)
   - C2 = 1 pF (NMOS gate MOSCAP)
   Provides a zero at 1/(R·C1) for phase margin (~52°).

4. **VCO** — 5-stage current-starved ring oscillator.  Each stage is a
   CMOS inverter with PMOS/NMOS current-limiting transistors controlled
   by Vctrl.  Kvco ≈ 1300 MHz/V.  Output buffered through a standard
   cell inverter chain.

5. **Frequency Divider** — Divide-by-4 using two toggle flip-flops
   (sky130_fd_sc_hd__dfxbp_1).  Feeds div_clk back to the PFD.

The control voltage (Vctrl) settles to ~1.016 V when locked, giving
VCO freq ≈ 401.6 MHz (target 400 MHz).

---

## Pinout

### Analog Pins (analog_pins = 2)

| Pin   | Signal   | Direction | Description                   |
|-------|----------|-----------|-------------------------------|
| ua[0] | ref_clk  | Input     | Reference clock input (100 MHz) |
| ua[1] | div_out  | Output    | Divided VCO output            |

### Digital Pins

| Pin         | Signal        | Description                    |
|-------------|---------------|--------------------------------|
| ui[7:0]     | div_N[7:0]    | Divider N ratio (default 4)    |
| uio[2:0]    | div_M[2:0]    | Divider M ratio                |
| uio[6:3]    | coarse_band   | VCO coarse tuning              |
| uio[7]      | pll_enable    | Enable PLL                     |
| uo[0]       | lock_detect   | Lock indicator output          |

---

## How to test

### Basic Lock Test

1. Apply VDD = 1.8 V.
2. Set pll_enable (uio[7]) = HIGH.
3. Set div_N = 4 (ui[7:0] = 0x04).
4. Apply a 100 MHz reference clock on ua[0].
5. Observe ua[1] — should output a 100 MHz divided clock (400 MHz / 4).
6. Check uo[0] lock_detect goes HIGH after ~500 ns.

### VCO Frequency Sweep

Vary the coarse_band bits (uio[6:3]) to shift the VCO frequency range.
With N=4 and 100 MHz ref, the PLL should lock at 400 MHz across bands.

### Divider Ratio Test

Change div_N to other values (e.g. 2, 8) and verify that the VCO
frequency tracks to N × f_ref.

---

## External hardware

| Component        | Value / Type       | Purpose                             |
|------------------|--------------------|-------------------------------------|
| Signal generator | 100 MHz, 1.8V CMOS | Reference clock on ua[0]            |
| Oscilloscope     | ≥1 GHz BW          | Monitor ua[1] and lock_detect       |
| Decoupling       | 100 nF on VDD      | Supply bypassing                    |

---

## Design Files

| File                                | Description                        |
|-------------------------------------|------------------------------------|
| projects/pll/sim/pll_full_tran_v2.spice | Full PLL transient simulation  |
| projects/pll/generate_layout.py     | Layout generator (gdstk)           |
| gds/tt_um_pll_sky130.gds            | Layout (GDS-II)                    |
| lef/tt_um_pll_sky130.lef            | Abstract (LEF)                     |
| projects/pll/lvs/pll_schematic.spice | LVS schematic netlist             |
| projects/pll/docs/pll_layout_report.md | Layout design report            |
| projects/pll/docs/pll_design.md     | PLL design equations               |
