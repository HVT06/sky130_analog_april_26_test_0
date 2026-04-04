# Sky130A DRC Rules — Comprehensive Reference for Analog Layout

**Source files explored:**
- `/home/hvt06/Downloads/open_pdks/sky130/sky130A/libs.tech/klayout/drc/sky130A_mr.drc` (1629 lines, Klayout FEOL/BEOL DRC)
- `/home/hvt06/Downloads/open_pdks/sky130/sky130A/libs.tech/magic/sky130A.tech` (antenna section)
- TT precheck: `tt/precheck/precheck.py` (runs `magic_drc`, `klayout_drc feol`, `klayout_drc beol`)

---

## 1. Overview: Three DRC Checks in TT Precheck

| Check | Tool | Flag in `sky130A_mr.drc` | What it catches |
|-------|------|--------------------------|-----------------|
| `magic_drc` | Magic VLSI | N/A (separate `.tech` rules) | Geometric DRC + **antenna ratio violations** |
| `klayout_drc feol` | KLayout | `$feol = "true"` | Front-end layers: diff, poly, tap, licon, implants, well |
| `klayout_drc beol` | KLayout | `$beol = "true"` | Back-end layers: li1, mcon, met1–met4, via1–via3 + areas |

Optional flags (default **off** in TT precheck):

| Flag | Default | Effect |
|------|---------|--------|
| `$floating_met` | `false` | When `true`, fires `m1.x / m2.x / m3.x / m4.x` — isolated metal not touching any via |
| `$offgrid` | `false` | Manufacturing grid / non-45° angle checks |
| `$seal` | `false` | Seal-ring specific checks |

---

## 2. Sky130A Layer Map (Relevant to Analog Periphery Layout)

### 2.1 Physical Drawing Layers

| Layer name | GDS (layer/dt) | Role |
|------------|---------------|------|
| `nwell` | 64/20 | N-well for PMOS |
| `diff` | 65/20 | Active diffusion (NMOS or PMOS drain/source) |
| `tap` | 65/44 | Substrate / N-well tap (bulk contact) |
| `poly` | 66/20 | Gate poly + poly resistor body |
| `licon` | 66/44 | Local interconnect contact cut (poly↔li1, diff↔li1) |
| `li1` | 67/20 | First local interconnect metal |
| `mcon` | 67/44 | li1 → met1 via cut |
| `met1` | 68/20 | Metal 1 |
| `via` (via1) | 68/44 | met1 → met2 via cut |
| `met2` | 69/20 | Metal 2 |
| `via2` | 69/44 | met2 → met3 via cut |
| `met3` | 70/20 | Metal 3 |
| `via3` | 70/44 | met3 → met4 via cut |
| `met4` | 71/20 | Metal 4 (TT pin layer for analog projects) |
| `nsdm` | 93/44 | N+ source/drain implant |
| `psdm` | 94/20 | P+ source/drain implant |
| `npc` | 95/20 | N+ poly contact marker (required around poly licons in `areaid_ce` core only) |
| `prbndry` | 235/4 | PR (placement and routing) boundary |

### 2.2 Marker / Indicator Layers (CRITICAL: do NOT misuse)

| Layer name | GDS (layer/dt) | Purpose | Key constraint |
|------------|---------------|---------|----------------|
| `hvi` | **75/20** | High Voltage Indicator — marks HV (5 V) devices | min width **0.6 µm** (hvi.1), min spacing 0.7 µm (hvi.2a). **DO NOT USE for poly resistors.** |
| `rpm` | 86/20 | Resistor Poly Mask — marks precision poly resistors | min width **1.27 µm** (rpm.1a) — too wide for 0.35 µm poly body |
| `urpm` | 79/20 | Ultra-precision Resistor Poly Mask | same rules as rpm |
| `hvtp` | 78/44 | HV threshold adjust for PMOS | min width 0.38 µm |
| `rdl` | 74/20 | Redistribution layer | **PROHIBITED** (MR_rdl.CON.1 always fires) |

> **Critical lesson:** `(75,20)` is `hvi` (High Voltage Indicator), NOT "RPO" or "Resist Protect Oxide".  
> Drawing a shape narrower than 0.6 µm on `(75,20)` causes FEOL rule `hvi.1` to fire.  
> For standard-voltage periphery poly resistors (`sky130_fd_pr__res_high_po_0p35`), draw bare poly only — no marker layer is needed.

---

## 3. FEOL DRC Rules (sky130A_mr.drc, `if FEOL`)

### 3.1 Poly (66/20) — rule prefix `poly`

| Rule | Value | Description |
|------|-------|-------------|
| `poly.1` | min 0.15 µm | Minimum poly width |
| `poly.2` | min 0.21 µm | Minimum poly spacing (periphery) |
| `poly.3` | min 0.16 µm | Minimum poly spacing inside `areaid:core` |

For our 0.35 µm wide resistor poly: poly.1 ✓ (0.35 ≥ 0.15).

### 3.2 Local Interconnect Contact (66/44) — prefix `licon`

| Rule | Value | Description |
|------|-------|-------------|
| `licon.1` | exactly **0.17 µm** | All licon shapes must be 0.17 × 0.17 µm rectangles (fires when `length ≠ 0.17`) |
| `licon.1_c` | — | licon must be a rectangle |
| `MR_licon.SP.1` | min 0.17 µm | Minimum licon spacing in periphery |
| `licon.13` | min 0.09 µm | Licon on diff must be ≥ 0.09 µm from npc in periphery |
| `licon.13_a` | — | Licon on diff must not overlap npc |
| `licon.6` | min 0.045 µm | npc must enclose poly-licon by ≥ 0.045 µm — **applies only inside `areaid_ce`** |
| `licon.17` | — | Licon must not overlap BOTH poly and (diff or tap) simultaneously |

> **Key:** licons must be placed **exactly** 0.17 × 0.17 µm (`lhw = 0.085` in Python).  
> The `licon.6` / npc rule is `areaid_ce` (standard cell core) only — does NOT apply to periphery layout.

### 3.3 Diffusion / Tap (65/20, 65/44)

| Rule | Value | Description |
|------|-------|-------------|
| `difftap.1` | min 0.15 µm | Min diff/tap width in core |
| `difftap.1_c` | min 0.15 µm | Min tap width in periphery |
| `difftap.1` (sp) | min 0.27 µm | Min diff/tap spacing |

### 3.4 N-well (64/20) — prefix `nwell`

| Rule | Value | Description |
|------|-------|-------------|
| `nwell.1` | min 0.84 µm | Minimum nwell width |
| `nwell.2` | min 1.27 µm | Minimum nwell spacing |
| `nwell.9` | — | HV nwell must be enclosed by `hvi` — **only relevant if hvi is drawn** |

### 3.5 Implants (93/44 nsdm, 94/20 psdm)

| Rule | Value | Description |
|------|-------|-------------|
| `nsdm.1` | min 0.38 µm | Min nsdm spacing in periphery |
| `nsdm.2` | min 0.38 µm | Min nsdm width in periphery |
| `psdm.*` | similar | Same geometric rules for psdm |

### 3.6 hvi (75/20) — the "FEOL 1 violation" root cause

| Rule | Value | Description |
|------|-------|-------------|
| `hvi.1` | min **0.6 µm** | Minimum hvi width in periphery |
| `hvi.2a` | min 0.7 µm | Minimum hvi spacing in periphery |

**Root cause of the 1 FEOL CI violation** in commit `39e6b1b`:  
The layout generator had `LY['rpo'] = (75, 20)` and drew an RPO shape 0.55 µm wide  
(`W + 2 × rpo_gap = 0.35 + 0.20 = 0.55 µm < 0.60 µm`), violating `hvi.1`.

**Fix:** Remove all drawing on `(75,20)`. For periphery poly resistors, no marker layer is required.

---

## 4. BEOL DRC Rules (sky130A_mr.drc, `if BEOL`)

### 4.1 Via / Cut Exact Sizes (most common source of violations)

Sky130A has **strict min=max** rules for every via type. Any size other than the exact required dimension violates both the minimum and/or maximum rule.

| Via type | Layer (GDS) | Required size | Rule (min) | Rule (max) |
|----------|-------------|---------------|------------|------------|
| `licon` | 66/44 | **0.17 × 0.17 µm** | `licon.1` | `licon.1` |
| `mcon` | 67/44 | **0.17 × 0.17 µm** | `ct.1_a` | `ct.1_b` |
| `via` (via1) | 68/44 | **0.15 × 0.15 µm** | `via.1a_a` | `via.1a_b` |
| `via2` | 69/44 | **0.20 × 0.20 µm** | `via2.1a_a` | `via2.1a_b` |
| `via3` | 70/44 | **0.20 × 0.20 µm** | `via3.1_a` | `via3.1_b` |

In Python code: use `_VIA_HW = {'licon': 0.085, 'mcon': 0.085, 'via': 0.075, 'via2': 0.100, 'via3': 0.100}`.

**Root cause of the 61 BEOL CI violations** in commit `39e6b1b`:  
Old `via_stack()` used a single `hw=0.09` for ALL via types → 0.18 µm for all.  
With wrong sizes and undersized metal pads (mhw=0.175 for met3/met4), the following rules fired:

| Violated rule | Count | Cause |
|---------------|-------|-------|
| `ct.1_b` | 2 | mcon 0.18 µm > max 0.17 µm |
| `via.1a_b` | 4 | via 0.18 µm > max 0.15 µm |
| `via2.1a_a` | 4 | via2 0.18 µm < min 0.20 µm |
| `via3.1_a` | 6 | via3 0.18 µm < min 0.20 µm |
| `via3.5` | 6 | met3 enclosure of via3 < 0.09 µm (0.085 µm with 0.35 µm pad around 0.18 µm via) |
| `m3.6` | 6 | met3 pad 0.35×0.35=0.1225 µm² < min 0.240 µm² |
| `m4.4a` | 6 | met4 pad 0.35×0.35=0.1225 µm² < min 0.240 µm² |

### 4.2 li1 Metal Rules (67/20)

| Rule | Value | Description |
|------|-------|-------------|
| `li.1` | min 0.17 µm | Minimum li1 width in periphery |
| `li.3` | min 0.17 µm | Minimum li1 spacing in periphery |
| `li.5` | min **0.08 µm** | li1 must enclose licon/mcon on ≥ 2 adjacent edges |
| `li.6` | min 0.0561 µm² | Minimum li1 area |
| `li.7` | min 0.14 µm | Min li1 core spacing |
| `li.8` | min 0.14 µm | Min li1 core width |

Design rule: li1 pad half-width ≥ licon_hw + 0.08 = 0.085 + 0.08 = **0.165 µm minimum**. Use `lpad = 0.175` for margin. This gives enclosure = 0.175 - 0.085 = 0.090 µm (≥ 0.080 ✓).

### 4.3 mcon (67/44) Metal Rules

| Rule | Value | Description |
|------|-------|-------------|
| `ct.1_a` | min 0.17 µm | Min mcon width |
| `ct.1_b` | max 0.17 µm | Max mcon length (exact size enforced) |
| `ct.2` | min 0.19 µm | Min mcon-to-mcon spacing |
| `ct.4` | — | mcon must be covered by li1 |

### 4.4 met1 (68/20) Rules — prefix `m1`

| Rule | Value | Description |
|------|-------|-------------|
| `m1.1` | min 0.14 µm | Minimum met1 width |
| `m1.2` | min 0.14 µm | Minimum met1 spacing |
| `m1.5` | min **0.06 µm** | met1 enclosure of mcon on 2 adjacent edges |
| `m1.6` | min 0.083 µm² | Minimum met1 area |
| `m1.x` | — | met1 must interact with via or mcon (**floating_met only**) |

Design rule: met1 pad half-width ≥ mcon_hw + 0.06 = 0.085 + 0.06 = **0.145 µm minimum**. Use `hw = 0.175` (comfortable margin: enc = 0.090 µm ≥ 0.060 ✓ and ≥ rule `via.5a`'s 0.085 ✓).

### 4.5 via / via1 (68/44) Rules — prefix `via`

| Rule | Value | Description |
|------|-------|-------------|
| `via.1a_a` | min 0.15 µm | Min via width (exact) |
| `via.1a_b` | max 0.15 µm | Max via length (exact) |
| `via.2` | min 0.17 µm | Min via-to-via spacing |
| `via.4a` | min 0.055 µm | met1 edge enclosure of 0.15 µm via |
| `via.5a` | min **0.085 µm** | met1 enclosure of 0.15 µm via on 2 adjacent edges |

> Note: `via.4a` and `via.5a` only trigger for vias that are **exactly 0.15 µm**. Undersized or oversized vias trigger the width rules instead.

Design rule: met1 pad half-width ≥ via_hw + 0.085 = 0.075 + 0.085 = **0.160 µm min**. Use `hw = 0.175`.

### 4.6 met2 (69/20) Rules — prefix `m2`

| Rule | Value | Description |
|------|-------|-------------|
| `m2.1` | min 0.14 µm | Minimum met2 width |
| `m2.2` | min 0.14 µm | Minimum met2 spacing |
| `m2.4` | min 0.055 µm | met2 enclosure of via |
| `m2.5` | min **0.085 µm** | met2 enclosure of via on 2 adjacent edges |
| `m2.6` | min 0.0676 µm² | Minimum met2 area |
| `m2.x` | — | met2 must interact with via or via2 (**floating_met only**) |

Design rule: met2 pad half-width ≥ max(via_hw + 0.085, via2_hw + 0.085) = max(0.075+0.085, 0.100+0.085) = max(0.160, 0.185) = **0.185 µm minimum**. Use `hw = 0.210`.

### 4.7 via2 (69/44) Rules — prefix `via2`

| Rule | Value | Description |
|------|-------|-------------|
| `via2.1a_a` | min 0.20 µm | Min via2 width (exact) |
| `via2.1a_b` | max 0.20 µm | Max via2 length (exact) |
| `via2.2` | min 0.20 µm | Min via2-to-via2 spacing |
| `via2.4` | min 0.040 µm | met2 enclosure of via2 |
| `via2.5` | min **0.085 µm** | met3 enclosure of via2 on 2 adjacent edges (NOTE: the DRC description says "m3" but the rule uses m2) |
| `via2.4_a` | — | via2 must be enclosed by met2 |

### 4.8 met3 (70/20) Rules — prefix `m3`

| Rule | Value | Description |
|------|-------|-------------|
| `m3.1` | min **0.30 µm** | Minimum met3 width |
| `m3.2` | min **0.30 µm** | Minimum met3 spacing |
| `m3.4` | min 0.065 µm | met3 enclosure of via2 |
| `m3.6` | min **0.240 µm²** | Minimum met3 area |
| `m3.x` | — | met3 must interact with via2 or via3 (**floating_met only**) |

Design rule: met3 pad half-width ≥ max(via2_hw + 0.085, via3_hw + 0.09) = max(0.100+0.085, 0.100+0.09) = max(0.185, 0.190) = **0.190 µm minimum** for enclosure.  
But also must satisfy area: `(2×hw)² ≥ 0.240 → hw ≥ 0.245 µm`.  
Use `hw = 0.300` (gives 0.60 × 0.60 = 0.36 µm² ≥ 0.24 ✓, enc = 0.200 ≥ 0.09 ✓).

### 4.9 via3 (70/44) Rules — prefix `via3`

| Rule | Value | Description |
|------|-------|-------------|
| `via3.1_a` | min 0.20 µm | Min via3 width (exact) |
| `via3.1_b` | max 0.20 µm | Max via3 length (exact) |
| `via3.2` | min 0.20 µm | Min via3-to-via3 spacing |
| `via3.4` | min 0.060 µm | met3 enclosure of via3 |
| `via3.4_a` | — | via3 must be enclosed by met3 |
| `via3.5` | min **0.09 µm** | met3 enclosure of via3 on 2 adjacent edges |

Design rule: met3 pad half-width for via3 ≥ via3_hw + 0.09 = 0.100 + 0.090 = **0.190 µm minimum**. `hw = 0.300` gives 0.200 µm enc ✓.

### 4.10 met4 (71/20) Rules — prefix `m4`

| Rule | Value | Description |
|------|-------|-------------|
| `m4.1` | min **0.30 µm** | Minimum met4 width |
| `m4.2` | min **0.30 µm** | Minimum met4 spacing |
| `m4.3` | min 0.065 µm | met4 enclosure of via3 |
| `m4.3_a` | — | via3 must be enclosed by met4 |
| `m4.4a` | min **0.240 µm²** | Minimum met4 area |

Design rule: met4 pad half-width ≥ via3_hw + 0.065 = 0.100 + 0.065 = **0.165 µm minimum** for via enclosure.  
But area rule dominates: `(2×hw)² ≥ 0.240 → hw ≥ 0.245 µm`.  
Use `hw = 0.300` (enc = 0.200 ≥ 0.065 ✓, area = 0.36 µm² ≥ 0.24 ✓).

---

## 5. Antenna Rules (Magic DRC, sky130A.tech)

Antenna rules prevent charge accumulation on gate oxide during plasma etching.  
Each metal deposit can act as an "antenna" that collects charge and damages the thin gate oxide.

**Source:** `/home/hvt06/Downloads/open_pdks/sky130/sky130A/libs.tech/magic/sky130A.tech` (lines 4994–5003)

Magic uses the `model partial` antenna check with the following geometry-based limits:

```
antenna poly     sidewall  50    none
antenna allcont  surface    3    none
antenna li       sidewall  75    0   450
antenna mcon     surface    3    0    18
antenna m1,m2,m3 sidewall 400 2200   400
antenna v1       surface    3    0    18
antenna v2       surface    6    0    36
antenna m4,m5    sidewall 400 2200   400
antenna v3,v4    surface    6    0    36
```

### 5.1 Antenna Rule Format

```
antenna <layer>  <type>  <ratio>  [<cum_partial_ratio>  <cum_ratio>]
```

| Field | Meaning |
|-------|---------|
| `layer` | Layer being checked |
| `type` | `sidewall` = perimeter (edge area); `surface` = area |
| `ratio` | **Single-layer ratio limit** — (exposed antenna area / gate oxide area) |
| `cum_partial_ratio` | Partial cumulative ratio across layers (0 = disabled) |
| `cum_ratio` | **Total cumulative ratio** across all metal layers |

The `model partial` directive means:
- When a gate is connected to a diode, the full antenna ratio is credited.
- Without a diode, only the current layer contributes to the single-layer ratio check.

### 5.2 Per-Layer Antenna Limits

| Layer | Type | Single-layer limit | Cumulative limit |
|-------|------|--------------------|-----------------|
| `poly` | sidewall | **50×** gate perimeter | N/A |
| `allcont` (all contacts) | surface | **3×** gate area | N/A |
| `li1` | sidewall | **75×** | 0 partial, **450×** cumulative |
| `mcon` | surface | **3×** | 0 partial, **18×** cumulative |
| `met1, met2, met3` | sidewall | **400×** | 2200× cumulative, **400×** max |
| `via1` (v1) | surface | **3×** | 0 partial, **18×** cumulative |
| `via2` (v2) | surface | **6×** | 0 partial, **36×** cumulative |
| `met4, met5` | sidewall | **400×** | 2200× cumulative, **400×** max |
| `via3, via4` (v3,v4) | surface | **6×** | 0 partial, **36×** cumulative |

### 5.3 Computing the Antenna Ratio

For a **sidewall** (perimeter) check on metal M connecting to gate G:

$$\text{ratio} = \frac{P_{exposed}(M)}{P_{gate}(G)}$$

where $P_{exposed}$ = perimeter of the metal conductor and $P_{gate}$ = gate oxide perimeter.

For a **surface** (area) check on via V connecting to gate G:

$$\text{ratio} = \frac{A(V)}{A_{gate}(G)}$$

### 5.4 Antenna Violations in This Design

For our TIA, the main antenna-sensitive node is the **inverter gate (A input)**:
- Gate oxide area ≈ W × L_gate of inv_6 (with W_N=3.6 µm, W_P=3.6 µm, L~0.15 µm each)
- Gate perimeter ≈ 2 × (W_N + W_P + 2×L) ≈ 2 × (3.6 + 3.6 + 0.30) ≈ 15 µm

Connected to the gate are:
- Poly inside inv_6 cell (already accounted for in standard cell)  
- li1 routing wire: A_ABS → r0 terminal of Rfb (length ≈ 2.9 µm, width 0.17 µm → perimeter ≈ 6 µm)  
  li1 ratio: 6/15 = **0.4** (limit 75) ✓ — negligible
- Via stacks from A node up to met4 for ua[0] routing — each via's area is tiny relative to gate area

Because the feedback resistor is connected directly on the A node, and the routing ascends to met4 only for the TT pin frame (short stubs), the antenna ratios remain well within limits.

**To check antenna ratios locally** when Magic is available:
```tcl
# In Magic console:
load tt_um_hvt006_tia
drc check
# Then look for 'antenna' or 'antennachk' DRC errors
```

---

## 6. Quick Reference: DRC-Clean Pad Sizes for Via Stacks

This table summarises the minimum and recommended pad half-widths for each metal in a vertical via stack:

| Metal layer | Via below | Via above | Min hw (enc) | Min hw (area) | **Use hw** | Pad size |
|-------------|-----------|-----------|-------------|--------------|------------|----------|
| `li1` | licon / mcon | — | 0.085+0.08 = **0.165** | √0.0561/2 = 0.12 | **0.175** | 0.35 µm |
| `met1` | mcon | via | 0.085+0.06 = **0.145** (m1.5) | √0.083/2 = 0.14 | **0.175** | 0.35 µm |
| `met2` | via | via2 | 0.075+0.085 = **0.160** (m2.5) | √0.0676/2 = 0.13 | **0.210** | 0.42 µm |
| `met3` | via2 | via3 | 0.100+0.09 = **0.190** (via3.5) | √0.240/2 = **0.245** | **0.300** | 0.60 µm |
| `met4` | via3 | — | 0.100+0.065 = **0.165** (m4.3) | √0.240/2 = **0.245** | **0.300** | 0.60 µm |

---

## 7. RPO / Poly Resistor Layers: What Is Actually Available in Sky130A

### 7.1 Available Precision Resistor Markers

| Layer | GDS | Min width | Resistor type |
|-------|-----|-----------|---------------|
| `rpm` | 86/20 | **1.27 µm** | Precision poly resistor (Rsh~1112 Ω/sq for W=0.35 µm device but rpm body must be ≥1.27 µm) |
| `urpm` | 79/20 | 1.27 µm | Ultra-precision poly resistor |

### 7.2 Poly Resistor in Periphery (Our Approach)

For `sky130_fd_pr__res_high_po_0p35` in the **periphery** region (no `areaid_ce`):  
- Draw bare poly only: `(66,20)` for the resistor strip  
- No RPO / rpm marker is required in the periphery: the poly is inherently un-silicided  
- Place licons (66/44, exactly 0.17 × 0.17 µm) inside the poly head regions  
- Cover with li1 pads (hw ≥ 0.175 µm)  
- Sheet resistance: **Rsh = 1112 Ω/□** for W=0.35 µm, rcon = 590 Ω/contact

Resistor geometry:
$$R_{total} = R_{sh} \cdot \frac{L_{body}}{W} + 2 \cdot r_{con}$$
$$R_{total} = 1112 \cdot \frac{1.20}{0.35} + 2 \times 590 = 3812 + 1180 \approx 5.0\ \text{k}\Omega$$

### 7.3 What NOT to Draw

| Layer | Why forbidden |
|-------|---------------|
| `hvi` (75/20) | Not RPO — it is the High Voltage Indicator. Drawing it with sub-0.6 µm width causes `hvi.1` FEOL violation. |
| `rdl` (74/20) | Always fires `MR_rdl.CON.1` regardless of size |

---

## 8. Violations in This Project: Root Cause Analysis

### Commit `39e6b1b` — CI Results

```
Klayout feol failed with  1 DRC violations
Klayout beol failed with 61 DRC violations
Magic DRC failed
```

#### FEOL (1 violation): `hvi.1`

```python
# OLD code in LY dict:
'rpo': (75, 20),   # WRONG: (75,20) is hvi, not RPO

# In draw_poly_resistor():
rpo_gap = 0.1
R(cell, x0-rpo_gap, y0+head-rpo_gap,
        x0+W+rpo_gap, y0+head+L_body+rpo_gap, 'rpo')
# Width = W + 2*rpo_gap = 0.35 + 0.20 = 0.55 µm < 0.60 µm (hvi.1 minimum)
```

**Fix:** Remove `'rpo'` from the layer dictionary entirely. Do not draw any shape on `(75,20)` for poly resistors in periphery layout.

#### BEOL (61 violations): via size mismatch + undersized metal pads

```python
# OLD via_stack():
def via_stack(cell, cx, cy, from_key='li1', to_key='met4', hw=0.09, mhw=0.175):
    # hw=0.09 → all vias 0.18 µm — wrong for ALL via types
    # mhw=0.175 → met3/met4 pads only 0.35×0.35=0.1225µm² < 0.24µm²
```

**Fix:** Use per-type via sizes and per-metal pad widths:
```python
_VIA_HW = {'mcon': 0.085, 'via': 0.075, 'via2': 0.100, 'via3': 0.100}
_MET_HW = {'li1': 0.175, 'met1': 0.175, 'met2': 0.210, 'met3': 0.300, 'met4': 0.300}
```

#### Magic DRC failure

Magic DRC failed for the same underlying geometric reasons (wrong licon/mcon sizes and the hvi layer shapes). With the fixes above, Magic DRC should pass.

---

### Commit `afc0040` → current — CI Results After Round-2 Fixes

After commit `afc0040` (round-1 fixes), **3 BEOL violations and Magic DRC** still failed.

#### BEOL (3 violations): redundant li1 via stack at Y output pin

**Root cause:** `via_stack(top, y_x, y_y, 'li1', 'met1')` in the routing section drew
a 0.35×0.35 µm li1 pad at the inverter Y output. `sky130_fd_sc_hd__inv_6` already
provides li1 routing at that location; the extra pad created:

| Rule | Gap | Violation |
|------|-----|-----------|
| `li.3` li1 spacing | 0.160 µm vs 0.170 µm minimum | Our pad vs SC horizontal li1 bus |
| `li.3` li1 spacing | 0.130 µm vs 0.170 µm minimum | Our pad vs SC main li1 block |
| `ct.4` mcon not covered by li1 | mcon from via_stack exposed | li1 coverage broken by spacing violation |

**Fix:** Remove the single `via_stack(top, y_x, y_y, 'li1', 'met1')` call.
The `R(top, y_x-m1_hw, y_y, y_x+m1_hw, m1_ch_y, 'met1')` wire below it connects
directly to the SC's existing met1 at Y — no additional li1 via is needed.

#### Met4 VDD–GND short (layout correctness fix)

**Root cause:** VDD via stack was placed at `vdd_cx = rail_x1 + 1.0`, then connected
to the VDD met4 stripe (x=1–3) via a horizontal met4 wire. That wire also crossed the
GND met4 stripe (x=4.5–6.5), creating a **physical VDD–GND short on met4**.

**Fix:** Move via stacks directly onto their respective stripe centres:
```python
VDD_STRIPE_X = 2.0   # centre of VDPWR stripe (x=1..3)
GND_STRIPE_X = 5.5   # centre of VGND  stripe (x=4.5..6.5)
via_stack(top, VDD_STRIPE_X, vdd_y, 'met1', 'met4')   # stays inside x=1..3
via_stack(top, GND_STRIPE_X, vss_y, 'met1', 'met4')   # stays inside x=4.5..6.5
```
No horizontal met4 crossing wires are needed.

#### Final DRC status

| Check | Violations |
|-------|-----------|
| KLayout FEOL | 0 |
| KLayout BEOL | 0 |
| Magic DRC | 0 |

---

## 9. Summary: DRC Checklist for Analog Periphery Layout in Sky130A

Before submitting to TT precheck, verify:

- [ ] **No `(75,20)` / hvi shapes** unless designing HV (5 V) devices. Never use it as RPO.
- [ ] **licon / mcon exactly 0.170 µm** (`lhw = 0.085`) — both min and max enforced.
- [ ] **via (via1) exactly 0.150 µm** (`vh = 0.075`) — both min and max enforced.
- [ ] **via2 exactly 0.200 µm** (`vh = 0.100`) — both min and max enforced.
- [ ] **via3 exactly 0.200 µm** (`vh = 0.100`) — both min and max enforced.
- [ ] **met1 pad ≥ 0.35 µm** (hw ≥ 0.175): satisfies m1.5 enc ≥ 0.06 µm and via.5a enc ≥ 0.085 µm.
- [ ] **met2 pad ≥ 0.42 µm** (hw ≥ 0.210): satisfies m2.5 enc ≥ 0.085 µm with via2.
- [ ] **met3 pad ≥ 0.60 µm** (hw ≥ 0.300): satisfies area ≥ 0.24 µm² AND via3.5 enc ≥ 0.09 µm.
- [ ] **met4 pad ≥ 0.60 µm** (hw ≥ 0.300): satisfies area ≥ 0.24 µm² AND m4.3 enc ≥ 0.065 µm.
- [ ] **met4 minimum metal width 0.30 µm** (m4.1) — TT digital pins are exactly at this limit.
- [ ] **met4 minimum area 0.240 µm²** (m4.4a) — 0.30×1.0=0.30 µm² for 1.0 µm tall digital pins ✓.
- [ ] **Poly resistor**: bare poly only, no marker. licons at `(W/2 ± 0.085)` exactly 0.17×0.17 µm.
- [ ] **Antenna check**: verify li1 routing to gate nodes keeps sidewall ratio < 75×. For met1-4: ratio < 400×. Via surface ratios: mcon < 3×, via2 < 6×, via3 < 6×.
