"""Stage 7 shadow caster + sun-path/glare study.
Casts terrain shadows over grade_proposed for representative sun positions,
builds sun-path diagrams, and a hillshade base. Pure ray-march, scipy bilinear."""
import sys, numpy as np, rasterio
sys.path.insert(0,"scripts")
from scipy.ndimage import map_coordinates
from solar import sun_position
from datetime import datetime, timedelta
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LightSource

LAT,LON=45.374516,-84.958225
DEM="stage5/grade_proposed.tif"
FOCAL=(19533075.2,750786.2)   # stage front / sightline focus
VIEW_AZ=330.0
SEAT_CTR=(19533150.0,750678.0) # approx seating-bowl centroid (SE of focal)

def load_dem():
    with rasterio.open(DEM) as ds:
        z=ds.read(1).astype(float); z[z==ds.nodata]=np.nan
        return z, ds.transform, ds.bounds, ds.res[0]

def cast_shadow(z, az, alt, px):
    """Return boolean shadow mask. az deg from N clockwise; alt deg."""
    if alt<=0.5: return np.ones_like(z,bool)  # sun down -> all shadow
    H,W=z.shape
    # unit step toward the sun, in pixels (row increases southward => dy_row = -cos(az))
    dx=np.sin(np.radians(az)); dy=np.cos(np.radians(az))
    col_step=dx; row_step=-dy
    tan_a=np.tan(np.radians(alt))
    zmin=np.nanmin(z); zmax=np.nanmax(z)
    rr,cc=np.mgrid[0:H,0:W].astype(float)
    shadow=np.zeros((H,W),bool)
    maxrelief=zmax-zmin
    step_ft=1.5
    s=step_ft
    nmax=int(np.hypot(H,W))+5
    for _ in range(nmax):
        rs=rr+row_step*(s/px); cs=cc+col_step*(s/px)
        samp=map_coordinates(np.nan_to_num(z,nan=-9999),[rs,cs],order=1,
                             mode='constant',cval=-9999)
        clear=z+ s*tan_a
        blocked=(samp> clear)&(samp>-9000)
        shadow|=blocked
        if s*tan_a> maxrelief: break
        s+=step_ft
    shadow[np.isnan(z)]=False
    return shadow

def main():
    z,tr,bounds,px=load_dem()
    extent=[bounds.left,bounds.right,bounds.bottom,bounds.top]
    ls=LightSource(azdeg=315,altdeg=45)
    base=ls.hillshade(np.nan_to_num(z,nan=np.nanmin(z)),vert_exag=2,dx=px,dy=px)

    # ---- representative times ----
    times=[
     ("Solstice 13:00 (midday)",datetime(2026,6,20,13),-4),
     ("Solstice 18:00",datetime(2026,6,20,18),-4),
     ("Solstice 19:00",datetime(2026,6,20,19),-4),
     ("Solstice 20:00",datetime(2026,6,20,20),-4),
     ("Solstice 21:00 (near sunset)",datetime(2026,6,20,21),-4),
     ("Equinox 18:00",datetime(2026,9,22,18),-4),
     ("Equinox 19:00 (near sunset)",datetime(2026,9,22,19),-4),
    ]
    fig,axes=plt.subplots(2,4,figsize=(20,10))
    axes=axes.ravel()
    fx,fy=FOCAL
    for ax,(name,dt,off) in zip(axes,times):
        az,alt,_=sun_position(dt,LAT,LON,off)
        sh=cast_shadow(z,az,alt,px)
        ax.imshow(base,cmap='gray',extent=extent,origin='upper',alpha=0.9)
        ov=np.zeros((*z.shape,4)); ov[sh]=[0.12,0.18,0.45,0.5]
        ax.imshow(ov,extent=extent,origin='upper')
        # seating + stage markers
        ax.plot(fx,fy,'r^',ms=10,label='stage/focus')
        # view axis arrow
        L=260; ax.annotate('',xy=(fx+L*np.sin(np.radians(VIEW_AZ)),fy+L*np.cos(np.radians(VIEW_AZ))),
            xytext=(fx,fy),arrowprops=dict(color='cyan',arrowstyle='->',lw=2))
        # sun direction arrow (toward sun)
        if alt>0.5:
            ax.annotate('',xy=(fx+L*np.sin(np.radians(az)),fy+L*np.cos(np.radians(az))),
                xytext=(fx,fy),arrowprops=dict(color='orange',arrowstyle='->',lw=2))
        ax.set_title(f"{name}\naz={az:.0f}  alt={alt:.0f}  shadow={100*sh.mean():.0f}%",fontsize=10)
        ax.set_xticks([]); ax.set_yticks([])
    axes[-1].axis('off')
    axes[-1].text(0.05,0.9,"Cyan = bay-view/seating axis (az 330)\nOrange = direction to sun\n"
        "Blue overlay = terrain shadow\nRed ^ = stage / sightline focus\n\n"
        "Hillshade base: grade_proposed (Stage 5)\nEPSG:6494, NAVD88 ft",
        va='top',fontsize=11,transform=axes[-1].transAxes)
    fig.suptitle("Stage 7 — Shadow studies, Petoskey Pit amphitheater (45.37 N)",fontsize=15)
    fig.tight_layout(rect=[0,0,1,0.97])
    fig.savefig("stage7/shadow_studies.png",dpi=110)
    print("wrote shadow_studies.png")

    # ---- sun-path diagram (polar: az around, alt radial inverted) ----
    fig2,(axp,axc)=plt.subplots(1,2,figsize=(16,8),subplot_kw=None)
    # polar
    axp=fig2.add_subplot(1,2,1,projection='polar')
    axp.set_theta_zero_location('N'); axp.set_theta_direction(-1)
    days={"Summer solstice Jun 20":(datetime(2026,6,20),-4,'crimson'),
          "Equinox Mar/Sep":(datetime(2026,9,22),-4,'goldenrod'),
          "Winter solstice Dec 21":(datetime(2026,12,21),-5,'navy')}
    for name,(d,off,col) in days.items():
        azs=[]; alts=[]
        for m in range(0,24*60,10):
            dt=d+timedelta(minutes=m)
            a,al,_=sun_position(dt,LAT,LON,off)
            if al>0: azs.append(np.radians(a)); alts.append(90-al)
        axp.plot(azs,alts,color=col,lw=2,label=name)
    # evening hour ticks for solstice
    for h in range(17,22):
        a,al,_=sun_position(datetime(2026,6,20,h),LAT,LON,-4)
        if al>0:
            axp.plot(np.radians(a),90-al,'o',color='crimson',ms=5)
            axp.annotate(f"{h}h",(np.radians(a),90-al),fontsize=8,color='crimson')
    axp.set_rmax(90); axp.set_rticks([0,30,60,90]); axp.set_yticklabels(['90','60','30','0'])
    # view axis + glare sector
    axp.plot([np.radians(VIEW_AZ)]*2,[0,90],'c--',lw=2,label='bay-view axis 330')
    axp.bar(np.radians(287.5),90,width=np.radians(35),bottom=0,color='orange',alpha=0.15)
    axp.annotate('low-sun\nglare sector\n(270-305)',(np.radians(290),70),fontsize=8,color='darkorange')
    axp.legend(loc='upper right',bbox_to_anchor=(1.25,1.1),fontsize=8)
    axp.set_title("Sun paths over Petoskey Pit (alt at center=90)")
    # cartesian az vs alt evening detail
    for name,(d,off,col) in days.items():
        ts=[];als=[];azs=[]
        for m in range(12*60,24*60,5):
            dt=d+timedelta(minutes=m); a,al,_=sun_position(dt,LAT,LON,off)
            if al>-1: ts.append(dt.hour+dt.minute/60); als.append(al); azs.append(a)
        axc.plot(azs,als,color=col,lw=2,label=name)
    axc.axvspan(270,305,color='orange',alpha=0.15,label='glare sector (W-WNW)')
    axc.axvline(330,color='c',ls='--',lw=2,label='view axis 330')
    axc.axhline(0,color='k',lw=0.8); axc.axhline(15,color='r',ls=':',label='alt 15 (glare ceiling)')
    axc.set_xlabel('Sun azimuth (deg from N)'); axc.set_ylabel('Sun altitude (deg)')
    axc.set_xlim(180,340); axc.set_ylim(-2,60); axc.legend(fontsize=8); axc.grid(alpha=0.3)
    axc.set_title("Afternoon-evening azimuth vs altitude")
    fig2.suptitle("Stage 7 — Sun-path diagrams, Petoskey Pit (45.37 N, -84.96 W)",fontsize=14)
    fig2.tight_layout(rect=[0,0,1,0.96])
    fig2.savefig("stage7/sun_path_diagrams.png",dpi=120)
    print("wrote sun_path_diagrams.png")

if __name__=="__main__":
    main()
