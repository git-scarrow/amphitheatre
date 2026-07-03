#!/usr/bin/env python3
"""Red-team the ~330 CY stage-pad fill finding. Advisory only — writes to
analysis/stage_pad_redteam/, changes no canon. All checks per the brief."""
import csv
import json
import os

import numpy as np
import rasterio
from rasterio.features import rasterize
from shapely.geometry import shape, mapping
from shapely.affinity import translate
from shapely.ops import unary_union

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "analysis", "stage_pad_redteam")
os.makedirs(OUT, exist_ok=True)
EVENT_FLOOR = 612.5


def load(p):
    return json.load(open(os.path.join(REPO, p)))


with rasterio.open(os.path.join(REPO, "dem", "dem_design_1ft.tif")) as ds:
    DEM = ds.read(1).astype(float)
    TRAN = ds.transform
    ND = ds.nodata
    CELL = abs(TRAN.a * TRAN.e)


def stats(geom, target=EVENT_FLOOR):
    """DEM stats + cut/fill CY under a polygon to `target`. all_touched=False."""
    m = rasterize([(mapping(geom), 1)], out_shape=DEM.shape, transform=TRAN,
                  fill=0, all_touched=False).astype(bool)
    if ND is not None:
        m &= (DEM != ND)
    z = DEM[m]
    if z.size == 0:
        return dict(cells=0, area=0.0, zmin=None, zmean=None, zmax=None,
                    mean_fill=0.0, cut_cy=0.0, fill_cy=0.0, net_cy=0.0)
    d = target - z                      # + = fill needed
    fill = float(np.clip(d, 0, None).sum()) * CELL / 27.0
    cut = float(np.clip(-d, 0, None).sum()) * CELL / 27.0
    return dict(cells=int(z.size), area=round(z.size * CELL, 1),
                zmin=round(float(z.min()), 2), zmean=round(float(z.mean()), 2),
                zmax=round(float(z.max()), 2),
                mean_fill=round(float(d.mean()), 2),
                cut_cy=round(cut, 1), fill_cy=round(fill, 1),
                net_cy=round(fill - cut, 1))


# ── geometry: inherited stage, adopted footprint, split ─────────────────────
geE = load("analysis/scenarioE_civic/geometry.geojson")
inh = [f for f in geE["features"] if f["properties"].get("role") == "stage_surface"]
inh_polys = sorted((shape(f["geometry"]) for f in inh), key=lambda g: g.area, reverse=True)
inh_core, inh_sh = inh_polys[0], inh_polys[1:]

adf = load("analysis/in_situ_normalization/adopted_stage_footprint.geojson")
deck = shape(adf["features"][0]["geometry"])          # core ∪ five-facet apron
off = adf["features"][0]["properties"]["lateral_offset_from_inherited_ft"]

core = translate(inh_core, xoff=off[0], yoff=off[1])   # P_opt-placed 70x34 core
apron = deck.difference(core).buffer(0)                # recovered five-facet apron
sh_l = translate(inh_sh[0], xoff=off[0], yoff=off[1])
sh_r = translate(inh_sh[1], xoff=off[0], yoff=off[1])

components = {
    "stage_core_70x34": core,
    "five_facet_apron": apron,
    "shoulder_a": sh_l,
    "shoulder_b": sh_r,
}
footprint_union = unary_union(list(components.values()))

# adjacent (NOT part of the stage footprint) — computed for context/overlap
bz = {f["properties"]["name"]: shape(f["geometry"])
      for f in load("vectors_geojson/bowl_zones.geojson")["features"]}
orchestra = bz["orchestra_event_floor"]

# ── CHECK 1 + 2: per-component + union CY, no double count ───────────────────
rows = []
for name, g in components.items():
    s = stats(g)
    rows.append(dict(name=name, **s, target_elev=EVENT_FLOOR))
uni = stats(footprint_union)
rows.append(dict(name="UNION(stage_footprint)", **uni, target_elev=EVENT_FLOOR))
rows.append(dict(name="orchestra_event_floor[adjacent]", **stats(orchestra),
                 target_elev=EVENT_FLOOR))

sum_fill = sum(r["fill_cy"] for r in rows if r["name"] in components)
print(f"[1/2] component fill sum = {sum_fill:.1f} CY ; union fill = {uni['fill_cy']:.1f} CY ; "
      f"double-count = {sum_fill - uni['fill_cy']:+.1f} CY")
print(f"      union area charged = {uni['area']} sf ; mean fill = {uni['mean_fill']} ft ; "
      f"identity area*mean/27 = {uni['area']*uni['mean_fill']/27:.1f} CY vs fill {uni['fill_cy']}")

with open(os.path.join(OUT, "stage_pad_volume_breakdown.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=["name", "area_sf", "zmin", "zmean", "zmax",
                                       "target_elev", "mean_fill_ft", "cut_cy",
                                       "fill_cy", "net_cy", "cells"])
    w.writeheader()
    for r in rows:
        w.writerow({"name": r["name"], "area_sf": r["area"], "zmin": r["zmin"],
                    "zmean": r["zmean"], "zmax": r["zmax"], "target_elev": r["target_elev"],
                    "mean_fill_ft": r["mean_fill"], "cut_cy": r["cut_cy"],
                    "fill_cy": r["fill_cy"], "net_cy": r["net_cy"], "cells": r["cells"]})

# split geojson
def to_feat(name, g):
    gg = g if g.geom_type == "Polygon" else unary_union([g])
    return {"type": "Feature", "properties": {"name": name,
            "area_sf": round(g.area, 0)},
            "geometry": mapping(gg)}
split = {"type": "FeatureCollection",
         "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::6494"}},
         "features": [to_feat(n, g) for n, g in components.items()]}
json.dump(split, open(os.path.join(OUT, "adopted_stage_footprint_split.geojson"), "w"), indent=1)

# ── CHECK 3: datum sweep ─────────────────────────────────────────────────────
print("\n[3] target-elevation sweep (union footprint):")
datum = {}
for t in (611.3, 611.8, 612.0, 612.5):
    s = stats(footprint_union, target=t)
    datum[t] = s
    print(f"    target {t}: fill {s['fill_cy']:>6.1f} CY  cut {s['cut_cy']:>4.1f}  "
          f"mean_fill {s['mean_fill']:>4.2f} ft")

# ── CHECK 4: construction alternatives (separate quantities) ────────────────
# A: solid earthen pad to 612.5 = union fill
# B: hybrid — fill only under apron + shoulders (access/edge); core decked over pan
edges = unary_union([apron, sh_l, sh_r])
B = stats(edges)
# C: freestanding deck — footings only; ~point loads, negligible earth volume
print("\n[4] construction alternatives (NOT one earthwork number):")
print(f"    A solid earthen pad→612.5 : {uni['fill_cy']:.1f} CY earthwork fill")
print(f"    B hybrid (fill apron+shoulders only, core decked) : {B['fill_cy']:.1f} CY fill "
      f"+ deck structure over {stats(core)['area']:.0f} sf core")
print(f"    C freestanding low deck : ~0 CY earthwork (footings/piers only), "
      f"deck over {uni['area']:.0f} sf")

# ── CHECK 5: contamination — is the footprint the CURRENT adopted stage? ─────
minx, miny, maxx, maxy = footprint_union.bounds
front = adf["features"][0]["properties"].get("front_to_row1_ft")
axis = adf["features"][0]["properties"].get("axis_az")
# inherited stage source lineage:
try:
    sf = load("design_open_low/stage_floor.geojson")
    sf_stage = [shape(f["geometry"]) for f in sf["features"]
                if "stage" in json.dumps(f["properties"]).lower()
                and f["geometry"]["type"] in ("Polygon", "MultiPolygon")]
    sf_area = round(sum(g.area for g in sf_stage), 0) if sf_stage else None
except Exception as e:
    sf_area = f"err:{e}"
core_area = round(core.area, 0)
contamination = {
    "adopted_core_area_sf": core_area,
    "is_70x34_not_52x26": bool(2300 < core_area < 2450),  # 70x34=2380; 52x26=1352
    "axis_az": axis,
    "lateral_offset_ft": off,
    "front_to_row1_ft": front,
    "min_row1_gap_ft": min(front.values()) if front else None,
    "no_85ft_or_35ft_stage_distance": bool(front and max(front.values()) < 60),
    "bbox": [round(minx, 1), round(miny, 1), round(maxx, 1), round(maxy, 1)],
    "design_open_low_stagefloor_area_sf": sf_area,
}
contam_fail = (not contamination["is_70x34_not_52x26"]
               or not contamination["no_85ft_or_35ft_stage_distance"]
               or axis != 150.0)
print("\n[5] contamination check:", json.dumps(contamination))
print("    CONTAMINATION:", "FAIL" if contam_fail else "PASS (current adopted stage, no stale coords)")

# ── CHECK 6: overlap with existing project quantities ───────────────────────
in_508 = {  # is this quantity already inside the 500.8 balance?
    "treatment_cell_landscape": False, "orchestra_event_floor": False,
    "ada_route": True, "terrace_treads": True,
    "east_flank_swale": True, "south_flank_swale": True,
    "construction_envelope": "envelope(not a volume)",
}
targets = {
    "treatment_cell_landscape": bz["treatment_cell_landscape"],
    "orchestra_event_floor": orchestra,
    "east_flank_swale": bz["east_flank_swale"],
    "south_flank_swale": bz["south_flank_swale"],
    "cross_aisle": bz["cross_aisle"],
    "construction_envelope": bz["construction_envelope"],
}
try:
    ada = unary_union([shape(f["geometry"]) for f in
                       load("vectors_geojson/ada_route.geojson")["features"]])
    targets["ada_route"] = ada
except Exception:
    pass
treads = unary_union([shape(f["geometry"]) for f in
                      load("vectors_geojson/terrace_treads.geojson")["features"]])
targets["terrace_treads"] = treads

ov_rows = []
print("\n[6] overlap audit (adopted stage footprint ∩ existing quantities):")
for name, g in targets.items():
    inter = footprint_union.intersection(g)
    a = round(inter.area, 1) if not inter.is_empty else 0.0
    ov_rows.append(dict(other=name, overlap_area_sf=a,
                        other_in_500_8=in_508.get(name, "?"),
                        note=("OVERLAP — double-count risk" if a > 1.0 else "clear")))
    print(f"    ∩ {name:<26} = {a:>7.1f} sf  (in 500.8: {in_508.get(name,'?')})")
with open(os.path.join(OUT, "overlap_audit.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=["other", "overlap_area_sf", "other_in_500_8", "note"])
    w.writeheader()
    for r in ov_rows:
        w.writerow(r)

# dump a machine summary for the .md
summary = dict(event_floor=EVENT_FLOOR, union=uni, components={n: stats(g) for n, g in components.items()},
               orchestra=stats(orchestra), datum_sweep={str(k): v for k, v in datum.items()},
               alt_B_edges=B, contamination=contamination, contam_fail=contam_fail,
               overlaps=ov_rows, double_count_cy=round(sum_fill - uni["fill_cy"], 1))
json.dump(summary, open(os.path.join(OUT, "_summary.json"), "w"), indent=1)
print("\nwrote:", os.listdir(OUT))
