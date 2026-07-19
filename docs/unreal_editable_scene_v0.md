# Unreal Editable Scene v0 — constrained authoring that returns to the gates

**Status:** design / plan. Creates **no** geometry, validation output, or ledger
entry yet. It specifies how the read-only handoff (`docs/unreal_handoff_v1.md`)
becomes an **editable** scene — a user placing benches, trees, and stage elements,
or reshaping the ground — **without** ever making Unreal an acceptance authority.

**Committed direction: parametric / constrained authoring.** Edits are expressed
as *typed, parameterized operations on validated objects* (place a catalog prop,
nudge a bench within its allowed envelope, add/modify a terrace op), never as a
freehand vertex/heightfield sculpt.

> **Freehand sculpt is an explicit NON-GOAL.** Free-form landscape sculpting would
> force the lossy inverse problem (arbitrary mesh/heightfield → georeferenced DEM →
> re-fit design intent) that the agentic-clay op-ledger was built to avoid, and it
> cannot be kept always-gateable. If freeform is ever wanted, it is a separate
> proposal, not this one.

Companions:

| Companion | Role |
|---|---|
| `docs/unreal_handoff_v1.md` | the governance contract this extends; §7 is the prose seed of the return path |
| `docs/TERRAIN_OPS_LEDGER.md` + `design/terrain_ops.current.json` | agentic-clay: terrain as an auditable per-op ledger (the Tier-B substrate) |
| `data/unreal_handoff_manifest.json` | machine index: per-layer source, sha256, role, `mcp_runway` boundary |
| `unreal_export/manifests/actor_manifest.json` | the both-way anchor table (local-metre + EPSG:6494) editable objects reuse |
| `scripts/verify_unreal_export.py` | `gate_roundtrip` — the tested inverse of the coordinate contract |
| `docs/speckle_publish_ledger.md` | the acceptance-ledger discipline every proposal still passes |

The authoring loop, end to end (extends the handoff runway into a closed loop):

```
repo truth ─▶ export ─▶ Unreal scene ─▶ constrained edit ─▶ proposal artifact (EPSG:6494)
     ▲            (real-time in-editor constraint feedback)                      │
     │                                                                          ▼
ledger + promote ◀─ maintainer fold-in ◀─ owning gate(s) PASS ◀─ diff (speckle_compare)
```

Unreal proposes; **the gates decide; the ledger records.** Nothing below changes that.

---

## 1. The two invariants (unchanged)

1. **The repo is the sole acceptance authority.** Python/QGIS gates +
   `data/speckle_publish_ledger.json`. An edit in Unreal is a *proposal* until a
   gate passes and a maintainer folds it in. Making the scene writable does not
   move, copy, or weaken this authority.
2. **Every editable thing is typed and identified.** An edit targets an object
   with a stable `feature_id` / `op_id` and a declared `object_class`; the round
   trip preserves that identity so a re-import diffs as *"moved bench #4"*, never
   *delete-all + add-all*.

These make every constrained edit **always re-validatable** and **always
diffable** — the property freehand sculpting cannot offer.

---

## 2. Object model — what "editable" means per class

Each editable class declares an **authoring envelope**: which parameters a user
may change, and the hard bounds inside which the edit stays gateable.

| Class | Authoring verb | Free parameters | Hard envelope (enforced) |
|---|---|---|---|
| **Site furniture** (bench, tree, planter, bin, bollard) | place / move / rotate / remove | position (x,y), yaw, catalog variant | inside site boundary; snap to validated surface; **no collision with ADA clear route, egress, seating treads, stage deck**; per-class spacing/count sanity |
| **Stage elements** (riser, speaker, lighting truss, set piece — *decoration, not the Rule-9 deck*) | place / move within stage envelope | position, yaw, variant | inside stage footprint; clear of the Rule-9-open deck geometry; provisional/`must_label` preserved |
| **Terrain** (the ground itself) | add / modify / remove a **terrace op** | op parameters (band radius, riser height, tread width, drainage…) | the agentic-clay gates **G1–G6** + coupled gates (§4) |
| **Structural seating / ADA / stage deck** | *not* directly editable | — | changes here are a terrain/design proposal, re-run the full suite; never a furniture edit |

The furniture and stage-element classes are **new**; the terrain class already
exists as the op-ledger. Structural classes stay in `MCP_DISALLOWED` for direct
edits (see §7).

---

## 3. Tier A — prop placement (the Phase-1 spike)

Additive objects that sit *on* the validated surface and touch no authoritative
geometry. This is the cheapest complete trip through the whole authoring loop, so
it is where the loop should be built first.

What must be built:

1. **Prop catalog** — `assets/props/catalog.json`: for each `object_class`, a UE
   mesh reference, footprint polygon, default variant set, and placement rules
   (surface classes it may sit on, min spacing, keep-clear classes). New artifact.
2. **Placement capture (UE → data)** — an editor-utility / MCP tool that reads the
   placed actors under an authoring root, and for each emits `{feature_id,
   object_class, variant, position, yaw}`. It **reverses the coordinate contract**
   (UE cm / Y-up / ×100 → EPSG:6494 intl ft / NAVD88) using the same inverse as
   `verify_unreal_export.gate_roundtrip`; a round-trip fidelity test gates it.
3. **Furniture proposal schema** — a point-feature GeoJSON in EPSG:6494 written to
   `requests/proposal_furniture_<topic>_<date>.geojson`, each feature carrying
   `feature_id`, `object_class`, `@review` provenance (placed_by, base build
   commit, timestamp). Mirrors the existing `@review` leaf convention.
4. **Light gate** — `scripts/validate_site_furniture.py`: in-boundary, surface
   snap/height sanity, **collision with the ADA clear route / egress / seating /
   stage** (the sharp one), per-class spacing/count. Exit 0 = promotable. This is
   a *fraction* of the grading suite — props do **not** recompute the DEM, seats,
   C-values, or earthwork, so those gates do not run.
5. **Furniture layer + promotion** — on PASS a maintainer folds the proposal into a
   tracked `vectors_geojson/site_furniture.geojson`; `build_unreal_export.py` gains
   a furniture layer; `build_unreal_handoff_manifest.py` indexes it (role
   `additive-furniture`, `editable_in_unreal: placement-only`).
6. **Diff + record** — reuse `speckle_compare.py` to show added/moved/removed props
   vs the accepted set, and the publish ledger to record acceptance (a furniture
   proposal is just another `proposal`-channel payload).

Phase-1 acceptance criteria: *place a bench in the editor → capture → proposal
GeoJSON → `validate_site_furniture.py` PASS → collision case for a bench dropped
on the ADA route FAILS → promote → re-export shows the bench as an additive layer,
audited design groups unchanged.*

---

## 4. Tier B — earthwork as op authoring (not sculpting)

Reshaping the ground changes the **authoritative surface**, so it cascades into
every downstream gate. The architecture is already chosen: terrain is a build
product of the **agentic-clay op-ledger** (`design/terrain_ops.current.json`,
`build_terrain_ops.py`, gates `G1–G6`, `proposal → current` promotion). "Editable
earthwork" therefore means **authoring ops**, not deforming a mesh.

What must be built on top of the op-ledger:

1. **Op handles in-editor** — surface the ops as manipulable gizmos: a band radius,
   a riser height, a tread width map to op parameters, so dragging a handle edits
   the *op*, not the triangles. `unreal/ue_terrace_ops.py` already applies ops
   repo→UE; this adds the UE→op parameter capture (the missing reverse).
2. **Regenerate + validate** — capture → modified `terrain_ops.proposal.json` →
   `validate_terrain_ops.py` (G1–G6) → **plus the coupled gates** that a grade
   change re-opens: cut/fill vs existing DEM, seat-tread re-emission + C-values (if
   the edit is under the bowl), ADA slope/landing/cross-slope re-solve, sightlines,
   drainage. Moving the stage that requires regrade **re-opens `DESIGN_CANON` Rule 9**.
3. **Precision discipline** — the inverse must reverse the ×100 UE scale and the
   NAVD88 (Geoid12A) vertical datum exactly; earthwork CY is already known
   understated ~2–2.6× vs raster truth, so op→surface→quantity must be reconciled
   against the raster, not the component-sum proxy.
4. **New grading op-classes** (beyond the 6 terrace ops) as needed — path regrade,
   mound, swale — each a typed op with its own G-gate, so a "new earthwork" is still
   a ledger entry, never a freehand patch.

Tier B is large and lands after Tier A proves the loop. It should extend the
terrain-ops-ledger stream (PR: *agentic clay*), not fork a parallel one.

---

## 5. The return-path spine (shared by both tiers)

Today `edit_return_path` is prose in the handoff manifest and the reverse export is
`MCP_DISALLOWED`. The spine turns that into a **controlled, gated** export:

1. **Capture** placed/edited objects under an authoring root → typed records.
2. **Reverse-transform** to EPSG:6494 / NAVD88 with a round-trip fidelity test
   (extend `gate_roundtrip`; fail closed on tolerance breach).
3. **Emit** a single-purpose proposal under `requests/` with preserved identity +
   `@review` provenance (base build commit, author, timestamp).
4. **Diff** with `speckle_compare.py` (proposal vs accepted).
5. **Gate** with the owning validator(s) — light for furniture, full suite for grade.
6. **Promote**: on PASS a maintainer folds it into authoritative sources, rebuilds
   the export + manifest, and (if reviewed in Speckle) re-publishes through the
   guarded path and **adds a ledger entry**.

Steps 1–3 are the genuinely new engineering; 4–6 already exist and are reused.

---

## 6. In-editor constraint feedback (what makes it *feel* like a map editor)

Correctness comes from the gates; **usability** comes from surfacing the same
constraints live, so a user edits with guardrails instead of discovering rejection
at gate-time:

- slope shading and a running **cut/fill total** while dragging a terrain op;
- **ADA clear-route / egress / seating** highlighted as keep-clear volumes that a
  prop cannot enter (snaps back or turns red);
- surface snap + footprint collision preview for furniture;
- provisional / Rule-9 / planning-grade labels always visible on the objects they gate.

Implementation: port a **read-only subset** of the gate logic into the editor, or
drive a fast MCP round-trip against the real validators. Optional for correctness,
essential for the experience — but it must never become a *second* authority; the
repo gate is still the decision.

---

## 7. MCP boundary changes

The `mcp_runway.allowed` / `disallowed` lists (machine-readable in the manifest)
move a bounded set of operations from disallowed to **allowed-as-proposal-only**:

- **New allowed (proposal-only):** place/move/remove **catalog furniture**; place
  stage **decoration** within the stage envelope; author/modify a **terrain op**
  within its G-gate envelope — each captured to a `requests/` proposal, never
  written to `vectors_geojson/`, `dem/`, or `truth_package/` directly.
- **Still disallowed:** editing structural seating/ADA/stage-deck geometry or
  elevations directly; changing seat counts / C-values / ADA slopes / earthwork
  *quantities* by hand; recolouring a provisional element to read as accepted;
  writing back in Unreal units without reversing the coordinate contract.

The boundary stays **data**, so an MCP bridge keeps enforcing it.

---

## 8. Phasing

| Phase | Scope | Risk | Proves |
|---|---|---|---|
| **1** | Prop placement (Tier A) end to end | low | the whole authoring loop on the cheapest payload |
| **2** | Constrained moves + identity/diff (bench move, stage decoration) | low–med | round-trip identity + `speckle_compare` deltas |
| **3** | Earthwork as op authoring (Tier B) on the agentic-clay ledger | high | grade edits re-validate through G1–G6 + coupled gates |
| **4** | In-editor real-time constraint feedback | med | "video-game-map" UX without a second authority |

Build the spine (§5) once, in Phase 1; Phases 2–4 reuse it.

---

## 9. Open questions to resolve before Phase 1

- **Catalog ownership** — who curates `assets/props/catalog.json` and the UE meshes,
  and where do the meshes live relative to the repo truth boundary?
- **Authoring root convention** — the UE Outliner root(s) the capture tool reads
  (parallel to PR #2's `TerrainOps_OpenCivicBowl`), so capture never scoops up
  imported design geometry.
- **`feature_id` minting** — how a *newly placed* prop (no source feature) gets a
  stable id that survives round trips and merges.
- **Terrain-ops alignment** — the op-ledger currently targets the Open Civic Bowl
  16-row fan; Tier B needs it re-pointed at Scenario E for row-for-row alignment
  (already flagged as a follow-up on the agentic-clay PR).
