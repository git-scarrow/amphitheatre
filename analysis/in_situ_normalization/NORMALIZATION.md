# Flank normalization report — three-section civic bowl

Measured study (no visual judgment): section balance, composite audience frame, and whether the east flank can be extended or the south flank should be shortened. Planning-grade; EPSG:6494, NAVD88 intl ft.

## 1 · Section balance (current Scenario E package)

| family | rows | arc ft | Band-A seats | radial depth ft | az span | row1→stage front ft | centroid→stage ft |
|---|---|---|---|---|---|---|---|
| east | 15 | 835 | 365 | 71.8 | 87–116° | 17.3 | 98.7 |
| bend | 15 | 952 | 419 | 71.8 | 120–151° | 20.6 | 90.7 |
| south | 15 | 1129 | 499 | 71.8 | 154–195° | 2.2 | 73.2 |

Arc-length min/max ratio **0.74** vs declared threshold 0.75 → **justification required and provided** (see below).

## 2 · Composite audience frame

- seat-weighted audience centroid: (19533142.9, 750713.4)
- dominant facing (seat-weighted circular mean of band normals): **az 323.4°** (axis from stage: 143.4°)
- bearing stage-front → centroid: **124.6°** vs inherited stage axis 150.0° → **axis mismatch -25.4°**
- lateral offset of the centroid from the stage axis: **-22.2 ft**

## 3 · Why the east flank is short (measured)

- march caps: east az 85 / south az 197 (declared in `design_extended_bays.py`)
- row-18 end gaps: east → Petoskey St 46.9 ft; south → E Mitchell St 60.3 ft
- contour-walk extension test (rows 6-18, east cap end): **~342 ft total** additional on-contour arc (~149 seats upper bound) before the 45° seat-splay gate stops every row — the basin wraps north and seats would face across the bowl; per-row detail in section_balance.json

## 4 · Candidates

| name | Δseats | balance ratio | cut/fill proxy CY | verdict |
|---|---|---|---|---|
| N0_status_quo | +0 | 0.74 | 0.0 | SELECTED |
| N1_east_contour_extension | +149 | 0.81 | 11.4 | CANDIDATE (analysis-tier) |
| N2_add_row19_all | +114 | 0.74 | 6.2 | CANDIDATE (analysis-tier) |
| N3_trim_south_to_balance | -86 | 0.88 | 0.0 | REJECTED |

### Selected: N0_status_quo

east/south arc ratio 0.74 < declared 0.75. Measured causes: (1) the extended-bays march caps the east section at az 85 vs south at az 197 (asymmetric by design of the contour families); (2) row-18 east terminates 46.9 ft from Petoskey St vs south 60.3 ft from E Mitchell St; (3) the contour-walk test finds ~342 ft of additional on-contour east arc across rows 6-18 before the seat-facing splay gate (45° off the stage) stops every row — the closed basin wraps north past the east cap, so further seats would face across the bowl, not at the stage. The east flank is bounded by audience-facing geometry (and ultimately the street corner), not arbitrarily trimmed.

N1 (east re-march) and N2 (+row 19, per-seat formal) remain live analysis-tier options; adopting either requires re-emission and Scenario E re-validation before any seat is claimed (canon Rules 3/5). N3 (south trim) is rejected: symmetry is not a site constraint and it deletes validated seats.
