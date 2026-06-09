#!/usr/bin/env python3
"""
Design exploration: minimal-work, OPEN-arc seating that sits on the natural rake.
Sweeps fan half-angle x outer radius; reuses Stage-4 sightline+earthwork logic.
Reports seats, tread fill volume (CY, fill-only per Stage-4), max fill, rake quality.
Tread earthwork is fill-only (never cut below terrain), matching stage4_amphitheater.py.
"""
import math, numpy as np, rasterio
from rasterio.transform import rowcol

DEM="dem/dem_design_1ft.tif"
CX,CY=19533067.7,750799.2
AX_AZ=150.0; FOCUS_ELEV=612.5; F_T=15.0; EYE_HT=3.94
R_INNER=85.0; TREAD=3.00; C_TGT=0.295
SEAT_W=1.83  # generous 22in (civic comfort); compact also reported
SEAT_W_C=1.50
AISLE=0.18
CELL_AREA=1.0  # 1-ft DEM

ds=rasterio.open(DEM); A=ds.read(1); nod=ds.nodata; T=ds.transform
def elev(x,y):
    r,c=rowcol(T,x,y)
    if 0<=r<A.shape[0] and 0<=c<A.shape[1]:
        v=A[r,c]
        return None if (v==nod or not np.isfinite(v)) else float(v)
    return None
def unit(az):
    a=math.radians(az); return math.sin(a),math.cos(a)
UX,UY=unit(AX_AZ); FX,FY=CX+UX*F_T,CY+UY*F_T
def polar(R,az):
    ex,ny=unit(az); return FX+ex*R,FY+ny*R
def terr_med(R,fan,n=41):
    azs=np.linspace(AX_AZ-fan,AX_AZ+fan,n); vals=[]
    for az in azs:
        e=elev(*polar(R,az))
        if e is not None: vals.append(e)
    return float(np.median(vals)) if vals else None

def design(fan,R_OUTER):
    radii=[]; r=R_INNER
    while r<=R_OUTER+1e-6: radii.append(round(r,2)); r+=TREAD
    rows=[dict(R=R,terr=terr_med(R,fan)) for R in radii]
    rows=[x for x in rows if x["terr"] is not None]
    if len(rows)<3: return None
    rows[0]["tread"]=max(rows[0]["terr"],FOCUS_ELEV+0.5)
    for i in range(1,len(rows)):
        Dp,D=rows[i-1]["R"],rows[i]["R"]
        Ep=(rows[i-1]["tread"]+EYE_HT)-FOCUS_ELEV
        tread_req=FOCUS_ELEV+(C_TGT+Ep)*(D/Dp)-EYE_HT
        rows[i]["tread"]=max(tread_req,rows[i]["terr"])
    fill_v=0.0; maxfill=0.0; nfill=0
    sc=sg=0
    for x in rows:
        cf=x["tread"]-x["terr"]               # >=0 fill-only
        arc=x["R"]*math.radians(2*fan)
        area=arc*TREAD
        fill_v+=cf*area
        if cf>0.05: nfill+=1
        maxfill=max(maxfill,cf)
        usable=arc*(1-AISLE)
        sg+=max(0,int(usable//SEAT_W)); sc+=max(0,int(usable//SEAT_W_C))
    top=rows[-1]
    return dict(fan=fan,Rout=R_OUTER,nrows=len(rows),
                seats_gen=sg,seats_comp=sc,
                fill_cy=fill_v/27.0,maxfill=maxfill,nfill=nfill,
                toe=rows[0]["terr"],top_terr=top["terr"],top_tread=top["tread"],
                height=top["tread"]-rows[0]["tread"])

print(f"{'fan°tot':>7} {'Rout':>5} {'rows':>4} {'seatsG':>6} {'seatsC':>6} "
      f"{'fillCY':>7} {'maxfill':>7} {'nfill':>5} {'height':>6} {'topGrade':>8}")
for fan in (30,45,55,65,75):
    for Rout in (130,145,160,172):
        d=design(fan,Rout)
        if d: print(f"{2*fan:>7} {Rout:>5.0f} {d['nrows']:>4} {d['seats_gen']:>6} "
                    f"{d['seats_comp']:>6} {d['fill_cy']:>7.0f} {d['maxfill']:>7.2f} "
                    f"{d['nfill']:>5} {d['height']:>6.1f} {d['top_terr']:>8.1f}")
