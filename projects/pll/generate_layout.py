#!/usr/bin/env python3
"""
PLL Layout Generator for Tiny Tapeout sky130A
=============================================
Generates a complete ring-oscillator PLL GDS using:
  - Standard cells from sky130_fd_sc_hd for digital blocks (PFD, divider)
  - Custom analog cells for VCO, charge pump, MOSCAP, poly resistor
  - Custom routing between blocks

Target: 1x2 Tiny Tapeout tile (~161 x 225.76 µm)
PLL spec: 5-stage current-starved ring VCO, 50-500 MHz tunable
"""

import gdstk
import os
import sys
import math

# ===========================================================================
# SKY130 GDS LAYER MAP (from open_pdks klayout layers_def.py)
# ===========================================================================
L = {
    "nwell":  (64, 20),
    "diff":   (65, 20),
    "tap":    (65, 44),
    "poly":   (66, 20),
    "licon":  (66, 44),
    "li1":    (67, 20),
    "mcon":   (67, 44),
    "met1":   (68, 20),
    "via1":   (68, 44),
    "met2":   (69, 20),
    "via2":   (69, 44),
    "met3":   (70, 20),
    "via3":   (70, 44),
    "met4":   (71, 20),
    "via4":   (71, 44),
    "met5":   (72, 20),
    "nsdm":   (93, 44),
    "psdm":   (94, 20),
    "npc":    (95, 20),
    "hvtp":   (78, 44),
    "poly_res": (66, 13),
    "rpm":    (86, 20),
    "prbndry": (235, 4),
    # Labels
    "li1_lbl":  (67, 5),
    "met1_lbl": (68, 5),
    "met2_lbl": (69, 5),
    "met3_lbl": (70, 5),
    "met4_lbl": (71, 5),
}

# ===========================================================================
# DESIGN CONSTANTS (derived from studying sky130_fd_sc_hd__inv_1)
# ===========================================================================
# Standard cell row
ROW_HEIGHT   = 2.720   # VDD-to-VSS distance
ROW_PITCH    = 3.200   # Row-to-row pitch (cell height with margin)
SITE_WIDTH   = 0.460   # Standard cell site width

# Gate geometry
GATE_LEN_MIN = 0.150   # Minimum gate length (poly width across diff)
POLY_EXT_DIFF = 0.130  # Poly extends past diffusion edge
DIFF_EXT_POLY = 0.260  # Diffusion extends past poly (source/drain)

# Contacts and vias (all square)
LICON_SIZE   = 0.170
MCON_SIZE    = 0.170
VIA1_SIZE    = 0.150
VIA2_SIZE    = 0.200
VIA3_SIZE    = 0.200

# Wire widths
LI1_W        = 0.170
MET1_W       = 0.140
MET2_W       = 0.140
MET3_W       = 0.300
MET4_W       = 0.300

# Implant/well enclosures
NSDM_ENC     = 0.125   # NSDM enclosure of n-diff
PSDM_ENC     = 0.125   # PSDM enclosure of p-diff
NWELL_ENC    = 0.180   # Nwell enclosure of p-diff
NPC_EXT      = 0.100   # NPC extension past poly

# Tiny Tapeout 1x2 tile
TILE_W       = 161.00
TILE_H       = 225.76

# PDK paths
PDK_ROOT = "/home/hvt06/Downloads/open_pdks/sky130/sky130A"
STDCELL_GDS = os.path.join(PDK_ROOT, "libs.ref/sky130_fd_sc_hd/gds/sky130_fd_sc_hd.gds")

# Output
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_GDS = os.path.join(SCRIPT_DIR, "gds_out", "tt_um_pll_sky130.gds")


def rect(cell, layer, x0, y0, x1, y1):
    """Add a rectangle to cell on the given layer."""
    cell.add(gdstk.rectangle((x0, y0), (x1, y1), layer=layer[0], datatype=layer[1]))


def contact_array(cell, layer, x0, y0, nx, ny, size, pitch_x, pitch_y):
    """Add an array of square contacts/vias."""
    for ix in range(nx):
        for iy in range(ny):
            cx = x0 + ix * pitch_x
            cy = y0 + iy * pitch_y
            rect(cell, layer, cx, cy, cx + size, cy + size)


def label(cell, layer, x, y, text):
    """Add a text label."""
    cell.add(gdstk.Label(text, (x, y), layer=layer[0], texttype=layer[1]))


# ===========================================================================
# CUSTOM ANALOG CELL BUILDERS
# ===========================================================================

def build_nfet(lib, name, w, l, nf=1):
    """
    Build a custom NFET cell.
    NMOS: diff in pwell (substrate), nsdm implant.
    w: total width (µm), l: gate length (µm), nf: number of fingers
    Returns cell with ports: gate(poly), drain(li1), source(li1), body(li1/tap)
    """
    cell = lib.new_cell(name)
    wf = w / nf  # width per finger

    # Geometry per finger
    gate_w = l
    sd_ext = max(DIFF_EXT_POLY, 0.260)  # source/drain extension past gate
    poly_ext = max(POLY_EXT_DIFF, 0.130)
    finger_pitch = gate_w + 2 * sd_ext + 0.170  # gate + 2*SD + gap

    total_x = nf * finger_pitch + sd_ext
    total_y = wf + 2 * poly_ext

    for i in range(nf):
        fx = i * finger_pitch
        # Diffusion
        diff_x0 = fx
        diff_x1 = fx + 2 * sd_ext + gate_w
        diff_y0 = 0.0
        diff_y1 = wf
        rect(cell, L["diff"], diff_x0, diff_y0, diff_x1, diff_y1)

        # Poly gate
        poly_x0 = fx + sd_ext
        poly_x1 = poly_x0 + gate_w
        poly_y0 = -poly_ext
        poly_y1 = wf + poly_ext
        rect(cell, L["poly"], poly_x0, poly_y0, poly_x1, poly_y1)

        # NSDM (N+ implant over diff)
        rect(cell, L["nsdm"],
             diff_x0 - NSDM_ENC, diff_y0 - NSDM_ENC,
             diff_x1 + NSDM_ENC, diff_y1 + NSDM_ENC)

        # Licon contacts on source/drain
        # Source side
        sc_x = fx + 0.045
        nc_y = max(1, int((wf - 0.170) / 0.340))
        for iy in range(nc_y):
            cy = 0.045 + iy * 0.340
            if cy + LICON_SIZE <= wf - 0.045:
                rect(cell, L["licon"], sc_x, cy, sc_x + LICON_SIZE, cy + LICON_SIZE)
                rect(cell, L["li1"], sc_x - 0.005, cy - 0.005,
                     sc_x + LICON_SIZE + 0.005, cy + LICON_SIZE + 0.005)

        # Drain side
        dc_x = fx + sd_ext + gate_w + 0.045
        for iy in range(nc_y):
            cy = 0.045 + iy * 0.340
            if cy + LICON_SIZE <= wf - 0.045:
                rect(cell, L["licon"], dc_x, cy, dc_x + LICON_SIZE, cy + LICON_SIZE)
                rect(cell, L["li1"], dc_x - 0.005, cy - 0.005,
                     dc_x + LICON_SIZE + 0.005, cy + LICON_SIZE + 0.005)

        # Poly contact (gate) — place above diffusion
        pc_x = poly_x0 + (gate_w - LICON_SIZE) / 2
        pc_y = wf + poly_ext + 0.100
        if gate_w >= LICON_SIZE:
            rect(cell, L["poly"], poly_x0, poly_y1, poly_x1, pc_y + LICON_SIZE + 0.100)
            rect(cell, L["licon"], pc_x, pc_y, pc_x + LICON_SIZE, pc_y + LICON_SIZE)
            rect(cell, L["li1"], pc_x - 0.005, pc_y - 0.005,
                 pc_x + LICON_SIZE + 0.005, pc_y + LICON_SIZE + 0.005)
            rect(cell, L["npc"], poly_x0 - NPC_EXT, pc_y - 0.050,
                 poly_x1 + NPC_EXT, pc_y + LICON_SIZE + 0.050)

    # LI1 bus for source and drain (horizontal stripes)
    # Source bus (left side of each finger)
    li_y0 = 0.0
    li_y1 = wf
    for i in range(nf):
        fx = i * finger_pitch
        rect(cell, L["li1"], fx, li_y0, fx + sd_ext, li_y1)

    # Drain bus
    for i in range(nf):
        fx = i * finger_pitch + sd_ext + gate_w
        rect(cell, L["li1"], fx, li_y0, fx + sd_ext, li_y1)

    # MCON + MET1 on source and drain for higher-level routing
    for i in range(nf):
        fx = i * finger_pitch
        # Source mcon
        mc_x = fx + 0.045
        mc_y = 0.045
        rect(cell, L["mcon"], mc_x, mc_y, mc_x + MCON_SIZE, mc_y + MCON_SIZE)
        rect(cell, L["met1"], mc_x - 0.030, mc_y - 0.030,
             mc_x + MCON_SIZE + 0.030, mc_y + MCON_SIZE + 0.030)
        # Drain mcon
        dc_x = fx + sd_ext + gate_w + 0.045
        rect(cell, L["mcon"], dc_x, mc_y, dc_x + MCON_SIZE, mc_y + MCON_SIZE)
        rect(cell, L["met1"], dc_x - 0.030, mc_y - 0.030,
             dc_x + MCON_SIZE + 0.030, mc_y + MCON_SIZE + 0.030)

    return cell


def build_pfet(lib, name, w, l, nf=1):
    """
    Build a custom PFET cell (same structure as NFET but with nwell + psdm).
    """
    cell = lib.new_cell(name)
    wf = w / nf

    gate_w = l
    sd_ext = max(DIFF_EXT_POLY, 0.260)
    poly_ext = max(POLY_EXT_DIFF, 0.130)
    finger_pitch = gate_w + 2 * sd_ext + 0.170

    for i in range(nf):
        fx = i * finger_pitch
        diff_x0 = fx
        diff_x1 = fx + 2 * sd_ext + gate_w
        diff_y0 = 0.0
        diff_y1 = wf

        rect(cell, L["diff"], diff_x0, diff_y0, diff_x1, diff_y1)

        # Poly gate
        poly_x0 = fx + sd_ext
        poly_x1 = poly_x0 + gate_w
        rect(cell, L["poly"], poly_x0, -poly_ext, poly_x1, wf + poly_ext)

        # PSDM + NWELL
        rect(cell, L["psdm"],
             diff_x0 - PSDM_ENC, diff_y0 - PSDM_ENC,
             diff_x1 + PSDM_ENC, diff_y1 + PSDM_ENC)
        rect(cell, L["nwell"],
             diff_x0 - NWELL_ENC, diff_y0 - NWELL_ENC,
             diff_x1 + NWELL_ENC, diff_y1 + NWELL_ENC)

        # Contacts (same as NFET)
        sc_x = fx + 0.045
        nc_y = max(1, int((wf - 0.170) / 0.340))
        for iy in range(nc_y):
            cy = 0.045 + iy * 0.340
            if cy + LICON_SIZE <= wf - 0.045:
                rect(cell, L["licon"], sc_x, cy, sc_x + LICON_SIZE, cy + LICON_SIZE)
                rect(cell, L["li1"], sc_x - 0.005, cy - 0.005,
                     sc_x + LICON_SIZE + 0.005, cy + LICON_SIZE + 0.005)

        dc_x = fx + sd_ext + gate_w + 0.045
        for iy in range(nc_y):
            cy = 0.045 + iy * 0.340
            if cy + LICON_SIZE <= wf - 0.045:
                rect(cell, L["licon"], dc_x, cy, dc_x + LICON_SIZE, cy + LICON_SIZE)
                rect(cell, L["li1"], dc_x - 0.005, cy - 0.005,
                     dc_x + LICON_SIZE + 0.005, cy + LICON_SIZE + 0.005)

        # Poly contact above
        pc_x = poly_x0 + (gate_w - LICON_SIZE) / 2
        pc_y = wf + poly_ext + 0.100
        if gate_w >= LICON_SIZE:
            rect(cell, L["poly"], poly_x0, wf + poly_ext, poly_x1, pc_y + LICON_SIZE + 0.100)
            rect(cell, L["licon"], pc_x, pc_y, pc_x + LICON_SIZE, pc_y + LICON_SIZE)
            rect(cell, L["li1"], pc_x - 0.005, pc_y - 0.005,
                 pc_x + LICON_SIZE + 0.005, pc_y + LICON_SIZE + 0.005)
            rect(cell, L["npc"], poly_x0 - NPC_EXT, pc_y - 0.050,
                 poly_x1 + NPC_EXT, pc_y + LICON_SIZE + 0.050)

    # LI1 buses
    for i in range(nf):
        fx = i * finger_pitch
        rect(cell, L["li1"], fx, 0.0, fx + sd_ext, wf)
        rect(cell, L["li1"], fx + sd_ext + gate_w, 0.0, fx + 2 * sd_ext + gate_w, wf)

    # MCON + MET1
    for i in range(nf):
        fx = i * finger_pitch
        mc_x = fx + 0.045; mc_y = 0.045
        rect(cell, L["mcon"], mc_x, mc_y, mc_x + MCON_SIZE, mc_y + MCON_SIZE)
        rect(cell, L["met1"], mc_x - 0.030, mc_y - 0.030,
             mc_x + MCON_SIZE + 0.030, mc_y + MCON_SIZE + 0.030)
        dc_x = fx + sd_ext + gate_w + 0.045
        rect(cell, L["mcon"], dc_x, mc_y, dc_x + MCON_SIZE, mc_y + MCON_SIZE)
        rect(cell, L["met1"], dc_x - 0.030, mc_y - 0.030,
             dc_x + MCON_SIZE + 0.030, mc_y + MCON_SIZE + 0.030)

    return cell


def build_moscap(lib, name, cap_pf, cap_density=8.3):
    """
    Build a MOS capacitor (NMOS gate cap) with interdigitated fingers.
    Gate = top plate, Source/Drain/Body = bottom plate (all tied to VSS).
    Uses multi-row, multi-column finger grid to fit in compact area.
    cap_pf: capacitance in pF, cap_density: fF/µm² (gate oxide Cox)
    """
    cell = lib.new_cell(name)
    gate_area = cap_pf * 1000.0 / cap_density  # required gate area in µm²

    # Design fingers: L_gate=2µm, W=variable, interdigitated (shared S/D)
    lg = 2.0          # gate length per finger
    sd_ext = 0.260    # S/D extension past gate
    sd_gap = 0.170    # minimum gap between fingers (shared S/D with contacts)
    poly_ext = 0.130  # poly extends past diff
    fp = lg + sd_ext + sd_gap  # finger pitch (shared S/D) = 2.43 µm

    # Choose W (transistor width in Y) and number of columns/rows
    # to get a roughly square layout
    target_side = math.sqrt(gate_area * 1.5)  # ~1.5x for overhead
    w = min(40.0, max(5.0, target_side))      # finger width 5–40 µm
    area_per_finger = lg * w
    nf = max(1, int(math.ceil(gate_area / area_per_finger)))

    # Arrange in rows: max columns to fit in ~70 µm width
    max_cols = max(1, int(60.0 / fp))
    ncols = min(nf, max_cols)
    nrows = max(1, int(math.ceil(nf / ncols)))
    w = min(w, 40.0)  # cap finger width

    row_pitch = w + 2 * poly_ext + 1.5  # row pitch with contacts + gap

    for row in range(nrows):
        ry = row * row_pitch
        cols_in_row = min(ncols, nf - row * ncols)

        # Single wide diffusion strip for this row (all fingers share it)
        diff_x0 = 0
        diff_x1 = cols_in_row * fp + sd_ext
        rect(cell, L["diff"], diff_x0, ry, diff_x1, ry + w)

        # NSDM over entire diff strip
        rect(cell, L["nsdm"],
             diff_x0 - NSDM_ENC, ry - NSDM_ENC,
             diff_x1 + NSDM_ENC, ry + w + NSDM_ENC)

        for col in range(cols_in_row):
            fx = col * fp

            # Poly gate
            poly_x0 = fx + sd_ext
            poly_x1 = poly_x0 + lg
            rect(cell, L["poly"], poly_x0, ry - poly_ext, poly_x1, ry + w + poly_ext)

        # S/D contacts (between/around gates) and LI1
        for sd in range(cols_in_row + 1):
            sx = sd * fp
            # Licon contacts along the S/D strip
            nc_y = max(1, int((w - 0.300) / 0.510))
            for j in range(nc_y):
                cy = ry + 0.150 + j * 0.510
                if cy + LICON_SIZE <= ry + w - 0.040:
                    rect(cell, L["licon"], sx + 0.045, cy,
                         sx + 0.045 + LICON_SIZE, cy + LICON_SIZE)
            # LI1 strip over S/D
            rect(cell, L["li1"], sx, ry, sx + sd_ext, ry + w)

        # LI1 horizontal bus for bottom plate (S/D) at bottom of row
        rect(cell, L["li1"], 0, ry, diff_x1, ry + LI1_W)

        # Poly contacts (top plate) — above this row's diff
        pc_y = ry + w + poly_ext + 0.150
        for col in range(cols_in_row):
            fx = col * fp
            poly_x0 = fx + sd_ext
            poly_x1 = poly_x0 + lg
            pc_x = poly_x0 + lg / 2 - LICON_SIZE / 2
            rect(cell, L["poly"], poly_x0, ry + w + poly_ext, poly_x1,
                 pc_y + LICON_SIZE + 0.100)
            rect(cell, L["licon"], pc_x, pc_y, pc_x + LICON_SIZE, pc_y + LICON_SIZE)
            rect(cell, L["li1"], pc_x - 0.005, pc_y - 0.005,
                 pc_x + LICON_SIZE + 0.005, pc_y + LICON_SIZE + 0.005)
            rect(cell, L["npc"], poly_x0 - 0.050, pc_y - 0.050,
                 poly_x1 + 0.050, pc_y + LICON_SIZE + 0.050)
            rect(cell, L["mcon"], pc_x, pc_y, pc_x + MCON_SIZE, pc_y + MCON_SIZE)

    # Calculate total dimensions
    total_x = max(ncols * fp + sd_ext, 1.0)
    total_y = nrows * row_pitch

    # Top-plate bus (met1) — horizontal, connecting all poly contacts
    met1_top_y = total_y - 0.500
    rect(cell, L["met1"], 0, met1_top_y, total_x, met1_top_y + 0.500)

    # Bottom-plate bus (met1) — horizontal at bottom
    rect(cell, L["met1"], 0, -0.200, total_x, 0.200)

    # MCON connections to bottom-plate met1 bus
    for row in range(nrows):
        ry = row * row_pitch
        cols_in_row = min(ncols, nf - row * ncols)
        for sd in range(min(3, cols_in_row + 1)):
            sx = sd * fp
            rect(cell, L["mcon"], sx + 0.045, ry + 0.045,
                 sx + 0.045 + MCON_SIZE, ry + 0.045 + MCON_SIZE)

    # Vertical met1 strip connecting all row S/D buses to bottom bus
    rect(cell, L["met1"], 0, -0.200, 0.400, total_y)

    label(cell, L["met1_lbl"], total_x / 2, met1_top_y + 0.1, "TOP")
    label(cell, L["met1_lbl"], total_x / 2, -0.1, "BOT")

    return cell


def build_poly_resistor(lib, name, r_ohm, rsh=48.2, w=0.350):
    """
    Build a precision poly resistor (xhrpoly, ~48.2 Ω/sq).
    r_ohm: resistance in ohms
    rsh: sheet resistance (Ω/sq)
    w: poly width (µm)
    Returns cell with met1 terminals at each end.
    """
    cell = lib.new_cell(name)
    nsq = r_ohm / rsh
    l = nsq * w  # total length

    # If too long, serpentine
    max_seg = 20.0
    n_seg = max(1, int(math.ceil(l / max_seg)))
    seg_l = l / n_seg
    seg_pitch = w + 0.500  # spacing between parallel segments

    total_h = n_seg * seg_pitch

    for i in range(n_seg):
        y0 = i * seg_pitch
        if i % 2 == 0:
            rect(cell, L["poly"], 0, y0, seg_l, y0 + w)
            rect(cell, L["poly_res"], 0.200, y0, seg_l - 0.200, y0 + w)
            rect(cell, L["rpm"], 0.200, y0 - 0.100, seg_l - 0.200, y0 + w + 0.100)
        else:
            rect(cell, L["poly"], 0, y0, seg_l, y0 + w)
            rect(cell, L["poly_res"], 0.200, y0, seg_l - 0.200, y0 + w)
            rect(cell, L["rpm"], 0.200, y0 - 0.100, seg_l - 0.200, y0 + w + 0.100)

        # Connect adjacent segments with U-turns
        if i < n_seg - 1:
            if i % 2 == 0:
                rect(cell, L["poly"], seg_l - w, y0, seg_l, y0 + seg_pitch + w)
            else:
                rect(cell, L["poly"], 0, y0, w, y0 + seg_pitch + w)

    # Terminal contacts at ends
    # Terminal A (start)
    rect(cell, L["licon"], 0.045, 0.045, 0.045 + LICON_SIZE, 0.045 + LICON_SIZE)
    rect(cell, L["npc"], -0.050, -0.050, 0.045 + LICON_SIZE + 0.050, 0.045 + LICON_SIZE + 0.050)
    rect(cell, L["li1"], 0, 0, 0.260, w)
    rect(cell, L["mcon"], 0.045, 0.045, 0.045 + MCON_SIZE, 0.045 + MCON_SIZE)
    rect(cell, L["met1"], 0, 0, 0.300, w + 0.100)

    # Terminal B (end — last segment)
    last_y = (n_seg - 1) * seg_pitch
    end_x = seg_l if (n_seg - 1) % 2 == 0 else 0.0
    if (n_seg - 1) % 2 == 0:
        bx = seg_l - 0.260
    else:
        bx = 0.0
    rect(cell, L["licon"], bx + 0.045, last_y + 0.045,
         bx + 0.045 + LICON_SIZE, last_y + 0.045 + LICON_SIZE)
    rect(cell, L["npc"], bx - 0.050, last_y - 0.050,
         bx + 0.045 + LICON_SIZE + 0.050, last_y + 0.045 + LICON_SIZE + 0.050)
    rect(cell, L["li1"], bx, last_y, bx + 0.260, last_y + w)
    rect(cell, L["mcon"], bx + 0.045, last_y + 0.045,
         bx + 0.045 + MCON_SIZE, last_y + 0.045 + MCON_SIZE)
    rect(cell, L["met1"], bx, last_y - 0.050, bx + 0.300, last_y + w + 0.050)

    label(cell, L["met1_lbl"], 0.150, w / 2, "A")
    label(cell, L["met1_lbl"], bx + 0.150, last_y + w / 2, "B")

    return cell


# ===========================================================================
# VCO CELL — 5-stage current-starved ring oscillator
# ===========================================================================
def build_vco(lib, stdcell_lib):
    """
    Build VCO cell with 5 current-starved inverter stages + bias + output buffer.
    Each stage: PMOS source (L=0.5u W=4u), PMOS inv (L=0.15u W=2u),
                NMOS inv (L=0.15u W=1u), NMOS sink (L=0.5u W=2u)
    Bias: PMOS diode (L=0.5u W=4u), NMOS V-to-I (L=0.5u W=2u)
    Output buffer: 2 × inv_1 from standard cells
    Compact layout: two rows (PMOS top, NMOS bottom) with shared power.
    """
    cell = lib.new_cell("pll_vco")

    # Build individual transistor cells
    pfet_bias = build_pfet(lib, "pfet_vco_bias", w=4.0, l=0.50, nf=2)
    nfet_vtoi = build_nfet(lib, "nfet_vco_vtoi", w=2.0, l=0.50, nf=1)
    pfet_src  = build_pfet(lib, "pfet_vco_src",  w=4.0, l=0.50, nf=2)
    pfet_inv  = build_pfet(lib, "pfet_vco_inv",  w=2.0, l=0.15, nf=1)
    nfet_inv  = build_nfet(lib, "nfet_vco_ninv", w=1.0, l=0.15, nf=1)
    nfet_sink = build_nfet(lib, "nfet_vco_sink", w=2.0, l=0.50, nf=1)

    # Compact placement: bias left, then 5 stages tightly packed
    x = 0.0
    y_pmos = 6.0   # PMOS row (top half)
    y_nmos = 0.0   # NMOS row (bottom half)
    stage_pitch = 4.0  # X pitch between stages

    # Bias section
    cell.add(gdstk.Reference(pfet_bias, (x, y_pmos)))
    cell.add(gdstk.Reference(nfet_vtoi, (x, y_nmos)))
    x += 3.5

    # 5 VCO stages
    for i in range(5):
        sx = x + i * stage_pitch
        # Source current PMOS (above inverter PMOS)
        cell.add(gdstk.Reference(pfet_src, (sx, y_pmos + 5.0)))
        # Inverter PMOS
        cell.add(gdstk.Reference(pfet_inv, (sx + 0.5, y_pmos)))
        # Inverter NMOS
        cell.add(gdstk.Reference(nfet_inv, (sx + 0.5, y_nmos + 3.0)))
        # Sink current NMOS (below inverter NMOS)
        cell.add(gdstk.Reference(nfet_sink, (sx, y_nmos)))

    x += 5 * stage_pitch + 1.5

    # Output buffer from standard cells
    inv1_cell = None
    for c in stdcell_lib.cells:
        if c.name == "sky130_fd_sc_hd__inv_1":
            inv1_cell = c
            break
    if inv1_cell:
        cell.add(gdstk.Reference(inv1_cell, (x, y_nmos + 2.0)))
        cell.add(gdstk.Reference(inv1_cell, (x + 1.5, y_nmos + 2.0)))
    x += 4.0

    # Power rails (met1)
    rect(cell, L["met1"], 0, y_pmos + 9.5, x, y_pmos + 10.0)  # VDD
    rect(cell, L["met1"], 0, y_nmos - 0.5, x, y_nmos)           # VSS
    label(cell, L["met1_lbl"], 1.0, y_pmos + 9.7, "VPWR")
    label(cell, L["met1_lbl"], 1.0, y_nmos - 0.3, "VGND")

    # Inter-stage routing (met2 vertical wires)
    for i in range(5):
        sx = 3.5 + i * stage_pitch + 1.2
        rect(cell, L["met2"], sx, y_nmos, sx + 0.300, y_pmos + 5.0)

    return cell


# ===========================================================================
# CHARGE PUMP CELL
# ===========================================================================
def build_charge_pump(lib):
    """Build charge pump with PMOS/NMOS current mirrors + switches."""
    cell = lib.new_cell("pll_cp")

    # PMOS mirror section
    pfet_diode = build_pfet(lib, "pfet_cp_diode", w=4.0, l=1.0, nf=2)
    pfet_mir   = build_pfet(lib, "pfet_cp_mir",   w=4.0, l=1.0, nf=2)
    pfet_sw    = build_pfet(lib, "pfet_cp_sw",    w=2.0, l=0.15, nf=1)

    # NMOS mirror section
    nfet_diode = build_nfet(lib, "nfet_cp_diode", w=2.0, l=1.0, nf=1)
    nfet_mir   = build_nfet(lib, "nfet_cp_mir",   w=2.0, l=1.0, nf=1)
    nfet_sw    = build_nfet(lib, "nfet_cp_sw",    w=1.0, l=0.15, nf=1)

    # Place transistors
    y_p = 8.0  # PMOS row
    y_n = 0.0  # NMOS row

    cell.add(gdstk.Reference(pfet_diode, (0, y_p)))
    cell.add(gdstk.Reference(pfet_mir, (6, y_p)))
    cell.add(gdstk.Reference(pfet_sw, (12, y_p)))
    cell.add(gdstk.Reference(nfet_diode, (0, y_n)))
    cell.add(gdstk.Reference(nfet_mir, (6, y_n)))
    cell.add(gdstk.Reference(nfet_sw, (12, y_n)))

    # Power rails
    rect(cell, L["met1"], 0, y_p + 5.5, 15, y_p + 6.0)  # VDD
    rect(cell, L["met1"], 0, y_n - 0.5, 15, y_n)          # VSS

    label(cell, L["met1_lbl"], 1.0, y_p + 5.7, "VPWR")
    label(cell, L["met1_lbl"], 1.0, y_n - 0.3, "VGND")

    return cell


# ===========================================================================
# PFD CELL — uses standard cells
# ===========================================================================
def build_pfd(lib, stdcell_lib):
    """
    Build PFD from standard cells:
    2x dfrtp_1 (DFF with active-low async reset) + 1x nand2_1 + 4x inv_1
    PFD: D=VDD, CLK=ref/div, Q=UP/DN, RESET_B = NAND(UP,DN) through delay chain
    """
    cell = lib.new_cell("pll_pfd")

    # Get standard cells
    cells = {}
    for c in stdcell_lib.cells:
        if c.name in ("sky130_fd_sc_hd__dfrtp_1", "sky130_fd_sc_hd__nand2_1",
                       "sky130_fd_sc_hd__inv_1", "sky130_fd_sc_hd__tapvpwrvgnd_1"):
            cells[c.name] = c

    dfrtp = cells.get("sky130_fd_sc_hd__dfrtp_1")
    nand2 = cells.get("sky130_fd_sc_hd__nand2_1")
    inv1  = cells.get("sky130_fd_sc_hd__inv_1")
    tap   = cells.get("sky130_fd_sc_hd__tapvpwrvgnd_1")

    x = 0.0
    row_y = 0.0

    # Row: [tap] [DFF_UP] [tap] [DFF_DN] [tap] [NAND2] [INV×4] [tap]
    if tap:
        cell.add(gdstk.Reference(tap, (x, row_y)))
        x += 0.920

    if dfrtp:
        cell.add(gdstk.Reference(dfrtp, (x, row_y)))
        x += 9.660  # dfrtp_1 width ≈ 9.58, round up

    if tap:
        cell.add(gdstk.Reference(tap, (x, row_y)))
        x += 0.920

    if dfrtp:
        cell.add(gdstk.Reference(dfrtp, (x, row_y)))
        x += 9.660

    if tap:
        cell.add(gdstk.Reference(tap, (x, row_y)))
        x += 0.920

    if nand2:
        cell.add(gdstk.Reference(nand2, (x, row_y)))
        x += 1.840

    # 4 inverters for reset delay chain (dead-zone prevention)
    for _ in range(4):
        if inv1:
            cell.add(gdstk.Reference(inv1, (x, row_y)))
            x += 1.380

    if tap:
        cell.add(gdstk.Reference(tap, (x, row_y)))
        x += 0.920

    # Power rails along the row (met1 extending full width)
    rect(cell, L["met1"], 0, -0.100, x, 0.100)   # VSS at bottom
    rect(cell, L["met1"], 0, 2.620, x, 2.820)      # VDD at top

    label(cell, L["met1_lbl"], 1.0, -0.05, "VGND")
    label(cell, L["met1_lbl"], 1.0, 2.72, "VPWR")

    return cell


# ===========================================================================
# DIVIDER CELL — uses standard cells
# ===========================================================================
def build_divider(lib, stdcell_lib):
    """
    Build ÷4 divider from 2× toggle DFFs.
    Toggle FF: dfxbp_1 with Q_N → D feedback.
    """
    cell = lib.new_cell("pll_div4")

    cells = {}
    for c in stdcell_lib.cells:
        if c.name in ("sky130_fd_sc_hd__dfxbp_1", "sky130_fd_sc_hd__inv_1",
                       "sky130_fd_sc_hd__tapvpwrvgnd_1"):
            cells[c.name] = c

    dfxbp = cells.get("sky130_fd_sc_hd__dfxbp_1")
    inv1  = cells.get("sky130_fd_sc_hd__inv_1")
    tap   = cells.get("sky130_fd_sc_hd__tapvpwrvgnd_1")

    x = 0.0
    row_y = 0.0

    # Row: [tap] [DFF1] [tap] [DFF2] [tap] [INV_buf] [tap]
    if tap:
        cell.add(gdstk.Reference(tap, (x, row_y)))
        x += 0.920

    if dfxbp:
        cell.add(gdstk.Reference(dfxbp, (x, row_y)))
        x += 9.200  # dfxbp_1 width ≈ 9.12

    if tap:
        cell.add(gdstk.Reference(tap, (x, row_y)))
        x += 0.920

    if dfxbp:
        cell.add(gdstk.Reference(dfxbp, (x, row_y)))
        x += 9.200

    if tap:
        cell.add(gdstk.Reference(tap, (x, row_y)))
        x += 0.920

    if inv1:
        cell.add(gdstk.Reference(inv1, (x, row_y)))
        x += 1.380

    if tap:
        cell.add(gdstk.Reference(tap, (x, row_y)))
        x += 0.920

    # Power rails
    rect(cell, L["met1"], 0, -0.100, x, 0.100)
    rect(cell, L["met1"], 0, 2.620, x, 2.820)

    label(cell, L["met1_lbl"], 1.0, -0.05, "VGND")
    label(cell, L["met1_lbl"], 1.0, 2.72, "VPWR")

    return cell


# ===========================================================================
# LOOP FILTER CELL — MOSCAP + poly resistor
# ===========================================================================
def build_loop_filter(lib):
    """
    Build loop filter: R=4.7kΩ (poly), C1=10pF (MOSCAP), C2=1pF (MOSCAP).
    Sized for: Kvco=1300MHz/V, Icp=10µA, N=4 → ωn≈7MHz, ζ≈0.9
    Topology: vctrl → R → vlf1; C1: vlf1-to-VSS; C2: vctrl-to-VSS
    """
    cell = lib.new_cell("pll_loop_filter")

    # Build sub-cells
    moscap_c1 = build_moscap(lib, "moscap_c1_10p", cap_pf=10.0)
    moscap_c2 = build_moscap(lib, "moscap_c2_1p", cap_pf=1.0)
    res_r1    = build_poly_resistor(lib, "poly_r_4k7", r_ohm=4700)

    # Vertical stacking: R on top, C2 middle, C1 bottom
    x = 0.0
    y = 0.0

    ref_c1 = gdstk.Reference(moscap_c1, (x, y))
    cell.add(ref_c1)
    c1_bb = moscap_c1.bounding_box()
    y += (c1_bb[1][1] - c1_bb[0][1]) + 3.0

    ref_c2 = gdstk.Reference(moscap_c2, (x, y))
    cell.add(ref_c2)
    c2_bb = moscap_c2.bounding_box()
    y += (c2_bb[1][1] - c2_bb[0][1]) + 3.0

    ref_r = gdstk.Reference(res_r1, (x, y))
    cell.add(ref_r)

    # Labels
    label(cell, L["met1_lbl"], 5.0, -1.0, "VGND")
    label(cell, L["met2_lbl"], 5.0, y + 2.0, "VCTRL")

    return cell


# ===========================================================================
# TOP-LEVEL PLL ASSEMBLY
# ===========================================================================
def build_pll_top(lib, stdcell_lib):
    """
    Assemble the complete PLL in a top-level cell.
    Floorplan (bottom to top, within 161×226 µm tile):
      - Divider + PFD + CP digital (y=5, left side)
      - Loop Filter MOSCAPs (y=5, right side)
      - VCO (y=80)
    Power: VDD and VSS on met4 (horizontal stripes)
    Analog pins: ua[0]=ref_clk (met4), ua[1]=div_out (met4)
    """
    top = lib.new_cell("tt_um_pll_sky130")

    # Build all sub-blocks
    vco_cell = build_vco(lib, stdcell_lib)
    cp_cell  = build_charge_pump(lib)
    pfd_cell = build_pfd(lib, stdcell_lib)
    div_cell = build_divider(lib, stdcell_lib)
    lf_cell  = build_loop_filter(lib)

    # Measure block sizes for placement
    def bb_size(cell):
        bb = cell.bounding_box()
        if bb is None:
            return (0, 0)
        return (bb[1][0] - bb[0][0], bb[1][1] - bb[0][1])

    vco_sz = bb_size(vco_cell)
    cp_sz  = bb_size(cp_cell)
    pfd_sz = bb_size(pfd_cell)
    div_sz = bb_size(div_cell)
    lf_sz  = bb_size(lf_cell)

    margin = 3.0
    y_cursor = margin

    # --- Row 1: Divider (bottom left) ---
    top.add(gdstk.Reference(div_cell, (margin, y_cursor)))
    y_cursor += div_sz[1] + 2.0

    # --- Row 2: PFD ---
    top.add(gdstk.Reference(pfd_cell, (margin, y_cursor)))
    y_cursor += pfd_sz[1] + 2.0

    # --- Row 3: Charge Pump ---
    top.add(gdstk.Reference(cp_cell, (margin, y_cursor)))
    y_cursor += cp_sz[1] + 2.0

    # --- Loop Filter: placed to the right of digital blocks ---
    lf_x = max(pfd_sz[0], div_sz[0], cp_sz[0]) + margin + 5.0
    top.add(gdstk.Reference(lf_cell, (lf_x, margin)))

    # --- VCO: placed above everything ---
    y_cursor = max(y_cursor, margin + lf_sz[1] + 2.0)
    top.add(gdstk.Reference(vco_cell, (margin, y_cursor)))

    # ===== POWER DISTRIBUTION (met4 horizontal stripes) =====
    # VDD stripe at top
    rect(top, L["met4"], 0, TILE_H - 4.0, TILE_W, TILE_H - 3.0)
    label(top, L["met4_lbl"], TILE_W / 2, TILE_H - 3.5, "VPWR")

    # VSS stripe at bottom
    rect(top, L["met4"], 0, 1.0, TILE_W, 2.0)
    label(top, L["met4_lbl"], TILE_W / 2, 1.5, "VGND")

    # Vertical met3 power trunks
    rect(top, L["met3"], 1.0, 0, 2.0, TILE_H)    # VSS left
    rect(top, L["met3"], TILE_W - 2.0, 0, TILE_W - 1.0, TILE_H)  # VDD right

    # Via3 between met3 and met4
    for vx in [1.2, TILE_W - 1.8]:
        for vy in [1.2, TILE_H - 3.8]:
            rect(top, L["via3"], vx, vy, vx + VIA3_SIZE, vy + VIA3_SIZE)

    # ===== ANALOG PINS (met4) =====
    pin_w = 2.0
    pin_h = 2.0

    # ua[0] — ref clock input (left edge, middle height)
    ua0_y = TILE_H * 0.35
    rect(top, L["met4"], 0, ua0_y, pin_w, ua0_y + pin_h)
    label(top, L["met4_lbl"], pin_w / 2, ua0_y + pin_h / 2, "ua[0]")

    # ua[1] — divided VCO output (right edge, middle height)
    ua1_y = TILE_H * 0.35
    rect(top, L["met4"], TILE_W - pin_w, ua1_y, TILE_W, ua1_y + pin_h)
    label(top, L["met4_lbl"], TILE_W - pin_w / 2, ua1_y + pin_h / 2, "ua[1]")

    # ===== INTER-BLOCK SIGNAL ROUTING (met2 vertical buses) =====
    bus_x = margin + 2.0

    # vctrl: CP output → loop filter → VCO input
    rect(top, L["met2"], bus_x + 30.0, margin, bus_x + 30.5, y_cursor + vco_sz[1])
    label(top, L["met2_lbl"], bus_x + 30.2, y_cursor - 1.0, "vctrl")

    # VCO_out: VCO output → divider input
    rect(top, L["met2"], bus_x + 25.0, margin, bus_x + 25.5, y_cursor + vco_sz[1])

    # div_clk: divider output → PFD feedback
    rect(top, L["met2"], bus_x + 20.0, margin, bus_x + 20.5, margin + div_sz[1] + pfd_sz[1] + 4.0)

    # UP/DN: PFD outputs → CP inputs
    rect(top, L["met2"], bus_x + 10.0, margin + div_sz[1] + 2.0,
         bus_x + 10.5, margin + div_sz[1] + pfd_sz[1] + cp_sz[1] + 6.0)
    rect(top, L["met2"], bus_x + 12.0, margin + div_sz[1] + 2.0,
         bus_x + 12.5, margin + div_sz[1] + pfd_sz[1] + cp_sz[1] + 6.0)

    # Ref clock routing from ua[0] to PFD (met3)
    rect(top, L["met3"], margin + 1.0, margin + div_sz[1] + 1.0, margin + 1.5, ua0_y)
    # Via3 at PFD end
    rect(top, L["via3"], margin + 1.1, margin + div_sz[1] + 2.0,
         margin + 1.1 + VIA3_SIZE, margin + div_sz[1] + 2.0 + VIA3_SIZE)
    # Via3 at pin end
    rect(top, L["via3"], 0.5, ua0_y + 0.5, 0.5 + VIA3_SIZE, ua0_y + 0.5 + VIA3_SIZE)

    # Div output routing to ua[1] (met3)
    rect(top, L["met3"], TILE_W - margin - 2.0, margin,
         TILE_W - margin - 1.5, ua1_y + pin_h)
    rect(top, L["via3"], TILE_W - margin - 1.9, ua1_y + 0.5,
         TILE_W - margin - 1.9 + VIA3_SIZE, ua1_y + 0.5 + VIA3_SIZE)

    # ===== CELL BOUNDARY =====
    rect(top, L["prbndry"], 0, 0, TILE_W, TILE_H)

    return top


# ===========================================================================
# MAIN
# ===========================================================================
def main():
    print("PLL Layout Generator — sky130A")
    print(f"Tile: {TILE_W} x {TILE_H} µm")
    print()

    # Load standard cell library
    print(f"Loading standard cells from: {STDCELL_GDS}")
    import warnings
    warnings.filterwarnings("ignore")
    stdcell_lib = gdstk.read_gds(STDCELL_GDS)
    print(f"  Loaded {len(stdcell_lib.cells)} standard cells")

    # Create new library
    lib = gdstk.Library("tt_um_pll_sky130", unit=1e-6, precision=1e-9)

    # Build top-level cell (which builds all sub-cells)
    print("Building PLL layout...")
    top_cell = build_pll_top(lib, stdcell_lib)

    # Write GDS
    os.makedirs(os.path.dirname(OUT_GDS), exist_ok=True)
    lib.write_gds(OUT_GDS)
    file_size = os.path.getsize(OUT_GDS)
    print(f"\nGDS written: {OUT_GDS}")
    print(f"  File size: {file_size / 1024:.1f} KB")

    # Summary
    print(f"\n  Top cell: {top_cell.name}")
    bb = top_cell.bounding_box()
    if bb is not None:
        w = bb[1][0] - bb[0][0]
        h = bb[1][1] - bb[0][1]
        print(f"  Layout size: {w:.1f} x {h:.1f} µm")
        print(f"  Tile utilization: {(w * h) / (TILE_W * TILE_H) * 100:.1f}%")

    print("\nCustom analog cells:")
    for c in lib.cells:
        if c.name.startswith(("pfet_", "nfet_", "moscap_", "poly_r")):
            bb = c.bounding_box()
            if bb is not None:
                w = bb[1][0] - bb[0][0]
                h = bb[1][1] - bb[0][1]
                print(f"  {c.name}: {w:.2f} x {h:.2f} µm")

    # Copy GDS to repo root
    repo_root = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
    repo_gds = os.path.join(repo_root, "gds", "tt_um_pll_sky130.gds")
    os.makedirs(os.path.dirname(repo_gds), exist_ok=True)
    import shutil
    shutil.copy2(OUT_GDS, repo_gds)
    print(f"\nGDS copied to: {repo_gds}")

    # ================================================================
    # LEF GENERATION
    # ================================================================
    generate_lef(repo_root, top_cell)

    # ================================================================
    # SVG GENERATION
    # ================================================================
    generate_svgs(OUT_GDS, repo_root)

    print("\nLayout generation complete.")


# ===========================================================================
# LEF GENERATION — TT-compatible pin frame
# ===========================================================================
# Tiny Tapeout standard analog pin X positions (from TIA template)
ANALOG_X = [152.260, 132.940, 113.620, 94.300, 74.980, 55.660, 36.340, 17.020]
VDPWR_RECT = (1.0, 5.0, 3.0, 220.76)
VGND_RECT  = (4.5, 5.0, 6.5, 220.76)

# Digital pin positions (x, y) on met4; y=225.260 = top edge
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


def generate_lef(repo_root, top_cell):
    """Generate LEF abstract for TT CI compatibility."""
    TOP = top_cell.name
    lef_dir = os.path.join(repo_root, "lef")
    os.makedirs(lef_dir, exist_ok=True)

    lef_lines = [
        'VERSION 5.8 ;', 'BUSBITCHARS "[]" ;', 'DIVIDERCHAR "/" ;', '',
        f'MACRO {TOP}', '  CLASS BLOCK ;', f'  FOREIGN {TOP} ;',
        '  ORIGIN 0.000 0.000 ;', f'  SIZE {TILE_W:.3f} BY {TILE_H:.3f} ;',
        '  SYMMETRY X Y ;', '',
    ]

    # Power pins
    for name, rect_coords in [('VDPWR', VDPWR_RECT), ('VGND', VGND_RECT)]:
        use = 'POWER' if name == 'VDPWR' else 'GROUND'
        x1, y1, x2, y2 = rect_coords
        lef_lines += [
            f'  PIN {name}', f'    DIRECTION INOUT ;', f'    USE {use} ;',
            f'    PORT', f'      LAYER met4 ;',
            f'        RECT {x1:.3f} {y1:.3f} {x2:.3f} {y2:.3f} ;',
            f'    END', f'  END {name}', '']

    # Analog pins
    for i in range(8):
        cx = ANALOG_X[i]
        lef_lines += [
            f'  PIN ua[{i}]', '    DIRECTION INOUT ;', '    USE SIGNAL ;',
            '    PORT', '      LAYER met4 ;',
            f'        RECT {cx - 0.45:.3f} 0.000 {cx + 0.45:.3f} 1.000 ;',
            '    END', f'  END ua[{i}]', '']

    # Digital pins
    for name, (cx, cy) in DIGITAL_PINS.items():
        d = ('OUTPUT' if any(k in name for k in ('uo_out', 'uio_out', 'uio_oe'))
             else 'INPUT')
        lef_lines += [
            f'  PIN {name}', f'    DIRECTION {d} ;', '    USE SIGNAL ;',
            '    PORT', '      LAYER met4 ;',
            f'        RECT {cx - 0.15:.3f} {cy - 0.5:.3f} {cx + 0.15:.3f} {cy + 0.5:.3f} ;',
            '    END', f'  END {name}', '']

    lef_lines += [f'END {TOP}', '', 'END LIBRARY', '']
    lef_path = os.path.join(lef_dir, f'{TOP}.lef')
    with open(lef_path, 'w') as f:
        f.write('\n'.join(lef_lines))
    print(f'\nLEF written: {lef_path}')


# ===========================================================================
# SVG GENERATION — per-layer + combined
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
        d = f"M {(pts[0][0] - bb_min[0]) * scale:.2f},{(h_total - (pts[0][1] - bb_min[1])) * scale:.2f}"
        for px, py in pts[1:]:
            d += f" L {(px - bb_min[0]) * scale:.2f},{(h_total - (py - bb_min[1])) * scale:.2f}"
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
            f'<text x="{x:.2f}" y="{y:.2f}" '
            f'font-family="monospace" font-size="{fs:.1f}" '
            f'fill="#ffffff" stroke="#000000" stroke-width="0.3" '
            f'text-anchor="middle" dominant-baseline="central">'
            f'{lbl.text}</text>')
    return "\n    ".join(elems)


def generate_svgs(gds_path, repo_root):
    """Generate per-layer and combined SVG visualizations."""
    import warnings
    warnings.filterwarnings("ignore")
    # Load the PLL GDS, then merge standard cells so references resolve
    lib = gdstk.read_gds(gds_path)
    stdcell_lib = gdstk.read_gds(STDCELL_GDS)
    existing = {c.name for c in lib.cells}
    for sc in stdcell_lib.cells:
        if sc.name not in existing:
            lib.add(sc)
    cell = [c for c in lib.top_level() if c.name.startswith("tt_um_")][0]
    bb = cell.bounding_box()

    bb_min = (bb[0][0] - MARGIN_SVG, bb[0][1] - MARGIN_SVG)
    die_w = bb[1][0] - bb[0][0] + 2 * MARGIN_SVG
    die_h = bb[1][1] - bb[0][1] + 2 * MARGIN_SVG

    svg_w = die_w * SCALE_SVG
    svg_h = die_h * SCALE_SVG + 25

    svg_dir = os.path.join(repo_root, "svg")
    os.makedirs(svg_dir, exist_ok=True)

    # Flatten all polygons by layer
    layer_polys = {}
    all_polys = cell.get_polygons(depth=-1)
    for poly in all_polys:
        key = (poly.layer, poly.datatype)
        layer_polys.setdefault(key, []).append(poly)

    all_labels = cell.get_labels(depth=-1)

    # --- Combined SVG ---
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
            f'<path d="{path_data}" '
            f'fill="{fill}" fill-opacity="{opacity}" '
            f'stroke="{stroke}" stroke-width="{sw}" '
            f'stroke-dasharray="{dash}"/>')

    # Labels
    combined_parts.append(labels_to_svg(all_labels, bb_min, die_h, SCALE_SVG))

    # Legend
    legend_y = die_h * SCALE_SVG - 15
    for i, lk in enumerate(LAYER_ORDER):
        if lk not in SVG_STYLE:
            continue
        fill, stroke, opacity, name = SVG_STYLE[lk]
        lx = 10 + (i % 9) * 95
        ly = legend_y + (i // 9) * 14
        cfill = fill if fill != "none" else "#333333"
        combined_parts.append(
            f'<rect x="{lx}" y="{ly}" width="10" height="8" '
            f'fill="{cfill}" opacity="0.8" stroke="#fff" stroke-width="0.5"/>')
        combined_parts.append(
            f'<text x="{lx + 14}" y="{ly + 7}" font-family="sans-serif" '
            f'font-size="8" fill="#cccccc">{name}</text>')

    content = "\n    ".join(combined_parts)
    svg_text = (
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_w:.1f}" height="{svg_h:.1f}" '
        f'viewBox="0 0 {svg_w:.1f} {svg_h:.1f}">\n'
        f'<rect width="100%" height="100%" fill="#1a1a2e"/>\n'
        f'<text x="{svg_w/2:.1f}" y="18" font-family="sans-serif" font-size="14" '
        f'fill="#eee" text-anchor="middle" font-weight="bold">'
        f'{cell.name} — Combined Layout</text>\n'
        f'<g transform="translate(0, 25)">\n    {content}\n</g>\n</svg>\n')

    comb_path = os.path.join(svg_dir, "combined.svg")
    with open(comb_path, "w") as f:
        f.write(svg_text)
    print(f"  SVG combined: {comb_path}")

    # --- Per-layer SVGs ---
    for layer_key in LAYER_ORDER:
        if layer_key not in SVG_STYLE:
            continue
        polys = layer_polys.get(layer_key, [])
        if not polys:
            continue

        fill, stroke, opacity, name = SVG_STYLE[layer_key]
        parts = []

        # Boundary outline for context
        bndry = layer_polys.get((235, 4), [])
        if bndry and layer_key != (235, 4):
            bd = polygons_to_svg(bndry, bb_min, die_h, SCALE_SVG)
            parts.append(
                f'<path d="{bd}" fill="none" stroke="#555555" '
                f'stroke-width="1" stroke-dasharray="4,2"/>')

        path_data = polygons_to_svg(polys, bb_min, die_h, SCALE_SVG)
        cfill = fill if fill != "none" else "#666666"
        parts.append(
            f'<path d="{path_data}" '
            f'fill="{cfill}" fill-opacity="{opacity}" '
            f'stroke="{stroke}" stroke-width="0.5"/>')

        # Polygon count
        parts.append(
            f'<text x="10" y="{die_h * SCALE_SVG - 5}" font-family="sans-serif" '
            f'font-size="11" fill="#aaaaaa">'
            f'{name} ({layer_key[0]},{layer_key[1]}) — {len(polys)} polygons</text>')

        layer_content = "\n    ".join(parts)
        layer_title = f"{cell.name} — {name} ({layer_key[0]},{layer_key[1]})"
        layer_svg = (
            f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_w:.1f}" height="{svg_h:.1f}" '
            f'viewBox="0 0 {svg_w:.1f} {svg_h:.1f}">\n'
            f'<rect width="100%" height="100%" fill="#1a1a2e"/>\n'
            f'<text x="{svg_w/2:.1f}" y="18" font-family="sans-serif" font-size="14" '
            f'fill="#eee" text-anchor="middle" font-weight="bold">{layer_title}</text>\n'
            f'<g transform="translate(0, 25)">\n    {layer_content}\n</g>\n</svg>\n')

        fname = os.path.join(svg_dir, f"layer_{name}.svg")
        with open(fname, "w") as f:
            f.write(layer_svg)
        print(f"  SVG layer: {fname}")


if __name__ == "__main__":
    main()
