#!/usr/bin/env python3
"""Parse ngspice binary raw file and plot post-layout AC transimpedance."""

import struct
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os

RAW_FILE = "sim/results/postlayout_ac.raw"
OUT_DIR  = "sim/results"

# ── parse binary raw ──────────────────────────────────────────────────────────
with open(RAW_FILE, "rb") as f:
    content = f.read()

marker = b"Binary:\n"
hdr_end = content.find(marker)
header  = content[:hdr_end].decode("ascii", errors="replace")

# Extract counts
n_vars = n_pts = 0
for line in header.splitlines():
    if line.startswith("No. Variables:"):
        n_vars = int(line.split(":")[1].strip())
    elif line.startswith("No. Points:"):
        n_pts  = int(line.split(":")[1].strip())

print(f"Variables: {n_vars}, Points: {n_pts}")

# Binary section: each row = n_vars complex doubles (re + im) = n_vars * 2 * 8 bytes
# except frequency is stored as real (2 doubles: real and 0-imag)
data_start = hdr_end + len(marker)
data_bytes = content[data_start:]

# ngspice stores: for each frequency point, n_vars complex128 values
# (frequency is stored as complex with im=0)
vals = np.frombuffer(data_bytes[:n_pts * n_vars * 16], dtype=np.complex128)
vals = vals.reshape(n_pts, n_vars)

freq   = vals[:, 0].real          # index 0 = frequency
v_vout = vals[:, 40]              # index 40 = v(vout)

zt_mag = np.abs(v_vout)           # |Zt| = |V(vout)| since AC current = 1A
zt_db  = 20 * np.log10(zt_mag)
zt_ph  = np.angle(v_vout, deg=True)

# ── find -3 dB bandwidth ─────────────────────────────────────────────────────
zt_dc = zt_db[0]
idx3  = np.where(zt_db <= zt_dc - 3)[0]
bw    = freq[idx3[0]] if len(idx3) else None
print(f"Zt(DC) = {zt_dc:.1f} dBΩ  ({10**(zt_dc/20):.0f} Ω)")
if bw:
    print(f"3-dB BW = {bw/1e9:.2f} GHz")

# ── magnitude plot ────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(9, 4.5))
ax.semilogx(freq, zt_db, color="steelblue", linewidth=2)
if bw:
    ax.axvline(bw, color="tomato", linestyle="--", label=f"BW = {bw/1e9:.2f} GHz")
    ax.axhline(zt_dc - 3, color="grey", linestyle=":", linewidth=0.8)
    ax.legend(fontsize=10)
ax.set_xlabel("Frequency (Hz)")
ax.set_ylabel("|Zt| (dBΩ)")
ax.set_title("TIA Post-Layout: Transimpedance Magnitude")
ax.set_xlim(1e6, 1e11)
ax.grid(True, which="both", linestyle=":", linewidth=0.5)
fig.tight_layout()
fig.savefig(os.path.join(OUT_DIR, "postlayout_zt_mag.png"), dpi=150)
print("Saved postlayout_zt_mag.png")

# ── phase plot ────────────────────────────────────────────────────────────────
fig2, ax2 = plt.subplots(figsize=(9, 4.5))
ax2.semilogx(freq, zt_ph, color="darkorange", linewidth=2)
ax2.set_xlabel("Frequency (Hz)")
ax2.set_ylabel("Phase (°)")
ax2.set_title("TIA Post-Layout: Transimpedance Phase")
ax2.set_xlim(1e6, 1e11)
ax2.grid(True, which="both", linestyle=":", linewidth=0.5)
fig2.tight_layout()
fig2.savefig(os.path.join(OUT_DIR, "postlayout_zt_phase.png"), dpi=150)
print("Saved postlayout_zt_phase.png")
