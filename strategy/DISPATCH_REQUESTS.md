# STRAT → design-pipeline dispatch requests

Per P-1 (one viewshed truth): the strategy workstream never computes viewshed products.
Needs are filed here with full observer geometry, occluder sets, and leaf states; the
design pipeline (bay-band v2 machinery, `analysis/bay_view_obstruction/`) executes them.

---

## DR-1 — Tower-floor observer class (canopy-lever asymmetry test) · **FILED 2026-07-21 · OPEN**

**Assumption tested:** the canopy-lever asymmetry — that a hypothetical tower's upper
floors already clear the canopy (so de-treeing adds little to `V_up`'s view premium),
while removal substantially widens low-elevation bands (street receptors, amphitheater
rows). This is the half of the asymmetry test no v2 observer class covers; it prices the
pit owner's vertical option. Until this returns, the asymmetry is [assumption], qualified
by P-5's partial-lever facts.

**Observer set requested:**
- Plan positions: grid sampled across the buildable envelope of the pit parcel
  (GIS polygon `52-19-06-224-001` = tax PID 52-19-06-227-016 — see STRAT_FINDINGS F2;
  2.01 ac). [assumption: plate grid; ~25-ft spacing suggested, pipeline's choice — label it]
- Floors 2–8: plate at grade ~618 ft + 12 ft/floor; eyes +5 ft per plate →
  eye elevations 635 / 647 / 659 / 671 / 683 / 695 / 707 ft NAVD88 (floors 2→8).
- Bands per D1–D5: occluder sets S0 / S1 / S2, both leaf states, far-shore waterline
  band top (D3), corridor 318–342°.

**Verdict wanted:** per-floor water-band % with and without canopy (S1 vs S2, both leaf
states). **Asymmetry CONFIRMED** if canopy removal's band gain concentrates below
~floor 3–4 and at street/row receptors; **REFUTED** if upper floors gain comparably.

**Dependents blocked on this:** T-1 conclusion; T-8 per-floor view-premium pricing
(`V_up` bracket assumptions).

**Note for the pipeline:** floor-2 eyes (635 ft) sit almost exactly at the adopted S1
neighbor over-stage ceiling (635.4) — unrelated quantities, but a useful cross-check that
the receptor machinery is behaving.
