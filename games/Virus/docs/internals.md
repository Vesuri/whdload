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
(`$70000` and `$78000` stored at its entry). `ws_ExpMem` asks for an optional 620 KB
(`$9b000`) for everything the CPU alone uses, the drawing buffer and, after them, the 132 KB
of frames between ticks' tables ([below](#frames-between-ticks)); WHDLoad gives fast memory
when there is some, else chip memory above the 544 KB, which the slave leaves unused.

## The frame

Offsets are into `Disk.1` (address - `$3b800`); data addresses below `$3b800` are absolute.
Everything runs in supervisor mode on one stack, which the main loop resets to `$4b546`.

- Two 320x184, 4-plane displays at `$70000` and `$78000` (8000 bytes a plane), with a
  copper list each (`$121e`, `$1242`). The level 3 handler (`$24f40`) serves the VBL and the
  blitter; level 2 (`$250a8`) reads the keyboard.
- The main loop (`$28a04`, entered at `$289fe` once per game or demo start) increments the
  frame counter `$c9f4` (cleared at the start), runs the simulation, the particles
  (`$2521c`: count `$c9ec`, list `$a2a6`, each moved, projected with `divs` and put into
  the depth lists with its plotter, such as `$1c08a` or `$1c0ce`; `$29eb2` is the terrain
  height, a sum of sines, for the ground), then the landscape renderer (`$29974`), the swap
  and the clear request.
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

## Drawing in fast memory

With the game moved, its main loop draws into a buffer in fast memory instead of the chip
back buffer, and nothing waits for the blitter. The buffer is a screen in the game's layout
(four planes of 8000 bytes, 200 lines; the 3D view from line 16, `$280`, 184 lines), in
ExpMem 4 KB after the moved block, with 32 KB after it for the renderer's writes past a
screen's end (what the 544 KB `ws_BaseMemSize` covers in chip memory). The game's own
pointers say where it draws: `$1006` the screen, `$100a` its view; `$100e`/`$1012` are the
two chip screens, and `$3ca08` says which is the back one (0: `$1012`, while the copper
list `$3ca1e` shows `$100e`; else `$100e`, the list `$3ca42` showing `$1012`).

- The main loop's swap (`jsr $1d58c` at `$28a38`): when the frame was drawn in the buffer,
  waits until the chip back screen has left the display (a VBL since the previous swap, the
  same point at which the original's clear could start), copies the buffer there, then
  swaps as the game does. The copy goes by rows (40 bytes, a line of a plane) and leaves out
  those that are zero in the buffer and already zero in that chip screen: a flag per row
  and chip screen, in ExpMem after the buffer, says which may be nonzero there; they are
  all set whenever the game draws in the chip screens itself. In the demo 89 to 521 of the
  800 rows are zero (the sky, the black below the landscape, empty planes). When the frame was drawn in chip memory (the first
  after the main loop's entry, or after the mode was left), swaps first and copies the new
  back screen into the buffer. Either way `$1006`/`$100a` then point at the buffer.
- The main loop's clear request (`jsr $1d4fe` at `$28a3e`) marks a clear due. It happens,
  by the CPU in fast memory (the view's four planes, only the rows that the last copy
  found nonzero: nothing draws into the view between the swap and the clear), at the next
  wait for the clear: the
  renderer's (`$29c7e`) or another of the game's (`$1d53e`, `$2a5e8`, `$2a722`, `$2c022`).
  The original's blitter clear starts at the next VBL, and the renderer waits for its end;
  the radar's bitmap (`$292cc`), the depth-tested particles and everything else drawn
  after the wait are drawn after either.
- The score draws into both screens through a pair of pointer swaps (`$1d5da`, from
  `$2a2f0` and `$2a302`). In the mode the first points the game at the shown chip screen,
  the second back at the buffer, and `$3ca08` changes as in the original; the buffer then
  carries the score to the other screen. In the demo this happens 93 times in 25 s, each
  of which left the mode before (two whole copies and a frame drawn in chip memory).
- Everything else that swaps (`$1d58c`), swaps only the pointers (`$1d5da`, out of the
  score's pair), requests a clear (`$1d4fe`, `$1d548`) first leaves the mode: the due
  clear, the buffer copied to the chip back screen (once hidden), the pointers back to it. The attract screen, the title, the wave and highscore screens
  therefore run on the chip screens as in the original.

Measured (tools/pace.py, the demo window): 37.8 to 46.7 fps on the a1200-030, 32.2 to
36.0 on the a1200-fast; Enhanced framerate at 25 Hz on the a1200-030 now draws 24.8 frames
a second of its 25.0 ticks. aprof on the a1200-030: of all time, 46.7% waits for the chip
back screen to leave the display (the frame is ready before the next VBL: the display's
limit), 25.2% is the copy to chip memory (about 5 ms a frame), 2.6% the CPU clear, 25.5%
the game.

The copy by rows, the score in the mode and the clear by rows, each added to the one
before (tools/pace.py, `CACHE`). The first four columns are from the window as it was then,
from the demo's start, whose 1250 fields held the fade-in and, at 50 fps, the demo's end:
47.6 fps there was the ceiling, a steady 50. The last is the window now, from the fade-in's
end until the demo's (it is 1189 ticks long), at most 1250 fields:

| Machine | Whole copies | Copy by rows | Score in the mode | Clear by rows | Clear by rows, window now |
|---|---:|---:|---:|---:|---:|
| a500+-020 (68020, 14 MHz, 16-bit chip bus) | 31.7 | 32.9 | 35.4 | 35.7 | 35.8 |
| a1200-fast (68020, 14 MHz) | 36.0 | 36.0 | 37.2 | 37.4 | 37.8 |
| a3000 (68030, 25 MHz) | 46.6 | 46.6 | 47.6 | 47.6 | 50.0 |
| a3000-50, a1200-030, a1200-040, a1200-060 | 47.6 | | | 47.6 | 50.0 |

Enhanced framerate at 25 Hz on the a1200-030, the window now: 25.0 drawn a second of 25.0
ticks (100.0%).

aprof, the copy's share of all time: on the a1200-030 25.2% (whole copies) to 14.6% by
rows plus 3.8% of whole copies on leaving and entering the mode, to 17.2% with the score
in the mode (the wait for the display 46.6% to 52.1%); on the a1200-fast 25.2% to 23.7%:
its chip writes halve, but there a 14 MHz 68020 spends nearly as long finding the zero
rows (the CPU clear is 6.9%, the game itself about 63%).

`DCACHE` (instruction and data cache) against `CACHE`, whole copies: no frame rate changes
(the window then: a1200-030, a1200-040, a1200-060, a3000-50 47.6, its ceiling, both; a3000 46.6 and 46.7); aprof on the
a1200-030 puts the wait for the display at 47.8% against 46.6%.

Checked: at demo tick 200 the game state is the original's (pointers, the unused clear
request and the patches apart); screenshots at the same ticks (600, 900, 1166, 1175)
match the original's; play through waves 1 to 4, game over, the highscore screen and a new
game drew correctly on the a1200-030.

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
| `$28b56` | a four-entry position queue (`$10e4`): the seeds push where they land (`$25e5c`), this moves it on each tick its head's map cell is empty or marked (bit 4), the flying fighters steer at its head | simulation |

The renderer writes no game state (tools/callwrites.py, Unicorn from a demo chip dump):
with the drawing left out of every other pass, 8 passes end in the same game state as 8
whole passes, except for the radar list, which the enemies append to every pass and only
the renderer resets. Its own scratch (`$1073-$1190`, `$1300-$16dc`, the polygon filler's edge
state at `$2c586`) is read by nothing else. The renderer also starts sounds: the low-fuel
warnings (25, 29 and 34, `$2937a`-`$294ce`, with a latch, `$3ca17`, so that 29 sounds once)
and sound 0 every 64 ticks while a type-11 tile is in view (`$297ca`). A pass that does not
draw does not start them. That holds for the demo. In play the renderer changes game state
in three more places:

- Visible burning tiles (map bit 4) spawn smoke every 8 ticks (`$2981c`, through `$25c7e`
  and the RNG).
- The attractor's lightning bolt (`$28182`) takes 9 RNG draws a drawn frame (`$282dc`).
- The object drawer tests every vertex it projects against the terrain height (`$2bd12`).
  For the ship's model (`$fe38`) it sets `$3ca0f` (`$2be3e`). The player routine crashes the
  ship on it at the next tick (`$2b15e`, the crash at `$2b432`); the player's own height
  test covers only its centre.

A pass that leaves the drawing out therefore changes the RNG's sequence while smoke or the
lightning is on screen. It would also leave out the ship's terrain test, so that a crash into
a slope came on the next drawn pass if the ship was still in it, or not at all: Enhanced
framerate runs that test itself on such a pass (below).

**Enhanced framerate** (CUSTOM1=1) runs one pass per tick at a fixed rate: a tick every
3, 2 or 4 fields (CUSTOM2 0, 1, 2: 16.7, 25, 12.5 Hz;
16.7 Hz, chosen by play, is the default: the list in `_config` and the table in `_start`), counted by a hook in the VBL.
A pass waits while it is early. When the next tick is already due too, it leaves out the
renderer, the swap and the clear request and only simulates; at most 3 passes in a row,
then it draws anyway. Such a pass resets the radar list as the renderer would, and runs the
drawer's terrain test on the ship's depth-list entry (`_shiptest`, the same vertices, matrix
and arithmetic as `$2bc1e`-`$2be3e`; a hook on the ship's store, `$2b250`, notes the entry),
so a contact still crashes the ship at the next tick. Behind by more than 16
fields, the time past that is dropped. The loop's entry (`$289fe`, after the title, a wave
screen, the game's start) and every paused pass restart the clock, so pauses and screens
between waves add no backlog. The attract screen's approaching ship (`$2a4e4`: 768 frames,
then the departure, each at most a field because of the clear) gets the same at a tick a
field. The death sequence (`$2b472`, after a crash: 51 passes of its own with the
particles, the objects, the renderer and the swap, then the next life or game over) gets
the same at a tick a pass, its last pass always drawn. The frame counter `$c9f4` still
counts passes, now ticks.

Input is the original's: the mouse position (accumulated by the VBL), the buttons and the
key table are read when a pass reads them, so catch-up ticks see the latest state. Fades,
sounds and the "press SPACE" waits are VBL-timed and keep real time.

The title shows while the game builds its tables, from its fade-in (`$2886c`) to its fade-out
(`$288fe`): 543 fields on the a500+, 166 on the a1200, 12 on the a1200-030 with `CACHE`.
In every mode the slave now holds it for at least 166 fields, the a1200's
(`TITLE`, `_title` and `_untitle`, below): the a1200-030 reaches the attract screen in 177
fields, as the a1200 does; the a500+ and the a1200 are unchanged.

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

The ship's terrain test on the passes that do not draw costs the a500+ at 25 Hz, in the
window now (tools/pace.py): 567 ticks and 262 drawn frames (10.48 fps) without it, 566 and
251 (10.04 fps) with it. Checked against the drawer: a check build ran both on every drawn
pass of the demo and of the scripted play (wander) on the a1200-030, lowering the ship's
entry by 0 to 2976 on every 32nd pass to make contacts; in 998 passes, 17 with a contact,
the two never differed.

Same game state at the same tick (tools/callwrites.py `compare`, captures at tick 200
against the original on the a1200-030): no byte of game state differs for the original on
the a500+, Enhanced off, Enhanced at 25 and 16.7 Hz on the a1200-030 and at 25 Hz on the
a500+ (which skipped drawing and dropped time on the way), and with the ship's terrain test
on the a1200-030 and at 25 Hz on the a500+. Tick 191 came after exactly
380 fields at 25 Hz and 570 at 16.7 Hz on the a1200-030.

## A 50 Hz tick

What a tick every field would take with the game's pace kept (each pass half of a 25 Hz
tick), read from the code; nothing of it is built. The CPU is not the limit: the simulation
calls, with the particles' projection, are about 9% of all time on the a1200-fast and 4% on
the a1200-030 in the demo window (aprof). The limit is that the game is written per tick, in
integers:

| What | Where (`Disk.1`) | At half a tick |
|---|---|---|
| Positions, `pos += v` | the particles' dispatcher `$25248`, the player `$2b136`, about 16 sites in the object handlers | `v>>1` and `v-(v>>1)` on alternate passes sum to v exactly, v kept in 25 Hz units |
| Gravity `$c9ea` (3 to 6 by wave, `$26624`) | 9 particle and 6 object handlers, the player `$2b140` | `g>>1` and `g-(g>>1)` alternately |
| Drag, `v -= v>>k` (the player 6, `$2afc2`; fighters 5, chasers 6, seeders and the missile 4) | | one more shift keeps the retention (within 0.1%) but not the dead band: a positive speed under 2^k never slows and `asr` takes a negative one down a unit a tick; at k+1 the player drifts at up to 127 a tick instead of 63 and negative speeds decay twice as fast. Needs a fraction kept per velocity |
| Homing, `v += (target-pos)>>k` (`$285dc`, `$28600`, the chasers) | | as drag |
| Thrust from a matrix byte shifted 3 to 6 (the player `$2b00c`, the fliers `$2847c`, the missile) | | positive rows lose a unit or more (the player's `up>>3` of 15 becomes 7 and 7): fractions kept, or thrust on alternate passes |
| The attitude, half the way to the mouse's, at most 5120 (`$2af56`) | | `1-1/sqrt(2)` a pass is not a shift: a multiply, the clamp halved |
| Countdowns | the wave table's delays (`$265e4`, up to 3000 ticks), the seeders' 512, the chasers' reversals 511 and 169, stuns, the death sequence's 51 passes and its text at 16 to 19 (`$2b472`), the missile's life 256 in a byte | doubled, or counted on alternate passes |
| Amounts a tick | fuel: thrust 3 (`$2afde`), the attractor 25, refuelling 25 (`$2b3fe`); a point a shot; keyboard steering 1536 and 3072 (`$2aebe`); turns 1792 and 2 (`$2833c`) | halved, odd ones alternating |
| Gates on the counter's low bits | `$c9f4`: the spin matrices (`$2bafc`, `$2963c`), the dust every 2nd (`$2b33e`), the autopilot every 8th (`$2ace2`), the gauge's blink (`$293ae`), a sound every 64th (`$297b8`), the smoke every 8th (`$2981c`); `$c9f8`: about 12 in the object handlers; `$c9f5` bit 0: blinks and models | one more bit, or a 25 Hz counter and its phase |
| Emission | exhaust 5 a tick (`$2b04e`), a shot a tick (`$2b0ee`), the trail puffs (`$2b2d2`), seeds every tick (`$26eb0`), smoke, bombs, enemy shots, the bomber's 21 instant infections a tick (`$258b4`) | alternate passes; otherwise the 375-particle cap fills and drops emissions, seeds among them |
| Sounds started every tick | thrust, 5 and 54, which restart on each call (`$1ca58`, a positive flag word); 16, 22, 30, 37, 49 | alternate passes |
| Decisions | mutants, two-hit fliers and the missile steer every tick, one way or the other | on alternate passes, or they aim twice as finely |

That is on the order of 80 patch sites, and the game is then close to the 25 Hz one, not the
same: collision tests run twice as often, so fast shots that pass through objects, tiles and
ridges today hit (the player's shot moves up to about 576 a tick, the boxes are 320 and,
against the ship, 192); the RNG (`$101a`) is drawn in another order, so infections, spreads
and waves differ; and the demo is not a recording but an autopilot (`$2ace2`: every 8 ticks
it heads for the nearest object, it fires and thrusts by distance and terrain), so it plays
another game. Only 25 and 12.5 Hz are shifts of 50 Hz; 16.7 Hz is not. No comparison with the
original's state applies (tools/gametime.py), so only play could judge it.

Drawing between ticks gives the frames without any of that: see the next section.

## Frames between ticks

Frames drawn between two ticks, interpolated: on the fields between tick N−1's frame and
tick N's, the game draws what lies a fraction α of the way from N−1 to N. Enhanced framerate
always draws them when ExpMem is in fast memory; what is still open is in
[open work](open-work.md#frames-between-ticks). The game state stays as it is:
the frames between only read it, and everything the renderer writes is restored or kept
from happening, so the demo stays in sync and the state comparisons (tools/gametime.py,
tools/callwrites.py) still apply.

Interpolating, not predicting forward. Both ends are known, so every pose between them is
right: no frame shows a bounce, a landing or a hit before it happens. The cost is that tick
N's own frame is shown P−1 fields later than now (P fields a tick: 20 ms at 25 Hz, 40 ms at
16.7 Hz, 60 ms at 12.5 Hz). A forward prediction (`pos + α·v`) would add no delay, but
tools/pairs.py's first version measured it: the ship's velocity changes every tick (thrust,
drag), so the predicted camera was off on 99 of 99 ticks of the demo by 1 to 17 units, and
the whole landscape would step back at every tick.

**What the renderer draws.** The depth lists are 10 buckets of 3276 bytes at `$16ac-$96a3`,
256 units of depth each:

- `$29594` holds each bucket's write pointer and end, and `$295e4` its start and end;
  `$29574` copies the second over the first after the renderer.
- An entry is a plotter's address followed by its data.
- The renderer (`$29cc2`) draws the buckets far to near, between the landscape's rows. It
  calls each plotter with a5 at its data and only reads the entries.
- The simulation fills the lists before the renderer runs. The renderer adds the tiles'
  objects as it walks the grid, at its camera (`$107e`, the only camera it reads).

| Writer (`Disk.1`, store) | Entry | Its position |
|---|---|---|
| Particles, a dot (`$252a4`) | 8 bytes: plotter, x, y | on the screen, against the camera of the tick before |
| Particles, a dot and its ground dot (`$25312`, `$25348`) | two of 8 bytes | the same; the ground dot at the terrain under it |
| Particles, shards (`$253bc`) | 32 bytes: plotter `$2bbaa`, model, matrix (9 words), position | 3D, camera-relative |
| Objects (`$26dac`) | 32 bytes, as the shards | 3D, camera-relative |
| The attractor's lightning (`$27cdc`) | 16 bytes: plotter `$28182`, two points | 3D, camera-relative |
| The ship (`$2b250`) | 32 bytes, its matrix in `$1084` from the attitude | 3D, camera-relative |
| The renderer's tile objects (`$297d4`, stores `$29672`-`$29840`) | 32, 14 and 4 bytes | from the grid, at the renderer's camera |

**Pairing.** Each entry of tick N is blended with the entry its source made on tick N−1. The
source is a slot: a particle's in `$a2a6` (18 bytes a record), an object's in `$bd04` (20
bytes), for the lightning its object's, and the ship. Records move only in the two
dispatchers' removals (`$25406`, `$26e0a`): the last record is copied into the freed slot
and handled at once, so a slot's entry is the record's that had the slot at the end of the
last tick, but in the iteration right after a removal, where it is the last slot's. Nothing
else removes particles or objects (the only writes to their counts, `$c9ec` and `$c9ee`, and
list ends, `$102a` and `$102e`, are in the dispatchers, the spawns and the resets).
Measured with tools/pairs.py (Unicorn from chip dumps, the record as the next tick's
dispatcher finds it against the record at the source's tail): in the demo (1005 ticks) and
in play (two games started with SPACE, 298 ticks), no record changed between its tail and
the next tick's dispatcher, and the move rule pairs every source that existed on both ticks.
What pairs and what does not, in the demo:

| Writer | Sources | Paired | Unpaired: new (spawned during or after the dispatcher) |
|---|---:|---:|---:|
| Dot | 59122 | 96.8% | 3.2% |
| Dot and ground dot | 47420 | 89.9% | 10.1% |
| Shard | 255 | 96.9% | 3.1% |
| Object | 2106 | 99.6% | 0.4% |
| Ship | 1005 | 100% | |

The object handlers seen were 6 of the 18 (`$26eb0`, `$26fb2`, `$27094`, `$27382`, `$27426`,
`$27514`), and no lightning: neither run met an attractor.

How the pairs differ from one tick to the next (the demo; play alike):

- the dots move up to 64 pixels a tick, mostly 3 to 16; 47% change their plotter (their
  colour) and 22% their bucket;
- the 3D entries move up to 256 units against the camera; the camera itself 9 to 256;
- the objects' matrices are the spin matrix `$109c` (words up to 4096 apart, 1.0 being
  `$7ffe`), the identity, or their own (up to 8192); the shards' spin `$10ae` up to 16384;
  the ship's up to 16384, mostly under 4096; once an object changed matrix (32768 apart);
- a source changes writer (a dot that gains or loses its ground dot) in 1%.

**Blending.** For a pair of entries of the same size, at α = k/P:

- positions, word by word, `a + (b − a)·α` (dots: x and y on the screen; 3D: x, y, z; the
  lightning: both points);
- matrices word by word, unless a word moves more than 16384 (a change of matrix, not a
  turn): then the nearer tick's. Blending a turn of 30° shortens the axes by 3.4% at the
  middle, 0.2% at the common 7° (a word step of 4096);
- the plotter (a dot's colour) and the model from the nearer tick (α < ½: N−1);
- the bucket: 3D entries' from their blended depth, as the writers compute it
  (`(z − 2304) >> 5`, clamped to 0 to 72); the dots' and the lightning's from the nearer tick.

Unpaired entries are drawn as on their tick, on the frames nearer it: tick N's new ones
from α ≥ ½, tick N−1's ones with none on N (removed, or culled on N) below ½. The camera
(`$107e-$1082`) is blended as the positions, wrapping as words, so the landscape moves with
the rest; the renderer adds the tiles' objects at it.

**What a frame between ticks must leave as it was.** The renderer changes game state (see
[Game time](#game-time)):

| What | Where (`Disk.1`) | In a frame between |
|---|---|---|
| The camera `$107e-$1082` | | staged, then restored |
| The depth lists' tables `$29594`, `$295e4` | | pointed at the slave's staging lists, then restored; the game's lists are not touched |
| The RNG `$101a`/`$101e` (the lightning's 9 draws) | `$282dc` | saved, then restored |
| Smoke from burning tiles (a particle and the RNG) | `$2981c` | not spawned (the call skipped) |
| The fuel warnings 25, 29 and 34, their latch `$3ca17`; sound 0 | `$2937a`-`$294ce`, `$297ca` | not started (the five calls skipped); the latch restored |
| The ship's terrain contact `$3ca0f` | `$2be3e` | restored |
| The radar list's end `$1022`, `$1026` | `$29358`, `$29362` | restored |

Everything else the renderer and its plotters write is their own scratch: the ranges in
[Game time](#game-time), `$1072`, `$c704`, `$3ca06`, `$3ca0e`, `$3ca16` and `$1c088`. That list
comes from the call graph, read statically; a state comparison with the frames between on
and off checks it at run time.

**Where it goes.** In the main loop's pass (`_pass`), after the simulation and before the
renderer. Hooks at the 7 stores and the 2 removals record each entry: its key (particle slot
times 2 plus 0 or 1 for the ground dot, `K_OBJ`, `K_LIGHT` or `K_SHIP` plus the object's
slot), the key it had on the last tick, its bucket, size and place. A removal notes the slot
it fills and marks the last slot as moved away for the rest of the tick, so a particle
spawned there later pairs with nothing. After the simulation (`_btcapture`) the entries are
copied by key into one of two tables in ExpMem, tagged with the tick, the size and the
bucket; the other table holds the last tick's. The death sequence's passes (`_death`,
`_drender`) are ticks of their own and record and draw the same way; the main loop's pass
in which the ship crashed records no whole tick, so the death sequence's first pass draws no
frames between, and the main loop's entry (the next life) forgets the last tick. On the last
life the death sequence draws its text after the renderer from its pass 16 on; a frame
between draws it too (`_bttext`).

When the pass draws and the last pass recorded a whole tick (`_btframes`), for k = 1 to
P−1, while the tick's field plus k−1 has not gone: build the staging lists at α = k/P
(`_btbuild`), point the game's list tables at them, stage the camera and the counter `$c9f4`
(the nearer tick's: the renderer's blinks and gates follow it), run the renderer with its
sounds and smoke held back (`_btrender`), restore, then swap and request the clear as a
drawn pass does. Then the pass goes on as before: the renderer draws tick N's own frame.
The game's calls keep their order, and the copy waits for the display as before, so there
is at most one frame a field. In ExpMem: 32 KB of staging lists, two entry tables of 32 KB
(1024 keys of 32 bytes), their tags, the pairing marks and two lists of 1024 records.

**Checks.**

- The game state: tools/callwrites.py `compare` at demo tick 200 against the original's
  capture, with frames between ticks at 25 and 16.7 Hz on the a1200-030 and at 25 Hz on the
  a1200-fast (where some frames between are left out): no byte differs. At tick 1150, near
  the demo's end, none against Enhanced framerate without it. (Enhanced framerate against
  the original differs there in 3 bytes of the VBL's sound state, `$584d7-$584d9`, which
  keeps real time; at tick 200 in none.) Two places the frames between leave changed are
  the renderer's own and are left out of the comparison: the object drawer's polygon list
  `$c704-$c9bf` and its saved place `$103a` (written by the plotter `$2bb5a`, read by
  `$2bb96`).
- A check build (`BTCHECK`) draws every frame between at α = 0, nearer the last tick: its
  frames must be the last tick's own. On the a1200-030 in the demo at 25 Hz (29 ticks) and
  16.7 Hz (20 ticks, two frames between each), the 3D view was the last tick's frame pixel
  for pixel but for 2 dots of 4 by 2 pixels, where two dots of a bucket overlap and the
  staging lists draw them in another order. The panel's radar and gauges differ by a few
  pixels: they draw this tick's radar list and fuel, a field early.
- In play (a game started with SPACE, the a1200-030 at 25 Hz, the same input on the same
  fields: thrust and pitch until a crash, the death sequence, the next life), the game state
  at tick 3150 is byte-identical with frames between ticks on and off.
- Screenshots of consecutive fields show the landscape, objects and particles moving between
  their places of two ticks, the death sequence's debris too, and its GAME OVER on every
  field.

Measured (tools/pace.py, the window after the fade-in, 1250 fields; ticks against the
nominal rate, drawn frames a second, of them frames between ticks):

| Machine | Without | With |
|---|---|---|
| a1200-030, CACHE, 25 Hz | 100.0%, 25.0 fps | 100.0%, 50.0 fps (625 between) |
| a1200-030, CACHE, 16.7 Hz | | 100.1%, 50.0 fps (834 between) |
| a1200-030, CACHE, 12.5 Hz | | 100.2%, 50.0 fps (936 between) |
| a3000, CACHE, 25 Hz | | 99.8%, 49.6 fps (615 between) |
| a1200-fast, CACHE, 25 Hz | 100.5%, 24.8 fps | 100.5%, 39.0 fps (383 between) |
| a500+-020, CACHE, 25 Hz | 100.5%, 24.5 fps | 100.3%, 36.3 fps (323 between) |
| a500+ (no fast memory) | 90.6%, 10.0 fps | unchanged: not enabled |

On the 14 MHz 68020s a frame between fits on some ticks and not on others, so frames show
for one field or two in a mix.

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
| a1200-030, CACHE | 23.4 | 32.8 | 36.0 | 37.8; 46.7 drawing in fast memory |
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
| `$2886c` (the title's fade-in) | `jsr $62236` | `jsr _title`: the fade-in, then notes the field count |
| `$288fe` (the title's fade-out) | `jsr $621a6` | `jsr _untitle`: waits until the title has shown 166 fields, then the fade-out |

With CUSTOM1=1 (Enhanced framerate, [game time](#game-time)), a second patch list:

| `Disk.1` offset | Original | Patch |
|---|---|---|
| `$24ffe` (level 3, VBL part) | `move.b $3ca1b,d0` | `jsr`: counts the field, then the same |
| `$289fe` (the main loop's entry) | `jsr` to `$1d538` (clear and wait) | `jsr`: the same, then restarts the clock |
| `$28a12` (the main loop, after its top) | `tst.b $3ca07; bne.s` and the calls to `$28a4b` | `jsr _pass; bra.s $28a4c`: paused, restarts the clock; else waits for the tick, then the calls, the drawing only when not behind |
| `$2a530` (the attract screen) | `jsr` to `$26a36` (fade-in) | `jsr`: the same, then restarts the clock |
| `$2a584` (the attract screen's frame) | the ship's rotation, drawing, swap and clear, to `$2a5b1` | `jsr _attract; bra.s $2a5b2`: the same at a tick a field, left out when behind |
| `$2b250` (the ship's depth-list entry) | `lea $2bbaa(pc),a2; movem.l a2/a6,(a1)` | `jsr _shipemit; nop`: the same, and notes the entry for `_shiptest` |
| `$2b472` (the death sequence's pass) | `tst.b $609a2` | `jsr _death`: waits for the tick, then the same |
| `$2b47c`, `$2b494`, `$2b4e4` (its clear request, renderer, swap) | `jsr` to `$1d4fe`, `$29974`, `$1d58c` | `jsr`: the same, left out when behind (the radar list reset instead of the renderer); in fast memory the main loop's buffer swap and clear |

With ExpMem in fast memory as well (frames between ticks,
[above](#frames-between-ticks)), a third:

| `Disk.1` offset | Original | Patch |
|---|---|---|
| `$252a4`, `$25348` (a particle's dot, its ground dot) | `move.l d4,(a4); movem.w ...,4(a4)` | `jsr; nop`: the same, and records the entry |
| `$25312` (the dot of a dot and ground dot) | `move.l #$1c08a,(a4)` | `jsr`: the same, and records it |
| `$253bc`, `$26dac` (a shard's, an object's entry) | `lea $2bbaa(pc),a2; movem.l a2/a5,(a1)` | `jsr; nop`: the same, and records it |
| `$27cdc` (the lightning's entry) | `move.l #$28182,(a1)` | `jsr`: the same, and records it |
| `$2541e`, `$26e26` (a particle's, an object's removal) | the last record copied into the freed slot | `jsr` and `nop`s: the same, and notes the move |
| `$2937e`, `$293a8`, `$294bc`, `$294ce`, `$297ca` (the renderer's sounds) | `jsr` to `$1ca58` | `jsr`: the same, but not in a frame between |
| `$2981c` (the renderer's smoke) | `jsr` to `$25c7e` | `jsr`: the same, but not in a frame between |

The ship's store (`$2b250`, above) records its entry too, and the death sequence's pass and
renderer (`$2b472`, `$2b494`, above) start, record and draw its ticks the same way.

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
