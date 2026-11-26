# Open work

Psygore's slave 1.3, reconstructed (both slaves byte for byte with `BUILD=original`). The
AlienBreed3D variant boots on the a1200-030 into the first level with both the Aminet
8-channel ($c4dc, AGA drawer) and the CD32 ($fd78) version; in the first, mouse control
(M) turns and moves. Enhanced resolution (CUSTOM5, $c4dc only) builds the 1x1 palette and the
pen tables before the menu and shows the game on 8-plane screens through a c2p. The small
view is drawn at 192x160 by the game's own writers; full screen is still 96x80, scaled 3x3.

## Goal

Enhanced resolution (CUSTOM5): both views at 1x1 pixels on bitplane screens fed by a
Kalms c2p, as fast as we can make them. The design, the steps and the open decisions are
in [resolution-plan.md](resolution-plan.md); how the original draws is in
[internals](internals.md#display).

## Next

1. Plan step 5's play-test: level 2 at 192x160 (walk, fight, pause, a death, its end);
   level 1 has been played to its first fights. Steps 0-4 are done, and step 5's writers
   ([internals](internals.md#the-1x1-renderer)); the costs are in
   [performance](performance.md).
2. Plan step 6: full screen at 288x240, the same patches at the second size.
3. A heavy scene for the baseline (many aliens and objects), when one is found.
4. `tools/display.sh` once failed on level 1's end with CUSTOM5=0: the original's frame
   showed its option text (SFX QUALITY, FLOOR DETAIL) and the run with the option on did
   not. Same slave bytes passed before and after. Find what reaches the original's keys
   there, or make `ab3d.py end` wait it out.

## Before a first release

- A dated `$VER` string in both slaves and a ReadMe entry above Psygore's.
- The release ships `src/AlienBreed3D.s` in place of the encrypted
  `src/AlienBreed3DHD_src.lzx` (decided 26.11.2026; `release.json` `source`). The first
  `make dist` is its first test.
- Boot both variants on every machine in `SETUPS` (only AlienBreed3D on the a1200-030 so
  far).
