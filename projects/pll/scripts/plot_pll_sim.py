#!/usr/bin/env python3
"""
Plot PLL transient simulation results from ngspice TSV output.
Generates PNG plots: Vctrl settling, VCO/div/ref waveforms, UP/DN pulses.
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJ_DIR = os.path.dirname(SCRIPT_DIR)
TSV_FILE = os.path.join(PROJ_DIR, "sim", "results", "pll_full_tran_v2.tsv")
OUT_DIR = os.path.join(PROJ_DIR, "sim", "results")

def load_tsv(path):
    """Load ngspice paired-column output: (time, v(sig)) repeated per signal."""
    with open(path) as f:
        header = f.readline().strip().split()
    # Column names: time, v(vctrl), time, v(vco_out), ...
    signal_names = []
    for i in range(1, len(header), 2):
        name = header[i].strip()
        signal_names.append(name)
    data = np.loadtxt(path, skiprows=1)
    signals = {}
    for i, name in enumerate(signal_names):
        t_col = i * 2
        v_col = i * 2 + 1
        signals[name] = (data[:, t_col], data[:, v_col])
    return signals


def plot_vctrl_settling(signals):
    """Plot control voltage settling during PLL lock."""
    t, v = signals['v(vctrl)']
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(t * 1e6, v, color='steelblue', linewidth=1.0)
    ax.axhline(1.016, color='tomato', linestyle='--', linewidth=0.8, label='Vctrl_target ≈ 1.016V')
    ax.set_xlabel('Time (µs)')
    ax.set_ylabel('Vctrl (V)')
    ax.set_title('PLL Control Voltage Settling')
    ax.set_xlim(0, t[-1] * 1e6)
    ax.set_ylim(0.5, 1.2)
    ax.legend(loc='lower right')
    ax.grid(True, linestyle=':', linewidth=0.5)
    fig.tight_layout()
    path = os.path.join(OUT_DIR, 'pll_vctrl_settling.png')
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  {path}")
    return path


def plot_lock_zoom(signals):
    """Zoom into first 1µs showing lock acquisition."""
    t, v = signals['v(vctrl)']
    mask = t <= 1e-6
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(t[mask] * 1e9, v[mask], color='steelblue', linewidth=1.0)
    ax.set_xlabel('Time (ns)')
    ax.set_ylabel('Vctrl (V)')
    ax.set_title('PLL Lock Acquisition (first 1 µs)')
    ax.grid(True, linestyle=':', linewidth=0.5)
    fig.tight_layout()
    path = os.path.join(OUT_DIR, 'pll_lock_zoom.png')
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  {path}")
    return path


def plot_waveforms_locked(signals):
    """Plot ref_clk, div_clk, vco_out when locked (last 50ns)."""
    t_ref, v_ref = signals['v(ref_clk)']
    t_div, v_div = signals['v(div_clk)']
    t_vco, v_vco = signals['v(vco_out)']

    # Zoom into last 50 ns
    t_end = t_ref[-1]
    t_start = t_end - 50e-9
    mask_ref = (t_ref >= t_start)
    mask_div = (t_div >= t_start)
    mask_vco = (t_vco >= t_start)

    fig, axes = plt.subplots(3, 1, figsize=(10, 7), sharex=True)

    axes[0].plot(t_ref[mask_ref] * 1e9, v_ref[mask_ref], color='#2196F3', linewidth=1)
    axes[0].set_ylabel('ref_clk (V)')
    axes[0].set_title('PLL Locked Waveforms (last 50 ns)')
    axes[0].set_ylim(-0.1, 1.9)
    axes[0].grid(True, linestyle=':', linewidth=0.5)

    axes[1].plot(t_div[mask_div] * 1e9, v_div[mask_div], color='#4CAF50', linewidth=1)
    axes[1].set_ylabel('div_clk (V)')
    axes[1].set_ylim(-0.1, 1.9)
    axes[1].grid(True, linestyle=':', linewidth=0.5)

    axes[2].plot(t_vco[mask_vco] * 1e9, v_vco[mask_vco], color='#FF5722', linewidth=1)
    axes[2].set_ylabel('vco_out (V)')
    axes[2].set_xlabel('Time (ns)')
    axes[2].set_ylim(-0.1, 1.9)
    axes[2].grid(True, linestyle=':', linewidth=0.5)

    fig.tight_layout()
    path = os.path.join(OUT_DIR, 'pll_locked_waveforms.png')
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  {path}")
    return path


def plot_up_dn_pulses(signals):
    """Plot UP/DN charge pump control signals during lock."""
    t_up, v_up = signals['v(up)']
    t_dn, v_dn = signals['v(dn)']

    # Show 200ns window around 1µs (during settling)
    t0, t1 = 0.8e-6, 1.0e-6
    mask_up = (t_up >= t0) & (t_up <= t1)
    mask_dn = (t_dn >= t0) & (t_dn <= t1)

    fig, axes = plt.subplots(2, 1, figsize=(10, 4), sharex=True)

    axes[0].plot(t_up[mask_up] * 1e9, v_up[mask_up], color='#E91E63', linewidth=1)
    axes[0].set_ylabel('UP (V)')
    axes[0].set_title('PFD UP/DN Pulses (800–1000 ns)')
    axes[0].set_ylim(-0.1, 1.9)
    axes[0].grid(True, linestyle=':', linewidth=0.5)

    axes[1].plot(t_dn[mask_dn] * 1e9, v_dn[mask_dn], color='#9C27B0', linewidth=1)
    axes[1].set_ylabel('DN (V)')
    axes[1].set_xlabel('Time (ns)')
    axes[1].set_ylim(-0.1, 1.9)
    axes[1].grid(True, linestyle=':', linewidth=0.5)

    fig.tight_layout()
    path = os.path.join(OUT_DIR, 'pll_up_dn_pulses.png')
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  {path}")
    return path


def plot_vco_frequency(signals):
    """Estimate instantaneous VCO frequency from zero crossings."""
    t, v = signals['v(vco_out)']
    # Find rising zero crossings
    threshold = 0.9
    crossings = []
    for i in range(1, len(v)):
        if v[i-1] < threshold <= v[i]:
            # Linear interpolation
            frac = (threshold - v[i-1]) / (v[i] - v[i-1])
            tc = t[i-1] + frac * (t[i] - t[i-1])
            crossings.append(tc)
    crossings = np.array(crossings)

    if len(crossings) < 3:
        print("  Not enough VCO crossings for frequency plot")
        return None

    periods = np.diff(crossings)
    freq = 1.0 / periods / 1e6  # MHz
    t_mid = (crossings[:-1] + crossings[1:]) / 2

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(t_mid * 1e6, freq, color='#FF9800', linewidth=0.5, alpha=0.7)
    ax.axhline(400, color='tomato', linestyle='--', linewidth=0.8, label='Target: 400 MHz')
    ax.set_xlabel('Time (µs)')
    ax.set_ylabel('VCO Frequency (MHz)')
    ax.set_title('Instantaneous VCO Frequency')
    ax.set_xlim(0, t[-1] * 1e6)
    ax.set_ylim(200, 600)
    ax.legend()
    ax.grid(True, linestyle=':', linewidth=0.5)
    fig.tight_layout()
    path = os.path.join(OUT_DIR, 'pll_vco_frequency.png')
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  {path}")
    return path


def main():
    print("PLL Simulation Plots")
    print(f"  Input: {TSV_FILE}")
    print()

    if not os.path.exists(TSV_FILE):
        print(f"ERROR: TSV file not found: {TSV_FILE}")
        print("Run the ngspice simulation first:")
        print("  ngspice -b projects/pll/sim/pll_full_tran_v2.spice")
        return

    signals = load_tsv(TSV_FILE)
    print(f"  Loaded {len(signals)} signals: {', '.join(signals.keys())}")
    print()

    plot_vctrl_settling(signals)
    plot_lock_zoom(signals)
    plot_waveforms_locked(signals)
    plot_up_dn_pulses(signals)
    plot_vco_frequency(signals)

    print("\nAll plots generated.")


if __name__ == "__main__":
    main()
