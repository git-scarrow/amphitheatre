#!/usr/bin/env python3
"""
DESIGN: "Civic contour bowl" — baseline implementation of the user's revised
seating principle (2026-06-05).

  * Aim the fan at the natural fall line: FACE_AZ = 312 (AX_AZ = 132).
  * Rows 1-4 = a TIGHT STAGE FORECOURT (narrower fan, on grade, near the floor,
    no bay obligation — they sit at/below the 618 rim and can't see the bay anyway).
  * Rows 5+ = CIVIC TERRACES placed on NATURAL CONTOURS (constant elevation),
    NOT circular arcs. Each terrace is level by construction, so the ~680-889 CY
    cross-arc leveling penalty (see design_open_low) goes to ~0. Radial spacing
    (tread depth) is set by the terrain: riser / local slope.

Method: for each target tread elevation E_k, solve r(theta) along every fan ray
where bare ground == E_k (the wall rises monotonically with r). The row polyline
{polar(r(theta),theta)} is therefore a contour. We then measure: lateral
levelness (residual along the row ~0), intrinsic bench cut/fill to carve a flat
TREAD-deep platform into the slope, seats, and the centreline sightline C-value.

Planning-grade. NAVD88 (Geoid12A) intl ft. CRS EPSG:6494. -> design_civic_contour/
"""
import json, csv, math, os
import numpy as np, rasterio
from rasterio.transform import rowcol
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

DEM="dem/dem_design_1ft.tif"; OUT="design_civic_contour"
os.makedirs(OUT, exist_ok=True)
CX,CY=19533067.7,750799.2
AX_AZ=132.0; FACE_AZ=(AX_AZ+180)%360          # face 312 (natural fall line ~307)
FOCUS_ELEV=612.5; F_T=15.0; EYE_HT=3.94
STAGE_R=50.0
C_TARGET_FT=0.295                              # 90 mm
EYE_HT=3.94
SEAT_W_C=1.50; SEAT_W_G=1.83; AISLE=0.18

# --- forecourt (stage zone): 4 shallow rows on grade, narrower fan ---
FORE_FAN=40.0; FORE_R=[85.0,88.0,91.0,94.0]; FORE_TREAD=3.0
# --- civic terraces: contour rows, wider fan ---
CIVIC_FAN=55.0; RISER=1.0; CIVIC_TREAD=3.0
R_SCAN_MAX=150.0; E_CAP=629.5                  # stay below the steep band (~R155)

ds=rasterio.open(DEM); A=ds.read(1).astype(float); A[A==ds.nodata]=np.nan; T=ds.transform
def elev(x,y):
    r,c=rowcol(T,x,y)
    return np.nan if not(0<=r<A.shape[0] and 0<=c<A.shape[1]) else A[r,c]
def U(az): a=math.radians(az); return math.sin(a),math.cos(a)
UX,UY=U(AX_AZ); FX,FY=CX+UX*F_T,CY+UY*F_T               # orchestra centre
SFx,SFy=FX+UX*STAGE_R,FY+UY*STAGE_R                     # stage front / focus
def polar(R,az,ox=FX,oy=FY): e,n=U(az); return ox+e*R,oy+n*R

def ec(r):  # centreline ground elevation at radius r (single consistent reference)
    return elev(*polar(r,AX_AZ))
def ray_profile(az):
    """elev vs r along a fan ray (0.5 ft step)."""
    rr=np.arange(70.0,R_SCAN_MAX+1e-6,0.5)
    zz=np.array([elev(*polar(r,az)) for r in rr])
    return rr,zz
def r_at_elev(rr,zz,E):
    """first radius where ground crosses up through E; nan if not in range."""
    f=np.isfinite(zz)
    if not f.any(): return np.nan
    for i in range(1,len(rr)):
        z0,z1=zz[i-1],zz[i]
        if np.isfinite(z0) and np.isfinite(z1) and (z0<=E<=z1):
            t=(E-z0)/(z1-z0) if z1!=z0 else 0.0
            return float(rr[i-1]+t*(rr[i]-rr[i-1]))
    return np.nan

# ---------- FORECOURT rows 1-4 (arcs on grade, centreline-referenced tread) ----------
AZF=np.linspace(AX_AZ-FORE_FAN,AX_AZ+FORE_FAN,81)
fore=[]
for i,R in enumerate(FORE_R):
    e=ec(R)
    coords=[[round(polar(R,az)[0],2),round(polar(R,az)[1],2)] for az in AZF]
    arclen=R*math.radians(2*FORE_FAN)
    sc=int(arclen*(1-AISLE)//SEAT_W_C); sg=int(arclen*(1-AISLE)//SEAT_W_G)
    fore.append(dict(row=i+1,zone="forecourt",R=R,elev=round(float(e),2),
                     dist_to_stage=round(R-STAGE_R,1),coords=coords,
                     arclen=round(arclen,1),sc=sc,sg=sg))

# ---------- CIVIC terraces (contour rows; march by fixed TREAD on centreline) ----------
AZC=np.linspace(AX_AZ-CIVIC_FAN,AX_AZ+CIVIC_FAN,121)
profiles={az:ray_profile(az) for az in AZC}
civic=[]; rn=len(FORE_R)
prev_r_center=FORE_R[-1]; prev_E=fore[-1]["elev"]
r_center=FORE_R[-1]+CIVIC_TREAD
while r_center<=R_SCAN_MAX:
    Ek=ec(r_center)                                     # level elevation of this terrace
    if not np.isfinite(Ek) or Ek>E_CAP: break
    rs=[]; coords=[]
    for az in AZC:
        rr,zz=profiles[az]; r=r_at_elev(rr,zz,Ek)
        if np.isfinite(r):
            rs.append(r); x,y=polar(r,az); coords.append([round(x,2),round(y,2)])
    if len(coords)<10: r_center+=CIVIC_TREAD; continue
    rs=np.array(rs)
    # arc length of the (non-circular) polyline
    arclen=sum(math.dist(coords[k],coords[k+1]) for k in range(len(coords)-1))
    # intrinsic BENCH cut/fill: carve a flat TREAD-deep platform at Ek about r(theta)
    cut=fill=0.0
    for az in AZC:
        rr,zz=profiles[az]; r=r_at_elev(rr,zz,Ek)
        if not np.isfinite(r): continue
        darc=arclen/len(coords)
        for rr2 in np.arange(r-CIVIC_TREAD/2,r+CIVIC_TREAD/2+1e-6,0.5):
            g=elev(*polar(rr2,az))
            if not np.isfinite(g): continue
            d=(Ek-g)*0.5*darc        # 0.5 ft radial cell * darc lateral
            if d>0: fill+=d
            else:   cut+=-d
    # lateral levelness residual along the row (should be ~0 by construction)
    zrow=np.array([elev(*polar(r,az)) for r,az in zip(rs,AZC[:len(rs)])])
    lat_resid=float(np.nanmax(zrow)-np.nanmin(zrow))
    rn+=1
    sc=int(arclen*(1-AISLE)//SEAT_W_C); sg=int(arclen*(1-AISLE)//SEAT_W_G)
    civic.append(dict(row=rn,zone="civic",elev=round(float(Ek),2),
                      r_center=round(float(r_center),1),
                      r_min=round(float(rs.min()),1),r_max=round(float(rs.max()),1),
                      noncirc=round(float(rs.max()-rs.min()),1),
                      tread_depth=round(float(r_center-prev_r_center),2),
                      riser=round(float(Ek-prev_E),2),
                      dist_to_stage=round(float(r_center)-STAGE_R,1),
                      arclen=round(arclen,1),
                      bench_cut_cy=round(cut/27,1),bench_fill_cy=round(fill/27,1),
                      lat_resid=round(lat_resid,2),coords=coords,sc=sc,sg=sg))
    prev_r_center=r_center; prev_E=Ek; r_center+=CIVIC_TREAD

rows=fore+civic
N=len(rows); Ncivic=len(civic)

# ---------- centreline sightline C-values ----------
def cval(D,E,Dp,Ep): return E*(Dp/Dp if False else (Dp/D))-Ep   # E*(Dp/D)-Ep
seq=[]
for x in rows:
    R=x.get("R",x.get("r_center"))
    seq.append((R, x["elev"]))
cvals=[None]
for i in range(1,len(seq)):
    Dp=seq[i-1][0]-STAGE_R; D=seq[i][0]-STAGE_R
    Ep=(seq[i-1][1]+EYE_HT)-FOCUS_ELEV; E=(seq[i][1]+EYE_HT)-FOCUS_ELEV
    C=E*(Dp/D)-Ep
    cvals.append(C)
for x,C in zip(rows,cvals):
    x["C_mm"]=None if C is None else round(C*304.8)
    x["meets_C"]=(C is None) or (C>=C_TARGET_FT-1e-6)

# bay visibility tag: eye clears the ~618 bare rim (from viewshed work)
RIM=618.0
for x in rows:
    eye=x["elev"]+EYE_HT
    x["eye"]=round(eye,2)
    x["sees_bay"]=bool(eye>RIM+0.5)

# ---------- sightline-ENFORCED variant: raise treads above grade to hold 90 mm ----------
# (forward recurrence; added fill above the natural contour is the only extra earthwork)
prev_eye=None; prev_D=None
for x in rows:
    R=x.get("R",x.get("r_center")); D=R-STAGE_R; grade=x["elev"]
    TRD=FORE_TREAD if x["zone"]=="forecourt" else CIVIC_TREAD
    if prev_eye is None:                 # front row: stay on natural grade, nothing ahead of it
        tread=grade
    else:
        Ep=prev_eye-FOCUS_ELEV
        eye_req=FOCUS_ELEV+(C_TARGET_FT+Ep)*(D/prev_D)
        tread=max(grade,eye_req-EYE_HT)   # lift ONLY if grade fails 90 mm
    x["tread_enf"]=round(float(tread),2)
    x["addfill_ft"]=round(float(tread-grade),2)
    x["addfill_cy"]=round(float((tread-grade)*x["arclen"]*TRD/27.0),1)
    prev_eye=tread+EYE_HT; prev_D=D
addfill_cy=sum(x["addfill_cy"] for x in rows)
nlift=sum(1 for x in rows if x["addfill_ft"]>0.01)

# ---------- totals ----------
seats_c=sum(x["sc"] for x in rows); seats_g=sum(x["sg"] for x in rows)
bench_cut=sum(x.get("bench_cut_cy",0) for x in rows)
bench_fill=sum(x.get("bench_fill_cy",0) for x in rows)
lat_pen=sum(x.get("bench_fill_cy",0)+x.get("bench_cut_cy",0) for x in civic)  # gross moved, civic
rise=round(rows[-1]["elev"]-rows[0]["elev"],1)
bay_rows=[x["row"] for x in rows if x["sees_bay"]]

# ---------- geojson ----------
CRS={"type":"name","properties":{"name":"urn:ogc:def:crs:EPSG::6494"}}
def fc(f): return {"type":"FeatureCollection","crs":CRS,"features":f}
feats=[]
for x in rows:
    feats.append({"type":"Feature","properties":{
        "row":x["row"],"zone":x["zone"],"elev_navd88":x["elev"],"eye_navd88":x["eye"],
        "dist_to_stage_ft":x["dist_to_stage"],"C_value_mm":x["C_mm"],"meets_C_90mm":x["meets_C"],
        "sees_bay":x["sees_bay"],"seats_generous_22in":x["sg"],"seats_compact_18in":x["sc"],
        "noncircularity_ft":x.get("noncirc"),"tread_depth_ft":x.get("tread_depth"),
        "bench_cut_cy":x.get("bench_cut_cy"),"bench_fill_cy":x.get("bench_fill_cy"),
        "lateral_residual_ft":x.get("lat_resid"),"datum":"NAVD88 Geoid12A intl ft"},
        "geometry":{"type":"LineString","coordinates":x["coords"]}})
json.dump(fc(feats),open(f"{OUT}/seating_rows.geojson","w"),indent=1)

# stage focus point
stagef=[{"type":"Feature","properties":{"name":"stage_front_focus","elev_navd88":FOCUS_ELEV,
         "centerline_az_deg":AX_AZ,"audience_face_az_deg":FACE_AZ},
         "geometry":{"type":"Point","coordinates":[round(SFx,2),round(SFy,2)]}}]
json.dump(fc(stagef),open(f"{OUT}/stage_focus.geojson","w"),indent=1)

# ---------- table ----------
with open(f"{OUT}/sightline_table.csv","w",newline="") as fh:
    w=csv.writer(fh)
    w.writerow(["row","zone","elev_navd88","eye","dist_to_stage_ft","riser_ft","C_value_mm","meets_C_90mm",
                "sees_bay","tread_depth_ft","noncircularity_ft","bench_cut_cy","bench_fill_cy",
                "lateral_residual_ft","enforced_tread_navd88","addfill_above_grade_ft","addfill_cy",
                "seats_generous_22in","seats_compact_18in"])
    for x in rows:
        w.writerow([x["row"],x["zone"],x["elev"],x["eye"],x["dist_to_stage"],x.get("riser",""),
                    x["C_mm"],x["meets_C"],x["sees_bay"],x.get("tread_depth",""),x.get("noncirc",""),
                    x.get("bench_cut_cy",""),x.get("bench_fill_cy",""),x.get("lat_resid",""),
                    x["tread_enf"],x["addfill_ft"],x["addfill_cy"],x["sg"],x["sc"]])

# ---------- plan PNG ----------
win=210
c0=int((CX-win-T.c)/T.a); c1=int((CX+win-T.c)/T.a)
r1=int((CY-win-T.f)/T.e); r0=int((CY+win-T.f)/T.e)
sub=A[r0:r1,c0:c1]
ext=[T.c+c0*T.a,T.c+c1*T.a,T.f+r1*T.e,T.f+r0*T.e]
fig,ax=plt.subplots(figsize=(9,9))
ax.imshow(sub,extent=ext,origin="upper",cmap="terrain",alpha=0.85)
cs=ax.contour(np.linspace(ext[0],ext[1],sub.shape[1]),
              np.linspace(ext[3],ext[2],sub.shape[0])[::-1],sub,
              levels=np.arange(606,632,2),colors="k",linewidths=0.4,alpha=0.5)
ax.clabel(cs,fontsize=6,fmt="%d")
for x in rows:
    xs=[p[0] for p in x["coords"]]; ys=[p[1] for p in x["coords"]]
    col="tab:red" if x["zone"]=="forecourt" else ("tab:blue" if x["sees_bay"] else "tab:gray")
    ax.plot(xs,ys,color=col,lw=1.6)
ax.plot(SFx,SFy,"k*",ms=16); ax.annotate("stage",(SFx,SFy),fontsize=8)
ax.annotate("",xy=(SFx+U(FACE_AZ)[0]*90,SFy+U(FACE_AZ)[1]*90),
            xytext=(SFx,SFy),arrowprops=dict(arrowstyle="->",color="navy",lw=2))
ax.set_aspect("equal"); ax.set_title(f"Civic contour bowl — face {FACE_AZ:.0f}  (red=forecourt, blue=bay-civic, gray=no-bay)")
ax.set_xlabel("EPSG:6494 X (ft)"); ax.set_ylabel("Y (ft)")
plt.tight_layout(); plt.savefig(f"{OUT}/plan.png",dpi=130); plt.close()

# ---------- summary ----------
print(f"=== Civic contour bowl (face {FACE_AZ:.0f}, AX {AX_AZ:.0f}) ===")
print(f"rows: {len(fore)} forecourt + {Ncivic} civic = {N}   rise {rows[0]['elev']}->{rows[-1]['elev']} = {rise} ft")
print(f"seats: generous {seats_g:,} / compact {seats_c:,}")
print(f"bay-seeing rows (eye>{RIM}+0.5): {bay_rows}")
print(f"sightline C>=90mm: {sum(1 for x in rows if x['meets_C'])}/{N}  "
      f"min civic C={min((x['C_mm'] for x in civic if x['C_mm'] is not None),default='NA')} mm")
print(f"civic lateral leveling residual (mean): {np.mean([x['lat_resid'] for x in civic]):.2f} ft  "
      f"(arc scheme paid 7.7-8.7 ft -> ~680-889 CY; contour ~0)")
print(f"intrinsic bench earthwork: cut {bench_cut:.0f} CY + fill {bench_fill:.0f} CY (carve flat treads into 33% wall)")
nfail=sum(1 for x in civic if not x['meets_C'])
print(f"pure-contour-on-grade sightlines: {sum(1 for x in rows if x['meets_C'])}/{N} meet 90 mm "
      f"({nfail} civic rows dip on flat stretches)")
print(f"sightline-ENFORCED top-up to hold 90 mm everywhere: +{addfill_cy:.0f} CY added fill ({nlift} rows lifted above grade)")
print("\nrow  zone       elev   eye   dist  Cmm  bay  riser  noncirc  +fill_ft")
for x in rows:
    print(f"{x['row']:3d}  {x['zone']:9s} {x['elev']:6.1f} {x['eye']:6.1f} {x['dist_to_stage']:5.0f} "
          f"{str(x['C_mm']):>4s}  {'Y' if x['sees_bay'] else '.':>3s}  "
          f"{str(x.get('riser','')):>5}  {str(x.get('noncirc','')):>6}   "
          f"{x['addfill_ft']:>6.1f}")
print(f"\nwrote {OUT}/seating_rows.geojson sightline_table.csv plan.png stage_focus.geojson")
