![](../../workflows/gds/badge.svg) ![](../../workflows/docs/badge.svg)

# Analog IC Projects — Tiny Tapeout sky130A

Multi-project repository for analog IC designs targeting the Tiny Tapeout sky130A shuttle.
Each project lives under `projects/` and a top-level `config.yaml` selects which design
is built as the final GDS.

## Active Project: Ring-Oscillator PLL

A fully transistor-level phase-locked loop (PLL) with:
- **5-stage current-starved ring VCO** (50–500 MHz tunable)
- **Transistor-level PFD** (resettable TG DFFs + NAND reset — no XSPICE)
- **On-chip MOSCAP loop filter** (C1=10pF, C2=1pF, R=4.7kΩ)
- **10 µA matched charge pump** with current mirrors
- **÷4 feedback divider** (TG master-slave toggle FFs)

### Specifications

| Parameter | Value |
|-----------|-------|
| Process | SkyWater sky130A (130 nm) |
| Supply | 1.8 V |
| Tile | 1×2 (~161 × 226 µm) |
| Reference clock | 100 MHz |
| VCO range | 50 – 500 MHz |
| Lock frequency | 400 MHz (÷4 → 100 MHz) |
| Loop BW | ~7 MHz, ζ ≈ 0.9 |
| Analog pins | ua[0] = ref clock in, ua[1] = divided output |

### Layout

Hybrid standard-cell + custom analog layout generated with Python/gdstk:
- Digital blocks use `sky130_fd_sc_hd` standard cells (DRC-clean by construction)
- Analog blocks use custom transistor cells derived from PDK geometry
- MOSCAPs use NMOS gate capacitance (~8.3 fF/µm²)

## Project Structure

```
config.yaml              # Select active project (pll or tia)
build.py                 # Build script: generates GDS + updates info.yaml
projects/
  pll/                   # Ring-oscillator PLL
    generate_layout.py   # Layout generator
    sim/                 # SPICE simulations
    docs/                # Design documentation
    lvs/                 # LVS netlist
    gds_out/             # Generated GDS
  tia/                   # TIA (on main branch)
gds/                     # Final GDS for TT CI
info.yaml                # Tiny Tapeout project metadata
```

## Building

```bash
# Select project in config.yaml, then:
python3 build.py

# Or run the PLL layout generator directly:
python3 projects/pll/generate_layout.py
```

## Other Projects

- **TIA** (main branch): Inverter-based transimpedance amplifier, Zt ≈ 3776 Ω, BW ≈ 1.26 GHz
