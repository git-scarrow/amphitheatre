# Prop-Placement Phase 1 Implementation Plan

> **For agentic workers:** implement task-by-task; steps use checkbox (`- [ ]`) syntax for
> tracking. Each task carries a `→ verify:` success criterion. The three schema-shaping decisions
> (D1–D3 below) are **confirmed (2026-07-19)** — Task 1 may start.

**Goal:** Make the read-only Unreal scene *editable for additive site furniture* (benches,
trees, planters, bins, bollards) end to end — placed in the editor, captured to an EPSG:6494
proposal, gated, and folded into the export as an additive layer — proving the full authoring
loop from `docs/unreal_editable_scene_v0.md` on the cheapest payload. No terrain, seating,
ADA, stage, or DEM changes.

**Architecture:** A tracked catalog declares placeable classes + placement rules. A capture
tool reverses the coordinate contract (the tested inverse in `verify_unreal_export.gate_roundtrip`)
to emit a point-feature proposal GeoJSON under `requests/`. A single new light gate
(`scripts/validate_site_furniture.py`) checks boundary/snap/collision/spacing and fails closed.
On PASS a maintainer folds the proposal into a tracked furniture layer; `build_unreal_export.py`
and `build_unreal_handoff_manifest.py` gain an additive layer; `speckle_compare.py` and the
publish ledger record it. Props never recompute the DEM, seats, C-values, or earthwork, so the
grading suite does not run.

**Tech Stack:** Python 3 standard library only (no shapely — point-in-polygon and segment
distance are implemented directly, matching the repo's stdlib-gate convention); JSON; GeoJSON;
plain-script repo tests (`scripts/test_*.py`, exit 0/1); Markdown. UE-side capture is a small
Python MCP/editor utility.

## Decisions (confirmed 2026-07-19)

The three open questions from `docs/unreal_editable_scene_v0.md` §9, settled by the owner:

- **D1 — Catalog ownership.** *Confirmed:* `assets/props/catalog.json` is **repo-tracked metadata**
  and the single authority for what is placeable + its rules; UE **mesh binaries are NOT committed**
  (heavy, like `unreal_export/terrain/*.glb`), referenced by a stable `mesh_id` resolved UE-side.
  Adding a prop class = a catalog PR reviewed by a maintainer.
- **D2 — Authoring root.** *Confirmed:* the capture tool reads **only** actors under a dedicated
  Outliner root **`Authoring_Furniture`** (parallel to PR #2's `TerrainOps_OpenCivicBowl`), so
  imported design geometry is never scooped. Actors outside it are ignored and reported.
- **D3 — `feature_id` minting.** *Confirmed:* a newly placed prop gets a **readable deterministic
  id** `furn_<object_class>_<nnnn>` (zero-padded, monotonic per class), minted at capture, written
  into the proposal, and stored back as a UE actor tag so it **survives re-import** and diffs
  human-readably (matching the repo's `feature_id` / `op_id` style). Rejected alt: opaque UUID.

## Global Constraints

- The repo (`vectors_geojson/` + Python/QGIS gates + `data/speckle_publish_ledger.json`) remains
  the **sole acceptance authority**. Capture writes only to `requests/`; nothing here writes
  `vectors_geojson/`, `dem/`, `truth_package/`, or `analysis/` directly.
- **Additive only.** The audited design groups (seating, stage, ADA, terrain, human-scale, context)
  must be **byte-unchanged** after a furniture round trip. Props sit *on* the surface; they do not
  edit it.
- Coordinate contract is reversed with the existing constants — `ORIGIN_X, ORIGIN_Y = 19533067.7,
  750799.2`, `FT2M = 0.3048`, ENU metres Z-up, ×100 UE scale, ENU→UE det −1 — via the inverse
  already in `gate_roundtrip` (`x_ft = local_m / FT2M + ORIGIN_X`). No new transform math is invented.
- The gate **fails closed**: any unproven check → non-zero exit, no promotion.
- Stdlib + current repo deps only; add no heavy dependency (no shapely/trimesh in the gate path).
- Preserve unrelated untracked files (`proxmox-jobs.sqlite3*`).
- Do not run `build_unreal_export.py` in a checkout missing the DEM rasters; the furniture layer
  addition (Task 4) is exercised with the existing committed geo layers, not a full re-export.

---

### Task 1: Prop catalog + schema validator

- [ ] Add `assets/props/catalog.json`: `{schema, version, classes: [...]}`. Each class:
  `object_class` (e.g. `bench`, `tree_deciduous`, `planter`, `bin`, `bollard`), `mesh_id`,
  `footprint` (list of local-metre offsets forming the plan footprint), `default_variant`,
  `variants` (list), `place_on` (allowed surface classes, e.g. `["terrace_tread","context_ground"]`),
  `keep_clear_of` (classes it must not collide with, e.g. `["ada_route","egress","stage_deck"]`),
  `min_spacing_m`, `max_count` (nullable).
- [ ] Seed 3 classes for the spike: `bench`, `tree_deciduous`, `planter`.
- [ ] Add `scripts/validate_prop_catalog.py`: validates the schema, unique `object_class`,
  non-empty footprint, `place_on`/`keep_clear_of` reference known classes. Exit 0/1.
- [ ] Add `scripts/test_prop_catalog.py`: valid catalog passes; a duplicate class, an empty
  footprint, and an unknown `keep_clear_of` reference each FAIL.
- → **verify:** `python3 scripts/validate_prop_catalog.py` exits 0 on the seed; the test suite
  passes; catalog carries no absolute mesh paths (D1: metadata only).

### Task 2: Capture tool + furniture proposal schema (UE → EPSG:6494)

- [ ] Define the proposal artifact: `requests/proposal_furniture_<topic>_<date>.geojson`, a
  `FeatureCollection` of `Point` features in EPSG:6494 (a `crs` member naming EPSG:6494), each
  feature `properties`: `feature_id` (D3), `object_class`, `variant`, `yaw_deg`,
  `anchor_epsg6494_ft` (the point coords), plus `@review`: `placed_by`, `base_build_git_commit`,
  `timestamp`, `object_truth: "proposal — not design until gated"`.
- [ ] Add `scripts/capture_furniture.py`: input = a UE-exported placement dump (JSON list of
  `{actor_name, object_class, variant, ue_location_cm, yaw_deg}` read from the `Authoring_Furniture`
  root, D2). For each: reverse UE→local-metre (÷100, undo det −1 handedness) then local→EPSG:6494
  (`local_m / FT2M + ORIGIN`), mint `feature_id` (D3), write the proposal GeoJSON. Actors outside
  the authoring root are dropped with a reported count.
- [ ] Add `scripts/test_capture_furniture.py`: a **round-trip** test — take a known
  `anchor_epsg6494_ft` from the committed `actor_manifest.json`, forward-transform it to UE cm,
  feed it through `capture_furniture`, assert the recovered EPSG:6494 point matches within
  `<1e-6 ft` (mirrors `gate_roundtrip`'s tolerance). Also assert out-of-root actors are excluded.
- [ ] Add `unreal/ue_capture_furniture.py` (UE-side stub): reads actors under `Authoring_Furniture`,
  writes the placement dump. Documented as running inside UE; not exercised in repo CI.
- → **verify:** round-trip recovers the source coordinate within `1e-6 ft`; a placed actor outside
  `Authoring_Furniture` is excluded; the emitted file validates as EPSG:6494 GeoJSON.

### Task 3: The gate — `scripts/validate_site_furniture.py`

- [ ] Load the proposal, the catalog, and the constraint layers from committed geo:
  `unreal_export/geo/ada_route.geojson` (+ a derived clear-route buffer), `seating_rows.geojson`,
  `stage_floor.geojson`, plus the site boundary. Implement point-in-polygon + point-to-segment
  distance in stdlib.
- [ ] Checks, each emitting a per-feature reason on failure:
  - **B1 in-boundary** — every prop inside the site boundary.
  - **B2 surface/`place_on`** — prop sits on an allowed surface class (from the catalog).
  - **B3 keep-clear collision** — footprint clears the **ADA clear route** (route + width buffer),
    egress, seating treads, and the stage deck (the sharp check).
  - **B4 spacing/count** — pairwise `min_spacing_m` respected; `max_count` not exceeded per class.
  - **B5 identity/provenance** — every feature has a unique `feature_id`, a known `object_class`,
    and `@review.base_build_git_commit` present.
- [ ] Exit 0 only if all features pass; else exit 1 and print the blocking features. **Fail closed**
  if a required constraint layer is missing.
- [ ] Add `scripts/test_site_furniture_gate.py`: a clean bench on context ground **PASSES**; a bench
  dropped **on the ADA route buffer FAILS B3**; two benches closer than `min_spacing_m` FAIL B4; a
  prop outside the boundary FAILS B1; a missing constraint layer FAILS closed.
- → **verify:** all gate tests pass; the ADA-collision case is the headline negative and blocks
  with a clear reason.

### Task 4: Additive furniture layer + export/manifest integration

- [ ] Define the promoted layer path `vectors_geojson/site_furniture.geojson` (folded in by a
  maintainer from a passed proposal — the plan documents the fold-in step; it does not auto-write it).
- [ ] Extend `build_unreal_export.py` with a furniture layer (points → per-prop actor anchors in
  the `actor_manifest`, `object_class` as `actor_class`, `validation_state: additive`,
  `provisional: false`), emitting `unreal_export/geo/site_furniture.geojson`. Guard: absent source →
  layer simply omitted (no failure), so existing checkouts still build.
- [ ] Extend `build_unreal_handoff_manifest.py` `LAYERS` with a `site_furniture` entry
  (role `additive-furniture`, `editable_in_unreal: "placement-only (proposal round-trip)"`,
  `authoritative_source: ["vectors_geojson/site_furniture.geojson"]`).
- [ ] Update the manifest `mcp_runway` boundary (MCP_ALLOWED/DISALLOWED): allow
  *place/move/remove catalog furniture under `Authoring_Furniture`, captured to a `requests/`
  proposal*; keep direct writes to `vectors_geojson/`/`dem/` disallowed.
- → **verify:** with a small sample `site_furniture.geojson`, `build_unreal_handoff_manifest.py`
  then `--check` exits 0; with **no** furniture source the manifest builds unchanged (additive,
  audited groups untouched); manifest fingerprint reflects the new layer only when present.

### Task 5: Diff + ledger reuse

- [ ] Make `speckle_compare.py` furniture-aware: added / moved (by `feature_id`) / removed props
  between the accepted set and a proposal, reported under a `furniture` delta block.
- [ ] Confirm a furniture proposal flows through the existing `publish_speckle.py` **proposal**
  channel + `append_entry` unchanged (it is just another `proposal`-state payload; the #3 guard
  keeps it honest). No ledger schema change.
- [ ] Add coverage to `scripts/test_speckle_phase2.py`: a furniture proposal compares with a
  non-empty `furniture` delta and records a proposal-channel ledger entry.
- → **verify:** compare shows the placed/moved/removed props; the ledger round-trips the proposal
  entry; `test_speckle_phase2.py` stays green.

---

## Final Acceptance

- [ ] Place a bench under `Authoring_Furniture` in UE → `ue_capture_furniture.py` dump →
  `capture_furniture.py` → `requests/proposal_furniture_<topic>_<date>.geojson`.
- [ ] `validate_site_furniture.py` **PASSES** the valid bench; the same bench dropped on the ADA
  route **FAILS** with a B3 reason.
- [ ] Maintainer folds the passed proposal into `vectors_geojson/site_furniture.geojson`; the
  furniture layer appears in the export + manifest as **additive**, and the audited design groups
  (seating, stage, ADA, terrain, human-scale, context) are **byte-unchanged**.
- [ ] `speckle_compare.py` shows the added bench; a `proposal`-channel ledger entry records it.
- [ ] All new + existing repo test suites pass (`test_prop_catalog.py`, `test_capture_furniture.py`,
  `test_site_furniture_gate.py`, `test_speckle_phase2.py`); `build_unreal_handoff_manifest.py
  --check` exits 0.

## Out of scope (defer to later phases)

- Terrain/earthwork editing (Phase 3, op authoring on the agentic-clay ledger).
- In-editor real-time constraint feedback (Phase 4) — Phase 1 validates at gate-time only.
- Moving/rotating **existing design** objects (Phase 2 covers constrained moves + identity/diff).
- Freehand sculpt — an explicit non-goal per `docs/unreal_editable_scene_v0.md`.
