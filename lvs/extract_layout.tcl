# Magic batch extraction script for tt_um_hvt006_tia
# Usage: magic -dnull -noconsole -rcfile <magicrc> extract_layout.tcl

# Load sky130A GDS layer map
gds read gds/tt_um_hvt006_tia.gds

# Select the top cell
load tt_um_hvt006_tia

# Flatten the cell for extraction
flatten tt_um_hvt006_tia_flat
load tt_um_hvt006_tia_flat
select top cell

# Run extraction
extract all
ext2spice lvs
ext2spice -o lvs/tt_um_hvt006_tia_layout.spice

quit -noprompt
