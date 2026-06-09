# Civic-Bowl Core + Upper Civic Landscape

Design partition of the street-bounded contour envelope
(`design_extended_bays/seating_bays.geojson`, natural grade, face 312).
**The envelope is the maximum site reach; this partition is the seating plan.**

## Formal-bowl stop (last defensible sightline band)
- **Formal seating stops at civic row 19** (elev ≈ 635.08 ft).
- Stop rule: last contiguous row whose **per-seat 10th-pct C ≥ 90 mm** (flank-aware,
  authoritative — `perseat_bands.csv`). Centreline C alone stopped at row 18; the per-seat
  ray-cast confirms row 18 (97 mm) **and** clears row 19 (93 mm, 95% of seats pass).
- **Row 20 is the true break: 59 mm / 54% pass → landscape** (no 60–90 soft band survives).
- Rows 20–25 fall to 30–60 / <30 mm AND lose their east/south sections to the streets
  (clipped) → **landscape, not seats.**

## Capacity by quality band (NOT a single raw number)
| band | generous 22-in | compact 18-in | weight |
|---|---|---|---|
| **Formal core (per-seat ≥90 mm, forecourt 1–4 + civic 6–19)** | 1,566 | 1,917 | 1.0 |
| **C_formal (quality-banded)** | **1,566** | **1,917** | — |
| Upper rows 20–25 reallocated to landscape (NOT counted as seats) | 329 | 403 | 0 |

**Public-facing:** *"~1,570 high-quality formal seats (generous 22-in spacing; ~1,920 at
compact 18-in), plus lawn/terrace overflow and bay overlooks along the rim."* Do **not**
advertise the full envelope (1,895 gen / 2,320 compact) as formal seating.

## Upper civic landscape program (rows 20–25)
The weakest-stage rows are the **best bay-view** rows and sit **at street grade** — so the
upper contours become public landscape, not forced seats:
- **Lawn / picnic terraces** — the broad upper contour benches (informal seating, blankets,
  standing overflow during large events).
- **Bay overlooks** — schematic points at the top of each section (face NW / 312 toward the
  bay); best panorama in the park, reached at grade.
- **Rim circulation** — perimeter path along the top tying the three street frontages.
- **ADA-accessible rim connections** — at-grade entries from Petoskey (E), E Mitchell (S),
  and E Lake (N, bay/stage side → promenade). Because the rim is ~at street grade, the
  **upper rim is the natural accessible viewing zone**; switchback ramps descend from the
  rim/promenade to mid-bowl accessible positions (row 5).

## Public-space hierarchy
1. Stage + forecourt (event focus)
2. Formal raked bowl (rows ≤19) — every seat reliable view geometry
3. Soft upper-edge seating (row 20, optional)
4. Lawn / picnic terraces + bay overlooks (rows 21+)
5. Street-edge rim circulation + ADA connections (Petoskey / E Lake / E Mitchell)

## Caveats (observed)
- Bands use **centreline** C; per-seat 10th-pct C (flank-aware) is stricter — formal counts
  are an upper bound. No core rows exceed the oblique flank threshold.
- Overlook & ADA features are **schematic** (planning grade); alignment/slope require survey.
- Geometry inherits the extended_bays gates (tread z-residual ≤0.25 ft, zero forced fill,
  no retaining wall) — feasibility carried from that sweep, not re-run here.
