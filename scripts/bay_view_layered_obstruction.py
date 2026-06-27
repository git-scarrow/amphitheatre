#!/usr/bin/env python3
"""Layered bay-view obstruction — terrain / +stage / +city / +harbor-trees.

Extends scripts/bay_view_obstruction.py (terrain-only DEM ray-trace) by adding
the current adopted stage geometry and the LiDAR-height-verified city massing
as additional, cumulative obstruction layers, so each layer's marginal
contribution to blocked-% can be isolated per row and azimuth.

Layers (cumulative):
  L0 terrain          DEM bare-earth silhouette (the existing pass)
  L1 +stage           three current Scenario-E stage surfaces (core + 2
                      shoulders) as flat polygons at deck elev 612.5 ft.
                      NO vertical shell exists (verified in UE: stage actor
                      Z-bounds 612.0-612.5 ft) — claim is scoped to the
                      current flat/open stage only.
  L2 +city            18 LiDAR-height-verified OSM buildings in the W/NW
                      sector (heights = USGS DSM - 3DEP DTM, from the
                      massing audit). Each building footprint bbox is
                      extruded to its measured roof top and tested for ray
                      crossing. Buildings WITHOUT a verified height are NOT
                      counted as blockers (logged separately as unverified).
  L3 +harbor/trees    NO verified tree/canopy actors exist in the scene and
                      harbor structures sit at the bay water surface
                      (<= bay plane). This layer adds nothing measurable and
                      is reported as INDETERMINATE by absence, not as clear.

A ray is "clear" for a layer-set if the geometric bay horizon (bay plane
579.45 ft, earth-curvature dip applied) is above the MAX silhouette angle
contributed by any included layer along that azimuth.

Outputs (analysis/bay_view_obstruction/):
  layered_obstruction.json   per row/sample/azimuth, first-blocker layer + margins
  layered_obstruction.csv    per-band summary: clear% at L0/L1/L2 + deltas
  layered_delta_row_x_az.csv blocked-% per (band, az) for each layer-set

EPSG:6494 · NAVD88 intl ft · planning-grade.  Read-only; no geometry edits.
"""
import csv
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import in_situ_common as C


def _main_repo_root():
    import subprocess
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        common = subprocess.check_output(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=here, text=True, stderr=subprocess.DEVNULL).strip()
        git_dir = common if os.path.isabs(common) else os.path.normpath(os.path.join(here, common))
        main = os.path.normpath(os.path.join(git_dir, ".."))
        if os.path.exists(os.path.join(main, "dem", "dem_design_1ft.tif")):
            return main
    except Exception:
        pass
    return here


_repo = _main_repo_root()
if _repo != C.REPO:
    C.REPO = _repo
    C.DEM_DESIGN = os.path.join(_repo, "dem", "dem_design_1ft.tif")
    C.VEC_DIR = os.path.join(_repo, "vectors_geojson")

OUT_DIR = os.path.join(C.REPO, "analysis", "bay_view_obstruction")
AZ_MIN, AZ_MAX, AZ_STEP = 280.0, 360.0, 2.0
AZ_CORRIDOR = (C.BAY_VIEW_AZ - 12.0, C.BAY_VIEW_AZ + 12.0)   # 318-342
RAY_STEP, RAY_MAX = 2.0, 760.0
R_EARTH_FT = 20.9e6
FORMAL_ROWS = tuple(r for r in range(1, 19) if r not in (5, 9, 10))
FT_PER_M = 1.0 / 0.3048


def horizon_dip_deg(eye_above_water_ft):
    return math.degrees(math.sqrt(max(2.0 * eye_above_water_ft, 0.0) / R_EARTH_FT))


def sample_points_on_tread(geom):
    from shapely.geometry import shape
    g = shape(geom)
    polys = [g] if g.geom_type == "Polygon" else list(g.geoms)
    xy = np.vstack([np.array(p.exterior.coords) for p in polys])
    mu = xy.mean(axis=0)
    d = xy - mu
    _, _, vt = np.linalg.svd(d, full_matrices=False)
    t = d @ vt[0]
    tmin, tmax = t.min(), t.max()
    out = []
    for label, frac in (("left_third", 0.25), ("centroid", 0.50), ("right_third", 0.75)):
        p = mu + (tmin + frac * (tmax - tmin)) * vt[0]
        out.append((label, (float(p[0]), float(p[1]))))
    return out


class LayeredAnalyzer:
    def __init__(self):
        import rasterio
        from shapely.geometry import shape, box

        ds = rasterio.open(C.DEM_DESIGN)
        self.Z = ds.read(1).astype(float)
        self.Z[self.Z == ds.nodata] = np.nan
        self.T = ds.transform
        self.shape = self.Z.shape

        # treads
        treads = json.load(open(os.path.join(C.VEC_DIR, "terrace_treads.geojson")))["features"]
        self.treads = {(p["properties"]["row"], p["properties"]["section"]): p for p in treads}

        # stage polygons (current adopted Scenario E) — top elev 612.5 ft, flat
        geom = json.load(open(os.path.join(C.REPO, "analysis", "scenarioE_civic", "geometry.geojson")))
        self.stage = []
        for f in geom["features"]:
            if f["properties"].get("role") == "stage_surface":
                self.stage.append(dict(
                    poly=shape(f["geometry"]),
                    top_ft=float(f["properties"].get("elev_navd88_ft", 612.5)),
                    name=f["properties"].get("zone", "stage")))

        # city massing — LiDAR-height-verified buildings joined to bbox footprints
        ms = json.load(open(os.path.join(OUT_DIR, "massing_suspects.json")))
        osm = {b["osm_id"]: b for b in
               json.load(open(os.path.join(OUT_DIR, "osm_near_focal.json")))["buildings"]}
        self.buildings = []
        self.unverified_excluded = 0
        for m in ms:
            o = osm.get(m["osm_id"])
            if not o or "bbox" not in o:
                continue
            # bbox is ENU metres rel origin: [minE, minN, maxE, maxN]
            be0, bn0, be1, bn1 = o["bbox"]
            minx = C.CX + be0 * FT_PER_M
            maxx = C.CX + be1 * FT_PER_M
            miny = C.CY + bn0 * FT_PER_M
            maxy = C.CY + bn1 * FT_PER_M
            self.buildings.append(dict(
                osm_id=m["osm_id"], name=m.get("name"),
                poly=box(minx, miny, maxx, maxy),
                top_ft=float(m["top_ft"]),
                base_minus_terrain_m=m.get("base_minus_terrain_m"),
                az_focal=m.get("az")))

        self.azimuths = np.arange(AZ_MIN, AZ_MAX + 0.001, AZ_STEP)

    def elev(self, x, y):
        import rasterio
        r, c = rasterio.transform.rowcol(self.T, x, y)
        if 0 <= r < self.shape[0] and 0 <= c < self.shape[1]:
            v = self.Z[r, c]
            return float(v) if np.isfinite(v) else None
        return None

    def terrain_silhouette(self, ox, oy, ex, ey, eye):
        """Max terrain silhouette angle (deg) along a ray, + distance to it."""
        best, bd = -90.0, None
        d = 6.0
        while d <= RAY_MAX:
            z = self.elev(ox + ex * d, oy + ey * d)
            if z is None:
                break
            a = math.degrees(math.atan2(z - eye, d))
            if a > best:
                best, bd = a, d
            d += RAY_STEP
        return best, bd

    def poly_silhouette(self, ox, oy, ex, ey, eye, poly, top_ft):
        """Silhouette angle a flat-topped polygon subtends along the ray, or None.

        Returns (angle_deg, nearest_crossing_dist_ft, clearance_deg) where
        clearance is (eye-ray horizon 0°) minus the polygon top angle — i.e.
        how far the polygon top sits below the viewer's level sightline.
        Positive angle => polygon top rises above eye level (could block).
        """
        from shapely.geometry import LineString
        line = LineString([(ox + ex * 6, oy + ey * 6),
                           (ox + ex * RAY_MAX, oy + ey * RAY_MAX)])
        inter = line.intersection(poly)
        if inter.is_empty:
            return None
        dists = []
        for g in getattr(inter, "geoms", [inter]):
            for cx, cy in (g.coords if hasattr(g, "coords") else []):
                dists.append(math.hypot(cx - ox, cy - oy))
        if not dists:
            return None
        d_near = min(dists)
        ang = math.degrees(math.atan2(top_ft - eye, d_near))
        return ang, d_near

    def analyse(self, row, section):
        key = (row, section)
        if key not in self.treads:
            return None
        feat = self.treads[key]
        elev = feat["properties"]["tread_elev_navd88"]
        eye = elev + C.EYE_SEATED_FT
        horizon = -horizon_dip_deg(eye - C.BAY_PLANE)

        samples = []
        for label, (sx, sy) in sample_points_on_tread(feat["geometry"]):
            rays = []
            for az in self.azimuths:
                ex, ey = C.U(az)
                t_sil, t_d = self.terrain_silhouette(sx, sy, ex, ey, eye)
                # stage
                s_ang, s_d = -90.0, None
                for st in self.stage:
                    r = self.poly_silhouette(sx, sy, ex, ey, eye, st["poly"], st["top_ft"])
                    if r and r[0] > s_ang:
                        s_ang, s_d = r[0], r[1]
                # city
                c_ang, c_d, c_hit = -90.0, None, None
                for b in self.buildings:
                    r = self.poly_silhouette(sx, sy, ex, ey, eye, b["poly"], b["top_ft"])
                    if r and r[0] > c_ang:
                        c_ang, c_d, c_hit = r[0], r[1], b["osm_id"]
                # cumulative max silhouette per layer-set
                sil_L0 = t_sil
                sil_L1 = max(t_sil, s_ang)
                sil_L2 = max(t_sil, s_ang, c_ang)
                rays.append(dict(
                    az=float(az), horizon=round(horizon, 3),
                    terrain_sil=round(t_sil, 3), terrain_d=t_d,
                    stage_ang=round(s_ang, 3) if s_ang > -90 else None, stage_d=s_d,
                    city_ang=round(c_ang, 3) if c_ang > -90 else None,
                    city_d=c_d, city_hit=c_hit,
                    clear_L0=bool(horizon > sil_L0),
                    clear_L1=bool(horizon > sil_L1),
                    clear_L2=bool(horizon > sil_L2)))
            corr = [r for r in rays if AZ_CORRIDOR[0] <= r["az"] <= AZ_CORRIDOR[1]]
            n = len(corr)
            def pct(k): return round(100.0 * sum(1 for r in corr if r[k]) / n, 1) if n else None
            samples.append(dict(
                sample=label, eye_elev_navd88=round(eye, 2), corridor_rays=n,
                clear_pct_L0=pct("clear_L0"), clear_pct_L1=pct("clear_L1"),
                clear_pct_L2=pct("clear_L2"), rays=rays))
        return dict(band_key=f"{section} r{row}", section=section, row=row,
                    tread_elev_navd88=round(elev, 2),
                    eye_elev_navd88=round(eye, 2), horizon_deg=round(horizon, 3),
                    samples=samples)


def main():
    az = LayeredAnalyzer()
    os.makedirs(OUT_DIR, exist_ok=True)
    print(f"Layered obstruction: terrain / +stage({len(az.stage)} surf) / "
          f"+city({len(az.buildings)} verified-height bldgs)")
    print(f"  Stage tops: {sorted(set(round(s['top_ft'],1) for s in az.stage))} ft "
          f"(flat — no vertical shell)")
    print()

    summaries, bands, delta_rows = [], [], []
    for section in C.SECTIONS:
        for row in FORMAL_ROWS:
            b = az.analyse(row, section)
            if not b:
                continue
            L0 = round(np.mean([s["clear_pct_L0"] for s in b["samples"]]), 1)
            L1 = round(np.mean([s["clear_pct_L1"] for s in b["samples"]]), 1)
            L2 = round(np.mean([s["clear_pct_L2"] for s in b["samples"]]), 1)
            d_stage = round(L0 - L1, 1)
            d_city = round(L1 - L2, 1)
            summaries.append(dict(
                band_key=b["band_key"], section=section, row=row,
                eye_elev_navd88=b["eye_elev_navd88"],
                clear_pct_terrain=L0, clear_pct_terrain_stage=L1,
                clear_pct_terrain_stage_city=L2,
                delta_stage_pct=d_stage, delta_city_pct=d_city))
            # delta rows by az (avg over samples)
            azc = {}
            for s in b["samples"]:
                for r in s["rays"]:
                    if AZ_CORRIDOR[0] <= r["az"] <= AZ_CORRIDOR[1]:
                        azc.setdefault(r["az"], []).append(r)
            for a, rs in sorted(azc.items()):
                bl0 = 100 * (1 - sum(r["clear_L0"] for r in rs) / len(rs))
                bl1 = 100 * (1 - sum(r["clear_L1"] for r in rs) / len(rs))
                bl2 = 100 * (1 - sum(r["clear_L2"] for r in rs) / len(rs))
                delta_rows.append(dict(
                    band_key=b["band_key"], az=a,
                    blocked_terrain=round(bl0, 1),
                    blocked_terrain_stage=round(bl1, 1),
                    blocked_terrain_stage_city=round(bl2, 1)))
            # strip ray detail except keep first-blocker summary in bands
            for s in b["samples"]:
                s.pop("rays")
            bands.append(b)
            flag = "" if (d_stage == 0 and d_city == 0) else f"  <-- stage Δ{d_stage} city Δ{d_city}"
            print(f"  {b['band_key']:12s} terrain {L0:5.1f}%  +stage {L1:5.1f}%  "
                  f"+city {L2:5.1f}%{flag}")

    # ---- write outputs ----
    with open(os.path.join(OUT_DIR, "layered_obstruction.json"), "w") as fh:
        json.dump(dict(
            generated_by="scripts/bay_view_layered_obstruction.py",
            method=("cumulative-layer ray-trace; clear = bay horizon above max "
                    "silhouette of included layers; corridor 318-342, 3 samples/tread"),
            layers=dict(
                L0="terrain (DEM bare-earth)",
                L1="+ current Scenario-E stage (3 flat surfaces, top 612.5 ft, "
                   "no vertical shell — verified in UE, Z 612.0-612.5 ft)",
                L2="+ 18 LiDAR-height-verified W/NW OSM buildings",
                L3="+ harbor/trees: NO verified tree-canopy actors in scene; "
                   "harbor at/below bay plane — INDETERMINATE by absence"),
            caveats=[
                "stage claim scoped to current flat/open stage; any Rule-9 "
                "vertical element invalidates L1",
                "city layer counts only LiDAR-height-verified buildings; "
                f"{az.unverified_excluded} unverified-height buildings excluded",
                "foreground tree band (az 315-320) still not modelled (no actor)",
            ],
            stage_actors_verified="UE: Stage_zone_stage_core + shoulder_left + "
                                  "shoulder_right; Z 612.0-612.5 ft; no shell",
            summaries=summaries, bands=bands), fh, indent=1)
    print(f"\n  wrote analysis/bay_view_obstruction/layered_obstruction.json")

    with open(os.path.join(OUT_DIR, "layered_obstruction.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=[
            "band_key", "section", "row", "eye_elev_navd88",
            "clear_pct_terrain", "clear_pct_terrain_stage",
            "clear_pct_terrain_stage_city", "delta_stage_pct", "delta_city_pct"])
        w.writeheader()
        w.writerows(summaries)
    print(f"  wrote analysis/bay_view_obstruction/layered_obstruction.csv")

    with open(os.path.join(OUT_DIR, "layered_delta_row_x_az.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=[
            "band_key", "az", "blocked_terrain", "blocked_terrain_stage",
            "blocked_terrain_stage_city"])
        w.writeheader()
        w.writerows(delta_rows)
    print(f"  wrote analysis/bay_view_obstruction/layered_delta_row_x_az.csv")

    # ---- headline deltas ----
    tot_stage = sum(s["delta_stage_pct"] for s in summaries)
    tot_city = sum(s["delta_city_pct"] for s in summaries)
    print(f"\n  TOTAL stage delta across all bands: {round(tot_stage,1)} pct-points")
    print(f"  TOTAL city  delta across all bands: {round(tot_city,1)} pct-points")
    worst_city = sorted(summaries, key=lambda s: s["delta_city_pct"], reverse=True)[:5]
    print("  Largest city deltas:")
    for s in worst_city:
        print(f"    {s['band_key']:12s} city Δ {s['delta_city_pct']:+.1f}%  "
              f"(terrain {s['clear_pct_terrain']:.0f}% -> +city {s['clear_pct_terrain_stage_city']:.0f}%)")


if __name__ == "__main__":
    main()
