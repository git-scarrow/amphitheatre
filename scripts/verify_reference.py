#!/usr/bin/env python3
"""
Reconcile our pipeline against the authoritative reference CSVs (now on disk).

Reference method: percentiles computed on RAW GROUND POINTS (class 2), not a DEM grid.
We reproduce that exactly for two AOIs:
  * EXPANDED  = original EPT box + 150 ft buffer  (matches expanded_aoi_metrics.csv)
  * TIGHT     = original EPT box (no buffer)       (the central-bowl work area)
Both in EPSG:6494 (intl ft), NAVD88.
"""
import json, subprocess, pathlib, sys
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
TILES = [str(ROOT / "data" / f"USGS_LPC_MI_13County_2015_C16_{n}.laz") for n in (532749, 532751)]
TMP = ROOT / "scripts"

# AOI center = reprojected prior EPT-request centroid (verified == reference center)
CE, CN = 19533022.70, 750785.65
AOIS = {
    # label: (half_width_E, half_height_N)
    "expanded": (822.9737 / 2, 644.5192 / 2),  # +150 ft buffer version
    "tight":    (523.0 / 2,    352.1 / 2),      # original EPT box (central bowl)
}
PCTS = [1, 5, 10, 50, 90, 95, 99]

def dump_ground_z(label, hw, hh):
    emin, emax = CE - hw, CE + hw
    nmin, nmax = CN - hh, CN + hh
    out = TMP / f"_gz_{label}.txt"
    pipe = {"pipeline": [
        *TILES,
        {"type": "filters.merge"},
        {"type": "filters.range", "limits": "Classification[2:2]"},
        {"type": "filters.crop", "bounds": f"([{emin},{emax}],[{nmin},{nmax}])"},
        {"type": "writers.text", "format": "csv", "order": "Z", "keep_unspecified": "false",
         "filename": str(out)},
    ]}
    pf = TMP / f"_pipe_{label}.json"; pf.write_text(json.dumps(pipe))
    r = subprocess.run(["pdal", "pipeline", str(pf)], capture_output=True, text=True)
    if r.returncode: sys.exit(f"PDAL failed ({label}): {r.stderr}")
    z = np.loadtxt(out, skiprows=1)
    return z, (emin, emax, nmin, nmax)

REF_EXPANDED = dict(ground_points=149803, min=589.11, p01=592.75, p05=594.32, p10=602.04,
                    median=625.54, p90=643.16, p95=647.75, p99=652.89, max=655.99,
                    abs_relief=66.88, r1090=41.12, r1095=45.71, area_below_p10=1.0836)

def report(label, z, bounds):
    ps = dict(zip(PCTS, np.percentile(z, PCTS)))
    print(f"\n=== {label.upper()} AOI  ({bounds[1]-bounds[0]:.1f} x {bounds[3]-bounds[2]:.1f} ft) ===")
    print(f"  ground points : {z.size}")
    print(f"  min {z.min():.2f}  p01 {ps[1]:.2f}  p05 {ps[5]:.2f}  p10 {ps[10]:.2f}  "
          f"med {ps[50]:.2f}  p90 {ps[90]:.2f}  p95 {ps[95]:.2f}  p99 {ps[99]:.2f}  max {z.max():.2f}")
    print(f"  abs relief {z.max()-z.min():.2f}  r10-90 {ps[90]-ps[10]:.2f}  r10-95 {ps[95]-ps[10]:.2f}")
    return ps

def main():
    rows = []
    for label, (hw, hh) in AOIS.items():
        z, b = dump_ground_z(label, hw, hh)
        ps = report(label, z, b)
        rows.append((f"ours_{label}", z, ps, b))
        if label == "expanded":
            print("  --- vs reference expanded_aoi_metrics.csv (Δ = ours - ref) ---")
            mine = dict(ground_points=z.size, min=z.min(), p01=ps[1], p05=ps[5], p10=ps[10],
                        median=ps[50], p90=ps[90], p95=ps[95], p99=ps[99], max=z.max(),
                        abs_relief=z.max()-z.min(), r1090=ps[90]-ps[10], r1095=ps[95]-ps[10])
            for k, ref in REF_EXPANDED.items():
                if k not in mine:  # area_below_p10 is a DEM-area metric, not a point percentile
                    continue
                d = mine[k] - ref
                flag = "" if abs(d) <= (50 if k == "ground_points" else 0.6) else "  <-- CHECK"
                print(f"    {k:16s} ours {mine[k]:>10.2f}   ref {ref:>10.2f}   Δ {d:+.2f}{flag}")

    # write reconciliation CSV (point-based percentiles)
    cols = ["set", "n_points", "min", "p01", "p05", "p10", "median",
            "p90", "p95", "p99", "max", "abs_relief", "r10_90", "r10_95"]
    out = ROOT / "metrics" / "reference_reconciliation.csv"
    lines = [",".join(cols)]
    # reference row first
    r = REF_EXPANDED
    lines.append(",".join(str(x) for x in ["ref_expanded_csv", r["ground_points"], r["min"],
        r["p01"], r["p05"], r["p10"], r["median"], r["p90"], r["p95"], r["p99"], r["max"],
        r["abs_relief"], r["r1090"], r["r1095"]]))
    for label, z, ps, b in rows:
        lines.append(",".join([
            label, str(z.size), f"{z.min():.2f}", f"{ps[1]:.2f}", f"{ps[5]:.2f}",
            f"{ps[10]:.2f}", f"{ps[50]:.2f}", f"{ps[90]:.2f}", f"{ps[95]:.2f}",
            f"{ps[99]:.2f}", f"{z.max():.2f}", f"{z.max()-z.min():.2f}",
            f"{ps[90]-ps[10]:.2f}", f"{ps[95]-ps[10]:.2f}"]))
    out.write_text("\n".join(lines) + "\n")
    print(f"\nwrote {out.relative_to(ROOT)}")

if __name__ == "__main__":
    main()
