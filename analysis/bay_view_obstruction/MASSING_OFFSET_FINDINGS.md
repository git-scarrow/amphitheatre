# W/NW context massing — suspected vertical/registration offset: FINDINGS

Audit of the "large building/massing west of the Civic Bowl appears to obstruct/dominate
the bay-side context" report. Read-only. **Nothing in the scene was moved, deleted, hidden,
or re-lit.** No design geometry touched.

Date: 2026-06-26. Scene: live `/Game/Maps/CivicBowl` (gentoo UE 5.8 MCP host) + ground-truth
reconstruction from OSM + USGS 3DEP/LiDAR.

---

## Verdict: **A — real and approximately correctly placed.** Not a placement/offset bug.

The W/NW massing is **real OpenStreetMap buildings at correct real-world positions, sitting on
grade, with normal heights.** No vertical offset, no wrong datum, no horizontal misplacement,
no mirror, no un-hidden proxy, no artifact. The "dominance" is a *viewing/fidelity* effect, not
a registration error.

Secondary note: the generic (`building=yes`) blocks are lo-fi flat-grey extrusions at
LiDAR-measured (not surveyed) heights — they read bulkier than the real 1–3 storey buildings.
That is fidelity, not misplacement (a minor **D** flavour, but the geometry is genuine).

---

## What the camera is looking at

Current viewport camera (live `GetCameraTransform`): UE `(-4052, 4182, 19639) cm`
→ ENU **E +41.8 m, N −40.5 m, eye 196.4 m (≈644 ft)**, yaw −35° / pitch −14°
→ facing **az ≈ 325° (NNW), down the bay-view axis**. This is the "upper-rim-down-to-stage" view.

Eye 644 ft is **above the top seating row (row 18 ≈ 637 ft)**, so the terrain rim does **not**
block the bay from this camera (see `summary.md`). Anything in front of the bay here is **city
massing**, which is the subject of this audit.

## The suspect actor(s)

- The city buildings are a **single merged StaticMesh actor**: `ctx_city_massing`
  (`StaticMeshActor_6`, folder `Context/City_LoFi/city_massing`, transform = origin, scale ×100,
  `bVisible=true`). Individual buildings are sub-meshes — not separate actors — so the "suspect"
  is identified from the GIS source, not an actor name.
- Source layer: `Context/City_LoFi/city_massing`, built by `gen_context.py` from
  `data/context/osm_petoskey_buildings.geojson` (OSM, ODbL); heights from USGS LiDAR DSM −
  3DEP DTM; base draped on the city 3DEP DTM.

The buildings a viewer reads as "the large mass to the west," ranked by apparent size from the eye
(full table in `massing_suspects.csv`):

| OSM id | name | footprint | dist | az (from eye) | base | top | height | base−terrain | crosses bay sightline? |
|---|---|---|---|---|---|---|---|---|---|
| 510501792 | **Beards Brewery** | 551 m² | 112 m | 348° NNW | 188.7 m | 198.7 m | 10.0 m | −0.07 m | **yes (+1.2°)** |
| 510276684 | **Petoskey Police Dept** | **1119 m²** | 253 m | 299° WNW | 179.9 m | 190.4 m | 10.5 m | −0.39 m | no (below) |
| 510276685 | Lit. Traverse Hist. Soc. | 631 m² | 196 m | 326° (on axis) | 179.9 m | 184.4 m | 4.5 m | +0.03 m | no (below) |
| 465785898 | Petoskey Fire Dept | 533 m² | 319 m | 293° WNW | 180.7 m | 186.8 m | 6.1 m | −0.12 m | no (below) |
| 558923136 | (unnamed `yes`) | 754 m² | 510 m | 302° WNW | 179.0 m | 189.7 m | 10.7 m | −0.75 m | no (below) |

## Evidence the placement is correct (rules out B / C / D / E)

1. **On the vertical datum (rules out B).** For every W/NW building, `base − terrain directly
   beneath` is within ±1 m (Beards −0.07, Police −0.39, Hist.Soc +0.03, worst −1.12). Buildings
   sit **on** the ground — not floating, not buried, not on the water datum. The live merged actor's
   Z-envelope (176.4–286.8 m) matches reconstruction = terrain (176.4–262.0 m, city DEM) + building
   heights; Z-min sits exactly on the 176.6 m water datum (consistent terrain bottom, not an offset).
2. **At the right place (rules out C / mirror).** Footprints come straight from OSM lon/lat →
   EPSG:6494 → ENU; the named civic buildings land at their true real-world bearings
   (Police/Fire WNW az 288–295°, Hist. Soc NNW az 331° on the bay axis, Beards NNE az 16°). The
   prior E–W mirror bug was already fixed (downtown reads ESE). No residual flip.
3. **Real, not placeholder (mostly rules out D).** Beards, Police Dept, Fire Dept, Historical
   Society are named OSM features; heights are LiDAR-measured (DSM−DTM). The generic `yes` blocks
   are real footprints with measured heights — lo-fi in appearance, not fabricated.
4. **Not an un-hidden proxy/artifact (rules out E).** The three legacy proxies
   (`ctx_bay_water_plane`, `ctx_shoreline_proxy`, `ctx_distant_horizon_band`) are all
   `bVisible=false` (hidden) in the live scene; they only appear in `GetVisibleActors` because that
   tests frustum bounds regardless of visibility.

## Why it still *looks* like it dominates the bay

- **Along the true bay-view axis (330°), nothing obstructs.** The eye→bay-water sightline clears
  every building the axis crosses (see `massing_section_bayaxis.png`): terrain descends from 196 m
  at the eye to the 176.6 m water by ~290 m out, and the buildings on it stay below the line.
- The dominant "west" building (**Police Dept, 1119 m²**) is **off-axis (WNW, az 295–299°) and
  below the sightline** — it is on the *left edge* of the wide (≈90°) editor FOV, not between the
  bowl and the bay.
- The bowl is genuinely set back **~500 m south of open Little Traverse Bay** (az ≈ 354°), with the
  downtown/civic edge (these buildings) in between; the open water the user sees on Google Maps is
  *beyond* that edge. The nearest water due-west (az 263°, ~197 m) is the **Bear River**, not the bay.
- The only real bay-direction obstructor is **Beards Brewery** (NNW, 112 m, a real ~10 m building)
  — the long-documented marginal obstruction subject, ~18° east of the curated axis.

## Smallest correction (NOT applied — presentation only; placement needs none)

The buildings are correct; do **not** move/delete/lower them. If the review *reads* wrong:
1. **Re-frame the review camera** to the exact bay-view axis (330°) with a narrower FOV (≈50–60°,
   as the named review cams use) so the off-axis WNW civic cluster falls outside the frame. (No
   geometry change.)
2. Optionally give `ctx_city_massing` a less monolithic material so lo-fi blocks read as the low
   buildings they are. (Appearance only; heights are measured — do not flatten them.)

## Outstanding live confirmation (blocked: MCP dropped mid-audit)

Ground truth + the live actor data gathered before the drop already support the verdict. To
fully close, when the `unreal` MCP server is reconnected (`/mcp`), two quick live checks:
- `SceneTools.trace_world` straight down at the Police Dept / Beards UE coords → confirm live
  rendered top Z matches the reconstruction (190.4 / 198.7 m).
- `EditorAppToolset.CaptureViewport` (current camera, annotations on) → labeled screenshot.

## Artifacts
- `massing_plan_view.png` — plan: bowl/stage, bay-view axis + cone, OSM water edge, W/NW footprints.
- `massing_section_bayaxis.png` — section along 330°: eye, terrain, building tops, bay sightline.
- `massing_suspects.csv` / `.json` — per-building bounds, UE coords, base/top, terrain deltas.
- `massing_rows.json` — full 2475-building reconstruction.
