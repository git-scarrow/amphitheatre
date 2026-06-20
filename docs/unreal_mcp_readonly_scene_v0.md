# Unreal MCP Read-Only Scene Assembly v0 — Petoskey Pit Civic Bowl

**Status:** `v0 · BLOCKED-ON-HOST · package validated & import-ready`
**Date:** 2026-06-20 · **Repo HEAD:** `5d47190` (`main`) · **Authoritative commit:** `5d47190`
**Change to geometry / validation / ledger:** **none.** This file is documentation only.

This is the v0 record of attempting the *read-only review scene* described in the
[Unreal handoff v1 governance contract](unreal_handoff_v1.md). It is deliberately honest:
the scene **was not assembled inside Unreal on this host** because neither Unreal Engine
nor an Unreal MCP bridge is present here (see §2). What this document *does* deliver is the
complete, executable assembly runbook plus a proof that no accepted geometry changed.

> Unreal proposes; **the gates decide; the ledger records.** Nothing in this v0 step is design
> truth. The repo (Python/QGIS gates + `data/speckle_publish_ledger.json`) remains the sole
> acceptance authority; Unreal and Speckle are never acceptance authority.

---

## 1. Summary (read this first)

| Question | Answer |
|---|---|
| **Unreal project path** | **None on this host.** No `.uproject`, no `UnrealEditor` binary (PATH, `~`, `/opt`, flatpak, Steam all checked). Target project name when created: `PetoskeyCivicBowl.uproject` (UE 5.8). |
| **MCP connection status** | **Not connected.** `~/.claude.json` top-level `mcpServers: []` and amphitheatre-project `mcpServers: []`; no `unreal` MCP server registered; no Unreal MCP tool in the session inventory. |
| **Imported layers** | **0 imported into Unreal** (no engine). 12 committed package files + 9 regenerable terrain binaries are staged, hashed, and **import-ready** under `unreal_export/` (see §4). |
| **Screenshots / outputs** | **None rendered** (no engine/viewport). Capture plan in §6 step 9; output dir reserved: `unreal_export/captures/` (not yet created). |
| **Files changed** | `docs/unreal_mcp_readonly_scene_v0.md` (this file) only. |
| **Tests run** | `verify_unreal_export.py` → **30 pass · 0 fail**; `build_unreal_handoff_manifest.py --check` → **PASS**. Both before and after authoring this doc (§7). |
| **Ready for first proposal-edit experiment?** | **No — not from this host.** Prereqs in §8 must be met first. The repo-side return path (§6 step 10) is already specified and gated. |

---

## 2. Host capability probe (observed facts, 2026-06-20)

This is what made the difference between "assemble the scene" and "document the runway."

```
Unreal Engine 5.8 editor ........ ABSENT
  - which UnrealEditor / UnrealEditor-Cmd / UE5Editor / UE4Editor : not on PATH
  - ~/UnrealEngine*, ~/Epic*, /opt/UnrealEngine*, /opt/Epic*       : none
  - ~/.var/app (flatpak Epic/Unreal)                               : none
  - ~/.steam/.../steamapps/common/*unreal*                         : none
  - **/*.uproject (under ~)                                        : none
  - running 'unreal' process                                       : none
Unreal MCP bridge ............... ABSENT
  - ~/.claude.json mcpServers (top-level)                          : []
  - ~/.claude.json projects[amphitheatre].mcpServers              : []
  - any MCP server name containing 'unreal'                        : none
  - Unreal MCP tool surfaced to this session                       : none
Host (per ~/.ai/notes/identity.md) ... gentoo workstation; SSH target sam@nix is a
  headless NixOS service VM (no GPU/editor); Speckle review server is the Proxmox VM 131.
  None of these is an Unreal editor host.
Python ........................... .venv (3.13.14) present; numpy 2.4.2; gate scripts run clean.
```

**Conclusion:** Goal steps 3–11 (open the UE project, enable the MCP plugin, connect, import
layers, build the hierarchy, assign materials/labels, set camera bookmarks, capture
screenshots) are **not executable on this host**. They are fully specified below so an
operator on a UE-5.8 + MCP host can run them deterministically. Steps 1, 2, 12, 13, 14, 15
(git confirm, doc reading, this document, validation proof, commit, no-push) were completed
here.

---

## 3. Intended scene hierarchy (target World Outliner layout)

The five requested collections, mapped to the manifest's layers, roles, and Speckle bundle
membership. **Editable** = legitimate proposal subject *only via the §6-step-10 return path* —
never editable as truth inside Unreal.

```
World Outliner
├── Accepted_ReadOnly          (governing, validated — view/camera/label/recolour only)
│   ├── Seating/               seating_rows  (Row_*)   · seating_row_splines (Row_*)
│   └── (DataTable) Sightlines sightline_table.csv  → DT_Sightlines  (C_mm, band, verdict)
├── Proposal_Editable          (labelled NOT-yet-accepted; proposal subjects)
│   ├── Stage/                 stage_floor (Stage_*) — PROVISIONAL, DESIGN_CANON Rule 9 OPEN
│   └── ADA/                   ada_route (ADA_/ADANode_) — CONCEPT, pending civil/code
├── Reference                  (context surfaces — read-only)
│   ├── Terrain/               Terrain_Existing · Terrain_Proposed (Landscape r16 or mesh)
│   ├── CutFill_Overlay        (toggle; from dem/cut_fill_1ft.tif)
│   └── BayViewAxis            (330.0° reference axis)
├── Cameras                    (Cam_* CineCameras — spawn/move freely, visual-only)
└── Labels                     (text/decals from sightline_table.csv + feature properties)
```

> **ADA dual status (do not flatten):** ADA rides in the Speckle *accepted-context* bundle
> `{Seating, ADA, Reference}` but its `acceptance` is `proposal` and its status strings are
> carried **verbatim** — never strengthened past `concept`/`pending`. For *Unreal editing
> discipline* it lives under `Proposal_Editable`. For *Speckle bundling* it stays in the
> accepted-context bundle. Both are true; the manifest is the arbiter.

---

## 4. Layers to import (from the validated package)

Source of truth: `data/unreal_handoff_manifest.json` → `layers[]` (per-file sha256 there).
Import mechanics: `README_UNREAL.md`. None of these is recomputed in Unreal; validation
attributes (`C_mm`, seat counts, ADA status) are **read**, drift = gate failure.

| Layer | Package file | Unreal folder / prefix | Import as | Role |
|---|---|---|---|---|
| `seating_rows` | `unreal_export/geo/seating_rows.geojson` | Seating / `Row_` | GeoJSON (georef) | accepted · read-only |
| `seating_row_splines` | `unreal_export/geo/seating_row_splines.geojson` | Seating / `Row_` | GeoJSON spline | accepted · read-only |
| `stage_floor` | `unreal_export/geo/stage_floor.geojson` | Stage / `Stage_` | GeoJSON (render-only Z) | **proposal · PROVISIONAL** |
| `ada_route` | `unreal_export/geo/ada_route.geojson` | ADA / `ADA_`,`ADANode_` | GeoJSON | **proposal · CONCEPT** |
| `sightline_table` | `unreal_export/tables/sightline_table.csv` | — | DataTable | accepted · read-only |
| `terrain_existing` | `…/heightfield_existing.heightfield.json` (+ gitignored `.r16/.png/.glb`) | Terrain / `Terrain_Existing` | Landscape (r16) or mesh (glb) | reference · read-only |
| `terrain_proposed` | `…/heightfield_proposed.heightfield.json` (+ gitignored `.r16/.png/.glb/.obj`) | Terrain / `Terrain_Proposed` | Landscape (r16) or mesh | reference · read-only |
| `actor_manifest` | `unreal_export/manifests/actor_manifest.{json,csv}` | — | placement table | index (91 actor anchors) |
| `material_manifest` | `unreal_export/manifests/material_manifest.json` | — | material set | styling · visual-only |
| `camera_manifest` | `unreal_export/manifests/camera_manifest.json` | Cameras / `Cam_` | CineCamera placements | viewpoints · visual-only |
| `provenance` | `unreal_export/manifests/provenance.json` | — | metadata | authority |

**Coordinate contract (load-bearing):** GeoJSON layers stay in **EPSG:6494 international feet
/ NAVD88** (so they validate against the existing gates unchanged). All 3D scene geometry uses
**local ENU, Z-up, metres**, origin `(19533067.7, 750799.2)` intl ft, `ft→m = 0.3048` exact.
Reverse transform and datum caveats: `unreal_handoff_v1.md` §1 and `provenance.json`.
Terrain binaries are gitignored/regenerable: `python scripts/build_unreal_export.py`.

---

## 5. Materials & labels (presentation only)

All 17 materials are defined in `unreal_export/manifests/material_manifest.json`, each **keyed
to a validation attribute that is read, never recomputed**. Provisional/concept tiers carry
`must_label: true` and must stay visually marked — gate F refuses otherwise.

- Seating bands: `row_formal` `#2e7d32` (C≥90 mm) · `row_partial` `#f9a825` · `row_warn`
  `#ef6c00` (C<90 mm) · `row_unknown` `#9e9e9e`.
- Stage: `stage` `#37474f`; **`stage_provisional` `#c62828` diagonal hatch, `must_label:true`**
  (Rule 9 OPEN).
- Concept tiers: `event_floor_concept`, `treatment_cell_concept` (illustrative, not
  geometry-backed).
- ADA: `ada_preferred` `#1565c0` · `ada_alternative` `#7e57c2` · `ada_service` · `ada_landing`.
- Reference: `terrain_existing`/`terrain_proposed`, `bay_view_axis` `#01579b`,
  `cutfill_diverging` ramp (blue=cut / white=balanced / red=fill).

**Labels** are spawned from `sightline_table.csv` (per-row `C_mm`, band, verdict) and from
feature properties; the south r18 WARN row (C below the 90 mm bar) must read as WARN, not be
silently promoted.

---

## 6. Exact reproduction steps (operator runbook)

Run on a host **with Unreal Engine 5.8 and a GPU/display**. Steps 1–2 here were already done.

1. **Confirm repo state.** `git -C <repo> rev-parse HEAD` → `5d47190…`; `git status` clean
   except known untracked (`.claude/`, `scripts/serve_viewer.*`, `README_web_viewer.md`).
2. **Read the contract.** `docs/unreal_handoff_v1.md` + `data/unreal_handoff_manifest.json`
   (especially `mcp_runway.allowed` / `mcp_runway.disallowed`).
3. **Regenerate terrain binaries** (gitignored): `python scripts/build_unreal_export.py`, then
   `python scripts/verify_unreal_export.py` (expect 30 pass) and
   `python scripts/build_unreal_handoff_manifest.py --check` (expect PASS).
4. **Create the UE project.** New UE 5.8 project `PetoskeyCivicBowl` (Blank, no starter
   content). Set **World Settings → World units = centimeters** (UE default); the import layer
   converts the local-ENU-metre scene frame (×100) — **never** treat GeoJSON feet as cm.
5. **Enable the Unreal MCP plugin (local editor only).** Install the official Unreal MCP plugin
   into `PetoskeyCivicBowl/Plugins/`, enable it in *Edit → Plugins*, restart the editor. It
   exposes a local MCP server (loopback only — do not bind to a routable interface).
6. **Register & connect the MCP server in Claude Code.** Add an `mcpServers` entry (the host's
   `~/.claude.json` or project `.mcp.json`) pointing at the plugin's local endpoint; restart
   the session so the Unreal MCP tools surface. Verify the connection with a no-op (e.g. list
   actors) before any spawn.
7. **Import the layers (MCP-driven, allowed ops only).** For each row in §4: import the
   GeoJSON/heightfield/DataTable into its §3 folder with its `actor_prefix`; place via
   `actor_manifest` anchors (local-metre + EPSG:6494). Apply the §5 material keyed to each
   feature's **read** validation attribute. Confirm the §3 hierarchy in the World Outliner.
   Keep all `must_label` flags. **Do not** move/rescale/rotate/re-loft any geometry, edit any
   elevation, or change any seat count / C-value / ADA slope (manifest `mcp_runway.disallowed`).
8. **Camera bookmarks (5 requested → existing CineCameras).** All are pre-computed in
   `camera_manifest.json` (frame: local ENU metres; azimuth clockwise from north; bay axis
   330.0°). Spawn them under `Cameras/` and bind editor bookmarks:

   | Requested bookmark | Camera (`Cam_*`) | Slot | look_az° / fov° | note |
   |---|---|---|---|---|
   | human-scale floor view | `Cam_row1_bend_r1` | row1 | 330.0 / 50 | **derived** (tread centroid + 3.94 ft seated eye) |
   | stage looking to seating | `Cam_stage_looking_back_to_audience` | stage | 126.9 / 60 | performer's view, three families rise ~15 ft |
   | seating looking to bay/stage | `Cam_mid_row_audience_to_bay` | row9 | 327.4 / 60 | bay + sky backdrop, treatment cell foreground |
   | overhead civic-bowl view | `Cam_outside_bowl_from_park_edge` | rim | 139.7 / 60 | bowl reads as landscape from NE park edge |
   | ADA route review view | `Cam_ada_arrival_to_cross_aisle` | ada_route | 236.0 / 60 | rows-9/10 cross-aisle, concept route |

   (Two more authoritative cameras ship in the manifest: `Cam_upper_rim_down_to_stage`,
   `Cam_event_floor_to_treatment_cell` — spawn them too for completeness.) For a true overhead
   plan, optionally add a top-down ortho camera over the bowl centroid; mark it `derived`.
9. **Capture.** Render a still per bookmark to `unreal_export/captures/` (create the dir). These
   are review artifacts, **not** committed as design truth. Note any are gitignored if heavy.
10. **(Return path — NOT this step.)** A geometry idea explored later becomes truth only via:
    edit in Unreal → export a **proposal GeoJSON in EPSG:6494 intl ft / NAVD88** (keep every
    `feature_id`) under `requests/proposal_<topic>_<date>.geojson` → run the owning gate(s)
    (`audit_in_situ_package.py`, the relevant builder/validator, QGIS) → only on PASS does a
    maintainer fold it in, rebuild the export + manifest, and (if reviewed in Speckle)
    re-publish through the guarded path **and add a ledger entry**. See `unreal_handoff_v1.md`
    §7. **v0 makes no such edit.**

---

## 7. What MCP controlled · what stayed read-only · what failed/was manual

- **What MCP controlled:** **nothing.** No Unreal MCP bridge on this host; zero MCP scene
  operations executed.
- **What remains read-only:** **everything.** No scene was mutated; all accepted geometry
  (`seating_rows`, `seating_row_splines`, `sightline_table`, terrain) is untouched, and the
  proposal layers (`stage_floor` PROVISIONAL, `ada_route` CONCEPT) keep their labels.
- **What failed (environmental, not error):** the full UE-5.8 + MCP path — open project (no
  project), enable plugin (no engine), connect MCP (no server), import, hierarchy, materials,
  cameras, screenshots. Cause: tooling absent on host (§2), not a defect in the package.
- **What was done manually / deterministically here:** git state confirmed; contract + manifest
  read; both validation gates run; this document authored; commit (doc-only, no push).

---

## 8. Proof that no accepted geometry changed

Run **before and after** authoring this doc — identical, because nothing geometry-touching
occurred:

```
$ .venv/bin/python scripts/build_unreal_handoff_manifest.py --check
PASS  data/unreal_handoff_manifest.json matches the tree (layers, hashes, CRS, acceptance, MCP boundary)

$ .venv/bin/python scripts/verify_unreal_export.py
… 30 pass · 0 fail
  (C seat sum export=1283 == source=1283; D 0 sightline drift; E ADA status verbatim;
   F Rule-9 stage flagged provisional; H local→EPSG:6494 round-trip worst 0.0049 ft)
```

`package_fingerprint_sha256` unchanged:
`4280f54f5cef25769005ef969ff6355da1993d95ff6988265d2eb04724fa0bea`. Ledgered accepted version
`a6e9dab770` (source commit `84aa207`) untouched; `data/speckle_publish_ledger.json` not
edited; live Speckle server not contacted.

---

## 9. Readiness for the first proposal-edit experiment

**Not ready from this host.** Prerequisites, in order:

1. A host with **Unreal Engine 5.8** + GPU/display.
2. The **official Unreal MCP plugin** installed, enabled, bound to loopback.
3. The plugin's MCP server **registered in `mcpServers`** and connected in the session.
4. Steps §6.3–§6.9 completed → a legible read-only review scene + camera bookmarks + captures.
5. Only then attempt a proposal edit, returning **exclusively** through §6 step 10
   (proposal GeoJSON in EPSG:6494 → gates → maintainer fold → rebuild → ledger).

Until then, the repo gates and ledger are unaffected and remain authoritative. This v0 step is
purely additive documentation and changes no design truth.
