#!/usr/bin/env python3
"""
PLL Layout Generator for Tiny Tapeout sky130A
=============================================
100% custom geometry — NO standard cells.
All transistors built from primitives (diff, poly, licon, li1, mcon, met1, etc.)

Target: 1x2 Tiny Tapeout tile (161.000 x 225.760 um)
PLL: 5-stage current-starved ring VCO, custom PFD, charge pump, MOSCAP loop filter
"""

import gdstk
import os
import sys
import math
import shutil
import warnings

warnings.filterwarnings("ignore")

# ===========================================================================
# SKY130 GDS LAYER MAP
# ===========================================================================
LY = {
    'nwell':    (64, 20),
    'diff':     (65, 20),
    'tap':      (65, 44),
    'poly':     (66, 20),
    'licon':    (66, 44),
    'li1':      (67, 20),  'li1_pin': (67, 16), 'li1_lbl': (67, 5),
    'mcon':     (67, 44),
    'met1':     (68, 20),  'met1_pin': (68, 16), 'met1_lbl': (68, 5),
    'via':      (68, 44),
    'met2':     (69, 20),  'met2_pin': (69, 16), 'met2_lbl': (69, 5),
    'via2':     (69, 44),
    'met3':     (70, 20),  'met3_pin': (70, 16), 'met3_lbl': (70, 5),
    'via3':     (70, 44),
    'met4':     (71, 20),  'met4_pin': (71, 16), 'met4_lbl': (71, 5),
    'nsdm':     (93, 44),
    'psdm':     (94, 20),
    'npc':      (95, 20),
    'prbndry':  (235, 4),
}

# ===========================================================================
# DESIGN CONSTANTS — all coordinates snap to 5nm grid
# ===========================================================================
TILE_W = 161.000
TILE_H = 225.760
TOP_NAME = "tt_um_pll_sky130"

# DRC-clean via sizes
LICON_SZ = 0.170
MCON_SZ  = 0.170
VIA_SZ   = 0.150
VIA2_SZ  = 0.200
VIA3_SZ  = 0.200

_VIA_HW = {'licon': 0.085, 'mcon': 0.085, 'via': 0.075, 'via2': 0.100, 'via3': 0.100}
_MET_HW = {'li1': 0.175, 'met1': 0.175, 'met2': 0.210, 'met3': 0.300, 'met4': 0.300}

# Transistor geometry
POLY_EXT_DIFF = 0.130
NSDM_ENC      = 0.125
PSDM_ENC      = 0.125
NWELL_ENC     = 0.180
NPC_EXT       = 0.100

# Output paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))

# TT pin positions (from working TIA — EXACT)
ANALOG_X = [152.260, 132.940, 113.620, 94.300, 74.980, 55.660, 36.340, 17.020]
VDPWR_RECT = (1.000, 5.000, 3.000, 220.760)
VGND_RECT  = (4.500, 5.000, 6.500, 220.760)

DIGITAL_PINS = {}
DIGITAL_PINS['clk']   = (143.980, 225.260)
DIGITAL_PINS['ena']   = (146.740, 225.260)
DIGITAL_PINS['rst_n'] = (141.220, 225.260)
for _i in range(8):
    DIGITAL_PINS[f'ui_in[{_i}]']   = (138.460 - _i * 2.760, 225.260)
    DIGITAL_PINS[f'uo_out[{_i}]']  = ( 94.300 - _i * 2.760, 225.260)
    DIGITAL_PINS[f'uio_in[{_i}]']  = (116.380 - _i * 2.760, 225.260)
    DIGITAL_PINS[f'uio_out[{_i}]'] = ( 72.220 - _i * 2.760, 225.260)
    DIGITAL_PINS[f'uio_oe[{_i}]']  = ( 50.140 - _i * 2.760, 225.260)


# ===========================================================================
# HELPER FUNCTIONS
# ===========================================================================
def snap(v, grid=0.005):
    return round(round(v / grid) * grid, 3)


def R(cell, x1, y1, x2, y2, layer_key):
    ly = LY[layer_key]
    cell.add(gdstk.rectangle(
        (snap(min(x1, x2)), snap(min(y1, y2))),
        (snap(max(x1, x2)), snap(max(y1, y2))),
        layer=ly[0], datatype=ly[1]))


def L(cell, text, x, y, layer_key):
    ly = LY[layer_key]
    cell.add(gdstk.Label(text, (snap(x), snap(y)), layer=ly[0], texttype=ly[1]))


def via_stack(cell, cx, cy, from_key='li1', to_key='met4'):
    layers_order = ['li1', 'met1', 'met2', 'met3', 'met4']
    via_info = [('mcon', 'met1'), ('via', 'met2'), ('via2', 'met3'), ('via3', 'met4')]
    si = layers_order.index(from_key)
    ei = layers_order.index(to_key)
    hw = _MET_HW[from_key]
    R(cell, cx - hw, cy - hw, cx + hw, cy + hw, from_key)
    for idx, (via_key, upper_metal) in enumerate(via_info):
        if idx < si or idx >= ei:
            continue
        vh = _VIA_HW[via_key]
        R(cell, cx - vh, cy - vh, cx + vh, cy + vh, via_key)
        hw = _MET_HW[upper_metal]
        R(cell, cx - hw, cy - hw, cx + hw, cy + hw, upper_metal)


# ===========================================================================
# SUBSTRATE TAP (P+ tap for NMOS regions) — connects to VSS
# ===========================================================================
def build_ptap(cell, x, y, w=0.500, h=0.500):
    tw = snap(max(w, 0.290))
    th = snap(max(h, 0.290))
    R(cell, x, y, x + tw, y + th, 'tap')
    R(cell, x - PSDM_ENC, y - PSDM_ENC, x + tw + PSDM_ENC, y + th + PSDM_ENC, 'psdm')
    lcx = snap(x + (tw - LICON_SZ) / 2)
    lcy = snap(y + (th - LICON_SZ) / 2)
    R(cell, lcx, lcy, lcx + LICON_SZ, lcy + LICON_SZ, 'licon')
    cx = snap(x + tw / 2)
    cy = snap(y + th / 2)
    R(cell, cx - 0.175, cy - 0.175, cx + 0.175, cy + 0.175, 'li1')
    R(cell, cx - 0.085, cy - 0.085, cx + 0.085, cy + 0.085, 'mcon')
    R(cell, cx - 0.175, cy - 0.175, cx + 0.175, cy + 0.175, 'met1')


# ===========================================================================
# NWELL TAP (N+ tap inside nwell for PMOS regions) — connects to VDD
# ===========================================================================
def build_ntap(cell, x, y, w=0.500, h=0.500, draw_nwell=True):
    """Place an N+ nwell tap at (x,y). If draw_nwell=False, assumes existing nwell covers it."""
    tw = snap(max(w, 0.290))
    th = snap(max(h, 0.290))
    R(cell, x, y, x + tw, y + th, 'tap')
    R(cell, x - NSDM_ENC, y - NSDM_ENC, x + tw + NSDM_ENC, y + th + NSDM_ENC, 'nsdm')
    if draw_nwell:
        # Make nwell large enough: min width 0.84um (nwell.1), overlap of tap >= 0.18um (diff/tap.10)
        nw_ext = max(0.200, (0.840 - tw) / 2 + 0.020, (0.840 - th) / 2 + 0.020)
        R(cell, x - nw_ext, y - nw_ext, x + tw + nw_ext, y + th + nw_ext, 'nwell')
    lcx = snap(x + (tw - LICON_SZ) / 2)
    lcy = snap(y + (th - LICON_SZ) / 2)
    R(cell, lcx, lcy, lcx + LICON_SZ, lcy + LICON_SZ, 'licon')
    cx = snap(x + tw / 2)
    cy = snap(y + th / 2)
    R(cell, cx - 0.175, cy - 0.175, cx + 0.175, cy + 0.175, 'li1')
    R(cell, cx - 0.085, cy - 0.085, cx + 0.085, cy + 0.085, 'mcon')
    R(cell, cx - 0.175, cy - 0.175, cx + 0.175, cy + 0.175, 'met1')


# ===========================================================================
# TAP ROW helper — place ptap/ntap at regular intervals along X
# ===========================================================================
def build_ptap_row(cell, y, total_w, pitch=10.0):
    for tx in range(0, int(total_w), int(pitch)):
        build_ptap(cell, snap(tx), snap(y))

def build_ntap_row(cell, y, total_w, pitch=10.0, draw_nwell=True):
    for tx in range(0, int(total_w), int(pitch)):
        build_ntap(cell, snap(tx), snap(y), draw_nwell=draw_nwell)


# ===========================================================================
# CUSTOM NFET BUILDER — DRC-clean
# ===========================================================================
def build_nfet(lib, name, w, l, nf=1):
    cell = lib.new_cell(name)
    wf = snap(w / nf)
    gate_w = snap(l)
    sd_ext = 0.380
    poly_ext = 0.130
    finger_pitch = snap(gate_w + 2 * sd_ext + 0.300)

    for i in range(nf):
        fx = snap(i * finger_pitch)
        diff_x0 = fx
        diff_x1 = snap(fx + 2 * sd_ext + gate_w)
        R(cell, diff_x0, 0.0, diff_x1, wf, 'diff')
        R(cell, diff_x0 - NSDM_ENC, -NSDM_ENC, diff_x1 + NSDM_ENC, wf + NSDM_ENC, 'nsdm')

        poly_x0 = snap(fx + sd_ext)
        poly_x1 = snap(poly_x0 + gate_w)
        R(cell, poly_x0, -poly_ext, poly_x1, wf + poly_ext, 'poly')

        # S/D licon contacts
        sc_x = snap(fx + (sd_ext - LICON_SZ) / 2)
        nc_y = max(1, int((wf - 0.120) / 0.340))
        for iy in range(nc_y):
            cy = snap(0.060 + iy * 0.340)
            if cy + LICON_SZ <= wf - 0.040:
                R(cell, sc_x, cy, sc_x + LICON_SZ, cy + LICON_SZ, 'licon')

        li_hw = 0.170
        li_src_cx = snap(fx + sd_ext / 2)
        R(cell, snap(li_src_cx - li_hw), 0.0, snap(li_src_cx + li_hw), wf, 'li1')

        dc_x = snap(fx + sd_ext + gate_w + (sd_ext - LICON_SZ) / 2)
        for iy in range(nc_y):
            cy = snap(0.060 + iy * 0.340)
            if cy + LICON_SZ <= wf - 0.040:
                R(cell, dc_x, cy, dc_x + LICON_SZ, cy + LICON_SZ, 'licon')

        li_drn_cx = snap(fx + sd_ext + gate_w + sd_ext / 2)
        R(cell, snap(li_drn_cx - li_hw), 0.0, snap(li_drn_cx + li_hw), wf, 'li1')

        # S/D MCON + MET1
        sm_x = snap(fx + sd_ext / 2)
        sm_y = snap(wf / 2)
        R(cell, sm_x - 0.085, sm_y - 0.085, sm_x + 0.085, sm_y + 0.085, 'mcon')
        R(cell, sm_x - 0.175, sm_y - 0.175, sm_x + 0.175, sm_y + 0.175, 'met1')

        dm_x = snap(fx + sd_ext + gate_w + sd_ext / 2)
        R(cell, dm_x - 0.085, sm_y - 0.085, dm_x + 0.085, sm_y + 0.085, 'mcon')
        R(cell, dm_x - 0.175, sm_y - 0.175, dm_x + 0.175, sm_y + 0.175, 'met1')

        # Poly contact above diffusion
        pc_x = snap(poly_x0 + (gate_w - LICON_SZ) / 2)
        pc_y = snap(wf + poly_ext + 0.120)
        if gate_w >= LICON_SZ:
            R(cell, poly_x0, wf + poly_ext, poly_x1, pc_y + LICON_SZ + 0.100, 'poly')
            R(cell, pc_x, pc_y, pc_x + LICON_SZ, pc_y + LICON_SZ, 'licon')
            R(cell, poly_x0 - NPC_EXT, pc_y - 0.050,
                  poly_x1 + NPC_EXT, pc_y + LICON_SZ + 0.050, 'npc')
            gx = snap(pc_x + LICON_SZ / 2)
            gy = snap(pc_y + LICON_SZ / 2)
            R(cell, gx - 0.175, gy - 0.175, gx + 0.175, gy + 0.175, 'li1')
            R(cell, gx - 0.085, gy - 0.085, gx + 0.085, gy + 0.085, 'mcon')
            R(cell, gx - 0.175, gy - 0.175, gx + 0.175, gy + 0.175, 'met1')

    return cell


# ===========================================================================
# CUSTOM PFET BUILDER — DRC-clean
# ===========================================================================
def build_pfet(lib, name, w, l, nf=1):
    cell = lib.new_cell(name)
    wf = snap(w / nf)
    gate_w = snap(l)
    sd_ext = 0.380
    poly_ext = 0.130
    finger_pitch = snap(gate_w + 2 * sd_ext + 0.300)

    total_x = snap(nf * finger_pitch)
    R(cell, -NWELL_ENC, -NWELL_ENC,
          total_x - 0.300 + 2 * sd_ext + gate_w + NWELL_ENC,
          wf + NWELL_ENC, 'nwell')

    for i in range(nf):
        fx = snap(i * finger_pitch)
        diff_x0 = fx
        diff_x1 = snap(fx + 2 * sd_ext + gate_w)
        R(cell, diff_x0, 0.0, diff_x1, wf, 'diff')
        R(cell, diff_x0 - PSDM_ENC, -PSDM_ENC, diff_x1 + PSDM_ENC, wf + PSDM_ENC, 'psdm')

        poly_x0 = snap(fx + sd_ext)
        poly_x1 = snap(poly_x0 + gate_w)
        R(cell, poly_x0, -poly_ext, poly_x1, wf + poly_ext, 'poly')

        sc_x = snap(fx + (sd_ext - LICON_SZ) / 2)
        nc_y = max(1, int((wf - 0.120) / 0.340))
        for iy in range(nc_y):
            cy = snap(0.060 + iy * 0.340)
            if cy + LICON_SZ <= wf - 0.040:
                R(cell, sc_x, cy, sc_x + LICON_SZ, cy + LICON_SZ, 'licon')

        li_hw = 0.170
        li_src_cx = snap(fx + sd_ext / 2)
        R(cell, snap(li_src_cx - li_hw), 0.0, snap(li_src_cx + li_hw), wf, 'li1')

        dc_x = snap(fx + sd_ext + gate_w + (sd_ext - LICON_SZ) / 2)
        for iy in range(nc_y):
            cy = snap(0.060 + iy * 0.340)
            if cy + LICON_SZ <= wf - 0.040:
                R(cell, dc_x, cy, dc_x + LICON_SZ, cy + LICON_SZ, 'licon')

        li_drn_cx = snap(fx + sd_ext + gate_w + sd_ext / 2)
        R(cell, snap(li_drn_cx - li_hw), 0.0, snap(li_drn_cx + li_hw), wf, 'li1')

        sm_x = snap(fx + sd_ext / 2)
        sm_y = snap(wf / 2)
        R(cell, sm_x - 0.085, sm_y - 0.085, sm_x + 0.085, sm_y + 0.085, 'mcon')
        R(cell, sm_x - 0.175, sm_y - 0.175, sm_x + 0.175, sm_y + 0.175, 'met1')

        dm_x = snap(fx + sd_ext + gate_w + sd_ext / 2)
        R(cell, dm_x - 0.085, sm_y - 0.085, dm_x + 0.085, sm_y + 0.085, 'mcon')
        R(cell, dm_x - 0.175, sm_y - 0.175, dm_x + 0.175, sm_y + 0.175, 'met1')

        pc_x = snap(poly_x0 + (gate_w - LICON_SZ) / 2)
        pc_y = snap(wf + poly_ext + 0.120)
        if gate_w >= LICON_SZ:
            R(cell, poly_x0, wf + poly_ext, poly_x1, pc_y + LICON_SZ + 0.100, 'poly')
            R(cell, pc_x, pc_y, pc_x + LICON_SZ, pc_y + LICON_SZ, 'licon')
            R(cell, poly_x0 - NPC_EXT, pc_y - 0.050,
                  poly_x1 + NPC_EXT, pc_y + LICON_SZ + 0.050, 'npc')
            gx = snap(pc_x + LICON_SZ / 2)
            gy = snap(pc_y + LICON_SZ / 2)
            R(cell, gx - 0.175, gy - 0.175, gx + 0.175, gy + 0.175, 'li1')
            R(cell, gx - 0.085, gy - 0.085, gx + 0.085, gy + 0.085, 'mcon')
            R(cell, gx - 0.175, gy - 0.175, gx + 0.175, gy + 0.175, 'met1')

    return cell


# ===========================================================================
# CUSTOM INVERTER — NFET + PFET + taps
# ===========================================================================
def build_inverter(lib, name, wn=1.0, wp=2.0, l=0.150):
    cell = lib.new_cell(name)
    nfet = build_nfet(lib, f"{name}_n", w=wn, l=l)
    pfet = build_pfet(lib, f"{name}_p", w=wp, l=l)

    nfet_bb = nfet.bounding_box()
    pfet_bb = pfet.bounding_box()
    n_h = nfet_bb[1][1] - nfet_bb[0][1] if nfet_bb is not None else 2.0
    n_w = nfet_bb[1][0] - nfet_bb[0][0] if nfet_bb is not None else 2.0

    # Gap must ensure ndiff to nwell >= 0.34um (diff/tap.9)
    # PFET nwell extends 0.180 below pfet origin
    # Need gap where nfet poly contacts don't overlap with pfet nwell
    gap = 3.000
    cell.add(gdstk.Reference(nfet, (0, 0)))
    pfet_y = snap(n_h + gap)
    cell.add(gdstk.Reference(pfet, (0, pfet_y)))

    tap_x = snap(n_w + 0.400)
    build_ptap(cell, tap_x, 0.0)
    # Ntap with its own nwell that's big enough to satisfy nwell.1 (min 0.84um)
    # Place far enough from PFET nwell to satisfy nwell.2a (spacing >= 1.27um)
    # OR overlap with PFET nwell so they merge
    # Strategy: extend nwell from PFET to cover the tap
    p_w = pfet_bb[1][0] - pfet_bb[0][0] if pfet_bb is not None else n_w
    p_h = pfet_bb[1][1] - pfet_bb[0][1] if pfet_bb is not None else 2.0
    # Place ntap and create one big nwell covering both pfet and ntap
    build_ntap(cell, tap_x, pfet_y, draw_nwell=False)
    R(cell, -NWELL_ENC, pfet_y - NWELL_ENC,
          snap(tap_x + 0.500 + NWELL_ENC),
          snap(pfet_y + wp + NWELL_ENC), 'nwell')

    return cell


# ===========================================================================
# CUSTOM NAND2 GATE — with taps
# ===========================================================================
def build_nand2(lib, name, wn=1.0, wp=2.0, l=0.150):
    cell = lib.new_cell(name)
    nfet_a = build_nfet(lib, f"{name}_na", w=wn, l=l)
    nfet_b = build_nfet(lib, f"{name}_nb", w=wn, l=l)
    pfet_a = build_pfet(lib, f"{name}_pa", w=wp, l=l)
    pfet_b = build_pfet(lib, f"{name}_pb", w=wp, l=l)

    nfet_bb = nfet_a.bounding_box()
    pfet_bb = pfet_a.bounding_box()
    n_h = nfet_bb[1][1] - nfet_bb[0][1] if nfet_bb is not None else 2.0
    n_w = nfet_bb[1][0] - nfet_bb[0][0] if nfet_bb is not None else 1.0
    p_w = pfet_bb[1][0] - pfet_bb[0][0] if pfet_bb is not None else 1.0

    cell.add(gdstk.Reference(nfet_a, (0, 0)))
    cell.add(gdstk.Reference(nfet_b, (0, snap(n_h + 0.500))))

    p_y = snap(2 * n_h + 3.000)
    cell.add(gdstk.Reference(pfet_a, (0, p_y)))
    cell.add(gdstk.Reference(pfet_b, (snap(p_w + 1.500), p_y)))

    tap_x = snap(max(n_w, p_w * 2 + 1.5) + 0.400)
    build_ptap(cell, tap_x, 0.0)
    build_ptap(cell, tap_x, snap(n_h + 0.500))
    # Ntap inside extended nwell covering both PFETs and tap
    build_ntap(cell, tap_x, p_y, draw_nwell=False)
    R(cell, -NWELL_ENC, p_y - NWELL_ENC,
          snap(tap_x + 0.500 + NWELL_ENC),
          snap(p_y + wp + NWELL_ENC), 'nwell')

    return cell


# ===========================================================================
# CUSTOM DFF — transmission-gate master-slave with taps
# ===========================================================================
def build_dff(lib, name, wn=0.500, wp=1.000, l=0.150):
    cell = lib.new_cell(name)

    inv1 = build_inverter(lib, f"{name}_inv1", wn=wn, wp=wp, l=l)
    inv2 = build_inverter(lib, f"{name}_inv2", wn=wn, wp=wp, l=l)
    inv3 = build_inverter(lib, f"{name}_inv3", wn=wn, wp=wp, l=l)
    inv4 = build_inverter(lib, f"{name}_inv4", wn=wn, wp=wp, l=l)

    tg_n1 = build_nfet(lib, f"{name}_tgn1", w=wn, l=l)
    tg_p1 = build_pfet(lib, f"{name}_tgp1", w=wp, l=l)
    tg_n2 = build_nfet(lib, f"{name}_tgn2", w=wn, l=l)
    tg_p2 = build_pfet(lib, f"{name}_tgp2", w=wp, l=l)

    inv_bb = inv1.bounding_box()
    inv_w = inv_bb[1][0] - inv_bb[0][0] if inv_bb is not None else 2.0

    tg_bb = tg_n1.bounding_box()
    tg_w = tg_bb[1][0] - tg_bb[0][0] if tg_bb is not None else 1.0
    tg_h = tg_bb[1][1] - tg_bb[0][1] if tg_bb is not None else 2.0

    # Pitch must ensure nwell spacing >= 1.27um
    # Each pfet nwell extends 0.180 beyond diff edge
    # Min gap = pitch - pfet_cell_w; nwell gap = gap - 2*0.180
    # Need gap - 0.360 >= 1.270 → gap >= 1.630 → use 2.0
    pitch = snap(max(inv_w, tg_w) + 2.000)

    x = 0.0
    cell.add(gdstk.Reference(inv1, (x, 0)))
    x += pitch
    cell.add(gdstk.Reference(tg_n1, (x, 0)))
    tg_p_y = snap(tg_h + 3.000)  # 3.0 gap for diff/tap.9
    cell.add(gdstk.Reference(tg_p1, (x, tg_p_y)))
    # Taps for TG1 — ntap inside extended nwell
    tg1_tap_x = snap(x + tg_w + 0.2)
    build_ptap(cell, tg1_tap_x, 0.0)
    build_ntap(cell, tg1_tap_x, tg_p_y, draw_nwell=False)
    # Extended nwell for TG1 pfet + ntap
    tg_pfet_bb = tg_p1.bounding_box()
    tg_p_h = tg_pfet_bb[1][1] - tg_pfet_bb[0][1] if tg_pfet_bb else 2.0
    R(cell, x - NWELL_ENC, tg_p_y - NWELL_ENC,
          snap(tg1_tap_x + 0.500 + NWELL_ENC),
          snap(tg_p_y + wp + NWELL_ENC), 'nwell')
    x += pitch
    cell.add(gdstk.Reference(inv2, (x, 0)))
    x += pitch
    cell.add(gdstk.Reference(tg_n2, (x, 0)))
    cell.add(gdstk.Reference(tg_p2, (x, tg_p_y)))
    # Taps for TG2 — ntap inside extended nwell
    tg2_tap_x = snap(x + tg_w + 0.2)
    build_ptap(cell, tg2_tap_x, 0.0)
    build_ntap(cell, tg2_tap_x, tg_p_y, draw_nwell=False)
    R(cell, x - NWELL_ENC, tg_p_y - NWELL_ENC,
          snap(tg2_tap_x + 0.500 + NWELL_ENC),
          snap(tg_p_y + wp + NWELL_ENC), 'nwell')
    x += pitch
    cell.add(gdstk.Reference(inv3, (x, 0)))
    x += pitch
    cell.add(gdstk.Reference(inv4, (x, 0)))

    return cell


# ===========================================================================
# MOSCAP (MOS Capacitor)
# ===========================================================================
def build_moscap(lib, name, cap_pf, cox_ff_um2=8.3):
    cell = lib.new_cell(name)
    gate_area = cap_pf * 1000.0 / cox_ff_um2
    lg = 2.000
    sd_ext = 0.380
    poly_ext = 0.130
    finger_w = snap(min(50.0, max(2.0, math.sqrt(gate_area))))
    area_per_f = lg * finger_w
    nf = max(1, int(math.ceil(gate_area / area_per_f)))
    fp = snap(lg + 2 * sd_ext + 0.300)
    split = nf // 2
    tap_gap = 1.200 if nf > 2 else 0.0

    for col in range(nf):
        gap_off = tap_gap if (tap_gap > 0 and col >= split) else 0.0
        fx = snap(col * fp + gap_off)
        diff_x0 = fx
        diff_x1 = snap(fx + 2 * sd_ext + lg)
        R(cell, diff_x0, 0, diff_x1, finger_w, 'diff')
        R(cell, diff_x0 - NSDM_ENC, -NSDM_ENC,
              diff_x1 + NSDM_ENC, finger_w + NSDM_ENC, 'nsdm')

        poly_x0 = snap(fx + sd_ext)
        poly_x1 = snap(poly_x0 + lg)
        R(cell, poly_x0, -poly_ext, poly_x1, finger_w + poly_ext, 'poly')

        sc_x = snap(fx + (sd_ext - LICON_SZ) / 2)
        dc_x = snap(fx + sd_ext + lg + (sd_ext - LICON_SZ) / 2)
        nc = max(1, int((finger_w - 0.200) / 0.340))
        for j in range(nc):
            cy = snap(0.100 + j * 0.340)
            if cy + LICON_SZ <= finger_w - 0.040:
                R(cell, sc_x, cy, sc_x + LICON_SZ, cy + LICON_SZ, 'licon')
                R(cell, dc_x, cy, dc_x + LICON_SZ, cy + LICON_SZ, 'licon')

        li_hw = 0.170
        li_src_cx = snap(fx + sd_ext / 2)
        R(cell, snap(li_src_cx - li_hw), 0, snap(li_src_cx + li_hw), finger_w, 'li1')
        li_drn_cx = snap(fx + sd_ext + lg + sd_ext / 2)
        R(cell, snap(li_drn_cx - li_hw), 0, snap(li_drn_cx + li_hw), finger_w, 'li1')

        bm_x = snap(fx + sd_ext / 2)
        bm_y = snap(finger_w / 2)
        R(cell, bm_x - 0.085, bm_y - 0.085, bm_x + 0.085, bm_y + 0.085, 'mcon')
        R(cell, bm_x - 0.175, bm_y - 0.175, bm_x + 0.175, bm_y + 0.175, 'met1')

        pc_x = snap(poly_x0 + (lg - LICON_SZ) / 2)
        pc_y = snap(finger_w + poly_ext + 0.120)
        R(cell, poly_x0, finger_w + poly_ext,
              poly_x1, pc_y + LICON_SZ + 0.100, 'poly')
        R(cell, pc_x, pc_y, pc_x + LICON_SZ, pc_y + LICON_SZ, 'licon')
        R(cell, poly_x0 - NPC_EXT, pc_y - 0.050,
              poly_x1 + NPC_EXT, pc_y + LICON_SZ + 0.050, 'npc')
        gc_cx = snap(pc_x + LICON_SZ / 2)
        gc_cy = snap(pc_y + LICON_SZ / 2)
        R(cell, gc_cx - 0.175, gc_cy - 0.175, gc_cx + 0.175, gc_cy + 0.175, 'li1')
        R(cell, gc_cx - 0.085, gc_cy - 0.085, gc_cx + 0.085, gc_cy + 0.085, 'mcon')
        R(cell, gc_cx - 0.175, gc_cy - 0.175, gc_cx + 0.175, gc_cy + 0.175, 'met1')

    total_x = snap(nf * fp + tap_gap)
    bb = cell.bounding_box()
    top_y = bb[1][1] if bb is not None else finger_w + 1.0

    # Bottom and top met1 bus
    R(cell, 0, -0.200, total_x, 0.200, 'met1')
    R(cell, 0, snap(top_y - 0.400), total_x, snap(top_y), 'met1')

    # P+ substrate tap
    build_ptap(cell, snap(total_x + 0.400), snap(finger_w / 2 - 0.250))

    # Internal substrate-tap column for wide MOSCAP arrays (LU.2)
    if tap_gap > 0:
        tap_col_x = snap(split * fp + 0.350)
        for ty in range(0, int(finger_w) + 1, 8):
            build_ptap(cell, tap_col_x, snap(ty + 0.500))

    L(cell, 'BOT', snap(total_x / 2), 0.0, 'met1_lbl')
    L(cell, 'TOP', snap(total_x / 2), snap(top_y - 0.200), 'met1_lbl')

    return cell


# ===========================================================================
# POLY RESISTOR
# ===========================================================================
def build_poly_resistor(lib, name, r_ohm, rsh=1112.0, w=0.350):
    cell = lib.new_cell(name)
    nsq = r_ohm / rsh
    body_l = snap(nsq * w)
    head = 0.350
    total_l = head + body_l + head

    R(cell, 0, 0, w, total_l, 'poly')

    lhw = LICON_SZ / 2
    cx = w / 2
    r0_y = head / 2
    R(cell, cx - lhw, r0_y - lhw, cx + lhw, r0_y + lhw, 'licon')
    R(cell, cx - 0.175, r0_y - 0.175, cx + 0.175, r0_y + 0.175, 'li1')
    R(cell, cx - 0.085, r0_y - 0.085, cx + 0.085, r0_y + 0.085, 'mcon')
    R(cell, cx - 0.175, r0_y - 0.175, cx + 0.175, r0_y + 0.175, 'met1')
    R(cell, snap(cx - w/2 - NPC_EXT), r0_y - lhw - 0.050,
          snap(cx + w/2 + NPC_EXT), r0_y + lhw + 0.050, 'npc')

    r1_y = head + body_l + head / 2
    R(cell, cx - lhw, r1_y - lhw, cx + lhw, r1_y + lhw, 'licon')
    R(cell, cx - 0.175, r1_y - 0.175, cx + 0.175, r1_y + 0.175, 'li1')
    R(cell, cx - 0.085, r1_y - 0.085, cx + 0.085, r1_y + 0.085, 'mcon')
    R(cell, cx - 0.175, r1_y - 0.175, cx + 0.175, r1_y + 0.175, 'met1')
    R(cell, snap(cx - w/2 - NPC_EXT), r1_y - lhw - 0.050,
          snap(cx + w/2 + NPC_EXT), r1_y + lhw + 0.050, 'npc')

    L(cell, 'A', cx, r0_y, 'met1_lbl')
    L(cell, 'B', cx, r1_y, 'met1_lbl')

    return cell


# ===========================================================================
# VCO — 5-stage current-starved ring oscillator (ALL CUSTOM)
# ===========================================================================
def build_vco(lib):
    cell = lib.new_cell("pll_vco")

    pfet_bias = build_pfet(lib, "pfet_vco_bias", w=4.0, l=0.500, nf=2)
    nfet_vtoi = build_nfet(lib, "nfet_vco_vtoi", w=2.0, l=0.500, nf=1)

    pfet_src = build_pfet(lib, "pfet_vco_src", w=4.0, l=0.500, nf=2)
    pfet_inv = build_pfet(lib, "pfet_vco_inv", w=2.0, l=0.150, nf=1)
    nfet_inv = build_nfet(lib, "nfet_vco_ninv", w=1.0, l=0.150, nf=1)
    nfet_sink = build_nfet(lib, "nfet_vco_sink", w=2.0, l=0.500, nf=1)

    buf_inv1 = build_inverter(lib, "vco_buf1", wn=1.0, wp=2.0, l=0.150)
    buf_inv2 = build_inverter(lib, "vco_buf2", wn=1.0, wp=2.0, l=0.150)

    def cell_size(c):
        bb = c.bounding_box()
        return (bb[1][0] - bb[0][0], bb[1][1] - bb[0][1]) if bb else (2, 2)

    bias_p_sz = cell_size(pfet_bias)
    bias_n_sz = cell_size(nfet_vtoi)
    src_sz = cell_size(pfet_src)
    pinv_sz = cell_size(pfet_inv)
    ninv_sz = cell_size(nfet_inv)
    sink_sz = cell_size(nfet_sink)
    buf_sz = cell_size(buf_inv1)

    y_nmos = 0.0
    y_pmos = snap(max(sink_sz[1], ninv_sz[1]) + 3.000)
    stage_pitch = snap(max(src_sz[0], sink_sz[0]) + 2.000)

    x = 0.0
    cell.add(gdstk.Reference(pfet_bias, (x, y_pmos)))
    cell.add(gdstk.Reference(nfet_vtoi, (x, y_nmos)))

    # Bias-stage taps
    bias_tap_x = snap(max(bias_p_sz[0], bias_n_sz[0]) + 0.2)
    build_ptap(cell, bias_tap_x, snap(y_nmos + 0.5))
    build_ntap(cell, bias_tap_x, snap(y_pmos + 0.5), draw_nwell=False)
    R(cell, x - NWELL_ENC, y_pmos - NWELL_ENC,
      snap(bias_tap_x + 0.500 + NWELL_ENC),
      snap(y_pmos + bias_p_sz[1] + NWELL_ENC), 'nwell')

    x = snap(x + max(bias_p_sz[0], bias_n_sz[0]) + 1.500)

    for i in range(5):
        sx = snap(x + i * stage_pitch)
        pfet_src_y = snap(y_pmos + pinv_sz[1] + 1.5)
        cell.add(gdstk.Reference(pfet_src, (sx, pfet_src_y)))
        cell.add(gdstk.Reference(pfet_inv, (sx + 0.500, y_pmos)))
        cell.add(gdstk.Reference(nfet_inv, (sx + 0.500, snap(y_nmos + sink_sz[1] + 0.500))))
        cell.add(gdstk.Reference(nfet_sink, (sx, y_nmos)))

        tap_sx = snap(sx + max(src_sz[0], sink_sz[0]) + 0.200)
        build_ptap(cell, tap_sx, snap(y_nmos + 0.5))
        build_ntap(cell, tap_sx, snap(y_pmos + 0.5), draw_nwell=False)
        R(cell, sx - NWELL_ENC, y_pmos - NWELL_ENC,
          snap(tap_sx + 0.500 + NWELL_ENC),
          snap(pfet_src_y + src_sz[1] + NWELL_ENC), 'nwell')

    x = snap(x + 5 * stage_pitch + 2.000)
    cell.add(gdstk.Reference(buf_inv1, (x, y_nmos)))
    x = snap(x + buf_sz[0] + 1.500)
    cell.add(gdstk.Reference(buf_inv2, (x, y_nmos)))

    pfet_src_top = snap(y_pmos + pinv_sz[1] + 1.5 + src_sz[1])
    R(cell, -1.000, y_pmos - NWELL_ENC,
      snap(x + buf_sz[0] + 1.000),
      snap(pfet_src_top + NWELL_ENC), 'nwell')

    bb = cell.bounding_box()
    total_w = bb[1][0] - bb[0][0] + 2.0 if bb else 40.0
    pwr_top = bb[1][1] + 0.500 if bb else 15.0
    R(cell, -0.500, pwr_top + 0.100, total_w, pwr_top + 0.600, 'met1')
    R(cell, -0.500, -0.600, total_w, -0.100, 'met1')

    build_ptap_row(cell, -1.200, total_w, pitch=8.0)

    L(cell, 'VPWR', 1.0, pwr_top + 0.350, 'met1_lbl')
    L(cell, 'VGND', 1.0, -0.350, 'met1_lbl')

    return cell


# ===========================================================================
# CHARGE PUMP — all custom transistors
# ===========================================================================
def build_charge_pump(lib):
    cell = lib.new_cell("pll_cp")

    pfet_diode = build_pfet(lib, "pfet_cp_diode", w=4.0, l=1.000, nf=2)
    pfet_mir   = build_pfet(lib, "pfet_cp_mir",   w=4.0, l=1.000, nf=2)
    pfet_sw    = build_pfet(lib, "pfet_cp_sw",    w=2.0, l=0.150, nf=1)
    nfet_diode = build_nfet(lib, "nfet_cp_diode", w=2.0, l=1.000, nf=1)
    nfet_mir   = build_nfet(lib, "nfet_cp_mir",   w=2.0, l=1.000, nf=1)
    nfet_sw    = build_nfet(lib, "nfet_cp_sw",    w=1.0, l=0.150, nf=1)

    def cell_size(c):
        bb = c.bounding_box()
        return (bb[1][0] - bb[0][0], bb[1][1] - bb[0][1]) if bb else (2, 2)

    pd_sz = cell_size(pfet_diode)
    pm_sz = cell_size(pfet_mir)
    ps_sz = cell_size(pfet_sw)
    nd_sz = cell_size(nfet_diode)

    y_n = 0.0
    y_p = snap(max(nd_sz[1], cell_size(nfet_mir)[1], cell_size(nfet_sw)[1]) + 3.000)

    cell.add(gdstk.Reference(pfet_diode, (0, y_p)))
    cell.add(gdstk.Reference(pfet_mir, (snap(pd_sz[0] + 1.5), y_p)))
    cell.add(gdstk.Reference(pfet_sw, (snap(pd_sz[0] + pm_sz[0] + 3.0), y_p)))

    cell.add(gdstk.Reference(nfet_diode, (0, y_n)))
    cell.add(gdstk.Reference(nfet_mir, (snap(nd_sz[0] + 1.5), y_n)))
    cell.add(gdstk.Reference(nfet_sw, (snap(nd_sz[0] + cell_size(nfet_mir)[0] + 3.0), y_n)))

    bb = cell.bounding_box()
    total_w = bb[1][0] + 1.0 if bb else 20.0
    pwr_top = bb[1][1] + 0.500 if bb else 12.0
    R(cell, 0, pwr_top + 0.100, total_w, pwr_top + 0.600, 'met1')
    R(cell, 0, -0.600, total_w, -0.100, 'met1')

    # Dense taps — every 8um along bottom
    build_ptap_row(cell, -1.200, total_w, pitch=8.0)

    # Place ntaps inside explicit PFET nwell regions (avoids standalone nwell spacing issues)
    x_p0 = 0.0
    x_p1 = snap(pd_sz[0] + 1.5)
    x_p2 = snap(pd_sz[0] + pm_sz[0] + 3.0)
    ntap_y = snap(y_p + 0.500)

    tap0_x = snap(pd_sz[0] + 0.200)
    build_ntap(cell, tap0_x, ntap_y, draw_nwell=False)

    tap1_x = snap(x_p1 + pm_sz[0] + 0.200)
    build_ntap(cell, tap1_x, ntap_y, draw_nwell=False)

    tap2_x = snap(x_p2 + ps_sz[0] + 0.200)
    build_ntap(cell, tap2_x, ntap_y, draw_nwell=False)

    # Single merged nwell across PFET devices and all ntaps (prevents nwell spacing/HVI violations)
    pf_h = max(pd_sz[1], pm_sz[1], ps_sz[1])
    R(cell, x_p0 - NWELL_ENC, y_p - NWELL_ENC,
      snap(tap2_x + 0.500 + NWELL_ENC),
      snap(y_p + pf_h + NWELL_ENC), 'nwell')

    L(cell, 'VPWR', 1.0, pwr_top + 0.350, 'met1_lbl')
    L(cell, 'VGND', 1.0, -0.350, 'met1_lbl')

    return cell


# ===========================================================================
# PFD — ALL CUSTOM
# ===========================================================================
def build_pfd(lib):
    cell = lib.new_cell("pll_pfd")

    dff_up = build_dff(lib, "pfd_dff_up", wn=0.500, wp=1.000, l=0.150)
    dff_dn = build_dff(lib, "pfd_dff_dn", wn=0.500, wp=1.000, l=0.150)
    nand   = build_nand2(lib, "pfd_nand", wn=1.0, wp=2.0, l=0.150)
    inv_chain = []
    for i in range(4):
        inv_chain.append(build_inverter(lib, f"pfd_inv{i}", wn=0.500, wp=1.000, l=0.150))

    def cell_size(c):
        bb = c.bounding_box()
        return (bb[1][0] - bb[0][0], bb[1][1] - bb[0][1]) if bb else (2, 2)

    dff_sz = cell_size(dff_up)
    nand_sz = cell_size(nand)
    inv_sz = cell_size(inv_chain[0])

    x = 0.0
    cell.add(gdstk.Reference(dff_up, (x, 0)))
    x = snap(x + dff_sz[0] + 2.000)
    cell.add(gdstk.Reference(dff_dn, (x, 0)))
    x = snap(x + dff_sz[0] + 2.000)
    cell.add(gdstk.Reference(nand, (x, 0)))
    x = snap(x + nand_sz[0] + 1.500)

    for inv_c in inv_chain:
        cell.add(gdstk.Reference(inv_c, (x, 0)))
        x = snap(x + inv_sz[0] + 1.500)

    bb = cell.bounding_box()
    total_w = bb[1][0] + 1.0 if bb else 30.0
    pwr_top = bb[1][1] + 0.500 if bb else 8.0
    R(cell, 0, pwr_top + 0.100, total_w, pwr_top + 0.600, 'met1')
    R(cell, 0, -0.600, total_w, -0.100, 'met1')

    # Tap rows for latchup compliance
    build_ptap_row(cell, -1.200, total_w, pitch=8.0)
    # Ntap row far enough from sub-cell PFET nwells (> 1.27um gap)
    ntap_y = snap(pwr_top + 1.500)
    build_ntap_row(cell, ntap_y, total_w, pitch=8.0)

    L(cell, 'VPWR', 1.0, pwr_top + 0.350, 'met1_lbl')
    L(cell, 'VGND', 1.0, -0.350, 'met1_lbl')

    return cell


# ===========================================================================
# DIVIDER — /4 from custom DFFs
# ===========================================================================
def build_divider(lib):
    cell = lib.new_cell("pll_div4")

    dff1 = build_dff(lib, "div_dff1", wn=0.500, wp=1.000, l=0.150)
    dff2 = build_dff(lib, "div_dff2", wn=0.500, wp=1.000, l=0.150)
    buf  = build_inverter(lib, "div_buf", wn=1.0, wp=2.0, l=0.150)

    def cell_size(c):
        bb = c.bounding_box()
        return (bb[1][0] - bb[0][0], bb[1][1] - bb[0][1]) if bb else (2, 2)

    dff_sz = cell_size(dff1)
    buf_sz = cell_size(buf)

    x = 0.0
    cell.add(gdstk.Reference(dff1, (x, 0)))
    x = snap(x + dff_sz[0] + 2.000)
    cell.add(gdstk.Reference(dff2, (x, 0)))
    x = snap(x + dff_sz[0] + 2.000)
    cell.add(gdstk.Reference(buf, (x, 0)))

    bb = cell.bounding_box()
    total_w = bb[1][0] + 1.0 if bb else 20.0
    pwr_top = bb[1][1] + 0.500 if bb else 8.0
    R(cell, 0, pwr_top + 0.100, total_w, pwr_top + 0.600, 'met1')
    R(cell, 0, -0.600, total_w, -0.100, 'met1')

    # Tap rows for latchup compliance
    build_ptap_row(cell, -1.200, total_w, pitch=8.0)
    # Ntap row far enough from sub-cell PFET nwells (> 1.27um gap)
    ntap_y = snap(pwr_top + 1.500)
    build_ntap_row(cell, ntap_y, total_w, pitch=8.0)

    L(cell, 'VPWR', 1.0, pwr_top + 0.350, 'met1_lbl')
    L(cell, 'VGND', 1.0, -0.350, 'met1_lbl')

    return cell


# ===========================================================================
# LOOP FILTER — MOSCAP + poly resistor
# ===========================================================================
def build_loop_filter(lib):
    cell = lib.new_cell("pll_loop_filter")

    moscap_c1 = build_moscap(lib, "moscap_c1_10p", cap_pf=10.0)
    moscap_c2 = build_moscap(lib, "moscap_c2_1p", cap_pf=1.0)
    res_r1    = build_poly_resistor(lib, "poly_r_4k7", r_ohm=4700)

    def cell_size(c):
        bb = c.bounding_box()
        return (bb[1][0] - bb[0][0], bb[1][1] - bb[0][1]) if bb else (2, 2)

    c1_sz = cell_size(moscap_c1)
    c2_sz = cell_size(moscap_c2)

    y = 0.0
    c1_y = y
    cell.add(gdstk.Reference(moscap_c1, (0, c1_y)))

    y = snap(y + c1_sz[1] + 2.000)
    c2_y = y
    cell.add(gdstk.Reference(moscap_c2, (0, c2_y)))

    y = snap(y + c2_sz[1] + 2.000)
    cell.add(gdstk.Reference(res_r1, (0, y)))

    # Extra substrate taps around MOSCAP boundaries to satisfy LU.2 without touching active areas
    def add_moscap_taps(base_y, cap_w, cap_h):
        # Side-only taps keep clearance from dense source/drain edges while reducing LU.2 distance
        for ty in range(0, int(cap_h) + 1, 8):
            build_ptap(cell, snap(-1.000), snap(base_y + ty + 0.5))
            build_ptap(cell, snap(cap_w + 0.400), snap(base_y + ty + 0.5))

    add_moscap_taps(c1_y, c1_sz[0], c1_sz[1])
    add_moscap_taps(c2_y, c2_sz[0], c2_sz[1])

    L(cell, 'VGND', 5.0, -1.0, 'met1_lbl')
    L(cell, 'VCTRL', 5.0, snap(y + 2.0), 'met1_lbl')

    return cell


# ===========================================================================
# TOP-LEVEL PLL ASSEMBLY — with exact TT pin frame
# ===========================================================================
def build_pll_top(lib):
    top = lib.new_cell(TOP_NAME)

    vco_cell = build_vco(lib)
    cp_cell  = build_charge_pump(lib)
    pfd_cell = build_pfd(lib)
    div_cell = build_divider(lib)
    lf_cell  = build_loop_filter(lib)

    def cell_size(c):
        bb = c.bounding_box()
        return (bb[1][0] - bb[0][0], bb[1][1] - bb[0][1]) if bb else (0, 0)

    vco_sz = cell_size(vco_cell)
    cp_sz  = cell_size(cp_cell)
    pfd_sz = cell_size(pfd_cell)
    div_sz = cell_size(div_cell)
    lf_sz  = cell_size(lf_cell)

    margin = 8.000
    y_cursor = 8.000

    # All blocks stacked vertically — no side-by-side
    top.add(gdstk.Reference(div_cell, (margin, y_cursor)))
    y_cursor = snap(y_cursor + div_sz[1] + 2.000)

    top.add(gdstk.Reference(pfd_cell, (margin, y_cursor)))
    y_cursor = snap(y_cursor + pfd_sz[1] + 2.000)

    top.add(gdstk.Reference(cp_cell, (margin, y_cursor)))
    y_cursor = snap(y_cursor + cp_sz[1] + 2.000)

    top.add(gdstk.Reference(lf_cell, (margin, y_cursor)))
    y_cursor = snap(y_cursor + lf_sz[1] + 2.000)

    top.add(gdstk.Reference(vco_cell, (margin, y_cursor)))

    # ===== PR BOUNDARY =====
    R(top, 0, 0, TILE_W, TILE_H, 'prbndry')

    # ===== POWER DISTRIBUTION (met4 stripes) =====
    R(top, *VDPWR_RECT, 'met4')
    R(top, *VDPWR_RECT, 'met4_pin')
    L(top, 'VDPWR',
      (VDPWR_RECT[0] + VDPWR_RECT[2]) / 2,
      (VDPWR_RECT[1] + VDPWR_RECT[3]) / 2, 'met4_lbl')

    R(top, *VGND_RECT, 'met4')
    R(top, *VGND_RECT, 'met4_pin')
    L(top, 'VGND',
      (VGND_RECT[0] + VGND_RECT[2]) / 2,
      (VGND_RECT[1] + VGND_RECT[3]) / 2, 'met4_lbl')

    vdd_x = (VDPWR_RECT[0] + VDPWR_RECT[2]) / 2
    gnd_x = (VGND_RECT[0] + VGND_RECT[2]) / 2

    for vy in [10.0, 50.0, 100.0, 150.0, 200.0]:
        via_stack(top, vdd_x, vy, 'met1', 'met4')
        via_stack(top, gnd_x, vy, 'met1', 'met4')

    # Met1 power trunks from stripes down to sub-blocks
    R(top, vdd_x - 0.175, 5.000, vdd_x + 0.175, 220.760, 'met1')
    R(top, gnd_x - 0.175, 5.000, gnd_x + 0.175, 220.760, 'met1')

    # ===== TT PIN FRAME — analog pins =====
    for i in range(8):
        cx = ANALOG_X[i]
        R(top, cx - 0.450, 0.0, cx + 0.450, 1.000, 'met4')
        R(top, cx - 0.450, 0.0, cx + 0.450, 1.000, 'met4_pin')
        L(top, f'ua[{i}]', cx, 0.500, 'met4_lbl')

    # ===== TT PIN FRAME — digital pins =====
    for pin_name, (cx, cy) in DIGITAL_PINS.items():
        R(top, cx - 0.150, cy - 0.500, cx + 0.150, cy + 0.500, 'met4')
        R(top, cx - 0.150, cy - 0.500, cx + 0.150, cy + 0.500, 'met4_pin')
        L(top, pin_name, cx, cy, 'met4_lbl')

    # ===== ANALOG SIGNAL ROUTING (met4 up from pin pads) =====
    ua0_x = ANALOG_X[0]
    R(top, ua0_x - 0.450, 1.000, ua0_x + 0.450, 30.000, 'met4')
    via_stack(top, ua0_x, 29.500, 'met1', 'met4')

    ua1_x = ANALOG_X[1]
    R(top, ua1_x - 0.450, 1.000, ua1_x + 0.450, 20.000, 'met4')
    via_stack(top, ua1_x, 19.500, 'met1', 'met4')

    # ===== INTER-BLOCK MET2 ROUTING =====
    bus_base_x = margin + 2.0

    vctrl_x = snap(bus_base_x + 30.0)
    R(top, vctrl_x - 0.150, 8.0, vctrl_x + 0.150, y_cursor + vco_sz[1], 'met2')
    L(top, 'vctrl', vctrl_x, snap(y_cursor - 1.0), 'met2_lbl')

    vco_out_x = snap(bus_base_x + 25.0)
    R(top, vco_out_x - 0.150, 8.0, vco_out_x + 0.150, y_cursor + vco_sz[1], 'met2')

    div_fb_x = snap(bus_base_x + 20.0)
    div_top_y = snap(8.0 + div_sz[1] + pfd_sz[1] + 6.0)
    R(top, div_fb_x - 0.150, 8.0, div_fb_x + 0.150, div_top_y, 'met2')

    up_x = snap(bus_base_x + 12.0)
    dn_x = snap(bus_base_x + 14.0)
    cp_top_y = snap(8.0 + div_sz[1] + pfd_sz[1] + cp_sz[1] + 9.0)
    R(top, up_x - 0.150, snap(8.0 + div_sz[1] + 3.0), up_x + 0.150, cp_top_y, 'met2')
    R(top, dn_x - 0.150, snap(8.0 + div_sz[1] + 3.0), dn_x + 0.150, cp_top_y, 'met2')

    return top


# ===========================================================================
# LEF GENERATION
# ===========================================================================
def generate_lef(repo_root):
    lef_dir = os.path.join(repo_root, "lef")
    os.makedirs(lef_dir, exist_ok=True)

    lef_lines = [
        'VERSION 5.8 ;', 'BUSBITCHARS "[]" ;', 'DIVIDERCHAR "/" ;', '',
        f'MACRO {TOP_NAME}', '  CLASS BLOCK ;', f'  FOREIGN {TOP_NAME} ;',
        '  ORIGIN 0.000 0.000 ;', f'  SIZE {TILE_W:.3f} BY {TILE_H:.3f} ;',
        '  SYMMETRY X Y ;', '',
    ]

    for name, rect_coords in [('VDPWR', VDPWR_RECT), ('VGND', VGND_RECT)]:
        use = 'POWER' if name == 'VDPWR' else 'GROUND'
        x1, y1, x2, y2 = rect_coords
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
            f'        RECT {cx - 0.45:.3f} 0.000 {cx + 0.45:.3f} 1.000 ;',
            '    END', f'  END ua[{i}]', '']

    for name, (cx, cy) in DIGITAL_PINS.items():
        d = ('OUTPUT' if any(k in name for k in ('uo_out', 'uio_out', 'uio_oe'))
             else 'INPUT')
        lef_lines += [
            f'  PIN {name}', f'    DIRECTION {d} ;', '    USE SIGNAL ;',
            '    PORT', '      LAYER met4 ;',
            f'        RECT {cx - 0.15:.3f} {cy - 0.5:.3f} {cx + 0.15:.3f} {cy + 0.5:.3f} ;',
            '    END', f'  END {name}', '']

    lef_lines += [f'END {TOP_NAME}', '', 'END LIBRARY', '']
    lef_path = os.path.join(lef_dir, f'{TOP_NAME}.lef')
    with open(lef_path, 'w') as f:
        f.write('\n'.join(lef_lines))
    print(f'LEF written: {lef_path}')


# ===========================================================================
# SVG GENERATION
# ===========================================================================
SVG_STYLE = {
    (235, 4):  ("none",    "#555555", 0.3, "prbndry"),
    (64, 20):  ("#8B4513", "#6b3410", 0.25, "nwell"),
    (65, 20):  ("#228B22", "#1a6b1a", 0.5,  "diff"),
    (65, 44):  ("#33CC33", "#229922", 0.5,  "tap"),
    (66, 20):  ("#FF0000", "#cc0000", 0.45, "poly"),
    (66, 44):  ("#FFD700", "#ccaa00", 0.6,  "licon"),
    (93, 44):  ("#00CED1", "#00a0a5", 0.15, "nsdm"),
    (94, 20):  ("#FF69B4", "#cc5490", 0.15, "psdm"),
    (95, 20):  ("#9400D3", "#7500a8", 0.2,  "npc"),
    (67, 20):  ("#00BFFF", "#0099cc", 0.55, "li1"),
    (67, 44):  ("#FFD700", "#ccaa00", 0.7,  "mcon"),
    (68, 20):  ("#4169E1", "#2a4a9e", 0.5,  "met1"),
    (68, 44):  ("#FFFFFF", "#aaaaaa", 0.8,  "via"),
    (69, 20):  ("#FF8C00", "#cc7000", 0.45, "met2"),
    (69, 44):  ("#FFFFFF", "#aaaaaa", 0.8,  "via2"),
    (70, 20):  ("#32CD32", "#28a428", 0.45, "met3"),
    (70, 44):  ("#FFFFFF", "#aaaaaa", 0.8,  "via3"),
    (71, 20):  ("#DA70D6", "#b05aaa", 0.5,  "met4"),
}

LAYER_ORDER = [
    (235, 4), (64, 20), (65, 20), (65, 44), (66, 20), (66, 44),
    (93, 44), (94, 20), (95, 20), (67, 20), (67, 44),
    (68, 20), (68, 44), (69, 20), (69, 44), (70, 20), (70, 44), (71, 20),
]

MARGIN_SVG = 5
SCALE_SVG  = 4


def polygons_to_svg(polys, bb_min, h_total, scale):
    parts = []
    for poly in polys:
        pts = poly.points
        d = "M %.2f,%.2f" % ((pts[0][0] - bb_min[0]) * scale,
                              (h_total - (pts[0][1] - bb_min[1])) * scale)
        for px, py in pts[1:]:
            d += " L %.2f,%.2f" % ((px - bb_min[0]) * scale,
                                    (h_total - (py - bb_min[1])) * scale)
        d += " Z"
        parts.append(d)
    return " ".join(parts)


def labels_to_svg(labels, bb_min, h_total, scale, font_size=2.5):
    elems = []
    for lbl in labels:
        x = (lbl.origin[0] - bb_min[0]) * scale
        y = (h_total - (lbl.origin[1] - bb_min[1])) * scale
        fs = font_size * scale
        elems.append(
            '<text x="%.2f" y="%.2f" '
            'font-family="monospace" font-size="%.1f" '
            'fill="#ffffff" stroke="#000000" stroke-width="0.3" '
            'text-anchor="middle" dominant-baseline="central">'
            '%s</text>' % (x, y, fs, lbl.text))
    return "\n    ".join(elems)


def generate_svgs(gds_path, repo_root):
    lib = gdstk.read_gds(gds_path)
    cell = [c for c in lib.top_level() if c.name.startswith("tt_um_")][0]
    bb = cell.bounding_box()

    bb_min = (bb[0][0] - MARGIN_SVG, bb[0][1] - MARGIN_SVG)
    die_w = bb[1][0] - bb[0][0] + 2 * MARGIN_SVG
    die_h = bb[1][1] - bb[0][1] + 2 * MARGIN_SVG

    svg_w = die_w * SCALE_SVG
    svg_h = die_h * SCALE_SVG + 25

    svg_dir = os.path.join(repo_root, "svg")
    os.makedirs(svg_dir, exist_ok=True)

    layer_polys = {}
    all_polys = cell.get_polygons(depth=-1)
    for poly in all_polys:
        key = (poly.layer, poly.datatype)
        layer_polys.setdefault(key, []).append(poly)

    all_labels = cell.get_labels(depth=-1)

    # Combined SVG
    combined_parts = []
    for layer_key in LAYER_ORDER:
        if layer_key not in SVG_STYLE:
            continue
        polys = layer_polys.get(layer_key, [])
        if not polys:
            continue
        fill, stroke, opacity, name = SVG_STYLE[layer_key]
        path_data = polygons_to_svg(polys, bb_min, die_h, SCALE_SVG)
        sw = "1.5" if fill == "none" else "0.5"
        dash = "4,2" if fill == "none" else "none"
        combined_parts.append(
            '<path d="%s" '
            'fill="%s" fill-opacity="%s" '
            'stroke="%s" stroke-width="%s" '
            'stroke-dasharray="%s"/>' % (path_data, fill, opacity, stroke, sw, dash))

    combined_parts.append(labels_to_svg(all_labels, bb_min, die_h, SCALE_SVG))

    legend_y = die_h * SCALE_SVG - 15
    for i, lk in enumerate(LAYER_ORDER):
        if lk not in SVG_STYLE:
            continue
        fill, stroke, opacity, name = SVG_STYLE[lk]
        lx = 10 + (i % 9) * 95
        ly = legend_y + (i // 9) * 14
        cfill = fill if fill != "none" else "#333333"
        combined_parts.append(
            '<rect x="%d" y="%d" width="10" height="8" '
            'fill="%s" opacity="0.8" stroke="#fff" stroke-width="0.5"/>' % (lx, ly, cfill))
        combined_parts.append(
            '<text x="%d" y="%d" font-family="sans-serif" '
            'font-size="8" fill="#cccccc">%s</text>' % (lx + 14, ly + 7, name))

    content = "\n    ".join(combined_parts)
    svg_text = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<svg xmlns="http://www.w3.org/2000/svg" width="%.1f" height="%.1f" '
        'viewBox="0 0 %.1f %.1f">\n'
        '<rect width="100%%" height="100%%" fill="#1a1a2e"/>\n'
        '<text x="%.1f" y="18" font-family="sans-serif" font-size="14" '
        'fill="#eee" text-anchor="middle" font-weight="bold">'
        '%s - Combined Layout</text>\n'
        '<g transform="translate(0, 25)">\n    %s\n</g>\n</svg>\n'
        % (svg_w, svg_h, svg_w, svg_h, svg_w/2, cell.name, content))

    comb_path = os.path.join(svg_dir, "combined.svg")
    with open(comb_path, "w") as f:
        f.write(svg_text)
    print("  SVG combined: %s" % comb_path)

    for layer_key in LAYER_ORDER:
        if layer_key not in SVG_STYLE:
            continue
        polys = layer_polys.get(layer_key, [])
        if not polys:
            continue
        fill, stroke, opacity, name = SVG_STYLE[layer_key]
        parts = []
        bndry = layer_polys.get((235, 4), [])
        if bndry and layer_key != (235, 4):
            bd = polygons_to_svg(bndry, bb_min, die_h, SCALE_SVG)
            parts.append(
                '<path d="%s" fill="none" stroke="#555555" '
                'stroke-width="1" stroke-dasharray="4,2"/>' % bd)
        path_data = polygons_to_svg(polys, bb_min, die_h, SCALE_SVG)
        cfill = fill if fill != "none" else "#666666"
        parts.append(
            '<path d="%s" '
            'fill="%s" fill-opacity="%s" '
            'stroke="%s" stroke-width="0.5"/>' % (path_data, cfill, opacity, stroke))
        parts.append(
            '<text x="10" y="%d" font-family="sans-serif" '
            'font-size="11" fill="#aaaaaa">'
            '%s (%d,%d) - %d polygons</text>'
            % (die_h * SCALE_SVG - 5, name, layer_key[0], layer_key[1], len(polys)))
        layer_content = "\n    ".join(parts)
        layer_title = "%s - %s (%d,%d)" % (cell.name, name, layer_key[0], layer_key[1])
        layer_svg = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<svg xmlns="http://www.w3.org/2000/svg" width="%.1f" height="%.1f" '
            'viewBox="0 0 %.1f %.1f">\n'
            '<rect width="100%%" height="100%%" fill="#1a1a2e"/>\n'
            '<text x="%.1f" y="18" font-family="sans-serif" font-size="14" '
            'fill="#eee" text-anchor="middle" font-weight="bold">%s</text>\n'
            '<g transform="translate(0, 25)">\n    %s\n</g>\n</svg>\n'
            % (svg_w, svg_h, svg_w, svg_h, svg_w/2, layer_title, layer_content))
        fname = os.path.join(svg_dir, "layer_%s.svg" % name)
        with open(fname, "w") as f:
            f.write(layer_svg)
        print("  SVG layer: %s" % fname)


# ===========================================================================
# MAIN
# ===========================================================================
def main():
    print("PLL Layout Generator - sky130A (100%% custom geometry)")
    print("Tile: %.3f x %.3f um" % (TILE_W, TILE_H))
    print()

    lib = gdstk.Library(TOP_NAME, unit=1e-6, precision=1e-9)

    print("Building PLL layout (NO standard cells)...")
    top_cell = build_pll_top(lib)

    # Flatten hierarchy
    print("Flattening hierarchy...")
    top_cell.flatten()

    sub_cells = [c for c in lib.cells if c.name != TOP_NAME]
    for c in sub_cells:
        lib.remove(c)

    # Merge overlapping polygons
    print("Merging overlapping polygons per layer...")
    MERGE_LAYERS = [
        'nwell', 'diff', 'tap', 'nsdm', 'psdm', 'npc',
        'li1', 'met1', 'met2', 'met3', 'met4',
    ]
    all_polys = top_cell.polygons[:]
    all_labels = top_cell.labels[:]

    seen_labels = set()
    unique_labels = []
    for lbl in all_labels:
        key = (lbl.text, round(lbl.origin[0], 3), round(lbl.origin[1], 3),
               lbl.layer, lbl.texttype)
        if key not in seen_labels:
            seen_labels.add(key)
            unique_labels.append(lbl)
    all_labels = unique_labels

    layer_groups = {}
    keep_polys = []
    for p in all_polys:
        key = (p.layer, p.datatype)
        layer_name = None
        for ln, lk in LY.items():
            if lk == key:
                layer_name = ln
                break
        if layer_name in MERGE_LAYERS:
            layer_groups.setdefault(key, []).append(p)
        else:
            keep_polys.append(p)

    top_cell.remove(*top_cell.polygons)
    top_cell.remove(*top_cell.labels)

    for p in keep_polys:
        top_cell.add(p)

    for (ly, dt), polys in layer_groups.items():
        if len(polys) <= 1:
            for p in polys:
                top_cell.add(p)
            continue
        merged = gdstk.boolean(polys, [], "or", layer=ly, datatype=dt)
        for m in merged:
            top_cell.add(m)
        print("  Layer (%d,%d): %d -> %d polygons" % (ly, dt, len(polys), len(merged)))

    for lbl in all_labels:
        top_cell.add(lbl)

    # Write GDS
    out_dir = os.path.join(SCRIPT_DIR, "gds_out")
    os.makedirs(out_dir, exist_ok=True)
    out_gds = os.path.join(out_dir, "%s.gds" % TOP_NAME)
    lib.write_gds(out_gds)
    print("GDS written: %s (%.1f KB)" % (out_gds, os.path.getsize(out_gds)/1024))

    repo_gds = os.path.join(REPO_ROOT, "gds", "%s.gds" % TOP_NAME)
    os.makedirs(os.path.dirname(repo_gds), exist_ok=True)
    shutil.copy2(out_gds, repo_gds)
    print("GDS copied: %s" % repo_gds)

    bb = top_cell.bounding_box()
    if bb is not None:
        w = bb[1][0] - bb[0][0]
        h = bb[1][1] - bb[0][1]
        print("Layout size: %.1f x %.1f um" % (w, h))
        print("Tile utilization: %.1f%%" % ((w * h) / (TILE_W * TILE_H) * 100))

    print("\nTotal cells: %d" % len(lib.cells))
    stdcell_count = sum(1 for c in lib.cells if 'sky130_fd_sc' in c.name)
    print("Standard cells embedded: %d" % stdcell_count)
    assert stdcell_count == 0, "ERROR: Standard cells found!"

    labels = top_cell.get_labels(depth=0)
    met4_labels = [l for l in labels if l.layer == 71 and l.texttype == 5]
    print("Met4 pin labels: %d" % len(met4_labels))
    for lbl in sorted(met4_labels, key=lambda l: l.text):
        print("  %s: (%.3f, %.3f)" % (lbl.text, lbl.origin[0], lbl.origin[1]))

    generate_lef(REPO_ROOT)

    print("\nGenerating SVGs...")
    generate_svgs(repo_gds, REPO_ROOT)

    print("\nLayout generation complete - 100%% custom geometry, no standard cells.")


if __name__ == "__main__":
    main()
