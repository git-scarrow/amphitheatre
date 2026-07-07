#!/usr/bin/env python3
"""
Stage 2 — stage/storage curve for the closed central bowl of the Petoskey Pit.

Inputs
  dem/dem_design_1ft.tif        1 ft ground DEM, EPSG:6494, NAVD88 (Geoid12A) intl ft
  masks/artifact_mask.geojson   north-edge bayward low (treated as a BARRIER here)

Method
  1. Build analysis domain = valid DEM cells minus the artifact mask. The mask is
     treated as a *barrier* (not an open outlet): otherwise the bowl would falsely
     "drain" into the bay-ward low and never register as a closed depression.
  2. Priority-flood depression fill (Barnes/Planchon, 8-connected). Outlets = domain
     cells on the grid edge OR adjacent to a barrier/nodata cell, seeded at their own
     elevation. fill - dem = depression depth.
  3. The closed central bowl = connected depression component containing the cell of
     maximum fill depth. Its constant fill value is the spill (pour-point) elevation.
  4. Pour point = the bowl-perimeter cell whose lowest exterior neighbour is the global
     drainage exit (min fill among exits). Outflow direction = toward that neighbour.
  5. Stage/storage: for each candidate water-surface elevation, inundated area and
     cumulative volume are summed over cells INSIDE the bowl footprint with dem < stage.
     Cell area = 1 ft^2 (1 ft DEM). Volume = sum((stage - dem)) ft^3.

Units: international feet (horizontal & vertical), NAVD88. 1 acre = 43560 ft^2.
Run inside the project venv:  python scripts/stage_storage.py
"""
import json, heapq, pathlib
import numpy as np
import rasterio
import geopandas as gpd
from rasterio.features import rasterize, shapes
from scipy import ndimage
from shapely.geometry import shape, mapping, Point
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEM_PATH = ROOT / "dem" / "dem_design_1ft.tif"
MASK_PATH = ROOT / "masks" / "artifact_mask.geojson"
OUT = ROOT  # deliverables at project root, like Stage 1
METRICS = ROOT / "metrics"; METRICS.mkdir(exist_ok=True)

CRS = "EPSG:6494"
ACRE = 43560.0
CELL = 1.0  # ft^2 per cell (1 ft DEM)

# Datum reconciliation (see docs/datum_note.md). Δ is now CONFIRMED +0.162 ft (2026-06-06
# NOAA VDatum, gating_dossier A-1). The constant below stays at the as-run 0.40 until the
# authorized stage_storage regen flips it to 0.162 and refreshes the CSV/summary together.
BAY_IGLD85 = 581.0          # ft IGLD85, Little Traverse Bay nominal
DELTA_NAVD = 0.40           # ft, NAVD88 = IGLD85 + DELTA (as-run; CONFIRMED value +0.162 pending regen)
BAY_NAVD88 = BAY_IGLD85 + DELTA_NAVD

# Requested floor-candidate range, plus an extension to the spill so the full bowl
# capacity and the pour point are captured (the requested 604-616 sits entirely below
# the spill — see README / DATA_GAPS).
REQ_LO, REQ_HI, STEP = 604.0, 616.0, 0.25


def priority_flood(dem, domain):
    H, W = dem.shape
    fill = np.full((H, W), np.inf)
    closed = np.zeros((H, W), bool)
    heap = []
    # seeds: domain edge cells or domain cells touching a barrier (non-domain) cell
    for r, c in zip(*np.where(domain)):
        outlet = (r == 0 or r == H - 1 or c == 0 or c == W - 1)
        if not outlet:
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                if not domain[r + dr, c + dc]:
                    outlet = True
                    break
        if outlet:
            fill[r, c] = dem[r, c]
            closed[r, c] = True
            heapq.heappush(heap, (dem[r, c], r, c))
    nb = ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1))
    while heap:
        z, r, c = heapq.heappop(heap)
        for dr, dc in nb:
            nr, nc = r + dr, c + dc
            if 0 <= nr < H and 0 <= nc < W and domain[nr, nc] and not closed[nr, nc]:
                nz = dem[nr, nc] if dem[nr, nc] > z else z
                fill[nr, nc] = nz
                closed[nr, nc] = True
                heapq.heappush(heap, (nz, nr, nc))
    return fill


def main():
    ds = rasterio.open(DEM_PATH)
    dem = ds.read(1).astype("float64")
    nod = ds.nodata
    T = ds.transform
    H, W = dem.shape

    gj = gpd.read_file(MASK_PATH)
    barrier = rasterize(((g, 1) for g in gj.geometry), out_shape=dem.shape,
                        transform=T, fill=0, dtype="uint8").astype(bool)
    domain = (dem != nod) & ~barrier

    fill = priority_flood(dem, domain)
    depth = np.where(domain, fill - dem, 0.0)

    # closed central bowl = component (depth>1e-3) holding the deepest cell
    lab, n = ndimage.label(depth > 1e-3)
    deepest = np.unravel_index(np.argmax(np.where(domain, depth, -1)), depth.shape)
    bowl_id = lab[deepest]
    foot = (lab == bowl_id)
    spill = float(np.nanmax(fill[foot]))            # constant fill on a single sink
    floor = float(np.nanmin(dem[foot]))
    fj = np.unravel_index(np.argmin(np.where(foot, dem, np.inf)), dem.shape)
    fx, fy = T * (fj[1] + 0.5, fj[0] + 0.5)
    foot_area_ac = foot.sum() * CELL / ACRE

    # ---- pour point: bowl-perimeter cell with the lowest *exterior* neighbour ----
    nb = ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1))
    best = None  # (exit_fill, pr, pc, nr, nc)
    rr, cc = np.where(foot)
    for r, c in zip(rr, cc):
        for dr, dc in nb:
            nr, nc = r + dr, c + dc
            if 0 <= nr < H and 0 <= nc < W and domain[nr, nc] and not foot[nr, nc]:
                ef = fill[nr, nc]
                if best is None or ef < best[0]:
                    best = (ef, r, c, nr, nc)
    _, pr, pc, nr, nc = best
    px, py = T * (pc + 0.5, pr + 0.5)             # pour-point cell centre
    ex, ey = T * (nc + 0.5, nr + 0.5)             # exit neighbour centre
    dxy = np.array([ex - px, ey - py])
    bearing = (np.degrees(np.arctan2(dxy[0], dxy[1])) + 360) % 360  # 0=N,90=E (grid)
    compass = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"][int(((bearing + 22.5) % 360) // 45)]

    head_to_bay = spill - BAY_NAVD88

    # ---- stage-storage table (restricted to bowl footprint) ----
    demf = np.where(foot, dem, np.nan)
    top = float(np.ceil(spill * 4) / 4)           # extend to spill (round up to 0.25)
    stages = np.round(np.arange(REQ_LO, max(REQ_HI, top) + STEP / 2, STEP), 2)
    rows = []
    for s in stages:
        wet = foot & (dem < s)
        ncell = int(wet.sum())
        area_ac = ncell * CELL / ACRE
        vol_ft3 = float(np.nansum((s - demf)[wet])) if ncell else 0.0
        rows.append(dict(stage_ft_navd88=float(s),
                         depth_above_floor_ft=round(float(s - floor), 2),
                         inundated_area_ac=round(area_ac, 4),
                         inundated_area_ft2=ncell,
                         storage_volume_ft3=round(vol_ft3, 1),
                         storage_volume_acft=round(vol_ft3 / ACRE, 4),
                         at_or_above_spill=bool(s >= spill)))
    import csv
    with open(OUT / "stage_storage.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)

    # ---- basin_footprint.geojson (dissolved) ----
    polys = [shape(g) for g, v in shapes(foot.astype("uint8"), mask=foot, transform=T) if v == 1]
    from shapely.ops import unary_union
    basin = unary_union(polys)
    gpd.GeoDataFrame(
        [{"name": "central_closed_bowl", "spill_elev_ft_navd88": round(spill, 2),
          "floor_elev_ft_navd88": round(floor, 2), "depth_ft": round(spill - floor, 2),
          "footprint_area_ac": round(foot_area_ac, 4),
          "datum": "NAVD88 Geoid12A intl ft", "note": "artifact mask treated as barrier"}],
        geometry=[basin], crs=CRS).to_file(OUT / "basin_footprint.geojson", driver="GeoJSON")

    # ---- pour_point.geojson ----
    gpd.GeoDataFrame(
        [{"name": "pour_point", "spill_elev_ft_navd88": round(spill, 2),
          "outflow_bearing_deg_grid": round(float(bearing), 1),
          "outflow_compass_grid": compass,
          "exit_neighbour_fill_ft": round(float(fill[nr, nc]), 2),
          "head_to_bay_ft": round(float(head_to_bay), 2),
          "bay_navd88_ft": round(BAY_NAVD88, 2),
          "datum": "NAVD88 Geoid12A intl ft"}],
        geometry=[Point(px, py)], crs=CRS).to_file(OUT / "pour_point.geojson", driver="GeoJSON")

    # ---- plot ----
    df_s = [r["stage_ft_navd88"] for r in rows]
    df_a = [r["inundated_area_ac"] for r in rows]
    df_v = [r["storage_volume_acft"] for r in rows]
    fig, ax = plt.subplots(1, 2, figsize=(11, 5))
    ax[0].plot(df_a, df_s, "-", color="#1f6feb"); ax[0].set_xlabel("inundated area (ac)")
    ax[0].set_ylabel("stage — water surface elev (ft NAVD88)"); ax[0].set_title("Stage – Area")
    ax[1].plot(df_v, df_s, "-", color="#2da44e"); ax[1].set_xlabel("storage volume (acre-ft)")
    ax[1].set_title("Stage – Storage")
    for a in ax:
        a.axhline(spill, color="#cf222e", lw=1, ls="--")
        a.axhline(floor, color="#6e7781", lw=1, ls=":")
        a.grid(alpha=.3)
    ax[1].text(0.02, 0.97, f"spill {spill:.2f} ft (pour pt {compass})\nfloor {floor:.2f} ft\n"
               f"depth {spill-floor:.2f} ft  area {foot_area_ac:.2f} ac\n"
               f"head to bay (NAVD88 {BAY_NAVD88:.1f}) {head_to_bay:.1f} ft",
               transform=ax[1].transAxes, va="top", fontsize=8,
               bbox=dict(boxstyle="round", fc="white", ec="#cccccc"))
    fig.suptitle("Petoskey Pit — central closed bowl stage/storage (NAVD88, intl ft)")
    fig.tight_layout(); fig.savefig(OUT / "stage_storage_curve.png", dpi=150)

    summary = dict(floor=floor, floor_EN=(round(fx, 2), round(fy, 2)), spill=spill,
                   depth=spill - floor, area_ac=foot_area_ac,
                   pour_EN=(round(px, 2), round(py, 2)), bearing=round(float(bearing), 1),
                   compass=compass, exit_fill=round(float(fill[nr, nc]), 2),
                   bay_navd88=BAY_NAVD88, head_to_bay=round(float(head_to_bay), 2),
                   n_depressions=int(n), stage_max=float(stages.max()))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
