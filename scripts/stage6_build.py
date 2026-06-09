"""Stage 6 — treatment train + outlet works geometry builder.
All georeferenced EPSG:6494 (NAD83 MI Central, intl ft); elevations NAVD88 Geoid12A ft."""
import json, math, numpy as np, geopandas as gpd, rasterio
from shapely.geometry import (Point, LineString, Polygon, mapping, shape)
from shapely.ops import unary_union
from rasterio.features import geometry_mask, shapes as rio_shapes
from rasterio.windows import Window

CRS="EPSG:6494"
sf  = gpd.read_file("stage4/stage_floor.geojson")
twc = sf[sf['name']=='treatment_wet_cell'].geometry.iloc[0]
bf  = gpd.read_file("basin_footprint.geojson").geometry.iloc[0]
ot  = gpd.read_file("stage2/outlet_trace.geojson").geometry.iloc[0]
oc  = list(ot.coords)

# ---------- elevation-banded planting / pool footprints from proposed grade ----------
gp = rasterio.open("stage5/grade_proposed.tif")
arr=gp.read(1); nod=gp.nodata; tr=gp.transform
inbasin = geometry_mask([mapping(bf)], out_shape=arr.shape, transform=tr, invert=True) & (arr!=nod)

def band_polys(lo,hi):
    m=(inbasin & (arr>=lo) & (arr<hi)).astype('uint8')
    polys=[shape(g) for g,v in rio_shapes(m, mask=m.astype(bool), transform=tr) if v==1]
    polys=[p for p in polys if p.area>=60]  # drop tiny specks <60 ft2
    return unary_union(polys) if polys else None

WET   = band_polys(600.0, 610.0)   # wet bottom  (<= WQ first-flush WSEL ~610.0)
MARG  = band_polys(610.0, 611.8)   # fluctuating margin (10yr..500yr WSEL band)
UP    = band_polys(611.8, 640.0)   # upland garden (> 500yr WSEL)

def ac(g): return 0 if g is None else g.area/43560.0

# ---------- treatment-train components ----------
# Forebay: ~30x30 ft micro-pool at the SSE/upgradient toe of the wet cell (sheet flow from seating)
wet_b = WET.bounds  # (minx,miny,maxx,maxy)
fb_cx = (wet_b[0]+wet_b[2])/2 + 15   # toward SE
fb_cy = wet_b[1] + 14                # near south edge
half=15.0
forebay = Polygon([(fb_cx-half,fb_cy-half),(fb_cx+half,fb_cy-half),
                   (fb_cx+half,fb_cy+half),(fb_cx-half,fb_cy+half)])
forebay = forebay.intersection(bf)

# Bioretention / WQ cell = wet-bottom footprint minus forebay
wqcell = WET.difference(forebay)

# Control structure point: NE bowl edge near pour point, just inside the bowl
cs = Point(oc[0][0]+6, oc[0][1]-6)

# Outlet pipe: follow outlet_trace from rim to daylight where wide-DEM ground < ~607 (L~460 ft)
wd = rasterio.open("stage2/dem/dem_wide_5ft.tif")
def zwide(x,y): return float(list(wd.sample([(x,y)]))[0][0])
cum=0; prev=oc[0]; pipe_pts=[(cs.x,cs.y)]; daylight=None
for c in oc:
    if c is not oc[0]: cum+=math.dist(prev,c)
    prev=c
    pipe_pts.append(c)
    if daylight is None and cum>50 and zwide(*c) < 607.0:
        daylight=(c[0],c[1],cum,zwide(*c)); 
        pipe_pts.append(c); break
outlet_pipe=LineString(pipe_pts)
plunge=Point(daylight[0],daylight[1])

# Emergency spillway: crest line across rim at pour point, perpendicular-ish to trace, L=25 ft
# trace heading at start:
hx,hy = oc[3][0]-oc[0][0], oc[3][1]-oc[0][1]
hl=math.hypot(hx,hy); ux,uy=hx/hl,hy/hl          # along-trace unit
px,py=-uy,ux                                      # perpendicular
Lc=25.0; cxs,cys=oc[1]                            # crest center near rim
spill_crest=LineString([(cxs-px*Lc/2,cys-py*Lc/2),(cxs+px*Lc/2,cys+py*Lc/2)])
# spillway channel centerline = first ~480 ft of trace
sp_pts=[]; cum=0; prev=oc[0]
for c in oc:
    if c is not oc[0]: cum+=math.dist(prev,c)
    prev=c; sp_pts.append(c)
    if cum>480: break
spill_chan=LineString(sp_pts)

# ---------- emergency-spillway rim-cut earthwork (notch to crest 612.0 through rim plateau) ----------
warr=wd.read(1); wtr=wd.transform; wnod=wd.nodata
tv=[]; cum=0; prev=oc[0]
for c in oc:
    if c is not oc[0]: cum+=math.dist(prev,c)
    prev=c; tv.append((c[0],c[1],cum))
tv=np.array(tv)
dayL=None
for x,y,L in tv:
    if L>50 and zwide(x,y)<612.0: dayL=L; break
reach=LineString([(x,y) for x,y,L in tv if L<=dayL+20])
corridor=reach.buffer(14.0)   # ~28 ft wide (25 ft crest + margins)
cmask=geometry_mask([mapping(corridor)],out_shape=warr.shape,transform=wtr,invert=True)&(warr!=wnod)
cut=np.where(warr>612.0,(warr-612.0),0.0)[cmask].sum()*wd.res[0]*wd.res[1]
cut_cy=cut/27.0
# ---------- write treatment_train.geojson ----------
feats=[]
def F(geom,props): feats.append({"type":"Feature","geometry":mapping(geom),"properties":props})
F(forebay,{"name":"forebay","role":"sediment_pretreatment","pool_bottom_navd88":609.1,
           "perm_pool_depth_ft":1.0,"target_vol_cf":round(0.20*4108),"pct_of_WQv":20,
           "note":"permanent micro-pool at SSE inflow toe; maintenance access for sediment removal"})
F(wqcell,{"name":"bioretention_wq_cell","role":"water_quality_treatment","cell_bottom_navd88":609.1,
          "wq_pool_navd88":610.0,"WQv_acft":0.0943,"WQv_cf":4108,"footprint_ac":round(ac(wqcell),3),
          "media":"bioretention sand/compost + native plantings; optional underdrain (TIGHT soils)",
          "target_drawdown_hr":"24-48 (parametric: SANDY hrs / TIGHT needs underdrain)"})
F(cs,{"name":"control_structure","role":"controlled_outlet","base_invert_navd88":609.5,
      "wqv_orifice_in":2.0,"wqv_orifice_invert_navd88":609.5,"overflow_weir_navd88":611.0,
      "note":"riser/weir box; orifice = WQv drawdown (~24-36 h) or tie to underdrain; weir caps design WSEL"})
F(outlet_pipe,{"name":"outlet_pipe","role":"controlled_discharge","diam_in":15,
               "length_ft":round(daylight[2],0),"daylight_navd88":round(daylight[3],1),
               "note":"buried outfall NE through rim to plunge pool; ALT/preferred = tie to municipal storm sewer (DATA_GAPS)"})
F(plunge,{"name":"plunge_pool_riprap","role":"energy_dissipation","ground_navd88":round(daylight[3],1),
          "note":"riprap apron / plunge pool at pipe daylight; discharges to natural swale toward bay path"})
F(spill_crest,{"name":"emergency_spillway_crest","role":"emergency_overflow","crest_navd88":612.0,
               "crest_length_ft":25,"weir_C":2.6,"design_storm":"500yr-24hr (surface)",
               "H_500yr_ft":0.20,"WSEL_500yr":612.20,"freeboard_to_floor_ft":0.80,
               "floor_navd88":613.0,"note":"broad-crested armored notch in NE rim; protects occupied floor"})
F(spill_chan,{"name":"emergency_spillway_channel","role":"non_erosive_overflow_route",
              "lining":"riprap / turf-reinforcement mat","along":"outlet_trace alignment",
              "rim_cut_cy_est":round(cut_cy,0),
              "note":"defined non-erosive route to bay path; rim-cut earthwork is a Stage-6 add not in Stage-5 balance"})
gpd.GeoDataFrame.from_features(feats,crs=CRS).to_file("stage6/treatment_train.geojson",driver="GeoJSON")

# ---------- write planting_zones.geojson ----------
pz=[]
def PZ(geom,name,lo,hi,inund,palette):
    if geom is None or geom.is_empty: return
    pz.append({"type":"Feature","geometry":mapping(geom),"properties":{
        "zone":name,"elev_lo_navd88":lo,"elev_hi_navd88":hi,"inundation":inund,
        "area_ac":round(ac(geom),3),"palette":palette}})
PZ(WET ,"wet_bottom",     609.1,610.0,"<= WQ first-flush (wet most events)",
   "emergent wetland / sedge-rush; shade discharge for coldwater")
PZ(MARG,"fluctuating_margin",610.0,611.8,"10yr-500yr WSEL band (intermittent)",
   "wet-mesic meadow + shrubs (facultative)")
PZ(UP  ,"upland_garden",  611.8,640.0,"> 500yr WSEL (never inundated by design)",
   "native upland prairie/meadow + canopy; seating terraces & east garden")
gpd.GeoDataFrame.from_features(pz,crs=CRS).to_file("stage6/planting_zones.geojson",driver="GeoJSON")

print("=== AREAS (ac) ===")
print(f"forebay {ac(forebay):.4f}  wqcell {ac(wqcell):.3f}  wet {ac(WET):.3f}  margin {ac(MARG):.3f}  upland {ac(UP):.3f}")
print(f"outlet pipe length {daylight[2]:.0f} ft, daylight z {daylight[3]:.1f}")
print(f"emergency spillway rim-cut (planning est) = {cut_cy:.0f} CY")
wd.close(); gp.close()
