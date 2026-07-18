# Authoritative Design Decisions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Record the owner's seating C/A-fallback, Rule 9 Path A, and ADA Concept C selections as authoritative repository state while keeping unpropagated geometry and engineering work explicitly incomplete.

**Architecture:** Add one machine-readable decision artifact and a focused Python projection module that validates it and applies it to the generated truth/viewer structures. The full truth-package generator will call that module on future builds; a preservation-mode synchronizer will update the currently committed generated artifacts without rebuilding the intentionally absent source TIFFs or changing the existing real terrain payload.

**Tech Stack:** Python 3 standard library, JSON, plain-script repository tests, Markdown, static JavaScript/HTML.

## Global Constraints

- `analysis/decision_packet/adopted_decisions.json` is the single machine-readable authority.
- All three decisions use `decision_status: adopted`.
- Decision status and implementation status remain independent.
- Do not invent an owner rationale; use `owner_selection_no_additional_rationale_recorded`.
- Do not switch seating geometry, relocate the stage, select an apron/typology, or assert ADA compliance.
- The current inherited azimuth-150 stage remains provisional until Path A geometry is emitted and validated.
- Preserve the existing non-placeholder terrain payload byte-for-byte at the decoded JSON value level.
- Do not run the full truth-package build in this checkout while the ignored source TIFFs are absent.
- Preserve unrelated untracked Proxmox database files and `scripts/unreal/open_and_frame_civicbowl.py`.

---

### Task 1: Authoritative decision artifact and validation boundary

**Files:**
- Create: `analysis/decision_packet/adopted_decisions.json`
- Create: `scripts/authoritative_decisions.py`
- Create: `scripts/test_authoritative_decisions.py`

**Interfaces:**
- Consumes: a filesystem path to `adopted_decisions.json`.
- Produces: `load_decision_record(path: Path) -> dict` and `index_decisions(record: dict) -> dict[str, dict]`.

- [ ] **Step 1: Write the failing artifact-validation test**

Create `scripts/test_authoritative_decisions.py` with the first test block:

```python
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
```

- [ ] **Step 2: Run the test to verify RED**

Run: `python3 scripts/test_authoritative_decisions.py`

Expected: FAIL because `authoritative_decisions` does not exist.

- [ ] **Step 3: Add the authoritative JSON record**

Create `analysis/decision_packet/adopted_decisions.json`:

```json
{
  "schema": "petoskey-pit/adopted-decisions/1",
  "decided_on": "2026-07-18",
  "authority": "project_owner",
  "decisions": [
    {
      "id": "seating_scope",
      "selected_option": "C",
      "selected_label": "ambitious_shaped_bowl (seating scope)",
      "fallback_option": "A",
      "fallback_label": "Scenario E baseline",
      "decision_status": "adopted",
      "implementation_status": "pending_package_propagation",
      "validated_metrics": {
        "band_a_seats": 1505,
        "nominal_seats": 1516,
        "delta_seats_vs_baseline": 262,
        "incremental_earthwork_cy": 47.3
      },
      "rationale": "owner_selection_no_additional_rationale_recorded",
      "required_follow_ups": [
        "point the in-situ package at the emitted ambitious geometry",
        "rerun the in-situ package audit"
      ],
      "sources": [
        "analysis/decision_packet/decision_table.csv",
        "docs/HUMAN_DECISION_BRIEF.md"
      ]
    },
    {
      "id": "stage_rule9",
      "selected_option": "A",
      "selected_label": "audience-axis alignment",
      "decision_status": "adopted",
      "implementation_status": "pending_geometry_and_validation",
      "target_axis_az_deg": 124.0,
      "target_audience_facing_az_deg": 304.0,
      "rationale": "owner_selection_no_additional_rationale_recorded",
      "required_follow_ups": [
        "select and emit the exact stage footprint",
        "select the stage-front geometry and typology",
        "update the fan declaration",
        "rerun Rule 9 geometry and package validation"
      ],
      "sources": [
        "docs/DESIGN_CANON.md",
        "analysis/stage_refit/STAGE_REFIT_SWEEP.md",
        "analysis/stage_adoption/STAGE_RULE9_DECISION_TEMPLATE.md"
      ]
    },
    {
      "id": "ada_concept",
      "selected_option": "C",
      "selected_label": "naturalistic promenade",
      "decision_status": "adopted",
      "implementation_status": "planning_grade_pending_civil_detailing",
      "seats_displaced": 0,
      "rationale": "owner_selection_no_additional_rationale_recorded",
      "required_follow_ups": [
        "resolve corridor benching sections",
        "complete civil and code detailing"
      ],
      "sources": [
        "analysis/ada_rebuild/ada_validation.json",
        "docs/ADA_CONCEPT_C_VS_D.md"
      ]
    }
  ]
}
```

- [ ] **Step 4: Implement strict loading and indexing**

Create `scripts/authoritative_decisions.py`:

```python
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
```

- [ ] **Step 5: Run the test to verify GREEN**

Run: `python3 scripts/test_authoritative_decisions.py`

Expected: `PASS — authoritative decision artifact and validation boundary`.

- [ ] **Step 6: Commit Task 1**

```bash
git add analysis/decision_packet/adopted_decisions.json scripts/authoritative_decisions.py scripts/test_authoritative_decisions.py
git commit -m "feat: record authoritative design decisions"
```

---

### Task 2: Project decisions into truth and viewer data without terrain rebuild

**Files:**
- Modify: `scripts/authoritative_decisions.py`
- Modify: `scripts/test_authoritative_decisions.py`
- Modify: `scripts/build_truth_package.py`
- Modify: `truth_package/design_state.current.json`
- Modify: `truth_package/evaluation_report.current.json`
- Modify: `web_viewer/data/site_data.js`

**Interfaces:**
- Consumes: validated record plus existing `design_state`, `evaluation_report`, and `site_data` dictionaries.
- Produces: `apply_decisions(record, design_state, evaluation_report, site_data) -> tuple[dict, dict, dict]` and `sync_existing_outputs(repo: Path) -> None`.

- [ ] **Step 1: Extend the test with a failing projection contract**

Append to `scripts/test_authoritative_decisions.py`:

```python
import base64
import hashlib

from authoritative_decisions import apply_decisions

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
```

- [ ] **Step 2: Run the test to verify RED**

Run: `python3 scripts/test_authoritative_decisions.py`

Expected: FAIL because `apply_decisions` does not exist.

- [ ] **Step 3: Implement the projection functions**

Add to `scripts/authoritative_decisions.py`:

```python
import copy


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
    decisions = index_decisions(record)
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
```

- [ ] **Step 4: Integrate the same projection into the full generator**

In `scripts/build_truth_package.py`:

```python
from authoritative_decisions import apply_decisions, load_decision_record
```

Add to `SRC`:

```python
"adopted_decisions": "analysis/decision_packet/adopted_decisions.json",
```

After `site_data` is assembled and before any output is written, replace direct writes with:

```python
decision_record = load_decision_record(Path(p(SRC["adopted_decisions"])))
design_state, evaluation_report, site_data = apply_decisions(
    decision_record, design_state, evaluation_report, site_data)
```

Move the three truth JSON writes below that call. Add `from pathlib import Path` at the import block. This keeps future full builds and preservation-mode synchronization on the same projection logic.

- [ ] **Step 5: Add preservation-mode synchronization for current outputs**

Add the complete preservation-mode implementation to `scripts/authoritative_decisions.py`:

```python
import hashlib

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
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args()
    if not args.sync_existing:
        parser.error("use --sync-existing")
    sync_existing_outputs(args.repo)
```

- [ ] **Step 6: Run the focused test to verify GREEN**

Run: `python3 scripts/test_authoritative_decisions.py`

Expected: PASS, including the terrain-hash assertion.

- [ ] **Step 7: Synchronize existing generated outputs without rebuilding terrain**

Run: `python3 scripts/authoritative_decisions.py --sync-existing`

Expected: prints the paths updated and `terrain payload preserved`.

- [ ] **Step 8: Verify the committed site terrain remains non-placeholder**

Run:

```bash
python3 -c 'import json, pathlib; p=pathlib.Path("web_viewer/data/site_data.js"); s=p.read_text(); d=json.loads(s.split("window.SITE_DATA = ",1)[1][:-2]); assert d["terrain"]["placeholder"] is False; print("PASS — real terrain preserved")'
```

Expected: `PASS — real terrain preserved`.

- [ ] **Step 9: Commit Task 2**

```bash
git add scripts/authoritative_decisions.py scripts/test_authoritative_decisions.py scripts/build_truth_package.py truth_package/design_state.current.json truth_package/evaluation_report.current.json web_viewer/data/site_data.js
git commit -m "feat: project adopted decisions into truth data"
```

---

### Task 3: Render adopted decisions in the static viewer

**Files:**
- Modify: `web_viewer/index.html:338-349`
- Modify: `scripts/test_authoritative_decisions.py`

**Interfaces:**
- Consumes: `window.SITE_DATA.audit.adopted_decisions`.
- Produces: an owner-decision summary that names adopted C/A/C choices and implementation caveats.

- [ ] **Step 1: Add a failing static-viewer contract test**

Append to `scripts/test_authoritative_decisions.py`:

```python
viewer_html = (ROOT / "web_viewer/index.html").read_text()
assert "D.audit.adopted_decisions" in viewer_html
assert "human decision, not yet made" not in viewer_html
assert "Implementation remains pending" in viewer_html
```

- [ ] **Step 2: Run the test to verify RED**

Run: `python3 scripts/test_authoritative_decisions.py`

Expected: FAIL because the viewer still reads `D.audit.pending` and says the decision is not made.

- [ ] **Step 3: Replace the pending-decision renderer**

Replace `web_viewer/index.html` lines 338–349 with:

```javascript
  const P = document.getElementById("pending");
  const adopted = D.audit.adopted_decisions ?? [];
  if (adopted.length) {
    const byId = Object.fromEntries(adopted.map(d => [d.id, d]));
    const seating = byId.seating_scope, stage = byId.stage_rule9, ada = byId.ada_concept;
    P.innerHTML = `<b>Owner decisions — adopted 2026-07-18</b>
      <table><tr><th>decision</th><th>adopted direction</th><th>implementation</th></tr>
        <tr><td>Seating</td><td>${seating.selected_option} — ${seating.selected_label}; fallback ${seating.fallback_option}</td><td>${seating.implementation_status}</td></tr>
        <tr><td>Stage · Rule 9</td><td>Path ${stage.selected_option} — ${stage.selected_label}</td><td>${stage.implementation_status}</td></tr>
        <tr><td>Accessible route</td><td>${ada.selected_option} — ${ada.selected_label}</td><td>${ada.implementation_status}</td></tr>
      </table>
      <div style="margin-top:6px;color:#8e887a;font-size:11.5px"><b>Implementation remains pending:</b> the current model retains baseline seating and the inherited provisional stage until package propagation and validation are complete.</div>`;
  }
```

- [ ] **Step 4: Run the focused test to verify GREEN**

Run: `python3 scripts/test_authoritative_decisions.py`

Expected: PASS.

- [ ] **Step 5: Commit Task 3**

```bash
git add web_viewer/index.html scripts/test_authoritative_decisions.py
git commit -m "feat: show adopted decisions in the viewer"
```

---

### Task 4: Synchronize governing documents and guard against stale decision language

**Files:**
- Modify: `docs/POST_EMISSION_DECISION_MEMO.md`
- Modify: `docs/HUMAN_DECISION_BRIEF.md`
- Modify: `analysis/stage_adoption/STAGE_RULE9_DECISION_TEMPLATE.md`
- Modify: `docs/ADA_CONCEPT_C_VS_D.md`
- Modify: `docs/DESIGN_CANON.md`
- Modify: `README.md`
- Modify: `scripts/test_authoritative_decisions.py`

**Interfaces:**
- Consumes: the authoritative JSON decision IDs and status language.
- Produces: governing human-readable records that distinguish owner adoption from implementation completion.

- [ ] **Step 1: Add failing documentation assertions**

Append to `scripts/test_authoritative_decisions.py`:

```python
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
```

- [ ] **Step 2: Run the test to verify RED**

Run: `python3 scripts/test_authoritative_decisions.py`

Expected: FAIL on the first missing adopted-decision phrase.

- [ ] **Step 3: Update the controlling memo and seating brief**

In `docs/POST_EMISSION_DECISION_MEMO.md`, replace “The two live decisions” and its Decision 1/2 text with:

```markdown
## Owner decisions and implementation follow-ups

**Owner decision recorded 2026-07-18.** The human selections are settled; geometry-dependent implementation and validation remain separate.

1. **Seating scope C — ambitious shaped bowl is adopted.** Quote 1,505 Band-A / 1,516 nominal, +262 seats and 47.3 CY versus the validated control. **A — Scenario E baseline remains the fallback.** The current in-situ package still points at A until package propagation and re-audit are complete.
2. **Rule 9 Path A — audience-axis alignment is adopted as the stage direction.** Target approximately az 124° / audience facing 304°. The exact footprint, apron, typology, fan declaration, and stage-derived artifacts remain pending; the inherited az-150 stage stays provisional and Rule 9's geometry-validation gate remains non-passing.
3. **ADA Concept C — naturalistic promenade is adopted at planning grade.** It preserves seating and remains pending civil/code detailing. This adoption does not assert ADA compliance.

The machine-readable authority is `analysis/decision_packet/adopted_decisions.json`. No downstream artifact may promote `decision_status: adopted` into completed implementation without the required re-emission and validation.
```

In `docs/HUMAN_DECISION_BRIEF.md`, replace the fill-in block with:

```markdown
## Decision record

**Owner decision recorded 2026-07-18.**

- **Chosen scope: C** — ambitious shaped bowl, 1,505 Band-A / 1,516 nominal.
- **Fallback scope: A** — Scenario E baseline.
- **Decision status:** adopted.
- **Implementation status:** pending package propagation and package re-audit.
- **Rationale:** owner selection; no additional rationale recorded.
```

- [ ] **Step 4: Convert the Rule 9 template into an adopted-direction record**

Rename its title from template to record and replace the fill-in block with:

```markdown
## Decision record

**Owner decision recorded 2026-07-18.**

- **Chosen path: A — audience-axis alignment.**
- **Target axis / audience facing:** approximately az 124° / 304°.
- **Exact footprint:** not selected by this direction-level decision; pending emission study.
- **Apron:** not selected by this direction-level decision.
- **Typology / roof:** not selected by this direction-level decision.
- **Decision status:** adopted.
- **Implementation status:** pending geometry emission and validation; the inherited az-150 stage remains provisional.
- **Rationale:** owner selection; no additional rationale recorded.
```

Keep the required follow-up checklist and state that Rule 9’s human direction is settled but its geometry-dependent closure gate remains non-passing.

- [ ] **Step 5: Record ADA adoption and synchronize canon/README language**

Add beneath the recommendation in `docs/ADA_CONCEPT_C_VS_D.md`:

```markdown
### Owner adoption

**Owner adoption: Concept C — naturalistic promenade, recorded 2026-07-18.**
Decision status is adopted. Implementation remains planning-grade pending civil/code detailing; this record does not assert ADA compliance.
```

Add this status note immediately under the Rule 9 heading in `docs/DESIGN_CANON.md`, replacing its former OPEN-status note:

```markdown
> **Owner direction recorded 2026-07-18:** owner-selected Path A — audience-axis alignment, target approximately az 124° / audience facing 304°. The human direction is adopted; exact footprint, apron, typology, fan declaration, re-emission, and validation remain incomplete. The inherited az-150 stage is still PROVISIONAL and does not represent Path A. Rule 9's geometry-validation gate therefore remains non-passing. Authority: `analysis/decision_packet/adopted_decisions.json`.
```

Replace the current README intervention-tier and stage rows with:

```markdown
| Intervention tiers — emission validation (2026-06-11) | **Seating scope C adopted**: ambitious shaped bowl, 1,505 Band-A / 1,516 nominal, +262 seats / 47.3 CY. **A remains the fallback.** Package propagation and re-audit are pending. |
| Scenario E — stage configuration | **Rule 9 Path A adopted as owner direction** — audience-axis alignment, approximately az 124°. Current inherited az-150 stage remains PROVISIONAL pending geometry emission and validation. |
| Accessible route | **Concept C adopted at planning grade** — naturalistic promenade; civil/code detailing remains pending and no ADA-compliance claim is made. |
```

Replace “The two live decisions” with:

```markdown
**The three owner selections** are recorded in `analysis/decision_packet/adopted_decisions.json`: seating C with A fallback, Rule 9 Path A, and ADA Concept C. Adoption settles direction; the status table above names the implementation work still pending.
```

- [ ] **Step 6: Run the focused test to verify GREEN**

Run: `python3 scripts/test_authoritative_decisions.py`

Expected: PASS.

- [ ] **Step 7: Run repository verification**

Run:

```bash
python3 scripts/test_authoritative_decisions.py
python3 scripts/audit_in_situ_package.py
python3 scripts/test_cross_aisle_provenance.py
python3 scripts/test_speckle_payload.py
python3 scripts/test_speckle_phase2.py
git diff --check
```

Expected: every command exits 0. The audit may report warnings for implementation work still pending, but no failures.

- [ ] **Step 8: Verify scope and unrelated files**

Run: `git status --short`

Expected: only planned decision files plus the user’s pre-existing untracked Proxmox database files and `scripts/unreal/open_and_frame_civicbowl.py`; no TIFF or geometry files modified.

- [ ] **Step 9: Commit Task 4**

```bash
git add docs/POST_EMISSION_DECISION_MEMO.md docs/HUMAN_DECISION_BRIEF.md analysis/stage_adoption/STAGE_RULE9_DECISION_TEMPLATE.md docs/ADA_CONCEPT_C_VS_D.md docs/DESIGN_CANON.md README.md scripts/test_authoritative_decisions.py
git commit -m "docs: adopt owner-selected design directions"
```

---

## Final Acceptance

- The authoritative JSON records seating C with fallback A, Rule 9 Path A, and ADA Concept C.
- Every decision is `adopted`; every incomplete implementation remains explicit.
- The truth package and static viewer show adopted directions rather than pending human choices.
- Rule 9 remains non-passing at the geometry/validation level.
- The real terrain payload remains non-placeholder and unchanged.
- No geometry, TIFF, Speckle, Unreal, or hosted-site artifact is published or regenerated.
