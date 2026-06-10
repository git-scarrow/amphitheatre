#!/usr/bin/env bash
# Build + audit the Open Civic Bowl in-situ design package.
#
# From a fresh checkout this either generates the full package or completes
# the vector/board scaffolding and writes dem/MISSING_DATA.md with precise
# missing-data diagnostics (rasters and source LiDAR are gitignored).
#
# Dependencies (venv): numpy rasterio shapely matplotlib
#   python -m venv .venv && .venv/bin/pip install numpy rasterio shapely matplotlib
set -euo pipefail
cd "$(dirname "$0")/.."

PY="${PYTHON:-}"
if [ -z "$PY" ]; then
  if [ -x .venv/bin/python ]; then PY=.venv/bin/python; else PY=python3; fi
fi
echo "== in-situ package build ($($PY --version 2>&1)) =="

$PY scripts/in_situ_common.py                 # 0. constants vs design of record
$PY scripts/build_in_situ_geometry.py         # 1. treads, edges, zones (+copies)
$PY scripts/build_site_context.py             # 2. site context + material zones
$PY scripts/build_viewpoints_and_events.py    # 3. viewpoints + event modes
$PY scripts/build_proposed_grade.py           # 4. rasters OR missing-data diagnostic
$PY scripts/build_qgis_project.py             # 5. QGIS review project
$PY scripts/render_in_situ_boards.py          # 6. renders + three boards
$PY scripts/audit_in_situ_package.py          # 7. audit gate (exit 1 on failure)
