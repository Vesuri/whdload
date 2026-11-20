# Open work

2.0b (20.11.2026) on John Selck's reconstructed V1.0 slave. Enhanced framerate (CUSTOM1)
gives the game fixed-rate game time, a tick every 2, 3 or 4 fields (CUSTOM2), with drawing
left out while behind; off, the game runs as the original
([internals](internals.md#game-time)). The demo benchmark has a baseline on the a1200-030
([internals](internals.md#measurements)): 23.4 fps, with 31% of the time spent waiting for
the blitter clear of the back buffer. It boots to the game's attract mode on the a500+ and
the a1200, and F10 quits with `OK`.

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
- Play-test on every machine in `SETUPS`, including saving a highscore.

## Candidates

Each needs an A/B on the demo benchmark (same machine, same window) before any claim. The
analysis behind them, against the repository's direction for 68020+ with fast memory (CPU
only, everything not DMA in fast memory, every cache on), is in
[internals](internals.md#what-must-be-in-chip-memory) and its measurements:

1. **Code and CPU-only data in fast memory.** 97.7% of the 68030's time is chip access.
   Instruction fetches are 43% of its chip reads (the 256-byte cache does not hold this
   code), data in work memory and the image most of the rest; the display writes the game
   must do are 3.3% of its slots. What holds it back: a raw image with no relocations (518
   absolute longs in the demo's code alone, code pointers in data tables, PC-relative data
   inside the code), so a relocation needs a full disassembly, or a narrower move of the hot
   routines with their PC-relative data. The slave also needs fast memory to put it in:
   today it declares only 544 KB of chip (no `ws_ExpMem` yet).
2. **CPU only.** The blitter does one job, the screen clear, and it is what the CPU waits
   for (31%): 11.9 ms from the VBL after each swap, at the blitter's full D-only rate
   (`BLTPRI` is on; the CPU's polling does not slow it). A CPU clear could only start at the
   same VBL. The bigger change is the playbook's draw in fast memory, copy to chip: drawing
   into a fast staging buffer needs no wait at all, and the copy goes to the back buffer,
   which has been off screen since the previous swap's VBL. That needs the renderer and
   span writers in fast memory (item 1). Keep the blitter clear on the 68000 and on
   machines without fast memory.
3. **Caches.** Real boards never data-cache chip memory, so with everything in chip WHDLoad's
   `DCACHE` can do nothing (FS-UAE without the MMU model agrees). The data cache only pays
   once item 1 moves data to fast memory. Nothing else blocks it then: no DMA touches
   CPU-only data, and the slave flushes the cache after the one self-modifying routine
   (since 2.0b). The instruction cache is already on (`resload_SetCACR` and `CACHE`).
- The game speed still waits for whole fields; drawing between ticks (interpolation) or
  a tick shorter than the drawing would need the renderer faster first (items 1 and 2).
- Run on a 512 KB chip A500: find the render writes past `$80000` (a write watchpoint
  above `$80000`) and clip them, so `ws_BaseMemSize` can be `$80000`. The unused `_clamp`
  shows where the original author started.
- `ws_ExpMem` for item 1 (the header is v17 since 2.0b). The game waits for the blitter only through the clear flag `$606ac`.
