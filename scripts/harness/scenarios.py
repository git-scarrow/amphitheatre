"""ScenarioLibrary: load and apply earthwork_scenarios.geojson borrow/fill circuits.

Each scenario is a named set of features with roles: borrow, fill, haul_corridor,
no_touch, evaluation_boundary. The library validates proposals against no-touch
rules and scenario-level constraints before applying any delta.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from shapely.geometry import shape

if TYPE_CHECKING:
    from .project import ProjectState
    from .clay import ClayDelta


class ScenarioLibrary:
    def __init__(self, state: "ProjectState"):
        self.state = state
        self._features: list[dict] = []
        self._geoms: dict[str, object] = {}  # name -> shapely geom
        self._by_scenario: dict[str, list[dict]] = {}

        scenarios_path = state.root / "earthwork_scenarios.geojson"
        if scenarios_path.exists():
            self.load(scenarios_path)

    def load(self, path: str | Path):
        with open(path) as fh:
            fc = json.load(fh)
        self._features = fc.get("features", [])
        self._geoms = {}
        self._by_scenario = {}
        for feat in self._features:
            pr = feat["properties"]
            name = pr.get("name", "")
            sid = pr.get("scenario_id", "")
            self._geoms[name] = shape(feat["geometry"])
            if sid not in self._by_scenario:
                self._by_scenario[sid] = []
            self._by_scenario[sid].append(feat)

    def all_geoms(self) -> dict[str, object]:
        """Return {name: shapely_geom} for all named features."""
        return dict(self._geoms)

    def scenario_geoms(self, scenario_id: str) -> dict[str, object]:
        """Return {name: shapely_geom} for all features in a scenario."""
        feats = self._by_scenario.get(scenario_id, [])
        return {f["properties"]["name"]: shape(f["geometry"]) for f in feats}

    def scenario_ids(self) -> list[str]:
        return sorted(self._by_scenario.keys())

    def feature_props(self, name: str) -> dict:
        for feat in self._features:
            if feat["properties"].get("name") == name:
                return feat["properties"]
        return {}

    def validate_proposal(self, proposal: dict, state: "ProjectState") -> dict:
        """Pre-validate a proposal dict before applying delta.
        Returns {valid: bool, warnings: list, errors: list}.
        """
        errors = []
        warnings = []

        actions = proposal.get("actions", [])
        for action in actions:
            op = list(action.keys())[0]
            params = action[op] if isinstance(action[op], dict) else action

            # Check polygon references exist
            poly_name = params.get("polygon") or params.get("geom")
            if poly_name and poly_name not in self._geoms:
                # May be a no-touch preserve action
                if op != "preserve":
                    warnings.append(
                        f"polygon '{poly_name}' not in earthwork_scenarios.geojson — "
                        f"will need to be added or defined inline"
                    )

            # Check no-touch violations
            no_touch = proposal.get("preserve", []) + state.cfg.get("no_touch", [])
            if poly_name in no_touch and op not in ("preserve",):
                errors.append(f"Action '{op}' on '{poly_name}' is in no-touch list")

            # Check depth limits
            if op == "cut_bench":
                max_cut = params.get("max_cut_ft", 2.0)
                if max_cut > 4.0:
                    warnings.append(f"cut_bench max_cut_ft={max_cut} may trigger retaining walls")
            if op == "fill_shelf":
                mf = params.get("max_fill_ft", 1.25)
                if mf > 3.0:
                    warnings.append(f"fill_shelf max_fill_ft={mf} > 3 ft — review slope stability")

        # Check earthwork balance (borrow + fill)
        # flatten_pad / grade_ceiling count as implicit borrow when target < terrain
        has_borrow = any(
            list(a.keys())[0] in ("cut_bench", "lower_patch", "flatten_pad",
                                  "grade_ceiling", "terrace_plane")
            for a in actions
        )
        has_fill = any(
            list(a.keys())[0] in ("fill_shelf", "raise_patch") for a in actions
        )
        if has_fill and not has_borrow:
            errors.append("Fill action found but no borrow/cut action — violates net-zero rule")
        if has_borrow and not has_fill and not proposal.get("borrow_only_ok", False):
            warnings.append("Cut-only action — excess material needs disposal route")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }

    def apply_proposal(self, delta: "ClayDelta", proposal: dict,
                        state: "ProjectState") -> list[str]:
        """Apply proposal actions to delta. Returns list of warnings."""
        from .clay import ClayDelta  # avoid circular
        actions = proposal.get("actions", [])
        all_geoms = self.all_geoms()
        warnings = []

        for action in actions:
            op = list(action.keys())[0]
            params = action.get(op, action)
            if not isinstance(params, dict):
                params = action
            delta.apply_scenario_action(state, {"op": op, **params, op: params}, all_geoms)

        return warnings
