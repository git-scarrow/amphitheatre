#!/usr/bin/env python3
"""Proposed-grade + cut/fill rasters for the three-section civic bowl.

Inputs   dem/dem_design_1ft.tif (existing ground)
         vectors_geojson/terrace_treads.geojson   (restored tread planes)
         vectors_geojson/bowl_zones.geojson       (aisle, swales, cell)
Outputs  dem/proposed_grade_1ft.tif
         dem/cut_fill_1ft.tif        (proposed − existing; + = fill, − = cut)
         dem/in_situ_grading_manifest.json  (volumes per zone, tiers, flags)

Grading model (planning-grade, mirrors the validated Scenario E earthwork):
  · tread bands restored to their composition elevation (cut AND fill —
    the Scenario D restoration; z-residuals are gated ≤0.25 ft so moves
    are small)
  · cross-aisle benched level at 622.01 (rows 9/10 reclassification)
  · drainage swales cut down by their design depth (down-only)
  · treatment cell shaped DOWN ONLY toward 609.1 at 4:1 — SCHEMATIC
    stand-in, flagged; never impounds permanent water
  · ADA switchbacks are NOT re-burned here — their geometry-backed volumes
    live in analysis/scenarioE_civic/earthwork.csv and are referenced
  · the stage deck is a STRUCTURE (refit OPEN per Rule 9), not grading

Missing-data path: when dem/dem_design_1ft.tif is absent (fresh checkout)
this writes dem/MISSING_DATA.md and exits 0 so the vector/board pipeline
completes. EPSG:6494, NAVD88 intl ft.
"""
import json
import os

import in_situ_common as C

MISSING = os.path.join(C.REPO, "dem", "MISSING_DATA.md")

DIAGNOSTIC = """\
# MISSING DATA — proposed-grade build skipped

`scripts/build_proposed_grade.py` could not find **`dem/dem_design_1ft.tif`**
(existing-ground DEM, 1 ft, EPSG:6494, NAVD88 intl ft).

## What was skipped
- `dem/proposed_grade_1ft.tif` (existing ground + tread/aisle/swale/cell grading)
- `dem/cut_fill_1ft.tif` and the regenerated grading manifest
- hillshade base on the boards (boards fall back to vector-only rendering)

## What still completed
All vector layers in `vectors_geojson/`, the QGIS project, viewpoint stations
(with documented fallback elevations), event overlays, and the three boards.
The committed `dem/in_situ_grading_manifest.json` (if present) records the
volumes from the last DEM-backed build; Scenario E's validated component
volumes remain in `analysis/scenarioE_civic/earthwork.csv`.

## How to restore the DEM
1. Fetch the two USGS LiDAR tiles into `data/` (gitignored):
   `USGS_LPC_MI_13County_2015_C16_532749.laz` and `..._532751.laz`
   (USGS LPC MI 13County 2015 C16, e.g. via The National Map / EPT).
2. Run `python scripts/build_dems.py` (needs the PDAL CLI) to rebuild
   `dem/dem_design_1ft.tif` and `dem/dem_context_2p5ft.tif`.
3. Re-run `bash scripts/build_in_situ_package.sh`.

This file is deleted automatically once the build succeeds with a DEM.
"""


def main():
    C.verify_against_design()
    if not os.path.exists(C.DEM_DESIGN):
        os.makedirs(os.path.dirname(MISSING), exist_ok=True)
        with open(MISSING, "w") as fh:
            fh.write(DIAGNOSTIC)
        print(f"DEM missing -> wrote {os.path.relpath(MISSING, C.REPO)} "
              "(vector pipeline continues; rasters skipped)")
        return

    import numpy as np
    import rasterio
    from rasterio.features import rasterize, geometry_mask
    import shapely
    from shapely.geometry import shape

    ds = rasterio.open(C.DEM_DESIGN)
    existing = ds.read(1).astype("float64")
    nodata = ds.nodata if ds.nodata is not None else -9999.0
    valid = existing != nodata
    T = ds.transform
    H, W = existing.shape
    proposed = existing.copy()
    zone_burns = []

    def burn(geom_elev_pairs, zone, all_touched=True):
        # all_touched=True flattens the WHOLE visible footprint of each flat
        # plate, including the perimeter fringe.  With all_touched=False the
        # one-cell ring whose centre falls outside the polygon kept existing
        # ground, which rose up to ~2.7 ft above the flat tread — green terrain
        # poking through the rendered seating plate (the audited overflow defect,
        # analysis/terrain_audit/).  Flat terraces MUST burn all_touched=True so
        # no retained ground overflows a designed flat surface.
        surf = rasterize(geom_elev_pairs, out_shape=(H, W), transform=T,
                         fill=np.nan, dtype="float64", all_touched=all_touched)
        m = np.isfinite(surf) & valid
        proposed[m] = surf[m]
        zone_burns.append((zone, m))

    treads = json.load(open(os.path.join(C.VEC_DIR, "terrace_treads.geojson")))["features"]
    burn([(f["geometry"], f["properties"]["tread_elev_navd88"]) for f in treads],
         "terrace_treads_restored")

    zfeats = json.load(open(os.path.join(C.VEC_DIR, "bowl_zones.geojson")))["features"]
    zones = {}
    for f in zfeats:
        zones.setdefault(f["properties"]["zone"], []).append(f)

    burn([(zones["cross_aisle"][0]["geometry"], C.AISLE_ELEV)], "cross_aisle")

    for f in zones.get("drainage_swale", []):
        depth = float(f["properties"].get("depth_ft") or 0.5)
        m = ~geometry_mask([f["geometry"]], out_shape=(H, W), transform=T,
                           invert=False) & valid
        proposed[m] = np.minimum(proposed[m], existing[m] - depth)
        zone_burns.append((f["properties"].get("name", "drainage_swale"), m))

    # treatment cell — schematic down-only shaping toward 609.1 at 4:1
    cell = shape(zones["treatment_cell_landscape"][0]["geometry"])
    cmask = ~geometry_mask([cell.__geo_interface__], out_shape=(H, W),
                           transform=T, invert=False) & valid
    rr, cc = np.nonzero(cmask)
    if rr.size:
        xs, ys = rasterio.transform.xy(T, rr, cc)
        pts = shapely.points(np.asarray(xs), np.asarray(ys))
        dist = shapely.distance(pts, cell.exterior)
        target = np.maximum(C.TREATMENT_BOTTOM, C.FOCUS_ELEV - dist / 4.0)
        proposed[rr, cc] = np.minimum(existing[rr, cc], target)
        zone_burns.append(("treatment_cell_schematic", cmask))

    cut_fill = np.where(valid, proposed - existing, 0.0)

    prof = ds.profile.copy()
    prof.update(dtype="float32", nodata=nodata, count=1, compress="deflate")
    with rasterio.open(os.path.join(C.REPO, "dem", "proposed_grade_1ft.tif"),
                       "w", **prof) as o:
        o.write(np.where(valid, proposed, nodata).astype("float32"), 1)
    cf_prof = prof.copy()
    cf_prof.update(nodata=-9999.0)
    with rasterio.open(os.path.join(C.REPO, "dem", "cut_fill_1ft.tif"),
                       "w", **cf_prof) as o:
        o.write(np.where(valid, cut_fill, -9999.0).astype("float32"), 1)

    cell_ft3 = abs(T.a * T.e)
    tiers = {"terrace_treads_restored": "geometry_backed",
             "cross_aisle": "geometry_backed",
             "east_flank_swale": "geometry_backed",
             "south_flank_swale": "geometry_backed",
             "treatment_cell_schematic": "concept"}
    manifest = {
        "crs": "EPSG:6494",
        "datum": "NAVD88 Geoid12A intl ft",
        "governing_scheme": C.GOVERNING_SCHEME,
        "source_dem": "dem/dem_design_1ft.tif",
        "outputs": ["dem/proposed_grade_1ft.tif", "dem/cut_fill_1ft.tif"],
        "fill_cy_total": round(float(cut_fill[cut_fill > 0].sum()) * cell_ft3 / 27.0, 1),
        "cut_cy_total": round(float(-cut_fill[cut_fill < 0].sum()) * cell_ft3 / 27.0, 1),
        "zones": {},
        "flags": {
            "tread_model": "restored to composition elevation (Scenario D "
                           "restoration — cut AND fill; z-residual gate 0.25 ft)",
            "flat_plate_rasterization": "treads + cross-aisle burned "
                           "all_touched=True (2026-06-27): flattens the full "
                           "visible footprint incl. perimeter fringe so no "
                           "existing ground overflows a designed flat terrace. "
                           "Prior all_touched=False left a one-cell ring of "
                           "retained ground up to +2.71 ft above the plate "
                           "(audit: analysis/terrain_audit/).",
            "ada_ramps": "not burned in this raster; geometry-backed volumes in "
                         "analysis/scenarioE_civic/earthwork.csv (route A 79.2, "
                         "route B 126.0 gross CY)",
            "stage": "low deck STRUCTURE, not grading; refit OPEN per "
                     "DESIGN_CANON Rule 9 — excluded here as in Scenario E's "
                     "500.8 CY total",
            "orchestra_event_floor": "left on existing grade (schematic zone, "
                                     "concept tier)",
            "treatment_cell_grading": "schematic 4:1 shaping toward 609.1 — "
                                      "down-only, never impounds water",
            "permanent_water": False,
            "reference_earthwork": "analysis/scenarioE_civic/earthwork.csv "
                                   "(validated component volumes, 500.8 CY gross)",
        },
    }
    for zone, m in zone_burns:
        d = cut_fill[m]
        manifest["zones"][zone] = {
            "area_sf": round(float(m.sum()) * cell_ft3, 0),
            "fill_cy": round(float(d[d > 0].sum()) * cell_ft3 / 27.0, 1),
            "cut_cy": round(float(-d[d < 0].sum()) * cell_ft3 / 27.0, 1),
            "cost_status": tiers.get(zone, "concept"),
        }
    with open(os.path.join(C.REPO, "dem", "in_situ_grading_manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=1)
    if os.path.exists(MISSING):
        os.remove(MISSING)
    print("  wrote dem/proposed_grade_1ft.tif, dem/cut_fill_1ft.tif")
    print(f"  totals: fill {manifest['fill_cy_total']} CY · cut "
          f"{manifest['cut_cy_total']} CY (manifest: dem/in_situ_grading_manifest.json)")


if __name__ == "__main__":
    main()
