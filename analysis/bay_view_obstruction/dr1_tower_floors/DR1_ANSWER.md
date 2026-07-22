# DR-1 — Tower-floor observer class · **ANSWER: asymmetry CONFIRMED**

**Filed:** STRAT 2026-07-21 · **Executed:** design pipeline (gentoo), 2026-07-22 ·
branch `stage/rule9-path1-audience-axis`.
**Basis:** bay-band v2 machinery at commit `4e6d03a` — identical occluder sets
(D2), effective-silhouette definition (D1), far-shore band top (D3), and corridor
as the adopted seated-row product. Driver: `scripts/dr1_tower_floors.py`.
Analysis only; **adopts nothing** and modifies no decision record or geometry.

---

## Verdict

**The canopy-lever asymmetry is CONFIRMED.** Canopy removal's bay-band gain
concentrates entirely **below floor 4** (i.e. at floors 2–3) and is **exactly zero
at floors 4–8**. A hypothetical tower's upper floors already clear the canopy, so
de-treeing adds nothing to their water view; the canopy lever's value lives at low
elevations — the same street receptors and seated rows the venue itself serves.
The crossover sits precisely in the predicted **~floor 3–4** band.

Per-floor **median water-band clear%** across 138 grid observers (values are
median; IQR p25–p75 in the summary table). Canopy-removal gain = clear%(S1) −
clear%(S2), i.e. what de-treeing buys at that eye height:

| floor | eye ft NAVD88 | S0 | S1 (durable) | S2 leaf-off (meas.) | S2 leaf-on (assum.) | gain leaf-off | gain leaf-on |
|---|---|---|---|---|---|---|---|
| **2** | 635 | 100 | 100 | 15.4 | **7.7** | **+46.2** | **+53.8** |
| **3** | 647 | 100 | 100 | 61.5 | **53.8** | **+19.2** | **+23.1** |
| 4 | 659 | 100 | 100 | 100 | **100** | **0.0** | **0.0** |
| 5 | 671 | 100 | 100 | 100 | 100 | 0.0 | 0.0 |
| 6 | 683 | 100 | 100 | 100 | 100 | 0.0 | 0.0 |
| 7 | 695 | 100 | 100 | 100 | 100 | 0.0 | 0.0 |
| 8 | 707 | 100 | 100 | 100 | 100 | 0.0 | 0.0 |

**Position-level distribution (leaf-on, the operating-season figure):**
- Floor 2: **102 / 138 positions blocked** through the canopy (S2on <40%), only 6
  acceptable — de-treeing frees essentially the whole floor to S1 = 100%.
- Floor 3: 49 blocked / 59 marginal / 30 acceptable — a mixed floor; removal still
  lifts a large minority.
- Floor 4: **131 / 138 already acceptable** *through* today's canopy; **128
  positions gain 0** from removal.
- Floors 5–8: every position at 100% under every set — the canopy is geometrically
  below the sightline and never enters the band.

The two decision criteria resolve unambiguously:
- **CONFIRM test:** does canopy-removal gain concentrate below ~floor 3–4? **Yes** —
  all of it is at floors 2–3; floors 4–8 gain nothing.
- **REFUTE test:** do upper floors gain comparably? **No** — upper-floor gain is 0.

## Cross-checks against the known low-elevation lever facts

The tower result is the top of a monotone elevation gradient already measured at
lower eyes on the **same S1/S2 basis**:

- **Street receptors** (D4 / `neighbor_ceiling_summary.json`; eyes +5 / +17 ft ≈
  605–637 ft NAVD88): canopy present (S2 leaf-on) leaves **72 / 184** receptors
  with any water band; canopy-free (S1) restores it to **178 / 184** — de-treeing
  returns a band to **106 receptors**. Large low-elevation gain.
- **Seated rows** (`per_row_bands_by_set.csv`; eyes 614–638 ft): under S2 leaf-on
  every formal row is **blocked** (0–46% clear, r_m does not exist); under S1 the
  bend/south rows that clear terrain reach 100% — per-row canopy gains up to
  **+84.6** (e.g. bend r11: 15.4 → 100). Large.
- **Tower floor 2** (635 ft) parallels the *highest* seated eye (east r18 ≈ 637.6):
  both canopy-blocked, both freed by removal — the lever is still live at the very
  top of the seated envelope.
- **Tower floors 4–8** (659–707 ft): **zero** gain. This is the new fact DR-1 asked
  for — the elevation at which the canopy lever switches off.

Reading the gradient end to end: de-treeing is a **grade-and-low-floor amenity**.
It restores water views to streets, to the venue's own seats, and to the lowest
1–2 floors of any tower — and adds nothing to floors 4+. The pit owner's *vertical*
option (upper-floor bay view) is **already owned regardless of the trees**;
de-treeing does not price into it.

## Secondary finding — durable occluders never bind a tower

S0 = S1 = **100% at every floor, including floor 2.** Terrain (the pit's own NNW
rim) and the LiDAR-verified city massing (roofs ≤ ~630 ft) sit below every tower
eye ≥ 635 ft, so the **only** occluder that ever enters a tower observer's bay band
is the canopy — and only transiently, at floors 2–3. This contrasts with seated
**east** rows, where durable city massing caps clear% at ~54–62% (those eyes sit at
or below the roofline). For a tower, the entire bay-view question reduces to the
canopy, which the geometry above resolves as a low-floor-only effect.

## Caveats (occluder set + leaf state labels are load-bearing)

1. **Leaf state.** S2 leaf-off (2015-05-02 3DEP) is the winter-screen
   **MEASUREMENT**; S2 leaf-on is a crown-opacity **ASSUMPTION** (heights not
   raised) and is the **season-relevant** figure — summer is the operating season.
   The verdict holds in **both** states (gains: floor 2 +46.2/+53.8, floor 3
   +19.2/+23.1, floors 4–8 0.0/0.0). Ten years of growth since acquisition biases
   today's real screen denser than measured, which would push the floor-2/3 gains
   *up*, not change the floor-4+ zero.
2. **Contingency (D2/D5).** All S2 leeway is contingent on third-party canopy (City
   Bayfront-Park land + MDOT US-31 ROW). No observer is credited a water view on S2
   alone. The floors-4–8 "already clear" finding is stated on **S1** (durable) —
   those floors clear the corridor even with the stage + city in place — so it does
   **not** rest on the canopy at all.
3. **Grid assumption.** Observer plan positions are a uniform **25-ft plate grid**
   over the 2.01-ac outer envelope of parcel `52-19-06-224-001` (138 points inside
   the polygon) — pipeline's choice per DR-1, labeled here as an assumption. The 15
   inner parcel rings are condo-unit subdivisions; the buildable envelope is the
   outer ring.
4. **Band top.** Far-shore waterline per azimuth (D3); **0** of the 966
   (floor,position) cells fell back to the open-water dip on any corridor ray —
   every corridor ray lands on the north shore, as expected. `far_skyline` (D3
   composition metric) is not computed for this observer class; only the water band
   is scored, per DR-1's ask.
5. **Floor-2 cross-check.** Floor-2 eyes (635) sit ~0.4 ft below the adopted S1
   neighbor over-stage ceiling (635.4) — unrelated quantities, but a sanity check
   that the receptor machinery is on the same datum (DR-1 note): floor 2 behaves as
   a canopy-limited low observer, consistent with the seated envelope top.
6. **Planning-grade.** EPSG:6494, NAVD88 intl ft; same DEM/canopy/city inputs and
   provenance as the adopted v2 run. Not a survey.

## Artifacts

- `dr1_per_position_bands.csv` — per (floor, grid position): clear% + verdict for
  S0 / S1 / S2 leaf-off / S2 leaf-on, plus per-position canopy-removal gain and the
  `uses_dip_fallback` flag. (966 rows = 138 positions × 7 floors.)
- `dr1_per_floor_summary.csv` / `dr1_per_floor_summary.md` — per floor per set:
  median + IQR (p25/p75) clear%, and canopy-removal delta medians.
- `dr1_summary.json` — machine-readable summary (floor eyes, corridor, per-floor
  table).
- Driver: `scripts/dr1_tower_floors.py`.

## Dependents (informational — not modified by this run)

DR-1 lists T-1 conclusion and T-8 per-floor `V_up` view-premium pricing as blocked
on this. Handing back to STRAT: the pricing input is **"upper floors (4+) carry no
canopy-removal premium; the de-treeing premium is a grade / floors-2–3 / street /
seated-row asset."**
