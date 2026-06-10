#!/usr/bin/env python3
"""Write qgis/in_situ_package.qgs — a minimal QGIS project for manual review.

All layer datasources are RELATIVE to the project file (../vectors_geojson/…,
../dem/…) so the project travels with the repo. The raster layers exist only
after scripts/build_proposed_grade.py has run with a DEM present; on a fresh
checkout QGIS will list them as unavailable, which is expected and covered by
dem/MISSING_DATA.md.

Authored as plain XML because PyQGIS is not importable in this environment;
scripts/audit_in_situ_package.py parses the file back and resolves every
datasource, so a path regression cannot land silently.
"""
import os
from xml.sax.saxutils import escape

import in_situ_common as C

QGIS_DIR = os.path.join(C.REPO, "qgis")
PROJECT = os.path.join(QGIS_DIR, "in_situ_package.qgs")

SRS = """      <spatialrefsys nativeFormat="Wkt">
        <authid>EPSG:6494</authid>
        <srsid>0</srsid>
        <description>NAD83(2011) / Michigan Central (ft)</description>
        <projectionacronym>lcc</projectionacronym>
        <ellipsoidacronym>EPSG:7019</ellipsoidacronym>
        <geographicflag>false</geographicflag>
      </spatialrefsys>"""

# (id, display name, relative path, type, geometry)  — drawing order bottom→top
LAYERS = [
    ("dem_design", "existing ground DEM 1ft", "../dem/dem_design_1ft.tif", "raster", None),
    ("proposed_grade", "proposed grade 1ft", "../dem/proposed_grade_1ft.tif", "raster", None),
    ("cut_fill", "cut/fill 1ft (+fill/−cut)", "../dem/cut_fill_1ft.tif", "raster", None),
    ("site_context", "site context", "../vectors_geojson/site_context.geojson", "vector", "Unknown"),
    ("material_zones", "material zones", "../vectors_geojson/material_zones.geojson", "vector", "Polygon"),
    ("bowl_zones", "bowl zones (stage Rule 9 OPEN, aisle, ADA, swales, hinges)", "../vectors_geojson/bowl_zones.geojson", "vector", "Unknown"),
    ("terrace_treads", "terrace treads (3 sections x 15 rows)", "../vectors_geojson/terrace_treads.geojson", "vector", "Polygon"),
    ("terrace_edges", "low seat edges", "../vectors_geojson/terrace_edges.geojson", "vector", "Line"),
    ("scenarioE_geometry", "Scenario E emitted geometry (governing source)", "../vectors_geojson/scenarioE_geometry.geojson", "vector", "Unknown"),
    ("seating_bays", "extended-bays centrelines (incl. row-5 promenade)", "../design_extended_bays/seating_bays.geojson", "vector", "Line"),
    ("event_modes", "event modes (schematic, nonbinding)", "../vectors_geojson/event_modes.geojson", "vector", "Unknown"),
    ("in_situ_viewpoints", "render viewpoints", "../vectors_geojson/in_situ_viewpoints.geojson", "vector", "Point"),
]


def maplayer(lid, name, rel, ltype, geom):
    geom_attr = f' geometry="{geom}"' if (ltype == "vector" and geom) else ""
    provider = "ogr" if ltype == "vector" else "gdal"
    return f"""    <maplayer type="{ltype}"{geom_attr} autoRefreshEnabled="0">
      <id>{lid}</id>
      <datasource>{escape(rel)}</datasource>
      <layername>{escape(name)}</layername>
      <srs>
{SRS}
      </srs>
      <provider encoding="UTF-8">{provider}</provider>
    </maplayer>"""


def main():
    os.makedirs(QGIS_DIR, exist_ok=True)
    tree = "\n".join(
        f'    <layer-tree-layer id="{lid}" name="{escape(name)}" '
        f'source="{escape(rel)}" providerKey="{"ogr" if t == "vector" else "gdal"}" '
        f'checked="Qt::Checked" expanded="0"/>'
        for lid, name, rel, t, g in reversed(LAYERS)
    )
    layers = "\n".join(maplayer(*l) for l in LAYERS)
    order = "\n".join(f'      <item>{lid}</item>' for lid, *_ in reversed(LAYERS))
    xml = f"""<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis projectname="Petoskey Pit — three-section civic bowl in-situ package" version="3.34.0" saveUser="in_situ_pipeline">
  <homePath path=""/>
  <title>Petoskey Pit — three-section civic bowl in-situ package</title>
  <transaction mode="Disabled"/>
  <projectFlags set=""/>
  <projectCrs>
{SRS.replace('      ', '    ')}
  </projectCrs>
  <layer-tree-group>
{tree}
  </layer-tree-group>
  <projectlayers>
{layers}
  </projectlayers>
  <layerorder>
{order}
  </layerorder>
  <properties>
    <Paths>
      <Absolute type="bool">false</Absolute>
    </Paths>
    <Measure>
      <Ellipsoid type="QString">EPSG:7019</Ellipsoid>
    </Measure>
  </properties>
</qgis>
"""
    with open(PROJECT, "w") as fh:
        fh.write(xml)
    print(f"  wrote {os.path.relpath(PROJECT, C.REPO)} ({len(LAYERS)} layers, relative paths)")

    readme = os.path.join(QGIS_DIR, "README.md")
    with open(readme, "w") as fh:
        fh.write("""# QGIS project — in-situ package

Open `in_situ_package.qgs` in QGIS ≥3.28. All layer paths are **relative**
(`../vectors_geojson/…`, `../dem/…`), so the project works from any checkout
location.

Expected on a fresh checkout: the three raster layers (existing DEM, proposed
grade, cut/fill) are reported *unavailable* because rasters are gitignored —
see `../dem/MISSING_DATA.md` for how to rebuild them, then reopen. Vector
layers load with default styling; this project is a review scaffold, not a
styled deliverable.

CRS: EPSG:6494 (NAD83(2011) / Michigan Central, **international feet**),
elevations NAVD88 (Geoid12A) intl ft — see `../docs/datum_note.md`.
""")
    print(f"  wrote {os.path.relpath(readme, C.REPO)}")


if __name__ == "__main__":
    main()
