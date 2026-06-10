# QGIS project — in-situ package

Open `in_situ_package.qgs` in QGIS ≥3.28. All layer paths are **relative**
(`../vectors_geojson/…`, `../dem/…`), so the project works from any checkout
location.

Expected on a fresh checkout: the three raster layers (existing DEM, proposed
grade, cut/fill) are reported *unavailable* because rasters are gitignored —
see `../dem/MISSING_DATA.md` for how to rebuild them, then reopen. Vector
layers load with default styling; this project is a review scaffold, not a
styled deliverable.

CRS: EPSG:6494 (NAD83(2011) / Michigan Central, **international feet**),
elevations NAVD88 (Geoid12A) intl ft — see `../docs/datum_note.md`.
