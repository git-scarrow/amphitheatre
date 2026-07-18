#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from authoritative_decisions import index_decisions, load_decision_record

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

print("PASS — authoritative decision artifact and validation boundary")
