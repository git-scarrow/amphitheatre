# ADA Concept C vs Concept D — naturalistic promenade vs constructed cut

**Date:** 2026-06-12 · **Engine:** `scripts/design_constructed_ada.py`
(runs AFTER `design_ada_routes.py`; merges the `concepts` block into
`analysis/ada_rebuild/ada_validation.json`).
**Corridors:** `route_corridors_C.geojson` / `route_corridors_D.geojson`
(both are SURFACES — centerline + width + station profile + grading; a
centerline is not an ADA route). **Grade delta raster:**
`dem/proposed_ada_grade_delta_D.tif` (preferred D).
**Label everywhere:** *planning/concept-grade accessible route pending civil/code determination*
— no concept is called compliant.

## The question

Stage 2 (Concept C) follows what the landscape gives: perimeter sloped
walks, ≤4.2% primary arrivals, zero seats touched. Is that good enough, or
should the amphitheater be **reshaped** by a constructed accessible route
that buys directness with intentional cut, walls, and displaced seats?

## The terrain bound (the most important number)

A compliant route cannot be shorter than drop ÷ 8.33%. From the east
arrival (crest 639.4) that means:

| target | desire line | minimum compliant route | **floor on detour ratio** |
|---|---|---|---|
| cross-aisle | 52 ft | 209 ft | **4.0** |
| cross-aisle wheelchair cluster | 43 ft | 209 ft | **4.9** |
| event floor | 90 ft | 323 ft | **3.6** |
| floor wheelchair cluster | 86 ft | 323 ft | **3.7** |

**No construction can make this bowl "direct."** Every concept — however
much it cuts — lands at ≥4× the stair desire line. The C-vs-D decision is
therefore about a *bounded* improvement (worst pair ~9× → ~5×), not about
reaching parity.

## The ledger

| | **C naturalistic** | **D1 integrated aisle-ramp** | **D2 diagonal terrace cut** | **D3 hybrid** |
|---|---|---|---|---|
| concept | perimeter sloped walks + west park floor walk | switchback stacks ON the east hinge: arrival→aisle→floor on one central line | 215-ft two-leg 8.1% diagonal across rows 11–18 to the cluster + park floor walk | D1's upper stack + park floor walk |
| network length | 1,508 ft | 1,400 ft | 1,188 ft | 1,460 ft |
| ramp runs / landings | 0 runs on primary (walks ≤4.2%) | 11 runs / 9 landings (5×5 ft) | 2 runs / 1 landing | 7 runs / 6 landings |
| max running slope | 4.2% primary / 6.2% egress | 8.33% runs | 8.26% | 8.33% runs |
| detour: aisle cluster | **8.95** | 6.76 | **5.04** | 6.76 |
| detour: floor | 4.21 (park) | 5.11 | 4.21 (park) | 4.21 (park) |
| seats displaced | **0** | **158** (12%) | **121** (9%) | **95** (7%) |
| rows severed mid-tread | 0 | 0 (widens the existing hinge aisle) | **2** (bend r11, r16 → dead-end segments) | 0 |
| cut / fill | bench-only (in C corridors) | 126 / 87 CY, max cut 5.4 ft | 62 / 162 CY (raised walled causeway, 79 wall stations) | 90 / 52 CY |
| post-grading cross-slope | designed 1.5% (1:48 OK) | designed 1.5% | designed 1.5% | designed 1.5% |
| treatment cell / swale | 0 / declared crossings | 0 / 0 | 0 / 0 (park leg crossing reused) | 0 / 0 |
| sightline / stage impact | none | guard walls beside hinge — C-value restudy of adjacent seats | **railed causeway crossing the fan's visual field**; restudy required | hinge guards — restudy required |
| dignity/directness score | **16** | 67 | **79** | 67 |

Dignity rubric (documented heuristic, not code): 100 − 12·(worst served
detour − 1.5), −15 perimeter-only character, +10 shared arrival, +10
in-bowl delivery, +10 cluster/companion integration. C scores low because
its perimeter walks are long *and* read as going around the building; D
concepts deliver users into the bowl with everyone else.

**Gate note:** an earlier D2 draft collapsed to a 45-ft / 39% "ramp" and
scored detour 1.06 — the new constructed-grade gate now zeroes any concept
whose built elements exceed 8.33%, so that class of error fails loudly.

## Recommendation

**Concept C governs the amphitheater plan.** Preferred D = **D2**, carried
as the design-development alternative — not adopted.

### Owner adoption

Owner adoption: **Concept C** — naturalistic promenade, recorded 2026-07-18.
Decision status is adopted. Implementation remains planning-grade pending civil/code
detailing; this record does not assert ADA compliance.

Decision rule (documented in `ada_validation.json`): D governs only if it
beats C on dignity by ≥20 points AND displaces <60 seats (<5%) AND severs
no row mid-tread. D2 beats C on dignity by 63 points **but** displaces 121
seats and severs two rows into dead-end segments, and its 162 CY raised
causeway draws a railed line across the bowl's visual field that the
user-experience score does not price.

Why this is the right call at planning grade:

1. **The terrain bound caps the prize.** D2's best pairs (4.4–5.0) sit
   near the theoretical floor (4.0–4.9) — but C's floor access via the
   west park walk already achieves 4.2. The only big win D offers is the
   cross-aisle pair (9.0 → 5.0), and it costs ~9% of capacity plus
   severance plus the causeway.
2. **C's costs are reversible; D's are not.** Adopting C leaves every D
   option open. Cutting the fan forecloses seating that the validated
   tier options (+114/+262 seats) are meanwhile trying to add.
3. **D2's path to adoption is explicit, not closed:** realign to convert
   the two severances into end-shortenings, pass an adjacent-seat C-value
   study of the causeway guard line, and re-run the rule. If a future
   program decision values the cross-aisle dignity gain over ~100 seats,
   D2 is drawn, costed, and ready.

**Remaining gaps for every concept:** surface material, edge protection
details, handrails/guards, drainage at runs and landings, lighting, field
cross-slope QA, §221 dispersion counts — see
`ada_validation.json:unchecked_code_details`. Concept C additionally needs
its corridor benching sections resolved before any compliance language.

## Reproduce

```
.venv/bin/python scripts/rebuild_ada_routes.py      # stage 1 feasibility
.venv/bin/python scripts/design_ada_routes.py       # Concept C (stage 2)
.venv/bin/python scripts/design_constructed_ada.py  # Concept D + verdict
.venv/bin/python scripts/build_truth_package.py
.venv/bin/python scripts/audit_in_situ_package.py
```
