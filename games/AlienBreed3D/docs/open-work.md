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
2. Speed on the 68030: the dark room fight (`ab3d.py` SCRIPTS `door`, `turn720`;
   [performance](performance.md#where-the-time-can-still-go)), largest first. Each
   step's estimate is a count of the clocks removed, not a measurement.
   1. **The measure** (done): `tools/frametime.py --loops A.json B.json` prints each
      capture's pixels a frame, clocks a pixel and ms a frame for each pixel loop (its
      `LOOPS`), and the c2p's ms and clocks a Chip store. Compare builds on those, since
      the frame totals drift between runs. A loop moved into the slave gets a slave part
      in `LOOPS` beside the game's.
   2. **Gouraud floor spans** ($20fd0-$21016, 28.3 clocks a pixel): our own loop through
      `PL_P`, as the walls'. Eight pixels a pass at displacements, entered by a jump.
      Keep the game's stepping, but as two unrolled tracks (the next pixel steps by d6
      after a carry, else by d2), with one branch a pixel in place of the `dbcs`/`dbcc`
      pair (6.9 clocks). Mask with a register in place of `andi.w #$3f3f` (4.1 clocks).
      Estimate: about 22 clocks a pixel, 3 ms a frame. The flat spans ($20f4c) and
      the water's (patched at $2110a and $2112e) have the same loop.
   3. **Wall strips** (21.3 clocks a pixel, 360 strips of about 140 pixels a frame): a
      variant without the `and.w` wrap for strips that do not wrap, and the two `mulu.w`
      of each strip's entry from a table (0.35 ms). Then unpack the walls to a byte a
      texel at each level's load (about 264 KB more ExpMem for the 176 KB of packed
      walls), with one loop for all three packings and no `lsr`/`andi` a pixel.
      Estimate: 17-18 clocks a pixel, 3-5 ms a frame.
   4. **The object search** (3.1 ms): put the objects in zone lists once a frame, and
      clear only the sort list's used entries. Estimate: 2-2.5 ms. The drawing order must
      stay the same (compare frames with `ab3d.py chunky`).
   5. **Bitmap columns** (25.9 clocks a pixel visited): our own loops, eight rows a pass
      at displacements, no `adda` or `dbf` a pixel. Estimate: a quarter less, 2 ms a frame
      here and about 5 ms in an explosion's frames.
   6. **The c2p at FMODE 3 below the 68040:** Kalms' loop with a row counter that adds 4
      to the destination every 9 longs of a plane, so that one call writes 36 of each
      40-byte row. Estimate: 1.3 ms, from the measured 8% cheaper Chip stores.
      Anything more needs fewer bytes to Chip, such as 7 planes and 128 colours, which
      changes the picture.
   7. **The set-up code:** the game's wall columns (8.8 ms) and floor spans (7.8 ms), after
      steps 2 and 3. Not yet looked into.
   8. **Small:** skip the game's SuperState/UserState calls (our exec's are RTS) with
      `PL_S`: 0.15 ms, and no Chip read of ExecBase.

   Steps 2-6 together: about 12 ms of the 96-100 ms a frame, 10.0 to about 11.5 fps.
   A barrel shot point-blank is not yet scripted.
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
