#!/usr/bin/env python3
"""Tailnet-local Speckle webhook receiver — a handshake, not a geometry sink.

Speckle can emit a webhook when a version is created. This receiver treats that
event as a *handshake only*: it never pulls the geometry payload and never trusts
the event as design state. Its single job is to answer one question against the
repo-side ledger:

    "Does this Speckle version correspond to a recorded repo publish?"

and, in particular, to **flag any accepted/* version that has no valid ledger
entry** — because on the server an accepted/* model looks authoritative, but
Speckle history is not acceptance history unless the repo ledger backs it.

The decision logic (:func:`evaluate_version_event`) is a pure function so it is
unit-testable without a socket. The HTTP server is a thin wrapper:

    python scripts/speckle_webhook.py --serve --host 100.64.0.10 --port 8765
    python scripts/speckle_webhook.py --check event.json      # one-shot, exit 1 if FLAG

Verdict ``status`` values:
    ok      — version is backed by a ledger entry
    warn    — non-accepted version with no ledger entry (allowed but unrecorded)
    FLAG    — accepted/* version with no valid ledger entry (acceptance-history gap)
    mismatch— ledger entry exists but its design_state disagrees with the model prefix
    ignored — not a version-created event

Stdlib only. No specklepy, no outbound calls.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import speckle_ledger as L  # noqa: E402

VERSION_EVENT_NAMES = {"version_create", "versioncreated", "version_created",
                       "commit_create", "commitcreate"}


# ── event normalisation (Speckle webhook shapes vary by version) ──────────────
def _dig(d: dict, *paths):
    """Return the first present value among dotted ``paths`` (e.g. 'event.data.id')."""
    for path in paths:
        cur: object = d
        ok = True
        for key in path.split("."):
            if isinstance(cur, dict) and key in cur:
                cur = cur[key]
            else:
                ok = False
                break
        if ok and cur not in (None, ""):
            return cur
    return None


def normalize_event(event: dict) -> dict:
    """Pull the handshake fields out of a raw webhook body into a flat dict.

    Tolerant of v2 (``commit_create``) and v3 (``version_create``) shapes and of
    a pre-flattened test event. We only ever read identifiers + the model/branch
    name — never geometry."""
    name = _dig(event, "event_name", "event.event_name", "payload.event_name",
                "eventName", "type")
    return {
        "event_name": (str(name).lower() if name else None),
        "version_id": _dig(event, "version_id", "versionId",
                           "event.data.id", "payload.version.id", "commit.id",
                           "event.data.versionId"),
        "object_id": _dig(event, "object_id", "objectId",
                          "event.data.objectId", "payload.version.objectId",
                          "commit.referencedObject"),
        "project_id": _dig(event, "project_id", "projectId", "stream_id", "streamId",
                           "event.data.streamId", "payload.project.id", "stream.id"),
        "model_id": _dig(event, "model_id", "modelId", "branch_id",
                         "event.data.branchId", "payload.model.id"),
        "branch": _dig(event, "branch", "branch_name", "branchName", "model_name",
                       "modelName", "event.data.branchName", "payload.model.name",
                       "commit.branchName"),
    }


def branch_prefix(branch: str | None) -> str | None:
    if not branch:
        return None
    return branch.split("/", 1)[0]


# ── the verdict ────────────────────────────────────────────────────────────────
def evaluate_version_event(event: dict, ledger: dict) -> dict:
    """Pure handshake verdict for one webhook event against the ledger."""
    ev = normalize_event(event)
    name = ev["event_name"]
    if not name or name not in VERSION_EVENT_NAMES:
        return {"status": "ignored", "reason": f"not a version-created event ({name!r})",
                "event": ev}

    prefix = branch_prefix(ev["branch"])
    matches = L.find_entries(ledger, version_id=ev["version_id"],
                             object_id=ev["object_id"])
    # Prefer a version_id match; fall back to object_id; then to branch.
    if not matches and ev["branch"]:
        matches = L.find_entries(ledger, branch=ev["branch"])

    if matches:
        entry = matches[0]
        # the ledger entry exists — but does its design_state agree with the model
        # prefix the server reported?
        if prefix and entry.get("design_state") and prefix != entry["design_state"]:
            return {"status": "mismatch", "severity": "high",
                    "reason": (f"model prefix {prefix!r} disagrees with ledger "
                               f"design_state {entry['design_state']!r}"),
                    "event": ev, "ledger_entry": entry}
        return {"status": "ok",
                "reason": "version is backed by a repo ledger entry",
                "matched_by": ("version_id" if ev["version_id"]
                               and entry.get("version_id") == ev["version_id"]
                               else "object_id/branch"),
                "event": ev, "ledger_entry": entry}

    # no ledger entry
    if prefix == L.DS_ACCEPTED:
        return {"status": "FLAG", "severity": "high",
                "reason": ("accepted/* version has NO valid repo ledger entry — "
                           "Speckle history is not acceptance history. This version "
                           "must not be treated as accepted until a verified "
                           "accepted publish records it in data/speckle_publish_ledger.json."),
                "event": ev}
    return {"status": "warn", "severity": "low",
            "reason": (f"{prefix or 'unknown'}/* version has no ledger entry "
                       "(allowed for non-accepted channels, but unrecorded)"),
            "event": ev}


# ── HTTP wrapper (thin; the logic above is what matters) ──────────────────────
def _make_handler(ledger_path: str, log):
    from http.server import BaseHTTPRequestHandler

    class Handler(BaseHTTPRequestHandler):
        def _reply(self, code: int, body: dict):
            payload = json.dumps(body).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):  # health check
            self._reply(200, {"status": "alive",
                              "ledger": os.path.relpath(ledger_path, L.REPO)})

        def do_POST(self):
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b"{}"
            try:
                event = json.loads(raw or b"{}")
            except json.JSONDecodeError as exc:
                self._reply(400, {"status": "error", "reason": f"bad JSON: {exc}"})
                return
            verdict = evaluate_version_event(event, L.load_ledger(ledger_path))
            log(f"[webhook] {verdict['status']}: {verdict.get('reason')}")
            # Always 200 so Speckle does not retry-storm; the verdict is in the body.
            self._reply(200, verdict)

        def log_message(self, *a):  # quiet default access log
            return

    return Handler


def serve(host: str, port: int, ledger_path: str) -> int:
    from http.server import HTTPServer
    handler = _make_handler(ledger_path, print)
    httpd = HTTPServer((host, port), handler)
    print(f"Speckle webhook receiver on http://{host}:{port}  "
          f"(ledger: {os.path.relpath(ledger_path, L.REPO)})")
    print("  POST a Speckle 'version created' event; GET / for health. Ctrl-C to stop.")
    print("  Bind to the tailnet IP (e.g. --host 100.64.0.10) to keep it private.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--serve", action="store_true", help="run the HTTP receiver")
    ap.add_argument("--host", default="127.0.0.1",
                    help="bind host (use the tailnet IP, e.g. 100.64.0.10, to keep private)")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--ledger", default=L.LEDGER_PATH)
    ap.add_argument("--check", metavar="EVENT_JSON", default=None,
                    help="evaluate one event file and print the verdict (exit 1 if FLAG)")
    args = ap.parse_args(argv)

    if args.check:
        with open(args.check) as fh:
            event = json.load(fh)
        verdict = evaluate_version_event(event, L.load_ledger(args.ledger))
        print(json.dumps(verdict, indent=2, ensure_ascii=False))
        return 1 if verdict["status"] in ("FLAG", "mismatch") else 0

    if args.serve:
        return serve(args.host, args.port, args.ledger)

    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
