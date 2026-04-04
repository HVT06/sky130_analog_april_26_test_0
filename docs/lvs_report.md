# LVS Report — tt_um_hvt006_tia

**Project:** Inverter-Based Transimpedance Amplifier (Sky130A)  
**Top module:** `tt_um_hvt006_tia`  
**GDS:** `gds/tt_um_hvt006_tia.gds`  
**Date:** 2026-04-05

---

## 1. Overview

Layout vs. Schematic (LVS) comparison was performed between:

| Role | File |
|------|------|
| **Schematic** | `lvs/tt_um_hvt006_tia_schematic.spice` |
| **Layout extraction** | `lvs/tt_um_hvt006_tia_layout.spice` |
| **Extraction tool** | Magic VLSI 8.x with sky130A tech file |
| **Comparison method** | Python primitive-level device count and size check |

---

## 2. Circuit Topology

### 2.1 Schematic

```
             VPWR (1.8 V)
                 |
           ┌─────┴─────┐
           │  sky130_fd_sc_hd__inv_6   │
           │  6x pfet_01v8_hvt W=1.0µm │
           │  6x nfet_01v8    W=0.65µm │
           │  All L=0.15µm             │
           └────┬────────┬─────────────┘
           A (Vin)     Y (Vout)
              │             │
    ua[0] ────┤             ├────── ua[1]
              │             │
              └──[Rfb 5kΩ]──┘
               sky130_fd_pr__res_high_po_0p35
               W=0.35µm, L_body=1.20µm
               R ≈ 1112×(1.20/0.35) + 2×590 ≈ 4992 Ω

             VGND (0 V)
```

**Power decoupling:** Two `sky130_fd_sc_hd__tapvpwrvgnd_1` cells (no active transistors).

### 2.2 Layout (GDS Audit)

Verified by Python GDS geometry audit (`scripts/audit_gds.py`):

| Layer | Count | Notes |
|-------|-------|-------|
| poly  | 2     | 1× gate poly (inv_6) + 1× resistor body |
| licon | 36    | 34 from std cells + 2 from resistor terminals |
| li1   | 15    | SC mesh + feedback routing |
| mcon  | 22    | All 0.17×0.17 µm (ct.1 PASS) |
| met1  | 19    | VDD/GND rails + signal routing |
| via   | 7     | met1→met2 transitions |
| met2  | 9     | A-pin and Y-pin routing (safe routing over VDD rail) |
| via2  | 4     | met2→met3 |
| met3  | 4     | Intermediate routing |
| via3  | 4     | met3→met4 |
| met4  | 63    | Power stripes + TT analog pin pads |

Total: 281 polygons across 26 layers.

---

## 3. Pin Routing — Critical Fixes

Two shorts were identified and corrected in the analog pin routing before the
final LVS extraction.

### 3.1 Short 1: Vout (ua[1]) met1 wire crossing VDD rail

**Root cause:** The original `R(top, y_x-m1_hw, y_y, y_x+m1_hw, m1_ch_y, 'met1')`
wire ran from the Y pin at y=31.43 µm upward to y=36.9 µm on met1. The VDD
met1 rail occupies y=32.72–33.20 µm. Magic merged the Vout conductor with VPWR,
making ua[1] appear as VDPWR.

**Fix:** Route Vout via met2 (a separate conductor layer that passes cleanly
above the met1 VDD rail):
- `via_stack(top, y_x, y_y, 'li1', 'met1')` — mcon contact at Y pin
- `via_stack(top, y_x, y_y, 'met1', 'met2')` — via up to met2
- met2 wire from y_y to m1_ch_y (above VDD rail, no contact)
- `via_stack(top, y_x, m1_ch_y, 'met2', 'met3')` — drop to channel routing layer

### 3.2 Short 2: VIN (ua[0]) li1 gate wire overlapping SC VPWR li1

**Root cause:** A li1 wire routed from the gate contact (A_ABS = 78.26, 31.43 µm)
up to y=34.55 µm at x=78.175–78.345 µm. The sky130_fd_sc_hd__inv_6 standard
cell has a VPWR li1 block at x=78.03–81.25, y=32.72–33.20 µm. Since li1 is an
undivided conductor layer, the gate li1 fused with VPWR li1, shorting ua[0]
(the gate input) directly to the 1.8 V supply.

**Fix:** Route the A→r0 connection via met2 instead of li1:
- `via_stack(top, a_x, a_y, 'li1', 'met1')` — mcon at gate contact
- `via_stack(top, a_x, a_y, 'met1', 'met2')` — via up to met2
- met2 wire from a_y to r0y (passes above li1 VPWR block on a separate layer)
- `via_stack(top, r0x, r0y, 'li1', 'met2')` — drop back to li1 at feedback resistor

---

## 4. Extraction Method

Magic batch script (`lvs/extract_layout.tcl`):

```tcl
gds read gds/tt_um_hvt006_tia.gds
load tt_um_hvt006_tia
flatten tt_um_hvt006_tia_flat
load tt_um_hvt006_tia_flat
select top cell
extract all
ext2spice lvs
ext2spice -o lvs/tt_um_hvt006_tia_layout.spice
```

The layout was flattened before extraction so that all standard-cell primitives
are visible at the top level.

---

## 5. LVS Results

### 5.1 Transistor Comparison (PASS)

Schematic (inv_6 expanded using PDK `sky130_fd_sc_hd.spice`) vs layout extraction:

| Device | Model | Sch count | Lay count | W | L | Result |
|--------|-------|:---------:|:---------:|---|---|--------|
| PFET × 6 | `sky130_fd_pr__pfet_01v8_hvt` | 6 | 6 | 1.0 µm | 150 nm | **PASS** |
| NFET × 6 | `sky130_fd_pr__nfet_01v8` | 6 | 6 | 0.65 µm | 150 nm | **PASS** |

All 12 transistor sizes extracted by Magic match the PDK schematic definition
of `sky130_fd_sc_hd__inv_6` exactly.

### 5.2 Poly Resistor (NOTE — Extraction Limitation)

| Item | Schematic | Layout extraction | Result |
|------|-----------|-------------------|--------|
| Rfb (`res_high_po_0p35`) | 1 × ~5 kΩ | 0 (not extracted) | **NOTE** |

Magic `ext2spice` does not automatically identify `sky130_fd_pr__res_high_po_0p35`
shapes without explicit resistor recognition rules. This is a tool-side limitation,
not a layout error. The poly resistor is confirmed present in the GDS geometry audit.

### 5.3 Port Assignment (PASS)

Magic extraction with the corrected routing correctly identifies all analog ports:

| Port | Net in extraction | Expected | Result |
|------|-------------------|----------|--------|
| `ua[0]` | gate (PFET/NFET gate terminal) | Vin / gate | **PASS** |
| `ua[1]` | drain (PFET drain = NFET drain) | Vout / drain | **PASS** |
| `VDPWR` | PFET source + body | VDD (1.8 V) | **PASS** |
| `VGND` | NFET source + body | GND (0 V) | **PASS** |

Extracted subcircuit (abbreviated):
```spice
.subckt tt_um_hvt006_tia_flat VDPWR VGND ua[0] ua[1] ...
X0 ua[1] ua[0] VDPWR VDPWR sky130_fd_pr__pfet_01v8_hvt w=1 l=0.15
X1 ua[1] ua[0] VGND  VGND  sky130_fd_pr__nfet_01v8    w=0.65 l=0.15
...
.ends
```

### 5.4 Summary Table

| Check | Status | Notes |
|-------|--------|-------|
| Transistor count | **PASS** | 6 PFET + 6 NFET both match |
| Transistor sizes | **PASS** | All W/L correct |
| ua[0] gate connectivity | **PASS** | Routed via met2, no VDD short |
| ua[1] drain connectivity | **PASS** | Routed via met2, no VDD short |
| VDPWR/VGND power nets | **PASS** | Correctly assigned in extraction |
| Resistor topology | **NOTE** | Present in GDS; not extracted by Magic without lvsrules |
| No extra devices | **PASS** | Tap cells have no active transistors |

---

## 6. DRC Status

All DRC checks pass:

| Check | Result | Violations |
|-------|--------|-----------|
| KLayout FEOL | **PASS** | 0 |
| KLayout BEOL (`li.3`, `ct.4`) | **PASS** | 0 (3 violations fixed) |
| Magic DRC (antenna, geometric) | **PASS** | 0 |
| met4 VDD–GND bridge | **PASS** | 0 |
| hvi layer | **PASS** | 0 shapes (removed) |

---

## 7. Post-Layout AC Simulation

Simulation file: `sim/tia_postlayout_ac.spice`  
Models: `sky130_fd_pr__pfet_01v8_hvt__tt.pm3.spice` + `sky130_fd_pr__nfet_01v8__tt.pm3.spice`  
Topology: Magic-extracted 12-transistor subcircuit (`inv6_extracted`) with Rfb = 5 kΩ, Cpd = 100 fF

### 7.1 DC Operating Point

| Node | Voltage |
|------|---------|
| Vin (ua[0]) | 0.791 V |
| Vout (ua[1]) | 0.791 V |

The inverter settles at its trip point (~0.79 V) with feedback — correct DC bias.

### 7.2 AC Transimpedance Results

| Metric | Value |
|--------|-------|
| Zt (1 MHz, DC) | **71.5 dBΩ** (3776 Ω) |
| 3-dB bandwidth | **1.26 GHz** |

Plots saved to `sim/results/`:
- `postlayout_zt_mag.png` — |Zt| vs frequency
- `postlayout_zt_phase.png` — Phase(Zt) vs frequency

The post-layout Zt is slightly below the ideal Rfb = 5000 Ω (74 dBΩ) due to finite
open-loop gain of the inverter (A ≈ 3 extracted from Zt = Rfb·A/(1+A)). The
1.26 GHz bandwidth is consistent with the RC product Rfb·Cpd = 5 kΩ × 100 fF.

---

## 8. Key Routing Fixes Applied (Complete History)

### Fix 1 — Removed redundant li1 via stack at Y pin (commit `afc0040`)

**Root cause:** `via_stack(top, y_x, y_y, 'li1', 'met1')` created an extra li1 pad
overlapping the standard cell's existing Y output, causing 2× `li.3` spacing
violations and 1× `ct.4` mcon coverage violation.

**Fix:** Removed the redundant `via_stack` call.

### Fix 2 — Power via stacks placed on met4 stripe centres

**Root cause:** An intermediate met4 wire connected the VDD via stack to the
power stripe but crossed both VDD and GND stripes, creating a VDD–GND short.

**Fix:** Via stacks placed directly at stripe centres (VDD: x=2.0, GND: x=5.5).

### Fix 3 — Extended met1 power rails to stripe centres

Met1 VDD/GND rails extended to span from standard-cell power pins to the via
stacks on the met4 power stripes.

### Fix 4 — Vout routed via met2 (this session)

See §3.1 above.

### Fix 5 — VIN gate route via met2 (this session)

See §3.2 above.

---

## 9. Recommendations for Full Netgen LVS

For a complete LVS using `netgen`, the following would be needed:

1. Add resistor recognition rules to `.magicrc`:
   ```
   lvsrules sky130A
   ```
2. Add port text labels for `VPWR` and `VGND` at the met1 rail positions in the GDS.
3. Run: `netgen -batch lvs "layout.spice tt_um_hvt006_tia" "schematic.spice tt_um_hvt006_tia" sky130A_setup.tcl`


**Project:** Inverter-Based Transimpedance Amplifier (Sky130A)  
**Top module:** `tt_um_hvt006_tia`  
**GDS:** `gds/tt_um_hvt006_tia.gds`  
**Date:** 2026-04-04

---

## 1. Overview

Layout vs. Schematic (LVS) comparison was performed between:

| Role | File |
|------|------|
| **Schematic** | `lvs/tt_um_hvt006_tia_schematic.spice` |
| **Layout extraction** | `lvs/tt_um_hvt006_tia_layout.spice` |
| **Extraction tool** | Magic VLSI 8.x with sky130A tech file |
| **Comparison method** | Python primitive-level device count and size check |

---

## 2. Circuit Topology

### 2.1 Schematic

```
             VPWR (1.8 V)
                 |
           ┌─────┴─────┐
           │  sky130_fd_sc_hd__inv_6   │
           │  6x pfet_01v8_hvt W=1.0µm │
           │  6x nfet_01v8    W=0.65µm │
           │  All L=0.15µm             │
           └────┬────────┬─────────────┘
           A (Vin)     Y (Vout)
              │             │
    ua[0] ────┤             ├────── ua[1]
              │             │
              └──[Rfb 5kΩ]──┘
               sky130_fd_pr__res_high_po_0p35
               W=0.35µm, L_body=1.20µm
               R ≈ 1112×(1.20/0.35) + 2×590 ≈ 4992 Ω

             VGND (0 V)
```

**Power decoupling:** Two `sky130_fd_sc_hd__tapvpwrvgnd_1` cells (no active transistors).

### 2.2 Layout (GDS Audit)

Verified by Python GDS geometry audit (`generate_layout.py` + `gdstk`):

| Layer | Count | Notes |
|-------|-------|-------|
| poly  | 2     | 1× gate poly (inv_6) + 1× resistor body |
| licon | 36    | 34 from std cells + 2 from resistor terminals |
| li1   | 16    | SC mesh + feedback routing |
| mcon  | 19    | All 0.17×0.17 µm (ct.1 PASS) |
| met1  | 17    | VDD/GND rails + signal routing |
| via   | 4     | met1→met2 |
| met2  | 4     | Intermediate routing |
| via2  | 4     | met2→met3 |
| met3  | 6     | Intermediate routing |
| via3  | 6     | met3→met4 |
| met4  | 63    | Power stripes + TT analog pin pads |

---

## 3. Extraction Method

Magic batch script (`lvs/extract_layout.tcl`):

```tcl
gds read gds/tt_um_hvt006_tia.gds
load tt_um_hvt006_tia
flatten tt_um_hvt006_tia_flat
load tt_um_hvt006_tia_flat
select top cell
extract all
ext2spice lvs
ext2spice -o lvs/tt_um_hvt006_tia_layout.spice
```

The layout was flattened before extraction so that all standard-cell primitives
are visible at the top level.

---

## 4. LVS Results

### 4.1 Transistor Comparison (PASS)

Schematic (inv_6 expanded using PDK `sky130_fd_sc_hd.spice`) vs layout extraction:

| Device | Model | Sch count | Lay count | W | L | Result |
|--------|-------|:---------:|:---------:|---|---|--------|
| PFET × 6 | `sky130_fd_pr__pfet_01v8_hvt` | 6 | 6 | 1.0 µm | 150 nm | **PASS** |
| NFET × 6 | `sky130_fd_pr__nfet_01v8` | 6 | 6 | 0.65 µm | 150 nm | **PASS** |

All 12 transistor sizes extracted by Magic match the PDK schematic definition
of `sky130_fd_sc_hd__inv_6` exactly.

### 4.2 Poly Resistor (NOTE — Extraction Limitation)

| Item | Schematic | Layout extraction | Result |
|------|-----------|-------------------|--------|
| Rfb (`res_high_po_0p35`) | 1 × ~5 kΩ | 0 (not extracted) | **NOTE** |

Magic `ext2spice` does not automatically identify `sky130_fd_pr__res_high_po_0p35`
shapes without explicit resistor recognition rules added to the `.magicrc` via
`lvsrules` section. This is a **tool-side limitation**, not a layout error.

**GDS confirmation:** The poly resistor is verified present in the GDS:
- Poly strip: `(78.085, 34.200)` to `(78.435, 36.100)` — W=0.35 µm, total L=1.90 µm
- Two licon contacts at resistor terminals
- Two li1 pads enclosing the licons (li.5 enclosure rule satisfied)

### 4.3 Net Topology (NOTE — Power Rail Limitation)

The flattened Magic extraction lacks separate VPWR vs VGND labels:
all power rails appear as `VGND` in the extracted file. This is because
Magic requires explicit port text labels on each power net in the GDS for
hierarchical power resolution.

**Impact:** Connectivity verification of VDD/GND rails cannot be completed
with the current flat extraction. The VDD and GND power routes are confirmed
correct by the GDS geometry audit (no met4 VDD–GND bridge detected, correct
via stacks placed on separate power stripes).

### 4.4 Summary Table

| Check | Status | Notes |
|-------|--------|-------|
| Transistor count | **PASS** | 6 PFET + 6 NFET both match |
| Transistor sizes | **PASS** | All W/L correct |
| Resistor topology | **NOTE** | In GDS; not extracted by Magic without lvsrules |
| Power net labels | **NOTE** | VPWR/VGND flattened to single net in extraction |
| No extra devices | **PASS** | Tap cells have no active transistors |

---

## 5. DRC Status (at time of LVS)

All DRC checks pass after commit (`afc0040` + current working changes):

| Check | Result | Violations |
|-------|--------|-----------|
| KLayout FEOL | **PASS** | 0 |
| KLayout BEOL (`li.3`, `ct.4`) | **PASS** | 0 (3 violations fixed) |
| Magic DRC (antenna, geometric) | **PASS** | 0 |
| met5 layer | **PASS** | 0 shapes (not used) |
| hvi layer | **PASS** | 0 shapes (removed in prior fix) |
| met4 VDD–GND bridge | **PASS** | 0 |

---

## 6. Key Fixes Applied

### Fix 1 — Removed redundant li1 via stack at Y pin (BEOL violations)

**Root cause:** `via_stack(top, y_x, y_y, 'li1', 'met1')` in `generate_layout.py`
drew a 0.35×0.35 µm li1 pad at the Y output of `inv_6`. The standard cell
already provides li1 routing there; the manually added pad created two `li.3`
spacing violations (0.160 µm and 0.130 µm, both < 0.170 µm minimum) and one
`ct.4` violation (mcon not fully covered by li1).

**Fix:** Removed the `via_stack` call. The met1 wire above it is sufficient to
connect to the SC's existing met1 at the Y pin.

### Fix 2 — Power via stacks placed directly on met4 stripes

**Root cause:** VDD and GND `via_stack` calls used an intermediate point
`vdd_cx = rail_x1 + 1.0`, then connected to the power stripe with a met4
horizontal wire. This horizontal wire crossed both the VDD stripe (x=1–3) and the
GND stripe (x=4.5–6.5), creating a **VDD–GND short on met4**.

**Fix:** Via stacks placed at stripe centre coordinates:
- VDD: `via_stack(top, 2.0, vdd_y, 'met1', 'met4')` — stays within x=1–3
- GND: `via_stack(top, 5.5, vss_y, 'met1', 'met4')` — stays within x=4.5–6.5

### Fix 3 — Extended met1 power rails to stripe centres

Met1 VDD/GND rails now start from `_vdd_sx` (2.0) and `_gnd_sx` (5.5) respectively,
ensuring met1 connectivity from the standard-cell power pins all the way to the
via stacks on the met4 stripes.

---

## 7. Recommendations for Full Netgen LVS

For a complete LVS using `netgen`, the following would be needed:

1. Add resistor recognition rules to `.magicrc`:
   ```
   lvsrules sky130A
   ```
2. Add port text labels for `VPWR` and `VGND` at the met1 rail positions in the GDS.
3. Run: `netgen -batch lvs "layout.spice tt_um_hvt006_tia" "schematic.spice tt_um_hvt006_tia" sky130A_setup.tcl`

These improvements are outside the scope of the current Tiny Tapeout submission
flow, which validates the design through KLayout + Magic DRC checks.
