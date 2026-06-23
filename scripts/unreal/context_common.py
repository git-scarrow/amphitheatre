#!/usr/bin/env python3
"""Shared contract for the CivicBowl UE 5.8 *context + horizon* layer (v0).

This is the geographic-context companion to ``civicbowl_common.py``. It adds
**approximate, clearly-labeled** scenery around the audited Petoskey Pit bowl —
Little Traverse Bay, a horizon reference, optional open-data city massing, and a
calculated sunset sun/sky — so the scene can be reviewed at human / civic scale.

Hard separation from the audited design path (this is the whole point):

  * The audited design geometry (``civicbowl_common.SCENE_SPEC``,
    ``gen_review_meshes.py``, ``scene_plan.json``) is **NOT touched** by anything
    here. Its determinism hash and its verifier gates are unchanged.
  * Context actors live under their own Outliner root (``Context/``), which is
    asserted DISJOINT from every design folder root. The design verifier's
    group-count gates therefore never see a context actor.
  * Every context layer must DECLARE its provenance in
    ``data/unreal_context_manifest.json`` (source, source_type, accuracy_class,
    redistributable, intended_use, included_in_verification). Context never
    contributes to a design-count gate unless a layer explicitly opts in with
    ``included_in_verification: true`` — none do in v0.

Pure stdlib (no shapely/trimesh/unreal) so it imports anywhere. The solar
position is a *real* NOAA calculation (not a guessed atmospheric value), so the
sunset orientation is a computed azimuth/elevation, labeled as such.
"""
from __future__ import annotations

import datetime as dt
import math
import os

import civicbowl_common as cb  # design contract (frame, ENU->UE, SCENE_SPEC)

# ── site location ────────────────────────────────────────────────────────────
# Derived ONCE from the EPSG:6494 local origin via pyproj
# (EPSG:6494 -> EPSG:4326, always_xy); recorded here as a constant so the solar
# calc needs no GIS deps. Provenance lives in data/unreal_context_manifest.json.
SITE_LAT = 45.374552          # deg N  (Petoskey, MI — bowl local origin)
SITE_LON = -84.958053         # deg E
SITE_TZ_OFFSET_H = -4         # EDT (summer); display only, never used in the calc

# ── bay / horizon datums ─────────────────────────────────────────────────────
# Little Traverse Bay water-surface elevation: MEASURED via the EPT viewshed
# analysis (see scripts/build_site_context.py:95 "water plane 579.45"). The
# *elevation* is measured; the planar EXTENT we draw for it is a simplified proxy.
WATER_ELEV_NAVD88_FT = 579.45
WATER_ELEV_M = cb.ft_z_to_m(WATER_ELEV_NAVD88_FT)   # ~176.62 m local-z
# NW rim crest (reference only; "flat 618-ft rim" per the bay-view memo).
RIM_ELEV_NAVD88_FT = 618.0

# Simplified bay-plane extent (local ENU metres). North/NNW of the site; the near
# edge is kept well beyond the bowl so the water surface never intrudes on the
# audited seating geometry. Shared by gen_context (draws it) + verify_context
# (uses the near edge as the bay sightline target).
BAY_NEAR_N_M = 150.0
BAY_FAR_N_M = 3500.0
BAY_HALF_E_M = 2000.0

# ── context Outliner root (MUST be disjoint from design roots) ───────────────
CONTEXT_FOLDER_ROOT = "Context"
CONTEXT_MANIFEST = "data/unreal_context_manifest.json"
CONTEXT_PLAN = "context_plan.json"   # sibling of scene_plan.json in build dir

# Required provenance fields every context layer must declare (Task 1 schema).
REQUIRED_LAYER_FIELDS = (
    "layer_name",
    "source",
    "source_type",            # measured | public GIS | OSM | LiDAR-derived | inferred | atmospheric
    "accuracy_class",
    "redistributable",        # bool
    "intended_use",           # audit | review | cinematic | reference
    "included_in_verification",  # bool — design-count contribution (false in v0)
)
VALID_SOURCE_TYPES = {
    "measured", "public GIS", "OSM", "LiDAR-derived", "inferred", "atmospheric", "derived",
}
VALID_INTENDED_USE = {"audit", "review", "cinematic", "reference"}


# ── design-path disjointness guard ───────────────────────────────────────────
def design_folder_roots() -> set[str]:
    """The top-level Outliner roots owned by the AUDITED design (SCENE_SPEC)."""
    return {g["folder"].split("/")[0] for g in cb.SCENE_SPEC.values()}


def assert_disjoint_from_design() -> None:
    """Fail loudly if the context root ever collides with a design root — the
    invariant that keeps context out of the design-count gates."""
    if CONTEXT_FOLDER_ROOT in design_folder_roots():
        raise AssertionError(
            f"context root {CONTEXT_FOLDER_ROOT!r} collides with a design root "
            f"{sorted(design_folder_roots())} — context would contaminate the "
            f"audited group gates")


# ── manifest loader + validation ─────────────────────────────────────────────
def load_context_manifest(root: str) -> dict:
    return cb.load_json(os.path.join(root, CONTEXT_MANIFEST))


def validate_manifest(man: dict) -> list[str]:
    """Return a list of human-readable problems (empty == valid)."""
    problems: list[str] = []
    layers = man.get("layers")
    if not isinstance(layers, list) or not layers:
        return ["manifest has no 'layers' list"]
    for i, layer in enumerate(layers):
        nm = layer.get("layer_name", f"#{i}")
        for f in REQUIRED_LAYER_FIELDS:
            if f not in layer:
                problems.append(f"{nm}: missing required field '{f}'")
        st = layer.get("source_type")
        if st is not None and st not in VALID_SOURCE_TYPES:
            problems.append(f"{nm}: source_type {st!r} not in {sorted(VALID_SOURCE_TYPES)}")
        iu = layer.get("intended_use")
        if iu is not None and iu not in VALID_INTENDED_USE:
            problems.append(f"{nm}: intended_use {iu!r} not in {sorted(VALID_INTENDED_USE)}")
        for b in ("redistributable", "included_in_verification"):
            if b in layer and not isinstance(layer[b], bool):
                problems.append(f"{nm}: field '{b}' must be a bool")
        if layer.get("redistributable") is False:
            problems.append(f"{nm}: redistributable=false — must NOT be committed/built")
    return problems


def layer_by_name(man: dict, name: str) -> dict | None:
    return next((l for l in man.get("layers", []) if l.get("layer_name") == name), None)


# ── real solar position (NOAA spreadsheet algorithm; stdlib only) ────────────
def solar_position(lat: float, lon: float, when_utc: dt.datetime) -> dict:
    """Sun azimuth (deg cw from true North) + elevation for a UTC instant.

    NOAA solar-position algorithm (the published 'NOAA_Solar_Calculations'
    spreadsheet). Accuracy ~0.01 deg for these dates — good enough that the
    sunset orientation is a *computed* value, not an eyeballed atmospheric guess.
    Atmospheric refraction (Saemundsson) is applied to give apparent elevation.
    """
    y, mo, d = when_utc.year, when_utc.month, when_utc.day
    h = when_utc.hour + when_utc.minute / 60 + when_utc.second / 3600
    if mo <= 2:
        y -= 1; mo += 12
    A = y // 100; B = 2 - A + A // 4
    jd = math.floor(365.25 * (y + 4716)) + math.floor(30.6001 * (mo + 1)) + d + B - 1524.5 + h / 24
    T = (jd - 2451545.0) / 36525.0
    L0 = (280.46646 + T * (36000.76983 + T * 0.0003032)) % 360
    M = 357.52911 + T * (35999.05029 - 0.0001537 * T)
    e = 0.016708634 - T * (0.000042037 + 0.0000001267 * T)
    Mr = math.radians(M)
    C = ((1.914602 - T * (0.004817 + 0.000014 * T)) * math.sin(Mr)
         + (0.019993 - 0.000101 * T) * math.sin(2 * Mr)
         + 0.000289 * math.sin(3 * Mr))
    omega = 125.04 - 1934.136 * T
    lam = L0 + C - 0.00569 - 0.00478 * math.sin(math.radians(omega))
    eps = (23 + (26 + ((21.448 - T * (46.815 + T * (0.00059 - T * 0.001813)))) / 60) / 60
           + 0.00256 * math.cos(math.radians(omega)))
    decl = math.degrees(math.asin(math.sin(math.radians(eps)) * math.sin(math.radians(lam))))
    y_ = math.tan(math.radians(eps) / 2) ** 2
    L0r = math.radians(L0)
    eot = 4 * math.degrees(
        y_ * math.sin(2 * L0r) - 2 * e * math.sin(Mr)
        + 4 * e * y_ * math.sin(Mr) * math.cos(2 * L0r)
        - 0.5 * y_ * y_ * math.sin(4 * L0r) - 1.25 * e * e * math.sin(2 * Mr))
    tst = (h * 60 + eot + 4 * lon) % 1440
    ha = tst / 4 - 180 if tst / 4 >= 0 else tst / 4 + 180
    latr = math.radians(lat); declr = math.radians(decl); har = math.radians(ha)
    cz = max(-1.0, min(1.0,
             math.sin(latr) * math.sin(declr) + math.cos(latr) * math.cos(declr) * math.cos(har)))
    zen = math.degrees(math.acos(cz)); el = 90 - zen
    den = math.cos(latr) * math.sin(math.radians(zen))
    if abs(den) > 1e-9:
        ca = max(-1.0, min(1.0,
              (math.sin(latr) * math.cos(math.radians(zen)) - math.sin(declr)) / den))
        az_core = math.degrees(math.acos(ca))
        az = (az_core + 180) % 360 if ha > 0 else (540 - az_core) % 360
    else:
        az = 180.0
    refr = (1.02 / math.tan(math.radians(el + 10.3 / (el + 5.11))) / 60) if -1 < el < 85 else 0.0
    return {
        "azimuth_deg": round(az, 3),
        "elevation_true_deg": round(el, 3),
        "elevation_apparent_deg": round(el + refr, 3),
        "declination_deg": round(decl, 3),
    }


def find_sun_event(date_local: dt.date, target_apparent_el: float,
                   lat: float = SITE_LAT, lon: float = SITE_LON,
                   tz_offset_h: int = SITE_TZ_OFFSET_H) -> dict | None:
    """Afternoon instant when apparent elevation first drops to ``target`` deg.

    Scans 1-minute steps from local noon. Returns the UTC + local time and the
    full solar_position dict. ``target = -0.833`` is the standard sunset
    (apparent solar disc centre with refraction); ``+5`` ~ golden hour.
    """
    start_utc = dt.datetime(date_local.year, date_local.month, date_local.day, 12, 0) \
        - dt.timedelta(hours=tz_offset_h)
    for m in range(0, 18 * 60):
        t = start_utc + dt.timedelta(minutes=m)
        sp = solar_position(lat, lon, t)
        if sp["azimuth_deg"] > 180 and sp["elevation_apparent_deg"] <= target_apparent_el:
            local = t + dt.timedelta(hours=tz_offset_h)
            return {
                "utc": t.strftime("%Y-%m-%dT%H:%MZ"),
                "local": local.strftime("%Y-%m-%dT%H:%M"),
                "tz": f"UTC{tz_offset_h:+d} (EDT)",
                **sp,
            }
    return None


# Named solar references the gen/verify both resolve (deterministic — the dates
# are fixed constants; the times/angles are computed, not hand-entered).
SOLAR_EVENTS = {
    "summer_solstice_sunset_2026": {"date": dt.date(2026, 6, 21), "target_el": -0.833,
                                    "label": "Summer solstice sunset, Petoskey MI"},
    "midsummer_concert_sunset_2026": {"date": dt.date(2026, 8, 15), "target_el": -0.833,
                                      "label": "Mid-August evening concert sunset, Petoskey MI"},
}


def resolve_solar_events() -> dict:
    out = {}
    for key, spec in SOLAR_EVENTS.items():
        ev = find_sun_event(spec["date"], spec["target_el"])
        out[key] = {"label": spec["label"], "date": spec["date"].isoformat(),
                    "target_apparent_el_deg": spec["target_el"], **(ev or {})}
    return out


# ── bay-view corridor (for the obstruction gate) ─────────────────────────────
def bay_view_axis_enu(root: str) -> tuple[tuple[float, float], tuple[float, float]] | None:
    """The audited bay-view axis endpoints in local ENU metres (read, not drawn)."""
    feats = cb.geojson_features(os.path.join(root, "unreal_export/geo/stage_floor.geojson"))
    axis = next((f for f in feats if cb.feature_id(f) == "lineage_bay_view_axis"), None)
    if not axis:
        return None
    c0 = axis["geometry"]["coordinates"][0]
    c1 = axis["geometry"]["coordinates"][-1]
    return cb.ft_xy_to_enu(c0[0], c0[1]), cb.ft_xy_to_enu(c1[0], c1[1])


def corridor_geometry(root: str) -> dict | None:
    """Bay-view corridor as an origin + unit direction (bay side) + half-width.

    The corridor is the strip within ``half_width_m`` of the axis line, on the
    NNW (bay) side of the stage focal point. An occluder whose footprint falls in
    the strip AND whose top rises above the eye->bay sightline obstructs the view.
    """
    ax = bay_view_axis_enu(root)
    if not ax:
        return None
    (e0, n0), (e1, n1) = ax
    de, dn = e1 - e0, n1 - n0
    L = math.hypot(de, dn)
    if L < 1e-6:
        return None
    ue_dir = (de / L, dn / L)   # points toward the bay (NNW)
    return {
        "origin_enu_m": [e0, n0],
        "dir_to_bay": list(ue_dir),
        "azimuth_deg": (math.degrees(math.atan2(ue_dir[0], ue_dir[1])) + 360) % 360,
        "half_width_m": 60.0,    # generous v0 corridor half-width
    }
