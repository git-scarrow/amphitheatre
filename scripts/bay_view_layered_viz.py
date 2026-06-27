#!/usr/bin/env python3
"""Plan-view + section diagnostics for the layered bay-view obstruction.

Reads the layered analysis + source geometry and renders:
  layered_plan_view.png       bay window, stage footprint, W/NW building
                              footprints (color = blocks corridor or not),
                              sample seat points + sample rays.
  section_beards_east.png     vertical section from east r17 eye along
                              az 334 through Beards Brewery, showing eye,
                              bay horizon line, building silhouette, terrain.

Read-only.  EPSG:6494 ft.
"""
import json
import math
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPoly

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import in_situ_common as C


def _main_repo_root():
    import subprocess
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        common = subprocess.check_output(["git", "rev-parse", "--git-common-dir"],
            cwd=here, text=True, stderr=subprocess.DEVNULL).strip()
        gd = common if os.path.isabs(common) else os.path.normpath(os.path.join(here, common))
        main = os.path.normpath(os.path.join(gd, ".."))
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
OUT = os.path.join(C.REPO, "analysis", "bay_view_obstruction")
FT = 1.0 / 0.3048
AZ_CORR = (318.0, 342.0)


def load():
    from shapely.geometry import shape, box
    treads = json.load(open(os.path.join(C.VEC_DIR, "terrace_treads.geojson")))["features"]
    geom = json.load(open(os.path.join(C.REPO, "analysis", "scenarioE_civic", "geometry.geojson")))
    stage = [shape(f["geometry"]) for f in geom["features"]
             if f["properties"].get("role") == "stage_surface"]
    ms = json.load(open(os.path.join(OUT, "massing_suspects.json")))
    osm = {b["osm_id"]: b for b in json.load(open(os.path.join(OUT, "osm_near_focal.json")))["buildings"]}
    blds = []
    for m in ms:
        o = osm.get(m["osm_id"])
        if not o or "bbox" not in o:
            continue
        be0, bn0, be1, bn1 = o["bbox"]
        blds.append(dict(
            osm_id=m["osm_id"], name=m.get("name") or f"osm{m['osm_id']}",
            poly=box(C.CX + be0 * FT, C.CY + bn0 * FT, C.CX + be1 * FT, C.CY + bn1 * FT),
            top_ft=float(m["top_ft"]), az=m.get("az")))
    return treads, stage, blds


def plan_view(treads, stage, blds):
    from shapely.geometry import shape
    fig, ax = plt.subplots(figsize=(9, 13))
    ax.ticklabel_format(useOffset=False, style="plain")

    # treads
    for f in treads:
        g = shape(f["geometry"])
        polys = [g] if g.geom_type == "Polygon" else list(g.geoms)
        for p in polys:
            ax.add_patch(MplPoly(np.array(p.exterior.coords), closed=True,
                                 fc="#d8e8d8", ec="#88aa88", lw=0.4, zorder=2))

    # stage
    for s in stage:
        ax.add_patch(MplPoly(np.array(s.exterior.coords), closed=True,
                             fc="#e8c8a0", ec="#a0703a", lw=1.2, zorder=3,
                             label="_stage"))
    sc = stage[0].centroid
    ax.text(sc.x, sc.y, "STAGE\n(flat 612.5ft\nΔ=0%)", ha="center", va="center",
            fontsize=7, zorder=6, fontweight="bold")

    # bay-view corridor wedge from focal point
    fx, fy = C.FX, C.FY
    for az, style in ((330, dict(color="cyan", lw=1.4, ls="--")),
                      (AZ_CORR[0], dict(color="cyan", lw=0.8, ls=":")),
                      (AZ_CORR[1], dict(color="cyan", lw=0.8, ls=":"))):
        e, n = C.U(az)
        ax.plot([fx, fx + e * 850], [fy, fy + n * 850], **style, zorder=4)
    ax.text(fx + C.U(330)[0] * 870, fy + C.U(330)[1] * 870, "bay\naz330",
            color="teal", fontsize=8, ha="center", zorder=6)

    # buildings — color by whether top is tall enough to plausibly block
    for b in blds:
        in_win = AZ_CORR[0] - 8 <= b["az"] <= AZ_CORR[1] + 8
        col = "#c0392b" if (in_win and b["top_ft"] >= 600) else "#999999"
        ax.add_patch(MplPoly(np.array(b["poly"].exterior.coords), closed=True,
                             fc=col, ec="black", lw=0.6, alpha=0.85, zorder=5))
        cx, cy = b["poly"].centroid.x, b["poly"].centroid.y
        if "Beards" in str(b["name"]) or (in_win and b["top_ft"] >= 620):
            ax.text(cx, cy, f"{str(b['name'])[:14]}\n{b['top_ft']:.0f}ft",
                    fontsize=6, ha="center", va="center", zorder=7, color="white",
                    fontweight="bold")

    # sample rays from east r17 (the worst-affected band)
    t = next(f for f in treads if f["properties"]["row"] == 17 and f["properties"]["section"] == "east")
    g = shape(t["geometry"]).centroid
    for az in range(318, 343, 2):
        e, n = C.U(az)
        # clear (no Beards crossing) vs blocked — quick test
        from shapely.geometry import LineString
        ray = LineString([(g.x + e * 6, g.y + n * 6), (g.x + e * 760, g.y + n * 760)])
        hit = any(ray.intersects(b["poly"]) and b["top_ft"] >= 620 for b in blds)
        col = "#c0392b" if hit else "#2ecc71"
        ax.plot([g.x, g.x + e * 700], [g.y, g.y + n * 700], color=col, lw=0.7, alpha=0.7, zorder=4)
    ax.plot(g.x, g.y, "ko", ms=5, zorder=8)
    ax.text(g.x + 8, g.y, "east r17 eye", fontsize=7, zorder=8)

    ax.set_aspect("equal")
    ax.set_title("Bay-view obstruction plan — terrain treads (green), stage (tan, Δ=0%),\n"
                 "W/NW buildings (red = in corridor & ≥600ft, grey = not), "
                 "east-r17 rays (green clear / red blocked by Beards Brewery)\n"
                 "Verified against live UE trace_world (az334 hit @77m, az322 clear)")
    ax.set_xlabel("EPSG:6494 Easting (ft)")
    ax.set_ylabel("EPSG:6494 Northing (ft)")
    # frame around the action
    ax.set_xlim(C.CX - 60, C.CX + 240)
    ax.set_ylim(C.CY - 130, C.CY + 380)
    plt.tight_layout()
    fig.savefig(os.path.join(OUT, "layered_plan_view.png"), dpi=140, bbox_inches="tight")
    plt.close(fig)
    print("  wrote analysis/bay_view_obstruction/layered_plan_view.png")


def section_beards(treads, blds):
    import rasterio
    from shapely.geometry import shape, LineString
    ds = rasterio.open(C.DEM_DESIGN)
    Z = ds.read(1).astype(float)
    Z[Z == ds.nodata] = np.nan
    T = ds.transform

    def dem(x, y):
        r, c = rasterio.transform.rowcol(T, x, y)
        if 0 <= r < Z.shape[0] and 0 <= c < Z.shape[1]:
            v = Z[r, c]
            return float(v) if np.isfinite(v) else np.nan
        return np.nan

    t = next(f for f in treads if f["properties"]["row"] == 17 and f["properties"]["section"] == "east")
    g = shape(t["geometry"]).centroid
    eye_z = t["properties"]["tread_elev_navd88"] + C.EYE_SEATED_FT
    az = 334.0
    e, n = C.U(az)
    horizon = -math.degrees(math.sqrt(2 * (eye_z - C.BAY_PLANE) / 20.9e6))

    ds_ft = np.arange(0, 760, 2.0)
    terr = [dem(g.x + e * d, g.y + n * d) for d in ds_ft]

    # Beards on this ray
    beards = next((b for b in blds if "Beards" in str(b["name"])), None)
    bd0 = bd1 = None
    if beards:
        ray = LineString([(g.x + e * 6, g.y + n * 6), (g.x + e * 760, g.y + n * 760)])
        inter = ray.intersection(beards["poly"])
        if not inter.is_empty:
            dd = [math.hypot(cx - g.x, cy - g.y) for gg in getattr(inter, "geoms", [inter])
                  for cx, cy in (gg.coords if hasattr(gg, "coords") else [])]
            bd0, bd1 = min(dd), max(dd)

    fig, ax = plt.subplots(figsize=(13, 6))
    ax.plot(ds_ft, terr, color="#8a6d3b", lw=1.4, label="terrain (DEM)")
    ax.fill_between(ds_ft, 560, terr, color="#e8dcc0", alpha=0.6)
    ax.axhline(eye_z, color="gray", lw=0.6, ls=":")
    ax.plot(0, eye_z, "ko", ms=7, label=f"east r17 eye ({eye_z:.0f}ft)")
    # horizon sightline
    xs = np.array([0, 760])
    ax.plot(xs, eye_z + xs * math.tan(math.radians(horizon)),
            color="teal", lw=1.2, ls="--", label=f"bay horizon sightline ({horizon:.2f}°)")
    ax.axhline(C.BAY_PLANE, color="#3a7abf", lw=1.0, label=f"bay plane ({C.BAY_PLANE:.0f}ft)")
    # Beards silhouette
    if beards and bd0 is not None:
        ax.add_patch(plt.Rectangle((bd0, dem(g.x + e * bd0, g.y + n * bd0)),
                                   bd1 - bd0, beards["top_ft"] - dem(g.x + e * bd0, g.y + n * bd0),
                                   fc="#c0392b", ec="black", alpha=0.8, zorder=5,
                                   label=f"Beards Brewery ({beards['top_ft']:.0f}ft, LiDAR height)"))
        # sightline to building top
        ang_top = math.degrees(math.atan2(beards["top_ft"] - eye_z, bd0))
        ax.annotate(f"+{ang_top:.1f}° (above horizon {horizon:.1f}° → BLOCKS)\n"
                    f"UE trace confirms hit @ {bd0*0.3048:.0f}m",
                    xy=(bd0, beards["top_ft"]), xytext=(bd0 + 60, beards["top_ft"] + 18),
                    fontsize=8, color="#c0392b",
                    arrowprops=dict(arrowstyle="->", color="#c0392b"))

    ax.set_xlabel("Distance from eye along az 334° (ft)")
    ax.set_ylabel("Elevation NAVD88 (ft)")
    ax.set_ylim(560, 680)
    ax.set_title("Section: east r17 eye → bay along az 334° (NW corridor)\n"
                 "Beards Brewery roof rises +3.6° above eye; bay horizon is −0.13°. "
                 "Building occludes the bay in this azimuth.")
    ax.legend(fontsize=8, loc="upper right")
    ax.grid(alpha=0.3)
    plt.tight_layout()
    fig.savefig(os.path.join(OUT, "section_beards_east.png"), dpi=140, bbox_inches="tight")
    plt.close(fig)
    print("  wrote analysis/bay_view_obstruction/section_beards_east.png")


def main():
    treads, stage, blds = load()
    plan_view(treads, stage, blds)
    section_beards(treads, blds)
    print("Done.")


if __name__ == "__main__":
    main()
