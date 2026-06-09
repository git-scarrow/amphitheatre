#!/usr/bin/env python3
"""
Stage 8 — Package assembly: combined georeferenced layout.

Merges every design vector layer (basin, floor/stage, seating, garden/planting,
ADA paths, treatment train, watershed/outlet) into:
  - package/01_layout/site_layout.gpkg          (one GeoPackage, one layer per theme)
  - package/01_layout/site_layout_combined.geojson  (single FeatureCollection, 'layer' tag)
  - package/01_layout/site_layout_plan.png      (annotated plan over proposed-grade hillshade)

Planning-grade. CRS EPSG:6494 (NAD83(2011)/Michigan Central, intl ft); Z NAVD88 (Geoid12A) ft.
Reproduce: source .venv/bin/activate && python scripts/stage8_package.py
"""
import json, os
import numpy as np
import rasterio
import geopandas as gpd
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.colors import LightSource

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "package", "01_layout")
os.makedirs(OUT, exist_ok=True)

# (path, layer-name) — each becomes a GPKG layer and a tagged block of the merged GeoJSON
LAYERS = [
    ("basin_footprint.geojson",        "basin_closed_bowl"),
    ("pour_point.geojson",             "pour_point_natural_spill"),
    ("stage4/stage_floor.geojson",     "stage_floor_view"),
    ("stage4/seating_rows.geojson",    "seating_rows"),
    ("stage4/ada_route.geojson",       "ada_routes"),
    ("stage6/planting_zones.geojson",  "planting_zones_garden"),
    ("stage6/treatment_train.geojson", "treatment_train"),
    ("stage2/watershed.geojson",       "watershed"),
    ("stage2/outlet_trace.geojson",    "outlet_trace"),
]

GPKG = os.path.join(OUT, "site_layout.gpkg")
if os.path.exists(GPKG):
    os.remove(GPKG)

merged = []
for rel, name in LAYERS:
    p = os.path.join(ROOT, rel)
    g = gpd.read_file(p)
    if g.crs is None:
        g.set_crs(6494, inplace=True)
    g.to_file(GPKG, layer=name, driver="GPKG")
    gg = g.copy()
    gg["layer"] = name
    # stringify all non-geometry props into one field so the merged file stays portable
    propcols = [c for c in gg.columns if c not in ("geometry", "layer")]
    gg["attrs"] = gg[propcols].apply(
        lambda r: json.dumps({k: (None if pd.isna(v) else v) for k, v in r.items()},
                             default=str), axis=1)
    merged.append(gg[["layer", "attrs", "geometry"]])
    print(f"  + {name:28s} {len(g):3d} feat  ({rel})")

mdf = gpd.GeoDataFrame(pd.concat(merged, ignore_index=True), crs="EPSG:6494")
mgeo = os.path.join(OUT, "site_layout_combined.geojson")
mdf.to_file(mgeo, driver="GeoJSON")
print(f"  GPKG  -> {GPKG} ({len(LAYERS)} layers)")
print(f"  GeoJSON -> {mgeo} ({len(mdf)} features, tagged by 'layer')")

# ---------------------------------------------------------------- plan figure
with rasterio.open(os.path.join(ROOT, "stage5", "grade_proposed.tif")) as r:
    z = r.read(1).astype(float)
    nod = r.nodata
    if nod is not None:
        z[z == nod] = np.nan
    b = r.bounds
    extent = [b.left, b.right, b.bottom, b.top]
    res = r.res[0]

ls = LightSource(azdeg=315, altdeg=45)
zf = np.where(np.isnan(z), np.nanmin(z), z)
hs = ls.hillshade(zf, vert_exag=2.0, dx=res, dy=res)

fig, ax = plt.subplots(figsize=(13, 13))
ax.imshow(hs, cmap="gray", extent=extent, origin="upper", alpha=0.85, zorder=0)
# faint elevation tint
ax.imshow(np.where(np.isnan(z), np.nan, z), cmap="terrain", extent=extent,
          origin="upper", alpha=0.30, zorder=1)

def gj(rel):
    return gpd.read_file(os.path.join(ROOT, rel))

# planting / garden zones (filled, lowest layer)
pz = gj("stage6/planting_zones.geojson")
zcol = {"wet_bottom": "#2c7fb8", "fluctuating_margin": "#7fcdbb", "upland_garden": "#c2e699"}
for _, row in pz.iterrows():
    gpd.GeoSeries([row.geometry], crs=6494).plot(
        ax=ax, color=zcol.get(row["zone"], "#cccccc"), alpha=0.45,
        edgecolor="#1b7837", linewidth=0.6, zorder=2)

# basin closed bowl outline
gj("basin_footprint.geojson").boundary.plot(ax=ax, color="#08519c", linewidth=2.2,
                                            linestyle="--", zorder=4)

# treatment train
tt = gj("stage6/treatment_train.geojson")
for _, row in tt.iterrows():
    geom = row.geometry
    gt = geom.geom_type
    nm = row["name"]
    if gt in ("Polygon", "MultiPolygon"):
        gpd.GeoSeries([geom], crs=6494).plot(ax=ax, facecolor="#4292c6", alpha=0.55,
                                             edgecolor="#084594", linewidth=1.0, zorder=5)
    elif gt in ("LineString", "MultiLineString"):
        c = "#d7301f" if "spillway" in nm else "#6a51a3"
        gpd.GeoSeries([geom], crs=6494).plot(ax=ax, color=c, linewidth=2.0,
                                             linestyle="-.", zorder=6)
    else:  # points
        x, y = geom.x, geom.y
        ax.plot(x, y, marker="s", color="#084594", markersize=8, zorder=8)

# seating rows
sr = gj("stage4/seating_rows.geojson")
regrade = sr[sr["needs_regrade"] == True] if "needs_regrade" in sr else sr.iloc[0:0]
sr.plot(ax=ax, color="#cb181d", linewidth=1.0, alpha=0.85, zorder=6)
if len(regrade):
    regrade.plot(ax=ax, color="#fd8d3c", linewidth=1.8, zorder=7)

# ADA routes + WC spaces
ada = gj("stage4/ada_route.geojson")
ada_lines = ada[ada.geometry.geom_type.isin(["LineString", "MultiLineString"])]
ada_pts = ada[ada.geometry.geom_type == "Point"]
if len(ada_lines):
    ada_lines.plot(ax=ax, color="#000000", linewidth=2.2, linestyle=":", zorder=7)
for _, row in ada_pts.iterrows():
    ax.plot(row.geometry.x, row.geometry.y, marker="P", color="black",
            markersize=10, zorder=9)

# stage / floor / focal point / view axis
sf = gj("stage4/stage_floor.geojson")
for _, row in sf.iterrows():
    geom = row.geometry; nm = row["name"]; gt = geom.geom_type
    if gt == "Polygon":
        fc = "#fdae6b" if "stage" in nm else "#ffffb2"
        gpd.GeoSeries([geom], crs=6494).plot(ax=ax, facecolor=fc, alpha=0.7,
                                             edgecolor="#cc4c02", linewidth=1.2, zorder=5)
    elif gt == "LineString":  # bay view axis
        gpd.GeoSeries([geom], crs=6494).plot(ax=ax, color="#02818a", linewidth=2.6,
                                             zorder=8)
        xs, ys = geom.xy
        ax.annotate("bay-view axis 330°", (xs[-1], ys[-1]), color="#02818a",
                    fontsize=10, fontweight="bold",
                    xytext=(6, 6), textcoords="offset points")
    else:  # focal point
        ax.plot(geom.x, geom.y, marker="*", color="#cc4c02", markersize=22,
                markeredgecolor="black", zorder=10)

ax.set_title("Petoskey Pit — Combined Site Layout (planning-grade)\n"
             "basin · stage/floor · 30-row fan · garden/planting · ADA paths · treatment train\n"
             "EPSG:6494 (Michigan Central, intl ft); elevations NAVD88 (Geoid12A) ft",
             fontsize=12)
ax.set_xlabel("Easting (intl ft)"); ax.set_ylabel("Northing (intl ft)")
ax.ticklabel_format(style="plain", useOffset=False)
ax.set_aspect("equal")

legend = [
    Line2D([0],[0], color="#08519c", lw=2.2, ls="--", label="closed bowl (floor 609.1 / spill 618.0)"),
    Line2D([0],[0], marker="*", color="w", markerfacecolor="#cc4c02", markersize=15,
           markeredgecolor="k", label="stage focal point (613.0 ft)"),
    Patch(facecolor="#fdae6b", edgecolor="#cc4c02", label="stage / event floor"),
    Line2D([0],[0], color="#cb181d", lw=1.5, label="seating rows (30)"),
    Line2D([0],[0], color="#fd8d3c", lw=2, label="rows needing regrade (25,27-30)"),
    Line2D([0],[0], color="#000000", lw=2.2, ls=":", label="ADA ramps + WC spaces (P)"),
    Line2D([0],[0], color="#02818a", lw=2.6, label="bay-view axis (330°)"),
    Patch(facecolor="#4292c6", edgecolor="#084594", label="treatment train (forebay/WQ cell/pool)"),
    Line2D([0],[0], color="#d7301f", lw=2, ls="-.", label="emergency spillway"),
    Line2D([0],[0], color="#6a51a3", lw=2, ls="-.", label="outlet pipe"),
    Patch(facecolor="#2c7fb8", alpha=0.5, label="planting: wet bottom"),
    Patch(facecolor="#7fcdbb", alpha=0.5, label="planting: fluctuating margin"),
    Patch(facecolor="#c2e699", alpha=0.5, label="planting: upland garden"),
]
ax.legend(handles=legend, loc="upper left", fontsize=8, framealpha=0.92, ncol=1)

png = os.path.join(OUT, "site_layout_plan.png")
fig.savefig(png, dpi=160, bbox_inches="tight")
print(f"  PNG   -> {png}")
print("DONE")
