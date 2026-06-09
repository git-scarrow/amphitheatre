#!/usr/bin/env python3
"""
DESIGN: "Designed civic bowl" v3 — designed crescent FIRST, terrain attraction
SECOND, with three-tier capacity recovery.

Generator rule (per the brief):
    fit  ->  designed crescent  +  terrain attraction  +  capacity recovery
NOT "fit smoothed contour row". Each civic row begins as a clean arc on the
stage-facing axis (the preferred civic shape), is then PULLED toward the natural
contour but CLAMPED to a bounded radial wander (no hook-chasing), and finally
zoned into three capacity tiers by how far its level tread sits off natural grade:

    core  (|dev| < 1.0 ft)        designed crescent      -> primary fixed seating
    bay   (1.0 < |dev| < 2.2 ft)  reclaimed inner flank  -> short fixed seating bays
    lawn  (|dev| > 2.2 ft / hook) outer side bank        -> informal lawn capacity

Flank policy is ASYMMETRIC: the east flank (the contour "hook", +X) is capped
tight and early so the eastern wall never becomes the visual boundary; the west
flank is extended so the bowl wraps the stage and each row's centroid stays near
the stage axis. The promenade (row 5) is widened into the civic spine.

Target: ~1,050-1,200 FORMAL seats (core+bay) plus lawn. Modest cut/fill is spent
to buy civic completeness. Planning-grade. EPSG:6494 NAVD88. -> design_civic_bowl/
"""
import json, csv, math, os
import numpy as np, rasterio
from rasterio.transform import rowcol
from scipy.ndimage import gaussian_filter, gaussian_filter1d
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

DEM="dem/dem_design_1ft.tif"; OUT="design_civic_bowl"; os.makedirs(OUT,exist_ok=True)
CX,CY=19533067.7,750799.2
AX_AZ=132.0; FACE_AZ=(AX_AZ+180)%360
FOCUS_ELEV=612.5; F_T=15.0; EYE_HT=3.94; STAGE_R=50.0
C_TARGET_FT=0.295
SEAT_W_C=1.50; SEAT_W_G=1.83; AISLE=0.18

FORE_FAN=40.0; FORE_R=[85.0,88.0,91.0,94.0]; FORE_TREAD=3.0; CIVIC_TREAD=3.0
# --- designed-crescent + attraction parameters ---
T1_GRADE=1.0            # core fixed-terrace grade tolerance (ft off natural)
T2_GRADE=2.2            # reclaimed-bay grade tolerance (modest extra cut/fill)
DRDT_REF=0.4            # hook-downweighting scale in the centred weighted fit (ft/deg)
DRDT_EAST=0.7           # retention stop-cap on the east/hook flank (ft/deg)
DRDT_WEST=1.1           # looser retention cap on the west flank (reach/wrap)
EAST_MAX_FAN=42.0       # cap east extent early (deg from axis)
WEST_MAX_FAN=60.0       # let west wrap the stage
SAMP_FAN=66.0           # symmetric sampling window (keeps the FIT centred)
FACE_TOL_DEG=28.0
PROMENADE_RC=100.0; PROMENADE_WIDTH=10.0

# civic families: (name, [centreline radii], polyfit order, kind)
FAMILIES=[
    ("promenade",[PROMENADE_RC],                 2, "promenade"),
    ("lower",    [106.0,109.0,112.0],            2, "seating"),
    ("middle",   [115.0,118.0,121.0,124.0],      2, "seating"),
    ("upper",    [127.0,130.0,133.0,136.0],      2, "seating"),
]

ds=rasterio.open(DEM); A0=ds.read(1).astype(float); A0[A0==ds.nodata]=np.nan; T=ds.transform
A=A0.copy(); m=np.isfinite(A0); A[~m]=np.nanmean(A0[m]); A=gaussian_filter(A,sigma=3.0); A[~m]=np.nan
def elev(x,y):
    r,c=rowcol(T,x,y)
    return np.nan if not(0<=r<A.shape[0] and 0<=c<A.shape[1]) else A[r,c]
def U(az): a=math.radians(az); return math.sin(a),math.cos(a)
UX,UY=U(AX_AZ); FX,FY=CX+UX*F_T,CY+UY*F_T
SFx,SFy=FX+UX*STAGE_R,FY+UY*STAGE_R
def polar(R,az,ox=FX,oy=FY): e,n=U(az); return ox+e*R,oy+n*R
def ec(r): return elev(*polar(r,AX_AZ))
def ray_profile(az):
    rr=np.arange(70.0,165.0+1e-6,0.5); zz=np.array([elev(*polar(r,az)) for r in rr]); return rr,zz
def r_at_elev(rr,zz,E):
    for i in range(1,len(rr)):
        z0,z1=zz[i-1],zz[i]
        if np.isfinite(z0) and np.isfinite(z1) and (z0<=E<=z1):
            t=(E-z0)/(z1-z0) if z1!=z0 else 0.0
            return float(rr[i-1]+t*(rr[i]-rr[i-1]))
    return np.nan

# ---------------- FORECOURT (regular arcs, stage zone) ----------------
AZF=np.linspace(AX_AZ-FORE_FAN,AX_AZ+FORE_FAN,81)
rows=[]
for i,R in enumerate(FORE_R):
    coords=[[round(polar(R,az)[0],2),round(polar(R,az)[1],2)] for az in AZF]
    arclen=R*math.radians(2*FORE_FAN)
    rows.append(dict(row=i+1,zone="forecourt",family="forecourt",kind="seating",
                     elev=round(float(ec(R)),2),R=R,dist=round(R-STAGE_R,1),
                     coords=coords,core=coords,bays=[],lawn=[],
                     core_len=round(arclen,1),bay_len=0.0,lawn_len=0.0))

# ---------------- CIVIC rows: designed crescent + attraction + 3-tier ----------------
civic_plan=[(fam,rc,order,kind) for fam,rcs,order,kind in FAMILIES for rc in rcs]
rn=len(FORE_R)
def seg_runs(mask):
    runs=[]; s=None
    for i,v in enumerate(mask):
        if v and s is None: s=i
        if (not v) and s is not None: runs.append((s,i)); s=None
    if s is not None: runs.append((s,len(mask)))
    return runs

for fam,rc,order,kind in civic_plan:
    R_row=rc; Ek=ec(R_row)
    AZ=np.arange(AX_AZ-SAMP_FAN, AX_AZ+SAMP_FAN+1e-6, 0.5)   # SYMMETRIC -> fit stays centred
    ci=int(np.argmin(np.abs(AZ-AX_AZ)))
    rcont=np.array([r_at_elev(*ray_profile(az),Ek) for az in AZ])
    fin=np.isfinite(rcont)
    if fin.sum()<8: continue
    rfill=rcont.copy(); rfill[~fin]=np.interp(AZ[~fin],AZ[fin],rcont[fin])
    rsm=gaussian_filter1d(rfill,sigma=2.5,mode="nearest")
    drdt=np.abs(np.gradient(rsm,AZ))
    # 2) designed crescent: WEIGHTED low-order fit that tracks the tame contour but
    #    downweights the hook -> centred & clean, no lopsided window, no extrapolation
    wt=np.where(fin,1.0/(1.0+(drdt/DRDT_REF)**2),0.0)
    coef=np.polyfit(AZ-AX_AZ, rsm, order, w=wt)
    rfit=np.polyval(coef,AZ-AX_AZ)
    # 3) ASYMMETRIC retention walk from the axis + three-tier zoning (extent only, not the fit)
    zone=np.array(["lawn"]*len(AZ),dtype=object)
    def dev_at(j):
        g=elev(*polar(rfit[j],AZ[j])); return abs(Ek-g) if np.isfinite(g) else 99.0
    for side in (-1,+1):                                # -1 east(lower az/hook), +1 west(wrap)
        capS=DRDT_EAST if side<0 else DRDT_WEST
        maxfan=EAST_MAX_FAN if side<0 else WEST_MAX_FAN
        j=ci
        while 0<=j<len(AZ) and abs(AZ[j]-AX_AZ)<=maxfan:
            d=dev_at(j)
            if (drdt[j]>capS or d>=T2_GRADE) and j!=ci: break
            zone[j]="core" if d<T1_GRADE else ("bay" if d<T2_GRADE else "bay")
            j+=side
    keep=zone!="lawn"
    if keep.sum()<6: continue
    lk=min(j for j in range(len(AZ)) if keep[j]); hk=max(j for j in range(len(AZ)) if keep[j])
    keep_idx=list(range(lk,hk+1))
    for j in keep_idx:                                  # make terrace continuous
        if zone[j]=="lawn": zone[j]="bay"
    rn+=1
    def poly(idx): return [[round(polar(rfit[j],AZ[j])[0],2),round(polar(rfit[j],AZ[j])[1],2)] for j in idx]
    cc=ci
    if zone[cc]!="core":
        cores=[j for j in keep_idx if zone[j]=="core"]
        cc=min(cores,key=lambda j:abs(j-ci)) if cores else ci
    lcr=cc
    while lcr-1>=lk and zone[lcr-1]=="core": lcr-=1
    hcr=cc
    while hcr+1<=hk and zone[hcr+1]=="core": hcr+=1
    core_run=list(range(lcr,hcr+1))
    bay_runs=[(a,b) for a,b in seg_runs(np.array([zone[j]=="bay" for j in range(len(AZ))])) if a>=lk and b<=hk+1]
    lawn_mask=np.array([(j<lk or j>hk) and fin[j] for j in range(len(AZ))])
    lawn_runs=seg_runs(lawn_mask)
    coreP=poly(core_run); fullP=poly(keep_idx)
    bays=[poly(range(a,b)) for a,b in bay_runs if b-a>=3]
    lawn=[poly(range(a,b)) for a,b in lawn_runs if b-a>=4]
    # lengths
    def plen(P): return float(sum(math.dist(P[k],P[k+1]) for k in range(len(P)-1))) if len(P)>1 else 0.0
    core_len=plen(coreP); bay_len=sum(plen(b) for b in bays); lawn_len=sum(plen(l) for l in lawn)
    # ---- composition metrics on the fixed (core+bay) polyline ----
    P=np.array(fullP); kappa=[]; Rcurv=np.inf
    for i in range(1,len(P)-1):
        a=P[i]-P[i-1]; b=P[i+1]-P[i]; da=math.hypot(*a); db=math.hypot(*b)
        if da<1e-6 or db<1e-6: continue
        ang=(math.atan2(b[1],b[0])-math.atan2(a[1],a[0])+math.pi)%(2*math.pi)-math.pi
        ds_=0.5*(da+db); kappa.append(abs(ang)/ds_)
        if abs(ang)>1e-6: Rcurv=min(Rcurv,ds_/abs(ang))
    kappa=np.array(kappa); curv_cv=float(np.std(kappa)/(np.mean(kappa)+1e-9)) if len(kappa)>2 else 0.0
    ferr=[]
    for i in range(1,len(P)-1):
        t=P[i+1]-P[i-1]; t/=np.hypot(*t)+1e-9; n=np.array([t[1],-t[0]])
        d=np.array([SFx,SFy])-P[i]; d/=np.hypot(*d)+1e-9
        if np.dot(n,d)<0: n=-n
        ferr.append(math.degrees(math.acos(max(-1,min(1,np.dot(n,d))))))
    face90=float(np.percentile(ferr,90)) if ferr else 0.0
    gresid=float(np.percentile([abs(Ek-elev(*p)) for p in fullP if np.isfinite(elev(*p))],90))
    # centroid azimuth offset from the stage axis (capacity-balance test)
    cen=np.mean(P,axis=0); cen_az=(math.degrees(math.atan2(cen[0]-FX,cen[1]-FY)))%360
    cen_off=round(((cen_az-AX_AZ+180)%360)-180,1)
    noncirc=round(float(rfit[keep_idx].max()-rfit[keep_idx].min()),1)
    # earthwork on the fixed tread
    cut=fill=0.0; darc=(core_len+bay_len)/max(1,len(keep_idx))
    for j in keep_idx:
        for d in np.arange(-CIVIC_TREAD/2,CIVIC_TREAD/2+1e-6,0.5):
            g=elev(*polar(rfit[j]+d,AZ[j]))
            if not np.isfinite(g): continue
            v=(Ek-g)*0.5*darc
            fill+= v if v>0 else 0.0; cut+= -v if v<0 else 0.0
    width=PROMENADE_WIDTH if kind=="promenade" else CIVIC_TREAD
    rows.append(dict(row=rn,zone="civic",family=fam,kind=kind,elev=round(float(Ek),2),
        R=R_row,dist=round(R_row-STAGE_R,1),coords=fullP,core=coreP,bays=bays,lawn=lawn,
        core_len=round(core_len,1),bay_len=round(bay_len,1),lawn_len=round(lawn_len,1),
        curv_cv=round(curv_cv,3),min_Rcurv=round(float(Rcurv),0),face_err90=round(face90,1),
        grade_resid90=round(gresid,2),noncirc=noncirc,cen_off=cen_off,width=width,
        cut_cy=round(cut/27,1),fill_cy=round(fill/27,1)))

# ---------------- sightline C (centreline) + bay tag ----------------
for x in rows: x["_R"]=x["R"]
pr=None;pe=None
for x in rows:
    D=x["_R"]-STAGE_R
    if x["kind"]!="seating": x["C_mm"]=None; continue
    if pr is None: x["C_mm"]=None
    else:
        Ep=(pe+EYE_HT)-FOCUS_ELEV; E=(x["elev"]+EYE_HT)-FOCUS_ELEV
        x["C_mm"]=round((E*(pr/D)-Ep)*304.8)
    pr=D; pe=x["elev"]
RIM=618.0
for x in rows:
    x["eye"]=round(x["elev"]+EYE_HT,2); x["sees_bay"]=bool(x["eye"]>RIM+0.5)
    x["meets_C"]=(x["C_mm"] is None) or (x["C_mm"]>=90)

# ---------------- capacity (three tiers) ----------------
def seats(L,w=SEAT_W_G): return max(0,int(L*(1-AISLE)//w))
core_g=bay_g=0; lawn_lf=0.0
for x in rows:
    x["core_seats"]=seats(x["core_len"]) if x["kind"]=="seating" else 0
    x["bay_seats"]=seats(x["bay_len"]) if x["kind"]=="seating" else 0
    core_g+=x["core_seats"]; bay_g+=x["bay_seats"]; lawn_lf+=x.get("lawn_len",0.0)
formal=core_g+bay_g
lawn_cap=int(lawn_lf*1.5/ SEAT_W_G)   # informal lawn: ~1.5 ft deep band equiv, rough

# ---------------- outputs ----------------
CRS={"type":"name","properties":{"name":"urn:ogc:def:crs:EPSG::6494"}}
def fc(f): return {"type":"FeatureCollection","crs":CRS,"features":f}
def line(c,p): return {"type":"Feature","properties":p,"geometry":{"type":"LineString","coordinates":c}}
rowf=[]; bayf=[]; lawnf=[]
for x in rows:
    p={k:x.get(k) for k in["row","zone","family","kind","elev","eye","dist","C_mm","meets_C",
        "sees_bay","curv_cv","min_Rcurv","face_err90","grade_resid90","noncirc","cen_off",
        "core_len","bay_len","lawn_len","core_seats","bay_seats"]}
    rowf.append(line(x["core"] if x["core"] else x["coords"],p|{"tier":"core","datum":"NAVD88 intl ft"}))
    for b in x.get("bays",[]): bayf.append(line(b,{"row":x["row"],"family":x["family"],"tier":"bay"}))
    for l in x.get("lawn",[]): lawnf.append(line(l,{"row":x["row"],"tier":"lawn_side_bank"}))
json.dump(fc(rowf),open(f"{OUT}/seating_rows.geojson","w"),indent=1)
json.dump(fc(bayf),open(f"{OUT}/seating_bays.geojson","w"),indent=1)
json.dump(fc(lawnf),open(f"{OUT}/side_banks.geojson","w"),indent=1)
json.dump(fc([{"type":"Feature","properties":{"name":"stage_front_focus","elev_navd88":FOCUS_ELEV,
    "centerline_az_deg":AX_AZ,"audience_face_az_deg":FACE_AZ},
    "geometry":{"type":"Point","coordinates":[round(SFx,2),round(SFy,2)]}}]),
    open(f"{OUT}/stage_focus.geojson","w"),indent=1)

with open(f"{OUT}/composition_table.csv","w",newline="") as fh:
    w=csv.writer(fh); w.writerow(["row","family","kind","elev","dist","C_mm","sees_bay","curv_cv",
        "min_Rcurv","face_err90","grade_resid90","noncirc","cen_off","core_len","bay_len","lawn_len",
        "core_seats","bay_seats","cut_cy","fill_cy"])
    for x in rows:
        w.writerow([x["row"],x["family"],x["kind"],x["elev"],x["dist"],x["C_mm"],x["sees_bay"],
            x.get("curv_cv",""),x.get("min_Rcurv",""),x.get("face_err90",""),x.get("grade_resid90",""),
            x.get("noncirc",""),x.get("cen_off",""),x["core_len"],x.get("bay_len",0),x.get("lawn_len",0),
            x.get("core_seats",0),x.get("bay_seats",0),x.get("cut_cy",""),x.get("fill_cy","")])

# plan
win=210
c0=int((CX-win-T.c)/T.a);c1=int((CX+win-T.c)/T.a);r1=int((CY-win-T.f)/T.e);r0=int((CY+win-T.f)/T.e)
sub=A0[r0:r1,c0:c1]; ext=[T.c+c0*T.a,T.c+c1*T.a,T.f+r1*T.e,T.f+r0*T.e]
fig,ax=plt.subplots(figsize=(9,9)); ax.imshow(sub,extent=ext,origin="upper",cmap="terrain",alpha=0.8)
cs=ax.contour(np.linspace(ext[0],ext[1],sub.shape[1]),np.linspace(ext[3],ext[2],sub.shape[0])[::-1],
              sub,levels=np.arange(606,634,2),colors="k",linewidths=0.3,alpha=0.4); ax.clabel(cs,fontsize=6,fmt="%d")
fam_col={"forecourt":"tab:red","promenade":"orange","lower":"#7fb8e6","middle":"tab:blue","upper":"#08306b"}
for x in rows:
    if x["core"]:
        ax.plot([p[0] for p in x["core"]],[p[1] for p in x["core"]],
                color=fam_col.get(x["family"],"gray"),lw=2.6 if x["family"]=="promenade" else 1.9)
    for b in x.get("bays",[]):
        ax.plot([p[0] for p in b],[p[1] for p in b],color="mediumpurple",lw=1.5,ls=(0,(4,2)))
    for l in x.get("lawn",[]):
        ax.plot([p[0] for p in l],[p[1] for p in l],color="tab:green",lw=1.0,alpha=0.6)
ax.plot(SFx,SFy,"k*",ms=16); ax.annotate("stage",(SFx,SFy),fontsize=8)
ax.annotate("",xy=(SFx+U(FACE_AZ)[0]*90,SFy+U(FACE_AZ)[1]*90),xytext=(SFx,SFy),
            arrowprops=dict(arrowstyle="->",color="navy",lw=2))
ax.set_aspect("equal"); ax.set_xlabel("EPSG:6494 X (ft)"); ax.set_ylabel("Y (ft)")
ax.set_title("Designed civic bowl v3 — core (red/orange/blue) + reclaimed bays (purple dash) + lawn (green)")
plt.tight_layout(); plt.savefig(f"{OUT}/plan.png",dpi=130); plt.close()

# ---------------- summary ----------------
seat_rows=[x for x in rows if x["kind"]=="seating"]
tcut=sum(x.get("cut_cy",0) for x in rows); tfill=sum(x.get("fill_cy",0) for x in rows)
print(f"=== Designed civic bowl v3 (face {FACE_AZ:.0f}) — designed crescent + attraction + 3-tier ===")
print(f"rows: {len(FORE_R)} forecourt + 1 promenade + {len(seat_rows)-len(FORE_R)} civic = {len(rows)}")
print(f"FORMAL seats (generous): core {core_g:,} + reclaimed bays {bay_g:,} = {formal:,}   "
      f"[target 1,050-1,200]   lawn ~{lawn_cap:,} informal")
print(f"tread earthwork: cut {tcut:.0f} + fill {tfill:.0f} = {tcut+tfill:.0f} CY")
print(f"sightline C>=90mm: {sum(1 for x in seat_rows if x['meets_C'])}/{len(seat_rows)}   "
      f"bay-seeing rows {[x['row'] for x in rows if x['sees_bay']]}")
print(f"mean centroid offset from stage axis: {np.mean([x['cen_off'] for x in rows if x['zone']=='civic']):+.1f} deg")
print("\n row family    elev dist Cmm curvCV minRc face90 gresid noncirc cenOff coreL bayL lawnL coreS bayS")
for x in rows:
    if x["zone"]=="forecourt": continue
    print(f" {x['row']:3d} {x['family']:9s}{x['elev']:6.1f}{x['dist']:5.0f}{str(x['C_mm']):>4} "
          f"{x.get('curv_cv',''):>5} {x.get('min_Rcurv',''):>5} {x.get('face_err90',''):>5} "
          f"{x.get('grade_resid90',''):>5} {x.get('noncirc',''):>6} {x.get('cen_off',''):>5} "
          f"{x['core_len']:>5.0f}{x.get('bay_len',0):>5.0f}{x.get('lawn_len',0):>5.0f}"
          f"{x.get('core_seats',0):>5}{x.get('bay_seats',0):>4}")
print(f"\nwrote {OUT}/seating_rows.geojson seating_bays.geojson side_banks.geojson composition_table.csv plan.png")
