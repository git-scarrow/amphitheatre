"""SightlineEngine: per-row C-value computation against proposed terrain."""
from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from .project import ProjectState
    from .clay import ClayDelta


class SightlineEngine:
    def __init__(self, state: "ProjectState"):
        self.state = state
        p = state.params()
        self.ax_az = p["AX_AZ"]
        self.fan_half = p["FAN_HALF"]
        self.R_inner = p["R_INNER"]
        self.R_outer = p["R_OUTER"]
        self.tread_spacing = p["TREAD"]
        self.focus_elev = p["FOCUS_ELEV"]
        self.eye_ht = p["EYE_HT"]
        self.stage_r = p["STAGE_R"]
        self.c_target_ft = p["C_TARGET_FT"]
        self.c_target_mm = p["C_TARGET_FT"] * 304.8
        self.nrows = p["NROWS"]
        self.formal_stop_row = state.cfg.get("capacity_bands", {}).get("formal_stop_row", 18)
        self.FX, self.FY = state.arc_centre()

        # Load row radii AND authoritative C-values from composition_table.
        # The composition_table accounts for cross-angle effects that the
        # arc-median harness model cannot capture; its C-values are used for
        # band classification in the terrace zone (rows > formal_stop_row).
        ctbl_rel = state.cfg.get("design", {}).get("composition_table")
        self._row_radii = None
        self._comp_c_mm: dict[int, float | None] = {}   # row_num → authoritative C
        if ctbl_rel:
            ctbl_path = state.root / ctbl_rel
            if ctbl_path.exists():
                seen_r: dict[int, float] = {}
                seen_c: dict[int, float | None] = {}
                for row in csv.DictReader(open(ctbl_path)):
                    if row.get("kind") == "seating":
                        rn = int(row["row"])
                        if rn not in seen_r:
                            seen_r[rn] = float(row["axis_radius_ft"])
                        c_raw = row.get("C_mm", "").strip()
                        if rn not in seen_c:
                            seen_c[rn] = float(c_raw) if c_raw else None
                if seen_r:
                    sorted_rows = sorted(seen_r)
                    self._row_radii = [seen_r[k] for k in sorted_rows]
                    self._comp_c_mm = {k: seen_c.get(k) for k in sorted_rows}
                    self.nrows = len(self._row_radii)

    def _cval(self, D: float, E: float, Dp: float, Ep: float) -> float:
        return E * (Dp / D) - Ep

    def compute_rows(self, proposed_dem: np.ndarray) -> list[dict]:
        """Recompute per-row sightlines against the proposed DEM surface."""
        if self._row_radii is not None:
            radii = self._row_radii
        else:
            radii = [self.R_inner + i * self.tread_spacing for i in range(self.nrows)]
        rows = []
        for i, R in enumerate(radii):
            terr = self.state.sample_arc_median(proposed_dem, R)
            prev = rows[i - 1] if i > 0 else None

            if i == 0:
                tread = max(terr, self.focus_elev + 0.5)
            else:
                Dp = prev["R"] - self.stage_r
                D = R - self.stage_r
                Ep = (prev["tread_elev"] + self.eye_ht) - self.focus_elev
                tread_req = self.focus_elev + (self.c_target_ft + Ep) * (D / Dp) - self.eye_ht
                tread = math.ceil(max(tread_req, terr) * 100) / 100

            eye = tread + self.eye_ht
            E = eye - self.focus_elev
            cutfill = round(tread - terr, 2)
            dist_to_stage = round(R - self.stage_r, 1)

            if i == 0:
                C = None
            else:
                Dp = prev["R"] - self.stage_r
                D = R - self.stage_r
                Ep_prev = prev["E"]
                C = self._cval(D, E, Dp, Ep_prev)

            row_num = i + 1
            in_formal_zone = row_num <= self.formal_stop_row

            # Authoritative C from composition_table (accounts for cross-angle).
            # For the formal zone the harness-computed C is used for pass/fail;
            # for the terrace zone the composition C is used for band classification.
            comp_c = self._comp_c_mm.get(row_num)

            row = {
                "row": row_num,
                "R": R,
                "dist_to_stage_ft": dist_to_stage,
                "terrain_elev": round(float(terr), 2) if np.isfinite(terr) else None,
                "tread_elev": round(tread, 2),
                "cut_fill_ft": cutfill,
                "eye_elev": round(eye, 2),
                "E": round(E, 3),
                "C_value_ft": round(C, 4) if C is not None else None,
                "C_value_mm": round(C * 304.8) if C is not None else None,
                "composition_c_mm": comp_c,
                # meets_C enforced only in formal zone
                "meets_C": C is None or C >= self.c_target_ft - 1e-6,
                "in_formal_zone": in_formal_zone,
                "needs_fill": cutfill > 0.02,
            }
            rows.append(row)

        return rows

    def summary(self, rows: list[dict]) -> dict:
        # Pass/fail enforced only within the formal zone (rows 1..formal_stop_row)
        formal = [r for r in rows if r.get("in_formal_zone", True)]
        eligible = [r for r in formal if r["C_value_mm"] is not None]
        if not eligible:
            return {"pass_count": 1, "fail_count": 0, "all_pass": True,
                    "min_C_mm": None, "max_fill_ft": 0.0, "total_fill_cy": 0.0}

        passing = [r for r in eligible if r["meets_C"]]
        min_C_formal = min(r["C_value_mm"] for r in eligible)
        # Also report global min for reference
        all_with_C = [r for r in rows if r["C_value_mm"] is not None]
        min_C_all = min(r["C_value_mm"] for r in all_with_C) if all_with_C else min_C_formal
        max_fill = max(r["cut_fill_ft"] for r in rows)
        fill_cy = sum(
            max(0.0, r["cut_fill_ft"]) * r["R"] * math.radians(2 * self.fan_half) * self.tread_spacing
            for r in rows
        ) / 27.0

        return {
            "pass_count": len(passing) + 1,  # row 1 always passes
            "fail_count": len(eligible) - len(passing),
            "all_pass": len(passing) == len(eligible),
            "min_C_mm": int(min_C_formal),        # formal zone minimum
            "min_C_mm_all": int(min_C_all),       # full envelope minimum
            "formal_stop_row": self.formal_stop_row,
            "max_fill_ft": round(max_fill, 2),
            "total_fill_cy": round(fill_cy, 1),
        }

    def delta_vs_baseline(self, rows: list[dict]) -> dict:
        """Compare against baseline design_open_low sightlines."""
        baseline_rows = self.state.rows_tbl
        diffs = []
        for b, p in zip(baseline_rows, rows):
            if b.get("C") is None or p["C_value_ft"] is None:
                continue
            diffs.append(p["C_value_ft"] - (b.get("C") or 0.0))
        return {
            "mean_C_change_mm": round(float(np.mean(diffs)) * 304.8, 1) if diffs else 0.0,
            "min_C_change_mm": round(float(np.min(diffs)) * 304.8, 1) if diffs else 0.0,
        }
