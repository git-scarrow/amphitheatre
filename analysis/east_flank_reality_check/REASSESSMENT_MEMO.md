# Petoskey Pit — Eastern Flank Reality Check and Design Space Reopening
## Reassessment Memo

**Compiled 2026-06-06. Planning-grade. NAVD88 intl ft, EPSG:6494.**
**DEM basis: `dem/dem_design_1ft.tif` (USGS LiDAR 2015 vintage, ±0.5–1 ft). Field verification required.**

---

## 1. What was wrong or over-assumed

### The "steep east escarpment" was 1-ft DEM pixel noise

Prior design work treated the east flank of the Petoskey Pit as a distinct zone with an implied or asserted 30° escarpment that constrained seating from extending east. This framing was never explicitly stated as a terrain measurement — it was embedded structurally in script parameters, stop conditions, and garden-zone designations. No surviving document presents a measured east-flank transect with a 30°+ slope at a design-relevant scale.

**Multi-scale slope analysis from `terrain_forensics.py` (2026-06-06) shows:**

| Zone | 1-ft raw p90 | 3-ft smooth p90 | 10-ft smooth p90 | Area >30° at 3-ft |
|------|-------------|----------------|-----------------|------------------|
| S_wall (az 165–195°, R 85–150 ft) | 27.9° | 22.1° | 21.5° | **0 sq ft** |
| SE_corner (az 120–165°, R 85–150 ft) | 28.6° | 21.6° | 21.2° | **0 sq ft** |
| **E_flank (az 75–120°, R 85–150 ft)** | **29.7°** | **20.7°** | **20.3°** | **0 sq ft** |
| upper_E_rim (az 75–120°, R 130–170 ft) | 28.3° | 20.4° | 20.0° | **0 sq ft** |
| upper_S_rim (az 150–195°, R 130–170 ft) | 23.7° | 20.7° | 20.4° | **0 sq ft** |

**Finding: The 30°+ signal in the 1-ft raw DEM disappears completely at 3-ft smoothing across all zones including the east flank.** There are zero square feet of >30° slope in any zone at 3-ft or 10-ft smoothing. The 30° pixels in the raw DEM are pure 1-ft pixel-scale artifacts — single-pixel elevation discontinuities, derivative noise, or micro-roughness from raw LiDAR returns.

The east flank (E_flank) has a 10-ft smooth median of **19.6°** and p90 of **20.3°** — essentially identical to the S_wall (20.2° median / 21.5° p90) and SE_corner (19.3° median / 21.2° p90).

### The "gentle east" framing was also wrong

Prior documents described the east flank as "gentle" and designated it as a "garden zone" (az 88–122°, in `scripts/stage5_grading.py`). This characterization was applied without measuring the east-flank slope. The data shows the east flank is **not gentle — it is the same ~20° bowl-wall character** as the south and SE seating bank.

The east side was simultaneously claimed to be "too steep for seating" (implied by stop conditions) and "gentle enough for a garden" (by the garden-zone designation). Both claims were wrong. The east flank is the same slope as the S/SE seating band — well-suited to contour-bay terraced seating.

### The retaining-wall claim was geometry-driven, not terrain-driven

The 6–14 ft retaining-wall figure from the original `/package` design arose from:
1. A narrow ±30° fan (60° total) that drove 30 rows straight up the S/SSE slope
2. Upper rows reaching the rim-flatten zone requiring fill
3. ADA Route B laterally bench-cutting into the steep upper wall

This was geometry-specific to that first design. It does not apply to:
- The current 16-row / open-arc budget baseline (confirmed: no walls needed)
- The corner-bays contour design (confirmed: no walls)
- Any future east-wrapped design using contour-bay geometry

### The "stop below the steep band" justification was unfounded

The current 16-row design stops at R≈130 ft "below the steep band." There is no steep band. The decision to stop at R=130 ft was a reasonable conservative choice for the budget baseline, but calling it terrain-constrained is incorrect. The terrain does not compel stopping there.

---

## 2. What the terrain now appears to say

**The S, SE, and E bowl walls form a continuous amphitheatre-grade bowl wall at approximately 20° (35% slope).**

This is consistent with the prior measured S/SE seating-band value of ~33% / ~18° — the slight discrepancy between ~18° (from median at R85–130) and ~20° (from zone median including areas up to R150) is expected as the bowl wall naturally varies.

**Specific terrain facts:**

| Fact | Source | Confidence |
|------|--------|-----------|
| S/SE seating bank ~30% avg (17–43% range) | Design scripts + seating-axis profile | High (measured) |
| E_flank same character as S/SE at design scale (~20° at 10-ft smooth) | terrain_forensics.py zone stats | High (measured) |
| No >30° zone persists at 3-ft smoothing anywhere | terrain_forensics.py connected-component analysis | High (measured) |
| 30°+ pixels at 1-ft raw are 1-pixel noise artifacts | Scale-comparison test | High |
| R 130–190 ft: same slope character as R85–130 (29–42%, avg ~30%) | User seating-axis DEM profile, 2026-06-06 | High (measured) |
| R 190–205 ft: terrain flattens to 7–16% then near-zero (upper plateau) | User seating-axis DEM profile | High (measured) |
| The 39–41% harness-flagged spikes are bumps, not an escarpment | User seating-axis DEM profile | Confirmed |
| Bowl floor ~609–610 ft | Design DEMs, consistent | High |
| Rim spill ~618 ft | Pour-point analysis | High |
| Seating arc center at EPSG:6494 (19533075.2, 750786.2) | design_open_low.py constants | Confirmed |

**Direct quote from seating-axis profile analysis (2026-06-06):**
> "There is no cliff. The hill doesn't do anything dramatic beyond row 16 that it wasn't already doing before it. R=130–190: slope continues at 29–42%. The same character as the seating zone."

**Interpretation (planning-grade, field verification required):**
The bowl has a continuous seating-grade bowl wall from the floor to approximately R=190 ft, where the terrain transitions to the upper plateau / Petoskey Street rim. There is no distinct east escarpment. The viable seating zone is approximately R85–190 ft — roughly twice what the current 16-row baseline uses. The east flank is available for seating using the same contour-bay geometry already proven.

---

## 3. What coordinate/directional language was corrected

**Key correction:** The east flank rises toward **Petoskey Street** (eastward), not toward "Lake/Mitchell Street." Lake Street is north; Mitchell Street is south. A west-to-east transect does not approach either.

**Required terminology going forward:**
- East flank / Petoskey Street flank — for the east side of the bowl
- Lake Street side — north edge only
- Mitchell Street side — south edge only
- Bayfront Park side / west side — western/open side

No explicit `Lake/Mitchell` conflation was found in existing files, but the guard is placed on all future documents.

---

## 4. What prior conclusions survive

| Prior conclusion | Status |
|-----------------|--------|
| S/SE seating bank ~33% / ~18° natural rake | **Survives — confirmed** |
| Stage forward (35 ft to row 1), bay-facing orientation (az ~330°) | **Survives — strong design decision** |
| Open-air landscape venue, no upstage wall | **Survives — design principle** |
| No retaining walls in the 16-row design geometry | **Survives — confirmed** |
| No fill import needed (cut-dominant site) | **Survives — confirmed** |
| ADA engineered ramps required (closed depression) | **Survives — confirmed** |
| Corner/contour-bay row geometry is better than circular arcs | **Survives — confirmed** |
| ~22–25 CY shallow fine-grading (design_corner_bays) | **Survives — confirmed** |
| Drainage cell at 609.1 ft / event floor 612.5 ft | **Survives — confirmed** |
| Bay-view screen is vegetation, not terrain | **Survives — confirmed** |
| All 988/988 per-seat sightlines pass | **Survives — confirmed** |
| ADA promenade fails ±0.12 ft gate (needs dedicated grading) | **Survives — open item** |

---

## 5. What conclusions must be reopened

| Prior conclusion | Why it must be reopened |
|----------------|------------------------|
| "Seating stops below the steep band" | No steep band exists; this was artifact-driven |
| "East flank is gentle" | E flank is ~20°, same as S/SE — not gentle |
| "Garden zone ENE 88–122°" | No terrain reason to designate east as garden vs. seating |
| "16 rows is the terrain-limited optimum" | 16 rows is the budget baseline; terrain supports more |
| "30° escarpment constrains east-wrap" | No 30° escarpment exists at design-relevant scale |
| "Retaining walls are unavoidable with east seating" | Retaining walls are design-preference, not terrain law |
| "East seating cannot use contour-bay method" | East flank is the same character → same method applies |

---

## 6. Design scenarios to test next

**Priority order (based on terrain confirmation):**

### Highest priority: Extend rows up the seating axis to R~190 ft (Scenario B / C)

**Terrain confirmed by direct profile (2026-06-06):** R130–190 ft has the same slope character as the current seating zone (29–42%, avg ~30%). The terrain flattens into the upper plateau at R~190–205 ft. This is the natural terminus.

Relax `DRDT_EAST` in `design_corner_bays.py`; remove the arbitrary R130 stop. Extend contour bays to R~150–190 ft. The harness's 39–41% spike warnings are bumps — same as what already exists in R85–130. Estimate: +170–470 seats, no walls, ~50–100 CY additional grading. **This is the immediate next design step.**

### Second: Continuous civic bowl at 150° fan (Scenario C-150)
A 150° seating fan (from ~az 80° to az 200°) covering S/SE/E is now geometrically supported. Estimate: ~1,500–1,700 seats, moderate earthwork (~60–100 CY), no walls assumed.

### Third: Petoskey Street rim terrace / overlook (Scenario D)
The upper eastern plateau (R130–170, confirmed ~20°) can host a civic arrival terrace at the Petoskey Street edge. No escarpment means this is a simple grading and paving task. Low architectural terrace walls (1–2 ft) may define the edge.

### Fourth: Net-zero rebalance (Scenario G)
With confidence that the east flank is bowl-wall grade, a net-zero earthwork study is feasible: cut from steeper rim zones, use fill for ADA landings, promenade, and stage-area improvements.

**Architectural walls are back in play.** Low (1–4 ft) seat walls and terrace walls are design vocabulary, not emergency geotechnical fixes. They should be evaluated on their civic-quality merits.

---

## 7. Files created

All in `analysis/east_flank_reality_check/`:

| File | Content |
|------|---------|
| `coordinate_correction.md` | Street-name and azimuth corrections; invalid phrasings removed |
| `assumption_audit.md` | 18 prior claims classified A–F with replacements |
| `terrain_reality_summary.md` | Corrected terrain narrative and knowledge-type separation |
| `retaining_wall_origin_audit.md` | Where the 6–14 ft claim came from; 8 questions answered |
| `slope_artifact_tests.md` | Test specifications; all 6 tests defined |
| `design_implications.md` | What changes, what doesn't; scoring framework |
| `candidate_next_step_scenarios.md` | 7 scenarios A–G with metrics |
| `readme_replacement_text.md` | Draft replacement text for README.md, seat_count.md, etc. |
| `field_verification_checklist.md` | 15 field items in 3 priority tiers |
| `terrain_forensics.py` | Multi-scale slope analysis script |
| `outputs/slope_stats_by_zone.csv` | 20-row zone statistics at 4 scales |
| `outputs/connected_components.csv` | >25°/>30° cluster analysis |
| `outputs/profile_table.csv` | Per-station elevation + slope, 7 profiles |
| `figures/s_se_e_profile_comparison.png` | S/SE/E elevation + slope profiles |
| `figures/multiscale_slope_east.png` | East transect at 4 smoothing scales |
| `figures/connected_components_map.png` | >25° and >30° cell map at 1-ft and 3-ft |
| `figures/east_parallel_profiles.png` | East + offset profiles |
| `figures/site_orientation_diagram.png` | Corrected orientation (N/S/E/W street labels) |
| `figures/zone_slope_statistics.png` | Bar charts of p90 and >30° area by zone |

---

## 8. Field data needed before design lock

**Minimum before extending seating east:**
1. RTK or total-station transect across the east bowl wall (R80–160, az ~90°)
2. Parallel transects at ±10 ft north and south of the centerline
3. Condition photos from Petoskey Street looking west into the bowl

**Minimum before designing a Petoskey Street terrace:**
4. Property boundary survey (PLS, ALTA) confirming the upper plateau is within city ownership
5. Petoskey Street ROW location and sidewalk tie-in confirmation

**Immediately actionable (no professional required):**
6. Site walkthrough from all four street approaches with photos
7. Documentation of any fence, wall, or curb remnants on the east rim (the likely source of isolated 1-ft DEM spikes)

**Before any PE-stamp:**
- RTK design-grade topographic survey (replaces LiDAR as design control)
- Geotechnical investigation (borings, slope stability, infiltration)
- Full gating dossier items as specified in `gating_dossier.md`

---

## Key quotation (for use in design documents going forward)

> "The S, SE, and E flanks form a continuous amphitheatre-grade bowl wall at approximately 20° slope (measured by multi-scale DEM analysis, confirmed free of 30°+ zones at 3-ft and 10-ft smoothing scales). The east flank is not an escarpment. The 16-row design is the budget baseline, not the terrain limit. East-wrap seating is available to test; the terrain supports it."

---

*Planning-grade. Not stamped engineering. Field verification required before design lock. The gating items in `gating_dossier.md` still govern before construction.*
