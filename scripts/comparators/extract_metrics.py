#!/usr/bin/env python3
"""Compute the comparator metric set for all three sites with explicit
basis labels on every value:

  measured_dem      — read from the 1 m USGS DEM (comparators) or the repo's
                      design rasters/vectors (Petoskey)
  inferred_imagery  — digitized from Esri imagery / OSM footprints (never
                      presented as measured)
  published         — venue/press/Wikipedia figures with URL
  canon             — Petoskey repo canon (truth_package / in_situ_common)

Petoskey source geometry is READ ONLY here — nothing in the repo canon is
modified.

Outputs:
  data/comparators/<slug>/derived/site_metrics.json
  data/comparators/petoskey_metrics.json
  data/comparators/comparison.json
Reproduce:  .venv/bin/python scripts/comparators/extract_metrics.py
"""
import csv
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from sites import SITES, US_FT_PER_M

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))


def V(value, basis, note=None, **kw):
    d = {"value": value, "basis": basis}
    if note:
        d["note"] = note
    d.update(kw)
    return d


def load_profile(slug):
    s, z = [], []
    p = os.path.join(ROOT, "data", "comparators", slug, "derived",
                     "centerline_section.csv")
    with open(p) as f:
        for row in csv.DictReader(f):
            if row["z_ft_navd88"]:
                s.append(float(row["s_ft"]))
                z.append(float(row["z_ft_navd88"]))
    return np.array(s), np.array(z)


def zat(s, z, target):
    return float(np.interp(target, s, z))


def comparator_metrics(slug):
    site = SITES[slug]
    sd = os.path.join(ROOT, "data", "comparators", slug)
    cfg = json.load(open(os.path.join(sd, "site_config.json")))
    prov = json.load(open(os.path.join(sd, "dem", "provenance.json")))
    s, z = load_profile(slug)

    b = cfg["breaks_ft"]
    s_row1, s_top = b["row1_s"], b["seating_top_s"]
    z_floor = zat(s, z, 2.0)
    z_row1 = zat(s, z, s_row1)
    z_top = zat(s, z, s_top)
    rise = z_top - z_row1
    avg_rake = rise / (s_top - s_row1)

    # local rake range over 20-ft windows inside the seating zone
    rakes = []
    for a in np.arange(s_row1, s_top - 20, 5):
        m = (s >= a) & (s <= a + 20)
        if m.sum() > 5:
            rakes.append(np.polyfit(s[m], z[m], 1)[0])
    arc = json.load(open(os.path.join(sd, "derived", "arc_fit.json")))
    fan_w = arc["fan_angle_measured_deg"]
    frontage = cfg["stage_frontage_ft"]
    row1_arc_ft = math.radians(fan_w) * s_row1

    dem = site["dem_product"]
    m = {
        "site": site["name"],
        "slug": slug,
        "location": site["location"],
        "crs": prov["native_crs"] + " (m), vertical NAVD88 m -> reported ft",
        "dem": V(f"{dem['title']} ({dem['resolution_m']} m)", "published",
                 url=dem["url"], acquisition=dem["lidar_acquisition"]),
        "capacity": V(site["facts_published"]["capacity"], "published",
                      source=site["facts_published"]["capacity_source"]),
        "audience_facing_az_deg": V(cfg["audience_facing_azimuth_deg"],
                                    "inferred_imagery",
                                    "from OSM stage rectangle orientation + "
                                    "seating side; consistent w/ DEM fall line"),
        "stage_frontage_ft": V(frontage["value"], "inferred_imagery",
                               frontage["_basis"], range=frontage["range"]),
        "stage_depth_ft": V(cfg["stage_depth_ft"]["value"], "inferred_imagery",
                            cfg["stage_depth_ft"]["_basis"],
                            range=cfg["stage_depth_ft"]["range"]),
        "stage_front_to_row1_ft": V(round(s_row1, 1), "measured_dem",
                                    b["_basis"]),
        "floor_elev_ft": V(round(z_floor, 1), "measured_dem"),
        "row1_elev_ft": V(round(z_row1, 1), "measured_dem"),
        "top_row_elev_ft": V(round(z_top, 1), "measured_dem"),
        "rise_row1_to_top_ft": V(round(rise, 1), "measured_dem"),
        "avg_rake_pct": V(round(avg_rake * 100, 1), "measured_dem"),
        "local_rake_range_pct": V([round(min(rakes) * 100, 1),
                                   round(max(rakes) * 100, 1)],
                                  "measured_dem", "20-ft windows on centerline"),
        "fan_angle_deg": V(fan_w, "measured_dem",
                           arc["fan_basis"] + " (anchor center inferred); "
                           f"imagery read was "
                           f"{(cfg['fan_deg']['end_az']-cfg['fan_deg']['start_az'])%360} deg"),
        "inner_radius_ft": V(round(s_row1, 1), "measured_dem",
                             "row-1 distance from stage-front arc center; "
                             "contour check r(row1+2ft) = "
                             f"{arc['radii_ft'].get('row1',{}).get('median')} ft"),
        "outer_radius_ft": V(round(s_top, 1), "measured_dem",
                             "top-of-seating distance on centerline; contour "
                             "check r(top-2ft) = "
                             f"{arc['radii_ft'].get('top',{}).get('median')} ft"),
        "upper_row_distance_ft": V(round(s_top, 1), "measured_dem",
                                   "stage front -> top seating row, on axis"),
        "row1_arc_length_ft": V(round(row1_arc_ft, 1), "measured_dem",
                                "measured fan x row-1 radius (anchor center "
                                "inferred)"),
        "frontage_to_row1_arc": V(round(frontage["value"] / row1_arc_ft, 2),
                                  "inferred_imagery",
                                  "frontage is the inferred quantity"),
        "row_count_est": V(cfg["row_count_inferred"]["value"],
                           "inferred_imagery",
                           cfg["row_count_inferred"]["_basis"]),
        "ada": V(cfg["ada_circulation_note"], "inferred_imagery"),
        "backdrop": V(cfg["backdrop_note"], "inferred_imagery"),
    }
    out = os.path.join(sd, "derived", "site_metrics.json")
    json.dump(m, open(out, "w"), indent=1)
    print("wrote", out)
    return m


def petoskey_metrics():
    """Read-only extraction from repo canon (Scenario E in-situ package)."""
    treads = json.load(open(os.path.join(ROOT, "vectors_geojson",
                                         "terrace_treads.geojson")))
    rows = {}
    for f in treads["features"]:
        p = f["properties"]
        rows.setdefault(p["row"], []).append(p)
    row_ids = sorted(rows)
    r1 = rows[row_ids[0]]
    rN = rows[row_ids[-1]]
    r1_rad = float(np.mean([p["axis_radius_ft"] for p in r1]))
    rN_rad = float(np.mean([p["axis_radius_ft"] for p in rN]))
    r1_z = float(np.mean([p["tread_elev_navd88"] for p in r1]))
    rN_z = float(np.mean([p["tread_elev_navd88"] for p in rN]))
    rise = rN_z - r1_z
    avg_rake = rise / (rN_rad - r1_rad)
    # per-section local rake
    sec_rakes = []
    for sec in ("east", "bend", "south"):
        sr = sorted([p for ps in rows.values() for p in ps
                     if p["section"] == sec], key=lambda p: p["row"])
        rr = [p["axis_radius_ft"] for p in sr]
        zz = [p["tread_elev_navd88"] for p in sr]
        sec_rakes.append(np.polyfit(rr, zz, 1)[0])

    STAGE_FRONT_TO_ROW1 = 35.0   # canon (goal/DESIGN_CANON; event floor)
    STAGE_W, STAGE_D = 70.0, 34.0
    FAN = 110.0
    row1_arc = math.radians(FAN) * r1_rad

    m = {
        "site": "Petoskey Pit civic bowl (Scenario E, in-situ package)",
        "slug": "petoskey",
        "location": "Petoskey, MI",
        "crs": "EPSG:6494 NAD83(2011) Michigan Central, intl ft; NAVD88 ft",
        "dem": V("2015 USGS LiDAR (MI 13County C16) + 2026 supplement, "
                 "design rasters at 1 ft", "canon"),
        "capacity": V(1283, "canon", "nominal Scenario E baseline; 1,243 "
                      "Band-A validated; options to 1,505 validated"),
        "audience_facing_az_deg": V(312.0, "canon",
                                    "seating axis az 132 -> nominal facing "
                                    "312; bay-view corridor az 330"),
        "stage_frontage_ft": V(STAGE_W, "canon",
                               "70x34 ft low stage core + lateral shoulders; "
                               "PROVISIONAL (Rule 9 OPEN)"),
        "stage_depth_ft": V(STAGE_D, "canon", "Rule 9 OPEN"),
        "stage_front_to_row1_ft": V(STAGE_FRONT_TO_ROW1, "canon",
                                    "event floor between stage and row 1"),
        "floor_elev_ft": V(612.5, "canon", "stage/event-floor reference"),
        "row1_elev_ft": V(round(r1_z, 1), "measured_dem",
                          "mean of row-1 treads (terrace_treads.geojson)"),
        "top_row_elev_ft": V(round(rN_z, 1), "measured_dem",
                             f"mean of row-{row_ids[-1]} treads"),
        "rise_row1_to_top_ft": V(round(rise, 1), "measured_dem"),
        "avg_rake_pct": V(round(avg_rake * 100, 1), "measured_dem",
                          "fit across tread radii/elevs"),
        "local_rake_range_pct": V([round(min(sec_rakes) * 100, 1),
                                   round(max(sec_rakes) * 100, 1)],
                                  "measured_dem", "per-section tread fits"),
        "fan_angle_deg": V(FAN, "canon", "±55° about the seating axis"),
        "inner_radius_ft": V(round(r1_rad, 1), "measured_dem",
                             "row-1 axis radius"),
        "outer_radius_ft": V(round(rN_rad, 1), "measured_dem",
                             f"row-{row_ids[-1]} axis radius"),
        "upper_row_distance_ft": V(round(STAGE_FRONT_TO_ROW1
                                         + (rN_rad - r1_rad), 1),
                                   "measured_dem",
                                   "stage front -> row 18: 35 ft floor + "
                                   "seating depth (rN - r1 radii)"),
        "row1_arc_length_ft": V(round(row1_arc, 1), "canon"),
        "frontage_to_row1_arc": V(round(STAGE_W / row1_arc, 2), "canon"),
        "row_count_est": V(len(row_ids), "canon",
                           "formal rows 1-18 minus promenade 5 + aisle 9/10 "
                           "= 15 treads x 3 sections",
                           mean_tread_ft=round((rN_rad - r1_rad)
                                               / (row_ids[-1] - row_ids[0]),
                                               1)),
        "ada": V("two 8.33% switchback routes + level cross-aisle "
                 "(rows 9/10) at 622.01; validated", "canon"),
        "backdrop": V("open to Little Traverse Bay az 330; no upstage wall "
                      "(landscape venue)", "canon"),
    }
    out = os.path.join(ROOT, "data", "comparators", "petoskey_metrics.json")
    json.dump(m, open(out, "w"), indent=1)
    print("wrote", out)
    return m


def main():
    comp = {slug: comparator_metrics(slug) for slug in SITES}
    pet = petoskey_metrics()
    allm = {"petoskey": pet, **comp,
            "generated": "scripts/comparators/extract_metrics.py",
            "units": "all *_ft values international feet; *_pct percent"}
    out = os.path.join(ROOT, "data", "comparators", "comparison.json")
    json.dump(allm, open(out, "w"), indent=1)
    print("wrote", out)


if __name__ == "__main__":
    main()
