# Open work

Psygore's slave 1.3, reconstructed (both slaves byte for byte with `BUILD=original`). The
AlienBreed3D variant boots on the a1200-030 into the first level with both the Aminet
8-channel ($c4dc, AGA drawer) and the CD32 ($fd78) version; in the first, mouse control
(M) turns and moves. Enhanced resolution (CUSTOM5, $c4dc only) builds the 1x1 palette and the
pen tables before the menu and shows the game on 8-plane screens through a c2p; the image
is still the original renderer's 96x80, scaled 2x2 or 3x3.

## Goal

Enhanced resolution (CUSTOM5): both views at 1x1 pixels on bitplane screens fed by a
Kalms c2p, as fast as we can make them. The design, the steps and the open decisions are
in [resolution-plan.md](resolution-plan.md); how the original draws is in
[internals](internals.md#display).

## Next

1. Plan step 5: the 1x1 renderer, writer by writer, walls and floors first. Steps 0-4 are
   done: the baseline and the skeleton's cost are in [performance](performance.md), the
   display inventory, the palette's tables and the new display in
   [internals](internals.md#display-inventory), the palette decision in the
   [plan](resolution-plan.md#colour).
2. A heavy scene for the baseline (many aliens and objects), when one is found.

## Before a first release

- A dated `$VER` string in both slaves and a ReadMe entry above Psygore's.
- The release ships `src/AlienBreed3D.s` in place of the encrypted
  `src/AlienBreed3DHD_src.lzx` (decided 26.11.2026; `release.json` `source`). The first
  `make dist` is its first test.
- Boot both variants on every machine in `SETUPS` (only AlienBreed3D on the a1200-030 so
  far).
