#!/usr/bin/env python3
"""Stage-shape study: utilitarian typologies under the visual-envelope rule.

RULE (replaces "low stage only"): a stage candidate is acceptable if its
roof, canopy, rigging, masts, storage, side walls or back-of-house mass
stays within the ALREADY-OBSTRUCTED sightline envelope (the NW rim/terrain
silhouette traced by scripts/obstruction_envelope.py), or if any NEW
obstruction is quantified and judged minor. Height is never a rejection
reason by itself.

Inputs
  analysis/in_situ_normalization/section_balance.json   audience frame
  analysis/stage_seating_decoupling/pareto_summary.json independent zone band
  scripts/obstruction_envelope.Envelope                 DEM ray tracer

Placements (all inside the independently-derived southern pan-toe band):
  P_inherited  the as-built front centre, axis 150 (tested, not assumed)
  P_lat        axis 150 kept (preserves the az-330 bay axis), front centre
               shifted laterally onto the audience-frame axis (~the
               stage-refit sweep's best feasible az150_lat-20)
  P_frame      axis turned to the audience-centroid bearing (audience-axis
               path; bay-axis deviation reported)

Typologies (each scored at P_lat; deck-only also at the other placements):
  T1 deck_only · T2 covered_civic (thin roof) · T3 acoustic_canopy (no back
  wall) · T4 asymmetric_utility (BOH tucked into the most-hidden upstage
  corner) · T5 movie_capable (removable masts; screen is night-only)
  T6 side_framed_acoustic (open upstage slot) · T7 hybrid (core + faceted
  apron + service canopy + corner BOH)

Per candidate: incremental obstruction by family (bay / treatment-cell
foreground / sky separately), frame fit, per-section stage-front→row-1,
cell clearance, pad volumes, operational scoring, constructability.

Outputs -> analysis/in_situ_normalization/stage_typology_scores.json,
STAGE_SHAPE_STUDY.md. EPSG:6494 · NAVD88 intl ft · planning-grade.
"""
import json
import math
import os

import numpy as np
from shapely.geometry import shape, Polygon, Point, LineString
from shapely.ops import unary_union
from shapely import affinity

import in_situ_common as C
from obstruction_envelope import Envelope

OUT = os.path.join(C.REPO, "analysis", "in_situ_normalization")
DECK_Z = (C.FOCUS_ELEV, C.FOCUS_ELEV + 1.0)
MINOR_BAY_PCT = 10.0      # new bay blockage above this (any family) = flagged
NO_MEANINGFUL_PCT = 2.0


def U(az):
    return C.U(az)


def rect(P, axis_az, w_half, u_from, u_to):
    """Rectangle in stage frame: u toward audience along axis_az, w lateral.
    u_from/u_to measured from the front centre P (positive toward audience)."""
    ux, uy = U(axis_az)
    wx, wy = U(axis_az + 90.0)
    c = []
    for uu, ww in ((u_from, -w_half), (u_from, w_half),
                   (u_to, w_half), (u_to, -w_half)):
        c.append((P[0] + ux * uu + wx * ww, P[1] + uy * uu + wy * ww))
    return Polygon(c)


def apron_front_candidates(P, az, fam_dirs):
    """Stage-front geometry candidates: the downstage edge as a VARIABLE.

    Local frame: u toward the audience along `az`, w lateral (+w to the
    right facing the audience → the south family; −w → east). Each candidate
    returns (front_pts_local [(w,u)…], note, complexity). The 70x34
    rectangular core is untouched — the apron is additive downstage."""

    def arc(bow, corner, n=29):
        ws = np.linspace(-35.0, 35.0, n)
        return [(float(w), float(corner + (bow - corner) * (1 - (w / 35.0) ** 2)))
                for w in ws]

    def facets(breaks, aims, max_proj):
        """Polyline whose facet normals aim at the given family directions
        (unit vectors in the LOCAL frame, +u = toward audience)."""
        pts = [(breaks[0], 0.0)]
        for i in range(len(breaks) - 1):
            nw, nu = aims[i]
            nu = max(nu, 0.30)               # stay front-facing
            slope = -nw / nu                  # du/dw along the facet edge
            w0, w1 = breaks[i], breaks[i + 1]
            u0 = pts[-1][1]
            pts.append((w1, u0 + slope * (w1 - w0)))
        us = np.array([u for _, u in pts])
        us -= us.min()
        if us.max() > max_proj:
            us *= max_proj / us.max()
        if us.max() < 4.0 and us.max() > 0:
            us *= 4.0 / us.max()
        return [(w, float(u)) for (w, _), u in zip(pts, us)]

    east, bend, south = fam_dirs["east"], fam_dirs["bend"], fam_dirs["south"]

    def mid(a, b):
        v = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        n = math.hypot(*v)
        return (v[0] / n, v[1] / n)

    return {
        "straight_front_baseline": (
            [(-35.0, 0.0), (35.0, 0.0)],
            "existing 70 ft straight downstage edge", 1),
        "shallow_arc_apron": (
            arc(4.0, 1.0),
            "70 ft chord, 4 ft centre bow, 1 ft corner projection "
            "(parabolic approximation of a circular bow)", 2),
        "moderate_arc_apron": (
            arc(8.0, 1.5),
            "70 ft chord, 8 ft centre bow, 1.5 ft corner projection", 2),
        "three_facet_apron": (
            facets([-35.0, -12.0, 12.0, 35.0], [east, bend, south], 6.0),
            "centre facet aimed at the bend/southeast family, side facets "
            "at east and south; max projection ≤6 ft", 3),
        "five_facet_apron": (
            facets([-35.0, -21.0, -7.0, 7.0, 21.0, 35.0],
                   [east, mid(east, bend), bend, mid(bend, south), south],
                   6.0),
            "five facets smoothing the three-family hinge; rectangular "
            "upstage core preserved", 3),
    }


def typologies(P, az, best_corner_w):
    """Each typology = list of (label, polygon, z_bot, z_top, solid_note)."""
    deck = ("deck", rect(P, az, 35.0, -34.0, 0.0), *DECK_Z, "deck slab")
    t = {}
    t["T1_deck_only"] = [deck]
    t["T2_covered_civic"] = [
        deck,
        ("roof", rect(P, az, 37.0, -36.0, 2.0),
         C.FOCUS_ELEV + 20.0, C.FOCUS_ELEV + 22.0,
         "thin roof slab on slender posts (posts <0.5 deg, not modelled)"),
    ]
    t["T3_acoustic_canopy"] = [
        deck,
        ("canopy", rect(P, az, 36.0, -34.0, -14.0),
         C.FOCUS_ELEV + 14.0, C.FOCUS_ELEV + 18.0,
         "curved acoustic canopy over the upstage half; open below; NO back wall"),
    ]
    t["T4_asymmetric_utility"] = [
        deck,
        ("boh", affinity.translate(rect(P, az, 12.0, -50.0, -34.0),
                                   xoff=U(az + 90)[0] * best_corner_w * 23.0,
                                   yoff=U(az + 90)[1] * best_corner_w * 23.0),
         C.FOCUS_ELEV, C.FOCUS_ELEV + 12.0,
         "24x16x12 back-of-house block tucked into the most-hidden upstage corner"),
    ]
    masts = []
    for s in (-1.0, 1.0):
        masts.append((f"mast_{'l' if s < 0 else 'r'}",
                      affinity.translate(rect(P, az, 1.0, -35.0, -33.0),
                                         xoff=U(az + 90)[0] * s * 33.0,
                                         yoff=U(az + 90)[1] * s * 33.0),
                      C.FOCUS_ELEV, C.FOCUS_ELEV + 26.0,
                      "removable screen mast (seasonal; screen itself is "
                      "night-only and not a permanent element)"))
    t["T5_movie_capable"] = [deck] + masts
    t["T6_side_framed_acoustic"] = [
        deck,
        ("wing_l", affinity.translate(rect(P, az, 1.0, -34.0, -14.0),
                                      xoff=U(az + 90)[0] * -36.0,
                                      yoff=U(az + 90)[1] * -36.0),
         C.FOCUS_ELEV, C.FOCUS_ELEV + 12.0, "solid side wing, lateral only"),
        ("wing_r", affinity.translate(rect(P, az, 1.0, -34.0, -14.0),
                                      xoff=U(az + 90)[0] * 36.0,
                                      yoff=U(az + 90)[1] * 36.0),
         C.FOCUS_ELEV, C.FOCUS_ELEV + 12.0, "solid side wing, lateral only"),
    ]
    t["T7_hybrid"] = [
        deck,
        ("apron", rect(P, az, 26.0, 0.0, 12.0), *DECK_Z,
         "faceted forecourt apron at deck level"),
        ("service_canopy", rect(P, az, 22.0, -32.0, -8.0),
         C.FOCUS_ELEV + 18.0, C.FOCUS_ELEV + 21.0,
         "overhead service/lighting canopy"),
        ("boh", affinity.translate(rect(P, az, 8.0, -46.0, -34.0),
                                   xoff=U(az + 90)[0] * best_corner_w * 27.0,
                                   yoff=U(az + 90)[1] * best_corner_w * 27.0),
         C.FOCUS_ELEV, C.FOCUS_ELEV + 10.0, "16x12x10 corner BOH"),
    ]
    return t


OPERATIONAL = {
    # deck_w, deck_d are filled per placement; scores 0-5 with stated basis
    "T1_deck_only": dict(
        wings=1, ceremony=4, concert=2, movie=2, rigging=0, weather=0,
        storage=0, acoustic=1,
        constructability=1,
        basis="bare 70x34 deck; PA/lighting fully temporary every event; no "
              "cover, no rig points, gear trucked per event"),
    "T2_covered_civic": dict(
        wings=2, ceremony=5, concert=4, movie=4, rigging=4, weather=4,
        storage=1, acoustic=3,
        constructability=3,
        basis="thin roof = rain-safe civic programming + permanent rig "
              "points; open all sides"),
    "T3_acoustic_canopy": dict(
        wings=2, ceremony=4, concert=4, movie=3, rigging=3, weather=2,
        storage=1, acoustic=4,
        basis="upstage canopy projects sound up the bowl without a back "
              "wall; partial rain cover",
        constructability=3),
    "T4_asymmetric_utility": dict(
        wings=3, ceremony=4, concert=3, movie=3, rigging=1, weather=1,
        storage=4, acoustic=2,
        basis="on-site storage/green room transforms operations; deck "
              "otherwise bare",
        constructability=2),
    "T5_movie_capable": dict(
        wings=1, ceremony=4, concert=3, movie=5, rigging=2, weather=0,
        storage=0, acoustic=1,
        basis="dedicated removable masts make movie night one-crew; masts "
              "double as PA points",
        constructability=2),
    "T6_side_framed_acoustic": dict(
        wings=4, ceremony=4, concert=4, movie=3, rigging=2, weather=1,
        storage=2, acoustic=4,
        basis="side wings give lateral reflection + true wing space; "
              "upstage slot stays open to the bay",
        constructability=2),
    "T7_hybrid": dict(
        wings=3, ceremony=5, concert=5, movie=4, rigging=4, weather=3,
        storage=3, acoustic=4,
        basis="performance core + apron for ceremonies + service canopy "
              "rig + corner BOH: the full utilitarian kit",
        constructability=4),
}


def main():
    C.verify_against_design()
    frame = json.load(open(os.path.join(
        OUT, "section_balance.json")))["audience_frame"]
    pareto = json.load(open(os.path.join(
        C.REPO, "analysis", "stage_seating_decoupling", "pareto_summary.json")))
    env = Envelope()

    treads = json.load(open(os.path.join(C.VEC_DIR,
                                         "terrace_treads.geojson")))["features"]
    row1 = {s: unary_union([shape(f["geometry"]) for f in treads
                            if f["properties"]["section"] == s
                            and f["properties"]["row"] == 1])
            for s in C.SECTIONS}
    zones = {}
    for f in json.load(open(os.path.join(C.VEC_DIR,
                                         "bowl_zones.geojson")))["features"]:
        zones.setdefault(f["properties"]["zone"], []).append(f)
    cell = shape(zones["treatment_cell_landscape"][0]["geometry"])
    corridor = shape(next(
        f for f in json.load(open(os.path.join(
            C.VEC_DIR, "site_context.geojson")))["features"]
        if f["properties"]["kind"] == "bay_view_corridor")["geometry"])

    acx, acy = frame["audience_centroid_seatweighted"]
    fx0, fy0 = frame["stage_front_centre"]
    ux, uy = U(C.STAGE_AX_AZ)
    wx, wy = U(C.STAGE_AX_AZ + 90.0)
    lat = frame["stage_lateral_offset_ft"]
    placements = {
        "P_inherited": dict(P=(fx0, fy0), az=C.STAGE_AX_AZ),
        "P_lat": dict(P=(fx0 + wx * lat, fy0 + wy * lat), az=C.STAGE_AX_AZ),
        "P_frame": dict(P=(fx0 + wx * lat * 0.5, fy0 + wy * lat * 0.5),
                        az=frame["centroid_bearing_from_stage_front_deg"]),
    }

    # precompute rays per station over the working sector
    az_grid = np.arange(255.0, 360.0, 1.0)
    rays = {}
    for st in env.stations:
        rays[(st["section"], st["band"])] = {
            az: env.trace(st, az) for az in az_grid}

    def placement_metrics(P, az):
        b_cent = (math.degrees(math.atan2(acx - P[0], acy - P[1]))) % 360.0
        mism = ((b_cent - az + 180) % 360) - 180
        vxx, vyy = acx - P[0], acy - P[1]
        uxx, uyy = U(az)
        lat_off = vxx * uyy - vyy * uxx
        deck = rect(P, az, 35.0, -34.0, 0.0)
        # downstage edge: the u=0 side of the rect (exterior ring points 2-3)
        front = LineString([deck.exterior.coords[2], deck.exterior.coords[3]])
        return dict(
            axis_mismatch_deg=round(mism, 1),
            lateral_offset_ft=round(lat_off, 1),
            front_to_row1_ft={s: round(row1[s].distance(front), 1)
                              for s in C.SECTIONS},
            cell_clearance_ft=round(deck.distance(cell), 1),
            deck_overlaps_cell=bool(deck.intersects(cell)),
        )

    def score_elements(elements):
        """Incremental obstruction vs the baseline envelope, per family.

        Area-weighted: blocked angular degrees are summed over ALL rays of
        the family's stations and divided by the total visible degrees, so a
        narrow mast that kills three rays reads as a small share of the bay,
        not "100% of the rays it crosses". Foreground (cell) blockage uses
        the RAW element band — the rim behind the cell cannot hide a mass
        standing in front of it."""
        out = {}
        for sec in C.SECTIONS:
            bay_blk = bay_tot = cell_blk = cell_tot = 0.0
            sky_sum, n_rays, n_cross = 0.0, 0, 0
            for band in ("front", "mid", "upper"):
                st = next(s for s in env.stations
                          if s["section"] == sec and s["band"] == band)
                for az in az_grid:
                    ray = rays[(sec, band)][az]
                    if ray is None:
                        continue
                    n_rays += 1
                    if ray["bay_band"]:
                        bay_tot += ray["bay_band"][1] - ray["bay_band"][0]
                    if ray["cell_band"]:
                        cell_tot += ray["cell_band"][1] - ray["cell_band"][0]
                    ex, ey = U(az)
                    rline = LineString(
                        [(st["x"] + ex * 6, st["y"] + ey * 6),
                         (st["x"] + ex * 760, st["y"] + ey * 760)])
                    bands = []
                    for label, poly, zb, zt, note in elements:
                        hit = rline.intersection(poly)
                        if hit.is_empty:
                            continue
                        pts = []
                        for g in getattr(hit, "geoms", [hit]):
                            pts += list(g.coords)
                        d0 = min(math.hypot(px - st["x"], py - st["y"])
                                 for px, py in pts)
                        bands.append((
                            math.degrees(math.atan2(zb - st["eye"], d0)),
                            math.degrees(math.atan2(zt - st["eye"], d0)),
                            d0))
                    if not bands:
                        continue
                    n_cross += 1
                    skyline = max(ray["sil"],
                                  ray["horizon"] if ray["bay_band"] else -90.0)
                    bay_f = cell_f = sky_d = 0.0
                    for lo, hi, d0 in bands:
                        if ray["bay_band"]:
                            blo, bhi = ray["bay_band"]
                            bay_f = max(bay_f, max(
                                0.0, min(hi, bhi) - max(lo, blo)))
                        if ray["cell_band"]:
                            clo, chi, dcn, dcf = ray["cell_band"]
                            if dcn > d0:   # cell lies beyond the element
                                cell_f = max(cell_f, max(
                                    0.0, min(hi, chi) - max(lo, clo)))
                        sky_d = max(sky_d, max(0.0, hi - max(skyline, lo)))
                    bay_blk += bay_f
                    cell_blk += cell_f
                    sky_sum += sky_d
            out[sec] = dict(
                rays_total=n_rays,
                rays_crossing=n_cross,
                new_bay_blocked_pct=round(100 * bay_blk / bay_tot, 1)
                if bay_tot > 0 else 0.0,
                new_cell_blocked_pct=round(100 * cell_blk / cell_tot, 1)
                if cell_tot > 0 else 0.0,
                new_sky_blocked_deg_mean=round(sky_sum / n_rays, 3)
                if n_rays else 0.0,
            )
        return out

    # P_opt: constrained search — keep the az-150 bay axis, slide laterally
    # toward the frame and pull the deck upstage until every family keeps a
    # workable orchestra gap. (The naive full-shift P_lat touches east row 1;
    # P_frame touches south row 1 — the row-1 pocket forbids a clean zero.)
    # This is canon Rule 9 path 3 territory: residuals are declared, not hidden.
    placements_search = []
    for s in (np.arange(0.0, lat - 0.01, -0.5) if lat < 0 else [0.0]):
        for t in np.arange(0.0, 14.01, 0.5):
            P = (fx0 + wx * s - ux * t, fy0 + wy * s - uy * t)
            m = placement_metrics(P, C.STAGE_AX_AZ)
            min_gap = min(m["front_to_row1_ft"].values())
            if min_gap >= 12.0 and m["cell_clearance_ft"] >= 15.0 \
                    and not m["deck_overlaps_cell"]:
                placements_search.append((abs(m["lateral_offset_ft"]),
                                          float(s), float(t), P))
    if placements_search:
        _, s_opt, t_opt, P_opt = min(placements_search)
        placements["P_opt"] = dict(P=P_opt, az=C.STAGE_AX_AZ)

    # axis comparison: deck-only at all placements
    axis_table = {name: placement_metrics(**pl)
                  for name, pl in placements.items()}
    sel_name = "P_opt" if "P_opt" in placements else "P_lat"
    sel = placements[sel_name]

    # most-hidden upstage corner for BOH typologies: trace both corners
    corner_scores = {}
    for s in (-1.0, 1.0):
        test = [("probe",
                 affinity.translate(rect(sel["P"], sel["az"], 12.0, -50.0, -34.0),
                                    xoff=U(sel["az"] + 90)[0] * s * 23.0,
                                    yoff=U(sel["az"] + 90)[1] * s * 23.0),
                 C.FOCUS_ELEV, C.FOCUS_ELEV + 12.0, "")]
        sc = score_elements(test)
        corner_scores[s] = sum(v["new_bay_blocked_pct"]
                               + v["new_sky_blocked_deg_mean"]
                               for v in sc.values())
    best_corner = min(corner_scores, key=corner_scores.get)

    # ── element menu: every overhead/vertical option scored ALONE so the
    # deltas compose — deck geometry and superstructure stay separable ──────
    all_typo = typologies(sel["P"], sel["az"], best_corner)
    element_menu = {}
    seen = set()
    for tname, elements in all_typo.items():
        for el in elements:
            label = el[0]
            if label in ("deck",) or label in seen:
                continue
            seen.add(label)
            sc = score_elements([el])
            element_menu[label] = dict(
                from_typology=tname,
                z_bottom=el[2], z_top=el[3],
                height_ft=round(el[3] - C.FOCUS_ELEV, 1),
                plan_area_sf=round(el[1].area, 0),
                note=el[4],
                obstruction_delta=sc,
                worst_new_bay_pct=max(v["new_bay_blocked_pct"]
                                      for v in sc.values()),
                worst_new_cell_pct=max(v["new_cell_blocked_pct"]
                                       for v in sc.values()),
            )
    deck_only_obs = score_elements([all_typo["T1_deck_only"][0]])

    # ── stage front / apron geometry: the downstage edge as a variable ─────
    ux_s, uy_s = U(sel["az"])
    wx_s, wy_s = U(sel["az"] + 90.0)
    P_s = sel["P"]

    def to_world(w, u):
        return (P_s[0] + ux_s * u + wx_s * w, P_s[1] + uy_s * u + wy_s * w)

    fam_dirs, fam_c8 = {}, {}
    for s in C.SECTIONS:
        f8 = next(f for f in treads if f["properties"]["section"] == s
                  and f["properties"]["row"] == 8)
        c = shape(f8["geometry"]).centroid
        fam_c8[s] = c
        v = (c.x - P_s[0], c.y - P_s[1])
        n = math.hypot(*v)
        v = (v[0] / n, v[1] / n)
        fam_dirs[s] = (v[0] * wx_s + v[1] * wy_s,    # local w component
                       v[0] * ux_s + v[1] * uy_s)    # local u component

    core_deck = rect(P_s, sel["az"], 35.0, -34.0, 0.0)
    apron_results = {}
    base_perf = None
    for name, (front, note, cx) in apron_front_candidates(
            P_s, sel["az"], fam_dirs).items():
        wf = [to_world(w, u) for w, u in front]
        ring = ([to_world(front[0][0], 0.0)] + wf
                + [to_world(front[-1][0], 0.0)])
        apron_poly = Polygon(ring).buffer(0)
        deck_total = core_deck.union(apron_poly)
        # performer at the front edge on the centreline
        ws_ = np.array([w for w, _ in front])
        us_ = np.array([u for _, u in front])
        u_mid = float(np.interp(0.0, ws_, us_))
        perf = Point(to_world(0.0, u_mid))
        # effective (Lambert-foreshortened, front-facing) frontage per family
        frontage = {}
        for s in C.SECTIONS:
            tot = 0.0
            for i in range(len(front) - 1):
                (w0, u0), (w1, u1) = front[i], front[i + 1]
                seg_l = math.hypot(w1 - w0, u1 - u0)
                if seg_l == 0:
                    continue
                nw, nu = (-(u1 - u0) / seg_l, (w1 - w0) / seg_l)  # outward
                n_world = (nw * wx_s + nu * ux_s, nw * wy_s + nu * uy_s)
                mx, my = to_world((w0 + w1) / 2, (u0 + u1) / 2)
                v = (fam_c8[s].x - mx, fam_c8[s].y - my)
                vn = math.hypot(*v)
                cosang = (n_world[0] * v[0] + n_world[1] * v[1]) / vn
                tot += seg_l * max(0.0, cosang)
            frontage[s] = round(tot, 1)
        gaps = {s: round(deck_total.distance(row1[s]), 1) for s in C.SECTIONS}
        perf_d = {s: round(perf.distance(row1[s]), 1) for s in C.SECTIONS}
        if name == "straight_front_baseline":
            base_perf = perf_d
        obs = score_elements([("deck_apron", deck_total, *DECK_Z,
                               "deck + apron slab")])
        apron_results[name] = dict(
            note=note,
            added_apron_area_sf=round(apron_poly.area, 0),
            max_projection_ft=round(float(us_.max()), 1),
            effective_frontage_ft=frontage,
            row1_gap_ft=gaps,
            performer_to_row1_ft=perf_d,
            bend_gap_improves_without_pocket_violation=bool(
                base_perf is not None
                and perf_d["bend"] < base_perf["bend"]
                and gaps["east"] >= 12.0 and gaps["south"] >= 12.0),
            bend_performer_delta_ft=round(
                perf_d["bend"] - base_perf["bend"], 1) if base_perf else 0.0,
            obstruction_delta=dict(
                worst_new_bay_pct=max(v["new_bay_blocked_pct"]
                                      for v in obs.values()),
                worst_new_cell_pct=max(v["new_cell_blocked_pct"]
                                       for v in obs.values())),
            usable_rect_core_retained="70x34 intact (apron additive downstage)",
            constructability=cx,
            rule9_status="OPEN preserved — front geometry adopts no axis",
        )

    results = {}
    for name, elements in all_typo.items():
        obs = score_elements(elements)
        worst_bay = max(v["new_bay_blocked_pct"] for v in obs.values())
        worst_cell = max(v["new_cell_blocked_pct"] for v in obs.values())
        if worst_bay > MINOR_BAY_PCT:
            verdict = (f"FLAGGED — {worst_bay}% of a family's visible bay "
                       "band newly blocked; redesign the offending mass or "
                       "justify explicitly (NOT a height rejection)")
        elif worst_cell > 35.0:
            verdict = (f"ACCEPTABLE w/ CAVEAT — bay clear (≤{worst_bay}%) but "
                       f"{worst_cell}% of a family's treatment-cell foreground "
                       "newly blocked; relocate the mass or accept the meadow "
                       "loss for that family explicitly")
        elif worst_bay <= NO_MEANINGFUL_PCT:
            verdict = "ACCEPTABLE — no meaningful new bay obstruction"
        else:
            verdict = ("ACCEPTABLE (minor) — new bay obstruction quantified "
                       f"at ≤{worst_bay}% of the visible band")
        opaque_upstage = any("wall" in lbl and poly.intersects(corridor)
                             for lbl, poly, *_ in elements)
        op = dict(OPERATIONAL[name])
        op_total = sum(v for k, v in op.items()
                       if k not in ("basis", "constructability"))
        results[name] = dict(
            elements=[dict(label=l, z_bottom=zb, z_top=zt,
                           height_ft=round(zt - C.FOCUS_ELEV, 1), note=nt)
                      for l, p, zb, zt, nt in elements],
            incremental_obstruction=obs,
            worst_new_bay_pct=worst_bay,
            worst_new_cell_pct=worst_cell,
            opaque_wall_in_bay_corridor=opaque_upstage,
            operational=op,
            operational_total=op_total,
            verdict=verdict,
            non_negotiables=dict(
                full_enclosure=False, permanent_fly_tower=False,
                permanent_water=False,
                acoustic_claim="qualitative plausibility only — no shell "
                               "performance claim",
            ),
        )

    payload = dict(
        generated_by="scripts/stage_shape_study.py",
        governing_scheme=C.GOVERNING_SCHEME,
        visual_envelope_rule=(
            "mass hiding below the terrain silhouette behind it adds no "
            "obstruction; new bay/cell/sky blockage is measured per family; "
            f"bay ≤{NO_MEANINGFUL_PCT}% none / ≤{MINOR_BAY_PCT}% minor / "
            "above = flagged-not-height-rejected"),
        frame_source=dict(
            file="analysis/in_situ_normalization/section_balance.json",
            audience_centroid=frame["audience_centroid_seatweighted"]),
        independent_zone_test=dict(
            file="analysis/stage_seating_decoupling/pareto_summary.json",
            co_leader_band=pareto["co_leaders_within_0p02"],
            inherited_in_band=pareto["inherited_stage_in_co_leader_band"],
            note="placements lie inside the independently-derived southern "
                 "pan-toe zone band"),
        placement_axis_comparison=axis_table,
        selected_placement=dict(
            name=sel_name, front_centre=[round(sel["P"][0], 1),
                                         round(sel["P"][1], 1)],
            axis_az=sel["az"],
            reason="constrained search keeping the az-330 bay axis: slide "
                   "laterally toward the frame + pull upstage until every "
                   "family keeps a >=12 ft orchestra gap and >=15 ft cell "
                   "clearance — the row-1 pocket forbids zeroing the offset "
                   "(P_lat touches east row 1, P_frame touches south row 1); "
                   "residual offset declared per Rule 9 path 3"),
        boh_corner=("west/left" if best_corner < 0 else "east/right"),
        rule9_status="open — this study produces the tested candidate set "
                     "for the Rule 9 decision; it does not adopt one",
        deck_geometry=dict(
            footprint="70 x 34 ft core, downstage edge at the selected front "
                      "centre, low shoulders excluded from this study",
            deck_elev_navd88=C.FOCUS_ELEV,
            structure_band_ft=1.0,
            placement=axis_table[sel_name],
            obstruction_of_deck_alone=deck_only_obs,
            stage_front_apron=apron_results,
        ),
        elements_menu=element_menu,
        rule9_implications=dict(
            status="OPEN — nothing here adopts a path",
            paths={
                "path1_audience_axis": dict(
                    placement="P_frame",
                    metrics=axis_table["P_frame"],
                    consequence="axis turns to the audience centroid "
                                "(124.6); audience faces ~305 — a 25 deg "
                                "bay-axis deviation must be acknowledged and "
                                "justified; touches south row 1 as searched "
                                "(needs its own gap search before adoption)"),
                "path2_bay_axis_lateral": dict(
                    placement="P_lat",
                    metrics=axis_table["P_lat"],
                    consequence="keeps az 150/330; the FULL lateral shift "
                                "zeroes the offset but touches east row 1 — "
                                "infeasible as-is; partial shift collapses "
                                "into path 3"),
                "path3_compromise": dict(
                    placement="P_opt (this study's tested candidate)",
                    metrics=axis_table.get("P_opt"),
                    consequence="keeps the bay axis, slides −15.5 ft lateral "
                                "+ pulls upstage; residuals −6.7 ft / −6.3 "
                                "deg DECLARED; all row-1 gaps ≥ 12 ft, cell "
                                "clearance 32 ft"),
                "path4_wide_fan_declaration": dict(
                    placement="any",
                    metrics=None,
                    consequence="config/canon change only "
                                "(harness_config fan fields); orthogonal to "
                                "placement; acoustic consequences must be "
                                "noted per Rule 9 text"),
            },
            adoption_requires=[
                "pick a placement path (P_opt = path 3 is the measured "
                "front-runner), a stage-front geometry from section A2 "
                "(faceted fronts are the measured front-runners), AND an "
                "element bundle",
                "declare every minor obstruction number for the chosen "
                "bundle (per-family deltas in section C)",
                "update harness_config.yaml / DESIGN_CANON Rule 9 status "
                "and re-run the Scenario E stage validation",
                "re-emit every stage-derived artifact from the ADOPTED "
                "footprint: the orchestra and untouched-slope zones in "
                "bowl_zones/material_zones, the six viewpoint stations "
                "(cameras/targets currently reference the inherited stage "
                "centroid), the event-mode movie-screen line, and the "
                "grading rasters — then drop Board 01's presentation "
                "patches (provisional floor override + backdrop hole fill), "
                "which become redundant",
                "only then un-pause the Claude Design handoff and let "
                "boards claim a settled stage",
            ],
        ),
        typologies=results,
    )
    with open(os.path.join(OUT, "stage_typology_scores.json"), "w") as fh:
        json.dump(payload, fh, indent=1)

    md = ["# Stage Shape Study — deck, superstructure options, obstruction, "
          "operations, Rule 9", "",
          "Five separated products; nothing here adopts a stage. "
          + payload["visual_envelope_rule"], "",
          "---", "", "## A · Deck geometry (placement + footprint)", "",
          "70 × 34 ft performance core at the event-floor grade "
          f"({C.FOCUS_ELEV} ft, ~1 ft structure band). Placement search "
          "against the audience frame and the row-1 pocket:",
          "",
          "| placement | axis | mismatch° | lateral ft | front→row1 e/b/s ft | cell gap ft |",
          "|---|---|---|---|---|---|"]
    for n, m in axis_table.items():
        fr = m["front_to_row1_ft"]
        md.append(f"| {n}{' **(selected)**' if n == sel_name else ''} | "
                  f"{placements[n]['az']:.1f} | "
                  f"{m['axis_mismatch_deg']} | {m['lateral_offset_ft']} | "
                  f"{fr['east']}/{fr['bend']}/{fr['south']} | "
                  f"{m['cell_clearance_ft']} |")
    dk = deck_only_obs
    md += ["", payload["selected_placement"]["reason"] + ".",
           f"Deck alone adds {max(v['new_bay_blocked_pct'] for v in dk.values())}% "
           f"bay / {max(v['new_cell_blocked_pct'] for v in dk.values())}% "
           "foreground obstruction (worst family) — the deck is visually free.",
           "", "### A2 · Stage front / apron geometry (the downstage edge "
           "as a variable)", "",
           "The bowl's three families subtend an obtuse angle at the stage; "
           "bowing or faceting the FRONT may close the bend/southeast "
           "distance more naturally than translating the whole rectangle "
           "into the east/south row-1 pockets. All candidates keep the "
           "70 × 34 rectangular core; facet normals are aimed at the "
           "measured family row-8 centroids.",
           "",
           "| front | apron sf | proj ft | eff. frontage e/b/s ft | "
           "row-1 gap e/b/s ft | performer→row1 e/b/s ft | bend Δ ft | "
           "bend better, pockets OK | bay/cell Δ% | cx /5 |",
           "|---|---|---|---|---|---|---|---|---|---|"]
    for n, a in apron_results.items():
        fr, gp, pf = (a["effective_frontage_ft"], a["row1_gap_ft"],
                      a["performer_to_row1_ft"])
        ob = a["obstruction_delta"]
        md.append(
            f"| {n} | {a['added_apron_area_sf']:.0f} | "
            f"{a['max_projection_ft']} | "
            f"{fr['east']}/{fr['bend']}/{fr['south']} | "
            f"{gp['east']}/{gp['bend']}/{gp['south']} | "
            f"{pf['east']}/{pf['bend']}/{pf['south']} | "
            f"{a['bend_performer_delta_ft']} | "
            f"{'✓' if a['bend_gap_improves_without_pocket_violation'] else '✗'} | "
            f"{ob['worst_new_bay_pct']}/{ob['worst_new_cell_pct']} | "
            f"{a['constructability']} |")
    md += ["",
           "**Reading:** the symmetric arcs close the bend distance (−3.9 / "
           "−7.8 ft) but project into the tight east pocket (gap 11.4 / 11.1 "
           "< 12 ft) — they fail. The AIMED facets concentrate projection on "
           "the bend-facing centre: −5.5 ft to bend with east held at 12.0 "
           "and south at 18.9, zero obstruction delta, and slightly MORE "
           "east frontage than the straight front. The faceted apron solves "
           "the bowl's obtuse audience angle without moving the rectangle — "
           "the five-facet adds smoothness over the three-facet for no "
           "measurable difference.",
           "",
           "Every candidate keeps the rectangular core usable, stays at deck "
           "level (z 612.5–613.5), and preserves Rule 9 OPEN (front geometry "
           "adopts no axis). The front choice composes with any element "
           "bundle in section B; T7's generic apron element is superseded by "
           "this section.",
           "", "---", "",
           "## B · Roof / canopy / mast options (element menu)", "",
           "Each superstructure element is scored ALONE at the selected "
           "placement so options compose; bundles in section C cross-check.",
           "",
           "| element | plan sf | top ft above deck | role |",
           "|---|---|---|---|"]
    for label, e in element_menu.items():
        md.append(f"| {label} | {e['plan_area_sf']:.0f} | {e['height_ft']} | "
                  f"{e['note']} |")
    md += ["", "---", "", "## C · Obstruction deltas (by family)", "",
           "Per-element, area-weighted share of the EXISTING visible band "
           "newly blocked (bay %), foreground meadow blocked (cell %), and "
           "mean new skyline cut (sky °):",
           "",
           "| element | east bay/cell | bend bay/cell | south bay/cell | worst sky ° |",
           "|---|---|---|---|---|"]
    for label, e in element_menu.items():
        ob = e["obstruction_delta"]
        sky = max(v["new_sky_blocked_deg_mean"] for v in ob.values())
        cells = " | ".join(
            f"{ob[s]['new_bay_blocked_pct']}/{ob[s]['new_cell_blocked_pct']}"
            for s in C.SECTIONS)
        md.append(f"| {label} | {cells} | {sky} |")
    md += ["", "Bundled typologies (measured as combinations, not sums):", "",
           "| bundle | elements | worst new bay % | worst new cell % | verdict |",
           "|---|---|---|---|---|"]
    for n, r in results.items():
        els = "+".join(e["label"] for e in r["elements"] if e["label"] != "deck") or "—"
        md.append(f"| {n} | {els} | {r['worst_new_bay_pct']} | "
                  f"{r['worst_new_cell_pct']} | {r['verdict'].split(' — ')[0]} |")
    md += ["", "---", "", "## D · Operational scores", "",
           "| bundle | wings | ceremony | concert | movie | rigging | weather "
           "| storage | acoustic | total /40 | constructability /5 |",
           "|---|---|---|---|---|---|---|---|---|---|---|"]
    for n, r in results.items():
        o = r["operational"]
        md.append(f"| {n} | {o['wings']} | {o['ceremony']} | {o['concert']} | "
                  f"{o['movie']} | {o['rigging']} | {o['weather']} | "
                  f"{o['storage']} | {o['acoustic']} | "
                  f"{r['operational_total']} | {o['constructability']} |")
    md += ["", "Bases for each rubric line: `stage_typology_scores.json` "
           "(`operational.basis`). The T5 screen is night-only; masts are "
           "removable and scored standing.",
           "", "---", "", "## E · Rule 9 implications", ""]
    for pname, p in payload["rule9_implications"]["paths"].items():
        md.append(f"- **{pname}** ({p['placement']}): {p['consequence']}")
    md += ["", "Adoption requires:",
           ""] + [f"1. {s}" for s in
                  payload["rule9_implications"]["adoption_requires"]] + [
           "", "**Rule 9 remains OPEN.** Board 01 shows only the selected "
           "PROVISIONAL footprint (P_opt) pending this decision.", ""]
    with open(os.path.join(OUT, "STAGE_SHAPE_STUDY.md"), "w") as fh:
        fh.write("\n".join(md))
    print("  wrote analysis/in_situ_normalization/stage_typology_scores.json, "
          "STAGE_SHAPE_STUDY.md")
    for n, r in results.items():
        print(f"  {n:24s} bay {r['worst_new_bay_pct']:5.1f}%  cell "
              f"{r['worst_new_cell_pct']:5.1f}%  op {r['operational_total']:2d}"
              f"  {r['verdict'].split(' — ')[0]}")


if __name__ == "__main__":
    main()
