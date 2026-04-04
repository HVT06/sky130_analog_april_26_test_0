#!/usr/bin/env python3
"""
Generate SVG visualizations of the TT analog GDS layout.
Outputs:
  svg/combined.svg            - All layers overlaid (full die)
  svg/circuit_zoom.svg        - Zoomed view of ring oscillator standard cells
  svg/layer_<name>.svg        - Individual layer views

Usage: cd sky130_analog_april_26_test_0 && python3 generate_svg.py
"""

import gdstk
import os

GDS_PATH = "gds/tt_um_hvt006_cs_amp.gds"
OUT_DIR = "svg"

# Layer colors and display names — ordered bottom to top for rendering
LAYER_STYLE = {
    (235, 4):  {"name": "prbndry",    "fill": "none",    "opacity": 1.0, "stroke": "#555555"},
    (64, 20):  {"name": "nwell",      "fill": "#8B4513", "opacity": 0.25, "stroke": "#6b3410"},
    (65, 20):  {"name": "diff",       "fill": "#228B22", "opacity": 0.5, "stroke": "#1a6b1a"},
    (66, 20):  {"name": "poly",       "fill": "#FF0000", "opacity": 0.45, "stroke": "#cc0000"},
    (66, 44):  {"name": "licon",      "fill": "#FFD700", "opacity": 0.6, "stroke": "#ccaa00"},
    (93, 44):  {"name": "nsdm",       "fill": "#00CED1", "opacity": 0.15, "stroke": "#00a0a5"},
    (94, 20):  {"name": "psdm",       "fill": "#FF69B4", "opacity": 0.15, "stroke": "#cc5490"},
    (95, 20):  {"name": "npc",        "fill": "#9400D3", "opacity": 0.2, "stroke": "#7500a8"},
    (67, 20):  {"name": "li1",        "fill": "#00BFFF", "opacity": 0.55, "stroke": "#0099cc"},
    (67, 44):  {"name": "mcon",       "fill": "#FFD700", "opacity": 0.7, "stroke": "#ccaa00"},
    (68, 20):  {"name": "met1",       "fill": "#4169E1", "opacity": 0.5, "stroke": "#2a4a9e"},
    (68, 44):  {"name": "via",        "fill": "#FFFFFF", "opacity": 0.8, "stroke": "#aaaaaa"},
    (69, 20):  {"name": "met2",       "fill": "#FF8C00", "opacity": 0.45, "stroke": "#cc7000"},
    (69, 44):  {"name": "via2",       "fill": "#FFFFFF", "opacity": 0.8, "stroke": "#aaaaaa"},
    (70, 20):  {"name": "met3",       "fill": "#32CD32", "opacity": 0.45, "stroke": "#28a428"},
    (70, 44):  {"name": "via3",       "fill": "#FFFFFF", "opacity": 0.8, "stroke": "#aaaaaa"},
    (71, 20):  {"name": "met4_draw",  "fill": "#DA70D6", "opacity": 0.5, "stroke": "#b05aaa"},
    (71, 16):  {"name": "met4_pin",   "fill": "#FF6347", "opacity": 0.4, "stroke": "#cc4f38"},
}

MARGIN = 5
SCALE = 4
LABEL_SIZE = 2.5


def polygons_to_svg_path(polygons, bb_min, h_total, scale):
    """Convert gdstk polygons to SVG path data (Y-flipped)."""
    parts = []
    for poly in polygons:
        pts = poly.points
        d = f"M {(pts[0][0] - bb_min[0]) * scale:.2f},{(h_total - (pts[0][1] - bb_min[1])) * scale:.2f}"
        for px, py in pts[1:]:
            d += f" L {(px - bb_min[0]) * scale:.2f},{(h_total - (py - bb_min[1])) * scale:.2f}"
        d += " Z"
        parts.append(d)
    return " ".join(parts)


def labels_to_svg(labels, bb_min, h_total, scale, font_size):
    """Convert gdstk labels to SVG text elements."""
    elems = []
    for lbl in labels:
        x = (lbl.origin[0] - bb_min[0]) * scale
        y = (h_total - (lbl.origin[1] - bb_min[1])) * scale
        fs = font_size * scale
        # White text with dark outline for readability
        elems.append(
            f'<text x="{x:.2f}" y="{y:.2f}" '
            f'font-family="monospace" font-size="{fs:.1f}" '
            f'fill="#ffffff" stroke="#000000" stroke-width="0.3" '
            f'text-anchor="middle" dominant-baseline="central">'
            f'{lbl.text}</text>'
        )
    return "\n    ".join(elems)


def make_svg(width, height, content, title=""):
    """Wrap content in an SVG document."""
    title_block = ""
    if title:
        title_block = (
            f'<text x="{width/2:.1f}" y="18" font-family="sans-serif" '
            f'font-size="16" fill="#222" text-anchor="middle" '
            f'font-weight="bold">{title}</text>'
        )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{width:.1f}" height="{height:.1f}"
     viewBox="0 0 {width:.1f} {height:.1f}">
  <rect width="100%" height="100%" fill="#1a1a2e"/>
  {title_block}
  <g transform="translate(0, 25)">
    {content}
  </g>
</svg>
"""


def generate_svgs():
    lib = gdstk.read_gds(GDS_PATH)
    cell = lib.top_level()[0]
    bb = cell.bounding_box()

    bb_min = (bb[0][0] - MARGIN, bb[0][1] - MARGIN)
    die_w = bb[1][0] - bb[0][0] + 2 * MARGIN
    die_h = bb[1][1] - bb[0][1] + 2 * MARGIN

    svg_w = die_w * SCALE
    svg_h = die_h * SCALE + 25  # +25 for title bar

    os.makedirs(OUT_DIR, exist_ok=True)

    # Group polygons by layer
    layer_polys = {}
    for poly in cell.polygons:
        key = (poly.layer, poly.datatype)
        layer_polys.setdefault(key, []).append(poly)

    # ---- Combined SVG ----
    combined_parts = []
    for layer_key, style in LAYER_STYLE.items():
        polys = layer_polys.get(layer_key, [])
        if not polys:
            continue
        path_data = polygons_to_svg_path(polys, bb_min, die_h, SCALE)
        sw = "1.5" if style["fill"] == "none" else "0.5"
        combined_parts.append(
            f'<path d="{path_data}" '
            f'fill="{style["fill"]}" fill-opacity="{style["opacity"]}" '
            f'stroke="{style["stroke"]}" stroke-width="{sw}" '
            f'stroke-dasharray="{"4,2" if style["fill"] == "none" else "none"}"/>'
        )

    # Add labels
    combined_parts.append(labels_to_svg(cell.labels, bb_min, die_h, SCALE, LABEL_SIZE))

    # Legend
    legend_y = die_h * SCALE - 15
    for i, (lk, style) in enumerate(LAYER_STYLE.items()):
        lx = 10 + i * 200
        fill = style["fill"] if style["fill"] != "none" else "#333333"
        combined_parts.append(
            f'<rect x="{lx}" y="{legend_y}" width="12" height="12" '
            f'fill="{fill}" opacity="0.8" stroke="#fff" stroke-width="0.5"/>'
        )
        combined_parts.append(
            f'<text x="{lx + 16}" y="{legend_y + 10}" font-family="sans-serif" '
            f'font-size="10" fill="#cccccc">{style["name"]} ({lk[0]},{lk[1]})</text>'
        )

    combined_content = "\n    ".join(combined_parts)
    svg_text = make_svg(svg_w, svg_h, combined_content, title=f"{cell.name} — Combined Layout")
    combined_path = os.path.join(OUT_DIR, "combined.svg")
    with open(combined_path, "w") as f:
        f.write(svg_text)
    print(f"  {combined_path}")

    # ---- Per-layer SVGs ----
    for layer_key, style in LAYER_STYLE.items():
        polys = layer_polys.get(layer_key, [])
        if not polys:
            continue

        parts = []
        # Draw boundary outline for context
        bndry = layer_polys.get((235, 4), [])
        if bndry and layer_key != (235, 4):
            bd = polygons_to_svg_path(bndry, bb_min, die_h, SCALE)
            parts.append(
                f'<path d="{bd}" fill="none" stroke="#555555" '
                f'stroke-width="1" stroke-dasharray="4,2"/>'
            )

        path_data = polygons_to_svg_path(polys, bb_min, die_h, SCALE)
        fill = style["fill"] if style["fill"] != "none" else "#666666"
        parts.append(
            f'<path d="{path_data}" '
            f'fill="{fill}" fill-opacity="{style["opacity"]}" '
            f'stroke="{style["stroke"]}" stroke-width="0.5"/>'
        )

        # Add labels for this layer
        layer_labels = [l for l in cell.labels if (l.layer, l.texttype) == layer_key
                        or (layer_key == (71, 20) and l.layer == 71 and l.texttype == 5)]
        if layer_labels:
            parts.append(labels_to_svg(layer_labels, bb_min, die_h, SCALE, LABEL_SIZE))

        # Count info
        parts.append(
            f'<text x="10" y="{die_h * SCALE - 5}" font-family="sans-serif" '
            f'font-size="11" fill="#aaaaaa">'
            f'{style["name"]} ({layer_key[0]},{layer_key[1]}) — {len(polys)} polygons</text>'
        )

        content = "\n    ".join(parts)
        layer_title = f"{cell.name} — {style['name']} ({layer_key[0]},{layer_key[1]})"
        svg_text = make_svg(svg_w, svg_h, content, title=layer_title)

        fname = os.path.join(OUT_DIR, f"layer_{style['name']}.svg")
        with open(fname, "w") as f:
            f.write(svg_text)
        print(f"  {fname}")

    print(f"Done! SVGs in {OUT_DIR}/")

    # ---- Zoomed circuit view ----
    # Standard cells are placed around x=75..88, y=110..113
    # Zoom into that region with higher scale
    zoom_margin = 3.0
    zoom_x0 = 73.0
    zoom_y0 = 107.0
    zoom_x1 = 92.0
    zoom_y1 = 117.0
    zoom_w = zoom_x1 - zoom_x0
    zoom_h = zoom_y1 - zoom_y0
    zoom_scale = 40  # much higher resolution

    zsvg_w = zoom_w * zoom_scale
    zsvg_h = zoom_h * zoom_scale + 25

    zoom_parts = []
    # Render key circuit layers
    circuit_layers = [
        (64, 20), (65, 20), (66, 20), (66, 44),
        (93, 44), (94, 20), (95, 20),
        (67, 20), (67, 44), (68, 20),
    ]
    for layer_key in circuit_layers:
        style = LAYER_STYLE.get(layer_key)
        if not style:
            continue
        polys = layer_polys.get(layer_key, [])
        # Filter polygons in zoom region
        zoom_polys = []
        for p in polys:
            bb_p = p.bounding_box()
            if bb_p is None:
                continue
            if bb_p[1][0] >= zoom_x0 and bb_p[0][0] <= zoom_x1 and \
               bb_p[1][1] >= zoom_y0 and bb_p[0][1] <= zoom_y1:
                zoom_polys.append(p)
        if not zoom_polys:
            continue
        path_data = polygons_to_svg_path(zoom_polys, (zoom_x0, zoom_y0), zoom_h, zoom_scale)
        sw = "0.5"
        zoom_parts.append(
            f'<path d="{path_data}" '
            f'fill="{style["fill"]}" fill-opacity="{style["opacity"]}" '
            f'stroke="{style["stroke"]}" stroke-width="{sw}"/>'
        )

    # Legend for zoomed view
    legend_y2 = zoom_h * zoom_scale - 20
    for i, lk in enumerate(circuit_layers):
        style = LAYER_STYLE.get(lk)
        if not style:
            continue
        lx = 10 + (i % 5) * 180
        ly = legend_y2 + (i // 5) * 16
        fill = style["fill"] if style["fill"] != "none" else "#333333"
        zoom_parts.append(
            f'<rect x="{lx}" y="{ly}" width="10" height="10" '
            f'fill="{fill}" opacity="0.8" stroke="#fff" stroke-width="0.5"/>'
        )
        zoom_parts.append(
            f'<text x="{lx + 14}" y="{ly + 9}" font-family="sans-serif" '
            f'font-size="9" fill="#cccccc">{style["name"]}</text>'
        )

    zoom_content = "\n    ".join(zoom_parts)
    zoom_svg = make_svg(zsvg_w, zsvg_h, zoom_content,
                        title=f"{cell.name} — Ring Oscillator (zoomed)")
    zoom_path = os.path.join(OUT_DIR, "circuit_zoom.svg")
    with open(zoom_path, "w") as f:
        f.write(zoom_svg)
    print(f"  {zoom_path}")


if __name__ == "__main__":
    generate_svgs()
