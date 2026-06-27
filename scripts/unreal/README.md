# `scripts/unreal/` — reproducible CivicBowl UE 5.8 MCP scene

Durable, repo-side toolchain that **regenerates and verifies** the read-only
`/Game/Maps/CivicBowl` Unreal Engine 5.8 scene from **tracked** Petoskey source
artifacts. It replaces the earlier one-off assembly whose scripts lived only in
ephemeral job-tmp (see `docs/UNREAL_MCP_SCENE_V0_NEXT.md`).

> **Not a web endpoint.** This is an editor / MCP target on gentoo. The always-on
> browser review surface is the static Three.js viewer
> (`http://gentoo.scarrow.tailnet:8788/`); Speckle is a third, separate surface.
>
> **Read-only.** The scene is a *viewer* assembled from the gated handoff package
> (`unreal_export/` + `data/unreal_handoff_manifest.json`). Nothing here writes back
> to `vectors_geojson/`, `dem/`, validation outputs, Speckle, or
> `data/speckle_publish_ledger.json`. The Python/QGIS gates + the ledger remain the
> sole acceptance authority. Anything *edited* in Unreal must return as a proposal
> GeoJSON in EPSG:6494 through the repo gates.

## Files

| File | Where it runs | Role |
|---|---|---|
| `civicbowl_common.py` | anywhere | Shared contract: tracked source paths (parameterized), the EPSG:6494-ft ↔ local-ENU-metre frame + ×100 UE scale, and `SCENE_SPEC` (the canonical inventory the verifier checks). |
| `gen_review_meshes.py` | **offline** (laptop/CI) | Reads the gated package → writes per-actor OBJ meshes + a deterministic `scene_plan.json` into `build/unreal_scene/` (git-ignored). |
| `ue_civicbowl.py` | **inside UE** (gentoo) | `assemble` builds the level from the plan; `verify` loads it and reports the actor inventory. `--dry-run` walks the plan with no engine. |
| `verify_civicbowl.py` | anywhere | Offline report: inputs present, expected vs. built group counts, missing meshes, deferred TODOs, and the live-verify command path. |

## Regenerate the scene

```sh
# 1. OFFLINE — stage meshes + the deterministic plan (needs the repo venv:
#    shapely trimesh numpy mapbox_earcut). Output: build/unreal_scene/
python scripts/unreal/gen_review_meshes.py            # --repo / --out to parameterize

# 2. OFFLINE — confirm the plan is complete before going near the engine
python scripts/unreal/verify_civicbowl.py             # exit 0 == PASS

# 3. ON GENTOO — start the headless MCP server (loopback 127.0.0.1:8000/mcp)
/mnt/data/UnrealProjects/PetoskeyCivicBowl/run_mcp_server.sh

# 4. ON GENTOO — assemble through MCP. Either have the MCP-connected Claude Code
#    session run ue_civicbowl.py via the server's Python tool, OR headless:
UnrealEditor-Cmd /mnt/data/UnrealProjects/PetoskeyCivicBowl/PetoskeyCivicBowl.uproject \
    -run=pythonscript \
    -script="$PWD/scripts/unreal/ue_civicbowl.py assemble --plan $PWD/build/unreal_scene/scene_plan.json"
```

`build/unreal_scene/` is git-ignored and fully regenerable; only the four
`scripts/unreal/*.py` + this README are tracked. `gen_review_meshes.py` is
deterministic — re-running produces a byte-identical `scene_plan.json`, so
`gen` + `git diff` is itself a reproducibility check.

## Verify

```sh
python scripts/unreal/verify_civicbowl.py             # offline: inputs + plan + counts
# on gentoo, editor up:
python scripts/unreal/ue_civicbowl.py verify          # live: load map, count actors vs SCENE_SPEC
```

`verify` reports: project/map path · imported actor inventory by folder · expected
geometry-group counts · missing inputs · whether the map reloads via MCP.

## Scene inventory (v0)

Built from the gated package (112 placed objects + 7 cameras):

| Group | Folder | Count | Source |
|---|---|---|---|
| terrain | `Reference/Terrain` | 2 | `terrain_{existing,proposed}` |
| seating | `Accepted_ReadOnly/Seating` | 45 | `geo/seating_rows.geojson` |
| stage | `Proposal_Editable/Stage` | 3 | `geo/stage_floor.geojson` (`zone_stage_*`) |
| treatment cell | `Concept_Landscape/TreatmentCell` | 1 | `geo/stage_floor.geojson` |
| event floor | `Concept_Landscape/EventFloor` | 1 | `geo/stage_floor.geojson` |
| bay-view axis | `Reference/BayView` | 2 | `geo/stage_floor.geojson` (`lineage_*`) |
| ADA routes | `Concept_ADA/Routes` | 8 | `geo/ada_route.geojson` (lines) |
| ADA landings | `Concept_ADA/Landings` | 31 | `geo/ada_route.geojson` (points) |
| human scale | `Reference/HumanScale` | 19 | `geo/human_scale_refs.geojson` (15 figures + 4 dims) |
| cameras | `Cameras` | 7 | `manifests/camera_manifest.json` |

Materials/validation/tags come from `manifests/actor_manifest.json` (joined by
`feature_id`) — never recomputed. Provisional/concept actors keep `PLANNING-GRADE`,
`Rule-9-OPEN`, `must_label`, and `concept_pending_civil` tags.

## Known risks / missing pieces (v0 is deliberately crude)

- **Visual crudeness:** footprint slabs (0.15 m), ribbon ADA routes (1.2 m proxy
  width), and unit-cube markers for points. Faithful positions, blocky geometry.
- **No colored materials yet:** legibility is via folder grouping + tags. The
  `material_manifest.json` colors are staged in the plan; applying them in-editor
  is a follow-on (creating persistable material assets headless is fiddly).
- **Draped elevations:** ADA route lines + the bay-view axis/focal carry `z==0` in
  the manifest, so they're draped onto a data-derived datum (route = mean of its
  landings; bay-view = stage datum). Recorded in `scene_plan.json["warnings"]`.
- **human-scale refs: INCLUDED** — exported to the gated
  `unreal_export/geo/human_scale_refs.geojson` by `build_unreal_export.build_human_scale`
  (baseline only; `scope:ambitious_option` excluded) and built as the
  `Reference/HumanScale` group: exact-height posts (head apex = ground + `height_ft`) +
  dimension ribbons, `SCENE_SPEC` expected **19**. `verify_unreal_export.py` gate I and
  the package audit fail if the layer is dropped.
- **Sightline DataTable: TODO** — needs a `TableRowBase` struct, not creatable
  headless (GUI or committed C++/uasset).
- **Rendered captures: TODO** — need a GPU/GUI launch (`run_mcp_server.sh 8000 gui`).
- **Handedness — FIXED (`civicbowl_common.enu_to_ue`).** ENU is right-handed
  (x=East, y=North, z=Up); Unreal is left-handed. The original component-wise copy
  (UE_X=East, UE_Y=North) had determinant **+1** — it left the data right-handed
  inside UE's left-handed frame, so the scene rendered **mirror-imaged**. The
  transform is now the conventional, handedness-flipping map
  **`UE_X = North, UE_Y = East, UE_Z = Up`** (East↔North swap, determinant **−1**),
  baked into every mesh, marker anchor, and camera coordinate by `gen_review_meshes`.
  `verify_civicbowl.py` asserts det = −1 and checks azimuths through the map:
  bay-view axis = 330.0° NNW; seating east/SE/south = 105/135/169° (S/SE rake);
  consistent with the geographically-faithful ENU source. `ue_civicbowl.py` is
  frame-agnostic (it just places the UE coords the plan gives it).

## First live run on gentoo — 2026-06-22 (PASS)

Ran headless via `UnrealEditor-Cmd … -run=pythonscript` (the MCP path needs a
session-registered server, unavailable mid-session). Result: `assemble` →
`/Game/Maps/CivicBowl` (2 terrain + 91 actors + 7 cameras), saved inline (250 KB
.umap); reload `verify` → **PASS**, all 9 groups exact. Two issues found + fixed
(both blocked assembly/verification, so in scope):

1. **`spawn_actor_from_object` SIGSEGVs in a commandlet.** It routes through the
   level-editor viewport `PlacementSubsystem::FindAssetFactoryFromAssetData`
   (`PlacementSubsystem.cpp:87`), null without a live editor viewport. **Fix:**
   spawn via `spawn_actor_from_class(StaticMeshActor)` + `set_static_mesh` (uses
   `UWorld::SpawnActor` directly — commandlet-safe).
2. **Assemble was not idempotent** — it spawned on top of the prior scene (counts
   doubled: cameras 7→14, etc.). `delete_asset` on the loaded startup level isn't
   reliable headless. **Fix:** after `load_level`, destroy any actors left in our
   managed folders, then rebuild (verified: cleared 111, rebuilt 93+7 clean).

Confirmed working headless: OBJ import via the **Interchange** importer (no glb —
terrain glb is converted to obj offline), per-mesh `save_asset`, inline level save,
reload + actor enumeration. `never pkill -f` a UE pattern; stop by PID.

**Update 2026-06-22 (later):** handedness fix applied (`UE_X=North, UE_Y=East`,
det −1) and re-verified live — assemble + reload `verify` → **PASS**, orientation
no longer mirrored (det −1, bay-view 330° NNW, seating in S/SE). UE captures are
now spatially trustworthy for review.

**Update 2026-06-22 (human scale):** the human-scale layer is now exported to the gated
package and built as `Reference/HumanScale` (19 = 15 exact-height figure posts + 4
dimension ribbons), through the same det −1 ENU→UE map; offline `gen` + `verify_civicbowl`
PASS (human_scale 19/19, det −1). MCP remains the intended in-editor inspection interface.

Still pending live: colored materials, sightline DataTable, rendered captures (GPU/GUI).

## Context + Horizon v0 (parallel layer — does NOT touch the audited design)

A separate, clearly-labeled geographic-context layer (bay, horizon, optional
open-data city massing, **calculated** sunset sun/sky) lives alongside the
audited scene. It writes its own artifact set and spawns only under the
`Context/` Outliner root, asserted disjoint from every design folder — so the
audited group-count gates never see a context actor. Full write-up:
[`docs/UE_CONTEXT_HORIZON_V0.md`](../../docs/UE_CONTEXT_HORIZON_V0.md).

| File | Where | Role |
|---|---|---|
| `context_common.py` | anywhere | Context contract: layer-field schema, `Context/` root + disjointness guard, bay/horizon datums, and a **real NOAA solar-position calc** (stdlib). |
| `fetch_osm_context.py` | anywhere | Reproducible OSM (ODbL) city fetch via Overpass → `data/context/osm_petoskey_*.geojson`. Default prints the query + expected paths; `--run` downloads. |
| `gen_context.py` | **offline** | Reads `data/unreal_context_manifest.json` → context meshes + deterministic `context_plan.json`. City layers built only if OSM input present, else DEFERRED. |
| `ue_context.py` | **inside UE** | `assemble` adds context under `Context/` (clears only `Context/`); `verify` counts context + confirms the audited design folders are still exact. |
| `verify_context.py` | anywhere | Extended offline gate: design unchanged · manifest valid · context isolated from design gates · **bay-view corridor unobstructed** · orientation preserved. |

```sh
python scripts/unreal/fetch_osm_context.py            # (optional) OSM query/paths; --run to download
python scripts/unreal/gen_context.py                  # -> build/unreal_scene/context_plan.json
python scripts/unreal/verify_context.py               # exit 0 == PASS
# on gentoo: ue_civicbowl.py assemble  THEN  ue_context.py assemble  THEN  ue_context.py verify
```

The layer registry `data/unreal_context_manifest.json` declares every layer's
`source / source_type / accuracy_class / redistributable / intended_use /
included_in_verification`. No proprietary Google assets; OSM carries ODbL
attribution. Context never contributes to a design gate (none set
`included_in_verification:true`).

**First context pass — 2026-06-22 (PASS).** Offline `verify_context` PASS; live
(gentoo, `-nullrhi`) context assemble → `3 actors + 1 camera + 2 sun lights` under
`Context/`, reload `ue_context.py verify` → **PASS** with all 9 audited design
groups still exact. Calculated sunsets: solstice 21:33 EDT az 305.7° NW; mid-Aug
20:48 EDT az 290.9° WNW — both ~24–39° west of the 330° bay-view axis. City
massing/roads DEFERRED pending an OSM fetch with network egress.
