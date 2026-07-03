#!/usr/bin/env python3
"""Site context + material zones for the three-section civic bowl package.

  vectors_geojson/site_context.geojson   street edges (real boundary lines),
      park paths, rim/arrival edge, tree masses, open lawn, service access,
      preserved areas, bay-view corridor
  vectors_geojson/material_zones.geojson turf terraces, low seat edges,
      hardscape/stage, accessible paths, bioretention planting, vegetated
      swales, existing vegetation

Provenance discipline: features carry `schematic` and `source`. Data-derived
features (rim edge from basin_footprint.geojson, street boundary lines from
the extended-bays march, bay-view corridor from the EPT viewshed) are
schematic=False; everything needing survey is schematic=True.

Requires build_in_situ_geometry.py to have run. EPSG:6494, NAVD88 intl ft.
"""
import json
import os
import sys

from shapely.geometry import shape, LineString, Point
from shapely.ops import unary_union

import in_situ_common as C
from build_in_situ_geometry import rounded, Y_LAKE, Y_MITCHELL, X_PETOSKEY

REPO = C.REPO


def load_vec(name):
    path = os.path.join(C.VEC_DIR, name)
    if not os.path.exists(path):
        sys.exit(f"ERROR: {os.path.relpath(path, REPO)} missing — "
                 "run scripts/build_in_situ_geometry.py first")
    with open(path) as fh:
        return json.load(fh)


def main():
    C.verify_against_design()
    treads = load_vec("terrace_treads.geojson")["features"]
    edges = load_vec("terrace_edges.geojson")["features"]
    zfeats = load_vec("bowl_zones.geojson")["features"]
    zones = {}
    for f in zfeats:
        zones.setdefault(f["properties"]["zone"], []).append(f)
    basin = json.load(open(os.path.join(REPO, "basin_footprint.geojson")))["features"][0]
    pour = json.load(open(os.path.join(REPO, "pour_point.geojson")))["features"][0]

    basin_poly = shape(basin["geometry"])
    rim_line = LineString(basin_poly.exterior.coords)
    pour_pt = shape(pour["geometry"])
    tread_union = unary_union([shape(f["geometry"]) for f in treads])
    stage_union = unary_union([shape(zones[z][0]["geometry"])
                               for z in ("stage_core", "stage_shoulder_left",
                                         "stage_shoulder_right")])
    stage_c = stage_union.centroid

    ctx = []

    def add(kind, geom, schematic, source, **props):
        ctx.append(C.feat(dict(kind=kind, schematic=schematic, source=source,
                               **props), geom))

    # rim / arrival edge — real: the basin spill contour
    add("rim_arrival_edge", rounded(rim_line), False, "basin_footprint.geojson",
        name="bowl rim / arrival edge",
        spill_elev_ft_navd88=basin["properties"]["spill_elev_ft_navd88"],
        note="closed-basin rim at spill elevation 618.04; principal arrival level")

    # street edges — real boundary lines from the extended-bays march
    x0, y0, x1, y1 = basin_poly.buffer(260).bounds
    for name, line in (
        ("E Lake Street (N boundary)", LineString([(x0, Y_LAKE), (x1, Y_LAKE)])),
        ("E Mitchell Street (S boundary)", LineString([(x0, Y_MITCHELL), (x1, Y_MITCHELL)])),
        ("Petoskey Street (E boundary)", LineString([(X_PETOSKEY, y0), (X_PETOSKEY, y1)])),
    ):
        add("street_edge", rounded(line), False,
            "design_extended_bays street boundaries (2026-06-06, WGS84→EPSG:6494)",
            name=name,
            note="boundary line used to clip the seating march; curb/ROW "
                 "geometry unsurveyed")

    # bay-view corridor — direction measured (EPT viewshed), extent schematic
    corridor_pts = (
        [[round(v, 2) for v in C.polar(10, C.BAY_VIEW_AZ - 12, stage_c.x, stage_c.y)]]
        + [[round(v, 2) for v in C.polar(660, az, stage_c.x, stage_c.y)]
           for az in (C.BAY_VIEW_AZ - 12, C.BAY_VIEW_AZ - 6, C.BAY_VIEW_AZ,
                      C.BAY_VIEW_AZ + 6, C.BAY_VIEW_AZ + 12)]
        + [[round(v, 2) for v in C.polar(10, C.BAY_VIEW_AZ + 12, stage_c.x, stage_c.y)]]
    )
    add("bay_view_corridor",
        {"type": "Polygon", "coordinates": [corridor_pts + [corridor_pts[0]]]},
        False, "EPT viewshed analysis (az 330 preferred; water plane 579.45)",
        name="bay-view corridor az 330",
        center_az_deg=C.BAY_VIEW_AZ, half_width_deg=12.0, length_ft=660.0,
        note="audience looks NNW over the low stage to Little Traverse Bay "
             "~200 m; corridor must stay free of view-blocking structures; "
             "seating sections face ~312 nominal — Rule 9 stage refit weighs "
             "this corridor against the audience centroid")

    # foreground tree masses — density measured az 315-320; boundary schematic
    band = [[round(v, 2) for v in C.polar(150, az, stage_c.x, stage_c.y)]
            for az in range(303, 328, 3)]
    band += [[round(v, 2) for v in C.polar(430, az, stage_c.x, stage_c.y)]
             for az in range(327, 302, -3)]
    add("tree_mass", {"type": "Polygon", "coordinates": [band + [band[0]]]},
        True, "EPT canopy screen finding (densest az 315-320); extent schematic",
        name="foreground tree screen (NNW band)",
        canopy_note="densest az 315-320; selective trimming equalizes 315 vs 330",
        note="existing trees between bowl and bay; boundary requires field survey")

    # preserved areas — untouched slope + row-end shoulders returned to landscape
    add("preserved_area", zones["untouched_slope"][0]["geometry"], False,
        "bowl_zones.geojson untouched_slope",
        name="untouched slope (no-work envelope)",
        note="existing grade and vegetation preserved")
    shoulders = unary_union([shape(f["geometry"])
                             for f in zones.get("row_end_shoulder", [])])
    add("preserved_area", rounded(shoulders), False,
        "scenarioE row_end_shoulder (topsoil-only landscape)",
        name="row-end shoulders returned to landscape",
        note="clipped row tips — landscape, not seats")

    # open lawn — pan between treatment cell and rim, NW of stage (schematic)
    cell_geom = shape(zones["treatment_cell_landscape"][0]["geometry"])
    lawn = (
        Point(C.polar(330, C.BAY_VIEW_AZ, stage_c.x, stage_c.y)).buffer(140)
        .intersection(basin_poly.buffer(120))
        .difference(cell_geom.buffer(10))
        .difference(stage_union.buffer(10))
    ).simplify(1.0)
    add("open_lawn", rounded(lawn), True, "schematic placement on the lower pan",
        name="open lawn / informal overflow",
        note="flexible lawn beyond the treatment cell")

    # park paths — rim promenade + spur from pour point toward bay (schematic)
    promenade = rim_line.parallel_offset(20.0, side="left").simplify(1.0)
    add("park_path", rounded(promenade), True, "schematic 20 ft offset of rim edge",
        name="rim promenade loop", surface="crushed aggregate",
        note="arrival walk around the bowl rim; alignment to be confirmed")
    spur = LineString([pour_pt.coords[0], C.polar(520, 30.0, pour_pt.x, pour_pt.y)])
    add("park_path", rounded(spur), True,
        "pour_point.geojson outflow bearing (NE); alignment schematic",
        name="bay connector spur", surface="crushed aggregate",
        note="connects rim toward existing bayfront path network")

    # service access — rim near pour point down to the event floor (schematic)
    svc = LineString([pour_pt.coords[0],
                      C.polar(C.F_T + 185, C.AX_AZ - C.SECTION_BREAK_AZ[0] + 100),
                      (stage_c.x, stage_c.y)])
    add("service_access", rounded(svc), True, "schematic routing via lowest rim head",
        name="service / emergency access route",
        note="drivable 12 ft route to stage + event floor; grades to be engineered")

    C.dump(C.fc(ctx), os.path.join(C.VEC_DIR, "site_context.geojson"))

    # ── material zones ──────────────────────────────────────────────────────
    mats = []

    def mat(name, geom, material, schematic=False, **props):
        mats.append(C.feat(dict(zone=name, name=name, material=material,
                                schematic=schematic, **props), geom))

    mat("turf_terraces", rounded(tread_union.simplify(0.1)),
        "mown turf on restored treads (Scenario D surface)",
        color_hint="#7fae6e",
        note="45 tread bands in three terrain-fitted sections (east/bend/south)")
    edge_band = unary_union([shape(f["geometry"]).buffer(0.75, cap_style="flat")
                             for f in edges]).simplify(0.1)
    mat("low_seat_edges", rounded(edge_band),
        "timber or split-stone low seat edge, ≤1.5 ft exposed face",
        retaining_wall=False, color_hint="#9c7b54",
        note="riser face at each tread front; informal bench seating")
    mat("hardscape_stage", rounded(stage_union),
        "low hardwood/composite deck over compacted base at event-floor grade",
        color_hint="#b9a48a", open_structure=True,
        rule9_status=C.STAGE_RULE9_STATUS,
        note="no enclosing shell — lateral shoulders only; refit OPEN (Rule 9)")
    # NOTE: the scenarioE ada_ramp/ada_landing zones were REMOVED from bowl_zones
    # by the 2026-06-12 ADA rebuild (build_in_situ_geometry.py no longer emits
    # them; see its "NOT imported" note). The live accessible-route surfaces now
    # come from the rebuilt Concept-C corridors (route_corridors_C.geojson) — this
    # script must run AFTER ADA stage 2. Sourcing the removed zones here was the
    # pre-existing KeyError (repro_tickets/build_site_context_stale_ada_zones.md).
    ada_corridors = load_vec("route_corridors_C.geojson")["features"]
    paths = unary_union(
        [shape(f["geometry"]) for f in
         zones["cross_aisle"] + zones["promenade_hinge"]]
        + [shape(f["geometry"]) for f in ada_corridors])
    mat("accessible_paths", rounded(paths.simplify(0.1)),
        "stabilized aggregate / boardwalk ramps, ≤8.33% running slope",
        color_hint="#d9cfa3",
        note="rebuilt Concept-C ADA corridors (route_corridors_C) + rows-9/10 "
             "cross-aisle + row-5 promenade hinge band")
    mat("event_floor", zones["orchestra_event_floor"][0]["geometry"],
        "stabilized turf (grass pavers at high-wear lines)",
        schematic=True, color_hint="#a4c08a",
        note="orchestra floor between stage and the three row-1 bands")
    mat("bioretention_planting", zones["treatment_cell_landscape"][0]["geometry"],
        "wet-tolerant meadow & bioretention mix (dry cell — no permanent water)",
        permanent_water=False, color_hint="#6f9b8f",
        note="ephemeral ponding only, after large storms")
    swales = unary_union([shape(f["geometry"])
                          for f in zones.get("drainage_swale", [])])
    mat("vegetated_swales", rounded(swales),
        "grassed interception swales falling to the NE pour point",
        color_hint="#5e8a7a", note="east + south flank swales (Scenario E)")
    tree_feat = next(f for f in ctx if f["properties"]["kind"] == "tree_mass")
    mat("existing_vegetation", tree_feat["geometry"],
        "existing canopy + understory, selectively trimmed in view corridor",
        schematic=True, color_hint="#4e7a4e",
        note="boundary schematic — field survey required")
    mat("existing_slope_grass", zones["untouched_slope"][0]["geometry"],
        "existing slope grasses, unmown except blanket maintenance",
        color_hint="#8da06b", note="no-work envelope")

    C.dump(C.fc(mats), os.path.join(C.VEC_DIR, "material_zones.geojson"))


if __name__ == "__main__":
    main()
