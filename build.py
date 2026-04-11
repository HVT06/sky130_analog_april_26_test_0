#!/usr/bin/env python3
"""
build.py — Multi-project build script for Tiny Tapeout sky130A.

Reads config.yaml to determine active project, runs the project's
generate_layout.py, and copies the resulting GDS to gds/<top_module>.gds.
Also updates info.yaml with the selected project's metadata.
"""

import yaml
import subprocess
import shutil
import sys
import os

ROOT = os.path.dirname(os.path.abspath(__file__))

def main():
    cfg_path = os.path.join(ROOT, "config.yaml")
    with open(cfg_path) as f:
        cfg = yaml.safe_load(f)

    active = cfg["active_project"]
    proj = cfg["projects"][active]
    top_module = proj["top_module"]
    print(f"Building project: {active}  (top_module={top_module})")

    proj_dir = os.path.join(ROOT, "projects", active)
    gen_script = os.path.join(proj_dir, "generate_layout.py")

    if not os.path.isfile(gen_script):
        print(f"ERROR: {gen_script} not found")
        sys.exit(1)

    # Run the layout generator
    result = subprocess.run(
        [sys.executable, gen_script],
        cwd=proj_dir,
        capture_output=False,
    )
    if result.returncode != 0:
        print("ERROR: generate_layout.py failed")
        sys.exit(1)

    # Copy GDS to gds/ directory
    gds_dir = os.path.join(ROOT, "gds")
    os.makedirs(gds_dir, exist_ok=True)
    src_gds = os.path.join(proj_dir, "gds_out", f"{top_module}.gds")
    dst_gds = os.path.join(gds_dir, f"{top_module}.gds")
    if os.path.isfile(src_gds):
        shutil.copy2(src_gds, dst_gds)
        print(f"GDS copied: {dst_gds}")
    else:
        print(f"WARNING: {src_gds} not found after generation")
        sys.exit(1)

    # Update info.yaml
    info_path = os.path.join(ROOT, "info.yaml")
    with open(info_path) as f:
        info = yaml.safe_load(f)

    info["project"]["top_module"] = top_module
    info["project"]["title"] = proj["description"]
    info["project"]["tiles"] = proj["tiles"]
    info["project"]["analog_pins"] = proj["analog_pins"]

    with open(info_path, "w") as f:
        yaml.dump(info, f, default_flow_style=False, sort_keys=False)

    print(f"info.yaml updated: top_module={top_module}")
    print("Build complete.")

if __name__ == "__main__":
    main()
