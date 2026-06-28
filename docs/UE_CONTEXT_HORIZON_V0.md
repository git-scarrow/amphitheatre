# UE Context + Horizon v0 — geographic context around the Petoskey Pit

Adds **approximate, clearly-labeled** geographic scenery around the audited
CivicBowl review scene — Little Traverse Bay, a horizon reference, optional
open-data city massing, and a **calculated** sunset sun/sky — so the
`/Game/Maps/CivicBowl` scene can be reviewed at human / civic scale (city, bay,
horizon, sunset orientation).

This is a *parallel* layer to the audited design toolchain in
`scripts/unreal/` (see that README). The governing rule is **separation**:

> The audited design geometry stays exact and gated. Context scenery may be
> approximate, but every context layer declares its source, accuracy, and
> intended use, and **nothing here can change a design-count gate or edit design
> truth.**

## What was added

| Layer | Geometry | What it is | Measured / inferred / atmospheric |
|---|---|---|---|
| `bay_water_plane` | flat surface at **579.45 ft NAVD88**, NNW of site | Little Traverse Bay water surface | **elevation MEASURED** (EPT viewshed); planar extent inferred (simplified rectangle) |
| `bay_shoreline_ref` | ribbon at water level | OSM shoreline if present, else a straight-line proxy | OSM (~few m) **or** schematic PROXY |
| `distant_horizon_band` | tall thin band far NNW | closes the view beyond the bay | **atmospheric** — non-metric visual reference |
| `city_massing` | extruded OSM footprints (generic 8 m) | town context massing | **OSM** footprints (~few m); heights generic unless tagged — *approximate massing, NOT measured architecture* |
| `city_roads` | flat ribbons | OSM road centerlines | **OSM** (~few m) |
| `sun_sky_sunset` | DirectionalLight(s) | **calculated** sun direction at named sunsets | sun direction **COMPUTED** (NOAA); sky colour atmospheric |
| `sunset_review_camera` | one CineCamera | upper seat over the stage toward the bay | position from **audited** seating; aim along the audited bay-view axis |

All context actors live under the **`Context/`** Outliner root, which is asserted
disjoint from every audited design folder root. Provenance for every layer is in
[`data/unreal_context_manifest.json`](../data/unreal_context_manifest.json),
which carries, per layer: `layer_name, source, source_type, accuracy_class,
redistributable, intended_use, included_in_verification` (plus `obstruction_role`,
`attribution`, `expected_input`).

## Sunset orientation (calculated, not eyeballed)

The sun direction is a **real NOAA solar-position calculation**
(`context_common.solar_position`), so it is a computed azimuth/elevation, not an
artistic guess. The sky **colour/intensity** remains atmospheric. Computed for
Petoskey, MI (**45.3746° N, 84.9581° W**, derived from the EPSG:6494 local origin):

| Event | Local time | Sun azimuth | Apparent elevation |
|---|---|---|---|
| Summer solstice sunset (2026-06-21) | 21:33 EDT | **305.7°** (NW) | −1.0° (at horizon) |
| Mid-August concert sunset (2026-08-15) | 20:48 EDT | **290.9°** (WNW) | −1.0° (at horizon) |

The **bay-view axis is 330° (NNW)**, so the setting sun sits ~24° (solstice) to
~39° (mid-August) **west/left** of the bay-view corridor — the sunset is in the
left of frame for a camera looking down the axis toward the bay, not dead ahead.
This is the kind of experiential fact the context layer exists to surface; it is
labeled experiential, and the angles are reproducible from the calculation.

## Data sources and limitations

- **Bay water elevation — measured.** 579.45 ft NAVD88 from the EPT viewshed
  analysis (`scripts/build_site_context.py`). The drawn rectangle (extent) is a
  simplified proxy, not a surveyed shoreline.
- **City massing / roads — OpenStreetMap (ODbL).** Fetched via
  `scripts/unreal/fetch_osm_context.py` (Overpass API). Footprints are OSM
  positions (~few m); heights are **generic 8 m** unless the OSM feature carries
  `height`/`building:levels`. Labeled *approximate massing, not measured
  architecture*. ODbL attribution is carried in the GeoJSON and the manifest.
- **Horizon band — atmospheric (SUPERSEDED 2026-06-27).** The flat
  `ctx_distant_horizon_band` was a visual reference only and did not claim a real
  far-shore profile. It is now **HIDDEN** and replaced by **`ctx_farshore_terrain`**
  — real USGS 3DEP terrain of the opposite (N/NW) shore (Harbor Springs / Harbor
  Point + bluffs), built via `fetch_farshore_dem.py` + `build_farshore_terrain.py`
  in the same EPSG:6494→ENU→UE frame. Real relief to ~136 m above the bay. See the
  far-shore section in `docs/UNREAL_SCENE_SUNSET_HANDOFF.md §7`.
- **No proprietary assets.** No Google Earth / Maps / Street View geometry,
  imagery, or DEM is imported. Layers marked `redistributable:false` are refused
  by both the generator and verifier.
- **v0 is deliberately crude.** Flat planes, ribbon roads, blocky massing,
  building bases draped on the water datum (not per-footprint terrain). Faithful
  positions, schematic geometry. Do **not** make public-facing claims from this
  approximate context without the labels.

## How to regenerate

```sh
# 0. (optional) fetch open city context — OSM via Overpass (needs HTTPS egress).
#    Without this, city_massing / city_roads stay DEFERRED (documented, not drawn).
python scripts/unreal/fetch_osm_context.py            # show query + expected paths
python scripts/unreal/fetch_osm_context.py --run      # download -> data/context/

# 1. OFFLINE — stage context meshes + the deterministic context plan
#    (repo venv: shapely trimesh numpy mapbox_earcut pyproj). -> build/unreal_scene/
python scripts/unreal/gen_context.py

# 2. OFFLINE — extended verification (design unchanged + context gates)
python scripts/unreal/verify_context.py               # exit 0 == PASS

# 3. ON GENTOO — the design scene must exist first, then add context, then verify
UEC=/mnt/storage/UnrealEngine-5.8/Engine/Binaries/Linux/UnrealEditor-Cmd
PROJ=/mnt/data/UnrealProjects/PetoskeyCivicBowl/PetoskeyCivicBowl.uproject
"$UEC" "$PROJ" -run=pythonscript -unattended -nullrhi -nosplash \
  -script="$PWD/scripts/unreal/ue_civicbowl.py assemble --plan $PWD/build/unreal_scene/scene_plan.json"
"$UEC" "$PROJ" -run=pythonscript -unattended -nullrhi -nosplash \
  -script="$PWD/scripts/unreal/ue_context.py  assemble --plan $PWD/build/unreal_scene/context_plan.json"
"$UEC" "$PROJ" -run=pythonscript -unattended -nullrhi -nosplash \
  -script="$PWD/scripts/unreal/ue_context.py  verify   --plan $PWD/build/unreal_scene/context_plan.json"
```

`gen_context.py` is deterministic (no timestamps; sorted; source shas), so
`gen` + `git diff` on `context_plan.json` is a reproducibility check. The headless
commandlet prints `Exiting abnormally (error code: 1)` on shutdown even on success
(UE quirk / leftover crash-report flush) — trust the `[context] …` / `VERDICT:`
log lines and `Python script executed successfully`, not the process exit code.

## How to capture the sunset review camera (later)

v0 runs `-nullrhi` (no GPU), so it produces no pixels — only geometry + the
calculated light/camera setup. To capture:

1. Launch with a GPU/GUI RHI: `run_mcp_server.sh 8000 gui` (host doc §), or
   `UnrealEditor` (not `-Cmd`) without `-nullrhi`.
2. Make the sun visible: the solstice DirectionalLight (`ctx_sun_summer_solstice_sunset_2026`)
   is spawned visible; the others are spawned hidden — toggle in the Outliner to
   switch the evening. For a full sky, add a `SkyAtmosphere` + `SkyLight` (a GUI
   follow-on; headless sky asset creation is fiddly).
3. Pilot `ctx_cam_sunset_review` (looks from the upper seating row over the stage
   down the 330° bay-view axis) and use **High-Resolution Screenshot** or Movie
   Render Queue.

## What remains TODO

- **City massing/roads live.** Fetch OSM (`fetch_osm_context.py --run`) in an
  environment with egress, re-`gen_context`, re-assemble. The bay-view
  obstruction gate (`verify_context.py` step 5) becomes a *live* check then —
  currently 0 occluders ⇒ corridor trivially clear.
- **Per-footprint terrain draping.** Building bases sit on the water datum in v0;
  drape them on the proposed/existing terrain for correct vertical placement.
- **Sky + atmosphere + colour grade.** Atmospheric, GUI follow-on.
- **Real shoreline.** Drop an OSM/Hydro coastline at `data/context/shoreline.geojson`
  to replace the straight-line proxy.
- **Rendered captures.** Need the GPU/GUI launch above.

## Verification summary (this pass)

- Offline `verify_context.py` → **PASS** (design unchanged · manifest valid · context
  isolated · corridor clear · orientation det −1, water level, camera aim 328.7° ≈ 330°).
- Live (gentoo, `-nullrhi`): design assemble → `2 terrain + 91 actors + 7 cameras`;
  context assemble → `3 actors + 1 camera + 2 sun lights` under `Context/`; reload
  `ue_context.py verify` → **VERDICT: PASS**, all 9 audited design groups exact.
