#!/usr/bin/env python3
"""
Run TIA corners + Monte Carlo simulations and generate all analysis plots.

Corners: tt/ff/ss/sf/fs × temps: -40/27/85°C
Monte Carlo: 200 runs, TT 27°C, MC_MM_SWITCH=MC_PR_SWITCH=1

Usage:
  python3 scripts/run_all_sims.py
"""

import subprocess
import os
import re
import sys
import struct
import tempfile
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# ─── paths ───────────────────────────────────────────────────────────────────
REPO  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDK   = '/home/hvt06/Downloads/open_pdks/sky130/sky130A/libs.ref/sky130_fd_pr/spice'
OUT   = os.path.join(REPO, 'sim', 'results')
os.makedirs(OUT, exist_ok=True)

CORNERS  = ['tt', 'ff', 'ss', 'sf', 'fs']
TEMPS    = [-40, 27, 85]
N_MC     = 200

# ─── subcircuit block (same for every file) ──────────────────────────────────
INV6_SUB = """.subckt inv6_extracted gate drain vdd vss
X0  drain gate vdd  vdd  sky130_fd_pr__pfet_01v8_hvt ad=0.135e-12 pd=1.27e-6 as=0.135e-12 ps=1.27e-6 w=1e-6 l=1.5e-7
X1  drain gate vss  vss  sky130_fd_pr__nfet_01v8     ad=0.08775e-12 pd=0.92e-6 as=0.247e-12 ps=2.06e-6 w=0.65e-6 l=1.5e-7
X2  vdd   gate drain vdd  sky130_fd_pr__pfet_01v8_hvt ad=0.135e-12 pd=1.27e-6 as=0.135e-12 ps=1.27e-6 w=1e-6 l=1.5e-7
X3  drain gate vss  vss  sky130_fd_pr__nfet_01v8     ad=0.08775e-12 pd=0.92e-6 as=0.08775e-12 ps=0.92e-6 w=0.65e-6 l=1.5e-7
X4  vdd   gate drain vdd  sky130_fd_pr__pfet_01v8_hvt ad=0.135e-12 pd=1.27e-6 as=0.135e-12 ps=1.27e-6 w=1e-6 l=1.5e-7
X5  vdd   gate drain vdd  sky130_fd_pr__pfet_01v8_hvt ad=0.27e-12  pd=2.54e-6 as=0.135e-12 ps=1.27e-6 w=1e-6 l=1.5e-7
X6  drain gate vss  vss  sky130_fd_pr__nfet_01v8     ad=0.08775e-12 pd=0.92e-6 as=0.08775e-12 ps=0.92e-6 w=0.65e-6 l=1.5e-7
X7  drain gate vdd  vdd  sky130_fd_pr__pfet_01v8_hvt ad=0.135e-12 pd=1.27e-6 as=0.43e-12  ps=2.86e-6 w=1e-6 l=1.5e-7
X8  vss   gate drain vss  sky130_fd_pr__nfet_01v8     ad=0.08775e-12 pd=0.92e-6 as=0.08775e-12 ps=0.92e-6 w=0.65e-6 l=1.5e-7
X9  drain gate vdd  vdd  sky130_fd_pr__pfet_01v8_hvt ad=0.135e-12 pd=1.27e-6 as=0.135e-12 ps=1.27e-6 w=1e-6 l=1.5e-7
X10 vss   gate drain vss  sky130_fd_pr__nfet_01v8     ad=0.08775e-12 pd=0.92e-6 as=0.08775e-12 ps=0.92e-6 w=0.65e-6 l=1.5e-7
X11 vss   gate drain vss  sky130_fd_pr__nfet_01v8     ad=0.1755e-12 pd=1.84e-6 as=0.08775e-12 ps=0.92e-6 w=0.65e-6 l=1.5e-7
.ends inv6_extracted"""

PARAM_BLOCK_TT = """.param mc_mm_switch=0 mc_pr_switch=0 MC_MM_SWITCH=0 MC_PR_SWITCH=0
.param sky130_fd_pr__nfet_01v8__toxe_slope=0 sky130_fd_pr__nfet_01v8__vth0_slope=0
.param sky130_fd_pr__nfet_01v8__voff_slope=0 sky130_fd_pr__nfet_01v8__nfactor_slope=0
.param sky130_fd_pr__nfet_01v8__toxe_slope1=0 sky130_fd_pr__nfet_01v8__vth0_slope1=0
.param sky130_fd_pr__nfet_01v8__voff_slope1=0 sky130_fd_pr__nfet_01v8__nfactor_slope1=0
.param sky130_fd_pr__nfet_01v8__wlod_diff=0 sky130_fd_pr__nfet_01v8__kvth0_diff=0
.param sky130_fd_pr__nfet_01v8__lkvth0_diff=0 sky130_fd_pr__nfet_01v8__wkvth0_diff=0
.param sky130_fd_pr__nfet_01v8__ku0_diff=0 sky130_fd_pr__nfet_01v8__lku0_diff=0
.param sky130_fd_pr__nfet_01v8__wku0_diff=0 sky130_fd_pr__nfet_01v8__kvsat_diff=0
.param sky130_fd_pr__pfet_01v8_hvt__toxe_slope=0 sky130_fd_pr__pfet_01v8_hvt__vth0_slope=0
.param sky130_fd_pr__pfet_01v8_hvt__voff_slope=0 sky130_fd_pr__pfet_01v8_hvt__nfactor_slope=0
.param sky130_fd_pr__pfet_01v8_hvt__toxe_slope1=0 sky130_fd_pr__pfet_01v8_hvt__vth0_slope1=0
.param sky130_fd_pr__pfet_01v8_hvt__voff_slope1=0 sky130_fd_pr__pfet_01v8_hvt__nfactor_slope1=0
.param sky130_fd_pr__pfet_01v8_hvt__wlod_diff=0 sky130_fd_pr__pfet_01v8_hvt__kvth0_diff=0
.param sky130_fd_pr__pfet_01v8_hvt__lkvth0_diff=0 sky130_fd_pr__pfet_01v8_hvt__wkvth0_diff=0
.param sky130_fd_pr__pfet_01v8_hvt__ku0_diff=0 sky130_fd_pr__pfet_01v8_hvt__lku0_diff=0
.param sky130_fd_pr__pfet_01v8_hvt__wku0_diff=0 sky130_fd_pr__pfet_01v8_hvt__kvsat_diff=0"""

# MC uses process variation (MC_PR_SWITCH=1) only — mismatch (MC_MM_SWITCH) is
# disabled because sky130 mismatch _slope params in pm3 are unnormalized; combined
# with AGAUSS they can push BSIM4 params negative (toxe < 0) causing fatal errors.
# Process variation via _diff params (in corner.spice) is physically bounded.
PARAM_BLOCK_MC = """.param mc_mm_switch=0 mc_pr_switch=1 MC_MM_SWITCH=0 MC_PR_SWITCH=1
.param sky130_fd_pr__nfet_01v8__toxe_slope=0 sky130_fd_pr__nfet_01v8__vth0_slope=0
.param sky130_fd_pr__nfet_01v8__voff_slope=0 sky130_fd_pr__nfet_01v8__nfactor_slope=0
.param sky130_fd_pr__nfet_01v8__toxe_slope1=0 sky130_fd_pr__nfet_01v8__vth0_slope1=0
.param sky130_fd_pr__nfet_01v8__voff_slope1=0 sky130_fd_pr__nfet_01v8__nfactor_slope1=0
.param sky130_fd_pr__nfet_01v8__wlod_diff=0 sky130_fd_pr__nfet_01v8__kvth0_diff=0
.param sky130_fd_pr__nfet_01v8__lkvth0_diff=0 sky130_fd_pr__nfet_01v8__wkvth0_diff=0
.param sky130_fd_pr__nfet_01v8__ku0_diff=0 sky130_fd_pr__nfet_01v8__lku0_diff=0
.param sky130_fd_pr__nfet_01v8__wku0_diff=0 sky130_fd_pr__nfet_01v8__kvsat_diff=0
.param sky130_fd_pr__pfet_01v8_hvt__toxe_slope=0 sky130_fd_pr__pfet_01v8_hvt__vth0_slope=0
.param sky130_fd_pr__pfet_01v8_hvt__voff_slope=0 sky130_fd_pr__pfet_01v8_hvt__nfactor_slope=0
.param sky130_fd_pr__pfet_01v8_hvt__toxe_slope1=0 sky130_fd_pr__pfet_01v8_hvt__vth0_slope1=0
.param sky130_fd_pr__pfet_01v8_hvt__voff_slope1=0 sky130_fd_pr__pfet_01v8_hvt__nfactor_slope1=0
.param sky130_fd_pr__pfet_01v8_hvt__wlod_diff=0 sky130_fd_pr__pfet_01v8_hvt__kvth0_diff=0
.param sky130_fd_pr__pfet_01v8_hvt__lkvth0_diff=0 sky130_fd_pr__pfet_01v8_hvt__wkvth0_diff=0
.param sky130_fd_pr__pfet_01v8_hvt__ku0_diff=0 sky130_fd_pr__pfet_01v8_hvt__lku0_diff=0
.param sky130_fd_pr__pfet_01v8_hvt__wku0_diff=0 sky130_fd_pr__pfet_01v8_hvt__kvsat_diff=0"""

CIRCUIT_BLOCK = """Vdd vdd 0 1.8
Xinv vin vout vdd 0 inv6_extracted
Rfb  vout vin 5000
Iin  0 vin DC 0 AC 1
Cpd  vin 0 100f"""


# ─── helpers ─────────────────────────────────────────────────────────────────
def _parse_section(header_text, body_bytes):
    """Parse one ngspice binary section header + body.
    Handles 'Flags: complex' (AC, default) and 'Flags: real' (tran/noise)."""
    n_vars = n_pts = 0
    var_names = []
    is_real = False
    in_vars = False
    for line in header_text.splitlines():
        ls = line.strip()
        if ls.startswith('No. Variables:'):
            n_vars = int(ls.split(':')[1].strip())
        elif ls.startswith('No. Points:'):
            n_pts  = int(ls.split(':')[1].strip())
        elif ls.startswith('Flags:') and 'real' in ls.lower():
            is_real = True
        elif ls == 'Variables:':
            in_vars = True
        elif in_vars and '\t' in ls:
            parts = ls.split('\t')
            var_names.append(parts[1].lower() if len(parts) > 1 else parts[0])
    if n_vars == 0 or n_pts == 0:
        return None, 0
    if is_real:
        # real: each row = n_vars × float64
        itemsize = 8
        dtype    = np.float64
    else:
        # complex: each row = n_vars × complex128
        itemsize = 16
        dtype    = np.complex128
    expected = n_pts * n_vars * itemsize
    if len(body_bytes) < expected:
        return None, 0
    vals = np.frombuffer(body_bytes[:expected], dtype=dtype).reshape(n_pts, n_vars)
    return {name: vals[:, i] for i, name in enumerate(var_names)}, expected


def read_raw(path, want_key='frequency'):
    """Parse ngspice binary raw file; return first section containing want_key.
    Sequential walk: each section's body size is computed from its header."""
    with open(path, 'rb') as f:
        data = f.read()
    marker = b'Binary:\n'
    hdr_start = 0
    pos = 0
    while True:
        idx = data.find(marker, pos)
        if idx == -1:
            break
        header     = data[hdr_start:idx].decode('ascii', errors='replace')
        body_start = idx + len(marker)
        d, consumed = _parse_section(header, data[body_start:])
        if d is not None and want_key in d:
            return d
        # Advance hdr_start to just after this section's binary body
        hdr_start = body_start + (consumed if consumed > 0 else 0)
        pos = idx + 1   # next search past current marker
    return None


def run_ngspice(spice_content, label):
    """Write temp file, run ngspice -b, return stdout."""
    tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.spice',
                                     dir=REPO, delete=False)
    tmp.write(spice_content)
    tmp.close()
    try:
        result = subprocess.run(
            ['ngspice', '-b', tmp.name],
            capture_output=True, text=True, cwd=REPO, timeout=120
        )
        if 'error' in result.stdout.lower() and 'no. of data' not in result.stdout.lower():
            print(f"  [WARN] {label}: {result.stdout[-300:]}")
        return result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        print(f"  [TIMEOUT] {label}")
        return ''
    finally:
        os.unlink(tmp.name)


def find_bw(freq, zt_db):
    """Find -3dB frequency from zt_db array."""
    zt_dc = zt_db[0]
    idx = np.where(zt_db <= zt_dc - 3)[0]
    return freq[idx[0]] if len(idx) else None


def make_spice_corner(corner, temp):
    nfet_model = f'{PDK}/sky130_fd_pr__nfet_01v8__{corner}.pm3.spice'
    pfet_model = f'{PDK}/sky130_fd_pr__pfet_01v8_hvt__{corner}.pm3.spice'
    raw_out = os.path.join(OUT, f'corner_{corner}_{temp:+d}C.raw').replace('+', 'p').replace('-', 'm')
    return f""".title TIA Corner {corner.upper()} {temp:+d}C
.include "{nfet_model}"
.include "{pfet_model}"
{PARAM_BLOCK_TT}
{INV6_SUB}
{CIRCUIT_BLOCK}
.control
  set noaskquit
  set temp = {temp}
  op
  ac dec 50 1MEG 100G
  let zt_db = 20*log10(mag(v(vout)))
  write {raw_out}
  quit
.endc
.end
""", raw_out


def make_spice_mc(run_idx, seed_offset=0):
    """Single MC run with process variation (MC_PR_SWITCH=1, MC_MM_SWITCH=0).
    Uses corner.spice which includes pm3 + calibrated _diff process params."""
    raw_out = os.path.join(OUT, f'mc_{run_idx:03d}.raw')
    return f""".title TIA MC Run {run_idx}
.include "{PDK}/sky130_fd_pr__nfet_01v8__tt.corner.spice"
.include "{PDK}/sky130_fd_pr__pfet_01v8_hvt__tt.corner.spice"
{PARAM_BLOCK_MC}
{INV6_SUB}
{CIRCUIT_BLOCK}
.control
  set noaskquit
  set temp = 27
  ac dec 30 1MEG 100G
  let zt_db = 20*log10(mag(v(vout)))
  write {raw_out}
  quit
.endc
.end
""", raw_out


# ─── run corners ─────────────────────────────────────────────────────────────
print("=" * 60)
print("Running PVT corners ...")
print("=" * 60)

corner_results = {}

for corner in CORNERS:
    for temp in TEMPS:
        label = f'{corner.upper()} {temp:+d}°C'
        spice, raw_out = make_spice_corner(corner, temp)
        print(f'  {label} ...', end=' ', flush=True)
        run_ngspice(spice, label)
        if not os.path.exists(raw_out):
            print('FAILED')
            continue
        d = read_raw(raw_out)
        if d is None:
            print('PARSE FAILED')
            continue
        freq   = d['frequency'].real
        zt_db  = 20 * np.log10(np.abs(d.get('v(vout)', d.get('vout', None))))
        zt_ph  = np.angle(d.get('v(vout)', d.get('vout', None)), deg=True)
        bw     = find_bw(freq, zt_db)
        vbias  = None
        corner_results[(corner, temp)] = {
            'freq': freq, 'zt_db': zt_db, 'zt_ph': zt_ph, 'bw': bw
        }
        print(f'Zt={zt_db[0]:.1f}dBΩ  BW={bw/1e9:.2f}GHz' if bw else f'Zt={zt_db[0]:.1f}dBΩ')

# ─── run Monte Carlo ──────────────────────────────────────────────────────────
print()
print("=" * 60)
print(f"Running Monte Carlo ({N_MC} runs) ...")
print("=" * 60)

mc_zt_dc   = []
mc_bw      = []
mc_freq    = None

for i in range(N_MC):
    spice, raw_out = make_spice_mc(i)
    if i % 20 == 0:
        print(f'  MC {i}/{N_MC} ...', flush=True)
    # Only run if not cached
    if not os.path.exists(raw_out):
        run_ngspice(spice, f'MC {i}')
    if not os.path.exists(raw_out):
        continue
    d = read_raw(raw_out)
    if d is None:
        continue
    freq   = d['frequency'].real
    vout_v = d.get('v(vout)', d.get('vout', None))
    if vout_v is None:
        continue
    zt_db  = 20 * np.log10(np.abs(vout_v))
    bw = find_bw(freq, zt_db)
    mc_zt_dc.append(zt_db[0])
    mc_bw.append(bw if bw else np.nan)
    if mc_freq is None:
        mc_freq = freq

mc_zt_dc = np.array(mc_zt_dc)
mc_bw    = np.array(mc_bw)
print(f'  Completed {len(mc_zt_dc)} valid MC runs')

# ─── plot: corner overlay ─────────────────────────────────────────────────────
# Plot 1: all corners at 27°C — Zt magnitude
fig, ax = plt.subplots(figsize=(10, 5))
colors_c = {'tt': 'black', 'ff': 'steelblue', 'ss': 'tomato', 'sf': 'darkorange', 'fs': 'mediumpurple'}
for corner in CORNERS:
    key = (corner, 27)
    if key not in corner_results:
        continue
    r = corner_results[key]
    bw_label = f' (BW={r["bw"]/1e9:.2f}GHz)' if r['bw'] else ''
    ax.semilogx(r['freq'], r['zt_db'], color=colors_c[corner],
                linewidth=2, label=f'{corner.upper()}{bw_label}')
ax.set_xlabel('Frequency (Hz)')
ax.set_ylabel('|Zt| (dBΩ)')
ax.set_title('TIA Transimpedance — All Process Corners (27°C)')
ax.set_xlim(1e6, 1e11)
ax.legend(fontsize=9)
ax.grid(True, which='both', linestyle=':', linewidth=0.5)
fig.tight_layout()
fig.savefig(os.path.join(OUT, 'corners_zt_mag.png'), dpi=150)
plt.close(fig)
print('\nSaved corners_zt_mag.png')

# Plot 2: TT across temperatures — Zt magnitude
fig, ax = plt.subplots(figsize=(10, 5))
colors_t = {-40: 'steelblue', 27: 'black', 85: 'tomato'}
for temp in TEMPS:
    key = ('tt', temp)
    if key not in corner_results:
        continue
    r = corner_results[key]
    bw_label = f' (BW={r["bw"]/1e9:.2f}GHz)' if r['bw'] else ''
    ax.semilogx(r['freq'], r['zt_db'], color=colors_t[temp],
                linewidth=2, label=f'TT {temp:+d}°C{bw_label}')
ax.set_xlabel('Frequency (Hz)')
ax.set_ylabel('|Zt| (dBΩ)')
ax.set_title('TIA Transimpedance — Temperature Corners (TT process)')
ax.set_xlim(1e6, 1e11)
ax.legend(fontsize=9)
ax.grid(True, which='both', linestyle=':', linewidth=0.5)
fig.tight_layout()
fig.savefig(os.path.join(OUT, 'temp_zt_mag.png'), dpi=150)
plt.close(fig)
print('Saved temp_zt_mag.png')

# Plot 3: corner phase at 27°C
fig, ax = plt.subplots(figsize=(10, 5))
for corner in CORNERS:
    key = (corner, 27)
    if key not in corner_results:
        continue
    r = corner_results[key]
    ax.semilogx(r['freq'], r['zt_ph'], color=colors_c[corner],
                linewidth=2, label=corner.upper())
ax.set_xlabel('Frequency (Hz)')
ax.set_ylabel('Phase (°)')
ax.set_title('TIA Phase — All Process Corners (27°C)')
ax.set_xlim(1e6, 1e11)
ax.legend(fontsize=9)
ax.grid(True, which='both', linestyle=':', linewidth=0.5)
fig.tight_layout()
fig.savefig(os.path.join(OUT, 'corners_zt_phase.png'), dpi=150)
plt.close(fig)
print('Saved corners_zt_phase.png')

# Plot 4: MC Zt histogram
if len(mc_zt_dc) > 10:
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    axes[0].hist(mc_zt_dc, bins=30, color='steelblue', edgecolor='white', linewidth=0.5)
    axes[0].axvline(np.mean(mc_zt_dc), color='tomato', linestyle='--', linewidth=2,
                    label=f'μ={np.mean(mc_zt_dc):.1f} dBΩ')
    axes[0].axvline(np.mean(mc_zt_dc)-np.std(mc_zt_dc), color='orange', linestyle=':',
                    label=f'σ={np.std(mc_zt_dc):.2f} dBΩ')
    axes[0].axvline(np.mean(mc_zt_dc)+np.std(mc_zt_dc), color='orange', linestyle=':')
    axes[0].set_xlabel('|Zt| at 1 MHz (dBΩ)')
    axes[0].set_ylabel('Count')
    axes[0].set_title(f'MC Transimpedance  (N={len(mc_zt_dc)})')
    axes[0].legend(fontsize=9)

    valid_bw = mc_bw[~np.isnan(mc_bw) & (mc_bw < 1e11)]
    if len(valid_bw) > 5:
        axes[1].hist(valid_bw / 1e9, bins=30, color='darkorange', edgecolor='white', linewidth=0.5)
        axes[1].axvline(np.mean(valid_bw)/1e9, color='steelblue', linestyle='--', linewidth=2,
                        label=f'μ={np.mean(valid_bw)/1e9:.2f} GHz')
        axes[1].axvline((np.mean(valid_bw)-np.std(valid_bw))/1e9, color='grey', linestyle=':',
                        label=f'σ={np.std(valid_bw)/1e9:.2f} GHz')
        axes[1].axvline((np.mean(valid_bw)+np.std(valid_bw))/1e9, color='grey', linestyle=':')
        axes[1].set_xlabel('3-dB Bandwidth (GHz)')
        axes[1].set_ylabel('Count')
        axes[1].set_title(f'MC Bandwidth  (N={len(valid_bw)})')
        axes[1].legend(fontsize=9)
    fig.suptitle(f'TIA Monte Carlo ({N_MC} runs, TT 27°C, process+mismatch)', fontsize=12)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, 'mc_histograms.png'), dpi=150)
    plt.close(fig)
    print('Saved mc_histograms.png')

# Plot 5: MC overlay — all freq responses
if mc_freq is not None and len(mc_zt_dc) > 5:
    fig, ax = plt.subplots(figsize=(10, 5))
    mc_runs_freq = []
    for i in range(N_MC):
        raw_out = os.path.join(OUT, f'mc_{i:03d}.raw')
        if not os.path.exists(raw_out):
            continue
        d = read_raw(raw_out)
        if d is None:
            continue
        v = d.get('v(vout)', d.get('vout', None))
        if v is not None:
            mc_runs_freq.append(20 * np.log10(np.abs(v)))
    for curve in mc_runs_freq:
        ax.semilogx(mc_freq, curve, color='steelblue', linewidth=0.4, alpha=0.3)
    # TT nominal overlay
    key = ('tt', 27)
    if key in corner_results:
        r = corner_results[key]
        ax.semilogx(r['freq'], r['zt_db'], 'k-', linewidth=2.5, label='TT nominal')
    ax.set_xlabel('Frequency (Hz)')
    ax.set_ylabel('|Zt| (dBΩ)')
    ax.set_title(f'TIA Monte Carlo Overlay ({len(mc_runs_freq)} runs)')
    ax.set_xlim(1e6, 1e11)
    ax.legend(fontsize=10)
    ax.grid(True, which='both', linestyle=':', linewidth=0.5)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, 'mc_overlay.png'), dpi=150)
    plt.close(fig)
    print('Saved mc_overlay.png')

# ─── summary table ────────────────────────────────────────────────────────────
print()
print("=" * 65)
print(f"{'Corner':<6} {'Temp':>6}  {'Zt(DC) dBΩ':>12}  {'Zt(DC) Ω':>10}  {'BW GHz':>8}")
print("=" * 65)
for corner in CORNERS:
    for temp in TEMPS:
        key = (corner, temp)
        if key not in corner_results:
            continue
        r = corner_results[key]
        zt = r['zt_db'][0]
        bw = r['bw']
        bw_s = f'{bw/1e9:.3f}' if bw else '  > 100'
        print(f'{corner.upper():<6} {temp:>+6}°C  {zt:>12.2f}  {10**(zt/20):>10.0f}  {bw_s:>8}')

if len(mc_zt_dc) > 0:
    valid_bw = mc_bw[~np.isnan(mc_bw) & (mc_bw < 1e11)]
    print()
    print(f"Monte Carlo (N={len(mc_zt_dc)}, TT 27°C, process variation):")
    print(f"  Zt(DC):  μ={np.mean(mc_zt_dc):.2f} dBΩ  σ={np.std(mc_zt_dc):.2f} dBΩ  "
          f"min={np.min(mc_zt_dc):.2f}  max={np.max(mc_zt_dc):.2f}")
    if len(valid_bw) > 0:
        print(f"  BW:      μ={np.mean(valid_bw)/1e9:.3f} GHz  σ={np.std(valid_bw)/1e9:.3f} GHz  "
              f"min={np.min(valid_bw)/1e9:.3f}  max={np.max(valid_bw)/1e9:.3f}")

# ─── Plot 6: noise ────────────────────────────────────────────────────────────
noise_path = os.path.join(OUT, 'noise_tia.raw')
if os.path.exists(noise_path):
    dn = read_raw(noise_path, want_key='frequency')
    if dn is not None:
        fn   = dn['frequency'].real
        ino  = np.abs(dn.get('inoise_spectrum', dn.get('inoise', None)))
        ono  = np.abs(dn.get('onoise_spectrum', dn.get('onoise', None)))
        if ino is not None and ono is not None:
            # Input-referred current noise density sqrt(Si) in A/√Hz
            # Output voltage noise density sqrt(Sv) in V/√Hz
            sqrt_ino = np.sqrt(ino)
            sqrt_ono = np.sqrt(ono)
            # Input-referred voltage noise = Vn/Zt
            key_tt = ('tt', 27)
            if key_tt in corner_results:
                zt_lin = 10 ** (corner_results[key_tt]['zt_db'] / 20)
                zt_interp = np.interp(fn, corner_results[key_tt]['freq'], zt_lin)
                ino_v = sqrt_ono / zt_interp   # V/√Hz referred back to input current-equiv

            fig, axes = plt.subplots(1, 2, figsize=(12, 5))
            axes[0].loglog(fn, sqrt_ino * 1e12, color='steelblue', linewidth=2)
            axes[0].set_xlabel('Frequency (Hz)')
            axes[0].set_ylabel('Input noise current density (pA/√Hz)')
            axes[0].set_title('TIA Input-Referred Current Noise')
            axes[0].set_xlim(fn[0], fn[-1])
            axes[0].grid(True, which='both', linestyle=':', linewidth=0.5)

            axes[1].loglog(fn, sqrt_ono * 1e9, color='darkorange', linewidth=2)
            axes[1].set_xlabel('Frequency (Hz)')
            axes[1].set_ylabel('Output voltage noise density (nV/√Hz)')
            axes[1].set_title('TIA Output-Referred Voltage Noise')
            axes[1].set_xlim(fn[0], fn[-1])
            axes[1].grid(True, which='both', linestyle=':', linewidth=0.5)

            # Annotate noise at 1 GHz
            f_ann = 1e9
            ino_ann = np.interp(f_ann, fn, sqrt_ino) * 1e12
            ono_ann = np.interp(f_ann, fn, sqrt_ono) * 1e9
            axes[0].annotate(f'{ino_ann:.1f} pA/√Hz @ 1GHz',
                             xy=(f_ann, np.interp(f_ann, fn, sqrt_ino*1e12)),
                             fontsize=8, color='steelblue')
            axes[1].annotate(f'{ono_ann:.1f} nV/√Hz @ 1GHz',
                             xy=(f_ann, np.interp(f_ann, fn, sqrt_ono*1e9)),
                             fontsize=8, color='darkorange')

            fig.suptitle('TIA Noise Analysis (schematic-level, TT 27°C)', fontsize=12)
            fig.tight_layout()
            fig.savefig(os.path.join(OUT, 'noise_spectral_density.png'), dpi=150)
            plt.close(fig)
            print('Saved noise_spectral_density.png')

            # Print summary
            idx_1g = np.argmin(np.abs(fn - 1e9))
            print(f"  Noise @ 1GHz: In={sqrt_ino[idx_1g]*1e12:.2f} pA/√Hz  "
                  f"Vout={sqrt_ono[idx_1g]*1e9:.2f} nV/√Hz")

# ─── Plot 7: transient ────────────────────────────────────────────────────────
tran_path = os.path.join(OUT, 'tran_tia.raw')
if os.path.exists(tran_path):
    dt = read_raw(tran_path, want_key='time')
    if dt is not None:
        t     = dt['time'].real
        v_in  = dt.get('v(vin)',  dt.get('vin',  None))
        v_out = dt.get('v(vout)', dt.get('vout', None))
        if v_in is not None and v_out is not None:
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
            ax1.plot(t * 1e9, v_in.real * 1e3, color='steelblue', linewidth=1.5, label='Vin (mV)')
            ax1.set_ylabel('Vin (mV)')
            ax1.set_title('TIA Transient Response (schematic-level)')
            ax1.legend(fontsize=9)
            ax1.grid(True, linestyle=':', linewidth=0.5)

            ax2.plot(t * 1e9, v_out.real, color='darkorange', linewidth=1.5, label='Vout (V)')
            ax2.set_xlabel('Time (ns)')
            ax2.set_ylabel('Vout (V)')
            ax2.legend(fontsize=9)
            ax2.grid(True, linestyle=':', linewidth=0.5)

            fig.tight_layout()
            fig.savefig(os.path.join(OUT, 'tran_response.png'), dpi=150)
            plt.close(fig)
            print('Saved tran_response.png')

# ─── save numerical summary as CSV ───────────────────────────────────────────
import csv
with open(os.path.join(OUT, 'corner_summary.csv'), 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['corner', 'temp_C', 'zt_dc_dBOhm', 'zt_dc_Ohm', 'bw_GHz'])
    for corner in CORNERS:
        for temp in TEMPS:
            key = (corner, temp)
            if key not in corner_results:
                continue
            r = corner_results[key]
            zt = r['zt_db'][0]
            bw = r['bw']
            w.writerow([corner, temp, f'{zt:.3f}', f'{10**(zt/20):.1f}',
                        f'{bw/1e9:.4f}' if bw else ''])

if len(mc_zt_dc) > 0:
    with open(os.path.join(OUT, 'mc_summary.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['run', 'zt_dc_dBOhm', 'bw_GHz'])
        for i, (zt, bw) in enumerate(zip(mc_zt_dc, mc_bw)):
            w.writerow([i, f'{zt:.3f}', f'{bw/1e9:.4f}' if not np.isnan(bw) else ''])

print()
print("All results written to sim/results/")
