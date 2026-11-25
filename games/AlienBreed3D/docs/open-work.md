# Open work

Psygore's slave 1.3, reconstructed (both slaves byte for byte); no improvement yet. The
AlienBreed3D variant boots on the a1200-030 to the main menu and into the first level,
where mouse control (M) turns and moves.

## Goal

Replace the game's 2x2-pixel 3D renderer with a 1x1-pixel one, as fast as possible,
behind an "Enhanced resolution" CUSTOM option (CUSTOM1-4 are taken by the original's
options, so CUSTOM5), with the original renderer when it is off.

## Before a first release

- A dated `$VER` string in both slaves and a ReadMe entry above Psygore's.
- The release ships `src/AlienBreed3D.s` in place of the encrypted
  `src/AlienBreed3DHD_src.lzx` (decided 26.11.2026; `release.json` `source`). The first
  `make dist` is its first test.
- Boot both variants on every machine in `SETUPS` (only AlienBreed3D on the a1200-030 so
  far).

## Next

1. Find the renderer: where the 2x2 view is drawn (chunky buffer, chunky-to-planar, the
   copper's line doubling), its size and its cost, measured on the a1200-030
   (AmigaXDev `reference/measurement-method.md`).
2. Name the remaining `Lxxxx` labels as the code is understood.
