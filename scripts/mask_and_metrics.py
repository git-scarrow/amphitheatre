#!/usr/bin/env python3
"""
Stage 1 (cont.) — mask the north-edge bayward artifact and recompute AOI metrics.

Method (documented, planning-grade):
  * The design DEM descends monotonically toward the bay (north). The global low
    (~588-589 ft) is the bayward shoreline/water plunge, NOT the venue bowl floor.
  * Artifact mask = the connected component of cells below ARTIFACT_THRESH ft that
    touches the NORTH edge of the AOI (8-connectivity). This isolates the bayward
    drop without removing interior low ground belonging to the bowl.
  * Metrics are reported BOTH for the full AOI and the masked basin so the effect
    of the mask is explicit and reversible.

Elevations: NAVD88 (Geoid12A), international feet. CRS EPSG:6494.
"""
import json, pathlib
import numpy as np
import rasterio
from rasterio.features import shapes
from scipy import ndimage

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEM = ROOT / "dem" / "dem_design_1ft.tif"
MASK_OUT = ROOT / "masks" / "artifact_mask.geojson"
CSV_OUT = ROOT / "metrics" / "aoi_metrics_recomputed.csv"
MASK_OUT.parent.mkdir(exist_ok=True)
CSV_OUT.parent.mkdir(exist_ok=True)

ARTIFACT_THRESH = 595.0  # ft NAVD88; break between bowl floor (~602-607) and bayward plunge (~588)
PCTS = [1, 5, 10, 50, 90, 95, 99]
SQFT_PER_ACRE = 43560.0

def main():
    ds = rasterio.open(DEM)
    z = ds.read(1)
    nd = ds.nodata
    valid = (z != nd) if nd is not None else np.ones_like(z, bool)
    cell_area = abs(ds.transform.a * ds.transform.e)  # ft^2 per cell (1.0)

    # --- artifact mask: connected low component touching the north edge (row 0) ---
    low = valid & (z < ARTIFACT_THRESH)
    lbl, n = ndimage.label(low, structure=np.ones((3, 3), int))
    north_labels = set(np.unique(lbl[0, :])) - {0}
    artifact = np.isin(lbl, list(north_labels)) if north_labels else np.zeros_like(low)
    print(f"artifact: {artifact.sum()} cells ({artifact.sum()*cell_area/SQFT_PER_ACRE:.3f} ac), "
          f"{len(north_labels)} N-edge component(s) of {n} below {ARTIFACT_THRESH} ft")

    # --- vectorize mask -> GeoJSON (EPSG:6494) ---
    feats = []
    for geom, val in shapes(artifact.astype("uint8"), mask=artifact, transform=ds.transform):
        feats.append({"type": "Feature",
                      "properties": {"artifact": int(val),
                                     "threshold_ft": ARTIFACT_THRESH,
                                     "datum": "NAVD88 Geoid12A intl ft"},
                      "geometry": geom})
    fc = {"type": "FeatureCollection",
          "name": "artifact_mask",
          "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::6494"}},
          "features": feats}
    MASK_OUT.write_text(json.dumps(fc))
    print(f"wrote {MASK_OUT.name}: {len(feats)} polygon(s)")

    # --- metrics, full vs masked basin ---
    def metrics(mask_bool, label):
        v = z[mask_bool]
        ps = np.percentile(v, PCTS)
        row = {"set": label, "n_cells": int(v.size),
               "area_ac": round(v.size * cell_area / SQFT_PER_ACRE, 4),
               "min": round(float(v.min()), 3), "max": round(float(v.max()), 3),
               "relief": round(float(v.max() - v.min()), 3),
               "mean": round(float(v.mean()), 3)}
        for p, val in zip(PCTS, ps):
            row[f"p{p:02d}"] = round(float(val), 3)
        p10 = row["p10"]
        below = mask_bool & (z < p10)
        row["area_below_p10_ac"] = round(below.sum() * cell_area / SQFT_PER_ACRE, 4)
        return row

    full = metrics(valid, "full_aoi")
    basin = metrics(valid & ~artifact, "masked_basin")
    ds.close()

    cols = ["set", "n_cells", "area_ac", "min", "p01", "p05", "p10", "p50",
            "p90", "p95", "p99", "max", "relief", "mean", "area_below_p10_ac"]
    lines = [",".join(cols)]
    for r in (full, basin):
        lines.append(",".join(str(r[c]) for c in cols))
    CSV_OUT.write_text("\n".join(lines) + "\n")
    print("wrote", CSV_OUT.name)
    for r in (full, basin):
        print(f"  {r['set']:13s} min {r['min']:.1f} p10 {r['p10']:.1f} "
              f"p50 {r['p50']:.1f} p90 {r['p90']:.1f} max {r['max']:.1f} "
              f"relief {r['relief']:.1f} | <p10 {r['area_below_p10_ac']:.2f} ac")

if __name__ == "__main__":
    main()
