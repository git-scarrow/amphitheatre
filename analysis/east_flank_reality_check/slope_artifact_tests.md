# Slope Artifact Tests — East Flank 30° Claim
## Petoskey Pit — East Flank Reality Check

**Compiled 2026-06-06. Planning-grade. Tests are specified here; results are in `outputs/` after running `terrain_forensics.py`.**

---

## Purpose

This document defines the tests needed to determine whether the alleged "steep east band" / "30° escarpment" near the eastern rim of the Petoskey Pit is:

1. A real, design-relevant landform persisting over meaningful width and length
2. A 1-ft DEM pixel-scale artifact (rim-break, classification noise, fence/wall return)
3. A derivative-slope artifact from applying `np.gradient` or a standard slope tool to a raw 1-ft DEM (this is a documented problem in this project — see memory)
4. A legacy retaining wall or structure condition near Petoskey Street

---

## Test 1 — Multi-axis DEM profiles

**Method:** Sample elevation along four transects from the pit center (approximate center ~EPSG:6494 X=19532693.76 Y=751107.83 based on low-point coordinates in archive AOI CSV):

| Profile | Direction | Description |
|---------|-----------|-------------|
| P1 | Due south (az 180°) | Reference — S bowl wall |
| P2 | SE diagonal (az ~135°) | SE corner |
| P3 | Due east (az 90°) | East flank toward Petoskey Street |
| P4 | E-SE offset profiles | Parallel offsets every 10 ft N and S of P3 |

**For each profile extract:**
- elevation at each 1-ft station along the transect
- local slope (rise/run between adjacent stations)
- cumulative rise from the bowl floor

**What to look for:**
- Does the east profile (P3) show a slope break that is absent in the south (P1) and SE (P2) profiles?
- Or does P3 show the same gradual rise-then-flatten as P1/P2?
- What is the width of any zone exceeding 25° or 30° in P3?

---

## Test 2 — Slope by scale (the key test for artifact discrimination)

**Method:** Compute slope rasters at four scales:

| Scale | Method |
|-------|--------|
| 1-ft raw | Standard GDAL/scipy gradient on raw DEM |
| 3-ft smoothed | Gaussian-smooth DEM with σ=1.5 ft before slope |
| 5-ft smoothed | Gaussian-smooth with σ=2.5 ft |
| 10-ft plane fit | Least-squares plane through each 10×10 ft neighborhood |

**Expected behavior:**

| Scenario | 1-ft raw | 3-ft | 5-ft | 10-ft |
|----------|----------|------|------|-------|
| Real escarpment | High | Still high | High | High |
| Rim-break artifact | Very high | Moderate | Low | Very low |
| Pixel noise | Very high | Low | Very low | Near zero |
| Wall/structure | Very high isolated | Drops rapidly away from feature | Low | Very low |

If the >30° signal disappears at 3–5 ft smoothing, it is not a design-relevant landform.

---

## Test 3 — Robust slope statistics by band

**Method:** For each of the following zones:

| Zone | Azimuth range from focus | Radial range |
|------|--------------------------|-------------|
| S wall | az 165–195° | R 85–150 ft |
| SE corner | az 120–165° | R 85–150 ft |
| E flank | az 75–120° | R 85–150 ft |
| Upper E rim | az 75–120° | R 130–170 ft |
| Upper S rim | az 150–195° | R 130–170 ft |

**Statistics per zone per slope scale:**
- median slope (°)
- mean slope (°)
- 90th percentile slope (°)
- 95th percentile slope (°)
- maximum slope (°)
- width (ft) of slope > 25°
- width (ft) of slope > 30°
- connected-component area (sq ft) of cells > 30°

**Key question:** Is there a 30°+ zone on the east flank that is comparable in extent to anything on the S or SE wall? Or is the E flank demonstrably gentler?

---

## Test 4 — Persistence test (connected-component analysis)

**Method:** At each slope scale, identify all connected clusters of pixels exceeding 25° and 30°. For each cluster:
- Area (sq ft)
- Perimeter (ft)
- Centroid location
- Azimuth from bowl center

**Classification:**
- Coherent landform-scale band: area > 500 sq ft, elongated (length/width > 3:1), consistent azimuth → treat as real
- Narrow rim artifact: area < 100 sq ft, 1–2 pixels wide → artifact
- Isolated speckle: area < 50 sq ft, aspect-ratio near 1 → noise
- Linear feature near property edge: may indicate fence, wall, or curb → field verify

---

## Test 5 — Contour test

**Method:** Extract 1-ft and 2-ft contour lines from the DEM over the eastern rim zone. Measure contour spacing (inverse-proportional to slope):

- If contours are compressed (closely spaced) in the eastern rim zone and persist over 20+ ft of horizontal extent → real escarpment
- If contours show smooth, evenly spaced climb and flatten into the upper plateau → no escarpment; just a sloping bank
- If there is a single closely-spaced contour pair isolated within otherwise smooth spacing → artifact (one noisy elevation cell)

---

## Test 6 — Profile shape test

**For each transect (P1–P4):**

Classify the elevation curve shape:
- **Type A** — monotonically steepening toward the rim (suggests a retaining-wall or escarpment)
- **Type B** — roughly constant slope throughout (natural bowl bank)
- **Type C** — flattening toward the upper plateau (typical of natural slope rolling into level ground — no escarpment)

The prior assumption was that the east flank was Type A (steep near rim). The corrected hypothesis is that it is Type B or C (consistent bowl wall or gentle upper plateau). The profiles will determine which.

---

## Null hypothesis

**H₀:** The east flank is continuous with the S/SE bowl wall character — similar slope (~15–25°), no distinct 30°+ band, consistent gradual rise toward the upper plateau.

**H₁:** The east flank has a distinct 30°+ band near the rim that persists across all smoothing scales and multiple parallel transects, and represents a genuine design constraint.

The prior design implicitly assumed H₁ without testing. The burden of proof has shifted: H₁ must be demonstrated, not assumed.

---

## Execution

See `terrain_forensics.py` in this workspace for the full test implementation. Outputs are written to `outputs/` and figures to `figures/`.

Key output tables:
- `outputs/profile_table.csv` — per-station elevation and slope for P1–P4
- `outputs/slope_stats_by_zone.csv` — robust statistics by zone and scale
- `outputs/connected_components.csv` — >25° and >30° cluster properties
- `outputs/contour_spacing.csv` — contour spacing in eastern rim zone

Key figures:
- `figures/s_se_e_profile_comparison.png` — elevation + slope for P1–P4
- `figures/multiscale_slope_east.png` — 1/3/5/10 ft slope comparison
- `figures/connected_components_map.png` — >25° and >30° cluster map
- `figures/contour_test.png` — contour spacing in eastern zone
