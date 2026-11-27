# Open work

Psygore's slave 1.3, reconstructed (both slaves byte for byte with `BUILD=original`). The
AlienBreed3D variant boots on the a1200-030 into the first level with both the Aminet
8-channel ($c4dc, AGA drawer) and the CD32 ($fd78) version; in the first, mouse control
(M) turns and moves. Enhanced resolution (CUSTOM5, both versions) builds the 1x1 palette and the
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
2. A heavy scene for the baseline: in level 1, through the first door, turn left or right,
   and shoot a barrel close by; a near explosion is the most taxing (the user's). Not yet
   scripted.
3. Plan step 8 is done ([resolution-plan](resolution-plan.md#steps)): the machines, both
   variants, the two-player link and CUSTOM5 off are checked, and the option applies on
   every CPU with the ReadMe's suggestions (27.11.2026). Step 9 is done for the CD32
   version (the floppy one needs the original disks); next step 10, the release. Open is
   whether the installer should ask for the option.

## Releases

2.0b (27.11.2026), `make dist`: both slaves with Enhanced resolution and `$VER`; the
ReadMe's entry above Psygore's; the five game icons add CUSTOM5=1 (`release.json`
`tooltypes`); the source drawer holds `src/` in place of the encrypted
`AlienBreed3DHD_src.lzx`. Both variants boot with CUSTOM5=1 into level 1 in both views on
the a1200-fast, a1200-030 and a1200-040. Not published (`make release PUBLISH=1`). The next
version: the `$VER` and `_info` strings in `src/AlienBreed3D.s` and a new ReadMe entry.
