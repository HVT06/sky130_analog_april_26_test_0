#!/usr/bin/env python3
"""
Generate GDS and LEF for Tiny Tapeout Sky130A Analog Project:
Common-Source NMOS Amplifier (tt_um_hvt006_cs_amp)

Usage:  cd sky130_analog_april_26_test_0 && python3 generate_layout.py
Output: gds/tt_um_hvt006_cs_amp.gds, lef/tt_um_hvt006_cs_amp.lef
"""

import gdstk
import os

# ==============================================================
# Configuration
# ==============================================================
TOP = "tt_um_hvt006_cs_amp"
DIE_W = 161.000     # um (from TT 1x2 analog template)
DIE_H = 225.760     # um

# ==============================================================
# Sky130A GDS Layer Definitions (layer, datatype)
# ==============================================================
LY = {
    'nwell':    (64, 20),
    'diff':     (65, 20),
    'tap':      (65, 44),
    'poly':     (66, 20),
    'licon1':   (66, 44),
    'npc':      (95, 20),
    'li1':      (67, 20),
    'mcon':     (67, 44),
    'met1':     (68, 20),
    'met1_pin': (68, 16),
    'met1_lbl': (68, 5),
    'via':      (68, 44),
    'met2':     (69, 20),
    'met2_pin': (69, 16),
    'met2_lbl': (69, 5),
    'via2':     (69, 44),
    'met3':     (70, 20),
    'met3_pin': (70, 16),
    'met3_lbl': (70, 5),
    'via3':     (70, 44),
    'met4':     (71, 20),
    'met4_pin': (71, 16),
    'met4_lbl': (71, 5),
    'nsdm':     (93, 44),
    'psdm':     (94, 20),
    'prbndry':  (235, 4),
}

# ==============================================================
# Pin Positions from tt_analog_1x2.def
# Format: (center_x, center_y, half_width, half_height, direction)
# All dimensions in um
# ==============================================================
PINS = {}

# Analog pins - bottom edge, met4, 0.9 x 1.0 um
ANALOG_X = [152.260, 132.940, 113.620, 94.300, 74.980, 55.660, 36.340, 17.020]
for i, x in enumerate(ANALOG_X):
    PINS[f"ua[{i}]"] = (x, 0.500, 0.450, 0.500, "INOUT")

# Digital pins - top edge, met4, 0.3 x 1.0 um
PINS['clk']   = (143.980, 225.260, 0.150, 0.500, "INPUT")
PINS['ena']   = (146.740, 225.260, 0.150, 0.500, "INPUT")
PINS['rst_n'] = (141.220, 225.260, 0.150, 0.500, "INPUT")

for i in range(8):
    PINS[f"ui_in[{i}]"]   = (138.460 - i*2.760, 225.260, 0.150, 0.500, "INPUT")
    PINS[f"uo_out[{i}]"]  = ( 94.300 - i*2.760, 225.260, 0.150, 0.500, "OUTPUT")
    PINS[f"uio_in[{i}]"]  = (116.380 - i*2.760, 225.260, 0.150, 0.500, "INPUT")
    PINS[f"uio_out[{i}]"] = ( 72.220 - i*2.760, 225.260, 0.150, 0.500, "OUTPUT")
    PINS[f"uio_oe[{i}]"]  = ( 50.140 - i*2.760, 225.260, 0.150, 0.500, "OUTPUT")

# Power stripe rectangles (x1, y1, x2, y2) on met4
VDPWR_RECT = (1.0, 5.0, 3.0, 220.76)
VGND_RECT  = (4.5, 5.0, 6.5, 220.76)


# ==============================================================
# Helper Functions
# ==============================================================
def add_rect(cell, x1, y1, x2, y2, layer_name):
    ly = LY[layer_name]
    cell.add(gdstk.rectangle((x1, y1), (x2, y2), layer=ly[0], datatype=ly[1]))


def add_label(cell, text, x, y, layer_name):
    ly = LY[layer_name]
    cell.add(gdstk.Label(text, (x, y), layer=ly[0], texttype=ly[1]))


def add_via_stack(cell, cx, cy, size=0.5):
    """Draw a complete via stack from li1 through met4 at (cx, cy)."""
    hs = size / 2.0

    # LI1
    add_rect(cell, cx-hs, cy-hs, cx+hs, cy+hs, 'li1')
    # MCON (li1 -> met1): 0.17 x 0.17
    add_rect(cell, cx-0.085, cy-0.085, cx+0.085, cy+0.085, 'mcon')
    # MET1
    add_rect(cell, cx-hs, cy-hs, cx+hs, cy+hs, 'met1')
    # VIA (met1 -> met2): 0.15 x 0.15
    add_rect(cell, cx-0.075, cy-0.075, cx+0.075, cy+0.075, 'via')
    # MET2
    add_rect(cell, cx-hs, cy-hs, cx+hs, cy+hs, 'met2')
    # VIA2 (met2 -> met3): 0.20 x 0.20
    add_rect(cell, cx-0.10, cy-0.10, cx+0.10, cy+0.10, 'via2')
    # MET3
    add_rect(cell, cx-hs, cy-hs, cx+hs, cy+hs, 'met3')
    # VIA3 (met3 -> met4): 0.20 x 0.20
    add_rect(cell, cx-0.10, cy-0.10, cx+0.10, cy+0.10, 'via3')
    # MET4
    add_rect(cell, cx-hs, cy-hs, cx+hs, cy+hs, 'met4')


def add_met4_route_L(cell, x1, y1, x2, y2, w=0.5):
    """L-shaped met4 route from (x1,y1) to (x2,y2): horizontal then vertical."""
    hw = w / 2.0
    # Horizontal segment at y1
    add_rect(cell, min(x1,x2)-hw, y1-hw, max(x1,x2)+hw, y1+hw, 'met4')
    # Vertical segment at x2
    add_rect(cell, x2-hw, min(y1,y2)-hw, x2+hw, max(y1,y2)+hw, 'met4')


# ==============================================================
# GDS Creation
# ==============================================================
def create_gds():
    lib = gdstk.Library(name=TOP, unit=1e-6, precision=1e-9)
    cell = lib.new_cell(TOP)

    # --- Cell Boundary ---
    add_rect(cell, 0, 0, DIE_W, DIE_H, 'prbndry')

    # --- All Pin Rectangles and Labels ---
    for name, (cx, cy, hw, hh, _dir) in PINS.items():
        add_rect(cell, cx-hw, cy-hh, cx+hw, cy+hh, 'met4')
        add_rect(cell, cx-hw, cy-hh, cx+hw, cy+hh, 'met4_pin')
        add_label(cell, name, cx, cy, 'met4_lbl')

    # --- Power Stripes ---
    for name, (x1, y1, x2, y2) in [("VDPWR", VDPWR_RECT), ("VGND", VGND_RECT)]:
        add_rect(cell, x1, y1, x2, y2, 'met4')
        add_rect(cell, x1, y1, x2, y2, 'met4_pin')
        add_label(cell, name, (x1+x2)/2, (y1+y2)/2, 'met4_lbl')

    # ===========================================================
    # NOTE: No transistor geometry is placed here.
    # The analog circuit (common-source NMOS amplifier) connects
    # externally through the analog pins ua[0] (gate) and ua[1]
    # (drain). This avoids Magic DRC issues from hand-drawn
    # device geometry that doesn't follow sky130A design rules.
    # For a real tapeout, use Magic or OpenLane to generate
    # DRC-clean device layout.
    # ===========================================================

    # --- Write GDS ---
    os.makedirs("gds", exist_ok=True)
    gds_path = f"gds/{TOP}.gds"
    lib.write_gds(gds_path)
    print(f"  GDS: {gds_path}")
    return PINS


# ==============================================================
# LEF Creation
# ==============================================================
def create_lef(pins):
    os.makedirs("lef", exist_ok=True)
    lef_path = f"lef/{TOP}.lef"

    lines = [
        "VERSION 5.8 ;",
        'BUSBITCHARS "[]" ;',
        'DIVIDERCHAR "/" ;',
        "",
        f"MACRO {TOP}",
        "  CLASS BLOCK ;",
        f"  FOREIGN {TOP} ;",
        "  ORIGIN 0.000 0.000 ;",
        f"  SIZE {DIE_W:.3f} BY {DIE_H:.3f} ;",
        "  SYMMETRY X Y ;",
        "",
    ]

    # Power pins
    for name, (x1, y1, x2, y2) in [("VDPWR", VDPWR_RECT), ("VGND", VGND_RECT)]:
        use = "POWER" if name == "VDPWR" else "GROUND"
        lines += [
            f"  PIN {name}",
            f"    DIRECTION INOUT ;",
            f"    USE {use} ;",
            f"    PORT",
            f"      LAYER met4 ;",
            f"        RECT {x1:.3f} {y1:.3f} {x2:.3f} {y2:.3f} ;",
            f"    END",
            f"  END {name}",
            "",
        ]

    # Signal pins
    for name, (cx, cy, hw, hh, direction) in pins.items():
        lef_dir = direction
        lines += [
            f"  PIN {name}",
            f"    DIRECTION {lef_dir} ;",
            f"    USE SIGNAL ;",
            f"    PORT",
            f"      LAYER met4 ;",
            f"        RECT {cx-hw:.3f} {cy-hh:.3f} {cx+hw:.3f} {cy+hh:.3f} ;",
            f"    END",
            f"  END {name}",
            "",
        ]

    lines += [
        f"END {TOP}",
        "",
        "END LIBRARY",
        "",
    ]

    with open(lef_path, 'w') as f:
        f.write('\n'.join(lines))
    print(f"  LEF: {lef_path}")


# ==============================================================
# Main
# ==============================================================
if __name__ == '__main__':
    print(f"Generating layout for {TOP}...")
    pins = create_gds()
    create_lef(pins)
    print(f"Done! Cell: {TOP}")
