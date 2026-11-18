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
| frames | at the start of the renderer (`$11AC6`-`$11AE5`): one step of a spread across connected land (`$C99E`: a queue at offset `$13426`, head and tail at offsets `$129EA`/`$129E8`, one cell a frame; what it shows in play is still to be identified), the terrain animation phase (offset `$12DAC`, every 10 frames), two object animation timers (offsets `$12DB8`, `$12DC8`, 2 a frame). And moves: 9 frames each, whatever they take |

So game time is partly tied to the frame rate. It can only get slower than nominal, never
faster, as the game stands: the world tick lags below 8.33 fps and loses time when frames
end late, and frame-counted things go at whatever the frame rate is. Measured on
archipelago 1, panning, in 250 fields (`tools/archipelagos.py frames 250 4`):

| Machine (emulated) | fps | fields a frame | world ticks | a move takes |
|---|---|---|---|---|
| a500 | 5.40 | 9.31 | 27 (5.4 Hz) | about 84 fields |
| a1200 | 6.40 | 7.84 | 32 (6.4 Hz) | |
| a1200-030 | 8.20 | 6.08 | 41 (8.2 Hz) | about 56 fields |
| a1200-030, WHDLoad `CACHE` (instruction cache) | 15.00 | 3.36 | 38 (7.6 Hz) | about 27 fields |

A move's length is from a field-by-field dump of the player's position (offsets `$129BE`,
`$129C0`) on the a500, a1200-030 and a cached a1200-030. At 50 fps a move would take 9 fields.
Anything that speeds the frame up makes moves, the spread and the animations faster in
the same proportion, so the game's time has to be decoupled before any of it ships
(`open-work.md`).

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

The only self-modifying code found is the level 3 handler's `jsr` (offset `$CE92`). Its
target at offset `$CE94` is written at `$E490`, `$10BB4`, `$1187E` and `$118B0`: the
pointer routine or the pan routine (the target kept at offset `$129CE`). That search
(`tools/smc.py`) compared the bytes of every instruction a traced run executed with the
relocated file, at the end of the a1200-030 run above; the other screens are not checked
yet.

## Limitations

- The DMA and writer delays wait on `VHPOSR` line changes: five lines, so they scale with
  the display, not the CPU.
