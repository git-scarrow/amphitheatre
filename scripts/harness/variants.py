"""VariantManager: save/load variants with full report cards.

Variant directory structure:
  variants/
    V0001/
      proposal.yaml        LLM-generated proposal
      delta.tif            ClayDelta raster
      proposed_dem.tif     P = E0 + delta
      metrics.json         All evaluator outputs
      score.json           Scoring breakdown
      report.md            Human-readable report card
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import yaml

if TYPE_CHECKING:
    from .project import ProjectState
    from .clay import ClayDelta


SCORE_COLOR = {
    "keep_for_refinement": "✓",
    "conditional": "~",
    "revise": "↻",
    "reject": "✗",
}


class VariantManager:
    def __init__(self, root: str | Path = "variants"):
        self.root = Path(root)
        self.root.mkdir(exist_ok=True)

    def next_id(self) -> str:
        existing = [d.name for d in self.root.iterdir()
                    if d.is_dir() and d.name.startswith("V")]
        nums = []
        for name in existing:
            try:
                nums.append(int(name[1:]))
            except ValueError:
                pass
        return f"V{(max(nums, default=0) + 1):04d}"

    def save(self, variant_id: str,
             delta: "ClayDelta",
             metrics: dict,
             score: dict,
             proposal: dict,
             state: "ProjectState") -> Path:
        vdir = self.root / variant_id
        vdir.mkdir(exist_ok=True)

        # proposal.yaml
        with open(vdir / "proposal.yaml", "w") as fh:
            yaml.dump(proposal, fh, default_flow_style=False)

        # delta.tif
        delta.save(vdir / "delta.tif", state)

        # proposed_dem.tif
        import rasterio
        Zp = delta.proposed(state)
        prof = rasterio.open(state.root / state.cfg["terrain"]["dem"]).profile.copy()
        prof.update(dtype="float32", count=1, nodata=-9999.0, compress="lzw")
        with rasterio.open(vdir / "proposed_dem.tif", "w", **prof) as dst:
            out = np.where(np.isfinite(Zp), Zp, -9999.0).astype("float32")
            dst.write(out, 1)

        # metrics.json (strip large arrays before serialising)
        metrics_out = _strip_arrays(metrics)
        with open(vdir / "metrics.json", "w") as fh:
            json.dump(metrics_out, fh, indent=2, default=str)

        # score.json
        with open(vdir / "score.json", "w") as fh:
            json.dump(score, fh, indent=2)

        # report.md
        with open(vdir / "report.md", "w") as fh:
            fh.write(self._build_report(variant_id, proposal, metrics, score))

        # render images
        try:
            from .render import render_variant
            render_variant(state, delta, vdir, metrics=metrics_out, score=score)
        except Exception as exc:
            print(f"  [render] warning: {exc}")

        return vdir

    def load(self, variant_id: str) -> dict:
        vdir = self.root / variant_id
        if not vdir.exists():
            raise FileNotFoundError(f"Variant {variant_id} not found at {vdir}")
        metrics = json.load(open(vdir / "metrics.json"))
        score = json.load(open(vdir / "score.json"))
        proposal = yaml.safe_load(open(vdir / "proposal.yaml"))
        return {"id": variant_id, "metrics": metrics, "score": score, "proposal": proposal}

    def list_variants(self) -> list[str]:
        return sorted(d.name for d in self.root.iterdir()
                      if d.is_dir() and d.name.startswith("V"))

    def comparison_table(self, ids: list[str] | None = None) -> str:
        if ids is None:
            ids = self.list_variants()
        rows = []
        for vid in ids:
            try:
                v = self.load(vid)
            except Exception:
                continue
            m = v["metrics"]
            s = v["score"]
            ew = m.get("earthwork", {})
            sl = m.get("sightlines", {})
            dr = m.get("drainage", {})
            sun = m.get("solar", {})
            verdict = _verdict(s)
            rows.append({
                "id": vid,
                "total": s.get("total", 0),
                "verdict": SCORE_COLOR.get(verdict, "?") + " " + verdict,
                "cut_cy": ew.get("cut_cy", 0),
                "fill_cy": ew.get("fill_cy", 0),
                "gross_cy": ew.get("gross_cy", 0),
                "haul_ft": ew.get("avg_haul_ft", 0),
                "wall": "Y" if ew.get("wall_trigger") else "N",
                "sightlines": f"{sl.get('pass_count', 0)}/{sl.get('pass_count', 0) + sl.get('fail_count', 0)}",
                "drainage": dr.get("delta", "?"),
                "sunset": sun.get("upper_crescent_score", 0),
                "intent": v["proposal"].get("intent", "")[:40],
            })

        if not rows:
            return "No variants found."

        header = (
            f"{'ID':<8} {'Score':>6} {'Verdict':<20} "
            f"{'Cut':>6} {'Fill':>6} {'Gross':>6} {'Haul':>6} "
            f"{'Wall':>4} {'Sightlines':>10} {'Drain':>8} {'Sunset':>6}\n"
        )
        sep = "-" * len(header.rstrip()) + "\n"
        lines = [header, sep]
        for r in sorted(rows, key=lambda x: -x["total"]):
            lines.append(
                f"{r['id']:<8} {r['total']:>6.1f} {r['verdict']:<20} "
                f"{r['cut_cy']:>6.0f} {r['fill_cy']:>6.0f} {r['gross_cy']:>6.0f} "
                f"{r['haul_ft']:>6.0f} {r['wall']:>4} {r['sightlines']:>10} "
                f"{r['drainage']:>8} {r['sunset']:>6.2f}\n"
            )
        return "".join(lines)

    def _build_report(self, vid: str, proposal: dict, metrics: dict, score: dict) -> str:
        ew = metrics.get("earthwork", {})
        sl = metrics.get("sightlines", {})
        dr = metrics.get("drainage", {})
        ada = metrics.get("ada", {})
        sun = metrics.get("solar", {})
        aes = metrics.get("aesthetic", {})
        cap = metrics.get("capacity", {})
        yb = ew.get("yield_balance", {})
        verdict = _verdict(score)
        vcolor = SCORE_COLOR.get(verdict, "?")

        lines = [
            f"# Variant {vid} — {proposal.get('id', vid)}",
            f"",
            f"**Score**: {score.get('total', 0):.1f}/100 {vcolor} *{verdict}*  ",
            f"**Intent**: {proposal.get('intent', 'unspecified')}  ",
            f"**Family**: {proposal.get('family', 'unspecified')}  ",
            f"**Bowl axis**: {metrics.get('bowl_axis_az', '—')}°",
            f"",
            "## Mass balance",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Cut | {ew.get('cut_cy', 0):.0f} CY |",
            f"| Fill | {ew.get('fill_cy', 0):.0f} CY |",
            f"| Net | {ew.get('net_cy', 0):+.0f} CY |",
            f"| Gross moved | {ew.get('gross_cy', 0):.0f} CY |",
            f"| Avg haul | {ew.get('avg_haul_ft', 0):.0f} ft |",
            f"| Haul effort | {ew.get('haul_effort_cy_ft', 0):.0f} CY-ft |",
            f"| Max cut | {ew.get('max_cut_ft', 0):.2f} ft |",
            f"| Max fill | {ew.get('max_fill_ft', 0):.2f} ft |",
            f"| LOD | {ew.get('lod_ac', 0):.3f} ac |",
            f"",
            "### Yield cases",
            "| Case | Yield | Balanced | Shortfall |",
            "|------|-------|----------|-----------|",
        ]
        for case, data in yb.items():
            ok = "✓" if data.get("balanced") else "✗"
            lines.append(f"| {case} | {data.get('yield_factor', '?')} | {ok} | "
                         f"{data.get('shortfall_cy', 0):.0f} CY |")

        # Topsoil and shrink/swell
        ts = ew.get("topsoil", {})
        ss = ew.get("shrink_swell", {})
        if ts:
            lines += [
                "",
                "### Topsoil stripping (separate from structural earthwork)",
                f"| Depth | {ts.get('topsoil_depth_ft', 0.5):.1f} ft |",
                f"| LOD area | {ts.get('topsoil_lod_sqft', 0):,} ft² |",
                f"| Volume | {ts.get('topsoil_vol_cy', 0):.0f} CY |",
                f"| Note | {ts.get('topsoil_note', '')} |",
            ]
        if ss:
            lines += [
                "",
                "### Shrink/swell correction",
                f"| K factor | {ss.get('shrink_factor_K', 0.95):.2f} |",
                f"| Usable compacted fill | {ss.get('usable_compacted_fill_cy', 0):.0f} CY |",
                f"| Fill demand | {ss.get('fill_demand_cy', 0):.0f} CY |",
                f"| Shortfall | {ss.get('shortfall_cy', 0):.0f} CY |",
                f"| Balanced | {'✓' if ss.get('balanced') else '✗'} |",
            ]

        lines += [
            "",
            "## Constructability",
            f"- Max delta slope: {ew.get('max_delta_slope_pct', 0):.0f}%",
            f"- Terrain slope improved: {'yes' if ew.get('slope_improved') else 'no'} "
            f"({ew.get('max_slope_before_pct', 0):.0f}% → {ew.get('max_slope_after_pct', 0):.0f}%)",
            f"- Retaining wall trigger: {'**YES**' if ew.get('wall_trigger') else 'no'}",
            "",
            "## Sightlines",
            f"- Pass: {sl.get('pass_count', 0)}/{sl.get('pass_count', 0) + sl.get('fail_count', 0)} rows",
            f"- All pass: {'✓' if sl.get('all_pass') else '✗'}",
            f"- Min C: {sl.get('min_C_mm', '—')} mm (target 90)",
            f"- Fill for sightlines: {sl.get('total_fill_cy', 0):.1f} CY",
            "",
            "## ADA",
            f"- Max running slope: {ada.get('max_running_slope_pct', 0):.1f}% (target ≤8.33%)",
            f"- All running slopes ok: {'✓' if ada.get('all_running_ok') else '✗'}",
            f"- Change vs baseline: {ada.get('delta', '—')}",
            "",
            "## Drainage",
            f"- 100-yr storage change: {dr.get('storage_100yr_change_pct', 0):+.1f}%",
            f"- Freeboard: {dr.get('event_floor_freeboard_ft', 0):.2f} ft (target ≥1.0)",
            f"- Cell function preserved: {'✓' if dr.get('cell_function_preserved') else '✗'}",
            f"- Change vs baseline: {dr.get('delta', '—')}",
            "",
            "## Solar / Bay view",
            f"- Upper crescent sunset score: {sun.get('upper_crescent_score', 0):.2f}",
            f"- Glare penalty: {sun.get('glare_penalty', '—')}",
            f"- Bay view score: {aes.get('bay_view_score', 0):.2f}",
            "",
            "## Aesthetic",
            f"- Landform fit: {aes.get('landform_fit', 0):.2f}",
            f"- Row-arc contour match: {aes.get('row_arc_contour_match', 0):.2f}",
            f"- Stage presence: {aes.get('stage_presence', 0):.2f}",
            f"- Open-air score: {aes.get('open_air_score', 0):.2f}",
            f"- Overbuild penalty: {aes.get('overbuild_penalty', 0):.2f}",
            "",
            "## Capacity",
            f"- Formal (C≥90mm): {cap.get('formal_seats', cap.get('generous', 0)):,}",
            f"- Soft upper (60–90mm): {cap.get('soft_seats', 0):,}",
            f"- Marginal/terrace (30–60mm): {cap.get('marginal_seats', 0):,}",
            f"- Rim/lawn (<30mm): {cap.get('terrace_seats', 0):,}",
            f"- **C_formal (quality-banded): {cap.get('c_formal', 0):.0f}**"
            f" (baseline {cap.get('baseline_c_formal', 1545)})",
            "",
            "## Scoring breakdown",
            "| Criterion | Raw | Weighted |",
            "|-----------|-----|---------|",
        ]
        for key, val in score.get("breakdown", {}).items():
            lines.append(f"| {key} | {val['raw']:.2f} | {val['weighted']:.2f} |")

        lines += [
            "",
            f"**Total**: {score.get('total', 0):.1f}  ",
            f"**Penalties**: {score.get('penalty_total', 0):.2f}  ",
            "",
            "## Verdict",
            f"**{vcolor} {verdict}**",
        ]

        failures = metrics.get("hard_failures", [])
        if failures:
            lines += ["", "### Hard constraint failures"]
            for f in failures:
                lines.append(f"- {f}")

        return "\n".join(lines) + "\n"


def _verdict(score: dict) -> str:
    return score.get("verdict", "unknown")


def _strip_arrays(obj):
    """Recursively remove numpy arrays from a dict for JSON serialisation."""
    if isinstance(obj, dict):
        return {k: _strip_arrays(v) for k, v in obj.items()
                if k not in ("sightline_rows",)}
    if isinstance(obj, list):
        if obj and isinstance(obj[0], dict):
            return [_strip_arrays(i) for i in obj]
        return obj
    if isinstance(obj, np.ndarray):
        return f"<array shape={obj.shape}>"
    return obj
