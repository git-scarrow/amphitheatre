# Claude Design handoff — three-section civic bowl, Petoskey Pit

> ## ▶ HANDOFF RESUMED — STAGE CARRIED PROVISIONAL (2026-07-02)
> Rule 9 is **carried_provisional**: the stage bundle is adopted provisionally —
> **P_opt** placement (az 150 kept, audience faces **330°, bay Δ 0°**; residuals
> −6.7 ft / −6.3° declared; row-1 gaps 12.0/32.7/21.9 ft) + **five_facet_apron**
> front + **path-4 wide-fan** declaration + **T1_deck_only** element bundle
> (0.0% bay / 1.7% foreground). Record + rationale:
> `analysis/stage_adoption/RULE9_DECISION_RECORD.md`.
>
> Visual work may resume, but **depict the stage as PROVISIONAL** in every image
> and never as resolved/monumental. The bundle is not yet audit-`resolved`
> (package audit + EarthworkEngine CY recompute + Decision-1 tier gap re-confirm
> pending; **`resolved` is blocked on Decision 1**, still open — the 1,283-seat
> frame below remains the baseline). The roof (**T2**) is a separate, *unadopted*
> upgrade — the stage adoption does not smuggle it in.
>
> Retired by this adoption: the "low stage only" height framing (use the
> visual-envelope rule — taller utilitarian mass is fine where the obstruction
> study clears it) and the sweep's `az150_lat-20` "best candidate" (superseded
> frame, pocket-unchecked; see the record's "Why not az150_lat-20").

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
   shoulders only. Stage **axis carried provisional** (Rule 9 carried_provisional):
   **P_opt keeps az 150 → audience faces 330°**, with a five-facet apron front and
   the T1 deck-only bundle. Keep the stage visually low-key and **PROVISIONAL**;
   never heroic architecture (the T2 roof is a separate, unadopted upgrade).
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
- ❌ A resolved, monumental stage — Rule 9 is only *provisional* (axis is P_opt/az150,
  T1 deck-only; the T2 roof is not adopted). Depict provisional, never resolved/monumental
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

- **Stage refit CARRIED PROVISIONAL (canon Rule 9):** bundle adopted provisionally
  2026-07-02 — P_opt (az 150, bay Δ 0°, residuals −6.7 ft / −6.3° declared) +
  five_facet_apron + path-4 wide-fan + T1_deck_only
  (`analysis/stage_adoption/RULE9_DECISION_RECORD.md`). Depict the stage as
  **provisional** (not resolved) until the package audit + EarthworkEngine CY
  recompute + Decision-1 tier gap re-confirm are green. The sweep's `az150_lat-20`
  is superseded (pocket-unchecked).
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
