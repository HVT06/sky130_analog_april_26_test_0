# PLL Sky130A DRC Closure Report

## Scope
This report documents the full custom-geometry DRC closure for `tt_um_pll_sky130` on branch `pll_sky130A`.

Constraints followed:
- No standard-cell usage for layout implementation
- Keep tile size at `161.0um x 225.76um` (`1x2` Tiny Tapeout tile)
- Preserve 53 met4 top-level pin labels
- Use Magic DRC flow equivalent to CI (`drc check` + `drc listall why`)

## Root-Cause Summary
Initial DRC failures were dominated by latchup/tap and nwell interactions:
- `LU.2`: N-diff to P-tap distance violations
- `LU.3`: P-diff to N-tap distance violations
- `nwell.1`, `nwell.2a`, `nwell.4`, `diff/tap.10`

Main causes:
- Insufficient local tap density
- Standalone ntap nwells too close to PFET nwells
- Missing explicit nwell coverage where ntaps were intended to share PFET nwell regions
- Loop-filter MOSCAP arrays too wide for LU.2 with only perimeter taps

## Implemented Fixes

### 1. DFF / NAND / Inverter tap strategy
- Added ntaps with `draw_nwell=False` where taps are intended to reside in PFET nwell regions.
- Added explicit nwell extensions to ensure ntap enclosure and connectivity.

### 2. VCO nwell/tap cleanup
- Added per-stage ptap + ntap with explicit local nwell extension around PFET-side regions.
- Added bias-stage tap and local nwell extension.
- Consolidated PFET-side nwell islands to remove residual narrow-spacing artifacts while keeping NFET region clear.

### 3. Charge pump nwell/tap cleanup
- Replaced problematic sparse/standalone ntap approach with explicit PFET-region ntaps.
- Added merged PFET-region nwell for those ntaps to avoid `nwell.2a` and HVI spacing artifacts.
- Kept bottom substrate tap row for LU.2 compliance.

### 4. Loop filter LU.2 closure
- Updated MOSCAP generator to create an internal tap corridor for wide capacitor arrays:
  - Finger array split with a controlled gap
  - Internal vertical ptap column in the gap
- This reduces max N-diff to P-tap distance without violating diffusion spacing.

## Verification Results

### Geometry and interface checks
- Layout size: `161.0 x 225.8 um` (fits tile)
- Standard cells embedded: `0`
- Met4 pin labels: `53`

### Final Magic DRC result
- `TOTAL_ERRORS: 0`

Run command used for final verification:
```bash
PDK_ROOT=/home/hvt06/Downloads/open_pdks/sky130 \
/usr/local/bin/magic -dnull -noconsole << 'EOFMAGIC'
tech load /home/hvt06/Downloads/open_pdks/sky130/sky130A/libs.tech/magic/sky130A.tech
gds maskhints yes
gds read gds/tt_um_pll_sky130.gds
load tt_um_pll_sky130
select top cell
expand
drc euclidean on
drc style drc(full)
drc check
set drc_result [drc listall why]
set total 0
foreach {msg rects} $drc_result {
    set total [expr {$total + [llength $rects]}]
}
puts "TOTAL_ERRORS: $total"
quit -noprompt
EOFMAGIC
```

## Files Updated
- `projects/pll/generate_layout.py`
- `projects/pll/docs/pll_drc_closure_report.md`
- Regenerated outputs:
  - `gds/tt_um_pll_sky130.gds`
  - `svg/*.svg`

## Notes
- This closure keeps the design fully custom and does not rely on standard cells.
- The final DRC pass confirms closure for the current GDS database generated from this script revision.
