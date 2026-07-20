# Rule 9 Path 1 (audience-axis, 124.4°) — pipeline dispatch / work order

**Status:** PROPOSED · owner-directed 2026-07-19 · **UNVALIDATED**. If — and only if —
the gates below pass on a harness host, this **supersedes** the P_opt / az-150 bundle
(`RULE9_DECISION_RECORD.md`, carried_provisional 2026-07-02). Until then, az-150 P_opt
remains the record.

**Why this exists:** the owner directed the stage be re-aimed to face the audience
(Rule 9 **Path 1 — audience-axis**), not kept on the bay axis. This work order can only be
*executed and validated* on a host with the pipeline + DEM (**gentoo**, `sam@gentoo`); the
authoring machine (macbook-m4) has neither, so the geometry change is **specified here, not
applied**, to avoid landing an unvalidated, un-gated reversal of a validated decision.

## The decision & its trade
- **Change:** stage axis **150° → 124.4°** (aim at the seat-weighted audience centroid, bearing 124.4°).
- **Trade (must be declared — Path 1 requirement):** audience now faces **~304.4°**, i.e.
  **−25.6° off the bay axis (330°)**. Bay-view alignment is deliberately given up for audience-facing.
- **Supersedes:** P_opt (az-150 kept, audience faces the bay) + the 2026-07-02 carried_provisional bundle.

## Run host
**gentoo** (primary workstation; has the truth pipeline, DEM rasters, and the stage-gate suite).
Do NOT run on macbook-m4 — no DEM, no harness; it cannot validate.

## Step 1 — apply the geometry (deterministic; run on the harness host)
Rotate the stage assembly **25.6° CCW about the focal point** `focal_point_stage_front`
`[19533100.2, 750742.91]` (EPSG:6494 intl ft). Self-contained, stdlib:

```python
import json, math
F=[19533100.2,750742.91]; alpha=math.radians(150.0-124.4)  # CCW; drops bearing 150->124.4
ca,sa=math.cos(alpha),math.sin(alpha)
def rot(p):
    dx,dy=p[0]-F[0],p[1]-F[1]
    return [round(F[0]+dx*ca-dy*sa,2), round(F[1]+dx*sa+dy*ca,2)]
def rot_geom(g):
    t=g["type"]; c=g["coordinates"]
    if t=="Polygon": g["coordinates"]=[[rot(p) for p in r] for r in c]
    elif t=="MultiPolygon": g["coordinates"]=[[[rot(p) for p in r] for r in poly] for poly in c]
    elif t=="LineString": g["coordinates"]=[rot(p) for p in c]

# authoritative stage-of-record deck
p1="analysis/in_situ_normalization/adopted_stage_footprint.geojson"
d=json.load(open(p1))
for f in d["features"]:
    pr=f.setdefault("properties",{})
    if pr.get("name")=="adopted_stage_deck" or "axis_az" in pr:
        rot_geom(f["geometry"]); pr["axis_az"]=124.4
        pr["reorientation_note"]="Rule 9 Path 1 audience-axis (124.4); supersedes P_opt az150 IF gates pass. Bay-view -25.6 declared."
json.dump(d,open(p1,"w"),indent=1,ensure_ascii=False); open(p1,"a").write("\n")

# design-family source (stage + shoulders + forecourt + focal metadata)
p2="design_open_low/stage_floor.geojson"
d=json.load(open(p2)); T={"stage","stage_shoulder_left","stage_shoulder_right","event_floor_forecourt"}
for f in d["features"]:
    pr=f.setdefault("properties",{}); nm=pr.get("name")
    if nm in T: rot_geom(f["geometry"])
    if nm=="focal_point_stage_front":
        pr["centerline_az_deg"]=124.4; pr["audience_face_az_deg"]=304.4
json.dump(d,open(p2,"w"),indent=1,ensure_ascii=False); open(p2,"a").write("\n")
```

**Verification checksum** (centroid bearing from focal, before → after):
`adopted_stage_deck` 342.9 → **317.3**; `design_open_low` `stage` 330.0 → **304.4**;
`event_floor_forecourt` 150.0 → **124.4**. `adopted_stage_deck.axis_az` = **124.4**.

## Step 2 — regenerate + gate (the arbiter)
Run on gentoo, in order; **any hard failure REJECTS 124°**:
- `scripts/build_in_situ_geometry.py` — re-derive geometry from the rotated sources.
- Stage gate suite: `stage_current_geometry_gate.py`, `stage_pad_lineage_audit.py`,
  `stage_pad_redteam.py`, `stage_placement_clearance.py`, `stage_shape_study.py`.
- `scripts/emit_tier_scenarios.py` + the sightline C-value re-emit (row-1 gaps ≥ 12 ft,
  C ≥ 90 mm bar), `scripts/build_truth_package.py`, `scripts/audit_in_situ_package.py`.

## Step 3 — acceptance
- **All gates PASS →** update `RULE9_DECISION_RECORD.md`, `docs/DESIGN_CANON.md` Rule 9, and
  `truth_package/design_state.current.json` to **Path 1 audience-axis, resolved**; record the
  **bay-view −25.6° deviation** as accepted; regenerate `unreal_export/` + manifest.
- **Any gate FAILS →** **124° is rejected**; az-150 / P_opt stands as the record. Report the
  failing gate + metric (e.g. row-1 gap, sightline C, pad clearance).

## Crux for the human running this
Several stage gates **encode az-150 as the adopted constant**, so they will flag the axis
change *by construction*. Distinguish:
- a **real geometric failure** (row-1 seat gap < 12 ft, sightline C below bar, pad/ADA
  clearance loss) — 124° is genuinely worse and should be rejected; vs
- a **stale-constant flag** (a gate asserting `axis_az == 150`) — the gate must be re-authored
  to the newly adopted axis, not treated as a rejection.

That distinction is an owner/human call, not an automated one.
