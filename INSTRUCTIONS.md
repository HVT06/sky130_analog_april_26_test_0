# Step-by-Step Instructions: Tiny Tapeout Sky130A Analog Project

This guide walks you through setting up, designing, and submitting a Tiny Tapeout analog project using the Sky130A PDK.

---

## Prerequisites

- **GitHub account** with Actions enabled
- **Python 3** with `gdstk` (`pip install gdstk`)
- **Git** installed locally
- Familiarity with analog IC layout concepts

---

## Step 1: Create Repository from Template

1. Go to the Tiny Tapeout analog template: https://github.com/TinyTapeout/tt10-analog-template
2. Click **"Use this template"** → **"Create a new repository"**
3. Name it (e.g., `tt10-my-analog-project`) and create
4. Clone it locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
   cd YOUR_REPO
   ```

> **⚠️ CRITICAL: Clone directly, do NOT nest repos!**
> Clone your repo into its own standalone directory. Do **not** clone it inside another git repository. If git detects a nested `.git` directory, it may register it as a **submodule** (a `160000` mode entry) without a `.gitmodules` file. This will cause GitHub Actions `actions/checkout` to fail with:
> ```
> fatal: No url found for submodule path '...' in .gitmodules
> ```
> If this happens, remove the submodule entry:
> ```bash
> git rm --cached path/to/nested_repo
> git commit -m "Remove stale submodule reference"
> git push
> ```

---

## Step 2: Choose Your Tile Size

Tiny Tapeout analog supports these tile sizes:

| Tiles | Width (µm) | Height (µm) | DEF Template |
|-------|-----------|------------|--------------|
| 1×2   | 161.000   | 225.760    | `tt_analog_1x2.def` |
| 2×2   | 334.880   | 225.760    | `tt_analog_2x2.def` |
| 3×2   | 508.760   | 225.760    | `tt_analog_3x2.def` |

Download the DEF template for reference:
```bash
wget https://raw.githubusercontent.com/TinyTapeout/tt-support-tools/tt10/def/analog/tt_analog_1x2.def
```

The DEF file defines:
- Die area (bounding box)
- All pin positions (analog + digital + power)
- Pin sizes and metal layers

---

## Step 3: Configure `info.yaml`

Edit `info.yaml` with your project details:

```yaml
project:
  title: "Your Project Title"
  author: "Your Name"
  description: "Brief description of your analog design"
  language: "Wokwi"          # keep as-is for analog
  clock_hz: 0                # set to 0 for analog-only designs
  tiles: "1x2"               # must match your chosen tile size
  analog_pins: 2             # number of analog pins used (max 8)
  top_module: "tt_um_YOURNAME_PROJECT"  # MUST start with tt_um_
```

### Naming Convention
The `top_module` name **must** start with `tt_um_`. Use your GitHub username to avoid collisions:
```
tt_um_<github_username>_<project_name>
```
Example: `tt_um_hvt006_cs_amp`

### Pinout Section
Define each pin's function under `pinout:`:
```yaml
pinout:
  ua[0]: "gate input"
  ua[1]: "drain output"
  # Only define pins you actually use
  # ua[2]-ua[7]: not connected
```

For unused digital outputs (`uo_out`, `uio_out`, `uio_oe`), write "not used" in the pinout. They **must** be tied to ground in the Verilog.

---

## Step 4: Update the Verilog Wrapper (`src/project.v`)

The Verilog file is a **black-box wrapper** for your analog cell. For pure analog designs:

1. Change the module name to match `top_module` in `info.yaml`
2. Tie all unused digital outputs to ground

```verilog
module tt_um_YOURNAME_PROJECT (
    input  wire [7:0] ui_in,
    output wire [7:0] uo_out,
    input  wire [7:0] uio_in,
    output wire [7:0] uio_out,
    output wire [7:0] uio_oe,
    inout  wire [7:0] ua,
    input  wire       ena,
    input  wire       clk,
    input  wire       rst_n,
    input  wire       VGND,
    input  wire       VDPWR
);
    // Tie unused digital outputs to ground
    assign uo_out  = 8'b0;
    assign uio_out = 8'b0;
    assign uio_oe  = 8'b0;
endmodule
```

---

## Step 5: Create the GDS Layout

### Option A: Python + gdstk (Recommended for Simple Designs)

This approach gives you full control over coordinates and layers.

```bash
pip install gdstk
```

Key Sky130A GDS layers (see also `docs/drc_rules.md` for full DRC constraints):

| Layer | GDS (layer, datatype) | Purpose | Key constraint |
|-------|----------------------|---------|----------------|
| diff | (65, 20) | N/P diffusion | min width 0.15 µm |
| poly | (66, 20) | Polysilicon gate | min width 0.15 µm |
| licon1 | (66, 44) | Local interconnect contact | **exactly 0.17×0.17 µm** |
| li1 | (67, 20) | Local interconnect | min width 0.17 µm |
| mcon | (67, 44) | LI-to-Met1 via | **exactly 0.17×0.17 µm** |
| met1 | (68, 20) | Metal 1 | min width 0.14 µm |
| via / via1 | (68, 44) | Met1-to-Met2 via | **exactly 0.15×0.15 µm** |
| met2 | (69, 20) | Metal 2 | min width 0.14 µm |
| via2 | (69, 44) | Met2-to-Met3 via | **exactly 0.20×0.20 µm** |
| met3 | (70, 20) | Metal 3 | min width **0.30 µm**, min area **0.24 µm²** |
| via3 | (70, 44) | Met3-to-Met4 via | **exactly 0.20×0.20 µm** |
| met4 | (71, 20) | Metal 4 (drawing) | min width **0.30 µm**, min area **0.24 µm²** |
| met4 pin | (71, 16) | Metal 4 (pin marker) | — |
| met4 label | (71, 5) | Metal 4 (text label) | — |
| nsdm | (93, 44) | N+ select implant | min width 0.38 µm |
| npc | (95, 20) | Nitride poly cut | min width 0.27 µm |
| prbndry | (235, 4) | PR boundary | — |
| **hvi** | **(75, 20)** | **High Voltage Indicator** — for 5 V devices | **min 0.60 µm** — NOT RPO/resistor marker |
| rpm | (86, 20) | Precision resistor poly mask | min 1.27 µm — rarely hand-drawn |

#### GDS Requirements

1. **Cell name** must exactly match `top_module` from `info.yaml`
2. **Bounding box** must fit within your tile size
3. **All pins** must be on **met4** at the exact positions from the DEF template
4. **Pin rectangles** on both drawing (71,20) and pin (71,16) layers
5. **Pin labels** (TEXT elements) on label layer (71,5)
6. **Power stripes** on met4: minimum width 1.2µm, from y=5µm to y=220.76µm
7. **No met5** — metal 5 is reserved for TT routing
8. **Analog pin stubs** — each analog pin declared in `analog_pins` **must** have adjacent metal connected to it (not just the pin rectangle). Add a met4 stub (e.g., 3µm extension) from each used analog pin into the cell area. Without this, the precheck fails with: `Analog pin ua[X] is not connected to any adjacent metal`
9. **Magic + KLayout DRC compliance** — if you draw device geometry (diff, poly, licon, vias) by hand, use correct PDK-mandated sizes. Wrong via sizes or misidentified layers (e.g., hvi vs RPO) will fail FEOL/BEOL. See `docs/drc_rules.md` for a full rule table.
10. Save as `gds/<top_module>.gds`

#### Pin Positions (1×2 tile)

**Analog pins** (bottom edge, 0.9 × 1.0 µm each):

| Pin | Center X (µm) | Center Y (µm) |
|-----|---------------|---------------|
| ua[0] | 152.260 | 0.500 |
| ua[1] | 132.940 | 0.500 |
| ua[2] | 113.620 | 0.500 |
| ua[3] | 94.300 | 0.500 |
| ua[4] | 74.980 | 0.500 |
| ua[5] | 55.660 | 0.500 |
| ua[6] | 36.340 | 0.500 |
| ua[7] | 17.020 | 0.500 |

**Digital pins** (top edge, 0.3 × 1.0 µm each):
- `clk`: x=143.980, `ena`: x=146.740, `rst_n`: x=141.220
- `ui_in[0..7]`: starting at x=138.460, stepping -2.760 µm
- `uio_in[0..7]`: starting at x=116.380, stepping -2.760 µm
- `uo_out[0..7]`: starting at x=94.300, stepping -2.760 µm
- `uio_out[0..7]`: starting at x=72.220, stepping -2.760 µm
- `uio_oe[0..7]`: starting at x=50.140, stepping -2.760 µm

All digital pins are at y=225.260 µm.

**Power stripes** (vertical on met4):
- VDPWR: x = 1.0 to 3.0 µm, y = 5.0 to 220.76 µm
- VGND: x = 4.5 to 6.5 µm, y = 5.0 to 220.76 µm

#### Analog Pin Stub Example

For each used analog pin, extend a met4 rectangle from the pin into the cell:

```python
# For pins ua[0] and ua[1] (analog_pins = 2)
for i in range(2):
    cx, cy, hw, hh = pin_positions[f"ua[{i}]"]
    # Met4 stub: same width as pin, extending 3um upward from top edge
    add_rect(cell, cx - hw, cy + hh, cx + hw, cy + hh + 3.0, 'met4')
```

This ensures the precheck sees metal connected to each declared analog pin.

#### Example GDS Script

See `generate_layout.py` in this repository for a complete working example that generates a DRC-clean GDS with all pins, power stripes, boundary, and analog pin stubs.

### Option B: Magic VLSI (For Complex Designs)

If you have sky130A set up with Magic:

```bash
export PDKPATH=/path/to/sky130A
magic -dnull -noconsole -rcfile $PDKPATH/libs.tech/magic/sky130A.magicrc << 'EOF'
def read tt_analog_1x2.def
cellname rename tt_um_template tt_um_YOUR_CELL

# Draw power stripes
box 1um 5um 1um 220.76um
box width 2um
paint met4
label VDPWR FreeSans 16 0 0 0 c met4
port make
port use power
port class bidirectional

# ... add your layout here ...

save tt_um_YOUR_CELL
file mkdir gds
gds write gds/tt_um_YOUR_CELL.gds
file mkdir lef
lef write lef/tt_um_YOUR_CELL.lef -hide -pinonly
quit -noprompt
EOF
```

---

## Step 6: Create the LEF File

The LEF file tells the TT integration tools where your pins are. It must include:
- `MACRO` name matching the GDS cell
- `SIZE` matching the die area
- `PIN` definitions for all ports (power + signal + analog)

Save as `lef/<top_module>.lef`.

See `generate_layout.py` for programmatic LEF generation, or use Magic's `lef write -hide -pinonly`.

### LEF Template

```lef
VERSION 5.8 ;
BUSBITCHARS "[]" ;
DIVIDERCHAR "/" ;

MACRO tt_um_YOUR_CELL
  CLASS BLOCK ;
  FOREIGN tt_um_YOUR_CELL ;
  ORIGIN 0.000 0.000 ;
  SIZE 161.000 BY 225.760 ;
  SYMMETRY X Y ;

  PIN VDPWR
    DIRECTION INOUT ;
    USE POWER ;
    PORT
      LAYER met4 ;
        RECT 1.000 5.000 3.000 220.760 ;
    END
  END VDPWR

  PIN VGND
    DIRECTION INOUT ;
    USE GROUND ;
    PORT
      LAYER met4 ;
        RECT 4.500 5.000 6.500 220.760 ;
    END
  END VGND

  PIN ua[0]
    DIRECTION INOUT ;
    USE SIGNAL ;
    PORT
      LAYER met4 ;
        RECT 151.810 0.000 152.710 1.000 ;
    END
  END ua[0]

  ... (all other pins) ...

END tt_um_YOUR_CELL
END LIBRARY
```

---

## Step 7: Write Documentation (`docs/info.md`)

Fill in these three sections:

```markdown
## How it works

Describe your circuit: topology, transistor sizing, expected gain/bandwidth, etc.

## How to test

Step-by-step instructions for testing on the TT demo board.

## External hardware

List external components needed (resistors, signal generator, etc.).
```

---

## Step 8: Verify Locally

Before pushing, check:

```bash
# 1. File structure
ls gds/*.gds lef/*.lef src/project.v docs/info.md info.yaml

# 2. Verify GDS cell name (requires gdstk)
python3 -c "
import gdstk
lib = gdstk.read_gds('gds/tt_um_YOUR_CELL.gds')
c = lib.top_level()[0]
print(f'Cell: {c.name}')
print(f'BBox: {c.bounding_box()}')
print(f'Polygons: {len(c.polygons)}')
print(f'Labels: {len(c.labels)}')
"

# 3. Check Verilog module name matches info.yaml top_module
grep 'module tt_um_' src/project.v
grep 'top_module' info.yaml

# 4. Check LEF MACRO name
head -10 lef/*.lef
```

---

## Step 9: Enable GitHub Pages

**Before pushing**, enable GitHub Pages so the viewer workflow can deploy:

1. Go to `https://github.com/YOUR_USERNAME/YOUR_REPO/settings/pages`
2. Under **Build and deployment → Source**, select **GitHub Actions**
3. Click **Save**

> **⚠️ If you skip this, the viewer step will fail with:**
> ```
> Error: Failed to create deployment (status: 404)
> ```
> You can enable Pages after the fact and re-run the failed workflow.

---

## Step 10: Commit and Push

```bash
git add -A
git status  # review changes
git commit -m "Add analog design: <your project name>"
git push origin main
```

---

## Step 11: Check GitHub Actions

1. Go to your repository on GitHub
2. Click the **Actions** tab
3. Two workflows should run:
   - **gds** — validates GDS/LEF, runs precheck, builds viewer
   - **docs** — builds documentation page

### Troubleshooting Common Failures

| Error | Cause | Fix |
|-------|-------|-----|
| `fatal: No url found for submodule path '...' in .gitmodules` | Repo was cloned inside another git repo, creating a phantom submodule | `git rm --cached <path>` then commit and push |
| `Magic DRC failed` | Via/cut sizes wrong, or (75,20)/hvi marker drawn with wrong width | See `docs/drc_rules.md`. Fix: use exact via sizes (mcon=0.17, via=0.15, via2/3=0.20 µm) and correct metal pad widths (met3/met4 pad ≥ 0.60 µm for area rule). Do NOT draw on layer (75,20) = hvi for poly resistors. |
| `Klayout feol failed with 1 DRC violations` | Layer (75,20) drawn with width < 0.60 µm — (75,20) is `hvi` (High Voltage Indicator), not RPO | Never use (75,20) for poly resistors. Periphery poly-resistors need bare poly only — no marker layer. See `docs/drc_rules.md§3.6`. |
| `Klayout beol failed with N DRC violations` | Via/cut sizes not exactly matching sky130A rules, or metal pads too small for area/enclosure rules | Use per-type via sizes: `mcon=0.17, via=0.15, via2=0.20, via3=0.20 µm`. Metal pads: met3/met4 ≥ 0.60×0.60 µm (area 0.36 µm² ≥ 0.24 µm²). Full table in `docs/drc_rules.md§6`. |
| `Analog pin ua[X] is not connected to any adjacent metal` | Analog pin declared in `info.yaml` but no metal extends from it in GDS | Add met4 stubs (≥3µm) extending from each used analog pin into the cell |
| `Failed to create deployment (status: 404)` | GitHub Pages not enabled | Go to repo Settings → Pages → Source: **GitHub Actions** |
| Cell name mismatch | `top_module` in info.yaml ≠ module name in project.v ≠ cell name in GDS ≠ MACRO in LEF | Ensure all four match exactly |
| Missing pins in GDS or LEF | Pin rectangles or labels missing for some ports | Include all 51 signal pins + 2 power pins from DEF template |
| Bounding box exceeds tile size | Layout extends beyond (161.000, 225.760) for 1×2 | Check prbndry and ensure all geometry is within bounds |
| Met5 usage | Metal 5 shapes in GDS | Remove all met5; it's reserved for TT top-level routing |
| Floating digital outputs | `uo_out`, `uio_out`, `uio_oe` not driven in Verilog | Add `assign uo_out = 8'b0; assign uio_out = 8'b0; assign uio_oe = 8'b0;` |

---

## Pre-Push Checklist

Run through **every item** before pushing. Each corresponds to a real CI failure we've encountered:

### Repository Setup
- [ ] Repo is **not** nested inside another git repo (no phantom submodules)
- [ ] No `Downloads/` or other stray directories committed to the repo
- [ ] GitHub Pages enabled: Settings → Pages → Source: **GitHub Actions**

### info.yaml
- [ ] `top_module` starts with `tt_um_` and matches Verilog module name exactly
- [ ] `tiles` set correctly (e.g., `"1x2"`)
- [ ] `analog_pins` matches the actual number of analog pins with metal stubs in GDS
- [ ] `clock_hz: 0` for analog-only designs

### src/project.v
- [ ] Module name matches `top_module` from `info.yaml` exactly
- [ ] All unused digital outputs tied to ground: `assign uo_out = 8'b0; assign uio_out = 8'b0; assign uio_oe = 8'b0;`

### GDS (`gds/<top_module>.gds`)
- [ ] Cell name matches `top_module` exactly
- [ ] Bounding box within tile size (161.000 × 225.760 µm for 1×2)
- [ ] All 51 signal pins + 2 power pins present on met4 at DEF positions
- [ ] Pin rectangles on BOTH met4 drawing (71,20) AND met4 pin (71,16) layers
- [ ] Pin labels on met4 label layer (71,5)
- [ ] Power stripes (VDPWR, VGND) on met4, min 1.2µm wide
- [ ] **Met4 stubs on every used analog pin** (extends ≥3µm from pin into cell)
- [ ] **No met5** shapes anywhere
- [ ] **No hand-drawn device geometry** (diff, poly, contacts) unless DRC-verified with Magic
- [ ] Only layers used: met4 (71,20), met4_pin (71,16), met4_lbl (71,5), prbndry (235,4)

### LEF (`lef/<top_module>.lef`)
- [ ] MACRO name matches `top_module` exactly
- [ ] SIZE matches die area (161.000 BY 225.760 for 1×2)
- [ ] All power + signal pins defined with correct RECT coordinates

### Documentation
- [ ] `docs/info.md`: all three sections filled in (How it works, How to test, External hardware)

### Quick Verification Commands
```bash
# Run all checks in one shot:
echo "=== Files ==="
ls gds/*.gds lef/*.lef src/project.v docs/info.md info.yaml

echo "=== Name consistency ==="
grep 'top_module' info.yaml
grep '^module ' src/project.v
head -8 lef/*.lef | grep MACRO

echo "=== GDS check ==="
python3 -c "
import gdstk
lib = gdstk.read_gds('gds/$(grep top_module info.yaml | sed 's/.*"\(.*\)".*/\1/').gds')
c = lib.top_level()[0]
bb = c.bounding_box()
print(f'Cell: {c.name}')
print(f'BBox: ({bb[0][0]:.3f},{bb[0][1]:.3f}) to ({bb[1][0]:.3f},{bb[1][1]:.3f})')
print(f'Polygons: {len(c.polygons)}, Labels: {len(c.labels)}')
layers = sorted(set((p.layer, p.datatype) for p in c.polygons))
print(f'Layers: {layers}')
for ly, dt in layers:
    if ly == 72: print('ERROR: met5 detected!')
    if ly in (65,66,67) and dt == 20: print(f'WARNING: device layer ({ly},{dt}) may cause Magic DRC failure')
"

echo "=== Submodule check ==="
git ls-files --stage | grep '^160000' && echo 'ERROR: submodule entries found!' || echo 'OK: no submodules'
```

---

## Resources

- [TT Analog Specs](https://tinytapeout.com/specs/analog/)
- [TT FAQ](https://tinytapeout.com/faq/)
- [Sky130A PDK Docs](https://skywater-pdk.readthedocs.io/)
- [gdstk Documentation](https://heitzmann.github.io/gdstk/)
- [Magic VLSI](http://opencircuitdesign.com/magic/)
- [TT Discord Community](https://tinytapeout.com/discord)
