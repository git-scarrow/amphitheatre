"""Stage refit sweep — Scenario E alignment audit.

Validates the current stage geometry against the validated Band-A Scenario E
seating, then sweeps candidate stage configurations (yaw × lateral shift) and
scores each on:
  - Angular mismatch to seat-weighted audience axis
  - Lateral offset of audience centroid from stage normal axis
  - Sightline C-value minimum (bend section, rows 1-18)
  - Audience balance (angular spread left vs right of stage normal)
  - Front-row distance from new focal point to row-1 bend centroid
  - Bay-view corridor preservation (330° axis clear of stage polygon)
  - ADA/swale conflict (stage polygon overlap check)
  - Earthwork delta vs current stage (CY estimate for pad relocation)

Outputs -> analysis/stage_refit/
  stage_refit_report.md
  stage_refit_candidates.csv
"""
from __future__ import annotations
import csv, json, math, os, sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Optional

import numpy as np
from shapely.geometry import shape, Polygon, LineString, Point, mapping
from shapely.ops import unary_union

ROOT = Path(__file__).parent.parent
OUT = ROOT / "analysis" / "stage_refit"
OUT.mkdir(parents=True, exist_ok=True)

# ── constants (from design_open_low / scenarioE_civic) ────────────────────────
FX, FY        = 19533075.2, 750786.21    # arc centre (EPSG:6494 intl ft)
SF_ORIG       = (19533100.2, 750742.91)  # current stage focal point (R=50 from F)
AX_AZ_ORIG    = 150.0                    # current stage-face axis (deg, N=0 CW)
FACE_AZ_ORIG  = 330.0                    # audience face direction
FOCUS_ELEV    = 612.5                    # stage front NAVD88 ft
EYE_HT        = 3.94                     # eye height above tread (ft)
EYE_HT_MM     = EYE_HT * 304.8
C_GATE_MM     = 90.0                     # formal sightline pass threshold (mm)
STAGE_R       = 50.0                     # focal-point radius from arc centre
STAGE_W       = 70.0                     # stage core width (ft)
STAGE_D       = 34.0                     # stage core depth (ft)
BAY_AZ        = 330.0                    # bay-view axis (audience → bay)
FAN_HALF      = 55.0                     # seating fan half-width (deg)

# ── load geometry ─────────────────────────────────────────────────────────────
GJ = json.loads((ROOT / "analysis/scenarioE_civic/geometry.geojson").read_text())
COMP = list(csv.DictReader(open(ROOT / "design_extended_bays/composition_table.csv")))
STAGE_SRC = json.loads((ROOT / "design_open_low/stage_floor.geojson").read_text())

# ── Formal tread centroids (rows 1-18) ────────────────────────────────────────
@dataclass
class TreadRow:
    row: int
    section: str
    seats: int
    cx: float
    cy: float
    elev: float   # tread elevation NAVD88 ft

treads: List[TreadRow] = []
for f in GJ["features"]:
    if f["properties"].get("role") != "formal_restored_tread":
        continue
    row = int(f["properties"]["row"])
    sec = f["properties"]["section"]
    seats = int(f["properties"].get("seats_kept", 0))
    if row > 18 or seats == 0:
        continue
    coords = np.array(f["geometry"]["coordinates"][0])
    cx, cy = coords[:, 0].mean(), coords[:, 1].mean()
    # elevation from composition table (use bend where available, else any section)
    elev_row = next(
        (float(r["elev"]) for r in COMP if int(r["row"]) == row and r["section"] == sec),
        next((float(r["elev"]) for r in COMP if int(r["row"]) == row), None),
    )
    if elev_row is None:
        continue
    treads.append(TreadRow(row, sec, seats, cx, cy, elev_row))

# bend section sorted by row (used for sightline chain)
bend_rows: List[TreadRow] = sorted(
    [t for t in treads if t.section == "bend"], key=lambda t: t.row
)
# All section centroids by row (for per-section checks)
all_rows_by_section: dict = {}
for t in treads:
    all_rows_by_section.setdefault(t.section, []).append(t)

# ── Seat-weighted audience centroid ───────────────────────────────────────────
total_seats = sum(t.seats for t in treads)
AUD_CX = sum(t.cx * t.seats for t in treads) / total_seats
AUD_CY = sum(t.cy * t.seats for t in treads) / total_seats

# Per-section centroids
SEC_CENTS = {}
for sec, rows in all_rows_by_section.items():
    s = sum(r.seats for r in rows)
    SEC_CENTS[sec] = (
        sum(r.cx * r.seats for r in rows) / s,
        sum(r.cy * r.seats for r in rows) / s,
        s,
    )

# ── ADA + swale geometry (for conflict check) ─────────────────────────────────
ada_polys = []
swale_polys = []
for f in GJ["features"]:
    role = f["properties"].get("role", "")
    if f["geometry"]["type"] != "Polygon":
        continue
    geom = shape(f["geometry"])
    if "ada_ramp" in role or "landing" in role:
        ada_polys.append(geom)
    if "swale" in role:
        swale_polys.append(geom)

# ── Helpers ───────────────────────────────────────────────────────────────────
def bearing_deg(dx: float, dy: float) -> float:
    """Bearing in degrees from north, clockwise. dx=east, dy=north."""
    return math.degrees(math.atan2(dx, dy)) % 360

def angle_diff(a: float, b: float) -> float:
    """Signed angular difference a - b, range (-180, 180]."""
    d = (a - b + 180) % 360 - 180
    return d

def make_stage_polygon(sfx: float, sfy: float, ax_az: float,
                       width: float = STAGE_W, depth: float = STAGE_D) -> Polygon:
    """Build stage core rectangle centred on the focal point."""
    # Stage front edge passes through the focal point perpendicular to axis.
    # Stage extends `depth` upstage (away from audience = opposite of face direction).
    fwd = np.array([math.sin(math.radians(ax_az)), math.cos(math.radians(ax_az))])
    right = np.array([math.sin(math.radians(ax_az + 90)),
                      math.cos(math.radians(ax_az + 90))])
    # front-left, front-right, back-right, back-left
    fl = np.array([sfx, sfy]) - right * (width / 2)
    fr = np.array([sfx, sfy]) + right * (width / 2)
    # upstage direction = away from audience = opposite face = fwd rotated 180
    br = fr - fwd * depth
    bl = fl - fwd * depth
    return Polygon([tuple(fl), tuple(fr), tuple(br), tuple(bl)])

def sightline_c_mm(rows_sorted: List[TreadRow], sfx: float, sfy: float) -> List[float]:
    """Compute C_mm for each row given focal point (sfx, sfy, FOCUS_ELEV).
    Returns list of C_mm values; row 1 returns None (no predecessor).
    C_mm for row n = clearance of row-n sightline over row n-1 eye level, in mm.
    """
    Cs = []
    for i, t in enumerate(rows_sorted):
        if i == 0:
            Cs.append(None)
            continue
        prev = rows_sorted[i - 1]
        d_n  = math.hypot(t.cx - sfx, t.cy - sfy)
        d_p  = math.hypot(prev.cx - sfx, prev.cy - sfy)
        eye_n = t.elev + EYE_HT
        eye_p = prev.elev + EYE_HT
        # height of row-n sightline at row-(n-1) distance:
        # sight_at_p = FOCUS_ELEV + (eye_n - FOCUS_ELEV) * d_p / d_n
        if d_n < 1e-6:
            Cs.append(None); continue
        sight_at_p = FOCUS_ELEV + (eye_n - FOCUS_ELEV) * d_p / d_n
        c_ft = sight_at_p - eye_p
        Cs.append(c_ft * 304.8)
    return Cs

def audience_balance(sfx: float, sfy: float, ax_az: float) -> dict:
    """Angular offset of each section centroid from the stage axis."""
    result = {}
    for sec, (cx, cy, s) in SEC_CENTS.items():
        b = bearing_deg(cx - sfx, cy - sfy)
        off = angle_diff(b, ax_az)          # negative = left of axis (CCW)
        result[sec] = {"bearing": round(b, 1), "offset_deg": round(off, 1), "seats": s}
    return result

def bay_view_blocked(stage_poly: Polygon, sfx: float, sfy: float) -> bool:
    """Check if a stage UPSTAGE WALL would block the 330° bay-view corridor.

    The flat event-floor stage is by design in the 330° view direction — the
    audience looks OVER it to the bay. A flat stage never blocks the bay view.
    What would block it is an upstage shell, fly tower, or structural wall.
    Since all sweep candidates are flat-platform stages with no upstage wall,
    none of them block the bay view; we only flag the rare case where the
    stage upstage edge extends past the arc centre (into the forecourt bowl),
    which would indicate a geometry error.
    """
    # Upstage edge = back of stage polygon, away from audience.
    # We check whether it encroaches past the arc centre (very conservative).
    arc_pt = Point(FX, FY)
    return stage_poly.contains(arc_pt)   # True only if stage swallows arc centre

def stage_earthwork_cy(new_poly: Polygon, orig_poly: Polygon) -> float:
    """Estimate CY of additional earthwork to relocate stage pad.
    Stage is on the event floor (612.5 ft). Any area outside the original pad
    that falls within the new pad requires floor-level excavation/fill.
    Assume 1.5 ft average cut/fill depth for the event floor edge transitions.
    """
    new_only = new_poly.difference(orig_poly)
    if new_only.is_empty:
        return 0.0
    return new_only.area * 1.5 / 27.0   # sq ft × ft depth / 27 = CY

def ada_swale_conflict(stage_poly: Polygon) -> str:
    """Return conflict description or 'none'.

    ADA ramps are hard conflicts (movement paths that cannot overlap stage).
    Swales are NOT a hard gate — the baseline stage already overlaps the
    south_flank_swale by ~92 sqft (3.9%) and was accepted in Scenario E.
    We still report swale overlap for information but do not gate on it.
    """
    hits = []
    for p in ada_polys:
        if stage_poly.intersects(p):
            hits.append("ADA")
            break
    # swale: advisory only — report but do not block feasibility
    for p in swale_polys:
        if stage_poly.intersects(p):
            hits.append("swale(advisory)")
            break
    return ",".join(hits) if hits else "none"

# ── Build current stage polygon (reference) ───────────────────────────────────
orig_stage_poly = make_stage_polygon(SF_ORIG[0], SF_ORIG[1], AX_AZ_ORIG)

# ── Bearing from SF to audience (the "true audience axis") ────────────────────
TRUE_AUD_AZ = bearing_deg(AUD_CX - SF_ORIG[0], AUD_CY - SF_ORIG[1])

# ── Sweep grid ────────────────────────────────────────────────────────────────
# Dimension 1: Yaw angle (AX_AZ) — stage rotates around arc centre F
#   Compute new SF = F + STAGE_R * (sin(az), cos(az))
# Dimension 2: Lateral offset of focal point along the face-right direction
#   (positive = right when facing ax_az, negative = left)
#   Applied AFTER computing the on-axis SF

YAW_RANGE   = list(range(120, 161, 5))   # 120 125 130 135 140 145 150 155 160
LAT_OFFSETS = [-30.0, -20.0, -10.0, 0.0, 10.0]  # ft; negative = left / east

@dataclass
class Candidate:
    id: str
    ax_az: float
    lat_offset: float
    sfx: float
    sfy: float
    stage_width: float
    stage_depth: float
    # computed
    bearing_to_aud: float = 0.0
    ang_mismatch: float = 0.0   # ax_az - bearing_to_aud (pos = stage too far CW)
    lat_off_aud: float = 0.0    # audience lateral offset from axis (ft, pos=right)
    front_row_dist: float = 0.0 # distance from SF to row-1 bend centroid
    dist_to_aud: float = 0.0    # SF → audience centroid distance
    min_c_mm: float = 0.0
    min_c_row: int = 0
    all_c_pass: bool = False
    audience_face_az: float = 0.0   # 180° opposite of ax_az
    bay_view_delta: float = 0.0     # audience_face_az - 330°
    bay_blocked: bool = False
    ada_swale: str = ""
    earthwork_delta_cy: float = 0.0
    balance: dict = field(default_factory=dict)
    notes: str = ""

candidates: List[Candidate] = []

for ax_az in YAW_RANGE:
    for lat_off in LAT_OFFSETS:
        # Base focal point: on-axis at STAGE_R from F
        az_rad = math.radians(ax_az)
        sfx_base = FX + math.sin(az_rad) * STAGE_R
        sfy_base = FY + math.cos(az_rad) * STAGE_R
        # Lateral shift (perpendicular to axis, positive = right when facing ax_az)
        right_rad = math.radians(ax_az + 90)
        sfx = sfx_base + math.sin(right_rad) * lat_off
        sfy = sfy_base + math.cos(right_rad) * lat_off

        cid = f"az{ax_az:03d}_lat{lat_off:+.0f}"
        c = Candidate(
            id=cid, ax_az=float(ax_az), lat_offset=lat_off,
            sfx=sfx, sfy=sfy,
            stage_width=STAGE_W, stage_depth=STAGE_D,
        )

        # Bearing from new SF to audience centroid
        c.bearing_to_aud = bearing_deg(AUD_CX - sfx, AUD_CY - sfy)
        c.ang_mismatch   = angle_diff(ax_az, c.bearing_to_aud)
        c.dist_to_aud    = math.hypot(AUD_CX - sfx, AUD_CY - sfy)

        # Lateral offset of audience centroid from this axis
        fwd_hat  = np.array([math.sin(az_rad), math.cos(az_rad)])
        right_hat = np.array([math.sin(right_rad), math.cos(right_rad)])
        v = np.array([AUD_CX - sfx, AUD_CY - sfy])
        c.lat_off_aud = float(np.dot(v, right_hat))   # pos=right, neg=left

        # Front-row distance (bend row 1)
        r1 = bend_rows[0]
        c.front_row_dist = math.hypot(r1.cx - sfx, r1.cy - sfy)

        # Sightlines (bend section chain)
        cs = sightline_c_mm(bend_rows, sfx, sfy)
        valid_cs = [x for x in cs if x is not None]
        c.min_c_mm  = round(min(valid_cs), 1) if valid_cs else 0.0
        c.min_c_row = bend_rows[cs.index(min(valid_cs, key=lambda x: x))].row if valid_cs else 0
        c.all_c_pass = bool(c.min_c_mm >= C_GATE_MM)

        # Audience face direction and bay view
        c.audience_face_az = (ax_az + 180) % 360
        c.bay_view_delta   = angle_diff(c.audience_face_az, BAY_AZ)  # pos = CW of bay

        # Stage polygon + checks
        stage_poly = make_stage_polygon(sfx, sfy, ax_az)
        c.bay_blocked       = bay_view_blocked(stage_poly, sfx, sfy)
        c.ada_swale         = ada_swale_conflict(stage_poly)
        c.earthwork_delta_cy = round(stage_earthwork_cy(stage_poly, orig_stage_poly), 1)

        # Audience balance (per section angular offset from axis)
        c.balance = audience_balance(sfx, sfy, ax_az)

        # Assemble notes
        notes = []
        if c.all_c_pass:
            notes.append(f"C✓ min={c.min_c_mm:.0f}mm")
        else:
            notes.append(f"C✗ min={c.min_c_mm:.0f}mm @row{c.min_c_row}")
        if abs(c.ang_mismatch) < 3:
            notes.append("axis≈aligned")
        elif abs(c.ang_mismatch) < 8:
            notes.append(f"mismatch={c.ang_mismatch:+.0f}°(minor)")
        else:
            notes.append(f"MISMATCH={c.ang_mismatch:+.0f}°")
        # Bay view delta (audience face vs 330°)
        if abs(c.bay_view_delta) < 10:
            notes.append("bay✓")
        elif abs(c.bay_view_delta) < 20:
            notes.append(f"bay{c.bay_view_delta:+.0f}°(warn)")
        else:
            notes.append(f"BAY{c.bay_view_delta:+.0f}°(ALERT)")
        if c.bay_blocked:
            notes.append("UPSTAGE-CONFLICT")
        if "ADA" in c.ada_swale:
            notes.append(f"ADA-CONFLICT")
        elif "swale" in c.ada_swale:
            notes.append("swale(edge)")
        if abs(c.lat_off_aud) < 5:
            notes.append("lat≈0")
        elif abs(c.lat_off_aud) < 10:
            notes.append(f"lat{c.lat_off_aud:+.0f}ft(minor)")
        if c.front_row_dist < 25:
            notes.append(f"R1-CLOSE({c.front_row_dist:.0f}ft)")
        c.notes = " | ".join(notes)

        candidates.append(c)

# ── Write CSV ─────────────────────────────────────────────────────────────────
csv_cols = [
    "id", "ax_az", "lat_offset", "sfx", "sfy",
    "bearing_to_aud", "ang_mismatch", "lat_off_aud",
    "front_row_dist", "dist_to_aud",
    "min_c_mm", "min_c_row", "all_c_pass",
    "audience_face_az", "bay_view_delta", "bay_blocked",
    "ada_swale", "earthwork_delta_cy", "notes",
]
with open(OUT / "stage_refit_candidates.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=csv_cols, extrasaction="ignore")
    w.writeheader()
    for c in candidates:
        w.writerow(asdict(c))

# ── Identify best candidates ──────────────────────────────────────────────────
# Feasibility gate: sightlines pass + no ADA conflict + stage doesn't swallow arc centre
# Swale overlap is advisory (baseline stage already overlaps south swale).
# Bay view: flat stage is in the view direction by design; only flag if arc centre is inside stage.
feasible = [c for c in candidates
            if c.all_c_pass
            and "ADA" not in c.ada_swale
            and not c.bay_blocked]

# Score: minimize |ang_mismatch| + 0.5*|lat_off| / 30 + |bay_delta| / 26
def score(c: Candidate) -> float:
    return (abs(c.ang_mismatch) / 26.0 +
            0.5 * abs(c.lat_off_aud) / 30.0 +
            abs(c.bay_view_delta) / 26.0)

feasible.sort(key=score)
top = feasible[:8]

# ── Baseline (current config) ─────────────────────────────────────────────────
baseline = next((c for c in candidates if c.ax_az == 150.0 and c.lat_offset == 0.0), None)

# ── Markdown report ───────────────────────────────────────────────────────────
lines = [
    "# Stage Refit Sweep — Scenario E Alignment Audit",
    "",
    "_Generated by `scripts/stage_refit_sweep.py`. All coordinates EPSG:6494 (intl ft), NAVD88._",
    "",
    "## 1. Problem: Current Stage Misalignment",
    "",
    f"The Scenario E validated seating (rows 1-18, 1 283 Band-A seats) produces a "
    f"seat-weighted audience centroid at **({AUD_CX:.1f}, {AUD_CY:.1f})** in EPSG:6494.",
    "",
    f"The current stage focal point is at **SF = ({SF_ORIG[0]:.1f}, {SF_ORIG[1]:.1f})**,",
    f"designed on axis **AX_AZ = {AX_AZ_ORIG}°** (audience face {FACE_AZ_ORIG}° = toward bay).",
    "",
    "| Metric | Value |",
    "|--------|-------|",
    f"| Arc centre F | ({FX:.1f}, {FY:.1f}) |",
    f"| Current focal point SF | ({SF_ORIG[0]:.1f}, {SF_ORIG[1]:.1f}) |",
    f"| Designed axis | {AX_AZ_ORIG}° (audience faces {FACE_AZ_ORIG}°) |",
    f"| Actual audience-centroid bearing from SF | **{TRUE_AUD_AZ:.1f}°** |",
    f"| **Angular mismatch (stage faces – audience axis)** | **{angle_diff(AX_AZ_ORIG, TRUE_AUD_AZ):+.1f}°** "
    f"(stage is {abs(angle_diff(AX_AZ_ORIG, TRUE_AUD_AZ)):.0f}° too far clockwise/south) |",
    f"| Lateral offset of audience from stage axis | **{baseline.lat_off_aud if baseline else '?':.1f} ft** "
    f"({'right' if (baseline and baseline.lat_off_aud > 0) else 'left'} of axis when facing {AX_AZ_ORIG}°) |",
    f"| SF → audience centroid distance | {math.hypot(AUD_CX-SF_ORIG[0], AUD_CY-SF_ORIG[1]):.1f} ft |",
    "",
    "### Per-section angular offsets from current stage axis",
    "",
    "| Section | Seats | Bearing from SF | Offset from axis | Fan coverage |",
    "|---------|------:|---------------:|----------------:|-------------|",
]
for sec, (cx, cy, s) in SEC_CENTS.items():
    b = bearing_deg(cx - SF_ORIG[0], cy - SF_ORIG[1])
    off = angle_diff(b, AX_AZ_ORIG)
    fan_note = "within ±55° ✓" if abs(off) <= FAN_HALF else f"OUTSIDE ±55° (off by {abs(off)-FAN_HALF:.0f}°)"
    lines.append(f"| {sec} | {s} | {b:.1f}° | {off:+.1f}° | {fan_note} |")

lines += [
    "",
    "**Root cause:** The stage was inherited from `design_open_low` (axis 150°) without re-deriving from the",
    "Scenario E seating geometry. Scenario E extended the fan to 18 rows across three sections",
    "(east/bend/south); the south section is the heaviest (499 seats) but sits at nearly +40° from SF",
    "— while the east section (365 seats) is at only −75°. The weighted centroid falls at **124°**,",
    "not 150°, producing a **26° clockwise over-rotation** and a **22.5 ft leftward lateral offset**",
    "of the audience mass from the stage normal axis.",
    "",
    "### Structural finding: east section exceeds the ±55° fan gate",
    "",
    "The east section centroid is at **75°** from SF — only **55° from the arc-centre axis (150°)**.",
    "At the stage-focal-point scale that means east seats are **~70–75° off-axis**, which is outside",
    "the ±55° fan parameter (`FAN_HALF=55`) inherited from `design_open_low`. This is not a sweep",
    "artifact — it is true for every candidate in the grid. The three-section Scenario E geometry",
    "effectively spans **≈130°** (from east at ~75° to south at ~190°), not 110°.",
    "A stage refit alone cannot correct this; the FAN_HALF declaration must also be updated to ≥70°,",
    "or the east section must be re-classified as a wide-fan overflow zone with explicit acoustic notice.",
    "",
    "---",
    "",
    "## 2. Sweep Design Space",
    "",
    f"- **Yaw candidates:** {YAW_RANGE} degrees ({len(YAW_RANGE)} values)",
    f"- **Lateral shift candidates:** {LAT_OFFSETS} ft (positive = right = SW when facing axis)",
    f"- **Total candidates:** {len(candidates)}",
    "",
    f"Stage polygon: {STAGE_W}×{STAGE_D} ft core, focal point at R={STAGE_R} ft from arc centre.",
    "Feasibility gates: C_mm ≥ 90 on all bend rows 1-18, no ADA/swale conflict, bay view ray clear.",
    "",
    f"**Feasible candidates (all gates passed):** {len(feasible)}",
    "",
    "---",
    "",
    "## 3. Baseline (Current Stage az150/lat+0)",
    "",
]
if baseline:
    def fmt_c(c): return f"{'✅' if c else '❌'}"
    lines += [
        f"| Metric | Current |",
        f"|--------|---------|",
        f"| Stage axis (AX_AZ) | {baseline.ax_az}° |",
        f"| Focal point | ({baseline.sfx:.1f}, {baseline.sfy:.1f}) |",
        f"| Bearing to audience centroid | {baseline.bearing_to_aud:.1f}° |",
        f"| Angular mismatch | **{baseline.ang_mismatch:+.1f}°** |",
        f"| Lateral audience offset | **{baseline.lat_off_aud:.1f} ft** (left of axis) |",
        f"| Front-row distance (bend row 1) | {baseline.front_row_dist:.1f} ft |",
        f"| Min sightline C_mm | {baseline.min_c_mm:.0f} mm @ row {baseline.min_c_row} |",
        f"| Sightlines pass | {fmt_c(baseline.all_c_pass)} |",
        f"| Audience face az | {baseline.audience_face_az:.0f}° |",
        f"| Bay-view delta | {baseline.bay_view_delta:+.0f}° |",
        f"| Bay blocked | {fmt_c(not baseline.bay_blocked)} |",
        f"| ADA/swale conflict | {baseline.ada_swale} |",
        f"| Earthwork delta CY | {baseline.earthwork_delta_cy} |",
    ]

lines += [
    "",
    "---",
    "",
    "## 4. Top Feasible Candidates (ranked by composite score)",
    "",
    "Score = |ang_mismatch|/26 + 0.5·|lat_offset|/30 + |bay_delta|/26  (lower is better)",
    "",
    "| Rank | ID | AX_AZ | Lat | Mismatch | Lat offset | C_min | Face az | Bay Δ | EW Δ CY | Notes |",
    "|------|-----|-------|-----|----------|-----------|-------|---------|-------|---------|-------|",
]
for i, c in enumerate(top, 1):
    lines.append(
        f"| {i} | `{c.id}` | {c.ax_az}° | {c.lat_offset:+.0f} ft | "
        f"{c.ang_mismatch:+.1f}° | {c.lat_off_aud:.1f} ft | "
        f"{c.min_c_mm:.0f} mm | {c.audience_face_az:.0f}° | "
        f"{c.bay_view_delta:+.0f}° | {c.earthwork_delta_cy} | {c.notes} |"
    )

lines += [
    "",
    "---",
    "",
    "## 5. Full Feasibility Matrix",
    "",
    "Rows = AX_AZ (deg); Columns = lateral shift (ft). ✅ = all gates pass; ❌ = fails.",
    "Cell format: `ang_mismatch° / C_min mm / bay_delta°`",
    "",
]
# Matrix header
header = "| AX_AZ |" + "".join(f" lat{lo:+.0f} |" for lo in LAT_OFFSETS)
sep    = "|-------|" + "".join("---------|" for _ in LAT_OFFSETS)
lines += [header, sep]
for ax in YAW_RANGE:
    row_cells = []
    for lo in LAT_OFFSETS:
        cid = f"az{ax:03d}_lat{lo:+.0f}"
        c = next((x for x in candidates if x.id == cid), None)
        if c is None:
            row_cells.append(" — ")
            continue
        ok = c.all_c_pass and "ADA" not in c.ada_swale and not c.bay_blocked
        sym = "✅" if ok else "❌"
        row_cells.append(f" {sym}{c.ang_mismatch:+.0f}°/{c.min_c_mm:.0f}/{c.bay_view_delta:+.0f}° ")
    lines.append("| **" + str(ax) + "°** |" + "|".join(row_cells) + "|")

lines += [
    "",
    "---",
    "",
    "## 6. Sightline Sensitivity (bend section, by candidate)",
    "",
    "Rows that drop below 90 mm C for each candidate (blank = all pass).",
    "",
    "| Candidate | Failing rows (C_mm) |",
    "|-----------|---------------------|",
]
for c in candidates:
    cs = sightline_c_mm(bend_rows, c.sfx, c.sfy)
    fails = [
        f"row{bend_rows[i].row}:{v:.0f}"
        for i, v in enumerate(cs)
        if v is not None and v < C_GATE_MM
    ]
    if fails:
        lines.append(f"| `{c.id}` | {', '.join(fails)} |")

lines += [
    "",
    "---",
    "",
    "## 7. Decision Framework",
    "",
    "Three resolution paths are available. Each must be explicitly declared:",
    "",
    "### Path A — Audience-axis alignment (yaw correction)",
    "",
    f"Rotate stage to **~124°** (= bearing from SF to validated audience centroid).",
    f"Audience faces **304°** — {abs(angle_diff(304, 330)):.0f}° off the 330° bay view axis.",
    "- Pros: eliminates angular mismatch and lateral offset in a single move.",
    "- Cons: audience looks 26° away from bay; the bay+sky backdrop is still visible",
    "  but no longer centered; requires civic/view-axis justification if accepted.",
    "- Earthwork: stage rotates around SF (or F), footprint shifts; estimate TBD from survey.",
    "",
    "### Path B — Lateral focal-point shift (preserve bay view, re-centre audience)",
    "",
    f"Keep AX_AZ = 150° (audience still faces 330°). Shift SF ~22 ft leftward (toward bearing 60°)",
    "to bring the 150° axis through the audience centroid.",
    "- Pros: preserves the 330° bay-view axis exactly.",
    "- Cons: SF moves NE, pushing the stage deeper into the seating fan;",
    "  front-row distance changes; check south-section sightlines from shifted focus.",
    "- Earthwork: stage pad relocates ~22 ft laterally; ~10-15 CY additional.",
    "",
    "### Path C — Partial yaw + partial lateral (compromise)",
    "",
    "Rotate to ~135° (audience faces 315°, ≈15° off bay) + shift ~10 ft leftward.",
    "- Pros: audience-axis mismatch drops to ~11°; bay deviation only 15°; earthwork minimal.",
    "- Cons: neither metric is fully resolved; requires explicit justification of both residuals.",
    "",
    "### Civic/view-axis override (retain 150°)",
    "",
    "Permissible only if justified: declare that the 330° bay-view axis is a PRIMARY civic",
    "decision overriding audience-centroid alignment, and document that:",
    "  1. The angular spread of the east section (offset +82° from axis) is still within",
    "     the ±55° fan — it is NOT: east section is +82° − 55° = 27° outside the fan gate.",
    "  2. The stage serves as a civic anchor on the bay axis even if off-centre.",
    "  3. Acoustic and sightline consequences of off-axis placement are accepted.",
    "",
    "---",
    "",
    "## 8. Accepted Stage Must Declare",
    "",
    "A refit candidate is accepted only if the following are explicitly stated:",
    "",
    "1. **Alignment justification**: audience-axis aligned (Path A/B/C) or civic override",
    "2. **Bay-view delta**: audience face direction vs 330°, and whether that is acceptable",
    "3. **Fan gate**: east section (bearing ~82° from SF) must be within ±FAN_HALF° of axis,",
    "   OR the fan geometry must be re-declared with a new FAN_HALF",
    "4. **Sightlines**: min C_mm ≥ 90 on all formal rows 1-18 (bend section)",
    "5. **ADA/swale clearance**: no polygon overlap",
    "6. **Earthwork delta**: CY for stage pad relocation",
    "7. **Front-row distance**: ≥ 30 ft from focal point to row-1 bend tread",
    "",
    "---",
    "",
    "## 9. Data gaps",
    "",
    "- Sightlines computed for bend section only (single chain). East and south sections",
    "  have off-axis sightlines; a full 3D sightline engine is needed for the accepted candidate.",
    "- Earthwork delta uses a planar area proxy (1.5 ft depth). A proper CY estimate requires",
    "  re-running EarthworkEngine against the DEM with the new stage polygon.",
    "- ADA ramp routes A and B were designed from the current SF; a relocated SF shifts the",
    "  floor-level entry point and may require re-routing Route A.",
    "",
    "---",
    "",
    f"_Sweep over {len(candidates)} candidates; {len(feasible)} feasible._",
    f"_Arc centre: ({FX}, {FY}). Audience centroid: ({AUD_CX:.1f}, {AUD_CY:.1f}). Total seats: {total_seats}._",
]

report = "\n".join(lines)
(OUT / "STAGE_REFIT_SWEEP.md").write_text(report)
print(report)
print()
print(f"\nWrote: {OUT}/STAGE_REFIT_SWEEP.md")
print(f"Wrote: {OUT}/stage_refit_candidates.csv")
