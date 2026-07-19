#!/usr/bin/env python3
"""Dry-run-first publisher for the Speckle review bridge.

Publishing is gated. This tool REFUSES to send anything to Speckle unless, in
order:

  1. ``scripts/verify_unreal_export.py`` exits 0 (the validated handoff package
     is intact — seat counts, C-values, ADA status, warnings un-weakened);
  2. the Speckle payload passes the object-truth boundary checks in
     ``speckle_common.validate_payload`` (every leaf has provenance + the
     required validation fields; ADA status not strengthened; warnings carried);
  3. the branch prefix (accepted/ proposal/ reference/) matches the payload's
     acceptance.state.

Default behaviour is a DRY RUN: it runs gates 1–3 and prints exactly what would
be sent (project, branch/model, object counts, acceptance state) WITHOUT any
network call and WITHOUT importing specklepy. Only ``--publish`` performs a real
send, and only then is ``specklepy`` (lazily) imported.

    python scripts/publish_speckle.py                         # dry run, accepted bundle
    python scripts/publish_speckle.py --payload speckle_export/petoskey_pit.proposal.speckle.json
    SPECKLE_TOKEN=... python scripts/publish_speckle.py --publish --server https://speckle.lan

Speckle is a review surface. A successful publish does NOT make anything design
truth. The Python/QGIS repo remains the only acceptance authority.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import speckle_common as S  # noqa: E402
import speckle_ledger as L  # noqa: E402

VERIFY_SCRIPT = os.path.join(S.REPO, "scripts", "verify_unreal_export.py")


# ── gate 1: the live Unreal-export verification ───────────────────────────────
def run_export_gate(verify_cmd: list[str] | None = None) -> tuple[bool, str]:
    """Run the Unreal-export acceptance gate. Returns (passed, tail_of_output).

    ``verify_cmd`` is injectable so tests can substitute a deliberately failing
    command and prove a failed gate blocks publication.
    """
    cmd = verify_cmd or [sys.executable, VERIFY_SCRIPT]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=S.REPO)
    out = (proc.stdout or "") + (proc.stderr or "")
    tail = "\n".join(out.strip().splitlines()[-4:])
    return proc.returncode == 0, tail


# ── the full pre-publish gauntlet ─────────────────────────────────────────────
def preflight(payload: dict, *, verify_cmd: list[str] | None = None,
              require_source_exists: bool = True) -> tuple[bool, list[str]]:
    """Run every refusal check. Returns (ok_to_publish, reasons_if_not)."""
    reasons: list[str] = []

    passed, tail = run_export_gate(verify_cmd)
    if not passed:
        reasons.append("Unreal-export verification FAILED "
                       "(scripts/verify_unreal_export.py exited non-zero):\n" + _indent(tail))

    errs = S.validate_payload(payload, require_source_exists=require_source_exists)
    if errs:
        reasons.append(f"payload failed the object-truth boundary ({len(errs)} error(s)):\n"
                       + _indent("\n".join(f"- {e}" for e in errs)))

    return (not reasons), reasons


def _indent(text: str, pad: str = "      ") -> str:
    return "\n".join(pad + ln for ln in text.splitlines())


# ── gates + acceptance-discipline guard (Phase 2) ─────────────────────────────
def gather_gates(payload: dict, *, verify_cmd: list[str] | None = None,
                 require_source_exists: bool = True, repo: str = S.REPO) -> dict:
    """Run every gate ONCE and return the structured results the guard consumes:
    the live verify result, the object-truth boundary errors, and the working-tree
    cleanliness. Kept separate from :func:`guard` so the policy is pure and
    testable with injected gate outcomes."""
    verify_passed, verify_tail = run_export_gate(verify_cmd)
    boundary_errs = S.validate_payload(payload, require_source_exists=require_source_exists,
                                       repo=repo)
    repo_clean, dirty = L.repo_status(repo)
    return {
        "verify_passed": verify_passed,
        "verify_tail": verify_tail,
        "boundary_errs": boundary_errs,
        "repo_clean": repo_clean,
        "dirty": dirty,
    }


def resolve_design_state(payload: dict, explicit: str | None = None) -> str:
    """The publish-discipline channel. Explicit --design-state wins; otherwise the
    payload's acceptance.state (accepted/proposal/reference). scratch only ever
    comes from the explicit flag — no payload carries a scratch acceptance.state."""
    if explicit:
        return explicit
    return (payload.get("acceptance") or {}).get("state") or L.DS_PROPOSAL


def guard(payload: dict, design_state: str, gates: dict, *,
          allow_dirty: bool = False, open_decisions: list[str] | None = None,
          allow_state_mismatch: bool = False
          ) -> tuple[bool, list[str]]:
    """The acceptance-discipline guard. Returns (allowed, reasons_if_blocked).

    Channels:
      * accepted/* — only verified mirrors of a repo-accepted, committed state:
        repo clean (or --allow-dirty), verify green, boundary clean, payload
        acceptance.state == accepted, and NO object carrying an unresolved hard
        decision flag (e.g. RULE-9-OPEN).
      * proposal/* — a reviewable alternative: verify green + boundary clean, and
        MUST carry open_decisions metadata (a proposal that resolves everything
        should publish as accepted).
      * reference/* — non-decision context: verify green + boundary clean.
      * scratch/*  — render/debug: permissive, nothing blocks; excluded from the
        accepted ledger reports.

    Channel/self-declaration agreement: on every real channel the payload's own
    ``acceptance.state`` must match the channel. The accepted channel enforces
    this as a hard, non-overridable gate (never let non-accepted content ride an
    accepted publish). proposal/reference enforce it too but honour
    ``allow_state_mismatch`` for a deliberate re-channel — without this, an
    ``accepted`` payload published on ``--design-state reference`` records a
    self-inconsistent ledger row and is silently dropped from accepted-only
    reports.
    """
    reasons: list[str] = []
    if design_state not in L.LEDGER_STATES:
        return False, [f"unknown design_state {design_state!r} (expected one of {L.LEDGER_STATES})"]

    if design_state == L.DS_SCRATCH:
        return True, reasons  # render/debug channel — deliberately permissive

    # accepted / proposal / reference are all real review bundles: the validated
    # export must be intact and the object-truth boundary clean.
    if not gates["verify_passed"]:
        reasons.append("Unreal-export verification FAILED "
                       "(scripts/verify_unreal_export.py exited non-zero):\n"
                       + _indent(gates["verify_tail"]))
    if gates["boundary_errs"]:
        reasons.append(f"payload failed the object-truth boundary "
                       f"({len(gates['boundary_errs'])} error(s)):\n"
                       + _indent("\n".join(f"- {e}" for e in gates["boundary_errs"])))

    if design_state == L.DS_ACCEPTED:
        if not gates["repo_clean"] and not allow_dirty:
            reasons.append(
                "repo is DIRTY — an accepted publish must mirror a committed repo "
                "state so the ledger commit is reproducible:\n"
                + _indent("\n".join(f"- {f}" for f in gates["dirty"][:20]))
                + "\n      (override with --allow-dirty only if the working tree "
                  "deliberately matches the intended accepted state)")
        st = (payload.get("acceptance") or {}).get("state")
        if st != L.DS_ACCEPTED:
            reasons.append(f"design_state is 'accepted' but payload acceptance.state is {st!r}")
        und = L.unresolved_object_decisions(payload)
        if und:
            flags = "; ".join(f"{u['name']} [{'/'.join(u['flags'])}]" for u in und)
            reasons.append(
                f"accepted publish blocked — {len(und)} object(s) carry unresolved "
                f"decision flags (these must ship as a proposal, not accepted): {flags}")

    if design_state == L.DS_PROPOSAL:
        od = open_decisions if open_decisions is not None else L.derive_open_decisions(payload)
        if not od:
            reasons.append(
                "proposal publish must carry open_decisions metadata (none found in "
                "the payload and none provided via --open-decision). A proposal that "
                "resolves every decision should be published as 'accepted' instead.")

    if design_state in (L.DS_PROPOSAL, L.DS_REFERENCE):
        pstate = (payload.get("acceptance") or {}).get("state")
        if pstate and pstate != design_state and not allow_state_mismatch:
            reasons.append(
                f"design_state is {design_state!r} but the payload declares "
                f"acceptance.state {pstate!r} — publishing it on the {design_state!r} "
                f"channel records self-inconsistent provenance (e.g. an 'accepted' "
                f"payload published as {design_state!r} is silently excluded from "
                f"accepted-only ledger reports). Publish on the matching channel, or "
                f"pass --allow-state-mismatch to re-channel deliberately.")

    return (not reasons), reasons


# ── publish plan (what a real send would do) ──────────────────────────────────
def publish_plan(payload: dict, server: str) -> dict:
    acc = payload.get("acceptance", {})
    n_leaves = sum(len(c.get("@elements", [])) for c in payload.get("@elements", []))
    return {
        "server": server,
        "project_slug": acc.get("project"),
        "branch_model": acc.get("branch"),
        "acceptance_state": acc.get("state"),
        "collections": [c.get("name") for c in payload.get("@elements", [])],
        "n_leaf_objects": n_leaves,
        "warnings_carried": len(payload.get("warnings", [])),
        "git_commit": payload.get("bridge", {}).get("git_commit"),
        "commit_message": _commit_message(payload),
    }


def _commit_message(payload: dict) -> str:
    acc = payload.get("acceptance", {})
    br = payload.get("bridge", {})
    return (f"{acc.get('state')}: {acc.get('branch')} @ {br.get('git_commit')} "
            f"| unreal-verify PASS | source unreal_export/ ({br.get('generated_from')})")


# ── real send (lazy specklepy; only reached on --publish) ─────────────────────
def _dict_to_base(node):
    """Rebuild a specklepy Base tree from our plain-dict payload.

    Leaf geometry and collections are rebuilt as their REAL specklepy classes
    (``Polyline`` / ``Point`` / ``Collection``) so the server records the correct
    ``speckle_type`` and the web viewer actually renders them. A bare ``Base``
    with ``speckle_type`` merely *assigned* is serialized by specklepy 3.x as
    ``"Base"`` (the type string is dropped) and the viewer shows nothing — so the
    class must be constructed, not faked. Dynamic / ``@``-detached members
    (``@review``, ``@geo_epsg6494``, ``name``, ``applicationId``) are set by item
    assignment, which preserves the ``@`` detach prefix on the server.
    """
    from specklepy.objects import Base
    from specklepy.objects.geometry import Polyline, Point
    from specklepy.objects.models.collections.collection import Collection

    if isinstance(node, list):
        return [_dict_to_base(x) for x in node]
    if not isinstance(node, dict):
        return node

    st = node.get("speckle_type")
    consumed = {"speckle_type"}
    if st == "Objects.Geometry.Polyline":
        b = Polyline(value=[float(x) for x in (node.get("value") or [])],
                     units=node.get("units", "m"))
        b.closed = bool(node.get("closed", False))
        consumed |= {"value", "units", "closed"}
    elif st == "Objects.Geometry.Point":
        b = Point(x=float(node.get("x", 0.0)), y=float(node.get("y", 0.0)),
                  z=float(node.get("z", 0.0)), units=node.get("units", "m"))
        consumed |= {"x", "y", "z", "units"}
    elif st == "Objects.Organization.Collection":
        b = Collection(name=node.get("name", "collection"), elements=[])
        b.elements = _dict_to_base(node.get("@elements", []))
        if node.get("collectionType"):
            b.collectionType = node["collectionType"]
        consumed |= {"name", "@elements", "collectionType"}
    else:
        b = Base()  # the payload root: a plain container traversed via @elements

    for k, v in node.items():
        if k in consumed:
            continue
        b[k] = _dict_to_base(v)  # dynamic / @-detached member
    return b


def do_publish(payload: dict, server: str, token: str, message: str) -> dict:
    """Perform the real Speckle send + version create. Imports specklepy lazily."""
    try:
        from specklepy.api import operations
        from specklepy.api.client import SpeckleClient
        from specklepy.transports.server import ServerTransport
        from specklepy.core.api.inputs.version_inputs import CreateVersionInput
    except ImportError as exc:  # pragma: no cover - depends on env
        raise SystemExit(
            "specklepy is not installed in this environment. Install it INTO THE "
            "PROJECT VENV (never system pip):\n"
            "    python -m venv .venv && . .venv/bin/activate\n"
            "    pip install specklepy\n"
            f"(import error: {exc})")

    acc = payload.get("acceptance", {})
    project_id = os.environ.get("SPECKLE_PROJECT_ID")
    model_id = os.environ.get("SPECKLE_MODEL_ID")
    if not project_id:
        raise SystemExit(
            "SPECKLE_PROJECT_ID is required for a real publish. Create a project "
            f"named '{acc.get('project')}' and a model named '{acc.get('branch')}' "
            "on the server, then export their ids:\n"
            "    export SPECKLE_PROJECT_ID=...  SPECKLE_MODEL_ID=...")

    client = SpeckleClient(host=server)
    client.authenticate_with_token(token)

    base = _dict_to_base(payload)
    transport = ServerTransport(stream_id=project_id, client=client)
    object_id = operations.send(base=base, transports=[transport])

    if model_id:
        version = client.version.create(CreateVersionInput(
            project_id=project_id, model_id=model_id,
            object_id=object_id, message=message))
        version_id = getattr(version, "id", None)
    else:
        version_id = None

    return {"object_id": object_id, "version_id": version_id,
            "project_id": project_id, "model_id": model_id}


# ── cli ───────────────────────────────────────────────────────────────────────
def default_payload_path() -> str:
    return os.path.join(S.OUT_DIR, "petoskey_pit.accepted.speckle.json")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--payload", default=default_payload_path(),
                    help="Speckle payload JSON (default: the accepted bundle)")
    ap.add_argument("--server", default=os.environ.get("SPECKLE_SERVER", "https://speckle.lan"),
                    help="Speckle server URL (env SPECKLE_SERVER)")
    ap.add_argument("--publish", action="store_true",
                    help="actually send to Speckle (default: dry run only)")
    ap.add_argument("--allow-state-mismatch", action="store_true",
                    help="permit a branch prefix that disagrees with acceptance.state")
    ap.add_argument("--design-state", choices=L.LEDGER_STATES, default=None,
                    help="publish-discipline channel (default: payload acceptance.state). "
                         "Use 'scratch' for render/debug pushes excluded from the "
                         "accepted ledger reports.")
    ap.add_argument("--allow-dirty", action="store_true",
                    help="permit an accepted publish from a dirty working tree "
                         "(otherwise blocked; the working tree must match a commit)")
    ap.add_argument("--open-decision", action="append", default=None, metavar="TEXT",
                    help="record an open decision (repeatable); proposals require at "
                         "least one (auto-derived from the payload if omitted)")
    ap.add_argument("--notes", default=None, help="free-text note stored on the ledger entry")
    ap.add_argument("--ledger", default=L.LEDGER_PATH, help="ledger path (advanced)")
    args = ap.parse_args(argv)

    if not os.path.exists(args.payload):
        print(f"FATAL: payload not found: {args.payload}\n"
              f"  run: python scripts/export_speckle_payload.py", file=sys.stderr)
        return 2
    with open(args.payload) as fh:
        payload = json.load(fh)

    mode = "PUBLISH" if args.publish else "DRY RUN"
    design_state = resolve_design_state(payload, args.design_state)
    print(f"=== Speckle publish · {mode} · channel={design_state} ===")
    print(f"payload: {os.path.relpath(args.payload, S.REPO)}")

    gates = gather_gates(payload)
    plan = publish_plan(payload, args.server)
    open_decisions = args.open_decision if args.open_decision else None

    print("\nplan:")
    for k, v in plan.items():
        print(f"  {k:18} {v}")
    print(f"  {'design_state':18} {design_state}")
    print(f"  {'repo_clean':18} {gates['repo_clean']}")

    ok, reasons = guard(payload, design_state, gates,
                        allow_dirty=args.allow_dirty, open_decisions=open_decisions,
                        allow_state_mismatch=args.allow_state_mismatch)

    # The ledger entry this publish would create / will create. Built before the
    # send so a dry run can show it; rebuilt with the real ids after a send.
    preview = L.build_entry(payload, design_state=design_state, gates=gates,
                            server=args.server, open_decisions=open_decisions,
                            notes=args.notes)

    # A DRY RUN always shows the prospective entry AND the guard verdict, so the
    # operator sees exactly what would be recorded and what (if anything) blocks it.
    if not args.publish:
        if ok:
            print(f"\nguard: OK ({design_state} discipline satisfied)")
        else:
            print(f"\nguard: WOULD BLOCK a real {design_state} publish:")
            for r in reasons:
                print("  • " + r)
        print("\nledger entry (preview — would be appended on --publish):")
        print(_indent(json.dumps(preview, indent=2)))
        print(f"\nDRY RUN complete — nothing was sent, ledger unchanged "
              f"({os.path.relpath(args.ledger, S.REPO)}). Re-run with --publish "
              "(and SPECKLE_TOKEN / SPECKLE_PROJECT_ID set) to publish + record.")
        return 0 if ok else 1

    # --publish: the guard is a hard gate.
    if not ok:
        print(f"\nREFUSED — {design_state} publication is blocked:", file=sys.stderr)
        for r in reasons:
            print("  • " + r, file=sys.stderr)
        print("\nSpeckle is a review surface; the repo gates are the acceptance "
              "authority. Fix the blocking issues and re-run.", file=sys.stderr)
        return 1

    print(f"\nguard: OK ({design_state} discipline satisfied)")

    token = os.environ.get("SPECKLE_TOKEN")
    if not token:
        print("FATAL: --publish requires SPECKLE_TOKEN in the environment.",
              file=sys.stderr)
        return 2

    result = do_publish(payload, args.server, token, plan["commit_message"])
    print("\nPUBLISHED:")
    for k, v in result.items():
        print(f"  {k:12} {v}")

    entry = L.build_entry(payload, design_state=design_state, gates=gates,
                          publish_result=result, server=args.server,
                          open_decisions=open_decisions, notes=args.notes)
    L.append_entry(entry, args.ledger)
    print(f"\nledger: appended entry (version={entry.get('version_id')}, "
          f"hash={entry.get('export_payload_hash')}) to "
          f"{os.path.relpath(args.ledger, S.REPO)}")
    print("Commit the ledger so the repo records this publish — Speckle history is "
          "not acceptance history without it.")
    print("\nReminder: this is a review version. It is NOT design truth. Any geometry "
          "edited in Speckle must return as a proposal GeoJSON and pass the repo gates.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
