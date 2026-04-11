# PLL Design Document — Ring-Oscillator PLL, Sky130A

## 1. Architecture Overview

### 1.1 Block Diagram

```
                         ┌─────────────────────────────────────────────────┐
                         │              PLL Top-Level                       │
                         │                                                  │
  ua[0] ──►  REF_CLK ──►│  ┌─────┐   ┌──────┐   ┌──────┐   ┌──────────┐ │
  (Analog    Input       │  │ PFD │──►│  CP  │──►│ Loop │──►│ Ring VCO │─┼──► VCO_OUT
   Pin)                  │  │     │   │      │   │Filter│   │ (5-stg)  │ │
                         │  └──┬──┘   └──────┘   └──────┘   └────┬─────┘ │
                         │     │                                   │       │
                         │     │    ┌──────────────────────┐       │       │
                         │     │    │  Programmable         │       │       │
                         │     └────│  Frequency Divider    │◄──────┘       │
                         │          │  /N  (N = 1..256)     │               │
                         │          └──────────┬───────────┘               │
                         │                     │                           │
                         │              DIV_OUT│                           │
                         │                     ▼                           │
                         │          ┌──────────────────────┐               │
                         │          │  Output Divider      │               │
                         │          │  /M  (M = 2,4,8,16   │──────────────┼──► ua[1]
                         │          │       32,64,128,256)  │  (Analog Pin)│
                         │          └──────────────────────┘               │
                         │                                                  │
                         │  Digital Controls (active when active):          │
                         │    ui[0..7] : N divider ratio [7:0]             │
                         │    uio[0..2]: M output divider select [2:0]     │
                         │    uio[3..6]: VCO coarse band select [3:0]      │
                         │    uio[7]   : PLL enable / reset_n              │
                         │    uo[0]    : lock_detect output                │
                         │    uo[1]    : div_out monitor                   │
                         └─────────────────────────────────────────────────┘
```

### 1.2 Design Philosophy

- **Two analog pins only**: `ua[0]` = REF_CLK input, `ua[1]` = divided output for oscilloscope
- **All tuning/control via digital pins**: `ui[7:0]`, `uio[7:0]`, `uo[7:0]`
- **Output divider /M**: brings 50-500 MHz VCO output down to scope-friendly frequencies (as low as ~200 kHz)
- **No blind zones**: coarse + fine tuning overlap ensures continuous frequency coverage
- **SKY130A 1.8V**: all transistors use `sky130_fd_pr__nfet_01v8` and `sky130_fd_pr__pfet_01v8`

---

## 2. PLL Theory

### 2.1 Phase-Locked Loop Fundamentals

A PLL is a negative-feedback control system that forces the phase of a
voltage-controlled oscillator (VCO) to track the phase of a reference clock.

**Transfer function (closed-loop):**

```
              Kpd · Kcp · F(s) · Kvco / s
H(s) = ────────────────────────────────────────
        1 + Kpd · Kcp · F(s) · Kvco / (N · s)
```

Where:
- `Kpd` = phase-frequency detector gain = 1/(2π) [V/rad] (full-range PFD)
- `Kcp` = charge-pump current [A]
- `F(s)` = loop filter transfer function [V/A]
- `Kvco` = VCO gain [rad/s/V]   (= 2π × MHz/V)
- `N` = feedback divider ratio

### 2.2 Loop Dynamics

For a 2nd-order type-II PLL with a simple RC loop filter:

```
F(s) = (1 + s·R·C₁) / (s·C₁)     [series R + C₁, with C₂=0 for now]
```

The open-loop gain becomes:

```
T(s) = Kpd · Icp · (1 + s·R·C₁) · Kvco / (N · s² · C₁)
```

**Natural frequency:**

    ωn = √(Icp · Kvco / (2π · N · C₁))

**Damping factor:**

    ζ = (R/2) · √(Icp · Kvco · C₁ / (2π · N))

**Loop bandwidth (approximate):**

    ωc ≈ 2ζ · ωn = R · Icp · Kvco / (2π · N)

Design rule of thumb: **ωc < (1/10) · ωref** for stability.

### 2.3 Phase Noise Theory

In a ring-oscillator PLL, the dominant noise sources are:

1. **VCO phase noise** (dominant outside loop BW):

       L_VCO(Δf) = (8·k·T·γ·F) / (P_osc · Q²) · (f₀/Δf)²

   For a ring oscillator, Q ~ 1-2, so phase noise is inherently poor.
   Typical: -80 to -90 dBc/Hz @ 1 MHz offset at 500 MHz.

2. **Charge pump noise** (in-band):

       L_CP(Δf) = (2·k·T·γ / gm_cp) · (Kpd·Kvco / (N·ωc))²

3. **Reference noise**: passes through with gain H(s) ≈ N inside loop BW.

4. **Divider noise**: typically negligible for CMOS dividers.

**Leeson's model adapted for ring oscillator:**

```
    L(Δf) = 10·log₁₀[ (2·F·k·T / Psig) · (1 + (f₀/(2·Q·Δf))²) · (1 + Δf_1/f³/|Δf|) ]
```

Where F = noise figure (~5-10 for ring osc), Q ~ π·N_stages/2 for ring.

### 2.4 Ring Oscillator Frequency

For an N-stage single-ended ring (each stage = CMOS inverter):

```
    f_osc = 1 / (2 · N_stages · t_pd)
```

Where t_pd = propagation delay per stage.

For a CMOS inverter `t_pd` depends on:
- Load capacitance `C_L` (gate caps + wiring + tuning varactors)
- Drive current `I_avg = (I_n + I_p) / 2`
- Supply voltage `VDD`

```
    t_pd ≈ C_L · VDD / (2 · I_avg)
```

**Number of stages:** Odd number required (3, 5, 7, 9...). We choose **5 stages**:
- 5 stages give good phase noise vs. area tradeoff
- f_osc = 1 / (10 · t_pd)
- For f_osc = 50-500 MHz: t_pd = 200 ps to 20 ps per stage

---

## 3. VCO Design

### 3.1 Topology: Current-Starved Ring Oscillator

```
        VDD
         │
    ┌────┴────┐
    │  PMOS   │ M_p_bias (current mirror — coarse tune)
    │  bias   │ W/L = 4u/1u (long L for matching)
    └────┬────┘
         │  I_bias (sets max current)
    ┌────┴────┐
    │  PMOS   │ M_p_stg (starved inverter PMOS)
    │  drive  │ W/L = 2u/150n
    └────┬────┘
         │
    in ──┤── out ──► next stage
         │
    ┌────┴────┐
    │  NMOS   │ M_n_stg (starved inverter NMOS)
    │  drive  │ W/L = 1u/150n
    └────┬────┘
         │
    ┌────┴────┐
    │  NMOS   │ M_n_bias (current mirror — coarse tune)
    │  bias   │ W/L = 2u/1u
    └────┬────┘
         │
        GND
```

### 3.2 Tuning Mechanisms

#### A. Coarse Tuning (Discrete, 4-bit)

Switch in/out parallel PMOS/NMOS current-mirror branches.
Each bit doubles the bias current:

| Bit | PMOS mirror W | NMOS mirror W | ΔI_bias (approx) |
|-----|---------------|---------------|-------------------|
| B0  | 0.5u/1u       | 0.25u/1u      | 1× (LSB)         |
| B1  | 1u/1u         | 0.5u/1u       | 2×                |
| B2  | 2u/1u         | 1u/1u         | 4×                |
| B3  | 4u/1u         | 2u/1u         | 8× (MSB)         |

Total range: code 0001 to 1111 = 1× to 15× unit current.
This provides 15 discrete frequency bands with ~30% overlap between adjacent bands
→ **no blind zones**.

#### B. Fine Tuning (Continuous — Vctrl from loop filter)

MOS varactors (`sky130_fd_pr__cap_var_lvt`) at each VCO stage output:

```
    VCO stage output ──┤├── Vctrl (from loop filter)
                    C_var(V)
```

The accumulation-mode varactor Cvar sweeps ~2:1 over 0V to VDD.
This provides continuous analog tuning within each coarse band.

**Varactor sizing (per node):**
- Nominal: W=1u, L=1u → Cvar ≈ 50-100 fF (varies with Vctrl)
- This gives Kvco ≈ 200-400 MHz/V (depends on coarse band)

#### C. No-Blind-Zone Guarantee

Design the coarse band overlap:
```
    Band_k:  f_min(k)  ──────────────── f_max(k)
    Band_k+1:       f_min(k+1) ──────────────── f_max(k+1)
                         ↑ overlap zone ↑
```

Requirement: **f_max(k) > f_min(k+1)** for all k. Achieved by ensuring
the fine-tuning range (~30-40% of band center) exceeds the coarse step size.

### 3.3 VCO Stage Sizing Summary

| Device       | Type    | W      | L      | Instance  | Notes                    |
|-------------|---------|--------|--------|-----------|--------------------------|
| M_p_drive   | PMOS    | 2.0 µm | 150 nm | per stage | Inverter pull-up         |
| M_n_drive   | NMOS    | 1.0 µm | 150 nm | per stage | Inverter pull-down       |
| M_p_bias    | PMOS    | 4.0 µm | 1.0 µm | per stage | Current-starve mirror    |
| M_n_bias    | NMOS    | 2.0 µm | 1.0 µm | per stage | Current-starve mirror    |
| C_var       | MOS cap | 1.0 µm | 1.0 µm | per node  | Varactor for fine tune   |
| M_sw_p[3:0] | PMOS    | varies  | 1.0 µm | global    | Coarse tune switches     |
| M_sw_n[3:0] | NMOS    | varies  | 1.0 µm | global    | Coarse tune switches     |

### 3.4 Expected VCO Performance

| Parameter              | Min   | Typ   | Max   | Unit      |
|------------------------|-------|-------|-------|-----------|
| Frequency (all bands)  | 40    | 275   | 550   | MHz       |
| Fine-tune range/band   | 30    | 35    | 40    | % of f₀   |
| Kvco (fine)            | 150   | 300   | 500   | MHz/V     |
| Phase noise @1MHz off  | -75   | -85   | -90   | dBc/Hz    |
| Power (core, 500MHz)   | —     | 2.0   | 3.0   | mW        |
| Supply                 | 1.62  | 1.80  | 1.98  | V         |

---

## 4. Phase-Frequency Detector (PFD)

### 4.1 Topology

Standard edge-triggered PFD using two resettable D-flip-flops:

```
    REF_CLK ──►[D-FF]──► UP ──►
                    \
                     XOR──► RESET (with delay)
                    /
    DIV_CLK ──►[D-FF]──► DN ──►
```

The D-FFs are built from NAND gates using `sky130_fd_pr__nfet_01v8` /
`sky130_fd_pr__pfet_01v8` transistors.

### 4.2 Dead-Zone Elimination

A minimum delay element (4 inverters) in the reset path ensures both UP and
DN pulses have minimum width > 200 ps, eliminating dead-zone behavior near
phase lock.

### 4.3 PFD Transistor Sizing

All gates in the PFD use minimum-area transistors for speed:
- NMOS: W=0.42u, L=0.15u
- PMOS: W=0.84u, L=0.15u (2x for balanced rise/fall)

---

## 5. Charge Pump (CP)

### 5.1 Topology: Symmetric CMOS Charge Pump

```
        VDD
         │
    ┌────┴────┐
    │  PMOS   │ M_up (W=2u, L=0.5u)
    │  switch │ gate = UP_b (inverted UP from PFD)
    └────┬────┘
         │
    ┌────┴────┐
    │  PMOS   │ M_bias_p (W=4u, L=1u)
    │  mirror │ sets I_cp = 10µA
    └────┬────┘
         │
         ├──────────► Vctrl (to loop filter)
         │
    ┌────┴────┐
    │  NMOS   │ M_bias_n (W=2u, L=1u)
    │  mirror │ mirrors I_cp = 10µA
    └────┬────┘
         │
    ┌────┴────┐
    │  NMOS   │ M_dn (W=1u, L=0.5u)
    │  switch │ gate = DN
    └────┬────┘
         │
        GND
```

### 5.2 Charge Pump Specifications

| Parameter           | Value   | Unit | Notes                          |
|--------------------|---------|------|--------------------------------|
| I_cp (nominal)     | 10      | µA   | Sourced/sinked                 |
| Current mismatch   | < 5     | %    | Across Vctrl range             |
| Output compliance  | 0.3-1.5 | V    | Full range for VCO tuning      |
| Charge sharing     | minimal |      | Unity-gain buffer on output    |

---

## 6. Loop Filter Design

### 6.1 Component Values

For a Type-II 2nd-order PLL (with 3rd-order stabilization cap):

**Design targets:**
- Loop bandwidth ωc = 2π × 2 MHz (1/25th of minimum fref = 50 MHz)
- Damping factor ζ = 0.707 (Butterworth)
- Phase margin > 60°

**Given:**
- Icp = 10 µA
- Kvco = 300 MHz/V = 2π × 300 × 10⁶ rad/s/V
- N = 1 (minimum divider ratio at low frequencies), up to N=10

**Loop filter components (R-C₁-C₂ topology):**

```
    Vcp ──[R]──┬── Vctrl
               │
              [C₁]
               │
              GND
    
    Vcp ──┬── (parallel C₂ to GND for ripple suppression)
          │
         [C₂]
          │
         GND
```

For N=1, fref=50MHz, ωc=2π×2MHz:

    R = ωc × N / (Icp × Kvco) = 2π×2e6 × 1 / (10e-6 × 2π×300e6)
      = 2e6 / (3e3) = 667 Ω  →  use **R = 680 Ω**

    C₁ = Icp × Kvco / (N × ωc²) = 10e-6 × 2π×300e6 / (1 × (2π×2e6)²)
       = 18.85e3 / (157.9e12) ≈ **120 pF**

    C₂ = C₁ / 10 = **12 pF** (ripple filter)

For N=10, fref=50MHz (VCO at 500MHz):

    ωc scales down by √10 ≈ 3.16 → ωc ≈ 2π×630kHz (still < fref/10 ✓)

### 6.2 Implementation

- R: poly resistor (`sky130_fd_pr__res_high_po_0p35` or `__res_xhigh_po`)
- C₁: MIM capacitor (`sky130_fd_pr__cap_mim_m3_1` or MOS cap)
- C₂: MOS capacitor (gate cap)

All integrated on-chip within the tt tile area.

---

## 7. Frequency Divider (Feedback /N)

### 7.1 Architecture: 8-bit Programmable Counter

```
    VCO_OUT ──►[÷2 (TSPC)]──►[÷2]──►[÷2]──►[÷2]──►[÷2]──►[÷2]──►[÷2]──►[÷2]──► DIV_RAW
                 ↑ prescaler                                                    │
                 │                                                              │
            Full-speed TSPC                                              8-bit MUX
            flip-flop for                                               selects tap
            first stage                                                 based on ui[7:0]
                                                                              │
                                                                              ▼
                                                                          DIV_OUT
                                                                         (to PFD)
```

### 7.2 Division Ratios

With 8-bit control via `ui[7:0]`:
- **N = 1 to 255** (code 0 = bypass/÷1, code 1-255 = ÷N)
- Actual implementation: cascade of ÷2 stages + terminal-count logic
- For fref = 50 MHz, fvco = N × 50 MHz → fvco = 50 to 500 MHz needs N=1..10
- Higher N values (up to 255) allow using lower reference frequencies

### 7.3 First-Stage: TSPC Flip-Flop

The first divider stage must toggle at up to 550 MHz. A True Single-Phase
Clock (TSPC) flip-flop is used:

```
    TSPC ÷2:  6 transistors, single clock input
    Max freq in sky130A: ~1 GHz (with W_n=0.84u, W_p=1.68u)
```

---

## 8. Output Observation Divider (/M)

### 8.1 Purpose

Bring the VCO output frequency down to an observable range on a standard
oscilloscope (bandwidth-limited). For a 100 MHz scope:

| fvco    | /M needed | fout       |
|---------|-----------|------------|
| 500 MHz | ÷8        | 62.5 MHz   |
| 500 MHz | ÷32       | 15.6 MHz   |
| 500 MHz | ÷256      | 1.95 MHz   |
| 50 MHz  | ÷1        | 50 MHz     |
| 50 MHz  | ÷256      | 195 kHz    |

### 8.2 Control

`uio[2:0]` selects M:

| uio[2:0] | M   |
|----------|-----|
| 000      | ÷2  |
| 001      | ÷4  |
| 010      | ÷8  |
| 011      | ÷16 |
| 100      | ÷32 |
| 101      | ÷64 |
| 110      | ÷128|
| 111      | ÷256|

Built from an 8-stage ÷2 chain with 3-bit MUX output selection.

---

## 9. Pin Assignment

### 9.1 Analog Pins (2 only)

| Pin    | Function                                    |
|--------|---------------------------------------------|
| ua[0]  | REF_CLK — input reference clock (analog)    |
| ua[1]  | OBS_OUT — divided output for oscilloscope   |

### 9.2 Digital Control Pins

| Pin(s)      | Function                     | Notes                        |
|-------------|------------------------------|------------------------------|
| ui[7:0]     | Feedback divider N [7:0]     | N = 1..255; 0 = bypass       |
| uio[2:0]    | Output divider M select      | /2 to /256 (see §8.2)        |
| uio[6:3]    | VCO coarse band [3:0]        | 16 frequency bands           |
| uio[7]      | PLL enable (active high)     | 0 = VCO free-run + reset     |
| uo[0]       | Lock detect output           | High when PLL is locked       |
| uo[1]       | DIV_OUT monitor              | Feedback divider output       |
| uo[2]       | VCO direct output (buffered) | For probing (may toggle fast) |
| uo[3..7]    | Reserved / unused            | Tie low                       |

### 9.3 Power

| Net   | Voltage | Notes                  |
|-------|---------|------------------------|
| VPWR  | 1.8 V   | Digital + analog VDD   |
| VGND  | 0 V     | Common ground          |

---

## 10. Sensitivity Analysis

### 10.1 Kvco Sensitivity

```
    Kvco = Δf / ΔVctrl  [MHz/V]
```

Target: Kvco = 200-400 MHz/V across the fine-tune range.

**Impact on loop dynamics:**
- Higher Kvco → wider loop BW → more reference spur suppression needed
- Lower Kvco → narrower loop BW → slower lock time

### 10.2 VCO Sensitivity to Supply

```
    Kpush = Δf / ΔVDD  [MHz/V]
```

Current-starved topology suppresses supply pushing:
- Target: Kpush < 50 MHz/V (< 10% of Kvco)
- Achieved by long-channel bias mirrors (L=1µm)

### 10.3 Temperature Sensitivity

```
    TCf = Δf / ΔT  [MHz/°C]
```

Ring oscillators have positive TC (mobility decreases → frequency drops).
Expected: TCf ≈ -0.5 to -1 MHz/°C → PLL will track this via feedback.

---

## 11. Lock Time Estimation

Lock time to within 1% of final frequency:

```
    t_lock ≈ (2π / ωn) × ln(100/1) / ζ
           ≈ (2π / (2π×1.4MHz)) × 4.6 / 0.707
           ≈ 4.6 µs
```

For ωn ≈ ωc/2ζ ≈ 2π×1.4MHz, ζ=0.707.

More conservative estimate: **t_lock < 10 µs** for any frequency step.

---

## 12. Area Estimate

| Block          | Est. area (µm²) | Notes                           |
|----------------|------------------|---------------------------------|
| VCO (5 stages) | 30 × 15 = 450   | 5 current-starved inverters     |
| Coarse tune    | 20 × 15 = 300   | 4-bit mirror array              |
| Varactors      | 20 × 10 = 200   | 5 MOS varactors                 |
| PFD            | 25 × 10 = 250   | ~20 transistors                 |
| Charge pump    | 15 × 10 = 150   | 6 transistors + bias            |
| Loop filter    | 40 × 30 = 1200  | On-chip R + C₁ + C₂            |
| /N divider     | 40 × 15 = 600   | 8 flip-flops + MUX              |
| /M divider     | 40 × 15 = 600   | 8 flip-flops + MUX              |
| Lock detect    | 10 × 10 = 100   | Simple XOR + filter             |
| I/O buffers    | 20 × 10 = 200   | Input/output analog buffers     |
| **Total**      | **~4050 µm²**   | Fits in 1x2 tile (~160×108 µm)  |

---

## 13. Simulation Plan

| Sim ID | Type       | Description                                        | Script                     |
|--------|------------|----------------------------------------------------|----------------------------|
| S1     | DC         | VCO bias point, operating point                    | pll_vco_dc.spice           |
| S2     | Transient  | VCO free-running frequency vs coarse/fine tune     | pll_vco_tran.spice         |
| S3     | AC (noise) | VCO phase noise via PSS/Pnoise (behavioral)       | pll_vco_noise.spice        |
| S4     | Transient  | PFD functionality — UP/DN pulses                   | pll_pfd_tran.spice         |
| S5     | DC/Tran    | Charge pump current matching, compliance            | pll_cp_tran.spice          |
| S6     | Transient  | Divider functionality ÷2, ÷4, ÷8, ÷N              | pll_div_tran.spice         |
| S7     | Transient  | Full PLL locking transient                         | pll_full_tran.spice        |
| S8     | AC/Tran    | Phase noise (behavioral Leeson model)              | pll_phase_noise.spice      |
| S9     | Corners    | Full PLL across TT/FF/SS/SF/FS ×Temp               | pll_corners.spice          |
