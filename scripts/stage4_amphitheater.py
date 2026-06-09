#!/usr/bin/env python3
"""
Stage 4 - Partial-fan amphitheater geometry fit to dem_design_1ft.tif.

Planning-grade. All elevations NAVD88 (Geoid12A), international feet.
CRS: EPSG:6494 (NAD83(2011) / Michigan Central, intl ft).

Design intent (from project brief + Stage 1-3):
  - Event/stage floor = 612.5 ft (Stage 3 band 612.0-613.0); bowl bottom ~609.1
    stays as wet/treatment cell (the NW low pan becomes a reflecting foreground).
  - Stage / focal point at the NW (downslope) edge of the event floor.
  - Audience on the S/SE steep compact arc faces NW (az ~330, bay + evening sun).
  - Seating centerline az = 150 deg (SSE); fan spans the steep S-SE arc.

Outputs (stage4/):
  stage_floor.geojson, seating_rows.geojson, ada_route.geojson,
  sightline_table.csv, seat_count.md, plan_and_sections.png, README.md
"""
import json, math, csv
import numpy as np
import rasterio
from rasterio.transform import rowcol

# ----------------------------------------------------------------------------- inputs / constants
DEM = "dem/dem_design_1ft.tif"
CRS_EPSG = 6494

CX, CY = 19533067.7, 750799.2          # bowl centroid (map ft)
AX_AZ = 150.0                          # seating centerline azimuth (SSE), stage->audience
FACE_AZ = (AX_AZ + 180.0) % 360.0      # audience facing azimuth (330, NNW toward bay)
FOCUS_ELEV = 612.5                     # stage-front / sightline focus elevation (event floor)
STAGE_PAD_ELEV = 612.5

# focal point F = plan center of seating arcs AND sightline focus point.
# placed +15 ft SSE of bowl centroid -> stage sits at NW edge of the flat pan.
F_T = 15.0
EYE_HT = 3.94                          # seated eye height above tread (1.20 m)

R_INNER = 85.0                         # inner seating radius from F (ft) = slope toe
R_OUTER = 172.0                        # outer seating radius from F (ft)
TREAD = 3.00                           # row-to-row tread depth (ft) -> terrace spacing
FAN_HALF = 30.0                        # fan half-angle (deg); 60 deg total fan

C_TARGET_FT = 0.295                    # sightline C-value target (90 mm) eye-over-eye
REGRADE_CUTFILL_FT = 1.5               # |proposed - terrain| above this -> earthwork flag

SEAT_W_COMPACT = 1.50                  # 18 in
SEAT_W_GENEROUS = 1.83                 # 22 in
AISLE_FRAC = 0.18                      # fraction of arc lost to longitudinal aisles/voms

# --------------------------------------------------------------------------- DEM helpers
_ds = rasterio.open(DEM)
_A = _ds.read(1)
_nod = _ds.nodata
_T = _ds.transform

def elev(x, y):
    r, c = rowcol(_T, x, y)
    if 0 <= r < _A.shape[0] and 0 <= c < _A.shape[1]:
        v = _A[r, c]
        return None if (v == _nod or not np.isfinite(v)) else float(v)
    return None

def unit(az):
    a = math.radians(az)
    return math.sin(a), math.cos(a)            # (east, north) for map y-up

UX, UY = unit(AX_AZ)
FX, FY = CX + UX * F_T, CY + UY * F_T           # focal point map coords

def polar(radius, az):
    ex, ny = unit(az)
    return FX + ex * radius, FY + ny * radius

def terrain_along_row(radius, n=25):
    """median + range of terrain elevation sampled across the fan arc at a radius."""
    azs = np.linspace(AX_AZ - FAN_HALF, AX_AZ + FAN_HALF, n)
    vals = []
    for az in azs:
        x, y = polar(radius, az)
        e = elev(x, y)
        if e is not None:
            vals.append(e)
    if not vals:
        return None, None, None
    v = np.array(vals)
    return float(np.median(v)), float(v.min()), float(v.max())

# --------------------------------------------------------------------------- rows
radii = []
r = R_INNER
while r <= R_OUTER + 1e-6:
    radii.append(round(r, 2))
    r += TREAD
NROWS = len(radii)

rows = []
for i, R in enumerate(radii, start=1):
    tmed, tmin, tmax = terrain_along_row(R)
    rows.append(dict(row=i, R=R, terr_med=tmed, terr_min=tmin, terr_max=tmax))

# --------------------------------------------------------------------------- sightline design
# E = eye elevation - focus elevation; D = horizontal radius from focus.
# C_i = E_i*(D_{i-1}/D_i) - E_{i-1}   (clearance of rear sightline over front eye).
# Proposed grade = "ideal rake": each row raised just enough to hit C_TARGET,
# anchored at row 1; never set below natural terrain (no benefit to cutting lower).

# Row 1 tread: sit on natural terrain but >= focus floor (gradeable forecourt step).
row1_terr = rows[0]["terr_med"]
# anchor row 1 on natural grade (slope toe), but never below the event floor.
tread1 = max(row1_terr, FOCUS_ELEV + 0.5)
rows[0]["tread_prop"] = round(tread1, 2)

for i in range(1, NROWS):
    Dp = rows[i-1]["R"]; D = rows[i]["R"]
    Ep = (rows[i-1]["tread_prop"] + EYE_HT) - FOCUS_ELEV
    # required E_i so that C = C_TARGET exactly:
    Ei_req = (C_TARGET_FT + Ep) * (D / Dp)
    tread_req = FOCUS_ELEV + Ei_req - EYE_HT
    # never below natural terrain (avoid needless cut); raise to meet sightline
    rows[i]["tread_prop"] = max(tread_req, rows[i]["terr_med"])

# achieved C-values for (a) proposed grade and (b) terrain-following treads
def cval(D, E, Dp, Ep):
    return E * (Dp / D) - Ep

for i, row in enumerate(rows):
    D = row["R"]
    row["eye_prop"] = row["tread_prop"] + EYE_HT
    row["E_prop"] = row["eye_prop"] - FOCUS_ELEV
    row["eye_terr"] = row["terr_med"] + EYE_HT
    row["E_terr"] = row["eye_terr"] - FOCUS_ELEV
    if i == 0:
        row["C_prop"] = None; row["C_terr"] = None
        row["rise_prop"] = round(row["tread_prop"] - FOCUS_ELEV, 2)
    else:
        Dp = rows[i-1]["R"]
        row["C_prop"] = cval(D, row["E_prop"], Dp, rows[i-1]["E_prop"])
        row["C_terr"] = cval(D, row["E_terr"], Dp, rows[i-1]["E_terr"])
        row["rise_prop"] = round(row["tread_prop"] - rows[i-1]["tread_prop"], 2)
    row["cutfill"] = round(row["tread_prop"] - row["terr_med"], 2)
    row["regrade"] = abs(row["cutfill"]) > REGRADE_CUTFILL_FT
    row["meets_prop"] = (row["C_prop"] is None) or (row["C_prop"] >= C_TARGET_FT - 1e-6)
    row["meets_terr"] = (row["C_terr"] is None) or (row["C_terr"] >= C_TARGET_FT - 1e-6)

# --------------------------------------------------------------------------- seat counts
def seats_in_row(R, seat_w):
    arc_len = R * math.radians(2 * FAN_HALF)
    usable = arc_len * (1 - AISLE_FRAC)
    return max(0, int(usable // seat_w))

cap = {"compact": 0, "generous": 0}
for row in rows:
    row["seats_compact"] = seats_in_row(row["R"], SEAT_W_COMPACT)
    row["seats_generous"] = seats_in_row(row["R"], SEAT_W_GENEROUS)
    cap["compact"] += row["seats_compact"]
    cap["generous"] += row["seats_generous"]

print(f"Focal point F: ({FX:.1f}, {FY:.1f})  focus_elev={FOCUS_ELEV}")
print(f"rows={NROWS}  R {R_INNER}-{R_OUTER} ft  fan +/-{FAN_HALF} deg  tread {TREAD} ft")
print(f"natural toe elev (row1) = {row1_terr:.2f} ; outer terrain = {rows[-1]['terr_med']:.2f}")
print(f"proposed tread row1={rows[0]['tread_prop']:.2f}  rowN={rows[-1]['tread_prop']:.2f}")
print(f"C_target={C_TARGET_FT} ft ({C_TARGET_FT*304.8:.0f} mm)")
nfail_terr = sum(1 for r in rows if not r['meets_terr'])
nregrade = sum(1 for r in rows if r['regrade'])
print(f"rows failing C on bare terrain: {nfail_terr}/{NROWS}")
print(f"rows needing >|{REGRADE_CUTFILL_FT}| ft earthwork: {nregrade}/{NROWS}")
print(f"capacity compact(18in)={cap['compact']}  generous(22in)={cap['generous']}")

# stash for the writer stage
import pickle
ctx = dict(rows=rows, cap=cap, F=(FX,FY), radii=radii,
           params=dict(AX_AZ=AX_AZ, FACE_AZ=FACE_AZ, FAN_HALF=FAN_HALF,
                       R_INNER=R_INNER, R_OUTER=R_OUTER, TREAD=TREAD,
                       FOCUS_ELEV=FOCUS_ELEV, EYE_HT=EYE_HT, C_TARGET_FT=C_TARGET_FT,
                       SEAT_W_COMPACT=SEAT_W_COMPACT, SEAT_W_GENEROUS=SEAT_W_GENEROUS,
                       AISLE_FRAC=AISLE_FRAC, NROWS=NROWS, F_T=F_T, CX=CX, CY=CY))
pickle.dump(ctx, open("stage4/_ctx.pkl","wb"))
print("ctx saved -> stage4/_ctx.pkl")
