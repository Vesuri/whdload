# Internals

## How it loads

A direct slave (`ws_Flags` Disk and NoError, no Kickstart), a v17 header since 2.0b for
`ws_config` (`C1` Enhanced framerate, `C2` its game speed). It clears `$1000-$3b7ff`, loads
the whole disk image `Disk.1` (184320 bytes) to `$3b800`, so a `Disk.1` offset is its
address minus `$3b800`. With ExpMem in fast memory it copies `$1000-$687ff` there and
relocates it ([CPU-only data in fast memory](#cpu-only-data-in-fast-memory)). Then it loads the highscores, applies its
patch list (with CUSTOM1 also the Enhanced framerate patch list) to the code where it runs,
turns the instruction cache on (`resload_SetCACR`) and jumps to the game's entry, `Disk.1`
offset `$286c8` (`$63ec8`).

## Memory

`ws_BaseMemSize` is `$88000` (544 KB). The ReadMe's reason: the render routines write past
the 512 KB border. The game itself uses fixed chip addresses up to at least `$78000`
(`$70000` and `$78000` stored at its entry). `ws_ExpMem` asks for an optional 416 KB
(`$68000`) for everything the CPU alone uses; WHDLoad gives fast memory when there is some,
else chip memory above the 544 KB, which the slave leaves unused.

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

## What must be in chip memory

The only DMA the game uses: the two display buffers (`$70000-$7ffff`), the two copper
lists (`Disk.1` `$121e-$1265`: bitplane pointers only, no sprites), the audio samples
(`$1266-$a9df` and `$e832-$ed45`, from the table at `$1cc58`), and the blitter, for the
screen clear only (one `BLTCON0` write, `BLTSIZE` in the level 3 handler). DMACON is
`$87c0` from the start (`$287b4`) and only the audio bits change after it, so `BLTPRI` is
always on. Everything else is CPU-only: the code (`$57000-$687ff`, `Disk.1` `$1b800-$2cfff`),
the work memory at `$1000-$3b7ff` (variables, the two 64 KB landscape maps at `$1ca06` and
`$2ca06` reached through the pointers `$1032`/`$1036`, the slope table `$14b06`, the
particles), the rest of the image's data and the stack (`$4b546` down).

Moving the CPU-only parts means relocating a raw memory image: the program has no
relocation table (the end of the disk holds the start of the original executable's
`HUNK_RELOC32` block, `$2cac8` onward, cut off after 1336 bytes). In the 6288 instructions the 25 s demo executes there are 518 absolute
long operands to game addresses (306 to work memory, 140 to code, 72 to image data), no
absolute short ones, and 103 PC-relative ones (some reach data inside the code, as the
pointer variable `$1d4b2` read by `movea.l (pc),a2; jmp (a2)`). Code pointers also sit in
data: the span writers' pointer table at `$24920`, the sound table, particle records (built
at run time from immediates). The title, the attract screen, play and the wave screens run
code the demo does not, so a relocation needs a whole-image disassembly. The code area
and the data have been moved that way ([below](#cpu-only-data-in-fast-memory)).

Self-modifying code: the landscape setup (`$28bd8`, at the game's start and from `$26706`
and `$26728` by the wave number) rewrites five renderer instructions (`$29f7a-$29f85`,
`$2a050-$2a053`: shift counts and constants) when the landscape type (`$c9fe`) changes,
then builds the new map. It runs at the game's start too (`$c9fc` starts at `$ffff`).
Nothing flushed the instruction cache after it, and the original slave runs with it on; on
a 68020/030 the map building in between likely evicted the 256 bytes, on a 68040/060 not
necessarily. Since 2.0b the slave flushes at the setup's end (`$28cb6`, below). In a 10-field demo sample no other CPU write touched
an executed instruction word. The slave's patches are written before its `resload_SetCACR`
(`resload_Patch` flushes too).

## CPU-only data in fast memory

With ExpMem in fast memory (at `$200000` or above) the slave copies `$1000-$687ff` there as
one block: the work memory, the image's data, the stack and the code area (`$57000-$687ff`,
`Disk.1` `$1b800-$2cfff`, with the variables and tables mixed into it: the clear flag
`$606ac`, the key table `$60962`, the dispatcher's state `$58cb2`, palettes, the highscore
table). The DMA data in it stays in chip memory, at the same addresses: the copper lists
(`$3ca1e`, `$3ca42`) and the samples (`$3ca66-$461df`, `$4a032-$4a545`, from the table at
`$58458`), with the 15 KB of unreferenced sample-like data between them: `$3ca1e-$4a545`,
`Disk.1` `$121e-$ed45`. One distance for everything keeps every byte in one place: the code
reads some of its variables PC-relative (`movea.l $58cb2(pc),a2`) and writes the same ones
with absolute addresses, and it writes its own instructions (`$28bd8`) and some operands
(`move.l #$aaaaaaaa,$5d86c`). The stack (`$4a546-$4b545`, set by `lea $4b546,sp` at
`$28788` and `$28a0c`) moves with it. With ExpMem in chip memory (no fast memory) nothing
moves: the game runs as the original.

`tools/relocmap.py` disassembles the image recursively and lists every long that holds an
address in the block but for the chip data: 2718, written to `src/reloc.i` as distances.
Nothing in the work memory needs one (the slave clears it; the game builds its pointers
there from the relocated operands and tables). They are:

- absolute-long operands with a moved value (1407), and long immediates with one (75) but
  for the numbers among them (`IMM_NUMBERS`: masks `#$ff00`/`#$ffff`, `#$10000` (the second
  map's distance, 1.0, a digit flag), `#$1f40` (a plane's size), `#$1cc0` (a display
  offset's bound), 5000, 10000, 100000, 12345). `check` fails on an immediate it does not
  classify. No short absolute operand and no word immediate names a moved address, and no
  PC-relative operand leaves the block;
- the pointer tables: object and particle routines, the dispatcher's states (`$1d45a`),
  the span writers' bases (`$24920`, entered at an offset from them), the key table's
  pointers (`$24e36`), the 18-byte records' pointers (`$1c93e`), the dot masks
  (`$29d50`), the depth buckets' bases in work memory (`$29594`, `$16ac + k * $ccc`), the
  landscape objects' models (`$29874`, `movea.l $65074(pc,d3.w),a6`), and the waves' enemy
  lists (`$265e4`: records of five longs, the routine at +16, each list ended by a zero
  long), with the dispatcher's state variable `$1d4b2`;
- the object models' face pointers (915): 43 models fill `$4b548-$4d96f` (`Disk.1`
  `$fd48-$1216f`). A model is a flags byte, a byte, the vertex count - 1, the face count - 1,
  the faces' offset (8 + 6 * vertices), the vertices (three words), then faces of 22 bytes:
  the normal (three words), three pointers to the vertices' projections in the scratch at
  `$1104` (8 bytes each), the colour (a long). The parser fails unless the models fill the
  range exactly and every face points at one of its own model's vertices.

The walk starts at the entry, the code tables' entries, 114 entries that traced runs
executed (`tools/coverage.py`: the title, the attract screen, the demo, play to wave 4,
game over, the highscore entry, a new game, pause; executed PCs not reachable from other
entries: span writer entries, interrupt handlers, routines reached through registers) and
ten entries found by reading the unreached gaps (later waves' enemy states, fades, the
score digits, one fade nothing references). `relocmap.py check` fails unless every executed
PC is reached, no decoded instructions overlap, and every long in data (bytes no
instruction covers) with a moved value is a listed pointer or lies in a range read by hand
to hold only lookalikes (`NOT_POINTERS`: mask, trigonometry and font tables, bitmaps, the
18-byte records, texts, the highscore table, the original executable's `HUNK_RELOC32`
leftover at `$682c8`; the chip data).

The slave copies the block, adds the distance to each listed long and to its own eight
references (`_srel`), and fills the chip copy, but for the chip data, with `ILLEGAL`: a code
reference the table missed stops at once (that is how the waves' enemy lists were found to
need their own parser: the first relocated code stopped at `$62a00`, `$27200`, at wave 2).
A missed data reference would read the stale copy instead, so `tools/chipaccess.py` counts
the CPU's accesses to it: none in the demo. Its patch lists use offsets from `$57000` and
are applied at the code's address; its calls into the game go through a stub that adds the
distance (`GCALL`, `GJMP`).

Checked: at demo tick 200 on the a1200-030 the game state ($1000-$687ff as the game sees
it, `tools/gametime.py capture`) is the original's apart from moved pointers, every one the
original's plus the distance, and what is not game state (the depth lists, the stack, the
sound countdowns, the slave's patches). The demo, play from it through waves 1 to 4 (the
landscape change at wave 4) to game over, the highscore entry and a new game ran without
stopping on the a1200-030; the a500+ runs unmoved.

## Game time

The original steps its simulation once per main loop pass, that is once per rendered
frame. The VBL keeps no field counter (it reads the mouse and buttons, loads palettes,
counts down `$3ca1b` for the fades and runs the sound), and nothing in the loop waits for a
field except the clear. Checked (tools/gametime.py): at demo frame 200 the whole work memory
`$1000-$3b7ff` is byte-identical on the a500+ (68000) and the a1200-030, and the image area
differs only in dead stack bytes, the VBL's sound countdowns and the two slave patch
addresses. The 68000 reached frame 190 after 650 fields, the 68030 after 325: the demo plays
twice as fast on the 68030. Sound effect lengths are in fields, so they keep real time.

The main loop's calls (`Disk.1` offsets, from `$28a1a`):

| Call | Does | Kind |
|---|---|---|
| `$2bafc` | object rotation matrices from the frame counter `$c9f4` | animation, per tick |
| `$2521c` | particles: move, project, into the depth lists (`$29594`) | simulation, emits drawing |
| `$2af18` | the player and the camera (`$107e`) | simulation |
| `$26c9a` | the other objects; each appends itself to the radar list (`$1022`, from `$9ea6`) | simulation, emits drawing |
| `$29974` | the renderer: landscape, depth lists, objects, radar (draws the list, resets `$1022`) | drawing |
| `$29574` | empties the depth lists | drawing lists |
| `$26732` | the wave's end (pops the loop's return and jumps to `$28972`) | simulation |
| `$1d58c`, `$1d4fe` | the swap, the clear request | drawing |
| `$2a278` | the score, extra lives | simulation |
| `$28b56` | the ship's trail positions | simulation |

The renderer writes no game state (tools/callwrites.py, Unicorn from a demo chip dump):
with the drawing left out of every other pass, 8 passes end in the same game state as 8
whole passes, except for the radar list, which the enemies append to every pass and only
the renderer resets. Its own scratch (`$1073-$1190`, `$1300-$16dc`, the polygon filler's edge
state at `$2c586`) is read by nothing else. The renderer also starts two sounds (the
low-fuel warning, `$2937a`), so a pass that does not draw does not start them.

**Enhanced framerate** (CUSTOM1=1) runs one pass per tick at a fixed rate: a tick every
2, 3 or 4 fields (CUSTOM2 0, 1, 2: 25, 16.7, 12.5 Hz), counted by a hook in the VBL.
A pass waits while it is early. When the next tick is already due too, it leaves out the
renderer, the swap and the clear request (and resets the radar list as the renderer would)
and only simulates; at most 3 passes in a row, then it draws anyway. Behind by more than 16
fields, the time past that is dropped. The loop's entry (`$289fe`, after the title, a wave
screen, the game's start) and every paused pass restart the clock, so pauses and screens
between waves add no backlog. The attract screen's approaching ship (`$2a4e4`: 768 frames,
then the departure, each at most a field because of the clear) gets the same at a tick a
field. The frame counter `$c9f4` still counts passes, now ticks.

Input is the original's: the mouse position (accumulated by the VBL), the buttons and the
key table are read when a pass reads them, so catch-up ticks see the latest state. Fades,
sounds and the "press SPACE" waits are VBL-timed and keep real time. From the game's entry to
the attract screen (`$2a4e4`) the title shows for 159 fields on the a1200-030 and 567 on the
a500+: start-up work, not frame-tied, unchanged.

Measured (tools/pace.py, the first 1250 fields of the demo; ticks against the nominal
rate, drawn frames a second):

| Machine | Original | 25 Hz | 16.7 Hz | 12.5 Hz |
|---|---|---|---|---|
| a500+ (68000) | 12.0 fps | 90.7%, 10.5 fps | 96.7%, 11.6 fps | 100.2%, 11.0 fps |
| a1200 (68020, no fast) | 22.2 fps | 100.0%, 21.0 fps | | |
| a1200-030, CACHE | 23.4 fps | 100.0%, 21.9 fps | 100.3%, 16.3 fps | |

The A500 cannot hold 25 Hz in the demo's heavy scenes, where a drawn frame takes more than
the three skipped ticks give it, and comes close at 16.7 Hz. The attract screen took 813
fields on both the a500+ and the a1200-030 (the original: 49 more on the a500+).

Same game state at the same tick (tools/callwrites.py `compare`, captures at tick 200
against the original on the a1200-030): no byte of game state differs for the original on
the a500+, Enhanced off, Enhanced at 25 and 16.7 Hz on the a1200-030 and at 25 Hz on the
a500+ (which skipped drawing and dropped time on the way). Tick 191 came after exactly
380 fields at 25 Hz and 570 at 16.7 Hz on the a1200-030.

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

aprof over the same window (tools/aprof.py; same frame count, 586, and the same 31.0% in the
clear wait): CACR `$2011` (instruction cache and burst on, data cache off), and **97.7% of
the CPU's time is chip-bus access**, waits included; 96.9% without the busy-wait. Per group:
renderer own code 93.2%, objects 93.9%, particles 93.4%, edge stepping 99.5%, span writers
99.0%, the rest 99.4%. The 50 MHz 68030 runs at the speed of the chip bus.

What the CPU's chip slots are (tools/chipaccess.py, 10 fields from demo field 300): reads
in the code area 71.4%, of which the clear-flag polling (`$606ac`, which lies there) is
31.7% of all CPU slots; of all chip reads 43.0% are instruction fetches and 57.0% data.
Work memory 13.2%, image data 11.8%, display buffers 3.3% (2.2% writes, 1.2% reads). While
the blitter clears, the slots alternate blitter and CPU (35% each, bitplanes 27%, free 1%):
the D-only clear runs at its full rate of a word every other cycle, and the polls take only
the cycles it leaves, so they do not slow it.

With the code and data in fast memory (2.0b), the same window (tools/pace.py; frames a
second):

| Machine | Original | Code in ExpMem | Code and stack | Everything CPU-only |
|---|---|---|---|---|
| a500+ (68000, no fast memory) | 12.0 | 12.0 (ExpMem in chip) | | not moved |
| a1200 (68020, no fast memory) | 22.2 | 22.2 (ExpMem in chip) | | not moved |
| a1200-fast (68020, fast memory) | 22.2 | 25.4 | | 32.2 |
| a1200-030, CACHE | 23.4 | 32.8 | 36.0 | 37.8 |
| a1200-030, DCACHE | | | | 38.2 |
| a1200-030, CACHE, Enhanced framerate 25 Hz | 21.9 drawn | 24.7 drawn (100.2% of the ticks) | | |

FS-UAE's a1200-060 gives 47.6 with the original and with the code moved, so it does not
model what this changes. aprof on the a1200-030, everything CPU-only moved: the busy-wait
for the clear is now **68.7% of all time** (43.9% with the code moved, 31.0% originally); of
the rest, 38.3% is chip access, nearly all of it the span writers' (12.2% of all time, 84%
of it chip access: the display buffers). The CPU's chip slots (tools/chipaccess.py, demo
field 100) are the display buffers 96%, custom registers 3%.

## Slave patches

Offsets are into `Disk.1`. All are patch-list entries applied to the code where it runs
(the list's addresses are offsets from `$57000`).

| `Disk.1` offset | Original | Patch |
|---|---|---|
| `$250c0` (level 2 interrupt, after reading CIA-A SDR into d0) | `bset #6,$bfee01` | `nop; jsr _keyboard`: does the same `bset`, then quits on F10 (`ws_keyexit`) or the reset-warning code `$78` through `resload_Abort` |
| `$2b916` (highscore entry) | `move.w #3000,d7; cmp.w #127,d0` | `nop; jsr _savehi`: on key 13 (return) saves the table, then does the replaced instructions |
| `$28cb6` (the landscape setup's end, after the code writes and the map) | `move.w $c9fe,$c9fc` | `jsr _flush` and four bytes of `nop`: the same, then `resload_FlushCache` |

With CUSTOM1=1 (Enhanced framerate, [game time](#game-time)), a second patch list:

| `Disk.1` offset | Original | Patch |
|---|---|---|
| `$24ffe` (level 3, VBL part) | `move.b $3ca1b,d0` | `jsr`: counts the field, then the same |
| `$289fe` (the main loop's entry) | `jsr` to `$1d538` (clear and wait) | `jsr`: the same, then restarts the clock |
| `$28a12` (the main loop, after its top) | `tst.b $3ca07; bne.s` and the calls to `$28a4b` | `jsr _pass; bra.s $28a4c`: paused, restarts the clock; else waits for the tick, then the calls, the drawing only when not behind |
| `$2a530` (the attract screen) | `jsr` to `$26a36` (fade-in) | `jsr`: the same, then restarts the clock |
| `$2a584` (the attract screen's frame) | the ship's rotation, drawing, swap and clear, to `$2a5b1` | `jsr _attract; bra.s $2a5b2`: the same at a tick a field, left out when behind |

The highscore table is 280 bytes at `$2b62e` (`$66e2e`). `Virus.hi` holds it nibble-swapped
and inverted (`_crypt`, its own inverse); it is loaded at start when its size is 280.

`_clamp` (slave offset `$130` in the code hunk) is never called: it would clamp `a3` below
`$78b40` before an offset add, apparently an unfinished fix for the render writes past
512 KB that the larger `ws_BaseMemSize` covers instead.

The game handshakes the keyboard with a CIA-A timer B one-shot, so the handshake does not
depend on CPU speed.

## Limitations

- Needs more than 512 KB of chip memory (above).
- No blitter-wait fixes. The slave enables the instruction cache only and flushes it after
  the one self-modifying routine.
- Without fast memory nothing moves.
- Enhanced framerate fixes the game's pace, not its frame rate: the drawing is as slow as
  before, and catching up costs a little of it.
