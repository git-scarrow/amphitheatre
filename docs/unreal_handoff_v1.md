# Unreal Handoff v1 — MCP runway for the Petoskey Pit Civic Bowl

**Status:** v1, additive. Creates and changes **no** geometry, validation output, or
ledger entry. It documents and indexes the existing validated export so an Unreal
scene — optionally driven by an MCP bridge — can be a disciplined *review and
proposal* surface, never an acceptance authority.

This doc is the **governance contract**. Its companions:

| Companion | Role |
|---|---|
| `README_UNREAL.md` | import **mechanics** (heightfield/mesh/GeoJSON/DataTable, coordinate contract, actor naming) |
| `data/unreal_handoff_manifest.json` | machine **index**: per-layer source, sha256, role, MCP boundary, acceptance pointer |
| `scripts/build_unreal_handoff_manifest.py` | deterministic generator + `--check` drift gate for the manifest |
| `unreal_export/manifests/provenance.json` | the export's own CRS / sources / warnings (this doc reads from it, never restates as new truth) |
| `docs/speckle_review_runbook.md`, `docs/speckle_publish_ledger.md` | Speckle review + acceptance-ledger discipline |
| `docs/unreal_mcp_readonly_scene_v0.md` | v0 read-only scene **assembly runbook + host status** (what to import, hierarchy, cameras, captures) |

The runway, end to end:

```
repo truth  ->  Speckle review  ->  Unreal scene import  ->  MCP visual/proposal edits
     ^                                                                |
     |                                                                v
ledgered acceptance  <-  repo validation gates  <-  proposal GeoJSON (EPSG:6494)
```

Unreal proposes; **the gates decide; the ledger records.**

---

## 1. CRS and units

One frame governs **all 3D scene geometry** (terrain meshes, heightfields, actor
anchors, cameras); the GeoJSON layers stay in full state-plane coordinates so they
validate against the existing QGIS/Python gates unchanged.

```
GeoJSON layers (geo/*.geojson):  EPSG:6494 NAD83(2011) / Michigan Central, INTERNATIONAL feet
                                 vertical NAVD88 (Geoid12A), international feet
3D scene frame:                  local ENU, Z-up, METRES
                                 x = east, y = north, z = NAVD88 ft x 0.3048
local origin:                    EPSG:6494 (19533067.7, 750799.2) intl ft   (canon bowl origin)
ft -> m:                         0.3048  (exact; EPSG:6494 is intl ft, NOT US-survey ft)
```

Reverse transform (exact round-trip, gate-verified < 0.005 ft):

```
X_epsg6494_ft = x_local_m / 0.3048 + 19533067.7
Y_epsg6494_ft = y_local_m / 0.3048 + 750799.2
navd88_ft     = z_local_m / 0.3048
```

> **Datum caveats (load-bearing).** EPSG:6494 is **international** feet — reading it
> as US-survey feet shifts the easting ~39 ft (`docs/datum_note.md`). Bay level is
> quoted IGLD85; the working Δ = +0.40 ft to NAVD88 is a **labelled assumption,
> unconfirmed**. The whole surface is **planning-grade** (2015 USGS LiDAR +
> supplement), not a survey. These ride verbatim in `provenance.json` → `acceptance.warnings`.

---

## 2. Layer names and source files

Layer keys, Unreal folders/prefixes, and per-file sha256 live in
`data/unreal_handoff_manifest.json` → `layers[]`. Summary:

| Layer | Package file (committed unless noted) | Authoritative source | Role |
|---|---|---|---|
| `seating_rows` | `unreal_export/geo/seating_rows.geojson` | `vectors_geojson/terrace_treads.geojson` (+ `validation.json`) | accepted · read-only |
| `seating_row_splines` | `unreal_export/geo/seating_row_splines.geojson` | `vectors_geojson/terrace_treads.geojson` | accepted · read-only |
| `stage_floor` | `unreal_export/geo/stage_floor.geojson` | `vectors_geojson/bowl_zones.geojson` + `design_open_low/stage_floor.geojson` | **proposal · provisional (Rule 9 OPEN)** |
| `ada_route` | `unreal_export/geo/ada_route.geojson` | `vectors_geojson/ada_route.geojson` (+ `validation.json` `ada[]`) | **proposal · concept (pending civil/code)** |
| `sightline_table` | `unreal_export/tables/sightline_table.csv` | `analysis/tier_emission/Scenario_E_baseline_reemit/validation.json` | accepted · read-only |
| `terrain_existing` | `…/heightfield_existing.heightfield.json` (+ gitignored `.glb/.r16/.png`) | `dem/dem_design_1ft.tif` | reference · read-only |
| `terrain_proposed` | `…/heightfield_proposed.heightfield.json` (+ gitignored `.glb/.obj/.r16/.png`) | `dem/proposed_grade_1ft.tif` | reference · read-only |
| `actor_manifest` | `unreal_export/manifests/actor_manifest.{json,csv}` | export provenance | index (anchors) |
| `material_manifest` | `unreal_export/manifests/material_manifest.json` | export provenance | **styling · visual-only** |
| `camera_manifest` | `unreal_export/manifests/camera_manifest.json` | `vectors_geojson/in_situ_viewpoints.geojson` | **viewpoints · visual-only** |
| `provenance` | `unreal_export/manifests/provenance.json` | `truth_package/design_state.current.json` | authority |

The terrain **binaries** (`*.glb/*.obj/*.r16/*.png`, ~31 MB) are git-ignored and
**regenerable** — rebuild with `python scripts/build_unreal_export.py`. Their sidecar
`*.heightfield.json` (scale/offset to reproduce true NAVD88 ft) **is** committed and hashed.

All upstream source hashes (sha256_12) are mirrored from `provenance.json` into the
manifest's `sources` block. If any source changes, rerun the export build, then
`build_unreal_handoff_manifest.py` — the export is **downstream of the gates, never a
substitute for them**.

---

## 3. Accepted / read-only geometry

These are the **governing, validated** layers. In Unreal they are reference: view,
camera, light, label, recolour — but their position, extent, and elevation are fixed.

- **Seating** (`seating_rows`, `seating_row_splines`) — the Scenario E three-section
  civic bowl. Seat counts and sightline `C_mm` are **read** from `validation.json`,
  never recomputed; `verify_unreal_export.py` gates C/D assert zero drift.
- **Sightline table** — a validation readout, not geometry; values copied verbatim.
- **Terrain** (`terrain_existing`, `terrain_proposed`) — reference surfaces from the
  DEMs; the proposed grade is the accepted earthwork context.

The Speckle **accepted bundle** = `{Seating, ADA, Reference}` (ADA carried with its
concept status; see §4). It is the surface ratified by the publish ledger.

## 4. Proposed / editable geometry

These layers ship **labelled as not-yet-accepted**. They are the legitimate subjects
of an Unreal exploration — but only through the round-trip in §7.

- **`stage_floor` — PROVISIONAL.** `DESIGN_CANON.md` Rule 9 is **OPEN** (inherited
  az-150 stage; +25.6° audience-axis mismatch on record). The Stage collection is
  **excluded from the accepted Speckle bundle** and ships separately as a proposal.
  Every Stage feature/actor/material carries `provisional` / `must_label: true`;
  `verify_unreal_export.py` gate F refuses if any Rule-9-open feature is unflagged.
- **`ada_route` — CONCEPT pending civil/code detailing.** ADA rides in the
  accepted-*context* bundle but with `acceptance: proposal`; route status strings are
  carried **verbatim** and gate E refuses any string strengthened past
  `concept`/`pending`.
- **Treatment cell / event floor** — concept-tier (illustrative), not geometry-backed.

"Editable" here means *a starting point for a proposal*, not *editable as truth*.

---

## 5. Unreal + MCP role

Unreal (or Twinmotion / Blender / Cesium), optionally driven through an MCP
automation bridge, is a **presentation and proposal surface**. Nothing rendered or
edited there is design truth until it has passed the repo gates and been ledgered.
Three structural guarantees (already enforced by the export build + `verify_unreal_export.py`):

1. **Validation is read, never recomputed** — `C_mm`, seat counts, ADA status, and the
   planning-grade warnings are copied from source; drift = gate failure.
2. **Provisional / concept tiers stay marked** — flags ride on every actor, feature,
   and material (`must_label: true`); a viewer cannot silently promote them.
3. **Materials are styling only** — colours key to a *read* validation attribute; no
   material overrides a validated state.

### Allowed MCP operations (viewer state only — never touch design truth)

- spawn / move **cameras**; render stills and flythroughs; set bookmarks
- assign or recolour **materials** from `material_manifest`; toggle layer visibility
- spawn **labels / text / decals** from `sightline_table.csv` and feature properties
- toggle the **cut/fill overlay**, validation tints, provisional hatching
- **import** the generated terrain / heightfield / GeoJSON / DataTable
- **measure, annotate**, place reference splines that are *not* exported back as design

### Disallowed MCP operations (these are not design truth from inside Unreal)

- move / rescale / rotate / re-loft **seating, stage, treatment cell, ADA, or terrain**
  and call the result the design
- edit **elevations** (tread `proposed_elev_navd88_ft`, stage deck, ADA landings)
- change **seat counts, C-values, ADA slopes/landings, or earthwork quantities**
- recolour a **provisional/concept** element to read as accepted, or drop the
  Rule-9 / planning-grade labels
- export Unreal geometry **directly** into `vectors_geojson/`, `dem/`, `truth_package/`,
  or `analysis/` validation outputs
- write back in **Unreal units** (cm, Y-up, local frame) without reversing the
  coordinate contract (§1) to EPSG:6494 intl ft / NAVD88

The same `allowed` / `disallowed` lists are machine-readable in the manifest's
`mcp_runway` block, so an MCP bridge can enforce them as data.

---

## 6. How Speckle stays review/exchange — not acceptance authority

Speckle is the **review and exchange** hop between the repo and Unreal. It is **never**
the acceptance authority:

- **Speckle version history is not acceptance history.** A Speckle version counts as
  part of the project record only while its `export_payload_hash` still matches a
  matching entry in `data/speckle_publish_ledger.json`. The repo gates remain the sole
  acceptance authority; the ledger is the repo's record of which review versions mirror
  a gated, committed state.
- Payloads are generated by `scripts/export_speckle_payload.py` (a pure derivation of
  `unreal_export/`), published only through `scripts/publish_speckle.py`, which **dry-runs
  first and refuses unless `verify_unreal_export.py` passes**. Drift is caught by
  `scripts/speckle_compare.py`; an un-ratified accepted version is FLAGged by
  `scripts/speckle_webhook.py`.
- The current ratified accepted version (`a6e9dab770`, source commit `84aa207`) is
  recorded in the ledger; its pointer is echoed read-only into the manifest's
  `acceptance.ledger_entry`. **This handoff does not publish to Speckle and does not
  mutate the live server.**

---

## 7. How an Unreal edit returns to repo validation

A geometry idea explored in Unreal becomes truth **only** after it passes the gates:

1. **Edit in Unreal** — move a row, test a stage footprint, reroute an ADA leg.
2. **Export a proposal GeoJSON** (not a copy of the export). Reverse the coordinate
   contract (§1) back to **EPSG:6494 intl ft / NAVD88 ft**, keep the `feature_id` of
   every changed feature, and write a single-purpose file, e.g.
   `requests/proposal_<topic>_<date>.geojson`, with a short note of what changed and why.
3. **Run the owning gate(s)** — e.g. `scripts/audit_in_situ_package.py` (in-situ geometry,
   CRS, families, viewpoints, ADA topology/slope/smoothness, rasters); the relevant
   builder/validator (`build_in_situ_geometry.py`, `design_ada_routes.py` +
   `analysis/.../validation.json`, `build_truth_package.py`); QGIS review against
   `qgis/in_situ_package.qgs`.
4. **Only on PASS** does a maintainer fold the proposal into the authoritative sources.
   Then **rebuild** the export (`build_unreal_export.py`), regenerate this manifest
   (`build_unreal_handoff_manifest.py`), and — if it is to be reviewed in Speckle —
   re-publish through the guarded path and **add a ledger entry**.

Unreal never writes design truth directly. It proposes; the gates decide; the ledger records.

---

## 8. Verifying the handoff package

```
python scripts/verify_unreal_export.py                 # 30 export acceptance gates (read-only)
python scripts/build_unreal_handoff_manifest.py --check # manifest matches the tree (hashes/roles/CRS/acceptance)
```

The manifest's `package_fingerprint_sha256` is a single hash over all committed package
files; `--check` recomputes it and the per-layer hashes and fails on any drift.
