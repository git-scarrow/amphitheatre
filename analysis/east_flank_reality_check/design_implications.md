# Design Implications of the Corrected Framing
## Petoskey Pit — East Flank Reality Check

**Compiled 2026-06-06. Planning-grade.**

---

## What changes if the east flank is a continuous bowl wall

If terrain forensics confirm that the east flank is continuous with the S/SE bowl wall — similar slope character, no 30°+ escarpment — the following design changes become appropriate:

### 1. The 16-row design is a budget baseline, not a terrain limit

The current `design_open_low` and `design_corner_bays` designs are valid low-intervention options. Their stopping point (R≈130 ft, 16 rows) should be documented as:
- **A cost and simplicity choice** — the minimum work to deliver a functioning amphitheatre
- **Not a terrain boundary** — the terrain does not force a stop at R130; the design chose to stop there

Removing "below the steep band" language from the design READMEs is necessary for accurate communication to the next engineering team.

### 2. East-wrap seating is available to test

The east flank can be tested as additional seating using the same contour-bay method already proven in `design_corner_bays.py`. The existing east-flank bay geometry in that script already reaches into the east sector (az<118°, R85–150 ft). An east-wrap scenario simply extends that logic further toward Petoskey Street.

Potential gains:
- Additional 150–400 seats (planning estimate — depends on wrap angle and row count)
- More equitable sightlines across a broader arc
- Better acoustic coverage
- Stronger civic presence from the Petoskey Street / east approach

Risks to test:
- Row-end cross-slope on the east flank (tested by forensics)
- ADA accessibility to east-sector seats
- Drainage from the upper eastern plateau toward seating rows
- View quality: east-sector seats may face slightly more toward the stage than toward the bay

### 3. The Petoskey Street rim becomes a civic design opportunity

If the upper eastern plateau is accessible and relatively flat, the Petoskey Street rim can function as:
- A public arrival terrace / civic overlook
- An accessible entry point from Petoskey Street (reducing reliance on Lake/Mitchell approaches)
- A location for a restroom/service kiosk, shade structure, or small pavilion
- A promenade connecting north (Lake Street) and south (Mitchell Street) sides

This is consistent with the existing ADA-route design intention (Route B is a mid-bowl accessible entry). A Petoskey Street terrace extends this logic to the upper bowl.

### 4. Row geometry rules must change

The existing scripts stop rows at R≈130 ft or use `DRDT_EAST=0.7` as a hard cap. Direct seating-axis profile measurement (2026-06-06) shows:

- **R 85–130 ft (current 16 rows):** slope 17–43%, avg ~30%. Normal seating terrain.
- **R 130–190 ft (rows 17–35+):** slope 29–42%, avg ~30%. **Same character. No change.**
- **R 190–205 ft:** terrain flattens to 7–16% → near zero. Upper plateau / Petoskey Street rim.

The viable seating zone is approximately R85–190 ft. The harness's 39–41% spike flags are bumps within the normal seating-band character — the same irregularities exist in R85–130 and don't stop rows there.

The row stop condition should be: **"Stop where sightlines, ADA access, cross-slope, drainage, row overlap, constructability, cost, or aesthetics fail. The natural terminus is the upper plateau at R~190–205 ft."**

NOT: "Stop where the east side becomes steep" — there is no such point.

**Harness change needed:** the `cut_bench max_cut_ft` warning in `scripts/harness/scenarios.py` and the `DRDT_EAST=0.7` cap in `design_civic_bowl.py` should not trigger retaining-wall or stop flags on slope spikes that are within the already-accepted seating-zone character.

Row families to test:
1. Extended circular arcs (current method, wider fan)
2. Contour-following bays (existing method, extended range)
3. Segmented rows with clean east-end termination at an aisle or promenade
4. Hybrid: formal contour bays on S/SE + lawn/terrace side seating on E/Petoskey flank

### 5. Earthwork transparency improves

If the east flank does not require retaining walls, the prior cost concern about eastward expansion largely dissolves. The design can be evaluated on:
- Shallow fine-grading (the honest metric from `design_corner_bays`)
- Cut volume for the stage/orchestra pad
- Drainage shaping
- ADA ramp earthwork

Without the retaining-wall premium, east seating is very likely lower cost per seat than the original first design.

---

## What does not change regardless of east-flank character

1. **Stage position and orientation** — stage forward (R≈35 ft to row 1), facing az≈315–330 toward the bay. This is a strong design decision independent of east-flank character.

2. **Bay-view axis** — the open NW backdrop (bay + sky) is the setting. Nothing about east-flank seating changes this.

3. **Drainage system** — the bowl bottom at 609.1 ft as a treatment cell, controlled outlet, emergency spillway at 612.0 ft. These are stormwater design decisions that are independent.

4. **Open-air character** — no upstage wall, no enclosure. This is a landscape venue principle, not an east-flank question.

5. **ADA route requirement** — the bowl is a closed depression with a rim; engineered ramps are required regardless of east-flank character. The east flank may offer a shorter/shallower approach than the S/SE wall, which is a benefit if confirmed.

6. **Planning-grade status** — no field data changes this. DEM-based forensics improve the quality of terrain analysis but do not replace field survey (RTK/total-station), geotech borings, or PE-stamped design.

---

## Scoring framework for east-wrap scenarios

Each scenario in `candidate_next_step_scenarios.md` will be evaluated on:

| Criterion | Description | Weight |
|-----------|-------------|--------|
| Seat count | Additional formal seats beyond current 1,127 | High |
| Row quality | Cross-slope, level, sightlines | High |
| ADA dispersion | Wheelchair spaces distributed through east sector | Medium |
| Earthwork | Shallow grading only vs. walls / import | High |
| Civic quality | Petoskey Street arrival, view, promenade | High |
| Bay-view preservation | Rows in E sector maintain northern sight angle to bay | Medium |
| Construction complexity | Grading, drainage, staging | Medium |
| Cost tier | Budget / moderate / major | High |
