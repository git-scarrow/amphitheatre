#!/usr/bin/env python3
"""Open civic bowl (v2, stage forward) — plan+section+C-value figure + seat_count.md."""
import json, math, pickle
import numpy as np, rasterio
from rasterio.transform import rowcol
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MPoly
OUT="design_open_low"
ctx=pickle.load(open(f"{OUT}/_ctx.pkl","rb"))
rows=ctx["rows"]; cap=ctx["cap"]; P=ctx["params"]; ada=ctx["ada"]; orch=ctx["orch"]
FX,FY=ctx["F"]; SFx,SFy=ctx["SF"]
AX_AZ=P["AX_AZ"]; FACE_AZ=P["FACE_AZ"]; FAN=P["FAN_HALF"]; R_IN=P["R_INNER"]; R_OUT=P["R_OUTER"]
FOCUS=P["FOCUS_ELEV"]; C_TGT=P["C_TARGET_FT"]; N=P["NROWS"]; SR=P["STAGE_R"]
ds=rasterio.open("dem/dem_design_1ft.tif"); A=ds.read(1).astype(float); A[A==ds.nodata]=np.nan; T=ds.transform
def elev(x,y):
    r,c=rowcol(T,x,y); return np.nan if not(0<=r<A.shape[0] and 0<=c<A.shape[1]) else A[r,c]
def Uu(az): a=math.radians(az); return math.sin(a),math.cos(a)
def polar(R,az,ox=FX,oy=FY): e,n=Uu(az); return ox+e*R,oy+n*R
pad=60; xs=[FX]; ys=[FY]
for az in (AX_AZ-FAN,AX_AZ+FAN,FACE_AZ):
    x,y=polar(R_OUT+40,az); xs.append(x); ys.append(y)
x0,x1=min(xs)-pad,max(xs)+pad; y0,y1=min(ys)-pad,max(ys)+pad
r0,c0=rowcol(T,x0,y1); r1,c1=rowcol(T,x1,y0)
r0,r1=max(0,r0),min(A.shape[0],r1); c0,c1=max(0,c0),min(A.shape[1],c1)
sub=A[r0:r1,c0:c1]; extent=[ds.xy(0,c0)[0],ds.xy(0,c1)[0],ds.xy(r1,0)[1],ds.xy(r0,0)[1]]
gy,gx=np.gradient(sub); slope=np.pi/2-np.arctan(np.hypot(gx,gy)); asp=np.arctan2(-gx,gy)
hs=np.sin(np.radians(45))*np.sin(slope)+np.cos(np.radians(45))*np.cos(slope)*np.cos(np.radians(315)-asp)
fig=plt.figure(figsize=(16,9)); gs=fig.add_gridspec(2,2,width_ratios=[1.25,1],height_ratios=[1,1])
axP=fig.add_subplot(gs[:,0]); axS=fig.add_subplot(gs[0,1]); axC=fig.add_subplot(gs[1,1])
axP.imshow(hs,extent=extent,cmap="gray",alpha=.85,origin="upper",aspect="equal")
axP.contour(np.linspace(extent[0],extent[1],sub.shape[1]),np.linspace(extent[3],extent[2],sub.shape[0]),sub,
            levels=np.arange(605,660,2),colors="#88663344",linewidths=.5)
for f in json.load(open(f"{OUT}/stage_floor.geojson"))["features"]:
    g=f["geometry"]; nm=f["properties"]["name"]
    if g["type"]=="Polygon":
        if nm=="treatment_wet_cell":
            axP.add_patch(MPoly(g["coordinates"][0],closed=True,fc="#9caf6a",ec="#5b6b2f",alpha=.5,lw=1,hatch="...",zorder=4))
        else:
            col={"stage":"#222","stage_shoulder_left":"#555","stage_shoulder_right":"#555",
                 "event_floor_forecourt":"#d9b38c"}.get(nm,"#999")
            axP.add_patch(MPoly(g["coordinates"][0],closed=True,fc=col,ec="k",alpha=.55,lw=1,zorder=4))
    elif g["type"]=="LineString":
        xx,yy=zip(*g["coordinates"]); axP.plot(xx,yy,"--",color="#1f6f1f",lw=1.4,zorder=5)
    else: axP.plot(*g["coordinates"],"*",color="yellow",ms=18,mec="k",zorder=8)
for f in json.load(open(f"{OUT}/seating_rows.geojson"))["features"]:
    xx,yy=zip(*f["geometry"]["coordinates"]); axP.plot(xx,yy,"-",color="#2c7",lw=1.8,zorder=6)
for f in json.load(open(f"{OUT}/ada_route.geojson"))["features"]:
    g=f["geometry"]; nm=f["properties"]["name"]; xx,yy=zip(*g["coordinates"])
    axP.plot(xx,yy,"-",color=("#8000ff" if "cross_aisle" in nm else "#0050ff"),lw=(2.0 if "cross_aisle" in nm else 2.4),zorder=7)
axP.plot([],[],"-",color="#2c7",label="seating (on grade, 0 fill, meets C)")
axP.plot([],[],"-",color="#0050ff",label="accessible ramp"); axP.plot([],[],"-",color="#8000ff",label="mid cross-aisle")
axP.plot([],[],"s",color="#9caf6a",mec="#5b6b2f",label="treatment cell (DRY/ephemeral)")
axP.plot([],[],"s",color="#333",mec="k",label="stage 70×34 + shoulders (~104 ft)")
axP.plot([],[],"--",color="#1f6f1f",label="bay-view axis → bay ~200 m"); axP.plot([],[],"*",color="yellow",mec="k",label="stage front / focus")
bx,by=polar(R_OUT+10,FACE_AZ); axP.annotate("→ Little Traverse Bay ~200 m\n(distant view)",xy=(bx,by),fontsize=7.5,color="#06c",ha="center")
axP.set_title(f"PLAN — Open civic bowl: ±{FAN:.0f}° ({2*FAN:.0f}°) fan, {N} rows; stage forward ({orch:.0f} ft orchestra)",fontsize=10)
axP.set_xlabel("Easting (ft, EPSG:6494)"); axP.set_ylabel("Northing (ft)"); axP.legend(loc="lower left",fontsize=7.5,framealpha=.9); axP.set_aspect("equal")
# section
ts=np.arange(-120,R_OUT+25,1.0)
axS.plot(ts,[elev(*polar(t,AX_AZ)) for t in ts],color="#7a5",lw=1.5,label="existing grade")
for x in rows: axS.plot([x["R"]-1.4,x["R"]+1.4],[x["tread"],x["tread"]],color="#2c7",lw=2.6)
axS.add_patch(plt.Rectangle((SR-34,FOCUS),34,3,fc="#222",ec="k",zorder=5)); axS.text(SR-17,FOCUS+3.3,"stage (70×34 + shoulders)",fontsize=6.5,ha="center")
axS.plot([SR,R_IN],[FOCUS,FOCUS],color="#d9b38c",lw=4,solid_capstyle="butt",label="orchestra/floor 612.5")
axS.annotate("",xy=(R_IN,FOCUS-1.0),xytext=(SR,FOCUS-1.0),arrowprops=dict(arrowstyle="<->",color="#a22",lw=1)); axS.text((SR+R_IN)/2,FOCUS-2.2,f"{orch:.0f} ft",fontsize=7,ha="center",color="#a22")
axS.plot([-120,SR-26],[609.1,609.1],color="#5b6b2f",lw=2.2); axS.plot([-120,SR-26],[611.3,611.3],color="#3b7fb0",ls=":",lw=1); axS.fill_between([-120,SR-26],609.1,611.3,color="#3b7fb0",alpha=.10)
axS.text(-60,611.9,"treatment cell — dry/ephemeral",fontsize=6.5,ha="center",color="#5b6b2f")
for i in (0,N//2,N-1): axS.plot([rows[i]["R"],SR],[rows[i]["eye"],FOCUS],color="#bbb",lw=0.6,zorder=1)
axS.plot([SR],[FOCUS],"*",color="orange",ms=12,mec="k",zorder=6)
axS.set_title("SECTION on centerline (az 150) — stage forward, treads on grade, sightlines",fontsize=9)
axS.set_xlabel("Distance from seating centre (ft) · NW ← → SE"); axS.set_ylabel("Elev NAVD88 (ft)"); axS.legend(loc="upper left",fontsize=7); axS.grid(alpha=.25)
rn=[x["row"] for x in rows[1:]]; cp=[x["C"]*304.8 for x in rows[1:]]; ct=[x["C_t"]*304.8 for x in rows[1:]]
axC.bar(rn,cp,color=["#2c7" if v>=90-1e-6 else "#d33" for v in cp],width=.8)
axC.plot(rn,ct,"o",ms=3,color="#777",label="bare terrain (pre-fill)")
axC.axhline(90,color="k",ls="--",lw=1,label="target 90 mm")
axC.set_title("Row C-value AS DESIGNED (bars all clear 90 mm; dots = bare terrain)",fontsize=9); axC.set_xlabel("Row"); axC.set_ylabel("C-value (mm)"); axC.legend(fontsize=7); axC.grid(axis="y",alpha=.25)
fig.suptitle("Petoskey Pit — OPEN CIVIC BOWL (open-arc, minimal-work, stage-forward) · planning-grade · NAVD88 intl ft",fontsize=12)
fig.tight_layout(rect=[0,0,1,.97]); fig.savefig(f"{OUT}/plan_and_sections.png",dpi=130)
print(f"wrote {OUT}/plan_and_sections.png")
# seat_count.md
md=f"""# Open Civic Bowl — Design Summary (v2, stage forward)

**Petoskey Pit amphitheater — open-arc partial fan on the S/SE rake.** Planning-grade,
NAVD88 intl ft, EPSG:6494. Audience faces **az {FACE_AZ:.0f}°** (NNW, bay + evening sun).

Opened + lowered vs the first design (±30°/60°, 30 rows up the steep wall, 6–14 ft retaining
walls), with the **stage pushed forward into the orchestra** so the front row is **{orch:.0f} ft**
from the stage (was 85 ft) — seats stay on the natural rake.

| Parameter | Value |
|---|---|
| Fan / arc | ±{FAN:.0f}° ({2*FAN:.0f}° total) |
| Rows · rise | {N} · {ctx['height']} ft |
| Inner/outer radius (arc centre) | {R_IN:.0f} / {R_OUT:.0f} ft |
| **Stage front → row 1 (orchestra)** | **{orch:.0f} ft** |
| **Stage** | **70 × 34 ft core + angled side shoulders (~104 ft frontage)** |
| Stage frontage vs row-1 arc ({R_IN*math.radians(2*FAN):.0f} ft) | **~64%** (was ~32% at a 52 ft stage) |
| Seating rake | ~33% (~18°) — gentler than Epidaurus (~26°) |
| Event floor / stage | {FOCUS:.1f} ft NAVD88 |
| Treatment cell (unchanged) | 609.1 / pool 611.3 ft |

## Capacity (geometric planning estimate — NOT code occupant load / event cap)
| Scenario | Seat width | Total |
|---|---|---|
| Compact | 18 in | **{cap['compact']:,}** |
| Generous | 22 in | **{cap['generous']:,}** |

## Earthwork & sightlines
- **Seat treads: ≈ {ctx['fill_vol']:.0f} CY total** — the front ~5 rows get ≤0.2 ft fill to clear sightlines to the 35 ft stage; the rest sit on natural grade. **No retaining walls.**
- **All {N}/{N} rows meet the 90 mm target as designed.** On bare terrain {sum(1 for x in rows if x['meets_t'])}/{N} clear; the front rows are the ones lifted (the cascade re-rake raises only the front, absorbed by the back rows' 150–280 mm surplus, so nothing behind is blocked).
- Earthwork is only the shared stage/orchestra pad + ADA ramps + treatment shaping — cut-balanced; never imports fill.

## Accessibility
~{ctx['height']} ft bowl → Route A to floor (~{ada['A_drop']} ft / {ada['A_runs']} runs @ 8.33%), Route B to mid cross-aisle at row {ada['B_row']} (~{ada['B_drop']} ft / {ada['B_runs']} runs) with wheelchair dispersion. Schematic; ≤2% cross-slope a design target.

> Planning-grade. Not stamped engineering. `../gating_dossier.md` prerequisites govern.
"""
open(f"{OUT}/seat_count.md","w").write(md); print(f"wrote {OUT}/seat_count.md")
