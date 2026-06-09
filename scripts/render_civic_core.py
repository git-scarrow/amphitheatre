"""Render the civic-bowl core design: plan view + sightline C-profile.

Reads:
  design_civic_core/zones.geojson      bays re-tagged by design_zone + overlooks/ADA
  design_civic_core/perseat_bands.csv  per-row centreline & per-seat 10th-pct C
  dem/dem_design_1ft.tif               topographic base
Writes:
  design_civic_core/plan.png
  design_civic_core/sightline_profile.png
"""
from __future__ import annotations
import csv, json, math
from pathlib import Path
import numpy as np
import rasterio
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize

OUT = Path("design_civic_core")
DEM = "dem/dem_design_1ft.tif"
CX, CY = 19533067.7, 750799.2
AX_AZ = 132.0; FACE_AZ = 312.0; F_T = 15.0; STAGE_R = 50.0
X_PETOSKEY = 19533270.8; Y_MITCHELL = 750593.6; Y_LAKE = 750943.1

def U(az): a = math.radians(az); return math.sin(a), math.cos(a)
UX, UY = U(AX_AZ)
FX, FY = CX + UX*F_T, CY + UY*F_T
SFx, SFy = FX + UX*STAGE_R, FY + UY*STAGE_R

ZONE_STYLE = {
    "promenade":        dict(color="#1f77b4", lw=2.4, ls="-", label="promenade / ADA cross-aisle"),
    "upper_landscape":  dict(color="#c8a24a", lw=3.0, ls="-", label="upper landscape (lawn/terrace)"),
    "soft_edge":        dict(color="#e08214", lw=2.6, ls="-", label="soft edge (optional)"),
}

def load_bands():
    rows = {}
    for r in csv.DictReader(open(OUT/"perseat_bands.csv")):
        def fnum(k):
            v = r[k]
            return float(v) if v not in ("", "None", None) else None
        rows[int(r["row"])] = dict(zone=r["zone"], kind=r["kind"],
                                   centre=fnum("centreline_C_mm"), c10=fnum("perseat_C10_mm"),
                                   pp=fnum("pct_pass"), bp=r["band_perseat"])
    return rows

def plan(feats, bands):
    ds = rasterio.open(DEM); Z = ds.read(1).astype(float); Z[Z == ds.nodata] = np.nan; T = ds.transform
    Xc = T.c + (np.arange(Z.shape[1]) + 0.5) * T.a
    Yc = T.f + (np.arange(Z.shape[0]) + 0.5) * T.e

    fig, ax = plt.subplots(figsize=(11, 10))
    # topographic base: light contour lines every 2 ft
    levels = np.arange(np.floor(np.nanmin(Z)/2)*2, np.nanmax(Z)+2, 2)
    ax.contour(Xc, Yc, Z, levels=levels, colors="#d9d9d9", linewidths=0.5, zorder=1)
    ax.contour(Xc, Yc, Z, levels=np.arange(600, 650, 10), colors="#bdbdbd", linewidths=0.9, zorder=1)

    # formal-core seating colored by per-seat 10th-pct C (sightline quality)
    c10s = [bands[r]["c10"] for r in bands if bands[r]["bp"] == "formal" and bands[r]["c10"]]
    norm = Normalize(vmin=90, vmax=max(220, max(c10s) if c10s else 220))
    cmap = plt.get_cmap("YlGn")

    for f in feats:
        p = f["properties"]; g = f["geometry"]; dz = p.get("design_zone")
        if g["type"] == "LineString" and dz in ("formal_core", "soft_edge", "upper_landscape", "promenade"):
            xy = np.array(g["coordinates"]);
            if dz == "formal_core" and p.get("kind") == "seating":
                rn = int(p["row"]); c10 = bands.get(rn, {}).get("c10")
                col = cmap(norm(c10)) if c10 else "#238b45"
                ax.plot(xy[:,0], xy[:,1], color=col, lw=3.0, solid_capstyle="round", zorder=4)
            elif dz in ZONE_STYLE:
                st = ZONE_STYLE[dz]
                ax.plot(xy[:,0], xy[:,1], color=st["color"], lw=st["lw"], ls=st["ls"],
                        solid_capstyle="round", zorder=3)

    # overlooks + ADA + stage
    for f in feats:
        p = f["properties"]; g = f["geometry"]
        if p.get("kind") == "bay_overlook":
            x, y = g["coordinates"]
            ax.plot(x, y, marker="*", ms=18, color="#7a0177", mec="white", mew=0.8, zorder=6)
            fx, fy = U(FACE_AZ); ax.annotate("", xy=(x+fx*38, y+fy*38), xytext=(x, y),
                        arrowprops=dict(arrowstyle="->", color="#7a0177", lw=1.6), zorder=6)
        elif p.get("kind") == "ada_entry":
            xy = np.array(g["coordinates"])
            ax.plot(xy[:,0], xy[:,1], color="#6a51a3", lw=2.2, ls=(0,(4,2)), zorder=5)
            ax.plot(xy[0,0], xy[0,1], marker="s", ms=7, color="#6a51a3", zorder=6)
    ax.plot(SFx, SFy, marker="*", ms=24, color="black", zorder=7)
    ax.annotate("STAGE", (SFx, SFy), xytext=(SFx-8, SFy+8), fontsize=10, fontweight="bold", zorder=7)
    fx, fy = U(FACE_AZ)
    ax.annotate("", xy=(SFx+fx*70, SFy+fy*70), xytext=(SFx, SFy),
                arrowprops=dict(arrowstyle="->", color="navy", lw=2.2), zorder=7)
    ax.annotate("to bay (NW)", (SFx+fx*70, SFy+fy*70), fontsize=8, color="navy")

    # streets
    ax.axvline(X_PETOSKEY, color="#cb181d", ls=(0,(6,3)), lw=1.3, zorder=2)
    ax.axhline(Y_MITCHELL, color="#cb181d", ls=(0,(6,3)), lw=1.3, zorder=2)
    ax.axhline(Y_LAKE, color="#cb181d", ls=(0,(6,3)), lw=1.3, zorder=2)
    ax.text(X_PETOSKEY, CY-150, "  Petoskey St (E, ~643')", color="#cb181d", rotation=90, va="center", fontsize=8)
    ax.text(CX-100, Y_MITCHELL+3, "E Mitchell St (S, ~641')", color="#cb181d", fontsize=8)
    ax.text(CX-100, Y_LAKE+3, "E Lake St (N, ~617' — bay side)", color="#cb181d", fontsize=8)

    ax.set_xlim(CX-120, CX+245); ax.set_ylim(CY-230, CY+185)
    ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
    ax.set_title("Petoskey Pit — Civic-Bowl Core + Upper Civic Landscape\n"
                 "formal seating rows ≤19 (per-seat C-confirmed) · envelope to the streets = landscape",
                 fontsize=12)

    # colorbar for sightline quality
    sm = ScalarMappable(norm=norm, cmap=cmap); sm.set_array([])
    cb = fig.colorbar(sm, ax=ax, fraction=0.035, pad=0.02)
    cb.set_label("formal-core sightline quality — per-seat 10th-pct C (mm)", fontsize=9)

    legend = [
        Line2D([0],[0], color="#238b45", lw=3, label="formal bowl (rows ≤19, ≥90 mm)"),
        Line2D([0],[0], color="#c8a24a", lw=3, label="upper landscape (lawn/terrace, rows 20–25)"),
        Line2D([0],[0], color="#1f77b4", lw=2.4, label="promenade / ADA cross-aisle (row 5)"),
        Line2D([0],[0], marker="*", color="#7a0177", lw=0, ms=13, label="bay overlook"),
        Line2D([0],[0], color="#6a51a3", lw=2, ls="--", label="ADA rim connection (schematic)"),
        Line2D([0],[0], marker="*", color="black", lw=0, ms=14, label="stage"),
        Line2D([0],[0], color="#cb181d", lw=1.3, ls="--", label="street boundary"),
    ]
    ax.legend(handles=legend, loc="lower left", fontsize=8, framealpha=0.92)
    ax.text(0.985, 0.015,
            "Formal core: ~1,566 (22\") / ~1,917 (18\") seats  ·  upper landscape: ~330–400 informal\n"
            "planning-grade; overlook/ADA schematic, alignment requires survey",
            transform=ax.transAxes, ha="right", va="bottom", fontsize=7.5, color="#555",
            bbox=dict(boxstyle="round", fc="white", ec="#ccc", alpha=0.9))
    fig.tight_layout()
    fig.savefig(OUT/"plan.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {OUT/'plan.png'}")

def profile(bands):
    seat = sorted(r for r in bands if bands[r]["kind"] == "seating" and bands[r]["zone"] == "civic")
    xs = seat
    centre = [bands[r]["centre"] for r in seat]
    c10 = [bands[r]["c10"] for r in seat]
    pp = [bands[r]["pp"] for r in seat]

    fig, ax = plt.subplots(figsize=(11, 6))
    # band shading
    ax.axhspan(90, 500, color="#e5f5e0", zorder=0)
    ax.axhspan(60, 90, color="#fff7bc", zorder=0)
    ax.axhspan(30, 60, color="#fee8c8", zorder=0)
    ax.axhspan(-60, 30, color="#fde0dd", zorder=0)
    ax.axhline(90, color="#444", lw=1.2, ls="--")
    ax.text(seat[0]-0.3, 92, "90 mm target", fontsize=8, color="#444")

    ax.plot(xs, centre, "-o", color="#9ecae1", lw=1.6, ms=5, label="centreline C (concentric)")
    ax.plot(xs, [c if c is not None else np.nan for c in c10], "-o", color="#08519c",
            lw=2.2, ms=6, label="per-seat 10th-pct C (flank-aware, authoritative)")
    # formal stop marker
    ax.axvline(19.5, color="#238b45", lw=2, ls=":")
    ax.text(19.4, 410, "formal stop\n(row 19)", color="#238b45", ha="right", fontsize=9, fontweight="bold")
    ax.text(20.1, 410, "→ landscape\n(rows 20–25)", color="#c8893a", ha="left", fontsize=9)

    # %pass annotation for boundary rows
    for r, c, q in zip(xs, c10, pp):
        if r >= 18 and c is not None:
            ax.annotate(f"{q:.0f}% pass", (r, c), textcoords="offset points", xytext=(0, -14),
                        ha="center", fontsize=7, color="#08519c")

    ax.set_xticks(xs); ax.set_xlabel("seating row (civic)")
    ax.set_ylabel("sightline C-value (mm)")
    ax.set_ylim(-60, 460); ax.set_xlim(seat[0]-0.6, seat[-1]+0.6)
    ax.set_title("Sightline quality by row — why the formal bowl stops at row 19\n"
                 "row 19 per-seat 93 mm / 95% pass (formal); row 20 drops to 59 mm / 54% pass (landscape)",
                 fontsize=12)
    ax.legend(loc="upper right", fontsize=9)
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT/"sightline_profile.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {OUT/'sightline_profile.png'}")

def main():
    feats = json.load(open(OUT/"zones.geojson"))["features"]
    bands = load_bands()
    plan(feats, bands)
    profile(bands)

if __name__ == "__main__":
    main()
