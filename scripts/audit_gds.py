"""
GDS geometry audit for tt_um_hvt006_tia.
Checks: met1 short, mcon placement, li1 spacing, ct.4, VDD-GND bridge.
"""
import gdstk, math, sys

GDS = 'gds/tt_um_hvt006_tia.gds'
A_X, A_Y = 78.26, 31.43   # A pin (Vin / gate)
Y_X, Y_Y = 81.00, 31.43   # Y pin (Vout)
VDD_Y1, VDD_Y2 = 32.72, 33.20   # VDD met1 rail y-range

lib  = gdstk.read_gds(GDS)
top  = {c.name: c for c in lib.cells}['tt_um_hvt006_tia']
polys = top.get_polygons(depth=None)

by_spec = {}
for p in polys:
    by_spec.setdefault((p.layer, p.datatype), []).append(p)

def brect(p):
    b = p.bounding_box()
    return (round(b[0][0],4), round(b[0][1],4), round(b[1][0],4), round(b[1][1],4))

def near(rects, cx, cy, tol=0.20):
    return any((r[0]-tol) < cx < (r[2]+tol) and (r[1]-tol) < cy < (r[3]+tol)
               for r in rects)

li1_r  = [brect(p) for p in by_spec.get((67,20),[])]
mcon_r = [brect(p) for p in by_spec.get((67,44),[])]
met1_r = [brect(p) for p in by_spec.get((68,20),[])]
via_r  = [brect(p) for p in by_spec.get((68,44),[])]
met2_r = [brect(p) for p in by_spec.get((69,20),[])]
via2_r = [brect(p) for p in by_spec.get((69,44),[])]
met3_r = [brect(p) for p in by_spec.get((70,20),[])]
via3_r = [brect(p) for p in by_spec.get((70,44),[])]
met4_r = [brect(p) for p in by_spec.get((71,20),[])]

fails = 0

# ----------------------------------------------------------------
# 1. met1 must NOT cross VDD rail (y=32.72..33.20) for signal wires
# ----------------------------------------------------------------
print("=== 1. met1 Vout-VPWR short check ===")
for r in met1_r:
    if r[0] > 5.0 and r[2] < 90 and r[1] < VDD_Y1 and r[3] > VDD_Y2:
        print(f"  FAIL: met1 {r} crosses VDD rail y={VDD_Y1}-{VDD_Y2} (VOUT-VPWR short)")
        fails += 1
if fails == 0:
    print("  PASS: no signal met1 crosses VDD rail")

# ----------------------------------------------------------------
# 2. Connection chains A_ABS and Y_ABS
# ----------------------------------------------------------------
print("\n=== 2. Signal pin connection chains ===")
chain_a = {
    'li1 at A':  near(li1_r,  A_X, A_Y),
    'mcon at A': near(mcon_r, A_X, A_Y),
    'met1 at A': near(met1_r, A_X, A_Y),
    'via at A':  near(via_r,  A_X, A_Y),
    'met2 at A': near(met2_r, A_X, A_Y),
}
chain_y = {
    'li1 at Y':  near(li1_r,  Y_X, Y_Y),
    'mcon at Y': near(mcon_r, Y_X, Y_Y),
    'met1 at Y': near(met1_r, Y_X, Y_Y),
    'via at Y':  near(via_r,  Y_X, Y_Y),
    'met2 at Y': near(met2_r, Y_X, Y_Y),
}
for k, v in chain_a.items():
    status = "OK" if v else "MISSING"
    if not v and k != 'li1 at A':  # li1 comes from SC
        fails += 1
    print(f"  {k}: {status}")
print("  ---")
for k, v in chain_y.items():
    status = "OK" if v else "MISSING"
    if not v and k in ('mcon at Y', 'met1 at Y', 'via at Y', 'met2 at Y'):
        fails += 1
    print(f"  {k}: {status}")

# met2 reaches channel height ~36.9
m2_at_y_col = [r for r in met2_r if (r[0]-0.5) < Y_X < (r[2]+0.5)]
print(f"\n  met2 wires at Y_COL (x≈{Y_X}):")
for r in m2_at_y_col:
    print(f"    y={r[1]:.3f}..{r[3]:.3f}  {'OK reaches channel' if r[3] > 36 else 'SHORT'}")

# ----------------------------------------------------------------
# 3. li1 spacing (li.3)
# ----------------------------------------------------------------
print("\n=== 3. li1 spacing violations (li.3, min 0.170um) ===")
viols = 0
for i in range(len(li1_r)):
    for j in range(i+1, len(li1_r)):
        r1, r2 = li1_r[i], li1_r[j]
        gx = max(0.0, max(r1[0], r2[0]) - min(r1[2], r2[2]))
        gy = max(0.0, max(r1[1], r2[1]) - min(r1[3], r2[3]))
        sp = math.sqrt(gx**2+gy**2) if gx>0 and gy>0 else max(gx,gy)
        # Use 169 nm threshold (integer nm grid) to avoid fp boundary at exactly 170 nm
        if sp < 0.1699 and sp > 1e-9:
            viols += 1
            fails += 1
            print(f"  FAIL sp={sp:.4f}: [{i}] vs [{j}]")
if viols == 0:
    print("  PASS: 0 violations")

# ----------------------------------------------------------------
# 4. ct.4 mcon must be covered by li1
# ----------------------------------------------------------------
print("\n=== 4. ct.4: mcon covered by li1 ===")
ct4 = 0
for i, r in enumerate(mcon_r):
    covered = any(lr[0]<=r[0]+1e-6 and lr[2]>=r[2]-1e-6 and
                  lr[1]<=r[1]+1e-6 and lr[3]>=r[3]-1e-6 for lr in li1_r)
    if not covered:
        ct4 += 1
        fails += 1
        print(f"  FAIL: mcon[{i}] {r} not covered by li1")
if ct4 == 0:
    print(f"  PASS: all {len(mcon_r)} mcon covered")

# ----------------------------------------------------------------
# 5. met4 VDD-GND bridge check
# ----------------------------------------------------------------
print("\n=== 5. met4 VDD-GND bridge ===")
bridges = [r for r in met4_r if r[0] < 3.0 and r[2] > 4.5 and r[0] > 0.5]
if bridges:
    for r in bridges:
        print(f"  FAIL: met4 {r} bridges VDD(x=1-3) and GND(x=4.5-6.5)")
        fails += 1
else:
    print("  PASS: no VDD-GND met4 bridge")

# ----------------------------------------------------------------
# 6. ua[] pin connectivity on met4
# ----------------------------------------------------------------
print("\n=== 6. ua[] pin met4 stubs ===")
UA0_X, UA1_X = 152.260, 132.940
ua0_stubs = [r for r in met4_r if abs((r[0]+r[2])/2 - UA0_X) < 1.0 and r[1] < 5]
ua1_stubs = [r for r in met4_r if abs((r[0]+r[2])/2 - UA1_X) < 1.0 and r[1] < 5]
print(f"  ua[0] (x={UA0_X}) met4 stub at y≈0: {'OK' if ua0_stubs else 'MISSING'}")
print(f"  ua[1] (x={UA1_X}) met4 stub at y≈0: {'OK' if ua1_stubs else 'MISSING'}")
if not ua0_stubs: fails += 1
if not ua1_stubs: fails += 1

# Check VIN and VOUT vertical met4 bridges reach down to their horizontal buses
vin_bridge  = [r for r in met4_r if abs((r[0]+r[2])/2 - A_X) < 1.0 and r[3] > 38]
vout_bridge = [r for r in met4_r if abs((r[0]+r[2])/2 - Y_X) < 1.0 and r[3] > 35]
print(f"  VIN  vertical met4 at x={A_X}: {'OK' if vin_bridge else 'MISSING'}")
print(f"  VOUT vertical met4 at x={Y_X}: {'OK' if vout_bridge else 'MISSING'}")

# ----------------------------------------------------------------
# 7. Summary
# ----------------------------------------------------------------
print(f"\n{'='*50}")
print(f"Layer counts: li1={len(li1_r)}, mcon={len(mcon_r)}, met1={len(met1_r)},",
      f"met2={len(met2_r)}, met4={len(met4_r)}")
print(f"met5: {len(by_spec.get((72,20),[]))} (PASS if 0)")
print(f"hvi:  {len(by_spec.get((75,20),[]))} (PASS if 0)")
print(f"\nTotal failures: {fails}")
if fails == 0:
    print("ALL CHECKS PASS")
else:
    print("SOME CHECKS FAILED -- review above")
    sys.exit(1)
