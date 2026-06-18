#!/usr/bin/env python3
"""Speckle publish ledger — the repo-side record of authority.

The Speckle server's own version history is **not** acceptance history. A version
becomes part of the project record only when ``scripts/publish_speckle.py`` writes
a ledger entry *here, in the repo*, on a real publish. This module is that ledger:
its data model, the content hash that pins each entry to an exact payload, the
git / working-tree helpers the accepted-publish guard relies on, the decision-flag
scanners, and the read-side reports (accepted-only views, hash verification,
webhook lookup).

Why a repo-side ledger at all? Because the truth boundary runs the other way:

    repo gates (authority)  ->  unreal_export/  ->  speckle_export/*.json  ->  Speckle (review)

Speckle can show anything anyone pushes to it. The ledger is how the repo records
which of those Speckle versions actually correspond to a gated, hashed, committed
repo state — so "there is an accepted/* model on the server" never silently reads
as "this design was accepted." Only a ledger entry says that, and only an entry
whose hash still matches the payload it claims.

Stdlib only. No network. Ledger file: ``data/speckle_publish_ledger.json``.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from typing import Any

import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import speckle_common as S  # noqa: E402

REPO = S.REPO
LEDGER_PATH = os.path.join(REPO, "data", "speckle_publish_ledger.json")
LEDGER_SCHEMA = "speckle-publish-ledger/1"
LEDGER_NOTE = (
    "Speckle version history is NOT acceptance history. A Speckle version counts "
    "as part of the project record only if it is backed by an entry in this "
    "ledger whose export_payload_hash still matches the payload it published. The "
    "Python/QGIS repo gates remain the sole acceptance authority; this file is the "
    "repo's record of which review versions mirror a gated, committed state."
)

# ── design states (the publish-discipline channels) ───────────────────────────
# These extend speckle_common.VALID_STATES (accepted/proposal/reference) with a
# fourth *publish channel*, scratch, for render/debug pushes that are deliberately
# excluded from the accepted-ledger reports. A payload's acceptance.state is still
# one of the three review states; scratch is a property of the publish, not of the
# design.
DS_ACCEPTED = S.STATE_ACCEPTED
DS_PROPOSAL = S.STATE_PROPOSAL
DS_REFERENCE = S.STATE_REFERENCE
DS_SCRATCH = "scratch"
LEDGER_STATES = (DS_ACCEPTED, DS_PROPOSAL, DS_SCRATCH, DS_REFERENCE)

DEFAULT_VALIDATION_COMMANDS = (
    "python scripts/verify_unreal_export.py",
    "python scripts/publish_speckle.py  (object-truth boundary: speckle_common.validate_payload)",
)


# ── content hash (pins an entry to an exact payload) ──────────────────────────
def canonical_json(obj: Any) -> str:
    """Deterministic JSON for hashing: sorted keys, tight separators, unicode kept."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def payload_hash(payload: dict) -> str:
    """SHA-256 of the canonical payload, ``sha256:<hex>``.

    Hashes the whole payload (including the build timestamp + git_commit in
    ``bridge``), so an entry's hash identifies the *exact* artifact published. A
    rebuild changes the hash; that is intentional — the ledger pins a build.
    """
    h = hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()
    return f"sha256:{h}"


def verify_entry_hash(entry: dict, payload: dict) -> tuple[bool, str, str]:
    """(matches, expected_from_entry, actual_recomputed)."""
    expected = entry.get("export_payload_hash") or ""
    actual = payload_hash(payload)
    return (expected == actual, expected, actual)


# ── git / working-tree helpers (the accepted-publish guard relies on these) ───
def git_head(repo: str = REPO) -> str | None:
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo,
                             capture_output=True, text=True)
        return out.stdout.strip() or None if out.returncode == 0 else None
    except Exception:  # noqa: BLE001 - git absent / not a repo
        return None


def repo_status(repo: str = REPO) -> tuple[bool, list[str]]:
    """(clean, dirty_paths). ``clean`` is True iff ``git status --porcelain`` is
    empty (no staged, unstaged, or untracked changes). On any git failure we
    report dirty with an explanatory pseudo-path, so the guard fails safe."""
    try:
        out = subprocess.run(["git", "status", "--porcelain"], cwd=repo,
                             capture_output=True, text=True)
        if out.returncode != 0:
            return False, [f"(git status failed: {out.stderr.strip()})"]
        lines = [ln for ln in out.stdout.splitlines() if ln.strip()]
        return (len(lines) == 0), lines
    except Exception as exc:  # noqa: BLE001
        return False, [f"(git unavailable: {exc})"]


# ── payload introspection ─────────────────────────────────────────────────────
def collect_source_files(payload: dict) -> list[str]:
    """Sorted unique ``@review.source_file`` across every leaf — the authoritative
    repo sources this published bundle was derived from."""
    files: set[str] = set()
    for _coll, leaf in S._iter_leaves(payload):
        sf = (leaf.get("@review") or {}).get("source_file")
        if sf:
            files.add(sf)
    return sorted(files)


# Hard, blocking decision flags. These are *open* design decisions that must not
# ride inside an accepted publish (they would silently read as decided). The
# canonical example is the Rule-9-OPEN stage deck.
def unresolved_object_decisions(payload: dict) -> list[dict]:
    """List leaves carrying an unresolved hard decision flag (e.g. RULE-9-OPEN).

    NOT flagged: the always-present ADA concept/pending caveat, which is a carried
    *label* on a flagged proposal sub-object, not an open binary decision — the
    accepted bundle is designed to carry such flagged sub-objects without
    promoting them (see export_speckle_payload acceptance rationale).
    """
    out: list[dict] = []
    for coll, leaf in S._iter_leaves(payload):
        rv = leaf.get("@review") or {}
        flags: list[str] = []
        if rv.get("rule9_status") == "open":
            flags.append("RULE-9-OPEN")
        df = rv.get("decision_flag") or rv.get("decision_status")
        if isinstance(df, str) and df.strip().lower() in ("open", "unresolved", "pending-decision"):
            flags.append(df.strip().upper())
        for f in (rv.get("decision_flags") or []):
            if isinstance(f, str) and ("open" in f.lower() or "-open" in f.lower()):
                flags.append(f)
        if flags:
            out.append({"collection": coll, "feature_id": rv.get("feature_id"),
                        "object_class": rv.get("object_class"),
                        "name": rv.get("name") or rv.get("feature_id"),
                        "flags": flags})
    return out


def derive_open_decisions(payload: dict) -> list[str]:
    """Human-readable open-decision descriptors for a bundle.

    Combines any bundle-level ``acceptance.open_decisions`` with descriptors
    derived from the leaves (Rule-9-OPEN stage, ADA concept/pending routes,
    concept-tier elements). This is what gives a *proposal* its required
    ``open_decisions`` metadata automatically.
    """
    decisions: list[str] = []
    seen: set[str] = set()

    def add(msg: str) -> None:
        if msg and msg not in seen:
            seen.add(msg)
            decisions.append(msg)

    acc = payload.get("acceptance") or {}
    for d in (acc.get("open_decisions") or []):
        if isinstance(d, str):
            add(d)

    for _coll, leaf in S._iter_leaves(payload):
        rv = leaf.get("@review") or {}
        oc = rv.get("object_class")
        name = rv.get("name") or rv.get("feature_id")
        if rv.get("rule9_status") == "open":
            add(f"RULE-9-OPEN: stage placement undecided (deck '{name}')")
        elif oc == "ada_route":
            st = (rv.get("ada_status") or "").lower()
            if "concept" in st or "pending" in st:
                add(f"ADA-CONCEPT-PENDING: route '{name}' is concept pending civil/code detailing")
        elif rv.get("concept_tier"):
            add(f"CONCEPT-TIER: '{name}' is concept-grade, not constructed")
    return decisions


# ── URL helper ─────────────────────────────────────────────────────────────────
def speckle_url(server: str | None, project_id: str | None,
                model_id: str | None, version_id: str | None) -> str | None:
    """Speckle v3 deep link: {server}/projects/{p}/models/{m}@{v}."""
    if not server or not project_id:
        return None
    url = f"{server.rstrip('/')}/projects/{project_id}"
    if model_id:
        url += f"/models/{model_id}"
        if version_id:
            url += f"@{version_id}"
    return url


# ── entry construction ─────────────────────────────────────────────────────────
def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def build_entry(payload: dict, *, design_state: str, gates: dict | None = None,
                publish_result: dict | None = None, server: str | None = None,
                open_decisions: list[str] | None = None, notes: str | None = None,
                validation_commands: list[str] | None = None,
                timestamp: str | None = None, repo: str = REPO) -> dict:
    """Build a ledger entry. ``gates`` is the dict from publish_speckle.gather_gates
    (verify_passed / boundary_errs / repo_clean). ``publish_result`` is the dict
    do_publish returns (object_id / version_id / project_id / model_id); omit it
    for a dry-run preview entry."""
    gates = gates or {}
    publish_result = publish_result or {}
    acc = payload.get("acceptance") or {}
    br = payload.get("bridge") or {}

    project_id = publish_result.get("project_id") or os.environ.get("SPECKLE_PROJECT_ID")
    model_id = publish_result.get("model_id") or os.environ.get("SPECKLE_MODEL_ID")
    version_id = publish_result.get("version_id")
    object_id = publish_result.get("object_id")

    verify_passed = gates.get("verify_passed")
    boundary_errs = gates.get("boundary_errs") or []
    boundary_ok = (len(boundary_errs) == 0)
    repo_clean = gates.get("repo_clean")
    # scratch publishes are not validated mirrors: validation_passed is null, not a
    # false claim of having validated.
    if design_state == DS_SCRATCH:
        validation_passed: bool | None = None
    else:
        validation_passed = bool(verify_passed and boundary_ok)

    return {
        "timestamp": timestamp or _now_iso(),
        "design_state": design_state,
        "project_slug": acc.get("project"),
        "branch": acc.get("branch"),
        "project_id": project_id,
        "model_id": model_id,
        "version_id": version_id,
        "object_id": object_id,
        "speckle_url": speckle_url(server, project_id, model_id, version_id),
        "source_git_commit": br.get("git_commit") or git_head(repo),
        "export_payload_hash": payload_hash(payload),
        "validation_commands": list(validation_commands or DEFAULT_VALIDATION_COMMANDS),
        "validation_passed": validation_passed,
        "validation_detail": {
            "verify_unreal_export": verify_passed,
            "object_truth_boundary": boundary_ok,
            "boundary_error_count": len(boundary_errs),
            "repo_clean": repo_clean,
        },
        "source_files": collect_source_files(payload),
        "open_decisions": (open_decisions if open_decisions is not None
                           else derive_open_decisions(payload)),
        "notes": notes or "",
    }


# ── ledger IO ──────────────────────────────────────────────────────────────────
def load_ledger(path: str = LEDGER_PATH) -> dict:
    if not os.path.exists(path):
        return {"schema": LEDGER_SCHEMA, "note": LEDGER_NOTE, "entries": []}
    with open(path) as fh:
        d = json.load(fh)
    d.setdefault("entries", [])
    d.setdefault("schema", LEDGER_SCHEMA)
    return d


def _atomic_write(path: str, ledger: dict) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(ledger, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    os.replace(tmp, path)


def append_entry(entry: dict, path: str = LEDGER_PATH) -> dict:
    """Append ``entry`` and persist. Returns the updated ledger."""
    ledger = load_ledger(path)
    ledger.setdefault("schema", LEDGER_SCHEMA)
    ledger.setdefault("note", LEDGER_NOTE)
    ledger["entries"].append(entry)
    ledger["updated"] = entry.get("timestamp")
    _atomic_write(path, ledger)
    return ledger


# ── read-side reports ──────────────────────────────────────────────────────────
def find_entries(ledger: dict, *, version_id: str | None = None,
                 object_id: str | None = None, branch: str | None = None,
                 model_id: str | None = None) -> list[dict]:
    """All entries matching ANY of the given identifiers (most-specific first is
    the caller's job). Returns [] if nothing matches."""
    out = []
    for e in ledger.get("entries", []):
        if version_id and e.get("version_id") == version_id:
            out.append(e); continue
        if object_id and e.get("object_id") == object_id:
            out.append(e); continue
        if model_id and e.get("model_id") == model_id:
            out.append(e); continue
        if branch and e.get("branch") == branch:
            out.append(e); continue
    return out


def entries_for_report(ledger: dict, *, include_scratch: bool = False) -> list[dict]:
    """Ledger entries for reporting. Scratch (render/debug) publishes are excluded
    by default — they are not part of the acceptance record."""
    return [e for e in ledger.get("entries", [])
            if include_scratch or e.get("design_state") != DS_SCRATCH]


def accepted_entries(ledger: dict) -> list[dict]:
    return [e for e in ledger.get("entries", []) if e.get("design_state") == DS_ACCEPTED]


def summarize(ledger: dict) -> dict:
    counts: dict[str, int] = {}
    for e in ledger.get("entries", []):
        counts[e.get("design_state", "?")] = counts.get(e.get("design_state", "?"), 0) + 1
    return {"total": len(ledger.get("entries", [])), "by_state": counts,
            "accepted": len(accepted_entries(ledger))}


# ── cli (inspection only; publish_speckle.py is the writer) ───────────────────
def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Inspect the Speckle publish ledger.")
    ap.add_argument("--path", default=LEDGER_PATH)
    ap.add_argument("--accepted-only", action="store_true",
                    help="show only accepted entries (the acceptance record)")
    ap.add_argument("--include-scratch", action="store_true",
                    help="include scratch (render/debug) entries in the listing")
    ap.add_argument("--json", action="store_true", help="emit raw JSON")
    args = ap.parse_args(argv)

    ledger = load_ledger(args.path)
    if args.accepted_only:
        entries = accepted_entries(ledger)
    else:
        entries = entries_for_report(ledger, include_scratch=args.include_scratch)

    if args.json:
        print(json.dumps({"summary": summarize(ledger), "entries": entries}, indent=2))
        return 0

    s = summarize(ledger)
    print(f"Speckle publish ledger: {args.path}")
    print(f"  {s['total']} entries  ({', '.join(f'{k}={v}' for k, v in s['by_state'].items()) or 'empty'})")
    print(f"  NOTE: {LEDGER_NOTE}\n")
    for e in entries:
        print(f"  · {e.get('timestamp')}  [{e.get('design_state')}]  {e.get('branch')}")
        print(f"      version={e.get('version_id')}  commit={e.get('source_git_commit')}")
        print(f"      validated={e.get('validation_passed')}  hash={e.get('export_payload_hash')}")
        if e.get("open_decisions"):
            print(f"      open_decisions: {len(e['open_decisions'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
