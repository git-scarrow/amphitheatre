# Unreal Handoff Package — Petoskey Pit Civic Bowl

A minimal, regenerable export layer that turns the **authoritative** GIS/design
repo into clean, Unreal-importable assets — terrain, seating, stage, ADA route,
sightline data, and provenance/material/camera manifests.

**Build:** `python scripts/build_unreal_export.py` → writes `unreal_export/`
**Verify:** `python scripts/verify_unreal_export.py` → 30 acceptance gates (must be green)

Everything under `unreal_export/` is generated. Delete it and rebuild at any time;
the build is read-only on the repo and content-deterministic — the only bytes that
vary between rebuilds are the `generated` timestamp and `git_commit` recorded in
`manifests/provenance.json` (so a rebuild leaves that one committed file dirty).

---

## 1. Authoritative-source boundary

The **GIS/design repo is the single source of truth.** The governing geometry is
the Scenario E three-section civic bowl as expressed by the in-situ package and
validated by the Python/QGIS gates. This export reads — and never mutates — these
authoritative files:

| Export asset | Read from (authoritative) |
|---|---|
| `geo/seating_rows.geojson`, `seating_row_splines.geojson` | `vectors_geojson/terrace_treads.geojson` (+ `validation.json` for C/band, `dem/cut_fill_1ft.tif` for cut/fill) |
| `geo/stage_floor.geojson` | `vectors_geojson/bowl_zones.geojson` + `design_open_low/stage_floor.geojson` (bay-view axis) |
| `geo/ada_route.geojson` | `vectors_geojson/ada_route.geojson` (+ `validation.json` `ada[]` cross-check) |
| `tables/sightline_table.csv` | `analysis/tier_emission/Scenario_E_baseline_reemit/validation.json` |
| `terrain/*` | `dem/dem_design_1ft.tif`, `dem/proposed_grade_1ft.tif` |
| warnings, origin, datum | `truth_package/design_state.current.json` |

Every source file's `sha256` (first 12) is recorded in
`manifests/provenance.json`. If a source changes, rerun the build — the export
is downstream of the gates, never a substitute for them.

The brief's filenames `seating_rows.geojson` / `stage_floor.geojson` /
`ada_route.geojson` / `sightline_table.csv` also exist (stale) under
`design_open_low/`, `package/05_seating/`, `stage4/`. Those encode the
**superseded single-fan** design (see `truth_package/data_inventory.md §1`).
This package regenerates those names from the **current** in-situ / tier-emission
sources instead — it does not copy the stale geometry.

---

## 2. Unreal is a viewer, not a source of truth

Unreal (or Twinmotion / Blender / Cesium) is a **presentation surface**. Nothing
rendered there is design truth until it has passed the existing gates. The
package enforces this in three ways:

- **Validation is read, never recomputed.** Sightline `C_mm`, seat counts, ADA
  running slopes, and the planning-grade warnings are copied verbatim from the
  source tables. `verify_unreal_export.py` asserts zero drift (gates C, D, E, G).
- **Provisional / concept tiers stay marked.** The stage deck is **PROVISIONAL**
  (DESIGN_CANON Rule 9 OPEN); the treatment cell and event floor are
  **concept-tier**. These flags ride on every actor, GeoJSON feature, and
  material (`must_label: true`), so a viewer cannot silently promote them.
- **Materials are styling only.** `manifests/material_manifest.json` keys colors
  to a validation attribute *read* from source (`band_status`, `rule9_status`,
  `preferred`, …). No material recomputes or overrides a validated state.

---

## 3. Coordinate contract

One frame for **all 3D geometry** (meshes, heightfields, actor anchors, cameras):

```
local ENU, Z-up, METRES
x = east, y = north, z = NAVD88 ft × 0.3048
origin = EPSG:6494 (19533067.7, 750799.2) INTERNATIONAL feet   ← canon bowl origin
ft → m = 0.3048 (exact; EPSG:6494 is intl ft, NOT US-survey ft)
```

Reverse (exact round-trip, verified to < 0.005 ft):

```
X_epsg6494_ft = x_local_m / 0.3048 + 19533067.7
Y_epsg6494_ft = y_local_m / 0.3048 + 750799.2
navd88_ft     = z_local_m / 0.3048
```

The **GeoJSON exports keep full EPSG:6494 coordinates** (so they validate against
the existing QGIS/Python gates unchanged and round-trip exactly). The **3D
meshes are recentered** to the local metre frame so single-precision Unreal does
not lose the ~19.5 million-foot easting. The **actor manifest carries both
anchors** and is the bridge between them.

> Datum caveat (carried from `design_state`): bay level is quoted IGLD85; the
> Δ = +0.162 ft to NAVD88 is **confirmed** (2026-06-06, NOAA VDatum — `gating_dossier.md`
> gate A-1; the prior +0.40 ft assumption is superseded).

---

## 4. Import steps (Unreal Engine 5)

**A. Terrain — Landscape (recommended for editing) or static mesh (fast).**

- *Heightfield:* `terrain/heightfield_proposed.r16` (and `_existing.r16`) are
  16-bit RAW, 801×801, row-major (N→S rows, W→E cols). Import as a Landscape
  heightmap. Set XY scale and Z scale/offset from the sidecar
  `terrain/heightfield_proposed.heightfield.json`
  (`unreal_landscape.xy_scale_cm_per_px`, `z_scale_note`) so the landscape
  reproduces true NAVD88 ft. `heightfield_*.png` is a 16-bit preview of the same.
- *Mesh:* `terrain/terrain_proposed.glb` / `terrain_existing.glb` import directly
  (Unreal glTF importer). `terrain_proposed.obj` is provided for Blender/round-trip.
  Meshes are **Z-up metres**; in the glTF import set the up-axis to Z (or rotate
  the imported actor +90° about X). Import scale ×100 if your project is in cm.

**B. Design vectors.** Two equivalent paths:

1. *Georeferenced (Datasmith / GeoReferencing plugin):* import the
   `geo/*.geojson` in EPSG:6494 and set the world origin to the canon origin
   above. Best fidelity; keeps you in real coordinates.
2. *Manifest-driven (no GIS plugin):* read `manifests/actor_manifest.json` —
   each actor has `anchor_local_m` (place the actor there) plus `source_file` +
   `source_feature_id` (pull the full polyline/polygon from the matching
   `geo/*.geojson` feature). `actor_manifest.csv` is the spreadsheet form.

**C. Sightline data table.** Import `tables/sightline_table.csv` as a DataTable
(string/float columns) to drive per-row labels, overlays, and validation tints.
Key column: `band` (`east r2`, `bend r1`, …). `sightline_verdict` ∈
{`PASS`,`WARN`,`front_row_no_obstruction`}; `band_status` ∈
{`formal`,`partial`,…}; `fail_reasons` is `;`-joined.

**D. Materials & cameras.** Build Unreal materials from
`manifests/material_manifest.json` (id → color/label/`keyed_to`). Place cameras
(CineCamera) from `manifests/camera_manifest.json` (`position_local_m`,
`look_azimuth_deg` clockwise-from-north, `fov_deg`).

---

## 5. Recommended actor naming

Use the `actor_name` already in `manifests/actor_manifest.json` (stable,
collision-free, traceable). Convention:

```
Row_<section>_<rr>        Row_bend_08          seating tread (spline + mesh)
Stage_<zone>              Stage_stage_core     stage deck (PROVISIONAL)
ForecourtEventFloor / TreatmentCellLandscape   concept-tier surfaces
ADA_<route>               ADA_route_arrival_to_cross_aisle
ADANode_<node>            ADANode_landing_3    ADA landing / node
BayViewAxis / FocalPointStageFront             reference axis (330°)
Cam_<viewpoint>           Cam_stage_looking_back_to_audience
Terrain_Proposed / Terrain_Existing            landscape or mesh
```

Group actors under folders `Seating/`, `Stage/`, `ADA/`, `Terrain/`, `Cameras/`,
`Reference/`. Keep the `source_feature_id` on a tag or string property so any
actor can be traced back to its authoritative feature.

---

## 6. MCP-safe operations

If you drive Unreal through an MCP/automation bridge, these are **safe** (viewer
state only — they never touch design truth):

- spawn/move **cameras**; render stills/flythroughs; toggle bookmarks
- assign/recolor **materials** from the material manifest; toggle layer visibility
- spawn **labels / text / decals** from `sightline_table.csv` and feature props
- toggle the **cut/fill overlay**, validation tints, provisional hatching
- import the generated terrain/heightfield/GeoJSON/DataTable as above
- measure, annotate, place reference splines that are not exported back as design

These are safe because they do not alter the position, elevation, or extent of
any governing feature, and they cannot change a validated number.

---

## 7. Prohibited mutations

Do **not** treat any of the following as design truth from inside Unreal:

- moving, rescaling, rotating, or re-lofting **seating rows, stage, treatment
  cell, ADA route, or terrain** and calling the result the design
- editing **elevations** (tread `proposed_elev_navd88_ft`, stage deck, landings)
- changing **seat counts**, **C-values**, ADA **slopes/landings**, or earthwork
- recoloring a **provisional/concept** element to read as accepted, or dropping
  the Rule-9 / planning-grade labels
- exporting Unreal geometry **directly** into `vectors_geojson/`, `dem/`,
  `truth_package/`, or the `analysis/` validation outputs
- writing back in Unreal units (cm, Y-up, local frame) without reversing the
  coordinate contract to EPSG:6494 intl ft / NAVD88

Any of these must instead go through §8.

---

## 8. Round-trip proposal workflow (Unreal edit → design truth)

A geometry idea explored in Unreal becomes truth **only** after it passes the
existing gates. The loop:

1. **Edit in Unreal** (move a row, test a stage footprint, reroute ADA).
2. **Export a proposal GeoJSON**, not a copy of the export. Reverse the
   coordinate contract (§3) back to **EPSG:6494 intl ft / NAVD88 ft**, keep the
   `feature_id` of every changed feature, and write a single-purpose file, e.g.
   `requests/proposal_<topic>_<date>.geojson` with a short note of what changed
   and why.
3. **Run the gates** that own the affected geometry — e.g.:
   - `python scripts/audit_in_situ_package.py` (in-situ geometry, CRS, families,
     viewpoints, ADA topology/slope/smoothness, rasters)
   - the relevant builder/validator (`scripts/build_in_situ_geometry.py`,
     `scripts/design_ada_routes.py` + `analysis/.../validation.json`,
     `scripts/build_truth_package.py`)
   - QGIS review against `qgis/in_situ_package.qgs`
4. **Only if the gates pass** does a maintainer fold the proposal into the
   authoritative sources. Then **rebuild this package** (`build_unreal_export.py`)
   so Unreal re-receives the now-validated geometry.

Unreal never writes design truth directly. It proposes; the gates decide.

---

## Package contents

```
unreal_export/
  geo/        seating_rows.geojson · seating_row_splines.geojson
              stage_floor.geojson · ada_route.geojson            (EPSG:6494)
  tables/     sightline_table.csv                                (from validation.json)
  terrain/    terrain_{existing,proposed}.glb · terrain_proposed.obj
              heightfield_{existing,proposed}.{r16,png,heightfield.json}
  manifests/  actor_manifest.{json,csv} · material_manifest.json
              camera_manifest.json · provenance.json
```

The `geo/`, `tables/`, and `manifests/` files are lightweight and review-friendly
(committed). The `terrain/` binaries (~31 MB, GLB/OBJ/RAW/PNG) are regenerable
and git-ignored — rebuild with `build_unreal_export.py`.

## Planning-grade warnings (verbatim from `truth_package/design_state.current.json`)

- PLANNING-GRADE ONLY — derived from 2015 USGS LiDAR + supplement; not a stamped
  engineering design and not a field survey.
- Stage deck is PROVISIONAL: DESIGN_CANON.md Rule 9 is OPEN (inherited az-150
  stage; +25.6° audience-axis mismatch on record).
- Coordinates are EPSG:6494 INTERNATIONAL feet — misreading as US survey feet
  shifts absolute easting ~39 ft (docs/datum_note.md).
- Component CY totals are validated proxies that understate mobilization-level
  earthwork (analysis/tier_emission/TIER_EMISSION_VALIDATION.md).
- Seating scope Decision 1 is pending; this package shows the Scenario E baseline
  (option A).
- Treatment-cell shaping and orchestra/event floor are concept-tier
  (illustrative), not geometry-backed.
