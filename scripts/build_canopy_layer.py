#!/usr/bin/env python3
"""T1 — Canopy layer (L3) from EPT first returns → canopy-top surface rasters.

Consumes the EPT-derived DSM (first-return top) and ground DTM built by PDAL
(analysis/bay_view_obstruction/canopy_work/{dsm_top_3ft,dtm_ground_3ft}.tif,
EPSG:6494 intl ft, NAVD88 ft) and produces a canopy-top *elevation* surface
(NAVD88 ft) suitable for per-ray silhouette extraction, in two labeled states:

  canopy_top_leafoff_3ft.tif   MEASUREMENT — 2015-05-02 leaf-off 3DEP LiDAR.
                               CHM = DSM - DTM; canopy where 6 <= CHM <= 90 ft
                               AND outside OSM building footprints. The winter
                               screen. This is what the LiDAR actually saw.
  canopy_top_leafon_3ft.tif    ASSUMPTION — crown-opacity inflation: the leaf-off
                               canopy mask is morphologically closed (gaps that a
                               ray could thread between bare branches are filled to
                               the local canopy-top envelope). Heights are NOT
                               raised (leaves fill gaps, they do not lift the crown
                               top); only porosity is removed. Summer is the
                               operating season, so this labeled variant exists — it
                               is not a measurement.

Vegetation could NOT be isolated by classification: this delivery classifies only
ground(2)/water(9)/road(11)/unclassified(1) — no ASPRS veg (3/4/5) or building(6)
classes. Canopy is therefore derived geometrically (CHM) with OSM footprints
subtracted to keep buildings out of the canopy (mutable) layer.

EPSG:6494 · NAVD88 intl ft · planning-grade. Read-only wrt canon.
"""
import json
import os
import sys

import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import in_situ_common as C

REPO = C.REPO
OUT = os.path.join(REPO, "analysis", "bay_view_obstruction")
W = os.path.join(OUT, "canopy_work")
FT_PER_M = 1.0 / 0.3048

CHM_MIN, CHM_MAX = 6.0, 90.0     # plausible tree/low-structure band (ft)
ACQ_DATE = "2015-05-02"
LEAF_STATE = "leaf-off"          # early May, N Michigan 45.4N: deciduous not yet out


def main():
    dsm_ds = rasterio.open(os.path.join(W, "dsm_top_3ft.tif"))
    dtm_ds = rasterio.open(os.path.join(W, "dtm_ground_3ft.tif"))
    dsm = dsm_ds.read(1)
    dsm_nd = dsm_ds.nodata
    # resample DTM onto the DSM grid
    dtm_on = np.full(dsm.shape, dtm_ds.nodata, dtype="float32")
    reproject(
        source=dtm_ds.read(1), destination=dtm_on,
        src_transform=dtm_ds.transform, src_crs=dtm_ds.crs,
        dst_transform=dsm_ds.transform, dst_crs=dsm_ds.crs,
        src_nodata=dtm_ds.nodata, dst_nodata=dtm_ds.nodata,
        resampling=Resampling.bilinear)

    valid = (dsm != dsm_nd) & (dtm_on != dtm_ds.nodata)
    chm = np.where(valid, dsm - dtm_on, np.nan)

    canopy_mask = valid & (chm >= CHM_MIN) & (chm <= CHM_MAX)

    # ── subtract OSM building footprints (keep permanent buildings OUT of the
    #    mutable canopy layer) ─────────────────────────────────────────────────
    osm = json.load(open(os.path.join(OUT, "osm_near_focal.json")))["buildings"]
    bld = np.zeros(dsm.shape, dtype=bool)
    T = dsm_ds.transform
    inv = ~T
    nrow, ncol = dsm.shape
    for b in osm:
        if "bbox" not in b:
            continue
        be0, bn0, be1, bn1 = b["bbox"]
        minx = C.CX + be0 * FT_PER_M; maxx = C.CX + be1 * FT_PER_M
        miny = C.CY + bn0 * FT_PER_M; maxy = C.CY + bn1 * FT_PER_M
        # pad footprint by 3 ft to catch eaves/roof overhang returns
        minx -= 3; miny -= 3; maxx += 3; maxy += 3
        c0, r0 = inv * (minx, maxy)   # upper-left
        c1, r1 = inv * (maxx, miny)   # lower-right
        c0 = max(0, int(np.floor(c0))); c1 = min(ncol, int(np.ceil(c1)))
        r0 = max(0, int(np.floor(r0))); r1 = min(nrow, int(np.ceil(r1)))
        if c1 > c0 and r1 > r0:
            bld[r0:r1, c0:c1] = True
    canopy_mask &= ~bld

    canopy_top_off = np.where(canopy_mask, dsm, -9999.0).astype("float32")

    # ── leaf-ON assumption: morphological closing to remove leaf-off porosity ──
    #    (fill gaps a ray could thread between bare branches; heights unchanged)
    struct = ndimage.generate_binary_structure(2, 2)
    closed = ndimage.binary_closing(canopy_mask, structure=struct, iterations=2)
    closed &= ~bld & valid          # never invent canopy over buildings/nodata
    # fill closed-but-not-original cells to the local canopy-top envelope
    top_for_fill = np.where(canopy_mask, dsm, np.nan)
    # local max of canopy top over a 9x9 window as the fill envelope
    filled_env = _nanmax_filter(top_for_fill, size=9)
    canopy_top_on = np.where(
        canopy_mask, dsm,
        np.where(closed & np.isfinite(filled_env), filled_env, -9999.0)
    ).astype("float32")
    canopy_top_on = np.where(np.isfinite(canopy_top_on), canopy_top_on, -9999.0)

    prof = dsm_ds.profile.copy()
    prof.update(dtype="float32", nodata=-9999.0, count=1, compress="deflate")
    with rasterio.open(os.path.join(OUT, "canopy_top_leafoff_3ft.tif"), "w", **prof) as d:
        d.write(canopy_top_off, 1)
    with rasterio.open(os.path.join(OUT, "canopy_top_leafon_3ft.tif"), "w", **prof) as d:
        d.write(canopy_top_on, 1)

    n_off = int(canopy_mask.sum())
    n_on = int((canopy_top_on != -9999.0).sum())
    chm_v = chm[canopy_mask]
    prov = dict(
        generated_by="scripts/build_canopy_layer.py",
        ept="USGS_LPC_MI_13Co_Emmett_2015_LAS_2017 (usgs-lidar-public S3 EPT)",
        acquisition_date=ACQ_DATE, leaf_state=LEAF_STATE,
        leaf_state_basis=("GpsTime decode of extracted points -> 2015-05-02; "
                          "northern Michigan (45.37N) deciduous leaf-out is "
                          "mid-to-late May, so this is a LEAF-OFF (winter-screen) "
                          "collection. Operating season is summer."),
        classification_note=("delivery has NO ASPRS veg(3/4/5) or building(6) "
                             "classes; canopy derived from CHM=DSM-DTM with OSM "
                             "footprints subtracted"),
        chm_band_ft=[CHM_MIN, CHM_MAX],
        canopy_cells_leafoff=n_off, canopy_cells_leafon=n_on,
        chm_stats_ft=dict(
            mean=round(float(np.nanmean(chm_v)), 1),
            p50=round(float(np.nanpercentile(chm_v, 50)), 1),
            p90=round(float(np.nanpercentile(chm_v, 90)), 1),
            max=round(float(np.nanmax(chm_v)), 1)),
        leafon_variant=("crown-opacity inflation: binary_closing(iter=2) of the "
                        "leaf-off canopy mask, gaps filled to local 9x9 canopy-top "
                        "envelope; heights NOT raised. ASSUMPTION, not measurement."),
        rasters=["canopy_top_leafoff_3ft.tif", "canopy_top_leafon_3ft.tif"],
        grid="EPSG:6494 intl ft, 3 ft, NAVD88 ft elevation of canopy top",
    )
    json.dump(prov, open(os.path.join(OUT, "canopy_layer_provenance.json"), "w"), indent=1)
    print(f"canopy leaf-off cells {n_off}  leaf-on cells {n_on}  "
          f"(mask +{n_on-n_off} from closing)")
    print(f"CHM canopy stats ft: mean {prov['chm_stats_ft']['mean']} "
          f"p90 {prov['chm_stats_ft']['p90']} max {prov['chm_stats_ft']['max']}")
    print(f"acq {ACQ_DATE} {LEAF_STATE}")
    print("wrote canopy_top_leafoff_3ft.tif, canopy_top_leafon_3ft.tif, "
          "canopy_layer_provenance.json")


def _nanmax_filter(a, size):
    """max filter ignoring NaN (returns NaN where the window is all-NaN)."""
    filled = np.where(np.isfinite(a), a, -1e9)
    mx = ndimage.maximum_filter(filled, size=size, mode="nearest")
    return np.where(mx <= -1e8, np.nan, mx)


if __name__ == "__main__":
    main()
