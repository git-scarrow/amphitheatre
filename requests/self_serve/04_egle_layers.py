"""EGLE ArcGIS open-data pull over the WIDE AOI.

Pre-answers parts of requests/07 (EGLE FOIA) and dossier F-5:
  RRDOpenData: Part 201 sites (0), USTs (1), Brownfields (3), use restrictions (4/5)
  WrdOpenData: Environmental Areas (0), Critical Dunes (2), High-Risk Erosion (4),
               Local Wetland Ordinances (6), NWI 2005 (9), Part 303 Inventory (11)
Output: egle_layers.json — summary to stdout. NPDES outfalls are NOT here; those
stay in the EGLE FOIA / MiWaters manual check.
"""

import json
import urllib.parse
import urllib.request

from aoi import WIDE, envelope_params

BASE = "https://gisagoegle.state.mi.us/arcgis/rest/services/EGLE"
TARGETS = [
    ("RRDOpenData", 0, "part201_sites"),
    ("RRDOpenData", 1, "underground_storage_tanks"),
    ("RRDOpenData", 3, "brownfields"),
    ("RRDOpenData", 4, "use_restriction_points"),
    ("RRDOpenData", 5, "use_restriction_polygons"),
    ("WrdOpenData", 0, "environmental_areas"),
    ("WrdOpenData", 2, "critical_dune_areas"),
    ("WrdOpenData", 4, "high_risk_erosion_zones"),
    ("WrdOpenData", 6, "local_wetland_ordinances"),
    ("WrdOpenData", 9, "nwi_2005"),
    ("WrdOpenData", 11, "part303_state_wetland_inventory"),
]

out = {}
for svc, layer, name in TARGETS:
    params = dict(envelope_params(WIDE))
    params.update({"outFields": "*", "returnGeometry": "false", "f": "json"})
    url = f"{BASE}/{svc}/MapServer/{layer}/query?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=90) as r:
            out[name] = json.load(r)
    except Exception as e:
        out[name] = {"error": str(e)}

with open("egle_layers.json", "w") as f:
    json.dump(out, f, indent=1)

for name, data in out.items():
    feats = data.get("features")
    if feats is None:
        print(f"{name}: ERROR {data.get('error') or data}")
        continue
    print(f"{name}: {len(feats)} features")
    for ft in feats[:8]:
        attrs = ft["attributes"]
        keep = {k: v for k, v in attrs.items() if v not in (None, "", " ")}
        print("  ", json.dumps(keep)[:300])
