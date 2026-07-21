#!/usr/bin/env python3
"""T4 — Neighbor receptors + Reading-B neighbor-ceiling raster.

Reading B (owner-selected 2026-07-21, in these words):
    "no owner loses any bay view"  — NOT "no visible skyline change."
New construction may appear above the 618.04 rim from the streets (skyline change
is accepted and REPORTED, not gated); it may NOT intrude into any existing bay
BAND of the E / S / SE street receptors (their water view is inviolable).

Receptors: E Lake St (N), E Mitchell St (S), Petoskey St (E) frontages
(vectors_geojson/site_context.geojson street_edge lines), sampled every ~25 ft,
eyes at +5.0 ft (ground/storefront) and +17.0 ft (second story).

Occluders for neighbors: existing terrain (their sightline skims OVER the open
pit — the pit floor/near wall don't rise into it), LiDAR-verified W/NW buildings,
and canopy. The proposed stage is NOT in their existing silhouette (it is the new
mass being gated). Effective silhouette computed under:
  S1  terrain(existing DEM) + city buildings           — DURABLE
  S2  + canopy (leaf-on, operating season)              — CONTINGENT (3rd-party)

Ceiling raster over the stage / event-floor zone:
  ceiling(x,y) = min over {receptor e, corridor az a whose ray crosses (x,y),
                           where e has a NON-EMPTY water band at a}
                 of  z_eye(e) + dist(e,(x,y)) * tan(theta_sil_eff(e,a))
New mass may rise exactly to each protected receptor's existing band-bottom ray
and no further. Receptors with an empty band impose NO constraint (recorded).
The S1 ceiling is the durable one; S2-only headroom is contingent leeway.

Outputs: neighbor_receptors.geojson, neighbor_ceiling_S1.tif/.png,
         neighbor_ceiling_S2.tif/.png, neighbor_ceiling_summary.json
EPSG:6494 · NAVD88 intl ft · planning-grade. Analysis only; adopts nothing.
"""
import json
import math
import os
import sys

import numpy as np
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import shape, Point
from shapely.ops import unary_union

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import in_situ_common as C
import bay_band_v2 as V

REPO = C.REPO
OUT = os.path.join(REPO, "analysis", "bay_view_obstruction")
STREET_STEP = 25.0
EYES = {"ground_+5ft": 5.0, "second_story_+17ft": 17.0}
AZS = V.azimuths()
CELL = 5.0
PAD = 20.0
RIM = 618.04


# Larger EPT-derived bare-ground DTM (reaches ~1800 ft N, past dem_design's 801ft
# square) so a neighbor's foreground silhouette toward the bay is set by the true
# highest terrain point (far pit rim / US-31 embankment), not truncated to nearby
# steep-down samples. Skip nodata rather than break.
NBR_RAYMAX, NBR_STEP = 2000.0, 3.0
_DTM = {}


def _dtm(eng):
    if "z" not in _DTM:
        d = rasterio.open(os.path.join(OUT, "canopy_work", "dtm_ground_3ft.tif"))
        a = d.read(1).astype(float); a[a == d.nodata] = np.nan
        _DTM.update(z=a, t=d.transform, sh=a.shape)
    return _DTM


def nbr_terrain_sil(eng, ox, oy, e, n, eye):
    dtm = _dtm(eng)
    best = -90.0
    d = 10.0
    while d <= NBR_RAYMAX:
        z = eng._samp(dtm["z"], dtm["t"], dtm["sh"], ox + e * d, oy + n * d)
        if z is not None:
            a = math.degrees(math.atan2(z - eye, d))
            if a > best:
                best = a
        d += NBR_STEP
    return best


def ground_elev(eng, ctx, x, y):
    z = eng._samp(eng.Zt, eng.Tt, eng.sht, x, y)
    if z is None:
        dtm = _dtm(eng)
        z = eng._samp(dtm["z"], dtm["t"], dtm["sh"], x, y)
    if z is None:
        cz, ct, csh = ctx
        z = eng._samp(cz, ct, csh, x, y)
    return z


def neighbor_sil(eng, sx, sy, e, n, eye, canopy_state):
    """Effective silhouette (deg) for a neighbor at (sx,sy): terrain+city (S1)
    and +canopy (S2). Stage excluded (pit occludes nothing for neighbors)."""
    terr = nbr_terrain_sil(eng, sx, sy, e, n, eye)
    cty, _, _ = eng.poly_sil(sx, sy, e, n, eye, eng.buildings)
    s1 = max(terr, cty)
    can, _ = eng.canopy_sil(sx, sy, e, n, eye, canopy_state)
    s2 = max(s1, can)
    return s1, s2, dict(terrain=terr, city=cty, canopy=can)


def main():
    eng = V.Engine()
    ctxds = rasterio.open(os.path.join(REPO, "dem", "dem_context_2p5ft.tif"))
    ctxa = ctxds.read(1).astype(float); ctxa[ctxa == ctxds.nodata] = np.nan
    ctx = (ctxa, ctxds.transform, ctxa.shape)

    sc = json.load(open(os.path.join(C.VEC_DIR, "site_context.geojson")))
    frontages = [(f["properties"]["name"], shape(f["geometry"]))
                 for f in sc["features"] if f["properties"].get("kind") == "street_edge"]

    receptors = []      # each: dict with pos, eye, sils per az, clear%
    feats = []
    for name, line in frontages:
        L = line.length
        d = 0.0
        while d <= L + 1e-6:
            p = line.interpolate(d)
            g = ground_elev(eng, ctx, p.x, p.y)
            if g is None:
                d += STREET_STEP
                continue
            for eye_label, dz in EYES.items():
                eye = g + dz
                per_az = {}
                nonempty = {"S1": 0, "S2": 0}
                for az in AZS:
                    e, n = C.U(float(az))
                    s1, s2, comp = neighbor_sil(eng, p.x, p.y, e, n, eye, "leafon")
                    dsh, tt, sky, fb = eng.far_shore(p.x, p.y, e, n, eye)
                    per_az[float(az)] = dict(s1=s1, s2=s2, theta_top=tt)
                    if tt > s1:
                        nonempty["S1"] += 1
                    if tt > s2:
                        nonempty["S2"] += 1
                nA = len(AZS)
                rec = dict(name=name, x=p.x, y=p.y, ground=g, eye_label=eye_label,
                           eye=eye, per_az=per_az,
                           clear_S1=round(100 * nonempty["S1"] / nA, 1),
                           clear_S2=round(100 * nonempty["S2"] / nA, 1))
                receptors.append(rec)
                feats.append(dict(
                    type="Feature",
                    geometry=dict(type="Point", coordinates=[round(p.x, 2), round(p.y, 2)]),
                    properties=dict(
                        frontage=name, eye=eye_label, ground_elev_navd88=round(g, 2),
                        eye_elev_navd88=round(eye, 2),
                        clear_pct_S1=rec["clear_S1"], clear_pct_S2_leafon=rec["clear_S2"],
                        has_bay_band_S1=rec["clear_S1"] > 0,
                        has_bay_band_S2=rec["clear_S2"] > 0,
                        note=("empty band => imposes no ceiling constraint"
                              if rec["clear_S1"] == 0 else
                              "protected water view => contributes to neighbor ceiling"))))
            d += STREET_STEP

    json.dump(dict(type="FeatureCollection", crs=C.CRS6494, features=feats),
              open(os.path.join(OUT, "neighbor_receptors.geojson"), "w"), indent=1)

    # ── ceiling raster over the stage / event-floor zone ──────────────────────
    geom = json.load(open(os.path.join(REPO, "analysis", "scenarioE_civic", "geometry.geojson")))
    env = [shape(f["geometry"]) for f in geom["features"]
           if f["properties"].get("role") == "construction_envelope"][0]
    minx, miny, maxx, maxy = env.bounds
    minx -= PAD; miny -= PAD; maxx += PAD; maxy += PAD
    nx = int(math.ceil((maxx - minx) / CELL))
    ny = int(math.ceil((maxy - miny) / CELL))
    transform = from_origin(minx, maxy, CELL, CELL)
    half = V.AZ_STEP / 2.0

    def build_ceiling(setkey):
        ceil = np.full((ny, nx), np.nan)  # (rows=ny, cols=nx)
        binder = np.full((ny, nx), "", dtype=object)
        for j in range(ny):
            cy = maxy - (j + 0.5) * CELL
            for i in range(nx):
                cx = minx + (i + 0.5) * CELL
                best = np.inf; who = ""
                for rec in receptors:
                    dx = cx - rec["x"]; dy = cy - rec["y"]
                    dist = math.hypot(dx, dy)
                    if dist < 1.0:
                        continue
                    bearing = math.degrees(math.atan2(dx, dy)) % 360.0
                    # nearest corridor azimuth
                    if bearing < AZS[0] - half or bearing > AZS[-1] + half:
                        continue
                    az = min(AZS, key=lambda a: abs(a - bearing))
                    if abs(az - bearing) > half:
                        continue
                    pa = rec["per_az"][float(az)]
                    sil = pa["s1"] if setkey == "S1" else pa["s2"]
                    # skip no-data / no-occluder sentinel (ray left the DEM): a
                    # -90 sentinel is not a real band-bottom and yields tan(-90)
                    # garbage. Also skip absurdly steep looks (not a water-band
                    # bottom, just open downhill into the pit).
                    if sil <= -20.0:
                        continue
                    # only protected where a water band exists at this az
                    if pa["theta_top"] <= sil:
                        continue
                    z = rec["eye"] + dist * math.tan(math.radians(sil))
                    if z < best:
                        best = z; who = f"{rec['name'].split()[0]}|{rec['eye_label']}"
                if np.isfinite(best):
                    ceil[j, i] = best; binder[j, i] = who
        return ceil, binder

    stats = {}
    for setkey in ("S1", "S2"):
        ceil, binder = build_ceiling(setkey)
        prof = dict(driver="GTiff", height=ny, width=nx, count=1, dtype="float32",
                    crs="EPSG:6494", transform=transform, nodata=-9999.0,
                    compress="deflate")
        arr = np.where(np.isfinite(ceil), ceil, -9999.0).astype("float32")
        with rasterio.open(os.path.join(OUT, f"neighbor_ceiling_{setkey}.tif"), "w", **prof) as d:
            d.write(arr, 1)
        valid = np.isfinite(ceil)
        # ceiling over the stage footprint specifically
        stages = [shape(f["geometry"]) for f in geom["features"]
                  if f["properties"].get("role") == "stage_surface"]
        su = unary_union(stages)
        stage_vals = []
        for j in range(ny):
            cy = maxy - (j + 0.5) * CELL
            for i in range(nx):
                cx = minx + (i + 0.5) * CELL
                if valid[j, i] and su.contains(Point(cx, cy)):
                    stage_vals.append(float(ceil[j, i]))
        stats[setkey] = dict(
            cells_constrained=int(valid.sum()), cells_total=int(nx * ny),
            ceiling_min_navd88=round(float(np.nanmin(ceil)), 2) if valid.any() else None,
            ceiling_median_navd88=round(float(np.nanmedian(ceil[valid])), 2) if valid.any() else None,
            ceiling_over_stage_min=round(min(stage_vals), 2) if stage_vals else None,
            ceiling_over_stage_median=round(float(np.median(stage_vals)), 2) if stage_vals else None,
            headroom_over_deck_min_ft=round(min(stage_vals) - C.FOCUS_ELEV, 2) if stage_vals else None)
        _png(ceil, os.path.join(OUT, f"neighbor_ceiling_{setkey}.png"), setkey,
             minx, miny, maxx, maxy, su, C.FOCUS_ELEV)

    stats["note_reading_B"] = ('"no owner loses any bay view" (NOT "no visible '
                               'skyline change"); skyline change above rim 618.04 is '
                               'accepted+reported, not gated.')
    stats["S1_is"] = "durable (terrain+city); S2 headroom is contingent on 3rd-party canopy"
    n_prot_s1 = sum(1 for r in receptors if r["clear_S1"] > 0)
    n_prot_s2 = sum(1 for r in receptors if r["clear_S2"] > 0)
    stats["receptors_total"] = len(receptors)
    stats["receptors_with_water_band_S1"] = n_prot_s1
    stats["receptors_with_water_band_S2_leafon"] = n_prot_s2
    json.dump(stats, open(os.path.join(OUT, "neighbor_ceiling_summary.json"), "w"), indent=1)

    print(f"neighbor receptors: {len(receptors)} (S1 water-band {n_prot_s1}, "
          f"S2 leaf-on water-band {n_prot_s2})")
    for k in ("S1", "S2"):
        s = stats[k]
        print(f"  ceiling {k}: constrained {s['cells_constrained']}/{s['cells_total']} cells; "
              f"over-stage min {s['ceiling_over_stage_min']} median {s['ceiling_over_stage_median']} "
              f"NAVD88 ft (deck {C.FOCUS_ELEV}; headroom_min {s['headroom_over_deck_min_ft']} ft)")
    print("wrote neighbor_receptors.geojson, neighbor_ceiling_S1/S2.tif+png, "
          "neighbor_ceiling_summary.json")


def _png(ceil, path, setkey, minx, miny, maxx, maxy, stage, deck):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon as MplPoly
    fig, ax = plt.subplots(figsize=(6, 6))
    m = np.ma.masked_invalid(ceil)
    im = ax.imshow(m, extent=[minx, maxx, miny, maxy], origin="upper",
                   cmap="viridis")
    cb = fig.colorbar(im, ax=ax, shrink=0.8)
    cb.set_label("max permissible top elev (NAVD88 ft)")
    try:
        xs, ys = stage.exterior.xy
        ax.add_patch(MplPoly(np.c_[xs, ys], fill=False, edgecolor="red", lw=1.5,
                             label="stage footprint"))
    except Exception:
        for g in getattr(stage, "geoms", []):
            xs, ys = g.exterior.xy
            ax.add_patch(MplPoly(np.c_[xs, ys], fill=False, edgecolor="red", lw=1.5))
    ax.set_title(f"Neighbor-ceiling {setkey}  (deck={deck} ft)\n"
                 f"Reading B: protect existing bay bands", fontsize=9)
    ax.set_xlabel("EPSG:6494 X ft"); ax.set_ylabel("Y ft")
    ax.ticklabel_format(useOffset=False, style="plain")
    plt.tight_layout(); plt.savefig(path, dpi=110); plt.close()


if __name__ == "__main__":
    main()
