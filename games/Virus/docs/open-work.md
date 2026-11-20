# Open work

Set up from John Selck's V1.0 slave; no improvement work yet. The demo benchmark has a
baseline on the a1200-030 ([internals](internals.md#measurements)): 23.4 fps, with 31% of
the time spent waiting for the blitter clear of the back buffer. The reconstruction rebuilds the
shipped slave byte for byte. It boots to the game's attract mode on the a500+ and the a1200,
and F10 quits with `OK`.

## Before a first release

- A dated `$VER` string and a version (`2.0b`), and the ReadMe's entry for it above the
  original text ([releasing](../../../docs/releasing.md)).
- Play-test on every machine in `SETUPS`, including saving a highscore.

## Candidates

Each needs an A/B on the demo benchmark (same machine, same window) before any claim. The
analysis behind them, against the repository's direction for 68020+ with fast memory (CPU
only, everything not DMA in fast memory, every cache on), is in
[internals](internals.md#what-must-be-in-chip-memory) and its measurements:

1. **Game time first.** The simulation steps once per frame, so every speed-up so far would
   make the game faster, not smoother (twice as fast on the 68030 already). Split simulation
   from rendering and run it at a fixed rate (AmigaXDev's
   `playbooks/fixed-time-simulation.md`) before or with any rendering work. The main loop
   calls are not yet sorted into simulation and drawing (the particles both move and draw).
2. **Code and CPU-only data in fast memory.** 97.7% of the 68030's time is chip access.
   Instruction fetches are 43% of its chip reads (the 256-byte cache does not hold this
   code), data in work memory and the image most of the rest; the display writes the game
   must do are 3.3% of its slots. What holds it back: a raw image with no relocations (518
   absolute longs in the demo's code alone, code pointers in data tables, PC-relative data
   inside the code), so a relocation needs a full disassembly, or a narrower move of the hot
   routines with their PC-relative data. The slave also needs fast memory to put it in:
   today it declares only 544 KB of chip (a v4 header without `ws_ExpMem`).
3. **CPU only.** The blitter does one job, the screen clear, and it is what the CPU waits
   for (31%): 11.9 ms from the VBL after each swap, at the blitter's full D-only rate
   (`BLTPRI` is on; the CPU's polling does not slow it). A CPU clear could only start at the
   same VBL. The bigger change is the playbook's draw in fast memory, copy to chip: drawing
   into a fast staging buffer needs no wait at all, and the copy goes to the back buffer,
   which has been off screen since the previous swap's VBL. That needs the renderer and
   span writers in fast memory (item 2). Keep the blitter clear on the 68000 and on
   machines without fast memory.
4. **Caches.** Real boards never data-cache chip memory, so with everything in chip WHDLoad's
   `DCACHE` can do nothing (FS-UAE without the MMU model agrees). The data cache only pays
   once item 2 moves data to fast memory. Nothing blocks it then: no self-modifying code
   was seen, and no DMA touches CPU-only data. The instruction cache is already on (the
   slave's `resload_SetCACR` and `CACHE`).
- Run on a 512 KB chip A500: find the render writes past `$80000` (a write watchpoint
  above `$80000`) and clip them, so `ws_BaseMemSize` can be `$80000`. The unused `_clamp`
  shows where the original author started.
- A newer slave version (WHDLoad 17 header, `ws_ExpMem` for item 2, `slv_config` for
  options). The game waits for the blitter only through the clear flag `$606ac`.
