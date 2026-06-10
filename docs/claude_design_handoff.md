# Claude Design handoff — three-section civic bowl, Petoskey Pit

**Purpose:** visual / prototype brief for Claude Design. Everything here
packages **audited repo outputs** (`scripts/audit_in_situ_package.py` green
as of this handoff). **Do not invent geometry** — consume the layers listed
below; where something is schematic it is flagged in the data itself.

CRS EPSG:6494 (intl ft) · NAVD88 (Geoid12A) intl ft · planning-grade.

## Approved design intent (must read in every image)

1. **Landscape venue, not a building.** The bowl is terraced parkland in a
   former pit; from the rim it reads as landscape. Backdrop = dry meadow
   foreground → tree band → **Little Traverse Bay + sky** (az 330, ~200 m).
2. **Three seating families, not one fan.** East / **bend (southeast)** /
   south sections, each contour-fitted with its own curvature, separated by
   hinge transitions (rays az 118°/152°) and the row-5 promenade band.
   1,283 Band-A seats, rows ≤ 18, total rise ~15 ft.
3. **The cross-aisle is a place.** Rows 9–10 became a level, wheelable
   622.01 bench — circulation + mid-bowl view pause.
4. **Low open stage.** Deck at event-floor grade with lateral floor-level
   shoulders only. Stage **axis is unresolved** (canon Rule 9 OPEN) — keep
   the stage visually low-key and provisional; never heroic architecture.
5. **Water is ephemeral or distant.** The treatment cell is a dry
   bioretention meadow that ponds only after large storms. The only standing
   water in any image is the bay.
6. **Minimal intervention.** Turf treads, low timber/stone seat edges
   ≤ 1.5 ft, grassed swales, crushed-aggregate paths. ~500 CY total
   earthwork — nothing reads as mass grading.

## Forbidden visual moves (audit-enforced in the data)

- ❌ One uniform fan / concentric arcs / a constant-radius 110° bowl
- ❌ Upstage shell, back wall, fly tower, proscenium, any enclosing room
- ❌ Anything tall in the bay-view corridor (az 330 ± 12°)
- ❌ A reflecting pool / pond / standing water in the treatment cell
- ❌ Retaining walls or risers over ~2 ft
- ❌ A resolved, monumental stage (Rule 9 is open — no committed stage axis)
- ❌ Permanent event infrastructure (screens, PA towers) — event overlays
  are temporary by definition

## Required viewpoints (`vectors_geojson/in_situ_viewpoints.geojson`)

Each feature has camera point, ground + eye elevation, look target
(xy + elev), azimuth, distance, suggested FOV, and target render filename.

| # | name | one-line intent |
|---|---|---|
| 1 | `upper_rim_down_to_stage` (REQUIRED) | three families stepping down to the low stage, bay beyond |
| 2 | `mid_row_audience_to_bay` (REQUIRED) | the governing image: seated on the bend section, performer below, bay + sky as the set |
| 3 | `stage_looking_back_to_audience` | performer's view of three distinct curving families |
| 4 | `ada_arrival_to_cross_aisle` | route-B arrival onto the level aisle bench |
| 5 | `outside_bowl_from_park_edge` | the bowl as landscape from the NE rim |
| 6 | `event_floor_to_treatment_cell` | floor → stage shoulder → dry meadow |

Replace `renders/<name>.png` (current files are labelled schematic plan
placeholders); keep the filenames so board 02 re-wires automatically.

## Material palette (`vectors_geojson/material_zones.geojson`)

| zone | material | hint |
|---|---|---|
| turf_terraces | mown turf on restored treads | `#7fae6e` |
| low_seat_edges | timber / split stone, ≤1.5 ft face | `#9c7b54` |
| hardscape_stage | low hardwood/composite deck | `#b9a48a` |
| accessible_paths | stabilized aggregate, boardwalk ramps | `#d9cfa3` |
| event_floor | stabilized turf, grass pavers | `#a4c08a` |
| bioretention_planting | wet-tolerant meadow (DRY cell) | `#6f9b8f` |
| vegetated_swales | grassed interception swales | `#5e8a7a` |
| existing_vegetation | canopy band, selectively trimmed | `#4e7a4e` |
| existing_slope_grass | unmown slope grasses | `#8da06b` |

Section accents on plans: east `#b08968` · bend `#7fae6e` · south `#5e8a9e`.

## Board list (regenerate via `bash scripts/build_in_situ_package.sh`)

- `boards/01_site_fit_board.png` — site fit, families coloured, cut/fill
- `boards/02_experience_board.png` — stations + renders + section profile
- `boards/03_landscape_character_board.png` — materials, water, six seasons
- `boards/board_sources.json` — structural manifest (audited)

## Current caveats

- **Stage refit OPEN (canon Rule 9):** +25.6° axis mismatch vs the seating
  centroid; best feasible candidate `az150_lat-20`
  (`analysis/stage_refit/STAGE_REFIT_SWEEP.md`). Until a path is adopted,
  depict the stage as provisional.
- DEM rasters are gitignored — fresh checkouts get `dem/MISSING_DATA.md`
  with restore steps; vector layers and boards still build.
- Orchestra floor, promenade walk width, paths, lawns, tree-mass boundaries
  and service access are **schematic** (flagged in-data); streets are
  boundary lines, not surveyed curbs.
- Renders in `renders/` are placeholders, not perspectives.
- Earthwork authority is `analysis/scenarioE_civic/earthwork.csv`
  (500.8 CY gross, excl. stage); the raster manifest is a planning mirror.

**Source of truth for any geometry question:**
`vectors_geojson/scenarioE_geometry.geojson` (governing emission) and
`vectors_geojson/terrace_treads.geojson` (enriched bands). If an image
contradicts those layers, the image is wrong.
