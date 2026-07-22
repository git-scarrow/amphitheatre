#!/usr/bin/env python3
"""DR-1 — Tower-floor observer class over the pit parcel (canopy-lever asymmetry test).

Strategy dispatch DR-1 (strategy/DISPATCH_REQUESTS.md). Prices the pit owner's
vertical option: does de-treeing widen the bay band mostly at LOW elevations
(street receptors, seated rows) while a hypothetical tower's UPPER floors already
clear the canopy (so removal adds little to their view premium)?

This is a NEW observer class on the SAME bay-band v2 measurement basis as the
adopted seated-row product (commit 4e6d03a): identical occluder sets, identical
effective-silhouette definition (D1), identical far-shore band top (D3), identical
corridor. The ONLY differences from `bay_band_v2.analyse` are:
  - observers are a plan GRID over the pit parcel (not tread rows), and
  - eyes are FIXED absolute NAVD88 tower-plate elevations (not ground+seated).

Observers
  Plan: grid over pit parcel GIS PARCELID 52-19-06-224-001 (= tax PID
        52-19-06-227-016; 2.01 ac outer envelope) at ~25 ft spacing.
        [ASSUMPTION: plate grid + 25 ft spacing, pipeline's choice per DR-1.]
  Floors 2-8: plate = grade 618 ft + 12 ft/floor; eye = plate + 5 ft ->
        635 / 647 / 659 / 671 / 683 / 695 / 707 ft NAVD88 (floors 2->8).

Bands (D1-D5, BAY_BAND_V2_DECISION_ADDENDUM.md)
  S0    terrain only (bare-earth dem_design)                     durable
  S1    + flat stage (612.5) + LiDAR-verified city massing       durable
  S2off + canopy-today, leaf-off 2015-05-02 (MEASUREMENT)        contingent
  S2on  + canopy-today, leaf-on (crown-opacity ASSUMPTION)       contingent
  Band top = far-shore waterline (D3). Corridor az 318-342 at 2 deg.
  A ray "sees water" when theta_top > effective silhouette of the set.
  clear% = fraction of the 13 corridor rays seeing water.
  verdict: acceptable >=80 · marginal 40-79 · blocked <40.

Canopy-removal band gain per floor = clear%(S1) - clear%(S2). S1 is canopy-free
(durable), so this delta is exactly what de-treeing buys at that eye height.

Outputs (analysis/bay_view_obstruction/dr1_tower_floors/):
  dr1_per_position_bands.csv   per (floor, position): clear% + verdict, all 4 sets
  dr1_per_floor_summary.csv    per floor per set: median + IQR (p25/p75) clear%,
                               and canopy-removal delta (S1 - S2off / S1 - S2on)
  dr1_per_floor_summary.md     same, human-readable
  (DR1_ANSWER.md is written by the caller / committed alongside)

EPSG:6494 · NAVD88 intl ft · planning-grade. Emits analysis only; adopts nothing.
Scripts print FAIL but exit 0 -> parse text, never rc. Leaf-off is the measurement;
leaf-on is a labeled assumption. No element/observer passes on S2 alone.
"""
import csv
import json
import math
import os
import sys

import numpy as np
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import in_situ_common as C
import bay_band_v2 as V

REPO = C.REPO
OUT = os.path.join(REPO, "analysis", "bay_view_obstruction", "dr1_tower_floors")
PARCELS = os.path.join(REPO, "strategy", "data", "parcels_block_6494.json")
TARGET_PARCELID = "52-19-06-224-001"

GRID_SPACING_FT = 25.0                       # [ASSUMPTION: plate grid, DR-1]
PLATE_GRADE = 618.0                          # DR-1: plate at grade ~618 ft
FT_PER_FLOOR = 12.0                          # DR-1
EYE_ABOVE_PLATE = 5.0                        # DR-1
FLOORS = list(range(2, 9))                   # floors 2..8
# plate: floor 1 sits at grade (618); each floor adds 12 ft; eye = plate + 5.
# eye(floor) = 618 + 12*(floor-1) + 5  ->  635/647/659/671/683/695/707 (floors 2..8),
# matching the DR-1 canonical eye list exactly.
FLOOR_EYE = {f: PLATE_GRADE + FT_PER_FLOOR * (f - 1) + EYE_ABOVE_PLATE for f in FLOORS}
_EXPECTED_EYE = {2: 635, 3: 647, 4: 659, 5: 671, 6: 683, 7: 695, 8: 707}
assert FLOOR_EYE == {f: float(v) for f, v in _EXPECTED_EYE.items()}, FLOOR_EYE

AZS = V.azimuths()                           # 318..342 step 2 (13 rays)
NAZ = len(AZS)
VERDICT = V.VERDICT
BAY_PLANE = V.BAY_PLANE
R_EARTH_FT = V.R_EARTH_FT


def load_parcel_polygon():
    """Outer envelope of the pit parcel (Esri JSON rings, EPSG:6494).

    The parcel has 1 outer ring (area>0, the 2.01 ac boundary) + 15 inner
    condo-unit subdivision rings. The buildable envelope is the outer ring."""
    d = json.load(open(PARCELS))
    feat = next(f for f in d["features"]
                if f["attributes"].get("PARCELID") == TARGET_PARCELID)
    rings = feat["geometry"]["rings"]

    def signed_area(r):
        s = 0.0
        for i in range(len(r) - 1):
            x1, y1 = r[i]; x2, y2 = r[i + 1]
            s += (x2 - x1) * (y2 + y1)
        return s / 2.0

    outers = [Polygon(r) for r in rings if signed_area(r) > 0]
    poly = unary_union(outers)
    if poly.geom_type != "Polygon":
        poly = max(poly.geoms, key=lambda g: g.area)
    return poly


def grid_points(poly, spacing):
    minx, miny, maxx, maxy = poly.bounds
    xs = np.arange(minx + spacing / 2.0, maxx, spacing)
    ys = np.arange(miny + spacing / 2.0, maxy, spacing)
    pts = []
    for y in ys:
        for x in xs:
            if poly.contains(Point(x, y)):
                pts.append((float(x), float(y)))
    return pts


def theta_top_for(eye, d_shore):
    """Far-shore-waterline band top (D3), matching bay_band_v2.far_shore exactly.
    d_shore is eye-independent (waterline crossing along the plan ray)."""
    h = eye - BAY_PLANE
    if d_shore is None:
        return -V.dip_deg(h), True
    theta = -(math.degrees(math.atan(h / d_shore))
              + math.degrees(d_shore / (2.0 * R_EARTH_FT)))
    tangent = math.sqrt(2.0 * R_EARTH_FT * max(h, 0.0))
    return theta, (d_shore >= tangent)


def main():
    os.makedirs(OUT, exist_ok=True)
    eng = V.Engine()
    poly = load_parcel_polygon()
    pts = grid_points(poly, GRID_SPACING_FT)
    print(f"pit parcel {TARGET_PARCELID}: {round(poly.area/43560,3)} ac outer envelope; "
          f"{len(pts)} grid observers @ {GRID_SPACING_FT} ft spacing")

    # d_shore is eye-independent -> compute once per (point, az) via engine.far_shore
    # (using floor-2 eye purely to drive the trace; only d_shore is retained).
    per_pos_rows = []
    # accumulate clear% per (floor, set) across positions for the summary
    acc = {f: {k: [] for k in ("S0", "S1", "S2off", "S2on")} for f in FLOORS}
    n_fallback = 0

    for (ox, oy) in pts:
        # --- eye-independent per-az geometry: waterline distance d_shore ---
        d_shore_az = {}
        for az in AZS:
            e, n = C.U(float(az))
            dsh, _, _, _ = eng.far_shore(ox, oy, e, n, FLOOR_EYE[2])
            d_shore_az[az] = dsh

        for f in FLOORS:
            eye = FLOOR_EYE[f]
            clear = {"S0": 0, "S1": 0, "S2off": 0, "S2on": 0}
            fb_any = False
            for az in AZS:
                e, n = C.U(float(az))
                terr, _ = eng.terrain_sil(ox, oy, e, n, eye)
                stg, _, _ = eng.poly_sil(ox, oy, e, n, eye, eng.stage)
                cty, _, _ = eng.poly_sil(ox, oy, e, n, eye, eng.buildings)
                koff, _ = eng.canopy_sil(ox, oy, e, n, eye, "leafoff")
                kon, _ = eng.canopy_sil(ox, oy, e, n, eye, "leafon")
                tt, fb = theta_top_for(eye, d_shore_az[az])
                fb_any = fb_any or fb
                r = dict(terrain=terr, stage=stg, city=cty,
                         canopy_off=koff, canopy_on=kon, theta_top=tt)
                sil = V.sil_sets(r)   # S0, S1, S2off, S2on
                for k in clear:
                    if tt > sil[k]:
                        clear[k] += 1
            if fb_any:
                n_fallback += 1
            pct = {k: round(100.0 * v / NAZ, 1) for k, v in clear.items()}
            for k in acc[f]:
                acc[f][k].append(pct[k])
            per_pos_rows.append(dict(
                floor=f, eye_elev_navd88=round(eye, 1),
                x=round(ox, 2), y=round(oy, 2),
                clear_S0=pct["S0"], verdict_S0=VERDICT(pct["S0"]),
                clear_S1=pct["S1"], verdict_S1=VERDICT(pct["S1"]),
                clear_S2_leafoff=pct["S2off"], verdict_S2_leafoff=VERDICT(pct["S2off"]),
                clear_S2_leafon=pct["S2on"], verdict_S2_leafon=VERDICT(pct["S2on"]),
                canopy_gain_leafoff=round(pct["S1"] - pct["S2off"], 1),
                canopy_gain_leafon=round(pct["S1"] - pct["S2on"], 1),
                uses_dip_fallback=fb_any))

    _write_csv(os.path.join(OUT, "dr1_per_position_bands.csv"), per_pos_rows)

    # --- per-floor summary: median + IQR per set, canopy-removal delta ---
    def stats(vals):
        a = np.array(vals, float)
        return (round(float(np.median(a)), 1),
                round(float(np.percentile(a, 25)), 1),
                round(float(np.percentile(a, 75)), 1))

    sum_rows = []
    for f in FLOORS:
        rec = dict(floor=f, eye_elev_navd88=round(FLOOR_EYE[f], 1),
                   n_positions=len(acc[f]["S0"]))
        med = {}
        for k, label in (("S0", "S0"), ("S1", "S1"),
                         ("S2off", "S2_leafoff"), ("S2on", "S2_leafon")):
            m, q1, q3 = stats(acc[f][k])
            med[k] = m
            rec[f"clear_{label}_median"] = m
            rec[f"clear_{label}_p25"] = q1
            rec[f"clear_{label}_p75"] = q3
        # canopy-removal band gain (S1 minus S2), median-of-medians proxy AND
        # median of per-position deltas (the honest one)
        gain_off = [s1 - s2 for s1, s2 in zip(acc[f]["S1"], acc[f]["S2off"])]
        gain_on = [s1 - s2 for s1, s2 in zip(acc[f]["S1"], acc[f]["S2on"])]
        rec["canopy_gain_leafoff_median"] = round(float(np.median(gain_off)), 1)
        rec["canopy_gain_leafon_median"] = round(float(np.median(gain_on)), 1)
        rec["canopy_gain_leafoff_p75"] = round(float(np.percentile(gain_off, 75)), 1)
        rec["canopy_gain_leafon_p75"] = round(float(np.percentile(gain_on, 75)), 1)
        sum_rows.append(rec)

    _write_csv(os.path.join(OUT, "dr1_per_floor_summary.csv"), sum_rows)
    _write_summary_md(sum_rows, len(pts), n_fallback)

    # machine-readable stash for DR1_ANSWER.md authoring
    json.dump(dict(parcelid=TARGET_PARCELID, n_positions=len(pts),
                   grid_spacing_ft=GRID_SPACING_FT, floors=FLOORS,
                   floor_eye=FLOOR_EYE, corridor_deg=[318, 342], az_step=2.0,
                   summary=sum_rows),
              open(os.path.join(OUT, "dr1_summary.json"), "w"), indent=1)

    print("\nPer-floor median water-band clear% (canopy-removal gain = S1 - S2):")
    print(f"  {'floor':>5} {'eye':>6} {'S0':>6} {'S1':>6} {'S2off':>7} {'S2on':>7} "
          f"{'gainOff':>8} {'gainOn':>8}")
    for rec in sum_rows:
        print(f"  {rec['floor']:>5} {rec['eye_elev_navd88']:>6} "
              f"{rec['clear_S0_median']:>6} {rec['clear_S1_median']:>6} "
              f"{rec['clear_S2_leafoff_median']:>7} {rec['clear_S2_leafon_median']:>7} "
              f"{rec['canopy_gain_leafoff_median']:>8} {rec['canopy_gain_leafon_median']:>8}")
    print(f"\n{n_fallback} (floor,position) cells used the open-water dip fallback "
          f"(no far-shore waterline within DEM reach along >=1 corridor ray).")
    print("wrote dr1_per_position_bands.csv, dr1_per_floor_summary.csv/.md, dr1_summary.json")


def _write_summary_md(sum_rows, npos, n_fallback):
    L = ["# DR-1 tower-floor per-floor summary — water-band clear% by occluder set",
         "",
         f"Observers: **{npos}** plan-grid positions over pit parcel "
         f"`{TARGET_PARCELID}` (2.01 ac outer envelope) @ {int(GRID_SPACING_FT)} ft "
         "spacing [ASSUMPTION: plate grid, pipeline's choice per DR-1].",
         "Floors 2-8: plate = 618 + 12·floor ft; eye = plate + 5 ft.",
         "Band top = far-shore waterline (D3). Corridor az 318-342° at 2° (13 rays).",
         "clear% = fraction of corridor rays seeing water. verdict: "
         "acceptable ≥80 · marginal 40-79 · blocked <40.",
         "",
         "**Occluder sets (D2):** S0 terrain · S1 +stage+city (**durable**) · "
         "S2_leafoff canopy 2015-05-02 (**measurement, contingent**) · "
         "S2_leafon canopy crown-opacity (**assumption, contingent**). "
         "Canopy-removal band gain = clear%(S1) − clear%(S2) — what de-treeing buys.",
         "",
         "Values are **median [p25–p75 IQR]** across grid positions.",
         "",
         "| floor | eye ft | S0 | S1 | S2 leaf-off | S2 leaf-on | gain leaf-off | gain leaf-on |",
         "|---|---|---|---|---|---|---|---|"]
    for r in sum_rows:
        L.append(
            f"| {r['floor']} | {r['eye_elev_navd88']} "
            f"| {r['clear_S0_median']} [{r['clear_S0_p25']}–{r['clear_S0_p75']}] "
            f"| {r['clear_S1_median']} [{r['clear_S1_p25']}–{r['clear_S1_p75']}] "
            f"| {r['clear_S2_leafoff_median']} [{r['clear_S2_leafoff_p25']}–{r['clear_S2_leafoff_p75']}] "
            f"| {r['clear_S2_leafon_median']} [{r['clear_S2_leafon_p25']}–{r['clear_S2_leafon_p75']}] "
            f"| {r['canopy_gain_leafoff_median']} | {r['canopy_gain_leafon_median']} |")
    L += ["",
          f"Gain column = median over positions of per-position (S1 − S2) clear%. "
          f"{n_fallback} (floor,position) cells fell back to the open-water dip band "
          f"top on ≥1 ray (no far-shore waterline within DEM reach); flagged in the "
          f"per-position CSV (`uses_dip_fallback`).",
          "",
          "**Leaf state labels are load-bearing:** leaf-off is the winter-screen "
          "MEASUREMENT (2015-05-02 3DEP); leaf-on is a crown-opacity ASSUMPTION and "
          "the season-relevant one (summer is the operating season). No observer is "
          "credited a water view on S2 leeway alone — S2 columns are contingent on "
          "third-party (City / MDOT) canopy.",
          ""]
    open(os.path.join(OUT, "dr1_per_floor_summary.md"), "w").write("\n".join(L) + "\n")


def _write_csv(path, rows):
    if not rows:
        return
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)


if __name__ == "__main__":
    main()
