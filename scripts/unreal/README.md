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

Built from the gated package (93 placed objects + 7 cameras):

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
- **human-scale refs: TODO** — `vectors_geojson/human_scale_refs.geojson` is not in
  the gated `unreal_export/geo/` package; export it via `build_unreal_export.py`
  first, then it becomes a built group.
- **Sightline DataTable: TODO** — needs a `TableRowBase` struct, not creatable
  headless (GUI or committed C++/uasset).
- **Rendered captures: TODO** — need a GPU/GUI launch (`run_mcp_server.sh 8000 gui`).
- **Handedness — CLASSIFIED (mirror, not a rotation/data error):** the ENU source
  data is geographically faithful (verified: bay-view axis azimuth = 330.0° NNW,
  matching the manifest; camera azimuths match; seating wraps the SE quadrant
  opening NW). The bug is only the frame mapping: `civicbowl_common` copies ENU
  (right-handed: E,N,Up) → UE (left-handed) component-wise, which is a **parity
  reflection** — the scene is internally consistent but mirror-imaged vs true
  geography (clockwise-from-north angles read counter-clockwise; E/W sense flips).
  Does **not** block assembly/verify. Fix (follow-on): negate one horizontal axis
  in the transform (e.g. UE_Y = −north, the conventional X=North/Y=East mapping),
  then re-gen. Left as-is for v0 per "don't fix visual issues that don't block."

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

Still pending live: colored materials, human-scale refs, sightline DataTable,
rendered captures (GPU/GUI), and the handedness Y-negation above.
