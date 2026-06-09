#!/usr/bin/env python3
"""
Stage 5 — Finished-grade surface + cut/fill balance.
Petoskey Pit amphitheater / civic event garden, Bayfront Park, Petoskey MI.
Planning-grade. CRS EPSG:6494 (NAD83(2011)/Mich Central, intl ft); NAVD88 ft.

Method
------
The proposed finished grade is assembled from design "pads", each daylighted to
existing grade with a slope-limited tie-in. For any pixel:

    z_prop = T                              if inside a design zone (target T)
           = clip(z_exist, T_nn - s*d,      otherwise  (d = dist to nearest pad,
                          T_nn + s*d)                    T_nn = that pad's elev)

i.e. existing grade is kept wherever it already lies inside the daylight wedge
of the nearest pad; otherwise a cut (existing too high) or fill (existing too
low) side slope of grade s ties the pad out to grade. s = max side slope.

Pads (priority low->high so overlaps resolve sensibly):
  treatment_cell (609.1)  <  event_floor/stage (FLOOR knob)  <  seating terraces
  + east garden terraces (cut benches)  + ADA ramp corridors (8.33%).

Cut/fill volume = sum((z_prop - z_exist)) * 1 sqft / 27  -> cubic yards, over the
limit-of-disturbance (LOD = pixels where |z_prop - z_exist| > tolerance).

The event-floor elevation (and an east-garden cut-depth term) are swept to drive
net cut/fill toward balance and minimise off-site haul.
"""
import json, csv, math
import numpy as np
import rasterio
from rasterio.features import rasterize
from scipy.ndimage import distance_transform_edt
from shapely.geometry import shape, Point, LineString, Polygon
from shapely.ops import unary_union

ROOT = "/home/sam/projects/amphitheatre"
DEM = f"{ROOT}/dem/dem_design_1ft.tif"

# ---- design constants (all NAVD88 intl ft) ----
FLOOR_BAND = (612.0, 613.0)        # Stage 3 event-floor band
TREAT_BOTTOM = 609.1               # treatment-cell bottom (natural, keep)
SIDE_SLOPE = 1/3.0                 # 3:1 (H:V) = 0.333 ft/ft default embankment/cut tie-in
ADA_SLOPE = 0.0833                 # 8.33% accessible running slope
ADA_HALFWIDTH = 5.0                # ft, graded path half-width (10 ft corridor)
TOL = 0.05                         # ft, LOD threshold
D_MAX = 30.0                       # ft, max tie-in apron from a pad edge. Beyond
                                   # this, existing grade is kept; a tie-in that
                                   # would need to climb/cut farther (e.g. into the
                                   # steep SE wall) becomes a RETAINING WALL line
                                   # (geotech flag), not a cut slope. Caps the cut
                                   # height at ~s*D_MAX = 10 ft at 3:1.

# ---- load existing DEM ----
ds = rasterio.open(DEM)
Z = ds.read(1).astype("float64")
nodata = ds.nodata
if nodata is not None:
    Z[Z == nodata] = np.nan
T_AFF = ds.transform
NX, NY = ds.width, ds.height
px = T_AFF.a  # 1.0 ft

# pixel-center coordinates
cols = np.arange(NX); rows = np.arange(NY)
XC = T_AFF.c + (cols + 0.5) * T_AFF.a
YC = T_AFF.f + (rows + 0.5) * T_AFF.e
XX, YY = np.meshgrid(XC, YC)

# ---- geometry / context ----
ctx = __import__("pickle").load(open(f"{ROOT}/stage4/_ctx.pkl", "rb"))
F = ctx["F"]                       # focus (x,y)
P = ctx["params"]
AX_AZ = P["AX_AZ"]; FAN_HALF = P["FAN_HALF"]
R_IN, R_OUT = P["R_INNER"], P["R_OUTER"]
rows_tbl = ctx["rows"]
radii = np.array([r["R"] for r in rows_tbl])
treads = np.array([r["tread_prop"] for r in rows_tbl])

# radius / azimuth fields from focus (azimuth = compass bearing, deg)
dx = XX - F[0]; dy = YY - F[1]
RAD = np.hypot(dx, dy)
AZ = (np.degrees(np.arctan2(dx, dy))) % 360.0   # bearing from +Y(N), +X(E)

def az_in_fan(center, half):
    d = (AZ - center + 180) % 360 - 180
    return np.abs(d) <= half

# tread elevation as monotone interpolation of radius
def tread_of_r(r):
    return np.interp(r, radii, treads)

# ---- load vector zones ----
def load_fc(path):
    return json.load(open(path))["features"]

floor_feats = load_fc(f"{ROOT}/stage4/stage_floor.geojson")
basin_feats = load_fc(f"{ROOT}/basin_footprint.geojson")
ada_feats = load_fc(f"{ROOT}/stage4/ada_route.geojson")

def geom_by_name(feats, name):
    for f in feats:
        if f["properties"].get("name") == name:
            return shape(f["geometry"])
    return None

g_stage = geom_by_name(floor_feats, "stage")
g_forecourt = geom_by_name(floor_feats, "event_floor_forecourt")
g_treat = geom_by_name(floor_feats, "treatment_wet_cell")
g_basin = shape(basin_feats[0]["geometry"])

def rasterize_geom(geom):
    if geom is None:
        return np.zeros((NY, NX), bool)
    return rasterize([(geom, 1)], out_shape=(NY, NX), transform=T_AFF,
                     fill=0, all_touched=True).astype(bool)

m_stage = rasterize_geom(g_stage)
m_forecourt = rasterize_geom(g_forecourt)
m_treat = rasterize_geom(g_treat)
m_basin = rasterize_geom(g_basin)

# seating wedge mask (annulus within fan)
m_seat = az_in_fan(AX_AZ, FAN_HALF) & (RAD >= R_IN) & (RAD <= R_OUT)

# ---- east garden terraces (designed here; Stage 4 left schematic) ----
# Gentle east/ENE flank, outside the seating fan, rising ground east of the bowl.
# Benched into the slope (net cut) to (a) make usable garden platforms and
# (b) supply balancing fill. Bands by existing-elevation contour; each pad set
# to a cut elevation = band low + (1-cut_frac)*band_range above the floor.
GARDEN_AZ = (88.0, 122.0)          # ENE..SE-of-east, between bay flank and seating
GARDEN_R = (95.0, 215.0)
m_garden_zone = (az_in_fan(*[ (GARDEN_AZ[0]+GARDEN_AZ[1])/2,
                              (GARDEN_AZ[1]-GARDEN_AZ[0])/2 ]) &
                 (RAD >= GARDEN_R[0]) & (RAD <= GARDEN_R[1]) & np.isfinite(Z))
# exclude overlap with seating / basin
m_garden_zone &= ~m_seat & ~m_basin

N_GARDEN_BENCH = 5
def garden_target(cut_frac):
    """Return (mask, target-elev) for garden benches. cut_frac in [0,1]:
    0 = pads at band-low (max cut), 1 = pads at band-high (~no cut)."""
    zt = np.full((NY, NX), np.nan)
    zin = Z[m_garden_zone]
    if zin.size == 0:
        return zt
    lo, hi = np.nanpercentile(zin, 2), np.nanpercentile(zin, 98)
    edges = np.linspace(lo, hi, N_GARDEN_BENCH + 1)
    for i in range(N_GARDEN_BENCH):
        b0, b1 = edges[i], edges[i+1]
        bm = m_garden_zone & (Z >= b0) & (Z < (b1 if i < N_GARDEN_BENCH-1 else b1+1e6))
        pad = b0 + cut_frac * (b1 - b0)     # flat bench pad elevation
        zt[bm] = pad
    return zt

# ---- ADA ramp corridors (graded at 8.33% along each switchback line) ----
def ada_target():
    zt = np.full((NY, NX), np.nan)
    for f in ada_feats:
        pr = f["properties"]
        if pr.get("type") != "switchback_ramp":
            continue
        line = shape(f["geometry"])
        z_top = pr["rim_elev_navd88"]; z_bot = pr["floor_elev_navd88"]
        total_len = line.length
        if total_len == 0:
            continue
        # buffer corridor, grade by along-line fraction (rim->floor)
        buf = line.buffer(ADA_HALFWIDTH)
        bm = rasterize_geom(buf)
        # along-line parameter for each pixel: project nearest point
        idx = np.argwhere(bm)
        for (r_, c_) in idx:
            pt = Point(XC[c_], YC[r_])
            t = line.project(pt) / total_len
            zt[r_, c_] = z_top + t * (z_bot - z_top)
    return zt

m_ada_target = ada_target()
m_ada = np.isfinite(m_ada_target)

# ---- assemble proposed surface for a given config ----
def build_surface(floor_elev, garden_cut_frac, side_slope=SIDE_SLOPE,
                  return_targets=False):
    T = np.full((NY, NX), np.nan)        # painted design targets (priority low->high)

    # 1 treatment cell (lowest). ONLY the wet-cell pad is shaped to the bottom;
    # the rest of the closed bowl is left at NATURAL grade per Stage 3
    # ("leave bowl bottom ~609.1"), so we never excavate the whole basin.
    m_t = m_treat & ~m_stage & ~m_forecourt
    T[m_t] = TREAT_BOTTOM

    # 2 event floor + stage pad
    m_floor = m_stage | m_forecourt
    T[m_floor] = floor_elev

    # 3 east garden terraces
    gt = garden_target(garden_cut_frac)
    gmask = np.isfinite(gt)
    T[gmask] = gt[gmask]

    # 4 seating STEPPED terraces — each pixel takes its row's flat tread
    # elevation (nearest row by radius), matching Stage 4's fill-only terraces
    # (flat 3 ft treads, steep risers) rather than a continuous raked plane.
    seat_idx = np.argwhere(m_seat)
    rr = RAD[m_seat]
    nearest_row = np.abs(rr[:, None] - radii[None, :]).argmin(axis=1)
    T[m_seat] = treads[nearest_row]

    # 5 ADA corridors (override, accessible grade) where defined & finite
    amask = m_ada & np.isfinite(Z)
    T[amask] = m_ada_target[amask]

    in_zone = np.isfinite(T)

    # daylight: nearest painted pad elevation + distance (in ft)
    if in_zone.any():
        dist, (ir, ic) = distance_transform_edt(~in_zone, sampling=px,
                                                 return_indices=True)
        T_nn = T[ir, ic]
    else:
        dist = np.zeros_like(Z); T_nn = np.zeros_like(Z)

    s = side_slope
    daylight = np.clip(Z, T_nn - s * dist, T_nn + s * dist)
    # beyond the tie-in apron (D_MAX), keep existing grade untouched; the cut/fill
    # that would be needed there is replaced by a retaining wall (geotech flag).
    z_prop = np.where(in_zone, T, np.where(dist <= D_MAX, daylight, Z))
    z_prop = np.where(np.isfinite(Z), z_prop, np.nan)
    if return_targets:
        return z_prop, in_zone, dict(treat=m_t, floor=m_floor, garden=gmask,
                                     seat=m_seat, ada=amask)
    return z_prop, in_zone

# ---- volumes ----
CF_PER_CY = 27.0
def volumes(z_prop):
    d = z_prop - Z
    valid = np.isfinite(d)
    lod = valid & (np.abs(d) > TOL)
    cut = -d[lod & (d < 0)].sum()        # ft*sqft = cf
    fill = d[lod & (d > 0)].sum()
    return dict(cut_cy=cut/CF_PER_CY, fill_cy=fill/CF_PER_CY,
                net_cy=(fill-cut)/CF_PER_CY, lod_sqft=int(lod.sum()),
                lod_ac=lod.sum()/43560.0, d=d, lod=lod)

def zone_volumes(z_prop, zones):
    d = z_prop - Z
    out = {}
    for name, m in zones.items():
        mm = m & np.isfinite(d)
        cut = -d[mm & (d < 0)].sum()/CF_PER_CY
        fill = d[mm & (d > 0)].sum()/CF_PER_CY
        out[name] = (cut, fill, fill-cut)
    # tie-in / side-slope remainder = everything else in LOD
    inzones = np.zeros((NY,NX),bool)
    for m in zones.values(): inzones |= m
    rem = ~inzones & np.isfinite(d) & (np.abs(d)>TOL)
    cut = -d[rem & (d<0)].sum()/CF_PER_CY; fill = d[rem & (d>0)].sum()/CF_PER_CY
    out["tie_in_side_slopes"] = (cut, fill, fill-cut)
    return out

# ---- balance sweep ----
if __name__ == "__main__":
    print("Sweeping floor x garden_cut_frac for cut/fill balance...")
    floors = np.round(np.arange(FLOOR_BAND[0], FLOOR_BAND[1] + 1e-6, 0.25), 2)
    fracs = np.round(np.arange(0.0, 1.0 + 1e-6, 0.25), 2)
    sweep = []
    best = None
    for fl in floors:
        for fr in fracs:
            zp, _ = build_surface(fl, fr)
            v = volumes(zp)
            row = dict(floor=fl, garden_cut_frac=fr,
                       cut_cy=round(v["cut_cy"]), fill_cy=round(v["fill_cy"]),
                       net_cy=round(v["net_cy"]), lod_ac=round(v["lod_ac"],2))
            sweep.append(row)
            if best is None or abs(v["net_cy"]) < abs(best[2]["net_cy"]):
                best = (fl, fr, v, row)
            print(f"  floor={fl:.2f} gcut={fr:.2f}  cut={row['cut_cy']:>6} "
                  f"fill={row['fill_cy']:>6} net={row['net_cy']:>+6} CY "
                  f"LOD={row['lod_ac']}ac")

    bf, bfr, bv, brow = best
    print(f"\nBALANCED: floor={bf:.2f} ft, garden_cut_frac={bfr:.2f} -> "
          f"net {brow['net_cy']:+d} CY (cut {brow['cut_cy']}, fill {brow['fill_cy']})")

    # ---- write outputs at balanced config ----
    zp, in_zone, zones = build_surface(bf, bfr, return_targets=True)
    v = volumes(zp)
    zv = zone_volumes(zp, zones)

    prof = ds.profile.copy()
    prof.update(dtype="float32", count=1, nodata=-9999.0, compress="lzw")

    with rasterio.open(f"{ROOT}/stage5/grade_proposed.tif", "w", **prof) as dst:
        out = np.where(np.isfinite(zp), zp, -9999.0).astype("float32")
        dst.write(out, 1)

    cf = np.where(np.isfinite(zp), zp - Z, -9999.0).astype("float32")
    with rasterio.open(f"{ROOT}/stage5/cut_fill_map.tif", "w", **prof) as dst:
        dst.write(cf, 1)

    # earthwork_volumes.csv : per-zone + balanced summary + sweep
    with open(f"{ROOT}/stage5/earthwork_volumes.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["# Stage 5 earthwork — balanced config",
                    f"floor={bf} ft", f"garden_cut_frac={bfr}"])
        w.writerow([])
        w.writerow(["zone", "cut_cy", "fill_cy", "net_cy"])
        for name, (c, f_, n) in zv.items():
            w.writerow([name, round(c), round(f_), round(n)])
        w.writerow(["TOTAL", round(v["cut_cy"]), round(v["fill_cy"]),
                    round(v["net_cy"])])
        w.writerow([])
        w.writerow(["LOD_acres", round(v["lod_ac"], 3)])
        w.writerow(["interpretation",
                    "net>0 => import fill; net<0 => export/haul-off"])
        w.writerow([])
        w.writerow(["# balance sweep (floor x garden_cut_frac)"])
        w.writerow(["floor_ft", "garden_cut_frac", "cut_cy", "fill_cy",
                    "net_cy", "lod_ac"])
        for r in sweep:
            w.writerow([r["floor"], r["garden_cut_frac"], r["cut_cy"],
                        r["fill_cy"], r["net_cy"], r["lod_ac"]])

    # save balance for report
    json.dump(dict(floor=float(bf), garden_cut_frac=float(bfr),
                   cut_cy=round(v["cut_cy"]), fill_cy=round(v["fill_cy"]),
                   net_cy=round(v["net_cy"]), lod_ac=round(v["lod_ac"],3),
                   zone_volumes={k:[round(x) for x in val] for k,val in zv.items()}),
              open(f"{ROOT}/stage5/_balance.json","w"), indent=2)
    print("Wrote grade_proposed.tif, cut_fill_map.tif, earthwork_volumes.csv, _balance.json")
