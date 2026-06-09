#!/usr/bin/env python3
"""
DESIGN: "Corner bowl" v2 — ONE authored master terrace curve, family by OFFSET.

Per the directive: do NOT fit each row. Author the plan logic once as a master
three-regime terrace curve (S/SW flank -> middle bend -> E/NE flank, fair / G2),
then DERIVE the whole row family by normal-offset from it, and only locally trim
at ends / promenade / side-banks. "Define the plan logic once, derive the family."

Master  : a single fair (C2) smoothing spline through the datum contour in the
          seating sector -> captures flank-bend-flank, no per-row wiggle. (Swap-in
          point for an explicit line-clothoid-arc-clothoid-line if parametric
          control of flank bearing / bend radius is wanted.)
Family  : rows = master offset by k*TREAD along its unit normal. Outward/up-slope
          offsets (convex) fan safely; inner offsets (toward stage, concave) are
          the forecourt and are bounded by the bend radius (~the orchestra opening).
          All rows share the master's three-regime character + parallel spacing.
Trim    : ONE asymmetric index window on the master (east/hook capped early, west
          extended to wrap) applied to every row -> coherent family. Tiers:
          core (window) / bay (reclaimed inner flank) / lawn (trimmed ends).
Seats toe-in to the stage. Planning-grade. EPSG:6494 NAVD88. -> design_corner_bowl/
"""
import json, csv, math, os
import numpy as np, rasterio
from rasterio.transform import rowcol
from scipy.ndimage import gaussian_filter, gaussian_filter1d
from scipy.interpolate import splprep, splev
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

DEM="dem/dem_design_1ft.tif"; OUT="design_corner_bowl"; os.makedirs(OUT,exist_ok=True)
CX,CY=19533067.7,750799.2
AX_AZ=132.0; FACE_AZ=(AX_AZ+180)%360
FOCUS_ELEV=612.5; F_T=15.0; EYE_HT=3.94; STAGE_R=50.0
C_TARGET_FT=0.295; SEAT_W_G=1.83; AISLE=0.18
TREAD=3.0; N_INNER=4; N_OUTER=12; DATUM_RC=100.0
SAMP_FAN=72.0                    # sector half-width to harvest the datum contour
SMOOTH_K=3.0                     # master spline smoothing (x #pts) -> fair, few-DOF
EAST_CORE=70.0; WEST_CORE=96.0   # core flank lengths from the bend apex (ft) -- asymmetric
BAY_EXTRA=22.0                   # reclaimed-bay extension beyond core each side (ft)
PROMENADE_K=0                    # offset index treated as the promenade spine (datum row)

ds=rasterio.open(DEM); A0=ds.read(1).astype(float); A0[A0==ds.nodata]=np.nan; T=ds.transform
A=A0.copy(); m=np.isfinite(A0); A[~m]=np.nanmean(A0[m]); A=gaussian_filter(A,sigma=3.0); A[~m]=np.nan
def elev(x,y):
    r,c=rowcol(T,x,y); return np.nan if not(0<=r<A.shape[0] and 0<=c<A.shape[1]) else A[r,c]
def U(az): a=math.radians(az); return math.sin(a),math.cos(a)
UX,UY=U(AX_AZ); FX,FY=CX+UX*F_T,CY+UY*F_T
SFx,SFy=FX+UX*STAGE_R,FY+UY*STAGE_R
def polar(R,az,ox=FX,oy=FY): e,n=U(az); return ox+e*R,oy+n*R
def ec(r): return elev(*polar(r,AX_AZ))
Xc=T.c+(np.arange(A.shape[1])+0.5)*T.a; Yc=T.f+(np.arange(A.shape[0])+0.5)*T.e

# ---------- 1) AUTHOR the master curve from the datum contour ----------
E_DATUM=float(ec(DATUM_RC))
_ax=plt.subplots()[1]
segs=_ax.contour(Xc,Yc,A,levels=[E_DATUM]).allsegs[0]
pts=np.vstack(segs)
az=(np.degrees(np.arctan2(pts[:,0]-FX,pts[:,1]-FY)))%360
d=np.hypot(pts[:,0]-FX,pts[:,1]-FY)
sel=pts[(az>=AX_AZ-SAMP_FAN)&(az<=AX_AZ+SAMP_FAN)&(d<170)]
sel=sel[np.isfinite(sel).all(1)]
o=np.argsort((np.degrees(np.arctan2(sel[:,0]-FX,sel[:,1]-FY)))%360); sel=sel[o]
keep=[0]                                                    # drop near-duplicate points for splprep
for i in range(1,len(sel)):
    if math.hypot(*(sel[i]-sel[keep[-1]]))>0.7: keep.append(i)
sel=sel[keep]
tck,_=splprep([sel[:,0],sel[:,1]],s=len(sel)*SMOOTH_K,k=3)
uu=np.linspace(0,1,400); mx,my=splev(uu,tck)
# resample master to uniform 1-ft arc length
seg=np.hypot(np.diff(mx),np.diff(my)); s=np.concatenate([[0],np.cumsum(seg)]); Lm=s[-1]
su=np.arange(0,Lm,1.0); mx=np.interp(su,s,mx); my=np.interp(su,s,my)
M=np.column_stack([mx,my])
# tangent, unit normal (smoothed), signed up-slope (+n = higher ground)
tx=np.gradient(gaussian_filter1d(mx,2)); ty=np.gradient(gaussian_filter1d(my,2))
tl=np.hypot(tx,ty)+1e-9; tx/=tl; ty/=tl
nx,ny=-ty,tx
e_plus=np.array([elev(M[i,0]+8*nx[i],M[i,1]+8*ny[i]) for i in range(len(M))])
e_minus=np.array([elev(M[i,0]-8*nx[i],M[i,1]-8*ny[i]) for i in range(len(M))])
if np.nanmean(e_plus)<np.nanmean(e_minus): nx,ny=-nx,-ny    # +n points up-slope (toward back rows)
# master curvature profile (verify three regimes)
ddx=np.gradient(tx); ddy=np.gradient(ty); kappa=np.abs(tx*ddy-ty*ddx)+1e-9
Rprof=1.0/kappa; apex=int(np.argmin(gaussian_filter1d(Rprof,5)))

# ---------- 2) DERIVE the family by offset; ONE asymmetric trim window ----------
# core index window on the master (asymmetric about the bend apex), shared by all rows
lo_core=max(0,apex-int(EAST_CORE)); hi_core=min(len(M),apex+int(WEST_CORE))
lo_bay=max(0,lo_core-int(BAY_EXTRA)); hi_bay=min(len(M),hi_core+int(BAY_EXTRA))
def offset_row(k):
    P=M+np.column_stack([nx,ny])*(k*TREAD)
    return P
def seglen(P): return float(np.hypot(*(P[1:]-P[:-1]).T).sum())
def plen(Q): return float(sum(math.dist(Q[i],Q[i+1]) for i in range(len(Q)-1))) if len(Q)>1 else 0.0

rows=[]
for k in range(-N_INNER, N_OUTER+1):
    P=offset_row(k)
    # self-intersection guard for inner (concave) offsets: drop if any segment collapses
    sl=np.hypot(*(P[1:]-P[:-1]).T)
    if k<0 and sl.min()<0.2:
        continue
    coreP=[[round(P[j,0],2),round(P[j,1],2)] for j in range(lo_core,hi_core)]
    bayL=[[round(P[j,0],2),round(P[j,1],2)] for j in range(lo_bay,lo_core)]
    bayR=[[round(P[j,0],2),round(P[j,1],2)] for j in range(hi_core,hi_bay)]
    lawnL=[[round(P[j,0],2),round(P[j,1],2)] for j in range(0,lo_bay)]
    lawnR=[[round(P[j,0],2),round(P[j,1],2)] for j in range(hi_bay,len(P))]
    # level tread = median terrain over the core span; grade spread = leveling residual
    zc=np.array([elev(P[j,0],P[j,1]) for j in range(lo_core,hi_core)])
    zc=zc[np.isfinite(zc)]
    if len(zc)<5: continue
    E_k=float(np.median(zc)); resid=float(np.percentile(np.abs(zc-E_k),90))
    earth=float(np.mean(np.abs(zc-E_k)))*plen([[P[j,0],P[j,1]] for j in range(lo_core,hi_core)])*TREAD/27.0
    # distance from stage at the centreline crossing
    azc=(np.degrees(np.arctan2(P[:,0]-FX,P[:,1]-FY)))%360
    off=((azc-AX_AZ+180)%360)-180; ccx=int(np.argmin(np.abs(off)))
    rcen=math.hypot(P[ccx,0]-FX,P[ccx,1]-FY)
    zone="forecourt" if k<0 else "civic"
    fam=("forecourt" if k<0 else ("promenade" if k==PROMENADE_K else
         ("lower" if k<=3 else ("middle" if k<=7 else "upper"))))
    kind="promenade" if fam=="promenade" else "seating"
    rows.append(dict(k=k,zone=zone,family=fam,kind=kind,elev=round(E_k,2),
        dist=round(rcen-STAGE_R,1),core=coreP,bays=[b for b in (bayL,bayR) if len(b)>=4],
        lawn=[l for l in (lawnL,lawnR) if len(l)>=4],
        core_len=round(plen(coreP),1),bay_len=round(plen(bayL)+plen(bayR),1),
        lawn_len=round(plen(lawnL)+plen(lawnR),1),grade_resid=round(resid,2),earth_cy=round(earth,1)))

rows.sort(key=lambda r:r["k"])
for i,x in enumerate(rows): x["row"]=i+1

# ---------- sightlines (centreline) + seats + bay ----------
pr=pe=None
for x in rows:
    D=x["dist"]
    if x["kind"]!="seating" or pr is None: x["C_mm"]=None
    else:
        Ep=(pe+EYE_HT)-FOCUS_ELEV; E=(x["elev"]+EYE_HT)-FOCUS_ELEV; x["C_mm"]=round((E*(pr/D)-Ep)*304.8)
    if x["kind"]=="seating": pr=D; pe=x["elev"]
    x["eye"]=round(x["elev"]+EYE_HT,2); x["sees_bay"]=bool(x["eye"]>618.5)
def seats(Lf): return max(0,int(Lf*(1-AISLE)//SEAT_W_G))
core_g=bay_g=0; lawn_lf=0.0
for x in rows:
    x["core_seats"]=seats(x["core_len"]) if x["kind"]=="seating" else 0
    x["bay_seats"]=seats(x["bay_len"]) if x["kind"]=="seating" else 0
    core_g+=x["core_seats"]; bay_g+=x["bay_seats"]; lawn_lf+=x["lawn_len"]
formal=core_g+bay_g; lawn_cap=int(lawn_lf*1.5/SEAT_W_G)
# coherence: min spacing between adjacent cores (offset family should never cross)
minspace=99
for a,b in zip(rows,rows[1:]):
    Pa=np.array(a["core"]); Pb=np.array(b["core"])
    if len(Pa)<2 or len(Pb)<2: continue
    minspace=min(minspace,min(np.min(np.hypot(Pb[:,0]-p[0],Pb[:,1]-p[1])) for p in Pa))

# ---------- outputs ----------
CRS={"type":"name","properties":{"name":"urn:ogc:def:crs:EPSG::6494"}}
def fc(f): return {"type":"FeatureCollection","crs":CRS,"features":f}
def Lf(c,p): return {"type":"Feature","properties":p,"geometry":{"type":"LineString","coordinates":c}}
rf=[];bf=[];lf=[]
for x in rows:
    rf.append(Lf(x["core"],{k:x.get(k) for k in["row","k","family","kind","elev","eye","dist","C_mm",
        "sees_bay","grade_resid","core_len","core_seats"]}|{"tier":"core"}))
    for b in x["bays"]: bf.append(Lf(b,{"row":x["row"],"tier":"bay"}))
    for l in x["lawn"]: lf.append(Lf(l,{"row":x["row"],"tier":"lawn"}))
json.dump(fc([Lf([[round(p[0],2),round(p[1],2)] for p in M],{"name":"master_terrace_curve",
    "datum_elev":round(E_DATUM,2),"bend_R_ft":round(float(Rprof[apex]),0)})]),open(f"{OUT}/master_curve.geojson","w"),indent=1)
json.dump(fc(rf),open(f"{OUT}/seating_rows.geojson","w"),indent=1)
json.dump(fc(bf),open(f"{OUT}/seating_bays.geojson","w"),indent=1)
json.dump(fc(lf),open(f"{OUT}/side_banks.geojson","w"),indent=1)
with open(f"{OUT}/composition_table.csv","w",newline="") as fh:
    w=csv.writer(fh); w.writerow(["row","k","family","kind","elev","dist","C_mm","sees_bay",
        "grade_resid","core_len","bay_len","lawn_len","core_seats","bay_seats"])
    for x in rows: w.writerow([x["row"],x["k"],x["family"],x["kind"],x["elev"],x["dist"],x.get("C_mm"),
        x["sees_bay"],x["grade_resid"],x["core_len"],x["bay_len"],x["lawn_len"],x["core_seats"],x["bay_seats"]])

# plan
win=210; c0=int((CX-win-T.c)/T.a);c1=int((CX+win-T.c)/T.a);r1=int((CY-win-T.f)/T.e);r0=int((CY+win-T.f)/T.e)
sub=A0[r0:r1,c0:c1]; ext=[T.c+c0*T.a,T.c+c1*T.a,T.f+r1*T.e,T.f+r0*T.e]
fig,ax=plt.subplots(figsize=(9,9)); ax.imshow(sub,extent=ext,origin="upper",cmap="terrain",alpha=0.8)
cs=ax.contour(np.linspace(ext[0],ext[1],sub.shape[1]),np.linspace(ext[3],ext[2],sub.shape[0])[::-1],sub,
    levels=np.arange(606,634,2),colors="k",linewidths=0.3,alpha=0.4); ax.clabel(cs,fontsize=6,fmt="%d")
col={"forecourt":"tab:red","promenade":"orange","lower":"#7fb8e6","middle":"tab:blue","upper":"#08306b"}
ax.plot(M[:,0],M[:,1],color="k",lw=1.0,ls=":",alpha=0.7)         # master curve
for x in rows:
    ax.plot([p[0] for p in x["core"]],[p[1] for p in x["core"]],color=col.get(x["family"],"gray"),
            lw=2.6 if x["family"]=="promenade" else 1.8)
    for b in x["bays"]: ax.plot([p[0] for p in b],[p[1] for p in b],color="mediumpurple",lw=1.4,ls=(0,(4,2)))
    for l in x["lawn"]: ax.plot([p[0] for p in l],[p[1] for p in l],color="tab:green",lw=0.9,alpha=0.55)
ax.plot(SFx,SFy,"k*",ms=16); ax.annotate("stage",(SFx,SFy),fontsize=8)
ax.annotate("",xy=(SFx+U(FACE_AZ)[0]*90,SFy+U(FACE_AZ)[1]*90),xytext=(SFx,SFy),arrowprops=dict(arrowstyle="->",color="navy",lw=2))
ax.set_aspect("equal"); ax.set_xlabel("EPSG:6494 X (ft)"); ax.set_ylabel("Y (ft)")
ax.set_title("Corner bowl — ONE master curve (dotted) offset into a family\nred=forecourt orange=promenade blue=civic purple=bay green=lawn")
plt.tight_layout(); plt.savefig(f"{OUT}/plan.png",dpi=130); plt.close()

# ---------- summary ----------
sr=[x for x in rows if x["kind"]=="seating"]
nA=len(Rprof)//3
print(f"=== Corner bowl v2 — ONE master curve, family by offset (face {FACE_AZ:.0f}) ===")
print(f"master: datum {E_DATUM:.1f} ft, length {Lm:.0f} ft, three-regime curvature "
      f"flank R~{np.median(Rprof[:nA]):.0f} -> bend R~{Rprof[apex]:.0f} -> flank R~{np.median(Rprof[-nA:]):.0f} ft")
print(f"family: {len([x for x in rows if x['k']<0])} forecourt + {len([x for x in rows if x['k']>=0])} civic = {len(rows)} rows "
      f"(all offsets of the one master)")
print(f"FORMAL seats: core {core_g:,} + bays {bay_g:,} = {formal:,}  [target 1,050-1,200]  lawn ~{lawn_cap:,}")
print(f"family coherence: min adjacent-row spacing {minspace:.2f} ft (>0 = no crossing); "
      f"leveling residual {np.mean([x['grade_resid'] for x in rows if x['zone']=='civic']):.2f} ft mean")
print(f"tread leveling earthwork: {sum(x.get('earth_cy',0) for x in rows):.0f} CY "
      f"(offset rows drift off true contour outward -> more than the on-contour ~140 CY; the price of one authored family)")
print(f"sightline C>=90mm: {sum(1 for x in sr if (x['C_mm'] is None or x['C_mm']>=90))}/{len(sr)}  "
      f"bay rows {[x['row'] for x in rows if x['sees_bay']]}")
print("\n row  k family    elev dist Cmm bay gresid coreL bayL lawnL coreS bayS")
for x in rows:
    print(f" {x['row']:3d} {x['k']:+2d} {x['family']:9s}{x['elev']:6.1f}{x['dist']:5.0f}{str(x.get('C_mm')):>4} "
          f"{'Y' if x['sees_bay'] else '.':>2}{x['grade_resid']:>6}{x['core_len']:>6.0f}{x['bay_len']:>5.0f}"
          f"{x['lawn_len']:>5.0f}{x['core_seats']:>5}{x['bay_seats']:>4}")
print(f"\nwrote {OUT}/master_curve.geojson seating_rows.geojson seating_bays.geojson side_banks.geojson plan.png")
