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

Key Sky130A GDS layers:

| Layer | GDS (layer, datatype) | Purpose |
|-------|----------------------|---------|
| diff | (65, 20) | N/P diffusion |
| poly | (66, 20) | Polysilicon gate |
| licon1 | (66, 44) | Local interconnect contact |
| li1 | (67, 20) | Local interconnect |
| mcon | (67, 44) | LI-to-Met1 via |
| met1 | (68, 20) | Metal 1 |
| via | (68, 44) | Met1-to-Met2 via |
| met2 | (69, 20) | Metal 2 |
| via2 | (69, 44) | Met2-to-Met3 via |
| met3 | (70, 20) | Metal 3 |
| via3 | (70, 44) | Met3-to-Met4 via |
| met4 | (71, 20) | Metal 4 (drawing) |
| met4 pin | (71, 16) | Metal 4 (pin marker) |
| met4 label | (71, 5) | Metal 4 (text label) |
| nsdm | (93, 44) | N+ select implant |
| npc | (95, 20) | Nitride poly cut |
| prbndry | (235, 4) | PR boundary |

#### GDS Requirements

1. **Cell name** must exactly match `top_module` from `info.yaml`
2. **Bounding box** must fit within your tile size
3. **All pins** must be on **met4** at the exact positions from the DEF template
4. **Pin rectangles** on both drawing (71,20) and pin (71,16) layers
5. **Pin labels** (TEXT elements) on label layer (71,5)
6. **Power stripes** on met4: minimum width 1.2µm, from y=5µm to y=220.76µm
7. **No met5** — metal 5 is reserved for TT routing
8. Save as `gds/<top_module>.gds`

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

#### Example GDS Script

See `generate_layout.py` in this repository for a complete working example.

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

## Step 9: Commit and Push

```bash
git add -A
git status  # review changes
git commit -m "Add analog design: <your project name>"
git push origin main
```

---

## Step 10: Check GitHub Actions

1. Go to your repository on GitHub
2. Click the **Actions** tab
3. Two workflows should run:
   - **gds** — validates GDS/LEF, runs precheck, builds viewer
   - **docs** — builds documentation page

If a workflow fails:
- Click the failed run to see logs
- Common issues:
  - Cell name mismatch between GDS, LEF, Verilog, and info.yaml
  - Missing pins in GDS or LEF
  - Bounding box exceeds tile size
  - Met5 usage (reserved for TT routing)
  - Floating digital output pins (must be tied to GND in Verilog)

---

## Checklist

- [ ] `info.yaml`: `top_module` starts with `tt_um_`, `tiles` set correctly, `analog_pins` count is right
- [ ] `src/project.v`: module name matches `top_module`, unused outputs tied to ground
- [ ] `gds/<top_module>.gds`: correct cell name, pins on met4, power stripes, no met5
- [ ] `lef/<top_module>.lef`: MACRO name matches, all pins defined, correct SIZE
- [ ] `docs/info.md`: all three sections filled in
- [ ] GitHub Actions: both `gds` and `docs` workflows pass

---

## Resources

- [TT Analog Specs](https://tinytapeout.com/specs/analog/)
- [TT FAQ](https://tinytapeout.com/faq/)
- [Sky130A PDK Docs](https://skywater-pdk.readthedocs.io/)
- [gdstk Documentation](https://heitzmann.github.io/gdstk/)
- [Magic VLSI](http://opencircuitdesign.com/magic/)
- [TT Discord Community](https://tinytapeout.com/discord)
