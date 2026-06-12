#!/usr/bin/env python3
"""Build the auditable truth package + web-viewer data for the civic bowl.

Reads the CURRENT accepted design (Scenario E three-section civic bowl, as
expressed by the in-situ package) and emits:

  truth_package/design_state.current.json       structured design state
  truth_package/evaluation_report.current.json   checks: pass/warn/fail/unknown
  truth_package/export_manifest.json             contract for future exports
  web_viewer/data/site_data.js                   self-contained viewer payload

Rules honoured (see truth_package/data_inventory.md):
  - no source GeoJSON is mutated; everything here is read-only on sources
  - no claim is hard-coded when it can be read from a source table
    (seat counts, C values, ADA/swale/volume numbers all come from
    analysis/tier_emission/Scenario_E_baseline_reemit/validation.json,
    vectors_geojson/*, dem/in_situ_grading_manifest.json,
    analysis/decision_packet/decision_table.csv)
  - checks that cannot be computed from repo data are emitted as UNKNOWN
  - the stage deck is carried PROVISIONAL (DESIGN_CANON.md Rule 9 OPEN)

Degrades gracefully when DEM rasters are absent (fresh checkout): the viewer
payload then carries a flat, clearly-labelled PLACEHOLDER surface and the
evaluation report marks terrain-derived items unknown.
"""
import base64
import csv
import datetime as _dt
import hashlib
import json
import math
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))

# ── governing constants (single source: scripts/in_situ_common.py) ──────────
try:
    import in_situ_common as C

    ORIGIN_X, ORIGIN_Y = C.CX, C.CY
    BAY_VIEW_AZ = C.BAY_VIEW_AZ
    BAY_PLANE = C.BAY_PLANE
    _CONST_SOURCE = "scripts/in_situ_common.py"
except Exception as exc:  # fresh checkout without deps for that module
    ORIGIN_X, ORIGIN_Y = 19533067.7, 750799.2
    BAY_VIEW_AZ, BAY_PLANE = 330.0, 579.45
    _CONST_SOURCE = f"fallback constants (in_situ_common import failed: {exc})"

SRC = {
    "treads": "vectors_geojson/terrace_treads.geojson",
    "zones": "vectors_geojson/bowl_zones.geojson",
    "site_context": "vectors_geojson/site_context.geojson",
    "viewpoints": "vectors_geojson/in_situ_viewpoints.geojson",
    "material_zones": "vectors_geojson/material_zones.geojson",
    "stage_lineage": "design_open_low/stage_floor.geojson",
    "human_refs": "vectors_geojson/human_scale_refs.geojson",
    "validation": "analysis/tier_emission/Scenario_E_baseline_reemit/validation.json",
    "ada_nodes": "vectors_geojson/ada_nodes.geojson",
    "ada_route": "vectors_geojson/ada_route.geojson",
    "ada_legacy": "vectors_geojson/legacy_ada_rejected.geojson",
    "ada_validation": "analysis/ada_rebuild/ada_validation.json",
    "grading_manifest": "dem/in_situ_grading_manifest.json",
    "decision_table": "analysis/decision_packet/decision_table.csv",
    "earthwork_csv": "analysis/scenarioE_civic/earthwork.csv",
    "dem_existing": "dem/dem_design_1ft.tif",
    "dem_proposed": "dem/proposed_grade_1ft.tif",
    "dem_cutfill": "dem/cut_fill_1ft.tif",
    "dem_context": "dem/dem_context_2p5ft.tif",
    "canon": "docs/DESIGN_CANON.md",
    "datum_note": "docs/datum_note.md",
    "decision_brief": "docs/HUMAN_DECISION_BRIEF.md",
    "tier_validation_memo": "analysis/tier_emission/TIER_EMISSION_VALIDATION.md",
}


def p(rel):
    return os.path.join(REPO, rel)


def sha12(rel):
    path = p(rel)
    if not os.path.exists(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:12]


def jload(rel):
    with open(p(rel)) as fh:
        return json.load(fh)


def rxy(x, y):
    """Project-CRS (EPSG:6494 intl ft) -> local feet about the bowl origin."""
    return [round(x - ORIGIN_X, 2), round(y - ORIGIN_Y, 2)]


def rings_of(geom):
    """All polygon parts of a (Multi)Polygon as [outer, hole, ...] ring lists."""
    if geom["type"] == "Polygon":
        polys = [geom["coordinates"]]
    elif geom["type"] == "MultiPolygon":
        polys = geom["coordinates"]
    else:
        return []
    return [[[rxy(x, y) for x, y in ring] for ring in poly] for poly in polys]


def centroid_of(geom):
    """Area centroid of the first outer ring (planning-grade label anchor).

    The shoelace terms are computed about the ring's first vertex: state-plane
    eastings here are ~1.9e7 ft, so raw cross products (~1e13) cancel away all
    but ~3 significant digits in float64 and the centroid lands far outside
    the polygon. Translating first keeps full precision.
    """
    ring = (geom["coordinates"][0] if geom["type"] == "Polygon"
            else geom["coordinates"][0][0])
    ox, oy = ring[0][0], ring[0][1]
    a = cx = cy = 0.0
    for p0, p1 in zip(ring, ring[1:]):
        x0, y0 = p0[0] - ox, p0[1] - oy
        x1, y1 = p1[0] - ox, p1[1] - oy
        cross = x0 * y1 - x1 * y0
        a += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross
    if abs(a) < 1e-9:
        xs = [pt[0] for pt in ring]
        ys = [pt[1] for pt in ring]
        return sum(xs) / len(xs), sum(ys) / len(ys)
    return cx / (3 * a) + ox, cy / (3 * a) + oy


NOW = _dt.datetime.now().astimezone().isoformat(timespec="seconds")

# ─────────────────────────────────────────────────────────────────────────────
# 1. Read sources
# ─────────────────────────────────────────────────────────────────────────────
treads_fc = jload(SRC["treads"])
zones_fc = jload(SRC["zones"])
site_fc = jload(SRC["site_context"])
views_fc = jload(SRC["viewpoints"])
mat_fc = jload(SRC["material_zones"])
stage_lineage_fc = jload(SRC["stage_lineage"])
validation = jload(SRC["validation"])
manifest = (jload(SRC["grading_manifest"])
            if os.path.exists(p(SRC["grading_manifest"])) else None)

with open(p(SRC["decision_table"])) as fh:
    decision_rows = list(csv.DictReader(fh))

per_band = {}
for rec in validation.get("per_band", []):
    sec, row = rec["band"].split(" r")
    per_band[(sec, int(row))] = rec

# ─────────────────────────────────────────────────────────────────────────────
# 2. Seating treads + per-row sightline status (computed, not asserted)
# ─────────────────────────────────────────────────────────────────────────────
treads = []
seats_nominal = 0
status_counts = {"pass": 0, "warn": 0, "fail": 0, "unknown": 0}
for f in treads_fc["features"]:
    pr = f["properties"]
    sec, row = pr["section"], pr["row"]
    seats = pr.get("seats_kept") or 0
    seats_nominal += seats
    band = per_band.get((sec, row))
    if band is None:
        status, fails, band_a = "unknown", ["no validation record"], None
    else:
        fails = band.get("fail_reasons") or []
        band_a = band.get("band_a")
        if band.get("pass_frac", 0) >= 1.0 and not fails:
            status = "pass"
        elif band.get("pass_frac", 0) >= 0.8:
            status = "warn"   # marginal bands (canon: within DEM noise / at gate ceiling)
        else:
            status = "fail"
    status_counts[status] += 1
    cx, cy = centroid_of(f["geometry"])
    treads.append({
        "section": sec, "row": row,
        "elev": pr["tread_elev_navd88"],
        "seats": seats, "band_a": band_a,
        "c_mm": pr.get("C_mm"),
        "sees_bay": pr.get("sees_bay"),
        "status": status, "fail_reasons": fails,
        "label_xy": rxy(cx, cy),
        "polys": rings_of(f["geometry"]),
    })

band_a_total = validation["banded"]["A"]

# ─────────────────────────────────────────────────────────────────────────────
# 3. Zones (stage, ADA, aisle, swales, cell, floor …) from bowl_zones
# ─────────────────────────────────────────────────────────────────────────────
ZONE_TIER = {  # rendering truth-tier; concept/schematic zones are illustrative
    "stage_core": ("stage", "provisional"),
    "stage_shoulder_left": ("stage", "provisional"),
    "stage_shoulder_right": ("stage", "provisional"),
    "cross_aisle": ("circulation", "source_of_truth"),
    "drainage_swale": ("drainage", "source_of_truth"),
    "treatment_cell_landscape": ("treatment_cell", "concept"),
    "orchestra_event_floor": ("event_floor", "concept"),
    "promenade_hinge": ("circulation", "source_of_truth"),
}
zones = []
for f in zones_fc["features"]:
    pr = f["properties"]
    zone = pr.get("zone", "")
    key = zone
    if key not in ZONE_TIER:
        continue
    group, tier = ZONE_TIER[key]
    elev = (pr.get("elev_navd88") or pr.get("grade_elev_navd88")
            or pr.get("bottom_navd88"))
    zones.append({
        "zone": zone, "name": pr.get("name", zone), "group": group,
        "tier": tier, "elev": elev,
        "cost_status": pr.get("cost_status"),
        "geometry_source": pr.get("geometry_source"),
        "note": pr.get("note"),
        "polys": rings_of(f["geometry"]),
    })

# human-scale references (calibrated schematic scale; heights exact in ft)
human_refs = {"humans": [], "dims": []}
if os.path.exists(p(SRC["human_refs"])):
    for f in jload(SRC["human_refs"])["features"]:
        pr = f["properties"]
        if "viewer" not in pr.get("view_context", ["viewer"]) \
                and pr["type"] == "human":
            continue                      # e.g. ambitious-option ref: boards only
        if pr["type"] == "human":
            x, y = f["geometry"]["coordinates"]
            human_refs["humans"].append({
                "id": pr["ref_id"], "posture": pr["posture"],
                "role": pr["role"], "h": pr["height_ft"],
                "eye": pr.get("eye_height_ft"),
                "xy": rxy(x, y), "z": pr["ground_elev_navd88"],
                "label": pr.get("label"),
                "note": pr.get("note"),
            })
        else:
            human_refs["dims"].append({
                "id": pr["ref_id"], "len": pr["length_ft"],
                "label": pr["label"], "z": pr["ground_elev_navd88"],
                "line": [rxy(x, y) for x, y in f["geometry"]["coordinates"]],
            })

# bay-view axis + focal point (lineage file also sources the inherited stage)
bay_axis = focal = None
for f in stage_lineage_fc["features"]:
    nm = f["properties"].get("name")
    if nm == "bay_view_axis":
        bay_axis = {
            "line": [rxy(x, y) for x, y in f["geometry"]["coordinates"]],
            "az_deg": f["properties"].get("az_deg"),
            "note": f["properties"].get("note"),
        }
    elif nm == "focal_point_stage_front":
        fx, fy = f["geometry"]["coordinates"]
        focal = {"xy": rxy(fx, fy),
                 "elev": f["properties"].get("elev_navd88"),
                 "audience_face_az_deg": f["properties"].get("audience_face_az_deg")}

# site context (truth flag per feature from its own `schematic` property)
site_ctx = []
for f in site_fc["features"]:
    pr = f["properties"]
    g = f["geometry"]
    item = {"kind": pr.get("kind"), "name": pr.get("name"),
            "schematic": bool(pr.get("schematic", False))}
    if g["type"] in ("Polygon", "MultiPolygon"):
        item["polys"] = rings_of(g)
    elif g["type"] == "LineString":
        item["lines"] = [[rxy(x, y) for x, y in g["coordinates"]]]
    elif g["type"] == "MultiLineString":
        item["lines"] = [[rxy(x, y) for x, y in ln] for ln in g["coordinates"]]
    else:
        continue
    site_ctx.append(item)

# ── ADA rebuild layers: nodes + concept routes + REJECTED legacy ──────────
ada_rebuild = {"label": "ADA route network — REBUILT 2026-06-12",
               "status": "ADA-compliant route concept pending civil/code "
                         "detailing",
               "routes": [], "landings": [], "nodes": [], "legacy": []}
if os.path.exists(p(SRC["ada_route"])):
    for f in jload(SRC["ada_route"])["features"]:
        pr = f["properties"]
        if pr.get("role") == "ada_route_concept":
            ada_rebuild["routes"].append({
                "name": pr["name"], "class": pr["class"],
                "length_ft": pr["length_ft"],
                "line": [rxy(x, y) for x, y in f["geometry"]["coordinates"]]})
        elif pr.get("role") == "landing":
            x, y = f["geometry"]["coordinates"]
            ada_rebuild["landings"].append({"xy": rxy(x, y),
                                            "route": pr["route"]})
if os.path.exists(p(SRC["ada_nodes"])):
    for f in jload(SRC["ada_nodes"])["features"]:
        x, y = f["geometry"]["coordinates"]
        ada_rebuild["nodes"].append({"name": f["properties"]["name"],
                                     "class": f["properties"]["class"],
                                     "xy": rxy(x, y)})
if os.path.exists(p(SRC["ada_legacy"])):
    for f in jload(SRC["ada_legacy"])["features"]:
        ada_rebuild["legacy"].append({
            "name": f["properties"].get("name"),
            "rejection": f["properties"].get("rejection"),
            "polys": rings_of(f["geometry"])})

# ─────────────────────────────────────────────────────────────────────────────
# 4. Terrain grids (real DEMs when present; labelled placeholder otherwise)
# ─────────────────────────────────────────────────────────────────────────────
def grid_from_raster(rel, step, fmt="u16", fill_voids=False):
    """Sample a GeoTIFF every `step` pixels -> quantized base64 grid dict.

    fill_voids: interpolate LiDAR nodata holes (GDAL fillnodata) so the render
    mesh is continuous, and ship a bit-packed `void_b64` mask of the filled
    cells so the viewer can tint them as interpolated, not measured.
    """
    import numpy as np
    import rasterio
    from rasterio.fill import fillnodata

    with rasterio.open(p(rel)) as r:
        full = r.read(1).astype("float64")
        nod = r.nodata
        res = r.res[0] * step
        x0, y1 = r.bounds.left, r.bounds.top
    void_full = (full == nod) if nod is not None else np.zeros(full.shape, bool)
    if fill_voids and void_full.any():
        # interpolate at full resolution, then decimate, so hole edges stay clean
        full = fillnodata(full, mask=~void_full, max_search_distance=400)
    arr = full[::step, ::step]
    void = void_full[::step, ::step]
    if nod is not None:
        arr = np.where(arr == nod, np.nan, arr)   # any residual unfilled cells
    ny, nx = arr.shape
    if fmt == "u16":
        zmin = float(np.nanmin(arr))
        scale = 0.02
        q = np.round((arr - zmin) / scale)
        q[~np.isfinite(q)] = 65535
        buf = q.clip(0, 65535).astype("<u2").tobytes()
    else:  # i8 (cut/fill, 0.1 ft steps, clamp ±12.7 ft)
        zmin, scale = 0.0, 0.1
        q = np.round(arr / scale)
        q[~np.isfinite(q)] = 0
        buf = q.clip(-127, 127).astype("i1").tobytes()
    out = {
        "nx": nx, "ny": ny, "res": res,
        # local coords of the NW grid corner; rows run north->south
        "x0": round(x0 - ORIGIN_X, 2), "y0": round(y1 - ORIGIN_Y, 2),
        "zmin": round(zmin, 3), "scale": scale, "fmt": fmt,
        "b64": base64.b64encode(buf).decode(),
        "source": rel, "sha256_12": sha12(rel),
    }
    if fill_voids and void.any():
        out["void_b64"] = base64.b64encode(np.packbits(void.ravel()).tobytes()).decode()
        out["void_frac"] = round(float(void.mean()), 4)
        out["void_note"] = ("LiDAR voids interpolated for display (GDAL fillnodata); "
                            "void cells flagged in void_b64 bitmask, not measured ground")
    return out


terrain = {"placeholder": False}
missing_rasters = [k for k in ("dem_existing", "dem_proposed", "dem_cutfill",
                               "dem_context") if not os.path.exists(p(SRC[k]))]
if not missing_rasters:
    terrain["existing"] = grid_from_raster(SRC["dem_existing"], 2, fill_voids=True)
    terrain["proposed"] = grid_from_raster(SRC["dem_proposed"], 2, fill_voids=True)
    terrain["cutfill"] = grid_from_raster(SRC["dem_cutfill"], 2, "i8")
    terrain["context"] = grid_from_raster(SRC["dem_context"], 2, fill_voids=True)
    terrain["label"] = ("LiDAR-derived DEM (USGS 2015 + eastern supplement), "
                        "planning grade — not a field survey; LiDAR voids "
                        f"(~{terrain['existing'].get('void_frac', 0)*100:.0f}% of design grid, "
                        "mostly east flank) interpolated for display and tinted in the viewer")
else:
    terrain["placeholder"] = True
    terrain["label"] = ("PLACEHOLDER TERRAIN — DEM rasters missing: "
                        + ", ".join(SRC[k] for k in missing_rasters))
    print(f"[build_truth_package] WARNING: {terrain['label']}", file=sys.stderr)

# DEM elevation lookup for computed camera presets
def dem_z(x_local, y_local, which="existing"):
    g = terrain.get(which)
    if not g:
        return None
    import numpy as np
    raw = base64.b64decode(g["b64"])
    arr = np.frombuffer(raw, dtype="<u2").reshape(g["ny"], g["nx"])
    col = int((x_local - g["x0"]) / g["res"])
    row = int((g["y0"] - y_local) / g["res"])
    if not (0 <= row < g["ny"] and 0 <= col < g["nx"]) or arr[row, col] == 65535:
        return None
    return g["zmin"] + float(arr[row, col]) * g["scale"]

# ─────────────────────────────────────────────────────────────────────────────
# 5. Camera presets (canonical viewpoints + computed seat-level stations)
# ─────────────────────────────────────────────────────────────────────────────
VIEW_MAP = {  # required preset id -> in-situ viewpoint name
    "stage_to_audience": "stage_looking_back_to_audience",
    "ada_cross_aisle": "ada_arrival_to_cross_aisle",
    "rim_overlook": "upper_rim_down_to_stage",
    "bay_view_axis": "mid_row_audience_to_bay",
}
views_by_name = {f["properties"]["name"]: f for f in views_fc["features"]}
presets = []


def preset_from_viewpoint(pid, label, vname):
    f = views_by_name[vname]
    pr = f["properties"]
    ex, ey = f["geometry"]["coordinates"]
    eye = rxy(ex, ey) + [pr["camera_elev_navd88"]]
    tgt = rxy(pr["look_target_x"], pr["look_target_y"]) + [pr["look_target_elev_navd88"]]
    presets.append({"id": pid, "name": label, "eye": eye, "target": tgt,
                    "desc": pr.get("description", ""),
                    "source": SRC["viewpoints"] + " :: " + vname})


def tread_station(section, row):
    t = next(t for t in treads if t["section"] == section and t["row"] == row)
    return t["label_xy"], t["elev"]


preset_from_viewpoint("stage_to_audience", "Stage → audience",
                      VIEW_MAP["stage_to_audience"])

xy, elev = tread_station("bend", 1)
fz = (focal["elev"] or 612.5) if focal else 612.5
presets.append({"id": "row1_to_stage", "name": "Row 1 → stage",
                "eye": [xy[0], xy[1], round(elev + 4.0, 2)],
                "target": [focal["xy"][0], focal["xy"][1], fz + 5.0],
                "desc": "seated eye (≈4 ft) on the bend row-1 tread, looking "
                        "at a performer at the stage-front focal point",
                "source": f"computed: {SRC['treads']} bend r1 centroid + "
                          f"{SRC['stage_lineage']} focal point"})

preset_from_viewpoint("ada_cross_aisle", "ADA cross-aisle",
                      VIEW_MAP["ada_cross_aisle"])

xy, elev = tread_station("south", 18)
presets.append({"id": "back_row", "name": "Back row (south r18)",
                "eye": [xy[0], xy[1], round(elev + 4.0, 2)],
                "target": [focal["xy"][0], focal["xy"][1], fz + 5.0],
                "desc": "seated eye on the south row-18 tread — the band that "
                        "sits 2 mm under the 90 mm C bar (WARN, within DEM noise)",
                "source": f"computed: {SRC['treads']} south r18 centroid"})

preset_from_viewpoint("rim_overlook", "Rim overlook", VIEW_MAP["rim_overlook"])
preset_from_viewpoint("bay_view_axis", "Bay-view axis", VIEW_MAP["bay_view_axis"])

# site overview: high SE of the bowl, looking down the bay-view azimuth
az = math.radians(BAY_VIEW_AZ)
back = 520.0
ovx = focal["xy"][0] - back * math.sin(az)
ovy = focal["xy"][1] - back * math.cos(az)
ovz = (dem_z(ovx, ovy) or fz) + 320.0
presets.insert(0, {"id": "site_overview", "name": "Site overview",
                   "eye": [round(ovx, 1), round(ovy, 1), round(ovz, 1)],
                   "target": [focal["xy"][0], focal["xy"][1], fz],
                   "desc": "aerial view aligned with the bay-view axis (az "
                           f"{BAY_VIEW_AZ:.0f}°)",
                   "source": "computed from focal point + bay-view azimuth"})

# ─────────────────────────────────────────────────────────────────────────────
# 6. Checks: pass / warn / fail / unknown — each with source provenance
# ─────────────────────────────────────────────────────────────────────────────
hard = validation.get("hard", {})
vols = validation.get("volumes", {})
ada = validation.get("ada", [])          # LEGACY (void for routes — kept for
                                          # cross-aisle band data only)
ada_rebuilt_valid = (jload(SRC["ada_validation"])
                     if os.path.exists(p(SRC["ada_validation"])) else {})
swales = validation.get("swales", [])
xaisle = validation.get("cross_aisle", {})

marginal = [f"{t['section']} r{t['row']}" for t in treads if t["status"] == "warn"]
failed = [f"{t['section']} r{t['row']}" for t in treads if t["status"] == "fail"]

checks = [
    {"id": "seats_nominal", "name": "Nominal seats (45 treads)",
     "status": "pass", "value": seats_nominal,
     "source": SRC["treads"], "note": "sum of per-tread seats_kept"},
    {"id": "seats_band_a", "name": "Strict Band-A seats (4-gate validated)",
     "status": "pass", "value": round(band_a_total),
     "source": SRC["validation"],
     "note": "Rule 4 gates (C≥90 mm, cross ≤2.5%, long ≤1.0%, surface) on the "
             "emitted surface"},
    {"id": "sightlines", "name": "Sightlines (per-row C, formal bowl)",
     "status": ("fail" if failed else ("warn" if marginal else "pass")),
     "value": f"{status_counts['pass']} pass / {status_counts['warn']} warn / "
              f"{status_counts['fail']} fail of {len(treads)} treads",
     "source": SRC["validation"],
     "note": "; ".join(filter(None, [
                 ("failed bands: " + ", ".join(failed) +
                  " — station C 2–7 mm under the 90 mm bar (canon Rule 8 note: "
                  "within DEM noise)") if failed else "",
                 ("marginal bands: " + ", ".join(marginal) +
                  " — at gate ceilings") if marginal else "",
             ])) or "all treads pass all four gates"},
    {"id": "ada_network", "name": "ADA route network (REBUILT: topology → "
                                   "conflicts → slopes)",
     "status": ("pass" if ada_rebuilt_valid.get("hard", {}).get("network_ok")
                else "fail"),
     "value": (f"{len(ada_rebuild['routes'])} routes / "
               f"{len(ada_rebuild['nodes'])} nodes; topology "
               f"{ada_rebuilt_valid.get('hard', {}).get('topology_ok')}, "
               f"conflicts {ada_rebuilt_valid.get('hard', {}).get('conflicts_ok')}, "
               f"slopes {ada_rebuilt_valid.get('hard', {}).get('slopes_ok')}"),
     "source": SRC["ada_validation"],
     "note": "concept pending civil/code detailing — legacy slope-only ADA "
             "fragments REJECTED 2026-06-12 (quarantined in "
             + SRC["ada_legacy"] + "); never described as ADA compliant"},
    {"id": "cross_aisle", "name": "Cross-aisle (rows 9/10 reclassification)",
     "status": "pass" if xaisle.get("wheelable") and xaisle.get("drains") else "warn",
     "value": f"datum {xaisle.get('datum')} ft, cross {xaisle.get('cross_slope_pct')}%, "
              f"long {xaisle.get('long_slope_pct')}%",
     "source": SRC["validation"], "note": "level, wheelable, drains"},
    {"id": "drainage", "name": "Flank swales fall toward treatment cell",
     "status": "pass" if swales and all(s.get("valid") for s in swales) else "unknown",
     "value": "; ".join(f"{s['name']} az {s['az_deg']}°" for s in swales) or None,
     "source": SRC["validation"], "note": "0 tread-conflict cells"},
    {"id": "bay_view", "name": "Bay view (mid/upper rows)",
     "status": "pass" if hard.get("bay_view_ok") else "unknown",
     "value": f"water plane {BAY_PLANE} ft NAVD88",
     "source": SRC["validation"],
     "note": "measured EPT: flat rim never blocks the bay for mid/upper rows; "
             "front/floor rows lose it inherently; foreground TREES govern — "
             "tree survey outstanding"},
    {"id": "earthwork", "name": "Earthwork (validated component proxy)",
     "status": "warn",
     "value": f"gross {vols.get('gross_cy')} CY (cut {vols.get('cut_cy')} / "
              f"fill {vols.get('fill_cy')}), LOD {vols.get('lod_ac')} ac",
     "source": SRC["validation"],
     "note": "component-sum proxy; mobilization-level quantities are KNOWN to "
             "be understated vs raster truth — see "
             + SRC["tier_validation_memo"]},
    {"id": "stage_rule9", "name": "Stage geometry / fan declaration (Rule 9)",
     "status": "fail",
     "value": "OPEN — inherited az-150 stage carried PROVISIONAL",
     "source": SRC["canon"],
     "note": "no adoption path (A/B/C/wide-fan) declared; stage shown for "
             "massing only; every stage-derived artifact re-emits on adoption"},
    {"id": "treatment_cell", "name": "Treatment cell preserved (dry bioretention)",
     "status": "pass" if hard.get("treatment_cell_preserved") else "unknown",
     "value": "never impounds permanent water",
     "source": SRC["validation"],
     "note": "cell SHAPING is concept-tier (schematic 4:1) — not geometry-backed"},
    {"id": "human_scale", "name": "Human-scale references (calibrated schematic)",
     "status": "pass" if human_refs["humans"] else "fail",
     "value": f"{len(human_refs['humans'])} figures "
              f"({sum(1 for h in human_refs['humans'] if h['posture'] == 'wheelchair')} wheelchair) "
              f"+ {len(human_refs['dims'])} dimensions in the viewer",
     "source": SRC["human_refs"],
     "note": "heights exact in data units (standing 5.0/5.75/6.25 ft; seated "
             "eye 3.94 ft = the C-value standard; wheelchair eye 3.90 ft); "
             "figure shapes schematic; placements anchored to governing layers"},
    {"id": "seating_scope", "name": "Seating scope decision (Decision 1)",
     "status": "warn",
     "value": "PENDING — " + " | ".join(
         f"{r['option']}: {r['label']} ({r['band_a_validated_seats']} Band-A)"
         for r in decision_rows),
     "source": SRC["decision_table"],
     "note": "viewer shows option A (Scenario E baseline); B/C are emitted+"
             "validated alternatives awaiting the human decision"},
]
for uid, uname in [
    ("groundwater", "Seasonal high groundwater"),
    ("geotech", "Geotechnical / bearing"),
    ("datum_delta", "IGLD85↔NAVD88 Δ confirmation (working +0.40 ft assumed)"),
    ("ada_full", "Full ADA/code compliance (built cross-slopes, handrails, clearances)"),
    ("egress", "Egress / life-safety capacity"),
    ("acoustics", "Stage acoustics (blocked on Rule 9)"),
    ("permits", "Permitting / zoning"),
    ("utilities", "Utility conflicts"),
    ("survey", "Survey-grade boundary + topo"),
    ("cost", "Construction cost estimate"),
    ("trees", "Tree survey (governs bay-view tuning)"),
]:
    checks.append({"id": uid, "name": uname, "status": "unknown", "value": None,
                   "source": "truth_package/data_inventory.md §7",
                   "note": "not derivable from current repo data"})

WARNINGS = [
    "PLANNING-GRADE ONLY — derived from 2015 USGS LiDAR + supplement; "
    "not a stamped engineering design and not a field survey.",
    "Stage deck is PROVISIONAL: DESIGN_CANON.md Rule 9 is OPEN (inherited "
    "az-150 stage; +25.6° audience-axis mismatch on record).",
    "Coordinates are EPSG:6494 INTERNATIONAL feet — misreading as US survey "
    "feet shifts absolute easting ~39 ft (docs/datum_note.md).",
    "Component CY totals are validated proxies that understate "
    "mobilization-level earthwork (analysis/tier_emission/TIER_EMISSION_VALIDATION.md).",
    "Seating scope Decision 1 is pending; this package shows the Scenario E "
    "baseline (option A).",
    "Treatment-cell shaping and orchestra/event floor are concept-tier "
    "(illustrative), not geometry-backed.",
]
if terrain["placeholder"]:
    WARNINGS.insert(0, terrain["label"])

sources_block = {k: {"path": v, "sha256_12": sha12(v),
                     "present": os.path.exists(p(v))}
                 for k, v in sorted(SRC.items())}

# ─────────────────────────────────────────────────────────────────────────────
# 7. truth_package/design_state.current.json
# ─────────────────────────────────────────────────────────────────────────────
sections = {}
for t in treads:
    s = sections.setdefault(t["section"], {"treads": 0, "seats_nominal": 0,
                                           "rows": []})
    s["treads"] += 1
    s["seats_nominal"] += t["seats"]
    s["rows"].append(t["row"])
for s in sections.values():
    s["rows"] = sorted(set(s["rows"]))

design_state = {
    "schema": "truthful-terrain/design-state/0.1",
    "generated": NOW,
    "generator": "scripts/build_truth_package.py",
    "project": "Petoskey Pit amphitheatre — Open Civic Bowl (in-situ package)",
    "design_of_record": {
        "scenario": "Scenario E three-section civic bowl (east/bend/south) "
                    "on the Scenario D restored baseline",
        "status": "seating / ADA / drainage cost-proxy ACCEPTED · stage refit OPEN (Rule 9)",
        "authority": [SRC["canon"], "INEVITABILITY.md", "SCENARIO_E_CIVIC.md"],
        "constants_source": _CONST_SOURCE,
    },
    "crs": {
        "horizontal": "EPSG:6494 NAD83(2011) / Michigan Central, INTERNATIONAL feet",
        "vertical": "NAVD88 (Geoid12A), international feet",
        "local_origin_epsg6494_ft": [ORIGIN_X, ORIGIN_Y],
        "igld85_delta_ft": {"value": 0.40, "status": "ASSUMED — unconfirmed",
                            "source": SRC["datum_note"]},
    },
    "elements": {
        "seating": {
            "kind": "terraced treads, three terrain-fitted sections",
            "sections": sections,
            "treads_total": len(treads),
            "seats_nominal": seats_nominal,
            "seats_band_a_validated": round(band_a_total),
            "rows_absent": [5, 9, 10],
            "rows_absent_reason": "row 5 = promenades; rows 9/10 reclassified "
                                  "as the accessible cross-aisle",
            "source": [SRC["treads"], SRC["validation"]],
            "truth_tier": "source_of_truth",
        },
        "stage": {
            "kind": "low hardscape deck + shoulders (open to bay side, no "
                    "upstage wall — landscape venue)",
            "elev_navd88": next((z["elev"] for z in zones
                                 if z["zone"] == "stage_core"), None),
            "geometry_source": "scenarioE stage_surface (inherited from "
                               "design_open_low, az 150)",
            "status": "PROVISIONAL — Rule 9 OPEN; no adoption path declared",
            "source": [SRC["zones"], SRC["stage_lineage"], SRC["canon"]],
            "truth_tier": "provisional",
        },
        "ada_route": {
            "kind": "REBUILT node-to-node accessible network: rim arrival + "
                    "south egress + cross-aisle + floor + wheelchair "
                    "clusters + classified service spur",
            "status": "ADA-compliant route concept pending civil/code "
                      "detailing — topology, conflicts and slopes validated; "
                      "code details explicitly unchecked",
            "legacy": "2026-06-12: legacy scenarioE ada_ramp/landing REJECTED "
                      "(disconnected fragments; route A 63% in treatment "
                      "cell; route B crossed swale short of the cross-aisle) "
                      "— quarantined in " + SRC["ada_legacy"],
            "validation": ada_rebuilt_valid.get("hard"),
            "source": [SRC["ada_nodes"], SRC["ada_route"],
                       SRC["ada_validation"]],
            "truth_tier": "concept",
        },
        "cross_aisle": {
            "kind": "rows 9/10 reclassified as level accessible cross-aisle",
            "validation": xaisle,
            "source": [SRC["zones"], SRC["validation"]],
            "truth_tier": "source_of_truth",
        },
        "drainage": {
            "kind": "east + south flank swales falling to the treatment cell",
            "validation": swales,
            "source": [SRC["zones"], SRC["validation"]],
            "truth_tier": "source_of_truth",
        },
        "treatment_cell": {
            "kind": "dry ephemeral bioretention landscape (natural bowl bottom)",
            "bottom_navd88": next((z["elev"] for z in zones
                                   if z["zone"] == "treatment_cell_landscape"),
                                  None),
            "shaping": "concept tier — schematic 4:1, down-only, never "
                       "impounds permanent water",
            "source": [SRC["zones"], "package/07_stormwater/treatment_train.geojson"],
            "truth_tier": "concept",
        },
        "bay_view_axis": {
            "az_deg": bay_axis["az_deg"] if bay_axis else BAY_VIEW_AZ,
            "water_plane_navd88": BAY_PLANE,
            "source": [SRC["stage_lineage"]],
            "truth_tier": "source_of_truth",
            "note": bay_axis.get("note") if bay_axis else None,
        },
        "event_floor": {
            "kind": "orchestra/event floor between stage and row 1",
            "truth_tier": "concept",
            "source": [SRC["zones"]],
        },
    },
    "pending_decisions": [{
        "id": "decision_1_seating_scope",
        "options": decision_rows,
        "source": [SRC["decision_table"], SRC["decision_brief"]],
        "shown_in_viewer": "option A (Scenario E baseline)",
    }],
    "warnings": WARNINGS,
    "missing_data": [c["name"] for c in checks if c["status"] == "unknown"],
    "sources": sources_block,
}

# ─────────────────────────────────────────────────────────────────────────────
# 8. truth_package/evaluation_report.current.json
# ─────────────────────────────────────────────────────────────────────────────
evaluation_report = {
    "schema": "truthful-terrain/evaluation-report/0.1",
    "generated": NOW,
    "generator": "scripts/build_truth_package.py",
    "design_state_ref": "truth_package/design_state.current.json",
    "summary": {
        "seats_nominal": seats_nominal,
        "seats_band_a_validated": round(band_a_total),
        "tread_status_counts": status_counts,
        "earthwork_gross_cy_component_proxy": vols.get("gross_cy"),
        "stage": "Rule 9 OPEN (provisional)",
        "decision_1": "PENDING (viewer shows option A)",
    },
    "checks": checks,
    "per_row_c_mm": validation.get("c_rows"),
    "volumes": vols,
    "warnings": WARNINGS,
    "unknowns": [c["name"] for c in checks if c["status"] == "unknown"],
    "sources": sources_block,
}

# ─────────────────────────────────────────────────────────────────────────────
# 9. truth_package/export_manifest.json  (contract only — not implemented)
# ─────────────────────────────────────────────────────────────────────────────
export_manifest = {
    "schema": "truthful-terrain/export-manifest/0.1",
    "generated": NOW,
    "note": "Contract for FUTURE handoffs. Only targets marked implemented "
            "exist today. Every export must carry the design_state warnings "
            "block — exports that strip the planning-grade caveats are "
            "non-conforming.",
    "targets": [
        {"id": "web_viewer", "format": "static HTML + Three.js",
         "status": "implemented", "path": "web_viewer/index.html",
         "consumers": ["public presentation", "GitHub Pages"]},
        {"id": "truth_json", "format": "design_state + evaluation_report JSON",
         "status": "implemented", "path": "truth_package/",
         "consumers": ["audit", "downstream agents"]},
        {"id": "geojson_gis", "format": "GeoJSON (EPSG:6494) per layer",
         "status": "exists_in_repo", "path": "vectors_geojson/",
         "consumers": ["QGIS (qgis/in_situ_package.qgs)", "GIS review"]},
        {"id": "geopackage", "format": "GeoPackage (single-file GIS handoff)",
         "status": "planned",
         "inputs": ["vectors_geojson/*.geojson"],
         "note": "ogr2ogr one-liner per layer; carry CRS + datum metadata"},
        {"id": "gltf", "format": "glTF/GLB (terrain mesh + design layers)",
         "status": "planned",
         "inputs": ["dem/*.tif", "vectors_geojson/*.geojson"],
         "consumers": ["Cesium", "Twinmotion", "Unreal", "Blender"],
         "note": "reuse the viewer's mesh builder; bake truth-tier into "
                 "material/extras so provisional layers stay marked"},
        {"id": "landxml", "format": "LandXML surfaces (existing + proposed)",
         "status": "planned_if_feasible",
         "inputs": ["dem/dem_design_1ft.tif", "dem/proposed_grade_1ft.tif"],
         "consumers": ["Civil 3D", "OpenSite"],
         "note": "TIN from grid; planning-grade flag in project metadata"},
        {"id": "audit_csv", "format": "CSV/JSON audit reports",
         "status": "exists_in_repo",
         "path": "analysis/tier_emission/Scenario_E_baseline_reemit/",
         "consumers": ["engineering review"]},
        {"id": "pdf_exhibits", "format": "PDF boards/exhibits",
         "status": "planned",
         "inputs": ["boards/*.png", "truth_package/*.json"],
         "consumers": ["council packet", "public meeting"]},
    ],
}

# ─────────────────────────────────────────────────────────────────────────────
# 10. Write outputs
# ─────────────────────────────────────────────────────────────────────────────
os.makedirs(p("truth_package"), exist_ok=True)
os.makedirs(p("web_viewer/data"), exist_ok=True)

with open(p("truth_package/design_state.current.json"), "w") as fh:
    json.dump(design_state, fh, indent=1)
with open(p("truth_package/evaluation_report.current.json"), "w") as fh:
    json.dump(evaluation_report, fh, indent=1)
with open(p("truth_package/export_manifest.json"), "w") as fh:
    json.dump(export_manifest, fh, indent=1)

site_data = {
    "meta": {
        "generated": NOW,
        "title": "Petoskey Pit — Open Civic Bowl",
        "origin_epsg6494_ft": [ORIGIN_X, ORIGIN_Y],
        "crs": "EPSG:6494 intl ft · NAVD88 (Geoid12A) intl ft",
        "bay_view_az": BAY_VIEW_AZ,
        "bay_plane_navd88": BAY_PLANE,
        "disclaimer": WARNINGS[0],
        "warnings": WARNINGS,
    },
    "terrain": terrain,
    "layers": {
        "treads": treads,
        "zones": zones,
        "bay_axis": bay_axis,
        "focal": focal,
        "site_context": site_ctx,
        "human_refs": human_refs,
        "ada_rebuild": ada_rebuild,
    },
    "presets": presets,
    "audit": {
        "checks": [{k: c[k] for k in ("id", "name", "status", "value", "note",
                                      "source")} for c in checks],
        "layer_truth": [
            {"layer": "Terrain (existing / proposed)",
             "tier": "placeholder" if terrain["placeholder"] else "source_of_truth",
             "source": terrain["label"]},
            {"layer": "Seating treads + sightline status",
             "tier": "source_of_truth", "source": SRC["treads"]},
            {"layer": "Cross-aisle, swales", "tier": "source_of_truth",
             "source": SRC["zones"]},
            {"layer": "ADA route network (rebuilt)", "tier": "concept",
             "source": SRC["ada_route"] + " — pending civil/code detailing"},
            {"layer": "Legacy ADA fragments", "tier": "rejected",
             "source": SRC["ada_legacy"] + " — REJECTED 2026-06-12, shown "
                       "only as quarantined history"},
            {"layer": "Stage deck", "tier": "provisional",
             "source": "inherited az-150 stage — Rule 9 OPEN"},
            {"layer": "Treatment cell, event floor", "tier": "concept",
             "source": SRC["zones"]},
            {"layer": "Bay-view axis", "tier": "source_of_truth",
             "source": SRC["stage_lineage"]},
            {"layer": "Site context (paths, rim, trees)", "tier": "mixed",
             "source": SRC["site_context"] + " (per-feature schematic flag)"},
            {"layer": "Row labels / annotations", "tier": "illustrative",
             "source": "generated from tread centroids"},
            {"layer": "Human-scale refs (figures + dimensions)",
             "tier": "source_of_truth",
             "source": SRC["human_refs"] + " (heights/positions data-backed; "
                       "figure shapes schematic)"},
        ],
        "missing": [c["name"] for c in checks if c["status"] == "unknown"],
        "pending": design_state["pending_decisions"][0],
        "sources": sources_block,
    },
}

with open(p("web_viewer/data/site_data.js"), "w") as fh:
    fh.write("// GENERATED by scripts/build_truth_package.py — do not edit.\n")
    fh.write("// Local coords: feet about EPSG:6494 origin "
             f"({ORIGIN_X}, {ORIGIN_Y}); z = NAVD88 ft.\n")
    fh.write("window.SITE_DATA = ")
    json.dump(site_data, fh, separators=(",", ":"))
    fh.write(";\n")

sz = os.path.getsize(p("web_viewer/data/site_data.js"))
print(f"truth_package written: design_state, evaluation_report, export_manifest")
print(f"web_viewer/data/site_data.js: {sz/1e6:.2f} MB "
      f"({'PLACEHOLDER terrain' if terrain['placeholder'] else 'real DEM terrain'})")
print(f"seats: nominal {seats_nominal}, Band-A {round(band_a_total)}; "
      f"treads {status_counts}")
checks_by = {}
for c in checks:
    checks_by[c["status"]] = checks_by.get(c["status"], 0) + 1
print(f"checks: {checks_by}")
