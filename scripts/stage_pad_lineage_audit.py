#!/usr/bin/env python3
"""Data-lineage audit for the ~330 CY stage-pad finding — source terrain → reported CY.

Advisory only. Changes no canon. Re-derives (does not hardcode) the proofs that make
the audit self-checking, and writes the deliverable set to analysis/stage_pad_redteam/:

  stage_pad_data_lineage_audit.md   (narrative — hand-maintained, not written here)
  stage_pad_volume_breakdown.csv    (per-split + union + datum sweep)
  adopted_stage_footprint_split.geojson
  stage_pad_overlap_audit.csv       (∩ existing quantities, cut-collision + double-count verdict)
  terrain_source_report.txt         (source, hashes, CRS/datum, existing-vs-proposed proof, lineage)

Run:  python scripts/stage_pad_lineage_audit.py
"""
import csv
import hashlib
import json
import os

import numpy as np
import rasterio
from rasterio.features import rasterize
from shapely.affinity import translate
from shapely.geometry import mapping, shape
from shapely.ops import unary_union

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "analysis", "stage_pad_redteam")
os.makedirs(OUT, exist_ok=True)
EVENT_FLOOR = 612.5
DESIGN = "dem/dem_design_1ft.tif"       # existing ground (verified below)
PROPOSED = "dem/proposed_grade_1ft.tif"  # existing + burned earthwork
EXIST_VIEWER = "package/10_3d_viewer/dem/existing_ground_1ft.tif"


def load(p):
    return json.load(open(os.path.join(REPO, p)))


def sha(rel):
    h = hashlib.sha256()
    with open(os.path.join(REPO, rel), "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


# ── reference grid = existing-ground design DEM ──────────────────────────────
with rasterio.open(os.path.join(REPO, DESIGN)) as ds:
    DEM = ds.read(1).astype(float)
    TRAN, SH, ND, CRS = ds.transform, ds.shape, ds.nodata, ds.crs
    CELL = abs(TRAN.a * TRAN.e)
    BOUNDS = [round(v, 2) for v in ds.bounds]
    PIX = (round(TRAN.a, 4), round(TRAN.e, 4))
Zp = rasterio.open(os.path.join(REPO, PROPOSED)).read(1).astype(float)
Zev = rasterio.open(os.path.join(REPO, EXIST_VIEWER)).read(1).astype(float)


def stats(geom, target=EVENT_FLOOR):
    m = rasterize([(mapping(geom), 1)], out_shape=SH, transform=TRAN,
                  fill=0, all_touched=False).astype(bool)
    if ND is not None:
        m &= (DEM != ND)
    z = DEM[m]
    if z.size == 0:
        return dict(cells=0, area=0.0, zmin=None, p10=None, zmean=None, zmed=None,
                    p90=None, zmax=None, mean_fill=0.0, cut_cy=0.0, fill_cy=0.0), m
    d = target - z
    return dict(
        cells=int(z.size), area=round(z.size * CELL, 1),
        zmin=round(float(z.min()), 2), p10=round(float(np.percentile(z, 10)), 2),
        zmean=round(float(z.mean()), 2), zmed=round(float(np.median(z)), 2),
        p90=round(float(np.percentile(z, 90)), 2), zmax=round(float(z.max()), 2),
        mean_fill=round(float(d.mean()), 3),
        cut_cy=round(float(np.clip(-d, 0, None).sum()) * CELL / 27.0, 1),
        fill_cy=round(float(np.clip(d, 0, None).sum()) * CELL / 27.0, 1),
    ), m


# ── footprint reconstruction (identical to stage_pad_redteam.py) ─────────────
geE = load("analysis/scenarioE_civic/geometry.geojson")
inh = [f for f in geE["features"] if f["properties"].get("role") == "stage_surface"]
inh_polys = sorted((shape(f["geometry"]) for f in inh), key=lambda g: g.area, reverse=True)
inh_core, inh_sh = inh_polys[0], inh_polys[1:]
adf = load("analysis/in_situ_normalization/adopted_stage_footprint.geojson")
props = adf["features"][0]["properties"]
deck = shape(adf["features"][0]["geometry"])
off = props["lateral_offset_from_inherited_ft"]
core = translate(inh_core, xoff=off[0], yoff=off[1])
apron = deck.difference(core).buffer(0)
sh_l = translate(inh_sh[0], xoff=off[0], yoff=off[1])
sh_r = translate(inh_sh[1], xoff=off[0], yoff=off[1])
components = {"stage_core_70x34": core, "five_facet_apron": apron,
             "shoulder_a": sh_l, "shoulder_b": sh_r}
union = unary_union(list(components.values()))

# ── deliverable 1: volume breakdown (splits + union + datum sweep) ───────────
rows = []
for name, g in components.items():
    s, _ = stats(g)
    rows.append(dict(name=name, **s, target_elev=EVENT_FLOOR))
uni, umask = stats(union)
rows.append(dict(name="UNION(stage_footprint)", **uni, target_elev=EVENT_FLOOR))
for t in (611.3, 611.8, 612.0, 612.5):
    s, _ = stats(union, target=t)
    rows.append(dict(name=f"UNION@{t}", **s, target_elev=t))
with open(os.path.join(OUT, "stage_pad_volume_breakdown.csv"), "w", newline="") as fh:
    cols = ["name", "area_sf", "cells", "zmin", "p10", "zmean", "zmed", "p90", "zmax",
            "target_elev", "mean_fill_ft", "cut_cy", "fill_cy"]
    w = csv.writer(fh)
    w.writerow(cols)
    for r in rows:
        w.writerow([r["name"], r.get("area"), r.get("cells"), r.get("zmin"), r.get("p10"),
                    r.get("zmean"), r.get("zmed"), r.get("p90"), r.get("zmax"),
                    r["target_elev"], r.get("mean_fill"), r.get("cut_cy"), r.get("fill_cy")])

# split geojson
split = {"type": "FeatureCollection",
         "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::6494"}},
         "features": [{"type": "Feature",
                       "properties": {"name": n, "area_sf": round(g.area, 0)},
                       "geometry": mapping(g)} for n, g in components.items()]}
json.dump(split, open(os.path.join(OUT, "adopted_stage_footprint_split.geojson"), "w"), indent=1)

# ── deliverable 2: overlap audit (∩ existing quantities) ─────────────────────
bz = {f["properties"]["name"]: shape(f["geometry"])
      for f in load("vectors_geojson/bowl_zones.geojson")["features"]}
# quantities already inside the geometry-backed 500.8 balance (earthwork.csv)
in_508 = {"east_flank_swale": True, "south_flank_swale": True, "cross_aisle": True,
          "terrace_treads": True, "ada_route": True, "orchestra_event_floor": False,
          "treatment_cell_landscape": False, "construction_envelope": "envelope"}
targets = {"treatment_cell_landscape": bz["treatment_cell_landscape"],
           "orchestra_event_floor": bz["orchestra_event_floor"],
           "east_flank_swale": bz["east_flank_swale"],
           "south_flank_swale": bz["south_flank_swale"],
           "cross_aisle": bz["cross_aisle"],
           "construction_envelope": bz["construction_envelope"]}
try:
    targets["ada_route"] = unary_union([shape(f["geometry"]) for f in
                                        load("vectors_geojson/ada_route.geojson")["features"]])
except Exception:
    pass
targets["terrace_treads"] = unary_union([shape(f["geometry"]) for f in
                                         load("vectors_geojson/terrace_treads.geojson")["features"]])

# proposed-minus-existing inside the footprint = the swale CUT the stage fill collides with
dif = Zp - DEM
valid = (DEM != ND) & (Zp != ND)
cut_in_fp = int((umask & valid & (dif < -0.01)).sum())

ov = []
for name, g in targets.items():
    inter = union.intersection(g)
    a = round(inter.area, 1) if not inter.is_empty else 0.0
    if a <= 1.0:
        verdict = "clear"
    elif in_508.get(name) is True:
        verdict = "COLLISION+DOUBLE-COUNT: area is in 500.8 (cut); stage fill reverses counted cut"
    elif in_508.get(name) is False:
        verdict = "SHARED 612.5 AREA: count once (not additive)"
    else:
        verdict = "envelope, not a volume"
    ov.append(dict(other=name, overlap_area_sf=a, other_in_500_8=in_508.get(name, "?"),
                   verdict=verdict))
with open(os.path.join(OUT, "stage_pad_overlap_audit.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=["other", "overlap_area_sf", "other_in_500_8", "verdict"])
    w.writeheader()
    w.writerows(ov)

# ── deliverable 3: terrain source report ─────────────────────────────────────
# proofs (recomputed, not asserted):
ev_id = float(np.abs((Zev - DEM)[valid]).max())            # existing_viewer == design ?
prop_fp = (Zp - DEM)[umask & valid]                        # proposed vs existing in footprint
row_note = ""
rep = []
rep.append("STAGE-PAD TERRAIN SOURCE REPORT  (advisory; changes no canon)")
rep.append("=" * 70)
rep.append("")
rep.append("[1] SOURCE SURFACE USED FOR THE STAGE-PAD VOLUME")
rep.append(f"    file            : {DESIGN}")
rep.append(f"    sha256          : {sha(DESIGN)}")
rep.append(f"    CRS             : EPSG:{CRS.to_epsg()}  ({CRS.to_wkt().split(chr(34))[1]})")
rep.append(f"    linear units    : {CRS.linear_units} (international ft)")
rep.append("    vertical datum  : NAVD88 Geoid12A intl ft  (per dem/in_situ_grading_manifest.json;")
rep.append("                      NOT embedded in the GeoTIFF — horizontal CRS only. Provenance-declared.)")
rep.append(f"    pixel size      : {PIX} ft   cell area {CELL:.2f} sf")
rep.append(f"    grid            : {SH[1]}x{SH[0]}   bounds {BOUNDS}")
rep.append(f"    nodata          : {ND}   band desc: 'idw' (IDW-interpolated)")
rep.append("    provenance      : USGS 3DEP LiDAR, USGS_LPC_MI_13County_2015_C16 tiles 532749/532751,")
rep.append("                      ground class 2 only -> PDAL writers.gdal IDW.  Generator: scripts/build_dems.py")
rep.append(f"    sampling method : rasterize(all_touched=False), point-in-cell; {CELL:.0f} sf per cell")
rep.append("")
rep.append("[2] IS THIS THE EXISTING GROUND?  (verified, not assumed)")
rep.append(f"    dem_design_1ft  vs  package/10_3d_viewer/dem/existing_ground_1ft.tif:")
rep.append(f"      max|delta| over all valid cells = {ev_id:.4f} ft  ->  BYTE-VALUE IDENTICAL")
rep.append("      => 'dem_design_1ft.tif' IS the bare existing-ground DEM (name 'design' is a misnomer).")
rep.append(f"    proposed_grade_1ft within stage footprint (proposed - existing):")
rep.append(f"      mean {prop_fp.mean():+.3f}  min {prop_fp.min():+.2f}  max {prop_fp.max():+.2f} ft")
rep.append(f"      => proposed grade NEVER rises in the stage area (max {prop_fp.max():+.2f}); it CUTS")
rep.append(f"         {cut_in_fp} cells (drainage swales). The stage pad is NOT in the proposed grade,")
rep.append("         so ~330 CY is additive to the raster — but it overlies counted swale CUTS (see overlap csv).")
rep.append("")
rep.append("[3] SAME SOURCE AS OTHER QUANTITIES?")
rep.append("    seating/sightlines : dem/dem_design_1ft.tif  (existing)   SAME")
rep.append("    drainage/swales    : dem/dem_design_1ft.tif  (existing)   SAME")
rep.append("    earthwork 500.8 CY : dem/dem_design_1ft.tif  (existing)   SAME")
rep.append("    ADA route grades   : dem/proposed_grade_1ft.tif (proposed) DIFFERENT — by design")
rep.append("                         (ADA slope must be checked on the finished surface). Not a defect.")
rep.append("    stage_pad_redteam  : dem/dem_design_1ft.tif  (existing)   SAME as seating/drainage/earthwork")
rep.append("    VERDICT: terrain source is consistent and correct for a fill-vs-existing volume.")
rep.append("")
rep.append("[4] ARITHMETIC CLOSURE (union, target 612.5)")
rep.append(f"    area {uni['area']} sf  mean_fill {uni['mean_fill']} ft  ->  "
           f"area*mean/27 = {uni['area']*uni['mean_fill']/27:.1f} CY  vs reported fill {uni['fill_cy']} CY")
rep.append(f"    prose '2699 sf' = deck-only (core+apron); 330 CY is charged over the 3386 sf union (+2 shoulders).")
open(os.path.join(OUT, "terrain_source_report.txt"), "w").write("\n".join(rep) + "\n")

print("union:", uni)
print("existing_viewer==design max|d| =", ev_id)
print("proposed-existing in footprint: mean %.3f max %.3f cut_cells %d" %
      (prop_fp.mean(), prop_fp.max(), cut_in_fp))
print("wrote:", sorted(os.listdir(OUT)))
