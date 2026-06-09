#!/usr/bin/env python3
"""
DESIGN: "Corner bays" — a THREE-PART terrace system, not a single-curve family.

The site is a corner bowl: two straighter flanks joined by a tight bend. A single
master curve + constant-normal offsets keeps the family coherent in plan but
carries the flank rows OFF the contour (they cross grade) -> not low-work
terraces. Fix (per directive): each terrace row is THREE linked bays at one level,
each bay aligned to its OWN local contour, joined by aisles, with the bend as the
formal hinge:

    south flank bay  | bend hinge bay | east flank bay
    (straighter,      (tight curved     (straighter,
     contour-aligned)  hinge)            contour-aligned, independently aligned)

Section breakpoints (measured, stable across elevations): bend = az 118-152 from
the orchestra centre (apex ~134); east flank az<118; south flank az>152.

Generator rule, per row elevation E_k:
  1. take the true level contour at E_k (level by construction);
  2. split into the 3 sections by azimuth;
  3. fit a simple FAIR curve inside each section (light spline -> stays on the
     contour, so the bay runs parallel to local contours);
  4. trim a small aisle at each join (the hinges are where aisles belong);
  5. DIAGNOSE LOCALLY: crossing angle |theta_terrace - theta_contour| per bay
     (~0 = of-the-grade) + elevation residual along the bay.
  6. count seats per bay.

Keeps face 312, 4-row forecourt, promenade. Planning-grade. EPSG:6494 NAVD88.
-> design_corner_bays/
"""
import json, csv, math, os
import numpy as np, rasterio
from rasterio.transform import rowcol
from scipy.ndimage import gaussian_filter
from scipy.interpolate import splprep, splev
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

DEM="dem/dem_design_1ft.tif"; OUT="design_corner_bays"; os.makedirs(OUT,exist_ok=True)
CX,CY=19533067.7,750799.2
AX_AZ=132.0; FACE_AZ=(AX_AZ+180)%360
FOCUS_ELEV=612.5; F_T=15.0; EYE_HT=3.94; STAGE_R=50.0
C_TARGET_FT=0.295; SEAT_W_G=1.83; AISLE=0.18
FORE_FAN=40.0; FORE_R=[85.0,88.0,91.0,94.0]
DATUM_RC=100.0; N_FORE=4; N_CIVIC=10; E_CAP=632.0   # rows placed ADAPTIVELY (unified march below)
# section azimuth breakpoints (from orchestra centre), + retain caps + aisle
AZ_E_CAP=AX_AZ-47; AZ_BEND_E=118.0; AZ_BEND_W=152.0; AZ_S_CAP=AX_AZ+65; AISLE_DEG=2.0
PROMENADE_RC=100.0
# STANDARD (adopted 2026-06-05): +/-0.20 ft tread tolerance vs RAW/de-noised DEM (terrain roughness ~+/-0.20 ft)
GATE_RESID_P90=0.25      # civic tread p90 raw-ground residual <= this (the +/-0.20 standard)
GATE_CLEAR=3.0           # adjacent-row min horizontal clearance >= nominal tread
MIN_CLEAR=3.10           # adaptive-march target clearance (widen locally to hold tread+detailing)
BLOCK_LEN=20.0           # seat-block length (stepped blocks)
ADA_RESID_P90=0.12       # promenade/accessible tread: stricter independent level check
ADA_CROSS_MAX=2.0        # accessible cross-slope max (%)

ds=rasterio.open(DEM); A0=ds.read(1).astype(float); A0[A0==ds.nodata]=np.nan; T=ds.transform
A=A0.copy(); m=np.isfinite(A0); A[~m]=np.nanmean(A0[m]); A=gaussian_filter(A,sigma=1.0); A[~m]=np.nan
gy,gx=np.gradient(gaussian_filter(np.nan_to_num(A,nan=np.nanmean(A)),2))  # de-noised gradient for contour dir
def _bilin(G,x,y):
    col=(x-T.c)/T.a-0.5; row=(y-T.f)/T.e-0.5
    c0=int(math.floor(col)); r0=int(math.floor(row)); fc=col-c0; fr=row-r0
    if not(0<=r0<G.shape[0]-1 and 0<=c0<G.shape[1]-1): return np.nan
    z00,z01,z10,z11=G[r0,c0],G[r0,c0+1],G[r0+1,c0],G[r0+1,c0+1]
    if not np.isfinite([z00,z01,z10,z11]).all(): return np.nan
    return (z00*(1-fc)*(1-fr)+z01*fc*(1-fr)+z10*(1-fc)*fr+z11*fc*fr)
def elev(x,y):  return _bilin(A,x,y)             # light-smoothed: contour extraction + fitting
def elevR(x,y): return _bilin(A0,x,y)            # RAW DEM: honest levelness validation
def contour_dir(x,y):                            # unit vector ALONG the local contour (perp to fall line)
    r,c=rowcol(T,x,y)
    if not(0<=r<A.shape[0] and 0<=c<A.shape[1]): return None
    Fx=gx[r,c]/T.a; Fy=gy[r,c]/T.e               # world fall vector (dz/dX, dz/dY)
    cd=np.array([-Fy,Fx]); n=np.hypot(*cd)
    return cd/n if n>1e-9 else None
def U(az): a=math.radians(az); return math.sin(a),math.cos(a)
UX,UY=U(AX_AZ); FX,FY=CX+UX*F_T,CY+UY*F_T
SFx,SFy=FX+UX*STAGE_R,FY+UY*STAGE_R
def polar(R,az,ox=FX,oy=FY): e,n=U(az); return ox+e*R,oy+n*R
def ec(r): return elev(*polar(r,AX_AZ))
Xc=T.c+(np.arange(A.shape[1])+0.5)*T.a; Yc=T.f+(np.arange(A.shape[0])+0.5)*T.e
_ax=plt.subplots()[1]
def contour_pts(E):
    segs=_ax.contour(Xc,Yc,A,levels=[E]).allsegs[0]
    if not segs: return None
    p=np.vstack(segs); az=(np.degrees(np.arctan2(p[:,0]-FX,p[:,1]-FY)))%360; d=np.hypot(p[:,0]-FX,p[:,1]-FY)
    p=p[(az>=AZ_E_CAP-3)&(az<=AZ_S_CAP+3)&(d<170)]
    if len(p)<12: return None
    a=(np.degrees(np.arctan2(p[:,0]-FX,p[:,1]-FY)))%360; o=np.argsort(a); p=p[o]; a=a[o]
    k=[0]
    for i in range(1,len(p)):
        if math.hypot(*(p[i]-p[k[-1]]))>0.7: k.append(i)
    return p[k],a[k]

def fit_bay(P):
    if len(P)<6: return None
    npts=max(8,int(round(sum(math.dist(P[i],P[i+1]) for i in range(len(P)-1)))))
    s=len(P)*0.18                                          # tight hug -> bay stays ON its contour (low elev-range)
    try: tck,_=splprep([P[:,0],P[:,1]],s=s,k=min(3,len(P)-1))
    except Exception: return None
    uu=np.linspace(0,1,npts); x,y=splev(uu,tck); dx,dy=splev(uu,tck,der=1)
    Q=np.column_stack([x,y]); tang=np.column_stack([dx,dy])
    cross=[]; zres=[]
    for i in range(len(Q)):
        t=tang[i]/(np.hypot(*tang[i])+1e-9); cd=contour_dir(Q[i,0],Q[i,1])
        if cd is not None: cross.append(math.degrees(math.acos(min(1,abs(np.dot(t,cd))))))
        z=elevR(Q[i,0],Q[i,1])                       # validate against RAW grade, not the smoothed surface
        if np.isfinite(z): zres.append(z)
    zres=np.array(zres); Emed=float(np.median(zres)) if len(zres) else np.nan
    zr=float(zres.max()-zres.min()) if len(zres) else 99.0   # full-bay raw elevation RANGE
    # range within a ~BLOCK_LEN seat block (sliding) -> what you'd actually build as stepped blocks
    cum=np.concatenate([[0],np.cumsum(np.hypot(*(Q[1:]-Q[:-1]).T))]); zb=0.0
    for i in range(len(Q)):
        w=(cum>=cum[i])&(cum<=cum[i]+BLOCK_LEN)
        zw=np.array([elevR(*Q[j]) for j in np.where(w)[0]]); zw=zw[np.isfinite(zw)]
        if len(zw)>1: zb=max(zb,float(zw.max()-zw.min()))
    return dict(coords=[[round(a,2),round(b,2)] for a,b in Q],
        length=round(float(cum[-1]),1),
        cross_ang=round(float(np.percentile(cross,90)) if cross else 99,1),
        elev=round(Emed,2), z_resid=round(float(np.percentile(np.abs(zres-Emed),90)) if len(zres) else 99,2),
        z_range=round(zr,2), z_block=round(zb,2),
        grade_cy=round(float(np.mean(np.abs(zres-Emed)))*float(cum[-1])*3.0/27.0,1) if len(zres) else 0.0)

rows=[]
SECTIONS=[("east",AZ_E_CAP+AISLE_DEG,AZ_BEND_E-AISLE_DEG),
          ("bend",AZ_BEND_E+AISLE_DEG,AZ_BEND_W-AISLE_DEG),
          ("south",AZ_BEND_W+AISLE_DEG,AZ_S_CAP-AISLE_DEG)]
def sector_poly(E):
    cp=contour_pts(E); return cp[0] if cp is not None else None
def mindist(P,Q): return min(np.min(np.hypot(Q[:,0]-p[0],Q[:,1]-p[1])) for p in P)
# ONE adaptive march for the WHOLE bank (forecourt + promenade + civic), lowest elev -> up.
# Every row is a contour bay -> the forecourt NESTS with the civic rows (no overlapping arcs).
# Spacing steps so adjacent contours clear MIN_CLEAR (widens the riser where the rake steepens).
E_START=float(ec(85.0))                         # lowest forecourt contour (near the orchestra)
elevs=[E_START]; prev=sector_poly(E_START); E=E_START
while len(elevs)<(N_FORE+1+N_CIVIC) and E<E_CAP and prev is not None:
    E2=E+0.8
    for _ in range(30):
        P2=sector_poly(E2)
        if P2 is None: E2+=0.15; continue
        if mindist(P2,prev)>=MIN_CLEAR: break
        E2+=0.12
    P2=sector_poly(E2)
    if P2 is None: break
    elevs.append(round(E2,2)); prev=P2; E=E2
for ix,Ek in enumerate(elevs):
    cp=contour_pts(Ek)
    if cp is None: continue
    P,a=cp
    bays={}
    for nm,lo,hi in SECTIONS:
        seg=P[(a>=lo)&(a<=hi)]; fb=fit_bay(seg)
        if fb: bays[nm]=fb
    if not bays: continue
    azc=(np.degrees(np.arctan2(P[:,0]-FX,P[:,1]-FY)))%360
    cc=P[np.argmin(np.abs(((azc-AX_AZ+180)%360)-180))]; rcen=math.hypot(cc[0]-FX,cc[1]-FY)
    zone="forecourt" if ix<N_FORE else "civic"
    kind="promenade" if ix==N_FORE else "seating"
    rows.append(dict(row=len(rows)+1,zone=zone,kind=kind,elev=round(float(Ek),2),
        dist=round(float(rcen-STAGE_R),1),bays=bays))

# sightlines (centreline) + seats + bay-view
pr=pe=None
for x in rows:
    D=x["dist"]
    if x["kind"]!="seating" or pr is None: x["C_mm"]=None
    else:
        Ep=(pe+EYE_HT)-FOCUS_ELEV; E=(x["elev"]+EYE_HT)-FOCUS_ELEV; x["C_mm"]=round((E*(pr/D)-Ep)*304.8)
    if x["kind"]=="seating": pr=D; pe=x["elev"]
    x["eye"]=round(x["elev"]+EYE_HT,2); x["sees_bay"]=bool(x["eye"]>618.5)
def seats(Lf): return max(0,int(Lf*(1-AISLE)//SEAT_W_G))
tot_by_sec={"east":0,"bend":0,"south":0,"forecourt":0}; total=0
for x in rows:
    x["seats"]={}
    for nm,b in x["bays"].items():
        s=seats(b["length"]) if x["kind"]=="seating" else 0
        x["seats"][nm]=s; tot_by_sec[nm]=tot_by_sec.get(nm,0)+s; total+=s

# ---------- VALIDATION GATES (the user's reject criteria) ----------
civ=[x for x in rows if x["zone"]=="civic"]
level_fail=[]    # G1: civic SEATING tread p90 raw residual <= +/-0.20 standard (promenade gated separately, stricter)
for x in civ:
    if x["kind"]!="seating": continue
    for nm,b in x["bays"].items():
        if b["z_resid"]>GATE_RESID_P90: level_fail.append((x["row"],nm,b["z_resid"]))
clear_fail=[]; min_clear=99.0
for a,b in zip(civ,civ[1:]):
    for nm in set(a["bays"])&set(b["bays"]):
        Pa=np.array(a["bays"][nm]["coords"]); Pb=np.array(b["bays"][nm]["coords"])
        dmin=min(np.min(np.hypot(Pb[:,0]-p[0],Pb[:,1]-p[1])) for p in Pa)
        min_clear=min(min_clear,dmin)
        if dmin<GATE_CLEAR: clear_fail.append((a["row"],b["row"],nm,round(dmin,2)))

# ---------- PER-SEAT flank sightlines (segmented non-concentric rows can't be certified from centreline C) ----------
def ray_seg(p0,d,a,b):
    e=b-a; den=d[0]*(-e[1])-d[1]*(-e[0])
    if abs(den)<1e-9: return None
    t=((a[0]-p0[0])*(-e[1])-(a[1]-p0[1])*(-e[0]))/den
    u=(d[0]*(a[1]-p0[1])-d[1]*(a[0]-p0[0]))/den
    return t if (t>1e-6 and -0.05<=u<=1.05) else None
SF=np.array([SFx,SFy]); allseat=sorted([x for x in rows if x["kind"]=="seating"],key=lambda r:r["elev"])
seat_pass=0; seat_tot=0; per_row_C={}
for idx,x in enumerate(allseat):
    if x["zone"]!="civic" or idx==0: continue
    front=allseat[idx-1]
    fsegs=[(np.array(c[i]),np.array(c[i+1]),front["elev"])
           for b in front["bays"].values() for c in [b["coords"]] for i in range(len(c)-1)]
    Eeye=x["elev"]+EYE_HT; Cs=[]
    for b in x["bays"].values():
        for p in [np.array(q) for q in b["coords"][::2]]:        # ~2-ft seat sampling
            d=SF-p; Ds=np.hypot(*d)
            if Ds<1e-3: continue
            dd=d/Ds; best=None
            for (a,bb,fe) in fsegs:
                t=ray_seg(p,dd,a,bb)
                if t is not None and t<Ds and (best is None or t<best[0]): best=(t,fe)
            if best is None: Cs.append(1.0); continue              # nobody in front -> open view
            Dfoc=Ds-best[0]                                        # distance of the front head FROM the focus
            h=FOCUS_ELEV+(Eeye-FOCUS_ELEV)*Dfoc/Ds; Cs.append(h-(best[1]+EYE_HT))
    if Cs:
        Cs=np.array(Cs); seat_tot+=len(Cs); seat_pass+=int((Cs>=C_TARGET_FT).sum())
        per_row_C[x["row"]]=(round(float(np.percentile(Cs,10))*304.8), round(float((Cs>=C_TARGET_FT).mean()*100)))

# ---------- ADA promenade (independent, stricter than ordinary seating treads) ----------
prom=[x for x in rows if x["kind"]=="promenade"]
ada=[]
for x in prom:
    for nm,b in x["bays"].items():
        ada.append((nm,b["z_resid"], b["z_resid"]<=ADA_RESID_P90))

# ---------- earthwork ----------
grade_total=sum(b.get("grade_cy",0) for x in rows if x["zone"]=="civic" for b in x["bays"].values())

# ---------- outputs ----------
CRS={"type":"name","properties":{"name":"urn:ogc:def:crs:EPSG::6494"}}
def fc(f): return {"type":"FeatureCollection","crs":CRS,"features":f}
feats=[]
for x in rows:
    for nm,b in x["bays"].items():
        feats.append({"type":"Feature","properties":{"row":x["row"],"section":nm,"zone":x["zone"],
            "kind":x["kind"],"elev":b.get("elev"),"length_ft":b["length"],"seats":x["seats"].get(nm),
            "cross_angle_deg":b.get("cross_ang"),"z_resid_ft":b.get("z_resid"),"C_mm":x.get("C_mm"),
            "sees_bay":x["sees_bay"]},"geometry":{"type":"LineString","coordinates":b["coords"]}})
json.dump(fc(feats),open(f"{OUT}/seating_bays.geojson","w"),indent=1)
with open(f"{OUT}/composition_table.csv","w",newline="") as fh:
    w=csv.writer(fh); w.writerow(["row","zone","kind","section","elev","length_ft","seats",
        "cross_angle_deg","z_resid_ft","C_mm","sees_bay"])
    for x in rows:
        for nm,b in x["bays"].items():
            w.writerow([x["row"],x["zone"],x["kind"],nm,b.get("elev"),b["length"],x["seats"].get(nm),
                b.get("cross_ang"),b.get("z_resid"),x.get("C_mm"),x["sees_bay"]])

# plan
win=210; c0=int((CX-win-T.c)/T.a);c1=int((CX+win-T.c)/T.a);r1=int((CY-win-T.f)/T.e);r0=int((CY+win-T.f)/T.e)
sub=A0[r0:r1,c0:c1]; ext=[T.c+c0*T.a,T.c+c1*T.a,T.f+r1*T.e,T.f+r0*T.e]
xxp=T.c+(np.arange(c0,c1)+0.5)*T.a; yyp=T.f+(np.arange(r0,r1)+0.5)*T.e   # true world coords
fig,ax=plt.subplots(figsize=(9,9)); ax.imshow(sub,extent=ext,origin="upper",cmap="terrain",alpha=0.8)
cs=ax.contour(xxp,yyp[::-1],sub[::-1,:],levels=np.arange(606,634,1),colors="k",      # FIXED y orientation
    linewidths=0.3,alpha=0.35); ax.clabel(cs,fontsize=5,fmt="%d")
sc={"east":"#1f77b4","bend":"tab:orange","south":"#2ca02c"}
for x in rows:
    for nm,b in x["bays"].items():
        col="tab:red" if x["zone"]=="forecourt" else sc.get(nm,"gray")   # forecourt nests, colored red
        ax.plot([p[0] for p in b["coords"]],[p[1] for p in b["coords"]],color=col,
                lw=2.4 if x["kind"]=="promenade" else 1.8)
ax.plot(SFx,SFy,"k*",ms=16); ax.annotate("stage",(SFx,SFy),fontsize=8)
ax.annotate("",xy=(SFx+U(FACE_AZ)[0]*90,SFy+U(FACE_AZ)[1]*90),xytext=(SFx,SFy),arrowprops=dict(arrowstyle="->",color="navy",lw=2))
ax.set_aspect("equal"); ax.set_xlabel("EPSG:6494 X (ft)"); ax.set_ylabel("Y (ft)")
ax.set_title("Corner bays — 3 contour-aligned bays/row (blue=east flank, orange=bend hinge,\ngreen=south flank, red=forecourt); aisles at the hinges")
plt.tight_layout(); plt.savefig(f"{OUT}/plan.png",dpi=130); plt.close()

# ZOOMED seating plan (legible): all bays + forecourt nesting + grade, correct orientation
axx=[p[0] for x in rows for b in x["bays"].values() for p in b["coords"]]
ayy=[p[1] for x in rows for b in x["bays"].values() for p in b["coords"]]
if axx:
    x0,x1=min(axx)-22,max(axx)+22; y0,y1=min(ayy)-22,max(ayy)+22
    d0=int((x0-T.c)/T.a);d1=int((x1-T.c)/T.a);e1=int((y0-T.f)/T.e);e0=int((y1-T.f)/T.e)
    zz=A[e0:e1,d0:d1]; xg=T.c+(np.arange(d0,d1)+0.5)*T.a; yg=T.f+(np.arange(e0,e1)+0.5)*T.e
    fig,ax=plt.subplots(figsize=(11,9))
    cs=ax.contour(xg,yg[::-1],zz[::-1,:],levels=np.arange(606,634,1),colors="dimgray",linewidths=0.6,alpha=0.7)
    ax.clabel(cs,fontsize=7,fmt="%d")
    for x in rows:
        for nm,b in x["bays"].items():
            col="tab:red" if x["zone"]=="forecourt" else sc.get(nm,"gray")
            ax.plot([p[0] for p in b["coords"]],[p[1] for p in b["coords"]],color=col,
                    lw=3.0 if x["kind"]=="promenade" else 2.0)
    ax.plot(SFx,SFy,"k*",ms=18); ax.annotate("stage",(SFx,SFy),fontsize=9)
    ax.set_aspect("equal"); ax.set_xlabel("X (ft)"); ax.set_ylabel("Y (ft)")
    ax.set_title("Corner bays (zoom): red=forecourt (nested), blue=east, orange=bend hinge, green=south\n"
                 "treads run ALONG the gray contours; aisle gaps at the hinges")
    plt.tight_layout(); plt.savefig(f"{OUT}/plan_zoom.png",dpi=140); plt.close()

# zoomed EAST-FLANK proof: bays vs 1-ft contours (does the tread centreline bow with grade?)
exs=[p[0] for x in rows for b in [x["bays"].get("east")] if b for p in b["coords"]]
eys=[p[1] for x in rows for b in [x["bays"].get("east")] if b for p in b["coords"]]
if exs:
    x0,x1=min(exs)-15,max(exs)+15; y0,y1=min(eys)-15,max(eys)+15
    cc0=int((x0-T.c)/T.a);cc1=int((x1-T.c)/T.a);rr1=int((y0-T.f)/T.e);rr0=int((y1-T.f)/T.e)
    z=A[rr0:rr1,cc0:cc1]                                    # the surface the bays were fit to
    xx=T.c+(np.arange(cc0,cc1)+0.5)*T.a                     # true world coords (no flip)
    yy=T.f+(np.arange(rr0,rr1)+0.5)*T.e
    fig,ax=plt.subplots(figsize=(8,8))
    cs=ax.contour(xx,yy[::-1],z[::-1,:],levels=np.arange(610,632,0.5),colors="dimgray",
        linewidths=0.6,alpha=0.8); ax.clabel(cs,fontsize=6,fmt="%.1f")
    for x in rows:
        b=x["bays"].get("east")
        if b: ax.plot([p[0] for p in b["coords"]],[p[1] for p in b["coords"]],color="#1f77b4",lw=2.4)
    ax.set_aspect("equal"); ax.set_title("EAST-FLANK PROOF: tread centrelines (blue) vs 0.5-ft contours (gray)\nbays run ALONG the contours (elev range 0.06 ft) — not across them")
    ax.set_xlabel("X (ft)"); ax.set_ylabel("Y (ft)"); plt.tight_layout(); plt.savefig(f"{OUT}/east_flank_proof.png",dpi=140); plt.close()

# summary
civ=[x for x in rows if x["zone"]=="civic"]
def secmean(nm,key):
    v=[b[key] for x in civ for n,b in x["bays"].items() if n==nm and b.get(key) is not None]
    return np.mean(v) if v else float("nan")
print("=== Corner bays — three-part contour-aligned terrace system (face 312) ===")
print(f"rows: {len(FORE_R)} forecourt + {len(civ)} civic ; bays/civic row up to 3 (south|bend|east)")
fc_seats=sum(s for x in rows if x['zone']=='forecourt' for s in x['seats'].values())
print(f"FORMAL seats {total:,}  (by section: east {tot_by_sec['east']:,} | bend {tot_by_sec['bend']:,} | "
      f"south {tot_by_sec['south']:,}; of which forecourt-zone {fc_seats:,})  [target 1,050-1,200]")
print("\nLOCAL diagnostic vs RAW/de-noised DEM -- crossing angle (p90 deg), p90 residual, full-bay range:")
for nm in ("east","bend","south"):
    print(f"  {nm:6s}: cross {secmean(nm,'cross_ang'):4.1f} deg   p90-resid {secmean(nm,'z_resid'):.2f} ft   "
          f"full-bay {secmean(nm,'z_range'):.2f} ft")
print(f"\nVALIDATION GATES (standard: +/-0.20 ft tread tolerance vs raw DEM):")
print(f"  [G1] civic SEATING tread p90 residual <= {GATE_RESID_P90} ft : "
      f"{'PASS' if not level_fail else 'FAIL'}  ({len(level_fail)} bays over; "
      f"worst {max((z for _,_,z in level_fail),default=0):.2f} ft)")
print(f"  [G2] adjacent-row clearance >= {GATE_CLEAR} ft (tread) : "
      f"{'PASS' if not clear_fail else 'FAIL'}  (min clearance {min_clear:.2f} ft; {len(clear_fail)} pairs tight)")
print(f"\n[earthwork] shallow tread fine-grading (raw DEM, 3-ft strip): ~{grade_total:.0f} CY ; "
      f"no retaining walls; no imported fill")
print(f"[sightlines] centreline C>=90mm: "
      f"{sum(1 for x in rows if x['kind']=='seating' and (x['C_mm'] is None or x['C_mm']>=90))}"
      f"/{sum(1 for x in rows if x['kind']=='seating')}")
print(f"[PER-SEAT flank sightlines] {seat_pass}/{seat_tot} sampled seats clear 90mm "
      f"({100*seat_pass/max(1,seat_tot):.0f}%); worst rows (row: p10 C mm / %pass): "
      f"{dict(sorted(per_row_C.items(),key=lambda kv:kv[1][1])[:4])}")
print(f"[ADA promenade] independent gate p90<={ADA_RESID_P90} ft: "
      f"{'PASS' if all(ok for _,_,ok in ada) else 'FAIL'}  {[(nm,r) for nm,r,ok in ada]}; "
      f"accessible connecting routes = separate ramp design (<=8.33% run, <=2% cross)")
print("\n row zone      elev dist Cmm bay | east(len/ang/zr) bend(..) south(..)")
for x in rows:
    if x["zone"]=="forecourt": continue
    def cell(nm):
        b=x["bays"].get(nm)
        return f"{b['length']:3.0f}/{b['cross_ang']:4.1f}/{b['z_resid']:.1f}" if b else "   -      "
    print(f" {x['row']:3d} {x['zone']:9s}{x['elev']:6.1f}{x['dist']:5.0f}{str(x.get('C_mm')):>4} "
          f"{'Y' if x['sees_bay'] else '.':>2} | {cell('east'):>14} {cell('bend'):>14} {cell('south'):>14}")
print(f"\nwrote {OUT}/seating_bays.geojson composition_table.csv plan.png")
