# Data Inventory — truth package / web viewer build (2026-06-11)

Pre-coding inventory required by the viewer-package brief. Establishes which
repo files are source of truth, what can be rendered honestly, and which
checks are computable vs unknown.

## 1. Source-of-truth geometry files found

The **current accepted design** is the Scenario E three-section civic bowl
(east / bend / south), per `docs/DESIGN_CANON.md` (Scenario D baseline +
Scenario E seating/ADA/drainage ACCEPTED; stage refit OPEN per Rule 9).
The in-situ package (`scripts/build_in_situ_package.sh`, audit-gated by
`scripts/audit_in_situ_package.py`) is the governing geometry expression:

| Element | File | Notes |
|---|---|---|
| Seating treads (45 bands, rows 1–18 ×3 sections, minus rows 5/9/10) | `vectors_geojson/terrace_treads.geojson` | per-tread `tread_elev_navd88`, `seats_kept`, `C_mm`, section, zone |
| Terrace edges / risers | `vectors_geojson/terrace_edges.geojson` | derived from treads |
| Stage core + shoulders, cross-aisle, ADA routes A/B + 5 landings, swales, treatment cell, event floor, promenades | `vectors_geojson/bowl_zones.geojson` | stage is `geometry_source: scenarioE stage_surface (inherited)` — **provisional** |
| Site context (paths, rim, tree mass, bay corridor, streets) | `vectors_geojson/site_context.geojson` | mix of measured (`schematic: false`) and schematic features |
| Material zones / event modes | `vectors_geojson/material_zones.geojson`, `event_modes.geojson` | event modes are `nonbinding: true` |
| Canonical viewpoints (6) | `vectors_geojson/in_situ_viewpoints.geojson` | eye XY + NAVD88 elev + look target + azimuth |
| Bay-view axis + focal point | `design_open_low/stage_floor.geojson` (`bay_view_axis`, `focal_point_stage_front`) | az 330° toward Little Traverse Bay; inherited lineage |
| Emission validation (per-segment) | `analysis/tier_emission/Scenario_E_baseline_reemit/{geometry.geojson,segments.csv,validation.json}` | strict Band-A, per-row C, ADA, swales, volumes |
| Earthwork (component CY) | `analysis/scenarioE_civic/earthwork.csv`, `dem/in_situ_grading_manifest.json` | 500.8 CY gross (validated proxy) |
| Engineering stormwater train | `package/07_stormwater/treatment_train.geojson` | forebay / WQ cell / outlet — earlier package generation |
| Pending human decision | `analysis/decision_packet/decision_table.csv`, `docs/HUMAN_DECISION_BRIEF.md` | Decision 1 (seating scope) NOT yet made |

**Superseded (do not present as current):** `design_open_low/seating_rows.geojson`,
`package/05_seating/*`, `stage4/*` — earlier single-fan generations. The brief's named
files (`seating_rows.geojson`, `stage_floor.geojson`, `ada_route.geojson`,
`sightline_table.csv`, `seat_count.md`) exist there but encode the superseded fan;
their current-design equivalents are the in-situ/tier-emission files above.
Exception: `design_open_low/stage_floor.geojson` still sources the inherited stage,
focal point, bay-view axis, and treatment-cell footprint lineage.

## 2. Terrain rasters

**Found (real, LiDAR-derived — no placeholder needed):**

- `dem/dem_design_1ft.tif` — existing ground, 801×801 @ 1 ft, EPSG:6494
- `dem/dem_context_2p5ft.tif` — context, 641×641 @ 2.5 ft (1,600 ft square)
- `dem/proposed_grade_1ft.tif` — proposed grade (treads/aisle/swales/cell burned; ADA ramps and stage deck NOT burned — see grading manifest flags)
- `dem/cut_fill_1ft.tif` — proposed − existing
- Source LiDAR: `data/USGS_LPC_MI_13County_2015_C16_*.laz` (2015 USGS) + eastern supplement

Rasters are planning-grade (2015 LiDAR + supplement), not survey.

## 3. CRS / vertical datum (from `docs/datum_note.md`)

- Horizontal: **EPSG:6494** NAD83(2011) / Michigan Central, **INTERNATIONAL feet** (false easting ≈ 19,685,039 ft — misreading as US-survey ft shifts easting ~39 ft).
- Vertical: **NAVD88, Geoid12A, intl ft**.
- Bay level quoted in IGLD85; working conversion Δ = +0.40 ft is a **labelled assumption**, unconfirmed.

## 4. Layers renderable truthfully (source-of-truth)

Terrain (existing + proposed, labelled planning-grade); 45 seating treads at
design elevations; stage deck footprint (rendered, but flagged PROVISIONAL —
Rule 9 open); cross-aisle; ADA routes A/B + landings; swales; bay-view axis;
per-row sightline status (from validation.json); cut/fill overlay.

## 5. Illustrative-only layers

Treatment-cell shaping (concept tier — schematic 4:1 shaping, `cost_status:
concept`); orchestra/event floor (schematic zone on existing grade); event-mode
overlays (nonbinding); parts of site context flagged `schematic: true`
(tree mass, some paths); row labels (annotation); any vegetation/water rendering.

## 6. Checks computable now (from repo data, with provenance)

- Seat counts: 1,283 nominal (sum of tread `seats_kept`), 1,243 strict Band-A (validation.json `banded`).
- Per-row sightline C (mm) for 42/45 treads (rows 1 have no row in front; canon: south r18 2.2 mm under 90 mm bar = WARN; bend r1 at 2.5% cross-slope ceiling = WARN).
- ADA running slope 8.33%, flights/landings, `running_ok` both routes (validation.json) — planning-grade only.
- Cross-aisle: level/wheelable/drains (validation.json).
- Drainage swales fall toward cell, 0 tread conflicts.
- Earthwork: 500.8 CY gross validated proxy + grading-manifest raster volumes — **with the known understatement caveat (~2–2.6×, TIER_EMISSION_VALIDATION.md)**.
- Bay-view: measured EPT result (rim never blocks bay for mid/upper rows; foreground tree screen governs 330 vs 315).

## 7. Checks that must be reported UNKNOWN

Groundwater seasonal high; geotech/bearing; IGLD85↔NAVD88 Δ confirmation;
stage structure/acoustics (Rule 9 unresolved); full ADA code compliance
(cross-slopes on built ramps, handrails, clearances); egress/life-safety
capacity; permitting/zoning; utility conflicts; survey-grade boundary;
construction cost; tree survey (governs bay-view tuning).
