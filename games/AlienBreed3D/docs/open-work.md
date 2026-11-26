# Open work

Psygore's slave 1.3, reconstructed (both slaves byte for byte with `BUILD=original`). The
AlienBreed3D variant boots on the a1200-030 into the first level with both the Aminet
8-channel ($c4dc, AGA drawer) and the CD32 ($fd78) version; in the first, mouse control
(M) turns and moves. Enhanced resolution (CUSTOM5, $c4dc only) builds the 1x1 palette and the
pen tables before the menu and shows the game on 8-plane screens through a c2p. Both views
are drawn at 1x1 by the game's own writers: the small view at 192x160, full screen at
288x240.

## Goal

Enhanced resolution (CUSTOM5): both views at 1x1 pixels on bitplane screens fed by a
Kalms c2p, as fast as we can make them. The design, the steps and the open decisions are
in [resolution-plan.md](resolution-plan.md); how the original draws is in
[internals](internals.md#display).

## Next

1. Play-test both 1x1 views by hand: level 1 (full screen not yet played), level 2 (walk,
   fight, pause, a death, its end). Steps 0-6 are done
   ([internals](internals.md#the-1x1-renderer)); the costs are in
   [performance](performance.md).
2. The holes larger than the original's ([plan](resolution-plan.md) step 6): a step's near
   edge in full screen, a strip at the small view's right edge once.
3. A heavy scene for the baseline (many aliens and objects), when one is found.
4. `tools/display.sh` once failed on level 1's end with CUSTOM5=0: the original's frame
   was still the pause screen (its option text, SFX QUALITY, FLOOR DETAIL), so the second
   P had not ended the pause. Same slave bytes passed before and after. `ab3d.py key 19`
   should wait until the pause is over (or check it) before the script goes on.
5. Plan step 7: speed.

## Releases

2.0b (26.11.2026), `make dist`: both slaves with Enhanced resolution and `$VER`; the
ReadMe's entry above Psygore's; the five game icons add CUSTOM5=1 (`release.json`
`tooltypes`); the source drawer holds `src/` in place of the encrypted
`AlienBreed3DHD_src.lzx`. Both variants boot with CUSTOM5=1 into level 1 in both views on
the a1200-fast, a1200-030 and a1200-040. Not published (`make release PUBLISH=1`). The next
version: the `$VER` and `_info` strings in `src/AlienBreed3D.s` and a new ReadMe entry.
