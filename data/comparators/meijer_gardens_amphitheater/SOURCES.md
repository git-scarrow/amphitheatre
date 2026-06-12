# Frederik Meijer Gardens Amphitheater — source notes

Site: Frederik Meijer Gardens & Sculpture Park, 1000 E Beltline Ave NE,
Grand Rapids, MI.
Benchmark role: capacity-matched comparator (~1,900, tiered lawn bowl,
covered low stage, open landscape backdrop — closest typology to the
Petoskey open-air landscape venue).

## Terrain (measured basis)
- Product: **USGS one meter x61y476 MI 31Co Kent 2016** (3DEP 1 m DEM)
  - URL: https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/1m/Projects/MI_31Co_Kent_2016/TIFF/USGS_one_meter_x61y476_MI_31Co_Kent_2016.tif
  - LiDAR project: MI_31Co_Kent_2016 (acquired 2016, published 2020-03-30) —
    same Michigan statewide program family as the Petoskey 2015 13County data
  - CRS: EPSG:26916 (NAD83 / UTM 16N, m); vertical NAVD88 m
  - Discovery: TNM Access API query archived at
    `data/comparators/_sources/tnm_mg.json`
  - Post-dates the 2003 amphitheater construction → geometry is current.
- Clip: `dem/dem_clip_1m.tif` via `scripts/comparators/fetch_comparator_dem.py`
  (provenance in `dem/provenance.json`).

## Geometry anchors (inferred basis)
- OSM stage footprint: way 490428003 ("Frederik Meijer Gardens
  Amphitheater", amenity=theatre, theatre:type=amphi). Raw Overpass responses
  in `data/comparators/_sources/`.
  Min rotated rect: 110 × 54 ft lens-shaped canopy, long axis az 110.9° →
  audience facing az 20.9° (NNE, toward the pond backdrop).
- Esri World Imagery clip (`imagery/`): mosaic, acquisition date unknown —
  all derived dims INFERRED (per-field `_basis` in `site_config.json`).
- Stage frontage 100 ft (range 90–110) = canopy chord facing the lawn;
  cross-checkable against the OSM long dimension (110 ft).

## Published facts
- Tiered lawn seating for ~1,900; amphitheater opened 2003; covered stage.
  Source: https://en.wikipedia.org/wiki/Frederik_Meijer_Gardens — NOTE the
  passage is flagged "citation needed" there; the 1,900 figure is used
  venue-wide in concert-series press, but treat it as weakly published.
- No official stage W×D spec found (meijergardens.org attraction page has
  hours/rates only; concerts page 403s to bots).

## Processing chain
Same command sequence as the SB Bowl SOURCES.md.

## Known limits
- 1 m DEM smooths the stone seat-wall terraces (~18 in risers) — terrace
  count is imagery-inferred (~8–10 + lawn), not DEM-counted.
- Pond north of stage reads as flat 809.5 ft plane (water return).
- Fan/radii measured about the inferred stage-front anchor.

## Patch 1 additions (2026-06-12, tightening pass)

### Searches performed beyond the venue website
- Wayback CDX scan of meijergardens.org for PDFs / "amphitheat" /
  tech / rider / production URLs → no PDFs archived; no spec pages.
- Archived attraction pages 2014 + 2025 read in full: "terraced lawn
  seating", "ivy growing on the stage" — NO capacity number and NO stage
  dimensions have ever been published on the venue's own site.
- meijergardens.org/calendar/concerts/ → 403 to autonomous fetchers.

### Failed searches (logged per audit requirement)
- Technical rider / production packet: none archived, none on site.
- mlive / Grand Rapids Press 2003 construction articles: not reachable
  without an interactive search engine (WebSearch tool incompatible this
  session; Exa 401; DuckDuckGo robots-blocked).
- Kent County / Grand Rapids Twp parcel GIS + planning-board packets:
  interactive JS viewers, not scriptable here.
- Conclusion: capacity ~1,900 stays **published (weak)** — press-
  circulated lawn/event capacity, not a venue figure, not a fixed-seat
  count. Stage dims remain **inferred** from the OSM canopy footprint
  (110 × 54 ft lens) and imagery.
