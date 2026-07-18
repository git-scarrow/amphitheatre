from __future__ import annotations

import json
from pathlib import Path

SCHEMA = "petoskey-pit/adopted-decisions/1"
ALLOWED_OPTIONS = {
    "seating_scope": {"A", "B", "C"},
    "stage_rule9": {"A", "B", "C", "wide_fan"},
    "ada_concept": {"C", "D2"},
}
EXPECTED_IMPLEMENTATION = {
    "seating_scope": "pending_package_propagation",
    "stage_rule9": "pending_geometry_and_validation",
    "ada_concept": "planning_grade_pending_civil_detailing",
}


def index_decisions(record: dict) -> dict[str, dict]:
    decisions = record.get("decisions")
    if not isinstance(decisions, list):
        raise ValueError("decisions must be a list")
    indexed = {item.get("id"): item for item in decisions}
    if set(indexed) != set(ALLOWED_OPTIONS) or len(indexed) != len(decisions):
        raise ValueError("decisions must contain each required unique id")
    return indexed


def load_decision_record(path: Path) -> dict:
    record = json.loads(path.read_text())
    if record.get("schema") != SCHEMA:
        raise ValueError(f"schema must be {SCHEMA}")
    if record.get("authority") != "project_owner":
        raise ValueError("authority must be project_owner")
    decisions = index_decisions(record)
    for decision_id, allowed in ALLOWED_OPTIONS.items():
        decision = decisions[decision_id]
        if decision.get("selected_option") not in allowed:
            raise ValueError(f"{decision_id}.selected_option is invalid")
        if decision.get("decision_status") != "adopted":
            raise ValueError(f"{decision_id}.decision_status must be adopted")
        if decision.get("implementation_status") != EXPECTED_IMPLEMENTATION[decision_id]:
            raise ValueError(f"{decision_id}.implementation_status is invalid")
        if decision.get("rationale") != "owner_selection_no_additional_rationale_recorded":
            raise ValueError(f"{decision_id}.rationale invents owner reasoning")
    if decisions["seating_scope"].get("fallback_option") != "A":
        raise ValueError("seating_scope.fallback_option must be A")
    return record
