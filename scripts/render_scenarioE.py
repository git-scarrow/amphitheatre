"""Render the Scenario E civic_bowl plan: hillshade + emitted surfaces by role."""
from __future__ import annotations
import json, os, sys
from pathlib import Path
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from shapely.geometry import shape

ROOT = Path(__file__).parent.parent; os.chdir(ROOT); sys.path.insert(0, str(ROOT / "scripts"))
from harness.project import ProjectState

STATE = ProjectState.load("harness_config.yaml")
TF = STATE.transform; Z = STATE.Z0
geo = json.load(open(ROOT / "analysis/scenarioE_civic/geometry.geojson"))

COLORS = {
    "formal_restored_tread": ("#1f77b4", "restored formal tread (rows 1-18)"),
    "cross_aisle": ("#ff7f0e", "row-9 cross-aisle (dispersion + pause)"),
    "ada_ramp": ("#d62728", "ADA switchback ramp (8.33%)"),
    "landing": ("#e377c2", "landing"),
    "drainage_swale": ("#17becf", "drainage swale → cell"),
    "row_end_shoulder": ("#2ca02c", "row 21-25 shoulder → lawn"),
    "stage_surface": ("#7f7f7f", "stage + lateral shoulders"),
    "construction_envelope": ("none", "construction envelope"),
}

def to_px(x, y):
    col = (x - TF.c) / TF.a; row = (y - TF.f) / TF.e
    return col, row

touched = []
for f in geo["features"]:
    if f["properties"]["role"] != "construction_envelope":
        touched.append(shape(f["geometry"]))
from shapely.ops import unary_union
b = unary_union(touched).bounds
(c0, r0) = to_px(b[0], b[3]); (c1, r1) = to_px(b[2], b[1])
m = 30
c0, c1 = int(min(c0, c1) - m), int(max(c0, c1) + m)
r0, r1 = int(min(r0, r1) - m), int(max(r0, r1) + m)

gy, gx = np.gradient(np.where(np.isfinite(Z), Z, np.nan))
shade = np.clip(0.5 - (gx + gy) * 0.7, 0, 1)

fig, ax = plt.subplots(figsize=(12, 11))
ax.imshow(shade, cmap="gray", alpha=0.55)
order = ["construction_envelope", "formal_restored_tread", "stage_surface", "row_end_shoulder",
         "cross_aisle", "ada_ramp", "drainage_swale", "landing"]
for role in order:
    col, _ = COLORS[role]
    for f in geo["features"]:
        if f["properties"]["role"] != role:
            continue
        g = shape(f["geometry"])
        polys = g.geoms if g.geom_type.startswith("Multi") else [g]
        for poly in polys:
            xs, ys = poly.exterior.xy
            cc = [to_px(x, y)[0] for x, y in zip(xs, ys)]
            rr = [to_px(x, y)[1] for x, y in zip(xs, ys)]
            if role == "construction_envelope":
                ax.plot(cc, rr, color="k", lw=1.2, ls="--", alpha=0.6)
            else:
                ax.fill(cc, rr, color=col, alpha=0.75, ec="white", lw=0.3)

ax.set_xlim(c0, c1); ax.set_ylim(r1, r0)
ax.set_xticks([]); ax.set_yticks([])
_v = json.load(open(ROOT / "analysis/scenarioE_civic/validation.json"))
_cy = _v.get("total_earthwork", {}).get("gross_cy", "?")
_seats = _v.get("formal_seats_emitted", "?")
ax.set_title("Scenario E — civic_bowl drawn & validated\n"
             f"restored bowl + ADA switchbacks + seam cross-aisle + swales + dissolved tips · "
             f"{_seats} formal seats · {_cy} CY · cost-proxy ACCEPTED")
ax.legend(handles=[Patch(facecolor=COLORS[k][0] if COLORS[k][0] != "none" else "white",
                         edgecolor="k", label=COLORS[k][1]) for k in order],
          loc="lower left", fontsize=9, framealpha=0.9)
out = ROOT / "analysis/scenarioE_civic/plan.png"
fig.savefig(out, dpi=120, bbox_inches="tight")
print("wrote", out)
