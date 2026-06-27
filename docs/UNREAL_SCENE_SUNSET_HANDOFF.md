# Little Traverse Bay sunset — scene-authoring handoff proposal

**Status:** PROPOSAL (not implemented). Lighting baseline below is SAVED in
`CivicBowl.umap` as of 2026-06-27. Everything in §3 is future authoring work that
exceeds the read-only review posture (it adds/edits material + post-process assets)
and is offered for a go/no-go decision.

---

## 1. What was done (saved baseline)

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
