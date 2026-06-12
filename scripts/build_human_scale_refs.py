#!/usr/bin/env python3
"""Generate the human-scale reference layer (calibrated schematic scale).

Emits vectors_geojson/human_scale_refs.geojson: to-scale human reference
points + dimension lines, every one ANCHORED to the governing geometry
(Scenario E three-section civic bowl) — never free-hand:

  · standing refs 5.00 / 5.75 / 6.25 ft (documented stature percentiles)
  · seated refs with the repo's documented seated eye height (3.94 ft —
    the same constant every C-value uses)
  · wheelchair refs at the ADA-critical locations (cross-aisle band,
    route-B landing)
  · dimension refs measured off the geometry: stage-front→row-1 gap,
    east/south row-1 pocket pinches, a 50-ft scale bar

Ground elevations come from the design layers (declared tread/zone
elevations, which match the emitted proposed-grade raster) or are sampled
from dem/proposed_grade_1ft.tif; the source is recorded per ref so the
audit gate can re-derive every number. Stage refs stand on the PROVISIONAL
612.5 deck (DESIGN_CANON Rule 9 OPEN — surfaced in their properties).

Canon preserved: open-air landscape venue; refs never block the bay view
(audited against the mid-row sightline); no walls/shell implied.

Deterministic. EPSG:6494 intl ft, NAVD88 (Geoid12A) intl ft.
"""
import json
import math
import os

from shapely.geometry import Point, Polygon, shape
from shapely.ops import nearest_points, unary_union

import in_situ_common as C
import human_scale_common as H

REPO = C.REPO
OUT = os.path.join(REPO, H.REFS_PATH)

SRC_TREADS = "vectors_geojson/terrace_treads.geojson"
SRC_ZONES = "vectors_geojson/bowl_zones.geojson"
SRC_CTX = "vectors_geojson/site_context.geojson"
SRC_STAGE_LINEAGE = "design_open_low/stage_floor.geojson"
SRC_TYPOLOGY = "analysis/in_situ_normalization/stage_typology_scores.json"
SRC_AMBITIOUS = "analysis/tier_emission/ambitious_shaped_bowl_seating/geometry.geojson"
SRC_RASTER = "dem/proposed_grade_1ft.tif"


def jload(rel):
    with open(os.path.join(REPO, rel)) as fh:
        return json.load(fh)


def raster_sampler():
    path = os.path.join(REPO, SRC_RASTER)
    if not os.path.exists(path):
        return None
    import rasterio

    ds = rasterio.open(path)

    def z(x, y):
        v = float(next(ds.sample([(x, y)]))[0])
        return None if v == ds.nodata else round(v, 2)

    return z


def rep_pt(geom):
    g = shape(geom)
    if g.geom_type == "MultiPolygon":
        g = max(g.geoms, key=lambda p: p.area)
    p = g.representative_point()
    return round(p.x, 2), round(p.y, 2)


def main():
    treads = jload(SRC_TREADS)["features"]
    zones = jload(SRC_ZONES)["features"]
    ctx = jload(SRC_CTX)["features"]
    sample = raster_sampler()

    zmap = {}
    for f in zones:
        zmap.setdefault(f["properties"]["zone"], []).append(f)
    tread = {(f["properties"]["section"], f["properties"]["row"]): f
             for f in treads}

    # stage anchors: inherited focal point (viewer) + P_opt deck (study)
    focal = next(f for f in jload(SRC_STAGE_LINEAGE)["features"]
                 if f["properties"].get("name") == "focal_point_stage_front")
    fx, fy = focal["geometry"]["coordinates"]
    deck_elev = zmap["stage_core"][0]["properties"]["elev_navd88"]

    st = jload(SRC_TYPOLOGY)
    sel = st["selected_placement"]
    P, az = sel["front_centre"], sel["axis_az"]
    ux, uy = C.U(az)
    wx, wy = C.U(az + 90.0)
    deck = Polygon([(P[0] + ux * a + wx * b, P[1] + uy * a + wy * b)
                    for a, b in ((0, -35), (0, 35), (-34, 35), (-34, -35))])

    feats = []

    def declared(layer, field, value):
        return value, f"declared:{layer}:{field}"

    def human(ref_id, xy, posture, height_ft, role, ground, ground_src,
              anchor, anchor_src, view_context, scope="baseline",
              eye_ft=None, label=None, note=None):
        props = {
            "ref_id": ref_id, "type": "human", "posture": posture,
            "role": role, "height_ft": height_ft,
            "ground_elev_navd88": round(ground, 2),
            "ground_elev_source": ground_src,
            "anchor": anchor, "geometry_anchor_source": anchor_src,
            "height_source": H.HEIGHT_SOURCE[posture],
            "view_context": view_context, "scope": scope,
            "blocks_bay_view": False,
            "schematic_figure": True,
        }
        if eye_ft is not None:
            props["eye_height_ft"] = eye_ft
        if label:
            props["label"] = label
        if note:
            props["note"] = note
        feats.append(C.feat(props, {"type": "Point",
                                    "coordinates": [round(xy[0], 2),
                                                    round(xy[1], 2)]}))

    def dimension(ref_id, p0, p1, label, anchor_src, ground, note=None,
                  scope="baseline"):
        length = round(math.hypot(p1[0] - p0[0], p1[1] - p0[1]), 2)
        props = {
            "ref_id": ref_id, "type": "dimension", "length_ft": length,
            "label": label.format(L=length),
            "ground_elev_navd88": round(ground, 2),
            "geometry_anchor_source": anchor_src, "scope": scope,
            "blocks_bay_view": False,
        }
        if note:
            props["note"] = note
        feats.append(C.feat(props, {
            "type": "LineString",
            "coordinates": [[round(p0[0], 2), round(p0[1], 2)],
                            [round(p1[0], 2), round(p1[1], 2)]]}))
        return length

    rule9 = ("stage deck PROVISIONAL — DESIGN_CANON Rule 9 OPEN; ref stands "
             "on the 612.5 deck for scale only, adopts no stage geometry")

    # ── stage ────────────────────────────────────────────────────────────
    g_dk, _ = declared(SRC_ZONES, "stage_core.elev_navd88", deck_elev)
    human("stage_front_performer", (fx, fy), "standing", 6.25, "performer",
          g_dk, f"declared:{SRC_ZONES}:stage_core.elev_navd88(structure_deck)",
          "stage-front focal point (inherited stage lineage)",
          f"{SRC_STAGE_LINEAGE}:focal_point_stage_front",
          ["viewer", "board02_section", "board05_section", "board06"],
          label="{h} ft person".format(h=6.25), note=rule9)
    sc = rep_pt(zmap["stage_core"][0]["geometry"])
    human("center_stage", sc, "standing", 5.75, "performer",
          g_dk, f"declared:{SRC_ZONES}:stage_core.elev_navd88(structure_deck)",
          "stage_core representative point",
          f"{SRC_ZONES}:stage_core", ["viewer", "board06"], note=rule9)

    # ── row 1 centre (bend family) ───────────────────────────────────────
    b1 = tread[("bend", 1)]
    e1, s1 = declared(SRC_TREADS, "tread_elev_navd88",
                      b1["properties"]["tread_elev_navd88"])
    c1 = rep_pt(b1["geometry"])
    human("row1_center_seated", c1, "seated", H.SEATED_HEIGHT_FT, "audience",
          e1, s1, "bend row-1 tread representative point",
          f"{SRC_TREADS}:bend r1",
          ["viewer", "board02_section", "board05_section", "board06"],
          eye_ft=H.SEATED_EYE_FT,
          label=f"seated eye {H.SEATED_EYE_FT} ft")
    human("row1_center_standing", (c1[0] + 4.0, c1[1] - 2.5), "standing",
          5.75, "audience", e1, s1,
          "bend row-1 tread, 4.7 ft along-row from the seated ref",
          f"{SRC_TREADS}:bend r1", ["viewer", "board06"])

    # ── row-1 pocket pinch points (P_opt deck vs east / south row 1) ────
    for sec, rid in (("east", "row1_east_pocket"), ("south", "row1_south_pocket")):
        tf = tread[(sec, 1)]
        a, b = nearest_points(deck, shape(tf["geometry"]))
        ev, sv = declared(SRC_TREADS, "tread_elev_navd88",
                          tf["properties"]["tread_elev_navd88"])
        human(rid, (b.x, b.y), "standing", 5.0, "audience",
              ev, sv,
              f"{sec} row-1 edge at the pinch vs the P_opt provisional deck",
              f"nearest_points({SRC_TYPOLOGY}:P_opt deck, {SRC_TREADS}:{sec} r1)",
              ["viewer", "board06"], note=rule9)
        dimension(f"dim_pocket_{sec}", (a.x, a.y), (b.x, b.y),
                  "{L:.0f} ft pocket",
                  f"nearest_points({SRC_TYPOLOGY}:P_opt deck, "
                  f"{SRC_TREADS}:{sec} r1)", ev,
                  note="row-1 pocket pinch — P_opt placement keeps every "
                       "family ≥12 ft (stage provisional, Rule 9 OPEN)")

    # ── stage front → row 1 relation ─────────────────────────────────────
    a, b = nearest_points(deck, shape(b1["geometry"]))
    dimension("dim_stage_front_to_row1", (a.x, a.y), (b.x, b.y),
              "{L:.0f} ft stage→row 1",
              f"nearest_points({SRC_TYPOLOGY}:P_opt deck, {SRC_TREADS}:bend r1)",
              e1,
              note="bend-family orchestra gap; canon baseline quotes stage "
                   "front ≈35 ft from row 1 (performer→row-1 39.6 ft per "
                   "stage_typology_scores.json)")

    # ── 50 ft scale bar on the event floor (exact by construction) ──────
    bar0 = (fx - 25.0 * wx, fy - 25.0 * wy)   # centred on focal, along-stage
    bar1 = (fx + 25.0 * wx, fy + 25.0 * wy)
    dimension("dim_scale_50ft", bar0, bar1, "{L:.0f} ft scale",
              f"constructed: 50 ft along the stage-front axis about "
              f"{SRC_STAGE_LINEAGE}:focal_point_stage_front", deck_elev)

    # ── row 5 promenade hinge ────────────────────────────────────────────
    pm = next(f for f in zmap["promenade_hinge"]
              if f["properties"]["name"] == "promenade_row5_bend")
    ep, sp = declared(SRC_ZONES, "promenade_row5_bend.elev_navd88",
                      pm["properties"]["elev_navd88"])
    human("row5_promenade", rep_pt(pm["geometry"]), "standing", 5.75,
          "promenade walker", ep, sp, "row-5 promenade hinge band (bend)",
          f"{SRC_ZONES}:promenade_row5_bend", ["viewer", "board06"])

    # ── cross-aisle (rows 9/10 reclassified) — ADA band ─────────────────
    ca = zmap["cross_aisle"][0]
    eca, sca = declared(SRC_ZONES, "cross_aisle.elev_navd88",
                        ca["properties"]["elev_navd88"])
    cca = rep_pt(ca["geometry"])
    human("cross_aisle_wheelchair", cca, "wheelchair", H.WHEELCHAIR_HEIGHT_FT,
          "wheelchair user", eca, sca,
          "accessible cross-aisle band (rows 9/10 reclassification)",
          f"{SRC_ZONES}:cross_aisle",
          ["viewer", "board02_section", "board05_section", "board06"],
          eye_ft=H.WHEELCHAIR_EYE_FT, label="wheelchair ref")
    human("cross_aisle_companion", (cca[0] + 4.5, cca[1] + 1.5), "standing",
          5.75, "companion", eca, sca,
          "accessible cross-aisle band, 4.7 ft from the wheelchair ref",
          f"{SRC_ZONES}:cross_aisle", ["viewer", "board06"])

    # ── upper formal row 18 ──────────────────────────────────────────────
    b18 = tread[("bend", 18)]
    e18, s18 = declared(SRC_TREADS, "tread_elev_navd88",
                        b18["properties"]["tread_elev_navd88"])
    c18 = rep_pt(b18["geometry"])
    human("row18_upper_seated", c18, "seated", H.SEATED_HEIGHT_FT, "audience",
          e18, s18, "bend row-18 tread (top formal row)",
          f"{SRC_TREADS}:bend r18",
          ["viewer", "board02_section", "board06"], eye_ft=H.SEATED_EYE_FT)
    human("row18_upper_standing", (c18[0] + 4.0, c18[1] - 2.5), "standing",
          6.25, "audience", e18, s18, "bend row-18 tread (top formal row)",
          f"{SRC_TREADS}:bend r18", ["viewer", "board06"],
          label="6.25 ft person")

    # ── ADA ramp landings ────────────────────────────────────────────────
    landings = {f["properties"]["name"]: f for f in zmap["ada_landing"]}
    l5 = landings["ada_landing_5"]          # route B arrival at cross-aisle
    p5 = rep_pt(l5["geometry"])
    g5 = sample(*p5) if sample else eca
    human("ada_landing_routeB_wheelchair", p5, "wheelchair",
          H.WHEELCHAIR_HEIGHT_FT, "wheelchair user", g5,
          f"raster:{SRC_RASTER}" if sample
          else f"fallback_declared:{SRC_ZONES}:cross_aisle.elev_navd88",
          "route-B switchback landing 5 (arrival at the cross-aisle)",
          f"{SRC_ZONES}:ada_landing_5", ["viewer", "board06"],
          eye_ft=H.WHEELCHAIR_EYE_FT)
    l2 = landings["ada_landing_2"]          # route A, near the event floor
    p2 = rep_pt(l2["geometry"])
    g2 = sample(*p2) if sample else 610.0
    human("ada_landing_routeA_standing", p2, "standing", 5.0, "walker",
          g2, f"raster:{SRC_RASTER}" if sample else "fallback_declared:610.0",
          "route-A switchback landing 2 (floor approach)",
          f"{SRC_ZONES}:ada_landing_2", ["viewer", "board06"])

    # ── treatment-cell foreground edge (visible beyond the stage) ───────
    cell = shape(zmap["treatment_cell_landscape"][0]["geometry"])
    bx, by = C.U(C.BAY_VIEW_AZ)
    from shapely.geometry import LineString

    ray = LineString([(fx, fy), (fx + bx * 400, fy + by * 400)])
    hit = ray.intersection(cell.exterior)
    if hit.is_empty:
        hp = nearest_points(cell.exterior, Point(fx, fy))[0]
    else:
        hp = min((hit.geoms if hasattr(hit, "geoms") else [hit]),
                 key=lambda p: Point(fx, fy).distance(p))
    gce = sample(hp.x, hp.y) if sample else \
        zmap["treatment_cell_landscape"][0]["properties"]["bottom_navd88"]
    human("treatment_cell_edge", (hp.x, hp.y), "standing", 5.75,
          "maintenance / passer-by", gce,
          f"raster:{SRC_RASTER}" if sample
          else f"fallback_declared:{SRC_ZONES}:treatment_cell_landscape.bottom_navd88",
          "treatment-cell foreground edge on the bay-view azimuth from the "
          "stage front (dry/ephemeral cell — landscape, not water)",
          f"intersection(az-{C.BAY_VIEW_AZ:.0f} ray from focal, "
          f"{SRC_ZONES}:treatment_cell_landscape exterior)",
          ["viewer", "board06"])

    # ── lawn / overflow edge ─────────────────────────────────────────────
    lawn = next(f for f in ctx if f["properties"]["kind"] == "open_lawn")
    lp = nearest_points(shape(lawn["geometry"]).exterior, cell)[0]
    gl = sample(lp.x, lp.y) if sample else None
    if gl is None:
        import rasterio

        cpath = os.path.join(REPO, "dem", "dem_context_2p5ft.tif")
        if os.path.exists(cpath):
            ds = rasterio.open(cpath)
            v = float(next(ds.sample([(lp.x, lp.y)]))[0])
            gl, gsrc = round(v, 2), "raster:dem/dem_context_2p5ft.tif"
        else:
            gl, gsrc = 619.5, "fallback_declared:619.5(schematic lawn)"
    else:
        gsrc = f"raster:{SRC_RASTER}"
    human("lawn_overflow_edge", (lp.x, lp.y), "standing", 5.0,
          "overflow / informal audience", gl, gsrc,
          "open-lawn informal overflow edge nearest the treatment cell "
          "(schematic lawn placement)",
          f"{SRC_CTX}:open_lawn exterior nearest "
          f"{SRC_ZONES}:treatment_cell_landscape", ["viewer", "board06"])

    # ── ambitious option: promoted row 20 (board 05 only) ────────────────
    amb_path = os.path.join(REPO, SRC_AMBITIOUS)
    if os.path.exists(amb_path):
        r20 = next(f for f in jload(SRC_AMBITIOUS)["features"]
                   if f["properties"].get("role") == "tier_promoted_tread"
                   and f["properties"]["section"] == "bend"
                   and f["properties"]["row"] == 20)
        human("ambitious_row20_seated", rep_pt(r20["geometry"]), "seated",
              H.SEATED_HEIGHT_FT, "audience",
              *declared(SRC_AMBITIOUS, "design_elev",
                        r20["properties"]["design_elev"]),
              "bend row-20 promoted tread — AMBITIOUS seating option only "
              "(Decision 1 pending; not in the baseline package)",
              f"{SRC_AMBITIOUS}:bend r20", ["board05_section"],
              scope="ambitious_option", eye_ft=H.SEATED_EYE_FT)

    out = C.fc(feats, extra={
        "generator": "scripts/build_human_scale_refs.py",
        "purpose": "calibrated schematic human scale — heights exact in data "
                   "units, figure shapes schematic; never decorative",
        "stage_rule9_status": C.STAGE_RULE9_STATUS,
        "governing_scheme": C.GOVERNING_SCHEME,
    })
    C.dump(out, OUT)
    nh = sum(1 for f in feats if f["properties"]["type"] == "human")
    nd = sum(1 for f in feats if f["properties"]["type"] == "dimension")
    print(f"  {nh} human refs ({sum(1 for f in feats if f['properties'].get('posture') == 'wheelchair')} wheelchair) "
          f"+ {nd} dimension refs")
    missing = [r for r in H.REQUIRED_PLACEMENTS
               if not any(f["properties"]["ref_id"] == r for f in feats)]
    if missing:
        raise SystemExit(f"required placements not emitted: {missing}")


if __name__ == "__main__":
    main()
