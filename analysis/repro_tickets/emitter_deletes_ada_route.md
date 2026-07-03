# Repro ticket — `build_in_situ_geometry.py` deletes the live `ada_route.geojson`

**Type:** data-loss / generator bug. **Severity:** high (silently removes a
committed, in-use artifact). **Status:** ✅ **RESOLVED 2026-07-03.**

## Resolution (2026-07-03)
Removed `ada_route.geojson` from the emitter's superseded-deletion tuple, aligning
it with `audit_in_situ_package.py`'s `SUPERSEDED_COPIES` (which already excluded
it). Added a `REQUIRED_KEEP` assertion guard so a future edit cannot re-add a live
artifact to the deletion set. Verified: re-running `build_in_situ_geometry.py`
leaves `vectors_geojson/ada_route.geojson` in place (no "removed superseded
ada_route" line). The orchestra re-emission is now baked into the emitter, so the
full normal pipeline runs without deleting live data. Post-pipeline invariant is
asserted by `scripts/check_pipeline_artifact_contract.py` (invariant 2).

## Symptom
Running `scripts/build_in_situ_geometry.py` prints:
```
removed superseded vectors_geojson/ada_route.geojson (design_open_low)
```
and **deletes** `vectors_geojson/ada_route.geojson` (git shows `D`).

## Why it's wrong
The file is **not** a stale design_open_low artifact. It is the **current** stage-2
designed ADA route:
| | |
|---|---|
| features / roles | 39 · `{ada_route_concept, landing}` |
| source tag | `scripts/design_ada_routes.py (LOS-rationalized from stage-1 solver corridor)` |
| last commit | `51e7fbd` 2026-06-12 "ADA stage 2: designed alignments, alternatives, hierarchy, corridors" |
| consumed by | `truth_package` (`SRC["ada_route"]`, `build_truth_package.py:301`) — `jload` **crashes** if absent; also `design_ada_routes.py`, `build_unreal_export.py`, viewer |

The emitter's cleanup block lumps it with genuinely-superseded single-fan files:
```python
# scripts/build_in_situ_geometry.py  (~line 293)
for stale in ("seating_rows.geojson", "stage_floor.geojson", "ada_route.geojson"):
    ...
    os.remove(p)
    print(f"  removed superseded vectors_geojson/{stale} (design_open_low)")
```
`seating_rows.geojson` and `stage_floor.geojson` ARE superseded single-fan outputs;
`ada_route.geojson` is NOT — the current ADA route was re-designed post-single-fan
and kept the same filename.

## Fix (when picked up)
Drop `ada_route.geojson` from the deletion tuple:
```python
for stale in ("seating_rows.geojson", "stage_floor.geojson"):
```
Optionally guard the remaining two by a provenance check (only delete if the file's
`source`/`role` marks it design_open_low) rather than by filename.

## Interim mitigation
(Historical: before this fix the orchestra re-emission was done by a surgical
standalone script to avoid running the deletion-prone emitter. With the emitter
fixed, the re-emission is baked into it and the standalone script was removed.)

## Scope guard
Do **not** fold this into the stage-pad / orchestra cleanup. This is a generator
data-loss bug in its own right.
