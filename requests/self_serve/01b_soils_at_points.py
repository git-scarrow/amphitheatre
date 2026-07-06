"""Which soil map unit covers key design points (bowl centre, NW 589-ft low, stage)?

The NW-low coordinates come from DATA_GAPS.md in EPSG:6494 intl ft and are converted
with pyproj. Output: soils_at_points.json + stdout table.
"""

import json
import urllib.request

from pyproj import Transformer

SDA = "https://sdmdataaccess.nrcs.usda.gov/TABULAR/post.rest"

t = Transformer.from_crs(6494, 4326, always_xy=True)
POINTS = {
    "bowl_centre": (-84.9582, 45.3746),
    "nw_589ft_low": t.transform(19532693.76, 751107.83),
    "north_rim_pour_point": t.transform(19532967.2, 750904.2),
}

out = {}
for name, (lon, lat) in POINTS.items():
    q = f"""
    SELECT mu.mukey, mu.musym, mu.muname, c.compname, c.comppct_r, c.hydgrp
    FROM mupolygon p
    JOIN mapunit mu ON p.mukey = mu.mukey
    JOIN component c ON mu.mukey = c.mukey AND c.majcompflag = 'Yes'
    WHERE p.mupolygongeo.STIntersects(
        geometry::STGeomFromText('POINT({lon} {lat})', 4326)) = 1
    """
    payload = json.dumps({"query": q, "format": "JSON+COLUMNNAME"}).encode()
    req = urllib.request.Request(
        SDA, data=payload, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        out[name] = {"lonlat": (lon, lat), "result": json.load(r).get("Table", [])}

with open("soils_at_points.json", "w") as f:
    json.dump(out, f, indent=1)

for name, rec in out.items():
    rows = rec["result"]
    lon, lat = rec["lonlat"]
    print(f"{name} ({lon:.5f}, {lat:.5f}):")
    for row in rows[1:] or [["(no map unit — water/urban?)"]]:
        print("  ", row)
