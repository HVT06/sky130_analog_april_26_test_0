# Simulation Files -- Inverter-Based TIA

## Requirements

- **ngspice** >= 44, installed at `/home/hvt06/.local/bin/ngspice`
  (or any ngspice in $PATH)
- **PDK**: open_pdks Sky130A at `/home/hvt06/Downloads/open_pdks/sky130/sky130A/`
  - NFET model: `libs.ref/sky130_fd_pr/spice/sky130_fd_pr__nfet_01v8__tt.pm3.spice`
  - PFET model: `libs.ref/sky130_fd_pr/spice/sky130_fd_pr__pfet_01v8__tt.corner.spice`

## Running All Simulations

```bash
cd sim/
bash run_sims.sh
```

Results are written to `sim/results/` as TSV (text) and raw (binary ngspice) files.

## Individual Simulations

### DC Operating Point + Transfer Curve

```bash
ngspice -b tia_dc.spice
```

Output: `results/dc_tia.tsv`, `results/dc_tia.raw`
Columns: `v(vin)  v(vout)` (201 rows, Iin = -100 uA .. +100 uA)

Key result: Vin = Vout = 0.854 V at Iin = 0.

### AC Frequency Response

```bash
ngspice -b tia_ac.spice
```

Output: `results/ac_tia.tsv`, `results/ac_tia.raw`
Columns: `frequency  Zt_dB  Zt_ohm` (81 rows, 1 MHz .. 100 GHz)

Key results:
- |Zt| = 3551 Ohm = 71.0 dBOhm at 1 MHz
- -3 dB bandwidth: ~1.05 GHz

### Transient Step Response

```bash
ngspice -b tia_tran.spice
```

Output: `results/tran_tia.tsv`, `results/tran_tia.raw`
Columns: `time  v(vin)  v(vout)`

Input: PULSE(0 -> 10 uA, Td=1ns, Tr=50ps, Tf=50ps, Pw=4ns, Period=10ns)
Key result: DeltaVout = -35.6 mV for DeltaIin = 10 uA => Zt = 3560 Ohm.

### Noise Analysis

```bash
ngspice -b tia_noise.spice
```

Output: `results/noise_tia.tsv`, `results/noise_tia.raw`
Columns: `frequency  inoise_spectrum  onoise_spectrum` (A^2/Hz, V^2/Hz)

Key result: sqrt(inoise) = 3.46 pA/sqrt(Hz) at 1 MHz.
Rf thermal floor: sqrt(4kT/Rf) = 1.82 pA/sqrt(Hz).

## Circuit Netlist Summary

```spice
* Self-biased CMOS inverter TIA
Vdd vdd 0 1.8
XM1 vout vin 0   0   sky130_fd_pr__nfet_01v8 l=0.15u w=2.0u
XM2 vout vin vdd vdd sky130_fd_pr__pfet_01v8 l=0.15u w=4.0u
Rfb vout vin 5000       ; feedback resistor = transimpedance
Cpd vin 0 100f          ; photodiode capacitance model
```

## Notes

- All spice files are **pure ASCII** -- no Unicode characters allowed.
  ngspice 45's parser misinterprets multi-byte UTF-8 sequences.

- The PDK model files use Monte Carlo parameters (slopes).
  All `.param ..._slope = 0` and `mc_*_switch = 0` must be defined before
  the `.include` lines, or ngspice will report "Mismatch: 13 formal params".

- MOSFET instance lines must fit on a **single line** (no continuation `+`):
  `XM1 vout vin 0 0 sky130_fd_pr__nfet_01v8 l=0.15u w=2.0u`
