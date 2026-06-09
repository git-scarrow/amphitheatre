#!/usr/bin/env python3
"""
Stage 4 output builder. Reads stage4/_ctx.pkl (from stage4_amphitheater.py) and
emits the georeferenced deliverables. CRS EPSG:6494 (Michigan Central, intl ft).
"""
import json, math, pickle, csv
import numpy as np
import rasterio
from rasterio.transform import rowcol

ctx = pickle.load(open("stage4/_ctx.pkl", "rb"))
rows = ctx["rows"]; cap = ctx["cap"]; P = ctx["params"]
FX, FY = ctx["F"]
AX_AZ = P["AX_AZ"]; FACE_AZ = P["FACE_AZ"]; FAN = P["FAN_HALF"]
R_IN = P["R_INNER"]; R_OUT = P["R_OUTER"]; FOCUS = P["FOCUS_ELEV"]
CRS = {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::6494"}}

_ds = rasterio.open("dem/dem_design_1ft.tif"); _A = _ds.read(1); _nod = _ds.nodata; _T = _ds.transform
def elev(x, y):
    r, c = rowcol(_T, x, y)
    if 0 <= r < _A.shape[0] and 0 <= c < _A.shape[1]:
        v = _A[r, c]; return None if v == _nod else float(v)
    return None
def U(az):
    a = math.radians(az); return math.sin(a), math.cos(a)
def polar(R, az, ox=FX, oy=FY):
    e, n = U(az); return ox + e * R, oy + n * R
def arc(R, a0, a1, ox=FX, oy=FY, step=2.0):
    n = max(2, int(abs(a1 - a0) / step) + 1)
    return [polar(R, a, ox, oy) for a in np.linspace(a0, a1, n)]

def feat(geom_type, coords, props):
    return {"type": "Feature", "properties": props,
            "geometry": {"type": geom_type, "coordinates": coords}}
def fc(features):
    return {"type": "FeatureCollection", "crs": CRS, "features": features}

a0, a1 = AX_AZ - FAN, AX_AZ + FAN

# ============================================================ seating_rows.geojson
seat_feats = []
for r in rows:
    line = arc(r["R"], a0, a1)
    seat_feats.append(feat("LineString", [[round(x, 2), round(y, 2)] for x, y in line], {
        "row": r["row"], "radius_ft": round(r["R"], 1),
        "tread_elev_navd88": round(r["tread_prop"], 2),
        "terrain_elev_navd88": round(r["terr_med"], 2),
        "cut_fill_ft": r["cutfill"],
        "row_rise_ft": r["rise_prop"],
        "C_value_proposed_mm": None if r["C_prop"] is None else round(r["C_prop"] * 304.8, 0),
        "C_value_terrain_mm": None if r["C_terr"] is None else round(r["C_terr"] * 304.8, 0),
        "meets_C_proposed": bool(r["meets_prop"]),
        "meets_C_on_terrain": bool(r["meets_terr"]),
        "needs_regrade": bool(r["regrade"] or not r["meets_terr"]),
        "seats_compact_18in": r["seats_compact"],
        "seats_generous_22in": r["seats_generous"],
        "datum": "NAVD88 Geoid12A intl ft",
    }))
json.dump(fc(seat_feats), open("stage4/seating_rows.geojson", "w"), indent=1)

# ============================================================ stage_floor.geojson
SX, SY = U(AX_AZ); BX, BY = U(FACE_AZ)              # SE (to audience), NW (downslope)
CRX, CRY = U(AX_AZ + 90)                            # cross axis
stage_w, stage_d = 52.0, 26.0                        # ft
# stage front edge through F; body extends NW (downslope)
sc = []
for sgn_w in (-1, 1):
    sc.append((FX + CRX * sgn_w * stage_w / 2, FY + CRY * sgn_w * stage_w / 2))
back = [(FX + BX * stage_d + CRX * s * stage_w / 2, FY + BY * stage_d + CRY * s * stage_w / 2) for s in (1, -1)]
stage_poly = [sc[0], sc[1], back[0], back[1], sc[0]]

# event-floor / forecourt pad: pie slice from stage front out to inner seating arc
forecourt = [[FX, FY]] + arc(R_IN, a0, a1) + [[FX, FY]]

# treatment / wet cell: low pan NW of the stage (natural bowl bottom)
tc_origin = (FX + BX * 30, FY + BY * 30)
treat = arc(70, FACE_AZ - 70, FACE_AZ + 70, ox=tc_origin[0], oy=tc_origin[1])
treat = [tc_origin] + treat + [tc_origin]

# bay-view axis (focal point toward NW bay)
bayaxis = [[FX, FY], list(polar(260, FACE_AZ))]

stage_feats = [
    feat("Point", [round(FX, 2), round(FY, 2)],
         {"name": "focal_point_stage_front", "elev_navd88": FOCUS,
          "centerline_az_deg": AX_AZ, "audience_face_az_deg": FACE_AZ,
          "note": "sightline focus + plan center of seating arcs"}),
    feat("Polygon", [[[round(x, 2), round(y, 2)] for x, y in stage_poly]],
         {"name": "stage", "elev_navd88": FOCUS, "width_ft": stage_w, "depth_ft": stage_d}),
    feat("Polygon", [[[round(x, 2), round(y, 2)] for x, y in forecourt]],
         {"name": "event_floor_forecourt", "grade_elev_navd88": FOCUS,
          "note": "flat performance/orchestra + floor-level accessible seating; ~1.5-2.5 ft fill over pan"}),
    feat("Polygon", [[[round(x, 2), round(y, 2)] for x, y in treat]],
         {"name": "treatment_wet_cell", "bottom_navd88": 609.1, "design_pool_navd88": 611.3,
          "note": "natural bowl bottom kept as stormwater treatment cell / reflecting foreground (Stage 3)"}),
    feat("LineString", [[round(x, 2), round(y, 2)] for x, y in bayaxis],
         {"name": "bay_view_axis", "az_deg": FACE_AZ, "note": "NNW toward Little Traverse Bay / evening sun"}),
]
json.dump(fc(stage_feats), open("stage4/stage_floor.geojson", "w"), indent=1)

# ============================================================ ada_route.geojson
MAX_RUN = 0.0833
def slope_pct(p, q):
    e0, e1 = elev(*p), elev(*q)
    d = math.hypot(q[0] - p[0], q[1] - p[1])
    if None in (e0, e1) or d == 0: return None
    return (e1 - e0) / d

ada_feats = []

def switchback(start, start_elev, target_elev, travel_az, bench_w=16.0, label="", note=""):
    """Engineered switchback ramp. Each run <=2.5 ft rise at 8.33% (run_len=rise/0.0833),
    5 ft landings between runs, folded alternately across a bench_w-wide corridor while
    advancing down `travel_az`. Returns (feature, drop, runs, run_len)."""
    drop = start_elev - target_elev
    runs = max(2, int(math.ceil(abs(drop) / 2.5)))
    rise = drop / runs
    run_len = abs(rise) / MAX_RUN
    perp = U(travel_az + 90); along = U(travel_az)
    advance = bench_w * 0.5                          # down-corridor step per fold
    pts = [list(start)]; cur = list(start)
    for k in range(runs):
        side = 1 if k % 2 == 0 else -1
        cur = [cur[0] + perp[0]*side*run_len + along[0]*advance,
               cur[1] + perp[1]*side*run_len + along[1]*advance]
        pts.append(list(cur))
        if k < runs - 1:                            # 5 ft landing
            cur = [cur[0] + along[0]*5, cur[1] + along[1]*5]
            pts.append(list(cur))
    f = feat("LineString", [[round(x, 2), round(y, 2)] for x, y in pts], {
        "name": label, "type": "switchback_ramp",
        "rim_elev_navd88": round(start_elev, 2), "floor_elev_navd88": round(target_elev, 2),
        "total_drop_ft": round(drop, 1), "runs": runs, "run_len_ft": round(run_len, 1),
        "landings": runs - 1, "ramp_run_total_ft": round(run_len * runs, 0),
        "design_running_slope_pct": round(MAX_RUN * 100, 2), "cross_slope_target_pct": 2.0,
        "note": note})
    return f, drop, runs, run_len

# --- Route A (primary): NW bay/garden rim -> event floor. Lowest rim azimuth ~310.
rimA_az = 310.0
rimA = polar(140, rimA_az); eA = elev(*rimA) or 618.2
fA, dropA, runsA, _ = switchback(rimA, eA, FOCUS, travel_az=(rimA_az+180)%360,
    label="accessible_route_A_NW_bay_garden",
    note="primary accessible entry from the NW bay-side garden through the closed rim lip to the floor; lands on floor-level accessible seating")
ada_feats.append(fA)

# --- Route B: SE upper garden rim -> mid-bowl accessible cross-aisle (row 15)
buf_az = AX_AZ + FAN + 9
mid_aisle_R = rows[14]["R"]
topB = polar(R_OUT + 8, buf_az); eB = elev(*topB) or 643.0
midB_elev = rows[14]["tread_prop"]
fB, dropB, runsB, _ = switchback(topB, eB, midB_elev, travel_az=AX_AZ,
    label="accessible_route_B_SE_upper_garden",
    note="secondary accessible route from the SE upper garden rim to the mid-bowl level cross-aisle (row 15)")
ada_feats.append(fB)
segsA = None; drop = dropB; runs = runsB; run_len = abs(eB - midB_elev)/max(runsB,1)/MAX_RUN

# --- accessible cross-aisle (level bench at row 15) feeding dispersed WC spaces
xaisle = arc(mid_aisle_R, a0, a1)
ada_feats.append(feat("LineString", [[round(x, 2), round(y, 2)] for x, y in xaisle],
    {"name": "accessible_cross_aisle_row15", "elev_navd88": round(rows[14]["tread_prop"], 2),
     "type": "level_circulation", "note": "wheelchair-height level bench; ties Route B to dispersed seating"}))

# --- dispersed accessible (wheelchair) seating spaces: front floor + mid cross-aisle, L/C/R
wc = []
for label, R, az_off in [("front_L", R_IN + 3, -FAN*0.6), ("front_C", R_IN + 3, 0), ("front_R", R_IN + 3, FAN*0.6),
                          ("mid_L", mid_aisle_R + 1.5, -FAN*0.6), ("mid_C", mid_aisle_R + 1.5, 0),
                          ("mid_R", mid_aisle_R + 1.5, FAN*0.6)]:
    x, y = polar(R, AX_AZ + az_off)
    e = elev(x, y)
    wc.append(feat("Point", [round(x, 2), round(y, 2)],
        {"name": f"accessible_seating_{label}", "type": "wheelchair_space_pair",
         "grade_elev_navd88": None if e is None else round(e, 2),
         "note": "WC space + companion seat; dispersed per ADA 221.2"}))
ada_feats += wc
json.dump(fc(ada_feats), open("stage4/ada_route.geojson", "w"), indent=1)

# ============================================================ sightline_table.csv
with open("stage4/sightline_table.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["row", "radius_ft", "terrain_elev_navd88", "proposed_tread_elev_navd88",
                "row_rise_ft", "cut_fill_ft", "eye_elev_proposed",
                "C_value_terrain_mm", "C_value_proposed_mm", "C_target_mm",
                "meets_C_on_bare_terrain", "meets_C_proposed", "needs_regrade",
                "seats_compact_18in", "seats_generous_22in"])
    Ctgt = round(P["C_TARGET_FT"] * 304.8)
    for r in rows:
        w.writerow([r["row"], round(r["R"], 1), round(r["terr_med"], 2), round(r["tread_prop"], 2),
                    r["rise_prop"], r["cutfill"], round(r["eye_prop"], 2),
                    "" if r["C_terr"] is None else round(r["C_terr"]*304.8),
                    "" if r["C_prop"] is None else round(r["C_prop"]*304.8), Ctgt,
                    r["meets_terr"], r["meets_prop"], (r["regrade"] or not r["meets_terr"]),
                    r["seats_compact"], r["seats_generous"]])

print("wrote: seating_rows.geojson, stage_floor.geojson, ada_route.geojson, sightline_table.csv")
print(f"Route A (NW bay garden): drop {dropA:.1f} ft -> {runsA} runs @ 8.33%")
print(f"Route B (SE upper garden): drop {dropB:.1f} ft -> {runsB} runs @ 8.33%")
# stash a couple values for the writer
ctx["ada"] = dict(routeA_drop=round(float(dropA),1), routeA_runs=runsA,
                  routeB_drop=round(float(dropB),1), routeB_runs=runsB,
                  mid_aisle_R=round(float(mid_aisle_R),1))
pickle.dump(ctx, open("stage4/_ctx.pkl", "wb"))
