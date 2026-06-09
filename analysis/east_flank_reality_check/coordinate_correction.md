# Coordinate and Street-Name Correction
## Petoskey Pit — East Flank Reality Check

**Compiled 2026-06-06. Planning-grade. Corrective reference only.**

---

## Authoritative orientation

| Direction | Feature |
|-----------|---------|
| North | E Lake Street (runs east–west) |
| South | E Mitchell Street (runs east–west) |
| East | Petoskey Street (runs north–south along the east side of the block) |
| West / open | Bayfront Park / Little Traverse Bay side |

The pit depression is bounded roughly:
- north: toward E Lake Street
- south: toward E Mitchell Street
- east: toward Petoskey Street
- west: open to Bayfront Park / the bay

**The east flank of the pit rises west-to-east toward Petoskey Street and the eastern property edge.** A west-to-east transect does not move toward Lake Street or Mitchell Street. Those are parallel east–west streets, not east destinations.

---

## Required terminology

| Term | Use for |
|------|---------|
| **Petoskey Street flank** | The east-facing rim / upper eastern plateau |
| **East/Petoskey edge** | The eastern property edge near Petoskey Street |
| **Upper eastern plateau** | The relatively flat upper zone on the east side of the pit |
| **Lake Street side** | Only the north edge / north approach |
| **Mitchell Street side** | Only the south edge / south approach |
| **Bayfront Park side** or **west side** | The open, bay-facing western flank |
| **S/SE bowl wall** | The south and southeast seating landform |
| **E/SE bowl wall** | The east and southeast seating landform |

---

## Invalid phrasings to remove

The following phrases are **directional errors** found or plausible in project documents. They must be removed or corrected wherever they appear.

| Invalid phrasing | Why it is wrong | Replacement |
|-----------------|----------------|-------------|
| "east-slope rises toward Lake/Mitchell" | Lake and Mitchell are east–west streets; moving east does not approach either | "east flank rises toward Petoskey Street" |
| "toward Lake/E Mitchell" (to mean eastward) | Same error | "toward Petoskey Street" or "eastward toward the eastern property edge" |
| "Lake/Mitchell" as the east boundary | They are north and south boundaries respectively | "Petoskey Street" (east boundary) |
| east flank described as "north slope" | The east flank faces west, slopes up to the east | correct as "east flank / Petoskey Street rim" |
| east flank described as "south slope" | Same error | correct as "east flank" |

---

## File-by-file audit for invalid directional language

The following files were searched for the phrases `Lake/Mitchell`, `Lake/E Mitchell`, and east-direction conflations.

### `executive_summary.md` (root)
- **Line 18:** "garden ring on the gentle east and open bayward flanks" — *directional description is correct (east = east), no invalid street conflation found*; retains the characterization "gentle east flank" which **may be an over-strong claim** (see `assumption_audit.md`) but is not a coordinate error.

### `design_open_low/README.md`
- No Lake/Mitchell directional conflation found.

### `design_corner_bays/README.md`
- No coordinate errors found.

### `DATA_GAPS.md`
- **Line 123:** "east-slope gentleness" — *not a coordinate error; describes slope character* but should be downgraded to "east-flank slope — unverified character" pending terrain forensics.

### `stage4/README.md`
- No coordinate errors found; uses `az 150–180` for the S–SSE arc correctly.

### Memory / `scripts/design_corner_bays.py`
- Uses "east flank az<118 | bend 118–152 | south flank az>152" — correct azimuth usage.

### `petoskey_pit_lidar_analysis_archive/petoskey_pit_expanded_section_summary.csv`
- Column labels `east_west positive` and `north_south` are correct spatial directions.

**Conclusion:** No explicit `Lake/Mitchell` conflation phrase was found in existing files. The instruction to avoid it is a prospective guard against introducing the error in *new* documents. Going forward, all east-direction references must use "Petoskey Street" or "eastern property edge," never "Lake Street" or "Mitchell Street."

---

## Summary rule (to paste into any new design document)

> **Site orientation memo:**
> E Lake Street is north. E Mitchell Street is south. Petoskey Street is east.
> The east flank rises from the bowl floor **west-to-east toward Petoskey Street**.
> "Toward Petoskey Street" = eastward. "Toward Lake Street" = northward. "Toward Mitchell Street" = southward. "Toward Bayfront Park" = westward.
> Do not conflate these.
