# Petoskey Pit Amphitheatre

Planning-grade civic bowl design for a proposed outdoor performance venue at the Petoskey Pit site in Petoskey, MI (45.373 N, 84.953 W). Seats on a natural rake descending toward the bay; stage at grade looking across the treatment cell toward Little Traverse Bay.

## What this is

An agentic-clay LLM harness that generates, evaluates, and validates bowl layout variants against a constrained set of civic and physical requirements: formal seating capacity, sightline C-values, ADA accessibility, earthwork volume, drainage, bay-view preservation, and landform fit.

The core principle: every cost-bearing design move must emit real geometry and pass polygon-intersection validation before it can appear in a cost table. Intent-only routes and inherited assumptions are machine-rejected.

## Current status

| Item | Status |
|---|---|
| Scenario D — formal seating baseline (1 452 seats, +26 CY restoration) | ACCEPTED |
| Scenario E — seating + aisles + ADA + drainage (500.8 CY) | ACCEPTED (seating/ADA/drainage) — **remains the validated control** |
| Intervention tiers — emission validation (2026-06-11) | **VALIDATED**: modest +114 seats / 25.3 CY; ambitious seating scope +262 / 47.3 CY; **N1 east extension REJECTED (0 of +149 seats survive emission)**. Adoption decision **OPEN** — see `docs/POST_EMISSION_DECISION_MEMO.md` |
| Scenario E — stage configuration | **OPEN** — Rule 9 unresolved; P_opt/apron/typologies are candidates only. Closure path: `analysis/stage_adoption/STAGE_RULE9_DECISION_TEMPLATE.md`. Claude Design handoff PAUSED |

**The two live decisions** (controlling doc: `docs/POST_EMISSION_DECISION_MEMO.md`):
(1) advance Scenario E baseline, validated modest_normalization (+114), or validated
ambitious seating scope (+262); (2) close Rule 9 for the stage.

## Key documents

- `docs/POST_EMISSION_DECISION_MEMO.md` — **controlling statement of project state + the two live decisions**
- `docs/DESIGN_CANON.md` — governing invariant rules (all scenarios)
- `docs/in_situ_design_brief.md` — three-section civic bowl in-situ package: three boards, layer inventory, assumptions, audit gate
- `INEVITABILITY.md` — narrative rationale and the "inevitable" design standard
- `SCENARIO_E_CIVIC.md` — Scenario E geometry, validation, and acceptance criteria
- `analysis/stage_refit/STAGE_REFIT_SWEEP.md` — stage alignment audit and refit candidates
- `PROBLEM_DEFINITION.md` — constrained multi-objective layout problem definition

## What not to overclaim

- Earthwork quantities are planning-grade (1 ft DEM, LOD ±0.05 ft). Not contractor-grade.
- ADA ramp surfaces: running slope designed to 8.33% by switchback geometry; raster cross-slope needs survey confirmation before construction documents.
- Swale drainage: geometric fall confirmed toward NE pour point; hydraulic sizing is data-gated pending soil and hydrology study.
- Scenario E stage: inherited geometry, not yet validated against emitted seating. See `DESIGN_CANON Rule 9`.

## Speckle review boundary (object-truth boundary)

The repo runs a **side-by-side 3D workflow**: the authoritative GIS/design repo
on one side, a [Speckle](https://speckle.systems) server as a **versioned review
surface** on the other. The boundary between them is strict and one-directional:

> **Speckle is for review, comparison, and collaboration. It is *not* design
> truth.** The Python/QGIS validation repo — its gates, its `validation.json`,
> its `verify_unreal_export.py` — is the **only acceptance authority.** Nothing
> rendered, measured, or edited in Speckle becomes design truth until it has
> returned as a proposal GeoJSON in EPSG:6494 and passed those gates.

The bridge is a downstream derivation, never a substitute for the gates:

```
repo (authoritative) ─► unreal_export/ (validated viewer layer) ─► speckle_export/*.json ─► Speckle (review)
        ▲                       gates run here                          │
        └──────────── proposal GeoJSON must pass the gates ◄────────────┘  (the only way back to truth)
```

- **`scripts/export_speckle_payload.py`** reshapes the *validated* `unreal_export/`
  artifacts into Speckle objects. It **recomputes nothing** — `C_mm`, seat
  counts, ADA status strings, cut/fill, and the planning-grade warnings are
  copied verbatim. Every leaf object preserves `source_file`, `feature_id`, a
  derived `row_id`, its C-value, ADA status, cut/fill, and the warnings; the
  lossless EPSG:6494 source geometry rides in `@geo_epsg6494` while the rendered
  geometry is the local ENU-metre frame (viewer float precision).
- **`scripts/publish_speckle.py`** is **dry-run-first**. It **refuses to publish**
  unless (1) `scripts/verify_unreal_export.py` exits 0, (2) the payload passes the
  object-truth boundary checks, and (3) the branch prefix matches the acceptance
  state. The default run sends nothing and imports no SDK; only `--publish` (with
  `SPECKLE_TOKEN`/`SPECKLE_PROJECT_ID`) performs a real send, lazily importing
  `specklepy` into the project venv.
- **`scripts/test_speckle_payload.py`** proves the boundary: missing provenance,
  missing validation fields, strengthened ADA status, dropped warnings, a
  branch/state mismatch, and a failed Unreal-export verification each **block**
  publication.

**Branch / stream naming conventions** (Speckle v3 calls a stream a *project*
and a branch a *model*; one project per venue, `petoskey-pit-civic-bowl`):

| State | Branch / model name | Meaning |
|---|---|---|
| **accepted** | `accepted/scenario-e-baseline` | the validated control. Provisional/concept elements (stage Rule 9 OPEN, ADA concept, treatment cell) ride inside it **individually flagged** `must_label` — inclusion never promotes them |
| **proposal** | `proposal/<topic>-<yyyymmdd>` | a not-yet-accepted bundle for review/comparison (e.g. `proposal/ambitious-seating-20260611`, `proposal/ada-concept-c-hybrid-20260612`) |
| **reference** | `reference/<topic>` | non-decision context (`reference/terrain-existing`, `reference/cameras-human-scale`) |

The publisher enforces that an `accepted/*` branch carries `acceptance.state =
accepted` and a `proposal/*` branch carries `proposal` — the accepted/proposal
distinction is enforced, not cosmetic.

Self-hosting the review server: **`docs/proxmox_speckle.md`** (Docker Compose on
Proxmox — reverse proxy, storage, backups, private-network assumptions).

## Running the scripts

All scripts require the project virtual environment. From the repo root:

```sh
bash scripts/build_in_situ_package.sh      # build + audit the in-situ package (boards, vectors, rasters)
python scripts/scenarioE_civic.py          # re-emit Scenario E geometry + validation
python scripts/stage_refit_sweep.py        # re-run stage alignment audit
python scripts/score_inevitability.py      # B-rejected / D-accepted proof
python scripts/validate_scenarioB.py       # Scenario B spatial validation
python scripts/test_cross_aisle_provenance.py  # provenance regression test

# Unreal handoff + Speckle review bridge
python scripts/build_unreal_export.py      # build the validated viewer package (unreal_export/)
python scripts/verify_unreal_export.py     # 30 acceptance gates (must be green)
python scripts/export_speckle_payload.py   # unreal_export/ → speckle_export/*.speckle.json
python scripts/publish_speckle.py          # DRY RUN review publish (gated; --publish to send)
python scripts/test_speckle_payload.py     # boundary tests (failures must block publication)
```
