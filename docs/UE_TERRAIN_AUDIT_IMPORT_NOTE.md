# Unreal import note — accepted after-state terrain (overflow audit)

**Date/time** 2026-06-27 (local America/Detroit)
**Repo commit at import** `2e636f6` (main; terrain-overflow judge commit merged)
**Editor** UnrealEditor 5.8 on gentoo, live MCP session `127.0.0.1:8000/mcp`
**Level** `/Game/Maps/CivicBowl`
**Datum / CRS** NAVD88 Geoid12A international feet · EPSG:6494 (NAD83(2011) Michigan Central, intl ft)

## What was pushed into Unreal

The CivicBowl review scene was made to visually match the **accepted after-state
terrain audit** (`docs/TERRAIN_OVERFLOW_AUDIT.md`, `reconciliation/`): flat seating
terrace plates with risers, and **no existing-grade terrain competing/overflowing
through the treads**.

This scene represents terrain as **imported static meshes**, not a sculpted UE
Landscape, so "regenerate the Landscape from the corrected heightfield" was done by
re-importing the corrected terrain **mesh** (which derives from the same audited
raster/heightfield) and repointing the terrain actor at it.

## Source provenance (authoritative inputs)

| Item | Path | sha256_12 |
|---|---|---|
| Source raster (proposed grade) | dem/proposed_grade_1ft.tif | 29d7770ba95e |
| Source heightfield (r16, Landscape form) | unreal_export/terrain/heightfield_proposed.r16 | b3958cfcf857 |
| Imported mesh (derived from the raster) | unreal_export/terrain/terrain_proposed.obj | refreshed from audited build |
| Grading ledger | dem/in_situ_grading_manifest.json (flat_plate_rasterization flag) | - |
| Audit overlay (NOT imported as geometry) | reconciliation/accepted_ops.geojson | - |

All four are the corrected (all_touched=True) artifacts. The stale pre-fix copies that
were sitting in the working tree (proposed_grade 86de4d4e99a7) were refreshed from the
audited build and re-audited in place (0 overflow) before import.

## Import parameters

- **Tool**: StaticMeshTools.import_file (FbxFactory; .glb unsupported, so the .obj
  sibling - same exporter, identical local frame - was used).
- **New asset**: /Game/Meshes/CivicBowl/terrain_proposed_audited (imported alongside
  the old terrain_proposed; the actor was repointed, the old asset left untouched - no
  destructive overwrite).
- **Material restored**: slot defaultMat -> /Game/Materials/Context/M_terrain
  (re-import with import_materials=false blanks materials; restored to match the prior
  terrain material - a display fix, not a geometry change).
- **Actor**: Terrain_Proposed (StaticMeshActor_94), folder Reference/Terrain.
  - location (0,0,0), **scale (100,100,100)** (mesh authored in metres -> UE cm),
  - **rotation yaw = 90 deg** - axis correction: the MCP/FbxFactory OBJ importer uses a
    different axis convention than the Interchange import used for the rest of the
    scene, which rotated the mesh 90 deg about Z. yaw=90 maps local->world as
    world_x=-local_y, world_y=+local_x, exactly reproducing the original terrain's
    world footprint so the corrected terrain re-aligns with the seating/stage.
  - tag AuditedAfterState_proposed_grade_29d7770ba95e_allTouchedTrue.

## Landscape / mesh geometry verification (against provenance metadata)

| Property | Expected (provenance) | Imported mesh | OK |
|---|---|---|---|
| Grid | 801 x 801 @ 1 ft | XY span 243.84 m = 800 ft | yes |
| Footprint local (m) | NW corner (-135.636, 118.095, 179.292) | min (-135.636, -118.095, 179.292) | yes |
| Z span | 73.862 ft = 22.513 m | 201.806 - 179.292 = 22.513 m | yes |
| Elevation min/max | 588.23 / 662.092 ft NAVD88 | local z 179.29-201.81 m, same span | yes |
| World placement (cm) | x[-12574.52,11809.48], y[-13563.60,10820.40], z[17929.25,20180.56] | identical after yaw=90 | yes |

Z origin 17929.25 cm = 179.2925 m = provenance nw_corner_local_m.z (datum preserved,
no vertical offset introduced). The decoded heightfield_proposed.r16 matches the source
raster exactly (801 sq, elev 588.230-662.092 ft) - the imported surface derives from
the audited heightfield.

## Existing-grade handling (no competing surface)

- Terrain_Existing (StaticMeshActor_95, mesh /Game/Meshes/CivicBowl/terrain_existing)
  was **visible** (bVisible=true) and competing over the bowl.
- It is now: bVisible=false, bHiddenInGame=true; moved to outliner folder
  **ExistingGrade_AuditGhost**; relabeled ExistingGrade_AuditGhost; tagged
  NonGoverning_AuditGhost_DisabledByDefault.
- *Data Layer note*: the MCP toolset exposes no World-Partition Data-Layer API, so a
  clearly-named **disabled-by-default outliner folder + hidden + tagged** actor is the
  available equivalent of the requested ExistingGrade_AuditGhost Data Layer. The actor
  is retained (not deleted) so the existing grade stays inspectable but subordinate and
  non-governing.
- ctx_fg_terrain (StaticMeshActor_5) was checked and lies entirely at +x
  (12267-65981 cm) - foreground context **outside** the bowl footprint (negative x); it
  does not overflow the treads and was left unchanged.

## Hard rule compliance (no faking)

No sculpting, smoothing, z-offset, vertex masking, mesh deletion, material-priority
trick, or camera trick was used to hide terrain. The visible terrace surface derives
entirely from the **audited corrected mesh** (<- terrain_proposed.obj <- corrected
proposed_grade_1ft.tif, re-audited 0 overflow). The only non-geometry edits are the
material restore (cosmetic, matches prior) and hiding the existing-grade actor into a
labeled disabled audit-ghost. accepted_ops.geojson was deliberately **not** imported as
terrain geometry (kept as a repo-side audit overlay).

## Matched-camera evidence (renders/ue_terrain_audit/)

Same four camera poses before and after the import (world cm):

| View | location | rotation (pitch,yaw) |
|---|---|---|
| overview | (-29086.79, 17944.01, 39766.09) | (-32, -30) |
| plan | (-2434, 1043, 22500) | (-88, -30) |
| oblique terraces | (-12000, 7000, 27000) | (-30, -30) |
| human-scale seat | (-1600, 2300, 18760) | (9, -128) |

Files: before_{overview,plan,oblique,human}.png, after_{...}.png.

**Reading the captures**: the after overview is indistinguishable from before - this
*confirms* the corrected terrain is placed/oriented identically (yaw=90 correct) and
aligned with the seating. The fringe correction is sub-foot (worst case +1.33 ft /
0.40 m at tread_south_r18), so it is intentionally subtle at review-camera scale; the
dominant visible change is removal of the now-hidden coincident existing surface (less
z-fighting). The **authoritative** proof of "no overflow" is the numeric audit on the
source raster/heightfield (0 cells, 0.00 ft) - Unreal is the viewer, the ledger is the
source of truth.

## Persisted

AssetTools.save_assets(['/Game/Maps/CivicBowl', '/Game/Meshes/CivicBowl/terrain_proposed_audited'])
-> true. Actor/component overrides (repoint, yaw, hide) are stored inline in the .umap.
The UE project lives at /mnt/data/UnrealProjects/PetoskeyCivicBowl (outside this repo);
this repo commit carries the display/import **record** (this note + the matched captures).
