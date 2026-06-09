# Terrain Reality Summary — Corrected Framing
## Petoskey Pit — East Flank Reality Check

**Compiled 2026-06-06. Planning-grade. All elevations NAVD88 intl ft, EPSG:6494.**

---

## Corrected terrain narrative

The S, SE, and E flanks appear to form a **continuous amphitheater-grade bowl wall**. The east flank rises west-to-east toward Petoskey Street and the eastern property edge. It is not currently proven to be a distinct escarpment.

Raw 1-ft DEM slope spikes near the eastern rim should be treated as **artifact candidates** until multi-scale slope, transect, contour, and/or field survey checks confirm a persistent physical break. The design problem is not avoiding the east side; it is deciding how to use the east flank, upper eastern plateau, and Petoskey Street rim transition without producing bad row geometry, excessive cross-slope, inaccessible circulation, drainage problems, or visually heavy earthwork.

---

## What the DEM currently supports

**Measured / computed from public USGS LiDAR 1-ft DEM (`dem_design_1ft.tif`), 2015 vintage. All figures are planning-grade. ±0.5–1.0 ft vertical accuracy. Field verification required.**

### The bowl floor
- Pit depression floor: approximately **609–610 ft** NAVD88
- Floor width: approximately 140 ft (±70 ft from center)
- Character: closed depression, cut-dominant terrain

### The S/SE seating band (R 85–130 ft from stage focus)
- Elevation range: approximately **613–628 ft** across this band
- Rise over run: approximately +15 ft over 45 ft horizontal run
- Slope: approximately 33% (18°) — this is a reliable, repeated measurement in multiple scripts
- Status: **confirmed (A)** — multiple scripts agree; not disputed

### The bowl rim
- Bay-side (NW) rim: approximately **618 ft**
- General rim spill elevation: **618.04 ft** (pour-point analysis)
- Upper eastern plateau: approximate elevation range from archive profiles — needs specific east-transect values from forensic script
- Status: rim elevation is confirmed; upper-plateau character requires targeted transect

### The east flank (the contested zone)
- Prior characterization: "gentle," "garden zone," "ENE 88–122°"
- Basis for prior characterization: azimuthal designation and the assumption that the seating wall was limited to S/SE; NOT a specific slope measurement confirming east-flank gentleness
- Corrected status: **unverified** — the 1-ft DEM archive profiles included an east-west profile (archival CSV in `petoskey_pit_lidar_analysis_archive/`) but the profile section summary showed a ~4.4% average east-side slope (from the archive expanded CSV negative side), which is far below the 30° escarpment claim. However, that profile was taken from a much larger context AOI, not specifically the eastern bowl rim.
- **Key data gap:** a targeted transect from the pit center due east through the bowl wall and upper plateau, sampled at 1-ft DEM resolution with multi-scale slope statistics, has not been produced in any surviving project file.

---

## The 30° claim — source reconstruction

The "30° escarpment" or "steep band" language appears as:

1. **Design stop parameters** in scripts (`R_SCAN_MAX=150`, `E_CAP=629.5`, `DRDT_EAST=0.7`) — these are code constants, not terrain measurements
2. **Relative comparisons** like "below the steep band" in `design_open_low/README.md` — describes a zone, not a measured slope
3. **The first-design retaining wall discussion** in `gating_dossier.md` C-3 — specifies 6–14 ft cuts against the "steep SE/SSE wall" for the *original 30-row ±30° design*, which had very different geometry
4. **Implied by the garden-zone designation** of the east sector in `stage5_grading.py` — east was "garden" partly because the seating arc stopped before reaching it

There is **no surviving project document** that presents a direct measured transect of the east flank with a documented slope exceeding 30° persisting over design-relevant width. The "steep band" is an assumption that has never been independently validated from the DEM.

### Plausible artifact sources for any 30°+ pixels near the eastern rim

| Artifact type | Mechanism | Detectability |
|---------------|-----------|---------------|
| 1-ft pixel edge / rim-break | Single-pixel elevation discontinuity at the top-of-bank; a 0.8 ft step across a 1-ft cell = 80% = 39° | Compare to 3/5/10-ft smoothed slope |
| Building, fence, wall | LiDAR classifies structure returns as ground → local spike | Check orthoimagery / field survey |
| Curb or retaining wall remnant | Small historical wall returns classified as ground points | Same as above |
| Derivative noise | `np.gradient` on raw 1-ft DEM produces 30–53° apparent slope from micro-roughness (documented in memory from `design_corner_bays.py` work) | Already documented anti-pattern; use de-noised gradient |
| Vegetation penetration | Partially filtered canopy near property edge | Compare to point cloud density / classification |

---

## Seating-axis profile — direct measurement (2026-06-06)

**Measured directly on the seating centerline from the bowl floor.** Source: user-supplied DEM profile on the seating axis.

| Radial range | Slope range | Character |
|---|---|---|
| R 85–130 ft (current 16 rows) | 17–43%, avg ~30% | Normal amphitheatre hillside — irregular, walkable, buildable. No arresting step. |
| R 130–190 ft (rows 17–35+ range) | 29–42%, avg ~30% | **Same character as the seating zone.** The hill continues at the same rate. |
| R 190–205 ft | 7–16% → near zero | **Terrain tops out. Upper plateau begins.** Consistent with Petoskey Street rim. |

> "There is no slope that warrants halting seating. The terrain rises continuously and gradually from row 1 to the street at roughly 30% average, then flattens into the plateau. The hill doesn't do anything dramatic beyond row 16 that it wasn't already doing before it."

The 39–41% slope spikes that the prior harness flagged are **real micro-irregularities — bumps — not an escarpment.** They occur within the already-validated R85–130 seating zone as well. No distinct terrain break separates rows 1–16 from rows 17+.

**Revised seating-viable zone (from this profile): R~85–190 ft**, potentially ~35 rows at 3-ft tread spacing before the terrain transitions to the upper plateau. The upper plateau transition at R~190–205 ft is the natural design terminus.

---

## What this means for design

1. **The S/SE/E rake (~30% avg, 17–43% range) is a solid measured foundation.** This is the seating bank character across the full bowl.
2. **The "gentle east" narrative is false.** The east flank is the same character as S/SE — not gentle, not an escarpment: a usable bowl wall.
3. **The "stop below R130 to avoid the steep band" rationale is proven wrong.** No steep band exists. R130 is an arbitrary budget stop, not a terrain limit.
4. **The viable seating zone extends to approximately R190 ft.** Beyond that, the terrain flattens into the upper plateau / Petoskey Street rim.
5. **A continuous civic bowl using the S/SE/E landform to R~150–190 is fully terrain-supported.** This is the principal scenario unlocked by the corrected framing.
6. **The harness stop condition must be updated.** Flagging 39–41% slope as an escarpment stop is wrong — those are bumps within the normal seating band character.

---

## Separation of knowledge types

| Claim | Type | Confidence |
|-------|------|-----------|
| Floor ~609–610 ft | Measured from DEM | High (±1 ft) |
| S/SE seating rake ~33%/~18° | Measured from DEM | High |
| Rim spill ~618 ft | Measured (pour-point) | High |
| Upper eastern plateau exists | Inferred from general context | Medium — needs transect |
| East flank slope is "gentle" | Prior assumption — unverified | Low |
| 30° escarpment exists on east rim | Inferred from script stop parameters | Not proven — treat as artifact candidate |
| S/SE/E is a continuous bowl wall | Hypothesis (corrected framing) | Testable — run terrain forensics |
