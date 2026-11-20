# Open work

2.0b (20.11.2026) on John Selck's reconstructed V1.0 slave. Enhanced framerate (CUSTOM1)
gives the game fixed-rate game time, a tick every 2, 3 or 4 fields (CUSTOM2), with drawing
left out while behind; off, the game runs as the original
([internals](internals.md#game-time)). The code area runs from ExpMem when there is some
([internals](internals.md#code-in-fast-memory)): the demo went from 23.4 to 32.8 fps on the
a1200-030 (36.0 with the stack moved too) and from 22.2 to 25.4 on the a1200-fast, and the busy-wait for the blitter clear
of the back buffer is now 43.9% of the time ([internals](internals.md#measurements)). It
boots to the game's attract mode on the a500+ and the a1200, and F10 quits with `OK`.

## Game speed

Which rate the game was meant for is not known: 25, 16.7 or 12.5 Hz (CUSTOM2 0, 1, 2;
0 is the default only because it comes first in the list). The originals ran the demo
at 12.0 fps on the a500+ and 22 to 23 fps on the a1200 and the a1200-030. The A500 holds
12.5 Hz, 97% of 16.7 Hz and 91% of 25 Hz. Choose by play; reordering the `C2` list in
`_config` and `_speed`'s mapping in `_start` changes the default.

## Before a first release

- Play-test Enhanced framerate at each speed, including pause, a wave's end, game over
  and the highscore entry (only the demo, the attract screen, pause and a wave's end are
  tested so far).
- Play-test on every machine in `SETUPS`, including saving a highscore (the moved table
  loads; saving it was not reached by the scripted play, whose firing kept the score
  negative).
- Decide whether the release keeps filling the chip copy of the code with `ILLEGAL` (a
  reference `src/reloc.i` missed then stops at once rather than misbehaving later).

## Candidates

Each needs an A/B on the demo benchmark (same machine, same window) before any claim. The
analysis behind them, against the repository's direction for 68020+ with fast memory (CPU
only, everything not DMA in fast memory, every cache on), is in
[internals](internals.md#what-must-be-in-chip-memory) and its measurements:

1. **CPU-only data in fast memory.** The code area and the stack are moved
   ([internals](internals.md#code-in-fast-memory)). The CPU's chip slots are now
   (tools/chipaccess.py, 10 fields from demo field 300, a1200-030) the display buffers 51%
   (the drawing's reads and writes), work memory 38% and the image's data below `$57000`
   10%. By address: the globals `$1000-$10ff` 10.5%, the renderer's scratch `$1100-$15ff`
   about 6%, the particles around `$a2a6-$abff` about 7%, the depth buckets 7.4%, a table at
   `$4d900` 4.5%; the landscape maps 1.1%. The same method works by address range, with
   what makes it harder than the code area:
   - Data holds work-memory pointers: the object models (`$4b548` on, read by
     `movea.l (a5)+,a6`) point into the vertex scratch at `$1104-$117c` (over 900 longs).
     Either parse the model format or leave `$1100-$11ff` in chip memory; the renderer's
     scratch `$1073-$1190` crosses `$1100`, so a split there needs every base-relative
     access checked (a trace's register snapshots give each access's address and PC).
   - Of the 60 long immediates with a work-memory value about ten are addresses
     (`#$1084`, `#$109c`, `#$9ea6`, `#$a2a6`, `#$bd04`, `#$1ca06`, `#$2ca06`, likely
     `cmpa.l #$1cc0,a2`); the rest are numbers (`#$ffff`, `#$10000`, `#$1f40`, 10000).
   - A missed data pointer does not stop the game the way the code's `ILLEGAL` fill
     does: it reads or writes the stale chip copy. Compare the state at tick 200
     (`tools/callwrites.py compare` must then read the moved ranges from ExpMem) and play.
   - The slave's own references (`$1022`, `$1084`, `$c9fc`/`$c9fe`) and the tools'
     (`$c9f4`) move with it.
2. **CPU only.** The blitter does one job, the screen clear, and it is what the CPU waits
   for (31%): 11.9 ms from the VBL after each swap, at the blitter's full D-only rate
   (`BLTPRI` is on; the CPU's polling does not slow it). A CPU clear could only start at the
   same VBL. The bigger change is the playbook's draw in fast memory, copy to chip: drawing
   into a fast staging buffer needs no wait at all, and the copy goes to the back buffer,
   which has been off screen since the previous swap's VBL. The renderer and span writers
   are in fast memory now. Keep the blitter clear on the 68000 and on machines without
   fast memory.
3. **Caches.** Real boards never data-cache chip memory, so WHDLoad's `DCACHE` can only
   help the data that moved with the code area (tables, palettes, variables) until item 1
   moves the rest. Nothing else blocks it then: no DMA touches
   CPU-only data, and the slave flushes the cache after the one self-modifying routine
   (since 2.0b). The instruction cache is already on (`resload_SetCACR` and `CACHE`).
- The game speed still waits for whole fields; drawing between ticks (interpolation) or
  a tick shorter than the drawing would need the renderer faster still (items 1 and 2).
- Run on a 512 KB chip A500: find the render writes past `$80000` (a write watchpoint
  above `$80000`) and clip them, so `ws_BaseMemSize` can be `$80000`. The unused `_clamp`
  shows where the original author started.
- The benchmark's trace reduction (`tools/bench.py`, `tools/report.py`) still assumes the
  code at `$57000`; `pace.py`, `aprof.py`, `chipaccess.py` and `gametime.py` find it
  (`tools/codebase.py`). The game waits for the blitter only through the clear flag `$606ac`.
