#!/usr/bin/env python3
"""Before/after + human-scale aisle views of the terrain-op terraces.

Produces three matched-frame SVGs (dependency-free; the repo's web viewer and
any browser render SVG, and live UE GPU capture is the existing PENDING item):

  analysis/terrace_ops/op_view_before_after.svg
      Plan, SAME extent both panels.  LEFT "before" = one undifferentiated
      terrain skin over the bowl (the grass-over-the-seats state -- terrain not
      generated from operations).  RIGHT "after" = every surface coloured by its
      op_id surface_class (cap, tread, riser, drainage, ADA, stage, cut/fill).

  analysis/terrace_ops/aisle_cross_section.svg
      Radial section along the 330 deg audience axis: existing ground line vs the
      engineered stepped terraces (treads, risers, seat caps, drainage), with a
      5 ft 6 in standing figure for scale.

stdlib only.  EPSG:6494, NAVD88 intl ft.
"""
from __future__ import annotations

import math
import os

import terrace_ops_common as T

OUT = os.path.join(T.REPO, "analysis", "terrace_ops")
LAYERS = ("terrain_transitions", "riser_faces", "tread_surfaces", "drainage_bands",
          "seat_caps", "ada_paths", "stage_floor")  # draw order: back -> front


def _bounds(features):
    xs, ys = [], []
    for f in features:
        for ring in f["geometry"]["coordinates"]:
            for x, y in ring:
                xs.append(x); ys.append(y)
    return min(xs), min(ys), max(xs), max(ys)


def _svg_header(w, h, title):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" font-family="Helvetica,Arial,sans-serif">',
            f'<title>{title}</title>',
            f'<rect width="{w}" height="{h}" fill="#101418"/>']


def plan_before_after():
    feats = {ln: T.load_geojson(os.path.join(T.GEO_OUT, f"{ln}.geojson"))["features"]
             for ln in LAYERS}
    grade = T.load_geojson(os.path.join(T.GEO_OUT, "grade_p_current.geojson"))["features"]
    allf = [f for fs in feats.values() for f in fs] + grade
    x0, y0, x1, y1 = _bounds(allf)
    pad = 14
    panel_w, panel_h = 460, 520
    gap = 24
    sx = (panel_w - 2 * pad) / (x1 - x0)
    sy = (panel_h - 2 * pad) / (y1 - y0)
    s = min(sx, sy)

    def tx(x, ox): return ox + pad + (x - x0) * s
    def ty(y): return panel_h - pad - (y - y0) * s   # north up

    def poly(ring, ox, fill, stroke="#0008", sw=0.4, op=1.0):
        pts = " ".join(f"{tx(x, ox):.1f},{ty(y):.1f}" for x, y in ring)
        return (f'<polygon points="{pts}" fill="{fill}" fill-opacity="{op}" '
                f'stroke="{stroke}" stroke-width="{sw}"/>')

    W = panel_w * 2 + gap
    svg = _svg_header(W, panel_h + 46, "Open Civic Bowl - terrain ops before/after")
    svg.append(f'<text x="14" y="22" fill="#e8eef2" font-size="15" '
               f'font-weight="bold">Open Civic Bowl - terrain generated from '
               f'auditable operations</text>')

    # BEFORE: single undifferentiated terrain skin
    bx = 0
    svg.append(f'<text x="{bx+pad}" y="44" fill="#9fb0bb" font-size="12">'
               f'BEFORE - one terrain skin (grass over the seats)</text>')
    svg.append(f'<g transform="translate(0,46)">')
    for f in grade:
        svg.append(poly(f["geometry"]["coordinates"][0], bx, "#5f7d4f"))
    # faint row hint lines to show seats are NOT articulated
    for f in feats["seat_caps"]:
        svg.append(poly(f["geometry"]["coordinates"][0], bx, "#5f7d4f", "#54703f", 0.5))
    svg.append('</g>')

    # AFTER: op-coloured surfaces
    ax = panel_w + gap
    svg.append(f'<text x="{ax+pad}" y="44" fill="#9fb0bb" font-size="12">'
               f'AFTER - coloured by op_id surface class</text>')
    svg.append(f'<g transform="translate(0,46)">')
    pal = T.debug_palette()
    for ln in LAYERS:
        for f in feats[ln]:
            sc = f["properties"]["surface_class"]
            svg.append(poly(f["geometry"]["coordinates"][0], ax,
                            f["properties"].get("debug_color", pal.get(sc, "#f0f")),
                            "#0006", 0.3))
    svg.append('</g>')

    # legend
    ly = panel_h + 30
    items = [("cap", "seat cap"), ("tread", "tread"), ("riser", "riser"),
             ("drainage", "drainage"), ("ada", "ADA"), ("stage", "stage"),
             ("fill", "fill"), ("cut", "cut"), ("existing_no_touch", "existing")]
    lx = ax + pad
    for sc, label in items:
        svg.append(f'<rect x="{lx}" y="{ly-9}" width="11" height="11" '
                   f'fill="{pal[sc]}" stroke="#0006"/>')
        svg.append(f'<text x="{lx+15}" y="{ly}" fill="#cdd6dc" font-size="10">{label}</text>')
        lx += 46 + len(label) * 3
        if lx > W - 80:
            lx = ax + pad; ly += 16
    svg.append('</svg>')
    return "\n".join(svg)


def aisle_section():
    rows = T.load_geojson(os.path.join(T.DESIGN_SRC, "seating_rows.geojson"))["features"]
    rows = sorted(rows, key=lambda f: f["properties"]["row"])
    r = [float(f["properties"]["radius_ft"]) for f in rows]
    tread = [float(f["properties"]["tread_elev_navd88"]) for f in rows]
    terr = [float(f["properties"]["terrain_elev_navd88"]) for f in rows]
    rise = [float(f["properties"].get("row_rise_ft", 0.0)) for f in rows]

    rmin, rmax = r[0] - 3, r[-1] + 4
    emin = min(min(terr), min(tread)) - 1.5
    emax = max(max(tread), max(terr)) + 7   # headroom for the figure
    W, H, padL, padB, padT = 900, 380, 54, 40, 30
    sx = (W - padL - 14) / (rmax - rmin)
    sy = (H - padB - padT) / (emax - emin)

    def X(rr): return padL + (rr - rmin) * sx
    def Y(e): return H - padB - (e - emin) * sy

    svg = _svg_header(W, H, "Open Civic Bowl - aisle cross-section")
    svg.append(f'<text x="14" y="20" fill="#e8eef2" font-size="14" font-weight="bold">'
               f'Aisle / cross-aisle section - engineered terraces vs existing grade '
               f'(330 deg axis)</text>')
    # axes
    svg.append(f'<line x1="{padL}" y1="{Y(emin)}" x2="{W-10}" y2="{Y(emin)}" '
               f'stroke="#33424c" stroke-width="1"/>')
    for e in range(int(emin) - int(emin) % 2, int(emax) + 1, 2):
        yy = Y(e)
        svg.append(f'<line x1="{padL}" y1="{yy:.1f}" x2="{W-10}" y2="{yy:.1f}" '
                   f'stroke="#1c2730" stroke-width="0.6"/>')
        svg.append(f'<text x="6" y="{yy+3:.1f}" fill="#6c7c86" font-size="9">{e}</text>')

    # existing ground line (the would-be grass surface)
    eg = " ".join(f"{X(r[i]):.1f},{Y(terr[i]):.1f}" for i in range(len(rows)))
    svg.append(f'<polyline points="{eg}" fill="none" stroke="#7f9b5f" '
               f'stroke-width="2" stroke-dasharray="5,3"/>')
    svg.append(f'<text x="{X(r[-1])-150:.1f}" y="{Y(terr[-1])-6:.1f}" '
               f'fill="#9bb277" font-size="10">existing ground (no-touch)</text>')

    # engineered stepped terraces
    pal = T.debug_palette()
    for i in range(len(rows)):
        inner = (r[i - 1] + r[i]) / 2 if i > 0 else r[i] - 1.5
        outer = (r[i] + r[i + 1]) / 2 if i < len(rows) - 1 else r[i] + 1.5
        te = tread[i]
        # tread plate
        svg.append(f'<rect x="{X(inner):.1f}" y="{Y(te):.1f}" '
                   f'width="{(outer-inner)*sx:.1f}" height="2.2" fill="{pal["tread"]}"/>')
        # riser face (down to row below tread)
        below = tread[i - 1] if i > 0 else te - rise[i]
        svg.append(f'<rect x="{X(inner)-1:.1f}" y="{Y(te):.1f}" width="2.4" '
                   f'height="{max((te-below)*sy,1):.1f}" fill="{pal["riser"]}"/>')
        # seat cap block at back of tread
        svg.append(f'<rect x="{X(outer)-6:.1f}" y="{Y(te)-5:.1f}" width="6" '
                   f'height="5" fill="{pal["cap"]}"/>')
        # drainage notch at the up-slope edge
        svg.append(f'<rect x="{X(outer)-2:.1f}" y="{Y(te):.1f}" width="2" '
                   f'height="2.4" fill="{pal["drainage"]}"/>')

    # 5 ft 6 in standing figure on a mid tread (row 8)
    mi = 7
    fx = X((r[mi] + r[mi + 1]) / 2 - 1.2)
    fy = Y(tread[mi])
    fig_h = 5.5 * sy
    head = fig_h * 0.12
    svg.append(f'<circle cx="{fx:.1f}" cy="{fy-fig_h+head:.1f}" r="{head:.1f}" '
               f'fill="#e8eef2"/>')
    svg.append(f'<line x1="{fx:.1f}" y1="{fy-fig_h+2*head:.1f}" x2="{fx:.1f}" '
               f'y2="{fy-fig_h*0.35:.1f}" stroke="#e8eef2" stroke-width="2.4"/>')
    svg.append(f'<line x1="{fx:.1f}" y1="{fy:.1f}" x2="{fx-fig_h*0.13:.1f}" '
               f'y2="{fy-fig_h*0.35:.1f}" stroke="#e8eef2" stroke-width="2.2"/>')
    svg.append(f'<line x1="{fx:.1f}" y1="{fy:.1f}" x2="{fx+fig_h*0.13:.1f}" '
               f'y2="{fy-fig_h*0.35:.1f}" stroke="#e8eef2" stroke-width="2.2"/>')
    svg.append(f'<text x="{fx+8:.1f}" y="{fy-fig_h*0.5:.1f}" fill="#e8eef2" '
               f'font-size="10">5\'6"</text>')

    # legend
    items = [("tread", "gravel-fines tread"), ("riser", "planted riser"),
             ("cap", "timber/precast cap"), ("drainage", "gravel drainage")]
    lx = padL
    for sc, label in items:
        svg.append(f'<rect x="{lx}" y="{H-16}" width="11" height="11" fill="{pal[sc]}"/>')
        svg.append(f'<text x="{lx+15}" y="{H-7}" fill="#cdd6dc" font-size="10">{label}</text>')
        lx += 150
    svg.append('</svg>')
    return "\n".join(svg)


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, fn in (("op_view_before_after", plan_before_after),
                     ("aisle_cross_section", aisle_section)):
        path = os.path.join(OUT, f"{name}.svg")
        with open(path, "w") as fh:
            fh.write(fn())
        print(f"  wrote {os.path.relpath(path, T.REPO)}")
    print("  (SVG: browser / web-viewer renderable; live UE GPU capture is the "
          "existing PENDING item)")


if __name__ == "__main__":
    main()
