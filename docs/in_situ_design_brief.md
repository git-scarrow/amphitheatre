# In-situ design brief — three-section civic bowl concept set

**Petoskey Pit, Bayfront Park, Petoskey MI.** Planning-grade, not stamped
engineering. CRS **EPSG:6494** (NAD83(2011) / Michigan Central, international
feet), elevations **NAVD88 (Geoid12A) intl ft** (`docs/datum_note.md`).

## Governing scheme

**Scenario E — the three-section naturalistic civic bowl**
(`analysis/scenarioE_civic/geometry.geojson`), canon-**ACCEPTED** for
seating / ADA / drainage (`docs/DESIGN_CANON.md`, `SCENARIO_E_CIVIC.md`):

- **Three seating families — east / bend (southeast) / south** — each a
  contour-fitted band family with its **own local curvature** (per-bay spline
  fits from `design_extended_bays/`). There is **no shared arc centre and no
  constant-radius fan**; the audit gate hard-fails on any regression to the
  superseded `design_open_low` single-fan scheme.
- Rows 1–4 forecourt · **row 5 promenade hinge band** (absorbs the geometry
  change between families) · rows 6–18 civic · **rows 9–10 reclassified as
  the level cross-aisle** (622.01, `geometry_source: row_reclassification`,
  `seam_derived: false` — preserved verbatim).
- **1,283 Band-A seats**, validated on the restored (Scenario D) surface.
- Hinge rays at the declared section breakpoints (az 118° / 152°).
- Switchback **ADA ramps + landings**, flank **drainage swales** to the NE
  pour point, row-end shoulders returned to landscape — all emitted +
  validated (500.8 CY gross, `analysis/scenarioE_civic/earthwork.csv`).
- **Stage: inherited and OPEN.** The low open deck (lateral shoulders only,
  no upstage shell / back wall / fly tower, nothing blocking the bay view)
  is reused from the prior scheme; its axis refit is an **open canon item
  (Rule 9)**. This package surfaces that status everywhere and declares
  **no fan** for it.
- **Dry/ephemeral treatment cell** beyond the stage (bottom 609.1) — never
  permanent water. **No retaining walls** — seat edges ≤ 1.5 ft.

### Geometry decision record (2026-06-10)

Candidates audited: `design_open_low` (single ±55° fan — superseded for this
package), `design_civic_contour` (raw contour rows, baseline),
`design_civic_bowl` (regularized crescents — superseded by the bay march),
`design_extended_bays` (three-family contour-bay march — the geometry
generator), `design_civic_core` (quality-band partition), **Scenario E**
(emitted + validated buildable subset — chosen). Scenario E is the only
candidate that is canon-ACCEPTED with geometry-backed validation; it consumes
the extended-bays families directly, so family curvature and hinge logic
carry through unchanged.

## Reproduce

```sh
python -m venv .venv && .venv/bin/pip install numpy rasterio shapely matplotlib
bash scripts/build_in_situ_package.sh
```

Seven build steps, then `scripts/audit_in_situ_package.py` (non-zero exit on
any failure). On a fresh checkout the DEM is absent (rasters + LiDAR are
gitignored): step 4 writes **`dem/MISSING_DATA.md`** with exact restore
instructions, every vector layer / board / QGIS artifact still builds, and
the audit accepts the diagnostic in place of the rasters. With
`dem/dem_design_1ft.tif` restored, the same command also produces
`dem/proposed_grade_1ft.tif`, `dem/cut_fill_1ft.tif`, and the grading
manifest.

## The boards

| Board | Shows | Built from |
|---|---|---|
| `boards/01_site_fit_board.png` | the three families coloured separately with hinge rays, on hillshade with real street boundary lines; cut/fill panel; governing metrics | all vector layers + DEM when present |
| `boards/02_experience_board.png` | six numbered camera stations, their placeholder renders, the bend-section axis profile with the row-8 bay sightline, per-section C-values | viewpoints, treads, composition, DEM when present |
| `boards/03_landscape_character_board.png` | material zones with legend, six nonbinding event-mode small multiples, the dry-cell water narrative | material zones, event modes, site context |

`boards/board_sources.json` is the **structural manifest** the audit checks:
governing scheme, three sections, `single_fan_declared: false`, stage Rule 9
status. The six `renders/*.png` are **schematic plan diagrams** (camera +
view cone + annotations), labelled as such — stand-ins until QGIS 3D /
Blender perspective renders are produced from the same stations.

## Layer inventory (`vectors_geojson/`)

`terrace_treads` (45 bands, section + composition properties + **measured
curvature metadata**: kasa fit centre/radius/rmse, tangent bearing,
curvature class), `terrace_edges` (low seat edges with riser vs the surface
in front), `bowl_zones` (stage ×3 Rule 9 OPEN · orchestra floor (derived,
schematic) · treatment cell · cross-aisle · ADA ramps + landings · swales ·
promenade hinge ×3 · hinge rays ×2 · row-end shoulders ×5 · construction
envelope · untouched slope), `site_context`, `material_zones`,
`in_situ_viewpoints`, `event_modes`, and `scenarioE_geometry` (verbatim copy
of the governing source). `qgis/in_situ_package.qgs` loads everything by
relative path, plus the extended-bays centrelines.

## Known assumptions

- **Tread grading restores each band to its composition elevation** (cut AND
  fill — the Scenario D restoration; z-residuals were gated ≤ 0.25 ft by the
  bay march, so moves are small). Raster volumes approximate the validated
  delta-engine volumes in `earthwork.csv`; that CSV remains the authority.
- **ADA switchbacks are not re-burned in the raster** — their geometry-backed
  volumes live in `analysis/scenarioE_civic/earthwork.csv` (route A 79.2,
  route B 126.0 gross CY).
- **The stage deck is a structure, not grading**, and is excluded from
  earthwork exactly as Scenario E's 500.8 CY total excludes it (refit OPEN).
- **Treatment-cell shaping is a flagged schematic stand-in** (4:1 down-only
  toward 609.1); the cell is never permanent water.
- The **orchestra event floor** is a derived, schematic zone (hull between
  stage and the three row-1 bands), concept tier.
- The **row-5 promenade band** is a buffer of the design centrelines
  (8 ft walk), concept tier, `seam_derived: false`.
- Site context marked `schematic: true` (paths, lawn, tree-mass boundaries,
  service access) is placement-grade. The rim/arrival edge
  (`basin_footprint.geojson`), street boundary lines (extended-bays march,
  2026-06-06), and the az-330 bay-view corridor (EPT viewshed) are
  data-derived.
- Eye heights 3.94 ft seated / 5.2 ft standing; bay water plane 579.45 ft.

## Canon alignment (`docs/DESIGN_CANON.md`)

- **Rules 1/2/4/5** — the 1,283-seat figure is Scenario E's Band-A count,
  validated on the restored surface (not an ideal-plane estimate).
- **Rule 3** — grading-manifest zones carry `cost_status`; schematic
  stand-ins (cell shaping, orchestra floor, promenade) are `concept`-tier.
- **Rules 6/7** — the cross-aisle's `row_reclassification` provenance is
  carried verbatim; the promenade band and hinge rays name their actual
  generators; the audit fails on any seam-derived claim.
- **Rule 9 — OPEN.** The inherited stage carries +25.6° audience-axis
  mismatch and −22.5 ft lateral offset vs the validated seating (best
  feasible refit candidate: `az150_lat-20`, see
  `analysis/stage_refit/STAGE_REFIT_SWEEP.md`). This package surfaces the
  status on every stage feature and board and declares no fan. Resolving
  Rule 9 (paths 1–4) is the first manual review step below.

## Missing inputs

- `dem/dem_design_1ft.tif` on fresh checkouts — restore per
  `dem/MISSING_DATA.md` (USGS tiles + `scripts/build_dems.py`).
- **A Rule 9 stage decision** (paths 1–4 in `DESIGN_CANON.md`).
- Surveyed curb/ROW geometry, park path network, tree survey, utilities.
- Geotech/soils + hydraulic sizing for the treatment cell
  (`gating_dossier.md`).
- True perspective renders (QGIS 3D / Blender) from the six stations.

## Next manual review steps

1. **Adopt a Rule 9 stage path** (audience-axis / bay-axis / compromise /
   wide-fan declaration) — until then the stage stays "refit OPEN" on all
   boards and the package cannot claim a settled stage.
2. Open `qgis/in_situ_package.qgs`; review each layer against the boards.
3. Field-verify all `schematic: true` context features.
4. Produce perspective renders from `in_situ_viewpoints.geojson` and replace
   the placeholders in `renders/` (same filenames keep board 02 wiring).
5. Re-run `bash scripts/build_in_situ_package.sh` after any change; the
   audit gate must stay green.
