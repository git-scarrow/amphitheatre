#!/usr/bin/env python3
"""
Revised close-up plan — treatment train moved off the primary audience-to-stage sightline.

Petoskey Pit Amphitheater. Plan-grade, derived from the real package layers:
  package/05_seating/{stage_floor,seating_rows,ada_route}.geojson
  package/07_stormwater/treatment_train.geojson

Plan is rotated so the seating-fan centerline (az 150, stage->audience) points DOWN.
Stage at top (apex of arcs), audience floor below, seating terraces fan downward.
Beyond the stage (up, toward az 330 / Little Traverse Bay) is the bowl bottom, where
the treatment train (forebay + bioretention cell) is RELOCATED so it no longer sits
in the audience floor / on the sightline.

Output: package/01_layout/revised_closeup_plan.svg
"""
import json, math, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def gj(p): return json.load(open(os.path.join(ROOT, p)))["features"]

# --- screen transform: focal at origin, +y = down (toward audience), -y = up (toward bay) ---
Xf, Yf = 19533075.2, 750786.21
C, S = math.cos(math.radians(30)), 0.5  # cos150 basis pieces
def scr(x, y):
    e, n = x - Xf, y - Yf
    sx = 0.8660254 * e + 0.5 * n
    sy = 0.5 * e - 0.8660254 * n
    return sx, sy

# --- SVG viewport ---
SCALE = 2.25          # px per foot
CX, CY = 555, 470     # svg px of focal point
W, H = 1180, 1180
def P(sx, sy):        # screen-ft -> svg px
    return CX + sx * SCALE, CY + sy * SCALE
def Pg(x, y):         # geojson -> svg px
    return P(*scr(x, y))

def path_from_coords(coords, close=False):
    d = ""
    for i, (x, y) in enumerate(coords):
        px, py = Pg(x, y)
        d += ("M" if i == 0 else "L") + f"{px:.1f},{py:.1f} "
    if close: d += "Z"
    return d

out = []
def add(s): out.append(s)

add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
    f'viewBox="0 0 {W} {H}" font-family="Helvetica,Arial,sans-serif">')

# ---- defs ----
add('''<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#eaf2f5"/>
    <stop offset="0.42" stop-color="#f3f1e9"/>
    <stop offset="1" stop-color="#efe7da"/>
  </linearGradient>
  <radialGradient id="pool" cx="0.5" cy="0.4" r="0.7">
    <stop offset="0" stop-color="#bfe0e8"/>
    <stop offset="1" stop-color="#9ccada"/>
  </radialGradient>
  <marker id="arrow" markerWidth="10" markerHeight="10" refX="7" refY="3" orient="auto">
    <path d="M0,0 L7,3 L0,6 Z" fill="#b23b2e"/>
  </marker>
  <marker id="arrowblue" markerWidth="11" markerHeight="11" refX="8" refY="3.2" orient="auto">
    <path d="M0,0 L8,3.2 L0,6.4 Z" fill="#2a6f97"/>
  </marker>
  <marker id="tick" markerWidth="6" markerHeight="6" refX="3" refY="3" orient="auto">
    <circle cx="3" cy="3" r="2" fill="#1f6f4a"/>
  </marker>
</defs>''')
add(f'<rect width="{W}" height="{H}" fill="url(#bg)"/>')

# ---- faint PROPOSED-GRADE contours (2-ft), from grade_proposed.tif ----
# answers "does the layout belong to the terrain?" — real finished-grade surface
try:
    contours = json.load(open(os.path.join(ROOT, "package/02_grading/contours_venue_2ft.json")))
except Exception:
    contours = []
add('<g fill="none" stroke="#9a8f78" stroke-width="0.9" opacity="0.30">')
for c in contours:
    coords = c["coords"]
    d = ""
    for i, (x, y) in enumerate(coords):
        px, py = Pg(x, y)
        d += ("M" if i == 0 else "L") + f"{px:.1f},{py:.1f} "
    # emphasise index contours (every 10 ft)
    idx = (round(c["elev"]) % 10 == 0)
    sw = "1.4" if idx else "0.9"
    op = "0.5" if idx else "0.3"
    add(f'<path d="{d}" stroke-width="{sw}" opacity="{op}"/>')
add('</g>')
# label a couple of index contours
add('<g font-size="9" fill="#8a7f68" opacity="0.8">')
for c in contours:
    if round(c["elev"]) in (620, 630, 640) and len(c["coords"]) > 4:
        x, y = c["coords"][len(c["coords"])//2]
        px, py = Pg(x, y)
        if 90 < px < W-90 and 120 < py < H-90:
            add(f'<text x="{px:.0f}" y="{py:.0f}">{round(c["elev"])}</text>')
add('</g>')

# ============================================================
# 1. CLEAR SIGHTLINE CORRIDOR (central viewing cone) — kept open
# ============================================================
# central +/-14 deg cone from focal, radius to back row
def cone(ang_half, r0, r1):
    a0 = 90 - ang_half; a1 = 90 + ang_half
    p = []
    p.append(P(r0*math.cos(math.radians(a0)), r0*math.sin(math.radians(a0))))
    p.append(P(r1*math.cos(math.radians(a0)), r1*math.sin(math.radians(a0))))
    p.append(P(r1*math.cos(math.radians(a1)), r1*math.sin(math.radians(a1))))
    p.append(P(r0*math.cos(math.radians(a1)), r0*math.sin(math.radians(a1))))
    return "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in p) + " Z"
add(f'<path d="{cone(15, 0, 180)}" fill="#fff7d6" opacity="0.55"/>')

# ============================================================
# 2. SEATING TERRACES — 30 rows, +/-30 deg fan (analytic arcs)
# ============================================================
# fan wedge fill
def wedge(r0, r1, a0=60, a1=120):
    pa0=(r1*math.cos(math.radians(a0)), r1*math.sin(math.radians(a0)))
    pa1=(r1*math.cos(math.radians(a1)), r1*math.sin(math.radians(a1)))
    pb1=(r0*math.cos(math.radians(a1)), r0*math.sin(math.radians(a1)))
    pb0=(r0*math.cos(math.radians(a0)), r0*math.sin(math.radians(a0)))
    x0,y0=P(*pa0); x1,y1=P(*pa1); x2,y2=P(*pb1); x3,y3=P(*pb0)
    R1=r1*SCALE; R0=r0*SCALE
    return (f'M{x0:.1f},{y0:.1f} A{R1:.1f},{R1:.1f} 0 0 1 {x1:.1f},{y1:.1f} '
            f'L{x2:.1f},{y2:.1f} A{R0:.1f},{R0:.1f} 0 0 0 {x3:.1f},{y3:.1f} Z')
add(f'<path d="{wedge(85,172)}" fill="#cdbd8f" opacity="0.5" stroke="#9c8c5e" stroke-width="1"/>')
# row arcs
add('<g fill="none" stroke="#8a7a4c" stroke-width="1" opacity="0.75">')
for i in range(30):
    r = 85 + i*3
    x0,y0=P(r*math.cos(math.radians(60)), r*math.sin(math.radians(60)))
    x1,y1=P(r*math.cos(math.radians(120)), r*math.sin(math.radians(120)))
    R=r*SCALE
    add(f'<path d="M{x0:.1f},{y0:.1f} A{R:.1f},{R:.1f} 0 0 1 {x1:.1f},{y1:.1f}"/>')
add('</g>')

# ============================================================
# 3. AUDIENCE FLOOR (event floor / forecourt)
# ============================================================
floor=[f for f in gj("package/05_seating/stage_floor.geojson")
       if f["properties"]["name"]=="event_floor_forecourt"][0]
add(f'<path d="{path_from_coords(floor["geometry"]["coordinates"][0], close=True)}" '
    f'fill="#e7ddc2" stroke="#b9a878" stroke-width="1.4"/>')

# ============================================================
# 4. STAGE
# ============================================================
stage=[f for f in gj("package/05_seating/stage_floor.geojson")
       if f["properties"]["name"]=="stage"][0]
add(f'<path d="{path_from_coords(stage["geometry"]["coordinates"][0], close=True)}" '
    f'fill="#5b6b73" stroke="#2f3b41" stroke-width="1.6"/>')

# ============================================================
# 5. TREATMENT TRAIN — RELOCATED beyond the stage (NW bowl bottom)
# ============================================================
# (a) ghost of the OLD conflicting positions, in the floor / on sightline
add('<g fill="none" stroke="#b23b2e" stroke-width="1.4" stroke-dasharray="5 4" opacity="0.85">')
# old forebay sat ~screen(-18,+40); old bioretention sprawled over floor
ox,oy=P(-18,40)
add(f'<rect x="{ox-26:.0f}" y="{oy-20:.0f}" width="52" height="40" rx="6"/>')
add(f'<path d="{cone(13,8,150)}" />')   # the swath it used to block
add('</g>')
oxc,oyc=P(0,70)
add(f'<text x="{oxc:.0f}" y="{oyc:.0f}" font-size="12" fill="#b23b2e" '
    f'text-anchor="middle" font-style="italic">was here — blocked sightline</text>')

# (b) relocated reflecting / bioretention cell BEYOND the stage (real wet-cell footprint)
wet=[f for f in gj("package/07_stormwater/treatment_train.geojson")] if False else None
wetcell=[f for f in gj("package/05_seating/stage_floor.geojson")
         if f["properties"]["name"]=="treatment_wet_cell"][0]
add(f'<path d="{path_from_coords(wetcell["geometry"]["coordinates"][0], close=True)}" '
    f'fill="url(#pool)" stroke="#5f93a6" stroke-width="1.6"/>')
# emergent-planting fringe ring
add(f'<path d="{path_from_coords(wetcell["geometry"]["coordinates"][0], close=True)}" '
    f'fill="none" stroke="#5a8a4a" stroke-width="3" stroke-dasharray="2 4" opacity="0.7"/>')

# (c) relocated FOREBAY — inflow sediment cell on the NW (upper-left) flank, off corridor
fb_cx, fb_cy = P(-52, -78)
add(f'<rect x="{fb_cx-22:.0f}" y="{fb_cy-15:.0f}" width="44" height="30" rx="5" '
    f'transform="rotate(-18 {fb_cx:.0f} {fb_cy:.0f})" '
    f'fill="#7fae8a" stroke="#3f7d57" stroke-width="1.6"/>')
# flow from forebay into the cell
c1x,c1y=P(-40,-66); c2x,c2y=P(-12,-58)
add(f'<path d="M{fb_cx:.0f},{fb_cy:.0f} Q{c1x:.0f},{c1y:.0f} {c2x:.0f},{c2y:.0f}" '
    f'fill="none" stroke="#2a6f97" stroke-width="2.2" marker-end="url(#arrowblue)"/>')

# (d) relocation arrow: old floor spot -> new beyond-stage cell
ax,ay=P(-14,30); bx,by=P(-26,-40)
add(f'<path d="M{ax:.0f},{ay:.0f} C{ax-30:.0f},{ay-30:.0f} {bx-10:.0f},{by+40:.0f} {bx:.0f},{by:.0f}" '
    f'fill="none" stroke="#b23b2e" stroke-width="2" stroke-dasharray="7 4" marker-end="url(#arrow)"/>')

# ============================================================
# 6. ACCESSIBLE ROUTE (engineered ADA ramp + dispersed WC spaces)
# ============================================================
ada=gj("package/05_seating/ada_route.geojson")
PURP="#7a3fa0"
def ada_built(coords, w=5):
    """built ramp/aisle segment from geojson coords (solid)"""
    add(f'<path d="{path_from_coords(coords)}" fill="none" stroke="{PURP}" '
        f'stroke-width="{w}" stroke-linejoin="round" stroke-linecap="round" opacity="0.92"/>')
    add(f'<path d="{path_from_coords(coords)}" fill="none" stroke="#e6d6f2" '
        f'stroke-width="{max(1.6,w-3)}" stroke-dasharray="4 4"/>')
def screen_path(pts):
    d=""
    for i,(sx,sy) in enumerate(pts):
        x,y=P(sx,sy); d+=("M" if i==0 else "L")+f"{x:.1f},{y:.1f} "
    return d
def ada_connector(pts):
    """planning placeholder link that CLOSES a gap in the route layers (dashed amber-purple)"""
    add(f'<path d="{screen_path(pts)}" fill="none" stroke="{PURP}" stroke-width="3" '
        f'stroke-dasharray="2 5" stroke-linecap="round" opacity="0.95"/>')
def node(sx,sy,r=4):
    x,y=P(sx,sy)
    add(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r}" fill="#fff" stroke="{PURP}" stroke-width="2.2"/>')
def ada_entry(pt,txt):
    sx,sy=pt
    x,y=P(sx,sy)
    add(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="9" fill="{PURP}" stroke="#fff" stroke-width="1.5"/>')
    add(f'<text x="{x:.0f}" y="{y+3.2:.0f}" font-size="11" fill="#fff" text-anchor="middle" '
        f'font-weight="bold">&#9855;</text>')
    add(f'<text x="{x:.0f}" y="{y-13:.0f}" font-size="9.5" fill="{PURP}" text-anchor="middle" '
        f'font-weight="bold">{txt}</text>')

routeA=[f for f in ada if f["properties"]["name"].startswith("accessible_route_A")][0]["geometry"]["coordinates"]
routeB=[f for f in ada if f["properties"]["name"].startswith("accessible_route_B")][0]["geometry"]["coordinates"]
xaisle=[f for f in ada if f["properties"]["name"]=="accessible_cross_aisle_row15"][0]["geometry"]["coordinates"]

add('<g>')
# --- built segments from the layers ---
ada_built(routeA, w=5)            # NW switchback ramp
ada_built(routeB, w=5)            # SE switchback ramp
ada_built(xaisle, w=4)           # row-15 level cross-aisle (ties mid WC)

# --- synthesized connectors REMOVED. The two layer gaps are NOT solved here.
#     Straight chords shown ONLY as INVALID red ghosts; real alignment = engineering note. ---
def ada_ghost(pts, tag):
    add(f'<path d="{screen_path(pts)}" fill="none" stroke="#c0392b" stroke-width="1.5" '
        f'stroke-dasharray="1 5" opacity="0.8"/>')
    mi=pts[len(pts)//2]; gx,gy=P(*mi)
    add(f'<circle cx="{gx:.0f}" cy="{gy:.0f}" r="9" fill="#fff" stroke="#c0392b" stroke-width="1.6"/>')
    add(f'<text x="{gx:.0f}" y="{gy+4:.0f}" font-size="12" fill="#c0392b" text-anchor="middle" '
        f'font-weight="bold">{tag}</text>')
ada_ghost([(-113.3,139.9),(-63.5,110.0)], "✗")   # Route B chord — crosses ~19% grade
ada_ghost([(-56.0,-92.4),(-27.2,83.7)], "✗")     # Route A chord — crosses the 609.1 pond
add('</g>')

# --- WC space pairs (front + mid) on the route ---
add('<g>')
for f in ada:
    if f["properties"].get("type")=="wheelchair_space_pair":
        x,y=f["geometry"]["coordinates"][:2]; px,py=Pg(x,y)
        add(f'<rect x="{px-5:.0f}" y="{py-5:.0f}" width="10" height="10" rx="2" '
            f'fill="{PURP}" stroke="#fff" stroke-width="1.2"/>')
add('</g>')

# --- accessible entries at ramp RIM ends (corrected: rim = higher-elev coord) ---
eA=scr(*routeA[0])      # NW ramp rim (617.75 ft)
eB=scr(*routeB[0])      # SE ramp rim (638.2 ft)  [was wrongly on the 627.66 floor end]
ada_entry(eA, "ADA ENTRY")
ada_entry(eB, "ADA ENTRY")

# --- connectivity note: GAPS UNRESOLVED (no solved geometry) ---
ccx,ccy=150,560
add(f'<rect x="{ccx-8}" y="{ccy-18}" width="346" height="172" rx="8" '
    f'fill="#fff6f4" opacity="0.92" stroke="#c0392b" stroke-width="1.3"/>')
add(f'<text x="{ccx+6}" y="{ccy+2}" font-size="12" font-weight="bold" fill="#c0392b">'
    f'ACCESSIBLE CONNECTION — GAPS UNRESOLVED</text>')
for i,t in enumerate([
    "Ramps do not yet land on the aisle/floor they serve;",
    "✗ red = invalid straight chord (NOT a route).",
    "① Route B → cross-aisle: connect ramp floor landing",
    "    to row-15 cross-aisle by benched level walk along",
    "    the 627–628 ft contour; alignment to be engineered.",
    "② Route A → floor: connect ramp toe to event floor by",
    "    level walk around stage / treatment edge; avoid",
    "    pond crossing; alignment to be engineered.",
    "No connector written to ada_route.geojson until it",
    "passes slope / landing / cross-slope / clear-width /",
    "WC-pad checks (see ada_route_profile.md)."]):
    wt='font-weight="bold"' if t.startswith(("①","②")) else ''
    add(f'<text x="{ccx+6}" y="{ccy+17+i*13:.0f}" font-size="9.6" fill="#3a2b28" {wt}>{t}</text>')
# small ①/② markers next to the two ghost chords
g1x,g1y=P(-88,125); g2x,g2y=P(-41,-4)
for (gx,gy,tag) in [(g1x,g1y-16,"①"),(g2x,g2y-14,"②")]:
    add(f'<text x="{gx:.0f}" y="{gy:.0f}" font-size="12" fill="#c0392b" font-weight="bold" '
        f'text-anchor="middle">{tag}</text>')

# ============================================================
# 7. PRIMARY SIGHTLINE axis (kept clear) — audience -> stage
# ============================================================
sx0,sy0=P(0,150); sx1,sy1=P(0,-8)
add(f'<line x1="{sx0:.0f}" y1="{sy0:.0f}" x2="{sx1:.0f}" y2="{sy1:.0f}" '
    f'stroke="#2f3b41" stroke-width="1.8" stroke-dasharray="9 6" marker-end="url(#arrowblue)"/>')
mx,my=P(20,150)
add(f'<text x="{mx:.0f}" y="{my:.0f}" font-size="12.5" fill="#2f3b41" '
    f'transform="rotate(-90 {mx:.0f} {my:.0f})">PRIMARY SIGHTLINE — kept clear</text>')

# ---- North arrow (north screen dir = (0.5,-0.866) -> up-right) ----
nx,ny=120,150
ndx,ndy=0.5,-0.8660254
add(f'<g stroke="#333" stroke-width="2" fill="#333">')
add(f'<line x1="{nx-ndx*34:.0f}" y1="{ny-ndy*34:.0f}" x2="{nx+ndx*34:.0f}" y2="{ny+ndy*34:.0f}"/>')
add(f'<path d="M{nx+ndx*34:.0f},{ny+ndy*34:.0f} l{-ndx*12-ndy*6:.0f},{-ndy*12+ndx*6:.0f} '
    f'l{ndy*12:.0f},{-ndx*12:.0f} Z"/>')
add('</g>')
add(f'<text x="{nx+ndx*46:.0f}" y="{ny+ndy*46+4:.0f}" font-size="14" font-weight="bold" '
    f'text-anchor="middle" fill="#333">N</text>')

# ---- scale bar (50 ft) ----
bx,by=90,1095; L=50*SCALE
add(f'<line x1="{bx}" y1="{by}" x2="{bx+L:.0f}" y2="{by}" stroke="#333" stroke-width="3"/>')
add(f'<line x1="{bx}" y1="{by-5}" x2="{bx}" y2="{by+5}" stroke="#333" stroke-width="2"/>')
add(f'<line x1="{bx+L:.0f}" y1="{by-5}" x2="{bx+L:.0f}" y2="{by+5}" stroke="#333" stroke-width="2"/>')
add(f'<text x="{bx+L/2:.0f}" y="{by-9}" font-size="12" text-anchor="middle" fill="#333">50 ft</text>')

# =====================  LABELS  =====================
def label(tx, ty, anchor, lines, lx, ly, color="#222", box=True):
    """leader from (lx,ly) data-px to text block at (tx,ty)."""
    add(f'<line x1="{lx:.0f}" y1="{ly:.0f}" x2="{tx:.0f}" y2="{ty:.0f}" '
        f'stroke="{color}" stroke-width="1.1" opacity="0.8"/>')
    add(f'<circle cx="{lx:.0f}" cy="{ly:.0f}" r="2.6" fill="{color}"/>')
    dy=0
    fw='font-weight="bold"'
    for i,(t,sz,w) in enumerate(lines):
        add(f'<text x="{tx:.0f}" y="{ty+dy:.0f}" font-size="{sz}" text-anchor="{anchor}" '
            f'fill="{color}" {"font-weight=\"bold\"" if w else ""}>{t}</text>')
        dy+=sz+2

# STAGE
sx,sy=P(0,-13)
label(905, 412, "start", [("STAGE",17,True),
       ("performance platform 52×26 ft",12,False),
       ("floor 613.0 ft NAVD88",12,False),
       ("(rec. band 612.0–613.0; grade @613.0)",10.5,False)], sx, sy, "#2f3b41")
# AUDIENCE FLOOR
ax2,ay2=P(34,55)
label(905, 500, "start", [("AUDIENCE FLOOR",16,True),
       ("event floor / orchestra forecourt",12,False),
       ("flat accessible seating at grade",12,False)], ax2, ay2, "#8a6d2f")
# SEATING TERRACES
tx2,ty2=P(70,150)
label(905, 600, "start", [("SEATING TERRACES",16,True),
       ("30 terraced rows · ±30° fan",12,False),
       ("~1,790 planning-seat equiv. (est.)",12,False),
       ("final cap. subject to code/egress/ADA",10.5,False),
       ("C-value ≥ 90 mm all rows",12,False)], tx2, ty2, "#6e5d2c")
# BIORETENTION / FOREBAY
bx2,by2=P(-30,-70)
label(150, 250, "start", [("REFLECTING STORMWATER GARDEN",13.5,True),
       ("bioretention / forebay cell — RELOCATED",11,True),
       ("below-stage foreground, outside the",11,False),
       ("primary seating floor (off sightline)",11,False),
       ("bowl bottom 609.1 ft · pool to 611.3 ft",11,False),
       ("forebay → WQ cell → control outlet",11,False)], bx2, by2, "#2f6b4e")
# ACCESSIBLE ROUTE
rx2,ry2=P(-52,-112)
label(150, 462, "start", [("ACCESSIBLE ROUTE",15,True),
       ("proposed alignment — concept",12,False),
       ("switchback ramps + row-15 cross-aisle",12,False),
       ("□ dispersed WC space pairs",12,False),
       ("grades/landings/rails/WC: ADA design TBD",10.5,False)], rx2, ry2, "#5b2d7a")

# ---- bay direction cue (beyond stage) ----
byx,byy=P(0,-120)
add(f'<text x="{byx:.0f}" y="{byy:.0f}" font-size="12.5" fill="#2a6f97" font-style="italic" '
    f'text-anchor="middle">↑ view past stage to Little Traverse Bay (az 330°)</text>')

# ---- revision note box (upper-right) ----
rnx,rny=720,150
add(f'<rect x="{rnx}" y="{rny}" width="420" height="118" rx="9" '
    f'fill="#ffffff" opacity="0.85" stroke="#b23b2e" stroke-width="1.3"/>')
add(f'<text x="{rnx+16}" y="{rny+26}" font-size="14" font-weight="bold" fill="#b23b2e">'
    f'REVISION — this sheet</text>')
notes=["Forebay + bioretention WQ cell moved OUT of the audience",
       "floor and off the audience→stage sightline.",
       "Relocated to the NW bowl bottom (609.1 ft) beyond the",
       "stage as reflecting foreground + inflow forebay on the",
       "W flank, feeding the existing control structure/outlet."]
for i,t in enumerate(notes):
    add(f'<text x="{rnx+16}" y="{rny+46+i*15:.0f}" font-size="11.5" fill="#3a3a3a">{t}</text>')

# ---- spot elevations (sampled from proposed grade, NAVD88 ft) ----
def spot(sx, sy, elev, dx=8, dy=-6):
    px, py = P(sx, sy)
    add(f'<g>')
    add(f'<path d="M{px-4:.0f},{py:.0f} L{px+4:.0f},{py:.0f} M{px:.0f},{py-4:.0f} '
        f'L{px:.0f},{py+4:.0f}" stroke="#444" stroke-width="1.4"/>')
    add(f'<text x="{px+dx:.0f}" y="{py+dy:.0f}" font-size="10.5" fill="#333" '
        f'font-weight="bold">▲{elev}</text>')
    add('</g>')
spot(0, 0, "613.0", dx=10, dy=-7)        # stage / event floor
spot(0, -82, "609.1", dx=-44, dy=2)      # treatment cell bottom
spot(-52, -78, "609.4", dx=8, dy=14)     # relocated forebay
spot(0, 85, "613.8", dx=10, dy=4)        # row 1 tread
spot(0, 127, "627.7", dx=10, dy=4)       # row 15 cross-aisle
spot(0, 170, "642.6", dx=10, dy=4)       # back-row rim

# ---- drainage-verified note (gravity routing check) ----
dvx, dvy = 720, 282
add(f'<rect x="{dvx}" y="{dvy}" width="420" height="86" rx="9" '
    f'fill="#ffffff" opacity="0.85" stroke="#2f6b4e" stroke-width="1.3"/>')
add(f'<text x="{dvx+16}" y="{dvy+24}" font-size="13.5" font-weight="bold" fill="#2f6b4e">'
    f'✓ GRAVITY DRAINAGE (planning-grade)</text>')
for i, t in enumerate([
    "Proposed grade falls floor 613.0 → cell 609.1 ft (~3.9 ft),",
    "monotonic. Bowl bottom already held as a flat 609.1 pan;",
    "relocation is a relabel within the graded cell — no re-cut."]):
    add(f'<text x="{dvx+16}" y="{dvy+42+i*14:.0f}" font-size="11" fill="#3a3a3a">{t}</text>')

# ---- title block ----
add('<g>')
add(f'<text x="40" y="56" font-size="23" font-weight="bold" fill="#1d2730">'
    f'Petoskey Pit Amphitheater — Revised Close-Up Plan</text>')
add(f'<text x="40" y="80" font-size="14" fill="#44525c">'
    f'Treatment train relocated off the primary audience-to-stage sightline · '
    f'audience faces az 330° (Little Traverse Bay)</text>')
add(f'<text x="40" y="100" font-size="11.5" fill="#8a6d2f" font-style="italic">'
    f'Planning-grade — not stamped engineering. Geometry from package/05_seating &amp; 07_stormwater. '
    f'Dashed red = prior treatment position · red ✗ chord = invalid (un-engineered) connector.</text>')
add('</g>')

# ---- mini legend (bottom-right) ----
lx0,ly0=880,1000
items=[("#5b6b73","Stage / platform"),
       ("#e7ddc2","Audience floor"),
       ("#cdbd8f","Seating terraces"),
       ("#9ccada","Bioretention / forebay (relocated)"),
       ("#7a3fa0","Accessible route + WC spaces"),
       ("#fff7d6","Clear sightline corridor")]
add(f'<rect x="{lx0-14}" y="{ly0-22}" width="290" height="{len(items)*22+18}" '
    f'rx="8" fill="#ffffff" opacity="0.82" stroke="#b9a878"/>')
for i,(c,t) in enumerate(items):
    yy=ly0+i*22
    add(f'<rect x="{lx0}" y="{yy-11}" width="18" height="14" rx="2" fill="{c}" '
        f'stroke="#666" stroke-width="0.7"/>')
    add(f'<text x="{lx0+26}" y="{yy}" font-size="12" fill="#333">{t}</text>')

add('</svg>')

dst=os.path.join(ROOT,"package/01_layout/revised_closeup_plan.svg")
open(dst,"w").write("\n".join(out))
print("wrote", dst, f"({os.path.getsize(dst)} bytes)")
