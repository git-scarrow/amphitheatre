# Terrain-overflow audit — green ground poking through the flat terraces

**Date** 2026-06-27 · **Datum** NAVD88 Geoid12A international feet · **CRS** EPSG:6494
· **Governing scheme** scenarioE_three_section_civic_bowl

## Symptom

In the Unreal scene the green *existing* terrain overflowed / poked through the
flat seating rows and terraces. This was a **terrain-operation failure**, not a
material, mesh-priority, or z-offset issue: the rendered ground surface genuinely
sat above the designed flat plate along the up-slope edge of every terrace.

## Root cause

The Unreal Landscape renders the **proposed-grade** terrain
(`dem/proposed_grade_1ft.tif` → `unreal_export/terrain/heightfield_proposed.r16`).
`scripts/build_proposed_grade.py` builds it by burning each tread's flat
composition elevation into the DEM with **`rasterize(..., all_touched=False)`**.
`all_touched=False` only flattens cells whose **centre** falls inside the tread
polygon, leaving a one-cell perimeter ring at *existing* ground. On the up-slope
side of every cut terrace that retained ring rose **up to +1.33 ft** above the
flat plate — the green overflow. The lost fringe was **3,555 cells (~25 %)** of
the total tread footprint.

## Audit method (`scripts/audit_terrace_terrain.py`)

For every designed flat surface — 45 seating treads, the cross-aisle bench, the
stage core/shoulders and the orchestra/event floor — the auditor samples the
rendered terrain over the **full** (`all_touched=True`) footprint and compares it
to the feature's design elevation. Each off-plate cell is classified:

- **retained-ground overflow (VIOLATION → cut)** — terrain > plate **and** the
  value matches no designed plate elevation, i.e. raw existing ground sticking up.
- **designed riser step (allowed)** — terrain ≠ plate but equals a *neighbouring*
  terrace's plate elevation: the legitimate step between terraces, not a defect.
- **interior fill** — measured on the unambiguous centre footprint only, so the
  riser face down to the row below is never miscounted as fill.

The discriminator is "does the protruding value equal a designed plate
elevation?", **not** "does it differ from existing" — because a burned neighbour
plate can coincidentally equal local existing ground (9 such cells were proven to
be neighbour terraces, not retained ground).

## Result

| metric (graded terraces: 45 treads + cross-aisle) | BEFORE | AFTER |
|---|---|---|
| features with retained-ground overflow | 46 | **0** |
| overflow cells (> 0.10 ft above plate) | 1,108 | **0** |
| worst overflow | **+1.33 ft** (`tread_south_r18`) | **0.00 ft** |
| overflow volume to cut | 27.2 CY | **0.0 CY** |
| error-layer polygons | 568 | **0** |
| designed riser-step cells (allowed) | 1,788 | 2,503 |

The same audit run on the **decoded Unreal heightfield** (`heightfield_proposed.r16`,
the exact artifact the editor imports) returns **0 overflow cells, worst +0.00 ft**;
the r16 vertical quantisation is 0.34 mm.

## The fix (real terrain edit, recorded numerically + geometrically)

`scripts/build_proposed_grade.py` — flat plates (treads + cross-aisle) now burn
with **`all_touched=True`**, flattening the whole visible footprint including the
perimeter fringe. Down-only ops (drainage swales, treatment cell) are unchanged.
Regenerated, tracked in `dem/in_situ_grading_manifest.json`
(`flat_plate_rasterization` flag), and propagated to the Unreal export via
`scripts/build_unreal_export.py` (proposed mesh + heightfield + per-row
`cutfill_*` stats re-sampled from the corrected raster).

Earthwork change from honouring the fringe: grading totals **cut 232.8 → 231.9 CY,
fill 103.1 → 155.1 CY** (the fringe restoration was previously skipped). No design
elevation moved (see below).

## Artifacts

- `dem/proposed_grade_1ft.tif`, `dem/cut_fill_1ft.tif` — corrected rasters *(regenerable; git-ignored)*
- `unreal_export/terrain/terrain_proposed.{glb,obj}`, `heightfield_proposed.{r16,png}` — corrected mesh + Landscape *(regenerable; git-ignored)*
- `analysis/terrain_audit/terrace_terrain_ledger_{before,after}.csv` — per-feature operation ledger
- `analysis/terrain_audit/terrain_error_layer_{before,after}.geojson` — intersection/error layer (feature_id, design_elev, terrain_max, delta, operation=cut)
- `analysis/terrain_audit/protrusion_delta_1ft_{before,after}.tif` — terrain − plate delta raster
- `analysis/terrain_audit/overflow_plan_before_after.png`, `section_before_after.png` — matched-framing before/after visuals

> The before/after rasters reproduce by reverting the one-line `all_touched`
> change and re-running `build_proposed_grade.py`. A live matched-camera Unreal
> capture is a follow-up requiring the editor; the post-fix Landscape imports
> `heightfield_proposed.r16`, audited clean above.

## Design claims — checked, all preserved

- **Stage / event floor ≈ 612.5 ft** — *preserved, clarified.* No green overflows
  these zones: existing ground there is **~609.8 ft (2.3–4.2 ft below 612.5)**, so
  612.5 is achieved by a **structure (deck)**, consistent with DESIGN_CANON Rule 9
  (stage refit OPEN). The ~515 CY "fill" under the stage/event footprints is the
  **void beneath the deck, not earthwork**; it is flagged as such in the ledger
  and **not** added to grading totals.
- **16-row open fan** — preserved. 45 tread features across east/bend/south; **0**
  rows changed `proposed_elev_navd88_ft`.
- **Row/terrace surfaces flat enough to read as constructed landform** — now true:
  AFTER audit = 0 retained-ground overflow; terraces render as flat plates joined
  by clean risers.
- **ADA route plausible** — geometry unchanged; the route is a sloped corridor
  (concept tier), audited separately, ramp volumes remain in
  `analysis/scenarioE_civic/earthwork.csv`.
- **No unexplained retaining walls** — none introduced. The fix only flattens the
  fringe to existing-design plate elevations; inter-terrace riser **heights are
  unchanged** (≤ ~1.5 ft typical; the 2.71 ft row-8→cross-aisle step is the
  pre-existing rows-9/10 reclassification, not a new wall).

## Hard invariant — satisfied

No visible terrain overflows a designed flat terrace. Where existing ground was
removed, the cut is represented geometrically (the corrected proposed-grade raster
/ heightfield / mesh) and recorded numerically (ledger + grading manifest). Risers
between terraces remain retained existing ground by design and are explicitly
classified as such.
