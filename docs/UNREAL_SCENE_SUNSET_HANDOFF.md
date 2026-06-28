# Little Traverse Bay sunset — scene-authoring handoff proposal

**Status:** **IMPLEMENTED 2026-06-27** (§3a + §3b). The lighting baseline (§1) plus
the post-process volume (§3a) and water-material upgrade (§3b) are all SAVED in
`CivicBowl.umap`. §3c (terrain z-fight) remains OUT OF SCOPE — it touches geometry
and is routed separately. See **§6 Implementation log** for exactly what was authored
and the revert recipe. This file was originally a go/no-go PROPOSAL; the go decision
was taken and the authoring work below is now live.

> **UPDATE 2026-06-27 — default look changed.** The §1 deep-red *sun-on-horizon* (0°)
> baseline has been **superseded** by a **graded golden-hour** look (sun lifted to ~4°)
> plus real water reflections, because at 0° the whole sky — and therefore the
> water — was a single colour. See **§8** for the adopted values; §1 is retained as
> the revert target / history.

---

## 1. What was done (saved baseline — SUPERSEDED by §8)

A grazing-horizon sunset over the bay corridor, achieved with **visibility, lighting,
and material binds only** — no geometry touched. Saved to `/Game/Maps/CivicBowl`.

| Actor / component | Property | Saved value | Original |
|---|---|---|---|
| `DirectionalLight_0.LightComponent0` (atmosphere sun) | RelativeRotation | pitch **0**, yaw **125**, roll 0 | pitch −50, yaw 30 |
| | Intensity | **28** | 12 |
| | LightColor (RGB) | **(1.0, 0.580, 0.302)** | (1.0, 0.96, 0.90) |
| | bAffectsWorld / bAtmosphereSunLight | true / true | (unchanged) |
| `SkyLight_0.SkyLightComponent0` | Intensity | **4.0** | 1.5 |
| | SourceType | SLS_CapturedScene | (unchanged) |
| `DirectionalLight_1` / `_2` | bAffectsWorld | false (disabled) | (unchanged) |

- **Azimuth yaw 125** = light forward travels SE→ so the sun disk sits **WNW (az ~305°)**,
  setting down the bay-view axis over the water — not behind the camera.
- **Elevation 0°** (pitch 0) = sun disk exactly on the horizon / waterline.

**Revert to the prior accepted single-sun review lighting** (see
`ue-lighting-singlesun-accepted` memory): set `DirectionalLight_0.LightComponent0`
RelativeRotation pitch −50 / yaw 30, Intensity 12, LightColor (1, 0.96, 0.90);
SkyLight_0 Intensity 1.5; then `save_assets ["/Game/Maps/CivicBowl"]`.

> NOTE: saving this **supersedes** the `ue-lighting-singlesun-accepted` decision
> (which kept a higher midday-ish sun). The sunset is now the default review look.

---

## 2. Why it still reads blood-red / dim (not a bug)

At elevation 0°, the sun's light traverses the **maximum atmospheric path**, so
`SkyAtmosphere` applies heavy Rayleigh extinction: the sky reddens hard and scene
exposure drops. This is physically correct — it is what a sun *on* the horizon does.
The current stack has no compensating authoring, so the bowl is hard to read:

1. **No post-process volume** — the scene runs on default auto-exposure, which chases
   the dark frame and crushes midtones; there is no fixed exposure or tone curve.
2. **`M_water` is a flat unlit-ish sheet** — no ripple normal, no specular response,
   so the low sun produces no glitter/sun-glint track on the bay; the water reads as
   a matte slab rather than a lit surface.
3. **White-speckle z-fight** on the terraced terrain/lawn (draped seating/ADA paths
   vs `Foreground_HiFi` terrain) — present independent of lighting; cosmetically
   worse under the low-key sunset. Touches geometry → out of scope here.

---

## 3. Proposed authoring work (the "proper" sunset)

Read-only-geometry-safe: all three items add or edit **material / post-process /
lighting** assets. None move seating, stage, ADA, or terrain vertices.

### 3a. Post-process volume (highest impact, lowest risk)
- Add an unbound `PostProcessVolume` (bUnbound=true) to `CivicBowl.umap`.
- Set **manual exposure** (e.g. EV100 ~10–11) to stop auto-exposure from crushing the
  frame; pick a value that keeps the bowl rows readable with the sun on the horizon.
- Gentle **color grading**: lift shadows, pull global saturation back from the
  blood-red, warm the midtones toward amber/gold rather than pure red.
- Optional mild **bloom** on the sun disk for the "glow" without overblowing.
- *Effort:* ~1 short session. *Reversible:* delete the volume.

### 3b. Water material upgrade
- Author `M_water_bay` (or a MaterialInstance of the existing `M_water`) with:
  - a scrolling/normal-mapped **ripple** for micro-surface,
  - **specular + roughness** tuned so the low sun lays a glint track across the bay,
  - subtle Fresnel so the far water lightens toward the horizon.
- Bind it on `ctx_bay_water_plane` (SMA_1), `ctx_shoreline_proxy` (SMA_2),
  `ctx_distant_horizon_band` (SMA_3) in place of the flat `M_water`.
- *Effort:* ~1 session in the material editor. *Reversible:* rebind `M_water`.
- *Optional later:* swap the flat plane for a `Water` plugin body (Water Zone) for
  real waves — larger lift, evaluate after 3a/3b.

### 3c. Terrain z-fight cleanup (separate decision — touches geometry)
- The white speckles are draped path meshes coplanar with the terrain. Fix options:
  small Z offset on the draped layer, a decal approach, or a depth-bias material.
- **Out of scope for the read-only posture** — flag to whoever owns
  `Foreground_HiFi` (see `ue-nested-context-build`). Listed here only so it isn't lost.

---

## 4. Recommended sequence
1. **3a post-process volume** first — biggest readability win, fully reversible, no
   geometry. Re-evaluate the sunset after this alone; it may be "good enough."
2. **3b water material** if the bay still reads as a matte slab.
3. **3c z-fight** routed separately as a geometry-touching change.

## 5. Verification
- Capture via `EditorAppToolset.CaptureViewport` (pose: loc(−3397.4, 3804.07, 19505.72),
  yaw −30, pitch −10, FOV 90) after each step; compare against the saved baseline
  frame `/tmp/shots/ue_sunset_00.png`.
- Keep the GUI editor (`run_mcp_server.sh 8000 gui`) as the only heavy GPU process —
  do not run a second editor/ollama load concurrently (box has hard-crashed under
  combined 4080 load).

---

## 6. Implementation log (2026-06-27)

Authored entirely through the Unreal MCP toolset against the already-running headless
`UnrealEditor-Cmd` instance (MCP `127.0.0.1:8000`). That instance **does** have a
working RHI, so `CaptureViewport` returned real frames and every step below was tuned
to the rendered image rather than to theoretical EV numbers. The documented review
pose was used throughout: loc(−3397.4, 3804.07, 19505.72), yaw −30, pitch −10, FOV 90.

### 6a. PostProcessVolume (§3a)
New actor `PostProcessVolume_1` (label `PPV_SunsetGrade`) in `CivicBowl.umap`:

| Property | Value | Purpose |
|---|---|---|
| `bUnbound` | true | affects the whole scene |
| `Priority` | 1.0 | |
| `Settings.AutoExposureMethod` | `AEM_Manual` | stop auto-exposure chasing the dark frame |
| `Settings.AutoExposureApplyPhysicalCameraExposure` | false | exposure independent of camera aperture/ISO |
| `Settings.AutoExposureBias` | **0.9** | fixed readable level (tuned: 1.5 → 0.7 → 0.9) |
| `Settings.ColorSaturation` | (0.85, 0.85, 0.85, 1.0) | pull saturation back from blood-red |
| `Settings.ColorContrast` | (1.1, 1.1, 1.1, 1.0) | restore tonal depth |
| `Settings.ColorGain` | (1.0, **1.07**, 1.03, 1.0) | lift green/blue → shift red toward amber/gold |
| `Settings.WhiteTemp` | 5800 | take a touch of heat off the deepest reds |
| `Settings.BloomIntensity` / `BloomThreshold` | 0.8 / 1.0 | soft glow on the sun disk |

Tonemapper left at the engine default (`Filmic`). Result: the bowl rows, bay corridor,
building silhouettes and sky gradient are all legible; the warm cast that remains is the
physically-correct `SkyAtmosphere` extinction at 0° elevation (see §2), not a defect.

### 6b. Water material (§3b)
The flat `M_water` exposes **zero parameters**, so a MaterialInstance of it cannot add
ripple/glint — the handoff's "or a MaterialInstance of the existing M_water" fork is a
dead end. Instead a new instance was parented to the self-contained Datasmith water
master (chosen over the UE Water-plugin masters, which need WaterBody/WaterZone
infrastructure and render broken on a plain static-mesh plane):

- **`/Game/Materials/Context/MI_water_bay`** — parent `/DatasmithContent/Materials/Water/M_Water`.
  - `WaveStrength` = 0.65, `WaveSize` = 1400 (calm-bay glint column; defaults were 1.0 / 1000).
  - `WaterColor` left at the deep blue-teal default (0.024, 0.125, 0.177); animated
    normals + Fresnel reflection are inherited from the master and give the sun-glint
    track and horizon lightening §3b asked for.
- Bound on the `StaticMeshComponent0.OverrideMaterials[0]` of all three water actors:
  `ctx_bay_water_plane` (SMA_1), `ctx_shoreline_proxy` (SMA_2), `ctx_distant_horizon_band` (SMA_3).
  All three were already `bVisible=true` (the 2026-06-25 hidden-proxies decision had been
  superseded by the later "re-show water" work), so the rebind is visible.

### 6c. Revert recipe
- **3b:** rebind `OverrideMaterials[0]` = `/Game/Materials/Context/M_water` on SMA_1/2/3,
  then optionally delete `/Game/Materials/Context/MI_water_bay`.
- **3a:** delete actor `PostProcessVolume_1`.
- Then `save_assets ["/Game/Maps/CivicBowl"]`. (The §1 lighting baseline is unaffected.)
- Full revert to the prior single-sun review look is still the §1 recipe above.
- *Note:* SMA_3 (`ctx_distant_horizon_band`) was later retired in §7 — it is now
  HIDDEN with `M_water` rebound, so the 3b revert only needs SMA_1/SMA_2.

---

## 7. Opposite-shore real terrain (2026-06-27) — replaces the fake horizon band

Follow-on to "How about the opposite shore? I'd like more fidelity to the actual
height and terrain of it." The far (N/NW) shore of Little Traverse Bay — the
Harbor Springs / Harbor Point headland seen down the ~330° bay-view axis — was a
flat, non-metric placeholder (`ctx_distant_horizon_band`, a 120 m vertical band
5.2 km out, manifest-labelled *"atmospheric … not a measured landform"*). It is now
**real USGS 3DEP terrain**.

### 7a. What was done
- **Fetch** — `scripts/unreal/fetch_farshore_dem.py --run`: USGS 3DEP `exportImage`
  over AOI lon/lat W −85.030 / S 45.400 / E −84.940 / N 45.462 (≈7.1 × 6.9 km) at
  **10 m** (coarse is right for a 5 km-distant ridge). Output
  `data/context/dem/farshore_3dep.tif` (EPSG:6494, NAVD88 m) + provenance JSON.
  Measured elevation **176.4 → 312.8 m** (i.e. ~136 m / 447 ft of real bluff relief
  above the 176.62 m bay datum).
- **Mesh** — `scripts/unreal/build_farshore_terrain.py --run`: reuses
  `gen_context._load_dem` / `_dem_mesh_enu` / the ENU→UE bake matrix, so it lands in
  the **identical coordinate frame** as every other context mesh (no reprojection, no
  datum offset). Water is dropped data-drivenly (cells ≤ `WATER_ELEV_M + 1.5 m` → NaN)
  so only land above the bay is meshed; `min_north_local_m = 3000` keeps it clear of
  the audited terrain. Result `build/unreal_scene/meshes/ctx_farshore_terrain.obj`:
  **66,954 verts / 132,512 tris**, ENU extent N 4954–9757 m, E −5607–1478 m,
  ztop 312.8 m (+ `.stats.json`).
- **Import / place** — MCP `StaticMeshTools.import_file` →
  `/Game/Meshes/CivicBowl/ctx_farshore_terrain`, slot material `M_terrain` (matches
  `ctx_fg_terrain`); spawned `StaticMeshActor_23` at origin, scale ×100 (same contract
  as the other context meshes).
- **Retire the band** — `ctx_distant_horizon_band` (SMA_3): `bVisible=false`,
  material reverted to `M_water`.
- **Close the near gap** — the bay water plane (SMA_1) far edge was at N≈4500 m, short
  of the far-shore base at N≈4954 m; its `RelativeScale3D.x` was raised 128.57 → 143
  so the water (still flat, at datum) reaches ≈5005 m and underlaps the shore in the
  primary view direction.

### 7b. Faithfulness & a known limitation
- The shore is real 3DEP height/shape; from the venue (≈5 km across the bay) 136 m of
  relief only subtends ~1.3°, so it correctly reads as a **low headland**, not a wall —
  exaggerating it would be the opposite of fidelity. In the canonical review/sunset
  pose it appears as the Harbor Point headland to the right of the setting sun (which
  sets W over open water toward Lake Michigan).
- **Known limitation:** the bay water is still a *rectangular* proxy (±2000 m E). The
  far shore extends west of that, and the bay is asymmetric, so from elevated NW angles
  a water/shore gap shows. Widening the rectangle east would flood land. Proper fix =
  a real **OSM bay-water polygon** (the pipeline already has `water_edge.geojson` /
  `_land_mask` hooks) or a Water-plugin Water Zone — a separate task.
- **Provenance / pipeline:** the two scripts are reproducible and carry provenance, but
  the layer is **not yet wired into `unreal_context_manifest.json` / `gen_context` /
  `verify_context`**. Optional follow-up: add a `farshore_terrain` manifest layer so a
  standard `gen_context` + `ue_context assemble` reproduces it and the obstruction gate
  accounts for it.

### 7c. Revert recipe (far shore)
- Show the band again: SMA_3 `StaticMeshComponent0.bVisible=true`.
- Hide/delete the new terrain: `StaticMeshActor_23` (or
  `delete /Game/Meshes/CivicBowl/ctx_farshore_terrain`).
- Restore the water plane: SMA_1 `RelativeScale3D.x = 128.57`.
- `save_assets ["/Game/Maps/CivicBowl"]`.

---

## 8. Graded golden-hour + water reflections (ADOPTED 2026-06-27) — new default

Follow-on to "make the water water so we can reflect the light" → "the water is
reflecting just one colour … the sunset is just orange." Correct diagnosis: at sun
**elevation 0°** (§1) the atmospheric path is maximal in every direction, so
`SkyAtmosphere` reddens the *whole* dome uniformly — a one-colour sky gives a
one-colour reflection. The fix is in the sky, not the water.

### 8a. What changed (all SAVED in CivicBowl.umap)
| Actor / setting | §1 value (old) | §8 value (now) | why |
|---|---|---|---|
| `DirectionalLight_0` RelativeRotation pitch | 0 (0° elev) | **−4 (≈4° elev)** | lift off the horizon → recover the gold→blue gradient |
| `DirectionalLight_0` Intensity | 28 | **14** | stop the warm sun flooding out the atmosphere's blue |
| `DirectionalLight_0` LightColor | (1.0, 0.58, 0.30) | **(1.0, 0.86, 0.72)** | near-neutral warm — let the atmosphere do the reddening |
| `SkyLight_0` Intensity | 4.0 | **2.0** | lower ambient fill so colour/contrast isn't washed flat |
| `PPV` Settings.AutoExposureBias | 0.9 | **0.0** | scene is brighter now; pull exposure down to keep colour |
| `PPV` Settings.ColorGain | (1, 1.07, 1.03) | **(1,1,1)** | the green/blue push was to fight pure red; not needed now |
| `PPV` Settings.LumenFrontLayerTranslucencyReflections | (off) | **true** | the water is `BLEND_Translucent` (DefaultLit); this is what lets Lumen put real **environment reflections** (sun, sky, far shore) on it |
| `PPV` Settings.LumenMaxRoughnessToTraceReflections | — | **1.0** | trace reflections across the full water roughness range |

`MI_water_bay` waves left balanced (WaveStrength 1.0, WaveSize 1000). Yaw 125 (WNW),
the §3a saturation/contrast/whiteTemp/bloom, and all of §6/§7 are unchanged.

### 8b. Result & note
- Sky now grades gold/peach at the horizon → blue-grey aloft; the bay reflects a
  **range** — a gold sun-glitter pillar toward the viewer plus the cooler sky on calm
  water. Grazing water still samples mostly the warm *horizon* band (physically
  correct), so the water reads warm with tonal range rather than flat red.
- Tradeoff vs §1: brighter, more naturalistic golden-hour; the sun sits just **off**
  the waterline rather than dramatically *on* it. (User chose this over keeping the
  deep-red mono look.)
- True mirror **planar** reflection was *not* used — it needs the project's global
  clip-plane setting + an editor restart (risky on this box); Lumen front-layer
  reflection gets most of the way with neither.

### 8c. Revert recipe (back to the §1 deep-red on-horizon look)
- `DirectionalLight_0.LightComponent0`: pitch 0, Intensity 28, LightColor (1,0.58,0.30).
- `SkyLight_0`: Intensity 4.0.
- `PPV`: AutoExposureBias 0.9, ColorGain (1,1.07,1.03). (Front-layer reflection can stay on.)
- `save_assets ["/Game/Maps/CivicBowl"]`.
