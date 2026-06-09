"""AffordanceEngine: read the site's latent form before any earthwork.

The governing reframing (see INEVITABILITY.md): the clay is not a cut/fill
minimizer, it is a site-affordance composer.  Its first job is to discover where
the land already wants to become something, so that later moves can be judged as
"compelled by a site affordance" rather than arbitrary optimization residue.

This engine derives the Site Affordance Map from the immutable DEM + confirmed
design context + (optionally) the Scenario-validation bands.  Every affordance
carries a `provenance` tag so downstream rules never treat an asserted constant
as if it were measured:
  computed     — derived from the LiDAR DEM here
  config       — a confirmed survey/design constant from harness_config.yaml
  validation   — imported from analysis/scenarioB_validation (segment bands)
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from .terrain import TerrainEngine

if TYPE_CHECKING:
    from .project import ProjectState


class AffordanceEngine:
    # natural-rake slope bands (%, rise/run) — planning assumptions, tunable
    PAN_MAX_PCT   = 8.0      # below this: flat pan / forecourt / stage apron
    RAKE_MIN_PCT  = 8.0      # seatable rake lower bound
    RAKE_MAX_PCT  = 45.0     # above this: too steep for seating without walls
    HINGE_LO_PCT  = 6.0
    HINGE_HI_PCT  = 12.0

    def __init__(self, state: "ProjectState"):
        self.state = state
        self.te = TerrainEngine(state)
        self.FX, self.FY = state.arc_centre()
        self.p = state.params()

    # ── natural rake: slope bands + does the rake face the stage? ────────────────
    def natural_rake(self) -> dict:
        Z = self.state.Z0
        slope = self.te.slope_pct(Z)
        # Robust latent-bowl test: arc-median elevation vs radius along the seating
        # fan (the same sampling the design uses). A true bowl rises with radius.
        radii = np.arange(self.p["R_INNER"], 192.0, 4.0)
        elevs = [self.te.sample_arc_row(Z, float(R))["median"] for R in radii]
        steps = [(elevs[i] - elevs[i - 1]) / (radii[i] - radii[i - 1])
                 for i in range(1, len(radii))
                 if np.isfinite(elevs[i]) and np.isfinite(elevs[i - 1])]
        rises = [s for s in steps if s > 0]
        total_rise = (np.nanmax(elevs) - np.nanmin(elevs)) if any(np.isfinite(elevs)) else 0.0

        fan = self.state.fan_mask(); finite = np.isfinite(Z)
        pan      = finite & (slope < self.PAN_MAX_PCT)
        seatable = finite & (slope >= self.RAKE_MIN_PCT) & (slope <= self.RAKE_MAX_PCT)
        steep    = finite & (slope > self.RAKE_MAX_PCT)

        def ac(m):
            return round(int(m.sum()) / 43560.0, 3)
        seat_in_fan = seatable & fan
        return {
            "provenance": "computed",
            "pan_ac": ac(pan), "seatable_rake_ac": ac(seatable), "steep_ac": ac(steep),
            "seatable_in_fan_ac": ac(seat_in_fan),
            "rake_rises_outward_frac": round(len(rises) / max(len(steps), 1), 3),
            "mean_radial_rise_pct": round(float(np.mean(steps) * 100), 1) if steps else 0.0,
            "natural_rise_over_fan_ft": round(float(total_rise), 1),
            "mean_seatable_slope_pct": round(float(np.nanmean(slope[seat_in_fan])) if seat_in_fan.any() else 0.0, 1),
            "note": "rake_rises_outward_frac near 1.0 = arc-median ground rises away from the stage "
                    "(rows step up the natural hill) = a latent bowl the design only intensifies",
        }

    # ── bowl hinge: radius where flat pan rolls into seating rake ────────────────
    def bowl_hinge(self) -> dict:
        Z = self.state.Z0
        slope = self.te.slope_pct(Z)
        FAN_HALF = self.p["FAN_HALF"]; AX = self.p["AX_AZ"]
        radii = np.arange(40, 200, 2.0)
        hinge_r = None; hinge_elev = None
        prev_pan = True
        for R in radii:
            azs = np.linspace(AX - FAN_HALF, AX + FAN_HALF, 31)
            sv, zv = [], []
            for az in azs:
                a = math.radians(az)
                x = self.FX + math.sin(a) * R; y = self.FY + math.cos(a) * R
                s = self.state.elev_at(slope, x, y); z = self.state.elev_at(Z, x, y)
                if np.isfinite(s): sv.append(s)
                if np.isfinite(z): zv.append(z)
            if not sv:
                continue
            med = float(np.median(sv))
            if prev_pan and med >= self.HINGE_LO_PCT:
                hinge_r = float(R); hinge_elev = round(float(np.median(zv)), 2)
                break
            prev_pan = med < self.HINGE_LO_PCT
        return {
            "provenance": "computed",
            "hinge_radius_ft": hinge_r,
            "hinge_elev_navd88": hinge_elev,
            "note": "the stage/forecourt belongs at or just inside the hinge — the natural seam "
                    "between flat pan and rising bowl",
        }

    # ── view axis: the set is the bay+sky, not an upstage wall ───────────────────
    def view_axis(self) -> dict:
        cfg = self.state.cfg
        focal = cfg["focal"]
        return {
            "provenance": "config",
            "face_az_deg": cfg["axes"]["face_az"],        # 330 NNW toward bay+evening sun
            "back_az_deg": cfg["axes"]["ax_az"],          # 150 stage looks at audience
            "focal_xy": [focal["x"], focal["y"]], "focal_elev_navd88": focal["elev_navd88"],
            "bay_navd88_ft": 581.4,
            "principle": "open upstage; the bay and sky are the backdrop. No tall element may "
                         "block the face_az view corridor without a stated civic reason.",
            "occluder_note": "foreground tree screen (densest az315-320) governs 330-vs-315 — see "
                             "bay-view viewshed analysis; not re-evaluated here.",
        }

    # ── edges: streets (hard clips) + arc-clipped tips ───────────────────────────
    def edges(self, validation: dict | None = None) -> dict:
        sb = self.state.cfg["street_bounds"]
        clipped_rows = []
        if validation:
            clipped_rows = sorted({int(r) for r in validation.get("clipped_tip_rows", [])})
        return {
            "provenance": "config+validation",
            "streets": {"lake_y_north": sb["lake_y"], "mitchell_y_south": sb["mitchell_y"],
                        "petoskey_x_east": sb["petoskey_x"], "west": "open to Bayfront Park"},
            "clipped_tip_rows": clipped_rows,
            "principle": "street edges are hard clips; arc-clipped row tips are NOT formal seating "
                         "— they dissolve into overlook/lawn/landscape shoulder.",
        }

    # ── drainage: where water already wants to move ──────────────────────────────
    def drainage(self) -> dict:
        root = self.state.root
        pour = None
        pp = root / "pour_point.geojson"
        if pp.exists():
            pour = json.load(open(pp))["features"][0]["properties"]
        tc = self.state.cfg["treatment_cell"]
        return {
            "provenance": "config+computed",
            "treatment_cell_bottom_navd88": tc["bottom_navd88"],
            "treatment_cell_pool_navd88": tc["pool_navd88"],
            "pour_point": pour,
            "principle": "drainage is landscape structure, not an afterthought. Treads must shed to "
                         "swales that reinforce the landform; clipped treads that dish and pond fail this.",
        }

    # ── strong / weak zones: where earthwork is worth it vs where to let go ───────
    def zones(self, validation: dict | None = None) -> dict:
        out = {"provenance": "validation", "strong_zones": [], "weak_zones": []}
        if not validation:
            out["note"] = "run scripts/validate_scenarioB.py first to populate band-derived zones"
            return out
        bands = validation.get("bands_scenarioD", {})
        out["strong_zones"] = [{"role": "formal lower bowl (Band A)", "seats": bands.get("A")}]
        out["weak_zones"] = [
            {"role": "soft terrace (Band B)", "seats": bands.get("B")},
            {"role": "overflow/lawn edge (Band C)", "seats": bands.get("C")},
            {"role": "landscape/no-count clipped tips (Band D)", "seats": bands.get("D")},
        ]
        out["principle"] = ("spend earthwork only on strong zones; demote weak zones to lawn/"
                            "overlook/planting instead of pretending clipped fragments are formal.")
        return out

    # ── assemble full map ────────────────────────────────────────────────────────
    def build(self, validation: dict | None = None) -> dict:
        return {
            "natural_rake": self.natural_rake(),
            "bowl_hinge":   self.bowl_hinge(),
            "view_axis":    self.view_axis(),
            "edges":        self.edges(validation),
            "drainage":     self.drainage(),
            "zones":        self.zones(validation),
        }
