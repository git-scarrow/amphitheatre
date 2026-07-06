"""FEMA NFHL pull — flood hazard zones, BFEs, and FIRM panels over the WIDE AOI.

Closes: DATA_GAPS 'Bear River / bay flood elevations (base flood, high-lake-stage)
in NAVD88 — UNKNOWN' at the mapped level (or documents that Emmet Co. is unmapped
in NFHL, which is itself the answer).
Output: fema_nfhl.json — summary printed to stdout.
"""

import json
import urllib.parse
import urllib.request

from aoi import WIDE, envelope_params

BASE = "https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer"
LAYERS = {
    "flood_hazard_zones": (28, "FLD_ZONE,ZONE_SUBTY,STATIC_BFE,SFHA_TF,FLD_AR_ID"),
    "base_flood_elevations": (16, "ELEV,LEN_UNIT,BFE_LN_ID"),
    "firm_panels": (3, "FIRM_PAN,PANEL,EFF_DATE,PANEL_TYP"),
}

out = {}
for name, (layer, fields) in LAYERS.items():
    params = dict(envelope_params(WIDE))
    params.update({"outFields": fields, "returnGeometry": "false", "f": "json"})
    url = f"{BASE}/{layer}/query?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            out[name] = json.load(r)
    except Exception as e:  # keep going; record the failure
        out[name] = {"error": str(e)}

with open("fema_nfhl.json", "w") as f:
    json.dump(out, f, indent=1)

for name, data in out.items():
    feats = data.get("features")
    if feats is None:
        print(f"{name}: ERROR {data.get('error') or data}")
        continue
    print(f"{name}: {len(feats)} features")
    for ft in feats[:20]:
        print("  ", ft["attributes"])
