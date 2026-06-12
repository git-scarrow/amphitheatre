#!/usr/bin/env python3
"""Comparator site registry — single source of truth for the benchmark.

Each site entry records WHERE the venue is (WGS84 center from OSM), WHICH
USGS 3DEP 1 m DEM product covers it (verified via TNM Access API on
2026-06-12; raw responses archived in data/comparators/_sources/), and how
large a clip to take.

Units policy (audit-critical):
  * USGS 1 m DEM tiles are in a projected METER CRS (UTM) with NAVD88
    METER heights. Clips are kept in native CRS/units on disk.
  * All derived metrics are converted to FEET explicitly at extraction
    time (see extract_metrics.py) and labeled `_ft`. Nothing downstream
    consumes raw meter values silently.
Petoskey canon stays in EPSG:6494 / NAVD88 ft and is NOT modified here.
"""

US_FT_PER_M = 3.280839895013123  # international foot = 0.3048 m exactly;
# NOTE: survey-foot vs international-foot differ by 2 ppm — irrelevant at
# site scale (<0.01 ft over 1,000 ft) but we standardize on international ft.

SITES = {
    "santa_barbara_bowl": {
        "name": "Santa Barbara Bowl",
        "location": "1122 N Milpas St, Santa Barbara, CA",
        "center_lonlat": (-119.69341, 34.43511),  # OSM way 623261253 (stage house)
        "osm_stage_way": 623261253,
        "clip_half_m": 350.0,
        "dem_product": {
            "title": "USGS one meter x25y382 CA Montecito",
            "project": "CA_Montecito_2018",
            "url": ("https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/"
                    "1m/Projects/CA_Montecito_2018/TIFF/"
                    "USGS_one_meter_x25y382_CA_Montecito_2018.tif"),
            "publication_date": "2020-03-31",
            "lidar_acquisition": "2018 (CA Montecito post-debris-flow project)",
            "resolution_m": 1.0,
        },
        "facts_published": {
            "capacity": 4562,
            "capacity_source": "https://en.wikipedia.org/wiki/Santa_Barbara_Bowl",
            "built": 1936,
            "stage_rebuilt": 2002,
            "stage_rebuild_note": ("stage+backstage expanded 3,000 -> 10,000 sq ft "
                                   "(Master Plan Phase 1A; SB Independent 2011 via "
                                   "Wikipedia ref)"),
            "floor_sections": "T,U,V reserved / GA standing",
            "section_bands": "A-C lower, D-I mid, J-O upper (sbbowl.com/seating-chart)",
        },
    },
    "meijer_gardens_amphitheater": {
        "name": "Frederik Meijer Gardens Amphitheater",
        "location": "1000 E Beltline Ave NE, Grand Rapids, MI",
        "center_lonlat": (-85.58568, 42.97985),  # OSM way 490428003 (stage)
        "osm_stage_way": 490428003,
        "clip_half_m": 300.0,
        "dem_product": {
            "title": "USGS one meter x61y476 MI 31Co Kent 2016",
            "project": "MI_31Co_Kent_2016",
            "url": ("https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/"
                    "1m/Projects/MI_31Co_Kent_2016/TIFF/"
                    "USGS_one_meter_x61y476_MI_31Co_Kent_2016.tif"),
            "publication_date": "2020-03-30",
            "lidar_acquisition": "2016 (MI 31-County Kent collection)",
            "resolution_m": 1.0,
        },
        "facts_published": {
            "capacity": 1900,
            "capacity_source": ("https://en.wikipedia.org/wiki/Frederik_Meijer_Gardens "
                                "(tiered lawn seating for 1,900; flagged citation-needed "
                                "there, but the 1,900 figure is used venue-wide in press)"),
            "built": 2003,
            "stage_note": "covered stage (canopy), open-air tiered lawn bowl",
        },
    },
}

# Candidates evaluated and REJECTED (goal requires documenting why)
REJECTED = {
    "gerald_r_ford_amphitheater_vail": {
        "name": "Gerald R. Ford Amphitheater (Vail, CO)",
        "dem": "covered (USGS one meter x38y439 CO Central Western 2016)",
        "reason": ("Roofed pavilion venue: most seating sits under a permanent "
                   "fabric roof structure, so the venue is not an open bowl-style "
                   "comparator for an open-air landscape bowl; LiDAR bare-earth "
                   "under the roof is also unreliable for row-level rake."),
    },
    "red_rocks_amphitheatre": {
        "name": "Red Rocks Amphitheatre (Morrison, CO)",
        "dem": "covered (CO 3DEP 1 m)",
        "reason": ("Scale and typology outlier: ~9,500 seats between monolithic "
                   "rock formations; rake/geometry driven by the rock landform, "
                   "not by civic-bowl design choices comparable to a ~1,500-2,300 "
                   "seat graded bowl."),
    },
}
