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
DECISION_AUTHORITY_PATH = "analysis/decision_packet/adopted_decisions.json"
DECISION_SOURCE_PATHS = {
    "adopted_decisions": DECISION_AUTHORITY_PATH,
    "canon": "docs/DESIGN_CANON.md",
    "decision_brief": "docs/HUMAN_DECISION_BRIEF.md",
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


def _source_entry(repo: Path, rel: str, *, presence_key: str) -> dict:
    path = repo / rel
    present = path.is_file()
    return {
        "path": rel,
        "sha256_12": hashlib.sha256(path.read_bytes()).hexdigest()[:12]
        if present else None,
        presence_key: present,
    }


def _refresh_decision_sources(repo: Path, sources: dict,
                              *, presence_key: str = "present") -> dict:
    refreshed = copy.deepcopy(sources)
    for key, rel in DECISION_SOURCE_PATHS.items():
        refreshed[key] = _source_entry(repo, rel, presence_key=presence_key)
    return refreshed


def _display_label(decision: dict) -> str:
    """Return the record-owned label in human-readable form."""
    return str(decision["selected_label"]).replace("_", " ")


def _option_display(decision: dict, *, stage: bool = False) -> str:
    """Format an option without baking a particular adopted option into code."""
    option = str(decision["selected_option"]).replace("_", " ")
    if stage and option in {"A", "B", "C"}:
        return f"Path {option}"
    return option


def _replace_legacy_decision_text(value: object, stage_status: str) -> object:
    """Replace stale pre-adoption wording at every generated-output layer."""
    if isinstance(value, dict):
        return {key: _replace_legacy_decision_text(item, stage_status)
                for key, item in value.items()}
    if isinstance(value, list):
        return [_replace_legacy_decision_text(item, stage_status) for item in value]
    if not isinstance(value, str):
        return value
    replacements = (
        ("DESIGN_CANON.md Rule 9 is OPEN (inherited az-150 stage; "
         "+25.6° audience-axis mismatch on record).", stage_status),
        ("DESIGN_CANON Rule 9 OPEN", stage_status),
        ("Rule 9 is OPEN", stage_status),
        ("Rule 9 OPEN (provisional)", stage_status),
        ("Rule 9 OPEN", stage_status),
        ("no adoption path (A/B/C/wide-fan) declared; stage shown for "
         "massing only; every stage-derived artifact re-emits on adoption",
         "exact footprint, apron, typology, fan declaration and validation "
         "remain incomplete"),
        ("no adoption path declared",
         "geometry emission and validation pending"),
        ("Seating scope Decision 1 is pending; this package shows the "
         "Scenario E baseline (option A).",
         "Seating scope adoption is recorded in adopted_decisions; current "
         "geometry remains pending package propagation."),
        ("ADA-compliant route concept pending civil/code detailing",
         "Planning/concept-grade accessible-route direction pending civil/code "
         "determination"),
    )
    for stale, replacement in replacements:
        value = value.replace(stale, replacement)
    return value


def _is_decision_projection_warning(warning: object) -> bool:
    """Identify warning variants superseded by the authoritative record."""
    if not isinstance(warning, str):
        return False
    return (
        warning.startswith("Stage deck is PROVISIONAL:")
        or warning.startswith("Seating scope adoption is recorded")
        or (warning.startswith("Seating ") and " is adopted with " in warning)
        or (warning.startswith("Rule 9 ")
            and " is adopted; the inherited az-150 stage" in warning)
        or (warning.startswith("ADA Concept ") and " is adopted at " in warning)
        or "Decision 1 is pending" in warning
        or "no adoption path" in warning
    )


def apply_decisions(record: dict, design_state: dict, evaluation_report: dict,
                    site_data: dict) -> tuple[dict, dict, dict]:
    state = copy.deepcopy(design_state)
    report = copy.deepcopy(evaluation_report)
    site = copy.deepcopy(site_data)
    decisions = index_decisions(record)
    adopted = copy.deepcopy(record["decisions"])
    seating = decisions["seating_scope"]
    stage = decisions["stage_rule9"]
    ada = decisions["ada_concept"]
    seating_option = _option_display(seating)
    seating_fallback = str(seating["fallback_option"]).replace("_", " ")
    stage_option = _option_display(stage, stage=True)
    ada_option = _option_display(ada)
    seating_label = _display_label(seating)
    seating_fallback_label = str(seating["fallback_label"]).replace("_", " ")
    stage_label = _display_label(stage)
    ada_label = _display_label(ada)
    stage_status = (
        f"Rule 9 {stage_option} — {stage_label} is adopted; the inherited "
        "az-150 stage remains PROVISIONAL pending geometry emission and validation"
    )

    state = _replace_legacy_decision_text(state, stage_status)
    report = _replace_legacy_decision_text(report, stage_status)
    site = _replace_legacy_decision_text(site, stage_status)
    state["adopted_decisions"] = adopted
    state.pop("pending_decisions", None)
    state.setdefault("warnings", [])
    state["warnings"] = [
        warning for warning in state["warnings"]
        if not _is_decision_projection_warning(warning)
    ]
    state["warnings"].extend([
        f"Seating {seating_option} — {seating_label} is adopted with "
        f"{seating_fallback} — {seating_fallback_label} as fallback; the "
        "current package remains pending package propagation.",
        stage_status + ".",
        f"ADA Concept {ada_option} — {ada_label} is adopted at "
        "planning/concept grade; civil/code determination remains pending.",
    ])
    report["warnings"] = copy.deepcopy(state["warnings"])
    site["meta"]["warnings"] = copy.deepcopy(state["warnings"])
    canonical_sources = state.get("sources")
    if canonical_sources is not None:
        report["sources"] = copy.deepcopy(canonical_sources)
        site["audit"]["sources"] = copy.deepcopy(canonical_sources)
    state.setdefault("design_of_record", {})["status"] = (
        "seating / ADA / drainage cost-proxy ACCEPTED · "
        f"Rule 9 {stage_option} — {stage_label} ADOPTED; geometry validation pending"
    )
    state["elements"]["stage"]["status"] = (
        "PROVISIONAL — " + stage_status
    )
    state["elements"].setdefault("ada_route", {})["status"] = (
        "Planning/concept-grade accessible-route direction pending civil/code "
        "determination — topology, conflicts and slopes validated; code details "
        "explicitly unchecked"
    )

    report.setdefault("summary", {})["seating_decision"] = (
        f"ADOPTED {seating_option} — {seating_label}; fallback "
        f"{seating_fallback} — {seating_fallback_label}"
    )
    report["summary"]["stage"] = (
        f"ADOPTED {stage_option} — {stage_label}; geometry validation pending"
    )
    report["summary"]["stage_decision"] = report["summary"]["stage"]
    report["summary"]["ada_decision"] = (
        f"ADOPTED Concept {ada_option} — {ada_label}; civil/code determination pending"
    )
    report["summary"].pop("decision_1", None)
    _replace_check(report["checks"], "seating_scope", status="warn",
                   value=(f"ADOPTED {seating_option} — {seating_label}; fallback "
                          f"{seating_fallback} — {seating_fallback_label}"),
                   note="current package remains pending propagation",
                   source=DECISION_AUTHORITY_PATH)
    _replace_check(report["checks"], "stage_rule9", status="fail",
                   value=(f"DIRECTION ADOPTED — {stage_option} — {stage_label}; "
                          "inherited az-150 stage still PROVISIONAL"),
                   note="exact footprint, apron, typology, fan declaration and validation remain incomplete",
                   source=DECISION_AUTHORITY_PATH)
    _replace_check(report["checks"], "ada_concepts", status="pass",
                   value=f"ADOPTED Concept {ada_option} — {ada_label}",
                   note=("planning/concept-grade direction adopted; civil/code "
                         "determination remains incomplete"),
                   source=DECISION_AUTHORITY_PATH)

    site["audit"]["checks"] = copy.deepcopy(report["checks"])
    for layer in site["audit"].get("layer_truth", []):
        if layer.get("layer") == "Stage deck":
            layer["tier"] = "provisional"
            layer["source"] = "inherited az-150 stage — " + stage_status
    site["audit"]["adopted_decisions"] = adopted
    site["audit"]["decision_record"] = {
        "decided_on": record["decided_on"],
        "authority": record["authority"],
    }
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
    provenance_path = repo / "unreal_export/manifests/provenance.json"
    state = json.loads(state_path.read_text())
    report = json.loads(report_path.read_text())
    site = load_site_data_js(site_path)
    provenance = json.loads(provenance_path.read_text())
    state["sources"] = _refresh_decision_sources(
        repo, state.get("sources", {}))
    terrain_before = _json_hash(site["terrain"])
    state, report, site = apply_decisions(record, state, report, site)
    terrain_after = _json_hash(site["terrain"])
    if terrain_before != terrain_after:
        raise RuntimeError("decision projection changed the terrain payload")
    state_path.write_text(json.dumps(state, indent=1) + "\n")
    report_path.write_text(json.dumps(report, indent=1) + "\n")
    write_site_data_js(site_path, site)
    provenance["warnings"] = copy.deepcopy(state["warnings"])
    provenance["warnings_source"] = "truth_package/design_state.current.json"
    provenance["sources"] = _refresh_decision_sources(
        repo, provenance.get("sources", {}), presence_key="exists")
    provenance["sources"]["design_state"] = _source_entry(
        repo, "truth_package/design_state.current.json", presence_key="exists")
    provenance["decision_projection"] = {
        "decided_on": record["decided_on"],
        "authority": record["authority"],
        "stage_geometry": "historical_inherited_az_150_snapshot",
        "implements_stage_rule9_path_a": False,
    }
    provenance_path.write_text(json.dumps(provenance, indent=1) + "\n")
    print(f"updated {state_path.relative_to(repo)}")
    print(f"updated {report_path.relative_to(repo)}")
    print(f"updated {site_path.relative_to(repo)}")
    print(f"updated {provenance_path.relative_to(repo)} (metadata only)")
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
