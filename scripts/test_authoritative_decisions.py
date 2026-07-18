#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
import base64
import hashlib
from pathlib import Path

from authoritative_decisions import (
    apply_decisions,
    index_decisions,
    load_decision_record,
    load_site_data_js,
)

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

design_state = {
    "warnings": [],
    "elements": {
        "stage": {},
        "ada_route": {"status": "ADA-compliant route concept pending civil/code detailing"},
    },
    "pending_decisions": [{"id": "decision_1_seating_scope"}],
}
evaluation = {"summary": {}, "checks": [
    {"id": "seating_scope", "status": "warn"},
    {"id": "stage_rule9", "status": "fail"},
    {"id": "ada_concepts", "status": "pass"},
]}
terrain_blob = base64.b64encode(b"terrain-sentinel").decode()
site_data = {
    "meta": {"warnings": []},
    "terrain": {"existing": {"b64": terrain_blob}},
    "layers": {
        "ada_rebuild": {
            "status": "ADA-compliant route concept pending civil/code detailing",
        },
    },
    "audit": {"checks": evaluation["checks"], "pending": {"id": "decision_1_seating_scope"}},
}
before = hashlib.sha256(json.dumps(site_data["terrain"], sort_keys=True).encode()).hexdigest()

projected = apply_decisions(record, design_state, evaluation, site_data)
projected_state, projected_eval, projected_site = projected
after = hashlib.sha256(json.dumps(projected_site["terrain"], sort_keys=True).encode()).hexdigest()

assert before == after
assert len(projected_state["adopted_decisions"]) == 3
assert "pending_decisions" not in projected_state
assert projected_eval["summary"]["seating_decision"] == (
    "ADOPTED C — ambitious shaped bowl (seating scope); fallback A — Scenario E baseline")
assert projected_eval["summary"]["stage_decision"] == (
    "ADOPTED Path A — audience-axis alignment; geometry validation pending")
checks = {item["id"]: item for item in projected_eval["checks"]}
assert checks["seating_scope"]["value"].startswith("ADOPTED C")
assert checks["stage_rule9"]["status"] == "fail"
assert "Path A" in checks["stage_rule9"]["value"]
assert "civil/code" in checks["ada_concepts"]["note"]
assert "pending" not in projected_site["audit"]
assert len(projected_site["audit"]["adopted_decisions"]) == 3
assert "ADA-compliant" not in json.dumps(projected_state)
assert "ADA-compliant" not in json.dumps(projected_site)

# Preservation-mode synchronization may be repeated; decision warnings must
# remain a replacement set instead of accumulating on each projection.
reprojected_state, _, _ = apply_decisions(
    record, projected_state, projected_eval, projected_site)
assert reprojected_state["warnings"] == projected_state["warnings"]

# Projection must reflect the authoritative record, not the currently adopted
# options.  These are all valid selections under the decision validator.
alternate = json.loads(json.dumps(record))
alternate_decisions = index_decisions(alternate)
alternate_decisions["seating_scope"].update(
    selected_option="B", selected_label="compact_civic_bowl",
)
alternate_decisions["stage_rule9"].update(
    selected_option="wide_fan", selected_label="broad_fan_declaration",
)
alternate_decisions["ada_concept"].update(
    selected_option="D2", selected_label="constructed_diagonal_terrace_cut",
)
alternate_state, alternate_eval, alternate_site = apply_decisions(
    alternate, design_state, evaluation, site_data)
alternate_checks = {item["id"]: item for item in alternate_eval["checks"]}
assert "B" in alternate_eval["summary"]["seating_decision"]
assert "A" in alternate_eval["summary"]["seating_decision"]
assert "wide fan" in alternate_eval["summary"]["stage_decision"]
assert "broad fan declaration" in alternate_checks["stage_rule9"]["value"]
assert "D2" in alternate_eval["summary"]["ada_decision"]
assert "constructed diagonal terrace cut" in alternate_checks["ada_concepts"]["value"]
assert "Path A" not in json.dumps(alternate_state)
assert "Path A" not in json.dumps(alternate_site)

# The checked-in generated outputs must present adoption consistently while
# retaining the intentionally non-passing geometry/validation status.
current_state = json.loads((ROOT / "truth_package/design_state.current.json").read_text())
current_evaluation = json.loads(
    (ROOT / "truth_package/evaluation_report.current.json").read_text())
current_site = load_site_data_js(ROOT / "web_viewer/data/site_data.js")
for current in (current_state, current_evaluation, current_site):
    rendered = json.dumps(current)
    assert "Rule 9 OPEN" not in rendered
    assert "Rule 9 is OPEN" not in rendered
    assert "no adoption path" not in rendered
    assert "ADA-compliant" not in rendered

assert current_evaluation["summary"]["stage"].startswith("ADOPTED")
current_checks = {item["id"]: item for item in current_evaluation["checks"]}
assert current_checks["stage_rule9"]["status"] == "fail"
stage_layer = next(
    layer for layer in current_site["audit"]["layer_truth"]
    if layer["layer"] == "Stage deck")
assert "adopted" in stage_layer["source"].lower()
assert "provisional" in stage_layer["tier"]

print("PASS — authoritative decision artifact and validation boundary")
