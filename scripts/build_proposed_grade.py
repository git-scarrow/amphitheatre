#!/usr/bin/env python3
"""Proposed-grade + cut/fill rasters for the in-situ package.

Inputs   dem/dem_design_1ft.tif (existing ground)
         vectors_geojson/terrace_treads.geojson   (tread elevations)
         vectors_geojson/stage_floor.geojson      (stage, shoulders, forecourt, cell)
         vectors_geojson/ada_route.geojson        (ramp corridors)
Outputs  dem/proposed_grade_1ft.tif
         dem/cut_fill_1ft.tif        (proposed − existing; + = fill, − = cut)
         dem/in_situ_grading_manifest.json  (volumes per zone, flags)

Grading model (planning-grade, matches design_open_low intent):
  · tread polygons take their design tread elevation (≈9 CY fill, front rows)
  · stage core, lateral shoulders, forecourt take the 612.5 event floor
  · ADA ramps cut 6 ft corridors with linear grade from existing arrival
    ground to their design landing
  · the treatment cell is shaped DOWN ONLY toward bottom 609.1 at 4:1 from
    a 612.5 edge grade — SCHEMATIC stand-in for the Stage-5 cell grading,
    flagged in the manifest; never raises grade, never impounds permanent water

Missing-data path: when dem/dem_design_1ft.tif is absent (rasters and source
LiDAR are gitignored — a fresh checkout has neither) this writes a precise
diagnostic to dem/MISSING_DATA.md and exits 0 so the vector/board pipeline
can still complete. EPSG:6494, NAVD88 intl ft.
"""
import json
import os
import sys

import in_situ_common as C

MISSING = os.path.join(C.REPO, "dem", "MISSING_DATA.md")

DIAGNOSTIC = """\
# MISSING DATA — proposed-grade build skipped

`scripts/build_proposed_grade.py` could not find **`dem/dem_design_1ft.tif`**
(existing-ground DEM, 1 ft, EPSG:6494, NAVD88 intl ft).

## What was skipped
- `dem/proposed_grade_1ft.tif` (existing ground + tread/stage/ADA/cell grading)
- `dem/cut_fill_1ft.tif` and `dem/in_situ_grading_manifest.json` (volumes)
- hillshade base on the boards (boards fall back to vector-only rendering)

## What still completed
All vector layers in `vectors_geojson/`, the QGIS project, viewpoint stations
(with documented fallback elevations), event overlays, and the three boards.

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
    layers = C.verify_against_design()
    if not os.path.exists(C.DEM_DESIGN):
        os.makedirs(os.path.dirname(MISSING), exist_ok=True)
        with open(MISSING, "w") as fh:
            fh.write(DIAGNOSTIC)
        print(f"DEM missing -> wrote {os.path.relpath(MISSING, C.REPO)} (vector "
              "pipeline continues; rasters skipped)")
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
    zone_burns = []  # (zone, mask) for the manifest

    def burn(geom_elev_pairs, zone, fill_only=False):
        surf = rasterize(geom_elev_pairs, out_shape=(H, W), transform=T,
                         fill=np.nan, dtype="float64", all_touched=False)
        m = np.isfinite(surf) & valid
        if fill_only:
            # terrain-following fill to the design plane; never cut high spots
            m = m & (surf > proposed)
        proposed[m] = surf[m]
        zone_burns.append((zone, m))
        return m

    # Treads are FILL-ONLY: the design seats rows on the natural rake, so the
    # tread plane is reached by fill where terrain dips below it and the
    # terrain is left alone where it rides above (residual cross-fall is
    # reported, not graded away). A level-bench burn would claim ~700 CY of
    # cut the design never proposes — the SCENARIO_B_VALIDATION lesson.
    treads = json.load(open(os.path.join(C.VEC_DIR, "terrace_treads.geojson")))["features"]
    tread_pairs = [(f["geometry"], f["properties"]["tread_elev_navd88"]) for f in treads]
    tread_fill_m = burn(tread_pairs, "terrace_treads", fill_only=True)
    tread_surf = rasterize(tread_pairs, out_shape=(H, W), transform=T,
                           fill=np.nan, dtype="float64", all_touched=False)
    tread_all = np.isfinite(tread_surf) & valid
    high = tread_all & (existing > tread_surf)
    residual_high = {
        "area_sf": round(float(high.sum()), 0),
        "volume_above_plane_cy": round(float((existing[high] - tread_surf[high]).sum()) / 27.0, 1),
        "max_above_plane_ft": round(float((existing[high] - tread_surf[high]).max()), 2) if high.any() else 0.0,
    }

    floor = {f["properties"]["name"]: f for f in layers["floor"]}
    burn([(floor[n]["geometry"], C.FOCUS_ELEV)
          for n in ("stage", "stage_shoulder_left", "stage_shoulder_right",
                    "event_floor_forecourt")], "stage_and_floor")

    # treatment cell — schematic down-only shaping toward 609.1 at 4:1
    cell = shape(floor["treatment_wet_cell"]["geometry"])
    cmask = ~geometry_mask([cell.__geo_interface__], out_shape=(H, W),
                           transform=T, invert=False) & valid
    rr, cc = np.nonzero(cmask)
    if rr.size:
        xs, ys = rasterio.transform.xy(T, rr, cc)
        pts = shapely.points(np.asarray(xs), np.asarray(ys))
        dist = shapely.distance(pts, cell.exterior)
        target = np.maximum(C.TREATMENT_BOTTOM, C.FOCUS_ELEV - dist / 4.0)
        vals = np.minimum(existing[rr, cc], target)   # never raise grade
        proposed[rr, cc] = vals
        zone_burns.append(("treatment_cell_schematic", cmask))

    # ADA ramps — 6 ft corridors, linear grade from existing arrival to landing
    ada = C.load_design("ada_route.geojson")["features"]
    mid_row = next(f for f in ada if f["properties"]["name"] == "mid_cross_aisle")
    aisle_elev = mid_row["properties"]["elev_navd88"]
    for f in ada:
        p = f["properties"]
        if p["type"] != "switchback_ramp":
            continue
        line = shape(f["geometry"])
        (x0, y0) = line.coords[0]
        r0, c0 = rasterio.transform.rowcol(T, x0, y0)
        start = existing[r0, c0] if (0 <= r0 < H and 0 <= c0 < W and
                                     valid[r0, c0]) else C.FOCUS_ELEV
        end = C.FOCUS_ELEV if p["name"].endswith("A_floor") else aisle_elev
        corr = line.buffer(3.0, cap_style="flat")
        m = ~geometry_mask([corr.__geo_interface__], out_shape=(H, W),
                           transform=T, invert=False) & valid
        rr, cc = np.nonzero(m)
        if not rr.size:
            continue
        xs, ys = rasterio.transform.xy(T, rr, cc)
        t = shapely.line_locate_point(line, shapely.points(np.asarray(xs),
                                                           np.asarray(ys)))
        proposed[rr, cc] = start + (end - start) * np.clip(t / line.length, 0, 1)
        zone_burns.append((p["name"], m))

    cut_fill = np.where(valid, proposed - existing, 0.0)

    prof = ds.profile.copy()
    prof.update(dtype="float32", nodata=nodata, count=1, compress="deflate")
    out_grade = os.path.join(C.REPO, "dem", "proposed_grade_1ft.tif")
    out_cf = os.path.join(C.REPO, "dem", "cut_fill_1ft.tif")
    with rasterio.open(out_grade, "w", **prof) as o:
        o.write(np.where(valid, proposed, nodata).astype("float32"), 1)
    cf_prof = prof.copy()
    cf_prof.update(nodata=-9999.0)
    with rasterio.open(out_cf, "w", **cf_prof) as o:
        o.write(np.where(valid, cut_fill, -9999.0).astype("float32"), 1)

    cell_ft3 = abs(T.a * T.e)  # 1 ft cells
    manifest = {
        "crs": "EPSG:6494",
        "datum": "NAVD88 Geoid12A intl ft",
        "source_dem": "dem/dem_design_1ft.tif",
        "outputs": ["dem/proposed_grade_1ft.tif", "dem/cut_fill_1ft.tif"],
        "fill_cy_total": round(float(cut_fill[cut_fill > 0].sum()) * cell_ft3 / 27.0, 1),
        "cut_cy_total": round(float(-cut_fill[cut_fill < 0].sum()) * cell_ft3 / 27.0, 1),
        "zones": {},
        "flags": {
            "tread_fill_model": "fill-only to the design tread plane (rows sit on "
                                "the natural rake); gross fill exceeds the 9 CY "
                                "centreline estimate because arc ends dip below "
                                "the row-median terrain — cf. SCENARIO_B_VALIDATION",
            "tread_residual_above_plane": residual_high,
            "treatment_cell_grading": "schematic 4:1 shaping toward 609.1 — "
                                      "stand-in for Stage-5 cell design, down-only",
            "ada_ramp_grading": "linear 6 ft corridors between arrival ground "
                                "and design landings; switchback geometry not "
                                "modelled; Route A clips the treatment-cell edge "
                                "(boardwalk candidate) — overlap shows as fill in "
                                "the cell zone row",
            "permanent_water": False,
        },
    }
    manifest["site_balance_cy"] = round(manifest["fill_cy_total"] - manifest["cut_cy_total"], 1)
    manifest["flags"]["cut_balance"] = (
        "on-footprint fill exceeds on-footprint cut; the design's 'never imports "
        "fill' claim relies on on-site borrow — candidate borrow zones are mapped "
        "in earthwork_scenarios.geojson (S01-S03)"
    )
    for zone, m in zone_burns:
        d = cut_fill[m]
        manifest["zones"][zone] = {
            "area_sf": round(float(m.sum()) * cell_ft3, 0),
            "fill_cy": round(float(d[d > 0].sum()) * cell_ft3 / 27.0, 1),
            "cut_cy": round(float(-d[d < 0].sum()) * cell_ft3 / 27.0, 1),
        }
    with open(os.path.join(C.REPO, "dem", "in_situ_grading_manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=1)
    if os.path.exists(MISSING):
        os.remove(MISSING)  # stale diagnostic from a DEM-less run
    print(f"  wrote dem/proposed_grade_1ft.tif, dem/cut_fill_1ft.tif")
    print(f"  totals: fill {manifest['fill_cy_total']} CY · cut {manifest['cut_cy_total']} CY"
          f" (manifest: dem/in_situ_grading_manifest.json)")


if __name__ == "__main__":
    main()
