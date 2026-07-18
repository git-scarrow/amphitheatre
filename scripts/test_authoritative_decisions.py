#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
import base64
import hashlib
from pathlib import Path

from authoritative_decisions import apply_decisions, index_decisions, load_decision_record

ROOT = Path(__file__).resolve().parent.parent
RECORD = ROOT / "analysis/decision_packet/adopted_decisions.json"


record = load_decision_record(RECORD)
decisions = index_decisions(record)

assert record["schema"] == "petoskey-pit/adopted-decisions/1"
assert record["decided_on"] == "2026-07-18"
assert record["authority"] == "project_owner"
assert decisions["seating_scope"]["selected_option"] == "C"
assert decisions["seating_scope"]["fallback_option"] == "A"
assert decisions["stage_rule9"]["selected_option"] == "A"
assert decisions["ada_concept"]["selected_option"] == "C"
assert all(d["decision_status"] == "adopted" for d in decisions.values())

bad = json.loads(json.dumps(record))
bad["decisions"][0]["selected_option"] = "Z"
with tempfile.TemporaryDirectory() as td:
    path = Path(td) / "bad.json"
    path.write_text(json.dumps(bad))
    try:
        load_decision_record(path)
    except ValueError as exc:
        assert "seating_scope.selected_option" in str(exc)
    else:
        raise AssertionError("invalid seating option was accepted")

design_state = {"warnings": [], "elements": {"stage": {}}, "pending_decisions": [{"id": "decision_1_seating_scope"}]}
evaluation = {"summary": {}, "checks": [
    {"id": "seating_scope", "status": "warn"},
    {"id": "stage_rule9", "status": "fail"},
    {"id": "ada_concepts", "status": "pass"},
]}
terrain_blob = base64.b64encode(b"terrain-sentinel").decode()
site_data = {"meta": {"warnings": []}, "terrain": {"existing": {"b64": terrain_blob}}, "audit": {"checks": evaluation["checks"], "pending": {"id": "decision_1_seating_scope"}}}
before = hashlib.sha256(json.dumps(site_data["terrain"], sort_keys=True).encode()).hexdigest()

projected = apply_decisions(record, design_state, evaluation, site_data)
projected_state, projected_eval, projected_site = projected
after = hashlib.sha256(json.dumps(projected_site["terrain"], sort_keys=True).encode()).hexdigest()

assert before == after
assert len(projected_state["adopted_decisions"]) == 3
assert "pending_decisions" not in projected_state
assert projected_eval["summary"]["seating_decision"] == "ADOPTED C; fallback A"
assert projected_eval["summary"]["stage_decision"] == "ADOPTED Path A; geometry validation pending"
checks = {item["id"]: item for item in projected_eval["checks"]}
assert checks["seating_scope"]["value"].startswith("ADOPTED C")
assert checks["stage_rule9"]["status"] == "fail"
assert "Path A" in checks["stage_rule9"]["value"]
assert "civil/code" in checks["ada_concepts"]["note"]
assert "pending" not in projected_site["audit"]
assert len(projected_site["audit"]["adopted_decisions"]) == 3

print("PASS — authoritative decision artifact and validation boundary")
