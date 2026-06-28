# Reconciliation judge — terrain-editor candidate patches

**Date** 2026-06-27 · **Judge baseline** Open Civic Bowl design (scenarioE three-section)
· **Datum** EPSG:6494 / NAVD88 Geoid12A intl ft · **Authority** terrain-operation ledger
(`dem/in_situ_grading_manifest.json`), *not* the Unreal/QGIS render.

## Decision rule applied

> Accept the smallest set of changes that makes the visible terrain match the governing
> design geometry **and** makes every earth change numerically auditable.

One candidate (the `terrain-cutfill-audit` fringe fix) satisfies this and is **accepted**.
Everything else is visual-only, out-of-scope, or stale and is **not** part of the judge
commit.

## 1. Reconciliation matrix — every agent output

| Candidate (branch / worktree) | What it changes | Class | Touches governing design? | Touches terrain ledger? | Verdict |
|---|---|---|---|---|---|
| **terrain-cutfill-audit** (uncommitted in worktree) | `build_proposed_grade.py` `all_touched=False→True`; regenerated raster/heightfield/mesh; manifest volumes; per-row `cutfill_*` stats; new audit script + doc + `analysis/terrain_audit/` | **REAL terrain edit** | Yes — proposed grade only; **no** row/stage/ADA *geometry* moved | Yes — manifest updated, fully accounted | **ACCEPT** |
| context-reclassify (uncommitted) | `reclassify_context_massing.py` + render; `analysis/context_reclassification/` only | Visual / provenance diagnostic | No | No | **REJECT for terrain commit** (out of scope; keep as separate context patch) |
| sunset-scene-authoring (merged @17b9635) | sun grade, water material, far-shore DEM context | Visual / rendering | No | No | **N/A** — already on main; not re-judged |
| bay-view-obstruction (@bd6e8f8) | obstruction analysis + doc edits | Analysis / visual | No | No | out of scope (analysis only) |
| ue-context-horizon-v0 (@21e2180) | ancestor of base; diff = −46,722 lines | **Stale** | n/a | n/a | **REJECT** — merging reverts accepted history |

## 2. Real edit vs visual-only vs stale

- **Real terrain edit:** only `terrain-cutfill-audit`. It edits the proposed-grade DEM
  (`dem/proposed_grade_1ft.tif`), which the Unreal Landscape imports via
  `heightfield_proposed.r16`. The edit is recorded numerically (manifest + ledgers) and
  geometrically (raster/heightfield/mesh regenerated, sha-linked in `provenance.json`).
- **Visual-only:** sunset-scene-authoring (lighting/water/far-shore) and context-reclassify
  (massing class overlay). Neither moves design geometry or earth.
- **Stale / conflicting:** ue-context-horizon-v0 is behind the merge base and would revert
  the obstruction + context history if merged. Rejected.

## 3. Independent verification performed by the judge

| Check | Method | Result |
|---|---|---|
| After-state overflow | re-ran `audit_terrace_terrain.py` on `proposed_grade_1ft.tif` | **0** features / **0** cells / worst **+0.00 ft** |
| Before-state overflow | re-ran audit on `proposed_grade_1ft.before.tif` | 46 features / **1108** cells / worst **+1.33 ft** / 568 polygons (matches doc) |
| Row geometry preserved | diffed `seating_rows*.geojson`; grep all `[+-]` keys | only `cutfill_{mean,min,max}_ft` changed — **0 coordinate edits** (judge rule 6 ✓) |
| Imported artifact honest | decoded `heightfield_proposed.r16` | identical grid 801² and elev range 588.230–662.092 ft to the corrected source raster |
| Earthwork auditable | computed `after − before` delta raster | 2418 cells changed; **net +52.9 CY** = manifest (fill +52.0, cut −0.9) |
| Design files untouched | git status | `stage_floor`, `ada_route`, sightline table, seat_count — **unmodified** |

## 4. Judge rule 5 — no hidden overflow

No candidate masked terrain overflow with **material priority, mesh deletion, z-offset, or
camera tricks**. The accepted fix removes/places real material in the DEM and records the
cut **and** fill. The audit's discriminator is "does the protruding value equal a *designed*
plate elevation?" — so legitimate inter-terrace risers (2,503 cells) are **not** miscounted
as overflow, and retained ground is. Recorded explicitly as `REJ-004` in `rejected_ops.geojson`.

## 5. Design invariants — preserved

- **16-row open fan** — 45 tread features east/bend/south; **0** rows changed
  `proposed_elev_navd88_ft`; **0** coordinate edits.
- **Stage/floor @612.5** — a **deck structure** over existing grade ~609.8 ft, not earthwork.
  The ~515 CY under the deck is void, flagged in the ledger and **excluded** from grading
  totals (DESIGN_CANON Rule 9, refit OPEN). No green overflows these zones.
- **Cross-aisle, treatment cell, ADA route, sightline table, seat count** — geometry
  unchanged; ADA corridors are concept-tier sloped (volumes in
  `analysis/scenarioE_civic/earthwork.csv`).

## 6. Known reconciliation notes (transparent, non-blocking)

- The before-audit reports **27.2 CY** of above-plate overflow; the after−before raster
  delta reports **15.7 CY** of cells *lowered*. These measure different quantities —
  protrusion volume above the plate vs. net change in the proposed-grade raster (most fringe
  cells were *below* plate and were raised → +68.6 CY fill dominates). Both are recorded; the
  governing net (**+52.9 CY**) ties to the manifest.
- `zone_cross_aisle` accepted op carries numerics but no polygon in `seating_rows.geojson`
  (its footprint lives in the grading set); 45/46 sited ops carry tread polygons.
- **Live matched-camera Unreal capture is an open follow-up** (requires the editor running).
  The before/after evidence here is matched-framing plan + section
  (`before_after_plan.png`, `before_after_section.png`); the imported `.r16` is audited clean
  above, so the rendered Landscape carries the corrected surface.

## 7. Artifacts (this folder)

| File | Contents |
|---|---|
| `cut_fill_ledger.csv` | 59 operation records (op_id, feature, source geom, op type, before/after elev, delta, volume CY, validation) |
| `accepted_ops.geojson` | 46 sited terrain ops (tread polygons + numerics) |
| `rejected_ops.geojson` | 4 branch/mechanism-level rejections (null geometry + reason) |
| `terrain_delta.tif` | after − before proposed-grade delta raster (the actual earth moved) |
| `before_after_plan.png`, `before_after_section.png` | matched-frame before/after of the overflow |
| `build_judge_artifacts.py` | deterministic regenerator for the ledger + geojsons |
