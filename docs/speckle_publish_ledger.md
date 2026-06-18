# Speckle publish ledger & acceptance discipline

This document describes the **repo-side publish ledger** and the
**scratch → proposal → accepted** publish lifecycle for the Petoskey Pit Speckle
review bridge. It is the Phase 2 layer on top of the object-truth boundary
documented in the repo `README.md` → *"Speckle review boundary"*.

> **The one rule this whole layer exists to enforce:**
> **Speckle version history is _not_ acceptance history.** A version on the
> Speckle server — even on an `accepted/*` model — means *someone published
> geometry*, nothing more. It becomes part of the project's acceptance record
> **only** when it is backed by an entry in
> [`data/speckle_publish_ledger.json`](../data/speckle_publish_ledger.json) whose
> `export_payload_hash` still matches the payload it published, derived from a
> gated, committed repo state. The Python/QGIS gates remain the **sole**
> acceptance authority; the ledger is the repo's record of which review versions
> actually mirror a gated state.

---

## 1. Why a repo-side ledger

The truth boundary is one-directional:

```
repo gates (authority) ─► unreal_export/ ─► speckle_export/*.json ─► Speckle (review)
```

Speckle will happily display anything anyone pushes. So "there is an `accepted/*`
model on the server" must never silently read as "this design was accepted." The
ledger closes that gap: it lives in the repo, is committed alongside the gated
state, and pins each published version to a content hash. The webhook receiver
([§6](#6-webhook-handshake)) then continuously checks the live server *against*
the ledger and flags any `accepted/*` version the repo has not ratified.

## 2. The lifecycle: scratch → proposal → accepted

Each publish goes to a **channel** (the `design_state`), encoded in the Speckle
model/branch prefix and recorded in the ledger. The
[`guard`](../scripts/publish_speckle.py) enforces a different discipline per
channel:

| Channel | Branch / model prefix | What it permits | Guard requires |
|---|---|---|---|
| **`scratch`** | `scratch/*` | render / debug / throwaway pushes | nothing — permissive. **Excluded from accepted ledger reports.** |
| **`proposal`** | `proposal/*` | visible alternatives for review/comparison | verify gate green · object-truth boundary clean · **carries `open_decisions` metadata** |
| **`reference`** | `reference/*` | non-decision context (terrain, cameras) | verify gate green · boundary clean |
| **`accepted`** | `accepted/*` | **only verified mirrors of a repo-accepted, committed state** | repo clean (or `--allow-dirty`) · verify green · boundary clean · `acceptance.state == accepted` · **no object carries an unresolved decision flag (e.g. `RULE-9-OPEN`)** |

The natural promotion path:

1. **scratch** — push a quick render to look at it in the viewer. Never claims to
   be anything. Never counted.
2. **proposal** — once it's a real alternative, publish it to `proposal/<topic>-<date>`.
   It must declare its `open_decisions` (auto-derived from the payload: Rule-9-OPEN
   stage, ADA concept routes, concept-tier elements — or add your own with
   `--open-decision`). A proposal is explicitly *not decided*.
3. **accepted** — only after the repo gates accept the state and the decisions are
   resolved. The guard refuses if the working tree is dirty, if any object still
   carries an open decision flag, or if the verify/boundary gates aren't green.
   The accepted bundle excludes the Rule-9-OPEN stage entirely (it ships as a
   proposal); the ADA concept rides inside individually flagged as proposal and is
   not promoted by inclusion.

> A proposal that has resolved *every* decision should be published as
> `accepted`, not as a "final proposal." The guard nudges this: a proposal with
> no open decisions is blocked.

## 3. Ledger entry fields

Every real publish appends one entry to `data/speckle_publish_ledger.json`
(`scripts/publish_speckle.py` writes it; a dry run only previews it). Fields:

| Field | Meaning |
|---|---|
| `timestamp` | UTC ISO-8601 of the publish |
| `design_state` | `accepted` \| `proposal` \| `scratch` \| `reference` (the channel) |
| `project_slug` | the venue project slug (`petoskey-pit-civic-bowl`) |
| `branch` | the Speckle model/branch name (`accepted/scenario-e-baseline`, …) |
| `project_id` / `model_id` / `version_id` | Speckle server identifiers (null on a dry-run preview) |
| `object_id` | the root object id the version points at |
| `speckle_url` | deep link `{server}/projects/{p}/models/{m}@{v}` |
| `source_git_commit` | the repo commit the payload was built from |
| `export_payload_hash` | `sha256:…` of the canonical payload — pins the entry to an exact artifact |
| `validation_commands` | the gate commands run (`verify_unreal_export.py`, the boundary check) |
| `validation_passed` | `true` / `false`; `null` for scratch (not a validated mirror) |
| `validation_detail` | per-gate booleans + boundary error count + repo-clean flag |
| `source_files` | sorted unique authoritative repo sources the bundle derives from |
| `open_decisions` | the known-open decisions carried (Rule-9-OPEN, ADA concept, …) |
| `notes` | free-text |

### The hash

`export_payload_hash` is the SHA-256 of the canonical (sorted-key) JSON of the
**whole** payload, including the build timestamp and `git_commit` in `bridge`. So
the hash identifies the *exact* artifact published — a rebuild produces a new
hash, by design. `scripts/speckle_ledger.py:verify_entry_hash(entry, payload)`
recomputes it; a mismatch means the payload on disk is not the one the entry
recorded (tampering, drift, or a rebuild) and the entry should not be trusted as
a mirror of that payload.

## 4. Publishing (and previewing) — `scripts/publish_speckle.py`

Dry run is always the default; it shows the exact ledger entry that *would* be
written and never touches the network or the ledger:

```sh
# preview the accepted publish + its prospective ledger entry (sends nothing)
python scripts/publish_speckle.py --design-state accepted

# a proposal (open_decisions auto-derived; add explicit ones if needed)
python scripts/publish_speckle.py \
    --payload speckle_export/petoskey_pit.proposal.speckle.json \
    --design-state proposal --open-decision "Decision 1: seating scope"

# a scratch render push (permissive, excluded from accepted reports)
python scripts/publish_speckle.py --design-state scratch \
    --payload speckle_export/petoskey_pit.proposal.speckle.json

# a real send (gated): only after the gates + guard pass
SPECKLE_TOKEN=… SPECKLE_PROJECT_ID=… SPECKLE_MODEL_ID=… \
  python scripts/publish_speckle.py --design-state accepted --publish
```

On a real `--publish`, the entry is appended to the ledger and you are reminded to
**commit the ledger** — that commit is what makes the publish part of the repo
record.

### The accepted guard, precisely

An `accepted` publish is **refused** unless *all* hold:

1. the working tree is clean, **or** `--allow-dirty` is passed deliberately;
2. `scripts/verify_unreal_export.py` exits 0 (the validated handoff is intact);
3. the Speckle payload passes the object-truth boundary
   (`speckle_common.validate_payload`);
4. the payload's `acceptance.state` is `accepted`;
5. **no** object carries an unresolved hard decision flag — the canonical one is
   `RULE-9-OPEN` (a Rule-9-open stage deck). The always-present ADA *concept/
   pending* caveat is **not** a blocker: it is a carried label on a flagged
   proposal sub-object, not an open binary decision.

## 5. Inspecting & comparing

```sh
# list the ledger (scratch hidden by default)
python scripts/speckle_ledger.py
python scripts/speckle_ledger.py --accepted-only         # the acceptance record only
python scripts/speckle_ledger.py --include-scratch       # everything

# diff an accepted bundle against a proposal
python scripts/speckle_compare.py \
    --accepted speckle_export/petoskey_pit.accepted.speckle.json \
    --proposal speckle_export/petoskey_pit.proposal.speckle.json
```

`speckle_compare.py` reports added/removed objects by class, changed seating row
ids, changed ADA route ids, changed stage/floor objects, validation deltas (seat
totals, warnings, boundary errors, leaf counts), and the unresolved decisions on
each side. Objects are matched by a stable key (seating rows by `row_id`,
everything else by `feature_id`); "changed" means a tracked review field or the
lossless source geometry differs.

## 6. Webhook handshake

`scripts/speckle_webhook.py` is a tailnet-local receiver that treats a Speckle
"version created" event as a **handshake only** — it never pulls geometry. Its job
is to check the event against the ledger and **flag any `accepted/*` version with
no valid ledger entry**:

```sh
# run the receiver (bind to the tailnet IP to keep it private)
python scripts/speckle_webhook.py --serve --host 100.64.0.10 --port 8765

# evaluate a single event file (exit 1 if it FLAGs)
python scripts/speckle_webhook.py --check event.json
```

Verdicts: `ok` (backed by the ledger) · `warn` (non-accepted, unrecorded) ·
**`FLAG`** (accepted/* with no ledger entry — an acceptance-history gap) ·
`mismatch` (ledger `design_state` disagrees with the model prefix) · `ignored`
(not a version-created event). The decision logic is the pure function
`evaluate_version_event(event, ledger)`, unit-tested without a socket.

## 7. Current known gap

The live `accepted/scenario-e-baseline` model currently holds version
`a6e9dab770` (per the deployment record), but the ledger starts **empty** — so the
webhook will **FLAG** that version. This is intentional and honest: the live
accepted model has not yet been ratified by a verified accepted publish through
this repo. Closing the gap requires an explicit, verified `--publish` (or a
deliberate backfill of the entry from the exact payload that produced
`a6e9dab770`), which is left for when that publish is explicitly requested — the
live model is not changed by this Phase 2 work.

## 8. Tests

`scripts/test_speckle_phase2.py` proves: accepted blocked on a dirty repo;
accepted blocked with a `RULE-9-OPEN` object; proposal allowed with (and blocked
without) `open_decisions`; scratch allowed but excluded from accepted reports;
ledger hash-mismatch detection; webhook flagging of an un-ledgered `accepted/*`
version; ledger round-trip persistence; compare diff; and that a dry-run accepted
publish shows the entry it would create without writing it. The Phase 1 boundary
tests remain in `scripts/test_speckle_payload.py`.
