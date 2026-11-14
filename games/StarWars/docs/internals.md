# Internals

The program, its display and game time, every slave patch (as offsets into the game's code
hunk or file), current measurements and known limitations. Offsets are for SPS 0403 (V1.0),
the only version pinned here, unless marked SPS 2926.

## How it loads

A kick13 slave (KickEmu, `BOOTDOS`, `HDINIT`, `CACHE`, `IOCACHE` 4096): WHDLoad starts
Kickstart 1.3 (`kick34005.A500`) with 512 KB chip and 512 KB ExpMem, and `_bootdos` runs as
the first process with the current directory `data` (`slv_CurrentDir`). It
`LoadSeg`s `starwars`, identifies the version by a CRC16 over part of the code hunk, applies
that version's patch list with `resload_PatchSeg`, and calls the program like the CLI
would (argument `"  \n"`, the `Input()` file handle's buffer set to it). When the program
returns, the slave unloads it and quits WHDLoad. The game reads its sounds, music and
shapes from `data/shapes/` through dos.library (`list` names them) and saves its high
scores there.

`data/starwars` (SPS 0403, SHA-256
`44f2a4223f4aef8eb0333930998dea7c8816c8be35c64ef7af947d364426c32c`, 64904 bytes) has three
hunks: code $e9e8 bytes (file data at $28, 2 relocations), data $1f20 ($11cc in the file,
at $ea3c, 88 relocations) and 4 bytes of BSS. Every patch below is in the code hunk: file
offset = code-hunk offset + $28. The program is C (small-data model, globals off `a4`) with
assembly routines, as the ReadMe says.

| Version | CRC16 range (code hunk) | CRC16 | Patch list |
|---|---|---|---|
| SPS 0403 (V1.0) | $0512-$058a | $48a3 | `PLGAME403` |
| SPS 2926 (protected) | $3b5e-$3c08 | $6f40 | `PLGAME2926` |

Any other file quits with "wrong version". The ReadMe also names SPS 939, which has no
table entry.

## Display and game time

The vertical blank code at $00ea (file $0112) sets the display (four bitplanes 8000 bytes
apart, DIW $2981-$f1c1, DDF $38-$d0, BPLCON0 $4200) and increments the frame counter
`-26430(a4)`. The program paces itself on that counter: each update clears it, then busy
waits until it reaches a threshold. The original thresholds are one frame at three of the
four sites and two at the fourth, so on a fast machine those loops ran at up to 50 (or 25)
updates a second, which the ReadMe calls unplayable. StingRay's timing fix sets all four to
three frames: at most 16.7 updates a second (PAL) at each, the same on every CPU fast
enough to meet it. Here the fix is a bug fix, always on (the original has no other
pacing). Each site ends one of the four flight loops; the loop starts with
`clr.w -26430(a4)` and a call:

| Loop | Tick start (clear, call) | Paced wait, swap request |
|---|---|---|
| space | $8962, `jsr $8720(pc)` | $897e, `jsr $09c0` |
| surface run-in | $b55e, `jsr $b2f8(pc)` | $b612, `jsr $0a10` |
| surface | $b63a, `jsr $b2f8(pc)` | $b65e, `jsr $09c0` |
| trench | $d584, `jsr -32454(a4)` | $d5a8, `jsr $0a10` |

The swap request $09c0 does per-tick work besides setting the swap flag -26448(a4) (at
$09fa): the shield countdown -26408(a4) through $4faa (a hit only counts when it is 1),
$579c's countdown -26406(a4) and the -26404(a4) text. The vertical blank server at $0046
swaps the shown and drawn screens (-26446, -26442) when the flag is set ($0066-$0077) and
writes the bitplane pointers every field. The attract loops ($3956, $39dc, $432c, $46dc,
$7734) are not paced.

| Site (code hunk) | File | Original | Fixed |
|---|---|---|---|
| $897e | $89a6 | `cmpi.w #1,-26430(a4)` | 3 |
| $b612 | $b63a | `cmpi.w #1,-26430(a4)` | 3 |
| $b65e | $b686 | `cmpi.w #1,-26430(a4)` | 3 |
| $d5a8 | $d5d0 | `cmpi.w #2,-26430(a4)` | 3 |

SPS 2926: $8390, $b0fe, $b14a, $ceca.

The same counter times other waits: 50 frames at $070a, 350 frames after saving the high
scores at $074c, 500 frames at $271a.

## The slave's patches (SPS 0403, `PLGAME403`)

| Code hunk | File | Patch | Why |
|---|---|---|---|
| $d750 | $d778 | `PL_PS SetStack` over `sub.l 4(a0),d0; addq.l #8,d0` | the stack bound from the slave's `STACKSIZE` (6000) instead of the process's |
| $8d36 | $8d5e | `PL_PS delay` over the `subq.l #1,-4(a5); bne` loop (2000000 iterations) | the instruction text before the game: 3 s or a mouse button (`resload_Delay` 30) instead of a CPU-dependent loop |
| $06ca | $06f2 | `PL_B $60` (`beq` to `bra`), unless CUSTOM1 | high-score saving: skip the IO size check |
| $06fa | $0722 | `PL_B $60`, unless CUSTOM1 | as above |
| $0752 | $077a | `PL_W $4e71` over `blt.s` of the 350-frame wait | no delay after saving |
| $511a | $5142 | CUSTOM1: `PL_B $4a`, `add.w d0,-25348(a4)` becomes `tst.w` | unlimited shields; `PL_GA` keeps the address for the toggle |
| $51c2 | $51ea | CUSTOM1: `PL_PSS .CheckKey,2` over `cmpi.l #$59,8(a5)` | the S key toggles the shields patch (`eor.b #$9b`, `add.w` and `tst.w`), then the original F10 test |
| $897e+2, $b612+2, $b65e+2, $d5a8+2 | +$28 | `PL_W 3` | the timing fix (above); always on. StingRay's v2.00 skipped it with CUSTOM2 |

CUSTOM1 (the trainer) also disables the high-score patches, so a trained score is never
saved. CUSTOM2 is "Enhanced framerate" below (in v2.00 it disabled the timing fix, which
ran the game too fast). The VERIFY build replaces the four `PL_W` with the work timer
(`src/StarWarsProbe.s`), which waits for the same three frames.

## SPS 2926 (`PLGAME2926`)

Not pinned here; from the source. The protected release: `PL_SA $e314,$e432` skips the
protection check and `PL_R $7184` the second one; `SetStack` at $d084, the info-text delay at
$874e; four `PL_PSS .fixDMAWait,10` at $023a, $028c, $02de and $0330 replace the sample
player's CPU-dependent DMA waits with three raster lines; high-score saving is added (it
calls the game's routine at $8d9e after name entry, $6ed4/$6eda/$6f50) unless CUSTOM1; the
shields trainer at $4ac4 with the S key at $4b56 (before the original F3 test); the timing
sites above, always (v2.00 skipped them with CUSTOM2). There is no enhanced framerate for it.

## Fast-CPU fixes (`src/StarWarsFixes.s`, `PLFIX403`)

Always applied (no option): they repair drawing and sound on faster CPUs and leave the
68000's behaviour as it was. `PLGAME403` ends in `PL_NEXT PLFIX403`.

| Code hunk | Patch | Why |
|---|---|---|
| $1890 | `PL_S` to $18b4 | the colour setter $1840 rewrote the four per-plane `bset`/`bclr` opcodes of the plot ($1b70) and of the CPU horizontal line ($1bb0) for each colour. With an instruction cache the stale opcodes ran: on the 68060 the vector-font text lost strokes or whole words (scoring page, wave select). The cause, not the blitter waits |
| $1b70, $1bb0 | `PL_PSS SetPixel,8` | set or clear per plane from the flags the setter stores (-28138..-28135(a4)) |
| $0898, $0a9c, $1a7e, $1aae, $990e, $9942, $9a16, $9a4a, $9b3c, $9b76 | `PL_PSS BlitWait` | every BBUSY poll reads DMACONR once first (WHDLoad's `BLITWAIT`); several polled right after BLTSIZE |
| $1b2c, $1b86, $1c08 | `PL_P`/`PL_PSS` | the CPU plot, horizontal line and screen clear wait for the blitter first: on a 68000 with the nasty blitter the CPU could not reach Chip RAM during a blit |
| $9918, $9a20, $1c08 | `PL_PS BlitMasks`; `BlitClear` | the game never writes BLTALWM (the line drawer writes BLTAFWM only, $ffff), so its blits ran with what was there: 0 in FS-UAE, what the OS last left under WHDLoad. The shape drawer $9806 copies a shape clipped at the left or right edge (mask and planes) through a buffer at -26258(a4) with the A channel, and the mask's last word came out opaque: at some crosshair x the left cannons cut a black box (columns 32+shift to 47, or 48+shift to 63) into the WAVE 1 text and Death Star of the wave select. Both copies, and the screen clear, now set BLTAFWM and BLTALWM to $ffff. The only other A-channel user, the rectangle fill $0810 (BLTADAT, the requester box at $03f8), now fills its last word as its word count asks. A 100-step crosshair sweep on a1200-030: holes in the Death Star outline in 4 frames with StingRay's slave, none now; a500-1.5m showed none with either |
| $26f6, $270c | `PL_PSS SelectStart,2`, `SelectEnd,2` | the wave select loop $26f6-$2720 (stars, cannons, until fire or the counter reaches 500) had no wait: a pass took 3 fields on a500-1.5m, 2 on a1200-030, 1 on a1200-060. Now it notes the counter after the swap wait ($26f6, with the `jsr -32670(a4)` after it) and, after the cannons (`jsr $59e6(pc)` at $270c), waits for 2 more before the swap request, so a pass takes 3 (a500-1.5m unchanged: 3, now and then 4). The counter keeps running for the 10 s timeout. The loop enters at $2714 (`bra.s` from $26f4), so the patch stays before it |
| $9f7c | `PL_PSS AudioWait,10` | the music player counted a 50-pass CPU loop (about 5 lines on a 68000) between starting channel 0 and writing its repeat pointer; now 8 raster lines by the beam (two periods of period 880). FS-UAE's `AUD0LCH HACK` log lines came from it |

## Enhanced framerate (CUSTOM2, `src/StarWarsSmooth.s`, `PLSMOOTH403`)

The WHDLoad option "Enhanced framerate": 50 frames a second at the game's own speed by
interpolation, not a finer simulation tick (a 50 Hz tick would mean dividing every rate,
countdown, spawn chance and random draw of the three phases by three, and AI decisions
would run three times as often). Each tick runs once, unchanged, while the drawing
primitives it calls are recorded as 16-byte ops; the presenter then draws the recording
n times, at j/n of the way from the previous tick's recording (n = 3 in the game and the
wave select, 2 to 4 in the attract loops). Game logic, random numbers and sounds are untouched: 1500 ticks
through space and surface after firing left the game state at $51e2 the same as the
default, tick for tick (`tmp/scripts/ticks2.sh`). Only the star table -25758(a4) differs:
the attract leaves it in a state that depends on how far the attract ran before the
fire, as it does between machines in the original.

| Code hunk | Patch | What |
|---|---|---|
| $0066 | `PL_PSS SmVbl,12` | the VBL server's swap: the original, and drops a queued frame |
| $00a0 | `PL_PSS SmBpl,2` | its bitplane pointers: shows the queued frame at its field (and the palette fade step with each exact frame), else the game's screen |
| $514a, $516c | `PL_PS SmPauseOn/Off` | the pause key draws "Game Paused" into the front screen: not recorded |
| $8962, $b55e, $b63a, $d584 | `PL_PSS SmTick*,2` | game tick start: picks smooth or direct mode, starts recording |
| $897e, $b612, $b65e, $d5a8 | `PL_PSS SmPresent*,8` | replaces the paced wait and the swap call: calls the swap request ($09c0 or $0a10, its flag suppressed) while recording, then draws and queues the frames |
| $771e/$7734, $393c/$3956, $398c/$39dc, $42ce/$432c | `PL_PSS SmTick*,2`, `SmPresent*,8` | the attract loops (text pages, title zoom, the Obi-Wan text, the flight instructions): `jsr $09a8; clr.w` at the start, the wait for the counter (1 or 2) and `jsr $09c0` at the end |
| $389a/$38c0, $43b4/$441c | `PL_PSS SmTick*,4`, `SmPresent2,14` | the credits and the scoring page, which keep the counter running: `jsr $09a8; move.w -26430(a4),-n(a5)` at the start, the wait for 1 more and `jsr $09c0` |
| $26f6/$270c | `PL_PSS SmTickSelect,2`, `SmPresentSelect,2` | the wave select loop, paced as the fix paces it (n = 3); its cannons are drawn (recorded) before the present |

The loops that keep the counter running (phase 8 on) note it at a direct tick's start
(sv_cstart) instead of clearing it, and the direct wait counts from there.

Run-time hooks, installed with `jmp` when a tick records and taken out (the saved bytes
put back, the cache flushed) in direct mode: colour $1840, line $19ae, plot $1b2c, shape
$9806, rectangle $0810, plane copy $0a1c, clear $1c08, swap wait $09a8, TIE fighter draw
$839c (keys its ops by the fighter), surface object draw $a982 (keys a tower's or a
base's lines by its world position), the ground dots ($1e6c, $1ea6, $a67e), the trench's
wall rows $c562 and floor ribs ($d16c, $d1c0), and the swap flag store $09fa. Static
(CUSTOM2, also in direct mode): the world's movement summed at $a6aa, the dots' wrap
marks at $a640 and $a666, and the trench's rib shifts counted at $bb88.

- **Pairing.** An op is keyed by the code address that called the primitive, and for TIE
  fighters by the fighter (the low word of its record). It is paired with the next op of
  the same key in the previous recording, within 64 ops (not counting the ops keyed by
  identity, below, which have their own cursor). Unpaired ops, and ops that moved more
  than 40 pixels (respawns, stars wrapping round), are drawn where they are now.
- **Towers and bases.** $b0bc draws the object table (-26080(a4), 14 bytes: z, x, type at
  +6, the map cell at +10), which $a7a8 rebuilds each tick from the map rows in view, near
  row first and each row outward from a column that changes as the view steers. Neither
  the record nor the draw order names an object. Each tick, $a6aa moves the world:
  -27068(a4) -= d4, -27066(a4) += d5. A row shift (+3500) or a column shift (+-1000)
  moves the map with it, so an object's z and x stay continuous, and z + the summed d4
  and x - the summed d5 stay constant. A line's key is a hash of those two and the type
  (top 10 bits) plus its number in the object (low 6). It is flagged `OPF_ID` and
  interpolated however far it moves. Each recording keeps an object list at its end (47
  objects: the key and the index of the object's first op). The pairing finds an object's
  first line through the previous recording's list, then pairs its other lines in order
  from there, with a cursor of their own.
- **Trench walls and ribs.** $cff4 draws the trench: the floor ribs, a table of 10
  depths (-24916(a4), near first), then the wall panels of the map rows in view, far to
  near, one $c562 call a row (the map word; the pointer to it at -26528(a4); the rows'
  depths, 1900 apart, at -24896(a4); panels only for the 6 nearest). When the nearest rib
  passes, $bb88 shifts the rib table down an entry; when the nearest row passes, $bc10
  shifts the depths and the map pointer moves on a row. By draw order each rib and each
  row's panels then paired with the next one along, and the near panels moved more than
  40 pixels and were drawn in place. A row's lines are keyed by its map word's address
  (bit 15 clear), a rib's by its index plus the shifts counted at $bb88 (bit 15 set), 9
  bits each, the low 6 bits numbering the lines, flagged `OPF_ID` and found through the
  object list as the surface's objects are. Wave 3 on a1200-030
  (`tmp/scripts/trdump.sh`, `tmp/scripts/trmotion.py`), 12 trench ticks: every wall and
  rib line drawn the tick before paired with itself, and the only unpaired lines were a
  new far row and new far ribs. The lines that changed velocity by more than 12 pixels (16
  a tick at most) were the nearest row and rib leaving past the camera, growing as 1/z.
  Before, in 5 of 11 ticks 16 to 32 panel lines were drawn in place, and up to 32 a tick
  changed velocity by more than 12 pixels.
- **Ground dots.** The surface's dots are a table of 25 entries (-25758(a4), z and x of
  two points each) sorted by depth, which $1dda projects into six points per entry and
  plots at $1ea6. When the nearest entry passes, $a67e shifts the table down one entry
  and adds a far one, so by draw order every dot paired with the next one along after a
  shift, within 40 pixels often enough to slide across. Their ops are keyed by identity
  instead: (entry index + shifts counted at $a67e) * 8 + point, flagged (`OPF_ID`), and
  interpolated however far they moved. Steering moves each point sideways ($a648), and a
  point beyond x = +-2048 wraps round by 4096: $a666 marks its entry (shifted along with
  the table at $a67e), and the entry's dots are drawn where they are that tick. Over seven
  wave 3 surface ticks
  (`tools/starwars.py recdump`, `tmp/scripts/paireval.py`) the 532 dots paired changed
  velocity by more than 12 pixels only in the tick the view turned, all alike; before,
  most dots were not interpolated (moved more than 40) and 16 of the 22 that were
  jumped. Pairing by the nearest op instead was tried and paired dots worse (126 of 231).
  Steering (the crosshair held right, `tmp/scripts/surfdump.sh`), 16 ticks: every dot and
  surface line whose key the previous recording held was paired (keyed by the record
  before, 15 to 85 lines a tick missed their pair). The dots that moved more than 40
  pixels were the wrapped ones, drawn in place, and objects near the camera growing in
  perspective.
- **Other buffers.** Ops recorded while the drawing buffer is not the tick's back buffer
  (the front buffer, or another page the game keeps from tick to tick: the flight
  instructions type their text into one and copy it to the screen) are drawn there. They are replayed
  exactly, never interpolated, so in-between frames add nothing to the page. Before,
  each typed letter's strokes were drawn there moving from the previous letter's and
  stayed, as fragments over the text.
- **Pacing.** The counter -26430(a4) runs free. Frame j of a tick is for field B + j;
  each frame is drawn for the first field it can still make, judged by the beam and the
  last frame's drawing time r, so a slow frame skips the in-between frame after it. An
  in-between frame is drawn only if the exact frame can still make its field after it
  (2.25 r from now, checked again after waiting for a free screen and copying the HUD
  strip), so slow frames thin out the in-between frames rather than make the tick late.
- **Screens.** The exact frame (j = n) is drawn into the game's own back screen, as the
  game would have drawn it, and becomes the game's front screen. In-between frames go into
  one of two extra Chip screens (allocated once, when the largest free block holds them
  plus 64 KB; one screen if only that fits; none: always direct), with the HUD strip (the
  31 rows the clear $1c08 leaves, which the game redraws only on change) copied from the
  game's back screen first. One frame at most is queued; the display ($00a0) takes it at
  its field. The palette fade the VBL server does with each swap is done when an exact
  frame is shown.
- **Direct mode.** A tick is late when it starts more than a frame behind or its exact
  frame misses its field. When more than half the recent ticks are late the hooks come out
  and ticks run exactly as the default runs them. Smooth is tried again (after 50 direct
  ticks at least) when a direct tick's work plus n - 1 frames at the running average
  drawing time fits 3/4 of the tick's fields.

Measured (VERIFY, `tools/starwars.py smooth`, `tmp/scripts/phases.sh`: attract, then space,
surface and trench with the trainer):

| Machine | Mode | Frames per tick | Fields per tick | Frame drawing (lines) |
|---|---|---|---|---|
| a500-1.5m | direct from the attract | 1 | as the default | direct tick work 600-670 mean |
| a1200 | direct from the attract | 1 | as the default | direct tick work about 470 mean |
| a1200-fast | smooth (1 % of ticks late by a field) | 1.68 | 2.97 | average 380-540; 3499 in-between frames dropped |
| a1200-030 | smooth throughout | 2.81 | 2.97 | average about 280 |

Wave 3 on a1200-030 (`tmp/scripts/wave3.sh`: space, the surface with towers, the trench),
5 to 35 s after the start, three runs each (the third two instances at once): 2.47 frames
a tick, 12, 17 and 20 late ticks and 113, 95 and 109 dropped frames in about 2900 ticks;
the build before the trench keys: 2.45, 6, 3 and 18, 98, 94 and 95. The late ticks vary
with the host's load more than between the builds. The trench alone, its first 12 s
(`tmp/scripts/trperf.sh`): 2.70 frames a tick for both, 2 late ticks each, 19 and 16
dropped frames, and the same frame drawing times.

The attract on a1200-030, scene by scene (`tmp/scripts/scenes.sh`): the credits, the
title zoom (2 frames a tick: 242 in its 121 ticks), the Obi-Wan text, the flight
instructions, the scoring page and the text pages all stayed smooth, with no late tick
and one dropped frame in 2273 ticks. The wave select (frames about
290-380 lines) gets one in-between frame a tick there; a1200-060 changed the stars on
every field in the zoom and the Obi-Wan text.

On a1200-030 the text pages drew 3839 frames in 3888 fields, with the "PULL TRIGGER"
flash in the default's pattern (each colour two fields); a500-1.5m in direct mode flashed
in the same pattern. Smooth on a500-1.5m, before direct mode also caught exact frames
missing their field, ticks came 1 to 3 fields apart and the flash was irregular. In
every attract scene and the wave select the stars change on every field; the Obi-Wan
text and the flight instructions scroll by plane copies, which are not interpolated (they
move per tick). At most 398 ops in a tick (room for 4096).

With CUSTOM2 off the recordings are not allocated, no hook is installed and
`PLSMOOTH403` applies nothing. The patched code hunk after reaching play
(`tools/starwars.py code`) was the same byte for byte as a build whose `PLSMOOTH403` is
empty and padded to the same length ($a8 bytes), on a500-1.5m and a1200-060.

## Memory and caches

The code and data hunks are in ExpMem (Fast RAM on an A1200 with it). Every buffer the
game allocates goes through $0ba8, `AllocMem(MEMF_CHIP|MEMF_PUBLIC|MEMF_CLEAR)`: four
32000-byte screens (-26446, -26442: displayed/drawn; -26402, -26262), the blitter mask
-26258 (4000), tables -26254/-26250/-26246/-26242 (1000 each), the sound buffer -26238
(800), the palette -26434 (32, CPU only), -26418 (10), 300 bytes per TIE fighter
(52(record), allocated at each spawn, freed at $8912), and the loaded shapes and sounds.
Which of the tables are CPU-only is not yet traced. KickEmu's `CACHE` is set: the 060
dump shows CACR $a0808000 (both caches and the store buffer on).

## Measurements

VERIFY work timer (`tools/starwars.py probe`, `tmp/scripts/measure.sh`): lines from the end
of one paced wait to the start of the next, swap wait included, space wave 1 with no input.

| Machine | Thresholds | Mean | Fields at the wait |
|---|---|---|---|
| a500-1.5m | 3 (fix) | 1038 lines (66 ms) | 2–5, mostly 3 |
| a500-1.5m | original | 999 lines | 2–5, mostly 3 |
| a1200-030 | 3 (fix) | 540 lines | 1 |
| a1200-030 | original | 322 lines (20.6 ms) | 1 |

Cycle profile, a1200-030 without MMU (`--uae_mmu_model=0`), 50 fields, fix on: 71 % busy
waits (paced wait $897e 44 %, swap wait $09b0 27 %), shape drawer $9806 8.7 % (mostly
its blitter polls), clear $1c08 6.1 %, line $19ae 4.4 %, plane copy $0a1c 1.8 %, plot
$1b2c 1.7 %; object update $7c6e and its callees about 2 %. DMA slots: 61 % free.

## Limitations

- The game is capped at 16.7 updates a second by the timing fix, its original speed on
  an A500. Enhanced framerate adds in-between frames but keeps that rate.
- Enhanced framerate shows the in-between frames up to two fields behind the tick; input
  is read per tick as before (the crosshair per field).
- Enhanced framerate only exists for SPS 0403. On SPS 2926 CUSTOM2 does nothing.
- The pause key in enhanced framerate is not yet tested.
- The gdb stub reads data the 68060 keeps writing as stale (the counter -26430 read 0 on
  a1200-060, the copyback data cache): measure the 060 by screenshots.
- Quit is Del (`slv_keyexit` $46); F10 is the game's own key in one version.
