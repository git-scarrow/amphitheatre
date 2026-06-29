# Terrain-Operation Ledger — agentic clay for the Unreal amphitheatre

**Problem this fixes.** The Unreal scene showed *grass over the seats*. That was
never only a material bug: it meant the **visible terrain was not being generated
from auditable terrain operations**. A single terrain skin was being drawn, and
the seating sat on top of it, so existing ground poked through the plates.

**The fix is architectural, not cosmetic.** The visible ground is now decomposed,
surface by surface, into *operations* in a ledger. Every earthform, terrace,
tread, riser, ADA path, drainage strip and stage surface carries an `op_id` and
traces back to the accepted **Open Civic Bowl** design. Unreal *visualizes* the
repo-generated after-state; it is never the source of truth and never sculpts
final terrain.

---

## Scope note (read first)

This work re-bases the auditable terrain-ops architecture on the **Open Civic
Bowl 16-row open fan** (`design_open_low/`), which the task names as the accepted
design to preserve:

- 16-row open fan, ±55° / 110° arc, audience facing 330° (NNW, Little Traverse Bay)
- stage-forward, low open bay-facing venue
- **no default retaining walls** (every riser is a planted slope < 2.0 ft)

The 45-tread **Scenario E** bowl currently imported into the live UE scene is a
separate seating-*capacity* study (`analysis/scenarioE_civic/`). It is not
contradicted here; this ledger is the auditable terrain architecture for the
accepted Open Civic Bowl and can be applied to Scenario E later by pointing the
generator at that geometry.

---

## The ledger

`design/terrain_ops.current.json` — schema `amphitheatre/terrain-ops/0.2`, the
**accepted** ledger (only written by the validator on a clean pass).
`design/terrain_ops.proposal.json` — the **proposed** ledger (written by the
generator; not trusted until gated).

Each operation records: `op_id`, `kind`, `surface_class`, `row`, `parent`,
`material`, `geometry_ref` (layer + `#op_id`), elevations, `debug_color`,
`provenance` (source feature + the validation attribute read), and `status`.

### Each row = six engineered terrace operations

A row is not a bare graded slope. Reading its ~3 ft radial pitch from the
down-slope (stage) edge outward to the up-slope (back) edge:

| op suffix      | surface_class | construction material              | what it is |
|----------------|---------------|------------------------------------|------------|
| `.riser`       | `riser`       | planted / seeded slope             | near-vertical face up from the row below |
| `.tread`       | `tread`       | compacted gravel fines             | the walkable foot tread plate |
| `.cap`         | `cap`         | timber / light precast             | the seat cap at the back of the tread |
| `.drainage`    | `drainage`    | open gravel strip                  | drainage edge at the up-slope back |
| `.transition`  | `cut`/`fill`/`existing_no_touch` | graded feather    | ties the plate back to existing grade |
| `.clip`        | `clip` (mask) | — (suppresses terrain draw)        | the footprint where terrain must not draw |

Plus the bowl-scale ops: `op.grade.existing` (existing/no-touch LiDAR ground),
`op.grade.p_current` (accepted after-state grade; raster authority
`dem/proposed_grade_1ft.tif`), `op.stage.*` / `op.floor.forecourt` (low open
stage), `op.cell.treatment` (stormwater basin, concept tier), `op.ada.*`.

### Surface classes (the debug-view taxonomy)

`existing_no_touch · cut · fill · cap · tread · riser · drainage · ada · stage`
— each with a fixed debug colour (see `surface_classes` in the ledger).

---

## How terrain is kept off the seats (criterion 5)

Three independent guarantees, defence in depth:

1. **Raster flattening** — `build_proposed_grade.py` already burns every flat
   plate with `all_touched=True`, so the proposed-grade DEM equals the plate
   elevation across the *whole* footprint incl. the perimeter fringe (the
   original +1.33 ft green overflow → 0; `docs/TERRAIN_OVERFLOW_AUDIT.md`).
2. **Geometric clip masks** — each row's `op.rowNN.clip` is the union footprint
   of its riser/tread/cap/drainage surfaces, flagged `suppress_terrain_draw`.
   ADA and stage surfaces carry the same flag. The validator proves (G4) that
   every cap/tread/riser/drainage radial footprint lies inside its clip mask.
3. **Render lift** — constructed surfaces are lifted `render_lift_ft` (0.02 ft)
   in UE so terrain cannot z-fight up through a plate at grazing angles.

The material manifest's `clip_policy` records all three.

---

## Pipeline

```
# 1. generate the PROPOSAL ledger + geometry layers + material manifest
python scripts/build_terrain_ops.py
#    -> design/terrain_ops.proposal.json
#    -> unreal_export/geo/terrace_ops/*.geojson
#    -> unreal_export/manifests/terrace_material_manifest.json

# 2. gate it; on PASS it is promoted to the ACCEPTED ledger
python scripts/validate_terrain_ops.py
#    -> design/terrain_ops.current.json   (only on all gates PASS)

# 3. bake per-op OBJ meshes for UE import (one mesh per op_id)
python scripts/build_terrace_op_meshes.py
#    -> unreal_export/terrain/terrace_ops/<op_id>.obj + mesh_manifest.json

# 4. before/after + human-scale aisle views
python scripts/viz_terrace_ops.py
#    -> analysis/terrace_ops/op_view_before_after.svg  (+ .png)
#    -> analysis/terrace_ops/aisle_cross_section.svg   (+ .png)
```

All four scripts are **stdlib + numpy only** — they run on a fresh checkout where
the LiDAR DEM and the GIS stack (rasterio/shapely/geopandas) are absent, mirroring
the repo's existing missing-data tolerance.

### Validator gates (= the acceptance criteria)

- **G1** 16-row open fan, every row carries all 6 operations
- **G2** fan arc is ±55° (110° total) — Open Civic Bowl invariant
- **G3** every visible surface feature has an `op_id` + `surface_class`
- **G4** each clip mask covers its cap/tread/riser/drainage; ADA + stage suppress
  terrain draw → *terrain cannot overlap seat caps or tread surfaces*
- **G5** no default retaining walls — every riser < 2.0 ft (planted slopes)
- **G6** every constructed surface has a construction material; manifest carries
  the clip policy

---

## In Unreal (criteria 6, 7)

`scripts/unreal/ue_terrace_ops.py` runs inside the UnrealEditor python env and is
driven entirely by the accepted ledger + mesh manifest — nothing is authored by
hand:

```python
import ue_terrace_ops as O
O.apply_construction_materials(unreal)   # timber caps, gravel treads, planted risers, …
O.apply_op_debug_view(unreal)            # colour every surface by op_id surface class
O.enforce_terrain_clip(unreal)           # lift plates + keep terrain off them
```

Headless (`python scripts/unreal/ue_terrace_ops.py`) prints the auditable per-op
assignment plan — what a reviewer / CI checks without a GPU. **Live GPU capture
of the scene is the project-wide PENDING item** (`docs/MACBOOK_UNREAL_CLIENT.md`,
`docs/SUNSHINE_MOONLIGHT_GENTOO.md`); the SVG/PNG before/after + aisle views stand
in for it, exactly as `viz_terrain_audit.py` already does for the overflow audit.

---

## Acceptance-criteria trace

| criterion | where |
|-----------|-------|
| 1. create/update `terrain_ops.current.json` | validator promotes proposal → current |
| 2. each row = 6 engineered terrace ops | `build_terrain_ops.py` (`BAND_PLAN`) |
| 3. explicit geometry layers | `unreal_export/geo/terrace_ops/*.geojson` + per-op OBJ |
| 4. material masks from the ledger | `terrace_material_manifest.json` |
| 5. terrain not drawn over caps/treads/ADA/stage | clip masks + all_touched raster + render lift (G4) |
| 6. UE debug view colours by `op_id` | `ue_terrace_ops.apply_op_debug_view` |
| 7. materials show construction logic | `CONSTRUCTION_LOOK` + manifest |
| 8. before/after + aisle views | `analysis/terrace_ops/*.svg/.png` |
| no grass over caps/treads | G4 PASS + raster overflow 1108→0 cells |
| every surface has an op_id or is existing/no-touch | G3 PASS |
| materials communicate *how*, not just colour | construction material per surface |
| UE matches the accepted audited after-state | UE reads the gated ledger only |
| proposals wait for validation before accepted | proposal → validate → current |
