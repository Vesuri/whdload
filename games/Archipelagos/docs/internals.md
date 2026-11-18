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
| (install) | same | the instruction cache on for BaseMem, the data cache off (`resload_SetCPU`: `WCPUF_Base_WT`, `WCPUF_IC`) |

## Memory

Everything is in the 512 KB of BaseMem, which is Chip RAM; the slave asks for no ExpMem.
The program image runs from `$201C` to `$16314` and mixes code, variables, tables and
data that DMA reads: the copper list (offset `$9976`, its address kept at offset `$8FE0`),
the sky's copper lists (tables at offsets `$99FA` and `$9A1A`, which the level 3 handler
puts in `COP2LC`), and audio samples (Paula reads offset `$3A10` in play). Fixed addresses
outside the image: the two screen buffers at `$5C780` and `$663C0` (40000 bytes each: five
320x200 planes, 8000 bytes apart), and the map, 64 KB at `$70000`-`$7FFFF`, which code
indexes from `$78000` with a signed word (256 cells a row; the low nibble is the terrain
type, bit 7 marks a cell with an object). The supervisor stack is `$784`-`$800`.

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
The second wait (step 3) adds nothing to that and caps the loop at 25 fps: with no work a
frame would still take two fields. The move routine `$11FA8` (eight steps between two
cells, each a world update, a render and a swap, then a final frame on the cell) has only
the renderer's wait.

Draw view: planes 3 and 4 of the ground (lines 113-179) by two blits; then, for each of
the 67 ground rows from the bottom up, the row's two edge rays across the map (`$11BD4`),
the map cells along the row (near rows by division, `$11D2C`; rows beyond the 45th with a
per-pixel loop, `$11E0E`-`$11E2C`) into a span list (offset `$13C26`), and the span drawer
`$11E52`, which looks up each span's terrain in the map, collects object cells, and fills
planes 0-2 through one of eight fill routines (table at offset `$1254A`, code from
`$1242A`, a `jsr` for each 16-pixel word). The view is 256 pixels wide (16 words from byte
4 of each 40-byte line), sky lines 20-112, ground 113-179. The sky fill `$AE32` blits five
planes of lines 20-112 (plane 1 ones, the rest zeros), waiting for the blitter before each.
All waits for the blitter go through `$11EFA` (BLTBUSY in `DMACONR`).

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
