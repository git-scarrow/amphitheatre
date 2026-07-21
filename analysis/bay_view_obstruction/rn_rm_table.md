# r_n / r_m table — bay-band v2 (effective silhouette, far-shore top)

**Definitions (owner row-threshold model, resolved by attribution):**
- **r_n** = first row/section with any non-empty band under **S0** (bare-earth terrain lets water through). Rows below r_n are rim-blocked.
- **r_m** = first row/section **acceptable (>=80% clear)** under **S2** (water visible even through today's canopy). Rows r_n..r_m-1 are canopy-blocked; rows >= r_m are clear.
- S2 is given in BOTH leaf states. **Leaf-off (2015-05-02) is the measurement**; leaf-on is a labeled crown-opacity assumption. Summer is the operating season, so r_m(leaf-on) is the season-relevant threshold.

verdict: acceptable >=80% clear · marginal 40-79 · blocked <40

| section | r_n (S0 non-empty) | r_m (S2 leaf-off accept) | r_m (S2 leaf-on accept) | binding r_n..r_m |
|---|---|---|---|---|
| east | 8 | None | None | canopy |
| bend | 6 | None | None | canopy |
| south | 6 | None | None | canopy |

## Per-row detail (clear% and binding occluder by set)

| band | S0 clear/bind | S1 clear/bind | S2 leaf-off clear/bind | S2 leaf-on clear/bind |
|---|---|---|---|---|
| east r1 | 0.0/terrain | 0.0/terrain | 0.0/canopy | 0.0/canopy |
| east r2 | 0.0/terrain | 0.0/terrain | 0.0/canopy | 0.0/canopy |
| east r3 | 0.0/terrain | 0.0/terrain | 0.0/canopy | 0.0/canopy |
| east r4 | 0.0/terrain | 0.0/terrain | 0.0/canopy | 0.0/canopy |
| east r6 | 0.0/terrain | 0.0/terrain | 0.0/canopy | 0.0/canopy |
| east r7 | 0.0/terrain | 0.0/terrain | 0.0/canopy | 0.0/canopy |
| east r8 | 7.7/terrain | 7.7/terrain | 0.0/canopy | 0.0/canopy |
| east r11 | 92.3/terrain | 69.2/terrain | 0.0/canopy | 0.0/canopy |
| east r12 | 100.0/terrain | 69.2/terrain | 0.0/canopy | 0.0/canopy |
| east r13 | 100.0/terrain | 69.2/terrain | 0.0/canopy | 0.0/canopy |
| east r14 | 100.0/terrain | 53.8/terrain | 0.0/canopy | 0.0/canopy |
| east r15 | 100.0/terrain | 61.5/terrain | 0.0/canopy | 0.0/canopy |
| east r16 | 100.0/terrain | 61.5/terrain | 0.0/canopy | 0.0/canopy |
| east r17 | 100.0/terrain | 53.8/city | 0.0/canopy | 0.0/canopy |
| east r18 | 100.0/terrain | 53.8/city | 7.7/canopy | 7.7/canopy |
| bend r1 | 0.0/terrain | 0.0/terrain | 0.0/terrain | 0.0/canopy |
| bend r2 | 0.0/terrain | 0.0/terrain | 0.0/canopy | 0.0/canopy |
| bend r3 | 0.0/terrain | 0.0/terrain | 0.0/canopy | 0.0/canopy |
| bend r4 | 0.0/terrain | 0.0/terrain | 0.0/canopy | 0.0/canopy |
| bend r6 | 23.1/terrain | 23.1/terrain | 0.0/canopy | 0.0/canopy |
| bend r7 | 38.5/terrain | 38.5/terrain | 0.0/canopy | 0.0/canopy |
| bend r8 | 61.5/terrain | 61.5/terrain | 23.1/canopy | 23.1/canopy |
| bend r11 | 100.0/terrain | 100.0/terrain | 23.1/canopy | 15.4/canopy |
| bend r12 | 100.0/terrain | 100.0/terrain | 23.1/canopy | 15.4/canopy |
| bend r13 | 100.0/terrain | 100.0/terrain | 38.5/canopy | 30.8/canopy |
| bend r14 | 100.0/terrain | 100.0/terrain | 38.5/canopy | 30.8/canopy |
| bend r15 | 100.0/terrain | 100.0/terrain | 38.5/canopy | 30.8/canopy |
| bend r16 | 100.0/terrain | 100.0/terrain | 46.2/canopy | 38.5/canopy |
| bend r17 | 100.0/terrain | 100.0/terrain | 46.2/canopy | 38.5/canopy |
| bend r18 | 100.0/terrain | 100.0/terrain | 53.8/canopy | 46.2/canopy |
| south r1 | 0.0/terrain | 0.0/terrain | 0.0/canopy | 0.0/canopy |
| south r2 | 0.0/terrain | 0.0/terrain | 0.0/canopy | 0.0/canopy |
| south r3 | 0.0/terrain | 0.0/terrain | 0.0/canopy | 0.0/canopy |
| south r4 | 0.0/terrain | 0.0/terrain | 0.0/canopy | 0.0/canopy |
| south r6 | 76.9/terrain | 76.9/terrain | 7.7/canopy | 0.0/canopy |
| south r7 | 100.0/terrain | 100.0/terrain | 38.5/canopy | 23.1/canopy |
| south r8 | 100.0/terrain | 100.0/terrain | 38.5/canopy | 30.8/canopy |
| south r11 | 100.0/terrain | 100.0/terrain | 38.5/canopy | 30.8/canopy |
| south r12 | 100.0/terrain | 100.0/terrain | 38.5/canopy | 30.8/canopy |
| south r13 | 100.0/terrain | 100.0/terrain | 30.8/canopy | 30.8/canopy |
| south r14 | 100.0/terrain | 100.0/terrain | 38.5/canopy | 30.8/canopy |
| south r15 | 100.0/terrain | 100.0/terrain | 38.5/canopy | 30.8/canopy |
| south r16 | 100.0/terrain | 100.0/terrain | 38.5/canopy | 30.8/canopy |
| south r17 | 100.0/terrain | 100.0/terrain | 38.5/canopy | 30.8/canopy |
| south r18 | 100.0/terrain | 100.0/terrain | 38.5/canopy | 30.8/canopy |
