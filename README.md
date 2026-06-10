# Petoskey Pit Amphitheatre

Planning-grade civic bowl design for a proposed outdoor performance venue at the Petoskey Pit site in Petoskey, MI (45.373 N, 84.953 W). Seats on a natural rake descending toward the bay; stage at grade looking across the treatment cell toward Little Traverse Bay.

## What this is

An agentic-clay LLM harness that generates, evaluates, and validates bowl layout variants against a constrained set of civic and physical requirements: formal seating capacity, sightline C-values, ADA accessibility, earthwork volume, drainage, bay-view preservation, and landform fit.

The core principle: every cost-bearing design move must emit real geometry and pass polygon-intersection validation before it can appear in a cost table. Intent-only routes and inherited assumptions are machine-rejected.

## Current status

| Item | Status |
|---|---|
| Scenario D — formal seating baseline (1 452 seats, +26 CY restoration) | ACCEPTED |
| Scenario E — seating + aisles + ADA + drainage (500.8 CY) | ACCEPTED (seating/ADA/drainage) |
| Scenario E — stage configuration | **OPEN** — stage refit required (see `DESIGN_CANON Rule 9`) |

## Key documents

- `docs/DESIGN_CANON.md` — governing invariant rules (all scenarios)
- `docs/in_situ_design_brief.md` — Open Civic Bowl in-situ package: three boards, layer inventory, assumptions, audit gate
- `INEVITABILITY.md` — narrative rationale and the "inevitable" design standard
- `SCENARIO_E_CIVIC.md` — Scenario E geometry, validation, and acceptance criteria
- `analysis/stage_refit/STAGE_REFIT_SWEEP.md` — stage alignment audit and refit candidates
- `PROBLEM_DEFINITION.md` — constrained multi-objective layout problem definition

## What not to overclaim

- Earthwork quantities are planning-grade (1 ft DEM, LOD ±0.05 ft). Not contractor-grade.
- ADA ramp surfaces: running slope designed to 8.33% by switchback geometry; raster cross-slope needs survey confirmation before construction documents.
- Swale drainage: geometric fall confirmed toward NE pour point; hydraulic sizing is data-gated pending soil and hydrology study.
- Scenario E stage: inherited geometry, not yet validated against emitted seating. See `DESIGN_CANON Rule 9`.

## Running the scripts

All scripts require the project virtual environment. From the repo root:

```sh
bash scripts/build_in_situ_package.sh      # build + audit the in-situ package (boards, vectors, rasters)
python scripts/scenarioE_civic.py          # re-emit Scenario E geometry + validation
python scripts/stage_refit_sweep.py        # re-run stage alignment audit
python scripts/score_inevitability.py      # B-rejected / D-accepted proof
python scripts/validate_scenarioB.py       # Scenario B spatial validation
python scripts/test_cross_aisle_provenance.py  # provenance regression test
```
