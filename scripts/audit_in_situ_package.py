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
    "human_scale_refs.geojson",
    # ADA rebuild (2026-06-12): nodes-first network + quarantined legacy
    "ada_nodes.geojson", "ada_route.geojson", "legacy_ada_rejected.geojson",
]
# ada_route.geojson left this list when the REBUILT network took the name:
# the legacy fragments live in legacy_ada_rejected.geojson instead
SUPERSEDED_COPIES = ["seating_rows.geojson", "stage_floor.geojson"]
BOARDS = ["boards/01_site_fit_board.png", "boards/02_experience_board.png",
          "boards/03_landscape_character_board.png",
          "boards/06_human_scale_board.png", "boards/board_sources.json"]
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
        if (p.get("enclosure") == "full" or p.get("upstage_shell") is True
                or p.get("back_wall") is True
                or p.get("blocks_bay_view") is not False):
            bad_stage.append(f"{p['zone']}: full-enclosure/bay-view flags wrong")
        # NOTE: "open" means no unacceptable enclosure or new view blockage —
        # NOT "tiny". Taller mass is fine when obstruction-tested; untested
        # tall mass is the failure.
        if (p.get("max_structure_height_ft", 0) > 8.0
                and not p.get("obstruction_tested")):
            bad_stage.append(
                f"{p['zone']}: {p['max_structure_height_ft']} ft mass with no "
                "incremental-obstruction test reference")
        if p.get("rule9_status") != "open":
            bad_stage.append(f"{p['zone']}: Rule 9 OPEN status not surfaced")
        if any("declared_fan" in k for k in p):
            bad_stage.append(f"{p['zone']}: declares a fan while Rule 9 is open")
    if bad_stage:
        fail("stage intent violations: " + "; ".join(bad_stage))
    elif stage_zones:
        ok(f"{len(stage_zones)} stage zones honest (no untested mass, no full "
           "enclosure), Rule 9 OPEN surfaced, no fan declared")
    else:
        fail("no stage zones found in bowl_zones.geojson")

    named_bad = []
    for layer in ("bowl_zones.geojson", "material_zones.geojson",
                  "site_context.geojson", "event_modes.geojson"):
        for f in load_vec(layer)["features"]:
            hay = " ".join(str(v) for k, v in f["properties"].items()
                           if k in ("name", "zone", "kind", "material", "use"))
            m = FORBIDDEN_STRUCTURES.search(hay)
            if m and not f["properties"].get("obstruction_tested"):
                named_bad.append(f"{layer}:{f['properties'].get('name')} ({m.group(0)})")
    if named_bad:
        fail("enclosing structures named in layers without an "
             "incremental-obstruction test: " + ", ".join(named_bad))

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


def check_normalization_and_stage_study():
    """Gates added 2026-06-10: section balance + audience frame, the
    visual-envelope stage study, and the circularity decoupling."""
    norm_dir = os.path.join(REPO, "analysis", "in_situ_normalization")
    dec_dir = os.path.join(REPO, "analysis", "stage_seating_decoupling")
    need = {
        "normalization": [os.path.join(norm_dir, n) for n in (
            "section_balance.json", "normalization_candidates.json",
            "NORMALIZATION.md", "obstruction_envelope.json",
            "stage_typology_scores.json", "STAGE_SHAPE_STUDY.md")],
        "decoupling": [os.path.join(dec_dir, n) for n in (
            "CIRCULARITY_AUDIT.md", "audience_envelopes.geojson",
            "stage_opportunity_zones.geojson",
            "pairwise_stage_audience_scores.csv",
            "STAGE_SEATING_PARETO.md", "pareto_summary.json")],
    }
    missing = [os.path.relpath(p, REPO) for ps in need.values() for p in ps
               if not os.path.exists(p)]
    if missing:
        fail("normalization / stage-study / circularity artifacts missing — "
             "seating geometry may not justify the stage without them: "
             + ", ".join(missing))
        return
    ok("normalization, obstruction-envelope, stage-shape, and circularity "
       "artifacts all present")

    bal = json.load(open(os.path.join(norm_dir, "section_balance.json")))
    # frame freshness vs the live tread layer
    treads = load_vec("terrace_treads.geojson")["features"]
    import numpy as np
    from shapely.geometry import shape as _shape

    w = np.array([f["properties"]["seats_kept"] for f in treads], float)
    cx = np.array([_shape(f["geometry"]).centroid.x for f in treads])
    cy = np.array([_shape(f["geometry"]).centroid.y for f in treads])
    live = ((cx * w).sum() / w.sum(), (cy * w).sum() / w.sum())
    rec = bal["audience_frame"]["audience_centroid_seatweighted"]
    drift = ((live[0] - rec[0]) ** 2 + (live[1] - rec[1]) ** 2) ** 0.5
    if drift > 5.0:
        fail(f"audience frame stale: recorded centroid {drift:.1f} ft from "
             "the live tread layer — re-run scripts/normalize_sections.py")
    else:
        ok(f"audience frame fresh (centroid drift {drift:.1f} ft ≤ 5)")

    imb = bal["imbalance"]
    if (imb["min_max_ratio"] < imb["declared_threshold"]
            and not imb.get("asymmetry_justification", "").strip()):
        fail(f"section imbalance {imb['min_max_ratio']} below declared "
             f"threshold {imb['declared_threshold']} with NO justification")
    else:
        ok(f"section imbalance {imb['min_max_ratio']} vs threshold "
           f"{imb['declared_threshold']} — "
           + ("within threshold" if imb["within_threshold"]
              else "justified by measured street/terrain/splay stops"))

    st = json.load(open(os.path.join(norm_dir, "stage_typology_scores.json")))
    sf = st.get("frame_source", {}).get("audience_centroid", [0, 0])
    if ((sf[0] - rec[0]) ** 2 + (sf[1] - rec[1]) ** 2) ** 0.5 > 1.0:
        fail("stage study not tested against the CURRENT audience frame")
    if "P_inherited" not in st.get("placement_axis_comparison", {}):
        fail("inherited stage placement was not explicitly tested against "
             "the audience frame (fixed-by-inheritance)")
    izt = st.get("independent_zone_test", {})
    if not izt.get("co_leader_band"):
        fail("stage study does not cite the independent stage-opportunity "
             "zone analysis — seating alone may not justify the stage")
    tall_tested = False
    bad_verdicts = []
    for name, r in st.get("typologies", {}).items():
        hmax = max(e["height_ft"] for e in r["elements"])
        if hmax >= 15.0:
            tall_tested = True
        v = r.get("verdict", "")
        if v.startswith("FLAGGED") and "%" not in v:
            bad_verdicts.append(f"{name}: flagged without a measured share")
        vl = v.lower()
        if "too tall" in vl or ("height" in vl
                                and "not a height" not in vl):
            bad_verdicts.append(f"{name}: rejected merely for height")
        if not v.startswith("FLAGGED") and hmax > 8.0 \
                and "incremental_obstruction" not in r:
            bad_verdicts.append(f"{name}: tall candidate accepted without "
                                "incremental obstruction analysis")
    if not tall_tested:
        fail("no stage candidate ≥15 ft was tested — 'open' is being "
             "interpreted as 'tiny'; taller utilitarian typologies must be "
             "measured, not excluded a priori")
    if bad_verdicts:
        fail("stage typology verdict violations: " + "; ".join(bad_verdicts))
    if tall_tested and not bad_verdicts:
        ok(f"{len(st.get('typologies', {}))} typologies incl. tall mass "
           "tested under the visual-envelope rule; no height-only rejections")

    par = json.load(open(os.path.join(dec_dir, "pareto_summary.json")))
    probs = []
    if par.get("n_envelopes", 0) < 2 or par.get("n_stage_zones", 0) < 2:
        probs.append("fewer than 2 envelopes or 2 stage zones — no real "
                     "independent comparison")
    if len(par.get("ranked_shortlist", [])) < 3:
        probs.append("no ranked/Pareto shortlist (single-design output)")
    if not par.get("why_winner_beats_runner_up", "").strip():
        probs.append("winner lacks an explanation vs nearby alternatives")
    if par.get("stage_zones_derived_from_seating") is not False:
        probs.append("stage zones not declared independent of seating")
    import csv as _csv
    with open(os.path.join(dec_dir, "pairwise_stage_audience_scores.csv")) as fh:
        rows = list(_csv.DictReader(fh))
    inh = {r["contains_inherited_stage"] for r in rows}
    if not ({"True", "False"} <= inh):
        probs.append("pairwise table never compares inherited vs "
                     "non-inherited stage zones (fixed-by-inheritance)")
    if probs:
        fail("circularity gates: " + "; ".join(probs))
    else:
        ok(f"circularity broken: {par['n_envelopes']} envelopes x "
           f"{par['n_stage_zones']} zones, shortlist of "
           f"{len(par['ranked_shortlist'])}, inherited location compared "
           "(not assumed), winner explained")

    man_path = os.path.join(REPO, "boards", "board_sources.json")
    if os.path.exists(man_path):
        man = json.load(open(man_path))
        if man.get("claude_design_ready") is not False:
            fail("boards claim Claude-Design readiness while Rule 9 is OPEN "
                 "and the stage decision is pending")
        else:
            ok("boards explicitly not Claude-Design-ready (Rule 9 open)")
    hand = os.path.join(REPO, "docs", "claude_design_handoff.md")
    if os.path.exists(hand):
        head = open(hand).read(400)
        if "PAUSED" not in head:
            fail("docs/claude_design_handoff.md not marked PAUSED while the "
                 "stage decision is unresolved")
        else:
            ok("Claude Design handoff marked PAUSED")


def check_human_scale_refs(rasters_present):
    """Human-scale reference gates (calibrated schematic scale). Hard fails:
      · refs missing required metadata, undocumented heights, or a missing
        required placement
      · coords outside the design extents
      · refs that float/sink off their recorded ground source
      · refs whose head would cut the audited mid-row bay sightline
      · wheelchair refs absent from the ADA-critical locations or views
      · human figures in presentation outputs (viewer payload / boards)
        without the source layer, or drawn off-scale vs height_ft
    """
    import human_scale_common as HS

    src_path = os.path.join(C.VEC_DIR, "human_scale_refs.geojson")
    viewer_payload = os.path.join(REPO, "web_viewer", "data", "site_data.js")
    man_path = os.path.join(REPO, "boards", "board_sources.json")

    def presentation_claims_refs():
        hits = []
        if os.path.exists(viewer_payload):
            txt = open(viewer_payload).read()
            if '"human_refs"' in txt:
                hits.append("web_viewer/data/site_data.js")
        if os.path.exists(man_path):
            if json.load(open(man_path)).get("human_scale", {}).get("figures"):
                hits.append("boards/board_sources.json")
        return hits

    if not os.path.exists(src_path):
        claims = presentation_claims_refs()
        if claims:
            fail("human refs exist ONLY in presentation output ("
                 + ", ".join(claims) + ") — source layer "
                 "vectors_geojson/human_scale_refs.geojson missing; run "
                 "scripts/build_human_scale_refs.py")
        # absence also caught by required-files
        return

    feats = load_vec("human_scale_refs.geojson")["features"]
    humans = {f["properties"]["ref_id"]: f for f in feats
              if f["properties"].get("type") == "human"}
    dims = {f["properties"]["ref_id"]: f for f in feats
            if f["properties"].get("type") == "dimension"}

    # 1. metadata completeness + documented heights
    gaps = []
    for rid, f in humans.items():
        p = f["properties"]
        missing = [k for k in HS.REQUIRED_HUMAN_FIELDS if p.get(k) is None]
        if missing:
            gaps.append(f"{rid}: missing {missing}")
        if p.get("posture") == "standing" \
                and p.get("height_ft") not in HS.STANDING_HEIGHTS_FT:
            gaps.append(f"{rid}: standing height {p.get('height_ft')} not in "
                        f"the documented set {HS.STANDING_HEIGHTS_FT}")
        if p.get("posture") == "seated" \
                and p.get("eye_height_ft") != HS.SEATED_EYE_FT:
            gaps.append(f"{rid}: seated eye {p.get('eye_height_ft')} != the "
                        f"documented C-value standard {HS.SEATED_EYE_FT}")
        if p.get("posture") == "wheelchair" \
                and p.get("eye_height_ft") != HS.WHEELCHAIR_EYE_FT:
            gaps.append(f"{rid}: wheelchair eye {p.get('eye_height_ft')} != "
                        f"documented {HS.WHEELCHAIR_EYE_FT}")
        if p.get("blocks_bay_view") is not False:
            gaps.append(f"{rid}: blocks_bay_view must be false")
    for rid, f in dims.items():
        p = f["properties"]
        missing = [k for k in HS.REQUIRED_DIM_FIELDS if p.get(k) is None]
        if missing:
            gaps.append(f"{rid}: missing {missing}")
    if gaps:
        fail("human-scale metadata: " + "; ".join(gaps[:8])
             + ("…" if len(gaps) > 8 else ""))
    else:
        ok(f"{len(humans)} human refs + {len(dims)} dimension refs carry "
           "full metadata; heights/eye heights match the documented sets")

    # 2. required placements
    missing = [r for r in HS.REQUIRED_PLACEMENTS
               if r not in humans and r not in dims]
    if missing:
        fail(f"required human-scale placements missing: {missing}")
    else:
        ok(f"all {len(HS.REQUIRED_PLACEMENTS)} required placements present "
           "(stage front/centre, row-1 centre + pockets, promenade, "
           "cross-aisle, row 18, ADA landings, cell edge, lawn, dimensions)")

    # 3. coords inside the design extents
    from shapely.geometry import shape as _shape
    xs, ys = [], []
    for layer in ("terrace_treads.geojson", "bowl_zones.geojson"):
        for f in load_vec(layer)["features"]:
            b = _shape(f["geometry"]).bounds
            xs += [b[0], b[2]]; ys += [b[1], b[3]]
    for f in load_vec("site_context.geojson")["features"]:
        if f["properties"]["kind"] == "open_lawn":
            b = _shape(f["geometry"]).bounds
            xs += [b[0], b[2]]; ys += [b[1], b[3]]
    x0, x1, y0, y1 = min(xs) - 25, max(xs) + 25, min(ys) - 25, max(ys) + 25
    stray = []
    for rid, f in {**humans, **dims}.items():
        g = _shape(f["geometry"])
        b = g.bounds
        if b[0] < x0 or b[2] > x1 or b[1] < y0 or b[3] > y1:
            stray.append(rid)
    if stray:
        fail(f"human-scale refs outside the design extents: {stray}")
    else:
        ok("every human-scale ref inside the design/lawn extents")

    # 4. ground anchoring (float/sink) — re-derive every recorded source
    tread_elev = {(f["properties"]["section"], f["properties"]["row"]):
                  f["properties"]["tread_elev_navd88"]
                  for f in load_vec("terrace_treads.geojson")["features"]}
    zones = {f["properties"].get("name", f["properties"]["zone"]): f
             for f in load_vec("bowl_zones.geojson")["features"]}
    samp = None
    if rasters_present:
        import rasterio

        ds = rasterio.open(os.path.join(REPO, "dem", "proposed_grade_1ft.tif"))

        def samp(x, y):
            v = float(next(ds.sample([(x, y)]))[0])
            return None if v == ds.nodata else v

    sunk = []
    for rid, f in humans.items():
        p = f["properties"]
        g = p["ground_elev_navd88"]
        src = p["ground_elev_source"]
        x, y = f["geometry"]["coordinates"]
        if src.startswith("declared:"):
            ref = None
            if "tread_elev_navd88" in src and not src.endswith("design_elev"):
                anchor = p["geometry_anchor_source"]
                for (sec, row), e in tread_elev.items():
                    if f"{sec} r{row}" in anchor:
                        ref = e
            if "stage_core" in src:
                ref = zones["stage_core"]["properties"]["elev_navd88"]
            elif "cross_aisle" in src:
                ref = zones["cross_aisle"]["properties"]["elev_navd88"]
            elif "promenade_row5_bend" in src:
                ref = zones["promenade_row5_bend"]["properties"]["elev_navd88"]
            elif "design_elev" in src:
                ref = g    # ambitious emission value — checked at build time
            if ref is not None and abs(g - ref) > 0.01:
                sunk.append(f"{rid}: recorded {g} != declared source {ref}")
            # structure-deck refs (stage) legitimately sit above grade;
            # everything else must also sit ON the emitted surface
            if (samp and "structure_deck" not in src
                    and "design_elev" not in src):
                rz = samp(x, y)
                if rz is not None and abs(g - rz) > 0.35:
                    sunk.append(f"{rid}: floats/sinks {g - rz:+.2f} ft vs "
                                "proposed grade")
        elif src.startswith("raster:") and samp:
            rz = samp(x, y)
            if rz is not None and abs(g - rz) > 0.35:
                sunk.append(f"{rid}: floats/sinks {g - rz:+.2f} ft vs "
                            f"{src.split(':', 1)[1]}")
    if sunk:
        fail("human refs float or sink off their ground source: "
             + "; ".join(sunk))
    else:
        ok("no ref floats or sinks: recorded ground elevations re-derive "
           "from their declared layers and sit on the proposed grade")

    # 5. dimension honesty — geometric length vs claimed length_ft
    bad_dims = []
    for rid, f in dims.items():
        p = f["properties"]
        (ax_, ay_), (bx_, by_) = f["geometry"]["coordinates"]
        L = ((bx_ - ax_) ** 2 + (by_ - ay_) ** 2) ** 0.5
        if abs(L - p["length_ft"]) > 0.15:
            bad_dims.append(f"{rid}: drawn {L:.2f} vs claimed {p['length_ft']}")
    if "dim_scale_50ft" in dims \
            and abs(dims["dim_scale_50ft"]["properties"]["length_ft"] - 50.0) > 0.01:
        bad_dims.append("dim_scale_50ft is not 50 ft")
    if bad_dims:
        fail("dimension refs disagree with their geometry: " + "; ".join(bad_dims))
    else:
        ok("dimension refs honest: geometric lengths match claimed length_ft "
           "(50-ft bar exact)")

    # 6. bay-view obstruction — the same visual-envelope rule the stage is
    # judged by: inside the measured az-330 corridor, no head may rise above
    # the camera→NW-rim-silhouette grazing ray (everything below that ray is
    # already hidden by the rim, so it cannot block NEW bay).
    RIM_SILHOUETTE = 618.5            # flat NW rim check datum (validation F5)
    vps = {f["properties"]["name"]: f
           for f in load_vec("in_situ_viewpoints.geojson")["features"]}
    mid = vps.get("mid_row_audience_to_bay")
    corr_f = next((f for f in load_vec("site_context.geojson")["features"]
                   if f["properties"]["kind"] == "bay_view_corridor"), None)
    if mid and corr_f:
        from shapely.geometry import LineString as _LS, Point as _Pt
        corr = _shape(corr_f["geometry"])
        mp = mid["properties"]
        cx_, cy_ = mid["geometry"]["coordinates"]
        cz = mp["camera_elev_navd88"]
        dx, dy = mp["look_target_x"] - cx_, mp["look_target_y"] - cy_
        D = (dx * dx + dy * dy) ** 0.5
        ux_, uy_ = dx / D, dy / D
        # distance camera → rim silhouette along the look ray
        rim = [f for f in load_vec("site_context.geojson")["features"]
               if f["properties"]["kind"] == "rim_arrival_edge"]
        d_rim = 263.0
        if rim:
            ray = _LS([(cx_, cy_), (cx_ + ux_ * 900, cy_ + uy_ * 900)])
            hit = ray.intersection(_shape(rim[0]["geometry"]))
            if not hit.is_empty:
                pts = (hit.geoms if hasattr(hit, "geoms") else [hit])
                d_rim = min(_Pt(cx_, cy_).distance(p) for p in pts)
        slope = (RIM_SILHOUETTE - cz) / d_rim
        cuts = []
        for rid, f in humans.items():
            p = f["properties"]
            x, y = f["geometry"]["coordinates"]
            if not _Pt(x, y).within(corr):
                continue
            s = (x - cx_) * ux_ + (y - cy_) * uy_
            if s <= 0:
                continue
            graze_z = cz + slope * s
            head = p["ground_elev_navd88"] + p["height_ft"]
            if head > graze_z - 0.25:
                cuts.append(f"{rid}: head {head:.1f} vs rim-grazing ray "
                            f"{graze_z:.1f} at {s:.0f} ft")
        if cuts:
            fail("human refs add silhouette inside the bay-view corridor "
                 "(incremental obstruction vs the NW rim, the stage's own "
                 "rule): " + "; ".join(cuts))
        else:
            ok("no human ref adds silhouette above the NW-rim grazing ray "
               f"inside the bay corridor (rim {RIM_SILHOUETTE} at "
               f"{d_rim:.0f} ft)")

    # 7. wheelchair refs at the ADA-critical locations
    chairs = [rid for rid, f in humans.items()
              if f["properties"]["posture"] == "wheelchair"]
    missing_ada = [r for r in HS.ADA_CRITICAL_WHEELCHAIR if r not in chairs]
    if missing_ada:
        fail(f"wheelchair refs missing from ADA-critical locations: {missing_ada}")
    else:
        ok(f"wheelchair refs present at the ADA-critical locations: {chairs}")

    # 8. presentation outputs consume the source and render to scale
    if os.path.exists(viewer_payload):
        txt = open(viewer_payload).read()
        payload = json.loads(txt[txt.index("window.SITE_DATA = ") + 19:]
                             .strip().rstrip(";"))
        vh = {h["id"]: h for h in payload["layers"]
              .get("human_refs", {}).get("humans", [])}
        probs = []
        if not vh:
            probs.append("viewer payload carries NO human refs — stale "
                         "site_data.js; re-run scripts/build_truth_package.py")
        for rid, h in vh.items():
            srcf = humans.get(rid)
            if srcf is None:
                probs.append(f"{rid}: in the viewer but not in the source layer")
                continue
            sp = srcf["properties"]
            if abs(h["h"] - sp["height_ft"]) > 1e-6 \
                    or abs(h["z"] - sp["ground_elev_navd88"]) > 1e-6:
                probs.append(f"{rid}: viewer height/ground differs from source")
        if vh and not any(vh[r]["posture"] == "wheelchair" for r in vh):
            probs.append("no wheelchair ref reaches the viewer (ADA preset "
                         "view would show none)")
        if probs:
            fail("viewer human-scale integrity: " + "; ".join(probs))
        else:
            ok(f"viewer payload mirrors the source layer ({len(vh)} figures, "
               "heights byte-exact, wheelchair present)")

    man = json.load(open(man_path)) if os.path.exists(man_path) else {}
    hs_blocks = []
    if man:
        hs_blocks.append(("boards/board_sources.json", man.get("human_scale")))
    dp_path = os.path.join(REPO, "analysis", "decision_packet", "sources.json")
    if os.path.exists(dp_path):
        hs_blocks.append(("analysis/decision_packet/sources.json",
                          json.load(open(dp_path)).get("human_scale")))
    probs = []
    for label, blk in hs_blocks:
        if not blk or not blk.get("figures"):
            probs.append(f"{label}: boards rendered without human-scale "
                         "figure records — regenerate the boards")
            continue
        for r in blk["figures"]:
            srcf = humans.get(r["ref_id"])
            if srcf is None:
                probs.append(f"{label}:{r['ref_id']}: drawn figure has no "
                             "source ref (hand-drawn?)")
                continue
            if abs(r["drawn_height_ft"] - r["height_ft"]) > 0.05:
                probs.append(f"{label}:{r['ref_id']}: drawn "
                             f"{r['drawn_height_ft']} vs height_ft "
                             f"{r['height_ft']}")
            if abs(r["height_ft"]
                   - srcf["properties"]["height_ft"]) > 1e-6:
                probs.append(f"{label}:{r['ref_id']}: record height differs "
                             "from the source layer")
        if not blk.get("wheelchair_figures"):
            probs.append(f"{label}: no wheelchair figure on the ADA-relevant "
                         "boards")
    if not hs_blocks:
        probs.append("no board manifest carries human-scale records")
    if probs:
        fail("board human-scale integrity: " + "; ".join(probs[:8])
             + ("…" if len(probs) > 8 else ""))
    else:
        nfig = sum(len(b.get("figures", [])) for _, b in hs_blocks)
        ok(f"boards draw {nfig} figures from the source layer at 1:1 "
           "(vertex-derived extents match height_ft; wheelchair on the "
           "ADA-relevant boards)")


def check_ada_rebuild():
    """ADA gates (2026-06-12 rebuild): a route network may only be called
    anything at all if TOPOLOGY and CONFLICTS pass — slope-only validation
    is exactly the failure mode that produced the rejected legacy layer.

    FAILS when: ada_validation.json missing; any required topology pair
    disconnected; any route touches the treatment cell; any swale overlap
    without a declared engineered crossing type (or longer than the cap);
    bowl_zones still carries ada_ramp/ada_landing zones; the design state
    labels the ADA element above concept tier or drops the pending-civil
    label; or any emitted route is a fragment (endpoint not a network
    node)."""
    av_path = os.path.join(REPO, "analysis", "ada_rebuild",
                           "ada_validation.json")
    if not os.path.exists(av_path):
        fail("ADA: analysis/ada_rebuild/ada_validation.json missing — "
             "run scripts/rebuild_ada_routes.py")
        return
    with open(av_path) as fh:
        av = json.load(fh)
    hard = av.get("hard", {})
    topo = av.get("topology", {})
    if not hard.get("topology_ok"):
        bad = [k for k, v in topo.get("pairs", {}).items() if not v]
        fail(f"ADA topology gate FAILED — disconnected pairs: {bad}")
    else:
        ok(f"ADA topology: all {len(topo.get('pairs', {}))} required "
           "connections present")
    confl = av.get("conflicts", {})
    if not hard.get("conflicts_ok"):
        bad = [n for n, c in confl.get("per_route", {}).items()
               if not c.get("ok")]
        fail(f"ADA conflict gate FAILED on: {bad}")
    else:
        n_cross = sum(1 for c in confl.get("per_route", {}).values()
                      if c.get("swale_crossing_declared"))
        ok(f"ADA conflicts: 0 treatment-cell/stage/wedge violations; "
           f"{n_cross} declared engineered swale crossings")
    for n, c in confl.get("per_route", {}).items():
        if c.get("treatment_cell_ft", 0) > 0.01:
            fail(f"ADA: {n} touches the treatment cell "
                 f"({c['treatment_cell_ft']} ft) — no crossing type exists "
                 "for the cell")
        if c.get("swale_ft", 0) > 0.01 and not c.get("swale_crossing_declared"):
            fail(f"ADA: {n} crosses a swale without a declared crossing type")
    if not hard.get("slopes_ok"):
        fail("ADA slope gate FAILED (after topology+conflicts)")
    elif hard.get("topology_ok") and hard.get("conflicts_ok"):
        ok("ADA slopes: within planning tolerance AFTER topology+conflict "
           "gates (never slope-only)")
    if "pending civil" not in av.get("label", ""):
        fail("ADA: validation label must carry 'pending civil/code "
             "detailing' — never plain 'ADA compliant'")
    # routes must be node-to-node (no fragments)
    routes = topo.get("routes", {})
    node_names = set()
    try:
        nfc = load_vec("ada_nodes.geojson")
        node_names = {f["properties"]["name"] for f in nfc["features"]}
    except FileNotFoundError:
        fail("ADA: ada_nodes.geojson missing")
    frag = [n for n, ri in routes.items()
            if ri.get("from") not in node_names
            or ri.get("to") not in node_names]
    if frag:
        fail(f"ADA: fragment routes with non-node endpoints: {frag}")
    else:
        ok(f"ADA: all {len(routes)} routes are node-to-node (no fragments)")
    # legacy layer must be quarantined OUT of bowl_zones
    zones = load_vec("bowl_zones.geojson")
    leftovers = [f["properties"].get("name") for f in zones["features"]
                 if f["properties"].get("zone") in ("ada_ramp", "ada_landing")]
    if leftovers:
        fail(f"ADA: legacy ada zones still in bowl_zones.geojson: {leftovers}")
    else:
        ok("ADA: bowl_zones carries no legacy ada_ramp/ada_landing zones")
    # design state must keep the element at concept tier with the label
    ds_path = os.path.join(REPO, "truth_package", "design_state.current.json")
    if os.path.exists(ds_path):
        with open(ds_path) as fh:
            ds = json.load(fh)
        el = ds.get("elements", {}).get("ada_route", {})
        if el.get("truth_tier") not in (None, "concept"):
            fail("ADA: design_state ada_route truth_tier must be 'concept' "
                 f"until civil/code detailing (found {el.get('truth_tier')})")
        if "pending civil" not in str(el.get("status", "")):
            fail("ADA: design_state ada_route status lost the "
                 "'pending civil/code detailing' label")


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
    check_normalization_and_stage_study()
    check_human_scale_refs(rasters_present)
    check_ada_rebuild()
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
