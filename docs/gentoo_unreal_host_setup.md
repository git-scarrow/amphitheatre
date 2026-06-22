# Gentoo as the Unreal MCP Execution Host — Setup Plan v0

**Status:** `✅ INSTALLED + MCP VERIFIED (headless) on gentoo — 2026-06-20`
**Engine:** UE 5.8.0 (promoted, CL 55116800) at `/mnt/storage/UnrealEngine-5.8/`. **Project:**
`/mnt/data/UnrealProjects/PetoskeyCivicBowl/` (plugins: `ModelContextProtocol`, `GeoReferencing`,
`EditorToolset`). **MCP bridge verified end-to-end headless** — see §7. The MCP-driven scene
*assembly* is the remaining follow-up (needs a Claude Code session with the server registered; and
rendered captures need a GPU/RHI launch, not `-nullrhi`). **Ledger untouched.**
**Date:** 2026-06-20 · **Host:** `gentoo` (primary workstation) · **Repo HEAD:** `d21419a`
**Change to geometry / validation / ledger:** **none.** Documentation only.

This is the host-preparation companion to
[`unreal_mcp_readonly_scene_v0.md`](unreal_mcp_readonly_scene_v0.md). That doc specified the
operator runbook for "a host with UE 5.8 + MCP." This doc records the **read-only capability
probe of gentoo** and the **minimal Gentoo-specific install/run plan** to make gentoo that host.

> Unreal proposes; the gates decide; the ledger records. Nothing here is design truth. The repo
> (Python/QGIS gates + `data/speckle_publish_ledger.json`) remains the sole acceptance authority.

---

## 1. Host capability probe (observed facts, 2026-06-20, read-only)

| Check | Result | Verdict vs UE 5.8 Linux requirement |
|---|---|---|
| **GPU** | NVIDIA GeForce **RTX 4080 SUPER**, 16 GB VRAM (5.3 GB in use) | ✅ exceeds rec. (2080, 8 GB+) |
| **Driver** | NVIDIA **610.43.02**, CUDA UMD 13.3 | ✅ exceeds min (NVIDIA 570+) |
| **Vulkan** | `vulkaninfo` OK — apiVersion **1.4.341**, NVIDIA driver, `/dev/dri/{card0,renderD128}` present | ✅ Vulkan RHI ready |
| **CPU** | Intel **i9-12900K**, 24 threads | ✅ exceeds rec. (quad-core 2.5 GHz) |
| **RAM** | **31 GiB** total (16 GiB free now) + **47 GiB swap** | ⚠️ at rec. line (32 GB); swap covers headroom |
| **Disk** | `/` 86 GB free · `/mnt/fast` 162 GB (NVMe) · `/mnt/data` 277 GB · `/mnt/storage` **2.8 TB** | ✅ ample — **install off `/`** |
| **Kernel / glibc** | kernel 7.0.11 (≫ 4.18) · modern glibc (≫ 2.28) | ✅ exceeds min |
| **Display** | Live **Hyprland/Wayland** session on seat0; **Xwayland `:0`** + `wayland-1` present | ✅ local GUI path (editor runs under Xwayland) |
| **Unreal Engine 5.8** | **ABSENT** — no `UnrealEditor` on PATH; no `~/UnrealEngine*`/`/opt`/flatpak/Steam; no `*.uproject` | ❌ must install |
| **Unreal MCP bridge** | **ABSENT** — no `unreal_mcp` module, no npm pkg, no source tree | ❌ ships *with* UE 5.8 (see §3) |
| **Agent MCP config** | `~/.claude.json` top-level `mcpServers: []`; amphitheatre project `mcpServers: []`; no `.mcp.json`; no `unreal` token anywhere | ❌ nothing to connect to yet |
| **Handoff package** | `verify_unreal_export.py` **30 pass · 0 fail**; `build_unreal_handoff_manifest.py --check` **PASS** | ✅ import-ready, unchanged |

**Bottom line:** gentoo is **hardware- and display-ready**. The only gaps are the engine and the
MCP bridge, both filled by **one install: the UE 5.8 precompiled Linux build** (the MCP plugin is
bundled — §3). RAM is exactly at the recommended line; the 47 GiB swap and 16 GB VRAM cover the
editor comfortably for a review scene.

---

## 2. Key simplification since the v0 doc

The v0 runbook assumed a *separate* "official Unreal MCP plugin" had to be installed into
`Plugins/`. As of **UE 5.8 the MCP server is a bundled engine plugin** — Epic's
[*Unreal MCP in Unreal Editor*](https://dev.epicgames.com/documentation/unreal-engine/unreal-mcp-in-unreal-editor):

- Plugin name: **"Unreal MCP"** (engine id `ModelContextProtocol`; auto-enables dependency
  *Toolset Registry*). **Experimental** — APIs/data formats may change.
- Server endpoint: **`http://127.0.0.1:8000/mcp`** (port + path configurable in Editor Preferences).
- Transport: **HTTP + Server-Sent Events only** (no `stdio`, no WebSocket).
- Security: **loopback-only by default**, rejects non-loopback `Origin`, **no auth** — do not expose.
- Start: Editor Preferences → General → *Model Context Protocol* → **Auto Start Server**, or console
  `ModelContextProtocol.StartServer`.
- Client wiring: console `ModelContextProtocol.GenerateClientConfig ClaudeCode` writes a `.mcp.json`
  into the **UE project root**; launch Claude Code from there. (Alternative: register the same HTTP
  endpoint in the amphitheatre project's `mcpServers` — see §4 step 6.)

**Consequence:** because scene assembly uses only MCP *allowed ops* (import GeoJSON / heightfield /
DataTable, spawn cameras, assign materials/labels) and the MCP plugin is an engine plugin, **no
engine source build and no project-C++ compile are required.** The **precompiled binary path is
sufficient end-to-end** — this is the minimal route and avoids the clang-18 / multi-hour compile.

---

## 3. Minimal install/run plan (precompiled binary — RECOMMENDED)

Two stages. Stage A is small. **Stage B is the large step and is gated on explicit approval +
interactive Epic login.** Nothing here is run yet.

### Stage A — small prerequisites  ✅ ALREADY SATISFIED (verified 2026-06-20, nothing to emerge)
All runtime deps and CLI tools are present; UE bundles its own clang/ICU/SDL.
```
media-libs/vulkan-loader-1.4.350.0   x11-libs/libX11-1.8.13   media-libs/libglvnd-1.7.0
sys-libs/glibc-2.43-r2   x11-libs/libxcb-1.17.0   media-libs/libsndfile-1.2.2-r2
curl ✓  wget ✓  unzip ✓  tar ✓  xdpyinfo ✓   NVIDIA Vulkan ICD: /usr/share/vulkan/icd.d/nvidia_icd.json ✓
DISPLAY=:0 reachable from a non-graphical shell ✓ (editor can be launched headless-of-session)
```
No emerge required. No `pip install` at system level (venv only) — the engine install is binary anyway.

### Stage B — install the engine  ⚠️ LARGE · NEEDS APPROVAL + EPIC LOGIN
1. **Obtain the UE 5.8 precompiled Linux build.** Epic ships a distribution-agnostic Linux zip
   ([requires Epic Games account login](https://www.unrealengine.com/en-US/linux)). This is an
   interactive, authenticated download I cannot perform headless — the operator must download it (or
   provide the URL/local path). Expect a large archive (~tens of GB compressed, **~100–150 GB
   extracted** with DDC).
2. **Extract off `/`** (which has only 86 GB free). Recommended:
   - Engine → `/mnt/storage/UnrealEngine-5.8/` (RAID, 2.8 TB free, **writable** ✓).
   - Project + Derived Data Cache → `/mnt/data` (NVMe, 277 GB, **writable** ✓).
     (`/mnt/fast` is **not writable** by `sam`, so it is not used here.)
3. **Smoke-test the editor** on the live Hyprland session:
   ```
   DISPLAY=:0 /mnt/storage/UnrealEngine-5.8/Engine/Binaries/Linux/UnrealEditor
   ```
   (UE uses Vulkan; runs under Xwayland `:0`. If it fails, fall back to a native X session.)

### Stage B' — source build (ALTERNATIVE, only if precompiled 5.8 Linux is unavailable)
Heavier: link GitHub↔Epic account → clone `EpicGames/UnrealEngine` `release`/`5.8` → `Setup.sh`
(pulls bundled clang toolchain) → `GenerateProjectFiles.sh` → `make`. Needs ~170+ GB and hours of
compile; RAM at 31 GiB will lean on swap during link. **Not recommended** given the bundled-MCP
simplification — only use if Epic has not yet posted a 5.8 precompiled Linux archive.

---

## 4. Run plan — assemble the read-only scene (after Stage B)
Follows `unreal_mcp_readonly_scene_v0.md` §6. Steps 1–2 (git confirm, contract read) and the gate
checks are already green on this host.
1. `python scripts/build_unreal_export.py` (regenerate gitignored terrain binaries) →
   `verify_unreal_export.py` (30 pass) → `build_unreal_handoff_manifest.py --check` (PASS).
2. New UE 5.8 project **`PetoskeyCivicBowl`** on `/mnt/data` — Blank, no starter content,
   World units = **centimeters**; scene frame is local-ENU-metres ×100. Never treat GeoJSON feet as cm.
3. Enable plugins: **Unreal MCP** (`ModelContextProtocol`) and **Georeferencing** (for the GeoJSON
   layers); restart the editor.
4. Start the MCP server (auto-start toggle or `ModelContextProtocol.StartServer`); confirm
   `http://127.0.0.1:8000/mcp` is listening (loopback only).
5. Wire the agent: console `ModelContextProtocol.GenerateClientConfig ClaudeCode` (writes `.mcp.json`
   to the UE project root) **or** add to amphitheatre `mcpServers`:
   ```json
   { "unreal": { "type": "http", "url": "http://127.0.0.1:8000/mcp" } }
   ```
   Restart the session; verify with a **no-op list-actors** before any spawn.
6. Run v0 §6 steps 7–9: import layers into the §3 hierarchy with their `actor_prefix`, place via
   `actor_manifest`, apply §5 materials keyed to **read** validation attributes, keep every
   `must_label` flag, spawn the 7 cameras from `camera_manifest.json`, render stills to
   `unreal_export/captures/`. **Do not** move/rescale/rotate geometry, edit elevations, or change any
   seat count / C-value / ADA slope (`mcp_runway.disallowed`).

---

## 5. Guardrails (unchanged)
- **Do not** modify project geometry, Speckle state, or `data/speckle_publish_ledger.json`.
- **Do not** substitute Blender / Twinmotion / Cesium — Unreal MCP is the path.
- **Update the ledger only if** the Unreal MCP scene setup actually completes on gentoo, and even
  then only via the §6-step-10 return path in the v0 doc (proposal GeoJSON → gates → maintainer fold
  → rebuild → ledger). v0/this step make no geometry edit.
- MCP server stays **loopback-only**; never bind to a routable interface.

---

## 6. Decision required before proceeding  — RESOLVED 2026-06-20
Approved the precompiled-binary path; installed to `/mnt/storage`. See §7 for the completed install
and the headless MCP verification. The remaining work (MCP-driven scene *assembly*) is a follow-up.

---

## 7. Install + MCP verification (COMPLETE 2026-06-20)

### What was done (autonomously, no display takeover, ledger untouched)
1. **Engine installed.** UE **5.8.0** precompiled Linux (promoted, CL 55116800) downloaded
   (37 GB zip, size + `unzip -t` integrity verified) and extracted to
   `/mnt/storage/UnrealEngine-5.8/`. No missing shared libs on Gentoo (`ldd` clean); the bundled
   plugins `ModelContextProtocol`, `ToolsetRegistry`, `GeoReferencing`, `EditorToolset` all present.
2. **Project staged.** `/mnt/data/UnrealProjects/PetoskeyCivicBowl/PetoskeyCivicBowl.uproject`
   with `ModelContextProtocol` + `GeoReferencing` + **`EditorToolset`** enabled. Also staged
   (outside the repo): `run_mcp_server.sh` (launcher) and `.mcp.json` (Claude client config).
3. **MCP server brought up headless** via
   `UnrealEditor-Cmd <proj> -nullrhi -unattended -ExecCmds="ModelContextProtocol.StartServer"`.
   Editor fully initialized; server listens **loopback-only** on `127.0.0.1:8000` (override
   `-ModelContextProtocolPort=N`).
4. **MCP protocol verified end-to-end** with a stdlib client + curl: `initialize` (negotiated
   protocol `2025-06-18`, session issued) → `notifications/initialized` (202) → `tools/list`
   (3 meta-tools: `list_toolsets`, `describe_toolset`, `call_tool`) → `tools/call list_toolsets`.
   **An agent can connect and invoke tools.** (Note: tool results stream over **SSE** — clients
   must read `text/event-stream`.)

### Capability surface (with `EditorToolset` enabled → 19 toolsets)
`EditorApp` (asset import, viewport camera, selection, content browser, PIE) · `Logs` ·
`actor.ActorTools` (transforms/labels/hierarchy/components) · `scene.SceneTools` (load level,
place/remove actors, level camera, outliner) · `static_mesh` · `skeletal_mesh` · `asset.AssetTools`
(assets + files on disk) · `data_table` (→ `sightline_table.csv`) · `curve_table` · `data_asset` ·
`material` / `material_instance` / `texture` · `object` (properties/class discovery) · `primitive` ·
`string_table` · `programmatic` (sandboxed Python orchestration). This covers the entire v0
read-only assembly (terrain import, vectors, DataTable, materials, cameras, outliner hierarchy).

### Key findings / caveats
- **`EditorToolset` is NOT enabled by default.** Without it the MCP server exposes only
  `AgentSkillToolset` (1 toolset) — no scene tools. It's enabled in the staged `.uproject`.
- **`-nullrhi` cannot render.** Headless is fine for *assembly* (import/spawn/properties), but the
  v0 §6.9 screenshot **captures need a GPU/RHI** — launch with `run_mcp_server.sh 8000 gui`
  (full editor on `DISPLAY=:0`) for captures.
- **EULA:** the MCP plugin warns that data sent to a connected LLM is Licensed Technology
  (UE EULA §6(e)); ensure the LLM provider does not train on it. Server is loopback + no auth.
- **Session registration:** Claude Code can't hot-register a new MCP server mid-session. To *drive*
  the import, start a **fresh** session from `/mnt/data/UnrealProjects/PetoskeyCivicBowl/` (picks up
  `.mcp.json`) — or add the §4-step-5 entry to the amphitheatre `mcpServers` — then verify with a
  no-op `list_toolsets` before any spawn.

### To use the host (on demand)
```sh
# headless assembly server (no display); MCP at http://127.0.0.1:8000/mcp
/mnt/data/UnrealProjects/PetoskeyCivicBowl/run_mcp_server.sh
# OR full editor (GPU) when you need rendered captures:
/mnt/data/UnrealProjects/PetoskeyCivicBowl/run_mcp_server.sh 8000 gui
# then start Claude Code from the project dir and drive the v0 §6 import runbook.
```
Until that assembly runs and completes, `data/speckle_publish_ledger.json` and all accepted
geometry remain authoritative and untouched.

---

## 8. Read-only scene ASSEMBLED + PERSISTED headlessly via MCP (2026-06-20)

Driven entirely over the MCP HTTP/JSON-RPC interface from the agent session (no GUI, no display
takeover). The saved review scene is **`/Game/Maps/CivicBowl`** in the project
`/mnt/data/UnrealProjects/PetoskeyCivicBowl/` (the project opens it via `Config/DefaultEngine.ini`).

### What's in the scene (verified after a disk reload)
| Outliner folder | Actors | Source |
|---|---|---|
| `Reference/Terrain` | `Terrain_Existing`, `Terrain_Proposed` | `unreal_export/terrain/terrain_*.obj` (existing converted glb→obj via trimesh) |
| `Accepted_ReadOnly/Seating` | `Seating_Rows` (45 treads, faithful, per-row NAVD88 elevations) | generated from `geo/seating_rows.geojson` |
| `Proposal_Editable/Stage` | `Stage_Floor` (6 slabs, **PROVISIONAL / Rule-9-OPEN** tag) | generated from `geo/stage_floor.geojson` |
| `Cameras` | 7 `CineCameraActor` (positioned + `look_at`-oriented; `slot:`/`fov:` tags) | `manifests/camera_manifest.json` |

All from authoritative sources; actors carry `acceptance:*`, `PLANNING-GRADE`, and `must_label`/
`Rule-9-OPEN` tags. Coordinate frame: local-ENU metres ×100 (UE cm), same frame as the terrain.

### Method (reproducible — scripts in the job tmp; copy into the repo if desired)
1. **No native GeoJSON importer** → generate slab OBJs offline from the EPSG:6494 GeoJSON in the
   local-ENU-metre frame (`shapely` + `trimesh` + `mapbox_earcut`), then `static_mesh.import_file`
   (FbxFactory accepts **obj/fbx, NOT glb**). Terrain `.obj`; existing terrain converted glb→obj.
2. Place via `scene.add_to_scene_from_asset` (scale ×100); cameras via `add_to_scene_from_class`
   (`/Script/CinematicCamera.CineCameraActor`) + `actor.look_at`; folders via `set_actor_folder`;
   `actor.set_label`/`add_tag`.

### Load-bearing gotchas discovered (the hard part)
- **World Partition / OFPA template ≠ headless-persistable.** The default temp world is the Open-World
  (WP + One-File-Per-Actor) template. There, `save_assets(level)` writes only the `.umap`;
  newly-spawned actors' external packages are **not** saved and `scene.save_actor` fails
  ("external package does not exist"); a fresh headless session also does **not** stream prior WP
  actors. Net: spawned actors never reach disk. **Fix: use a NON-WP Basic level** —
  `asset.duplicate("/Engine/Maps/Templates/Template_Default", "/Game/Maps/CivicBowl")`, open it,
  populate, `save_assets(level)` → actors are stored **inline in the `.umap`** and survive reload
  (verified: 2/1/1/7 after `load_level`). `Template_Default` = Basic/non-WP; `OpenWorld` = WP.
- **Persisting a transient temp world** via `asset.move(/Temp/Untitled_N → /Game/...)` works only on
  a *pristine* temp world; it fails if `EditorStartupMap` points at a missing map (degraded fallback
  world). Keep `DefaultEngine.ini` pointing at a map that exists.
- **`save_assets(level)` does not save imported mesh assets** — save each imported mesh's asset path
  too, or they're lost on exit (the actors then reference missing meshes).
- `never pkill -f` a UE pattern (it self-matches the killing shell → kills your own shell). Stop by PID.

### Still TODO (documented, not done)
- **ADA route** (39 LineStrings → ribbon extrusion), **materials** (band-status seating colors,
  provisional stage hatch), **sightline DataTable** (needs a `TableRowBase` struct — not creatable
  headless), **BayViewAxis / cut-fill overlay / Labels**, and **rendered captures** (need
  `run_mcp_server.sh 8000 gui`). Camera FOV is tagged, not yet applied to the CineCamera.
- **Handedness:** direct ENU→UE mapping (internally consistent; a global mirror vs true geography —
  refine with a Y-negation if true-north fidelity is needed).

### Acceptance discipline (unchanged)
This is a **viewer scene** only. No accepted geometry, validation script, Speckle state, or
`data/speckle_publish_ledger.json` was modified by the assembly (all work lives under `/mnt/data`
and the job tmp). The repo gates + ledger remain the sole acceptance authority.
