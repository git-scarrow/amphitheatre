# Assumption Audit — Eastern Flank Claims
## Petoskey Pit — East Flank Reality Check

**Compiled 2026-06-06. Planning-grade. Classifications are advisory.**

Classification key:
- **A** — still valid
- **B** — needs qualification
- **C** — likely false / artifact-driven
- **D** — true only for the prior narrow 30-row design
- **E** — design preference, not terrain fact
- **F** — coordinate / directional error

---

## Audit table

| # | Quoted language | Source file | Class | Reason | Proposed replacement |
|---|----------------|-------------|-------|--------|---------------------|
| 1 | "30 terraced rows, ±30° fan … up the steep S/SSE wall, which forces rim-flatten fill and **6–14 ft structural retaining walls** (the bulk of its cost)" | `design_open_low/README.md` line 18 | **D** | This describes the original `/package` design (30 rows, ±30°), not the current scheme. The retaining-wall claim was geometry-driven by that specific narrow fan and row count. | Retain as a description of the deprecated first scheme; label clearly as "original design, superseded." |
| 2 | "stop low at **16 rows / R 130 ft**, *below* the rim-flatten + retaining band" | `design_open_low/README.md` line 19 | **B/C** | "Below the rim-flatten + retaining band" treats the steep rim as a hard terrain constraint. This may be an artifact of the 1-ft DEM slope spikes near the eastern rim. Requires multi-scale slope verification. | "Stop at 16 rows / R 130 ft as the low-intervention budget baseline; whether the rim requires retaining walls is subject to terrain forensics and field survey." |
| 3 | "the bowl's S/SE wall **is already a ~33% natural rake (~18°)**" | `design_open_low/README.md` | **A** | Supported by DEM profiles; ~33% / ~18° is consistent with the measured seating band R85–130. | No change needed. |
| 4 | "gentler than Epidaurus' ~26°" | `design_open_low/README.md` | **A** | Accurate comparison at the S/SE seating band elevation. | No change needed. |
| 5 | "**the bowl's S/SE wall** … [distinct from east]" | Multiple files — `design_open_low/README.md`, `executive_summary.md`, `scripts/stage4_amphitheater.py` | **B** | The framing implies S and SE are the seating wall and east is something else ("gentle garden flank"). Prior DEM profiles suggest S, SE, and E may be a continuous bowl wall. The distinction is unproven. | "The S, SE, and E flanks appear to form a continuous bowl wall. Prior characterization of the east flank as distinctly gentler is unverified; see terrain forensics." |
| 6 | "**30° escarpment**" (implied in stopping criteria and retaining-wall discussion) | `scripts/design_civic_contour.py` line 42: `R_SCAN_MAX=150.0; E_CAP=629.5 # stay below the steep band (~R155)` | **C** | The `# stay below the steep band` comment treats the steep band as an established fact. Raw 1-ft DEM slope spikes near the rim are unverified at multi-scale. | Remove or soften: "R_SCAN_MAX=150.0; E_CAP=629.5  # conservative upper limit pending terrain forensics" |
| 7 | "the steep SE/SSE wall" (gating item C-3) | `gating_dossier.md` line 39 | **B** | The geotech flag is real and appropriate for the S/SSE seating zone. However "steep SE/SSE wall" should not be extended to the east flank without evidence. | Retain C-3 as written for S/SSE zone; add note that east flank characterization is unverified. |
| 8 | "**SE/SSE wall retaining + slope stability (REQUIRED follow-up)**. Tie-in/ramp cuts reach **6–14 ft over ~0.083 ac** against the steep wall" | `DATA_GAPS.md` line 150 | **D** | Arose from the original 30-row, ±30° design geometry and the ~72% perimeter tie-in of that scheme. Does not necessarily apply to the current 16-row or any east-wrapped design. | "Retaining-wall risk is geometry-dependent. Re-evaluate against actual proposed scheme geometry. The 6–14 ft figure is from the first design." |
| 9 | "**garden ring on the gentle east and open bayward flanks**" | `executive_summary.md` line 18; `package/executive_summary.md` | **B/C** | "Gentle east flank" is an assertion that the east flank is characteristically lower-slope than the S/SE seating wall. This has not been confirmed by multi-scale slope analysis. | "garden ring on the east and bayward flanks (east-flank slope character pending verification)" |
| 10 | "**East garden terraces (5 benches, ENE flank az 88–122°, r 95–215 ft)** were designed in Stage 5" | `DATA_GAPS.md` line 155 | **B** | Treating the ENE sector only as "garden" (not seating) was predicated on the east side being too gentle for formal seating rows or too steep for safe rows — neither has been confirmed. | "East garden terraces are placeholders. The ENE/east flank should be evaluated for seating potential before committing to a garden-only treatment." |
| 11 | `DRDT_EAST=0.7 # retention stop-cap on the east/hook flank` | `scripts/design_civic_bowl.py` line 44 | **E** | A script parameter controlling how far the contour-bowl row extends onto the east flank. Value = design choice, not terrain-proven limit. | "DRDT_EAST = design preference; revisit for east-wrap scenarios." |
| 12 | "flank policy is ASYMMETRIC: the east flank (the contour 'hook', +X) is capped" | `scripts/design_civic_bowl.py` line 17 | **E** | Design choice driven by aesthetic preference for a regularized crescent, not by a proven terrain limit. | "Asymmetric flank cap is a design choice; east-wrap scenarios should test relaxing this constraint." |
| 13 | "Slope/aspect recompute on a canonical AOI (south/SE arc steepness, **east-slope gentleness**)" | `DATA_GAPS.md` line 123 | **B** | The data-gaps list flags this as still open. "east-slope gentleness" is a hypothesis, not a confirmed fact. | "Slope/aspect recompute on a canonical AOI (south/SE arc steepness; **east flank slope character — unverified, may be continuous with S/SE wall**)" |
| 14 | `GARDEN_AZ = (88.0, 122.0)  # ENE..SE-of-east, between bay flank and seating` | `scripts/stage5_grading.py` line 132 | **E** | Design choice that pre-committed the ENE sector to garden use. Not terrain-mandated. | "GARDEN_AZ = provisional. East-sector seating scenarios should test replacing garden with terraced seating." |
| 15 | "seating centerline az = 150 deg (SSE); fan spans the **steep S-SE arc**" | `scripts/stage4_amphitheater.py` lines 13 | **D** | Describes the first (rejected) scheme. The steep S-SE characterization was correct for that scheme's seating band but should not be extended to the current multi-bay design without re-verification. | Label as first-scheme description. |
| 16 | "SE steep-wall geotech check" | `scripts/stage5_verify_plot.py` line 2, 36 | **B** | Geotech check framing is legitimate; "steep SE wall" should not be assumed to extend to east flank without evidence. | "SE/SSE steep-wall geotech check; east flank character pending forensics" |
| 17 | "~R155 steep band" (implied hard stop) | `scripts/design_civic_contour.py` line 42 comment | **C** | The ~R155 comment treats the steep band as an established spatial limit. Multi-scale analysis needed to confirm whether this is a real landform or a 1-ft raster artifact. | "R_SCAN_MAX=150 — provisional stop; terrain forensics needed to confirm or relax this." |
| 18 | "no retaining walls (ends ~11 ft below the steep band)" | `design_open_low/seat_count.md` | **B** | The "steep band" is not independently proven. The no-retaining-walls result is valid for the current 16-row design geometry, but the framing implies the steep band is what forced the stop. | "no retaining walls — 16-row design geometry does not require them; whether a taller/wider scheme would require them depends on unconfirmed terrain character at the upper rim." |

---

## Summary by classification

| Class | Count | Notes |
|-------|-------|-------|
| A — still valid | 2 | 33% rake at seating band; Epidaurus comparison |
| B — needs qualification | 8 | Most require "pending terrain forensics" qualifications |
| C — likely false / artifact-driven | 3 | Steep-band stop criteria; east-flank "gentleness"; `~R155` hard stop |
| D — true for first design only | 3 | 6–14 ft retaining walls; 30-row geometry references |
| E — design preference | 4 | DRDT_EAST cap; asymmetric policy; GARDEN_AZ; stage-5 garden terraces |
| F — coordinate error | 0 | No explicit `Lake/Mitchell` conflation found (guard for future docs) |

**No existing file explicitly says "east escarpment" or "east steep band" as a primary claim.** The assumption is embedded structurally in stop-cap parameters, garden-zone designations, and the framing of the low design as stopping "below the steep band." These are class C/E assumptions that were never independently tested.
