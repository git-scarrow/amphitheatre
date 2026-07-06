"""Shared AOI definitions for the self-serve public-data pulls (2026-07-06).

WIDE covers the park plus the blocks south/east that could plausibly drain to the
pit through the storm network (the ~19 ac back-calc case). TIGHT is the bowl itself.
Coordinates are WGS84 lon/lat.
"""

# lon_min, lat_min, lon_max, lat_max
WIDE = (-84.9640, 45.3690, -84.9520, 45.3760)
TIGHT = (-84.9600, 45.3735, -84.9565, 45.3757)

SITE = (-84.9582, 45.3746)  # bowl centre, from DATA_GAPS.md


def wkt_polygon(bbox):
    x0, y0, x1, y1 = bbox
    return (
        f"POLYGON(({x0} {y0}, {x1} {y0}, {x1} {y1}, {x0} {y1}, {x0} {y0}))"
    )


def envelope_params(bbox):
    x0, y0, x1, y1 = bbox
    return {
        "geometry": f"{x0},{y0},{x1},{y1}",
        "geometryType": "esriGeometryEnvelope",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
    }
