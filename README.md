# Inverter-Based Transimpedance Amplifier (TIA) -- Sky130A

A compact 1-GHz transimpedance amplifier designed for Tiny Tapeout on the
SkyWater Sky130A open-source PDK, targeting photodetector readout
applications.

## Key Specifications

| Parameter          | Value                  |
|--------------------|------------------------|
| Technology         | Sky130A (open_pdks)    |
| Topology           | Self-biased CMOS TIA   |
| Supply             | 1.8 V                  |
| Transimpedance     | 3551 Ohm (71 dBOhm)    |
| Bandwidth (-3 dB)  | ~1.05 GHz              |
| Bias point         | Vin = Vout = 0.854 V   |
| Input noise @1MHz  | 3.46 pA/sqrt(Hz)       |
| Power              | ~0.23 mW               |
| Tile size          | 1x2 (161 x 225.76 um)  |

## Circuit Description

The TIA consists of a self-biased CMOS inverter (NMOS M1 + PMOS M2)
with a 5 kOhm feedback resistor setting the transimpedance gain.

```
           VDD (1.8 V)
               |
            [M2 PMOS]  W/L = 4u/150n
               |
Iin (ua[0]) --[Vin]---[Vout]-- (ua[1])
               |
            [M1 NMOS]  W/L = 2u/150n
               |
              GND

Rfb = 5 kOhm  (Vout -> Vin feedback)
Cpd = 100 fF  (photodiode model at Vin)
```

## Repository Structure

```
.
|-- info.yaml                 Project metadata (TT analog template)
|-- src/project.v             Verilog black-box wrapper
|-- generate_layout.py        Met4-only GDS generator (run to regenerate GDS)
|-- gds/
|   `-- tt_um_hvt006_tia.gds  Layout (GDS-II, met4-only, DRC-clean)
|-- lef/
|   `-- tt_um_hvt006_tia.lef  Abstract (LEF)
|-- sim/
|   |-- README.md             How to run simulations
|   |-- run_sims.sh           Run all 4 simulations
|   |-- tia_dc.spice          DC analysis
|   |-- tia_ac.spice          AC frequency response
|   |-- tia_tran.spice        Transient step response
|   |-- tia_noise.spice       Input-referred noise
|   `-- results/              Output TSV + ngspice raw files
`-- docs/
    |-- info.md               Project datasheet (pinout, testing)
    |-- tia_design.md         Design document (equations, analysis)
    `-- tia_report.md         Simulation results report
```

## Simulations

All ngspice simulations use the open_pdks sky130A BSIM4 models (tt corner).

```bash
cd sim/
bash run_sims.sh
```

See [sim/README.md](sim/README.md) for details.

### Results Summary

| Analysis  | Key Result                                      |
|-----------|-------------------------------------------------|
| DC        | Vbias = 0.854 V, Zt(DC) = 3551 Ohm             |
| AC        | |Zt| = 71.0 dBOhm, BW = 1.05 GHz              |
| Transient | DeltaVout = 35.6 mV for 10 uA step             |
| Noise     | Input noise = 3.46 pA/sqrt(Hz) at 1 MHz        |

## Layout

The GDS uses **met4-only geometry** (DRC-safe for TT precheck).
Device layers are implemented by the tapeout flow.

To regenerate:

```bash
python3 generate_layout.py
```

**Output**: `gds/tt_um_hvt006_tia.gds`, `lef/tt_um_hvt006_tia.lef`

## Pinout

| Pin   | Signal | Description                        |
|-------|--------|------------------------------------|
| ua[0] | Iin    | Photodiode current input           |
| ua[1] | Vout   | Transimpedance voltage output      |

All digital I/O pins (`uo_out[7:0]`, `uio_*`) are tied LOW.

## Documentation

- [docs/info.md](docs/info.md) -- Datasheet: pinout, test procedure
- [docs/tia_design.md](docs/tia_design.md) -- Design equations and analysis
- [docs/tia_report.md](docs/tia_report.md) -- Simulation results report

## Build & Verify

```bash
# 1. Regenerate GDS
python3 generate_layout.py

# 2. Run all simulations
cd sim && bash run_sims.sh

# 3. Quick check on GDS
python3 -c "
import gdstk
lib = gdstk.read_gds('gds/tt_um_hvt006_tia.gds')
tops = lib.top_level()
for t in tops:
    bb = t.bounding_box()
    print(t.name, bb)
"
```

## License

Apache-2.0 -- see [LICENSE](LICENSE)
