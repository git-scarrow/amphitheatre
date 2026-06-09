# Petoskey Pit Civic Bowl — Constrained Multi-Objective Layout Problem

**Status:** canonical problem definition. Supersedes any ad-hoc framing.
**Date:** 2026-06-06
**Grounded against:** `harness_config.yaml`, `scripts/harness/*.py` (the agentic-clay evaluator suite).
**Datum/CRS:** NAVD88 Geoid12A international feet; EPSG:6494. DEM: `dem/dem_design_1ft.tif` @ 1 ft.

---

## 0. Corrective axioms (read first)

These exist because the project has a *documented* reasoning cycle (chatsearch, conf. 0.95):
a phantom "steep retaining-wall band" / "eastern escarpment" kept re-entering as if prior
measurement had not happened. The axioms below are load-bearing, not stylistic.

- **A1 — The DEM is the sole source of truth for existing grade.** No terrain feature
  (escarpment, bench, break) may be *asserted*. It is either present in `Z0` or it does
  not exist. Measured profile beats remembered abstraction, always.
- **A2 — There is no retaining wall on site, and none is desired.** A retaining wall is
  never an input, a zone, or a given. It is *only* an emergent infeasibility a candidate
  may trigger — and triggering it rejects the candidate.
- **A3 — Terrain interventions are endogenous outputs.** Cut, fill, benches, and any wall
  *requirement* must emerge from measured DEM/profile failures under the constraint set —
  never from a pre-named terrain zone.
- **A4 — Optimize useful, accessible, coherent public space, not raw seat count.**

### Glossary (the distinction that caused the cycle)

| Term | Kind | Question it answers | Source of truth |
|---|---|---|---|
| **Escarpment** | *Natural* terrain feature (cliff / steep break) | "What does the existing ground do?" (**input**) | `Z0` (the DEM). *Refuted on the east flank: ~30% uniform, no cliff.* |
| **Retaining wall** | *Engineered* structure a design might **need** | "Does this proposal force an unsupported face?" (**output**) | the proposed delta `Δ`, via `wall_trigger` |

They are not the same object and live on opposite sides of the model. Existing steep ground
is **not** a wall trigger (`earthwork.py:160`): a shallow 0.8 ft bench cut into a steep bank
needs no wall. A wall is triggered only by the *depth/abruptness of the proposed Δ*.

---

## 1. Decision vector

```
D = { S, M, θ, R, N, h, L_E, L_S, A, G, T, I, O }
```

> **Notation fix:** the original sketch used `R` for both *row radii* (decision var) and
> *risk* (objective penalty). Here `R` = row geometry; the risk/penalty aggregate is `Ξ`
> (Section 3). `θ` = fan angle.

| Sym | Variable | Meaning | Harness representation | Coverage |
|---|---|---|---|---|
| `S` | Stage | position, elevation, width, depth, orientation, backstage/service | `stage_floor.geojson` + `ctx` (`SF`, `FOCUS_ELEV`, `STAGE_R`, `cfg.stage.*`) | **Exogenous today** (fixed: elev 612.5, 70×34 ft, `stage_r` 50). Spec requires it become **endogenous**. |
| `M` | Use mode | speech / civic ceremony / movie / small amplified / larger concert / acoustic / lawn-picnic | — | **Unmodeled.** No `M` parameter, no mode-conditioned scoring. |
| `θ` | Fan angle | angular seating spread | `cfg.seating.fan_angle_deg` (110°, half 55°) → `ctx.FAN_HALF` | Parameterized; sweepable. |
| `R` | Row geometry | radii, spacing, curvature family | `R_INNER` 85, `R_OUTER` 130, `TREAD` 3.0, `row_mode` circular | Parameterized; sweepable. |
| `N` | Row count | number of rows | `NROWS` 16 | Parameterized; sweepable. |
| `h` | Row elevations | tread elevations, riser heights, tread slope, **cross-slope** | tread elevs solved by `SightlineEngine.compute_rows` (C-value recursion vs `Zp`) | Treads **endogenous (solved)**. **Cross-slope not computed** — flagged schematic, "requires survey" (`ada.py:76`). |
| `L_E` | East flank extent | how far north the east flank runs | implicit in fan azimuth coverage + `N`/`R_OUTER` | **Partially representable**; no clean scalar yet. |
| `L_S` | South flank extent | how far west the south flank runs | implicit (symmetric to `L_E`) | Partially representable. |
| `A` | Accessibility | ADA routes, landings, cross-aisles, wheelchair/companion positions, performer access | `ada_route.geojson` + `ADAEngine` | Routes **authored, then assessed** (running slope on switchback ramps). Not generated/optimized; dispersion, dignity, performer access, cross-slope **unmodeled**. |
| `G` | Terrain delta field | cut/fill raster, borrow/deposit zones, haul | `ClayDelta`: `P = E0 + Δ`; `earthwork_scenarios.geojson` borrow/fill circuits | **Fully represented.** This is the harness's core endogenous variable. |
| `T` | Acoustic strategy | shell/no-shell, low reflectors, speaker towers, mix position, power, amplification | — | **Unmodeled.** ⚠ Naming trap: `cfg.treatment_cell` is the **stormwater** wet cell, *not* acoustic treatment. |
| `I` | Infrastructure | power, drainage, lighting, service access, storage, restrooms, egress | drainage only (`DrainageEngine`, treatment cell) | Drainage covered; rest **unmodeled**. |
| `O` | Operations | free/ticketed, event scale, curfew/noise, maintenance, seasonal durability | — | **Unmodeled.** |

**Honest summary of current reach:** the harness today is a terrain-and-seating-geometry
optimizer over the clay field `G` (with seating params `θ, R, N` sweepable and `h` solved),
under a fixed stage `S`. It scores sightlines, ADA-slope (proxy), earthwork, drainage, and
landscape/solar quality. The full `D` you specified is a **superset**: `M, T, I, O` and the
objectives `Q_m, N_q, F` are **declared but not yet evaluable**. Defining the problem
correctly means naming that gap, not hiding it (Section 10).

---

## 2. Feasible set Ω (hard constraints — rejection rules)

A candidate is **rejected** (archived invalid) if it fails *any* of these. Grounded in
`evaluators.hard_constraints` + `no_touch_violations` + `cfg.no_touch`.

| # | Constraint | Test (as coded) |
|---|---|---|
| H1 | **Sightlines** | every eligible row meets the 90 mm (`c_target_ft` 0.295) C-value; `all_pass` true |
| H2 | **Drainage / treatment cell** | `s_100yr ≥ 0.90·s0_100yr` **and** event-floor freeboard ≥ 1 ft above 100-yr WSEL (611.3) |
| H3 | **No retaining wall** (A2) | `wall_trigger` false: `max_cut ≤ 3 ft` **and** `max_fill ≤ 3 ft` **and** delta-face slope ≤ 200% |
| H4 | **Earthwork balance** | balanced under **neutral** yield (0.95): `fill_cy ≤ cut_cy·0.95` |
| H5 | **ADA not worsened** | route running-slope delta vs baseline ≠ `worsened` |
| H6 | **Bay view not blocked** | `bay_view_score ≥ 0.30` (upstage stays open/low) |
| H7 | **No-touch zones** | no `Δ` beyond LOD tol (0.05 ft) in: treatment-cell core, bay-view corridor, seating-rows-on-natural-grade (>1.5 ft fill over >20% of fan), low upstage stage-side, existing utilities |

Constraints that the spec names but the code does **not yet** enforce as gates (Section 10):
ADA cross-slope ≤ 2% (schematic only), safe row-end transitions, emergency egress geometry,
neighborhood noise limits, performer/service access feasibility.

---

## 3. Objective

The **full research objective** (superset; many terms still unmodeled — see §10):

```
maximize  U(D) = w₁C + w₂V + w₃A_q + w₄E + w₅Q_m + w₆N_q + w₇L_q + w₈F − w₉Ξ
   over   D ∈ Ω           (Ω = the feasible set of Section 2)
```

The **operative civic-bowl objective** (2026-06-06 design reading — this is what the next
design target optimizes; raw seat count is explicitly NOT maximized):

```
maximize  U = w₁·C_formal,banded + w₂·L_terrace + w₃·A_access
            + w₄·V_bay/open-space − w₅·E_earthwork − w₆·D_risk
```

- `C_formal,banded` — quality-banded formal capacity (§4), **not** raw seats.
- `L_terrace` — value of the upper civic landscape (lawn/picnic terraces, overlooks,
  circulation) as *non-counted* public space — rewards converting weak-sightline upper
  contours into landscape rather than forcing them into bad seats.
- `A_access` — accessibility (ADA routes + dispersion + rim connections to the streets).
- `V_bay/open-space` — bay view + openness of the bowl/landscape.
- `E_earthwork`, `D_risk` — penalties (disturbance; drainage/permitting/construction risk).

### Term → evaluator map and weights (as implemented)

| Spec term | Meaning | Implemented as | Weight(s) | Fidelity |
|---|---|---|---|---|
| `C` | **Useful** capacity (quality-discounted) | `capacity.compact/generous` | 1.0 | ⚠ **raw seat count**, not quality-discounted. Upgrade in §4. |
| `V` | Sightline perf (C-values **and lateral** visibility) | `sightlines` pass-fraction | 1.5 | Radial C-value only; **lateral-stage angle unmodeled.** |
| `A_q` | Accessibility *quality* (route dignity, dispersion, performer access) | `ada` delta (improved/unchanged/worsened) | 1.5 | Running-slope proxy only. |
| `E` | Earthwork efficiency (low disturbance, balanced, short haul, low stabilization) | `earthwork` + `retaining_wall_avoidance` | 1.5 + 1.5 | Solid. |
| `Q_m` | Fitness for intended use modes | — | — | **Missing** (needs `M`). |
| `N_q` | Acoustic / noise-control quality | — | — | **Missing** (needs `T`). |
| `L_q` | Landscape quality (bay view, openness, stage presence, fit) | `bay_view`+`landform_fit`+`stage_presence`+`upper_sunset`+`glare_avoidance` | 1.5+1.5+1.0+1.2+1.2 | Best-covered objective. |
| `F` | Flexibility across event types & everyday use | — | — | **Missing** (needs `M`,`O`). |
| `Ξ` | Risk (permit, drainage, construction, maintenance, cost, safety, noise) | penalties: `cut_fill` 0.1/kCY, `haul` 0.1/100kCY-ft, `retaining_wall` 2.0, `drainage_loss` 0.5/10%, `overbuild` 0.5 (+`drainage` 1.5 as positive term) | — | Construction-volume/haul/drainage only; **cost, permitting, maintenance, safety, neighborhood-noise unmodeled.** |
| — | symmetry | `symmetry_penalty` (landscape *wants* asymmetry → weight near-zero) | 0.3 | intentional low weight |

**Scalarization (as coded, `scoring.py`):** additive penalized form —
`final = max(0, normalised − 10·Σpenalties)`, `normalised = 100·Σ(wᵢ·rawᵢ)/Σwᵢ`.
Verdict bands: ≥70 keep, ≥50 conditional, else revise; any H-failure ⇒ reject.

### The decision question, formalized

> *"Which configuration gives the highest civic usefulness per unit of terrain disturbance
> and operational complexity?"*

This is a **ratio**, dual to the coded additive form:

```
maximize  Usefulness(D) / ( Disturbance(D) · Complexity(D) )
   where  Usefulness   = w₁C+w₂V+w₃A_q+w₅Q_m+w₆N_q+w₇L_q+w₈F   (benefits)
          Disturbance  = gross_cy + haul_effort proxy            (earthwork footprint)
          Complexity   = Ξ operational/infra/permit aggregate
```

**Recommendation:** do **not** collapse to a single scalar for the decision. The weights
`wᵢ` are subjective and the *point* of the study is the trade-off. Report the **Pareto
frontier** of `Usefulness` vs `Disturbance` (and vs `Complexity`); use the additive `U(D)`
only to rank *within* the non-dominated set. "Usefulness per unit disturbance" is the
selection lens; the additive score is a tie-breaker.

---

## 4. Quality-banded capacity & the zone hierarchy (envelope ≠ plan)

**Principle (load-bearing): the street-bounded contour sweep is the maximum site ENVELOPE,
not the seating plan.** The formal bowl stops at the **last defensible sightline band**;
upper contours become landscape, not forced seats.

### Band formula (implemented — `scripts/quality_band_capacity.py`)

Seats are banded by natural-grade centreline C-value and credited partially:

```
C_formal = N(C≥90mm) + α·N(60–90mm) + β·N(30–60mm),   N(C<30mm) = 0
α = 0.5   β = 0.15
```

### Zone hierarchy

| Zone | Rows* | C band | Function | Counts as |
|---|---|---|---|---|
| Stage + forecourt | civic seating rows 6–18 (+ forecourt 1–4) | ≥ 90 mm | fixed raked seating / benches | **formal** (full credit) |
| Soft upper edge | ~row 19 | 60–90 mm | optional upper / low-expectation seating | partial (α=0.5) |
| Rim / overflow landscape | ~rows 20–25 | 30–60 / <30 mm | lawn/picnic terraces, standing, paths, **bay overlooks**, ADA rim ties to Petoskey/E.Lake/E.Mitchell | `L_terrace`, **not** formal seats |

\* From `design_extended_bays/composition_table.csv` (face 312, natural grade). Defensible
**formal-bowl stop = civic seating row 18** (R ≈ 157 ft); row 19 (86 mm) is the soft edge;
rows ≥20 fall to marginal/rim and become increasingly **bend-only (street-clipped)** with
cross-angles 40–46° (oblique). See `design_extended_bays/quality_bands.md`.

### Capacity result (the number to report — bands, never one raw figure)

| seat width | formal (≥90) | + soft (row 19) | full envelope raw | `C_formal` banded |
|---|---|---|---|---|
| generous 22-in | 1,452 | 1,566 | 1,895 | 1,545 |
| compact 18-in | 1,777 | 1,917 | 2,320 | 1,892 |

**Public-facing:** *"~1,450–1,780 high-quality formal seats, expandable to ~1,900–2,200 with
upper soft/overflow rows, plus lawn/terrace rim to the street edges."* The full-envelope raw
figure must **not** be advertised as formal seating — it includes weak-sightline and
street-clipped stub rows.

> Caveat: bands use **centreline** C; the per-seat 10th-pct C (cross-angle-aware) in the
> extended_bays sweep is stricter and would pull borderline upper rows down further — i.e.
> these formal counts are an upper bound on quality. (§10 #5 lateral metric: partially built.)

---

## 5. Design families (evaluate families, not one geometry)

Eight families. Families 1/2/3/7/8 are expressible by the current harness (terrain + seating
geometry over `G,θ,R,N`); families **4/5/6 require the `M`/`T`/`N_q`/`Q_m` extensions** and
cannot be honestly scored until those exist.

| # | Family | Primary levers | Existing instance(s) on disk (verify before citing) |
|---|---|---|---|
| 1 | Minimal-work open civic bowl | seats on natural rake, `G≈0` | `design_open_low/` (baseline), `design_civic_bowl/` |
| 2 | Larger-capacity extended-flank bowl | `L_E`,`L_S`,`N` up; `C` quality-discounted | `design_extended_bays/`, `design_corner_bays/` |
| 3 | Hybrid terraced bowl w/ picnic/lawn terraces | upper lawn terraces; mixed `M` | `design_corner_bowl/` (?) |
| 4 | Performance-oriented amplified venue | `T` (shell/towers/mix), `N_q` | *needs `T`/`N_q`* |
| 5 | Speech / civic-ceremony-first venue | `M`=speech; intelligibility-first | *needs `M`/`N_q`* |
| 6 | Movie-capable summer venue | screen siting, glare/solar, `O` | *needs `M`/`O`* |
| 7 | Earthwork-enhanced idealized bowl | deliberate `G` for ideal rake | `design_civic_contour/` (?) |
| 8 | Net-zero borrow/fill scenario | `balance_to_zero`, H4 binding | `cfg.variant_families.D/E`, `earthwork_scenarios.geojson` |

(Config `variant_families A–E` are axis-rotation/grading variants of essentially one bowl —
a *sub-sweep*, not the eight use-driven families above.)

---

## 6. Sweep grid

For each family, sweep:
`stage location · stage elevation · stage width/depth · fan angle θ · row count N ·
row spacing · riser height · L_E · L_S · aisle placement · ADA route strategy ·
acoustic-treatment level (T) · amplification infrastructure (T) · cut/fill strategy (G)`.

Currently runnable axes: axis `[330,325,320,315,305]` (`face_az`), `θ`, `R`, `N`, and the
`G` borrow/fill circuits. Stage, `T`, ADA-route generation, and `M`/`O` axes need the
extensions in §10 before they can be swept.

---

## 7. Per-candidate report card (computed metrics)

Each candidate emits: seats **by quality band** · per-row C-values (mm) · lateral sightline
angles* · stage-to-row distances · **row-by-row elevation residuals vs DEM** (`cut_fill_ft`)
· cross-slope* · cut/fill volume (cut/fill/net/gross CY) · haul distance & effort ·
exposed/unstable faces / **wall-trigger** · ADA route length & switchback count* &
running slope · accessible-seat distribution* · drainage impact (Δ storage %, freeboard) ·
acoustic/noise proxy* · view-obstruction (`bay_view_score`) · solar (upper-crescent, glare)
· operational-feasibility score* · `U(D)` breakdown + penalties + verdict.

`*` = specified, **not yet implemented** (see §10).

---

## 8. Decision rule

1. Filter to `Ω` (drop every H-failure — Section 2).
2. Plot the survivors on **Usefulness × Disturbance** (and × Complexity).
3. Keep the **non-dominated (Pareto) set**.
4. Within it, rank by `U(D)`; prefer the configuration with the highest **usefulness per
   unit disturbance** that also clears `O`/permitting reality.
5. Never select on raw capacity; never select a dominated point because its single scalar
   looked high under one weight vector.

---

## 9. Epistemic status (facts vs inferences)

**Observed (measured; DEM/EPT/profile — still re-verify against `Z0` per A1):**
- East flank has **no escarpment/cliff**; R130–190 is the same ~30% character as the current
  seating zone; viable seating extends to R≈190 ft. The 16-row stop is a *budget baseline,
  not a terrain limit*.
- Bay view: the flat ~618 ft rim does **not** block the bay for mid/upper rows; front/floor
  rows lose it inherently; 330° vs 315° turns on a *foreground tree screen* (densest
  az 315–320), so 330° wins under current trees and equalizes if trimmed. Water plane 579.45.
- Stormwater treatment cell: bottom 609.1, pool 611.3, 100-yr WSEL 611.3, event-floor
  min 612.5 (⇒ 1.2 ft freeboard at the configured floor).

**Inference (model/abstraction, not measurement):**
- The additive `U(D)` weight vector and verdict bands (70/50) are stipulated, not derived.
- "Useful capacity" quality bands and lateral/cross-slope discounts are *proposed* metrics.
- Family→on-disk-instance mapping in §5 is by directory name; contents need verification.

**Key assumption:** the existing DEM (`dem_design_1ft.tif`) faithfully represents buildable
grade at planning resolution; all feasibility flows from it (A1).

**Most decision-relevant unknown:** whether the project intends to *stay* within the
currently-modeled subproblem (terrain + seating geometry, `S` fixed) or to build out
`M/T/I/O` so the full `U(D)` — especially `Q_m`, `N_q`, `F` and endogenous stage `S` — can
actually be optimized. The answer determines whether families 4/5/6 are in scope now.

**Sufficient for the next step:** the problem is fully *defined* and the *runnable* subproblem
(maximize `U` over `G,θ,R,N` within Ω, `S` fixed) can be swept immediately. The full problem
needs the §10 build-out before families 4/5/6 are scorable.

---

## 10. Coverage gaps to close (to evaluate the full `D`)

1. **Endogenous stage `S`** — make stage position/elevation/orientation a swept variable, not
   a config constant; sightline focus and bay relationship follow from it.
2. **`M` use-mode parameter + `Q_m` evaluator** — mode-conditioned fitness (speech
   intelligibility vs concert vs movie vs lawn).
3. **`N_q` acoustic/noise evaluator + `T`** — shell/reflector/tower geometry, mix position,
   neighborhood-noise propagation proxy. (Rename to avoid clash with stormwater "treatment".)
4. **Lateral sightline angle** + **cross-slope** metrics (both feed H-constraints and `C`).
5. **Useful-capacity quality bands** (§4) replacing raw seat sum.
6. **`A` generation** — synthesize/optimize ADA routes (dispersion, dignity, performer
   access), not just assess authored ones.
7. **`I`/`O` and the missing `Ξ` terms** — cost, permitting, maintenance, safety, egress,
   durability.
8. **Egress & row-end transition** hard constraints (H-set is currently silent on these).
