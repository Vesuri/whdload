# Performance

Where the frame time goes in both games, walking in the jungle start, and the plan that
follows from it. Figures are measured in the runs below unless marked DERIVED (computed from
them) or INFERRED (read from code or screenshots, not measured). Offsets are START hunk
offsets (`docs/internals.md`).

## Workload and instruments

`tools/rr_prof.py OUT` boots a developer-type build (`docs/development.md`, "Straight into
the game"), stops at the open of `avion.DO`/`.CO`, runs 150 fields, then holds keypad 9
for 500 fields, 10 s PAL, under `WARP=1 DETERMINISTIC=1`. Keypad 9 turns the player on the
spot (AGA: its position stayed put for 182 fields while its heading went from -63 to -249
degrees); keypad 8 walks forward.
`tools/rr_report.py OUT` prints the tables below from its output; `tools/rr_passes.py OUT`
runs the same workload under gdb breakpoints for the AGA game's drawing passes and frame
intervals.

- The game draws no frame while the player stands still (`KEY=none`: 0 frames in 500
  fields), so turning is the workload. The player turns once per run of its script (`heros`,
  period 7, 7 to 9 degrees a run; `docs/internals.md`, "Objects and the scheduler"), and its
  runs depend on the frame rate ("Objects' rhythm" below), so the views drift apart
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
`+$d4c0`), which is 3 in game in both.

The AGA game's 3D frames are bounded further by the object the view follows, the player
(`heros`; the view redraws when it has moved, hunk 1 `+$48b8`). MAIN runs the due objects,
then the frame routine (hunk 1 `+$49b2`: after a swap the copper-interrupt wait for the
next field, the cap wait, the drawing, the swap), and again; an object is due once the VBL
count passes its last run plus its period (`docs/internals.md`, "Objects and the
scheduler"). The game, when it keeps up, runs its objects on the cap's grid of 3 fields,
the player (period 7) every 9: **a frame every 9 fields, 180 ms, 5.56 fps, is the ceiling
while frames come only when the player has run** (55.6 frames in the window), and the
world's speed since plan step 7, which keeps that grid whatever the drawing takes. Step 6's
frame pacing ran the player every 8 fields (6.25 fps), faster than the game. The player
turns and walks a fixed step per run of its script, so its period sets its speed; since
plan step 8 the frames between its runs show the camera on its way between two runs'
poses, so the drawing sets the frame rate, up to the cap's 3 fields (16.7 fps).

### Objects' rhythm

Fields between an object's runs, the mean of 117 to 171 fields (`tools/rr_objects.py`, the
`developer` build: START's scheduling, a slave assembled without step 6's `bsr
_pacepatch`; step 6's frame pacing; step 7's world count, the count the objects ran by):

| Objects | Period | START, standing | START, turning | Step 6, standing | Step 6, turning | Step 6, walking | Step 7, all three |
|---|---|---|---|---|---|---|---|
| MAIN, `souris`, `yoda`, `time`, `sjungle` | 0 | 3.00 | 3.1 | 3.97 | 2.7 | 2.7 | 3.00 |
| `caporal` | 3 | 6.00 | 4.65 | 8.00 | 5.82 | 4.80 | 6.00 |
| `heros` (the player) | 7 | 9.00 | 9.20 | 8.00 | 8.00 | 8.00 | 9.00 |
| `human` | 10 | 12.00 | 12.6 | 12.00 | 12.00 | 12.00 | 12.00 |
| `skyjun` | 15 | 18.00 | 18.6 | 16.00 | 16.00 | 16.00 | 18.00 |

Standing still in START's scheduling every object runs on the cap's grid: period + 1 fields
rounded up to a multiple of 3, the game's rhythm whenever it keeps up. Drawing breaks the
grid: a drawing pass delays what comes due during it, and the pass after a long one starts
at once (its cap has passed), so turning gives longer intervals to the long periods and
shorter ones (1-field gaps) to the short. The pacing (step 6) changed the rhythm in all
three cases: the player every 8 fields instead of 9, the period-0 objects (`time` counts
the passes: a game clock, INFERRED) every 3.97 fields standing and 2.7 turning instead of
3, `caporal` every 8 standing instead of 6, `skyjun` 16 instead of 18. Step 7 puts every
object on the grid standing, turning and walking, on both cores: every interval of the
world count is the grid's (47 of 47 for the period-0 objects), the VBL count's mean 2.91 to
3.00 for them (a catch-up pass runs them a field or two after their time).

In START's scheduling (before plan steps 6 and 7) MAIN sees the object due only between frame
routines: at the drawing pass's end, at the next pass's (the view copied into the other
buffer, a field later), then a cap apart. A frame landed on the 8 fields only when one of
those fell in the field the object came due, which depends on the field the drawing pass
ended in, not on its speed: `tools/rr_passes.py` (gdb breakpoints, the VBL count and the
beam's line) gave frames every 9 fields, now and then 10, for drawing passes of 2.0 to
3.1 fields on the setup's core, and every 6 to 12 fields, 8.9 on average, for 3.4 to 5.8
fields on the aprof core, where a pass ending in its fourth field put the next frame 10
fields on. So frame counts saturated near 53-57 while the work fell; `tools/rr_report.py`
also gives the busy time per frame, the frame time without the waits (the cap wait, the
copper-interrupt wait at a 3D pass's start, the beam wait, the slave's waits), which keeps
falling.

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

The plan's steps as they are done (below), frames in the window and the busy time per
frame on the aprof core, each the `profile` build of the step's commit; the setup's core is
the user's (`FSUAE=$FSUAE_ARM`, MMU model on), frames only:

| Step | aprof core | Busy per frame | Setup's core |
|---|---|---|---|
| v1.2 | 36 (277.8 ms) | 267.8 ms | 37 |
| 1: fast pool, 1 MB ExpMem | 48 (208.3 ms) | 198.5 ms | 51 |
| 2: caches on | 51 (196.1 ms) | 185.9 ms | 56 |
| 3: the 3D view's buffers in fast memory | 57 (175.4 ms) | 132.7 ms | 55 |
| 4: Kalms' 68030 chunky-to-planar | 57 (175.4 ms) | 111.3 ms | 53 |
| 5: no beam wait (not kept) | 57 (175.4 ms) | 113.5 ms | |
| 6a: the sky copy by longwords | 57 (175.4 ms) | 108.8 ms | 53 |
| 6b: frame pacing (replaced by step 7) | 62 (161.3 ms) | 108.4 ms | 62 |
| 7: the world on the cap's grid | 55 (181.8 ms) | 110.0 ms | 55 |
| 8: the camera between the player's runs | 80 (125.0 ms) | 94.8 ms | 126 |
| 9: the other moving objects between their runs | 80 (125.0 ms) | 94.9 ms | 126 |
| 10a: the wait for the world at the pass's end | 101 (99.0 ms) | 92.2 ms | 148 |
| 10b: the map in fast memory | 108 (92.6 ms) | 83.6 ms | 161 |
| 10c: the shade table in fast memory | 110 (90.9 ms) | 82.0 ms | 163 |
| 10d: the swap without the beam wait | 122 (82.0 ms) | 81.6 ms | 166 |

Rows 8 and 9 were measured before frames drawn only for the staging re-projected the
view's elements (step 8); the projection cost 10a 3 frames on the setup's core and 1 on
the aprof core (151 and 102 frames, busy 91.0 ms, without it).

After step 6 every frame interval is 8 fields on both cores (`tools/rr_passes.py`, 240
events: 36 frames on the aprof core with drawing passes of 3.3 to 6.5 fields, 28 on the
setup's core with 2.1 to 4.1). The busy time per frame stays (108.8 → 108.4 ms); the
pacing wait, 31.5 ms per frame, takes most of the cap wait's place (57.6 → 12.1 ms).
After step 7 every frame interval is 9 fields, the game's own (300 events: 30 frames on the
aprof core turning, drawing passes of 3.2 to 6.2 fields, 33 walking with 4.4 to 5.4; 26 on
the setup's core, 2.0 to 4.1), with a catch-up pass after nearly every frame on the aprof
core (33 in 92 passes turning, 33 in 99 walking) and 10 in 80 on the setup's core; the wait
for the world count is 61.2 ms per frame, the busy time 110.0 ms. After step 8 a frame
comes on every pass the drawing allows: every 6 fields on the aprof core (46 of 48
intervals turning, 47 of 48 walking; drawing passes of 3.3 to 6.2 fields), every 3 or 6 on
the setup's core (41 and 15 turning, 34 and 20 walking; 1.9 to 3.7 fields). The busy time
falls to 94.8 ms: the unchanged passes' copy of the shown planes (hunk 2 `+$5b6`, 13.3 → 1.7
ms per frame) is nearly gone, every pass drawing.

From step 3 on the frame counts are near the object period's ceiling: step 3's frames
alternate a drawing pass of about 7 fields with an idle 3-field pass (33.1 ms per frame in
the cap wait), and the setup's core, faster at every step, shows no gain.

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
| hunk 1 `+$bee2` | landscape columns: the loop over a row's samples (`+$c010`), two map walkers and the projection, every register taken | 128.2 | 19.2% |
| hunk 1 `+$9d54`-`+$a4ff` | landscape spans: clipping, shade lookups, fills | 103.7 | 15.5% |
| hunk 1 `+$ad48`-`+$b1ff` | unrolled vertical and `move.l` fills | 68 | 10.2% |
| hunk 1 `+$d090` | objects: scaled sprites with transparency, a byte per pixel (`+$d2de`) | 46.4 | 7.0% |
| hunk 1 `+$c73c` | sky: rows copied a word at a time (`+$c8c0`, `+$c8d8`) | 27.5 | 4.1% |
| hunk 0 `+$cac` | beam wait before the swap (VPOSR until line 256) | 8.3 | 1.3% |
| rest | logic, interrupts, Kickstart | 102 | 15.3% |

The chunky bytes carry a dither: an even pixel takes its byte's high nibble, an odd one its
low nibble (INFERRED from the conversion loop).

The plan's steps as they are done (below): frames in the window, the mean interval between
them (`tools/rr_report.py`, from the Barto trace's frame marks; finer than the frame count)
and the time per frame of the functions the plan works on, each the step's commit under
Barto (the `developer` build for v1.2 and step 1, then `profile`, the same code with the
slave's address recorded so that the report names the slave's routines):

| Step | Frames | Mean interval | Conversion | Column set-up `+$bee2` | Spans `+$9d54` | Sky `+$c73c` |
|---|---|---|---|---|---|---|
| v1.2 | 15 | 649.5 ms | 182.6 ms | 128.2 ms | 103.7 ms | 27.5 ms |
| 1: a merge chunky-to-planar | 17 | 596.3 ms | 138.9 ms | 121.4 ms | 94.0 ms | 25.8 ms |
| 2: the sky by unrolled longwords | 17 | 578.2 ms | 143.3 ms | 122.6 ms | 95.9 ms | 13.9 ms |

The functions other than the step's own change between the rows with the view (the walk
goes further with more frames).

## Pain points

AGA, a1200-030:

1. **Chip memory: 70% of the frame.** START throws its fast pool away and the slave has a
   256 KB ExpMem, so all renderer data, tables and the chunky buffer are in chip.
2. **Chunky-to-planar: 61-64 ms** (23-31%): byte accesses only, 64,000 chip accesses per
   frame.
3. **Caches off** under WHDLoad's default (no MMU): 12-21 ms on the aprof core.
4. **Landscape loop and spans: 67-136 ms**, most of it chip waits until the data moves.
5. **Waits: 5.3 ms beam wait** before each swap, 4.2 ms in the cap wait.
6. **The ceiling is 6.25 fps here**, not the cap's 16.7: the object that triggers the 3D
   frames runs every 8 fields at most, and MAIN, a cap apart, often sees it a pass late
   (above).

ECS, A500:

1. **Chunky-to-planar: 183 ms** (27%), an `add`/`addx` shifter at 40 cycles per pixel.
2. **Landscape: 300 ms** (45%): columns 128 ms, spans 104 ms, fills 68 ms.
3. **Objects 46 ms, sky 28 ms**, beam wait 8 ms. Memory and the blitter are idle.

## Plan

Each step's gain is to be measured with `tools/rr_prof.py` before the next; the estimates
are DERIVED from the tables above.

AGA, from 277.8 ms (3.6 fps):

1. **Keep the fast pool and give it room** (done): branch over hunk 0 `+$196` and a 1 MB
   ExpMem. Measured: 208.3 ms, 4.8 fps (setup's core 37 → 51 frames).
2. **Caches on** (done): `CACHECHIPDATA` instead of `CACHE`; the game's one blitter copy
   writes planes the CPU never reads. Measured: 196.1 ms, 5.1 fps (setup's core 56 frames).
3. **The CPU-only data to fast** (done): the 3D view's chunky buffer and the renderer's
   tables from the top of the fast pool (`docs/internals.md`, "AGA improvements"). Chip
   accesses 120.2 → 61.0 ms per frame (18.0 of them the plane writes); busy 185.9 → 132.7
   ms. The resource heap (map data) and MAIN's 256 KB block (the objects' graphics) stay in
   chip: the heap also holds the sounds Paula plays (INFERRED: the `.SND` files load there).
4. **A 68030 chunky-to-planar** (done): Kalms' `c2p1x1_8_c5_030_2` for the loop at hunk 2
   `+$2e84` (`src/c2p030.s`). The game's loop is a plain 8x8 bit transpose, chunky bit n to
   plane n; its planes 0-1 are in the slave's reserved chip block and 2-7 elsewhere (each
   pointer with its pair 16,000 bytes on), so each of Kalms' two passes writes through two
   bases; a row driver applies START's strides, and widths that are not a multiple of 32
   pixels (not in this walk) go back to START's loop. `tools/rr_c2pcheck.py`: 4,000 random
   rectangles byte-identical to START's loop; the walk's first screenshot is
   pixel-identical to step 3's. Measured: the conversion 36.2 → 10.5 ms (8,080 longword
   writes per frame instead of 32,256 byte writes and 32,256 chip reads); busy 132.7 →
   111.3 ms.
5. **No beam wait** (measured, not kept): the swap (hunk 0 `+$13e0`) waits for line 256 and
   rewrites the copper list's plane pointers (`+$13f6`) at the list's start. Two small
   copper lists in chip, the plane pointers and a jump into the game's list behind its
   own, swapped through COP1LC (taken at the next field), with the drawing into the
   replaced planes held until the next field (the conversion, the blitter copy hunk 2
   `+$5b6`, the pointer hunk 2 `+$4ec`), removed the beam wait (5.8 ms per frame) and the
   copper-interrupt wait (3.5 ms). Nothing came of it: the next 3D pass still waits for the
   swap to show, now in START's own wait for the pointer's redraw on the new screen (hunk 1
   `+$4a14`: `+$ed99`, set at the swap `+$4b44`, is cleared by the VBL's pointer routine
   `+$9aa6`), 7.3 ms per frame, and the rest grew from 111.3 to 113.5 ms; 57 frames either
   way. The beam wait ends at line 256, about a millisecond before the field does, so it
   never costs a pass a field. Step 10.2 removes it with the next pass's waits put off to
   its first access to the back screen.
6. **Every frame on the object's 8 fields** (done). The drawing pass, from the pass's
   start after the cap wait (hunk 1 `+$49f6`) to the swap (`+$4b30`), took 3.44 to 5.75
   fields on the aprof core after step 4 (`tools/rr_passes.py`), 2.0 to 3.1 on the
   setup's core, whose chip accesses cost less; the frames came every 6 to 12 fields and
   every 9 or 10 (above, "Workload and instruments").
   1. **The sky copy by longwords** (done, `docs/internals.md`, "AGA improvements"): the
      sky 8.5 → 4.1 ms per frame, busy 111.3 → 108.8 ms; the drawing pass 3.23 to 5.69
      fields on the aprof core, the setup's core unchanged.
   2. What is left in chip in the pass is read-only to it but not to the game: the map
      (hunk 1 `+$da6c`, `+$db1e`, `+$ba7c`-`+$ba92`, about 10 ms) and the shade table
      (`+$ef3c`, `+$bab6`, 2 ms), both in the resource heap. The heap compacts (hunk 1
      `+$92dc` moves the blocks above a freed one down and lowers every table pointer above
      it, with no upper bound), so a block cannot live in fast memory, and the scripts
      write the map (`+$3b2c`-`+$3b4e`, `+$3b82`), so a fast copy would go stale unless
      those writes reach it (done in step 10.2 for the map).
   3. **Frame pacing** (done, replaced by step 7): when a pass ends
      and the followed object comes due within the cap, the frame routine waits for it,
      so that MAIN runs it when it is due, and the next pass, which draws its frame, skips
      its cap wait. 62 frames on both cores, every interval 8 fields, with drawing passes
      of up to 6.5 fields: the frame starts when the object has run, so the pass has
      nearly the whole 8 fields. It changed every object's rhythm ("Objects' rhythm"):
      the player every 8 fields where the game, keeping up, gives 9; the period-0 objects
      (with `time`'s clock) every 2.7 fields turning and 3.97 standing instead of 3.

At 8 fields per frame the player's period holds every frame, and nothing faster shows by
drawing faster alone.

AGA, beyond the player's period: frames between the player's runs, with the world on the
game's own rhythm whatever the frame rate. Step 7 (done) replaces step 6.
The world's speed is the game's own, the cap's grid, as decided: the player every 9 fields,
not step 6's 8. Holding the player at 8 would need a grid of single fields, on which the
short periods run faster than the game ever runs them (`caporal` every 4 fields, not 6).

7. **The world on the cap's grid** (done, `docs/internals.md`, "AGA improvements"). A world count W, advanced by the cap (3 fields) per
   pass, takes the VBL count's place in the scheduler's due test and next run (hunk 1
   `+$257e` [`$6a2a`]) and in op `$36` (`+$6480` [`$a92c`]). At the list's end (`+$250e`
   [`$69ba`]) MAIN goes round the list again without the frame routine while W is a pass
   or more behind the VBL count, at most twice in a row; further behind (a load, a pause) W
   is set to the count, dropping the time as the game does. Each pass waits until the VBL
   count reaches W, which takes over the cap wait's job. Every object then runs as the game
   runs it when it keeps up (the "No pacing, standing" column), however long the drawing
   takes: the player every 9 fields (5.56 runs a second: the game's speed, 12.5% slower than
   step 6's 8), the period-0 objects and `time`'s clock every 3. In 3D mode (`+$ee03`)
   first, W set to the count when it starts. Measured: `tools/rr_objects.py` gives the
   grid's intervals standing, turning and walking on the setup's core and turning on the
   aprof core ("Objects' rhythm"); frames every 9 fields on both cores turning and walking,
   55 in the window, with about one catch-up pass per frame on the aprof core
   (`tools/rr_passes.py`, its `L` marks; table above). Not yet checked in a heavier scene
   (more trees and objects), where the drawing pass would pass the 9 fields two catch-up
   passes cover.
8. **The camera between the player's runs** (done, `docs/internals.md`, "AGA
   improvements"). The frame routine draws on every pass (at most
   every 3 fields, 16.7 fps) with the view's camera staged between the followed object's
   last two poses. At each list's end the slave samples the followed object's pose as
   `+$48b8` reads it, keeping the one before a change and the change's W and interval (at
   most the object's period on the cap's grid). Before the drawing (`+$4b8e`) it moves
   the camera back by (cur - prev) × (1 - alpha), alpha = (now - W of cur) / the interval,
   at most 1 (angles the short way round, in whole degrees), marks the view changed when
   that camera was not the last drawn, draws, and puts the camera back: scripts read the
   views among MAIN's variables, and `+$48b8` compares against the camera. No
   interpolation across a jump: a move longer than about four walking runs, a new followed
   object, 3D mode starting, a load. Per-frame code that assumes a frame per move stays on
   world passes: `+$4980` adds the view's velocity (`+42`-`+46`) on the game's own
   changed frames only, and the unchanged path's countdown `+$ef2a` (view flag bit 5) is
   counted by the slave on the frames drawn only for the staging. What runs between staging
   and putting back is the drawing and the interrupts (the VBL's `+$6c4e`, when `+$ee71` is
   set, fades the palette). The view lags by one run: a new pose is reached one run (9
   fields, 180 ms) after the run instead of at the next frame, though the motion starts
   showing in the same frame as before. Extrapolation, cur + (cur - prev) × alpha, has no
   lag but overshoots by up to a run's step (7 to 9 degrees) when the player stops: to
   try in play. Check: `tools/rr_passes.py` (frames per 500 fields, their intervals), the
   camera per frame evenly spaced while turning, `tools/rr_objects.py` as after step 7,
   and with alpha held at 1 (a test define) frames pixel-identical to step 7's. Estimate
   (DERIVED from the drawing passes after step 6, 2.1 to 4.1 fields on the setup's core
   and 3.3 to 6.5 on the aprof core, plus the objects' runs): a frame every 3 to 4 fields
   on the setup's core (12.5 to 16.7 fps) and every 4 to 7 on the aprof core (7 to 12.5
   fps), against 5.56 on the grid and 6.25 with the pacing. Measured: 126 frames in the
   window on the setup's core (12.6 fps, 79.4 ms) and 80 on the aprof core (8.0 fps, 125.0
   ms), against 55; the camera evenly spaced (`tools/rr_passes.py`'s cameras: turning 3
   degrees every 3 fields on the setup's core and 6 every 6 on the aprof core, walking
   about 9.5 units every 3 fields), the objects' intervals unchanged (`tools/rr_objects.py`
   turning and walking), and with `INTERP_OFF` the window's frames (55) and both
   screenshots pixel-identical to step 7's; with interpolation the last frame (after the key
   is let go) is too. A frame drawn only for the staging marks the view's elements to be
   projected again, as `+$4980` does on the game's own changes: the drawing projects an
   element only when it is marked (state 2), so without this a creature kept its screen
   position from the game's last change while the camera turned (seen in play, `human`
   walking up to the player; gdb at each changed drawing turning, `human`'s element was
   unmarked on 11 of 24 and its screen box unchanged, all 24 marked and moving with the
   fix). Extrapolation not tried; the pointer's picking in a staged frame not
   checked.
9. **The other moving objects between their runs** (done, `docs/internals.md`, "AGA
   improvements"): their 3D elements (`+$4792` moves them by their object's difference at
   each run) staged the same way for the drawing (`human` here); their animation frames
   stay per run. While the camera stays, frames for the staging only when a staged element
   is on screen; otherwise the game's own redraw of a moved element's region. Measured in
   the jungle start, where no creature comes into view in the window (`human` patrols
   some 2,000 units from the standing player, gdb over 2,000 fields): at
   each drawing `human`'s element lies between its last two positions as alpha gives
   (its 8-unit steps every 12 fields drawn 6, 4 and 2 units back), and at each frame
   routine it is back on the object's own (gdb, 120 events turning); standing, no frame is
   drawn (`tools/rr_passes.py KEY=none`: 40 passes every 3 fields, none drawing); turning,
   the frames and busy time are step 8's. A staged element is projected through step 8's
   marking of the view's elements. A creature moving on screen is checked only by eye in
   play (`human` walking up to the player, which showed step 8's missing projection).
10. **The drawing pass again**: it now sets the frame rate, up to the cap.
   1. **The wait for the world at the pass's end** (done, `docs/internals.md`, "AGA
      improvements"). After step 9 a frame still started on the cap's grid: the wait for W
      was at the frame routine's start, where START's cap wait is, so a drawing that ended
      late in its third field, its list then running into the fourth, set off a catch-up
      pass and the next frame waited for the sixth (19 of 55 frames walking on the setup's
      core, from `tools/rr_passes.py`'s swaps and pass starts; on the aprof core the world
      wait was 23.7 ms per frame). With the wait at the frame routine's end the next list
      waits for its time and the drawing after it starts at once. Measured: 151 frames in
      the window on the setup's core (frame intervals of 3 or 4 fields: turning 39 and 18,
      walking 48 and 10, 151.8 and 157.6 frames per 500 fields against 131.5 and 121.6) and
      102 on the aprof core (10.2 fps, 98.0 ms; intervals of 4 to 7 fields turning, 5 or 6
      walking), the world wait 0.4 ms per frame, busy 91.0 ms; the objects' intervals the
      grid's standing, turning and walking (`tools/rr_objects.py`). With step 8's
      projection of the view's elements in staged frames: 148 on the setup's core and 101
      on the aprof core (10.1 fps, 99.0 ms, busy 92.2 ms).
   2. **The map in fast memory** (done, `docs/internals.md`, "AGA improvements"). After
      10a the map's reads from chip took 9.6 ms per frame on the aprof core (`+$da6c`,
      `+$db1e`, `+$ba7c`-`+$ba92`: about 10,600 byte and word reads at 0.9 µs each). The
      landscape reads it only through the row table it loads at `+$d908`, so it gets a
      table into a copy in fast memory, in the row table's block from the fast pool; the
      copy follows the map's moves and the scripts' two grid writes. Checks: with
      `MAPCHECK` the copy equal to the map at all 86 drawings of 500 fields turning and
      500 walking; gdb at every map read site for 6 drawings walking, no pointer outside
      the copy (and the row after it) or the map (a control run with the copy left out of
      the range stops at once); screenshots after the keys are let go pixel-identical to
      10a's wherever the player's pose is the same (6 of 9: when a walk ends depends on
      when the frames fall, so the new build walked one step further, 5,090 against 5,062,
      in a run that is deterministic: the committed build gave the same poses twice).
      Measured: 161 frames on the setup's core against 148, 108 on the aprof core (10.8
      fps, 92.6 ms) against 101, busy 92.2 → 83.6 ms, the map's reads 0.9 ms; the beam
      wait 5.4 → 7.3 ms (more frames); the objects' intervals the grid's, turning and
      walking (`tools/rr_objects.py`).
   3. **The shade table in fast memory** (done, `docs/internals.md`, "AGA improvements").
      After 10b the spans' shade reads from chip (`+$bab6`, `+$babe`: 1,316 each a frame)
      took 2.1 ms per frame on the aprof core. The table (`<+$ef3c>`, 4 KB in the jungle)
      is set only by the view's shade set-up, so the set-up records how much of it the
      shading can read and each drawing gets a copy in the row table's block (item 2's),
      made again when the table's address changes. Checks: with `MAPCHECK` the copy equal
      to the table at all 86 drawings of 500 fields turning and 500 walking; gdb at the
      four shade reads for 14 drawings turning and walking, no index of 4,096 or more (a
      control run stopping at an index of 3,584, level 14, stops at once, at `+$bab6` and
      `+$babe`); screenshots at the start and after 500 fields turning and 500 walking
      pixel-identical to 10b's, with the same poses. Measured: 163 frames on the setup's
      core against 161, 110 on the aprof core (11.0 fps, 90.9 ms) against 108; the shade
      reads 2.37 → 0.47 ms per frame, the spans 15.9 → 14.2 ms and their chip accesses
      2,682 → 47 per frame; busy 83.6 → 82.0 ms; the objects' intervals the grid's,
      turning and walking (`tools/rr_objects.py`).
   4. **The swap without the beam wait** (done, `docs/internals.md`, "AGA
      improvements"). After 10c the waits around the swap took 8.4 ms per frame on the
      aprof core: the beam wait before it (hunk 0 `+$13ce`, 7.1 ms) and, at the next
      pass's start, the wait for it to show (`+$13c0`, 1.3 ms). The copper takes the plane
      pointers at the field's start, so the swap's line does not change the field the
      frame shows in; the waits only held back the next drawing, which renders into the
      fast chunky buffer and needs the back screen only from the conversion on. So the
      swap writes the pointers at once, and the wait for it to show, START's pointer
      wait (`+$4a14`) and the back screen's update are put off to the pass's first access
      to the back screen (step 5 had removed the waits without this, and the next pass
      waited at `+$4a14` instead). The back screen's other loads, from the scripts' and
      the menus' drawing, wait for the swap to show first. Checks: screenshots at the
      start and after 500 fields turning and 500 walking pixel-identical to 10c's, with
      the same poses (a first version that let START's `+$525a` leave its last rectangle
      in `<+$edda>`-`<+$ede3>` in the middle of the drawing showed the 3D view's bottom
      line drawn over the panel's border after turning); the release build reaches the
      jungle through the intro and menu (`tools/rr.py ingame`), pointer drawn. Measured:
      122 frames on the aprof core (12.2 fps, 82.0 ms) against 110, the waits 8.8 → 0.3
      ms per frame (the world wait), busy 82.0 → 81.6 ms; the setup's core at the cap, 166
      frames against 163, every frame interval 3 fields turning and walking (47 of 47,
      `tools/rr_passes.py`, drawing passes of 1.70 to 3.00 fields turning, 2.25 to 2.48
      walking); the aprof core's intervals 3 to 6 fields, 3.93 on average (turning,
      drawing passes of 2.93 to 4.98 fields); the objects' intervals the grid's, turning
      and walking (`tools/rr_objects.py`). The mouse pointer moving and the scripts'
      drawing (inventory, messages) are play-tested; the runs have neither.
   5. What is left is the drawing (aprof core after 10d, 122 frames, 82.0 ms per frame,
      busy 81.6 ms, 14.3 ms of it chip accesses):

      | Function | ms/frame | In chip accesses |
      |---|---|---|
      | hunk 1 `+$d88c`, the landscape | 30.6 | 0% |
      | hunk 1 `+$b7ca`, the spans | 14.1 | 0% |
      | Kalms' conversion, both passes | 10.5 | 45% |
      | hunk 1 `+$b6ea`, span set-up, 1,575 calls | 5.9 | 0% |
      | the sky (`_skyrows`) | 4.3 | 87% |
      | hunk 1 `+$ea3a`, objects | 2.1 | 82% |
      | hunk 2 `+$5b6`, the blitter copy of the view's rectangles | 1.1 | 93% |

      The landscape's loop (`+$d9ba`-`+$dbac`, 3,607 samples a frame) spreads its 28 ms
      over some 60 instructions of 0.1 to 1.0 ms each, most on its variables (`-6xx(a1)`)
      and five absolute stores a sample (step 15). The spans and their set-up spread 20 ms
      over 1,575 set-ups and 1,319 spans a frame. All of it is in fast memory.

AGA, to 50 fps. The target is a frame every field on a CPU as fast as one likes. What the
CPU's speed does not remove is the frame structure (one drawing per world pass, at most
every 3 fields: 16.7 fps) and the time on the chip bus. Measured with the aprof core's
68030 at 400 MHz, 8 times the preset's clock (`--uae_cpu_frequency=400000000`: still
cycle-exact, chip accesses at the chipset's speed; FS-UAE's `uae_cpu_speed=max` is no
stand-in: on the setup's core it gave 112 frames, against 166 at the preset's clock): 166 frames, the cap; busy 22.3
ms per frame, 13.7 ms of it chip accesses (17,745 a frame), and 37.9 ms waiting for the
world. The CPU's own work shrank with the clock (the landscape 30.6 → 3.5 ms, the spans
14.1 → 1.7, the span set-up 5.9 → 0.7); the chip-bound work did not: the sky 3.9 ms (98%
chip), the conversion 5.2 ms (90-95%: its 8,064 longword plane writes), the objects 1.8 ms
(98%), the blitter copy 0.7 ms. A frame every field needs frames between world passes (step
11) and a frame's chip time well inside a field (steps 12-14). The CPU's work (step 15)
decides only how close a real 68030 to 68060 gets.

11. **Frames between world passes** (done, `docs/internals.md`, "AGA improvements"),
    presentation only. After a world pass's frame, while the next pass is not due, the
    slave runs START's frame routine again (from hunk 1 `+$49c2`, past the list's
    operands, as on a pass on which no object came due) with the camera and the staged
    elements at the field the frame will show in, instead of waiting. The world pass
    keeps the game's grid. Of the frame routine's per-pass work, the countdown `+$ef2a`
    is kept on world passes; `+$4980`'s velocity, the objects' sampling, `+$525a`'s
    rectangles, the pointer's background and the locks are already safe to repeat (the
    velocity and the sampling run only on the game's changes, the rest for every frame
    routine as in START). A frame is drawn when the last one was staged (none standing),
    shows in a later field than it and is expected to swap an eighth of a field before
    the next pass is due (from the last frame's times). The pointer's picking reads the
    boxes of the frame shown last, as since step 8 (INFERRED, not play-checked). The test
    define `PRESENT_OFF` leaves them out. Checks: with `PRESENT_OFF` 166 frames on the
    setup's core and the start and end screenshots pixel-identical to 10.2's; the objects'
    intervals the grid's at 400 MHz turning and walking (`tools/rr_objects.py`).
    Measured at 400 MHz: 367 frames against 166 (36.7 fps, 27.2 ms), busy 20.4 ms a frame
    (13.8 of it chip accesses, 18,351 a frame), the world wait 5.8 ms; turning, 26 world
    passes and 37 frames between them in 77 fields, shown 1 field apart 50 times, 2
    fields 11 times and 4 fields once (`tools/rr_passes.py`, "shown intervals"), the
    camera a step a field. The estimate (DERIVED) was a frame every 1 to 2 fields. Per
    frame the sky 4.0 ms, the landscape 3.5, the conversion 2.7 + 2.6, the spans 1.6, the
    objects 1.5. On the 50 MHz cores no frames between passes (their drawing takes 1.7
    fields and more): 166 frames on the setup's core and 122 on the aprof core, as 10.2's.
12. **The sky in fast memory** (done, `docs/internals.md`, "AGA improvements"):
    `_skyrows` read 4,196 longwords a frame from the sky's image, a resource in the chip
    heap (width - 1 at `+2`, height at `+4`, the pixels from `+8`, 10,248 bytes in the
    jungle; the row's source set at hunk 1 `+$e252` [`$126fe`]). It now reads a copy in a
    32 KB room from the fast memory list, made again when the image's address or size
    changes and after the sky's set-up (the script op `+$30bc`). Checks: with `MAPCHECK`
    the copy equal to the image at all 87 drawings of 500 fields turning and 67 walking
    (the map's and the shade table's copies still made); `tools/rr_skycheck.py` with every
    other case from the copy, 1,000 cases (a control with a stale copy taken as current
    differs at its first); the setup core's start and end screenshots pixel-identical to
    step 11's. Measured at 400 MHz: 445 frames against 367 (44.5 fps, 22.5 ms), the sky
    4.0 → 0.1 ms a frame, chip accesses 13.8 → 9.9 ms (18,351 → 13,980 a frame), busy 20.4
    → 16.5 ms, the world wait 5.8 → 4.8 ms; turning, 23 world passes and 42 frames between
    them in 66 fields, shown a field apart 62 times and 2 fields once. The estimate
    (INFERRED) was under 1 ms. On the aprof core 129 frames against 122 (12.9 fps, 77.5
    ms), chip accesses 14.3 → 10.4 ms, the sky 0.8 ms; on the setup's core 165 against
    166, both at the cap.
13. **The objects' images in fast memory** (done, `docs/internals.md`, "AGA
    improvements"). The scaled sprites' pixel reads (hunk 1 `+$eb5c` [`$13008`] and
    `+$ec88` [`$13134`], `move.b (0,a0,d0.w),d2`) go to the objects' images, which are not
    in MAIN's 256 KB block (`$14c950`-`$18c950` in the jungle) but in the resource heap
    (the reads at `$bfc44` and `$c148b`), with the sounds Paula plays: 23 images, 33 KB, in
    27 fields of the walk. The routine now reads them from a cache of copies in fast memory
    (64 KB, up to 128 images), found by the image's address and emptied when the heap's
    top changes (an allocation, a compaction, a reset) or the cache is full. Checks: with
    `MAPCHECK` every copy given equal to its image, 1,421 calls turning and 1,297 walking
    (32 and 28 images, 52 and 44 KB; the sky's, the map's and the shade table's copies
    still made); the setup core's start and end screenshots pixel-identical to step 12's,
    166 frames. Measured at 400 MHz: 480 frames against 445 (48.0 fps, 20.8 ms), the
    objects 1.4 → 0.1 ms a frame and the cache 0.1, chip accesses 9.9 → 8.7 ms (13,980 →
    12,353 a frame), busy 16.5 → 15.3 ms, the world wait 4.8 → 4.4 ms; turning, 22 world
    passes and 43 frames between them in 65 fields, every frame shown a field after the
    last. The estimate (INFERRED) was 1.8 → about 0.2 ms. On the aprof core 130 frames
    against 129 (13.0 fps, 76.9 ms), chip accesses 10.4 → 8.8 ms, the objects 2.0 → 1.1 ms
    and the cache 0.2.
14. **The rest of a frame's chip time** (examined, not done). After 12 and 13, at 400 MHz
    (step 13's run, 480 frames, keypad 9 held), 8.7 ms a frame in chip accesses (12,353, 0.70
    µs each on average). By routine, per frame, and why it stays:

    | Chip time | ms/frame | Accesses | Why it stays |
    |---|---|---|---|
    | the conversion's plane writes (`c2p030_pass1`, `_pass2`) | 5.2 | 8,064 | the planes themselves, a floor while the CPU writes them |
    | the copper wait, hunk 0 `+$13c0` [`$13ec`] | 1.1 | 1,695 | polls: the pass's first access to the back screen waiting for the swap to show (step 10.2), not work |
    | the pointer: its background saved and the pointer drawn (hunk 2 `+$1b4` [`$16ce8`]), the background put back twice (`+$4ec` [`$17020`], from hunk 1 `+$4a46` and `+$519c`) | 0.7 | 1,036 | the planes' own words under the pointer, read and written in place |
    | the CPU waiting for the blitter, in hunk 2's blit routines: `+$5b6` [`$170ea`] (a panel strip, x 208-255, y 141-147 turning, copied from the shown screen to the back one), `+$dc0`, `+$1256` and `+$1f00` (a rectangle filled) | 0.7 | 326 | the blitter's own time on the planes, one plane at a time; the polls are the CPU idle |
    | reads of the resource heap: objects' headers (hunk 1 `+$a7d4` [`$ec80`], 22 calls), the scripts' bytes (`+$7b74` [`$c020`], `+$25e4` [`$6a90`]), the cells' objects' headers (`+$d712` [`$11bbe`]), the 2D objects' headers (hunk 2 `+$20fc` [`$18c30`]) | 0.7 | 721 | five routines of 0.03 to 0.3 ms; the heap stays in chip (the sounds, step 13) |
    | the map's row after its end, copied at every call (`_maprows`, step 10.2) | 0.1 | 129 | needed |
    | the rest (the landscape's two reads of the original map, the spans, ...) | 0.2 | 382 | each under 0.1 ms |

    The largest move to fast memory left, the objects' headers at `+$a7d4` through step
    13's cache (its five reads of the image's header, `+$a8ac` to `+$a94e`, from the copy
    the sprite routine then uses), would save 110 accesses, about 0.08 ms a frame
    (DERIVED: 0.70 µs an access); the scripts' bytes move with the heap's compaction. The
    pointer in longwords where its two words are aligned would save about a quarter of its
    0.7 ms (INFERRED). Neither is worth the patch: busy 15.3 ms a frame, the drawing passes
    0.61 to 0.99 fields turning, every frame shown a field after the last (step 13). On
    the aprof core (130 frames, 76.9 ms a frame) the same items are 8.8 ms, the blitter
    copy 1.0 ms and the scripts 0.7 ms there, as they run on every world pass and every
    frame is one; what decides that core is the CPU's work (step 15).
15. **The CPU's work**, for real CPUs. It does not decide the target: it scales with the
    clock.
    1. An equivalence check for the AGA landscape first, which every item below needs:
       `tools/rr_snap.py` and `tools/rr_ecsland.py` for the AGA game (snapshots at hunk 1
       `+$d88c` [`$11d38`], Unicorn as a 68030, all memory compared).
    2. The loop's stores, 3.9 ms a frame on the aprof core: `<+$d888>` (`+$da70`, 1.0 ms,
       read only after the loop at `+$de4a`), `<+$a21e>` (`+$db3e`, 0.8 ms, read only by
       `+$d712`, 11 calls a frame, and equal to `-604(a1)` there), `clr.w <+$d86e>`
       (`+$db88`, 0.6 ms, set only at `+$e0d6`) and `<+$a220>`
       (`+$db22`, 0.6 ms, read by `+$d712` and after the loop) can be written only where
       they are read. `<+$a226>` (`+$db8e`, 0.9 ms) is the previous row, read by every
       span call, and stays. About 2 to 3 ms (INFERRED).
    3. The 68020's scaled index for the row table (`movea.l (a2,d6.w*4),a0` instead of
       two `add.w` and `(0,a2,d0.w)`) and `lea (a0,d7.w*2),a0` for the two `adda.w`:
       about 1 ms (INFERRED).
    4. The loop's path within the 68030's 256-byte instruction cache. The path is about
       330 bytes with two cold blocks inline (`+$da02`-`+$da58`, `+$dab2`-`+$db08`);
       moved out of line, it may fit. Not estimated: to measure.
    5. The spans and their set-up (20 ms): examined after item 1; no change identified.
    6. On the 040 and 060, Kalms' 040/060 conversion instead of the 030's.

Not planned: running the scripts more often in smaller steps. The engine has no step
length: each object runs every period and its script moves it by its own constants (the
player 7 to 9 whole degrees a turn, two collision-checked sub-steps a walk). Smaller steps
would mean rewriting those constants and every per-run counter in `heros` and in every
creature's program in every level, with headings in whole degrees (a quarter of 9 degrees
has no value), for the picture step 8 gives less one run of lag.

ECS, from 666.7 ms (1.5 fps), far from both caps on a 7 MHz 68000:

1. **A merge chunky-to-planar** (done, `docs/internals.md`, "ECS improvements"): the
   game's loop (hunk 2 `+$1a62`) shifts one bit at a time with `add`/`addx`, about 40
   cycles a pixel. The chunky bytes carry the dither (pixel 4n+j is the high nibble of its
   byte for an even j, the low one for an odd j), so a merge conversion cannot start from
   packed nibbles as Kalms' `c2p1x1_4_c5_gen` does: each pair of chunky longwords is first
   packed into one (a 4-bit exchange and a byte select, about 11 cycles a pixel), then four
   exchanges (8, 1, 16 and 2 bits) give the plane words; about 32 cycles a pixel in all,
   not the 18-22 estimated. `tools/rr_ecsc2pcheck.py`: 3,000 random rectangles
   byte-identical to START's loop; the walk's first screenshot is pixel-identical to
   v1.2's. Measured: the conversion 182.6 → 138.9 ms, 15 → 17 frames (588.2 ms).
2. **The sky by unrolled longwords** (done, `docs/internals.md`, "ECS improvements"): the
   row loop (hunk 1 `+$c8b8`) copies a word at a time with `move.w (a0)+,(a1)+` and `dbf`,
   22 cycles a word; a jump into 80 unrolled `move.l (a0)+,(a1)+` takes 10.
   `tools/rr_skycheck.py ecs`: 2,000 random cases identical to START's loop. Measured: the
   sky 25.8 → 13.9 ms per frame, the mean frame interval 596.3 → 578.2 ms (17 frames
   either way).
3. **Column set-up** (examined, not done): the per-instruction profile of step 2's run puts
   the function's 122.6 ms in the loop over a row's far samples (hunk 1 `+$c010`-`+$c202`,
   966 samples a frame, about 900 cycles each: the near row's walker `+$c028` 38.7 ms, the
   far sample `+$c0ee` 40.0 ms, the rest 27.9 ms) and 14.3 ms in the 55 rows' set-up, of
   which its three divisions a row take 3.3 ms. The loop holds all fifteen registers (two
   map walkers and their steps, the screen x and its step, the map's row table, the
   projection table, the variables' base), so its 25 or so memory operands a sample cannot
   move into registers without spilling others. What can go without registers: the clear
   of `+$bec4` on every sample, needed only after an object's column (20 cycles, 2.7 ms),
   and a reload of `-604(a1)` in its min/max (about 10 cycles, 1.4 ms); reciprocal tables
   would save under 2 ms of the divisions and change their rounding. About 4-6 ms in all
   (DERIVED: the 68000's cycle counts times the profile's counts), 1% of the frame, for a
   second copy of the game's loop: not done.
4. **Span set-up and clipping** (examined, not done): hunk 1 `+$9d54`-`+$a4ff`, 95.9 ms
   over some 200 basic blocks, the largest `+$a0e2` (13.4 ms, register code already). The
   call from the column loop (`bsr`, `movem.l d4-d7` both ways, `rts`: 118 cycles, 503
   calls a frame, 8.4 ms) has to stay: d4-d7 are the caller's map walkers and the span code
   needs four registers of its own; the entry's checks (`+$9d54`-`+$9de6`, about 20 ms)
   compare against variables that change between calls. A few milliseconds at most: not
   done.

On the A500, stop there: the code that is left is register-bound (the landscape), unrolled already (the
fills, 65 ms) or small (the objects, 41 ms, and the logic), each a rewrite for a few per
cent. The conversion is the largest item (143 ms, 25% after step 2): the blitter, idle, could
take its last exchanges in parallel with the CPU (planes and an intermediate buffer in chip
memory). Beyond that, fewer pixels (the LOW detail and window settings), not code.

`tools/rr_snap.py` and `tools/rr_ecsland.py` are the check any patch to the landscape needs:
snapshots of the machine at its entry (hunk 1 `+$bee2`) in the walk, then the landscape run
from each under Unicorn as the game has it and patched, all memory compared. An equivalent
test patch at `+$c010` came out identical on four snapshots and a one-operand change did not.

ECS on a fast CPU, to 50 fps. The figures above are the A500's. On the AGA's CPU
(`a3000-50`: `a1200-030`'s 50 MHz 68030 and 8 MB of fast memory on ECS; aprof,
`--uae_mmu_model=0`) the ECS game draws 57 frames in the window (the landscape's calls; the
swap, hunk 0 `+$cbe`, runs 102 times, on passes that draw nothing too), where the AGA game
draws 122 on the same core. The frame routine idles in its cap wait (hunk 1
`+$30a6`-`+$30c6`, 29.9 ms a swap), and of the 98.0 ms a swap 49.2 are chip accesses.
At 400 MHz it draws 53: the frames come on the player's runs whatever the CPU. Chip
accesses then take 52.8 ms a swap, about 87 ms for each frame drawn (DERIVED, less the
beam wait's and the copper-interrupt wait's), against the AGA's 13.7. The landscape is 97%
chip (13.6 ms a swap), the conversion 94% (5.0), the sky 3.7, the spans and fills (`+$9e34`,
`+$b12e`) 5.0, and the blitter copy of the view (hunk 2 `+$34e` [`$1495e`], 3.3 ms) has the
CPU wait for the blitter. So the ECS game is behind for the two reasons the AGA's steps
1-3 and 7-10 removed there: all its data is in chip memory (the slave gives 1 MB of chip
and 256 KB of ExpMem, as the AGA's v1.2 did), and it draws only on the player's runs.
Measured with `tools/rr_prof.py`'s search for START widened to the 8 MB (step 5) and the
frames counted from the profile's calls. The A500 path (68000, no fast memory) stays as it
is, each step below chosen at install; on 68020 and up with fast memory nothing waits for
the blitter.

5. **Tools for the ECS game on fast machines**: `tools/rr.py`'s search for START over the
   machine's fast memory (the A500's 2 MB ends at `$400000`, the `a3000-50`'s 8 MB at
   `$a00000`; gdb's `find` gives no match past the end); a frame counter in the ECS
   `profile` build, as the AGA's; `tools/rr_passes.py` and `tools/rr_objects.py` for the
   ECS game.
6. **The AGA's sites in the ECS game**: both STARTs are the same program at other offsets
   (the ECS swap, hunk 0 `+$cbe` [`$cee`], is the AGA's `+$13e0` instruction for
   instruction). Each AGA patch's checked bytes find its ECS site, giving a table of both
   variants' sites, each checked as now.
7. **Memory, 68020 and up with fast memory**: START's fast pool kept with a 1 MB ExpMem
   when the machine has it (WHDLoad's optional ExpMem, a negative size, or a setting like
   the AGA's `MemConfig`), as now without it; caches on with `CACHECHIPDATA`; the chunky
   buffer, the renderer's tables and the longword table in fast memory; the map and shade
   table copies (AGA steps 1-3, 10b and 10c). Estimate: from about 87 ms of chip accesses a
   frame toward the AGA's 14 (INFERRED: the same data on a 16-bit chip bus).
8. **68020 code without the blitter**: a conversion for the 68020 and up from the
   chunky buffer in fast memory with longword plane writes (`c2p000.s`'s packing of the
   dither, then the exchanges; Kalms' 4-plane conversions cannot start from the dithered
   bytes, step 1), the sky copied from fast memory, and the view's blitter copy (`+$34e`)
   started without waiting: the blit runs while the CPU draws into the fast chunky
   buffer, with a wait only before the conversion writes the planes. Chosen at install
   from `AttnFlags`; the 68000 keeps today's code.
9. **The world on the cap's grid and frames between the player's runs**: AGA steps 7, 8,
   9 and 10a through step 6's sites, then 10d, the swap without the beam wait (7.1 ms a
   swap at 400 MHz).
10. **To 50 fps**: AGA steps 11-13 (frames between world passes, the sky and the
    objects' graphics in fast memory; step 14 found nothing more worth moving), shared
    code where the variants allow.
11. **The A500 path**: what helps only the 68000 without fast memory: the conversion's
    last exchanges on the blitter, in parallel with the CPU (the blitter is idle there,
    0.1% of the DMA slots), and steps 3 and 4's few milliseconds.

## Reproducing

```sh
# AGA, aprof core (one capture at a time per repository)
BUILD=profile APROF=1 FSUAE=$FSUAE_APROF EXTRA_ARGS=--uae_mmu_model=0 \
    python3 tools/rr_prof.py tmp/prof/base-aprof
# AGA, the setup's core: frames only
BUILD=profile FSUAE=$FSUAE_ARM python3 tools/rr_prof.py tmp/prof/base-arm
# ECS (v1.2's figures: BUILD=developer at commit a8bb6fbe)
VARIANT=RobinsonsRequiem SETUP=custom BUILD=profile BARTO=1 python3 tools/rr_prof.py tmp/prof/ecs
python3 tools/rr_report.py tmp/prof/base-aprof
# the chip floor ("AGA, to 50 fps"): the same with the 68030 at 400 MHz
BUILD=profile APROF=1 FSUAE=$FSUAE_APROF \
    EXTRA_ARGS='--uae_mmu_model=0 --uae_cpu_frequency=400000000' \
    python3 tools/rr_prof.py tmp/prof/aga-400
# ECS on the AGA's CPU ("ECS on a fast CPU"; after ECS step 5, which widens the search)
VARIANT=RobinsonsRequiem SETUP=a3000-50 BUILD=profile APROF=1 FSUAE=$FSUAE_APROF \
    EXTRA_ARGS=--uae_mmu_model=0 python3 tools/rr_prof.py tmp/prof/ecs-a3000
# the AGA game's drawing passes, frame intervals, the fields the frames show in, catch-up
# passes and frames between passes (gdb breakpoints, no profile; KEY=3e walking)
BUILD=profile FSUAE=$FSUAE_APROF EXTRA_ARGS=--uae_mmu_model=0 \
    python3 tools/rr_passes.py tmp/prof/passes
# the AGA game's objects and their intervals ("Objects' rhythm"; KEY=none standing,
# 3e walking; POSE=1 the poses; SLAVE=<a slave assembled without bsr _worldpatch> for
# START's scheduling)
BUILD=developer python3 tools/rr_objects.py tmp/prof/objects 300
# the AGA conversion and sky copy against START's loops (after make unpack)
python3 tools/rr_c2pcheck.py 2000
python3 tools/rr_skycheck.py 2000
# the ECS conversion and sky copy against START's loops
python3 tools/rr_ecsc2pcheck.py 3000
python3 tools/rr_skycheck.py ecs 2000
# the ECS landscape: snapshots at its entry in the walk, then each run under Unicorn
BUILD=profile python3 tools/rr_snap.py tmp/ecs/snap 4
python3 tools/rr_ecsland.py tmp/ecs/snap
```

The `profile` build is the current source, every step done so far; v1.2's figures are the
`profile` build at commit `a8bb6fbe`.
