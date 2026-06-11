# Petoskey Pit Amphitheatre — Web Viewer & Truth Package

A static, Google-Earth-style 3D viewer for the **Scenario E three-section civic
bowl** (east / bend / south), paired with a machine-readable *truth package*
that records exactly what is design, what is evaluation, what is unknown, and
where every number came from. This is **presentation, audit packaging, and
export scaffolding only** — it does not redesign anything. All geometry is read
from the repo's accepted source files; nothing here moves the stage, rows, ADA
routes, or treatment cell.

> **PLANNING-GRADE.** Terrain is 2015 USGS LiDAR + eastern supplement, not
> survey. The stage is **PROVISIONAL** (Design Canon Rule 9 open — no adoption
> path declared). Nothing in this package is construction documentation.

---

## 1. Open the viewer

```
web_viewer/index.html        ← open this file in any modern browser
```

No server, no build step, no network access required. Everything is local and
static:

| File | Role |
|---|---|
| `web_viewer/index.html` | the entire app (HTML/CSS/JS, one file) |
| `web_viewer/data/site_data.js` | generated data payload (~1.6 MB) — terrain grids + all design layers + audit results |
| `web_viewer/vendor/three.min.js`, `vendor/OrbitControls.js` | vendored Three.js r147 (UMD), the only dependency |

**Controls:** drag = orbit · right-drag = pan · wheel = zoom · keys **1–7** fly
to presets · **0** resets. Click any seating tread to see its per-row audit
record (elevation, seats kept, sightline C in mm, Band-A status).

**Camera presets** (buttons or keys 1–7): Site overview · Stage → audience ·
Row 1 → stage · ADA cross-aisle · Back row (south r18) · Rim overlook ·
Bay-view axis. Four come from the canonical `in_situ_viewpoints.geojson`; the
two row-eye presets are computed at tread centroid + 4 ft eye height.

**No WebGL?** The 3D pane degrades gracefully: a visible notice replaces the
scene and the left audit panel — which reads the same truth package — remains
fully functional. Tested in WebGL-less headless Firefox.

## 2. What you are looking at — truth tiers

Every layer in the panel is tagged with its tier. The viewer never blends them
silently:

**Source-of-truth (geometry-backed, validated):**
- 45 seating treads (rows 1–18 × 3 sections, minus rows 5/9/10) at design
  elevations, colored by Band-A audit status (pass / warn / fail)
- Cross-aisle (rows 9/10 reclassification), ADA routes A & B + 5 landings,
  drainage swales, terrace edges
- Existing + proposed terrain (planning-grade LiDAR, see §4)
- Bay-view axis (az 330°, measured EPT viewshed result behind it)

**Provisional (real geometry, decision OPEN):**
- **Stage core + shoulders** — inherited `design_open_low` az-150 footprint.
  Rule 9 is open: +25.6° audience-axis mismatch, −22.5 ft lateral offset. The
  viewer renders it dashed-purple, banners it persistently in the header, and
  labels it in the layer panel. Do not present the stage as settled.

**Illustrative only (schematic, non-binding):**
- Treatment-cell shaping (concept tier), event/orchestra floor zone,
  event-mode overlays, schematic site context (tree mass, some paths),
  the performer marker, all text sprites

## 3. The truth package (`truth_package/`)

| File | Contents |
|---|---|
| `design_state.current.json` | structured design state: site, CRS/datum, every layer with its source file + provenance + tier, the 7 camera presets, warnings block |
| `evaluation_report.current.json` | 22 checks, each **pass / warn / fail / unknown** with value, threshold, and source artifact. Uncomputable checks are reported `unknown`, never silently passed |
| `export_manifest.json` | export contract: what exists today (viewer, truth JSON, GeoJSON, audit CSV) and planned targets (GeoPackage, glTF/GLB, LandXML, PDF exhibits) with inputs and consumer lists |
| `data_inventory.md` | pre-build inventory: which repo files are source of truth, what renders honestly, computable vs unknown checks |

Headline audited numbers (regenerated, not hand-typed):
**1,283 nominal seats · 1,243 strict Band-A** (Rule 8 accounting; south r18
station-C 2–7 mm under the 90 mm bar within DEM noise = fail/warn; bend r1 at
the 2.5 % cross-slope ceiling = warn). Earthwork 500.8 CY gross carries the
known ~2–2.6× understatement caveat (`TIER_EMISSION_VALIDATION.md`).

Check totals: **7 pass · 2 warn · 2 fail · 11 unknown.** The unknowns are real
project gaps (groundwater, geotech, IGLD85↔NAVD88 Δ confirmation, stage
structure/acoustics, full ADA code compliance, egress, permitting, utilities,
boundary survey, cost, tree survey) — listed in the viewer's "Not yet known"
panel section.

## 4. Terrain honesty — LiDAR voids

The source rasters (`dem/dem_design_1ft.tif`, `dem/proposed_grade_1ft.tif`)
contain real LiDAR voids — **~12 % of the design grid, mostly the east flank**.
For display the build interpolates them (GDAL `fillnodata` at full resolution,
then decimation) so the mesh has no holes, **and discloses it**:

- a bit-packed void mask (`void_b64`) ships with every filled grid in
  `site_data.js`
- the viewer tints void cells grey (elevation view) / neutral (cut-fill view)
- the layer panel states the interpolation in plain text

Interpolated cells are *not measured ground*. Do not scale measurements off
the east flank.

## 5. Coordinates & datums

- Horizontal: **EPSG:6494** NAD83(2011) / Michigan Central, **INTERNATIONAL
  feet** (misreading as US-survey ft shifts easting ~39 ft — see
  `docs/datum_note.md`)
- Vertical: **NAVD88**, Geoid12A, intl ft
- Viewer-local coordinates are offsets from E 19,533,067.7 / N 750,799.2
  (recorded in `design_state.current.json → site.local_origin`)
- Bay level: 581 ft IGLD85 ≈ 581.4 ft NAVD88 via Δ = +0.40 ft — a **labelled
  assumption**, unconfirmed (evaluation report carries it as `unknown`)

## 6. Regenerate everything

```bash
.venv/bin/python scripts/build_truth_package.py
```

(needs an active venv with `numpy` + `rasterio`; never installs at system
level). The script:

1. reads the governing sources — `vectors_geojson/terrace_treads.geojson`,
   `bowl_zones.geojson`, `site_context.geojson`, `in_situ_viewpoints.geojson`,
   `material_zones.geojson`, `design_open_low/stage_floor.geojson` (stage
   lineage only), `analysis/tier_emission/Scenario_E_baseline_reemit/validation.json`,
   `dem/*.tif`, `dem/in_situ_grading_manifest.json`
2. writes the three `truth_package/*.json` files and `web_viewer/data/site_data.js`
3. **never mutates the source GeoJSON/rasters** and embeds a sha256 prefix of
   each raster it consumed

All seat counts, per-row C values, check statuses, and preset eyes are computed
from those sources at build time — there are no hard-coded claims in the
viewer.

## 7. Source-of-truth map (where each on-screen thing comes from)

| On-screen | Source file |
|---|---|
| Seating treads + per-row audit | `vectors_geojson/terrace_treads.geojson` + `analysis/tier_emission/.../validation.json` |
| Stage (provisional), cross-aisle, ADA, swales, cell, event floor | `vectors_geojson/bowl_zones.geojson` |
| Site context (rim, paths, tree mass, bay corridor) | `vectors_geojson/site_context.geojson` |
| Camera presets (4 of 7) | `vectors_geojson/in_situ_viewpoints.geojson` |
| Bay-view axis + focal point | `design_open_low/stage_floor.geojson` (inherited lineage) |
| Terrain (existing / proposed / cut-fill) | `dem/dem_design_1ft.tif`, `dem/proposed_grade_1ft.tif`, `dem/cut_fill_1ft.tif`, `dem/dem_context_2p5ft.tif` |
| Check statuses | `analysis/tier_emission/.../validation.json`, `analysis/scenarioE_civic/earthwork.csv`, `docs/DESIGN_CANON.md` Rule 8 note |

Superseded generations (`design_open_low/seating_rows.geojson`,
`package/05_seating/`, `stage4/`) are **not** rendered; see
`truth_package/data_inventory.md`.

## 8. Future exports

`truth_package/export_manifest.json` is the contract: GeoPackage (ogr2ogr from
the GeoJSON layers), glTF/GLB (reuse the viewer mesh builder, bake truth-tier
into material extras), LandXML TIN surfaces (if feasible at planning grade),
and PDF exhibit generation. Rule for all of them: **every export carries the
warnings block — an export that strips the planning-grade and
stage-provisional caveats is non-conforming.**
