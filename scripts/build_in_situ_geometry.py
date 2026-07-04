#!/usr/bin/env python3
"""In-situ geometry for the three-section naturalistic civic bowl.

Consumes the GOVERNING Scenario E emitted geometry (canon-ACCEPTED) plus the
extended-bays composition table and emits:

  vectors_geojson/terrace_treads.geojson   45 restored tread bands in three
      terrain-fitted sections (east / bend=SE / south), enriched with
      per-band elevation/zone/seats from the composition table and MEASURED
      curvature metadata (kasa fit on the band centerline)
  vectors_geojson/terrace_edges.geojson    low seat-edge polylines (front
      edge of each band) with riser heights vs the surface in front
  vectors_geojson/bowl_zones.geojson       stage (inherited, Rule 9 OPEN),
      orchestra event floor (derived, schematic), treatment-cell landscape,
      cross-aisle + ADA ramps + landings (Scenario E verbatim, provenance
      preserved), drainage swales, row-5 promenade hinge band, hinge rays,
      row-end shoulders, construction envelope, untouched slope
  vectors_geojson/scenarioE_geometry.geojson  verbatim copy of the governing
      source (predictable path; CRS header added)

No feature is sourced from design_open_low except what Scenario E itself
inherits: the stage surfaces (flagged rule9_status=open) and the treatment
cell (drain target). The audit gate enforces this.

Planning-grade. NAVD88 intl ft. EPSG:6494. Run from repo root.

── PIPELINE ARTIFACT CONTRACT (read before trusting this script's output) ──────
This emitter's `bowl_zones.geojson` is an INTERMEDIATE product, not final Scenario
E state. In particular:
  * This emitter does NOT emit `ada_ramp` / `ada_landing` zones. The scenarioE ADA
    layer was rejected by the 2026-06-12 rebuild; the LIVE accessible route is the
    rebuilt `ada_route.geojson` network (design_ada_routes.py), which this emitter
    must never delete (see the STALE_SINGLEFAN guard below).
  * It emits inherited/schematic STAGE zones (stage_core / stage_shoulder_*, flagged
    Rule 9 OPEN) and a schematic `orchestra_event_floor` that is re-emitted against
    the ADOPTED P_opt deck edge (0-quantity cleanup; _adopted_stage_footprint()).
The repo is valid ONLY after the full pipeline, IN ORDER:
    build_in_situ_geometry.py → rebuild_ada_routes.py → design_ada_routes.py
    → design_constructed_ada.py → build_site_context.py → build_truth_package.py
    → scripts/comparators/audit_comparators.py
Do NOT inspect or commit emitter-only outputs as final. Verify with
`scripts/check_pipeline_artifact_contract.py` (and docs/PIPELINE_ARTIFACT_CONTRACT.md).
"""
import json
import os

import numpy as np
from shapely.geometry import shape, mapping, LineString
from shapely.ops import unary_union

import in_situ_common as C

# Street boundary lines used by the extended-bays march (real coordinates,
# 2026-06-06, WGS84 -> EPSG:6494) — restated from scripts/design_extended_bays.py.
Y_LAKE, Y_MITCHELL, X_PETOSKEY = 750943.1, 750593.6, 19533270.8


def rounded(geom, nd=2):
    import shapely

    if geom.geom_type in ("Polygon", "MultiPolygon"):
        # snap to the output grid FIRST so coordinate rounding cannot
        # re-introduce self-intersections
        geom = shapely.set_precision(geom, 10 ** -nd, mode="valid_output")

    def rec(x):
        if isinstance(x, (list, tuple)):
            return [rec(v) for v in x]
        return round(x, nd)

    m = mapping(geom)
    return {"type": m["type"], "coordinates": rec(m["coordinates"])}


def front_edge(geom, ref_xy):
    """Front (stage-facing) edge of a tread band: the longest contiguous run
    of exterior-ring vertices nearer `ref_xy` than the ring median."""
    g = shape(geom)
    poly = g if g.geom_type == "Polygon" else max(g.geoms, key=lambda p: p.area)
    xy = np.array(poly.exterior.coords)[:-1]
    d = np.hypot(xy[:, 0] - ref_xy[0], xy[:, 1] - ref_xy[1])
    near = d <= np.median(d)
    # longest contiguous run on the closed ring
    n = len(xy)
    best, cur, best_start, cur_start = 0, 0, 0, 0
    for i in range(2 * n):
        if near[i % n]:
            if cur == 0:
                cur_start = i
            cur += 1
            if cur > best:
                best, best_start = cur, cur_start
            if cur >= n:
                break
        else:
            cur = 0
    idx = [(best_start + k) % n for k in range(min(best, n))]
    return xy[idx]


def _drop_slivers(geom, min_sf):
    """Drop disconnected polygon fragments below min_sf (schematic cleanup)."""
    if geom.geom_type == "Polygon":
        return geom
    keep = [g for g in geom.geoms if g.area >= min_sf]
    return unary_union(keep) if keep else geom


def _adopted_stage_components(roles):
    """Adopted P_opt stage geometry decomposed for zone emission, or None if the
    adoption artifact is absent. Returns a dict:
      core      P_opt-translated 70x34 performance core (OCCUPIED)
      apron     five-facet apron = deck - core (OCCUPIED, governing deck edge)
      deck      core ∪ apron (the occupied stage)
      shoulders list of (side, geom) translated lateral shoulders (NON-governing)
      full      deck ∪ shoulders (physical footprint)
    Source: analysis/in_situ_normalization/adopted_stage_footprint.geojson (emitted
    by stage_shape_study.py) + the inherited scenarioE stage_surface, translated by
    the recorded P_opt offset for the core/shoulder split. Construction is Method B
    (deck over compacted base) per STAGE_CONSTRUCTION_METHOD_DECISION.md. Concept-
    tier schematic: emitting these changes NO quantity (0 CY / 0 seats / 0 drainage)."""
    adf_path = os.path.join(C.REPO, "analysis", "in_situ_normalization",
                            "adopted_stage_footprint.geojson")
    if not os.path.exists(adf_path):
        return None
    from shapely.affinity import translate
    adf = json.load(open(adf_path))["features"][0]
    off = adf["properties"]["lateral_offset_from_inherited_ft"]
    deck = shape(adf["geometry"])
    inh = {f["properties"]["name"]: shape(f["geometry"]) for f in roles["stage_surface"]}
    core = translate(inh["stage"], xoff=off[0], yoff=off[1])
    apron = deck.difference(core).buffer(0)
    shoulders = [(side, translate(inh[f"stage_shoulder_{side}"], xoff=off[0], yoff=off[1]))
                 for side in ("left", "right") if f"stage_shoulder_{side}" in inh]
    full = unary_union([deck] + [g for _, g in shoulders])
    return dict(core=core, apron=apron, deck=deck, shoulders=shoulders, full=full)


def _adopted_stage_footprint(roles):
    """Adopted footprint (deck ∪ shoulders) or None. Thin wrapper over
    _adopted_stage_components for callers that only need the union."""
    c = _adopted_stage_components(roles)
    return c["full"] if c else None


def main():
    layers = C.verify_against_design()
    roles, comp = layers["roles"], layers["comp"]

    stage_polys = {f["properties"]["name"]: f for f in roles["stage_surface"]}
    stage_centroid = shape(stage_polys["stage"]["geometry"]).centroid
    ref = (stage_centroid.x, stage_centroid.y)

    # ── terrace treads: Scenario E bands + composition join + curvature ────
    treads, edges, tread_shapes = [], [], []
    for f in sorted(roles["formal_restored_tread"],
                    key=lambda f: (f["properties"]["section"], f["properties"]["row"])):
        p = f["properties"]
        row, sec = p["row"], p["section"]
        cm = comp[(row, sec)]
        elev = float(cm["elev"])
        props = {
            "row": row,
            "section": sec,
            "section_family": "southeast" if sec == "bend" else sec,
            "zone": cm["zone"],
            "role": "terrace_tread",
            "tread_elev_navd88": elev,
            "axis_radius_ft": float(cm["axis_radius_ft"]),
            "length_ft": float(cm["length_ft"]),
            "seats_kept": p["seats_kept"],
            "cross_angle_deg": float(cm["cross_angle_deg"]),
            "z_resid_ft": float(cm["z_resid_ft"]),
            "C_mm": float(cm["C_mm"]) if cm["C_mm"] else None,
            "sees_bay": cm["sees_bay"] == "True",
            "surface": "turf (Scenario D restored tread)",
            "geometry_source": "scenarioE formal_restored_tread (emitted + validated)",
            "datum": "NAVD88 Geoid12A intl ft",
        }
        props.update(C.curvature_metadata(f["geometry"]))
        treads.append(C.feat(props, f["geometry"]))
        tread_shapes.append(shape(f["geometry"]))

        # seat edge: front polyline + riser vs whatever sits in front
        if row == 1:
            base, base_src = None, "on grade (forecourt row 1)"
        elif row == 11:
            base, base_src = C.AISLE_ELEV, "cross-aisle 622.01"
        elif row == 6:
            base, base_src = float(comp[(C.PROMENADE_ROW, sec)]["elev"]), "row-5 promenade"
        else:
            base, base_src = float(comp[(row - 1, sec)]["elev"]), f"row {row - 1} tread"
        fe = front_edge(f["geometry"], ref)
        edges.append(C.feat(
            {
                "row": row,
                "section": sec,
                "name": f"terrace_edge_{sec}_row{row:02d}",
                "edge_type": "low_seat_edge",
                "riser_ft": round(elev - base, 2) if base is not None else 0.0,
                "riser_base": base_src,
                "top_elev_navd88": elev,
                "material": "timber-or-stone low seat edge (≤1.5 ft exposed)",
                "retaining_wall": False,
                "note": "front edge of tread; doubles as informal bench seating",
            },
            {"type": "LineString",
             "coordinates": [[round(x, 2), round(y, 2)] for x, y in fe]},
        ))
    C.dump(C.fc(treads), os.path.join(C.VEC_DIR, "terrace_treads.geojson"))
    C.dump(C.fc(edges), os.path.join(C.VEC_DIR, "terrace_edges.geojson"))

    # ── bowl zones ──────────────────────────────────────────────────────────
    zones = []

    def add_zone(zone_name, geom, **props):
        p = {"zone": zone_name, "name": zone_name}
        p.update(props)
        zones.append(C.feat(p, geom))

    open_stage_flags = dict(
        enclosure="none", upstage_shell=False, back_wall=False, fly_tower=False,
        open_to_bay_side=True, blocks_bay_view=False,
        rule9_status=C.STAGE_RULE9_STATUS,
    )
    # Phase-B stage-zone re-emission: emit the ADOPTED P_opt stage (70x34 core +
    # five-facet apron + non-governing lateral shoulders, construction Method B)
    # when the adoption artifact exists; otherwise fall back to the inherited
    # Rule-9-OPEN placeholder. Edge taxonomy is encoded per zone.
    adopted_stage = _adopted_stage_components(roles)
    if adopted_stage is not None:
        adopted_flags = dict(
            placement="P_opt (Rule 9 path-3 + path-4 wide-fan)",
            construction_method="Method B — deck over compacted base",
            rule9_note=("adopted P_opt stage: 70x34 core + five-facet apron at the "
                        "bay-preserving placement; construction Method B (deck over "
                        "compacted base). See STAGE_CONSTRUCTION_METHOD_DECISION.md."),
            **open_stage_flags)
        add_zone("stage_core", rounded(adopted_stage["core"]),
                 elev_navd88=C.FOCUS_ELEV,
                 surface="hardwood/composite deck over compacted base",
                 max_structure_height_ft=4.0, edge_class="performance_core",
                 occupied=True, governs_row1_pocket=False,
                 geometry_source="adopted_stage_footprint.geojson (P_opt 70x34 core)",
                 **adopted_flags)
        add_zone("stage_apron", rounded(adopted_stage["apron"]),
                 elev_navd88=C.FOCUS_ELEV,
                 surface="hardwood/composite deck over compacted base",
                 max_structure_height_ft=4.0, edge_class="occupied_deck_apron",
                 occupied=True, governs_row1_pocket=True,
                 geometry_source="adopted_stage_footprint.geojson (five_facet_apron)",
                 note="apron-inclusive deck front is the governed ≥12 ft row-1 "
                      "pocket edge (occupied deck)",
                 **adopted_flags)
        for side, g in adopted_stage["shoulders"]:
            add_zone(f"stage_shoulder_{side}", rounded(g),
                     elev_navd88=C.FOCUS_ELEV,
                     surface="flat landscape shoulder (not occupied deck)",
                     max_structure_height_ft=4.0, edge_class="lateral_nonoccupied",
                     occupied=False, governs_row1_pocket=False,
                     geometry_source="adopted_stage_footprint.geojson (translated shoulder)",
                     note="non-governing visual/landscape shoulder — not an enclosing "
                          "wall and not occupied deck unless explicitly adopted",
                     **adopted_flags)
    else:
        inherited_flags = dict(
            rule9_note=("inherited design_open_low stage reused by Scenario E; "
                        "axis refit OPEN per DESIGN_CANON Rule 9 — no fan is "
                        "declared by this package"),
            **open_stage_flags)
        add_zone("stage_core", stage_polys["stage"]["geometry"],
                 elev_navd88=C.FOCUS_ELEV, surface="hardscape deck",
                 max_structure_height_ft=4.0,
                 geometry_source="scenarioE stage_surface (inherited)",
                 **inherited_flags)
        for side in ("left", "right"):
            add_zone(f"stage_shoulder_{side}",
                     stage_polys[f"stage_shoulder_{side}"]["geometry"],
                     elev_navd88=C.FOCUS_ELEV, surface="hardscape deck",
                     max_structure_height_ft=4.0,
                     geometry_source="scenarioE stage_surface (inherited)",
                     note="lateral floor-level shoulder — not an enclosing wall",
                     **inherited_flags)

    # orchestra event floor — the flat floor between the stage and the row-1 bands.
    row1 = [s for f, s in zip(treads, tread_shapes) if f["properties"]["row"] == 1]
    all_treads = unary_union(tread_shapes)
    if adopted_stage is not None:
        # Adopted derivation: hull spanning the OCCUPIED deck to row 1, minus the
        # full adopted footprint (deck + shoulders) and the treads. The floor begins
        # at the adopted deck edge (overlap → 0) and reclaims the ground the inherited
        # stage vacated. Schematic / concept-tier → no quantity change.
        deck, full = adopted_stage["deck"], adopted_stage["full"]
        hull = unary_union([deck] + row1).convex_hull
        orchestra = _drop_slivers(hull.difference(full.buffer(0.1)).difference(
            all_treads.buffer(0.1)).simplify(0.25), 5.0)
        o_src = ("derived: hull(adopted P_opt deck, row-1 bands) minus adopted "
                 "footprint (deck + shoulders) + treads")
        o_extra = {"reemitted_against_adopted_deck": "adopted_stage_footprint.geojson (P_opt)"}
    else:
        stage_shape = unary_union([shape(f["geometry"]) for f in roles["stage_surface"]])
        hull = unary_union([stage_shape] + row1).convex_hull
        orchestra = hull.difference(stage_shape.buffer(0.1)).difference(
            all_treads.buffer(0.1)).simplify(0.25)
        o_src = "derived: convex_hull(inherited stage, row-1 bands) minus both"
        o_extra = {}
    add_zone("orchestra_event_floor", rounded(orchestra),
             grade_elev_navd88=C.FOCUS_ELEV,
             surface="stabilized turf / accessible event floor",
             schematic=True, cost_status="concept",
             geometry_source=o_src,
             note="floor between stage and the three row-1 bands; "
                  "floor-level accessible seating", **o_extra)

    # treatment cell — reused verbatim (stage4 lineage via design_open_low,
    # the same polygon Scenario E uses as its drainage target)
    stg0 = json.load(open(os.path.join(C.REPO, "design_open_low", "stage_floor.geojson")))
    cell = next(f for f in stg0["features"]
                if f["properties"].get("name") == "treatment_wet_cell")
    add_zone("treatment_cell_landscape", cell["geometry"],
             bottom_navd88=C.TREATMENT_BOTTOM,
             hydrology="dry_ephemeral_bioretention", permanent_water=False,
             planting="wet-tolerant meadow / bioretention mix",
             geometry_source="treatment_wet_cell reused verbatim "
                             "(stage4 → design_open_low → scenarioE drain target)",
             note="dry bioretention cell beyond the stage; ponds only shallowly "
                  "and transiently after large storms — never a standing pool")

    # cross-aisle + ADA + landings + swales + shoulders — Scenario E verbatim
    aisle = roles["cross_aisle"][0]
    add_zone("cross_aisle", aisle["geometry"], cost_status="geometry_backed",
             **{k: v for k, v in aisle["properties"].items() if k != "role"})
    # scenarioE ada_ramp/landing roles are NOT imported: that layer was
    # REJECTED 2026-06-12 (disconnected fragments; route A 63% inside the
    # treatment cell; route B crosses a swale and never reaches the
    # cross-aisle). The quarantined copies live in
    # vectors_geojson/legacy_ada_rejected.geojson; the rebuilt network is
    # emitted by scripts/rebuild_ada_routes.py into ada_nodes.geojson /
    # ada_route.geojson with analysis/ada_rebuild/ada_validation.json.
    for f in roles["drainage_swale"]:
        add_zone("drainage_swale", f["geometry"], cost_status="geometry_backed",
                 geometry_source="scenarioE drainage_swale (emitted + validated)",
                 **{k: v for k, v in f["properties"].items() if k != "role"})
    for i, f in enumerate(roles["row_end_shoulder"], 1):
        add_zone("row_end_shoulder", f["geometry"], name=f"row_end_shoulder_{i}",
                 cost_status="geometry_backed", surface="landscape (topsoil only)",
                 geometry_source="scenarioE row_end_shoulder",
                 note="clipped row tips returned to landscape",
                 **{k: v for k, v in f["properties"].items() if k != "role"})

    # promenade hinge band — row-5 bay centrelines buffered to a walk width
    prom_shapes = []
    for f in layers["promenade"]:
        sec = f["properties"]["section"]
        line = shape(f["geometry"])
        band = line.buffer(4.0, cap_style="flat")
        prom_shapes.append(band)
        add_zone("promenade_hinge", rounded(band), name=f"promenade_row5_{sec}",
                 section=sec, elev_navd88=float(comp[(C.PROMENADE_ROW, sec)]["elev"]),
                 cost_status="concept", seam_derived=False,
                 geometry_source="design_route_buffer (design_extended_bays "
                                 "row-5 promenade centreline, 8 ft walk)",
                 note="hinge promenade / accessible band absorbing the geometry "
                      "change between forecourt and civic families")

    # hinge rays — the declared section breakpoints (markers, not earthwork)
    for az, pair in zip(C.SECTION_BREAK_AZ, ("east|bend", "bend|south")):
        p0, p1 = C.polar(80.0, az), C.polar(210.0, az)
        add_zone("hinge_ray",
                 {"type": "LineString",
                  "coordinates": [[round(p0[0], 2), round(p0[1], 2)],
                                  [round(p1[0], 2), round(p1[1], 2)]]},
                 name=f"hinge_{pair}", az_deg=az, marker=True,
                 geometry_source="design_extended_bays section breakpoints "
                                 "(AZ_BEND_E=118, AZ_BEND_W=152)",
                 note=f"section transition {pair} (bend = southeast family)")

    env = roles["construction_envelope"][0]
    add_zone("construction_envelope", env["geometry"],
             cost_status="geometry_backed",
             geometry_source="scenarioE construction_envelope",
             gross_cy=env["properties"].get("gross_cy"),
             note="union grading footprint (priceable)")

    stage_fp = (adopted_stage["full"] if adopted_stage is not None
                else unary_union([shape(f["geometry"]) for f in roles["stage_surface"]]))
    footprints = unary_union(
        tread_shapes + prom_shapes
        + [shape(f["geometry"]) for f in
           roles["cross_aisle"] + roles["ada_ramp"] + roles["landing"]
           + roles["drainage_swale"]]
        + [stage_fp, shape(cell["geometry"]), orchestra])
    from shapely import make_valid
    from shapely.geometry import MultiPolygon

    envelope = footprints.buffer(40.0).simplify(0.5)
    untouched = make_valid(
        envelope.difference(footprints.buffer(0.1)).simplify(0.25))
    if untouched.geom_type == "GeometryCollection":
        untouched = MultiPolygon(
            [g for g in untouched.geoms if g.geom_type == "Polygon"])
    add_zone("untouched_slope", rounded(untouched),
             surface="existing slope vegetation", earthwork="none",
             note="existing grade preserved — no work; 40 ft study envelope "
                  "minus all footprints")
    C.dump(C.fc(zones), os.path.join(C.VEC_DIR, "bowl_zones.geojson"))

    # ── verbatim copy of the governing source at a predictable path ────────
    src = json.load(open(C.SRC_SCENARIOE))
    src["crs"] = C.CRS6494          # source file omits the header; coords are 6494
    src["governing_scheme"] = C.GOVERNING_SCHEME
    C.dump(src, os.path.join(C.VEC_DIR, "scenarioE_geometry.geojson"))

    # superseded copies from the old single-fan package must not linger.
    # NOTE: ada_route.geojson is deliberately NOT in this list. The REBUILT ADA
    # network (design_ada_routes.py, 2026-06-12) took that filename; it is a
    # REQUIRED current artifact (see audit_in_situ_package.py VECTORS /
    # SUPERSEDED_COPIES). Deleting it drops live Scenario E data and breaks
    # truth_package. Keep this tuple == audit_in_situ_package.SUPERSEDED_COPIES.
    STALE_SINGLEFAN = ("seating_rows.geojson", "stage_floor.geojson")
    REQUIRED_KEEP = ("ada_route.geojson", "ada_nodes.geojson",
                     "legacy_ada_rejected.geojson")
    for stale in STALE_SINGLEFAN:
        assert stale not in REQUIRED_KEEP, f"guard: refusing to delete required {stale}"
        p = os.path.join(C.VEC_DIR, stale)
        if os.path.exists(p):
            os.remove(p)
            print(f"  removed superseded vectors_geojson/{stale} (design_open_low)")


if __name__ == "__main__":
    main()
