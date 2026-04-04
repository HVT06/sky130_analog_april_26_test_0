#!/usr/bin/env tclsh
# ============================================================
# Ring Oscillator Layout for Tiny Tapeout Sky130A Analog
# 5-stage ring oscillator + output buffer = 12 transistors
# Cell: tt_um_hvt006_cs_amp  (161.000 x 225.760 um, 1x2 tile)
#
# Circuit:
#   ENABLE (ua[0]) -> gates inverter 0 NMOS (when high, ring runs)
#   INV0 -> INV1 -> INV2 -> INV3 -> INV4 -> feedback to INV0
#   INV4 output also drives BUFFER -> OUT (ua[1])
#
# Each inverter: 1 PMOS (W=1um, L=0.15um) + 1 NMOS (W=0.5um, L=0.15um)
# Buffer: 1 PMOS (W=2um, L=0.15um) + 1 NMOS (W=1um, L=0.15um)
# Total: 12 transistors (6 PMOS + 6 NMOS)
# ============================================================

set PDKPATH "/home/hvt06/Downloads/open_pdks/sky130/sky130A"
set CELL "tt_um_hvt006_cs_amp"
set PROJDIR "/home/hvt06/Downloads/sky130_april_26_test/sky130_analog_april_26_test_0"

set DIE_W 161.000
set DIE_H 225.760

# Start magic
source $PDKPATH/libs.tech/magic/sky130A.magicrc

tech load sky130A

# Create new cell
cellname create $CELL
edit

# ============================================================
# Draw PR Boundary
# ============================================================
box 0um 0um ${DIE_W}um ${DIE_H}um
paint prbndry

# ============================================================
# Power stripes on met4 (matching DEF template)
# VDPWR: x=1.0-3.0um, y=5.0-220.76um
# VGND:  x=4.5-6.5um, y=5.0-220.76um
# ============================================================
box 1.0um 5.0um 3.0um 220.76um
paint met4
label VDPWR FreeSans 16 0 0 0 c met4
port make
port use power
port class bidirectional

box 4.5um 5.0um 6.5um 220.76um
paint met4
label VGND FreeSans 16 0 0 0 c met4
port make
port use ground
port class bidirectional

# ============================================================
# Internal power rails on met1 for devices
# VDD rail (met1) at y=140um, connected to VDPWR via met1-met4 stack
# VSS rail (met1) at y=80um, connected to VGND via met1-met4 stack
# ============================================================

# VDD met1 rail: horizontal, wide enough for current
box 20um 139um 155um 141um
paint met1

# VSS met1 rail: horizontal
box 20um 79um 155um 81um
paint met1

# ============================================================
# Connect VDD rail to VDPWR stripe via vertical met2/met3/met4
# At x=2um (center of VDPWR stripe)
# ============================================================

# met1 stub from VDD rail going left to x=2
box 1.5um 139.5um 20um 140.5um
paint met1

# Via stack at (2, 140): met1 -> met2
box 1.55um 139.55um 1.72um 139.72um
paint viali
box 1.35um 139.35um 1.92um 139.92um
paint met2
# met2 -> met3
box 1.45um 139.45um 1.65um 139.65um
paint via2
box 1.35um 139.35um 1.92um 139.92um
paint met3
# met3 -> met4
box 1.45um 139.45um 1.65um 139.65um
paint via3
# Already have VDPWR met4 stripe there

# Connect VSS rail to VGND stripe
box 4.0um 79.5um 20um 80.5um
paint met1

# Via stack at (5.5, 80): met1 -> met2
box 5.05um 79.55um 5.22um 79.72um
paint viali
box 4.85um 79.35um 5.42um 79.92um
paint met2
box 4.95um 79.45um 5.15um 79.65um
paint via2
box 4.85um 79.35um 5.42um 79.92um
paint met3
box 4.95um 79.45um 5.15um 79.65um
paint via3

# ============================================================
# INVERTER CELLS
# Place 5 inverters + 1 buffer horizontally
# Each inverter at: x_base + i*20um, centered around y=110um
# PMOS on top (connected to VDD rail at y=140)
# NMOS on bottom (connected to VSS rail at y=80)
# ============================================================

# Inverter procedure: creates PMOS at top, NMOS at bottom
# Returns nothing, draws directly
proc draw_inverter {x_base wp wn label} {
    # NMOS: gate at x_base, source on left, drain on right
    # Active region for NMOS (ndiffusion)
    set nx $x_base
    set ny 95.0

    # NMOS diffusion (source-gate-drain)
    set nd_left [expr {$nx - 0.5}]
    set nd_right [expr {$nx + 0.5}]
    set nd_bot [expr {$ny - $wn/2.0}]
    set nd_top [expr {$ny + $wn/2.0}]
    box ${nd_left}um ${nd_bot}um ${nd_right}um ${nd_top}um
    paint ndiffusion

    # NMOS poly gate (vertical, crossing the diffusion)
    set pg_left [expr {$nx - 0.075}]
    set pg_right [expr {$nx + 0.075}]
    set pg_bot [expr {$nd_bot - 0.25}]
    set pg_top [expr {$nd_top + 0.25}]
    box ${pg_left}um ${pg_bot}um ${pg_right}um ${pg_top}um
    paint poly

    # PMOS: above NMOS
    set px $x_base
    set py 125.0

    # PMOS diffusion
    set pd_left [expr {$px - 0.5}]
    set pd_right [expr {$px + 0.5}]
    set pd_bot [expr {$py - $wp/2.0}]
    set pd_top [expr {$py + $wp/2.0}]

    # First draw nwell for PMOS
    set nw_left [expr {$pd_left - 0.38}]
    set nw_right [expr {$pd_right + 0.38}]
    set nw_bot [expr {$pd_bot - 0.38}]
    set nw_top [expr {$pd_top + 0.38}]
    box ${nw_left}um ${nw_bot}um ${nw_right}um ${nw_top}um
    paint nwell

    box ${pd_left}um ${pd_bot}um ${pd_right}um ${pd_top}um
    paint pdiffusion

    # PMOS poly gate
    set ppg_left [expr {$nx - 0.075}]
    set ppg_right [expr {$nx + 0.075}]
    set ppg_bot [expr {$pd_bot - 0.25}]
    set ppg_top [expr {$pd_top + 0.25}]
    box ${ppg_left}um ${ppg_bot}um ${ppg_right}um ${ppg_top}um
    paint poly

    # Connect NMOS and PMOS gates with poly (vertical strip)
    box ${pg_left}um ${pg_top}um ${ppg_right}um ${ppg_bot}um
    paint poly

    # Local interconnect contacts on NMOS source (left side)
    set ns_x [expr {$nx - 0.35}]
    box [expr {$ns_x - 0.085}]um [expr {$ny - 0.085}]um [expr {$ns_x + 0.085}]um [expr {$ny + 0.085}]um
    paint ndc
    box [expr {$ns_x - 0.25}]um [expr {$ny - 0.25}]um [expr {$ns_x + 0.25}]um [expr {$ny + 0.25}]um
    paint li1

    # LI contacts on NMOS drain (right side)
    set nd_x [expr {$nx + 0.35}]
    box [expr {$nd_x - 0.085}]um [expr {$ny - 0.085}]um [expr {$nd_x + 0.085}]um [expr {$ny + 0.085}]um
    paint ndc
    box [expr {$nd_x - 0.25}]um [expr {$ny - 0.25}]um [expr {$nd_x + 0.25}]um [expr {$ny + 0.25}]um
    paint li1

    # LI contacts on PMOS source (left side)
    set ps_x [expr {$px - 0.35}]
    box [expr {$ps_x - 0.085}]um [expr {$py - 0.085}]um [expr {$ps_x + 0.085}]um [expr {$py + 0.085}]um
    paint pdc
    box [expr {$ps_x - 0.25}]um [expr {$py - 0.25}]um [expr {$ps_x + 0.25}]um [expr {$py + 0.25}]um
    paint li1

    # LI contacts on PMOS drain (right side)
    set pd_x [expr {$px + 0.35}]
    box [expr {$pd_x - 0.085}]um [expr {$py - 0.085}]um [expr {$pd_x + 0.085}]um [expr {$py + 0.085}]um
    paint pdc
    box [expr {$pd_x - 0.25}]um [expr {$py - 0.25}]um [expr {$pd_x + 0.25}]um [expr {$py + 0.25}]um
    paint li1

    # Gate contact (below NMOS active region) on poly
    set gc_y [expr {$nd_bot - 0.55}]
    box [expr {$nx - 0.085}]um [expr {$gc_y - 0.085}]um [expr {$nx + 0.085}]um [expr {$gc_y + 0.085}]um
    paint polycont
    box [expr {$nx - 0.25}]um [expr {$gc_y - 0.25}]um [expr {$nx + 0.25}]um [expr {$gc_y + 0.25}]um
    paint li1

    # Connect NMOS source to VSS rail via li1 -> mcon -> met1
    # li1 vertical strip from source toward VSS rail
    box [expr {$ns_x - 0.085}]um 80.5um [expr {$ns_x + 0.085}]um [expr {$ny - 0.25}]um
    paint li1
    # mcon at the bottom of li1 strip
    box [expr {$ns_x - 0.085}]um 80.05um [expr {$ns_x + 0.085}]um 80.22um
    paint mcon
    box [expr {$ns_x - 0.25}]um 79.85um [expr {$ns_x + 0.25}]um 80.42um
    paint li1

    # Connect PMOS source to VDD rail via li1 -> mcon -> met1
    box [expr {$ps_x - 0.085}]um [expr {$py + 0.25}]um [expr {$ps_x + 0.085}]um 139.5um
    paint li1
    box [expr {$ps_x - 0.085}]um 139.55um [expr {$ps_x + 0.085}]um 139.72um
    paint mcon
    box [expr {$ps_x - 0.25}]um 139.35um [expr {$ps_x + 0.25}]um 139.92um
    paint li1

    # Connect NMOS drain to PMOS drain via li1 (output node)
    # Vertical li1 strip connecting both drains
    box [expr {$nd_x - 0.085}]um [expr {$ny + 0.25}]um [expr {$nd_x + 0.085}]um [expr {$py - 0.25}]um
    paint li1
}

# ============================================================
# Place 5 ring oscillator inverters + 1 output buffer
# ============================================================
set x_start 30.0
set x_step 20.0

# INV0-INV4: ring oscillator stages
for {set i 0} {$i < 5} {incr i} {
    set x [expr {$x_start + $i * $x_step}]
    draw_inverter $x 1.0 0.5 "INV$i"
}

# Buffer inverter (stage 5) - wider transistors
set buf_x [expr {$x_start + 5 * $x_step}]
draw_inverter $buf_x 2.0 1.0 "BUF"

# ============================================================
# Inter-stage wiring on li1
# Connect drain of stage N to gate of stage N+1
# Also feedback: drain of INV4 -> gate of INV0
# ============================================================

# Connect output (drain, right side) of each inverter to input (gate) of next
for {set i 0} {$i < 5} {incr i} {
    set this_x [expr {$x_start + $i * $x_step}]
    set next_x [expr {$x_start + ($i + 1) * $x_step}]

    # Drain is at this_x + 0.35, gate contact at next_x
    set drn_x [expr {$this_x + 0.35}]
    set gc_y [expr {95.0 - 0.5/2.0 - 0.55}]

    # Horizontal li1 from drain contact to next gate contact
    set y_route [expr {$gc_y}]
    box [expr {$drn_x - 0.085}]um [expr {$y_route - 0.085}]um [expr {$next_x + 0.085}]um [expr {$y_route + 0.085}]um
    paint li1

    # Vertical li1 from drain down to route level
    box [expr {$drn_x - 0.085}]um [expr {$y_route - 0.085}]um [expr {$drn_x + 0.085}]um [expr {95.0 - 0.25}]um
    paint li1
}

# Buffer output: connect drain of buffer to met1
set buf_drn_x [expr {$buf_x + 0.35}]
box [expr {$buf_drn_x - 0.085}]um 109.55um [expr {$buf_drn_x + 0.085}]um 109.72um
paint mcon

# Feedback: INV4 drain -> INV0 gate
# This needs met1 routing (going backward, above the li1 routing)
set inv4_drn_x [expr {$x_start + 4 * $x_step + 0.35}]
set inv0_gate_x $x_start
set fb_y 92.0

# mcon on INV4 drain node
box [expr {$inv4_drn_x - 0.085}]um 109.55um [expr {$inv4_drn_x + 0.085}]um 109.72um
paint mcon
box [expr {$inv4_drn_x - 0.25}]um 109.35um [expr {$inv4_drn_x + 0.25}]um 109.92um
paint met1

# met1 route from INV4 drain back to INV0 gate
# First go up in met1 to a routing channel
box [expr {$inv4_drn_x - 0.14}]um 109.5um [expr {$inv4_drn_x + 0.14}]um 143um
paint met1

# Horizontal met1 at y=142
box [expr {$inv0_gate_x - 0.14}]um 141.72um [expr {$inv4_drn_x + 0.14}]um 142.28um
paint met1

# Down from met1 to INV0 gate area
box [expr {$inv0_gate_x - 0.14}]um [expr {$fb_y}]um [expr {$inv0_gate_x + 0.14}]um 142.28um
paint met1

# mcon from met1 down to INV0 gate (li1)
set gc_y0 [expr {95.0 - 0.5/2.0 - 0.55}]
box [expr {$inv0_gate_x - 0.085}]um [expr {$gc_y0 - 0.085 + 0.5}]um [expr {$inv0_gate_x + 0.085}]um [expr {$gc_y0 + 0.085 + 0.5}]um
paint mcon

# ============================================================
# Pin Rectangles on met4 (from DEF template)
# All pins need met4 drawing + met4 pin marker + label
# ============================================================

# Analog pins (bottom edge)
set analog_x {152.260 132.940 113.620 94.300 74.980 55.660 36.340 17.020}
set analog_names {ua[0] ua[1] ua[2] ua[3] ua[4] ua[5] ua[6] ua[7]}

for {set i 0} {$i < 8} {incr i} {
    set cx [lindex $analog_x $i]
    set name [lindex $analog_names $i]
    set x1 [expr {$cx - 0.45}]
    set x2 [expr {$cx + 0.45}]
    box ${x1}um 0um ${x2}um 1.0um
    paint met4
    label $name FreeSans 4 0 0 0 c met4
    port make
    port use signal
    port class bidirectional
}

# Met4 stubs on ua[0] and ua[1] (extend 5um into cell)
box 151.81um 1.0um 152.71um 6.0um
paint met4
box 132.49um 1.0um 133.39um 6.0um
paint met4

# Digital pins (top edge, 0.3 x 1.0 um)
set dpin_data {
    clk 143.980 ena 146.740 rst_n 141.220
}
foreach {name cx} $dpin_data {
    set x1 [expr {$cx - 0.15}]
    set x2 [expr {$cx + 0.15}]
    box ${x1}um 224.76um ${x2}um 225.76um
    paint met4
    label $name FreeSans 4 0 0 0 c met4
    port make
    port use signal
    if {$name eq "clk" || $name eq "ena" || $name eq "rst_n"} {
        port class input
    }
}

# ui_in[0..7]
for {set i 0} {$i < 8} {incr i} {
    set cx [expr {138.460 - $i * 2.760}]
    set x1 [expr {$cx - 0.15}]
    set x2 [expr {$cx + 0.15}]
    box ${x1}um 224.76um ${x2}um 225.76um
    paint met4
    label "ui_in\[$i\]" FreeSans 4 0 0 0 c met4
    port make
    port use signal
    port class input
}

# uo_out[0..7]
for {set i 0} {$i < 8} {incr i} {
    set cx [expr {94.300 - $i * 2.760}]
    set x1 [expr {$cx - 0.15}]
    set x2 [expr {$cx + 0.15}]
    box ${x1}um 224.76um ${x2}um 225.76um
    paint met4
    label "uo_out\[$i\]" FreeSans 4 0 0 0 c met4
    port make
    port use signal
    port class output
}

# uio_in[0..7]
for {set i 0} {$i < 8} {incr i} {
    set cx [expr {116.380 - $i * 2.760}]
    set x1 [expr {$cx - 0.15}]
    set x2 [expr {$cx + 0.15}]
    box ${x1}um 224.76um ${x2}um 225.76um
    paint met4
    label "uio_in\[$i\]" FreeSans 4 0 0 0 c met4
    port make
    port use signal
    port class input
}

# uio_out[0..7]
for {set i 0} {$i < 8} {incr i} {
    set cx [expr {72.220 - $i * 2.760}]
    set x1 [expr {$cx - 0.15}]
    set x2 [expr {$cx + 0.15}]
    box ${x1}um 224.76um ${x2}um 225.76um
    paint met4
    label "uio_out\[$i\]" FreeSans 4 0 0 0 c met4
    port make
    port use signal
    port class output
}

# uio_oe[0..7]
for {set i 0} {$i < 8} {incr i} {
    set cx [expr {50.140 - $i * 2.760}]
    set x1 [expr {$cx - 0.15}]
    set x2 [expr {$cx + 0.15}]
    box ${x1}um 224.76um ${x2}um 225.76um
    paint met4
    label "uio_oe\[$i\]" FreeSans 4 0 0 0 c met4
    port make
    port use signal
    port class output
}

# ============================================================
# Route analog pins to circuit via met2/met3/met4
# ua[0] (enable/gate input) -> INV0 gate
# ua[1] (output) -> Buffer drain
# ============================================================

# ua[0] to INV0 gate: via met4 stub -> via3 -> met3 -> via2 -> met2 -> via -> met1 -> ...
# Use a via stack at (152.26, 4.0) connecting to met1 route to INV0 gate
set via_x 152.26

# Via stack from met4 down to met1 at (152.26, 4.0)
box [expr {$via_x - 0.10}]um 3.90um [expr {$via_x + 0.10}]um 4.10um
paint via3
box [expr {$via_x - 0.28}]um 3.72um [expr {$via_x + 0.28}]um 4.28um
paint met3
box [expr {$via_x - 0.10}]um 3.90um [expr {$via_x + 0.10}]um 4.10um
paint via2
box [expr {$via_x - 0.28}]um 3.72um [expr {$via_x + 0.28}]um 4.28um
paint met2
box [expr {$via_x - 0.085}]um 3.915um [expr {$via_x + 0.085}]um 4.085um
paint viali
box [expr {$via_x - 0.28}]um 3.72um [expr {$via_x + 0.28}]um 4.28um
paint met1

# met1 route from (152.26, 4.0) to INV0 gate area (30, ~93.7)
# Go horizontal at y=4, then vertical at x=30, then to gate
box [expr {$inv0_gate_x - 0.14}]um 3.86um [expr {$via_x + 0.14}]um 4.14um
paint met1
box [expr {$inv0_gate_x - 0.14}]um 4.0um [expr {$inv0_gate_x + 0.14}]um ${fb_y}um
paint met1

# ua[1] to buffer drain: via stack at (132.94, 4.0)
set via_x2 132.94
set buf_out_y 110.0

box [expr {$via_x2 - 0.10}]um 3.90um [expr {$via_x2 + 0.10}]um 4.10um
paint via3
box [expr {$via_x2 - 0.28}]um 3.72um [expr {$via_x2 + 0.28}]um 4.28um
paint met3
box [expr {$via_x2 - 0.10}]um 3.90um [expr {$via_x2 + 0.10}]um 4.10um
paint via2
box [expr {$via_x2 - 0.28}]um 3.72um [expr {$via_x2 + 0.28}]um 4.28um
paint met2
box [expr {$via_x2 - 0.085}]um 3.915um [expr {$via_x2 + 0.085}]um 4.085um
paint viali
box [expr {$via_x2 - 0.28}]um 3.72um [expr {$via_x2 + 0.28}]um 4.28um
paint met1

# met1 route from (132.94, 4) to buffer drain
box [expr {$buf_drn_x - 0.14}]um 3.86um [expr {$via_x2 + 0.14}]um 4.14um
paint met1
box [expr {$buf_drn_x - 0.14}]um 4.0um [expr {$buf_drn_x + 0.14}]um ${buf_out_y}um
paint met1

# ============================================================
# Save and Export
# ============================================================
select top cell
save $PROJDIR/$CELL

# Write GDS
file mkdir $PROJDIR/gds
gds write $PROJDIR/gds/$CELL.gds

# Write LEF
file mkdir $PROJDIR/lef
lef write $PROJDIR/lef/$CELL.lef -hide -pinonly

puts "Done! GDS and LEF written."

quit -noprompt
