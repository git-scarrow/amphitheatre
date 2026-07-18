#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
import base64
import hashlib
import subprocess
import sys
from pathlib import Path

from authoritative_decisions import (
    _json_hash,
    apply_decisions,
    index_decisions,
    load_decision_record,
    load_site_data_js,
    sync_existing_outputs,
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
assert projected_state["warnings"] == projected_eval["warnings"]
assert projected_state["warnings"] == projected_site["meta"]["warnings"]
assert projected_eval["summary"]["seating_decision"] == (
    "ADOPTED C — ambitious shaped bowl (seating scope); fallback A — Scenario E baseline")
assert projected_eval["summary"]["stage_decision"] == (
    "ADOPTED Path A — audience-axis alignment; geometry validation pending")
checks = {item["id"]: item for item in projected_eval["checks"]}
decision_authority = "analysis/decision_packet/adopted_decisions.json"
assert all(
    checks[check_id]["source"] == decision_authority
    for check_id in ("seating_scope", "stage_rule9", "ada_concepts")
)
assert checks["seating_scope"]["value"].startswith("ADOPTED C")
assert checks["stage_rule9"]["status"] == "fail"
assert "Path A" in checks["stage_rule9"]["value"]
assert "civil/code" in checks["ada_concepts"]["note"]
assert "pending" not in projected_site["audit"]
assert len(projected_site["audit"]["adopted_decisions"]) == 3
assert projected_site["audit"]["decision_record"] == {
    "decided_on": record["decided_on"],
    "authority": record["authority"],
}
assert "ADA-compliant" not in json.dumps(projected_state)
assert "ADA-compliant" not in json.dumps(projected_site)

# Preservation-mode synchronization may be repeated; decision warnings must
# remain a replacement set instead of accumulating on each projection.
reprojected_state, _, _ = apply_decisions(
    record, projected_state, projected_eval, projected_site)
assert reprojected_state["warnings"] == projected_state["warnings"]

# Preservation mode must update only decision/provenance metadata around the
# historical Unreal snapshot and must leave unrelated manifest content intact.
with tempfile.TemporaryDirectory() as td:
    repo = Path(td)
    for directory in (
        "analysis/decision_packet", "docs", "truth_package",
        "web_viewer/data", "unreal_export/manifests",
    ):
        (repo / directory).mkdir(parents=True, exist_ok=True)
    (repo / "analysis/decision_packet/adopted_decisions.json").write_text(
        RECORD.read_text())
    for rel in ("docs/DESIGN_CANON.md", "docs/HUMAN_DECISION_BRIEF.md"):
        (repo / rel).write_text((ROOT / rel).read_text())
    temp_state = json.loads(json.dumps(design_state))
    temp_state["sources"] = {
        "canon": {"path": "docs/DESIGN_CANON.md", "sha256_12": "stale", "present": False},
        "decision_brief": {"path": "docs/HUMAN_DECISION_BRIEF.md", "sha256_12": "stale", "present": False},
    }
    temp_report = json.loads(json.dumps(evaluation))
    temp_site = json.loads(json.dumps(site_data))
    temp_site["audit"]["sources"] = {}
    (repo / "truth_package/design_state.current.json").write_text(
        json.dumps(temp_state))
    (repo / "truth_package/evaluation_report.current.json").write_text(
        json.dumps(temp_report))
    (repo / "web_viewer/data/site_data.js").write_text(
        "// generated\n// test fixture\nwindow.SITE_DATA = "
        + json.dumps(temp_site) + ";\n")
    historical_stats = {"stage": {"n_stage_features": 7}}
    (repo / "unreal_export/manifests/provenance.json").write_text(json.dumps({
        "warnings": ["legacy warning"],
        "warnings_source": "truth_package/design_state.current.json",
        "sources": {},
        "build_stats": historical_stats,
    }))

    sync_existing_outputs(repo)
    synced_state = json.loads(
        (repo / "truth_package/design_state.current.json").read_text())
    synced_report = json.loads(
        (repo / "truth_package/evaluation_report.current.json").read_text())
    synced_site = load_site_data_js(repo / "web_viewer/data/site_data.js")
    synced_provenance = json.loads(
        (repo / "unreal_export/manifests/provenance.json").read_text())
    assert synced_state["warnings"] == synced_report["warnings"]
    assert synced_state["warnings"] == synced_site["meta"]["warnings"]
    assert synced_state["warnings"] == synced_provenance["warnings"]
    assert synced_state["sources"] == synced_report["sources"]
    assert synced_state["sources"] == synced_site["audit"]["sources"]
    assert synced_provenance["build_stats"] == historical_stats
    assert synced_provenance["decision_projection"]["stage_geometry"] == (
        "historical_inherited_az_150_snapshot")
    assert synced_provenance["decision_projection"]["implements_stage_rule9_path_a"] is False

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
assert current_state["warnings"] == current_evaluation["warnings"]
assert current_state["warnings"] == current_site["meta"]["warnings"]
assert current_state["sources"] == current_evaluation["sources"]
assert current_state["sources"] == current_site["audit"]["sources"]
expected_source_hashes = {
    "adopted_decisions": ("analysis/decision_packet/adopted_decisions.json", "025227f9be8c"),
    "canon": ("docs/DESIGN_CANON.md", "1394df51718d"),
    "decision_brief": ("docs/HUMAN_DECISION_BRIEF.md", "ae46edfa15b2"),
}
for key, (path, expected_hash) in expected_source_hashes.items():
    entry = current_state["sources"][key]
    assert entry == {"path": path, "sha256_12": expected_hash, "present": True}
    assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest()[:12] == expected_hash
assert all(
    current_checks[check_id]["source"] == decision_authority
    for check_id in ("seating_scope", "stage_rule9", "ada_concepts")
)
assert current_checks["stage_rule9"]["status"] == "fail"
assert current_site["terrain"]["placeholder"] is False
assert _json_hash(current_site["terrain"]) == (
    "9a06085dba23ff06ada66f8fcbdf8e10aaeb9ead5ebac2423149ce7d7a26737b")
assert current_site["audit"]["decision_record"] == {
    "decided_on": "2026-07-18",
    "authority": "project_owner",
}
stage_layer = next(
    layer for layer in current_site["audit"]["layer_truth"]
    if layer["layer"] == "Stage deck")
assert "adopted" in stage_layer["source"].lower()
assert "provisional" in stage_layer["tier"]

viewer_html = (ROOT / "web_viewer/index.html").read_text()
assert "D.audit.adopted_decisions" in viewer_html
assert "D.audit.decision_record" in viewer_html
assert "adopted 2026-07-18" not in viewer_html
assert "human decision, not yet made" not in viewer_html
assert "Implementation remains pending" in viewer_html

current_provenance = json.loads(
    (ROOT / "unreal_export/manifests/provenance.json").read_text())
assert current_provenance["warnings"] == current_state["warnings"]
assert current_provenance["decision_projection"]["stage_geometry"] == (
    "historical_inherited_az_150_snapshot")
assert current_provenance["decision_projection"]["implements_stage_rule9_path_a"] is False
for key, (path, expected_hash) in expected_source_hashes.items():
    assert current_provenance["sources"][key] == {
        "path": path, "sha256_12": expected_hash, "exists": True,
    }

# Governing human-readable documents must record the owner selections without
# promoting pending implementation work into completed validation.
docs = {
    path: (ROOT / path).read_text()
    for path in [
        "docs/POST_EMISSION_DECISION_MEMO.md",
        "docs/HUMAN_DECISION_BRIEF.md",
        "analysis/stage_adoption/STAGE_RULE9_DECISION_TEMPLATE.md",
        "docs/ADA_CONCEPT_C_VS_D.md",
        "docs/DESIGN_CANON.md",
        "README.md",
    ]
}
combined = "\n".join(docs.values())
assert "Owner decision recorded 2026-07-18" in docs["docs/POST_EMISSION_DECISION_MEMO.md"]
assert "Chosen scope: **C**" in docs["docs/HUMAN_DECISION_BRIEF.md"]
assert "Fallback scope: **A**" in docs["docs/HUMAN_DECISION_BRIEF.md"]
assert "Chosen path: **A — audience-axis alignment**" in docs["analysis/stage_adoption/STAGE_RULE9_DECISION_TEMPLATE.md"]
assert "Owner adoption: **Concept C**" in docs["docs/ADA_CONCEPT_C_VS_D.md"]
assert "owner-selected Path A" in docs["docs/DESIGN_CANON.md"]
assert "Seating scope C adopted" in docs["README.md"]
for stale in ["Adoption decision **OPEN**", "human decision, not yet made", "no adoption path declared"]:
    assert stale not in combined, stale

# The Rule 9 governing passages must distinguish the settled human direction
# from the inherited, non-passing geometry-validation work.  In particular,
# do not reintroduce language that treats Path A itself as undecided.
canon = docs["docs/DESIGN_CANON.md"]
readme = docs["README.md"]
assert "Path A is the adopted owner direction" in canon
assert "Remaining work is to emit and validate the Path A geometry" in canon
assert "Until one path is adopted" not in canon
assert "stage refit open" not in canon
assert "Adopting a path now means:" not in canon
assert "Rule 9's owner direction is adopted" in readme
assert "legacy geometry-validation gate remains non-passing" in readme
assert "stage Rule 9 OPEN" not in readme
assert "unresolved decision flag** such as `RULE-9-OPEN`" not in readme

# Final-review regression boundary: every viewer-owned current-state label must
# present the adopted direction separately from the provisional inherited
# geometry, the governing ADA note must avoid a compliance claim, and the
# deterministic handoff manifest must exactly match its current inputs.
final_review_failures = []
viewer_lower = viewer_html.lower()
for stale in ("rule 9 open", "pending decision", "no adoption path declared"):
    if stale in viewer_lower:
        final_review_failures.append(f"viewer contains stale current-state copy: {stale!r}")
for required in (
    "Adopted direction — implementation pending",
    "Rule 9 Path A is adopted",
    "inherited az-150 geometry is provisional",
    "Path A emission and validation are pending",
):
    if required not in viewer_html:
        final_review_failures.append(f"viewer is missing adopted-stage copy: {required!r}")

ada_doc = docs["docs/ADA_CONCEPT_C_VS_D.md"]
if "ADA-compliant" in ada_doc:
    final_review_failures.append("governing ADA document contains prohibited 'ADA-compliant' claim")
required_ada_label = (
    "planning/concept-grade accessible route pending civil/code determination"
)
if required_ada_label not in ada_doc:
    final_review_failures.append(
        f"governing ADA document is missing label: {required_ada_label!r}")

manifest_check = subprocess.run(
    [sys.executable, "scripts/build_unreal_handoff_manifest.py", "--check"],
    cwd=ROOT,
    text=True,
    capture_output=True,
)
if manifest_check.returncode:
    final_review_failures.append(
        "handoff manifest drift check failed: "
        + (manifest_check.stdout + manifest_check.stderr).strip()
    )

assert not final_review_failures, "\n".join(final_review_failures)

print("PASS — authoritative decision artifact and validation boundary")
