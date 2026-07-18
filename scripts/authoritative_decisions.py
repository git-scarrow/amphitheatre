from __future__ import annotations

import copy
import hashlib
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


def _replace_check(checks: list[dict], check_id: str, **values) -> None:
    target = next((item for item in checks if item.get("id") == check_id), None)
    if target is None:
        raise ValueError(f"missing generated check: {check_id}")
    target.update(values)


def apply_decisions(record: dict, design_state: dict, evaluation_report: dict,
                    site_data: dict) -> tuple[dict, dict, dict]:
    state = copy.deepcopy(design_state)
    report = copy.deepcopy(evaluation_report)
    site = copy.deepcopy(site_data)
    index_decisions(record)
    adopted = copy.deepcopy(record["decisions"])

    state["adopted_decisions"] = adopted
    state.pop("pending_decisions", None)
    state.setdefault("warnings", [])
    state["warnings"] = [
        warning for warning in state["warnings"]
        if "Decision 1 is pending" not in warning and "no adoption path" not in warning
    ]
    state["warnings"].extend([
        "Seating C is adopted with A as fallback; the current package still shows A pending package propagation.",
        "Rule 9 Path A is adopted; the inherited az-150 stage remains PROVISIONAL pending geometry emission and validation.",
        "ADA Concept C is adopted at planning grade and remains pending civil/code detailing.",
    ])
    state["elements"]["stage"]["status"] = (
        "PROVISIONAL — Rule 9 Path A adopted; current inherited az-150 geometry "
        "pending replacement and validation"
    )

    report["summary"]["seating_decision"] = "ADOPTED C; fallback A"
    report["summary"]["stage_decision"] = "ADOPTED Path A; geometry validation pending"
    report["summary"]["ada_decision"] = "ADOPTED Concept C; civil/code detailing pending"
    report["summary"].pop("decision_1", None)
    _replace_check(report["checks"], "seating_scope", status="warn",
                   value="ADOPTED C — ambitious shaped bowl; fallback A",
                   note="current package still shows A pending propagation")
    _replace_check(report["checks"], "stage_rule9", status="fail",
                   value="DIRECTION ADOPTED — Path A; inherited az-150 stage still PROVISIONAL",
                   note="exact footprint, apron, typology, fan declaration and validation remain incomplete")
    _replace_check(report["checks"], "ada_concepts", status="pass",
                   value="ADOPTED C — naturalistic promenade",
                   note="planning direction adopted; civil/code detailing remains incomplete")

    site["meta"]["warnings"] = copy.deepcopy(state["warnings"])
    site["audit"]["checks"] = copy.deepcopy(report["checks"])
    site["audit"]["adopted_decisions"] = adopted
    site["audit"].pop("pending", None)
    return state, report, site


SITE_DATA_MARKER = "window.SITE_DATA = "


def load_site_data_js(path: Path) -> dict:
    text = path.read_text()
    if SITE_DATA_MARKER not in text:
        raise ValueError(f"{path} does not contain {SITE_DATA_MARKER!r}")
    payload = text.split(SITE_DATA_MARKER, 1)[1].strip()
    if not payload.endswith(";"):
        raise ValueError(f"{path} does not end with a JavaScript semicolon")
    return json.loads(payload[:-1])


def write_site_data_js(path: Path, data: dict) -> None:
    old_lines = path.read_text().splitlines()
    if len(old_lines) < 3 or not all(line.startswith("//") for line in old_lines[:2]):
        raise ValueError(f"{path} is missing its two generated header lines")
    header = "\n".join(old_lines[:2])
    path.write_text(
        header + "\n" + SITE_DATA_MARKER
        + json.dumps(data, separators=(",", ":")) + ";\n"
    )


def _json_hash(value: dict) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def sync_existing_outputs(repo: Path) -> None:
    record = load_decision_record(
        repo / "analysis/decision_packet/adopted_decisions.json")
    state_path = repo / "truth_package/design_state.current.json"
    report_path = repo / "truth_package/evaluation_report.current.json"
    site_path = repo / "web_viewer/data/site_data.js"
    state = json.loads(state_path.read_text())
    report = json.loads(report_path.read_text())
    site = load_site_data_js(site_path)
    terrain_before = _json_hash(site["terrain"])
    state, report, site = apply_decisions(record, state, report, site)
    terrain_after = _json_hash(site["terrain"])
    if terrain_before != terrain_after:
        raise RuntimeError("decision projection changed the terrain payload")
    state_path.write_text(json.dumps(state, indent=1) + "\n")
    report_path.write_text(json.dumps(report, indent=1) + "\n")
    write_site_data_js(site_path, site)
    print(f"updated {state_path.relative_to(repo)}")
    print(f"updated {report_path.relative_to(repo)}")
    print(f"updated {site_path.relative_to(repo)}")
    print("terrain payload preserved")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--sync-existing", action="store_true")
    parser.add_argument("--repo", type=Path,
                        default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args()
    if not args.sync_existing:
        parser.error("use --sync-existing")
    sync_existing_outputs(args.repo)
