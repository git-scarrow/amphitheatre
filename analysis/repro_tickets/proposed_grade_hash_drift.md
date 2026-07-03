# Repro ticket — `proposed_grade_1ft.tif` hash drift (truth_package out of date)

**Type:** reproducibility / provenance. **Severity:** medium (blocks the comparator audit's source-
integrity guard). **Status:** ✅ **RESOLVED 2026-07-03.** **Independent of** the stage-pad clearance
work — do not entangle.

## Resolution (2026-07-03)
Re-ran `scripts/build_truth_package.py` (recomputes every source `sha256_12` live). Diffed the
regenerated `design_state.current.json` / `evaluation_report.current.json` against the 2026-06-13
baseline: **only the `generated` timestamp and four source hashes changed — no adopted quantity
moved** (seats 1283 nominal / 1243 Band-A, tread pass/warn/fail, sightlines, camera presets all
byte-identical). The four hash drifts, each traced to prior committed history (not this session):

| source | old → new sha256[:12] | provenance |
|---|---|---|
| `dem/proposed_grade_1ft.tif` | `86de4d4e99a7` → `29d7770ba95e` | `f90cf75` 06-27 all_touched terrain-overflow fix (build artifact, untracked) |
| `dem/cut_fill_1ft.tif` | `566badb423e6` → `774a9f492ccd` | same `f90cf75` rebuild (existing − proposed) |
| `dem/in_situ_grading_manifest.json` | `8fb51c9398aa` → `0e5ac2316db8` | same `f90cf75` rebuild (tracked) |
| `docs/DESIGN_CANON.md` | `60328eb434c7` → `0f8d7b025bd5` | `f713efb` 07-02 Decision-1 adoption — legitimate canon evolution since the snapshot |

Changed files: `truth_package/{design_state,evaluation_report,export_manifest}.current.json` +
regenerated `web_viewer/data/site_data.js`. Then `scripts/comparators/audit_comparators.py` →
**AUDIT PASS, 0 warnings, 0 failures** (hash guard clears; 35-ft-retirement checks still green).
Nothing about the stage-pad clearance work was touched.

## Symptom
`scripts/comparators/audit_comparators.py` aborts at its source-geometry guard:

```
FAIL: petoskey: dem/proposed_grade_1ft.tif hash changed —
      comparator work must not modify Petoskey source geometry
```

## Facts
| | value |
|---|---|
| Live `dem/proposed_grade_1ft.tif` sha256[:12] | `29d7770ba95e` (file mtime 2026-06-27) |
| Recorded in `truth_package/design_state.current.json` (+ `evaluation_report.current.json`) | `86de4d4e99a7` (mtime 2026-06-13) |
| Recorded hash matches | `dem/proposed_grade_1ft.before.tif` in the `terrain-cutfill-audit` worktree (the pre-fix surface) |

## Root cause (benign)
`proposed_grade_1ft.tif` was **legitimately rebuilt on 2026-06-27** by the terrace-terrain overflow
fix — `build_proposed_grade.py` was switched to `rasterize(all_touched=True)` so designed flat
terraces no longer let existing ground poke through (audit: `analysis/terrain_audit/`; the DEM went
`86de4d4e` → `29d7770b`). The `truth_package` design-state snapshot (2026-06-13) was **not
refreshed** afterward, so the guard compares the new DEM against the old recorded hash and trips.

This is a stale **baseline**, not a corruption of source geometry.

## Fix (when picked up)
1. Confirm the 2026-06-27 rebuild is the intended canonical surface (it is — the all_touched fix is
   adopted; see `docs/TERRAIN_OVERFLOW_AUDIT.md`).
2. Refresh the recorded `sha256_12` for `dem/proposed_grade_1ft.tif` (and re-check the other DEM
   hashes) in `truth_package/design_state.current.json` and `truth_package/evaluation_report.current.json`
   via whatever script builds them (`scripts/build_truth_package.py`).
3. Re-run `scripts/comparators/audit_comparators.py` → expect green (the 35-ft-retirement checks
   already pass; see `analysis/stage_pad_redteam/stage_current_geometry_gate.md` §5).

## Scope guard
Do **not** fold this into the stage-pad / clearance changes. Those touch only the comparator
stage-front metric and analysis artifacts; this ticket is a `truth_package` baseline refresh.
