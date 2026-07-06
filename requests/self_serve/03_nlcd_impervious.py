"""NLCD 2021 percent-impervious clip over the WIDE AOI (MRLC WCS).

Closes: DATA_GAPS 'Land cover (impervious vs pervious) — NOT INGESTED' (E-3) at
the mapped level. Output: nlcd_2021_impervious_wide.tif + stats to stdout.
"""

import urllib.parse
import urllib.request

import numpy as np
import rasterio
from pyproj import Transformer

from aoi import TIGHT, WIDE

COVERAGE = "mrlc_download__NLCD_2021_Impervious_L48"
WCS = "https://www.mrlc.gov/geoserver/ows"

t = Transformer.from_crs(4326, 5070, always_xy=True)


def bbox_5070(bbox):
    x0, y0, x1, y1 = bbox
    xs, ys = zip(t.transform(x0, y0), t.transform(x1, y0), t.transform(x1, y1), t.transform(x0, y1))
    return min(xs), min(ys), max(xs), max(ys)


X0, Y0, X1, Y1 = bbox_5070(WIDE)
params = [
    ("service", "WCS"),
    ("version", "2.0.1"),
    ("request", "GetCoverage"),
    ("coverageid", COVERAGE),
    ("subset", f"X({X0:.1f},{X1:.1f})"),
    ("subset", f"Y({Y0:.1f},{Y1:.1f})"),
    ("format", "image/geotiff"),
]
url = WCS + "?" + urllib.parse.urlencode(params)
with urllib.request.urlopen(url, timeout=180) as r:
    blob = r.read()
if not blob.startswith(b"II") and not blob.startswith(b"MM"):
    raise SystemExit("Not a TIFF — server said:\n" + blob[:500].decode(errors="replace"))

out = "nlcd_2021_impervious_wide.tif"
with open(out, "wb") as f:
    f.write(blob)

with rasterio.open(out) as src:
    a = src.read(1).astype(float)
    a[a > 100] = np.nan  # nodata
    print(f"clip: {src.width}x{src.height} px @30m, CRS {src.crs}")
    print(f"WIDE AOI  mean impervious: {np.nanmean(a):.1f}%  (p50 {np.nanpercentile(a,50):.0f}%, p90 {np.nanpercentile(a,90):.0f}%)")

    tx0, ty0, tx1, ty1 = bbox_5070(TIGHT)
    r0, c0 = src.index(tx0, ty1)
    r1, c1 = src.index(tx1, ty0)
    sub = a[max(r0, 0):r1 + 1, max(c0, 0):c1 + 1]
    print(f"TIGHT bowl mean impervious: {np.nanmean(sub):.1f}%  ({sub.size} px)")
