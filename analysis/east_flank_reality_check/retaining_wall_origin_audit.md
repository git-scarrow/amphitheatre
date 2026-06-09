# Retaining Wall Origin Audit
## Petoskey Pit — East Flank Reality Check

**Compiled 2026-06-06. Planning-grade.**

---

## Question 1: What geometry produced the 6–14 ft retaining-wall claim?

The 6–14 ft retaining-wall claim originated in **Stage 5 (`scripts/stage5_grading.py`)** of the original `/package` design. That design used:

- 30 terraced rows
- ±30° (60° total) fan
- Seating from R≈85 to R≈172 ft along the **S/SSE centerline (az 150°)**
- The upper rows (25–30) extended into the zone where the terrain begins to flatten near the 618-ft rim, requiring fill to maintain sightlines
- The design assumed a `D_MAX = 30 ft` tie-in apron beyond which a retaining wall would be needed rather than a graded 3:1 slope

The gating dossier C-3 describes the result: "Tie-in/ramp cuts reach **6–14 ft over ~0.083 ac**; flagged as **structural retaining walls**, not earth slopes." The ADA Route B accounted for ~28% of this figure as it bench-cut into the steep wall.

**Key geometry driver:** The narrow ±30° fan concentrated all seating directly up the S/SSE fall line. Row ends terminated near the steep upper wall zone because the fan was too narrow to wrap around and use shallower flanks. The tall upper rows and the ADA Route B cuts into the steep wall generated the 6–14 ft figure.

---

## Question 2: Did that geometry depend on a narrow ±30° fan and 30-row climb?

**Yes, entirely.** The 30-row, ±30° geometry:
- Required rows to climb ~30 ft of vertical (vs. 15 ft in the current 16-row design)
- Required rows to extend to R≈172 ft, reaching the rim-flatten zone where terrain flattens and fill is needed
- Concentrated the upper rows in the steepest part of the wall
- Forced ADA Route B to cut laterally across the steep wall at elevation

The current **16-row / open-arc design avoids this entirely** by stopping at R≈130 ft and opening the fan to ±55°. The retaining-wall claim does not transfer to this geometry.

---

## Question 3: Did the claim depend on the "steep band" / "30° escarpment"?

**Partially.** The retaining-wall concern has two components:

1. **The seating-row geometry** — the upper rows of the 30-row scheme needed flat treads in a zone where the natural terrain flattens/rolls. That is real regardless of whether the exact slope is 25° or 30°. Even a 20° rim-rollover with fill on top can require a retaining wall if the cut depth is large. *This component is geometry-driven, not escarpment-driven.*

2. **The ADA Route B lateral cut** — to cross the bowl at mid-height required cutting into the bowl wall. The depth of cut depends on the actual terrain slope. If the east flank is the same character as the S/SE slope (~33%/18°), a lateral ADA cut there would be similar in depth. *This component would scale with the actual terrain slope, not specifically a 30° escarpment.*

**The "steep band" / "escarpment" framing is not what drove the 6–14 ft number.** The number was driven by the first design's geometry. Calling it a "30° escarpment" was a description attached after the fact, not a geometric precondition.

---

## Question 4: Does the retaining-wall claim apply to the current 16-row design?

**No.** The current `design_open_low` and `design_corner_bays` designs both document **no retaining walls** for their respective geometries. The 6–14 ft figure is from the superseded first design. The current 16-row schemes stop at R≈130 ft, well within the S/SE seating band, where the terrain rake is consistent and no rim-flatten fill or deep ADA cut is required.

---

## Question 5: Does it necessarily apply to east-wrapped seating?

**Not necessarily.** Whether east-wrapped seating triggers retaining walls depends on:

- The actual slope of the east flank (currently unverified)
- Where seating rows terminate on the east side
- Whether rows end cleanly at an aisle or require a deep cut into the east rim
- Whether ADA routes need to cross the east flank at mid-height

If the east flank is the same bowl-wall character as the S/SE seating bank (~33%/18°), east-wrapped seating can use the same row geometry — contour-aligned bays with shallow fine-grading and no retaining walls.

If the east rim has a genuine step or wall remnant near Petoskey Street, a modest retaining wall might be appropriate at that specific transition — but that is an architectural terrace element, not a design-wide constraint.

---

## Question 6: Does it necessarily apply to a broader civic-bowl design?

**No.** A broader civic bowl (S/SE/E seating arc) that follows the bowl contour geometry does not inherently require retaining walls. The `design_corner_bays.py` scheme already extends onto the east flank with contour-aligned bays and no walls. The key conditions for avoiding walls are:
- Row stops within the natural bowl landform (not at the rim crest)
- Contour-aligned or near-contour rows (no deep cross-grade cuts)
- ADA routes designed with dedicated grading, not lateral rim cuts

---

## Question 7: What conditions would actually trigger retaining walls?

| Condition | Trigger level | Notes |
|-----------|--------------|-------|
| Row stop in a rim-flatten zone with fill > ~2–3 ft | Would need retained fill | Avoid by stopping below the rim-flatten zone |
| ADA lateral ramp cut into the bowl wall > ~4 ft deep | Structural retaining likely | Use switchback ramps on approach grades instead |
| Rows must maintain a flat tread across a slope > ~40% | Cut depth per tread exceeds 1 ft/row → cumulative step walls | Use contour-following bays instead |
| East rim contains a legacy retaining wall / structure | May need integration or replacement | Field survey required |
| Row-end termination requires a vertical step > ~3 ft | Low seat wall or terrace wall practical | This is an architectural element, not a failure mode |
| Petoskey Street rim terrace desired | Low (~1–3 ft) architectural terrace wall | Useful as a civic edge — not a cost emergency |

---

## Question 8: Could low walls be useful as architectural terrace elements?

**Yes, and this framing shift is important.** A 1–4 ft terrace or seat wall at the upper rim of the east flank, or at the Petoskey Street promenade edge, would:
- Define the upper civic edge without requiring large earthwork
- Create a legible seating terrace / promenade transition
- Handle minor grade changes at the property boundary
- Support drainage management at the upper rim
- Provide accessible seating at the top of the bowl

This is standard amphitheatre practice (stone terraces at Epidaurus; concrete terrace walls at Merriweather, Wolf Trap, etc.). Treating a 2-ft terrace wall as "failure" understates the design vocabulary available.

**Recommendation:** Reframe retaining walls on a scale:
- **0 ft** — pure earthwork, no wall (current design baseline)
- **1–2 ft** — architectural terrace / seat wall (useful civic element)
- **2–4 ft** — low retaining wall (normal, cost-modest)
- **4–8 ft** — medium retaining wall (increased structural requirement; requires geotech)
- **8–14 ft** — tall retaining wall (the original first-design cost driver; flag and minimize)

The prior framing treated any wall as equivalent to the 8–14 ft extreme. That is not accurate.

---

## Conclusion

The retaining-wall claim in the project record originated from a specific, superseded design geometry. It does not transfer to:
- The current 16-row design (confirmed: no walls)
- The corner-bays contour-aligned design (confirmed: no walls)
- East-wrapped seating using the same contour-bay approach (likely no walls, pending terrain forensics)
- Modest civic terrace walls at the Petoskey Street rim (useful design tool, not a constraint)

**"Avoid retaining walls" remains a valid cost preference, not a terrain law.** Modest architectural walls that improve the civic quality, drainage, or accessibility of the east rim should be evaluated on their merits, not reflexively avoided.
