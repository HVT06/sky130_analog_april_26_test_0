#!/usr/bin/env bash
# =============================================================
# run_sims.sh  —  Run all TIA ngspice simulations
# Sky130A Inverter-Based TIA  (Tiny Tapeout analog)
# =============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
mkdir -p results

NGSPICE="${NGSPICE:-ngspice}"

run_sim() {
    local netlist="$1"
    echo "------------------------------------------------------------"
    echo "Running: $netlist"
    echo "------------------------------------------------------------"
    "$NGSPICE" -b "$netlist" 2>&1
    echo "Done: $netlist"
    echo
}

run_sim tia_dc.spice
run_sim tia_ac.spice
run_sim tia_tran.spice
run_sim tia_noise.spice

echo "============================================================"
echo "All simulations complete.  Results in: $SCRIPT_DIR/results/"
ls -lh results/
echo "============================================================"
