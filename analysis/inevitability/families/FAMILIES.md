# Generated design families — composed from the affordance map, self-critiqued

_`scripts/generate_designs.py`: the Composer writes one Design per family from the site affordance map + Scenario-B validation; the InevitabilityEngine grades each._

All families ride the same latent bowl (rake rises 27.3%/ft, hinge R≈68.0 ft, bay axis 330.0°). They differ in where the formal/lawn line falls and which access/drainage/framing surfaces are composed.

| Family | Verdict | Inev | Done | Formal | Lawn | Restore CY | Stage | Character |
|---|---|---:|---:|---:|---:|---:|---|---|
| **processional_bowl** | ✅ accept | 14.91 | 10/10 | 1452 | 443 | 25.9 | concept | Civic bowl whose access route + landings are the composition. |
| **stormwater_garden_bowl** | ✅ accept | 14.91 | 10/10 | 1452 | 443 | 25.9 | concept | Civic bowl where swales/treatment cell are a designed garden edge. |
| **civic_bowl** | ✅ accept | 14.54 | 10/10 | 1452 | 443 | 25.9 | concept | Maximal formal lower bowl — the Scenario D baseline. |
| **ceremonial_bay_bowl** | ✅ accept | 14.41 | 10/10 | 1452 | 443 | 25.9 | concept | Civic bowl with lateral stage framing that protects the bay axis. |
| **meadow_bowl** | ✅ accept | 14.68 | 10/10 | 831 | 1064 | 12.4 | concept | Formal lower rows, the rest dissolved to lawn terraces. |
| **neighborhood_daily_bowl** | ✅ accept | 15.34 | 10/10 | 652 | 1243 | 8.8 | concept | Daily-use commons: smaller formal core, paths + drainage gardens. |
| **festival_bowl** | ✅ accept | 15.08 | 10/10 | 652 | 1243 | 8.8 | concept | Compact formal core + wide flexible lawn, with festival circulation. |
| **minimal_intervention_bowl** | ✅ accept | 14.75 | 10/10 | 483 | 1412 | 5.1 | concept | Restore only the rows needed to read as a bowl; lawn above. |

## Reading

- **processional_bowl** ranks first by civic value at near-zero earthwork — all formal capacity is *restoration of the latent bowl*, not imposed grading.
- **Every composed family is `concept`** — its access/drainage/framing moves are INTENT (no polygons yet), which lift concept ranking but cannot satisfy a cost-proxy gate. Reaching `cost_proxy` requires the Scenario E geometry emitter to draw real ADA/cross-aisle/swale surfaces and pass validation on them (`SCENARIO_E_CIVIC.md`). The engine enforces this: a cost-proxy claim backed only by intent moves is hard-rejected.
- No family counts formal seats on clipped/dished tread — the composer only promotes a row to formal when its *ideal* plane passes all gates, and spends the restoration CY to earn it.
- These are different characters, not one optimum at different prices: a planner picks by civic intent (max formal vs. meadow vs. festival vs. daily-use), then Scenario E makes it costable.

Per-family move ledgers: `analysis/inevitability/families/<family>.json`.
