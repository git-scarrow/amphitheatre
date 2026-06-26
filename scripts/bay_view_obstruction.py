#!/usr/bin/env python3
"""Per-row bay-view obstruction analysis for the Petoskey Civic Bowl.

Extends obstruction_envelope.py from 9 sample stations to every formal row
across all three sections (east / bend / south, rows 1-4, 6-8, 11-18).

For each tread band three eye-point samples are traced:
  centroid   — mid-seat, mid-tread
  left_third — leftward quarter of the tread chord
  right_third — rightward quarter of the tread chord

Rays are fired at 2° steps across az 280-360°.  The "bay corridor" is
318-342° (±12° of BAY_VIEW_AZ 330°).  For each ray the terrain silhouette
is extracted from the DEM (bare-earth) and compared to the geometric horizon
at the bay water plane 579.45 NAVD88 ft with earth-curvature dip applied.

Obstruction classification (applied per ray):
  terrain_rim   — DEM silhouette angle > horizon angle (bay hidden behind rim)
  clear         — horizon visible above DEM silhouette

Geometry that is NOT modelled here (stated caveats):
  stage_massing  — stage is at az ~150° (SSE), bay is at 330° (NNW); the
                   stage is geometrically behind the viewer when looking at
                   the bay.  blocks_bay_view=False confirmed in scene canon.
  foreground_trees — densest at az 315-320, documented separate lever (not
                   in bare-earth DEM)
  city_massing  — no OSM building heights available in GIS layer; city
                  buildings are far (>400 ft) and likely below the rim angle
  harbor_waterfront — harbor elements are AT the bay surface; they could
                   marginally reduce the effective water plane but are not
                   modelled here

Outputs (all under analysis/bay_view_obstruction/):
  per_row_obstruction.json     full per-band, per-sample detail
  per_row_obstruction.csv      one row per tread band (aggregated over samples)
  heatmap_row_x_az.csv         blocked% per (band_key × azimuth) for heatmap
  summary.md                   verdict by row band with obstruction source named

CLI: python scripts/bay_view_obstruction.py
EPSG:6494 · NAVD88 intl ft · planning-grade.
"""
import csv
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import in_situ_common as C

# If running from a git worktree, data files (DEM, vectors) live in the main
# working tree, not the worktree checkout.  Override C.REPO to the main tree.
def _main_repo_root():
    """Return the main working tree root even when run from a git worktree."""
    import subprocess
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        common = subprocess.check_output(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=here, text=True, stderr=subprocess.DEVNULL
        ).strip()
        if os.path.isabs(common):
            git_dir = common
        else:
            git_dir = os.path.normpath(os.path.join(here, common))
        main = os.path.normpath(os.path.join(git_dir, ".."))
        dem_candidate = os.path.join(main, "dem", "dem_design_1ft.tif")
        if os.path.exists(dem_candidate):
            return main
    except Exception:
        pass
    return here

_repo = _main_repo_root()
if _repo != C.REPO:
    C.REPO = _repo
    C.DEM_DESIGN = os.path.join(_repo, "dem", "dem_design_1ft.tif")
    C.VEC_DIR = os.path.join(_repo, "vectors_geojson")

OUT_DIR = None   # set after REPO override in __main__
AZ_MIN, AZ_MAX, AZ_STEP = 280.0, 360.0, 2.0
AZ_CORRIDOR = (C.BAY_VIEW_AZ - 12.0, C.BAY_VIEW_AZ + 12.0)   # 318-342
RAY_STEP = 2.0        # ft along ray
RAY_MAX = 760.0       # ft (DEM margin)
R_EARTH_FT = 20.9e6

# Rows included in the formal bowl (excludes promenade=5 and aisle=9,10)
FORMAL_ROWS = tuple(r for r in range(1, 19) if r not in (5, 9, 10))


def horizon_dip_deg(eye_above_water_ft: float) -> float:
    return math.degrees(math.sqrt(max(2.0 * eye_above_water_ft, 0.0) / R_EARTH_FT))


def sample_points_on_tread(geom, n=3):
    """Return n=3 (x,y) samples along the principal axis of a tread polygon.

    The three samples are at t = 0.25, 0.50, 0.75 along the PCA chord so
    they represent the left-third, centroid, and right-third of the seat arc.
    """
    from shapely.geometry import shape

    g = shape(geom)
    polys = [g] if g.geom_type == "Polygon" else list(g.geoms)
    xy = np.vstack([np.array(p.exterior.coords) for p in polys])
    # PCA axis
    mu = xy.mean(axis=0)
    d = xy - mu
    _, _, vt = np.linalg.svd(d, full_matrices=False)
    t = d @ vt[0]
    tmin, tmax = t.min(), t.max()
    pts = []
    labels = ["left_third", "centroid", "right_third"]
    for frac in (0.25, 0.50, 0.75):
        tf = tmin + frac * (tmax - tmin)
        pt_2d = mu + tf * vt[0]
        pts.append((float(pt_2d[0]), float(pt_2d[1])))
    return list(zip(labels, pts))


class ObstructionAnalyzer:
    def __init__(self):
        import rasterio
        if not os.path.exists(C.DEM_DESIGN):
            raise FileNotFoundError(
                "dem/dem_design_1ft.tif missing — run DEM fetch first")
        ds = rasterio.open(C.DEM_DESIGN)
        self.Z = ds.read(1).astype(float)
        self.Z[self.Z == ds.nodata] = np.nan
        self.T = ds.transform
        self.shape = self.Z.shape

        # Load all tread bands from terrace_treads.geojson
        treads = json.load(open(os.path.join(C.VEC_DIR, "terrace_treads.geojson")))["features"]
        # Index by (row, section)
        self.treads = {}
        for f in treads:
            p = f["properties"]
            self.treads[(p["row"], p["section"])] = f

        self.azimuths = np.arange(AZ_MIN, AZ_MAX + 0.001, AZ_STEP)
        self.corridor_mask = (
            (self.azimuths >= AZ_CORRIDOR[0]) & (self.azimuths <= AZ_CORRIDOR[1])
        )

    def elev(self, x: float, y: float):
        import rasterio
        r, c = rasterio.transform.rowcol(self.T, x, y)
        if 0 <= r < self.shape[0] and 0 <= c < self.shape[1]:
            v = self.Z[r, c]
            return float(v) if np.isfinite(v) else None
        return None

    def trace_ray(self, ex: float, ey: float, ox: float, oy: float, eye_elev: float):
        """Trace one ray from (ox,oy) in direction (ex,ey).

        Returns dict with:
          sil        — terrain silhouette angle (deg above horiz)
          d_sil      — distance (ft) to max silhouette
          horizon    — geometric bay horizon (deg, negative = dip below horiz)
          bay_clear  — bool: horizon is above silhouette
          obstructor — 'terrain_rim' | 'clear'
        """
        angs = []
        ds_ = []
        d = 6.0
        while d <= RAY_MAX:
            z = self.elev(ox + ex * d, oy + ey * d)
            if z is None:
                break
            angs.append(math.degrees(math.atan2(z - eye_elev, d)))
            ds_.append(d)
            d += RAY_STEP
        if not angs:
            return None
        angs_arr = np.array(angs)
        ds_arr = np.array(ds_)
        sil = float(angs_arr.max())
        d_sil = float(ds_arr[int(angs_arr.argmax())])
        horizon = -horizon_dip_deg(eye_elev - C.BAY_PLANE)
        bay_clear = horizon > sil
        return dict(
            sil=round(sil, 3),
            d_sil=round(d_sil, 1),
            horizon=round(horizon, 3),
            bay_clear=bay_clear,
            obstructor="clear" if bay_clear else "terrain_rim",
        )

    def analyse_tread(self, row: int, section: str):
        """Full obstruction analysis for one (row, section) tread band.

        Returns list of per-sample results, each covering all azimuths.
        """
        key = (row, section)
        if key not in self.treads:
            return None
        feat = self.treads[key]
        props = feat["properties"]
        elev = props["tread_elev_navd88"]
        eye = elev + C.EYE_SEATED_FT

        samples = sample_points_on_tread(feat["geometry"])
        results = []
        for label, (sx, sy) in samples:
            az_rays = []
            for az in self.azimuths:
                ex, ey = C.U(az)
                r = self.trace_ray(ex, ey, sx, sy, eye)
                if r:
                    az_rays.append(dict(az=float(az), **r))
                else:
                    az_rays.append(dict(az=float(az), sil=None, d_sil=None,
                                        horizon=None, bay_clear=None,
                                        obstructor="no_data"))
            # Corridor stats
            corr = [r for r in az_rays if AZ_CORRIDOR[0] <= r["az"] <= AZ_CORRIDOR[1]]
            n_corr = len(corr)
            n_clear = sum(1 for r in corr if r["bay_clear"])
            n_terrain = sum(1 for r in corr if r["obstructor"] == "terrain_rim")
            blocked_pct = round(100.0 * n_terrain / n_corr, 1) if n_corr else None
            clear_pct = round(100.0 * n_clear / n_corr, 1) if n_corr else None
            sils = [r["sil"] for r in corr if r["sil"] is not None]
            results.append(dict(
                sample=label,
                x=round(sx, 1),
                y=round(sy, 1),
                eye_elev_navd88=round(eye, 2),
                corridor_rays=n_corr,
                clear_rays=n_clear,
                terrain_blocked_rays=n_terrain,
                clear_pct=clear_pct,
                terrain_blocked_pct=blocked_pct,
                sil_mean_deg=round(float(np.mean(sils)), 3) if sils else None,
                sil_max_deg=round(float(np.max(sils)), 3) if sils else None,
                horizon_deg=round(-horizon_dip_deg(eye - C.BAY_PLANE), 3),
                az_detail=az_rays,
            ))
        return dict(
            band_key=f"{section} r{row}",
            section=section,
            row=row,
            tread_elev_navd88=round(elev, 2),
            sees_bay_elevation_threshold=bool(eye > 618.5),
            samples=results,
        )

    def aggregate_band(self, band_result):
        """Aggregate sample results into a single per-band summary."""
        if band_result is None:
            return None
        samples = band_result["samples"]
        all_clear = [s["clear_pct"] for s in samples if s["clear_pct"] is not None]
        all_blocked = [s["terrain_blocked_pct"] for s in samples if s["terrain_blocked_pct"] is not None]
        all_sil = [s["sil_mean_deg"] for s in samples if s["sil_mean_deg"] is not None]
        horizon = samples[0]["horizon_deg"] if samples else None

        clear_mean = round(float(np.mean(all_clear)), 1) if all_clear else None
        blocked_mean = round(float(np.mean(all_blocked)), 1) if all_blocked else None

        if clear_mean is None:
            verdict = "no_data"
        elif clear_mean >= 80:
            verdict = "acceptable"
        elif clear_mean >= 40:
            verdict = "marginal"
        else:
            verdict = "blocked"

        return dict(
            band_key=band_result["band_key"],
            section=band_result["section"],
            row=band_result["row"],
            tread_elev_navd88=band_result["tread_elev_navd88"],
            eye_elev_navd88=round(band_result["tread_elev_navd88"] + C.EYE_SEATED_FT, 2),
            sees_bay_elevation_threshold=band_result["sees_bay_elevation_threshold"],
            horizon_deg=horizon,
            sil_mean_deg_corridor=round(float(np.mean(all_sil)), 3) if all_sil else None,
            clear_pct_mean=clear_mean,
            terrain_blocked_pct_mean=blocked_mean,
            verdict=verdict,
            obstruction_source="terrain_rim" if blocked_mean and blocked_mean > 10 else "none",
        )

    def heatmap_row_x_az(self, band_result):
        """Return list of {band_key, az, blocked_pct} averaged over samples."""
        if band_result is None:
            return []
        key = band_result["band_key"]
        # Gather per-az clear status across samples
        az_status = {}  # az -> list of bay_clear bools
        for samp in band_result["samples"]:
            for ray in samp["az_detail"]:
                az = ray["az"]
                if ray["bay_clear"] is not None:
                    az_status.setdefault(az, []).append(ray["bay_clear"])
        rows = []
        for az in sorted(az_status):
                clears = az_status[az]
                blocked_pct = round(100.0 * (1 - sum(clears) / len(clears)), 1)
                rows.append(dict(band_key=key, az=az, blocked_pct=blocked_pct))
        return rows


def main():
    global OUT_DIR
    OUT_DIR = os.path.join(C.REPO, "analysis", "bay_view_obstruction")
    analyzer = ObstructionAnalyzer()
    os.makedirs(OUT_DIR, exist_ok=True)

    print(f"Running per-row bay-view obstruction analysis...")
    print(f"  Sections: {C.SECTIONS}")
    print(f"  Formal rows: {FORMAL_ROWS}")
    print(f"  Samples per tread: 3 (left_third / centroid / right_third)")
    print(f"  Bay corridor: {AZ_CORRIDOR[0]:.0f}-{AZ_CORRIDOR[1]:.0f}°  (±12° of {C.BAY_VIEW_AZ}°)")
    print()

    all_bands = []
    all_summaries = []
    all_heatmap = []

    for section in C.SECTIONS:
        for row in FORMAL_ROWS:
            band = analyzer.analyse_tread(row, section)
            if band is None:
                print(f"  SKIP {section} r{row} — tread not found")
                continue
            summary = analyzer.aggregate_band(band)
            hm = analyzer.heatmap_row_x_az(band)
            # Drop az_detail from JSON to keep it manageable (include separately)
            for s in band["samples"]:
                s.pop("az_detail")
            all_bands.append(band)
            all_summaries.append(summary)
            all_heatmap.extend(hm)

            v = summary["verdict"]
            icon = "✓" if v == "acceptable" else ("~" if v == "marginal" else "✗")
            print(f"  {icon} {summary['band_key']:14s}  eye {summary['eye_elev_navd88']:7.2f}ft  "
                  f"clear {summary['clear_pct_mean']:5.1f}%  "
                  f"terrain_blocked {summary['terrain_blocked_pct_mean']:5.1f}%  [{v}]")

    # ── write per_row_obstruction.json ────────────────────────────────────────
    json_path = os.path.join(OUT_DIR, "per_row_obstruction.json")
    payload = {
        "generated_by": "scripts/bay_view_obstruction.py",
        "governing_scheme": C.GOVERNING_SCHEME,
        "method": (
            f"DEM bare-earth ray-trace, az {AZ_MIN:.0f}-{AZ_MAX:.0f} step {AZ_STEP:.0f}°, "
            f"corridor {AZ_CORRIDOR[0]:.0f}-{AZ_CORRIDOR[1]:.0f}°, "
            f"3 samples/tread (left_third/centroid/right_third), "
            f"eye +{C.EYE_SEATED_FT} ft, bay plane {C.BAY_PLANE} NAVD88 ft, "
            "earth-curvature horizon dip applied"
        ),
        "caveats": [
            "bare-earth DEM — foreground tree band (az 315-320) is a known separate lever, NOT modelled",
            "stage_massing: stage faces az 150°; bay is at 330°; stage is behind the viewer "
            "when looking toward the bay — blocks_bay_view=False confirmed in scene canon",
            "city_massing: no OSM building heights in GIS layer; buildings far (>400 ft) "
            "and likely below DEM rim angle",
            "harbor_waterfront: harbor elements sit at the bay water surface; "
            "they do not intercept the NNW sightlines from the seating bowl",
            "terrain beyond DEM margin (~760 ft) assumed to not rise above in-DEM silhouette",
            "cross-aisle rows 9-10 and promenade row 5 omitted (not formal seating bands)",
        ],
        "verdicts": {
            "acceptable": "≥80% of bay-corridor rays clear",
            "marginal": "40-79% of bay-corridor rays clear",
            "blocked": "<40% of bay-corridor rays clear",
        },
        "summaries": all_summaries,
        "bands": all_bands,
    }
    with open(json_path, "w") as fh:
        json.dump(payload, fh, indent=1)
    print(f"\n  wrote {os.path.relpath(json_path, C.REPO)}")

    # ── write per_row_obstruction.csv ─────────────────────────────────────────
    csv_path = os.path.join(OUT_DIR, "per_row_obstruction.csv")
    csv_fields = [
        "band_key", "section", "row", "tread_elev_navd88", "eye_elev_navd88",
        "sees_bay_elevation_threshold", "horizon_deg", "sil_mean_deg_corridor",
        "clear_pct_mean", "terrain_blocked_pct_mean", "verdict", "obstruction_source",
    ]
    with open(csv_path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=csv_fields)
        w.writeheader()
        for s in all_summaries:
            w.writerow({k: s[k] for k in csv_fields})
    print(f"  wrote {os.path.relpath(csv_path, C.REPO)}")

    # ── write heatmap_row_x_az.csv ────────────────────────────────────────────
    hm_path = os.path.join(OUT_DIR, "heatmap_row_x_az.csv")
    with open(hm_path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["band_key", "az", "blocked_pct"])
        w.writeheader()
        w.writerows(all_heatmap)
    print(f"  wrote {os.path.relpath(hm_path, C.REPO)}")

    # ── write summary.md ──────────────────────────────────────────────────────
    _write_summary(all_summaries, os.path.join(OUT_DIR, "summary.md"))
    print(f"  wrote {os.path.relpath(os.path.join(OUT_DIR, 'summary.md'), C.REPO)}")


def _write_summary(summaries, path):
    lines = [
        "# Bay-view obstruction — per-row summary",
        "",
        "Generated by `scripts/bay_view_obstruction.py`.",
        f"Method: DEM bare-earth ray-trace, az 318-342° (bay corridor ±12° of 330°),",
        "3 eye-point samples per tread (left-third / centroid / right-third).",
        "",
        "**Verdicts:** acceptable ≥80% clear · marginal 40-79% · blocked <40%",
        "",
        "**Obstruction source:** `terrain_rim` (DEM) only. Stage massing: geometrically",
        "excluded (stage faces az 150°, bay at 330° — behind the viewer).",
        "Foreground trees, city massing, harbor elements: not modelled (see caveats).",
        "",
        "---",
        "",
        "## Results by section",
        "",
    ]

    for section in ("east", "bend", "south"):
        sec_rows = [s for s in summaries if s["section"] == section]
        lines.append(f"### Section: {section.upper()}")
        lines.append("")
        lines.append(
            f"| row | tread ft | eye ft | horizon° | sil° | clear% | blocked% | verdict |"
        )
        lines.append("|-----|----------|--------|----------|------|--------|----------|---------|")
        for s in sec_rows:
            icon = {"acceptable": "✓", "marginal": "~", "blocked": "✗"}.get(s["verdict"], "?")
            lines.append(
                f"| {s['row']:2d} | {s['tread_elev_navd88']:8.2f} | {s['eye_elev_navd88']:6.2f} "
                f"| {s['horizon_deg']:8.3f} | {s['sil_mean_deg_corridor']:4.2f} "
                f"| {s['clear_pct_mean']:6.1f} | {s['terrain_blocked_pct_mean']:8.1f} "
                f"| {icon} {s['verdict']} |"
            )
        lines.append("")

    # Band-level verdict
    blocked_rows = sorted(
        set(s["band_key"] for s in summaries if s["verdict"] == "blocked"),
    )
    marginal_rows = sorted(
        set(s["band_key"] for s in summaries if s["verdict"] == "marginal"),
    )
    acceptable_rows = sorted(
        set(s["band_key"] for s in summaries if s["verdict"] == "acceptable"),
    )

    # Find first acceptable row per section
    first_acceptable = {}
    for section in ("east", "bend", "south"):
        sec_rows = [s for s in summaries if s["section"] == section]
        for s in sec_rows:
            if s["verdict"] == "acceptable":
                first_acceptable[section] = s["row"]
                break

    lines += [
        "---",
        "",
        "## Overall verdict",
        "",
        f"**Blocked bands** ({len(blocked_rows)}): "
        + (", ".join(blocked_rows) if blocked_rows else "none"),
        "",
        f"**Marginal bands** ({len(marginal_rows)}): "
        + (", ".join(marginal_rows) if marginal_rows else "none"),
        "",
        f"**Acceptable bands** ({len(acceptable_rows)}): "
        + (", ".join(acceptable_rows) if acceptable_rows else "none"),
        "",
        "**First acceptable row by section:**",
    ]
    for sec, r in sorted(first_acceptable.items()):
        lines.append(f"  - {sec}: row {r}")

    lines += [
        "",
        "## Caveats",
        "",
        "- Bare-earth DEM only: foreground tree band (az 315-320) is a",
        "  documented separate lever that would add additional obstruction in",
        "  the marginal/transition zone — not modelled here.",
        "- Stage: confirmed non-obstructor (faces az 150°; bay at 330°).",
        "- City massing and harbor elements: not in GIS layer; not modelled.",
        "- The elevation threshold `sees_bay = (eye > 618.5 ft)` used in",
        "  sightline_table.csv is a floor filter, NOT a ray-trace result.",
        "  This analysis supersedes it for bay obstruction questions.",
        "",
    ]

    with open(path, "w") as fh:
        fh.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
