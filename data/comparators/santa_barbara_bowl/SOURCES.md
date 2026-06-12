# Santa Barbara Bowl — source notes

Site: Santa Barbara Bowl, 1122 N Milpas St, Santa Barbara, CA.
Benchmark role: larger terraced-bowl comparator (4,562 seats, canyon site).

## Terrain (measured basis)
- Product: **USGS one meter x25y382 CA Montecito** (3DEP 1 m DEM)
  - URL: https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/1m/Projects/CA_Montecito_2018/TIFF/USGS_one_meter_x25y382_CA_Montecito_2018.tif
  - LiDAR project: CA_Montecito_2018 (acquired 2018, published 2020-03-31)
  - CRS: EPSG:26911 (NAD83 / UTM 11N, m); vertical NAVD88 m
  - Discovery: TNM Access API query archived at
    `data/comparators/_sources/tnm_sb.json`
  - Post-dates the 2002 stage rebuild and 2000s terrace work → geometry is
    current. A second covering product (CA SoCal Wildfires B4 2018) exists;
    Montecito chosen for project specificity.
- Clip: `dem/dem_clip_1m.tif` via `scripts/comparators/fetch_comparator_dem.py`
  (GDAL /vsicurl/ windowed read; provenance in `dem/provenance.json`).

## Geometry anchors (inferred basis)
- OSM stage-house footprint: way 623261253 ("Santa Barbara Bowl",
  amenity=theatre). Raw Overpass responses in `data/comparators/_sources/`.
  Min rotated rect: 125 × 79 ft, long axis az 5.8° → audience facing az 95.8°.
- Esri World Imagery clip (`imagery/`): mosaic, acquisition date unknown —
  everything digitized from it is INFERRED (see `site_config.json`
  `_provenance` and per-field `_basis` notes).
- Stage deck frontage 92 ft (range 85–100) read from hillshade/imagery deck
  edge; independently cross-checkable against the OSM footprint (125 ft incl.
  wings = upper bound) and the published 2002 rebuild figure (stage +
  backstage = 10,000 sq ft total, which a ~92 × 50 ft deck + house fits).

## Published facts
- Capacity 4,562; built 1936 (WPA); stage rebuilt 2002 (3,000 → 10,000 sq ft
  stage+backstage); ADA platform 2003; terrace (McCaw) 2004.
  Source: https://en.wikipedia.org/wiki/Santa_Barbara_Bowl (renovation table
  cites Lassen, "Fixing the Bowl", Santa Barbara Independent, 2011).
- Seating bands: floor T/U/V (reserved) or GA standing; sections A–C / D–I /
  J–O. Source: https://sbbowl.com/seating-chart/
- No official stage W×D spec found online (sbbowl.com production page is
  video-only); stage dims remain INFERRED with the cross-checks above.

## Processing chain (reproduce in order)
```
.venv/bin/python scripts/comparators/fetch_comparator_dem.py
.venv/bin/python scripts/comparators/fetch_imagery.py
.venv/bin/python scripts/comparators/extract_osm_geometry.py
.venv/bin/python scripts/comparators/render_diagnostics.py
.venv/bin/python scripts/comparators/extract_sections.py
.venv/bin/python scripts/comparators/fit_bowl_arcs.py
.venv/bin/python scripts/comparators/extract_metrics.py
```

## Known limits
- 1 m bare-earth DEM cannot resolve individual ~1 ft bench risers — row
  counts and seat-level sightlines are NOT derived from this DEM.
- Bare-earth filtering under the stage house returns ground, not deck.
- Fan/radii are measured about the stage-front anchor (anchor itself
  inferred from the OSM footprint).
