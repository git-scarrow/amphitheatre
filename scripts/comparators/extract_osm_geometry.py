#!/usr/bin/env python3
"""Project OSM features for each comparator site into the site's native UTM
CRS and write per-site GeoJSON (osm_features.geojson, native CRS).

Source: data/comparators/_sources/overpass_detail.json + overpass_sites.json
(raw Overpass API responses, archived 2026-06-12). The stage building
footprint (osm_stage_way in sites.py) is the PRIMARY stage geometry anchor —
digitized by OSM contributors from imagery, so it is labeled inferred and is
cross-checked against our own Esri imagery digitization (see site_config).

Reproduce:  .venv/bin/python scripts/comparators/extract_osm_geometry.py
"""
import json
import math
import os
import sys

import pyproj

sys.path.insert(0, os.path.dirname(__file__))
from sites import SITES

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC = os.path.join(ROOT, "data", "comparators", "_sources")


def load_elements():
    els = {}
    for fn in ("overpass_sites.json", "overpass_detail.json"):
        with open(os.path.join(SRC, fn)) as f:
            for e in json.load(f)["elements"]:
                els[(e["type"], e["id"])] = e
    return list(els.values())


def main():
    elements = load_elements()
    for slug, site in SITES.items():
        with open(os.path.join(ROOT, "data", "comparators", slug,
                               "dem", "provenance.json")) as f:
            prov = json.load(f)
        crs = prov["native_crs"]
        tr = pyproj.Transformer.from_crs("EPSG:4326", crs, always_xy=True)
        cx, cy = prov["center_native_xy"]
        feats = []
        for e in elements:
            if "geometry" not in e or not e.get("tags"):
                continue
            pts = [tr.transform(p["lon"], p["lat"]) for p in e["geometry"]]
            # keep features within the clip
            if not any(abs(x - cx) < 400 and abs(y - cy) < 400 for x, y in pts):
                continue
            closed = len(pts) > 2 and (
                math.dist(pts[0], pts[-1]) < 0.01)
            geom = {"type": "Polygon", "coordinates": [list(map(list, pts))]} \
                if closed else \
                {"type": "LineString", "coordinates": list(map(list, pts))}
            props = dict(e["tags"])
            props["osm_id"] = e["id"]
            props["osm_type"] = e["type"]
            props["provenance"] = "OSM via Overpass API 2026-06-12 (inferred)"
            if e["id"] == site["osm_stage_way"]:
                props["role"] = "stage_structure_footprint"
            feats.append({"type": "Feature", "geometry": geom,
                          "properties": props})
        out = {"type": "FeatureCollection",
               "crs_note": f"coordinates in {crs} (meters)",
               "features": feats}
        out_path = os.path.join(ROOT, "data", "comparators", slug,
                                "osm_features.geojson")
        with open(out_path, "w") as f:
            json.dump(out, f)
        stage = [ft for ft in feats
                 if ft["properties"].get("role") == "stage_structure_footprint"]
        print(f"{slug}: {len(feats)} features, stage footprint "
              f"{'FOUND' if stage else 'MISSING'} -> {out_path}")


if __name__ == "__main__":
    main()
