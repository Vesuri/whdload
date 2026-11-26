# Open work

Psygore's slave 1.3, reconstructed (both slaves byte for byte); no improvement yet. The
AlienBreed3D variant boots on the a1200-030 into the first level with both the Aminet
8-channel ($c4dc, AGA drawer) and the CD32 ($fd78) version; in the first, mouse control
(M) turns and moves.

## Goal

Enhanced resolution (CUSTOM5): both views at 1x1 pixels on bitplane screens fed by a
Kalms c2p, as fast as we can make them. The design, the steps and the open decisions are
in [resolution-plan.md](resolution-plan.md); how the original draws is in
[internals](internals.md#display).

## Next

1. Plan step 2: the display inventory: what else writes into the view, past the renderer
   routines in [internals](internals.md#renderer-routines). Steps 0 and 1 are done; the
   baseline is in [performance](performance.md).
2. A heavy scene for the baseline (many aliens and objects), when one is found.

## Before a first release

- A dated `$VER` string in both slaves and a ReadMe entry above Psygore's.
- The release ships `src/AlienBreed3D.s` in place of the encrypted
  `src/AlienBreed3DHD_src.lzx` (decided 26.11.2026; `release.json` `source`). The first
  `make dist` is its first test.
- Boot both variants on every machine in `SETUPS` (only AlienBreed3D on the a1200-030 so
  far).
