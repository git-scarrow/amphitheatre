# Clay Harness Retrofit Audit

_Audit of `scripts/harness/` ahead of the intervention-tier retrofit (2026-06-10).
Goal: turn the agentic-clay harness into a scenario generator + evaluator that can
compare **Scenario E (locked baseline)** against modest / optimized / ambitious /
idealized earthwork interventions under one metric set._

## 1. What the harness is today

The harness is a proposal → deterministic-evaluation loop built around a single
mutable raster (`ClayDelta`, P = E0 + Δ) over the immutable LiDAR DEM, with a
suite of evaluators and a weighted scorer:

| Module | Role |
|---|---|
| `project.py` | `ProjectState`: DEM + design context loaded once (immutable) |
| `clay.py` | `ClayDelta`: bounded, stackable terrain-delta operations + audit trail |
| `scenarios.py` | `ScenarioLibrary`: named borrow/fill polygons from `earthwork_scenarios.geojson`; proposal pre-validation |
| `evaluators.py` | `EvaluatorSuite.run_all()`: merged metrics + `hard_constraints()` gate |
| `earthwork.py` | volumes, haul, yield/shrink, topsoil, wall trigger, slope improvement |
| `sightlines.py` | per-row C-value solver against proposed DEM (arc-median sampling) |
| `ada.py` | route running-slope assessment + baseline delta |
| `drainage.py` | treatment-cell storage / freeboard / function-preserved |
| `solar_eval.py` | sunset crescent + glare proxies |
| `aesthetic.py` | landform fit, contour match, stage presence, bay view, overbuild |
| `terrain.py` | slope rasters, LOD mask, arc sampling |
| `scoring.py` | `MultiObjectiveScorer`: weighted sum 0–100 + penalties + verdict |
| `variants.py` | `VariantManager`: variants/Vnnnn report cards (delta.tif, metrics.json, report.md) |
| `agent.py` | LLM loop (`claude -p`) generating YAML proposals per variant family |
| `affordance.py`, `inevitability.py`, `composer.py` | INEVITABILITY canon engines (site-affordance composer; Move/Design ledgers) |

## 2. Current operation primitives (`ClayDelta`)

All operate on a polygon mask over the delta raster:

| Primitive | Semantics | Default caps |
|---|---|---|
| `raise_patch` | add uniform fill | max_fill 5.0 ft |
| `lower_patch` | remove uniform depth | max_cut 5.0 ft |
| `smooth_patch` | Gaussian-smooth delta inside polygon | sigma 5 ft |
| `flatten_pad` | force absolute elevation (cut or fill) | uncapped |
| `terrace_plane` | planar draining shelf, axes from **the shared arc centre** | 2% cross / 0.5% long |
| `grade_ceiling` | cut-only lower-to-target | max_cut 2.0 ft |
| `cut_bench` | uniform bench cut | max_cut 2.0 ft |
| `fill_shelf` | uniform shelf fill (`auto_balance` supported) | max_fill 1.25 ft |
| `balance_to_zero` | scale fill to borrow × yield | yield 0.95 |
| `preserve` | no-op marker (enforced at evaluator level) | — |

Missing for the intervention-tier work: section extension/trim, row-family
morphing, row-end shoulder smoothing, cross-aisle plane solving, stage refit,
faceted apron geometry, borrow-zone selection, per-recipe cut/fill caps, and
configurable low-wall triggers. All current primitives are **terrain-only**;
none mutate the *seating/stage geometry model*, because the harness has no
mutable geometry model — see §3.1.

## 3. Hardcoded assumptions (retrofit blockers)

### 3.1 `design_open_low` is the governing geometry everywhere

This is the single biggest blocker, and it directly violates the project canon
(`scripts/in_situ_common.py`: governing scheme = `scenarioE_three_section_civic_bowl`;
`design_open_low` is SUPERSEDED for seating, user-corrected 2026-06-10).

- `harness_config.yaml design.baseline_ctx: design_open_low/_ctx.pkl` —
  `ProjectState` loads the arc centre `ctx["F"]`, row table `ctx["rows"]`,
  `stage_floor`, and `ada_route` from `design_open_low/`.
- `ProjectState.RAD`/`AZ` grids are computed from that **single shared arc
  centre**; `fan_mask()` is one constant-radius annulus `AX_AZ ± FAN_HALF`,
  `R_INNER..R_OUTER`. Scenario E has *no shared arc centre and no constant-radius
  fan* (three contour-fitted sections east/bend/south, each its own curvature).
- `SightlineEngine` samples **arc medians** about that centre; row pass/fail is
  a full-fan median, blind to per-section terrain.
- `sightlines.delta_vs_baseline()` explicitly "compares against baseline
  design_open_low sightlines".
- `aesthetic.row_arc_contour_match()` and `clay.terrace_plane()` both derive
  axes from `state.arc_centre()`.
- `ADAEngine` assesses `design_open_low/ada_route.geojson` schematic ramps
  (which fail at 10–17.8%), not the validated Scenario E switchbacks in
  `analysis/scenarioE_civic/geometry.geojson`.

### 3.2 Single-fan capacity formula

`EvaluatorSuite.run_all()` computes seats as
`R · radians(2·FAN_HALF) · (1 − 0.18 aisle) // 1.83 ft` per row — hardcoded
seat width (1.83), aisle fraction (0.18), and a full constant fan. It ignores
section spans, the rows-9/10 cross-aisle displacement (−169 seats), promenade
row 5, and per-section `seats` already tabulated in
`design_extended_bays/composition_table.csv` / Scenario E `seats_kept`.

### 3.3 Row geometry and row count

- Row radii: `composition_table.csv` (per row, axis radius) or
  `R_INNER + i·TREAD`; `formal_stop_row: 18` from config.
- The sightline tread solver (`compute_rows`) is **fill-only**:
  `tread = max(tread_req, terr)` — it will never cut a tread down, so any
  intervention tier that benefits from cutting high spots (the dominant cheap
  move per the fixed-stage sweep) cannot be expressed in the row model.

### 3.4 Stage

- Stage params (`width 70 / depth 34 / stage_r 50 / elev 612.5 / axis 150°`)
  are the **inherited design_open_low stage** — DESIGN_CANON Rule 9 is OPEN:
  +25.6° audience-axis mismatch and −22.5 ft lateral offset vs the validated
  Scenario E seating.
- `aesthetic.stage_presence()` hardcodes frontage `width + 2·17.0` and a 0.64
  target ratio; there is **no stage-axis-mismatch or lateral-offset metric**
  anywhere in the evaluator suite, despite that being the live design question.
- `bay_view_score()` samples upstage along the inherited axis only.

### 3.5 Treatment cell

`DrainageEngine` looks up a feature literally named `treatment_wet_cell` inside
`design_open_low/stage_floor.geojson`; elevations are config constants. Works,
but couples the drainage gate to the superseded package's file layout.

### 3.6 Baseline constants baked into code

- `evaluators.py`: fallbacks `c_formal 1545`, `compact 1797`, `generous 1472`.
- `scoring.py`: `WEIGHTS`/`PENALTIES` are module constants; the
  `scoring:` section of `harness_config.yaml` is **dead config** — `AgentLoop`
  constructs `MultiObjectiveScorer()` without passing it.
- `earthwork.wall_trigger`: 3.0 ft cut/fill and 200% delta-slope thresholds
  hardcoded. Fine as a *default*, but ambitious tiers need these to be
  recipe-declared (with the trigger **reported**, not only auto-failed).
- `evaluators.no_touch_violations`: ">1.5 ft fill over >20% of fan" uses the
  single-fan mask.

### 3.7 Hard-constraint gate shape

`hard_constraints()` returns one valid/invalid verdict. For tier comparison we
need *per-check* reporting (ADA / sightline / drainage / wall / bay-view each
pass-fail) so the audit gate can detect "aesthetics improved while a safety
check regressed" rather than collapsing to a single boolean.

### 3.8 Fill-only grading bias

Beyond the tread solver (§3.3), `ScenarioLibrary.validate_proposal` enforces a
net-zero rule oriented around small cut→fill circuits (warnings above
`max_cut 4.0` / `max_fill 3.0`). Ambitious/idealized tiers must be able to
declare larger caps and import/export assumptions explicitly in the recipe
rather than being silently warned.

## 4. What is already right (keep, don't rebuild)

- `ClayDelta` and its audit trail (`_ops`) — the P = E0 + Δ contract is exactly
  right and all new operations should keep appending to it.
- `EarthworkEngine` — volumes/yield/shrink/topsoil/haul are geometry-agnostic
  (pure delta-raster math) and reusable as-is; wall trigger only needs
  configurable thresholds.
- `DrainageEngine` storage/freeboard math (only the cell-geometry source needs
  to be parameterized).
- `SolarEvaluator`, `AestheticEvaluator.bay_view_score` (parameterize the
  upstage axis), `TerrainEngine`.
- `VariantManager` report-card pattern — tier outputs follow the same shape.
- Scenario E artifacts are complete and evaluator-ready:
  `analysis/scenarioE_civic/geometry.geojson` (45 tread polygons tagged
  role/row/section/seats_kept, cross-aisle, 2 switchback ramps + 5 landings,
  2 swales, shoulders, stage surfaces, construction envelope) +
  `earthwork.csv` (per-component CY, total 500.8) +
  `design_extended_bays/composition_table.csv` (per row×section elev, axis
  radius, length, seats, cross-angle, C_mm, sees_bay).
- `scripts/audit_in_situ_package.py` already enforces the
  no-design_open_low-regression rule for the in-situ package; the tier gates
  extend the same doctrine to the harness.

## 5. Retrofit architecture

New subpackage `scripts/harness/tiers/` (additive — nothing in the existing
modules is deleted; `agent.py`'s LLM loop keeps working against
`design_open_low` until separately migrated):

```
scripts/harness/tiers/
  geometry_model.py   SectionSeatingModel: rows × {east,bend,south} loaded from
                      Scenario E geometry + composition_table — the mutable
                      geometry counterpart to ClayDelta. No shared arc centre.
  operations.py       New primitives (recipe-driven): extend_section, trim_section,
                      morph_row_family, smooth_row_end_shoulders,
                      solve_cross_aisle_plane, refit_stage, faceted_apron,
                      select_borrow_zone, apply_cut_fill_caps, low-wall triggers.
                      Terrain effects land in ClayDelta; geometry effects in the
                      SectionSeatingModel. Both keep audit trails.
  recipes.py          Load/validate configs/intervention_tiers/*.yaml.
  evaluator.py        TierEvaluator: ONE evaluator class for every scenario
                      (identity hash recorded in outputs so the gate can prove it).
  cost_model.py       configs/cost_assumptions.yaml → cost ranges.
  gates.py            Audit gates (baseline lock, same-evaluator, no-regression,
                      ambitious-reporting, no-design_open_low-governing).
scripts/run_intervention_tiers.py   driver → analysis/intervention_tiers/
```

**Scenario E lock:** SHA-256 of `analysis/scenarioE_civic/geometry.geojson`,
`earthwork.csv`, and `design_extended_bays/composition_table.csv` pinned in
`configs/intervention_tiers/_baseline_lock.json`. The gate fails any run where
the hashes drift — Scenario E inputs are read-only to the tier system.

**Tier recipes** (`configs/intervention_tiers/*.yaml`): declare base geometry
(always Scenario E artifacts), allowed operations + parameters, constraint caps
(max cut/fill, wall policy, no-touch), and scoring weights. Five tiers:
`Scenario_E_baseline` (no ops — control), `modest_normalization`,
`optimized_civic_bowl`, `ambitious_shaped_bowl`, `idealized_reference_geometry`.

**Common evaluator output per scenario:** seats by quality band (per-section,
C-banded on the proposed surface); sightline distribution; east/bend/south
balance; stage-axis mismatch + lateral offset; row-1 gaps by family;
performer-to-seat distance distribution; ADA route + cross-aisle slope checks;
cut/fill/net/gross CY; max cut/fill depth; disturbed area; drainage/treatment
conflicts; bay/cell/sky obstruction; acoustic proxy; operations score;
wall/structure triggers — plus cost ranges and cost-effectiveness vs Scenario E.

## 6. Known constraints carried into the retrofit

- Open-air landscape venue: no view-blocking upstage wall; bay+sky backdrop.
- Stage judged by **incremental obstruction vs the NW rim silhouette**, never
  height (stage visual-envelope rule); Rule 9 stays OPEN — `refit_stage` is an
  *operation a recipe may invoke*, and its output must surface mismatch/offset
  metrics, not silently declare the fan resolved.
- Treatment cell function preserved (storage ≥90%, freeboard ≥1 ft).
- Escarpment/retaining-wall doctrine: walls are an *emergent output*
  (`wall_trigger`), never an input zone.
- Planning grade: cost model outputs **ranges**; cross-slope survey, geotech,
  swale hydrology remain data-gated externals.
