# PLL Sky130A — Learnings & Procedures

Accumulated learnings from developing the ring-oscillator PLL on `pll_sky130A` branch.
These notes capture procedures, pitfalls, and fixes discovered during development.

---

## 1. Tiny Tapeout CI Requirements

The TT GitHub Actions CI checks fail if any of these are missing:

### Required Files
| File | Purpose |
|------|---------|
| `info.yaml` | Project metadata — **`author` field must not be empty** |
| `docs/info.md` | Datasheet — must contain `## How it works` and `## How to test` sections |
| `gds/<top_module>.gds` | Layout in GDS-II format |
| `lef/<top_module>.lef` | Abstract layout for P&R tools |

### Common Mistakes
- **Empty author**: `author: ""` causes `tt_tool.py --check-docs` to fail
- **Template docs/info.md**: The placeholder sections like "Explain how your project works" must be replaced with actual content
- **Missing LEF**: The CI runs `cp lef/<top>.lef tt_submission/` — it will fail if the LEF doesn't exist
- **Pin frame**: LEF must contain all TT standard pin definitions (VDPWR, VGND, ua[0:7], digital pins)

### Fix
The `generate_layout.py` script now generates GDS, LEF, and SVGs in a single run.
LEF uses the standard TT pin frame coordinates (from TIA main branch template).

---

## 2. Standard Cell Pin Ordering

Sky130 standard cells have a specific pin ordering that must be followed exactly.

### inv_1
```
.subckt sky130_fd_sc_hd__inv_1 A VGND VNB VPB VPWR Y
```
Instance: `Xinv <A> <VGND> <VNB> <VPB> <VPWR> <Y> sky130_fd_sc_hd__inv_1`

Typical: `Xinv sig_in VGND VGND VPWR VPWR sig_out sky130_fd_sc_hd__inv_1`

### dfrtp_1 (DFF with active-low async reset)
```
.subckt sky130_fd_sc_hd__dfrtp_1 CLK D RESET_B VGND VNB VPB VPWR Q
```
Instance: `Xdff <CLK> <D> <RESET_B> <VGND> <VNB> <VPB> <VPWR> <Q> sky130_fd_sc_hd__dfrtp_1`

### dfxbp_1 (DFF with Q and Q_N outputs)
```
.subckt sky130_fd_sc_hd__dfxbp_1 CLK D VGND VNB VPB VPWR Q Q_N
```

### nand2_1
```
.subckt sky130_fd_sc_hd__nand2_1 A B VGND VNB VPB VPWR Y
```

### Key Pitfall
- VNB (body N) = VGND for NMOS body connections
- VPB (body P) = VPWR for PMOS body connections
- **Do not add extra pins** — subcircuit pin count must match exactly!

### Resistor Model (res_xhigh_po_0p35)
```
.subckt sky130_fd_pr__res_xhigh_po_0p35 r0 r1 b
```
- **3 pins**: r0, r1, body — body usually tied to VGND
- **`.lib tt` redefinition conflict**: `.lib tt` internally defines this subcircuit with
  broken `w=$; l=$; mult=$;` parameter defaults (ngspice 45 can't parse `$`). Any
  user-provided `.include` or local definition is treated as "redefinition, ignored".
- **Workaround**: Use a custom subcircuit name (e.g. `pll_res_xhigh_po_0p35`) in the
  LVS schematic and testbench. Put params on the `.subckt` line:
  ```spice
  .subckt pll_res_xhigh_po_0p35 r0 r1 b w=0.35 l=5 mult=1
  Rbody r0 r1 r={l*2000/w/mult}
  .ends pll_res_xhigh_po_0p35
  ```
  rsheet=2000 Ω/sq for xhigh_po. `l/w` ratio gives correct R regardless of unit prefix.

---

## 3. MOSCAP Loop Filter Sizing

### Problem
Original design had C1=500pF (MIM capacitor) — needs 250,000 µm² which exceeds the entire tile area (36,386 µm²).

### Solution: NMOS Gate MOSCAP
- Gate oxide capacitance density: ~8.3 fF/µm² (100Å SiO₂)
- 10× denser than MIM/VPP caps
- C1 = 10pF → area ≈ 1,205 µm² → fits in ~39×42 µm cell
- Must be biased: gate = analog signal, S/D/B = VGND (inversion mode)

### Loop Parameters (redesigned)
```
Kvco = 1300 MHz/V = 8.17e9 rad/s/V
N = 4, Icp = 10 µA
R = 4.7 kΩ (poly xhrpoly, 48.2 Ω/sq, W=0.35µm, L=34µm)
C1 = 10 pF (MOSCAP: nfet_01v8, L=2µm, W=602µm multi-finger)
C2 = 1 pF (MOSCAP: nfet_01v8, L=2µm, W=60µm)
ωn ≈ 7.2 MHz, ζ ≈ 0.9, PM ≈ 52°
```

### Layout: Multi-Row MOSCAP
The `build_moscap()` function creates an interdigitated multi-row finger grid:
- Each finger: poly strip over diff with licon contacts
- Multiple columns, multiple rows
- Prevents single-row layouts that make cells too wide

---

## 4. Custom Transistor Layout Procedure

Following sky130_fd_sc_hd__inv_1 geometry patterns:

### NFET
1. Diffusion (65,20) strip — extends 0.260µm past poly on each side
2. Poly (66,20) strip — extends 0.130µm past diff on each side
3. Licon (66,44) contacts on source/drain (0.170×0.170µm)
4. LI1 (67,20) local interconnect over contacts
5. NSDM (93,44) implant enclosing diff (0.125µm enc)
6. Mcon (67,44) + met1 (68,20) for upper metal connections

### PFET
Same as NFET plus:
- PSDM (94,20) instead of NSDM
- NWELL (64,20) enclosing everything (0.180µm enc past diff)
- NPC (95,20) poly cut layer

### Key Dimensions
```
Gate length min:    0.150 µm
Licon/mcon size:    0.170 µm
Via1 size:          0.150 µm
Via2/via3 size:     0.200 µm
NSDM/PSDM enc:     0.125 µm
Nwell enc:          0.180 µm
Poly ext past diff: 0.130 µm
Diff ext past poly: 0.260 µm
```

---

## 5. SVG Generation from GDS

### Procedure
1. Load GDS with `gdstk.read_gds()`
2. **Also load standard cell library** so cell references resolve
3. Use `cell.get_polygons(depth=-1)` to flatten all hierarchical cells
4. Group polygons by (layer, datatype)
5. Convert to SVG paths with Y-axis flip (GDS Y-up → SVG Y-down)

### Common Pitfall
Without loading the standard cell GDS library, `get_polygons()` returns empty results
for standard cell instances. Must merge stdcell lib: `lib.add(sc)` for each cell.

---

## 6. ngspice Simulation Data Format

### TSV Output
ngspice `wrdata` produces space-separated columns (not tabs despite .tsv extension):
```
time v(signal1) time v(signal2) ...
```
Each signal gets its own time column (paired columns).

### Parsing
```python
header = f.readline().strip().split()  # NOT split('\t')
data = np.loadtxt(path, skiprows=1)
```

### Measurements
Use `.meas` with `FIND ... AT=` for voltage at specific times:
```spice
meas tran vc_1u FIND v(vctrl) AT=1u
```
NOT `print v(vctrl) at 1u` (not valid ngspice).

---

## 7. LVS Netlist Simulation

### Purpose
Verify that the SPICE netlist used for LVS comparison actually simulates correctly
and matches the standalone PLL simulation behavior.

### Procedure
1. Create a testbench that `.include` the LVS subcircuit
2. Add power supplies, clock source, initial conditions
3. Run full transient 15µs
4. Compare Vctrl settling and VCO frequency with standalone sim
5. Generate plots for comparison

### Key Checks
- Vctrl converges to same value (~1.016V)
- VCO frequency matches (~400 MHz)
- Lock time similar (<500ns)

---

## 8. File Structure (Multi-Project)

```
config.yaml              # Active project selection
build.py                 # Top-level build orchestrator
gds/<top_module>.gds     # Final GDS (CI reads this)
lef/<top_module>.lef     # Final LEF (CI reads this)
svg/combined.svg         # Layout visualization
svg/layer_*.svg          # Per-layer SVGs
docs/info.md             # Datasheet (CI reads this)
info.yaml                # Project metadata (CI reads this)
projects/
  pll/
    generate_layout.py   # Layout generator (creates GDS + LEF + SVGs)
    scripts/
      plot_pll_sim.py    # Simulation plot generator
    sim/
      pll_full_tran_v2.spice  # Standalone PLL sim
      pll_lvs_sim.spice       # LVS netlist testbench
      results/                # TSV data + PNG plots (TSV: local only)
    lvs/
      pll_schematic.spice     # LVS reference netlist
    docs/
      pll_layout_report.md
      pll_design.md
```

### .gitignore Rules
```
# Large simulation data — keep local, do not push
projects/*/sim/results/*.tsv
*.raw
```

---

## 9. Checklist Before Push

- [ ] `info.yaml`: author not empty, top_module correct, analog_pins set
- [ ] `docs/info.md`: Has "How it works", "How to test", "External hardware"
- [ ] `gds/<top>.gds` exists and is correct size
- [ ] `lef/<top>.lef` exists with all TT pin definitions
- [ ] `svg/combined.svg` exists
- [ ] LVS netlist pin counts match PDK subcircuit definitions
- [ ] No `.tsv` or `.raw` files staged (check .gitignore)
- [ ] Simulation results match expectations
