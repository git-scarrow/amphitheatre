#!/usr/bin/env python3
"""Shared anchor for the in-situ design package.

GOVERNING GEOMETRY — the three-section naturalistic civic bowl:

  analysis/scenarioE_civic/geometry.geojson    emitted + validated Scenario E
      surfaces (canon-ACCEPTED for seating / ADA / drainage): 45 restored
      tread polygons in three terrain-fitted sections (east / bend / south,
      rows 1-4 forecourt + 6-8, 11-18 civic), the rows-9/10 cross-aisle with
      row_reclassification provenance, switchback ADA ramps + landings,
      drainage swales, row-end shoulders, construction envelope, and the
      inherited stage (Rule 9 refit OPEN).
  design_extended_bays/composition_table.csv   per-(row, section) elevation,
      zone (forecourt / promenade / civic), axis radius, seats, residuals.
  design_extended_bays/seating_bays.geojson    bay centrelines incl. the
      row-5 promenade hinge band.

The sections are contour-fitted families, each with its own local curvature.
There is NO shared arc centre and NO constant-radius fan; the audit gate
rejects any regression to the superseded design_open_low single-fan scheme
(which this package previously consumed — see git history).

`bend` is the southeast transition family (between east and south).

Planning-grade. NAVD88 (Geoid12A) intl ft. CRS EPSG:6494.
"""
import csv
import json
import math
import os

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

GOVERNING_SCHEME = "scenarioE_three_section_civic_bowl"
SUPERSEDED_SCHEMES = ("design_open_low",)

SRC_SCENARIOE = os.path.join(REPO, "analysis", "scenarioE_civic", "geometry.geojson")
SRC_COMPOSITION = os.path.join(REPO, "design_extended_bays", "composition_table.csv")
SRC_BAYS = os.path.join(REPO, "design_extended_bays", "seating_bays.geojson")

# ── governing parameters (design_extended_bays + Scenario E) ────────────────
SECTIONS = ("east", "bend", "south")        # bend = the southeast family
FORMAL_ROWS = tuple(r for r in range(1, 19) if r not in (5, 9, 10))
PROMENADE_ROW = 5                           # hinge promenade / accessible band
AISLE_ROWS = (9, 10)                        # reclassified into the cross-aisle
AISLE_ELEV = 622.01
AX_AZ = 132.0                               # seating axis (reference ray only)
FACE_AZ = (AX_AZ + 180.0) % 360.0           # nominal facing 312° (fall line 307°)
SECTION_BREAK_AZ = (118.0, 152.0)           # hinge rays east|bend and bend|south
CX, CY = 19533067.7, 750799.2
F_T = 15.0
FOCUS_ELEV = 612.5                          # stage / event-floor reference
TREATMENT_BOTTOM = 609.1
EYE_SEATED_FT = 3.94
EYE_STANDING_FT = 5.2
BAY_VIEW_AZ = 330.0                         # measured EPT view corridor
BAY_PLANE = 579.45                          # measured bay water plane

# Rule 9: the stage is INHERITED (design_open_low geometry reused by Scenario E)
# and its refit is an OPEN canon item. This package must surface that status
# and must never declare a resolved fan for it.
STAGE_RULE9_STATUS = "open"
STAGE_AX_AZ = 150.0                         # inherited stage axis

DEM_DESIGN = os.path.join(REPO, "dem", "dem_design_1ft.tif")
VEC_DIR = os.path.join(REPO, "vectors_geojson")

CRS6494 = {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::6494"}}


def U(az_deg):
    a = math.radians(az_deg)
    return math.sin(a), math.cos(a)


_UX, _UY = U(AX_AZ)
FX, FY = CX + _UX * F_T, CY + _UY * F_T      # axis origin (NOT a shared arc centre)


def polar(R, az_deg, ox=FX, oy=FY):
    e, n = U(az_deg)
    return ox + e * R, oy + n * R


def fc(features, extra=None):
    out = {"type": "FeatureCollection", "crs": CRS6494, "features": features}
    if extra:
        out.update(extra)
    return out


def feat(props, geom):
    return {"type": "Feature", "properties": props, "geometry": geom}


def dump(obj, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        json.dump(obj, fh, indent=1)
    print(f"  wrote {os.path.relpath(path, REPO)}")


def load_scenarioE():
    """Scenario E features grouped by role."""
    with open(SRC_SCENARIOE) as fh:
        d = json.load(fh)
    by_role = {}
    for f in d["features"]:
        role = f["properties"].get("role") or "named"
        by_role.setdefault(role, []).append(f)
    return by_role


def load_composition():
    """{(row:int, section): row-dict} from the extended-bays composition table."""
    with open(SRC_COMPOSITION) as fh:
        return {(int(r["row"]), r["section"]): r for r in csv.DictReader(fh)}


def load_bays():
    with open(SRC_BAYS) as fh:
        return json.load(fh)["features"]


# ── curvature metadata (measured from the emitted geometry, never invented) ─
def fit_circle(xy):
    """Kasa least-squares circle fit. Returns (cx, cy, r, rmse_ft)."""
    x, y = xy[:, 0], xy[:, 1]
    A = np.c_[2 * x, 2 * y, np.ones(len(x))]
    b = x ** 2 + y ** 2
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    cx, cy = float(sol[0]), float(sol[1])
    r = float(math.sqrt(max(sol[2] + cx ** 2 + cy ** 2, 0.0)))
    rmse = float(np.sqrt(np.mean((np.hypot(x - cx, y - cy) - r) ** 2)))
    return cx, cy, r, rmse


def centerline(xy, nbins=24):
    """Approximate band centerline by binning ring vertices along the
    principal axis and taking per-bin means."""
    c = xy.mean(axis=0)
    d = xy - c
    _, _, vt = np.linalg.svd(d, full_matrices=False)
    t = d @ vt[0]
    order = np.argsort(t)
    xs, ts = xy[order], t[order]
    edges = np.linspace(ts[0], ts[-1], nbins + 1)
    pts = []
    for i in range(nbins):
        m = (ts >= edges[i]) & (ts <= edges[i + 1])
        if m.sum() >= 2:
            pts.append(xs[m].mean(axis=0))
    return np.array(pts)


def curvature_metadata(geom):
    """Measured curvature record for a tread band polygon (geo dict)."""
    from shapely.geometry import shape

    g = shape(geom)
    polys = [g] if g.geom_type == "Polygon" else list(g.geoms)
    xy = np.vstack([np.array(p.exterior.coords) for p in polys])
    cl = centerline(xy)
    cx, cy, r, rmse = fit_circle(cl)
    chord = float(np.hypot(*(cl[-1] - cl[0])))
    seg = np.diff(cl, axis=0)
    bearings = (np.degrees(np.arctan2(seg[:, 0], seg[:, 1]))) % 360.0
    r_cap = min(r, 99999.0)
    return {
        "fit_method": "kasa_circle_on_pca_binned_centerline",
        "fit_centre_x": round(cx, 1),
        "fit_centre_y": round(cy, 1),
        "fit_radius_ft": round(r_cap, 1),
        "fit_rmse_ft": round(rmse, 2),
        "chord_ft": round(chord, 1),
        "mean_tangent_bearing_deg": round(float(np.median(bearings)), 1),
        "curvature_class": ("circular_arc" if (rmse < 1.0 and r < 500.0)
                            else "contour_fitted"),
    }


def shared_fan_detected(tread_features, rmse_gate=1.0, radius_gate=500.0,
                        centre_spread_gate=10.0, share_gate=0.9):
    """True iff the seating reads as ONE constant-centre circular fan —
    the superseded design_open_low signature. Detection requires that at
    least `share_gate` of bands fit clean circles (rmse < gate, plausible
    radius) AND their fitted centres coincide. Contour-fitted families
    cannot satisfy this; a regression to a single fan always does."""
    from shapely.geometry import shape

    centres = []
    n = 0
    for f in tread_features:
        n += 1
        g = shape(f["geometry"])
        polys = [g] if g.geom_type == "Polygon" else list(g.geoms)
        xy = np.vstack([np.array(p.exterior.coords) for p in polys])
        cl = centerline(xy)
        cx, cy, r, rmse = fit_circle(cl if len(cl) >= 5 else xy)
        if rmse < rmse_gate and r < radius_gate:
            centres.append((cx, cy))
    if n == 0 or len(centres) / n < share_gate:
        return False
    c = np.array(centres)
    spread = float(np.hypot(c[:, 0].std(), c[:, 1].std()))
    return spread < centre_spread_gate


def verify_against_design():
    """Assert the governing three-section geometry is intact. Raises on
    drift or on regression to the single-fan scheme."""
    roles = load_scenarioE()
    comp = load_composition()
    treads = roles.get("formal_restored_tread", [])
    by_sec = {}
    for f in treads:
        p = f["properties"]
        by_sec.setdefault(p["section"], set()).add(p["row"])
        assert (p["row"], p["section"]) in comp, (
            f"tread row {p['row']}/{p['section']} missing from composition table")
    assert set(by_sec) == set(SECTIONS), (
        f"sections {sorted(by_sec)} != required east/bend(SE)/south")
    for s in SECTIONS:
        assert by_sec[s] == set(FORMAL_ROWS), (
            f"section {s} rows {sorted(by_sec[s])} != formal rows {FORMAL_ROWS}")
    assert not shared_fan_detected(treads), (
        "seating reads as ONE constant-centre fan — regression to the "
        "superseded design_open_low scheme")
    aisle = roles["cross_aisle"][0]["properties"]
    assert aisle.get("geometry_source") == "row_reclassification", (
        "cross-aisle provenance must be row_reclassification (canon Rule 6/7)")
    assert aisle.get("seam_derived") is False, "cross-aisle claims seam derivation"
    assert sorted(aisle.get("consumes_rows", [])) == list(AISLE_ROWS)
    stage = roles.get("stage_surface", [])
    assert len(stage) == 3, "stage core + two shoulders expected"
    assert all(f["properties"].get("blocks_bay_view") is False for f in stage), (
        "a stage surface claims to block the bay view")
    prom = [f for f in load_bays()
            if f["properties"]["row"] == PROMENADE_ROW]
    assert len(prom) == len(SECTIONS), "row-5 promenade hinge band incomplete"
    return {"roles": roles, "comp": comp, "promenade": prom}


if __name__ == "__main__":
    layers = verify_against_design()
    n = len(layers["roles"]["formal_restored_tread"])
    seats = sum(f["properties"]["seats_kept"]
                for f in layers["roles"]["formal_restored_tread"])
    print(f"OK — governing scheme {GOVERNING_SCHEME}: {n} tread bands in "
          f"{len(SECTIONS)} terrain-fitted sections (east/bend/south), "
          f"{seats} Band-A seats, cross-aisle provenance honest, "
          f"stage Rule 9 status: {STAGE_RULE9_STATUS}")
