# Bay-band v2 decision addendum — constraint regime for bay-view charging

_Addendum to `RULE9_DECISION_RECORD.md`. Amends the **bay-view constraint regime** that Rule 9
arguments consume. Does **NOT** reopen the adopted P_opt / az-150 / five_facet_apron /
path-4 / T1_deck_only bundle — placement and fan are untouched._

- **Status:** `adopted` — DP1–DP4 decided by **owner instruction (session), 2026-07-21**,
  with amendments folded in below. Drafted and signed the same day.
- **Measured basis:** commit `4e6d03a` ("bay-band v2"), executed on gentoo per
  `analysis/bay_view_obstruction/DISPATCH_EFFECTIVE_SILHOUETTE_AND_NEIGHBOR_GATE.md`.
  Artifacts: `rn_rm_table.md`, `per_row_bands_by_set.csv`, `band_top_farshore.csv`,
  `canopy_top_leaf{off,on}_3ft.tif` (+ provenance), `neighbor_ceiling_S1/S2.tif`,
  `neighbor_receptors.geojson`, `element_verdicts_v2.md`, `summary_v2.md`,
  `mast_resite_search.json` (DP2c).

---

## Owner statements of record (2026-07-21, verbatim)

1. On the neighbor rule: _"One thing we CAN still keep is the rule that any construction not
   occlude any view above r_max (the rim) such that no owner on the streets east, south or
   southeast can complain."_ — clarified to **Reading B**: the protected asset is the
   **water view** ("no owner loses any bay view"), NOT the skyline ("no visible change
   above the rim"). Skyline change above the 618.04 rim is accepted and reported, not gated.
2. On the trees: _"If the project became a civic effort the trees, owned by Petoskey, could
   come down."_
3. On the constraint: _"100% bay view from any seat was never possible given the trees.
   not limiting what bay view we have is the constraint, and given how little we have,
   it's not much of one."_

Statement 3 is adopted **consciously as a weak gate**: the interior bay-view constraint
protects the bands that exist today, which measurement shows are thin (best seated band
~54% clear, most rows 0%).

---

## D1–D5 · Definitions (ADOPTED, DP1)

| # | Definition | Replaces |
|---|---|---|
| **D1** | **Effective silhouette:** per ray, the bay band's lower edge is the max occlusion angle over ALL opaque occluders (terrain, city massing, canopy, stage mass). | Bare-earth-only silhouette (`per_row_obstruction` v1, now the S0 baseline). |
| **D2** | **Occluder sets + charging policy:** S0 terrain · S1 +flat stage +LiDAR-verified city (**durable**) · S2 +canopy-today (**contingent**, leaf state labeled). **Interior gate = no reduction of S2 bands** (owner statement 3) *until the DP4 trigger fires, after which S1 governs all gates for permanent elements*. **S1 charges are declared option costs**, not gates, pre-trigger. No element may pass on S2 leeway alone without a `contingent_on_canopy` flag. | Single unlabeled "bay %" figures. |
| **D3** | **Band top = far-shore waterline** per azimuth (corridor rays hit the north shore at 1.85–2.4 mi, short of the ~8.5-mi tangent; waterline sits 0.12–0.18° below the open-water horizon — a real correction, ~10× the dispatch's estimate). Far-shore landform occlusion is reported separately as composition, not water. | `horizon_dip_deg` open-water horizon as band top. |
| **D4** | **Neighbor hard gate (Reading B):** no construction may intrude into any existing water band of the 184 street receptors (E Lake / E Mitchell / Petoskey St; eyes +5 / +17 ft). Gate = element top vs the neighbor-ceiling raster. **S1 ceiling is the durable gate** (over-stage min **635.4 ft ⇒ +22.9 ft** above the 612.5 deck); S2-only headroom (+25.8 ft) is contingent. | The informal "nothing above the rim" intuition (Reading A, considered and rejected by owner). |
| **D5** | **"Bay view" is retired as an unqualified term.** Every quoted figure carries occluder set + leaf state. r_n / r_m are attribution outputs: r_n = first row with a non-empty S0 band (east r8 / bend r6 / south r6); **r_m = first row acceptable under S2 = does not exist** (no row ≥80% clear through today's canopy, either leaf state). | The tiered r_n/r_m model as an assumption. |

**The gate asymmetry is deliberate (owner, DP1):** the regime gates interior views on **S2**
(today's thin bands) but gates neighbors on **S1** (restored, canopy-free). Chosen, not
accidental — neighbors receive durable protection independent of what happens to city-owned
trees, while the interior constraint honors owner statement 3. Recorded so no future reader
mistakes the asymmetry for an oversight.

**Standing caveats attached to D2/D5:** canopy is a 2015-05-02 **leaf-off measurement**
(3DEP EPT, GPS-time decoded) with crowns modeled opaque — true winter visibility is
somewhat better, summer (leaf-on assumption) somewhat worse; ten years of growth since
acquisition biases today's screen denser than measured. None of this changes the r_m
conclusion (no row clears in either state).

---

## DP1–DP4 · Decisions (owner instruction, 2026-07-21)

### DP1 — Definitions D1–D5 · **ADOPTED** ☑
With the deliberate-asymmetry note above added to the record. Effect: `STAGE_SHAPE_STUDY.md`
§C obstruction figures (e.g. roof 8.6% bay) are superseded-in-definition — historical,
terrain-only basis, not to be quoted without that label.

**Consequence named for the record (owner):** D5's finding that **r_m does not exist** is the
most consequential fact in this file — the "bay view" the design story has carried is, today,
a **part-glimpse asset concentrated in the bend/south**. That is not a reason to reject
anything; it is the reason the **de-treeing question is load-bearing for the design
narrative**, not merely the economics.

### DP2 — Mast policy · **ADOPTED: (a) + (c) hybrid** ☑
The permanent/removable distinction is principled — Reading B's complaint logic concerns
durable loss — but this is the sole carve-out in an otherwise clean covenant, so it is
tightened three ways:

1. **The (c) search was run** (`mast_resite_search.json`): **1,575 of 2,881 stage-zone cells
   (55%) admit the full 26-ft mast under the durable S1 ceiling** (max anywhere 44.3 ft;
   qualifying cells span the zone, concentrating toward the downstage/receptor side).
   **Re-siting is feasible → the seasonal exemption is belt-and-suspenders, not
   load-bearing.** Final mast siting to be selected from qualifying cells at
   element-adoption time, jointly with screen-geometry needs.
2. **Self-executing conditions** (written into the element definition, not "seasonal" as a
   vibe): masts erected **no earlier than May 15**, struck **no later than October 15**
   (proposed defaults, owner-adjustable at element adoption).
3. **Screen deployment only after civil twilight** (owner direction): the protected amenity
   peaks at summer sunset over the bay — a screen that rises only once the sun is down never
   intrudes on the view anyone actually values. This single condition does more
   complaint-prevention work than the height math.

### DP3 — T2 roof price · **ACCEPTED as the figure of record** ☑
The 8.6% → **38.5%** repricing stands (old figure: terrain-only basis, flattered the roof).
Two conditions attach **now**:

- **Spec condition travels with the T2 element definition immediately** (not rediscovered at
  final design): the S1 neighbor-gate pass margin is **~0.9 ft** — inside construction
  tolerance — so any T2 adoption specs the roof top at **≤ 634.0 ft NAVD88** or re-verifies
  against the ceiling raster at final geometry.
- **Identity tension named:** T2's charge is denominated against the **restored** view — the
  roof takes the single largest bite of precisely the asset a civic de-treeing effort would
  create. This is the same species of question as Rule 9 (does the venue serve the bay view
  or its own program?) and must be resolved **consciously at the typology decision** with
  the 38.5% figure on the table. The stage-shape memo carries this figure forward.

### DP4 — Sequencing rule · **ADOPTED, strengthened** ☑
The drafted present-both rule prevented drift but still permitted the corrosive order. As
adopted:

- **Anti-hypocrisy clause:** for **permanent elements**, once the trigger fires, the **S1
  evaluation binds** — on the neighbor gate (already D4) **and on every interior gate the
  element must pass**. The venue holds itself to the standard it would demand of any tower
  on this block: **no element survives only because trees someone intends to remove are
  still standing.**
- **Concrete trigger** (replacing "credible" as a judgment word): de-treeing becomes live
  upon **(i)** a City of Petoskey resolution addressing vista/canopy policy for the
  Bayfront-Park / US-31 frontage, or **(ii)** execution of the civic-effort instrument that
  formalizes owner statement 2. **Before the trigger, S2 governs interior gates; after it,
  S1 governs all gates for permanent elements. The transition date is logged in this
  record.** (Transition log: — none yet.)

---

## Effect on existing records (executed at adoption, 2026-07-21)

- `RULE9_DECISION_RECORD.md`: bundle unchanged; pointer added; T1/T2 obstruction figures
  labeled "terrain-only basis, superseded-in-definition by v2."
- `docs/DESIGN_CANON.md` Rule 9: status unchanged (`carried_provisional`); the fan/placement
  logic is orthogonal to this regime.
- `PROBLEM_DEFINITION.md` §9: "330° wins under current trees" annotated with the v2
  quantification (part-glimpse today; restorable view structurally a bend/south asset; east
  capped ~54–62% by durable city massing).
- `analysis/stage_adoption/MEMO_STAGE_SHAPE_VS_AUDIENCE_AXIS.md`: inherits the DP3 figure
  (38.5% S1 / roof-top ≤ 634.0 ft) prominently in its constraints.
- `DATA_GAPS.md`: NNW canopy screen now measured (2015 leaf-off); new gaps logged: field
  verification of 2015→2026 canopy growth; leaf-on opacity assumption unvalidated.
  Load-in/service access and utilities remain open (unrelated to this addendum).

## Sign-off

**Decided by:** owner instruction (session), 2026-07-21 — DP1 adopted (asymmetry recorded
deliberate) · DP2 (a)+(c) hybrid with tightened, self-executing conditions · DP3 price
accepted with immediate spec condition · DP4 adopted with binding-S1 clause and concrete
trigger. **Status: `adopted`.**
