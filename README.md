![](../../workflows/gds/badge.svg) ![](../../workflows/docs/badge.svg)

# Common-Source NMOS Amplifier — Tiny Tapeout Analog (Sky130A)

A simple common-source NMOS amplifier designed for the Tiny Tapeout analog shuttle using the Sky130A PDK.

| Parameter | Value |
|-----------|-------|
| **PDK** | Sky130A (1.8V) |
| **Tile size** | 1×2 (160 × 225 µm) |
| **Transistor** | NMOS W=2µm, L=150nm |
| **Analog pins** | ua[0] = gate input, ua[1] = drain output |
| **Power** | VDPWR = 1.8V, VGND = 0V |

## Quick Start

```bash
# Regenerate GDS and LEF (requires Python 3 + gdstk)
pip install gdstk
python3 generate_layout.py
```

- [Project documentation](docs/info.md)
- [Step-by-step instructions for analog TT projects](INSTRUCTIONS.md)
