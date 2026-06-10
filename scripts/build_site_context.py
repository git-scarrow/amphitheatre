#!/usr/bin/env python3
"""Site context + material zones for the in-situ package.

  vectors_geojson/site_context.geojson   street edges, park paths, rim/arrival
                                         edge, tree masses, open lawn, service
                                         access, preserved areas, bay-view corridor
  vectors_geojson/material_zones.geojson turf terraces, low seat edges,
                                         hardscape/stage, accessible paths,
                                         bioretention planting, existing vegetation

Provenance discipline: features carry `schematic` (boolean) and `source`.
Data-derived features (rim edge from basin_footprint.geojson, bay-view
corridor from the EPT viewshed analysis) are schematic=False; everything a
surveyor or parks plan must still confirm (streets, paths, lawns, tree-mass
boundaries, service access) is schematic=True. Nothing here changes the
governing geometry.

Requires build_in_situ_geometry.py to have run. EPSG:6494, NAVD88 intl ft.
"""
import json
import os
import sys

from shapely.geometry import shape, LineString, Point
from shapely.ops import unary_union

import in_situ_common as C
from build_in_situ_geometry import rounded

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
    zones = {f["properties"]["zone"]: f for f in load_vec("bowl_zones.geojson")["features"]
             if f["properties"]["zone"] not in ("ada_route",)}
    ada_corridors = [f for f in load_vec("bowl_zones.geojson")["features"]
                     if f["properties"]["zone"] == "ada_route"]
    basin = json.load(open(os.path.join(REPO, "basin_footprint.geojson")))["features"][0]
    pour = json.load(open(os.path.join(REPO, "pour_point.geojson")))["features"][0]

    basin_poly = shape(basin["geometry"])
    rim_line = LineString(basin_poly.exterior.coords)
    pour_pt = shape(pour["geometry"])
    tread_union = unary_union([shape(f["geometry"]) for f in treads])
    stage_union = unary_union([shape(zones[z]["geometry"])
                               for z in ("stage_core", "stage_shoulder_left",
                                         "stage_shoulder_right")])

    ctx = []

    def add(kind, geom, schematic, source, **props):
        ctx.append(C.feat(dict(kind=kind, schematic=schematic, source=source, **props), geom))

    # rim / arrival edge — real: the basin spill contour
    add("rim_arrival_edge", rounded(rim_line), False, "basin_footprint.geojson",
        name="bowl rim / arrival edge",
        spill_elev_ft_navd88=basin["properties"]["spill_elev_ft_navd88"],
        note="closed-basin rim at spill elevation 618.04; principal arrival level")

    # bay-view corridor — direction measured (EPT viewshed), extent schematic
    corridor_pts = (
        [[round(v, 2) for v in C.polar(10, C.FACE_AZ - 12, C.SFX, C.SFY)]]
        + [[round(v, 2) for v in C.polar(660, az, C.SFX, C.SFY)]
           for az in (C.FACE_AZ - 12, C.FACE_AZ - 6, C.FACE_AZ, C.FACE_AZ + 6, C.FACE_AZ + 12)]
        + [[round(v, 2) for v in C.polar(10, C.FACE_AZ + 12, C.SFX, C.SFY)]]
    )
    add("bay_view_corridor",
        {"type": "Polygon", "coordinates": [corridor_pts + [corridor_pts[0]]]},
        False, "EPT viewshed analysis (az 330 preferred; water plane 579.45)",
        name="bay-view corridor az 330",
        center_az_deg=C.FACE_AZ, half_width_deg=12.0, length_ft=660.0,
        note="audience looks NNW over the low stage to Little Traverse Bay ~200 m; "
             "corridor must stay free of view-blocking structures")

    # foreground tree masses — density measured az 315-320; boundary schematic
    band = [[round(v, 2) for v in C.polar(r, az, C.SFX, C.SFY)]
            for az in range(303, 328, 3) for r in (150,)]
    band += [[round(v, 2) for v in C.polar(r, az, C.SFX, C.SFY)]
             for az in range(327, 302, -3) for r in (430,)]
    add("tree_mass", {"type": "Polygon", "coordinates": [band + [band[0]]]},
        True, "EPT canopy screen finding (densest az 315-320); extent schematic",
        name="foreground tree screen (NNW band)",
        canopy_note="densest az 315-320; selective trimming equalizes 315 vs 330 views",
        note="existing trees between bowl and bay; boundary requires field survey")

    # preserved areas — the untouched slope plus the tree band
    add("preserved_area", zones["untouched_slope"]["geometry"], False,
        "bowl_zones.geojson untouched_slope",
        name="untouched slope (no-work envelope)",
        note="existing grade and vegetation preserved")

    # open lawn — pan between treatment cell and rim, NW of stage (schematic)
    lawn = (
        Point(C.polar(330, C.FACE_AZ, C.SFX, C.SFY)).buffer(140)
        .intersection(basin_poly.buffer(120))
        .difference(shape(zones["treatment_cell_landscape"]["geometry"]).buffer(10))
        .difference(stage_union.buffer(10))
    ).simplify(1.0)
    add("open_lawn", rounded(lawn), True, "schematic placement on the lower pan",
        name="open lawn / informal overflow", note="flexible lawn beyond the treatment cell")

    # park paths — rim promenade + spur from pour point toward bay (schematic)
    promenade = rim_line.parallel_offset(20.0, side="left").simplify(1.0)
    add("park_path", rounded(promenade), True, "schematic 20 ft offset of rim edge",
        name="rim promenade loop", surface="crushed aggregate",
        note="arrival walk around the bowl rim; alignment to be confirmed")
    spur = LineString([pour_pt.coords[0],
                       C.polar(520, 30.0, pour_pt.x, pour_pt.y)])
    add("park_path", rounded(spur), True,
        "pour_point.geojson outflow bearing (NE); alignment schematic",
        name="bay connector spur", surface="crushed aggregate",
        note="connects rim toward existing bayfront path network")

    # street edge — schematic offset south/east of the rim; names need survey
    bbox = LineString(basin_poly.buffer(150).envelope.exterior.coords)
    add("street_edge", rounded(bbox), True,
        "schematic 150 ft envelope of basin; verify against parcel/ROW data",
        name="surrounding street / ROW edge (UNVERIFIED)",
        note="placeholder — replace with surveyed back-of-curb / ROW lines")

    # service access — rim near pour point down to the event floor (schematic)
    svc = LineString([pour_pt.coords[0],
                      C.polar(C.R_OUTER + 40, C.AX_AZ - C.FAN_HALF - 20),
                      (C.SFX, C.SFY)])
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
        "mown turf on regraded tread (≤0.2 ft fill, front rows only)",
        color_hint="#7fae6e", note="16 terraced rows on the natural rake")
    edge_band = unary_union([shape(f["geometry"]).buffer(0.75, cap_style="flat")
                             for f in edges]).simplify(0.1)
    mat("low_seat_edges", rounded(edge_band),
        "timber or split-stone low seat edge, ≤1.5 ft exposed face",
        retaining_wall=False, color_hint="#9c7b54",
        note="riser face at each tread front; informal bench seating")
    mat("hardscape_stage", rounded(stage_union),
        "low hardwood/composite deck over compacted base at event-floor grade",
        color_hint="#b9a48a", open_structure=True,
        note="no enclosing shell — lateral shoulders only")
    paths = unary_union([shape(f["geometry"]) for f in ada_corridors]
                        + [shape(zones["cross_aisle"]["geometry"])])
    mat("accessible_paths", rounded(paths.simplify(0.1)),
        "stabilized aggregate / boardwalk ramps, ≤8.33% running slope",
        color_hint="#d9cfa3", note="ADA routes A and B + level mid cross-aisle")
    mat("event_floor", zones["event_floor_forecourt"]["geometry"],
        "stabilized turf (grass pavers at high-wear lines)",
        color_hint="#a4c08a", note="forecourt / accessible floor seating")
    mat("bioretention_planting", zones["treatment_cell_landscape"]["geometry"],
        "wet-tolerant meadow & bioretention mix (dry cell — no permanent water)",
        permanent_water=False, color_hint="#6f9b8f",
        note="ephemeral ponding only, after large storms")
    tree_feat = next(f for f in ctx if f["properties"]["kind"] == "tree_mass")
    mat("existing_vegetation", tree_feat["geometry"],
        "existing canopy + understory, selectively trimmed in view corridor",
        schematic=True, color_hint="#4e7a4e",
        note="boundary schematic — field survey required")
    mat("existing_slope_grass", zones["untouched_slope"]["geometry"],
        "existing slope grasses, unmown except blanket maintenance",
        color_hint="#8da06b", note="no-work envelope")

    C.dump(C.fc(mats), os.path.join(C.VEC_DIR, "material_zones.geojson"))


if __name__ == "__main__":
    main()
