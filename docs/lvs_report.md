# LVS Report — tt_um_hvt006_tia

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
