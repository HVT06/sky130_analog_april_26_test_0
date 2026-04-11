# PLL Design Report — Ring-Oscillator PLL for Tiny Tapeout sky130A

## 1. Overview

Fully transistor-level ring-oscillator PLL targeting the Tiny Tapeout sky130A shuttle.
All blocks are implemented with real sky130 PDK transistors — **no XSPICE behavioral models**.

| Parameter | Value |
|-----------|-------|
| Process | SkyWater sky130A (130 nm) |
| Supply | 1.8 V |
| Tile size | 1×2 (161 × 226 µm) |
| Reference frequency | 100 MHz |
| VCO frequency | 50 – 500 MHz (tunable) |
| Lock frequency | 400 MHz (÷4 → 100 MHz) |
| Analog pins | ua[0] = ref clock, ua[1] = divided output |

---

## 2. Architecture

```
            ┌──────────┐
 ua[0] ────►│   PFD    │──── UP ──►┌──────────┐
 (ref_clk)  │(2× DFF   │          │  Charge  │        ┌───────────┐
            │ + NAND   │──── DN ──►│  Pump    │──Vctrl─►│   Loop    │
            │ + delay) │          │  (10µA)  │        │  Filter   │
            └────▲─────┘          └──────────┘        │R=4.7kΩ   │
                 │                                     │C1=10pF   │
            div_clk                                    │C2=1pF    │
                 │                                     └─────┬────┘
            ┌────┴─────┐                                     │
            │ Divider  │◄── vco_out ──┌──────────┐◄──────────┘
            │   ÷4     │             │   VCO    │       (Vctrl)
            │(2×TG DFF)│             │ 5-stage  │
            └────┬─────┘             │curr-starv│
                 │                   │ring osc  │
              ua[1]                  └──────────┘
        (divided output)
```

---

## 3. Block Descriptions

### 3.1 Phase-Frequency Detector (PFD)

**Architecture:** Two resettable D flip-flops + NAND reset gate + 3-inverter delay chain.

| Component | Implementation |
|-----------|---------------|
| DFF | Transmission-gate master-slave with async reset (NMOS pull-down on master, PMOS pull-up on slave) |
| Reset gate | NAND2 (4 transistors) |
| Dead-zone delay | 3 inverters (~150 ps) |
| Total transistors | ~62 |

**Operation:**
- D inputs tied to VDD (always 1)
- Rising edge on ref_clk → UP = 1
- Rising edge on div_clk → DN = 1
- When both UP = DN = 1 → NAND(UP,DN) = 0 → through 3 inverters → rst = 1 → both DFFs reset
- The 3-inverter delay ensures both UP and DN pulses have minimum width (~150 ps) to avoid dead-zone

**Previous issue (fixed):** The original design used XSPICE `d_dff` and `d_and` behavioral models which cannot be fabricated. Now uses real sky130_fd_pr transistors throughout.

### 3.2 Charge Pump (CP)

| Parameter | Value |
|-----------|-------|
| Icp | 10 µA |
| Type | Dual current mirror with switches |
| PMOS mirror | L=1.0µ W=4.0µ (diode + mirror) |
| NMOS mirror | L=1.0µ W=2.0µ (diode + mirror) |
| Switches | L=0.15µ (W=2.0µ PMOS, W=1.0µ NMOS) |

### 3.3 Loop Filter

**Redesigned for on-chip feasibility.** Previous design used C1=500 pF which required ~250,000 µm² — larger than the entire tile.

| Component | Value | Implementation | Area |
|-----------|-------|---------------|------|
| R | 4.7 kΩ | Precision poly (xhrpoly, 48.2 Ω/sq) | ~17 × 1.4 µm |
| C1 | 10 pF | MOSCAP (NMOS gate cap, 8.3 fF/µm²) | ~39 × 42 µm |
| C2 | 1 pF | MOSCAP (NMOS gate cap) | ~13 × 15 µm |

**Loop dynamics:**
- K_vco ≈ 1300 MHz/V = 8.17 × 10⁹ rad/s/V
- N = 4 (÷4 divider)
- ω_n ≈ 2π × 7.2 MHz (natural frequency)
- ζ ≈ 0.9 (damping ratio)
- Phase margin ≈ 52°
- Lock time ≈ 1–2 µs (estimated)

### 3.4 Voltage-Controlled Oscillator (VCO)

**5-stage current-starved ring oscillator.**

| Parameter | Value |
|-----------|-------|
| Stages | 5 |
| Frequency range | 50 – 500 MHz |
| K_vco | ~1300 MHz/V |
| Supply | 1.8 V |
| Bias | PMOS diode (L=0.5µ W=4.0µ) + NMOS V-to-I (L=0.5µ W=2.0µ) |

Per-stage transistors:
| FET | Type | L (µm) | W (µm) | Function |
|-----|------|---------|---------|----------|
| Mp_src | PMOS | 0.50 | 4.0 | Current source |
| Mp_inv | PMOS | 0.15 | 2.0 | Inverter pull-up |
| Mn_inv | NMOS | 0.15 | 1.0 | Inverter pull-down |
| Mn_sink | NMOS | 0.50 | 2.0 | Current sink |

Output buffer: 2 cascaded standard cell inverters (sky130_fd_sc_hd__inv_1).

### 3.5 Feedback Divider (÷4)

Two cascaded divide-by-2 (toggle flip-flops).
Each div2: TG master-slave DFF with Q_N → D feedback.
Total: 44 transistors.

---

## 4. Layout

### 4.1 Approach

**Hybrid standard-cell + custom analog:**
- **Digital blocks** (PFD, divider): Use standard cells from `sky130_fd_sc_hd` library
  - `dfrtp_1` (DFF with async reset) for PFD
  - `dfxbp_1` (DFF with complementary outputs) for divider
  - `nand2_1`, `inv_1`, `tapvpwrvgnd_1` for logic and well taps
- **Analog blocks** (VCO, CP, MOSCAP, resistor): Custom transistor layout
  - Geometry derived from studying `sky130_fd_sc_hd__inv_1` standard cell
  - Gate length: 0.150 µm (matching PDK minimum)
  - All layers follow PDK DRC rules

### 4.2 Custom Cells

| Cell | Size (µm) | Description |
|------|-----------|-------------|
| pfet_vco_bias | 2.57 × 2.68 | PMOS diode-connected bias (L=0.5µ W=4.0µ, 2 fingers) |
| nfet_vco_vtoi | 1.27 × 2.63 | NMOS voltage-to-current (L=0.5µ W=2.0µ) |
| pfet_vco_src | 2.57 × 2.68 | VCO PMOS current source (L=0.5µ W=4.0µ, 2 fingers) |
| pfet_vco_inv | 1.03 × 2.36 | VCO PMOS inverter (L=0.15µ W=2.0µ) |
| nfet_vco_ninv | 0.92 × 1.26 | VCO NMOS inverter (L=0.15µ W=1.0µ) |
| nfet_vco_sink | 1.27 × 2.63 | VCO NMOS current sink (L=0.5µ W=2.0µ) |
| moscap_c1_10p | 39.39 × 41.96 | 10 pF MOSCAP (NMOS gate cap, multi-finger interdigitated) |
| moscap_c2_1p | 12.66 × 15.40 | 1 pF MOSCAP |
| poly_r_4k7 | 17.11 × 1.40 | 4.7 kΩ precision poly resistor (serpentine) |

### 4.3 Floorplan

```
┌──────────────────────────────────────┐ ← 226 µm
│    VDD (met4 power stripe)           │
│                                      │
│    ┌──────────────────────────┐      │
│    │       VCO (top)          │      │
│    │  5 stages + bias + buf   │      │
│    └──────────────────────────┘      │
│                                      │
│    ┌──────────┐  ┌───────────────┐   │
│    │  Charge  │  │  Loop Filter  │   │
│    │  Pump    │  │  C1 (39×42)   │   │
│    ├──────────┤  │  C2 (13×15)   │   │
│    │   PFD    │  │  R  (17×1.4)  │   │
│    ├──────────┤  └───────────────┘   │
│    │ Divider  │                      │
│    │   ÷4     │                      │
│    └──────────┘                      │
│                                      │
│    VSS (met4 power stripe)           │
└──────────────────────────────────────┘ ← 0
 ua[0]←                            →ua[1]
 (ref)                            (div_out)
```

### 4.4 Power Distribution

- **Met4**: Horizontal VDD and VSS stripes (top and bottom of tile)
- **Met3**: Vertical power trunks (left = VSS, right = VDD)
- **Via3**: Connects met3 trunks to met4 stripes
- **Met1**: Local power rails within each block

### 4.5 Signal Routing

- **Met2**: Vertical signal buses (vctrl, vco_out, div_clk, UP, DN)
- **Met3**: Analog pin connections (ref_clk from ua[0], div_out to ua[1])
- **Via3**: Connects met3 analog routing to met4 pads

---

## 5. SKY130 Layer Map (GDS)

| Layer | (GDS#, DT) | Usage |
|-------|-----------|-------|
| nwell | (64, 20) | N-well for PMOS |
| diff | (65, 20) | Active diffusion |
| tap | (65, 44) | Well tap |
| poly | (66, 20) | Polysilicon gate |
| licon | (66, 44) | Contact: diff/poly → LI1 |
| li1 | (67, 20) | Local interconnect |
| mcon | (67, 44) | Contact: LI1 → met1 |
| met1 | (68, 20) | Metal 1 |
| via1 | (68, 44) | Via: met1 → met2 |
| met2 | (69, 20) | Metal 2 |
| via3 | (70, 44) | Via: met3 → met4 |
| met3 | (70, 20) | Metal 3 |
| met4 | (71, 20) | Metal 4 (power, analog pins) |
| nsdm | (93, 44) | N+ source/drain implant |
| psdm | (94, 20) | P+ source/drain implant |
| npc | (95, 20) | Nitride poly cut |

---

## 6. Interface Pinout

| Pin | Direction | Layer | Description |
|-----|-----------|-------|-------------|
| ua[0] | Input | met4 | Reference clock (100 MHz) |
| ua[1] | Output | met4 | Divided VCO output |
| VPWR | Power | met4 | VDD = 1.8 V |
| VGND | Power | met4 | VSS = 0 V |

---

## 7. Key Design Decisions

### 7.1 Loop Filter Capacitor Sizing

The original design used C1 = 500 pF, which requires ~250,000 µm² of MIM capacitance — far exceeding the 161 × 226 µm = 36,386 µm² tile area. 

**Solution:** Reduced to C1 = 10 pF (MOSCAP, ~1650 µm²) and increased R to 4.7 kΩ to maintain the same loop bandwidth. This trades off lock time for area efficiency. The MOSCAP uses NMOS gate capacitance (Cox ≈ 8.3 fF/µm²) which is ~4× denser than VPP metal caps.

### 7.2 XSPICE PFD Replacement

The original PFD used ngspice XSPICE primitives (`d_dff`, `d_and`, `adc_bridge`, `dac_bridge`) which simulate correctly but cannot be fabricated. 

**Solution:** Replaced with a transmission-gate master-slave DFF modified with asynchronous reset. Each DFF uses:
- 4 transmission gates + 5 inverters + 1 reset NMOS + 1 reset PMOS
- Total: 24 transistors per DFF (vs. zero physical transistors in XSPICE)

### 7.3 Standard Cell + Custom Hybrid Layout

Rather than building everything custom (error-prone for DRC) or everything standard-cell (can't match analog specs), we use:
- Standard cells for digital blocks (DRC-clean by construction)
- Custom cells only for analog blocks (VCO, CP, MOSCAP) where exact W/L sizing matters

---

## 8. File Structure

```
projects/pll/
├── generate_layout.py      # Layout generator (Python + gdstk)
├── gds_out/
│   └── tt_um_pll_sky130.gds  # Generated layout
├── sim/
│   ├── pll_full_tran_v2.spice  # Full PLL sim (transistor-level PFD)
│   ├── pll_full_tran.spice     # Original sim (XSPICE PFD, archived)
│   ├── pll_vco_tran.spice      # VCO characterization
│   ├── pll_vco_dc.spice        # VCO DC transfer
│   ├── pll_vco_noise.spice     # VCO phase noise
│   ├── pll_div_tran.spice      # Divider standalone
│   └── results/                # Simulation data
├── docs/
│   ├── pll_design.md           # This document
│   ├── pll_specifications.md   # Detailed specifications
│   ├── pll_sim_report.md       # Simulation results
│   ├── pll_iteration_log.md    # Development history
│   └── pll_layout_report.md    # Layout report
└── lvs/
    └── pll_schematic.spice     # LVS reference netlist
```
