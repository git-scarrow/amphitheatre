#!/usr/bin/env python3
"""Audit gate for the in-situ design package. Exit 0 = package acceptable.

Checks, in order:
  1. required files (vectors, qgis project, boards, renders, brief);
     DEM rasters must exist OR dem/MISSING_DATA.md must explain their absence
  2. CRS consistency — every GeoJSON layer declares EPSG:6494
  3. QGIS project layer paths all resolve (rasters may be covered by the
     missing-data diagnostic)
  4. row properties — 16 rows, R85→130 @ 3 ft, row 1 at 35 ft from the stage
     front, tread/terrain/C-value/seat fields populated, and the restated
     constants still match the tracked geometry (in_situ_common)
  5. viewpoint completeness — six named stations with camera point, look
     target, eye height, render file; mid_row_audience_to_bay REQUIRED and
     looking az 330 ± 5
  6. design-intent constraints:
       · treatment cell never permanent water (flags, not vibes)
       · stage never an enclosing shell / back wall / fly tower; ≤ 8 ft
       · no retaining walls; seat-edge risers ≤ 2 ft
       · bay-view corridor present on az 330
       · event modes: all six, schematic + nonbinding, screen temporary
  7. raster sanity when present — |cut/fill| ≤ 8 ft, cell floor ≥ 609.0

Any FAIL prints a precise diagnostic and the script exits 1.
"""
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import in_situ_common as C

REPO = C.REPO
FAILS, WARNS, PASSES = [], [], []


def ok(msg):
    PASSES.append(msg)


def fail(msg):
    FAILS.append(msg)


def warn(msg):
    WARNS.append(msg)


def rel(p):
    return os.path.relpath(p, REPO)


def load_vec(name):
    with open(os.path.join(C.VEC_DIR, name)) as fh:
        return json.load(fh)


VECTORS = [
    "terrace_treads.geojson", "terrace_edges.geojson", "bowl_zones.geojson",
    "site_context.geojson", "material_zones.geojson",
    "in_situ_viewpoints.geojson", "event_modes.geojson",
    "seating_rows.geojson", "stage_floor.geojson", "ada_route.geojson",
]
BOARDS = ["boards/01_site_fit_board.png", "boards/02_experience_board.png",
          "boards/03_landscape_character_board.png"]
REQUIRED_VPS = [
    "upper_rim_down_to_stage", "mid_row_audience_to_bay",
    "stage_looking_back_to_audience", "ada_arrival_to_cross_aisle",
    "outside_bowl_from_park_edge", "event_floor_to_treatment_cell",
]
REQUIRED_MODES = [
    "empty_park_day", "small_civic_ceremony", "movie_night",
    "amplified_concert", "festival_spillover", "winter_offseason",
]
FORBIDDEN_STRUCTURES = re.compile(
    r"(upstage shell|fly[ _-]?tower|back[ _-]?wall|proscenium|enclos(ed|ing) "
    r"(room|hall|shell))", re.I)


def check_required_files():
    missing = [f"vectors_geojson/{v}" for v in VECTORS
               if not os.path.exists(os.path.join(C.VEC_DIR, v))]
    for p in BOARDS + ["qgis/in_situ_package.qgs", "docs/in_situ_design_brief.md"]:
        if not os.path.exists(os.path.join(REPO, p)):
            missing.append(p)
    if missing:
        fail("required files absent (no diagnostic covers them): "
             + ", ".join(missing))
    else:
        ok(f"all {len(VECTORS)} vector layers, 3 boards, qgis project, brief present")

    rasters = [os.path.join(REPO, "dem", n)
               for n in ("proposed_grade_1ft.tif", "cut_fill_1ft.tif")]
    have = [os.path.exists(p) for p in rasters]
    diag = os.path.join(REPO, "dem", "MISSING_DATA.md")
    if all(have):
        ok("terrain outputs present: proposed_grade_1ft.tif + cut_fill_1ft.tif")
        if os.path.exists(diag):
            fail("dem/MISSING_DATA.md exists alongside built rasters — stale "
                 "diagnostic; re-run scripts/build_proposed_grade.py")
        if not os.path.exists(os.path.join(REPO, "dem", "in_situ_grading_manifest.json")):
            fail("rasters present but dem/in_situ_grading_manifest.json missing")
        return True
    if os.path.exists(diag):
        ok("terrain outputs absent but precisely diagnosed by dem/MISSING_DATA.md")
        return False
    fail("dem/proposed_grade_1ft.tif / cut_fill_1ft.tif absent AND no "
         "dem/MISSING_DATA.md diagnostic — run scripts/build_proposed_grade.py")
    return False


def check_crs():
    bad = []
    for v in VECTORS:
        try:
            crs = load_vec(v).get("crs", {}).get("properties", {}).get("name", "")
            if "6494" not in crs:
                bad.append(f"{v} (crs={crs or 'missing'})")
        except FileNotFoundError:
            pass
    if bad:
        fail("layers without EPSG:6494 CRS declaration: " + ", ".join(bad))
    else:
        ok("CRS EPSG:6494 declared on every vector layer")


def check_qgis():
    proj = os.path.join(REPO, "qgis", "in_situ_package.qgs")
    if not os.path.exists(proj):
        return
    diag = os.path.exists(os.path.join(REPO, "dem", "MISSING_DATA.md"))
    unresolved = []
    for ml in ET.parse(proj).getroot().iter("maplayer"):
        src = ml.find("datasource").text
        path = os.path.normpath(os.path.join(os.path.dirname(proj), src))
        if not os.path.exists(path):
            if ml.get("type") == "raster" and diag:
                continue  # covered by the missing-data diagnostic
            unresolved.append(src)
    if unresolved:
        fail("QGIS project datasources do not resolve: " + ", ".join(unresolved))
    else:
        ok("QGIS project layer paths resolve (rasters covered by diagnostic "
           "when absent)")


def check_rows():
    try:
        C.verify_against_design()
        ok("governing geometry intact: az 330 audience, ±55° fan, 16 rows, "
           "stage front 35 ft from row 1")
    except AssertionError as e:
        fail(f"design drift vs design_open_low/: {e}")
        return
    treads = load_vec("terrace_treads.geojson")["features"]
    if len(treads) != C.N_ROWS:
        fail(f"terrace_treads has {len(treads)} rows, expected {C.N_ROWS}")
    need = ["row", "radius_ft", "tread_elev_navd88", "terrain_elev_navd88",
            "cut_fill_ft", "seats_compact_18in", "seats_generous_22in",
            "tread_inner_radius_ft", "tread_outer_radius_ft"]
    incomplete = [f"row {f['properties'].get('row', '?')}: missing {k}"
                  for f in treads for k in need if k not in f["properties"]]
    no_c = [f["properties"]["row"] for f in treads
            if f["properties"]["row"] > 1
            and f["properties"].get("C_value_proposed_mm") is None]
    if incomplete or no_c:
        fail("tread property gaps: " + "; ".join(
            incomplete + ([f"rows without C-value: {no_c}"] if no_c else [])))
    else:
        ok("tread polygons carry full row properties incl. C-values and seats")
    edges = load_vec("terrace_edges.geojson")["features"]
    tall = [(f["properties"]["row"], f["properties"]["riser_ft"])
            for f in edges if abs(f["properties"]["riser_ft"]) > 2.0]
    walls = [f["properties"]["row"] for f in edges
             if f["properties"].get("retaining_wall") is not False]
    if tall:
        fail(f"seat-edge risers exceed 2 ft (retaining-wall territory): {tall}")
    if walls:
        fail(f"terrace edges not flagged retaining_wall=False: rows {walls}")
    if not tall and not walls:
        ok(f"{len(edges)} low seat edges, all ≤ 2 ft risers, no retaining walls")


def check_viewpoints():
    vps = {f["properties"]["name"]: f
           for f in load_vec("in_situ_viewpoints.geojson")["features"]}
    missing = [n for n in REQUIRED_VPS if n not in vps]
    if missing:
        fail("viewpoints missing: " + ", ".join(missing)
             + (" — the mid-row audience/bay view is REQUIRED"
                if "mid_row_audience_to_bay" in missing else ""))
        return
    gaps = []
    for n, f in vps.items():
        p = f["properties"]
        if f["geometry"]["type"] != "Point":
            gaps.append(f"{n}: camera geometry is {f['geometry']['type']}")
        for k in ("look_target_x", "look_target_y", "look_target_elev_navd88",
                  "eye_height_ft", "camera_elev_navd88", "render_file", "name"):
            if p.get(k) in (None, ""):
                gaps.append(f"{n}: missing {k}")
        rf = os.path.join(REPO, p.get("render_file", ""))
        if p.get("render_file") and not os.path.exists(rf):
            gaps.append(f"{n}: render file {p['render_file']} not generated")
    mid = vps["mid_row_audience_to_bay"]["properties"]
    if not mid.get("required"):
        gaps.append("mid_row_audience_to_bay must be flagged required=true")
    if abs(((mid["look_azimuth_deg"] - C.FACE_AZ + 180) % 360) - 180) > 5:
        gaps.append(f"mid-row view looks az {mid['look_azimuth_deg']}, "
                    f"expected {C.FACE_AZ}±5 (over the stage to the bay)")
    if gaps:
        fail("viewpoint completeness: " + "; ".join(gaps))
    else:
        ok("all 6 viewpoints complete (camera, target, eye height, renders); "
           "mid-row bay view present, required, az 330")


def check_design_intent():
    zones = {f["properties"]["zone"]: f
             for f in load_vec("bowl_zones.geojson")["features"]}
    cell = zones.get("treatment_cell_landscape")
    if cell is None:
        fail("bowl_zones missing treatment_cell_landscape")
    else:
        p = cell["properties"]
        if p.get("permanent_water") is not False or "dry" not in str(
                p.get("hydrology", "")).lower():
            fail("treatment cell not flagged as dry/ephemeral with "
                 "permanent_water=false — permanent water is forbidden")
        else:
            ok("treatment cell flagged dry/ephemeral, permanent_water=false")
    wet = []
    for layer in ("material_zones.geojson", "bowl_zones.geojson"):
        for f in load_vec(layer)["features"]:
            if f["properties"].get("permanent_water") is True:
                wet.append(f"{layer}:{f['properties'].get('name')}")
    if wet:
        fail("features claiming permanent water: " + ", ".join(wet))

    stage_zones = [f for z, f in zones.items() if z.startswith("stage")]
    bad_stage = []
    for f in stage_zones:
        p = f["properties"]
        if (p.get("enclosure") != "none" or p.get("upstage_shell") is not False
                or p.get("back_wall") is not False or p.get("fly_tower") is not False):
            bad_stage.append(f"{p['zone']}: enclosure flags wrong")
        if p.get("max_structure_height_ft", 0) > 8.0:
            bad_stage.append(f"{p['zone']}: structure height "
                             f"{p['max_structure_height_ft']} ft > 8 ft cap")
    if bad_stage:
        fail("stage rendered as an enclosing structure: " + "; ".join(bad_stage))
    elif stage_zones:
        ok(f"{len(stage_zones)} stage zones open (no shell/back wall/fly tower, ≤8 ft)")
    else:
        fail("no stage zones found in bowl_zones.geojson")

    named_bad = []
    for layer in ("bowl_zones.geojson", "material_zones.geojson",
                  "site_context.geojson", "event_modes.geojson"):
        for f in load_vec(layer)["features"]:
            hay = " ".join(str(v) for k, v in f["properties"].items()
                           if k in ("name", "zone", "kind", "material", "use"))
            m = FORBIDDEN_STRUCTURES.search(hay)
            if m:
                named_bad.append(f"{layer}:{f['properties'].get('name')} ({m.group(0)})")
    if named_bad:
        fail("forbidden structures named in layers: " + ", ".join(named_bad))

    ctx = load_vec("site_context.geojson")["features"]
    corr = [f for f in ctx if f["properties"]["kind"] == "bay_view_corridor"]
    if not corr or abs(corr[0]["properties"].get("center_az_deg", 0) - C.FACE_AZ) > 1:
        fail("bay-view corridor missing from site_context or not on az 330")
    else:
        ok("bay-view corridor present on az 330")

    events = load_vec("event_modes.geojson")["features"]
    modes = {f["properties"]["mode"] for f in events}
    missing = [m for m in REQUIRED_MODES if m not in modes]
    binding = [f["properties"].get("name") for f in events
               if not (f["properties"].get("schematic") and
                       f["properties"].get("nonbinding"))]
    screen = [f for f in events if "screen" in f["properties"].get("name", "")]
    perm_screen = [f["properties"]["name"] for f in screen
                   if "night" not in str(f["properties"]).lower()
                   and "temporar" not in str(f["properties"]).lower()]
    if missing:
        fail("event modes missing: " + ", ".join(missing))
    if binding:
        fail("event features not schematic+nonbinding: " + ", ".join(map(str, binding)))
    if perm_screen:
        fail("movie screen not flagged temporary/night-only: " + ", ".join(perm_screen))
    if not (missing or binding or perm_screen):
        ok("six event modes, all schematic + nonbinding; screen is night-only")


def check_rasters(rasters_present):
    if not rasters_present:
        return
    import numpy as np
    import rasterio
    from rasterio.features import geometry_mask

    cf_ds = rasterio.open(os.path.join(REPO, "dem", "cut_fill_1ft.tif"))
    cf = cf_ds.read(1).astype(float)
    cf[cf == cf_ds.nodata] = np.nan
    peak = float(np.nanmax(np.abs(cf)))
    if peak > 8.0:
        fail(f"cut/fill peak {peak:.1f} ft exceeds 8 ft sanity gate — grading "
             "model is doing something the design never proposed")
    else:
        ok(f"cut/fill within sanity gate (peak {peak:.2f} ft ≤ 8 ft)")
    pg = rasterio.open(os.path.join(REPO, "dem", "proposed_grade_1ft.tif"))
    grade = pg.read(1).astype(float)
    grade[grade == pg.nodata] = np.nan
    cellf = next(f for f in load_vec("bowl_zones.geojson")["features"]
                 if f["properties"]["zone"] == "treatment_cell_landscape")
    m = ~geometry_mask([cellf["geometry"]], out_shape=grade.shape,
                       transform=pg.transform, invert=False)
    cmin = float(np.nanmin(grade[m]))
    if cmin < C.TREATMENT_BOTTOM - 0.15:
        fail(f"proposed grade digs the treatment cell to {cmin:.2f}, below "
             f"the {C.TREATMENT_BOTTOM} design bottom")
    else:
        ok(f"treatment-cell proposed floor ≥ design bottom ({cmin:.2f} ft)")


def main():
    rasters_present = check_required_files()
    check_crs()
    check_qgis()
    check_rows()
    check_viewpoints()
    check_design_intent()
    check_rasters(rasters_present)

    print("\n── in-situ package audit ──")
    for m in PASSES:
        print(f"  PASS  {m}")
    for m in WARNS:
        print(f"  WARN  {m}")
    for m in FAILS:
        print(f"  FAIL  {m}")
    print(f"\n{len(PASSES)} pass · {len(WARNS)} warn · {len(FAILS)} fail")
    if FAILS:
        print("AUDIT: REJECTED")
        sys.exit(1)
    print("AUDIT: ACCEPTED — package is reproducible and on design intent")


if __name__ == "__main__":
    main()
