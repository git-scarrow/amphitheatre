# In-situ design brief — Open Civic Bowl three-board concept set

**Petoskey Pit, Bayfront Park, Petoskey MI.** Planning-grade, not stamped
engineering. CRS **EPSG:6494** (NAD83(2011) / Michigan Central, international
feet), elevations **NAVD88 (Geoid12A) intl ft** (`docs/datum_note.md`).

Governing scheme: **`design_open_low/` (Open Civic Bowl)** — audience faces
**az 330°** (NNW, bay + evening sun), **±55° / 110° fan**, **16 rows**
R 85–130 ft on the ~33% natural rake, **stage front 35 ft from row 1**, low
open stage with **lateral shoulders only**, **dry/ephemeral treatment cell**
beyond the stage, **no retaining walls**, **no upstage shell or fly tower**.
`scripts/in_situ_common.py` re-verifies these invariants against the tracked
GeoJSON on every run; the audit gate fails on drift.

## Reproduce

```sh
python -m venv .venv && .venv/bin/pip install numpy rasterio shapely matplotlib
bash scripts/build_in_situ_package.sh
```

The script runs seven build steps then `scripts/audit_in_situ_package.py`
(non-zero exit on any failure). On a fresh checkout the DEM is absent
(rasters and LiDAR are gitignored): step 4 then writes **`dem/MISSING_DATA.md`**
with exact restore instructions, every vector layer / board / QGIS artifact
still builds, and the audit accepts the diagnostic in place of the rasters.
With `dem/dem_design_1ft.tif` restored (see the diagnostic), the same command
also produces `dem/proposed_grade_1ft.tif`, `dem/cut_fill_1ft.tif`, and
`dem/in_situ_grading_manifest.json`.

## The boards

| Board | Shows | Built from |
|---|---|---|
| `boards/01_site_fit_board.png` | design on the natural rake over hillshade; schematic context dotted; cut/fill panel; governing metrics incl. grading volumes | all vector layers + DEM/cut-fill when present |
| `boards/02_experience_board.png` | six numbered camera stations, their placeholder renders, centreline section with the row-8 sightline to the bay, per-row C-values | `in_situ_viewpoints.geojson`, `renders/*.png`, seating rows, DEM section when present |
| `boards/03_landscape_character_board.png` | material zones with legend, six nonbinding event-mode small multiples, the dry-cell water narrative | `material_zones.geojson`, `event_modes.geojson`, site context |

The six images in `renders/` are **schematic plan diagrams** (camera + view
cone + annotations), labelled as such — stand-ins until QGIS 3D / Blender
perspective renders are produced from the same camera stations.

## Layer inventory (`vectors_geojson/`)

`terrace_treads` (16 annular tread polygons, full row properties),
`terrace_edges` (low seat edges, riser ≤ 1.5 ft, `retaining_wall: false`),
`bowl_zones` (stage core / lateral shoulders / forecourt / ADA corridors /
cross-aisle overlay / treatment-cell landscape / untouched slope),
`site_context`, `material_zones`, `in_situ_viewpoints`, `event_modes`, plus
verbatim copies of the governing `seating_rows` / `stage_floor` / `ada_route`.
`qgis/in_situ_package.qgs` loads everything by relative path.

## Known assumptions

- **Tread grading is FILL-ONLY** to the design tread plane (rows sit on the
  natural rake). A level-bench interpretation would claim ~700 CY of cut the
  design never proposes — the `SCENARIO_B_VALIDATION.md` lesson applied here.
- **Treatment-cell shaping is a flagged schematic stand-in** (4:1 down-only
  toward the 609.1 bottom). The Stage-5 cell grading design governs when
  regenerated; the cell is never permanent water.
- **ADA ramps are straight schematic stand-ins for switchbacks** (6 ft
  corridors, linear grade). Per `DESIGN_CANON.md` Rule 3 these remain
  concept-tier until real switchback geometry is emitted and validated.
- Site context marked `schematic: true` (streets/ROW, paths, lawn, tree-mass
  boundaries, service access) is placement-grade only. The rim/arrival edge
  (from `basin_footprint.geojson`) and the az-330 bay-view corridor are
  data-derived.
- Eye heights 3.94 ft seated / 5.2 ft standing; bay water plane 579.45 ft
  (measured, EPT).

## Findings the grading model surfaced (for design review)

- **Residual high ground on the tread bands:** ~5,990 sf rides above the
  tread plane (up to ~6.7 ft at the eastern arc ends, ~699 CY if it were cut).
  Level 110° rows meet laterally rising ground at the fan edges; options are
  local cut, tapering the end bays, or letting the top rows shorten. Reported
  in `dem/in_situ_grading_manifest.json`, deliberately **not** graded away.
- **On-footprint fill exceeds cut by ~611 CY** (fill 769 / cut 158). The
  design's "never imports fill" stance therefore depends on on-site borrow —
  candidate zones are already mapped in `earthwork_scenarios.geojson` (S01–S03).
- **Route A clips the treatment-cell edge** — boardwalk candidate; the overlap
  shows as fill inside the cell zone in the manifest.

## Canon alignment (`docs/DESIGN_CANON.md`)

- **Rules 1/2/4/5** — seat figures on the boards are the Open Civic Bowl's
  *geometric planning estimates* (labelled as such), never Band-A formal
  counts: no four-gate validation on a built surface has been run for this
  scheme, so no formal capacity is claimed.
- **Rule 3** — the grading manifest tags every zone with `cost_status`;
  schematic stand-ins (ADA corridors, treatment-cell shaping) are
  `concept`-tier and may not enter a project cost table.
- **Rules 6/7** — the cross-aisle and ADA bands declare their actual
  generator (`design_route_buffer` of the tracked route lines) with
  `seam_derived: false`; the audit gate fails on missing provenance.
- **Rule 9** — applies to *Scenario E's* inherited stage and remains open
  there; it is **not** resolved or affected by this package. The Open Civic
  Bowl's declared ±55° fan matches its emitted arcs by construction, which
  `scripts/in_situ_common.py` re-verifies on every run.

## Missing inputs

- `dem/dem_design_1ft.tif` on fresh checkouts (gitignored) — restore per
  `dem/MISSING_DATA.md` (USGS LPC MI 13County 2015 C16 tiles + `scripts/build_dems.py`).
- Surveyed streets/ROW, park path network, tree survey, utility locations.
- Geotech/soils + hydraulic sizing for the treatment cell (`gating_dossier.md`).
- Stage-5 cell grading surface (regenerable, not tracked).
- True perspective renders (QGIS 3D / Blender) from the six camera stations.

## Next manual review steps

1. Open `qgis/in_situ_package.qgs`; check each layer against the boards.
2. Decide the treatment of residual high ground at the eastern arc ends
   (local cut vs row taper) — this changes the capacity table if rows shorten.
3. Confirm the borrow-zone story for the ~611 CY net fill, or revise the
   "never imports fill" claim in `design_open_low/README.md`.
4. Field-verify all `schematic: true` context features.
5. Produce perspective renders from `in_situ_viewpoints.geojson` and replace
   the placeholders in `renders/` (same filenames keep board 02 wiring).
6. Re-run `bash scripts/build_in_situ_package.sh` after any change; the audit
   gate must stay green.
