"""NRCS Soil Data Access pull — map units + hydrologic soil group over the WIDE AOI.

Closes: DATA_GAPS 'Soil infiltration rate / hydrologic soil group — UNKNOWN' at the
*mapped* (not field-verified) level; narrows the CN 61<->85 bracket. Dossier C-1/E-3.
Output: nrcs_soils.json (raw) — summary printed to stdout.
"""

import json
import sys
import urllib.request

from aoi import WIDE, wkt_polygon

SDA = "https://sdmdataaccess.nrcs.usda.gov/TABULAR/post.rest"

QUERY = f"""
SELECT DISTINCT mu.mukey, mu.musym, mu.muname,
       c.compname, c.comppct_r, c.hydgrp, c.drainagecl, c.majcompflag
FROM mupolygon p
JOIN mapunit mu ON p.mukey = mu.mukey
JOIN component c ON mu.mukey = c.mukey
WHERE p.mupolygongeo.STIntersects(
    geometry::STGeomFromText('{wkt_polygon(WIDE)}', 4326)) = 1
ORDER BY mu.musym, c.comppct_r DESC
"""

payload = json.dumps({"query": QUERY, "format": "JSON+COLUMNNAME"}).encode()
req = urllib.request.Request(
    SDA, data=payload, headers={"Content-Type": "application/json"}
)
with urllib.request.urlopen(req, timeout=60) as r:
    data = json.load(r)

with open("nrcs_soils.json", "w") as f:
    json.dump(data, f, indent=1)

rows = data.get("Table", [])
if not rows:
    sys.exit("No rows returned — check AOI / SDA availability")

header, body = rows[0], rows[1:]
print("\t".join(header))
for row in body:
    print("\t".join(str(v) for v in row))
print(f"\n{len(body)} component rows -> nrcs_soils.json")
