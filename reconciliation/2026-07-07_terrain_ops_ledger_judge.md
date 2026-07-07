# Reconciliation judge — terrain-ops-ledger worktree

**Date** 2026-07-07 · **Judge baseline** `DESIGN_CANON.md`, `POST_EMISSION_DECISION_MEMO.md`,
`gating_dossier.md`, `DATA_GAPS.md` (same authority chain as the 2026-07-06 state audit)
· **Datum** EPSG:6494 / NAVD88 Geoid12A intl ft
· **Scope** Item 1 of the 2026-07-06 state audit's proposed mutation plan: judge the
unmerged `terrain-ops-ledger` worktree (single commit `a4842a1`) for merge / partial
salvage / abandon. No mutation beyond this report is executed here — regeneration of
`truth_package`, doc fixes, and other-worktree cleanup remain out of scope pending
separate approval, per the calling instruction.

## Decision rule applied

> An unmerged candidate is mergeable only if the design geometry it depends on is still
> the accepted governing geometry as of today, and if the claims made in its commit
> message are corroborated by repo-local evidence. A candidate that targets retired
> geometry, or that lists a strict `read-mostly, no Unreal mutation` session, cannot be
> merged or executed against a live scene regardless of internal engineering quality.

**Verdict: ABANDON.** `a4842a1` is not merged, not partially salvaged, and not executed
against any live system in this session.

## 1. What the commit actually is

`a4842a1` ("Terrain-operation ledger (agentic clay) + live UE import", authored
2026-06-29 11:22) is a single commit on top of merge-base `8b0f161`, purely additive:
**111 files changed, 99,074 insertions(+), 0 deletions/modifications.** It adds 6 new
scripts (`build_terrain_ops.py`, `validate_terrain_ops.py`, `build_terrace_op_meshes.py`,
`viz_terrace_ops.py`, `terrace_ops_common.py`, `unreal/ue_terrace_ops.py`), a 106-operation
ledger (`design/terrain_ops.current.json`, schema `amphitheatre/terrain-ops/0.2`), 9
geojson layers and 88 per-op OBJ meshes under `unreal_export/`, a doc
(`docs/TERRAIN_OPS_LEDGER.md`), and two plan/section renders. It touches zero existing
files — no source-of-truth doc, no `truth_package` file, no `README.md` is modified.

Confirmed via `git merge-base --is-ancestor a4842a1 main`: **not an ancestor** (unmerged).

## 2. The geometry conflict — the actual reason to abandon

The commit's own doc states its scope up front (`docs/TERRAIN_OPS_LEDGER.md`, "Scope note
— read first"):

> "This work re-bases the auditable terrain-ops architecture on the **Open Civic Bowl
> 16-row open fan** (`design_open_low/`), which the task names as the accepted design to
> preserve... The 45-tread **Scenario E** bowl currently imported into the live UE scene
> is a separate seating-capacity study... It is not contradicted here."

`design/terrain_ops.current.json` confirms this in its own metadata:
`"design": "open_civic_bowl"`, `"op_count": 106`. Every op, mesh, and geojson layer in
this commit is built for `design_open_low`'s single-fan geometry, not Scenario E.

`docs/POST_EMISSION_DECISION_MEMO.md` — dated **2026-06-11, 18 days before `a4842a1` was
authored** — is explicit:

> "Geometry source for all three: Scenario E three-section civic bowl (east / bend /
> south, `design_extended_bays` composition). **`design_open_low`'s single-fan geometry is
> superseded for seating and must not be used as governing geometry** (it still sources
> only the inherited stage object and the treatment cell)."

This is not a case of the worktree going stale after the fact. The prohibition on
treating `design_open_low` as governing seating geometry was already standing project
policy a full 18 days *before* this worktree's commit was made. The commit's own doc
acknowledges Scenario E was already the live-scene design at authoring time, and proceeds
to build a 106-op ledger for the other design anyway, describing it as "the accepted
design to preserve."

Main's history since the merge-base doubles down on this, twice, after `a4842a1`:

| Commit | Date | What it does |
|---|---|---|
| `0e4ff10` | 2026-07-02 | Bannered `design_open_low/README.md` + `seat_count.md` **SUPERSEDED-FOR-SEATING**, quoting the same "must not be used as governing geometry" line, and removed those docs from the Claude project KB |
| `f713efb` | 2026-07-02 | Formally adopted Scenario E baseline (1,243 Band-A) as Decision 1; Rule 9 stays `carried_provisional` |
| `f2cf2b9` | 2026-07-04 | Further mutated Scenario E's own stage/ADA geometry (upstage pullback to open fan corners ≥20 ft, ADA forecourt re-route) |

So even bracketing the design-track conflict, the worktree's stage/ADA lineage
(`unreal_export/geo/terrace_ops/stage_floor.geojson`, `ada_paths.geojson`, inherited from
`design_open_low`) predates a *second* round of stage-geometry changes on the design that
is actually current. There is no version of "merge as-is" that lands on current geometry.

## 3. The "live UE import" claim — no repo-local evidence found

The commit message claims: "Imported live into `/Game/Maps/CivicBowl` via the
UnrealEditor MCP server: 88 per-op static meshes under Outliner root
`TerrainOps_OpenCivicBowl`... Additive; audited design groups unchanged."

Checked for corroboration:
- No scene/outliner snapshot, no post-import verification output, no screenshot of the
  Unreal Editor is committed anywhere in the 111 changed files. The two committed PNGs
  (`analysis/terrace_ops/aisle_cross_section.png`, `op_view_before_after.png`) are
  matplotlib-style plan/section renders generated by `viz_terrace_ops.py`, not editor
  captures.
- The repo's own pre-existing export gate, `scripts/verify_unreal_export.py` (last
  touched at ancestor commit `7436a78`, well before `a4842a1`), has **no reference to
  `terrace_ops` or `terrain_ops`** — it was never run against this worktree's outputs.
- No later commit anywhere in the repo (`git log --oneline --all -- '**/terrace_ops*'
  'design/terrain_ops*'`) references, builds on, or re-verifies this ledger. `a4842a1` is
  the only commit touching these paths in the entire history.
- `gating_dossier.md` and `DATA_GAPS.md` contain zero mentions of `design_open_low`,
  `open civic bowl`, `terrain_ops`, or `terrace_ops` — this worktree is invisible to both
  of those tracking docs.

This session has no Unreal MCP bridge connected (consistent with the "no Unreal editor
mutation" constraint), so the live scene state cannot be checked directly either way. The
claim is therefore **neither confirmed nor refuted by this session** — it remains exactly
the same open unknown flagged in the 2026-07-06 state audit (§5), not resolved by this
judge pass. What *is* new here: the repo itself offers no corroborating evidence, and the
one gate that could have corroborated it was never pointed at these outputs.

## 4. What's actually sound about it

Recorded for balance, and because it bears on the "partial salvage" question: the
per-op-ledger architecture (`op_id` scheme, gated proposal → accepted promotion via
`validate_terrain_ops.py`, drawover prevention via raster flattening + geometric clip
masks + render lift, deterministic mesh regeneration) is the same discipline the
2026-06-27 `terrain-cutfill-audit` judge commit endorsed and accepted elsewhere in this
repo. The engineering pattern is not the defect — the geometry source it was pointed at
is. The doc says as much itself: "can be applied to Scenario E later by pointing the
generator at that geometry." That is a real, separately-scoped future patch, not
something this commit already does.

## 5. Verdict and disposition

**ABANDON `a4842a1` as a merge candidate.** Do not merge, cherry-pick, or partially land
any file from this commit. Reasons: (1) it is built entirely on a design track that was
already prohibited as governing seating geometry 18 days before it was authored, (2) that
prohibition has since been reinforced twice and the current design has moved again since,
so there is no reconciliation that makes its geometry current, (3) its central factual
claim (live Unreal import) has no repo-local corroboration and cannot be checked this
session, and (4) merging it would deposit exactly the kind of stale/generated-artifact
clutter under `unreal_export/` and `design/` that the 2026-07-06 state audit was asked to
surface, not resolve.

**Not abandoned:** the architecture pattern itself, as an idea for a future patch that
regenerates the same op-ledger structure against current Scenario E geometry
(post-2026-07-04 pullback). That would be new work requiring its own worktree, its own
gating, and its own review — not a disposition of this commit.

**No mutation performed.** The worktree at
`.claude/worktrees/terrain-ops-ledger` (branch `worktree-terrain-ops-ledger`, commit
`a4842a1`) is left exactly as-is — not merged, not deleted, not rebased — pending explicit
approval to remove it. This report only records the judgment; removal (which would be
safe once approved, since the commit is fully described here and remains recoverable via
`origin/worktree-terrain-ops-ledger` regardless) is a separate action.

## 6. Explicit unknowns carried forward

- Live Unreal scene state (`/Game/Maps/CivicBowl` outliner contents) — still unverifiable
  without a connected Unreal MCP bridge. If a future session confirms
  `TerrainOps_OpenCivicBowl` meshes are actually present in the live scene alongside the
  Scenario E import, that is itself a reconciliation problem (two contradictory seating
  geometries in one map) requiring its own remediation — out of scope for this judge pass.
- Whether `docs/AMPHITHEATRE_COMPARATORS.md` (flagged as a known follow-up inside `0e4ff10`
  itself, "still benchmarks Petoskey using the retired 35 ft / 110° open-arc figures") has
  since been corrected — not checked in this pass; would be a natural companion item to
  the existing proposed-plan item on stale docs.

## 7. Artifacts (this folder)

| File | Contents |
|---|---|
| `2026-07-07_terrain_ops_ledger_judge.md` | This report |
