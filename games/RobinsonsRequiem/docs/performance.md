# Performance

Where the frame time goes in both games, walking in the jungle start, and the plan that
follows from it. Figures are measured in the runs below unless marked DERIVED (computed from
them) or INFERRED (read from code or screenshots, not measured). Offsets are START hunk
offsets (`docs/internals.md`).

## Workload and instruments

`tools/rr_prof.py OUT` boots a developer-type build (`docs/development.md`, "Straight into
the game"), stops at the open of `avion.DO`/`.CO`, runs 150 fields, then holds keypad 9
(forward and to the right) for 500 fields, 10 s PAL, under `WARP=1 DETERMINISTIC=1`.
`tools/rr_report.py OUT` prints the tables below from its output.

- The game draws no frame while the player stands still (`KEY=none`: 0 frames in 500
  fields), so walking is the workload. Movement depends on the frame rate (INFERRED: after
  the same window the compass reads NW at 36 frames and SE at 51), so the views drift apart
  between builds.
- **AGA**, `SETUP=a1200-030` (68030, 50 MHz). The setup's own core (with the MMU model)
  cannot be profiled; aprof runs on the cycle-exact core without it (`FSUAE=$FSUAE_APROF
  EXTRA_ARGS=--uae_mmu_model=0`). The two agree on the baseline: 36 and 37 frames. `BUILD=profile`
  counts frames at the chunky-to-planar call (`PROFILE`, hunk 2 `+$2e78`); its 36 matched
  aprof's call count.
- **ECS**, `custom` (A500, 68000 at 7.09 MHz, 1 MB chip, 2 MB fast), `BUILD=developer
  BARTO=1`: a Barto trace on the native cycle-exact 68000 core (142,102 cycles per field),
  frames counted at the beam wait's entry, hunk 0 `+$cac`. Detail and window are the boot
  values (the menu is skipped); the 3D window is full size in the screenshots.

Both games hold each frame to at least 3 fields: the frame wait (AGA hunk 1 `+$49e8`, ECS
`+$30ac`) loops until the VBL's field count reaches MAIN's cap, hunk 1 `+$ee6a` (ECS
`+$d4c0`), which is 3 in game in both. **60 ms per frame, 16.7 fps, is the ceiling.**

## AGA game, a1200-030

Baseline (`profile`, the release game's code): **36 frames, 3.6 fps, 277.8 ms per frame**,
the CPU never idle, both caches off (CACR `$2000`: KickEmu `CACHE` without WHDLoad's MMU).
195 ms of each frame (70%) is chip-memory access, 261,000 accesses; 83 ms is the rest.
DMA per field: 59% of slots free, bitplanes 13.5%, CPU 24%, blitter none.

| Function | What | ms/frame | In chip accesses |
|---|---|---|---|
| hunk 1 `+$d88c` | landscape, the 3D view's main loop | 108.1 | 76% |
| hunk 2 `+$2db8` | chunky-to-planar (loop `+$2e84`): byte reads, 8 byte writes per 8 pixels into 8 planes | 63.9 | 72%: 19.5 ms plane writes, 26.2 ms chunky reads |
| hunk 1 `+$b7ca` | landscape spans | 27.8 | 57% |
| hunk 1 `+$e0e6` | sky | 12.1 | 83% |
| hunk 1 `+$b6ea` | span set-up, 1,673 calls | 6.9 | 17% |
| hunk 0 `+$13ce` | beam wait before the swap (VPOSR until line 256) | 5.3 | 76% |
| hunk 1 `+$cada` | unrolled span fills | 4.2 | 87% |
| hunk 1 `+$49b2` | frame routine: the cap wait at `+$49ee` (cause not checked) | 4.2 | 0% |
| rest | objects (`+$ea3a`, 20 calls), logic, interrupts | 45.3 | |

Why so much chip: START sizes a fast pool (hunk 0 `+$162`: `AvailMem(MEMF_FAST|
MEMF_LARGEST)` - 50,000, none under 100,000) and then discards it unconditionally (hunk 0
`+$196`, `move.l #0,<hunk 1 +$f4>`), so MAIN, every object's variables and every resource
come from the chip pool. The slave's ExpMem is 256 KB.

The plan's steps as they are done (below), frames in the window, each the `profile` build
of the step's commit; the setup's core is the user's (`FSUAE=$FSUAE_ARM`, MMU model on):

| Step | aprof core | Setup's core |
|---|---|---|
| v1.2 | 36 (277.8 ms) | 37 |
| 1: fast pool, 1 MB ExpMem | 48 (208.3 ms) | 51 |
| 2: caches on | 51 (196.1 ms) | 56 |

Measured before the steps, with measurement switches since removed (commit `a01d9f08`):
a 2 MB ExpMem alone 35 and 37 (nothing moves to fast memory without the pool); the caches
alone (`CACHECHIPDATA`, `pcache`) 39 and 55, with the setup's core's data-cache emulation
off 43; both without the pool 40 and 54; v1.2 under WHDLoad's MMU (`WHD_ARGS=MMU`, caches
on) 55 on the setup's core; the pool with a 2 MB ExpMem 48 and 51, and with the caches
51 (196.1 ms) and 58.

The setup's core gains more from the caches because its data cache also caches chip
memory: with that cache's emulation off, `pcache` gives 43. Accelerator boards do not cache
chip memory, and the aprof core does not either (INFERRED: the aprof core is the closer one).

After step 2 (the same as `ppoolc` at `a01d9f08`), 196.1 ms per frame: chip accesses 120.2 ms (168,000), the rest 75.8 ms.

| Function | ms/frame | In chip accesses |
|---|---|---|
| chunky-to-planar | 61.0 | 72%: 19.1 ms plane writes, 25.1 ms chunky reads |
| landscape `+$d88c` | 45.6 | 39% |
| spans `+$b7ca` | 21.0 | 40% |
| sky `+$e0e6` | 11.7 | 99% |
| span set-up `+$b6ea` | 6.5 | 0% |
| beam wait | 5.4 | 99% |

Still in chip with the pool kept: the chunky buffer, the height-map row table, the shade
tables, the map data and the objects' graphics, all loaded or allocated from the chip pool
(the pool run's addresses); MAIN's frame and the renderer's variables moved to fast.
Of the 120.2 ms, the plane writes (19.1 ms) must stay in chip; the other 101.1 ms are
accesses to memory only the CPU uses.

## ECS game, A500

**15 frames, 1.5 fps, 666.7 ms per frame** (29.5 to 37.5 fields each), the CPU never idle.
DMA per field: 68.5% of slots free, bitplanes 22.5% (four lores planes), CPU 6.8%, copper
0.2%, blitter 0.1%. Four lores planes take only the odd slots, so the 68000 seldom waits
for chip memory: where data sits does not matter here (INFERRED).

| Function | What | ms/frame | Share |
|---|---|---|---|
| hunk 2 `+$19a2` | chunky-to-planar: 4 planes by `add`/`addx` bit shifts, 41 cycles per pixel, 32,000 pixels | 182.6 | 27.4% |
| hunk 1 `+$bee2` | landscape columns: per-column set-up with absolute-addressed variables, divisions (`+$c3a2`...) | 128.2 | 19.2% |
| hunk 1 `+$9d54`-`+$a4ff` | landscape spans: clipping, shade lookups, fills | 103.7 | 15.5% |
| hunk 1 `+$ad48`-`+$b1ff` | unrolled vertical and `move.l` fills | 68 | 10.2% |
| hunk 1 `+$d090` | objects: scaled sprites with transparency, a byte per pixel (`+$d2de`) | 46.4 | 7.0% |
| hunk 1 `+$c73c` | sky: rows copied a word at a time (`+$c8c0`, `+$c8d8`) | 27.5 | 4.1% |
| hunk 0 `+$cac` | beam wait before the swap (VPOSR until line 256) | 8.3 | 1.3% |
| rest | logic, interrupts, Kickstart | 102 | 15.3% |

The chunky bytes carry a dither: an even pixel takes its byte's high nibble, an odd one its
low nibble (INFERRED from the conversion loop).

## Pain points

AGA, a1200-030:

1. **Chip memory: 70% of the frame.** START throws its fast pool away and the slave has a
   256 KB ExpMem, so all renderer data, tables and the chunky buffer are in chip.
2. **Chunky-to-planar: 61-64 ms** (23-31%): byte accesses only, 64,000 chip accesses per
   frame.
3. **Caches off** under WHDLoad's default (no MMU): 12-21 ms on the aprof core.
4. **Landscape loop and spans: 67-136 ms**, most of it chip waits until the data moves.
5. **Waits: 5.3 ms beam wait** before each swap, 4.2 ms in the cap wait.

ECS, A500:

1. **Chunky-to-planar: 183 ms** (27%), an `add`/`addx` shifter at 41 cycles per pixel.
2. **Landscape: 300 ms** (45%): column set-up 128 ms, spans 104 ms, fills 68 ms.
3. **Objects 46 ms, sky 28 ms**, beam wait 8 ms. Memory and the blitter are idle.

## Plan

Each step's gain is to be measured with `tools/rr_prof.py` before the next; the estimates
are DERIVED from the tables above.

AGA, from 277.8 ms (3.6 fps):

1. **Keep the fast pool and give it room** (done): branch over hunk 0 `+$196` and a 1 MB
   ExpMem. Measured: 208.3 ms, 4.8 fps (setup's core 37 → 51 frames).
2. **Caches on** (done): `CACHECHIPDATA` instead of `CACHE`; the game's one blitter copy
   writes planes the CPU never reads. Measured: 196.1 ms, 5.1 fps (setup's core 56 frames).
3. **The CPU-only data to fast**: the chunky buffer, height-map rows, shade tables, map data
   and object graphics from the fast pool (find how START's allocator picks the chip pool for
   them; bitplanes, copper lists, sprites and samples stay in chip). Up to 101 ms of chip
   access goes; fast accesses cost some: about 105 ms, 9.5 fps.
4. **A 68030 chunky-to-planar**: Kalms' `c2p1x1_8_c5_030_2` (`$AMIGA_SHARE/kalms-c2p`)
   for the loop at hunk 2 `+$2e84`: 8,064 longword writes instead of 32,256 byte writes,
   the merge in registers. It fits: the game's loop is a plain 8x8 bit transpose, chunky
   bit n to plane n, no remap. What needs care: the game converts a rectangle (window x
   rounded down to 16 pixels, chunky stride `+$ef1e`, plane modulo set at `+$2e3a`), so a
   per-row driver like `KalmsC2PRect.s` with the strides read at run time (the adapter's
   are assembly constants); Kalms takes widths in 32-pixel steps, the game 16, so a window
   16 pixels over a multiple of 32 keeps the old loop for its last 16; the game's planes
   are 4 pointers (`+$2e02`), each with a second plane at +16000, while Kalms writes plane
   n at n x bplsize (16000 is under its 16 KB limit; if the 4 blocks are not 32,000 apart,
   its stores take 4 base registers); and it reads one longword past each row. The
   conversion goes from about 36 ms (after step 3) to about 10 ms: about 80 ms, 12.5 fps.
   Validate the planes byte for byte against the original loop.
5. **No beam wait**: set the bitplane pointers from the VBL (hunk 0 `+$13ce`, `+$13f6`), and
   wait only when the next conversion would write the shown planes. About 75 ms.
6. **The landscape loop for the 68030** (hunk 1 `+$d88c`, `+$b7ca`: about 40 ms of CPU
   work left after step 3) until the heaviest frames are under 60 ms.

Stop there: at 60 ms the cap holds every frame to 3 fields, and nothing faster shows.
Beyond it is a different project: lifting the cap changes the game's speed (movement per
frame, INFERRED) and needs a fixed-time simulation first. Check step 6 against heavier
scenes (more trees and objects) than this walk.

ECS, from 666.7 ms (1.5 fps); 60 ms is out of reach on a 7 MHz 68000:

1. **Chunky-to-planar** (hunk 2 `+$19a2`, loop `+$1a62`): a merge (Kalms c5) 4-plane
   conversion. The game's loop shifts one bit at a time with `add`/`addx`, 41 cycles per
   pixel; a merge conversion swaps bit groups a longword at a time, about 18-22 cycles per
   pixel on the 68000: 183 → about 85 ms. Kalms' `c2p1x1_4_c5_gen` is the model but not a
   drop-in: it wants a pixel per byte in the low nibble, whole-screen chunky and planes at
   one spacing. The game packs its dither into the chunky bytes (an even pixel is the high
   nibble of its byte, an odd one the low nibble of the next, `+$1a66`-`+$1a84`), so a mask
   (`$f00ff00f`) and shift replace Kalms' first merge stage; it converts a rectangle in
   16-pixel steps with a run-time modulo (`+$1a20`, `+$1a3e`) and writes two plane
   pointers, each with a second plane at +16000, from one of two tables (`+$d459` picks
   the buffer). Validate the planes byte for byte against the original loop. Later, if the
   CPU is still the limit: the blitter (idle, 68.5% of slots free) can take the last merge
   pass in parallel while the CPU runs from fast memory. About 570 ms.
2. **Sky** by blitter, or `movem.l`: up to 27 ms. About 540 ms.
3. **Column set-up** (hunk 1 `+$bee2`): variables in registers, divisions by reciprocal
   table: 30-50 ms. About 500 ms.
4. **Span set-up and clipping** (hunk 1 `+$9d54`-`+$a4ff`; the fills are unrolled
   already): 20-40 ms. About 470 ms, 2.1 fps.

Stop there: what is left is fills that are unrolled `move.l` stores already, the objects
(46 ms) and the logic, each a rewrite for under 10%. Beyond that, fewer pixels (the LOW
detail and window settings), not code.

## Reproducing

```sh
# AGA, aprof core (one capture at a time per repository)
BUILD=profile APROF=1 FSUAE=$FSUAE_APROF EXTRA_ARGS=--uae_mmu_model=0 \
    python3 tools/rr_prof.py tmp/prof/base-aprof
# AGA, the setup's core: frames only
BUILD=profile FSUAE=$FSUAE_ARM python3 tools/rr_prof.py tmp/prof/base-arm
# ECS
VARIANT=RobinsonsRequiem SETUP=custom BUILD=developer BARTO=1 python3 tools/rr_prof.py tmp/prof/ecs-base
python3 tools/rr_report.py tmp/prof/base-aprof
```

The `profile` build is the current source, every step done so far; v1.2's figures are the
`profile` build at commit `a8bb6fbe`.
