# Open work

Psygore's slave 1.3, reconstructed (both slaves byte for byte); no improvement yet. The
AlienBreed3D variant boots on the a1200-030 to the main menu and into the first level,
where mouse control (M) turns and moves.

## Goal

Enhanced resolution (CUSTOM5): both views at 1x1 pixels on bitplane screens fed by a
Kalms c2p, as fast as we can make them. The design, the steps and the open decisions are
in [resolution-plan.md](resolution-plan.md); how the original draws is in
[internals](internals.md#display).

## Next

1. Plan step 0: `tools/ab3d.py` (menu to level, full-screen toggle, frame counts, input
   scripts) and the renderer routines matched to game offsets.
2. Plan step 1: the original's baseline, both views, on a1200-030 and a1200-040.
3. Plan step 2: the display inventory.

## Before a first release

- A dated `$VER` string in both slaves and a ReadMe entry above Psygore's.
- The release ships `src/AlienBreed3D.s` in place of the encrypted
  `src/AlienBreed3DHD_src.lzx` (decided 26.11.2026; `release.json` `source`). The first
  `make dist` is its first test.
- Boot both variants on every machine in `SETUPS` (only AlienBreed3D on the a1200-030 so
  far).
