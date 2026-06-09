#!/usr/bin/env python3
"""
DESIGN: "Open civic bowl" — minimal-work, open-arc amphitheater on the natural rake.
v2: stage pushed FORWARD into the orchestra so the first row is ~45 ft from the stage
    front (was 85 ft). Seats stay on natural grade; sightlines re-derived to the new
    (nearer) focus and still clear 90 mm in every row. Drainage cell unchanged.

Geometry note: the seating ARC CENTRE (which keeps rows level / concentric with the
bowl contours) is distinct from the STAGE FRONT / sightline focus, which now sits
STAGE_R ft up the centreline toward the audience — exactly how a Greek theatron seats
the cavea about the orchestra centre while the skene stands forward of it.

Planning-grade. NAVD88 (Geoid12A) intl ft. CRS EPSG:6494. Outputs -> design_open_low/.
"""
import json, csv, math, pickle
import numpy as np, rasterio
from rasterio.transform import rowcol
import matplotlib; matplotlib.use("Agg")

DEM="dem/dem_design_1ft.tif"; OUT="design_open_low"
CX,CY=19533067.7,750799.2
AX_AZ=150.0; FACE_AZ=(AX_AZ+180)%360
FOCUS_ELEV=612.5; F_T=15.0; EYE_HT=3.94
R_INNER=85.0; R_OUTER=130.0; TREAD=3.00
FAN_HALF=55.0
STAGE_R=50.0                       # <-- stage front / sightline focus, ft up-centreline from arc centre
C_TARGET_FT=0.295
SEAT_W_C=1.50; SEAT_W_G=1.83; AISLE=0.18; REGRADE_FT=1.5

ds=rasterio.open(DEM); A=ds.read(1).astype(float); A[A==ds.nodata]=np.nan; T=ds.transform
def elev(x,y):
    r,c=rowcol(T,x,y); return np.nan if not(0<=r<A.shape[0] and 0<=c<A.shape[1]) else A[r,c]
def U(az): a=math.radians(az); return math.sin(a),math.cos(a)
UX,UY=U(AX_AZ); FX,FY=CX+UX*F_T,CY+UY*F_T          # seating ARC CENTRE
SFx,SFy=FX+UX*STAGE_R,FY+UY*STAGE_R                 # STAGE FRONT / sightline focus
def polar(R,az,ox=FX,oy=FY): e,n=U(az); return ox+e*R,oy+n*R
def arc(R,fan=FAN_HALF,n=81):
    return [[round(polar(R,az)[0],2),round(polar(R,az)[1],2)]
            for az in np.linspace(AX_AZ-fan,AX_AZ+fan,n)]
def terr_med(R,n=41):
    vs=[elev(*polar(R,az)) for az in np.linspace(AX_AZ-FAN_HALF,AX_AZ+FAN_HALF,n)]
    vs=[v for v in vs if np.isfinite(v)]; return float(np.median(vs)) if vs else np.nan

radii=[]; r=R_INNER
while r<=R_OUTER+1e-6: radii.append(round(r,2)); r+=TREAD
rows=[dict(row=i+1,R=R,terr=terr_med(R)) for i,R in enumerate(radii)]
# distance from the (forward) focus is R - STAGE_R
rows[0]["tread"]=round(max(rows[0]["terr"],FOCUS_ELEV+0.5),2)
for i in range(1,len(rows)):
    Dp,D=rows[i-1]["R"]-STAGE_R, rows[i]["R"]-STAGE_R
    Ep=(rows[i-1]["tread"]+EYE_HT)-FOCUS_ELEV
    tread_req=FOCUS_ELEV+(C_TARGET_FT+Ep)*(D/Dp)-EYE_HT
    rows[i]["tread"]=math.ceil(max(tread_req,rows[i]["terr"])*100)/100
def cval(D,E,Dp,Ep): return E*(Dp/D)-Ep
cap={"compact":0,"generous":0}
for i,x in enumerate(rows):
    x["eye"]=round(x["tread"]+EYE_HT,2); x["E"]=x["eye"]-FOCUS_ELEV
    x["eye_t"]=x["terr"]+EYE_HT; x["E_t"]=x["eye_t"]-FOCUS_ELEV
    x["cutfill"]=round(x["tread"]-x["terr"],2)
    x["rise"]=round(x["tread"]-(rows[i-1]["tread"] if i else FOCUS_ELEV),2)
    x["dist_to_stage"]=round(x["R"]-STAGE_R,1)
    if i==0: x["C"]=None; x["C_t"]=None
    else:
        Dp,D=rows[i-1]["R"]-STAGE_R, x["R"]-STAGE_R
        x["C"]=cval(D,x["E"],Dp,rows[i-1]["E"]); x["C_t"]=cval(D,x["E_t"],Dp,rows[i-1]["E_t"])
    x["meets"]=(x["C"] is None) or (x["C"]>=C_TARGET_FT-1e-6)
    x["meets_t"]=(x["C_t"] is None) or (x["C_t"]>=C_TARGET_FT-1e-6)
    x["regrade"]=abs(x["cutfill"])>REGRADE_FT
    al=x["R"]*math.radians(2*FAN_HALF); us=al*(1-AISLE)
    x["sc"]=max(0,int(us//SEAT_W_C)); x["sg"]=max(0,int(us//SEAT_W_G))
    cap["compact"]+=x["sc"]; cap["generous"]+=x["sg"]
N=len(rows)
fill_vol=sum(max(0,x["cutfill"])*x["R"]*math.radians(2*FAN_HALF)*TREAD for x in rows)/27.0
height=round(rows[-1]["tread"]-rows[0]["tread"],1)
orch=round(R_INNER-STAGE_R,0)

# ADA
mid=rows[N//2]
ada=dict(A_drop=round(rows[0]["tread"]-FOCUS_ELEV+5.0,1),A_runs=max(1,math.ceil((rows[0]["tread"]-FOCUS_ELEV+5.0)/2.5)),
         B_row=mid["row"],B_drop=round(mid["tread"]-FOCUS_ELEV,1),B_runs=max(1,math.ceil((mid["tread"]-FOCUS_ELEV)/2.5)))

CRS={"type":"name","properties":{"name":"urn:ogc:def:crs:EPSG::6494"}}
def fc(f): return {"type":"FeatureCollection","crs":CRS,"features":f}
def feat(p,g): return {"type":"Feature","properties":p,"geometry":g}

seat=[feat({"row":x["row"],"radius_ft":x["R"],"dist_to_stage_ft":x["dist_to_stage"],
            "tread_elev_navd88":x["tread"],"terrain_elev_navd88":round(x["terr"],2),
            "cut_fill_ft":x["cutfill"],"row_rise_ft":x["rise"],
            "C_value_proposed_mm":None if x["C"] is None else round(x["C"]*304.8),
            "C_value_terrain_mm":None if x["C_t"] is None else round(x["C_t"]*304.8),
            "meets_C_proposed":bool(x["meets"]),"meets_C_on_terrain":bool(x["meets_t"]),
            "needs_regrade":bool(x["regrade"]),"seats_compact_18in":x["sc"],
            "seats_generous_22in":x["sg"],"datum":"NAVD88 Geoid12A intl ft"},
           {"type":"LineString","coordinates":arc(x["R"])}) for x in rows]
json.dump(fc(seat),open(f"{OUT}/seating_rows.geojson","w"),indent=1)

# stage: 70 (W) x 34 (D) core + angled side shoulders, downstage edge at STAGE_R (faces audience SSE)
STAGE_W=70.0; STAGE_D=34.0; SH_OUT=17.0           # shoulder lateral flare beyond the core
PERPx,PERPy=U(AX_AZ+90)
def pt(R,lat):
    px,py=polar(R,AX_AZ); return [round(px+PERPx*lat,2),round(py+PERPy*lat,2)]
hw=STAGE_W/2; Rds=STAGE_R; Rus=STAGE_R-STAGE_D
core=[pt(Rds,hw),pt(Rds,-hw),pt(Rus,-hw),pt(Rus,hw),pt(Rds,hw)]
def shoulder(sgn):  # angled wing flaring the downstage corner out to the fan, tapering to the core upstage
    return [pt(Rds,sgn*hw),pt(Rds-2,sgn*(hw+SH_OUT)),pt(Rds-20,sgn*(hw+SH_OUT-6)),pt(Rus,sgn*hw),pt(Rds,sgn*hw)]
front_w=STAGE_W+2*SH_OUT                            # ~104 ft downstage frontage incl. shoulders
src=json.load(open("stage4/stage_floor.geojson"))
floor=[f for f in src["features"] if f["properties"].get("name") in {"treatment_wet_cell","bay_view_axis"}]
floor.append(feat({"name":"focal_point_stage_front","elev_navd88":FOCUS_ELEV,
                   "centerline_az_deg":AX_AZ,"audience_face_az_deg":FACE_AZ,
                   "note":f"sightline focus + stage front, {orch:.0f} ft from row 1"},
                  {"type":"Point","coordinates":[round(SFx,2),round(SFy,2)]}))
floor.append(feat({"name":"stage","elev_navd88":FOCUS_ELEV,"width_ft":STAGE_W,"depth_ft":STAGE_D,
                   "frontage_with_shoulders_ft":front_w,
                   "note":"70x34 core stage pushed forward into the orchestra"},
                  {"type":"Polygon","coordinates":[core]}))
floor.append(feat({"name":"stage_shoulder_left","elev_navd88":FOCUS_ELEV,
                   "note":"angled side shoulder framing the 110-deg fan"},
                  {"type":"Polygon","coordinates":[shoulder(1)]}))
floor.append(feat({"name":"stage_shoulder_right","elev_navd88":FOCUS_ELEV,
                   "note":"angled side shoulder framing the 110-deg fan"},
                  {"type":"Polygon","coordinates":[shoulder(-1)]}))
forecourt=[[round(SFx,2),round(SFy,2)]]+arc(R_INNER)+[[round(SFx,2),round(SFy,2)]]
floor.append(feat({"name":"event_floor_forecourt","grade_elev_navd88":FOCUS_ELEV,
                   "note":f"orchestra apron between stage front and row 1 (~{orch:.0f} ft); floor-level accessible seating"},
                  {"type":"Polygon","coordinates":[forecourt]}))
json.dump(fc(floor),open(f"{OUT}/stage_floor.geojson","w"),indent=1)

def ramp_line(az,Rf,Rt): 
    p0=polar(Rf,az); p1=polar(Rt,az); return [[round(p0[0],2),round(p0[1],2)],[round(p1[0],2),round(p1[1],2)]]
ada_f=[feat({"name":"accessible_route_A_floor","type":"switchback_ramp","total_drop_ft":ada["A_drop"],
             "runs":ada["A_runs"],"design_running_slope_pct":8.33,"cross_slope_target_pct":2.0,
             "note":"primary accessible entry to event floor / front accessible seating"},
            {"type":"LineString","coordinates":ramp_line(FACE_AZ,70,10)}),
       feat({"name":f"accessible_route_B_mid_row{ada['B_row']}","type":"switchback_ramp","total_drop_ft":ada["B_drop"],
             "runs":ada["B_runs"],"design_running_slope_pct":8.33,"cross_slope_target_pct":2.0,
             "note":f"accessible entry to mid cross-aisle at row {ada['B_row']}"},
            {"type":"LineString","coordinates":ramp_line(AX_AZ+FAN_HALF,R_OUTER+25,mid["R"])}),
       feat({"name":"mid_cross_aisle","type":"level_walk","row":ada["B_row"],"elev_navd88":mid["tread"],
             "note":"level accessible cross-aisle / wheelchair dispersion line"},
            {"type":"LineString","coordinates":arc(mid["R"])})]
json.dump(fc(ada_f),open(f"{OUT}/ada_route.geojson","w"),indent=1)

with open(f"{OUT}/sightline_table.csv","w",newline="") as fh:
    w=csv.writer(fh)
    w.writerow(["row","radius_ft","dist_to_stage_ft","terrain_elev_navd88","proposed_tread_elev_navd88",
                "row_rise_ft","cut_fill_ft","eye_elev_proposed","C_value_terrain_mm","C_value_proposed_mm",
                "C_target_mm","meets_C_on_bare_terrain","meets_C_proposed","needs_regrade",
                "seats_compact_18in","seats_generous_22in"])
    for x in rows:
        w.writerow([x["row"],x["R"],x["dist_to_stage"],round(x["terr"],2),x["tread"],x["rise"],x["cutfill"],
                    x["eye"],"" if x["C_t"] is None else round(x["C_t"]*304.8),
                    "" if x["C"] is None else round(x["C"]*304.8),90,
                    x["meets_t"],x["meets"],x["regrade"],x["sc"],x["sg"]])

pickle.dump(dict(rows=rows,cap=cap,F=(FX,FY),SF=(SFx,SFy),ada=ada,fill_vol=fill_vol,height=height,orch=orch,
                 params=dict(AX_AZ=AX_AZ,FACE_AZ=FACE_AZ,FAN_HALF=FAN_HALF,R_INNER=R_INNER,R_OUTER=R_OUTER,
                             TREAD=TREAD,FOCUS_ELEV=FOCUS_ELEV,EYE_HT=EYE_HT,C_TARGET_FT=C_TARGET_FT,
                             NROWS=N,STAGE_R=STAGE_R)),open(f"{OUT}/_ctx.pkl","wb"))
print(f"rows={N} fan=±{FAN_HALF:.0f}° R{R_INNER:.0f}-{R_OUTER:.0f}  stage_R={STAGE_R:.0f}  orchestra(row1→stage)={orch:.0f} ft")
print(f"seats compact={cap['compact']:,} generous={cap['generous']:,}  tread fill={fill_vol:.0f} CY")
print(f"sightlines on bare terrain: {sum(1 for x in rows if x['meets_t'])}/{N}  minC={min((x['C_t']*304.8 for x in rows if x['C_t'] is not None)):.0f} mm")
print(f"row1 dist={rows[0]['dist_to_stage']} ft  rowN dist={rows[-1]['dist_to_stage']} ft  rise={height} ft")
