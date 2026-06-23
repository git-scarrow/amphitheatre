#!/usr/bin/env python3
"""Reproducible OSM city-context fetch for the CivicBowl scene (interface + runner).

Open data only (OpenStreetMap, ODbL). NO Google/Maps/Earth assets. Downloads
building footprints + road centerlines around Petoskey from the Overpass API and
writes them as EPSG:4326 GeoJSON to ``data/context/`` — the exact paths the
context generator (``gen_context.py``) expects.

By default this prints the Overpass query + the expected output paths WITHOUT
touching the network (so it documents the acquisition path in environments with
no egress). Pass ``--run`` to actually fetch (needs outbound HTTPS).

    python scripts/unreal/fetch_osm_context.py            # show query + paths
    python scripts/unreal/fetch_osm_context.py --run      # download -> data/context/

Output (consumed by gen_context.py; ODbL — keep the attribution):
    data/context/osm_petoskey_buildings.geojson   (Polygon features)
    data/context/osm_petoskey_roads.geojson       (LineString features)
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import civicbowl_common as cb  # noqa: E402
import context_common as ctx   # noqa: E402

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
# bbox around the site toward the bay (NNW). [south, west, north, east].
# Centred on the site (45.3746, -84.9581); reaches ~1.7 km N to the waterfront.
BBOX = (45.3640, -84.9820, 45.3900, -84.9360)
ATTRIBUTION = "(c) OpenStreetMap contributors, ODbL"


def overpass_query(bbox=BBOX) -> str:
    s, w, n, e = bbox
    return (f"[out:json][timeout:60];\n"
            f"(\n"
            f"  way[\"building\"]({s},{w},{n},{e});\n"
            f"  way[\"highway\"]({s},{w},{n},{e});\n"
            f");\n"
            f"out geom;")


def _to_geojson(elements: list[dict]):
    """Split Overpass 'out geom' ways into building polygons + road lines."""
    buildings, roads = [], []
    for el in elements:
        if el.get("type") != "way" or "geometry" not in el:
            continue
        coords = [[p["lon"], p["lat"]] for p in el["geometry"]]
        tags = el.get("tags", {})
        if "building" in tags and len(coords) >= 4:
            if coords[0] != coords[-1]:
                coords = coords + [coords[0]]
            buildings.append({
                "type": "Feature",
                "properties": {"osm_id": el["id"], "building": tags.get("building"),
                               "height": tags.get("height"),
                               "building:levels": tags.get("building:levels"),
                               "name": tags.get("name")},
                "geometry": {"type": "Polygon", "coordinates": [coords]},
            })
        elif "highway" in tags and len(coords) >= 2:
            roads.append({
                "type": "Feature",
                "properties": {"osm_id": el["id"], "highway": tags.get("highway"),
                               "name": tags.get("name")},
                "geometry": {"type": "LineString", "coordinates": coords},
            })
    return buildings, roads


def _fc(features, kind):
    return {"type": "FeatureCollection", "attribution": ATTRIBUTION,
            "source": "OpenStreetMap via Overpass API", "kind": kind,
            "crs_note": "EPSG:4326 lon/lat; reprojected to EPSG:6494->ENU by gen_context.py",
            "features": features}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=None)
    ap.add_argument("--run", action="store_true", help="actually hit the Overpass API (needs HTTPS egress)")
    args = ap.parse_args()
    root = cb.repo_root(args.repo)
    outdir = os.path.join(root, "data", "context")
    b_path = os.path.join(outdir, "osm_petoskey_buildings.geojson")
    r_path = os.path.join(outdir, "osm_petoskey_roads.geojson")

    print("== OSM city-context fetch (OpenStreetMap, ODbL) ==")
    print(f"bbox (S,W,N,E): {BBOX}")
    print(f"endpoint      : {OVERPASS_URL}")
    print(f"buildings ->  : {b_path}")
    print(f"roads     ->  : {r_path}")
    print("\nOverpass QL:\n" + overpass_query())

    if not args.run:
        print("\n(interface mode — no network call. Re-run with --run to download.)")
        print("These two paths are exactly what gen_context.py looks for; absent them, the")
        print("city_massing / city_roads layers stay DEFERRED and are documented as such.")
        return 0

    import urllib.parse
    import urllib.request
    os.makedirs(outdir, exist_ok=True)
    data = urllib.parse.urlencode({"data": overpass_query()}).encode()
    print("\n[fetch] POSTing to Overpass …")
    with urllib.request.urlopen(urllib.request.Request(OVERPASS_URL, data=data), timeout=90) as resp:
        payload = json.load(resp)
    buildings, roads = _to_geojson(payload.get("elements", []))
    with open(b_path, "w") as fh:
        json.dump(_fc(buildings, "buildings"), fh)
    with open(r_path, "w") as fh:
        json.dump(_fc(roads, "roads"), fh)
    print(f"[fetch] wrote {len(buildings)} buildings, {len(roads)} roads")
    print("[fetch] now run: python scripts/unreal/gen_context.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
