#!/usr/bin/env python3
"""Boundary tests for the Speckle review bridge.

Proves the object-truth boundary is enforced: publication is blocked when

  1. a leaf is missing provenance (source_file / feature_id),
  2. a leaf is missing a required validation field (e.g. seating C_mm key),
  3. an ADA status string has been strengthened past 'concept/pending',
  4. the planning-grade warnings are dropped,
  5. the branch prefix disagrees with acceptance.state,
  6. the live Unreal-export verification fails.

and that the live, unmodified bundle passes all of the above.

Runs as a plain script (repo convention: `python scripts/test_*.py`). No pytest
dependency. Exit 0 = all checks pass, exit 1 = a check failed.
"""
from __future__ import annotations

import copy
import json
import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import speckle_common as S  # noqa: E402
import publish_speckle as P  # noqa: E402
import export_speckle_payload as X  # noqa: E402

RESULTS: list[tuple[bool, str]] = []
FIXTURE = os.path.join(S.REPO, "tests", "fixtures", "speckle_payload_minimal.json")


def check(cond: bool, label: str) -> None:
    RESULTS.append((bool(cond), label))


# ── fake specklepy (mocks the real send path without a live server) ───────────
def install_fake_specklepy(calls: dict):
    """Install a minimal fake specklepy module tree into sys.modules so
    publish_speckle.do_publish exercises the REAL send-path logic (including
    _dict_to_base) against recordable fakes. Returns the list of module names
    added, for teardown. Import PATHS mirror the names do_publish imports — those
    paths were verified against the specklepy docs (CreateVersionInput lives at
    specklepy.core.api.inputs.version_inputs)."""
    added = []

    def mod(name: str) -> types.ModuleType:
        m = types.ModuleType(name)
        sys.modules[name] = m
        added.append(name)
        return m

    class FakeBase:
        def __init__(self):
            object.__setattr__(self, "_items", {})
            object.__setattr__(self, "speckle_type", "Base")

        def __setitem__(self, k, v):
            self._items[k] = v

        def __getitem__(self, k):
            return self._items[k]

    def fake_send(base=None, transports=None):
        calls["send_base"] = base
        calls["send_transports"] = transports
        # prove _dict_to_base produced a Base carrying the root speckle_type
        calls["send_base_speckle_type"] = getattr(base, "speckle_type", None)
        return "obj_FAKE_ID"

    class FakeServerTransport:
        def __init__(self, stream_id=None, client=None):
            calls["transport_stream_id"] = stream_id
            calls["transport_client"] = client

    class FakeVersion:
        id = "ver_FAKE_ID"
        message = "ok"

    class FakeVersionResource:
        def create(self, inp):
            calls["version_create_input"] = inp
            return FakeVersion()

    class FakeClient:
        def __init__(self, host=None):
            calls["client_host"] = host
            self.version = FakeVersionResource()

        def authenticate_with_token(self, token):
            calls["auth_token"] = token

    class FakeCreateVersionInput:
        def __init__(self, **kw):
            self.kw = kw

    # build the package tree at the exact import paths do_publish uses
    mod("specklepy")
    objects = mod("specklepy.objects"); objects.Base = FakeBase
    api = mod("specklepy.api")
    operations = mod("specklepy.api.operations"); operations.send = fake_send
    api.operations = operations
    client_mod = mod("specklepy.api.client"); client_mod.SpeckleClient = FakeClient
    mod("specklepy.transports")
    server = mod("specklepy.transports.server"); server.ServerTransport = FakeServerTransport
    mod("specklepy.core"); mod("specklepy.core.api"); mod("specklepy.core.api.inputs")
    vi = mod("specklepy.core.api.inputs.version_inputs")
    vi.CreateVersionInput = FakeCreateVersionInput
    return added


def uninstall_modules(names):
    for n in names:
        sys.modules.pop(n, None)


def _first_leaf(payload: dict, coll_name: str) -> dict:
    coll = next(c for c in payload["@elements"] if c["name"] == coll_name)
    return coll["@elements"][0]


def _has_err(errs: list[str], needle: str) -> bool:
    return any(needle in e for e in errs)


def load_live_payload() -> dict:
    """Build the payload in-process from the live export (no file dependency)."""
    export = S.load_export()
    actor_path = os.path.join(S.EXPORT_DIR, "manifests/actor_manifest.json")
    export["_actor_by_fid"] = {a["source_feature_id"]: a
                               for a in S.jload(actor_path).get("actors", [])} \
        if os.path.exists(actor_path) else {}
    return X.build_payload(export, S.STATE_ACCEPTED, None)


def main() -> int:
    base = load_live_payload()

    # ── 0. positive control: the live bundle is clean ─────────────────────────
    errs = S.validate_payload(base)
    check(errs == [], f"live bundle passes the boundary (got {len(errs)} errs: {errs[:3]})")

    # ── 1. missing provenance: drop source_file from a seating leaf ───────────
    p1 = copy.deepcopy(base)
    _first_leaf(p1, "Seating")["@review"]["source_file"] = ""
    e1 = S.validate_payload(p1)
    check(_has_err(e1, "missing provenance field 'source_file'"),
          "missing source_file BLOCKS (provenance gate)")

    # also: a feature_id wiped out
    p1b = copy.deepcopy(base)
    _first_leaf(p1b, "Seating")["@review"]["feature_id"] = None
    check(_has_err(S.validate_payload(p1b), "missing provenance field 'feature_id'"),
          "missing feature_id BLOCKS (provenance gate)")

    # also: a source_file that does not exist on disk
    p1c = copy.deepcopy(base)
    _first_leaf(p1c, "Seating")["@review"]["source_file"] = "vectors_geojson/does_not_exist.geojson"
    check(_has_err(S.validate_payload(p1c), "source_file does not exist"),
          "non-existent source_file BLOCKS (provenance gate)")

    # ── 2. missing validation field: drop the C_mm KEY from a seating leaf ────
    p2 = copy.deepcopy(base)
    _first_leaf(p2, "Seating")["@review"].pop("C_mm", None)
    check(_has_err(S.validate_payload(p2), "missing validation field 'C_mm'"),
          "missing C_mm key BLOCKS (validation-field gate)")

    # band_status emptied (non-nullable) must also block
    p2b = copy.deepcopy(base)
    _first_leaf(p2b, "Seating")["@review"]["band_status"] = ""
    check(_has_err(S.validate_payload(p2b), "validation field 'band_status' is empty"),
          "empty band_status BLOCKS (validation-field gate)")

    # ── 3. ADA status strengthened past concept/pending ───────────────────────
    p3 = copy.deepcopy(base)
    ada = next(e for e in next(c for c in p3["@elements"] if c["name"] == "ADA")["@elements"]
               if e["@review"]["object_class"] == "ada_route")
    ada["@review"]["ada_status"] = "ADA-compliant"  # stripped the concept caveat
    check(_has_err(S.validate_payload(p3), "ADA status strengthened"),
          "strengthened ADA status BLOCKS (no silent 'compliant')")

    # ── 4. dropped planning-grade warnings ────────────────────────────────────
    p4 = copy.deepcopy(base)
    p4["warnings"] = []
    e4 = S.validate_payload(p4)
    check(_has_err(e4, "warnings block is empty") and _has_err(e4, "Rule 9"),
          "dropped warnings BLOCK (planning-grade caveats gate)")

    # ── 5. branch/state mismatch ──────────────────────────────────────────────
    p5 = copy.deepcopy(base)
    p5["acceptance"]["branch"] = "proposal/whatever-20260617"  # state is 'accepted'
    check(_has_err(S.validate_payload(p5), "disagrees with acceptance.state"),
          "branch prefix vs acceptance.state mismatch BLOCKS")

    # ── 6. failed Unreal-export verification blocks publication ───────────────
    fail_cmd = [sys.executable, "-c", "import sys; sys.exit(1)"]
    ok_fail, reasons_fail = P.preflight(base, verify_cmd=fail_cmd)
    check((not ok_fail) and any("verification FAILED" in r for r in reasons_fail),
          "failed unreal-export verify BLOCKS publication (preflight gate 1)")

    # ── 6b. live verify gate actually passes, so preflight clears the real tree
    ok_live, reasons_live = P.preflight(base)
    check(ok_live, f"live preflight CLEARS (verify green + boundary clean): {reasons_live}")

    # ── 7. committed fixture documents every schema and stays boundary-valid ──
    if os.path.exists(FIXTURE):
        with open(FIXTURE) as fh:
            fix = json.load(fh)
        check(S.validate_payload(fix) == [], "committed minimal fixture passes the boundary")
        classes = {leaf["@review"]["object_class"]
                   for c in fix["@elements"] for leaf in c["@elements"]}
        want = {"seating_row", "stage_feature", "ada_route", "ada_node", "reference"}
        check(want <= classes,
              f"fixture documents every object_class (missing {want - classes})")
    else:
        check(False, f"committed fixture missing: {os.path.relpath(FIXTURE, S.REPO)} "
                     "(regenerate: export_speckle_payload.py --emit-fixture ...)")

    # ── 8. dry run imports NO sdk (laziness) ──────────────────────────────────
    had_speckle = "specklepy" in sys.modules
    P.preflight(base)              # the dry-run gauntlet
    P.publish_plan(base, "https://speckle.lan")
    check(had_speckle or "specklepy" not in sys.modules,
          "dry-run path imports no specklepy (lazy import only on --publish)")

    # ── 9. mocked --publish send path: real do_publish against fakes ──────────
    calls: dict = {}
    added = install_fake_specklepy(calls)
    saved_env = {k: os.environ.get(k) for k in ("SPECKLE_PROJECT_ID", "SPECKLE_MODEL_ID")}
    try:
        os.environ["SPECKLE_PROJECT_ID"] = "proj_123"
        os.environ["SPECKLE_MODEL_ID"] = "model_456"
        result = P.do_publish(base, "https://speckle.lan", "tok_secret",
                              "accepted: test @ deadbeef")
        check(calls.get("client_host") == "https://speckle.lan",
              "do_publish: SpeckleClient built with server host")
        check(calls.get("auth_token") == "tok_secret",
              "do_publish: authenticate_with_token called with the token")
        check(calls.get("transport_stream_id") == "proj_123",
              "do_publish: ServerTransport stream_id == project id")
        check(calls.get("send_base_speckle_type") == base.get("speckle_type"),
              "do_publish: _dict_to_base built a Base carrying the root speckle_type")
        vk = getattr(calls.get("version_create_input"), "kw", {})
        check(vk.get("project_id") == "proj_123" and vk.get("model_id") == "model_456"
              and vk.get("object_id") == "obj_FAKE_ID" and vk.get("message"),
              "do_publish: CreateVersionInput wired (project/model/object/message)")
        check(result.get("object_id") == "obj_FAKE_ID"
              and result.get("version_id") == "ver_FAKE_ID",
              "do_publish: returns the sent object id + created version id")
    finally:
        uninstall_modules(added)
        for k, v in saved_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    # ── report ────────────────────────────────────────────────────────────────
    n_pass = sum(1 for ok, _ in RESULTS if ok)
    for ok, label in RESULTS:
        print(f"  {'PASS' if ok else 'FAIL'}  {label}")
    print(f"\n{n_pass}/{len(RESULTS)} checks pass")
    return 0 if n_pass == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
