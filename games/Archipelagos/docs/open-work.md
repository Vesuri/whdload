# Open work

Set up from StingRay's v1.2 slave. Both variants boot to the title and into archipelago
1, SPS 627 on the a500 and SPS 628 (NTSC) on the a1200, and F10 quits cleanly on both. The
frame loop, the game's clocks and the rendering cost are measured
([internals.md](internals.md#the-frame)). Game time is decoupled from the frame rate
(step 1 below); the rest of the 50 fps plan is still to do.

## Release

2.0b (18.11.2026): StingRay's v1.2 code, which the whdload.de install package lacked, with
`$VER` and the info text in the slave and the ReadMe entry above StingRay's, and game time
decoupled from the frame rate. Still to do: play-test both versions on every machine in
`SETUPS`, including saving and loading a game and an archipelago with blood eggs (20 or
later). `tools/play.py` plays archipelago 1 to its end.

## 50 fps on the a1200-030

The soft target is 50 fps in play on the a1200-030, which now draws 8.2 fps on archipelago
1. A frame there takes 124 ms: 90 ms of CPU work, 12 ms waiting for the blitter and 27 ms
waiting for fields. The causes, largest first:

- **Caches off.** WHDLoad's default marks BaseMem uncacheable, and without the MMU in use
  (the 68030's default) that turns both caches off. The slave sets no cache flags, so the
  whole game runs uncached from Chip RAM. WHDLoad's `CACHE` option alone took the
  emulated 030 from 8.0 to 15.0 fps.
- **Nothing in fast memory.** No ExpMem. Code, stack, tables, the span list and the map all
  sit in Chip RAM. With the instruction cache on, 80% of the CPU's chip accesses outside the
  wait loops go to things DMA never reads: about 31000 a frame, at least 8.7 ms.
- **Two field waits a frame.** One before drawing, which double buffering needs, and one
  before the swap, which it does not. That caps the game at 25 fps and adds up to a field
  to every frame.
- **Waiting for the blitter.** 10.6-11.7 ms a frame, 7 ms of it the sky fill. The CPU waits
  before each of its five plane blits and does nothing meanwhile.
- **The renderer's CPU work.** With the instruction cache: span drawer 9.5 ms, fill routines
  7.6, near rows 3.9, row set-up 3.6, far-row loop 2.6.

What does not matter: the world update (0.03%), interrupts (1-2%) and the swap (0.1%).

The decoupling came first: without it every later step would also speed up moves, the
spread and the animations. Measure every step with `tools/archipelagos.py frames 250 4` on
the a1200-030, a1200 and a500, with `tools/bench.py` (030 without the MMU model) for the
breakdown, and with `tools/timecheck.py` for game time. The a500 must neither slow down
nor change behaviour.

1. **Decouple game time.** Done (`src/timing.s`; [internals.md](internals.md#decoupled-srctimings-20b)).
   Decided 18.11.2026: every frame-counted step takes at least 6 fields (the game's world
   tick, 8.33 Hz), so today's a1200-030 pace holds on faster machines. The world tick stays
   as the game has it unless the a500 gets faster too. Checked with `tools/timecheck.py`
   on the a500, the US a1200 and the cached 030: moves, the renderer's steps and both
   effects (a stone's collapse, the Obelisk's ramps), and an image scan finds nothing
   else at the frame rate. Not checked in play: the blood spread (`$C99E`), which needs
   archipelago 20 or later; it runs in the renderer's steps, which are checked.
2. **Instruction cache.** First fix the one piece of self-modifying code: point the four
   writes of the level 3 handler's `jsr` target (`$E490`, `$10BB4`, `$1187E`, `$118B0`) at
   a slave variable, and make the `jsr` (`$CE92`) jump through it. Then call
   `resload_SetCACR` with the instruction cache on for BaseMem. Leave its data cache off:
   on a 68040/060 with the MMU it would make the screens data-cacheable.
   - Run `tools/smc.py` on runs through the title, the archipelago screen, the map, saving
     and loading, a level's end and a death.
   - Expected from the `CACHE` measurement: 15 fps on the 030. The 68000 is unaffected.
3. **One field wait a frame.** Drop the wait before the swap (`$1185C`). The renderer's wait
   (`$11AE6`) keeps the buffers safe, as it already does in the move routine. Guard the swap
   (`$12306`) so it never rewrites the bitplane pointers while the copper is loading them at
   the top of the frame: wait out those lines, or keep two copper lists and switch
   `COP1LC`. A frame then takes its work rounded up to whole fields, not that plus up to a
   field. That is a projection from the loop's structure; measure it. This removes the
   25 fps cap.
4. **Fast memory for what DMA never reads** (ExpMem; cached).
   - The stack, which is the slave's `$800`.
   - The renderer's data: the span list (offset `$13C26`), its tables (`$1254A` and the row
     tables), the variables its loops read pc-relative, and the 64 KB map. Every
     `lea $78000` must be patched for the map; count them first.
   - The renderer's code, last (its pc-relative data references have to become absolute),
     preferably as part of step 6.
   - Keep in chip everything DMA reads: the screens, the copper lists, the sky lists, the
     samples, sprite and blitter source data.
   - On a 68030 without the MMU the caches are global. Chip RAM is never data-cached on
     real hardware (the bus inhibits it), but FS-UAE models that only without its MMU
     model. So measure data-cache effects with `EXTRA_ARGS=--uae_mmu_model=0`, and
     confirm on hardware.
   - Gate: re-measure `tools/cpuchip.py` and the frame.
5. **Overlap the blitter with the CPU.** The sky (lines 20-112) and the ground (113-179)
   do not overlap. Start the sky's plane blits before draw view and start each next one
   when the blitter is idle, polled once a ground row or from the blitter interrupt. The
   CPU then draws the ground while the blitter fills the sky. The objects wait only for
   what is left. Also check which sky planes need clearing at all: only object pixels dirty
   them. Gate: the blitter-wait line of the bench report.
6. **The renderer's CPU work**, re-profiled after steps 2-5.
   - Inline the per-word `jsr 12(a1)` fills as long-word writes: the view is long-aligned,
     and AGA's chip bus takes a long in one access.
   - Keep the far-row loop's two direction constants in registers, not pc-relative chip
     reads.
   - Fold the span drawer's lookups.
   - A 68020+ path in the slave is allowed. Keep the 68000 path as it is.
7. **Triple buffering**, only if frames still end just after a field. It needs another
   40000 bytes of Chip RAM, so map what BaseMem uses between `$16314` and `$5C780` first.

Whether 50 fps is reachable is not shown yet. One field is 20 ms. With the instruction
cache, CPU work plus blitter waits are about 40 ms a frame, so steps 4-6 have to halve
that. Decide after step 4's measurement.

## Other candidates

- SPS 628 (NTSC): the same analysis on its offsets, once SPS 627's patches work.
