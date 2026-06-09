#!/usr/bin/env python3
"""True-scale (1:1) centerline section — stage pushed forward into the orchestra."""
import math, pickle, numpy as np, rasterio
from rasterio.transform import rowcol
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
ctx=pickle.load(open("design_open_low/_ctx.pkl","rb"))
rows=ctx["rows"]; P=ctx["params"]; FX,FY=ctx["F"]; orch=ctx["orch"]
AX_AZ=P["AX_AZ"]; R_IN=P["R_INNER"]; R_OUT=P["R_OUTER"]; FOCUS=P["FOCUS_ELEV"]; SR=P["STAGE_R"]
ds=rasterio.open("dem/dem_design_1ft.tif"); A=ds.read(1).astype(float); A[A==ds.nodata]=np.nan; T=ds.transform
def elev(x,y):
    r,c=rowcol(T,x,y); return np.nan if not(0<=r<A.shape[0] and 0<=c<A.shape[1]) else A[r,c]
def U(az): a=math.radians(az); return math.sin(a),math.cos(a)
def polar(R,az): e,n=U(az); return FX+e*R,FY+n*R
toe=rows[0]["tread"]; topT=rows[-1]["tread"]
rise=topT-toe; run=rows[-1]["R"]-rows[0]["R"]; slope=rise/run; ang=math.degrees(math.atan(slope))
steps=[r["rise"] for r in rows[1:]]; mx=max(steps); mxrow=rows[1+steps.index(mx)]["row"]
fig,ax=plt.subplots(figsize=(14,3.8))
ts=np.arange(-120,R_OUT+25,1.0)
ax.plot(ts,[elev(*polar(t,AX_AZ)) for t in ts],color="#7a5",lw=1.6,label="existing grade",zorder=2)
for r in rows: ax.plot([r["R"]-1.5,r["R"]+1.5],[r["tread"],r["tread"]],color="#2c7",lw=3,solid_capstyle="butt",zorder=4)
# stage pushed forward: downstage edge at SR, 34 ft deep toward NW
ax.add_patch(plt.Rectangle((SR-34,FOCUS),34,3.2,fc="#222",ec="k",zorder=6)); ax.text(SR-17,FOCUS+3.6,"stage 70×34 (+shoulders)",fontsize=8,ha="center")
# orchestra apron between stage front and row1
ax.plot([SR,R_IN],[FOCUS,FOCUS],color="#d9b38c",lw=5,solid_capstyle="butt",label="event floor / orchestra",zorder=3)
ax.annotate("",xy=(R_IN,FOCUS-1.2),xytext=(SR,FOCUS-1.2),arrowprops=dict(arrowstyle="<->",color="#a22",lw=1.3))
ax.text((SR+R_IN)/2,FOCUS-2.4,f"orchestra {orch:.0f} ft\n(was 85 ft)",fontsize=8,ha="center",color="#a22")
ax.plot([-120,SR-26],[609.1,609.1],color="#5b6b2f",lw=2.6,zorder=2)            # dry cell bottom (no standing water)
ax.plot([-120,SR-26],[611.3,611.3],color="#3b7fb0",ls=":",lw=1,zorder=2)
ax.fill_between([-120,SR-26],609.1,611.3,color="#3b7fb0",alpha=.10,zorder=1)
ax.text(-68,612.4,"treatment cell — dry/ephemeral",fontsize=7.5,ha="center",color="#5b6b2f")
ax.text(-118,624.5,"\u2190 Little Traverse Bay ~200 m  (distant view, not on-site)",fontsize=8,color="#06c")
# sightline rays from a few rows to the (forward) focus
for i in (0,len(rows)//2,len(rows)-1):
    ax.plot([rows[i]["R"],SR],[rows[i]["eye"],FOCUS],color="#bbb",lw=0.6,zorder=1)
ax.plot([SR],[FOCUS],"*",color="orange",ms=13,mec="k",zorder=7)
ax.plot([rows[0]["R"],rows[-1]["R"]],[toe,topT],color="#c33",ls="--",lw=1.1,zorder=5)
ax.text(118,623,f"rake ≈ {slope*100:.0f}% ({ang:.0f}°)",fontsize=9,color="#a22")
ax.set_aspect("equal")
ax.set_title(f"TRUE-SCALE section (1:1) — row 1 is {orch:.0f} ft from stage; rake ≈ {ang:.0f}°; {sum(1 for x in rows if x['meets'])}/{len(rows)} rows clear 90 mm as designed (front rows +≤0.2 ft fill)",fontsize=9.5)
ax.set_xlabel("Distance from seating centre (ft) · NW ← → SE upslope"); ax.set_ylabel("Elev NAVD88 (ft)")
ax.legend(loc="upper left",fontsize=8); ax.grid(alpha=.25)
fig.tight_layout(); fig.savefig("design_open_low/section_truescale.png",dpi=140)
print(f"orchestra row1->stage = {orch:.0f} ft; rake {slope*100:.0f}% ({ang:.1f}°); steepest step {mx:.2f}ft row{mxrow}")
