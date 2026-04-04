#!/usr/bin/env python3
"""
Inverter-Based TIA -- Full-Layer Layout Generator
Sky130A open_pdks / Tiny Tapeout 1x2 analog tile

Strategy
--------
* CMOS inverter: sky130_fd_sc_hd__inv_6 standard cell embedded by reference.
  Contains all device layers: nwell(64), diff(65), poly(66), licon(66,44),
  li1(67), mcon(67,44), met1(68), nsdm(93), psdm(94), boundary etc.
  Flanked by tapvpwrvgnd_1 cells for substrate/well taps.

* Feedback resistor Rfb=5kOhm: poly high-ohm (RPO) resistor drawn manually:
  poly(66,20) + RPO(75,20) + licon(66,44) contacts + li1(67,20) terminals.
  Rsh=1112 Ohm/sq, W=0.35um, L_body=1.20um => R~5kOhm.

* Routing: li1 -> mcon -> met1 -> via -> met2 -> via2 -> met3 -> via3 -> met4
* TT pin frame on met4: all analog + digital + power pins at exact DEF positions.
* SVG export: one SVG per layer + combined layered SVG.

Usage: python3 generate_layout.py
"""

import gdstk, os, math, colorsys

# ============================================================
# Sky130A layer map
# ============================================================
LY = {
    'nwell':    (64, 20),  'nwell_pin':(64,16),
    'diff':     (65, 20),
    'poly':     (66, 20),
    'licon':    (66, 44),  # local interconnect contact cut (exact size 0.17um)
    'li1':      (67, 20),  'li1_pin': (67,16), 'li1_lbl': (67,5),
    'mcon':     (67, 44),  # li1-to-met1 via (exact size 0.17um)
    'met1':     (68, 20),  'met1_pin':(68,16),
    'via':      (68, 44),  # met1-to-met2 via (exact size 0.15um)
    'met2':     (69, 20),  'met2_pin':(69,16),
    'via2':     (69, 44),  # met2-to-met3 via (exact size 0.20um)
    'met3':     (70, 20),  'met3_pin':(70,16),
    'via3':     (70, 44),  # met3-to-met4 via (exact size 0.20um)
    'met4':     (71, 20),  'met4_pin':(71,16), 'met4_lbl':(71,5),
    # hvi (75,20) = High Voltage Indicator: min width 0.6um, DO NOT use for poly resistors
    # rpm (86,20) = Resistor Poly Mask: min width 1.27um, too wide for 0.35um resistor body
    # For sky130_fd_pr__res_high_po_0p35: bare poly (no marker) is correct in periphery
    'nsdm':     (93, 44),  # n+ source/drain mask
    'psdm':     (94, 20),  # p+ source/drain mask
    'npc':      (95, 20),  # n+ poly contact (encloses poly licons in areaid_ce core)
    'prbndry':  (235,  4), # PR boundary
}

# Layer rendering colours for SVG (layer_key: '#rrggbb')
LAYER_COLORS = {
    'nwell':  '#c0e0ff',
    'diff':   '#90ee90',
    'poly':   '#ff6060',
    'licon':  '#b060b0',
    'li1':    '#ffa0a0',
    'mcon':   '#808040',
    'met1':   '#6060ff',
    'via':    '#404080',
    'met2':   '#a0c0ff',
    'via2':   '#305090',
    'met3':   '#ffd700',
    'via3':   '#a08000',
    'met4':   '#ff8c00',
    'nsdm':   '#00cc00',
    'psdm':   '#cc8800',
    'prbndry':'#888888',
}

# ============================================================
# Project constants
# ============================================================
TOP   = 'tt_um_hvt006_tia'
DIE_W = 161.000
DIE_H = 225.760
SC_GDS = ('/home/hvt06/Downloads/open_pdks/sky130/sky130A/libs.ref/'
          'sky130_fd_sc_hd/gds/sky130_fd_sc_hd.gds')

# Standard cells to embed
INV_NAME = 'sky130_fd_sc_hd__inv_6'    # W_N~2.1um, W_P~4.2um (closest to 2/4um)
TAP_NAME = 'sky130_fd_sc_hd__tapvpwrvgnd_1'

# Cell bounding box offsets (the bbox starts at -0.19,-0.24 for all hd cells)
CELL_OX = 0.190  # bbox left to cell origin
CELL_OY = 0.240  # bbox bottom to cell origin
INV6_W  = 3.600  # bbox width of inv_6
INV6_H  = 3.200  # bbox height (2.96-(-0.24))
TAP_W   = 0.840

# inv_6 pin positions RELATIVE to cell origin (from GDS labels)
INV6_A_REL  = (0.23,  1.19)   # A input (gate) - first occurrence
INV6_Y_REL  = (2.95,  1.19)   # Y output
INV6_VPW_REL= (0.23,  2.72)   # VPWR met1 rail
INV6_VGN_REL= (0.23,  0.0)    # VGND met1 rail

# Placement: cell row base (bbox bottom-left y)
Y_BASE   = 30.000   # cells placed at y=30us (bbox bottom)
X_TAP1   = 77.000   # left tap bbox-left
X_INV    = X_TAP1 + TAP_W          # inv bbox-left = 77.84
X_TAP2   = X_INV + INV6_W          # right tap bbox-left = 81.44

# Absolute pin positions
def abs_pin(cell_bbox_x, cell_bbox_y, rel_x, rel_y):
    """Convert PDK-relative pin pos to absolute die coords."""
    ox = cell_bbox_x + CELL_OX
    oy = cell_bbox_y + CELL_OY
    return (ox + rel_x, oy + rel_y)

A_ABS   = abs_pin(X_INV, Y_BASE, *INV6_A_REL)    # ~(78.26, 31.43)
Y_ABS   = abs_pin(X_INV, Y_BASE, *INV6_Y_REL)    # ~(81.00, 31.43)
VPW_ABS = abs_pin(X_INV, Y_BASE, *INV6_VPW_REL)  # ~(78.26, 32.96)
VGN_ABS = abs_pin(X_INV, Y_BASE, *INV6_VGN_REL)  # ~(78.26, 30.24)

# TT pin positions
ANALOG_X = [152.260, 132.940, 113.620, 94.300, 74.980, 55.660, 36.340, 17.020]
ANALOG_PIN_USED = 2  # ua[0]=Iin, ua[1]=Vout

DIGITAL_PINS = {}
DIGITAL_PINS['clk']   = (143.980, 225.260)
DIGITAL_PINS['ena']   = (146.740, 225.260)
DIGITAL_PINS['rst_n'] = (141.220, 225.260)
for _i in range(8):
    DIGITAL_PINS[f'ui_in[{_i}]']   = (138.460 - _i*2.760, 225.260)
    DIGITAL_PINS[f'uo_out[{_i}]']  = ( 94.300 - _i*2.760, 225.260)
    DIGITAL_PINS[f'uio_in[{_i}]']  = (116.380 - _i*2.760, 225.260)
    DIGITAL_PINS[f'uio_out[{_i}]'] = ( 72.220 - _i*2.760, 225.260)
    DIGITAL_PINS[f'uio_oe[{_i}]']  = ( 50.140 - _i*2.760, 225.260)

VDPWR_RECT = (1.0, 5.0, 3.0, 220.76)   # VDD met4 stripe
VGND_RECT  = (4.5, 5.0, 6.5, 220.76)   # GND met4 stripe

# ============================================================
# Primitive drawing helpers
# ============================================================

def R(cell, x1, y1, x2, y2, layer_key):
    """Add a filled rectangle on the given layer."""
    ly = LY[layer_key]
    cell.add(gdstk.rectangle((x1, y1), (x2, y2), layer=ly[0], datatype=ly[1]))

def L(cell, text, x, y, layer_key):
    ly = LY[layer_key]
    cell.add(gdstk.Label(text, (x, y), layer=ly[0], texttype=ly[1]))

# ----------------------------------------------------------------
# Exact via/cut sizes required by sky130A DRC (sky130A_mr.drc):
#   mcon (67/44): 0.17 x 0.17 um  (ct.1_a min=0.17, ct.1_b max=0.17)
#   via  (68/44): 0.15 x 0.15 um  (via.1a_a min=0.15, via.1a_b max=0.15)
#   via2 (69/44): 0.20 x 0.20 um  (via2.1a_a min=0.20, via2.1a_b max=0.20)
#   via3 (70/44): 0.20 x 0.20 um  (via3.1_a min=0.20, via3.1_b max=0.20)
# Metal pad half-widths satisfy enclosure rules AND minimum area rules:
#   li1  (0.17 min): li.5 enc of licon/mcon >=0.08um adj  -> hw=0.175
#   met1 (0.14 min): via.5a enc of via >=0.085um adj      -> hw=0.175  (enc=0.10)
#   met2 (0.14 min): via2.5 enc of via2 >=0.085um adj     -> hw=0.210  (enc=0.11)
#   met3 (0.30 min): area>=0.24um^2; via3.5 encl>=0.09um  -> hw=0.300  (0.6x0.6=0.36um^2)
#   met4 (0.30 min): area>=0.24um^2; m4.3 encl>=0.065um   -> hw=0.300  (0.6x0.6=0.36um^2)
# ----------------------------------------------------------------
_VIA_HW  = {'mcon': 0.085, 'via': 0.075, 'via2': 0.100, 'via3': 0.100}
_MET_HW  = {'li1': 0.175, 'met1': 0.175, 'met2': 0.210, 'met3': 0.300, 'met4': 0.300}

def via_stack(cell, cx, cy, from_key='li1', to_key='met4'):
    """
    Draw a DRC-clean via/cut stack at (cx,cy) from from_key to to_key.
    Uses per-type exact via sizes and per-layer metal pad half-widths
    from _VIA_HW/_MET_HW to satisfy all sky130A BEOL DRC rules.
    """
    layers_order = ['li1', 'met1', 'met2', 'met3', 'met4']
    via_info = [
        ('mcon', 'met1'),   # li1  -> met1
        ('via',  'met2'),   # met1 -> met2
        ('via2', 'met3'),   # met2 -> met3
        ('via3', 'met4'),   # met3 -> met4
    ]
    si = layers_order.index(from_key)
    ei = layers_order.index(to_key)

    # Bottom metal pad
    hw = _MET_HW[from_key]
    R(cell, cx-hw, cy-hw, cx+hw, cy+hw, from_key)
    for idx, (via_key, upper_metal) in enumerate(via_info):
        if idx < si or idx >= ei:
            continue
        vh = _VIA_HW[via_key]
        R(cell, cx-vh, cy-vh, cx+vh, cy+vh, via_key)
        hw = _MET_HW[upper_metal]
        R(cell, cx-hw, cy-hw, cx+hw, cy+hw, upper_metal)

def met1_wire(cell, x1, y1, x2, y2, w=0.28):
    """Horizontal or L-shaped met1 wire between two points."""
    hw = w / 2.0
    if abs(x2 - x1) < 1e-6:
        R(cell, x1-hw, min(y1,y2), x1+hw, max(y1,y2), 'met1')
    elif abs(y2 - y1) < 1e-6:
        R(cell, min(x1,x2), y1-hw, max(x1,x2), y1+hw, 'met1')
    else:
        # L-bend: horizontal first then vertical
        R(cell, min(x1,x2), y1-hw, max(x1,x2)+hw, y1+hw, 'met1')
        R(cell, x2-hw, min(y1,y2), x2+hw, max(y1,y2)+hw, 'met1')

def met4_wire(cell, x1, y1, x2, y2, w=0.5):
    """Vertical met4 wire."""
    hw = w / 2.0
    if abs(x2 - x1) < 1e-6:
        R(cell, x1-hw, min(y1,y2), x1+hw, max(y1,y2), 'met4')
    elif abs(y2 - y1) < 1e-6:
        R(cell, min(x1,x2), y1-hw, max(x1,x2), y1+hw, 'met4')
    else:
        R(cell, min(x1,x2), y1-hw, max(x1,x2)+hw, y1+hw, 'met4')
        R(cell, x2-hw, min(y1,y2)-hw, x2+hw, max(y1,y2)+hw, 'met4')

# ============================================================
# Poly high-ohm resistor (RPO)
# ============================================================

def draw_poly_resistor(cell, x0, y0, W=0.35, L_body=1.20, head=0.35):
    """
    Draw sky130_fd_pr__res_high_po style poly resistor.
    Rsh=1112 Ohm/sq, Rcon=590 Ohm/contact => 5 kOhm total.
    Orientation: vertical (poly runs in Y direction).

    Structure (bottom to top):
      [li1 pad] -- [licon (0.17x0.17)] -- [poly head (y0..y0+head)] --
      [poly body (y0+head .. y0+head+L_body)] --
      [poly head (y0+head+L_body .. y0+2*head+L_body)] -- [licon] -- [li1 pad]

    NOTE: No special resistor marker layer is drawn here.
    sky130 (75,20) = hvi (High Voltage Indicator, min width 0.6um) -- NOT RPO.
    sky130 (86,20) = rpm (Resistor Poly Mask, min width 1.27um) -- too wide.
    For periphery layout, bare poly without marker layers is correct; the high
    sheet resistance (Rsh~1112 Ohm/sq) comes from the un-silicided poly nature
    of sky130_fd_pr__res_high_po_0p35.
    licon size: exactly 0.17x0.17um (licon.1 rule: min/max = 0.17um).

    Returns: (r0_x, r0_y), (r1_x, r1_y) -- li1 pad centres at each terminal.
    """
    # Poly strip (entire length = 2*head + L_body)
    total_L = head + L_body + head
    R(cell, x0, y0, x0+W, y0+total_L, 'poly')

    # licon contacts: exactly 0.17x0.17um centred in each poly head
    lhw = 0.085  # half of 0.17um
    r0x = x0 + W / 2.0
    r0y = y0 + head / 2.0
    R(cell, r0x-lhw, r0y-lhw, r0x+lhw, r0y+lhw, 'licon')

    r1x = x0 + W / 2.0
    r1y = y0 + head + L_body + head / 2.0
    R(cell, r1x-lhw, r1y-lhw, r1x+lhw, r1y+lhw, 'licon')

    # li1 landing pads (0.35x0.35um) enclosing each licon
    # li.5: li1 must enclose licon by >=0.08um on 2 adjacent edges
    # lpad=0.175 => enclosure = 0.175-0.085 = 0.090um >= 0.08 ✓
    lpad = 0.175
    R(cell, r0x-lpad, r0y-lpad, r0x+lpad, r0y+lpad, 'li1')
    R(cell, r1x-lpad, r1y-lpad, r1x+lpad, r1y+lpad, 'li1')

    return (r0x, r0y), (r1x, r1y)


# ============================================================
# Main layout generation
# ============================================================

def main():
    print('Loading sky130_fd_sc_hd standard cell library...')
    sc_lib   = gdstk.read_gds(SC_GDS)
    sc_cells = {c.name: c for c in sc_lib.cells}

    # Create output library.  Reference the standard cells hierarchically
    # so ALL their device layers (diff, poly, licon, li1, nwell...) are present.
    lib = gdstk.Library(name=TOP, unit=1e-6, precision=1e-9)

    # Flatten the standard cells so only geometry is embedded (no sub-cell refs).
    # This keeps the output GDS compact — only inv_6 + tapvpwrvgnd_1, not all 446 cells.
    inv_src = sc_cells[INV_NAME]
    tap_src = sc_cells[TAP_NAME]
    # gdstk: a Cell.copy() with deep=True recursively copies all sub-cells
    # then flatten() embeds those sub-cells' polygons directly.
    inv_flat = gdstk.Cell(INV_NAME)
    for poly in inv_src.get_polygons(depth=None):
        inv_flat.add(poly)
    for path in inv_src.get_paths(depth=None):
        inv_flat.add(path)
    tap_flat = gdstk.Cell(TAP_NAME)
    for poly in tap_src.get_polygons(depth=None):
        tap_flat.add(poly)
    for path in tap_src.get_paths(depth=None):
        tap_flat.add(path)
    lib.add(inv_flat, tap_flat)

    top = lib.new_cell(TOP)

    # ---- PR boundary ----
    R(top, 0, 0, DIE_W, DIE_H, 'prbndry')

    # ================================================================
    # 1. Standard cell placement (by GDS reference; all device layers included)
    # ================================================================
    # Cell origin = (bbox_left + CELL_OX, bbox_bot + CELL_OY)
    def place_cell(cell_name, bbox_x, bbox_y, mirror_y=False):
        ox = bbox_x + CELL_OX
        oy = bbox_y + CELL_OY
        ref = gdstk.Reference(cell_name, origin=(ox, oy))
        if mirror_y:
            ref.x_reflection = True
        top.add(ref)
        print(f'  Placed {cell_name} at origin=({ox:.3f},{oy:.3f})')

    place_cell(TAP_NAME, X_TAP1, Y_BASE)
    place_cell(INV_NAME, X_INV,  Y_BASE)
    place_cell(TAP_NAME, X_TAP2, Y_BASE)

    # Power rails (met1, extended from taps through inv cell)
    rail_x1 = X_TAP1 - 0.1
    rail_x2 = X_TAP2 + TAP_W + 0.1
    rail_hw  = 0.24
    # VDD met1 rail
    R(top, rail_x1, VPW_ABS[1]-rail_hw, rail_x2, VPW_ABS[1]+rail_hw, 'met1')
    # GND met1 rail
    R(top, rail_x1, VGN_ABS[1]-rail_hw, rail_x2, VGN_ABS[1]+rail_hw, 'met1')

    # ================================================================
    # 2. Poly high-ohm resistor Rfb = 5 kOhm
    #    Position: just above standard cells, between A and Y nodes
    # ================================================================
    RES_X = A_ABS[0] - 0.175   # horizontally aligned with A pin
    RES_Y = Y_BASE + INV6_H + 1.0  # 1 um above cell top
    W_RES = 0.35
    L_BODY = 1.20    # 1.20 um body => R ~ 1112*1.20/0.35 + 2*590 ~ 4999 Ohm
    HEAD   = 0.35

    r0_pos, r1_pos = draw_poly_resistor(top, RES_X, RES_Y, W_RES, L_BODY, HEAD)
    print(f'  Poly resistor: r0={r0_pos}, r1={r1_pos}')

    # ================================================================
    # 3. Internal routing: connect A, Y, Rfb terminals on li1/met1
    # ================================================================
    # Wire widths
    li1_hw  = 0.085  # li1 half-width
    m1_hw   = 0.14   # met1 half-width (0.28um wide)
    mpad    = 0.175  # metal pad half-width for vias

    # --- Connect r0 (bottom resistor terminal) to A (Vin node) ---
    # r0 is at (r0_pos[0], r0_pos[1]) in li1
    # A is at A_ABS in li1
    # Route: li1 vertical segment from A up to r0 height, then horizontal stub
    a_x, a_y = A_ABS
    r0x, r0y = r0_pos

    # li1 single vertical wire from A pin pad up to r0 terminal pad.
    # r0x == a_x by construction (RES_X = A_ABS[0]-W/2+W/2 = A_ABS[0]).
    # li.6: area per segment >= 0.0561um^2; 0.17um * 3.0um = 0.51um^2 >> 0.0561 ✓
    R(top, a_x - li1_hw, a_y, a_x + li1_hw, r0y + li1_hw, 'li1')

    # --- Connect r1 (top resistor terminal) to Y (Vout node) ---
    y_x, y_y = Y_ABS
    r1x, r1y = r1_pos
    res_top_y = RES_Y + HEAD + L_BODY + HEAD

    # met1 via stack at Y pin
    via_stack(top, y_x, y_y, 'li1', 'met1')

    # met1 route from Y up to a met1 channel
    m1_ch_y = res_top_y + 0.8  # met1 routing channel above resistor
    R(top, y_x - m1_hw, y_y, y_x + m1_hw, m1_ch_y, 'met1')

    # met1 via stack at r1 in li1, lift to met1
    via_stack(top, r1x, r1y, 'li1', 'met1')
    # met1 horizontal from r1 col to Y col at channel height
    R(top, min(r1x, y_x) - m1_hw, m1_ch_y - m1_hw,
           max(r1x, y_x) + m1_hw, m1_ch_y + m1_hw, 'met1')

    # ================================================================
    # 4. VDD/GND routing: met1 rail -> via stack to met4 power stripes
    # ================================================================
    vdd_y = VPW_ABS[1]
    vss_y = VGN_ABS[1]

    # Via stacks from met1 power rails to met4 power stripes
    # (one via tower per rail, close to die left edge)
    VDD_STRIPE_X = (VDPWR_RECT[0] + VDPWR_RECT[2]) / 2.0   # =2.0
    GND_STRIPE_X = (VGND_RECT[0]  + VGND_RECT[2])  / 2.0   # =5.5

    # VDD connection point: junction of met1 rail and intermediate routing column
    vdd_cx = rail_x1 + 1.0   # somewhere on the power rail
    via_stack(top, vdd_cx, vdd_y, 'met1', 'met4')
    # met4 horizontal from via to power stripe center
    R(top, min(VDD_STRIPE_X, vdd_cx)-0.25, vdd_y-0.25,
           max(VDD_STRIPE_X, vdd_cx)+0.25, vdd_y+0.25, 'met4')

    # GND connection
    via_stack(top, vdd_cx, vss_y, 'met1', 'met4')
    R(top, min(GND_STRIPE_X, vdd_cx)-0.25, vss_y-0.25,
           max(GND_STRIPE_X, vdd_cx)+0.25, vss_y+0.25, 'met4')

    # VDD met4 stripe (vertical)
    R(top, *VDPWR_RECT[:2], *VDPWR_RECT[2:], 'met4')
    R(top, *VDPWR_RECT[:2], *VDPWR_RECT[2:], 'met4_pin')
    L(top, 'VDPWR', (VDPWR_RECT[0]+VDPWR_RECT[2])/2,
                    (VDPWR_RECT[1]+VDPWR_RECT[3])/2, 'met4_lbl')
    # GND met4 stripe (vertical)
    R(top, *VGND_RECT[:2],  *VGND_RECT[2:],  'met4')
    R(top, *VGND_RECT[:2],  *VGND_RECT[2:],  'met4_pin')
    L(top, 'VGND',  (VGND_RECT[0]+VGND_RECT[2])/2,
                    (VGND_RECT[1]+VGND_RECT[3])/2, 'met4_lbl')

    # ================================================================
    # 5. Signal routing to ua[] pins on met4
    #    ua[0] (Iin)  = Vin  node, at x=152.260, y=0 (bottom edge)
    #    ua[1] (Vout) = Vout node, at x=132.940, y=0
    # ================================================================
    # Build full via stacks from Vin/Vout met1 nodes up to met4, then
    # route met4 wires down to the ua pin locations

    # --- Vin (A / r0) routing column ---
    VIN_COL  = a_x        # x-column for Vin routing
    VOUT_COL = y_x        # x-column for Vout routing

    # Vin: met1-met2-met3-met4 via tower at (VIN_COL, a_y)
    via_stack(top, VIN_COL,  a_y,     'met1', 'met4')

    # Vout: the met1 channel height is m1_ch_y; put met4 tower there
    via_stack(top, VOUT_COL, m1_ch_y, 'met1', 'met4')

    # met4 vertical runs down to the ua[] pin stubs (y=1..4)
    UA0_X = ANALOG_X[0]   # 152.260
    UA1_X = ANALOG_X[1]   # 132.940
    STUB_Y_BOT = 0.0
    STUB_Y_TOP = 15.0

    # Vin -> ua[0]: met4 route
    # Horizontal met4 at mid-height, then vertical down to pin
    VIN_ROUTE_Y = 20.0
    R(top, min(VIN_COL,  UA0_X)-0.45, VIN_ROUTE_Y-0.45,
           max(VIN_COL,  UA0_X)+0.45, VIN_ROUTE_Y+0.45, 'met4')
    via_stack(top, VIN_COL, VIN_ROUTE_Y,  'met3', 'met4')
    # Extend met4 tower down  from VIN_ROUTE_Y to STUB_Y_TOP
    R(top, UA0_X-0.45, STUB_Y_BOT, UA0_X+0.45, VIN_ROUTE_Y+0.45, 'met4')

    # Vout -> ua[1]: met4 route
    VOUT_ROUTE_Y = 22.0
    R(top, min(VOUT_COL, UA1_X)-0.45, VOUT_ROUTE_Y-0.45,
           max(VOUT_COL, UA1_X)+0.45, VOUT_ROUTE_Y+0.45, 'met4')
    via_stack(top, VOUT_COL, VOUT_ROUTE_Y, 'met3', 'met4')
    R(top, UA1_X-0.45, STUB_Y_BOT, UA1_X+0.45, VOUT_ROUTE_Y+0.45, 'met4')

    # ================================================================
    # 6. TT met4 pin frame
    # ================================================================
    # Analog pins (bottom edge)
    for i in range(8):
        cx = ANALOG_X[i]
        R(top, cx-0.45, 0.0, cx+0.45, 1.0, 'met4')
        R(top, cx-0.45, 0.0, cx+0.45, 1.0, 'met4_pin')
        L(top, f'ua[{i}]', cx, 0.5, 'met4_lbl')

    # Digital pins (top edge)
    for name, (cx, cy) in DIGITAL_PINS.items():
        R(top, cx-0.15, cy-0.5, cx+0.15, cy+0.5, 'met4')
        R(top, cx-0.15, cy-0.5, cx+0.15, cy+0.5, 'met4_pin')
        L(top, name, cx, cy, 'met4_lbl')

    # ================================================================
    # 7. Write GDS
    # ================================================================
    os.makedirs('gds', exist_ok=True)
    gds_path = f'gds/{TOP}.gds'
    lib.write_gds(gds_path)
    gds_size = os.path.getsize(gds_path)
    print(f'\nGDS written: {gds_path}  ({gds_size/1024:.1f} KB)')

    # ================================================================
    # 8. Write LEF
    # ================================================================
    os.makedirs('lef', exist_ok=True)
    lef_lines = [
        'VERSION 5.8 ;', 'BUSBITCHARS "[]" ;', 'DIVIDERCHAR "/" ;', '',
        f'MACRO {TOP}', '  CLASS BLOCK ;', f'  FOREIGN {TOP} ;',
        '  ORIGIN 0.000 0.000 ;', f'  SIZE {DIE_W:.3f} BY {DIE_H:.3f} ;',
        '  SYMMETRY X Y ;', '',
    ]
    for name, (x1,y1,x2,y2) in [('VDPWR',VDPWR_RECT),('VGND',VGND_RECT)]:
        use = 'POWER' if name=='VDPWR' else 'GROUND'
        lef_lines += [
            f'  PIN {name}', f'    DIRECTION INOUT ;', f'    USE {use} ;',
            f'    PORT', f'      LAYER met4 ;',
            f'        RECT {x1:.3f} {y1:.3f} {x2:.3f} {y2:.3f} ;',
            f'    END', f'  END {name}', '']
    for i in range(8):
        cx = ANALOG_X[i]
        lef_lines += [
            f'  PIN ua[{i}]', '    DIRECTION INOUT ;', '    USE SIGNAL ;',
            '    PORT', '      LAYER met4 ;',
            f'        RECT {cx-0.45:.3f} 0.000 {cx+0.45:.3f} 1.000 ;',
            '    END', f'  END ua[{i}]', '']
    for name, (cx,cy) in DIGITAL_PINS.items():
        d = ('OUTPUT' if any(k in name for k in ('uo_out','uio_out','uio_oe'))
             else 'INPUT')
        lef_lines += [
            f'  PIN {name}', f'    DIRECTION {d} ;', '    USE SIGNAL ;',
            '    PORT', '      LAYER met4 ;',
            f'        RECT {cx-0.15:.3f} {cy-0.5:.3f} {cx+0.15:.3f} {cy+0.5:.3f} ;',
            '    END', f'  END {name}', '']
    lef_lines += [f'END {TOP}', '', 'END LIBRARY', '']
    lef_path = f'lef/{TOP}.lef'
    with open(lef_path,'w') as f: f.write('\n'.join(lef_lines))
    print(f'LEF written: {lef_path}')

    # ================================================================
    # 9. SVG export -- per layer + combined
    # ================================================================
    generate_svgs(gds_path)

    # ================================================================
    # 10. Quick verification
    # ================================================================
    vlib = gdstk.read_gds(gds_path)
    tops = vlib.top_level()
    print(f'\nVerification:')
    for tc in tops:
        bb = tc.bounding_box()
        polys = tc.get_polygons(depth=None)  # flatten all references
        layers = sorted({(p.layer, p.datatype) for p in polys})
        print(f'  {tc.name}: bbox {bb}')
        print(f'  Flat polygons: {len(polys)}, Layers: {len(layers)}')
        print(f'  Layer set: {layers}')
    print(f'  Subcell references in top: {len(tops[0].references) if tops else 0}')


# ============================================================
# SVG generator
# ============================================================

# Layer draw order (bottom to top in z-order)
# Note: 'rpo' removed -- sky130 layer (75,20) is hvi (High Voltage Indicator), not RPO;
#       no special marker layer is drawn for the poly resistor body.
LAYER_ORDER = [
    'prbndry','nwell','diff','poly','nsdm','psdm',
    'licon','li1','mcon','met1','via','met2','via2','met3','via3','met4',
]

# Colour + alpha for each layer in SVG
SVG_STYLE = {
    'prbndry': ('none', '#888888', 0.6, 1.0),  # (fill, stroke, fill_alpha, stroke_alpha)
    'nwell':   ('#c0e0ff', '#3080c0', 0.3, 0.5),
    'diff':    ('#90ee90', '#006600', 0.5, 0.7),
    'poly':    ('#ff6060', '#cc0000', 0.6, 0.8),
    'nsdm':    ('#00cc00', '#004400', 0.3, 0.6),
    'psdm':    ('#cc8800', '#664400', 0.3, 0.6),
    'licon':   ('#b060b0', '#600060', 0.8, 0.9),
    'li1':     ('#ffa0a0', '#cc4444', 0.5, 0.7),
    'mcon':    ('#808040', '#404000', 0.8, 0.9),
    'met1':    ('#6060ff', '#0000cc', 0.5, 0.7),
    'via':     ('#303080', '#000040', 0.8, 0.9),
    'met2':    ('#a0c0ff', '#2040aa', 0.5, 0.7),
    'via2':    ('#305090', '#001050', 0.8, 0.9),
    'met3':    ('#ffd700', '#886600', 0.5, 0.7),
    'via3':    ('#a08000', '#504000', 0.8, 0.9),
    'met4':    ('#ff8c00', '#884400', 0.5, 0.7),
}

def rect_to_svg(x1, y1, x2, y2, scale, die_h, fill, stroke, fa, sa, stroke_w=0.5):
    """Convert a GDS rectangle to an SVG <rect> element (Y-flipped)."""
    # GDS: y=0 is bottom; SVG: y=0 is top => flip
    sx1 = x1 * scale
    sy1 = (die_h - y2) * scale
    sw  = (x2 - x1) * scale
    sh  = (y2 - y1) * scale
    fill_attr   = fill   if fill   != 'none' else 'none'
    stroke_attr = stroke if stroke != 'none' else 'none'
    return (f'<rect x="{sx1:.2f}" y="{sy1:.2f}" '
            f'width="{sw:.2f}" height="{sh:.2f}" '
            f'fill="{fill_attr}" fill-opacity="{fa:.2f}" '
            f'stroke="{stroke_attr}" stroke-opacity="{sa:.2f}" '
            f'stroke-width="{stroke_w:.2f}"/>\n')

def polygons_by_layer(gds_path):
    """Return dict layer_key -> list of (x1,y1,x2,y2) boxes from flattened TIA top cell."""
    lib = gdstk.read_gds(gds_path)
    # Explicitly find the TIA top cell by name, not by top_level() which
    # returns all 446+ standard cells we loaded
    cell_map = {c.name: c for c in lib.cells}
    tia_cell = cell_map.get(TOP)
    if tia_cell is None:
        print(f'  WARNING: cell {TOP} not found in GDS for SVG export')
        return {}
    flat_polys = tia_cell.get_polygons(depth=None)

    # Reverse LY map: (layer, datatype) -> key (prefer the non-pin key if ambiguous)
    rev = {}
    for key, (l, d) in LY.items():
        if (l, d) not in rev:   # first match wins (drawing layer before pin layer)
            rev[(l, d)] = key

    result = {k: [] for k in LAYER_ORDER}
    for p in flat_polys:
        key = rev.get((p.layer, p.datatype))
        if key and key in result:
            bb = p.bounding_box()
            result[key].append((bb[0][0], bb[0][1], bb[1][0], bb[1][1]))
    return result

def generate_svgs(gds_path):
    """Generate per-layer SVG files + combined layered SVG."""
    os.makedirs('svg', exist_ok=True)
    SCALE = 3.0    # pixels per micron (3 px/um -> 161um = 483 px wide)
    W_px  = int(DIE_W * SCALE)
    H_px  = int(DIE_H * SCALE)

    layer_rects = polygons_by_layer(gds_path)

    combined_elements = []
    per_layer_files   = []

    for lk in LAYER_ORDER:
        rects = layer_rects.get(lk, [])
        if not rects:
            continue
        fill, stroke, fa, sa = SVG_STYLE.get(lk, ('#aaaaaa','#555555',0.5,0.7))

        layer_svg_lines = []
        for (x1,y1,x2,y2) in rects:
            s = rect_to_svg(x1, y1, x2, y2, SCALE, DIE_H,
                            fill, stroke, fa, sa)
            layer_svg_lines.append(s)
            combined_elements.append(f'<!-- {lk} -->\n' + s)

        # Per-layer SVG
        svg_path = f'svg/layer_{lk}.svg'
        with open(svg_path, 'w') as f:
            f.write(f'<svg xmlns="http://www.w3.org/2000/svg" '
                    f'width="{W_px}" height="{H_px}" '
                    f'viewBox="0 0 {W_px} {H_px}">\n')
            f.write(f'<rect width="{W_px}" height="{H_px}" fill="#1a1a2e"/>\n')
            for line in layer_svg_lines:
                f.write(line)
            f.write('</svg>\n')
        per_layer_files.append(svg_path)
        print(f'  SVG layer {lk:12s}: {len(rects):4d} shapes -> {svg_path}')

    # Combined SVG (all layers, proper z-order)
    comb_path = 'svg/combined.svg'
    with open(comb_path, 'w') as f:
        f.write(f'<svg xmlns="http://www.w3.org/2000/svg" '
                f'width="{W_px}" height="{H_px}" '
                f'viewBox="0 0 {W_px} {H_px}">\n')
        f.write(f'<rect width="{W_px}" height="{H_px}" fill="#1a1a2e"/>\n')
        for elem in combined_elements:
            f.write(elem)
        # Legend
        f.write('<g transform="translate(10,20)">\n')
        f.write('<rect width="160" height="{}" fill="#000000" '
                'fill-opacity="0.5" rx="4"/>\n'.format(
                    len(LAYER_ORDER)*14 + 6))
        for idx, lk in enumerate(LAYER_ORDER):
            clr = SVG_STYLE.get(lk, ('#aaaaaa',))[0]
            if clr == 'none':
                clr = SVG_STYLE.get(lk, ('','#888888'))[1]
            y_leg = idx*14 + 10
            f.write(f'<rect x="4" y="{y_leg-5}" width="10" height="8" '
                    f'fill="{clr}" opacity="0.8"/>\n')
            f.write(f'<text x="18" y="{y_leg}" fill="white" '
                    f'font-size="9" font-family="monospace">{lk}</text>\n')
        f.write('</g>\n')
        f.write('</svg>\n')
    print(f'  Combined SVG: {comb_path}')


if __name__ == '__main__':
    main()
