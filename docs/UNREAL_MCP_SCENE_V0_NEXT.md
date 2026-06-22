# Unreal MCP Read-Only Scene v0 — Next Step

**Status:** `PLAN · doc-only · no Unreal install/clone/launch · no Speckle · no geometry/ledger/validation change`
**Date:** 2026-06-22 · **Repo:** `amphitheatre` · branch `unreal/mcp-readonly-scene-v0`
**Companions:** [`unreal_mcp_readonly_scene_v0.md`](unreal_mcp_readonly_scene_v0.md) (operator runbook),
[`gentoo_unreal_host_setup.md`](gentoo_unreal_host_setup.md) (host install/MCP verification, §8 assembly log),
[`unreal_handoff_v1.md`](unreal_handoff_v1.md) (handoff governance), `data/unreal_handoff_manifest.json`.

> Scope reminder: this is the **Unreal / UE 5.8 MCP scene** surface — an editor/MCP target on
> gentoo, **not** a web endpoint. It is distinct from the always-on static Three.js web viewer
> (`http://gentoo.scarrow.tailnet:8788/`) and from the Speckle review service. Unreal is a
> viewer/proposal surface; the Python/QGIS gates + `data/speckle_publish_ledger.json` remain the
> sole acceptance authority.

---

## 1. Current state

- **Host:** gentoo has **UE 5.8.0** installed at `/mnt/storage/UnrealEngine-5.8/` and the bundled
  **Unreal MCP** plugin verified end-to-end **headless** (loopback `http://127.0.0.1:8000/mcp`,
  HTTP+SSE). Project: `/mnt/data/UnrealProjects/PetoskeyCivicBowl/`.
- **A read-only scene already exists and persists:** `/Game/Maps/CivicBowl` was assembled + saved
  headlessly via MCP and survives a disk reload — verified inventory **2 terrain / 1 seating /
  1 stage / 7 cameras** (see `gentoo_unreal_host_setup.md` §8):
  | Outliner folder | Actors |
  |---|---|
  | `Reference/Terrain` | `Terrain_Existing`, `Terrain_Proposed` |
  | `Accepted_ReadOnly/Seating` | `Seating_Rows` (45 treads, per-row NAVD88 elevations) |
  | `Proposal_Editable/Stage` | `Stage_Floor` (6 slabs, `Rule-9-OPEN` / PROVISIONAL) |
  | `Cameras` | 7 `CineCameraActor` (positioned + `look_at`; `slot:`/`fov:` tags) |
- **Two reproducibility gaps block v0 from being "done":**
  1. The assembly scripts (offline GeoJSON→OBJ generator + the MCP placement driver) live only in
     the **ephemeral job tmp** — they are **not in the repo**, so the scene **cannot be rebuilt
     deterministically** from a checkout.
  2. The committed runbook `unreal_mcp_readonly_scene_v0.md` §1 is **stale** — it predates the
     assembly and still reports "0 imported / none rendered / not connected." The accurate assembly
     record (`gentoo_unreal_host_setup.md`) is itself currently **untracked**.

## 2. Exact missing artifact(s)

In priority order (smallest/safest first):
1. **`scripts/unreal/` — committed, reproducible assembly** (the smallest next implementation, §4):
   - `gen_review_meshes.py` — offline EPSG:6494 GeoJSON + terrain → OBJ in the local-ENU-metre frame
     (`shapely` + `trimesh` + `mapbox_earcut`; glb→obj for existing terrain). No engine needed.
   - `assemble_scene_mcp.py` — the MCP driver: import meshes, place actors (scale ×100), folders,
     labels, tags, cameras (`look_at`), then save level **inline** + save each imported mesh asset.
2. **ADA route ribbon** — `geo/ada_route.geojson` (39 LineStrings) → extruded ribbon actor.
3. **Material assignment** — band-status seating colors + provisional stage hatch from
   `manifests/material_manifest.json` (currently untextured).
4. **Sightline DataTable** — from `tables/sightline_table.csv`; needs a `TableRowBase` struct that is
   **not creatable headless** (needs a GUI session or a committed C++/uasset struct).
5. **Rendered captures** — `unreal_export/captures/` (reserved, not yet created); needs a **GUI/GPU**
   launch (`run_mcp_server.sh 8000 gui`).
6. **Camera FOV application** — FOV is tagged on the actors but not yet applied to the `CineCamera`.

## 3. Required source inputs (all present + verified, do not regenerate)

`verify_unreal_export.py` → **30 pass · 0 fail**; `build_unreal_handoff_manifest.py --check` → **PASS**.

- `unreal_export/geo/{seating_rows,seating_row_splines,stage_floor,ada_route}.geojson`
- `unreal_export/terrain/terrain_{existing,proposed}.{obj,glb}` (+ heightfields, not needed for v0)
- `unreal_export/manifests/{actor,material,camera,provenance}_manifest.json`
- `unreal_export/tables/sightline_table.csv`
- `data/unreal_handoff_manifest.json` (CRS, units, MCP runway allow/deny, fingerprint)

Frame contract (from the manifest): **local ENU metres, Z-up** (`x=east, y=north, z=NAVD88 ft ×0.3048`),
origin EPSG:6494 `(19533067.7, 750799.2)` intl ft; UE places at **×100** (cm). Reverse transform is
in the manifest `crs` block for any proposal round-trip.

## 4. Smallest viable next implementation

**Land the two assembly scripts in the repo so `/Game/Maps/CivicBowl` is reproducible from a
checkout, and de-stale the runbook.** This is authorable **without launching the editor** (only the
later *verification* run needs gentoo's MCP). It converts a one-off manual artifact into a gated,
repeatable v0, and is the prerequisite for every later increment (ADA/materials/captures).

Scene contents for this v0 = exactly the proven baseline (no new geometry): Terrain ×2 +
Seating_Rows (45 treads) + Stage_Floor (6 slabs, provisional) + 7 cameras, in a **non-WP
`Template_Default`** level saved as `/Game/Maps/CivicBowl`. ADA/materials/sightline DataTable/captures
are explicitly **deferred** to follow-on increments (§2 items 2–6).

Deliverables of this step:
- **DONE** — `scripts/unreal/` toolchain landed: `civicbowl_common.py` (frame + `SCENE_SPEC`
  contract), `gen_review_meshes.py` (offline mesh + deterministic `scene_plan.json`),
  `ue_civicbowl.py` (in-editor `assemble`/`verify`), `verify_civicbowl.py` (offline report),
  and `scripts/unreal/README.md`. Offline gen+verify tested; in-editor scripts syntax- and
  dry-run-checked. The v0 inventory actually exceeds the original baseline (adds ADA routes +
  landings, treatment cell, event floor, bay-view axis), sourced entirely from the gated
  `unreal_export/` package. Remaining: human-scale refs (not yet in the geo/ package),
  colored materials, sightline DataTable, captures — see `scripts/unreal/README.md`.
- TODO — refresh `unreal_mcp_readonly_scene_v0.md` §1 once the scripts run live on gentoo.
- DONE — `gentoo_unreal_host_setup.md` is now tracked (commit `756ac9d`).

## 5. MCP verification target (run later on gentoo)

After running the committed scripts against the live MCP and `save_assets(level)`, **reload** the
level in a fresh session and assert:
- Actor inventory: **2** terrain, **1** seating (45 treads), **1** stage (6 slabs), **7** cameras.
- Tags present: `acceptance:*`, `PLANNING-GRADE`, stage carries `Rule-9-OPEN` / `must_label`.
- Coordinate sanity: a known tread's UE position == `anchor_local_m × 100` from `actor_manifest.json`.
- No new/edited authoritative files (see §7 acceptance).

## 6. Commands expected to be run later on Gentoo (NOT run now)

```sh
# 1. start the headless MCP assembly server (no display); MCP at http://127.0.0.1:8000/mcp
/mnt/data/UnrealProjects/PetoskeyCivicBowl/run_mcp_server.sh
#    (GPU/GUI variant only when rendering captures — a later increment:)
#    /mnt/data/UnrealProjects/PetoskeyCivicBowl/run_mcp_server.sh 8000 gui

# 2. register the Unreal MCP server in this project's mcpServers BEFORE starting the session
#    (mid-session registration is not possible), then start Claude Code from the project dir:
cd /mnt/data/UnrealProjects/PetoskeyCivicBowl && claude

# 3. drive assembly from the committed scripts (offline meshes first, then MCP placement):
python /home/sam/projects/amphitheatre/scripts/unreal/gen_review_meshes.py --out /tmp/civicbowl_meshes
#    then run scripts/unreal/assemble_scene_mcp.py via the MCP tools (import → place → save inline)

# 4. verify: reload /Game/Maps/CivicBowl in a fresh session, assert the §5 inventory + tags
```

## 7. Risks / unknowns

- **Job-tmp scripts may be gone.** If the original generator/driver are not recoverable, re-author
  from `gentoo_unreal_host_setup.md` §8.222 (documented in enough detail to reconstruct).
- **World Partition / OFPA persistence trap.** Spawned actors do **not** persist in a WP/OpenWorld
  template headless. **Must** use a non-WP `Template_Default` level and save actors **inline** in the
  `.umap` (proven). Keep `DefaultEngine.ini` `EditorStartupMap` pointing at a map that exists.
- **`save_assets(level)` does not save imported meshes** — save each imported mesh asset path too, or
  actors reference missing meshes on reload.
- **Sightline DataTable struct** (`TableRowBase`) is **not creatable headless** — needs a GUI session
  or a committed C++/uasset struct; that increment cannot be fully headless.
- **Handedness:** current mapping is direct ENU→UE (internally consistent but a global mirror vs true
  geography); a Y-negation may be needed for true-north fidelity — decide before captures.
- **Importer constraints:** FbxFactory accepts **obj/fbx, not glb**; no native GeoJSON importer (hence
  the offline OBJ step). `never pkill -f` a UE pattern (self-matches the killing shell); stop by PID.

## 8. Acceptance criteria

1. `/Game/Maps/CivicBowl` is **rebuildable from the committed `scripts/unreal/`** alone (given a live
   MCP on gentoo) — no reliance on job-tmp.
2. A fresh-session reload shows the **§5 inventory + tags** exactly.
3. `unreal_mcp_readonly_scene_v0.md` no longer claims "0 imported"; `gentoo_unreal_host_setup.md` is
   tracked.
4. **No accepted geometry, validation script, Speckle state, or ledger change.**
   `verify_unreal_export.py` → 30/0 and `build_unreal_handoff_manifest.py --check` → PASS still hold.
5. Anything edited in Unreal returns **only** as a proposal GeoJSON in EPSG:6494 through the existing
   gates before it can become design truth (manifest `authoritative_boundary`).
