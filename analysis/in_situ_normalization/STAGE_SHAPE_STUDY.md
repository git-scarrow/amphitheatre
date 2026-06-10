# Stage Shape Study — deck, superstructure options, obstruction, operations, Rule 9

Five separated products; nothing here adopts a stage. mass hiding below the terrain silhouette behind it adds no obstruction; new bay/cell/sky blockage is measured per family; bay ≤2.0% none / ≤10.0% minor / above = flagged-not-height-rejected

---

## A · Deck geometry (placement + footprint)

70 × 34 ft performance core at the event-floor grade (612.5 ft, ~1 ft structure band). Placement search against the audience frame and the row-1 pocket:

| placement | axis | mismatch° | lateral ft | front→row1 e/b/s ft | cell gap ft |
|---|---|---|---|---|---|
| P_inherited | 150.0 | -25.4 | -22.2 | 17.3/20.6/2.2 | 46.0 |
| P_lat | 150.0 | -0.0 | -0.0 | 0.0/18.7/13.1 | 46.0 |
| P_frame | 124.6 | 12.1 | 10.1 | 18.9/20.3/0.0 | 41.8 |
| P_opt **(selected)** | 150.0 | -6.3 | -6.7 | 12.0/32.7/21.9 | 32.0 |

constrained search keeping the az-330 bay axis: slide laterally toward the frame + pull upstage until every family keeps a >=12 ft orchestra gap and >=15 ft cell clearance — the row-1 pocket forbids zeroing the offset (P_lat touches east row 1, P_frame touches south row 1); residual offset declared per Rule 9 path 3.
Deck alone adds 0.0% bay / 1.7% foreground obstruction (worst family) — the deck is visually free.

---

## B · Roof / canopy / mast options (element menu)

Each superstructure element is scored ALONE at the selected placement so options compose; bundles in section C cross-check.

| element | plan sf | top ft above deck | role |
|---|---|---|---|
| roof | 2812 | 22.0 | thin roof slab on slender posts (posts <0.5 deg, not modelled) |
| canopy | 1440 | 18.0 | curved acoustic canopy over the upstage half; open below; NO back wall |
| boh | 384 | 12.0 | 24x16x12 back-of-house block tucked into the most-hidden upstage corner |
| mast_l | 4 | 26.0 | removable screen mast (seasonal; screen itself is night-only and not a permanent element) |
| mast_r | 4 | 26.0 | removable screen mast (seasonal; screen itself is night-only and not a permanent element) |
| wing_l | 40 | 12.0 | solid side wing, lateral only |
| wing_r | 40 | 12.0 | solid side wing, lateral only |
| apron | 624 | 1.0 | faceted forecourt apron at deck level |
| service_canopy | 1056 | 21.0 | overhead service/lighting canopy |

---

## C · Obstruction deltas (by family)

Per-element, area-weighted share of the EXISTING visible band newly blocked (bay %), foreground meadow blocked (cell %), and mean new skyline cut (sky °):

| element | east bay/cell | bend bay/cell | south bay/cell | worst sky ° |
|---|---|---|---|---|
| roof | 8.6/0.0 | 7.7/0.0 | 3.8/0.0 | 1.025 |
| canopy | 2.8/0.0 | 16.1/0.0 | 2.7/0.0 | 1.315 |
| boh | 7.3/57.9 | 1.2/23.0 | 0.0/0.0 | 0.723 |
| mast_l | 3.2/6.3 | 1.2/1.1 | 0.0/0.0 | 0.242 |
| mast_r | 0.4/0.0 | 1.7/1.5 | 1.7/4.9 | 0.194 |
| wing_l | 4.3/30.4 | 0.0/0.3 | 0.0/0.0 | 0.484 |
| wing_r | 0.0/0.0 | 2.2/3.4 | 1.6/14.8 | 0.159 |
| apron | 0.0/0.0 | 0.0/0.0 | 0.0/0.0 | 0.0 |
| service_canopy | 12.9/0.0 | 18.6/0.0 | 7.8/0.0 | 0.719 |

Bundled typologies (measured as combinations, not sums):

| bundle | elements | worst new bay % | worst new cell % | verdict |
|---|---|---|---|---|
| T1_deck_only | — | 0.0 | 1.7 | ACCEPTABLE |
| T2_covered_civic | roof | 8.6 | 1.7 | ACCEPTABLE (minor) |
| T3_acoustic_canopy | canopy | 16.1 | 1.7 | FLAGGED |
| T4_asymmetric_utility | boh | 7.3 | 57.9 | ACCEPTABLE w/ CAVEAT |
| T5_movie_capable | mast_l+mast_r | 3.6 | 6.8 | ACCEPTABLE (minor) |
| T6_side_framed_acoustic | wing_l+wing_r | 4.3 | 30.4 | ACCEPTABLE (minor) |
| T7_hybrid | apron+service_canopy+boh | 18.6 | 41.6 | FLAGGED |

---

## D · Operational scores

| bundle | wings | ceremony | concert | movie | rigging | weather | storage | acoustic | total /40 | constructability /5 |
|---|---|---|---|---|---|---|---|---|---|---|
| T1_deck_only | 1 | 4 | 2 | 2 | 0 | 0 | 0 | 1 | 10 | 1 |
| T2_covered_civic | 2 | 5 | 4 | 4 | 4 | 4 | 1 | 3 | 27 | 3 |
| T3_acoustic_canopy | 2 | 4 | 4 | 3 | 3 | 2 | 1 | 4 | 23 | 3 |
| T4_asymmetric_utility | 3 | 4 | 3 | 3 | 1 | 1 | 4 | 2 | 21 | 2 |
| T5_movie_capable | 1 | 4 | 3 | 5 | 2 | 0 | 0 | 1 | 16 | 2 |
| T6_side_framed_acoustic | 4 | 4 | 4 | 3 | 2 | 1 | 2 | 4 | 24 | 2 |
| T7_hybrid | 3 | 5 | 5 | 4 | 4 | 3 | 3 | 4 | 31 | 4 |

Bases for each rubric line: `stage_typology_scores.json` (`operational.basis`). The T5 screen is night-only; masts are removable and scored standing.

---

## E · Rule 9 implications

- **path1_audience_axis** (P_frame): axis turns to the audience centroid (124.6); audience faces ~305 — a 25 deg bay-axis deviation must be acknowledged and justified; touches south row 1 as searched (needs its own gap search before adoption)
- **path2_bay_axis_lateral** (P_lat): keeps az 150/330; the FULL lateral shift zeroes the offset but touches east row 1 — infeasible as-is; partial shift collapses into path 3
- **path3_compromise** (P_opt (this study's tested candidate)): keeps the bay axis, slides −15.5 ft lateral + pulls upstage; residuals −6.7 ft / −6.3 deg DECLARED; all row-1 gaps ≥ 12 ft, cell clearance 32 ft
- **path4_wide_fan_declaration** (any): config/canon change only (harness_config fan fields); orthogonal to placement; acoustic consequences must be noted per Rule 9 text

Adoption requires:

1. pick a placement path (P_opt = path 3 is the measured front-runner) AND an element bundle
1. declare every minor obstruction number for the chosen bundle (e.g. thin roof: per-family bay deltas below)
1. update harness_config.yaml / DESIGN_CANON Rule 9 status and re-run the Scenario E stage validation
1. only then un-pause the Claude Design handoff and let boards claim a settled stage

**Rule 9 remains OPEN.** Board 01 shows only the selected PROVISIONAL footprint (P_opt) pending this decision.
