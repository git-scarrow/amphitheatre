#!/usr/bin/env python3
"""Audit gate for the in-situ design package. Exit 0 = package acceptable.

Enforces the THREE-SECTION NATURALISTIC GEOMETRY in addition to the
original package checks. Hard failures:

  · all seating bands share one arc centre / read as one constant-radius
    fan (the superseded design_open_low signature)
  · east / bend (southeast) / south families missing or incomplete
  · family curvature metadata absent from the tread bands
  · seating geometry sourced from design_open_low while the accepted
    Scenario E / civic-core source exists (stale single-fan layer copies
    included)
  · the boards' structural manifest declares a single fan, omits the three
    sections, or claims a different governing scheme
  · stage presented as resolved (a declared fan) while DESIGN_CANON Rule 9
    is open, or stage rendered as an enclosing shell / back wall / fly tower
  · treatment cell represented as permanent water
  · retaining walls (seat-edge risers > 2 ft)
  · the required mid_row_audience_to_bay viewpoint missing or off the bay
  · required geometry absent without a diagnostic (DEM rasters may be
    substituted ONLY by dem/MISSING_DATA.md)
  · CRS drift off EPSG:6494, unresolvable QGIS datasources, cross-aisle
    provenance not row_reclassification / claiming seam derivation

Prints precise diagnostics; exits 1 on any failure.
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


def load_vec(name):
    with open(os.path.join(C.VEC_DIR, name)) as fh:
        return json.load(fh)


VECTORS = [
    "terrace_treads.geojson", "terrace_edges.geojson", "bowl_zones.geojson",
    "site_context.geojson", "material_zones.geojson",
    "in_situ_viewpoints.geojson", "event_modes.geojson",
    "scenarioE_geometry.geojson",
]
SUPERSEDED_COPIES = ["seating_rows.geojson", "stage_floor.geojson",
                     "ada_route.geojson"]
BOARDS = ["boards/01_site_fit_board.png", "boards/02_experience_board.png",
          "boards/03_landscape_character_board.png", "boards/board_sources.json"]
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
CURVATURE_KEYS = ("fit_centre_x", "fit_centre_y", "fit_radius_ft",
                  "fit_rmse_ft", "curvature_class")


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
        ok(f"all {len(VECTORS)} vector layers, 3 boards + manifest, qgis "
           "project, brief present")

    rasters = [os.path.join(REPO, "dem", n)
               for n in ("proposed_grade_1ft.tif", "cut_fill_1ft.tif")]
    diag = os.path.join(REPO, "dem", "MISSING_DATA.md")
    if all(os.path.exists(p) for p in rasters):
        ok("terrain outputs present: proposed_grade_1ft.tif + cut_fill_1ft.tif")
        if os.path.exists(diag):
            fail("dem/MISSING_DATA.md exists alongside built rasters — stale "
                 "diagnostic; re-run scripts/build_proposed_grade.py")
        if not os.path.exists(os.path.join(REPO, "dem",
                                           "in_situ_grading_manifest.json")):
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
                continue
            unresolved.append(src)
    if unresolved:
        fail("QGIS project datasources do not resolve: " + ", ".join(unresolved))
    else:
        ok("QGIS project layer paths resolve (rasters covered by diagnostic "
           "when absent)")


def check_three_families():
    """The core regression gates: sections, curvature, no shared fan, no
    superseded design_open_low sourcing."""
    try:
        C.verify_against_design()
        ok("governing source intact: Scenario E three-section geometry, "
           "cross-aisle provenance honest, stage Rule 9 status surfaced")
    except AssertionError as e:
        fail(f"governing-source drift: {e}")
        return

    treads = load_vec("terrace_treads.geojson")["features"]
    secs = {}
    for f in treads:
        secs.setdefault(f["properties"].get("section"), []).append(f)
    missing_secs = [s for s in C.SECTIONS if s not in secs]
    if missing_secs:
        fail(f"seating families missing from the package: {missing_secs} — "
             "east / bend (southeast) / south are all required")
        return
    counts = {s: len(v) for s, v in secs.items()}
    if any(c != len(C.FORMAL_ROWS) for c in counts.values()):
        fail(f"family row counts {counts} != {len(C.FORMAL_ROWS)} formal rows each")
    else:
        ok(f"three families complete: east/bend(SE)/south x {len(C.FORMAL_ROWS)} rows")

    no_meta = [f"{f['properties'].get('section')}/r{f['properties'].get('row')}"
               for f in treads
               if any(k not in f["properties"] for k in CURVATURE_KEYS)]
    if no_meta:
        fail("tread bands without curvature metadata: " + ", ".join(no_meta[:8])
             + ("…" if len(no_meta) > 8 else ""))
    else:
        classes = {f["properties"]["curvature_class"] for f in treads}
        ok(f"curvature metadata on all {len(treads)} bands "
           f"(classes: {sorted(classes)})")

    if C.shared_fan_detected(treads):
        fail("seating reads as ONE constant-centre / constant-radius fan — "
             "regression to the superseded design_open_low scheme")
    else:
        ok("no shared arc centre: bands do not collapse onto a single fan")

    bad_src = [f"{f['properties'].get('section')}/r{f['properties'].get('row')}"
               for f in treads
               if any(s in str(f["properties"].get("geometry_source", "")).lower()
                      for s in C.SUPERSEDED_SCHEMES)]
    if bad_src:
        fail("seating sourced from superseded design_open_low: "
             + ", ".join(bad_src[:8]))
    else:
        ok("seating geometry_source is the accepted Scenario E emission")

    stale = [s for s in SUPERSEDED_COPIES
             if os.path.exists(os.path.join(C.VEC_DIR, s))]
    if stale:
        fail("stale single-fan layer copies present in vectors_geojson/ while "
             "the civic source exists: " + ", ".join(stale))
    else:
        ok("no superseded design_open_low layer copies in vectors_geojson/")

    edges = load_vec("terrace_edges.geojson")["features"]
    tall = [(f["properties"]["name"], f["properties"]["riser_ft"])
            for f in edges if abs(f["properties"]["riser_ft"]) > 2.0]
    walls = [f["properties"]["name"] for f in edges
             if f["properties"].get("retaining_wall") is not False]
    if tall:
        fail(f"seat-edge risers exceed 2 ft (retaining-wall territory): {tall}")
    if walls:
        fail(f"terrace edges not flagged retaining_wall=False: {walls}")
    if not tall and not walls:
        ok(f"{len(edges)} low seat edges, all ≤ 2 ft risers, no retaining walls")


def check_board_manifest():
    path = os.path.join(REPO, "boards", "board_sources.json")
    if not os.path.exists(path):
        return  # covered by required-files
    man = json.load(open(path))
    bad = []
    if man.get("governing_scheme") != C.GOVERNING_SCHEME:
        bad.append(f"governing_scheme={man.get('governing_scheme')}")
    if man.get("single_fan_declared") is not False:
        bad.append("single_fan_declared must be false")
    if sorted(man.get("sections", [])) != sorted(C.SECTIONS):
        bad.append(f"sections={man.get('sections')}")
    if any(s in str(man.get("seating_source", "")).lower()
           for s in C.SUPERSEDED_SCHEMES):
        bad.append("boards consume design_open_low seating")
    if man.get("stage_rule9_status") != "open":
        bad.append("stage Rule 9 status not surfaced as open")
    if bad:
        fail("boards structurally imply the wrong scheme "
             f"(boards/board_sources.json): {'; '.join(bad)}")
    else:
        ok("boards built from the three-section scheme (structural manifest)")


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
    if abs(((mid["look_azimuth_deg"] - C.BAY_VIEW_AZ + 180) % 360) - 180) > 10:
        gaps.append(f"mid-row view looks az {mid['look_azimuth_deg']}, "
                    f"expected {C.BAY_VIEW_AZ}±10 (over the stage to the bay)")
    if abs(mid["look_target_elev_navd88"] - C.BAY_PLANE) > 0.1:
        gaps.append("mid-row view target is not the bay water plane")
    if gaps:
        fail("viewpoint completeness: " + "; ".join(gaps))
    else:
        ok("all 6 viewpoints complete (camera, target, eye height, renders); "
           "mid-row bay view present, required, on the bay corridor")


def check_design_intent():
    zfeats = load_vec("bowl_zones.geojson")["features"]
    zones = {}
    for f in zfeats:
        zones.setdefault(f["properties"]["zone"], []).append(f)

    cell = zones.get("treatment_cell_landscape", [None])[0]
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

    stage_zones = [f for z, fs in zones.items() if z.startswith("stage")
                   for f in fs]
    bad_stage = []
    for f in stage_zones:
        p = f["properties"]
        if (p.get("enclosure") != "none" or p.get("upstage_shell") is not False
                or p.get("back_wall") is not False
                or p.get("fly_tower") is not False
                or p.get("blocks_bay_view") is not False):
            bad_stage.append(f"{p['zone']}: enclosure/bay-view flags wrong")
        if p.get("max_structure_height_ft", 0) > 8.0:
            bad_stage.append(f"{p['zone']}: height {p['max_structure_height_ft']} > 8 ft")
        if p.get("rule9_status") != "open":
            bad_stage.append(f"{p['zone']}: Rule 9 OPEN status not surfaced")
        if any("declared_fan" in k for k in p):
            bad_stage.append(f"{p['zone']}: declares a fan while Rule 9 is open")
    if bad_stage:
        fail("stage intent violations: " + "; ".join(bad_stage))
    elif stage_zones:
        ok(f"{len(stage_zones)} stage zones open + low (no shell/back wall/"
           "fly tower), Rule 9 OPEN surfaced, no fan declared")
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

    aisle = zones.get("cross_aisle", [None])[0]
    if aisle is None:
        fail("cross_aisle zone missing")
    else:
        p = aisle["properties"]
        if (p.get("geometry_source") != "row_reclassification"
                or p.get("seam_derived") is not False):
            fail("cross-aisle provenance violates canon Rules 6/7: "
                 f"geometry_source={p.get('geometry_source')}, "
                 f"seam_derived={p.get('seam_derived')}")
        else:
            ok("cross-aisle provenance: row_reclassification, seam_derived=false")
    prov_bad = []
    for f in zones.get("promenade_hinge", []):
        p = f["properties"]
        if p.get("seam_derived") is not False or not p.get("geometry_source"):
            prov_bad.append(f"{p.get('name')}: provenance fields")
        if p.get("cost_status") != "concept":
            prov_bad.append(f"{p.get('name')}: schematic band must be concept-tier")
    if prov_bad:
        fail("promenade provenance: " + "; ".join(prov_bad))
    if not zones.get("hinge_ray"):
        fail("hinge rays (section transitions) missing from bowl_zones")
    elif not prov_bad:
        ok("hinge rays + row-5 promenade band present with honest provenance")

    ctx = load_vec("site_context.geojson")["features"]
    corr = [f for f in ctx if f["properties"]["kind"] == "bay_view_corridor"]
    if not corr or abs(corr[0]["properties"].get("center_az_deg", 0)
                       - C.BAY_VIEW_AZ) > 1:
        fail("bay-view corridor missing from site_context or off az 330")
    else:
        ok("bay-view corridor present on az 330")

    events = load_vec("event_modes.geojson")["features"]
    modes = {f["properties"]["mode"] for f in events}
    missing = [m for m in REQUIRED_MODES if m not in modes]
    binding = [f["properties"].get("name") for f in events
               if not (f["properties"].get("schematic")
                       and f["properties"].get("nonbinding"))]
    screen = [f for f in events if "screen" in f["properties"].get("name", "")]
    perm_screen = [f["properties"]["name"] for f in screen
                   if "night" not in str(f["properties"]).lower()
                   and "temporar" not in str(f["properties"]).lower()]
    if missing:
        fail("event modes missing: " + ", ".join(missing))
    if binding:
        fail("event features not schematic+nonbinding: "
             + ", ".join(map(str, binding)))
    if perm_screen:
        fail("movie screen not flagged temporary/night-only: "
             + ", ".join(perm_screen))
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
        fail(f"cut/fill peak {peak:.1f} ft exceeds 8 ft sanity gate")
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
    man = json.load(open(os.path.join(REPO, "dem",
                                      "in_situ_grading_manifest.json")))
    if man.get("governing_scheme") != C.GOVERNING_SCHEME:
        fail("grading manifest claims a different governing scheme: "
             f"{man.get('governing_scheme')}")
    bad_tier = [z for z, v in man.get("zones", {}).items()
                if "schematic" in z and v.get("cost_status") != "concept"]
    if bad_tier:
        fail("schematic grading presented as cost-backed (Rule 3): "
             + ", ".join(bad_tier))


def main():
    rasters_present = check_required_files()
    check_crs()
    check_qgis()
    check_three_families()
    check_board_manifest()
    check_viewpoints()
    check_design_intent()
    check_rasters(rasters_present)

    print("\n── in-situ package audit (three-section civic bowl) ──")
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
    print("AUDIT: ACCEPTED — three-section package reproducible and on design intent")


if __name__ == "__main__":
    main()
