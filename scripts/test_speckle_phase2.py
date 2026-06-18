#!/usr/bin/env python3
"""Phase 2 tests: acceptance discipline, publish ledger, compare, webhook.

Proves the publish-discipline guard, the repo-side ledger, the payload compare,
and the webhook handshake all behave. Required scenarios (from the Phase 2 brief):

  1. accepted publish BLOCKED with a dirty repo (and allowed with --allow-dirty);
  2. accepted publish BLOCKED with a RULE-9-OPEN object;
  3. proposal publish ALLOWED with open_decisions metadata (BLOCKED without);
  4. scratch publish ALLOWED but EXCLUDED from accepted ledger reports;
  5. ledger hash mismatch detected;
  6. webhook event without ledger entry FLAGGED (accepted/*).

Plus: ledger round-trip persistence, compare diff smoke, dry-run entry preview.

Plain script (repo convention). Exit 0 = all pass, 1 = a check failed. No pytest.
"""
from __future__ import annotations

import copy
import io
import json
import os
import sys
import tempfile
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import speckle_common as S  # noqa: E402
import speckle_ledger as L  # noqa: E402
import publish_speckle as P  # noqa: E402
import speckle_compare as C  # noqa: E402
import speckle_webhook as W  # noqa: E402
import export_speckle_payload as X  # noqa: E402

RESULTS: list[tuple[bool, str]] = []


def check(cond: bool, label: str) -> None:
    RESULTS.append((bool(cond), label))


# ── payload builders (in-process; no file dependency) ─────────────────────────
def _load_export() -> dict:
    export = S.load_export()
    actor_path = os.path.join(S.EXPORT_DIR, "manifests/actor_manifest.json")
    export["_actor_by_fid"] = ({a["source_feature_id"]: a
                                for a in S.jload(actor_path).get("actors", [])}
                               if os.path.exists(actor_path) else {})
    return export


def accepted_clean(export) -> dict:
    """The real accepted bundle: Seating + ADA + Reference, Rule-9-OPEN stage
    excluded (it ships as a proposal)."""
    return X.build_payload(export, S.STATE_ACCEPTED, None,
                           layers={"Seating", "ADA", "Reference"})


def accepted_with_stage(export) -> dict:
    """An accepted payload that (wrongly) includes the Rule-9-OPEN stage."""
    p = X.build_payload(export, S.STATE_ACCEPTED, None)  # layers=None → all
    # guarantee at least one stage leaf carries the open flag (isolate the guard
    # from live-data drift)
    stage = next((c for c in p["@elements"] if c["name"] == "Stage"), None)
    if stage and stage["@elements"]:
        stage["@elements"][0]["@review"]["rule9_status"] = "open"
        stage["@elements"][0]["@review"]["provisional"] = True
    return p


def proposal_full(export) -> dict:
    return X.build_payload(export, S.STATE_PROPOSAL, "alt-test", None)


def proposal_seating_only(export) -> dict:
    """A proposal with no open decisions at all (seating rows only)."""
    return X.build_payload(export, S.STATE_PROPOSAL, "seats-only", layers={"Seating"})


CLEAN_GATES = {"verify_passed": True, "verify_tail": "", "boundary_errs": [],
               "repo_clean": True, "dirty": []}


def gates(**over) -> dict:
    g = dict(CLEAN_GATES)
    g.update(over)
    return g


def main() -> int:
    export = _load_export()
    acc = accepted_clean(export)
    acc_stage = accepted_with_stage(export)
    prop = proposal_full(export)
    prop_empty = proposal_seating_only(export)

    # sanity: the clean accepted bundle really has no unresolved decision flags
    check(L.unresolved_object_decisions(acc) == [],
          "accepted bundle (stage excluded) has NO unresolved decision flags")
    check(len(L.unresolved_object_decisions(acc_stage)) >= 1,
          "stage-included payload HAS an unresolved RULE-9-OPEN flag")

    # ── 1. accepted publish blocked with a dirty repo ─────────────────────────
    ok_dirty, why_dirty = P.guard(acc, L.DS_ACCEPTED, gates(repo_clean=False,
                                  dirty=["?? scratch.txt"]), allow_dirty=False)
    check((not ok_dirty) and any("DIRTY" in r for r in why_dirty),
          "accepted publish BLOCKED with a dirty repo")
    ok_override, _ = P.guard(acc, L.DS_ACCEPTED, gates(repo_clean=False,
                             dirty=["?? scratch.txt"]), allow_dirty=True)
    check(ok_override, "accepted publish ALLOWED from dirty repo with --allow-dirty")

    # ── 2. accepted publish blocked with a RULE-9-OPEN object ──────────────────
    ok_r9, why_r9 = P.guard(acc_stage, L.DS_ACCEPTED, gates(), allow_dirty=True)
    check((not ok_r9) and any("RULE-9-OPEN" in r and "unresolved decision" in r
                              for r in why_r9),
          "accepted publish BLOCKED with a RULE-9-OPEN object")

    # ── 3. proposal allowed with open_decisions; blocked without ──────────────
    od = L.derive_open_decisions(prop)
    check(len(od) >= 1, "proposal auto-derives open_decisions metadata from the payload")
    ok_prop, why_prop = P.guard(prop, L.DS_PROPOSAL, gates(), open_decisions=None)
    check(ok_prop, f"proposal publish ALLOWED with open_decisions metadata ({why_prop})")
    ok_empty, why_empty = P.guard(prop_empty, L.DS_PROPOSAL, gates(), open_decisions=None)
    check((not ok_empty) and any("open_decisions" in r for r in why_empty),
          "proposal publish BLOCKED without open_decisions metadata")

    # ── 4. scratch allowed (permissive) + excluded from accepted reports ──────
    ok_scratch, _ = P.guard(prop, L.DS_SCRATCH,
                            gates(verify_passed=False, boundary_errs=["x"], repo_clean=False))
    check(ok_scratch, "scratch publish ALLOWED even with failing gates (render/debug channel)")

    tmp_ledger = os.path.join(tempfile.mkdtemp(), "ledger.json")
    e_scratch = L.build_entry(prop, design_state=L.DS_SCRATCH, gates=gates(),
                              publish_result={"version_id": "v_scratch",
                                              "project_id": "p", "model_id": "m"},
                              timestamp="2026-06-18T00:00:00+00:00")
    e_accept = L.build_entry(acc, design_state=L.DS_ACCEPTED, gates=gates(),
                             publish_result={"version_id": "v_accept",
                                             "project_id": "p", "model_id": "m"},
                             timestamp="2026-06-18T00:01:00+00:00")
    L.append_entry(e_scratch, tmp_ledger)
    led = L.append_entry(e_accept, tmp_ledger)
    rep = L.entries_for_report(led)              # default: scratch excluded
    accepted_only = L.accepted_entries(led)
    check(all(e["design_state"] != L.DS_SCRATCH for e in rep)
          and len(rep) == 1,
          "scratch entry EXCLUDED from default ledger report")
    check(len(accepted_only) == 1 and accepted_only[0]["version_id"] == "v_accept",
          "accepted_entries() returns only the accepted entry")
    check(len(L.entries_for_report(led, include_scratch=True)) == 2,
          "scratch entry visible only with include_scratch=True")

    # ── ledger round-trip persistence ─────────────────────────────────────────
    reloaded = L.load_ledger(tmp_ledger)
    check(len(reloaded["entries"]) == 2 and reloaded.get("schema") == L.LEDGER_SCHEMA,
          "ledger persists + reloads with schema header")
    found = L.find_entries(reloaded, version_id="v_accept")
    check(len(found) == 1, "find_entries locates an entry by version_id")

    # ── 5. ledger hash mismatch detected ──────────────────────────────────────
    entry = L.build_entry(prop, design_state=L.DS_PROPOSAL, gates=gates(),
                          timestamp="2026-06-18T00:00:00+00:00")
    ok_hash, exp, act = L.verify_entry_hash(entry, prop)
    check(ok_hash and exp == act, "ledger hash matches the unmodified payload")
    mutated = copy.deepcopy(prop)
    next(iter(c for c in mutated["@elements"]))["@elements"][0]["@review"]["seats_kept"] = 99999
    ok_hash2, exp2, act2 = L.verify_entry_hash(entry, mutated)
    check((not ok_hash2) and exp2 != act2,
          "ledger hash MISMATCH detected after the payload is altered")

    # ── 6. webhook event without ledger entry flagged ─────────────────────────
    empty = {"schema": L.LEDGER_SCHEMA, "entries": []}
    ev_acc = {"event_name": "version_create",
              "branch": "accepted/scenario-e-baseline",
              "version_id": "ver_X", "project_id": "p", "model_id": "m"}
    v_flag = W.evaluate_version_event(ev_acc, empty)
    check(v_flag["status"] == "FLAG" and "acceptance history" in v_flag["reason"],
          "webhook FLAGS an accepted/* version with no ledger entry")

    backed = {"schema": L.LEDGER_SCHEMA, "entries": [
        {"design_state": "accepted", "version_id": "ver_X",
         "branch": "accepted/scenario-e-baseline"}]}
    v_ok = W.evaluate_version_event(ev_acc, backed)
    check(v_ok["status"] == "ok", "webhook OK when the accepted version is in the ledger")

    ev_prop = dict(ev_acc, branch="proposal/alt-20260618", version_id="ver_Y")
    v_warn = W.evaluate_version_event(ev_prop, empty)
    check(v_warn["status"] == "warn",
          "webhook WARNs (not flags) a non-accepted version with no entry")

    v_ignored = W.evaluate_version_event({"event_name": "comment_created"}, empty)
    check(v_ignored["status"] == "ignored", "webhook IGNORES non-version events")

    # design_state vs model-prefix mismatch
    mism = {"schema": L.LEDGER_SCHEMA, "entries": [
        {"design_state": "proposal", "version_id": "ver_X",
         "branch": "accepted/scenario-e-baseline"}]}
    v_mism = W.evaluate_version_event(ev_acc, mism)
    check(v_mism["status"] == "mismatch",
          "webhook flags a ledger design_state vs model-prefix mismatch")

    # ── compare smoke: accepted (no stage) vs proposal (with stage) ───────────
    diff = C.compare_payloads(acc, prop)
    check(diff["added_by_class"].get("stage_feature", 0) >= 1,
          "compare: proposal adds stage_feature objects vs the accepted bundle")
    check("validation_delta" in diff and "seat_total" in diff["validation_delta"],
          "compare: reports validation deltas incl. seat_total")
    check(len(diff["unresolved_decisions"]["proposal"]) >= 1,
          "compare: surfaces the proposal's unresolved decisions")
    # changed-row detection: bump a row's seats in the proposal copy
    prop2 = copy.deepcopy(prop)
    seat = next(l for cc in prop2["@elements"] if cc["name"] == "Seating"
                for l in cc["@elements"])
    seat["@review"]["seats_kept"] = (seat["@review"].get("seats_kept") or 0) + 1
    diff2 = C.compare_payloads(acc, prop2)
    check(len(diff2["changed_rows"]) >= 1, "compare: detects a changed seating row id")

    # ── dry-run accepted publish shows the ledger entry it would create ───────
    tmp_payload = os.path.join(tempfile.mkdtemp(), "accepted.speckle.json")
    with open(tmp_payload, "w") as fh:
        json.dump(acc, fh)
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = P.main(["--payload", tmp_payload, "--design-state", "accepted",
                     "--allow-dirty", "--ledger", tmp_ledger])
    out = buf.getvalue()
    check("ledger entry (preview" in out and "export_payload_hash" in out,
          "dry-run accepted publish SHOWS the ledger entry it would create")
    check("DRY RUN complete" in out and rc in (0, 1),
          "dry-run sends nothing (no publish, ledger untouched on dry run)")
    # confirm the dry run did NOT append to the ledger (still 2 entries from step 4)
    check(len(L.load_ledger(tmp_ledger)["entries"]) == 2,
          "dry-run did not write to the ledger")

    # ── report ────────────────────────────────────────────────────────────────
    n_pass = sum(1 for ok, _ in RESULTS if ok)
    for ok, label in RESULTS:
        print(f"  {'PASS' if ok else 'FAIL'}  {label}")
    print(f"\n{n_pass}/{len(RESULTS)} checks pass")
    return 0 if n_pass == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
