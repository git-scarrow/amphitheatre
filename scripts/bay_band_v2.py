#!/usr/bin/env python3
"""Bay-band v2 — effective silhouette per occluder set, far-shore band top,
canopy layer (leaf-off measurement + leaf-on assumption), r_n/r_m attribution.

Promotes the layered (effective-silhouette) computation from a sensitivity study
to the DEFINITION of the bay band (owner directive 2026-07-21):

  per ray, band BOTTOM = max occlusion angle over ALL opaque occluders of the
  included set; band TOP = far-shore waterline (T2), not the open-water horizon.

Occluder sets (cumulative, charged separately because not equally durable):
  S0  terrain only (bare-earth DEM)                         — the old baseline
  S1  + current flat stage + LiDAR-height-verified city     — durable reality
  S2  + canopy-today (leaf-off measurement / leaf-on assump) — mutable, 3rd-party

A corridor ray "sees water" when the far-shore-waterline band top sits ABOVE the
set's effective silhouette. clear% = fraction of corridor rays seeing water.
verdict: acceptable >=80 · marginal 40-79 · blocked <40 (unchanged convention).

r_n = first row/section with any non-empty band under S0 (terrain lets water through).
r_m = first row/section ACCEPTABLE under S2 (clear even through the canopy).
Binding occluder per row = the layer whose silhouette tops the band bottom.

Outputs (analysis/bay_view_obstruction/):
  canopy_silhouette.csv      per (band, az): canopy silhouette angle, both leaf states
  band_top_farshore.csv      per (band, az): d_shore, theta_top, dip, far skyline
  per_row_bands_by_set.csv   per row: clear% + binding occluder, S0/S1/S2off/S2on
  rn_rm_table.md             r_n / r_m per section per leaf state + attribution

EPSG:6494 · NAVD88 intl ft · planning-grade. Emits analysis only; adopts nothing.
"""
import csv
import json
import math
import os
import sys

import numpy as np
import rasterio
from shapely.geometry import shape, box, LineString

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import in_situ_common as C

REPO = C.REPO
OUT = os.path.join(REPO, "analysis", "bay_view_obstruction")
AZ_CORRIDOR = (C.BAY_VIEW_AZ - 12.0, C.BAY_VIEW_AZ + 12.0)   # 318-342
AZ_STEP = 2.0
RAY_STEP, RAY_MAX = 2.0, 760.0          # terrain/stage/city (design DEM margin)
CANOPY_STEP, CANOPY_MAX = 3.0, 1600.0   # canopy raster reaches ~3000 ft
R_EARTH_FT = 20.9e6
FT_PER_M = 1.0 / 0.3048
FORMAL_ROWS = C.FORMAL_ROWS
SECTION_ORDER = ("east", "bend", "south")
BAY_PLANE = C.BAY_PLANE
VERDICT = lambda p: ("acceptable" if p >= 80 else "marginal" if p >= 40 else "blocked")


def dip_deg(eye_above_water_ft):
    return math.degrees(math.sqrt(max(2.0 * eye_above_water_ft, 0.0) / R_EARTH_FT))


def azimuths():
    return np.arange(AZ_CORRIDOR[0], AZ_CORRIDOR[1] + 0.001, AZ_STEP)


class Engine:
    def __init__(self):
        # terrain DEM (S0) — same dem_design_1ft used by the committed baseline
        ds = rasterio.open(C.DEM_DESIGN)
        self.Zt = ds.read(1).astype(float)
        self.Zt[self.Zt == ds.nodata] = np.nan
        self.Tt = ds.transform; self.sht = self.Zt.shape

        # canopy rasters (S2) — top-of-canopy elevation, both leaf states
        self.can = {}
        for st, fn in (("leafoff", "canopy_top_leafoff_3ft.tif"),
                       ("leafon", "canopy_top_leafon_3ft.tif")):
            d = rasterio.open(os.path.join(OUT, fn))
            a = d.read(1).astype(float); a[a == d.nodata] = np.nan
            self.can[st] = (a, d.transform, a.shape)

        # far-shore DEM (T2 band top + far skyline)
        fd = rasterio.open(os.path.join(REPO, "data", "context", "dem", "farshore_3dep.tif"))
        fa = fd.read(1).astype(float)
        fa[fa == fd.nodata] = np.nan
        # far-shore DEM is NAVD88 *metres* -> feet
        self.Zf = fa * FT_PER_M
        self.Tf = fd.transform; self.shf = self.Zf.shape
        self.fbounds = fd.bounds

        # stage surfaces (S1) — flat deck, top 612.5 ft (no vertical shell)
        geom = json.load(open(os.path.join(REPO, "analysis", "scenarioE_civic", "geometry.geojson")))
        self.stage = []
        for f in geom["features"]:
            if f["properties"].get("role") == "stage_surface":
                self.stage.append((shape(f["geometry"]),
                                   float(f["properties"].get("elev_navd88_ft") or 612.5)))

        # city massing (S1) — LiDAR-height-verified buildings, bbox extrusion
        ms = json.load(open(os.path.join(OUT, "massing_suspects.json")))
        osm = {b["osm_id"]: b for b in
               json.load(open(os.path.join(OUT, "osm_near_focal.json")))["buildings"]}
        self.buildings = []
        for m in ms:
            o = osm.get(m["osm_id"])
            if not o or "bbox" not in o:
                continue
            be0, bn0, be1, bn1 = o["bbox"]
            self.buildings.append((box(C.CX + be0 * FT_PER_M, C.CY + bn0 * FT_PER_M,
                                       C.CX + be1 * FT_PER_M, C.CY + bn1 * FT_PER_M),
                                   float(m["top_ft"])))

        # treads
        treads = json.load(open(os.path.join(C.VEC_DIR, "terrace_treads.geojson")))["features"]
        self.treads = {(p["properties"]["row"], p["properties"]["section"]): p for p in treads}

    # ── samplers ────────────────────────────────────────────────────────────
    def _samp(self, Z, T, sh, x, y):
        c, r = ~T * (x, y)
        r = int(r); c = int(c)
        if 0 <= r < sh[0] and 0 <= c < sh[1]:
            v = Z[r, c]
            return float(v) if np.isfinite(v) else None
        return None

    def terrain_sil(self, ox, oy, e, n, eye):
        best, bd = -90.0, None
        d = 6.0
        while d <= RAY_MAX:
            z = self._samp(self.Zt, self.Tt, self.sht, ox + e * d, oy + n * d)
            if z is None:
                break
            a = math.degrees(math.atan2(z - eye, d))
            if a > best:
                best, bd = a, d
            d += RAY_STEP
        return best, bd

    def canopy_sil(self, ox, oy, e, n, eye, state):
        Z, T, sh = self.can[state]
        best, bd = -90.0, None
        d = 6.0
        while d <= CANOPY_MAX:
            z = self._samp(Z, T, sh, ox + e * d, oy + n * d)
            if z is not None:
                a = math.degrees(math.atan2(z - eye, d))
                if a > best:
                    best, bd = a, d
            d += CANOPY_STEP
        return best, bd

    def poly_sil(self, ox, oy, e, n, eye, polys):
        best, bd, hit = -90.0, None, None
        line = LineString([(ox + e * 6, oy + n * 6), (ox + e * RAY_MAX, oy + n * RAY_MAX)])
        for i, (poly, top) in enumerate(polys):
            inter = line.intersection(poly)
            if inter.is_empty:
                continue
            dists = []
            for g in getattr(inter, "geoms", [inter]):
                for cx, cy in (g.coords if hasattr(g, "coords") else []):
                    dists.append(math.hypot(cx - ox, cy - oy))
            if not dists:
                continue
            dn = min(dists)
            a = math.degrees(math.atan2(top - eye, dn))
            if a > best:
                best, bd, hit = a, dn, i
        return best, bd, hit

    def far_shore(self, ox, oy, e, n, eye):
        """Return (d_shore_ft, theta_top_deg, far_skyline_deg, uses_dip_fallback).

        Trace NNW; first far-shore DEM cell with elev>BAY_PLANE = waterline.
        theta_top = -(h/d_shore + d_shore/2R). far_skyline = max angle of the
        north-shore landform beyond the waterline."""
        h = eye - BAY_PLANE
        tangent = math.sqrt(2.0 * R_EARTH_FT * max(h, 0.0))
        d_shore = None
        sky = -90.0
        d = 200.0
        step = 20.0
        while d <= 40000.0:
            x = ox + e * d; y = oy + n * d
            if not (self.fbounds.left <= x <= self.fbounds.right
                    and self.fbounds.bottom <= y <= self.fbounds.top):
                d += step
                continue
            z = self._samp(self.Zf, self.Tf, self.shf, x, y)
            if z is not None and z > BAY_PLANE:
                if d_shore is None:
                    d_shore = d
                a = math.degrees(math.atan2(z - eye, d))
                if a > sky:
                    sky = a
            d += step
        if d_shore is None:
            # genuinely open water within DEM reach -> fall back to horizon dip
            return None, -dip_deg(h), None, True
        # theta_top = -(h/d_shore + d_shore/2R); atan() form is exact for the
        # depression term, curvature term d_shore/2R in radians -> deg.
        theta_top = -(math.degrees(math.atan(h / d_shore))
                      + math.degrees(d_shore / (2.0 * R_EARTH_FT)))
        return d_shore, theta_top, sky, (d_shore >= tangent)

    # ── per-band analysis ─────────────────────────────────────────────────────
    def samples(self, geom):
        g = shape(geom)
        polys = [g] if g.geom_type == "Polygon" else list(g.geoms)
        xy = np.vstack([np.array(p.exterior.coords) for p in polys])
        mu = xy.mean(axis=0); d = xy - mu
        _, _, vt = np.linalg.svd(d, full_matrices=False)
        t = d @ vt[0]; tmin, tmax = t.min(), t.max()
        out = []
        for frac in (0.25, 0.50, 0.75):
            p = mu + (tmin + frac * (tmax - tmin)) * vt[0]
            out.append((float(p[0]), float(p[1])))
        return out

    def analyse(self, row, section):
        feat = self.treads.get((row, section))
        if not feat:
            return None
        elev = feat["properties"]["tread_elev_navd88"]
        eye = elev + C.EYE_SEATED_FT
        pts = self.samples(feat["geometry"])
        rays = []
        for az in azimuths():
            e, n = C.U(float(az))
            # aggregate silhouettes over the 3 samples (mean of per-sample max)
            t_l, s_l, c_l, koff_l, kon_l, tt_l, sky_l, dsh_l, fb_l = ([] for _ in range(9))
            for (sx, sy) in pts:
                ts, _ = self.terrain_sil(sx, sy, e, n, eye)
                ss, _, _ = self.poly_sil(sx, sy, e, n, eye, self.stage)
                cs, _, _ = self.poly_sil(sx, sy, e, n, eye, self.buildings)
                koff, _ = self.canopy_sil(sx, sy, e, n, eye, "leafoff")
                kon, _ = self.canopy_sil(sx, sy, e, n, eye, "leafon")
                dsh, tt, sky, fb = self.far_shore(sx, sy, e, n, eye)
                t_l.append(ts); s_l.append(ss); c_l.append(cs)
                koff_l.append(koff); kon_l.append(kon)
                tt_l.append(tt); sky_l.append(sky if sky is not None else -90.0)
                dsh_l.append(dsh if dsh is not None else np.nan); fb_l.append(fb)
            terr = float(np.mean(t_l)); stg = float(np.mean(s_l)); cty = float(np.mean(c_l))
            koff = float(np.mean(koff_l)); kon = float(np.mean(kon_l))
            theta_top = float(np.mean(tt_l))
            far_sky = float(np.mean(sky_l))
            d_shore = float(np.nanmean(dsh_l)) if np.any(np.isfinite(dsh_l)) else None
            fallback = bool(np.any(fb_l))
            rays.append(dict(
                az=float(az), eye=eye, terrain=terr, stage=stg, city=cty,
                canopy_off=koff, canopy_on=kon, theta_top=theta_top,
                far_sky=far_sky, d_shore=d_shore, dip_fallback=fallback))
        return dict(section=section, row=row, tread=elev, eye=eye, rays=rays)


def sil_sets(r):
    """effective silhouette (band bottom) per occluder set for one ray dict."""
    S0 = r["terrain"]
    S1 = max(r["terrain"], r["stage"], r["city"])
    S2off = max(S1, r["canopy_off"])
    S2on = max(S1, r["canopy_on"])
    return {"S0": S0, "S1": S1, "S2off": S2off, "S2on": S2on}


def binding_layer(r, setname):
    """which occluder tops the band bottom under the given set."""
    cand = [("terrain", r["terrain"])]
    if setname in ("S1", "S2off", "S2on"):
        cand += [("stage", r["stage"]), ("city", r["city"])]
    if setname == "S2off":
        cand += [("canopy", r["canopy_off"])]
    if setname == "S2on":
        cand += [("canopy", r["canopy_on"])]
    return max(cand, key=lambda kv: kv[1])[0]


def main():
    eng = Engine()
    bands = []
    for section in SECTION_ORDER:
        for row in FORMAL_ROWS:
            b = eng.analyse(row, section)
            if b:
                bands.append(b)
    _write_canopy_csv(bands)
    _write_bandtop_csv(bands)
    per_row = _write_perrow_csv(bands)
    _write_rn_rm(per_row)
    # stash structured for downstream tasks (T4/T5 use the same engine module)
    json.dump({"bands": [{"section": b["section"], "row": b["row"], "eye": b["eye"],
                          "rays": b["rays"]} for b in bands]},
              open(os.path.join(OUT, "bay_band_v2_rays.json"), "w"))
    print(f"\nwrote canopy_silhouette.csv, band_top_farshore.csv, "
          f"per_row_bands_by_set.csv, rn_rm_table.md, bay_band_v2_rays.json")


def _write_canopy_csv(bands):
    rows = []
    for b in bands:
        for r in b["rays"]:
            rows.append(dict(
                band_key=f"{b['section']} r{b['row']}", section=b["section"],
                row=b["row"], az=r["az"], eye_elev_navd88=round(b["eye"], 2),
                canopy_sil_leafoff_deg=round(r["canopy_off"], 3) if r["canopy_off"] > -90 else None,
                canopy_sil_leafon_deg=round(r["canopy_on"], 3) if r["canopy_on"] > -90 else None,
                leaf_state_measured="leaf-off (2015-05-02)",
                leaf_on_is="assumption (crown-opacity closing; heights not raised)"))
    _csv(os.path.join(OUT, "canopy_silhouette.csv"), rows)


def _write_bandtop_csv(bands):
    rows = []
    for b in bands:
        for r in b["rays"]:
            rows.append(dict(
                band_key=f"{b['section']} r{b['row']}", section=b["section"], row=b["row"],
                az=r["az"], eye_elev_navd88=round(b["eye"], 2),
                d_shore_ft=round(r["d_shore"], 0) if r["d_shore"] else None,
                theta_top_deg=round(r["theta_top"], 4),
                horizon_dip_deg=round(-dip_deg(b["eye"] - BAY_PLANE), 4),
                far_skyline_deg=round(r["far_sky"], 3) if r["far_sky"] > -90 else None,
                uses_dip_fallback=r["dip_fallback"]))
    _csv(os.path.join(OUT, "band_top_farshore.csv"), rows)


def _row_clearpct(rays, setkey):
    n = len(rays); c = 0
    for r in rays:
        sil = sil_sets(r)[setkey]
        if r["theta_top"] > sil:
            c += 1
    return round(100.0 * c / n, 1)


def _row_binding(rays, setkey):
    """modal binding occluder among corridor rays (the layer topping the band)."""
    from collections import Counter
    setname = {"S0": "S0", "S1": "S1", "S2off": "S2off", "S2on": "S2on"}[setkey]
    cnt = Counter(binding_layer(r, setname) for r in rays)
    return cnt.most_common(1)[0][0]


def _write_perrow_csv(bands):
    out = []
    for b in bands:
        rays = b["rays"]
        rec = dict(
            band_key=f"{b['section']} r{b['row']}", section=b["section"], row=b["row"],
            eye_elev_navd88=round(b["eye"], 2),
            clear_S0=_row_clearpct(rays, "S0"), verdict_S0=VERDICT(_row_clearpct(rays, "S0")),
            clear_S1=_row_clearpct(rays, "S1"), verdict_S1=VERDICT(_row_clearpct(rays, "S1")),
            clear_S2_leafoff=_row_clearpct(rays, "S2off"),
            verdict_S2_leafoff=VERDICT(_row_clearpct(rays, "S2off")),
            clear_S2_leafon=_row_clearpct(rays, "S2on"),
            verdict_S2_leafon=VERDICT(_row_clearpct(rays, "S2on")),
            binding_S0=_row_binding(rays, "S0"), binding_S1=_row_binding(rays, "S1"),
            binding_S2_leafoff=_row_binding(rays, "S2off"),
            binding_S2_leafon=_row_binding(rays, "S2on"))
        out.append(rec)
    _csv(os.path.join(OUT, "per_row_bands_by_set.csv"), out)
    return out


def _write_rn_rm(per_row):
    by = {s: [r for r in per_row if r["section"] == s] for s in SECTION_ORDER}
    lines = ["# r_n / r_m table — bay-band v2 (effective silhouette, far-shore top)",
             "",
             "**Definitions (owner row-threshold model, resolved by attribution):**",
             "- **r_n** = first row/section with any non-empty band under **S0** "
             "(bare-earth terrain lets water through). Rows below r_n are rim-blocked.",
             "- **r_m** = first row/section **acceptable (>=80% clear)** under **S2** "
             "(water visible even through today's canopy). Rows r_n..r_m-1 are "
             "canopy-blocked; rows >= r_m are clear.",
             "- S2 is given in BOTH leaf states. **Leaf-off (2015-05-02) is the "
             "measurement**; leaf-on is a labeled crown-opacity assumption. Summer is "
             "the operating season, so r_m(leaf-on) is the season-relevant threshold.",
             "",
             "verdict: acceptable >=80% clear · marginal 40-79 · blocked <40",
             "",
             "| section | r_n (S0 non-empty) | r_m (S2 leaf-off accept) | r_m (S2 leaf-on accept) | binding r_n..r_m |",
             "|---|---|---|---|---|"]
    summary = {}
    for s in SECTION_ORDER:
        rows = sorted(by[s], key=lambda r: r["row"])
        r_n = next((r["row"] for r in rows if r["clear_S0"] > 0), None)
        r_m_off = next((r["row"] for r in rows if r["clear_S2_leafoff"] >= 80), None)
        r_m_on = next((r["row"] for r in rows if r["clear_S2_leafon"] >= 80), None)
        # binding occluder in the r_n..r_m transition zone (leaf-on)
        zone = [r for r in rows if r_n and r["row"] >= r_n
                and (r_m_on is None or r["row"] < r_m_on)]
        binds = sorted(set(r["binding_S2_leafon"] for r in zone)) or ["—"]
        summary[s] = dict(r_n=r_n, r_m_off=r_m_off, r_m_on=r_m_on, binding=binds)
        lines.append(f"| {s} | {r_n} | {r_m_off} | {r_m_on} | {', '.join(binds)} |")
    lines += ["",
              "## Per-row detail (clear% and binding occluder by set)",
              "",
              "| band | S0 clear/bind | S1 clear/bind | S2 leaf-off clear/bind | S2 leaf-on clear/bind |",
              "|---|---|---|---|---|"]
    for s in SECTION_ORDER:
        for r in sorted(by[s], key=lambda r: r["row"]):
            lines.append(
                f"| {r['band_key']} | {r['clear_S0']}/{r['binding_S0']} "
                f"| {r['clear_S1']}/{r['binding_S1']} "
                f"| {r['clear_S2_leafoff']}/{r['binding_S2_leafoff']} "
                f"| {r['clear_S2_leafon']}/{r['binding_S2_leafon']} |")
    open(os.path.join(OUT, "rn_rm_table.md"), "w").write("\n".join(lines) + "\n")
    print("\nr_n / r_m summary:")
    for s in SECTION_ORDER:
        d = summary[s]
        print(f"  {s:5s}  r_n={d['r_n']}  r_m(leaf-off)={d['r_m_off']}  "
              f"r_m(leaf-on)={d['r_m_on']}  binding[{','.join(d['binding'])}]")
    return summary


def _csv(path, rows):
    if not rows:
        return
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)


if __name__ == "__main__":
    main()
