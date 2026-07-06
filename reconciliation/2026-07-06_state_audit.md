# Reconciliation judge — repo/export state vs. source-of-truth invariants

**Date** 2026-07-06 · **Judge baseline** `docs/DESIGN_CANON.md` + `docs/POST_EMISSION_DECISION_MEMO.md`
+ `gating_dossier.md` + `DATA_GAPS.md` (the append-only decision/correction log) · **Datum**
EPSG:6494 / NAVD88 Geoid12A intl ft · **Scope** read-mostly audit — no Unreal editor mutation,
no remote machines, no external data downloads, no deletion. This report proposes; it does not
execute.

## Decision rule applied

> An artifact is **CURRENT** if its content matches the latest state of every authority
> document it depends on, as of its own generation/edit timestamp. If a later authority-doc
> update exists that it does not reflect, it is **STALE** and must be flagged — not trusted,
> and not silently corrected — until it is regenerated or hand-corrected under review.
> No artifact is deleted. No mutation (doc fix, script regen, worktree merge, or Unreal
> import) is executed by this audit; each is proposed below and requires separate approval,
> extending the same review gate this repo already applies to Speckle publishes
> (`docs/speckle_publish_ledger.md`: "nothing becomes design truth until it passes the gates")
> to documentation and generated-truth-snapshot artifacts.

This is the second instance of this repo's judge pattern — the first is
`reconciliation/conflict_notes.md` (2026-06-27, terrain-editor candidates). That audit judged
*branches*; this one judges *current doc/export state* against the invariant chain, following
the same method: state the rule, build a matrix, verify independently, record what's
unresolved.

## 1. Source-of-truth chain (what this audit treats as ground truth)

- `PROBLEM_DEFINITION.md` axioms **A1** (DEM is sole truth for existing grade) and **A2** (no
  retaining wall is ever an input; it is only emergent infeasibility) and constraints
  **H1–H7** (sightline, drainage, no-wall, earthwork balance, ADA, bay-view, no-touch zones).
- `docs/DESIGN_CANON.md` (updated 2026-07-03) — design-of-record table and the 9 numbered
  invariant rules, most load-bearing here: **Rule 9** (stage geometry/fan declaration).
- `docs/POST_EMISSION_DECISION_MEMO.md` (updated 2026-07-02) — "the controlling statement of
  project state," Decisions 1 and 2.
- `gating_dossier.md` — field-data gate closures (e.g. A-1 datum offset).
- `DATA_GAPS.md` — running corrections log, most recent entry 2026-07-06 (site identity).

These four are append-only and mutually consistent as of their own latest edits. Everything
judged below is either a **generated snapshot** of this chain (`truth_package/*.current.json`,
`unreal_export/`) or a **hand-authored summary** of it (`README.md`, `executive_summary.md`)
— i.e. materialized views that can lag their source, exactly as `node_states`/`leases` can lag
the event log in an event-sourced system. The audit's job is to check replay-vs-cache.

## 2. Reconciliation matrix

| Artifact | Generated/edited | Depends on | Verdict | Evidence |
|---|---|---|---|---|
| `truth_package/design_state.current.json`, `evaluation_report.current.json` | 2026-07-04 18:32 (`build_truth_package.py`) | `docs/DESIGN_CANON.md` (2026-07-03), `gating_dossier.md` (A-1 closed 2026-06-06) | **STALE** (two independent defects, both in the artifact meant to be the current machine-readable truth) | See §3.1, §3.2 |
| `README.md` status table | 2026-06-18 | `docs/POST_EMISSION_DECISION_MEMO.md` (2026-07-02), `docs/DESIGN_CANON.md` (2026-07-03) | **STALE** | See §3.3 |
| `README_UNREAL.md` datum caveat | carries `design_state` value verbatim | `gating_dossier.md` A-1 | **STALE** (inherits §3.1's defect) | `README_UNREAL.md:90-91` still reads "+0.40 ft... unconfirmed" |
| `executive_summary.md` | 2026-07-02 | `DATA_GAPS.md` 2026-07-06 site-identity correction | **STALE and actively wrong** | line 3: "Bayfront Park, Petoskey, Emmet County, Michigan" — `DATA_GAPS.md` names this exact framing as one that "must not be propagated" |
| `harness_config.yaml` `design.baseline_dir: design_open_low` | unknown | `truth_package/data_inventory.md` (2026-06-11: `design_open_low/seating_rows.geojson` named superseded) | **FLAGGED RESIDUE**, not confirmed harmful | naming only; did not trace whether any script trusts this path as governing at runtime (see §5 unknowns) |
| `terrain-ops-ledger` worktree (`a4842a1`, 2026-06-29) | 2 days after the 2026-06-27 judge run | never entered `reconciliation/conflict_notes.md`; scoped to `design_open_low` | **UNRECONCILED — highest priority** | confirmed `git merge-base --is-ancestor a4842a1 main` fails; confirmed `main`'s `unreal_export/geo/` has none of the worktree's `terrace_ops/*` files |
| `context-reclassify` worktree untracked files | matches its already-recorded verdict | `reconciliation/conflict_notes.md` line 21 ("keep as separate context patch") | **Consistent but unlanded** | files still sit untracked in the worktree; the "separate patch" they were routed to was never actually created |
| `sunset-scene-authoring`, `terrain-cutfill-audit` worktrees | fully merged, clean | — | **Redundant, safe to remove** | both confirmed ancestors of `main`; `git status` clean in each |
| `00_START_HERE.md` | referenced, never created | `executive_summary.md`, `gating_dossier.md` both cite it as master index | **Dangling reference** | confirmed absent via `find` and full git history search |
| `speckle_export/{accepted,proposal}.speckle.json` | 2026-06-17 | `README.md` "Speckle review boundary" section | **CURRENT — working as designed** | distinct md5s, correct `applicationId`/`rationale` per the documented `accepted/*` vs `proposal/*` branch convention |
| `unreal_export/manifests/provenance.json` | 2026-07-04 18:36 | upstream source files (sha256-tracked) | **CURRENT by construction** | per-file hash manifest; but see §4 for a caveat about what it can't see |

## 3. Independent verification performed by the judge

### 3.1 — `truth_package` did not ingest the closed datum gate

`gating_dossier.md` line 23: **"A-1 ✅ CLOSED 2026-06-06 ... NAVD88 = IGLD85 + 0.162 ft. Prior
assumption (+0.40 ft) was ... high by ~0.24 ft; no design decisions change."** Grepping the
generated snapshot built almost a month later (2026-07-04):

```
truth_package/evaluation_report.current.json:142:  "IGLD85↔NAVD88 Δ confirmation (working +0.40 ft assumed)"
truth_package/design_state.current.json:291:       "IGLD85↔NAVD88 Δ confirmation (working +0.40 ft assumed)"
```

Both still list it under `missing_data` as unconfirmed, using the exact superseded phrasing
from `truth_package/data_inventory.md` (2026-06-11). `README_UNREAL.md:91` carries the same
stale value into the Unreal-facing doc. `build_truth_package.py` has a source it isn't
reading, or isn't re-reading on rebuild.

### 3.2 — `truth_package`'s own declared authority contradicts its output

`truth_package/design_state.current.json` lists `docs/DESIGN_CANON.md` as an authority source
(line 10) and was generated 2026-07-04 — one day *after* `DESIGN_CANON.md`'s 2026-07-03
update. Yet:

- `design_state.current.json:116`: `"status": "PROVISIONAL — Rule 9 OPEN; no adoption path declared"`
- `DESIGN_CANON.md:143`: **"Adopted (carried_provisional, 2026-07-02) — a bundle, not a
  placement:"** placement path 3 = P_opt + path-4 wide-fan + five_facet_apron + T1_deck_only,
  with an explicit closure path pending only a package-audit re-run.

`carried_provisional` (a documented decision state) and "no adoption path declared" are not
the same claim. The generator is stale relative to a source it names as authoritative.

### 3.3 — `README.md` predates the un-pause

`README.md` line 18: **"Claude Design handoff PAUSED"** (last touched 2026-06-18).
`docs/POST_EMISSION_DECISION_MEMO.md` line 66 (2026-07-02): **"Claude Design is UN-PAUSED,
stage flagged provisional."** `README.md` is the oldest of the five docs in this tension
(06-18, vs. memo 07-02, canon 07-03, truth_package 07-04, DATA_GAPS 07-06) and reads as the
stalest single file in the repo relative to its own stated role as the entry point.

### 3.4 — `terrain-ops-ledger` unmerged status, confirmed directly

```
$ git merge-base --is-ancestor a4842a1 main
NOT an ancestor (unmerged)
$ ls unreal_export/geo/     # on main
ada_route.geojson  human_scale_refs.geojson  seating_rows.geojson  seating_row_splines.geojson  stage_floor.geojson
```

None of the worktree's `unreal_export/geo/terrace_ops/{clip_mask,drainage_bands,riser_faces,
seat_caps,grade_p_current,stage_floor,ada_paths}.geojson` exist on `main`. The worktree's own
commit message claims a **live import into the running Unreal Editor** ("Imported live into
`/Game/Maps/CivicBowl` via the UnrealEditor MCP server: 88 per-op static meshes... Additive;
audited design groups unchanged") — meaning the live scene state, if that claim is accurate,
may currently diverge from both `main` and from `unreal_export/manifests/provenance.json`'s
last recorded hash set. **This audit cannot verify or refute the live-import claim** — no
Unreal MCP tool was connected in this session (see §5).

## 4. What's working as designed (not everything here is a defect)

The Speckle accepted/proposal boundary, the `publish_speckle.py` dry-run-first gate, and the
`unreal_export/` provenance-hash convention are all functioning exactly as `README.md`'s
"Speckle review boundary" section and `README_UNREAL.md` describe. The failure mode found in
this audit is concentrated in **doc/snapshot staleness and one unreconciled worktree** — not
in the generation/gating scripts themselves, which appear sound where they run.

## 5. Explicit unknowns (not resolved by this audit)

- **Live Unreal scene state** — whether `/Game/Maps/CivicBowl` actually contains the
  `terrain-ops-ledger` worktree's claimed 88 per-op meshes is unverified. This audit's session
  had no Unreal MCP bridge connected (the repo's own `.mcp.json` configures one at
  `http://127.0.0.1:8000/mcp`, but it wasn't reachable from here). This is the single most
  decision-relevant unknown in this report: judging the ledger worktree without first reading
  the live scene risks judging against a false picture of current state.
- **Whether `harness_config.yaml`'s `baseline_dir: design_open_low` is load-bearing** — not
  traced whether any currently-run script treats this as governing geometry vs. a harness
  optimization seed. Flagged, not confirmed.
- **Whether `context-reclassify`'s untracked files are still wanted** — no doc states intent
  to land them; they've sat untracked since before 2026-06-27.

**Key assumption made in this report**: that `docs/DESIGN_CANON.md` and
`docs/POST_EMISSION_DECISION_MEMO.md`, as the two most recently updated and mutually
consistent authority docs, correctly represent current project state, and that everything
older or machine-generated should be reconciled toward them — not the reverse. If that
assumption is wrong (e.g. if the 2026-07-02/03 "carried_provisional" adoption was itself
later reverted and no doc records the reversion), several verdicts above would flip.

## 6. Proposed next safe mutation plan (not executed — each item requires review before action)

1. **Judge `terrain-ops-ledger` (`a4842a1`)** through the same process as
   `reconciliation/conflict_notes.md`, but only after independently reading the live Unreal
   scene from a session with the MCP bridge connected. Highest priority — it's the only item
   here with a claimed live-mutation side effect on a shared, non-git resource.
2. **Regenerate `truth_package/*.current.json`** via `scripts/build_truth_package.py` after
   fixing the datum constant (0.162 ft) and the Rule 9 adoption-state ingestion at their
   source — a script re-run, not a hand-edit, consistent with "truth is generated, not
   asserted." Review the diff before commit.
3. **Hand-correct `README.md`'s status table and `executive_summary.md`'s site framing** to
   match `DATA_GAPS.md`/`DESIGN_CANON.md`/`POST_EMISSION_DECISION_MEMO.md`. Low risk, but
   `executive_summary.md` feeds the `requests/` outreach letters — review before sending
   anything downstream of it.
4. **Annotate or rename `harness_config.yaml`'s `baseline_dir`** to remove the "baseline"
   naming residue, once §5's unknown is resolved.
5. **Remove the two fully-merged worktrees** (`sunset-scene-authoring`,
   `terrain-cutfill-audit`) — no unique content, confirmed ancestors of `main`.
6. **Land `context-reclassify`'s untracked files** as the standalone context patch that
   `conflict_notes.md` already authorized, or explicitly abandon them.
7. **Resolve the `00_START_HERE.md` dangling reference** — create the doc-map file both
   `executive_summary.md` and `gating_dossier.md` assume exists, or remove the references.

None of the above is executed by this report. Per the audit's own scope constraints (no
Unreal editor mutation, no deletion, review required before any packet/projection), items 1–7
are recommendations awaiting explicit approval.

## 7. Artifacts (this folder)

| File | Contents |
|---|---|
| `2026-07-06_state_audit.md` | this report |
