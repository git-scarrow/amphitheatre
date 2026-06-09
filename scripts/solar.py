"""NOAA solar position algorithm (Meeus-based, ~0.01 deg accuracy).
Pure numpy, no external deps. Returns azimuth (deg from N, clockwise) and
altitude (deg above horizon, refraction-corrected)."""
import numpy as np
from datetime import datetime, timedelta, timezone

def _julian(dt_utc):
    y=dt_utc.year; m=dt_utc.month
    d=dt_utc.day + (dt_utc.hour + dt_utc.minute/60 + dt_utc.second/3600)/24
    if m<=2: y-=1; m+=12
    A=y//100; B=2-A+A//4
    return int(365.25*(y+4716))+int(30.6001*(m+1))+d+B-1524.5

def sun_position(dt_local, lat, lon, utc_offset_hours):
    """dt_local: naive datetime in local clock; utc_offset_hours e.g. -4 for EDT."""
    dt_utc=dt_local - timedelta(hours=utc_offset_hours)
    JD=_julian(dt_utc)
    T=(JD-2451545.0)/36525.0
    L0=(280.46646+36000.76983*T+0.0003032*T*T)%360
    M=357.52911+35999.05029*T-0.0001537*T*T
    Mr=np.radians(M)
    C=(1.914602-0.004817*T-0.000014*T*T)*np.sin(Mr)+(0.019993-0.000101*T)*np.sin(2*Mr)+0.000289*np.sin(3*Mr)
    true_long=L0+C
    omega=125.04-1934.136*T
    lam=true_long-0.00569-0.00478*np.sin(np.radians(omega))
    eps0=23+(26+((21.448-T*(46.815+T*(0.00059-T*0.001813))))/60)/60
    eps=eps0+0.00256*np.cos(np.radians(omega))
    lamr=np.radians(lam); epsr=np.radians(eps)
    decl=np.degrees(np.arcsin(np.sin(epsr)*np.sin(lamr)))
    # equation of time (minutes)
    y=np.tan(epsr/2)**2
    L0r=np.radians(L0)
    Eot=4*np.degrees(y*np.sin(2*L0r)-2*0.016708634*np.sin(Mr)
        +4*0.016708634*y*np.sin(Mr)*np.cos(2*L0r)
        -0.5*y*y*np.sin(4*L0r)-1.25*0.016708634**2*np.sin(2*Mr))
    # true solar time
    minutes=dt_local.hour*60+dt_local.minute+dt_local.second/60
    tst=(minutes+Eot+4*lon-60*utc_offset_hours)%1440
    ha=tst/4-180  # hour angle deg
    if ha< -180: ha+=360
    har=np.radians(ha); latr=np.radians(lat); declr=np.radians(decl)
    zenith=np.degrees(np.arccos(np.sin(latr)*np.sin(declr)+np.cos(latr)*np.cos(declr)*np.cos(har)))
    alt=90-zenith
    # azimuth
    az=np.degrees(np.arctan2(np.sin(har),
        np.cos(har)*np.sin(latr)-np.tan(declr)*np.cos(latr)))
    az=(az+180)%360
    # atmospheric refraction (Saemundsson) for alt>-1
    if alt>-1:
        R=1.02/np.tan(np.radians(alt+10.3/(alt+5.11)))/60
        alt=alt+R
    return az, alt, decl
