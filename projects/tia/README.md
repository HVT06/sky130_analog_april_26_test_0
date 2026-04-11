# TIA Project — Placeholder
# (Full TIA design files are on the `main` branch)

This directory is a placeholder for the transimpedance amplifier (TIA) project.
The complete TIA design (DRC/LVS-clean layout, simulations, documentation) lives on
the `main` branch at commit `2e26fb1`.

To build the TIA instead of PLL, edit `config.yaml`:
```yaml
active_project: tia
```

Then run:
```
python3 build.py
```

## TIA Summary
- Inverter-based TIA using sky130_fd_sc_hd__inv_6
- Poly feedback resistor (~5 kΩ)
- Zt ≈ 3776 Ω, BW ≈ 1.26 GHz (TT/27°C)
- 15 corners (5 process × 3 temps) + 200 MC runs verified
- Analog pins: ua[0] = gate/input, ua[1] = Vout
