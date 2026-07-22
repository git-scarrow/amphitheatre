# STRAT → design-pipeline dispatch requests

Per P-1 (one viewshed truth): the strategy workstream never computes viewshed products.
Needs are filed here with full observer geometry, occluder sets, and leaf states; the
design pipeline (bay-band v2 machinery, `analysis/bay_view_obstruction/`) executes them.

---

## DR-1 — Tower-floor observer class (canopy-lever asymmetry test) · **FILED 2026-07-21 · ANSWERED 2026-07-22**

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

### ANSWERED — 2026-07-22 (design pipeline, gentoo) · **asymmetry CONFIRMED**

**Artifacts:** `analysis/bay_view_obstruction/dr1_tower_floors/` —
`DR1_ANSWER.md` (verdict + caveats), `dr1_per_position_bands.csv` (966 rows =
138 grid observers × 7 floors), `dr1_per_floor_summary.csv`/`.md` (median + IQR
per set), `dr1_summary.json`. Driver: `scripts/dr1_tower_floors.py`. Same bay-band
v2 basis as commit `4e6d03a` (D1–D5); analysis only, adopts nothing.

**Verdict (one paragraph):** The canopy-lever asymmetry is **CONFIRMED**. Over a
25-ft plate grid (138 observers) on parcel `52-19-06-224-001` (2.01 ac; grid an
[assumption]), canopy-removal bay-band gain (clear% S1 − S2) concentrates entirely
**below floor 4**: median gain **+53.8** at floor 2 (eye 635, leaf-on) and **+23.1**
at floor 3 (647), then **exactly 0.0 at floors 4–8** (659–707) in both leaf states —
those floors already clear the canopy (S2 = S1 = 100%). The crossover sits in the
predicted ~floor 3–4 band; upper floors do **not** gain, refuting the REFUTE test.
This matches the known low-elevation lever facts on the same S1/S2 basis: de-treeing
restores a water band to **106 of 184 street receptors** (72→178, D4) and lifts
seated rows up to **+84.6** (bend r11), while giving a tower's upper floors nothing.
Secondary finding: S0 = S1 = 100% at every floor including floor 2 — durable
occluders (pit rim, city roofs ≤~630 ft) never bind a tower eye ≥635 ft, so the
whole tower bay-view question reduces to the canopy, which bites only floors 2–3.
**Hand-back for T-8:** upper floors (4+) carry **no** canopy-removal `V_up` premium;
the de-treeing premium is a grade / floors-2–3 / street / seated-row asset. All S2
leeway is contingent (third-party canopy, leaf-off measurement / leaf-on assumption);
the floors-4+ result rests on **S1** and needs no trees.
