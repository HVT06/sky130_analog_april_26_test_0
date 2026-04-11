# PLL Design Iteration Log — SKY130A Ring Oscillator PLL

## Summary

This document chronicles the complete iteration and debugging journey of
bringing up a charge-pump PLL in the SKY130A PDK using NGSPICE simulation.
The process spanned multiple sessions and involved fundamental discoveries
about NGSPICE XSPICE conventions, PFD architecture limitations, and charge
pump behavior.

---

## Phase 1: Individual Block Verification

### 1.1 VCO Simulation (Standalone)

**File:** `sim/pll/pll_vco_tran.spice`

- 5-stage current-starved ring oscillator with PMOS current source + NMOS
  current sink controlled by Vctrl
- Transistor sizing: current source/sink L=0.5µm W=4µm/2µm; inverter
  L=0.15µm W=2µm/1µm
- **Result:** Tuning range 31–722 MHz (Vctrl = 0.7–1.6 V)
- **Issue encountered:** VCO didn't oscillate when instantiated as subcircuit
- **Root cause:** `.ic` statements inside subcircuits don't work in NGSPICE
- **Fix:** Use top-level `.ic` with hierarchical node names:
  `.ic v(xvco.s1)=1.8 v(xvco.s2)=0 v(xvco.s3)=1.8 v(xvco.s4)=0 v(xvco.s5)=1.8`

### 1.2 PFD + Charge Pump (Standalone)

**File:** `sim/pll/pll_pfd_cp.spice`

- 3-inverter edge-detector PFD: `UP = NAND(clk, inv(inv(inv(clk))))`
- Charge pump: 10µA simple PMOS/NMOS mirrors
- **Result:** +24.2 mV for 1 ns phase lag, −23.7 mV for 1 ns lead → correct
- **Caveat:** Tested with ideal PULSE sources only (0.1 ns edges)

### 1.3 Frequency Divider (Standalone)

**File:** `sim/pll/pll_div_tran.spice`

- Transmission-gate master-slave DFF in toggle configuration
- ÷2 × ÷2 = ÷4 cascade
- **Result:** 500 → 250 → 125 → 62.5 → 31.25 MHz chain verified

---

## Phase 2: First Full PLL Integration Attempt

### 2.1 Initial Integration

Combined VCO + 3-inv PFD + simple CP + ÷4 divider + loop filter.

**Loop filter design:**
- Target: ωn = 2π×1 MHz, ζ = 1 (critically damped)
- Kvco = 8.17×10⁹ rad/s/V, Icp = 10µA, N = 4
- R = 625 Ω, C1 = 500 pF, C2 = 50 pF

**Result:** Vctrl rose from 0.9V but settled at 1.38V (VCO ≈ 650 MHz,
div ≈ 163 MHz). This is NOT the correct lock point (should be ~1.01V
for 400MHz).

### 2.2 Charge Pump Investigation

**Hypothesis:** PMOS headroom issue at high Vctrl.

- Tried cascode charge pump → identical result (1.38V)
- This ruled out CP as the sole cause

### 2.3 Ideal VCCS Charge Pump Test

**File:** `sim/pll/pll_ideal_pfdcp.spice`

Replaced transistor CP with ideal voltage-controlled current sources.

**Discovery: NGSPICE VCCS polarity convention is opposite to naive expectation!**

- `G n+ n- nc+ nc- gm`: current **sinks** from n+ (current leaves n+)
- To SOURCE current into node X: `G 0 X ctrl 0 gm`
- To SINK current from node X: `G X 0 ctrl 0 gm`
- Verified with isolated test circuit

**After polarity fix:** Vctrl rose to 1.64V (still wrong) — PFD was the problem.

---

## Phase 3: PFD Root Cause Analysis

### 3.1 The 3-Inverter Edge Detector Problem

**File:** `sim/pll/pfd_test_170.spice`

- 3-inverter chain delay ≈ 60 ps
- VCO-driven divider output has 80–160 ps rise times
- When rise time ≈ delay chain time, NAND pulse too narrow or absent
- **PFD works with ideal PULSE sources but fails with VCO-driven clocks**

### 3.2 Fix Attempt: 7-Inverter Chain

Changed from 3 to 7 inverters (delay ≈ 140 ps).

- With ideal VCCS CP: Vctrl settled at ~1.1V (near target!)
- With transistor CP: Vctrl settled at 1.32V (offset from CP asymmetry)

**Partial success** — but still not right.

### 3.3 Detailed Waveform Analysis (7-inv PFD + Transistor CP)

Measured actual frequencies at end of 50µs simulation:
- VCO = 626 MHz (not 503 MHz as MEAS reported — MEAS measured early)
- DIV = 156 MHz (not 124 MHz)
- UP duty = 23.4%, DN duty = 23.9% — **nearly equal despite 56 MHz error!**

### 3.4 PFD Event Trace at 49µs

Detailed awk analysis of transitions revealed:
- At 49004.4 ns: div_clk rises but DN does NOT go HIGH
- The PFD was **missing divider rising edges** entirely (~30% miss rate)
- div_clk showed ringing: −0.1V undershoot, 1.95V overshoot
- The edge-detector pulse/reset timing race prevented reliable operation

**Conclusion:** The NAND-based edge-detector PFD architecture is
fundamentally unreliable with realistic (VCO-driven) clock edges,
regardless of delay chain length.

---

## Phase 4: Alternative PFD Architecture Search

### 4.1 Architectures Considered

| Architecture | Issue |
|---|---|
| 3-inv edge detector | Pulse too narrow for slow edges |
| 7-inv edge detector | Still misses edges due to reset race |
| TG master-slave PFD DFF | Q re-asserts after reset when CLK still HIGH |
| NAND SR latch PFD | Same edge detection problem |
| Standard cell DFF (dfrtp) | Possible but transistor-level complexity |
| **XSPICE digital PFD** | **Correct by construction** |

### 4.2 Decision: XSPICE Digital PFD

NGSPICE's XSPICE extension provides `d_dff` (digital D flip-flop) that
handles edge detection internally using digital simulation, completely
bypassing analog timing issues.

---

## Phase 5: XSPICE PFD Implementation

### 5.1 Initial d_dff Investigation

**Files:** `/tmp/test_dff.spice` through `/tmp/test_dff4.spice`

Multiple test circuits to understand d_dff behavior:
- Basic DFF works with default parameters
- `ic=0` vs `ic=2` behavior explored
- SET/RESET polarity unclear from documentation

### 5.2 First Working Behavioral PFD

**File:** `/tmp/test_bpfd.spice`

- Used d_dff + d_and + d_buffer + d_inverter
- Ref=100MHz, Div=120MHz (div faster)
- Result: UP=8%, DN=49% → **PFD correctly indicates div leads**

### 5.3 First PLL Integration (XSPICE PFD)

Replaced transistor PFD with XSPICE models in `pll_full_tran.spice`.

**Critical bug:** Assumed d_dff RESET was active-LOW, added an inverter
between AND(UP,DN) and reset pin.

**Result:** UP and DN never went HIGH. Vctrl barely moved (0.9→0.9001V
in 50µs). The inverter created a permanent reset deadlock:
- Reset_inv = NOT(AND(UP,DN)) = NOT(AND(0,0)) = NOT(0) = 1
- Both DFFs held in permanent reset → outputs always 0

### 5.4 Discovery: d_dff SET/RESET Are ACTIVE-HIGH

**Source:** Official NGSPICE XSPICE PLL example:
`/home/hvt06/Downloads/ngspice-45.2/examples/xspice/pll/f-p-det-d-sub.cir`

Key revelations:
```spice
* d_dff pinout: data clk set reset out ~out
* SET and RESET are ACTIVE-HIGH (HIGH = asserted)
* ic=2 means UNKNOWN initial state
* Pattern: D=VDD, SET=GND(inactive), RESET=AND(UP,DN) directly
```

The example uses `.global d_d0 d_d1` for digital constants created via
analog voltage sources through ADC bridges.

### 5.5 Fixed XSPICE PFD

Removed the inverter. AND(UP,DN) feeds DFF reset directly.
Added global digital constants `d_gnd` and `d_vdd` via voltage sources
through `adc_bridge`.

### 5.6 Standalone Verification

**File:** `/tmp/pll_xspice_debug3.spice`

- Ref=100MHz, Div=60MHz (ref much faster)
- Result: UP duty=69.8%, DN duty=0.5% → **Correct!**
  PFD generates dominant UP pulses since ref leads.

---

## Phase 6: Full PLL Lock Verification

### 6.1 First Full Sim with Fixed XSPICE PFD (50µs)

- Simulation too slow: only reached 8.7µs after many minutes
- Killed and reduced to 10µs

### 6.2 10µs Simulation

**Key results:**
| Time | Vctrl (V) |
|------|-----------|
| 1µs  | 0.915     |
| 5µs  | 0.961     |
| 8µs  | 0.992     |
| 10µs | 1.016     |

- VCO = 399.9 MHz (measured from zero crossings in last 200ns)
- DIV = 98.9 MHz
- **Clear convergence toward lock!** But not yet settled.

### 6.3 25µs Simulation (Final)

Extended to see complete lock acquisition.

**Vctrl trajectory:**
| Time   | Vctrl (V) | State |
|--------|-----------|-------|
| 0      | 0.900     | Initial |
| 5µs    | 0.961     | Ramping |
| 10µs   | 1.016     | Overshoot |
| 12µs   | 1.013     | Settling |
| 15µs   | 1.014     | Locked |
| 20µs   | 1.014     | Locked |
| 25µs   | 1.014     | Locked |

**Final locked state:**
- **Vctrl = 1.0140 V** (stable ± 0.0001V)
- **VCO = 400 MHz**
- **DIV = 100.0 MHz (exact)**
- **Lock time ≈ 12µs**
- **Overshoot = 1.6mV (0.16%)**

---

## Phase 7: VCO Phase Noise Analysis

### 7.1 First Noise Attempt (Without trnoise)

**File:** `sim/pll/pll_vco_noise.spice` (first version)

- Set Vctrl=0.9V (wrong — should be lock point ~1.01V)
- Used `reset` between baseline and noisy runs → lost `f0` variable
- No transient noise generated (NGSPICE BSIM4 doesn't inject noise
  by default in transient simulation)
- All periods identical → zero jitter

### 7.2 Proper Transient Noise with trnoise Sources

**Discovery:** NGSPICE transient noise requires explicit `trnoise` voltage
sources in series with circuit nodes. Format:
```spice
Vn1 node_internal node_external dc 0 trnoise Vrms timestep 1/f_exp 1/f_coeff
```

**Source:** NGSPICE example:
`ngspice-45.2/examples/transient-noise/noi-ring51-demo.cir`

### 7.3 Updated Noise Simulation

- Added 5 trnoise voltage sources (one per VCO stage output)
- Parameters: Vrms=5mV, timestep=0.02ns, 1/f_exp=1.0, 1/f_coeff=0.002
- Vctrl = 1.01V (operational lock point)
- Single 2000ns run (no reset needed)

**Results:**
- f0 = 406.7 MHz
- Period jitter: 2454.5–2462.4 ps (pk-pk ≈ 7.9 ps, 0.32% of T0)
- Leeson model: L(1MHz) = −134.8 dBc/Hz

---

## Key Lessons Learned (Cumulative)

1. **`.ic` inside subcircuits doesn't work** — use top-level hierarchical names
2. **NGSPICE VCCS `G n+ n-`:** current sinks from n+ (opposite of intuition)
3. **Edge-detector PFD fails with real clocks:** NAND(clk, delayed_inv(clk))
   is fundamentally unreliable when rise_time ≈ delay_chain_time
4. **XSPICE d_dff SET/RESET are ACTIVE-HIGH** (not active-low)
5. **d_dff `ic=2`** means UNKNOWN initial state (preferred for PFD)
6. **`dac_bridge(out_undef=0.0)`** maps UNKNOWN→0V (safe for CP)
7. **NGSPICE MEAS timing matters:** RISE=N counts from t=0, so MEAS points
   can reflect early (pre-lock) behavior, not steady state
8. **NGSPICE transient noise requires explicit `trnoise` sources** — BSIM4
   doesn't generate thermal noise in `.tran` by default
9. **Always test PFD with realistic VCO-driven edges**, not ideal PULSE
10. **CP current asymmetry shifts lock point** but is secondary to PFD issues

---

## Configuration Comparison Table

| # | PFD | CP | Vctrl (V) | VCO (MHz) | DIV (MHz) | Status |
|---|-----|----|-----------|-----------|-----------|--------|
| 1 | 3-inv edge | Simple 10µA | 1.38 | ~650 | ~163 | Wrong lock |
| 2 | 3-inv edge | Cascode | 1.38 | ~650 | ~163 | Same issue |
| 3 | 3-inv edge | Ideal VCCS | 1.64 (↑) | >700 | >175 | No lock |
| 4 | 7-inv edge | Ideal VCCS | 1.11 | ~433 | ~107 | Near lock |
| 5 | 7-inv edge | Simple 10µA | 1.32 | ~626 | ~156 | PFD misses edges |
| 6 | XSPICE (broken) | Simple 10µA | 0.900 | 249 | 62 | Reset deadlock |
| **7** | **XSPICE (fixed)** | **Simple 10µA** | **1.014** | **400** | **100** | **✅ Locked** |

---

## Files Created/Modified

| File | Purpose | Status |
|------|---------|--------|
| `docs/pll/pll_design.md` | Design document | ✅ Complete |
| `docs/pll/pll_specifications.md` | Specifications | ✅ Complete |
| `docs/pll/pll_sim_report.md` | Simulation report | ✅ Complete |
| `sim/pll/pll_vco_tran.spice` | VCO simulation | ✅ Verified |
| `sim/pll/pll_pfd_cp.spice` | PFD+CP standalone | ✅ Verified |
| `sim/pll/pll_div_tran.spice` | Divider standalone | ✅ Verified |
| `sim/pll/pll_full_tran.spice` | Full PLL (25µs) | ✅ Locked |
| `sim/pll/pll_vco_noise.spice` | VCO phase noise | ✅ Complete |
| `sim/pll/pll_ideal_pfdcp.spice` | Ideal CP debug | Debug tool |
| `sim/pll/pfd_test_170.spice` | PFD at 170MHz | Debug tool |
| `sim/pll/pfd_test_95.spice` | PFD at 95MHz | Debug tool |
