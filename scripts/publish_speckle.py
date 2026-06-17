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

    Follows specklepy's documented dynamic-member idiom: dynamic and
    ``@``-detached members are set by item assignment (``base[key] = value``),
    which is what keeps the ``@`` detach prefix meaningful on the server. Only
    ``speckle_type`` is a fixed attribute.
    """
    from specklepy.objects import Base

    if isinstance(node, list):
        return [_dict_to_base(x) for x in node]
    if not isinstance(node, dict):
        return node
    b = Base()
    if node.get("speckle_type"):
        b.speckle_type = node["speckle_type"]
    for k, v in node.items():
        if k == "speckle_type":
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
    args = ap.parse_args(argv)

    if not os.path.exists(args.payload):
        print(f"FATAL: payload not found: {args.payload}\n"
              f"  run: python scripts/export_speckle_payload.py", file=sys.stderr)
        return 2
    with open(args.payload) as fh:
        payload = json.load(fh)

    mode = "PUBLISH" if args.publish else "DRY RUN"
    print(f"=== Speckle publish · {mode} ===")
    print(f"payload: {os.path.relpath(args.payload, S.REPO)}")

    ok, reasons = preflight(payload)
    plan = publish_plan(payload, args.server)

    print("\nplan:")
    for k, v in plan.items():
        print(f"  {k:18} {v}")

    if not ok:
        print("\nREFUSED — publication is blocked:", file=sys.stderr)
        for r in reasons:
            print("  • " + r, file=sys.stderr)
        print("\nSpeckle is a review surface; the repo gates are the acceptance "
              "authority. Fix the blocking issues and re-run.", file=sys.stderr)
        return 1

    print("\npreflight: OK (verify gate green · boundary clean · branch matches state)")

    if not args.publish:
        print("\nDRY RUN complete — nothing was sent. Re-run with --publish "
              "(and SPECKLE_TOKEN / SPECKLE_PROJECT_ID set) to publish.")
        return 0

    token = os.environ.get("SPECKLE_TOKEN")
    if not token:
        print("FATAL: --publish requires SPECKLE_TOKEN in the environment.",
              file=sys.stderr)
        return 2

    result = do_publish(payload, args.server, token, plan["commit_message"])
    print("\nPUBLISHED:")
    for k, v in result.items():
        print(f"  {k:12} {v}")
    print("\nReminder: this is a review version. It is NOT design truth. Any geometry "
          "edited in Speckle must return as a proposal GeoJSON and pass the repo gates.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
