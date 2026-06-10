#!/usr/bin/env python3
"""Baseline visual-obstruction envelope for the three-section civic bowl.

For nine representative seated stations (3 families x front/mid/upper row
bands) this traces DEM sightlines across the NW viewing sector (az 280-360,
2-degree rays) and establishes the EXISTING terrain/rim silhouette as the
baseline blocked envelope:

  - terrain silhouette angle per ray (the skyline within the DEM)
  - bay visibility: the angular band between the silhouette and the sea
    horizon (Little Traverse Bay plane 579.45, earth-curvature dip applied)
  - treatment-cell foreground visibility band
  - share of the bay corridor already blocked by terrain per station

A stage element adds NEW obstruction only where it rises above this
envelope; anything seen against the rim/slope face hides inside it. The
stage-shape study imports `Envelope` to score candidates incrementally.

Caveats (stated, not hidden): bare-earth DEM only — the foreground tree
band (densest az 315-320) is a separate, known lever and is NOT part of the
baseline; terrain beyond the DEM margin (~400 ft) is assumed not to rise
above the in-DEM silhouette (the site falls toward the bay).

CLI: writes analysis/in_situ_normalization/obstruction_envelope.json
EPSG:6494 · NAVD88 intl ft · planning-grade.
"""
import json
import math
import os

import numpy as np

import in_situ_common as C

OUT = os.path.join(C.REPO, "analysis", "in_situ_normalization")
AZ_MIN, AZ_MAX, AZ_STEP = 280.0, 360.0, 2.0
CORRIDOR = (C.BAY_VIEW_AZ - 12.0, C.BAY_VIEW_AZ + 12.0)
RAY_STEP = 2.0
R_EARTH_FT = 20.9e6
CELL_SURF = 609.6          # nominal treatment-cell meadow surface
BANDS = {"front": 2, "mid": 8, "upper": 15}


def horizon_dip_deg(eye_above_water_ft):
    return math.degrees(math.sqrt(max(2.0 * eye_above_water_ft, 0.0) / R_EARTH_FT))


class Envelope:
    def __init__(self):
        import rasterio
        from shapely.geometry import shape

        if not os.path.exists(C.DEM_DESIGN):
            raise FileNotFoundError(
                "dem/dem_design_1ft.tif missing — the obstruction envelope "
                "needs the DEM (see dem/MISSING_DATA.md)")
        ds = rasterio.open(C.DEM_DESIGN)
        self.Z = ds.read(1).astype(float)
        self.Z[self.Z == ds.nodata] = np.nan
        self.T = ds.transform
        self.shape = self.Z.shape

        treads = json.load(open(os.path.join(C.VEC_DIR,
                                             "terrace_treads.geojson")))["features"]
        zones = {}
        for f in json.load(open(os.path.join(C.VEC_DIR,
                                             "bowl_zones.geojson")))["features"]:
            zones.setdefault(f["properties"]["zone"], []).append(f)
        self.cell = shape(zones["treatment_cell_landscape"][0]["geometry"])

        self.stations = []
        for sec in C.SECTIONS:
            for band, row in BANDS.items():
                f = next(t for t in treads if t["properties"]["section"] == sec
                         and t["properties"]["row"] == row)
                g = shape(f["geometry"]).centroid
                eye = f["properties"]["tread_elev_navd88"] + C.EYE_SEATED_FT
                self.stations.append(dict(
                    section=sec, band=band, row=row,
                    x=g.x, y=g.y, eye=eye,
                    seats=f["properties"]["seats_kept"]))
        self.azimuths = np.arange(AZ_MIN, AZ_MAX + 0.001, AZ_STEP)

    def elev(self, x, y):
        import rasterio
        r, c = rasterio.transform.rowcol(self.T, x, y)
        if 0 <= r < self.shape[0] and 0 <= c < self.shape[1]:
            v = self.Z[r, c]
            return None if not np.isfinite(v) else float(v)
        return None

    def trace(self, st, az):
        """One ray. Returns dict with the distances/angles needed for both
        the baseline and incremental candidate scoring."""
        ex, ey = C.U(az)
        ds_, angs = [], []
        d = 6.0
        while d <= 760.0:
            z = self.elev(st["x"] + ex * d, st["y"] + ey * d)
            if z is None:
                break
            ds_.append(d)
            angs.append(math.degrees(math.atan2(z - st["eye"], d)))
            d += RAY_STEP
        ds_ = np.array(ds_)
        angs = np.array(angs)
        if not len(ds_):
            return None
        sil = float(angs.max())
        d_sil = float(ds_[int(angs.argmax())])
        # suffix max: the silhouette of terrain BEYOND a given distance —
        # what a stage element at that distance can hide against
        suffix = np.maximum.accumulate(angs[::-1])[::-1]
        horizon = -horizon_dip_deg(st["eye"] - C.BAY_PLANE)
        bay_visible = horizon > sil
        bay_band = (sil, horizon) if bay_visible else None

        # treatment-cell crossing band (visible part above nearer terrain)
        from shapely.geometry import LineString
        ray_line = LineString([(st["x"] + ex * 6, st["y"] + ey * 6),
                               (st["x"] + ex * 760, st["y"] + ey * 760)])
        cell_band = None
        inter = ray_line.intersection(self.cell)
        if not inter.is_empty:
            dists = []
            geoms = getattr(inter, "geoms", [inter])
            for g in geoms:
                for cx, cy in g.coords:
                    dists.append(math.hypot(cx - st["x"], cy - st["y"]))
            d0, d1 = min(dists), max(dists)
            a_near = math.degrees(math.atan2(CELL_SURF - st["eye"], d0))
            a_far = math.degrees(math.atan2(CELL_SURF - st["eye"], d1))
            lo, hi = min(a_near, a_far), max(a_near, a_far)
            blocker = float(angs[ds_ < d0].max()) if (ds_ < d0).any() else -90.0
            if hi > blocker:
                cell_band = (max(lo, blocker), hi, d0, d1)
        return dict(az=az, ds=ds_, angs=angs, suffix=suffix, sil=sil,
                    d_sil=d_sil, horizon=horizon, bay_band=bay_band,
                    cell_band=cell_band)

    def suffix_at(self, ray, d):
        """Terrain silhouette beyond distance d along a traced ray."""
        i = int(np.searchsorted(ray["ds"], d))
        if i >= len(ray["suffix"]):
            return -90.0
        return float(ray["suffix"][i])

    def baseline(self):
        out = []
        for st in self.stations:
            rays = [self.trace(st, az) for az in self.azimuths]
            rays = [r for r in rays if r]
            corr = [r for r in rays if CORRIDOR[0] <= r["az"] <= CORRIDOR[1]]
            bay_vis = [r for r in corr if r["bay_band"]]
            cellr = [r for r in rays if r["cell_band"]]
            out.append(dict(
                section=st["section"], band=st["band"], row=st["row"],
                eye_elev_navd88=round(st["eye"], 2),
                station=[round(st["x"], 1), round(st["y"], 1)],
                silhouette_deg_mean=round(float(np.mean([r["sil"] for r in rays])), 2),
                silhouette_deg_range=[round(min(r["sil"] for r in rays), 2),
                                      round(max(r["sil"] for r in rays), 2)],
                bay_corridor_rays=len(corr),
                bay_visible_rays=len(bay_vis),
                bay_already_blocked_pct=round(
                    100.0 * (1 - len(bay_vis) / len(corr)), 1) if corr else None,
                bay_band_mean_deg=round(float(np.mean(
                    [r["bay_band"][1] - r["bay_band"][0] for r in bay_vis])), 2)
                if bay_vis else 0.0,
                cell_rays=len(cellr),
                cell_band_mean_deg=round(float(np.mean(
                    [r["cell_band"][1] - r["cell_band"][0] for r in cellr])), 2)
                if cellr else 0.0,
            ))
        return out


def main():
    env = Envelope()
    base = env.baseline()
    os.makedirs(OUT, exist_ok=True)
    payload = {
        "generated_by": "scripts/obstruction_envelope.py",
        "governing_scheme": C.GOVERNING_SCHEME,
        "method": f"DEM ray trace, az {AZ_MIN:.0f}-{AZ_MAX:.0f} step {AZ_STEP:.0f}, "
                  f"corridor {CORRIDOR[0]:.0f}-{CORRIDOR[1]:.0f}, seated eye "
                  f"+{C.EYE_SEATED_FT} ft, bay plane {C.BAY_PLANE}, "
                  "earth-curvature horizon dip applied",
        "caveats": [
            "bare-earth DEM baseline — foreground tree band (densest az "
            "315-320) is a separate lever, NOT included",
            "terrain beyond the DEM margin assumed below the in-DEM silhouette",
            "cell surface taken at 609.6 (meadow nominal)",
        ],
        "stations": base,
    }
    path = os.path.join(OUT, "obstruction_envelope.json")
    with open(path, "w") as fh:
        json.dump(payload, fh, indent=1)
    print(f"  wrote {os.path.relpath(path, C.REPO)}")
    print(f"  {'station':18s} {'sil°':>6s} {'bay blocked %':>14s} {'bay band°':>10s} {'cell band°':>10s}")
    for b in base:
        print(f"  {b['section']:>5s}/{b['band']:<10s} {b['silhouette_deg_mean']:6.2f} "
              f"{b['bay_already_blocked_pct']:14.1f} {b['bay_band_mean_deg']:10.2f} "
              f"{b['cell_band_mean_deg']:10.2f}")


if __name__ == "__main__":
    main()
