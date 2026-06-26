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
# Mirrors tried in order; public Overpass instances return 504/429 under load, so a
# fetch retries with backoff and rolls to the next endpoint before giving up.
OVERPASS_MIRRORS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
)
# Overpass returns HTTP 406 to the default python-urllib User-Agent; a descriptive
# UA is required (and is good open-data etiquette — identifies the caller).
HTTP_HEADERS = {
    "User-Agent": "amphitheatre-civicbowl-context/0.1 (Petoskey Pit review scene; sscarrow@gmail.com)",
    "Accept": "application/json",
}


def robust_post(query: str, attempts: int = 3) -> list[dict]:
    """POST an Overpass query, retrying with backoff across mirrors on 429/504/timeout."""
    import time
    import urllib.error
    import urllib.parse
    import urllib.request
    data = urllib.parse.urlencode({"data": query}).encode()
    last = None
    for endpoint in OVERPASS_MIRRORS:
        for attempt in range(attempts):
            try:
                req = urllib.request.Request(endpoint, data=data, headers=HTTP_HEADERS)
                with urllib.request.urlopen(req, timeout=180) as resp:
                    return json.load(resp).get("elements", [])
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
                last = exc
                code = getattr(exc, "code", None)
                if code in (400, 403, 406):   # request-level error — retrying won't help
                    raise
                wait = 3 * (attempt + 1)
                print(f"[fetch]   {endpoint.split('//')[1].split('/')[0]} "
                      f"attempt {attempt + 1}/{attempts} failed ({exc}); retry in {wait}s")
                time.sleep(wait)
        print(f"[fetch]   giving up on {endpoint}; rolling to next mirror")
    raise SystemExit(f"[fetch] all Overpass mirrors failed: {last}")
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


# City_LoFi context beyond buildings/roads: green space, water EDGE, and labels.
# Deliberately query water/coastline as *ways* (not the Lake Michigan relation) so
# we get only local shoreline segments inside the bbox, never the whole lake. The
# bay edge is drawn as a cartographic LINE (a polygon ring traced as a LineString),
# never a filled water slab.
def context_query(bbox=BBOX) -> str:
    s, w, n, e = bbox
    return (f"[out:json][timeout:90];\n"
            f"(\n"
            f"  way[\"leisure\"~\"^(park|garden|nature_reserve|common)$\"]({s},{w},{n},{e});\n"
            f"  way[\"landuse\"~\"^(recreation_ground|grass)$\"]({s},{w},{n},{e});\n"
            f"  way[\"natural\"=\"coastline\"]({s},{w},{n},{e});\n"
            f"  way[\"natural\"=\"water\"]({s},{w},{n},{e});\n"
            f"  node[\"place\"~\"^(town|village|suburb|neighbourhood|locality)$\"]({s},{w},{n},{e});\n"
            f");\n"
            f"out geom;")


# The Little Traverse Bay shore is the boundary of the Lake Michigan water *relation*;
# its member ways carry no own tag (so the plain natural=water way query misses them).
# Pull the relation's member ways CLIPPED to the bbox -> just the local bay edge, not
# the whole lake. role=bay_shoreline marks them for the cartographic bay-edge layer.
def shoreline_query(bbox=BBOX) -> str:
    s, w, n, e = bbox
    return (f"[out:json][timeout:120];\n"
            f"rel[\"natural\"=\"water\"]({s},{w},{n},{e})->.w;\n"
            f"way(r.w)({s},{w},{n},{e});\n"
            f"out geom;")


# Harbor man-made structures: breakwaters + piers (the protrusions into the bay)
# and the marina/harbour basin polygon. These let gen_context.py (a) carve the
# harbor basin to water and (b) re-draw the breakwaters/piers as thin structures
# surrounded by water instead of one fused land peninsula.
def harbor_query(bbox=BBOX) -> str:
    s, w, n, e = bbox
    return (f"[out:json][timeout:120];\n"
            f"(\n"
            f"  way[\"man_made\"=\"breakwater\"]({s},{w},{n},{e});\n"
            f"  way[\"man_made\"=\"pier\"]({s},{w},{n},{e});\n"
            f"  way[\"man_made\"=\"groyne\"]({s},{w},{n},{e});\n"
            f"  way[\"leisure\"=\"marina\"]({s},{w},{n},{e});\n"
            f"  node[\"man_made\"=\"lighthouse\"]({s},{w},{n},{e});\n"
            f");\n"
            f"out tags geom;")


def _harbor_features(elements: list[dict]) -> list[dict]:
    out = []
    for el in elements:
        tags = el.get("tags", {})
        if el.get("type") == "node" and tags.get("man_made") == "lighthouse":
            out.append({
                "type": "Feature",
                "properties": {"osm_id": el["id"], "kind": "lighthouse", "name": tags.get("name")},
                "geometry": {"type": "Point", "coordinates": [el["lon"], el["lat"]]},
            })
            continue
        if el.get("type") != "way" or "geometry" not in el:
            continue
        coords = [[p["lon"], p["lat"]] for p in el["geometry"]]
        if len(coords) < 2:
            continue
        kind = tags.get("man_made") or tags.get("leisure")
        if kind == "marina":                       # basin polygon (water to carve)
            if coords[0] != coords[-1]:
                coords = coords + [coords[0]]
            geom = {"type": "Polygon", "coordinates": [coords]}
        else:                                       # breakwater / pier / groyne centreline
            geom = {"type": "LineString", "coordinates": coords}
        out.append({
            "type": "Feature",
            "properties": {"osm_id": el["id"], "kind": kind, "name": tags.get("name")},
            "geometry": geom,
        })
    return out


def _shoreline_features(elements: list[dict]) -> list[dict]:
    out = []
    for el in elements:
        if el.get("type") != "way" or "geometry" not in el:
            continue
        coords = [[p["lon"], p["lat"]] for p in el["geometry"]]
        if len(coords) < 2:
            continue
        out.append({
            "type": "Feature",
            "properties": {"osm_id": el["id"], "natural": "water", "role": "bay_shoreline",
                           "name": el.get("tags", {}).get("name"),
                           "source_note": "Lake Michigan / Little Traverse Bay water-relation member edge"},
            "geometry": {"type": "LineString", "coordinates": coords},
        })
    return out


def _split_context(elements: list[dict]):
    """Classify a context 'out geom' response into parks / water-edges / places."""
    parks, water, places = [], [], []
    for el in elements:
        tags = el.get("tags", {})
        t = el.get("type")
        if t == "node" and "place" in tags:
            places.append({
                "type": "Feature",
                "properties": {"osm_id": el["id"], "place": tags.get("place"),
                               "name": tags.get("name")},
                "geometry": {"type": "Point", "coordinates": [el["lon"], el["lat"]]},
            })
            continue
        if t != "way" or "geometry" not in el:
            continue
        coords = [[p["lon"], p["lat"]] for p in el["geometry"]]
        if len(coords) < 2:
            continue
        leisure, landuse, natural = tags.get("leisure"), tags.get("landuse"), tags.get("natural")
        if leisure in ("park", "garden", "nature_reserve", "common") or \
                landuse in ("recreation_ground", "grass"):
            if coords[0] != coords[-1]:
                coords = coords + [coords[0]]
            parks.append({
                "type": "Feature",
                "properties": {"osm_id": el["id"], "kind": leisure or landuse,
                               "name": tags.get("name")},
                "geometry": {"type": "Polygon", "coordinates": [coords]},
            })
        elif natural in ("coastline", "water"):
            # Water EDGE as a polyline (ring for a water polygon, line for coastline).
            role = "bay_shoreline" if natural == "coastline" else "inland_water_edge"
            water.append({
                "type": "Feature",
                "properties": {"osm_id": el["id"], "natural": natural, "role": role,
                               "name": tags.get("name")},
                "geometry": {"type": "LineString", "coordinates": coords},
            })
    return parks, water, places


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
    paths = {
        "buildings": os.path.join(outdir, "osm_petoskey_buildings.geojson"),
        "roads": os.path.join(outdir, "osm_petoskey_roads.geojson"),
        "parks": os.path.join(outdir, "osm_petoskey_parks.geojson"),
        "water_edge": os.path.join(outdir, "osm_petoskey_water_edge.geojson"),
        "places": os.path.join(outdir, "osm_petoskey_places.geojson"),
        "harbor": os.path.join(outdir, "osm_petoskey_harbor.geojson"),
    }

    print("== OSM city-context fetch (OpenStreetMap, ODbL) ==")
    print(f"bbox (S,W,N,E): {BBOX}")
    print(f"endpoint      : {OVERPASS_URL}")
    for k, p in paths.items():
        print(f"{k:10s} -> : {p}")
    print("\nOverpass QL (buildings/roads):\n" + overpass_query())
    print("\nOverpass QL (parks/water-edge/places):\n" + context_query())
    print("\nOverpass QL (harbor structures):\n" + harbor_query())

    if not args.run:
        print("\n(interface mode — no network call. Re-run with --run to download.)")
        print("buildings/roads feed city_massing/city_roads; parks/water_edge/places feed")
        print("city_parks/bay_edge_cartographic/city_labels. Absent them those layers DEFER.")
        return 0

    os.makedirs(outdir, exist_ok=True)

    print("\n[fetch] POSTing buildings/roads …")
    buildings, roads = _to_geojson(robust_post(overpass_query()))
    with open(paths["buildings"], "w") as fh:
        json.dump(_fc(buildings, "buildings"), fh)
    with open(paths["roads"], "w") as fh:
        json.dump(_fc(roads, "roads"), fh)

    print("[fetch] POSTing parks/water-edge/places …")
    parks, water, places = _split_context(robust_post(context_query()))
    print("[fetch] POSTing bay shoreline (water-relation member edges, bbox-clipped) …")
    shoreline = _shoreline_features(robust_post(shoreline_query()))
    water = water + shoreline
    n_bay = sum(1 for f in water if f["properties"].get("role") == "bay_shoreline")
    print("[fetch] POSTing harbor structures (breakwaters/piers/marina) …")
    harbor = _harbor_features(robust_post(harbor_query()))
    with open(paths["parks"], "w") as fh:
        json.dump(_fc(parks, "parks"), fh)
    with open(paths["water_edge"], "w") as fh:
        json.dump(_fc(water, "water_edge"), fh)
    with open(paths["places"], "w") as fh:
        json.dump(_fc(places, "places"), fh)
    with open(paths["harbor"], "w") as fh:
        json.dump(_fc(harbor, "harbor"), fh)

    print(f"[fetch] wrote {len(buildings)} buildings, {len(roads)} roads, "
          f"{len(parks)} parks, {len(water)} water-edges ({n_bay} bay-shoreline), "
          f"{len(places)} places, {len(harbor)} harbor structures")
    print("[fetch] now run: python scripts/unreal/gen_context.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
