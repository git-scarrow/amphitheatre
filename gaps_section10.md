# §10 Coverage Gaps — required for the full endogenous-stage problem

Logged alongside the fixed-stage sweep (which optimizes `G, θ, R, N` with stage `S`
fixed). These are the capabilities the harness lacks before the **full** `U(D)` —
especially endogenous stage `S`, use modes, and acoustics — can be optimized.
Cross-reference: `PROBLEM_DEFINITION.md` §1, §3, §10.

Status legend: ❌ absent · ◐ partial/proxy · ⚠ naming/semantic trap.

---

## 1. Use-mode definitions `M` ❌ (gates objective `Q_m`, `F`)

No `M` parameter exists; nothing is mode-conditioned. Required: an enumerated mode set,
each with its own success criteria and weight overrides, because the optimal bowl differs
sharply by mode.

| Mode | Drives | Mode-specific criteria (proposed) |
|---|---|---|
| speech / civic address | intelligibility, intimacy | short max distance, tight fan, STI proxy ≥ target, no amplification dependence |
| civic ceremony | dignity, processional, ADA-front | accessible front positions, flat ceremonial apron, clear central axis |
| movie (summer) | screen siting, ambient darkness, glare | screen az vs sunset/glare, rear projection throw, lawn depth |
| small amplified | mix position, modest SPL, neighbor noise | FOH location, tower siting, noise at property line |
| larger concert | SPL coverage, egress, durability | coverage uniformity, turf wear, crowd egress width |
| acoustic / unplugged | natural projection, reflectors | shell/reflector geometry, low background noise |
| lawn / picnic (everyday) | openness, informal access | unstructured capacity, view, low-maintenance turf |

**Deliverable:** `modes.yaml` + a `Q_m` evaluator returning per-mode fitness ∈ [0,1];
`F` = aggregate/variance across modes (flexibility = good performance in many modes).

## 2. Stage families (endogenous `S`) ❌ (currently a config constant)

Stage is fixed (`focus_elev 612.5`, `70×34 ft`, `stage_r 50`, orientation slaved to axis).
To make `S` endogenous, define a **stage-family** parameterization and sweep it jointly
with the bowl:

- position (x,y) / radial offset `stage_r`, floor elevation, width, depth, orientation;
- typology: **band-shell** (low reflector, bay backdrop preserved) vs **flat thrust/apron**
  vs **screen-primary** (movie). NOT a proscenium / view-blocking upstage wall (per the
  open-air axiom).
- coupling: stage elevation sets `FOCUS_ELEV` (sightline datum) and the bay-view/upstage
  openness constraint; backstage/service access and drainage of the stage pad.

**Deliverable:** `stage_families.yaml`; lift `FOCUS_ELEV`, `STAGE_R`, stage geom out of
`harness_config.stage` into swept variables; re-derive sightlines, bay-view, drainage per
stage. Until then families 4/5/6 (amplified/ceremony/movie) are not honestly scorable.

## 3. Acoustic proxy `N_q` ❌ (gates the acoustic objective)

No acoustic evaluator. ⚠ **Naming trap:** `harness_config.treatment_cell` is the
**stormwater** wet cell, *not* acoustic treatment — do not conflate.

Minimum viable proxy (planning grade, no ray-tracing needed first pass):
- **direct-field SPL falloff** to back row (geometric 6 dB/distance-doubling);
- **intelligibility proxy** (distance + fan-angle penalty as STI surrogate) for speech mode;
- **early-reflection support** from a band-shell/reflector surface (presence/absence + angle);
- **off-axis coverage** uniformity across the fan.

**Deliverable:** `acoustic.py` returning `{spl_backrow_db, sti_proxy, reflection_support,
coverage_cv}` → `N_q ∈ [0,1]`, mode-weighted (speech weights STI; concert weights SPL/coverage).

## 4. Amplification assumptions `T` ❌ (couples to `N_q`, `I`, `O`)

No model of the amplified case. Needs explicit, documented assumptions:
- **speaker towers / line-array** siting (delay towers for deep audience), power budget;
- **mix position (FOH)** location & the seats it consumes;
- **infrastructure**: power drops, conduit, weather protection, storage;
- **neighborhood-noise** propagation to the property line / nearest residence (drives `O`
  curfew & SPL caps). This is the binding external constraint for evening concerts.

**Deliverable:** `amplification.yaml` (tower positions, SPL targets, FOH footprint, power)
+ a noise-at-receptor proxy feeding `N_q` and the risk term `Ξ`.

## 5. Lateral & cross-slope metrics ◐ (partially built in the contour-bay sweep)

**Partial:** `design_extended_bays` already computes per-row `cross_angle_deg` (oblique
viewing, hits 40–46° in upper rows) and per-seat 10th-pct C (flank-aware). NOT yet in the
fan-bowl `SightlineEngine`, and cross-*slope* (transverse grade, distinct from cross-*angle*)
is still absent. To finish: port cross-angle + per-seat C into the harness and add a
cross-slope raster gate. Original note:

- **Lateral sightline angle**: sightlines are radial-only (`sightlines.py` computes C-values
  down the fall line). No off-axis/oblique-to-stage angle. Wide-fan and extended-flank seats
  are not penalized for awkward viewing angle — so `V` and `useful_cap` overcount edge seats.
- **Cross-slope**: `ada.py:76` explicitly defers it ("schematic — requires survey; target
  ≤2%"). It is neither computed nor gated. Cross-slope > 2% should be a **hard constraint**
  on seating rows and ADA routes; today it is silent.

**Deliverable:** lateral-angle term in `SightlineEngine`; a `cross_slope_pct` raster metric
(transverse gradient along each row arc) wired into `hard_constraints` and seat quality `q`.

## 6. Quality-banded capacity `C` ◐→✅ for contour-bay sweeps (2026-06-06)

**Now implemented** in `scripts/quality_band_capacity.py`: `C_formal = N(≥90) + 0.5·N(60–90)
+ 0.15·N(30–60)`, `N(<30)=0`, with zone hierarchy (formal / soft / rim) and the defensible
formal-bowl stop. Applied to `design_extended_bays/composition_table.csv` → formal 1,452
(gen) / 1,777 (compact), stop at civic row 18. Still TODO: wire band capacity into the
fan-bowl `EvaluatorSuite` (the fixed-stage sweep still uses the passing-rows proxy because
its forced-fill model makes every row ≥90 mm — bands only emerge on natural grade).

Original note retained below:

`evaluators` reports **raw** seat count. The spec demands quality-discounted useful capacity.
This sweep's interim proxy = seats only in rows that pass the 90 mm C-value (drops failing
rows) — honest but coarse. Full version per `PROBLEM_DEFINITION.md` §4:

```
C = Σ_rows Σ_seats q,  q = clip(C_margin · lateral · distance_band · cross_slope_ok, 0, 1)
report seats by band: premium / standard / marginal / lawn
```

Blocked by #5 (lateral + cross-slope). **Deliverable:** `q(seat)` and band reporting in the
capacity step; replace raw sum in scoring.

---

## Other gates the spec names but code does not enforce (from PROBLEM_DEFINITION §2)
- safe **row-end transitions** (no unguarded drop-offs at flank ends),
- **emergency egress** geometry (aisle/exit width vs occupancy),
- **service/performer access** feasibility (back-of-house route),
- **neighborhood noise** limits (needs #3/#4),
- cost / permitting / maintenance / durability terms of risk `Ξ` (`I`, `O`).

## Dependency order (what unblocks what)
1. **#5 lateral + cross-slope** → unblocks **#6 useful capacity** and a real `V`/hard gate.
2. **#2 stage families** (endogenous `S`) → unblocks honest sightline/bay/drainage variation.
3. **#1 modes `M`** → unblocks `Q_m`, `F`, and mode-weighted scoring.
4. **#3 acoustic + #4 amplification** → unblocks `N_q`, neighbor-noise risk, families 4/5/6.
