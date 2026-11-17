# Internals

How the game loads, memory, every slave patch, how the program draws and keeps time, and
current measurements. Offsets are into the loader `data/Zany` (its first code hunk, $664
bytes, at file offset $58) or into `data/files/FILE1` (the main program, loaded whole at
$10000 on every machine tried, so its runtime address is $10000 + offset).

## Loading and memory

A WHDLoad v10 slave (flags `NoError`, `EmulTrap`, `NoKbd`), 512 KB base memory, an optional
72 KB ExpMem (ours, for the renderer's caches, "Display"), `ws_keyexit` $59 (F10). The slave
takes the ExpMem's address before it initialises OSEmu and clears `ws_ExpMem`, so OSEmu does
not give the memory to the game. It loads `OSEmu.400` from `data/` to $400 and initialises it, then
calls `dos.library` `LoadSeg` on `data/Zany` through OSEmu. The loader opens
`Zany:FILES/FILE1` and the other files through OSEmu's DOS emulation, all from `data/`
(`PRELOAD` holds them). The slave patches the loader's first hunk, then jumps to its start.

## Slave patches

The loader, first hunk:

| Offset | Original | Patch | Why |
|---|---|---|---|
| $48 | `jsr` (absolute, relocated) to the protection check | `bra.s *+4` ($6002) | skips the check; see below |
| $5a | `beq.w $ae` (check passed) | `bra.w $ae` (byte $60) | always takes the passed path |
| $62e | the drive routine (writes $ff, $87, $87, $ff to CIA-B PRB $bfd100) | `rts` | no disk access |
| $658 | `jsr (a3)`, a3 = `FILE1`'s address | `jmp Patch` | patch `FILE1` before it runs |

`Patch` takes WHDLoad's CRC16 over the 64 KB at a3 (`FILE1`) and aborts with
`TDREASON_WRONGVER` unless it is $9cc8. Then it patches `FILE1`:

| Offset | Original | Patch | Why |
|---|---|---|---|
| $1f38 | `move.w #300,d0; dbf d0,*` (the keyboard handshake delay, a CPU loop) | `nop; jsr FixKey` | a delay on the beam, and the trainer |
| $14a4 | the flip's `move.w d0,$2312(a4); move.w #$8000,d0` | `jsr FrameCap; nop` | ours: at most one frame a field, the flip off the copper's pointer loads ("Game time", "Display") |
| $14bc | the renderer's `move.l $1462(a4),d0; move.w $2326(a4),d0` (the back buffer) | `jsr Hidden; nop` | ours: no drawing into a buffer still on screen ("Display") |
| $5238 | the main loop's `LDA $0ea0; BEQ $524c` (threaded) | primitive $0138, `jmp Split` | ours: a world step each 6 fields, draw-only passes between ("Game time") |
| $1de2 | the input's `move.b $bfe001,d1` | `jsr ReadButton` | ours: a click between two steps is not lost ("Game time") |
| $14c4 | the renderer's tile redraw ($14c4-$15dd) | `jmp NewDraw` | ours, with ExpMem: only the cells that changed ("Display") |
| $173c | the shape drawer's `addq.w #8,a3; movea.l $32(a4),a0` | `jsr ShapeHook` | ours, with ExpMem: marks the cells a shape covers ("Display") |
| $7a9c | a game's start: the immediate of `LDY #0` (threaded), the position in the hole order | `CUSTOM1` | ours, debug, only with `CUSTOM1`=1-9: start on that hole (below) |

Then `Patch` flushes the caches and turns on the instruction cache for BaseMem
(`resload_SetCACR`). The game never changes its native code: FILE1 dumped at the title and
twice in play differs from the file only in data (the variables between routines, the
slave's own patches). The data cache stays off: every Amiga with a 68030 or later marks
chip RAM, where the whole game is, non-cacheable for data in hardware, and on a 68040 or
68060 a cacheable access to it is cancelled and restarted, several times slower (WHDLoad's
`cache.html`).

The slave header is version 17, for `ws_config`: the splash window's "Start on hole
(debug)" list sets `CUSTOM1` to 0-9, and `CUSTOM1=N` starts every game on hole N+1 instead
of hole 1, the windmill (for profiling the later holes). The game plays the hole files in
the order of the table at $bb02 (3, 8, 0, 9, 4, 5, 1, 7, 6, 2: hole 1 is `HOLE3`), with the
position in it at $bb23 and the hole file's number at $5c5a. A game's start ($7a86) sets the
position with `LDY #0` and loads the hole from the table; the advance after each hole is at
$99a4. The skipped holes score 0, and the game ends after hole 10 as before.

`FixKey` decodes the raw key the game pushed at $1f20 (from 4(sp)). On F10 ($59) it writes 9
to $15ca2 (`FILE1` $5ca2), the strokes left. Then it
waits for nine changes of `VHPOSR`'s line byte, about nine raster lines, in place of the
CPU loop. `Patch` then jumps to `FILE1` (with `jmp`, so the loader's `jsr` return address
is never pushed; the game does not return).

`bra.s *+4` at $48 lands at $4c, the low word of the `jsr`'s relocated address, not at
$4e after the instruction: the CPU executes that word as an instruction. It boots on a500
and a1200, so whatever that word decodes to is harmless at the address OSEmu loads to; it
has not been looked at.

## Keys

F10 is both `ws_keyexit` and the trainer key. WHDLoad checks the quit key on each interrupt
before the game sees the key, so with the default quit key F10 quits. The install package's
NewIcon sets `QUITKEY=$5D` (keypad *), which leaves F10 to the trainer; the Retroplay icon
does not. Not tested.

## The program

`FILE1` is 64 KB of code and data in one bank, addressed from a4 = $10000 (`lea $10000(pc),a4`
throughout). Most of the game logic is threaded code: a5 walks a list of 16-bit addresses in
the bank, and each primitive ends with `move.w (a5)+,d5; movea.l d5,a0; jmp (a0)` (d5's
high word is the bank's). The primitives ($0100-$0c2a) model a 6502/65816-style machine: d0
is the accumulator, d4 holds the result for the N and Z flags, d3's top bit the carry
(`roxr.b #1,d3`); `$05e8` calls a threaded subroutine, `$0602` returns, `$0492` and
`$04a0` branch on Z. Words in the data are little-endian (the native code byte-swaps them with
`ror.w #8`). All this fits a machine translation of the Apple IIGS original (an inference,
not documented anywhere seen). Native routines (the renderer, multiply and divide helpers
such as $2a04 and $2a3a, the shape drawer) are called from the threaded code and return
with `lea <next>(a4),a5; jmp $106(a4)`, the dispatcher.

The main code runs in user mode on a stack near $9570; the interrupts run in supervisor mode
on WHDLoad's stack near $7fff0, after WHDLoad's own entry in fast memory.

## Display

Four lores bitplanes, 40-byte rows, planes $2000 apart, two buffers: $40000-$47fff and
$48000-$4ffff. The copper list is in `FILE1` at $2272. Its playfield section holds the low
words of BPL1PT-BPL4PT at $231a, $231e, $2322 and $2326 (bit 15 picks the buffer), and
BPLCON1 at $2312.

The renderer ($147a, entered from the threaded code once a frame):

1. $14a8: flips bit 15 of the four pointer words, which shows the frame drawn last time, and
   writes the fine scroll to BPLCON1. There is no wait for a field. The copper list loads
   the pointers and BPLCON1 after its wait for line $4a and shows the playfield from line
   $52 to $f4 (DIWSTOP), so a flip on lines $4a-$f4 shows only from the next field, and
   until line $f4 the buffer the renderer now draws into is still on screen. The game took
   6 fields a frame, so its drawing seldom met the beam; at a frame a field it does, a
   plane at a time when the blitter copies (the flicker this slave had). `FrameCap` keeps
   the flip off lines $48-$4b (the copper loading some planes before it and some after)
   and writes BPLCON1 with the flip rather than before its wait, and `Hidden`, after the
   flip, waits for line $f4 to pass when the flip fell on lines $4a-$f4.
2. Draws the next frame into the other buffer from the tile map (pointer at $0eb4) at the
   view position ($0e9c x, $0e9e y, little-endian): 20 rows ($151e) of 40 tiles ($153a),
   each tile 8x8 pixels, 32 bytes at $21d0a + its map word (pointer at $146a), copied with
   32 `move.b (a2)+,d16(An)`, chip RAM to chip RAM. Then a partial 21st row ($15f2) when the
   view's y is not a multiple of 8.
3. The shape drawer ($16f2) then draws shapes into the same buffer (twice a frame in the
   measured window).

The game's renderer redraws all 800 tiles every frame, whether or not the view moved: on
the A500 that was 61 % of the CPU (`bench.py`, hole 1, the shipped renderer). Copying a
byte with `move.b (a2)+,d16(An)` is already the 68000's cheapest way, so the slave draws
fewer tiles instead. With ExpMem, `NewDraw` replaces the redraw (step 2):

- A cache per buffer (21 rows of 40 words in ExpMem) holds the map word each cell was last
  drawn from, and the view origin it was drawn at (x in 16-pixel steps, y in pixels). A cell
  is drawn only when its map word differs, two cells compared at a time. Map words are
  32-byte tile offsets, all even, so `$0001` marks a cell to redraw.
- When the origin moved since the back buffer was drawn, the blitter copies the other
  buffer (last frame's) into it, shifted by the difference: x moves in 16-pixel steps, so
  the copy is whole words, one blit a plane. The other buffer's cache comes along shifted,
  and the cells uncovered are marked. The game never uses the blitter (no write to its
  registers in FILE1). After the blits the slave flushes the caches (`resload_FlushCache`):
  with the data cache on, the shape drawer's `bclr`/`bset` would read stale bytes.
- `ShapeHook` runs at the shape drawer's start, walks the shape's rows with the drawer's own
  arithmetic (x steps, pixel-pair counts, the clip to lines 0-159 and pixels 0-319) and marks
  the cells it covers in the back buffer's cache. A shape drawn at fixed screen lines from
  $40000 (`$32` = $30000, the status line) that reaches line 33, where buffer 0's tiles
  start, drops both caches.
- The course pieces that change ($19ea, from $4fd0) change map words, which the compare
  catches. `Split` drops both caches whenever the drawing flag is clear or the interrupts
  are off (a hole may load).
- When the ExpMem is fast memory (not chip, not $c00000 slow RAM), the tiles are read from
  a copy of the hole block there (64 KB + 32, the reach of a 16-bit offset), made again when
  the block's address changes or the caches were dropped.

Without ExpMem the game's renderer stays. The verify build (`make build BUILD=verify`)
checks every cell of the back buffer against its tile in the hole block after every frame;
`development.md`, "Harness".

## Interrupts

Every interrupt vector ($64-$78) points to one handler at $21e6. It acknowledges VERTB and
COPER, and runs twice a field: at the vertical blank and at the copper interrupt the copper
list raises mid-screen (`move #$8010,INTREQ`). It flips a toggle at $21e2 on every run and
increments the field counter at $145c (low byte, then $145d) when the toggle returns to 0,
so the counter counts fields. Each run adds the mouse's counter changes (JOY0DAT) to
$1d54/$1d56, so no motion is lost however late the game reads them, and polls the keyboard
($1f0c, with the slave's FixKey patch). Once a field it runs the sound effects ($3642: four
channels of note durations at $2d92, written to Paula) and, while $126e is set, the music
sequencer at $40b8. Sound runs on real time; nothing in the handler moves the game world.
The counter stops while the game loads a hole, which it does with interrupts off.

## Game time

The world advances one fixed step for every frame the main loop draws: there is no
separate simulation rate, nothing waits for time, and the frame rate sets the game speed.

The main loop, threaded code at $5232 (`tools/thread.py 5232 5258`):

```
5232: MOVW $145c $0c50     stamp the field counter
5238: LDA  $0ea0           the drawing flag
523c: BEQ  $524c
5240: JSR  $4fd0           \
5244: JSR  $1478            > draw a frame (the renderer is $1478, native at $147a)
5248: JSR  $48d4           /
524c: JSR  $1d5a           input
5250: JSR  $62b2           the clock, then the current state's update
5254: JMP  $5232
```

$62b2 counts passes at $0e9a (16-bit), then advances the elapsed-fields sum at $5de4
(16-bit). With the drawing flag set it adds $11da, which is 6: a hole's start copies it
from a table of ten at $11dc, one a hole, all 6. With the flag clear it adds the fields
since the previous pass ($0c50 less the stamp it keeps at $6426). The clock at $5de6 is the
sum less an epoch at $6424, and about 35 places read it (animation phases and the like,
not traced one by one). Then $62b2 runs the state's update through the jump table at
$5bba, indexed by the state at $0ea8: 3 the title, 4 a hole's intro and play, 5 the pause
screen.

The flag is set while the title, a hole's intro and play are drawn. So in play the clock
moves by exactly 6 at every frame (measured: the real counter moved 4 or 5 fields between
frames on the 68030), and the game counts each frame as 6 fields (100 ms at NTSC),
however long it took. Entering the pause screen ($6548) saves the clock at $6684, sets
state 5 and clears the flag. Leaving it ($65be) adds the clock's advance during the pause
to the epoch and sets the flag again, so a pause adds nothing to game time.

The ball is updated once a pass, so once a frame. Within the pass it moves in smaller
steps: a per-field record catches it part way. It is object 0 of four in the table at $5c7a: x at $5c7a and
y at $5c82 (16-bit pixels on the course map), a velocity at $5c8a and $5c92 (signed, along
the course's diagonal axes), and subpixel fractions at $5cc2 and $5cca. Friction is applied
by frame count, not by time: the routine at $a988 decrements a per-object timer at $5cd2
once a frame. When it reaches zero, the routine reloads it from $5e26 (4) and subtracts one
friction step from the velocity, a per-surface amount from the table at $5dd8 (the surface
type at $5caa). Friction thus applies every fifth frame. A per-object accumulator at $5d12
adds the ball's speed every frame, and a minimum while the ball is at rest; its carry
drives the code at $ab26, not traced.

Measured with one putt on hole 1, `tools/route.py hole1 putt` (press, drag 48 right and 36
down, hold, release), NTSC, the shipped slave, 17.11.2026. The putt launches with the
same velocity everywhere. "Fields a frame" is the mean from the launch to the ball's
stop; game speed is 6 game fields a frame over the real fields a frame.

| Machine | WHDLoad option | Fields a frame | Game speed | Frames to rest | Rests at |
|---|---|---:|---:|---:|---|
| `a500` (68000, 7 MHz) | | 6.23 | 0.96x | 44 | 155, 227 (154, 229 with friction in phase, below) |
| `a1200` (68EC020, 14 MHz) | | 4.84 | 1.24x | 44 | 154, 229 |
| `a1200-030`, no MMU model | | 4.36 | 1.38x | 44 | 154, 229 |
| `a1200-030`, no MMU model | `CACHE` | 2.84 | 2.11x | 44 | 154, 229 |

The same putt took 125 fields with `CACHE` and 274 on the A500. At every frame
(`frametrack`, a breakpoint at the flip), the 68030 with and without `CACHE` had identical
object tables for 70 frames, at 13.5 and 21 frames a second. The A500's first difference
is the friction timer before the release, 4 against 3. The timer runs from the hole's
start, so its phase at the release depends on how many frames were drawn before it, and
from the putt's third frame on the A500 lost speed at different frames. Holding the
button 37 or 40 fields instead of 30 put the A500's timer in phase. Then the A500's object
table matched the 68030's at every frame except $5d12, which differed by a constant $80
gathered at rest before the putt, and the ball came to rest at 154, 229.

**With the world on its own clock** (ours): `Split` replaces the main loop's flag test at
$5238 with native code that chooses the rest of the pass. With the drawing flag clear, the
pass reads the input and steps ($524c), as before. With the flag set, a step is due each 6
fields by the game's counter: a due pass reads the input and steps only, and loops (the
step is not held up behind a frame, and a step that clears the flag is seen by the next
pass, as the game's own next pass saw it); the passes between draw only (`DrawOnly`, a
thread in the slave: JSR $4fd0, $1478, $48d4, JMP $5232). Those three are drawing only:
$4fd0 draws the course pieces that have come into view once (it clears their bit in $111a),
$48d4 builds the visible objects' draw list, $1478 is the renderer. What $4fd0 reads (the
view, the pieces, their bits) changes only in a step, so draw-only passes skip it after its
first run following a step. A step more than one
step late restarts the schedule, so a slow machine steps at most twice in a row and never
catches up in a burst; with the interrupts off (the counter stops) every pass steps.
`FrameCap` at the flip now only keeps the flips to one a field. The draw-only frames show
the last step's state again; interpolating between steps is open work.

The input routine reads the left mouse button from CIA-A once a step, its only read of it
($1de2), so a click shorter than 6 fields between two steps would be lost. Every pass polls
the button (`PollButton`, from `Split`), and `ReadButton`, in place of the read, reports the
other state from the one it reported last whenever a poll since saw it change: a click
reaches the game as a press at one step and a release at the next. Each step turns a press
edge, or any key, into a click event ($6462 sets $649a), so a click on the hole's intro can
carry over into play as a click and open the pause screen, or not, depending on where it
fell between two steps.

The putt (900 fields from the press, `track`) and hole 1 with the pointer moving and the
view scrolling (`frames 240 5 3`, and `frames 240 10 8 20` for more scrolling), NTSC,
17.11.2026, this slave with `Hidden` (no drawing into a buffer on screen; without it, which
flickered, the `a500` had 46.5 and 48.25 and the `a1200` 57.5 and 58.5 a second). Game speed is the clock's advance over the real fields; the "before"
column is the slave with the steps split but the game's renderer:

| Machine | WHDLoad option | Putt: frames a second | Game speed | Pointer moving | More scrolling | Before |
|---|---|---:|---:|---:|---:|---:|
| `a500` | | 36.6 | 1.00x | 37.0 | 37.5 | 9.25 |
| `a1200` | | 44.2 | 1.00x | 58.5 | 39.0 | 13.25 |
| `a1200-030` | | 60 | 1.00x | 57.0 | 60 | 14.75 |
| `a1200-030`, no MMU model | | 60 | 1.00x | 60 | 60 | |
| `a1200-030`, no MMU model | `CACHE` | 60 | 1.00x | 60 | 60 | 24.75 |

Steps run exactly 6 fields apart on both (a pass is now shorter than a field). Before the
renderer change the A500 held 10 steps a second by stepping twice before a frame when a
frame took more than 6 fields. The ball comes to rest at 156, 226 on the A500 and 155, 227
on the 68030: within a pixel or two of earlier runs, as the fields at which the steps sample
the mouse move with the schedule. The verify build found no cell differing from its tile on
`a500`, `a1200`, the `a1200-030` preset with `DCACHE`, `a1200-030` without the MMU model
with `CACHE` and with `DCACHE` (FS-UAE then caches chip data, so the flush after the blits is
exercised), and `a1200-040` and `a1200-060` with `DCACHE`: 120 to 1500 frames each, scrolled
frames among them.

Where the A500's time goes now (`bench.py`, scrolling, 38 frames a second before $4fd0 was
skipped between steps; and a trace of 60 fields with the view still, by threaded routine):
the threaded-code primitives 53 %, the slave's renderer 26 % (the cell compare and the tiles
19 %, the scroll copy with its blitter waits and the cache shift 7 %), the shape drawer 11 %
(it plots shapes pixel by pixel with `bclr`/`bset`). With the view still, a frame took 0.25
fields in the renderer, 0.16 in $4fd0 (now skipped between steps), 0.33 in $48d4's threaded
code (the object draw list) and 0.22 in the shape drawer it calls.

**The intended speed is 10 frames a second at NTSC**, 6 fields a frame: that is what the
game takes a frame to be. The stock NTSC A500 comes close and stays below it: hole 1 draws
at 6.2 to 6.7 fields a frame (9.0 to 9.6 frames a second), 90 to 96% of the intended speed.
Every faster machine plays the whole game fast in proportion to its frame rate: the ball,
friction, the clock and the animations it drives. The music and the sound effects do not
scale: they run on fields. That the 10 frames a second comes from the Apple IIGS
original is an inference, not checked. PAL has not been measured: play is counted in
frames either way, but the music would run at 50 fields a second.

## Measurements

The shipped slave's figures, the baseline (this slave's are in "Game time"). Hole 1 in play
with the pointer moving and the view scrolling, NTSC (60 fields a second, 16.7 ms a field),
the shipped slave, 17.11.2026. Frames are counted by `tools/zanygolf.py
frames 240 5 3` (flips of the plane pointer, no breakpoints; 240 fields, the mouse moving
5, 3 counts a field), the costs from `tools/bench.py` traces (120 fields), which need a CPU
without an MMU model: `a1200-030` with `EXTRA_ARGS=--uae_mmu_model=0`, the same 50 MHz
cycle-exact 68030 with WHDLoad running as it does with the MMU.

| Machine | WHDLoad option | Fields a frame | Frames a second |
|---|---|---:|---:|
| `a500` (68000, 7 MHz) | | 6.66 | 9.0 |
| `a1200` (68EC020, 14 MHz, chip only) | | 5.13 | 11.75 |
| `a1200-030` (68030, 50 MHz) | | 4.37 | 13.75 |
| `a1200-030`, no MMU model | | 4.42 (trace: 4.43) | 13.5 |
| `a1200-030`, no MMU model | `CACHE` | 2.84 (trace: 2.83) | 21.0 |
| `a1200-030`, no MMU model | `DCACHE` | 2.82 | 21.25 |
| `a1200-030` | `CACHE` | 2.79 | 21.5 |
| `a1200-030` | `DCACHE` | 1.77 | 34.0, not a hardware figure (below) |

The game runs entirely in chip RAM (its 512 KB BaseMem), and WHDLoad marks BaseMem
non-cacheable, which without WHDLoad's `MMU` option means both caches off. So every
instruction fetch and data access of the 68030 waits for a chip-bus slot: the 50 MHz 68030
is 17 % faster than the 14 MHz 68020. With the instruction cache (`CACHE`) the loops run from
the cache: 55 % more frames. The data cache cannot help on hardware, which refuses to cache
chip RAM; FS-UAE models that refusal only without an MMU model, so the `a1200-030` preset
with `DCACHE` caches chip data and its 34 frames a second are not a hardware figure.

Where a frame's time goes on the 68030 (fields of CPU per frame, from the traces; every
frame drew 800 tiles):

| | Caches off | `CACHE` |
|---|---:|---:|
| Frame | 4.43 (73.9 ms) | 2.83 (47.2 ms) |
| Renderer ($1400-$16ff) | 2.92 (66 %) | 1.85 |
| Threaded-code primitives ($0100-$0c2a) | 1.23 (28 %) | 0.84 |
| Everything else (native helpers, interrupts, WHDLoad) | 0.30 | 0.14 |

A tile costs 3063 cycles (61 µs) with the caches off: 32 byte copies, each a chip read,
a chip write and the code fetches (about 40 code fetches a tile on the bus). With `CACHE` it
is 1940 cycles (39 µs), the 64 data accesses alone, about 0.6 µs each. Chip-bus slots over
the window: CPU 41 %, bitplanes 22 %, free 35 % (a CPU access cannot use every free slot).
The CPU never idles: no `STOP`, no wait for a field.
