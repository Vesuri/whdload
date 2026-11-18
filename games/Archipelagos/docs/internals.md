# Internals

## Loading

A direct slave (`ws_Version` 10, `WHDLF_NoError|WHDLF_ClearMem|WHDLF_EmulTrap`): 512 KB
base memory, no ExpMem, quit key F10, files from the `data` drawer. It installs its own
level 2 (keyboard) interrupt, sets the stack to `$800`, loads `Archipelagos_03FC00` (the
game's Atari ST format program, from disk offset `$3FC00`) to `$2000` and identifies it by
the CRC16 of the whole file: `$55BF` SPS 627, `$F600` SPS 628, anything else
`TDREASON_WRONGVER`. It applies the ST relocation table itself, patches the program and
jumps to its body, `$201C`, with A6 = `$DFF000`.

Every other load goes through the game's disk loader, which the slave replaces: the
loader's parameter block gives a disk offset and a destination, and the slave loads the
file `Archipelagos_<offset as six hex digits>`. A saved game is 512 bytes written to disk
offset `76*512*10` = `$5F000`, the file `Archipelagos_05F000`.

## Slave patches

Offsets are into the program body: a file offset of `Archipelagos_03FC00` minus its `$1C`
byte ST header (so at runtime `$201C` + offset).

The rows marked "68020 or better" or "body in fast memory", the body in ExpMem and the
instruction cache (`resload_SetCPU`) are the Enhanced framerate option, CUSTOM1 (the
installed icon sets it; `ws_version` 17 for the config string). Without it the slave runs
as on a 68000, with WHDLoad's caches; the other rows, game time included, apply always.
The harness sets CUSTOM1=1 (`game.conf`); `ENHANCED=0` runs without it.

| SPS 627 | SPS 628 | Patch |
|---|---|---|
| `$8E68`, `$8E72`, `$8E7C` | same | level 1, 5 and 6 interrupt handlers acknowledge twice and return |
| `$8D44` | same | keyboard: the slave's level 2 handler passes each key to the game, storing it at `$E33C` and jumping to `$E37E` (628 `$E390`, `$E3D2`) |
| `$8D6C`-`$8D76` | same | skip setting the level 7 vector |
| `$CEA2` | `$CECE` | the vertical blank acknowledge |
| `$A2C8`, `$A4DA`, `$A47A` | `$A2D4`, `$A4E6`, `$A486` | loader init, drive on and drive off return at once |
| `$9FD2`-`$A03E` | `$9FDE`-`$A04A` | the disk read: load the file named by the offset |
| `$12240` | `$124F8` | the protection track check returns at once |
| `$11512`-`$117CC` | `$1175A`-`$11A82` | the manual protection skipped whole |
| `$E4B8` | `$E50C` | "end level 2 interrupt code": returns at once; the slave's handler acknowledges the interrupt |
| `$C4AA` | `$C4BC` | the text writer's CPU loop: 58 times five raster lines |
| `$1118` | same | the replayer's DMA wait: five raster lines |
| `$1098C` | `$9E60` | save game to a file |
| | `$125CE` | the US "Fanfare" intro ends with the left mouse button |
| `$11AC6`-`$11AE5` | `$11D7E`-`$11D9D` | game time: the renderer's frame-counted steps, at most one every 6 fields ([Game time](#decoupled-srctimings-20b)) |
| `$11FA8` | `$12260` | game time: a move, interpolated over 48 fields |
| `$CD4E`; `$C5F2`, `$C60E` | `$CD7A`; `$C61E`, `$C63A` | game time: the effects' frames, until each step has had 6 fields |
| `$12220` | `$124D8` | the swap's end: it also measures each frame |
| `$CE92`; `$E494`, `$10BBA`, `$11884`, `$118B4` | `$CEBE`; `$E4E8`, `$10C9E`, `$11B3C`, `$11B6C` | the level 3 handler's self-modifying `jsr` (the pointer or the pan routine): it jumps through a slave variable, and the four writes of its target write that variable |
| `$12334`, `$1238C` | `$126D8`, `$12730` | the swap's copper-list writes: all interrupts off, and never in lines 0-2 or a frame's last three ([The frame](#the-frame)) |
| `$1185C` | `$11B14` | 68020 or better: the frame's second field wait skipped |
| `$11B72`-`$11BCD`; `$AE32` | `$11E2A`-`$11E85`; `$AE3E` | 68020 or better: draw view's two ground fills and the sky fill's five go into the slave's blit queue at draw view's start ([The frame](#the-frame)) |
| `$11EFA` | `$121B2` | 68020 or better: the blitter wait also waits for the queue, runs it when the interrupt cannot, and sets BLITHOG while the objects' blits run |
| `$CE1A`; `$CEA2` | `$CE46`; `$CECE` | 68020 or better: the level 3 handler starts the queue's next blit on BLIT, and its acknowledge leaves BLIT |
| `$B7F0` | `$B7FE` | 68020 or better: the CPU clears the border, after the objects' last blit |
| `$11E52` | `$1210A` | 68020 or better: the span drawer builds each row's 32 pixels of planes 0-2 in registers and writes them a long at a time ([The frame](#the-frame)) |
| `$11E0E` | `$120C6` | 68020 or better: the far rows' spans from carry to carry, not a pixel at a time |
| (install) | same | the instruction cache on for BaseMem and ExpMem, the data cache off (`resload_SetCPU`: `WCPUF_Base_WT`, `WCPUF_Exp_CB`, `WCPUF_IC`) |
| (install) | same | 68020 or better with ExpMem in fast memory: the body relocated to run there, DMA's data kept in chip ([Memory](#memory)) |
| `$AEFA`, `$B10E`, `$C8D8` | `$AF06`, `$B11C`, `$C904` | body in fast memory: the blitter's shape tables and buffer, which the game takes pc-relative, from the chip copy |
| `$8D44` (`.kbdcust`) | same | body in fast memory: the key handler's addresses follow the body |
| `$C636`; `$C77A` | `$C662`; `$C7A6` | body in fast memory: the title's pre-scaler scales each object from a fast copy of its source into fast scratch, then copies it to chip ([The pre-scaler](#the-pre-scaler)) |

## Memory

BaseMem is 512 KB of Chip RAM. The program image runs from `$201C` to `$16314` (SPS 628
`$166B8`), all text, no BSS, with 894 relocations (SPS 628 927), and mixes code,
variables, tables and data that DMA reads: the copper list (offset `$9976`, its address kept at offset `$8FE0`),
the sky's copper lists (tables at offsets `$99FA` and `$9A1A`, which the level 3 handler
puts in `COP2LC`), and audio samples (Paula reads offset `$3A10` in play). Fixed addresses
outside the image: the two screen buffers at `$5C780` and `$663C0` (40000 bytes each: five
320x200 planes, 8000 bytes apart), and the map, 64 KB at `$70000`-`$7FFFF`, which code
indexes from `$78000` with a signed word (256 cells a row; the low nibble is the terrain
type, bit 7 marks a cell with an object). The supervisor stack is the slave's, below `$800`
(the game uses `$724`-`$800`).

### The body in fast memory (2.0b)

The slave asks for an optional ExpMem of `$16000` bytes. On a 68020 or better that gets it
in fast memory (not chip, below `$200000`, nor slow memory, `$C00000`-`$DFFFFF`), the body
runs from there with the stack at ExpMem's top; otherwise (a 68000, no fast memory)
everything stays as it was. The relocation resolves each relocated long to one of two
copies of the body: the chip copy at `$201C` for a target in one of these blocks, the fast
copy otherwise. Both copies are relocated and patched alike, so they start out the same;
then the game runs only the fast one, apart from the replayer.

| Offsets (both versions unless given) | What | Why it stays in chip |
|---|---|---|
| `$0`-`$8D2A` | the replayer, its data and samples, and other data | Paula reads the samples (`$2C12`-`$4929`); the replayer addresses everything pc-relative, so it runs from the chip copy as a whole |
| `$8F50`-`$8F9C` | sprites | sprite DMA |
| `$8FFA`-`$9258`, `$9976`-`$99AC` | copper lists | the copper |
| `$B004`-`$B0A4`, `$B2CC`-`$B7EC` (628 `$B010`-`$B0B0`, `$B2DA`-`$B7FA`) | the blitter's shape tables | blitter sources |
| `$14076`-`$140F8` (628 `$1441A`-`$1449C`) | a buffer | a blitter source |

The blocks come from the trace's DMA records through every screen (`tools/smc.py`'s two
routes, both versions): every DMA read of the body is in one of them. A pc-relative
reference across a block's edge would reach the wrong copy; decoding every executed
instruction, and a linear sweep of the whole body, finds only five, the `lea`s that hand
the blitter its shape tables and buffer, which the slave patches to the chip copy. The
slave's own absolute addresses into the body follow it: the timing tables, the key
handlers and the US intro's check. With the body in fast memory nothing touches the chip
copy outside the blocks (`tools/cpuchip.py`) and no DMA reaches beyond the game's memory.
The slave leaves the running body's address at `$2012` (the ST header's reserved long) for
the tools.

### The pre-scaler

The title's PLEASE WAIT is the pre-scaler (`$C636`, SPS 628 `$C662`), called once at boot
(`$11490`). It scales each of the 36 objects, 48x48 pixels in the ST picture at `$70000`
(four interleaved planes, 160 bytes a row; the offset table at `$D3F6`), to 15 sizes (the
table at `$D1B2`, 20-byte entries: at 0 the size, at 4 the bytes a row of the four colour
planes, at 6 and 10 the colour and mask pointers, at 16 the bytes a plane-row), into the
blitter's object buffer, `$193B8`-`$5C780` in chip memory (the stride, `$1DE2` bytes an
object, at `$CF0A`; the objects' offsets at `$D122`; the object counter at `$12E62`). The
scaler (`$C724`) does it a pixel at a time: four word reads of the source and a
read-modify-write of five destination planes, the mask and four colours, all chip
accesses. With the body in fast memory the slave runs the same loops with the game's
scaler but points its source at a fast copy of the object's 48 rows and its destination
at fast scratch, then copies the object's stride bytes to chip with long writes. The
scratch is the fast copy's replayer area (body offsets `$1000` and `$3000`), which only
the chip copy runs. The buffer and every variable the routine leaves are identical to the
original's on the a1200-030 (both versions), a1200-fast and a1200-060
(`gdb dump` at the call's return). The call, by breakpoints: a1200-030 190 to 35 fields
(SPS 628 226 to 33), a1200-fast 369 to 320 (a 14 MHz 68EC020: now CPU-bound), a1200-060
102 to 103 (its core is not cycle-exact). Without fast memory it is unchanged: a1200
about 400 fields, a500 about 2000 (sampled).

The map stays in chip memory: 38 code sites address it absolutely and about 90 longs in
data point into `$70000`-`$7FFFF`, some of them other buffers there, against 464 chip
accesses a field in a pan with the body in fast memory (about 0.13 ms).

## The frame

Offsets below are SPS 627's (the `Archipelagos` variant). The game loop calls the frame
routine at `$117EA` once a frame:

1. the world update `$F6F6` (a tick, below);
2. the renderer `$11AC6`: the frame-counted steps (below), then a wait for the next field
   (`$11AE6`), then draw view `$11B72`, the sky fill `$AE32`, the objects (`$B0A4` and
   `$BEFA`, `$C8BA`, `$B7F0`);
3. a second wait for the next field (`$1185C`), then the swap `$12210`, which flips the
   back-buffer pointer (offset `$1286A`, `$5C780` or `$663C0`) and writes the five
   bitplane pointers into the copper list (`$12306`, with VERTB disabled).

The swap takes effect at the next vertical blank, when the copper reloads the list, and
the renderer's own wait (step 2) keeps it from drawing into a buffer still on screen.
The second wait (step 3) adds nothing to that and caps the loop at 25 fps: after it the
renderer's wait takes almost a whole field more, so a frame takes its work rounded up to
whole fields plus one. The move routine `$11FA8` (eight steps between two cells, each a
world update, a render and a swap, then a final frame on the cell) has only the renderer's
wait.

On a 68020 or better the slave skips the second wait (2.0b). A frame then takes its work
rounded up to whole fields: one field less than before, measured on every setup below. The
68000 keeps it, so the a500 runs as it did. A swap can now come at any line, as the move
routine's always could, and the copper reads the list's first ten moves (the pointers) at
the start of line 0: a write while it reads them would show planes from both buffers for
a frame. The slave makes the swap turn off all interrupts, not only VERTB, and wait out
lines 0-2 and a frame's last three (PAL 310-312, NTSC 260-262; it reads the beam position
twice, so a line change between `VPOSR` and `VHPOSR` is not taken for a line) before it
writes. That matters: on the a1200-030 the frame's work in a pan is close to two fields,
and without the end-of-frame lines a swap begun at line 312.9 wrote at line 0.1. Traced
over 300 fields with the guard, every write was at line 3 or later (line estimated from
the cycles into the field).

On a 68020 or better the blitter's fills run behind the CPU (2.0b). Draw view's two ground
fills and the sky fill's five (below) are constant fills of planes 3-4 of the ground and of
the sky, which the CPU's drawing (the ground's planes 0-2) never touches. The slave puts all
seven into a queue at draw view's start, and the blitter interrupt starts each next one, so
the blitter fills while the CPU draws the ground, and the sky fill returns at once. The
game's blitter wait, which every one of its blits calls first, waits for the queue too, so
every other blit still starts after the fills, as before. It also runs the queue itself when
the interrupt cannot (a wait at level 3, a BLIT request lost), and the game's level 3
acknowledge leaves BLIT to the slave. The border clear after the objects (`$B7F0`: bytes
36-43 of lines 20-179, the right border and the next line's left, which the objects' blits
overrun) is the CPU's now, two longs a line and plane, and the blitter's registers are left
as the game's last fill left them. And while the objects' blits run (from the sky fill to the
border clear) the wait sets BLITHOG: the CPU only polls `DMACONR` then, and without it the
blitter gives the CPU every fourth cycle of a four-channel blit. On the a1200-030, facing two
trees and two stones on archipelago 1 (`tools/timeline.py`, lines a frame):

| | 2.0b step 4 | with the queue |
|---|---|---|
| draw view | 196 | 210 |
| sky fill | 76 (waits) | 0 |
| objects | 65 | 51 |
| border clear | 35 | 15 |
| the swap at | line 63 of the next field (2 fields a frame) | line 280 (1 field) |

Draw view takes 14 lines more: the CPU's chip accesses share the bus with the fills, which
end well inside it (9584 blitter slots in 210 lines), so the objects' first blit does not
wait for them. The border takes 15 lines against the blitter's 24-40 with the CPU waiting.
BLITHOG is set only for the objects' blits, which are short. With it a CPU poll stalls until
the blit ends and an interrupt waits behind the poll, which the game's longer blits on other
screens would stretch to milliseconds.

Draw view: planes 3 and 4 of the ground (lines 113-179) by two blits; then, for each of
the 67 ground rows from the bottom up, the row's two edge rays across the map (`$11BD4`),
the map cells along the row (near rows by division, `$11D2C`; rows beyond the 45th with a
per-pixel loop, `$11E0E`-`$11E2C`) into a span list (offset `$13C26`), and the span drawer
`$11E52`, which looks up each span's terrain in the map, collects object cells, and fills
planes 0-2 through one of eight fill routines (table at offset `$1254A`, code from
`$1242A`, a `jsr` for each 16-pixel word). The view is 256 pixels wide (16 words from byte
4 of each 40-byte line), sky lines 20-112, ground 113-179.

On a 68020 or better the slave draws the rows (2.0b). A span list entry is a span's end x
and its map cell, a span runs from the last one's end, and the last one runs to the row's
end; the game's fill routines write a span's colour (the cell's terrain type, plane k bit k
of the type) from its start to its last word's end, read-modify-writing its first word in
chip memory, and later spans write over the rest. So a row is a function of its list: the
slave builds each 32 pixels of the three planes in registers and writes them once, 24 long
writes a row (the rows are long-aligned) and no reads, with one paint routine for each
terrain type. Object cells are noted and cleared in the map as the game does: a cell with an object joins the list (offset `$12F26`) the first time a span crosses it, up to row `$12892` (126, so not in the three farthest rows), and the object's size comes later from its screen line (`$B0A4`, table `$A5FA`); the lists at 80 frames of turning and moving, both versions, are step 5's. The far rows'
loop steps x a pixel at a time, adding a step to each of two 16-bit accumulators, a carry
ending a span: 256 steps a row for about 23 spans. The slave works out each carry instead:
the first one (65535 - acc) / step + 1 steps on, then, as the accumulator is below the step
after a carry, q = 65536 / step steps on, or q + 1 when the accumulator is below the
remainder, and the lists come out in the game's order. `tools/spancheck.py` runs both
routines and the game's against each other on 3000 random rows each, both versions, with no
difference in the screen, the map, the variables or the registers the game reads after;
the screens at twelve headings match step 5's pixel for pixel but for the creatures'
animation. Draw view on the a1200-030, facing two trees and two stones: 210 lines to 107.
The queued fills (above) then outlast it, so the objects' first blit waits for them: the
objects 51 to 98 lines, and the frame ends near line 226 instead of 280. On the a1200-fast
(14 MHz 68020) a frame's work went from 1.22 fields to 0.91 (`tools/bench.py`, 100 fields). The sky fill `$AE32` blits five
planes of lines 20-112 (plane 1 ones, the rest zeros), waiting for the blitter before each.
All waits for the blitter go through `$11EFA` (BLTBUSY in `DMACONR`).

The objects (`$B0A4`, `$BEFA`, `$C8BA` and the routines they call) are blits of all four
channels (A a column mask, B the shape, C and D the screen, minterm `$CA`), four bus cycles a
word, a plane at a time, the CPU waiting before each; scaled shapes repeat a 16-line source
in blits of 16 lines. Facing the two trees and two stones above, the objects make 45 blits
and 1860 words a frame. They take 51 lines (3.3 ms) of which 42 the CPU waits; the blitter
has 58% of the bus slots then, the rest going to the bitplanes (down to line 244) and the
CPU's set-up between blits. With nothing in view they take nothing, and the rest of the
frame does not change with them: on a fast machine they decide whether a frame fits a field.

## Game time

The level 3 handler (`$CE1A`, every field) counts fields in the long at offset `$12862`
and counts down the world tick (offset `$129B6`). It also changes the sky's copper list
on a field schedule, counts down offset `$CF16` while offset `$CF18` is set, applies the
mouse (`$E102` in pan mode, `$DEFA` for the pointer), reads the buttons (`$E296`) and
runs the music. So the clocks are:

| Clock | What runs on it |
|---|---|
| fields (the level 3 handler) | the field counter, the sky's colour changes, the `$CF16` countdown, pan turning (the mouse's X counts added to the heading, offset `$12880`, 0-719 half degrees, each field), buttons, music |
| world tick: every 6 fields, checked once a frame | the world update `$F700`: spawning near the player and other world events. It runs when the countdown is below zero and reloads it with 5 (offset `$129B4`), so it never runs more than once a frame and a late check loses the time it was late |
| frames | at the start of the renderer (`$11AC6`-`$11AE5`): one step of the blood spread (`$C99E`, below), the terrain animation phase (offset `$12DAC`, every 10 frames), two object animation timers (offsets `$12DB8`, `$12DC8`, 2 a frame). Moves: 9 frames each, whatever they take. Two effects: a stone's collapse, six frames (`$CD1C`, counting at offset `$12B96`), when a stone joined to the Obelisk is clicked (`$CBEC` checks the land path; the count of stones left, offset `$129DC`, drops); the Obelisk's destruction, two ramps of 32 frames (`$C5D0`, offsets `$CF1C` and `$CF1E`), when it is clicked with no stones left (`$1196C`) |

The blood spread is the manual's first kind of blood egg (archipelago 20 on), whose blood
spreads "until it has covered the whole of an island". A world tick counts each egg's
ticks (`$F950`, offset `$12B5A`) and at 50 puts its cell (offset `$129D6`) at the head of
a queue (`$FED6`; the queue at offset `$13426`, head and tail at offsets `$129EA` and
`$129E8`). Each step takes one cell off the queue, infects it (clears bit 2 of the terrain:
land 6 to 2, sand 7 to 3) and queues its unvisited land and sand neighbours (bit 3 marks
them). The second kind, which eats the island away, is the same with a second queue
(`$CAA4`, which turns cells into sea, type 4; the queue at offset `$13826`, head and tail at
offsets `$129EE` and `$129EC`; seeded by `$FEF0`). Nothing in the program refers to `$CAA4`
or `$FEF0` (no absolute, pc-relative or branch reference), so that egg never hatches in
this version.

The game's own speed therefore depends on the CPU. The world tick lags below 8.33 fps
and loses the time a late check was late, but never runs faster than every 6 fields.
Everything counted in frames goes at whatever the frame rate is. Measured with the original
slave on archipelago 1, panning, in 250 fields (`tools/archipelagos.py frames 250 4`):

| Machine (emulated) | fps | fields a frame | world ticks | a move takes |
|---|---|---|---|---|
| a500 | 5.40 | 9.31 | 27 (5.4 Hz) | about 84 fields |
| a1200 | 6.40 | 7.84 | 32 (6.4 Hz) | |
| a1200-030 | 8.20 | 6.08 | 41 (8.2 Hz) | about 56 fields |
| a1200-030, WHDLoad `CACHE` (instruction cache) | 15.00 | 3.36 | 38 (7.6 Hz) | about 27 fields |

A move's length is from a field-by-field dump of the player's position (offsets `$129BE`,
`$129C0`). At 50 fps a move would take 9 fields.

### Decoupled (`src/timing.s`, 2.0b)

Every frame-counted step now takes at least 6 fields, the world tick's period
(`STEP_FIELDS`), and never more than one step a frame. So a machine whose frames take 6
fields or more runs as before, and a faster one runs at that pace. The world tick is left as
the game has it. Time is the level 3 handler's field counter, each interval clamped to 6
fields (the game clears the counter when an archipelago starts).

- The renderer's steps (`$11AC6`) run when the fields since the previous render add up to
  6, with the rest carried. A render with no swap since the previous one also runs them, as
  the original did: an archipelago's opening renders twice in one field.
- A move (`$11FA8`) is interpolated: the start plus the original's eighth of the way times
  the fields into the move / 6. It takes 48 fields plus the frame on the cell, drawn in as
  many frames as fit. At 6 fields a frame its positions are the original's.
- Each step of the two effects (`$CD4E`, `$C5F2`, `$C60E`) draws frames until it has had 6
  fields, the swap measuring each frame and the rest carried to the effect's next step. An
  effect's first frame (6 fields or more after an effect's last) carries nothing from an
  earlier effect. Its first step also counts the fields since the last frame shown before
  it, as every frame's length does.

Checked with `tools/timecheck.py` (300 fields from the first interactive field, a move to
the cell ahead), the original slave against this one:

| Machine (emulated) | | fps | the move | renderer steps a second |
|---|---|---|---|---|
| a500 | original, decoupled | 5.67 | 65 fields, 9 frames | 5.67 |
| a1200, US version (60 Hz) | original, decoupled | 6.80 | 65 fields, 9 frames | 6.80 |
| a1200-030, `CACHE` | original | 12.83 | 25 fields, 9 frames | 12.83 |
| a1200-030, `CACHE` | decoupled | 13.33 | 46 fields, 17 frames | 8.33 |

On the a500 and the US a1200 every field's state (position, buffer, phase, timer, world
tick) is the original's.

The effects, with `tools/timecheck.py OUT effects` (archipelago 1 played to its end by
`tools/play.py`: both stones collapsed, then the Obelisk destroyed):

| Machine (emulated) | | a stone's collapse (6 steps) | the Obelisk's ramps (64 steps) |
|---|---|---|---|
| a500 | original, decoupled | 48 fields, 6 frames | 512 fields, 64 frames |
| a1200, US version (60 Hz) | original, decoupled | 48 fields, 6 frames | 512 fields, 64 frames |
| a1200-030, `CACHE` | original | 17 and 12 fields, 6 frames | 129 fields, 64 frames |
| a1200-030, `CACHE` | decoupled | 32 fields, 16 frames | 384 fields, 183 frames |
| a1200-030, `CACHE`, US version | decoupled | 33 fields, 11 frames | 384 fields, 128 frames |

On the a500 the whole run (2550 fields) is the original's field by field. On the US a1200
it is the original's frame by frame up to frame 62, where one frame ends a field later
(fields 62-72, against 62-71). The route's input is timed in fields, so the two runs then
take different paths, with the same effect lengths.

Nothing else follows the frame rate. The input dispatch after the swap (`$11866`-`$11AC2`)
acts once on each button or key flag the level 3 handler sets and keeps no counter of its
own. Program-image dumps after every field (150 fields of
crosshair moves in cursor mode, then 150 of panning, archipelago 1), counting each word's
changes, find no word that changes more often than every 6 fields on the cached 030 and
more often than on the a500, apart from the presentation: the copper list's bitplane
pointers, the swap's pointer table (offset `$1239A`), the back-buffer pointer and the span
list. With the original slave the same scan also finds the renderer's three counters
(offsets `$12DAC`, `$12DB8`, `$12DC8`, at the frame rate).

## Rendering cost

Traced on the a1200-030 without its MMU model (`tools/bench.py`, 258 fields from the
first interactive field: the right button, then panning right 2 degrees a field), ms a
frame:

| | caches off (WHDLoad's default) | instruction cache (`CACHE`) |
|---|---|---|
| frame | 124 (8.0 fps) | 68 (14.8 fps) |
| CPU work outside the two wait loops | 90.0 | 29.8 |
| per-pixel loop of the far rows | 37.9 | 2.6 |
| span drawer | 24.5 | 9.5 |
| fill routines | 11.1 | 7.6 |
| near rows (division) | 8.3 | 3.9 |
| row set-up | 4.2 | 3.6 |
| waiting for the blitter (about 29 waits a frame) | 11.7 | 10.6 |
| of which the sky fill | 6.7 | 7.0 |
| waiting for the next field (both waits) | 26.6 | 27.9 |
| interrupts | 2.2 | 1.1 |

2.0b on the same run (the body in fast memory, one field wait, the blit queue, the rows
drawn by the slave): 49.8 fps; of a frame's 20 ms, 8.2 are CPU work (draw view 6.6), 3.3
waiting for the blitter and 8.6 waiting for the field (with the blit queue alone: 14.5,
13.0, 0.8 and 5.0).

The world update is 0.03% of the time and the swap 0.1%. 99.7% of the cycles run code in
Chip RAM. With the instruction cache on, the CPU still makes 11500 chip accesses a field
outside the two wait loops (`tools/cpuchip.py`, 4 fields of the same pan). Only the 19%
to the screen buffers and the 0.8% to custom registers need chip memory. The rest are code
fetches that miss the 68030's 256-byte cache (37%), the program image's variables, tables
and span list (29%), the stack (12%) and the map (2%): about 31000 accesses a frame at
one chip slot (282 ns) or more each, at least 8.7 ms.

The only self-modifying code is the level 3 handler's `jsr` (offset `$CE92`). Its target
at offset `$CE94` was written at `$E490`, `$10BB4`, `$1187E` and `$118B0`: the pointer
routine or the pan routine (the target kept at offset `$129CE`). With an instruction cache
the `jsr` could run a stale target. The slave makes the `jsr` jump through a variable of
its own and points the four writes at that variable (patch table above), then turns the
instruction cache on.

`tools/smc.py` checks for any other: it keeps the program image at the game's entry
(relocated and patched) and, at each stop of a route, traces 2 fields and compares every
executed instruction with it. Its two routes cover the title, the archipelago screen,
creating archipelago 1, play, the map, pan mode, both stones' collapse, the Obelisk's
destruction, the end screen and its save, the Obelisk destroying the player, the death
screen, retrying, and selecting another archipelago. The progress block (the loader's
table at `$9F7C`, entry 3: disk offset `$5F000`) loads once at boot, before the title, into
a data buffer. On the a1200-030 with the instruction cache, both versions: no instruction
differs from the entry's image, apart from the `rts` at `$12398` (628 `$1273C`), after which the
comparison runs into the swap's pointer table (data). Nothing outside the image runs
except the slave and WHDLoad.

## Limitations

- The DMA and writer delays wait on `VHPOSR` line changes: five lines, so they scale with
  the display, not the CPU.
