# Internals

## How it loads

A WHDLoad v4 direct slave (`ws_Flags` Disk and NoError, no Kickstart). It clears
`$1000-$3b7ff`, loads the whole disk image `Disk.1` (184320 bytes) to `$3b800`, so a
`Disk.1` offset is its address minus `$3b800`, loads the highscores, applies two patches,
turns the instruction cache on (`resload_SetCACR`) and jumps to the game's entry,
`Disk.1` offset `$286c8` (`$63ec8`).

## Memory

`ws_BaseMemSize` is `$88000` (544 KB). The ReadMe's reason: the render routines write past
the 512 KB border. The game itself uses fixed chip addresses up to at least `$78000`
(`$70000` and `$78000` stored at its entry), so no part moves to fast memory.

## The frame

Offsets are into `Disk.1` (address - `$3b800`); data addresses below `$3b800` are absolute.
Everything runs in supervisor mode on one stack, which the main loop resets to `$4b546`.

- Two 320x184, 4-plane displays at `$70000` and `$78000` (8000 bytes a plane), with a
  copper list each (`$121e`, `$1242`). The level 3 handler (`$24f40`) serves the VBL and the
  blitter; level 2 (`$250a8`) reads the keyboard.
- The main loop (`$28a04`, entered at `$289fe` once per game or demo start) increments the
  frame counter `$c9f4` (cleared at the start), runs the simulation, the particles
  (`$2521c`: count `$c9ec`, list `$a2a6`, each projected with `divs` and plotted by the
  depth-tested dot plotter `$29eb2`), then the landscape renderer (`$29974`), the swap and
  the clear request.
- The renderer projects the landscape grid, then waits (`$29c7e`: `tst.w $606ac`) for the
  back buffer's clear, then draws the tiles and the objects (`$2bbaa`, `$2bc00`). All
  polygons are CPU-filled: `$2c58e` steps the edges and jumps, per scanline, into unrolled
  span writers (one per colour, `$1e412`, `$1f6b2`, ...) that `or`/`and` all four planes.
- The swap (`$1d58c`) writes COP1LC wherever the frame ends; the new buffer shows from the
  next VBL. The clear request (`$1d4fe`) asks for the old front buffer: the VBL handler
  starts its first plane (`$24f7e`, `BLTSIZE` 184x20 words) at that next VBL, when the
  buffer has left the display, and the blitter-done interrupt chains the other three
  (`$25044`, done at `$25094`). So every frame waits for a VBL and then for the clear.
- `$1d614` is a VBL-timed wait (the countdown `$3ca1b`, which the VBL decrements): the fades
  use it, two fields a palette step (the demo's fade-in, `$26a36`, 7 steps).

## Measurements

The demo benchmark (tools/bench.py, [development](development.md#benchmark)): the first
1250 fields (25 s) of the demo mode from `$289fe`, on the `a1200-030` (68030, 50 MHz, cycle
exact) without its MMU model, WHDLoad `CACHE` (instruction cache on, data cache off; the
slave enables the instruction cache too), the original slave. 99.07% of all cycles traced.

- 586 frames: 23.4 fps, 2.13 fields a frame; 12 to 50 fps per half second (the first second
  is the fade-in). Frames of 1 field: 131, 2: 280, 3: 149, 4: 24.
- Frame time (main loop top to top): mean 42.2 ms, p50 39.7, p95 68.3.
- The clear takes 11.9 ms from the VBL (25-field sample after the window), 60% of a field,
  and the renderer cannot draw before it ends. In the sample the swaps came 9 to 18 ms into
  a field, so those frames took 2 fields.

| Where the time goes (all cycles of the window) | Share | ms a field |
|---|---:|---:|
| Waiting for the blitter clear (`$29c7e`) | 31.0% | 6.14 |
| Polygon fill and span writers (`$2c58e`) | 17.3% | 3.43 |
| Objects: ship, trees, ... (`$2bbaa`, `$2bc00`) | 16.4% | 3.24 |
| Particles (`$2521c`) | 11.0% | 2.19 |
| Renderer's own code: grid projection, tile setup (`$29974`) | 10.4% | 2.06 |
| Renderer helpers `$292cc`, `$2a04e` and the `$1c08a`-`$1c4fc` routines | 8.1% | 1.61 |
| Rest of the main loop | 3.7% | 0.73 |
| Interrupts (level 3: VBL, sound, blitter chaining) | 1.3% | 0.25 |
| Fade-in wait (`$1d614`) | 0.8% | 0.16 |

Chip bus slots over the window: CPU 43.1%, bitplanes 22.5%, free 22.4%, blitter 9.7%,
refresh 1.8%, audio 0.4%. Game code and data are all in chip memory (99.7% of the
executed cycles are at chip addresses).

## Slave patches

Offsets are into `Disk.1`.

| `Disk.1` offset | Original | Patch |
|---|---|---|
| `$250c0` (level 2 interrupt, after reading CIA-A SDR into d0) | `bset #6,$bfee01` | `nop; jsr _keyboard`: does the same `bset`, then quits on F10 (`ws_keyexit`) or the reset-warning code `$78` through `resload_Abort` |
| `$2b916` (highscore entry) | `move.w #3000,d7; cmp.w #127,d0` | `nop; jsr _savehi`: on key 13 (return) saves the table, then does the replaced instructions |

The highscore table is 280 bytes at `$2b62e` (`$66e2e`). `Virus.hi` holds it nibble-swapped
and inverted (`_crypt`, its own inverse); it is loaded at start when its size is 280.

`_clamp` (slave offset `$130` in the code hunk) is never called: it would clamp `a3` below
`$78b40` before an offset add, apparently an unfinished fix for the render writes past
512 KB that the larger `ws_BaseMemSize` covers instead.

The game handshakes the keyboard with a CIA-A timer B one-shot, so the handshake does not
depend on CPU speed.

## Limitations

- Needs more than 512 KB of chip memory (above).
- No blitter-wait, cache or game-speed fixes: the slave enables the instruction cache only.
