#!/usr/bin/env python3
"""Fetch aerial imagery clips for the comparator sites (plan diagrams +
independent digitization cross-check).

Uses the public Esri World Imagery export endpoint, requesting the SAME
native-UTM bounds as each site's DEM clip (read from provenance.json), at
0.5 m/px. Imagery acquisition date is NOT controlled by us — World Imagery
is a mosaic — so anything digitized from it is labeled INFERRED, never
measured. Attribution: Esri, Maxar, Earthstar Geographics, USDA, USGS, et al.

Reproduce:  .venv/bin/python scripts/comparators/fetch_imagery.py
"""
import json
import os
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(__file__))
from sites import SITES

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
EXPORT = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/export"


def fetch(slug):
    dem_dir = os.path.join(ROOT, "data", "comparators", slug, "dem")
    with open(os.path.join(dem_dir, "provenance.json")) as f:
        prov = json.load(f)
    xmin, ymin, xmax, ymax = prov["clip_bounds_native"]
    epsg = prov["native_crs"].split(":")[1]
    w = int(round((xmax - xmin) / 0.5))
    h = int(round((ymax - ymin) / 0.5))
    params = {
        "bbox": f"{xmin},{ymin},{xmax},{ymax}",
        "bboxSR": epsg, "imageSR": epsg,
        "size": f"{w},{h}", "format": "png", "f": "image",
    }
    url = EXPORT + "?" + urllib.parse.urlencode(params)
    out_dir = os.path.join(ROOT, "data", "comparators", slug, "imagery")
    os.makedirs(out_dir, exist_ok=True)
    out_png = os.path.join(out_dir, "esri_world_imagery_0p5m.png")
    req = urllib.request.Request(url, headers={
        "User-Agent": "amphitheatre-comparator-research/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r, open(out_png, "wb") as f:
        f.write(r.read())
    meta = {
        "source": "Esri World Imagery export endpoint",
        "request_url": url,
        "bounds_native": [xmin, ymin, xmax, ymax],
        "crs": prov["native_crs"],
        "px_size_m": 0.5,
        "size_px": [w, h],
        "acquisition_date": "UNKNOWN (mosaic) — derived measurements are INFERRED",
        "attribution": "Esri, Maxar, Earthstar Geographics, USDA, USGS, "
                       "AeroGRID, IGN, GIS User Community",
        "fetched_on": "2026-06-12",
    }
    with open(os.path.join(out_dir, "imagery_meta.json"), "w") as f:
        json.dump(meta, f, indent=1)
    print(f"{slug}: {w}x{h} px -> {out_png}")


def main():
    for slug in SITES:
        fetch(slug)


if __name__ == "__main__":
    main()
