# Internals

The program, its display and game time, every slave patch (as offsets into the game's code
hunk or file), current measurements and known limitations.

## Program

`data/MarbleMadness!` is the decrypted executable (347 hunks, Aztec C style: one library
stub per LVO) that JOTD's slave loads with `LoadSeg` under kick13 (Kickstart 1.3 in
ExpMem, 256 KB of OS fast memory). Offsets below are `resload_PatchSeg` offsets: the hunks'
data concatenated in file order. Runtime addresses are not stable; a hunk's allocation is
rounded to 8 bytes, so do not derive one hunk's address from another's by adding sizes.

The program uses absolute addressing throughout (no base register), so a flat image of the
hunks placed at their PatchSeg offsets, with the RELOC32 entries applied against those
bases, has addresses equal to PatchSeg offsets; every `$` offset below reads directly in
such an image. Library calls go through stubs at `$24730`–`$24C44` (`$1F4` holds SysBase,
`$1F8` DOSBase, `$7B1C` GfxBase, `$2CD4` IntuitionBase).

## Tasks and the frame pipeline

The main program (`$2F54`) starts the idle task, the Scroller, the Painter and the Framer,
and sets ExecBase's `Quantum` to 2. The sound set-up (`$21D9C`) starts the other two.

| Task | Struct | Entry | Pri | Job |
|---|---|---|---|---|
| `dummer` | `$2D9C` | `$2CF0` | −126 | idle loop (patched by the slave: `key_control`) |
| `Scroller` | `$AB1C` | `$A9E4` | 1 | one game frame per message: the mode's step, then drawing |
| `Painter` | `$94BC` | `$91C0` | 1 | paints the playfield on request (messages built by `$92D6`, drawn by `$9910`); no cycles in the traced race fields |
| `Framer` | `$7058` | `$6DA8` | 15 | display pacing, per-vsync display work |
| music | `$1FA82` | `$1F2FA` | 6 | music sequencer, woken by a VERTB server (`$1F260`) |
| `SfxTask` | `$21170` | `$20A3C` | 7 | sound-effect envelopes on `timer.device` ticks |

One frame:

1. The Framer sends the Scroller a message (`$AA3C`), then loops: `WaitTOF()`, the
   per-vsync routine `$7596` with the vsync's index in the frame, and a poll of its reply
   port.
2. The Scroller (`$B23A`) calls the handler of the current mode (`$5D2`, table `$B2A2`;
   mode 0, the race, is `$AF9E`). The race handler runs the logic, 12 calls in a fixed
   order (`$D320` scroll decision, `$A6E8`, `$B454`, `$13A0A` objects, including the marble
   physics at `$14EF0`, then `$1D364`, `$196C6`, `$1A452`, `$1B6F2`, `$1C1C2`, `$1CF80`,
   `$1D3EC`, `$FC8A`, `$AF7A`), and replies to the Framer (`$AA8A`). The Scroller then
   counts down `$794`, runs the draw pass `$11704` and sets `$5DB` (frame ready).
3. The Framer pads to `minvbl` vsyncs. The first vsync that sees `$5DB` advances the frame
   counter `$230`, copies the logic's scroll row `$224` to the displayed row `$226`, swaps
   the sprite sets and rebuilds the copper list (`$86B4`).

The logic reads the frame counter: `$D320` re-decides the scroll every 8th frame
(`$230 & 7`), or every frame while a scroll is running.

## Display

- **Playfield:** one bitmap, not double-buffered. Each plane is a 512-row circular buffer of
  36-byte rows (288 pixels; DDFSTRT `$38`, DDFSTOP `$C0`). The copper list (two lists,
  alternated) points the planes at row `$226` and splits at the wrap. A 4-plane status bar
  sits above it. There is no horizontal scrolling.
- **Moving objects are hardware sprites.** There are two sprite sets of 8 × `$208` bytes,
  swapped per frame. The draw pass `$11704` walks the sorted object list (`$5F7`–`$615`,
  indices into the record pointer table `$21CC`, ending with −1) and dispatches on the
  record's type byte to a draw routine in hunk 26 (`$5BE0`–`$6750`):

  | Type | Records | Routine |
  |---|---|---|
  | 1 | marbles (`$2158`) | `$5DFC` |
  | 2 | `$2160` | `$60F6` |
  | 4 | `$2248` | `$621C` |
  | 5 | `$2168` | `$64B6` |
  | 7–9 | `$2274` | `$650A` |
  | `$E` | `$2258` | `$645E` |
  | `$F` | `$2298` | `$6350` |
  | `$2A` | `$BA6`+ | `$62C6` |
  | `$2C` | `$CCA`+ | `$6562` |

  `$122AC` places an image at a screen position: it allocates sprite channels through the
  multiplexer `$3BB2` and copies the image in. Its counter `$638` limits a draw pass to 60
  placements. The sets are handed over at the vsync: `$3F38`, at the end of a pass, sets
  `$5BCA`, the per-vsync routine swaps the sets and clears it (`$38F0`), and the next pass's
  placement loop (`$1179C`) spins while it is set. So a pass that starts before the vsync
  has taken the last set waits for that vsync. The marble's rolling texture is dots plotted into its sprite image (`$6864`,
  `$68B6`, list `+$AE`); walls cover sprites by masking their images (below, "What a step
  leaves for its draw").
- **Positions:** world coordinates are 16.16 fixed-point longwords at record `+$C`, `+$10`
  and `+$14`. The logic projects them during its step with `$6918` (integer parts only):
  `sx = y − x + $88`, `sy = z + [$9BA] + $6C − (x + y)/2`. The result goes into the record
  (a marble's at `+$1E`/`+$20`), and the draw pass reads only that result. `$9BA` is the
  world offset of the view.
- **Scrolling:** a scroll moves `$9BA` and the target row `$224` in steps decided by
  `$D320` (`$D0xx` also asks the Painter for the new rows). `$22A` is set while a scroll is
  running, `$22B` holds its speed in rows per frame and `$228` its direction. The game
  already smooths it: on a vsync without a new frame, while a scroll runs at a speed of 2
  or more, `$74D4` (from the per-vsync routine) moves `$226` part of the way, shifts every
  built sprite to match (`$65B6`, `$6658`) and has the copper list rebuilt. With `minvbl` =
  2 that is half a step on the second vsync of a frame. At speed 1 the view moves once a
  frame.
- **Per-vsync colour cycling:** `$A7A2` and `$B6DE` advance player colour animations once a
  vsync (counters at player record `+$7A`, `+$7B`). They run at the display rate: 50 Hz on
  PAL, 60 Hz on NTSC.

## Frame pacing and game time

The Framer pads every frame to at least `minvbl` vsyncs and counts the vsyncs each frame
took in a 16-word histogram right after `minvbl`.

- `minvbl` is a static longword, **2**, at PatchSeg `$70B4` (hunk 34 + `$5C`). Nothing in
  the game writes it. The code also has a special case for 4.
- The game logic takes one fixed step per displayed frame, and the clock ticks once every
  30 frames: the time counter at `$B566` (the slave's `seconds_count` hook) runs once per
  30 frames.
- So one game second is 60 vsyncs: 1.00 s on NTSC (30 fps) and **1.20 s on PAL (25 fps)**.
  On PAL the whole game, ball motion included, runs at 5/6 of the speed it was written for.

MEASURED (release build, PAL unless stated, frame changes counted from per-field
screenshots, clock ticks from `PC == $B566's jsr` in the traces):

| Machine | fps | fields per game second | frames that needed >1 vsync |
|---|---|---|---|
| `a500-1.5m` | 25 (21–25 at race start) | 60–61 | 43 of 557 |
| `a1200-030` + `CACHE` | 25 | 60 | 1 of 472 |
| `a1200-030` + `CACHE`, NTSC | 30 | 60 (1.00 s) | – |
| `a1200-030` + `CACHE`, `minvbl` = 1 (experiment) | 50 | 30 (2× speed) | – |

On the 68030 the Framer's frames are ready within one field: the per-field game work is
45–90k of about 1 010k cycles (5–9%), and the rest is the game's idle task. That task
(PatchSeg `$2CF0`, patched to `jsr key_control`) spins `addq.l #1,$100; addq.l #1,counter`
and the slave's keyboard read (CIA-A SDR) about 1950 times a field. The 68030 runs are on
`--uae_mmu_model=0` for the trace; the MMU-model core gives the same frame rates.

The options menu runs through the same Framer: its pointer (the ball) moves every second
field, 25 Hz on PAL, which is the jerky motion seen there.

MEASURED, cost per frame on `a1200` (14 MHz 68020, chip RAM only, 284k cycles a field),
Intermediate race start with no enemy in view, release build, 8 traced fields with the
mouse moving. The step and the draw pass finish within the field after the Framer's
message, and the copper list is rebuilt in the next field:

| Work | Cycles | When |
|---|---|---|
| race logic (`$AF9E`) | 97k | per frame |
| draw pass (`$11704`) | 21k | per frame |
| copper rebuild (`$86B4`) | 29k | per frame |
| rest of the Framer, `SfxTask`, music, interrupts | 48k | per field |

That totals about 43% busy at 25 fps; the rest is the idle task. On `a1200-030`, the
practice race costs about 60k of 1 010k cycles a field.

## Sound timing

Both sound clocks run at the display rate, so on PAL music and effects play at 5/6 of
the NTSC tempo. The arcade original plays its music at the faster (NTSC) tempo.

- **Music:** the VERTB server `$1F260` counts vblanks and signals the music task, which
  runs the sequencer step `$1F286` once per elapsed vblank (at most 5 to catch up). Each
  step advances every voice by `$1FA68`, which `$1F3B2` sets to `(tempo << 16) / 150` (the
  constant at `$1F3D6`; a song's tempo word comes in through `$21D82`). Nothing checks the
  display rate.
- **Effects:** `SfxTask` re-sends a `TR_ADDREQUEST` of 16 666 µs (60 Hz) on `UNIT_VBLANK`
  and runs its per-channel envelope step `$21740` for each completed request. A vblank-unit
  request completes on a vblank, so the step runs once a field.

MEASURED, `a1200` PAL, 8 consecutive fields: `$1F260`, `$1F286`, `$21740` and the Framer's
`$7596` each ran exactly once per field.

**CUSTOM5** (PAL only: `is_pal` watches the beam for two frames, and a display with more
than 300 lines counts as PAL) patches both clocks:
- `$1F3D8` changes the divisor from 150 to 125, so each vblank's music step grows by 6/5;
- `$20B1A` (`sfx_tick`) runs the effects step six times per five fields.

MEASURED: with CUSTOM5 the music step `$1FA68` is `$13333`, against `$10000` without it,
on `a500-1.5m` at the options menu. `$21740` ran 12 times in 10 fields on `a1200-030`. On an
NTSC machine (`NTSC=1`) the game's code is byte-identical to a run without the option.

## Sound fixes

Always on (`pl_sound_fix`). Sound goes through Kick 1.3's `audio.device`, via the game's
BeginIO stub `$24A3C` (hunk 337; timer.device's requests use it too). Each music note or
effect is a CMD_WRITE of a short loop (16 to 256 bytes), with ADIOF_PERVOL and cycles 1,
then the same with cycles 0; ADCMD_PERVOL steps its volume each field, and `$201CA` cuts it
with CMD_FLUSH (IOF_QUICK) 2 to 3 fields later, copying the channel's request from `$21250`
(`$44` a channel).

**Note pops.** The flush stops Paula mid-loop. The channel then holds the last byte it
fetched, at the note's volume, until the next note starts with a jump from that level.
The 16-byte waveform starts 13, 124, so the held level is often its peak.
- `audio_io` keeps each channel's volume from the requests that set it, and before a flush
  takes the channel's volume register (`AUDxVOL`) down to 0 over 32 display lines (2 ms)
  while the loop plays on; the flush then holds 0. The next note's write sets its own
  volume.
- Ending a note at a loop boundary instead (ADCMD_FINISH with ADIOF_SYNCCYCLE, waiting for
  the write's reply) did not help: `audio.device` stops at the interrupt of the next loop's
  start, when Paula already plays its first word, and the levels held were the same.

**The practice rumble's loop.** At the race start channel 0 loops a 3200-byte rumble at
period 429 (0.39 s), `prcsnd` hunk 40, PatchSeg offset `$23A8`. Where it loops the waveform
jumps from -59 (mid-fall) to 2. `seg_loaded` (after the LoadSeg at `$8CF0`'s `$8D00`)
patches 12 bytes when the file is `prcsnd`: bytes 0–3 and 3192–3199. The values come from a
16th-order linear predictor fitted to the sample, solved by least squares for the bytes
that make the played loop as predictable as the rest of it: the worst prediction error
across the loop point is 2.7σ, against 21.8σ before; 99% of the sample is within 2.8σ.

MEASURED, `a1200-030`, the practice race with channels 0 and 2 alone (a temporary debug
build), 10 s from the race start, full stereo separation:
- channel 2 held a level between notes 74 times, up to 7770 (of 32767), and jumped out of
  them by up to 10087 (median 902); with the fade the 71 holds are at 0 and the jumps up
  to 1523 (median 78). The waveform's own steps (99.9th percentile, about 1290) are
  unchanged;
- 69 cuts in the first 700 fields after GO!, so the fade waits about 140 ms in 14 s (1%,
  computed from the count, not measured as time);
- the release build on `a500-1.5m`, `a1200`, `a1200-030` and `a1200-040`: the race runs,
  the rumble in chip memory has the designed bytes, and on `a1200-030` neither stereo side
  holds a level other than 0 for more than 10 ms in the first 10 s of the race.

## Mouse

Always on (`pl_mouse_fix`). The race reads the mouse once a step (`$19390`, hunk 206, from
the mode handler at `$AF8E`): for each port, the change of the 8-bit counters (JOY0DAT or
JOY1DAT, swapped by `$195E1`) since the last step, against the last values at `$195E2`/
`$195E6` + port. The deltas go to `$195E4`/`$195E8` and, turned 45° for the isometric view,
to the words `$195EA`/`$195EE`. A change beyond $60 counts whose sign differs from the
last step's output is taken for a counter that wrapped and replaced by 127 the other way
(`$194A8`, `$19506`). An output of 0 counts as positive, so from rest a move of 97–127
counts in +x or −y goes the wrong way at full speed, and so does any fast reversal (80
counts one way, then 100 back, gives 127 the first way). Moves of more than 127 counts a
step are guessed from the last step's sign. The options menu has its own reader (`$19008`,
no guess) and is unchanged.

The slave samples both counters every field (a VERTB server, `mouse_irq`) into 16-bit
totals. At `$1947E`, the counter path, `mouse_read` samples again, takes the port's total,
limits it to −127..127 (not −128: the game negates the mouse's x, and −(−128) is −128 in a
byte) and writes it as the counter word, so the game's own subtraction
gives the total; totals older than 10 fields are dropped (the race's start). The guess is
switched off: the limits $60 and −$60 become 127 and −128.

MEASURED (`monitor mouse` moves in a practice race, the outputs at `$195E8`/`$195E4`):
- original, `a1200`: +110 x gave +127 (+60 gave −60); −110 y gave +127; 80 then −100 x gave
  −80, then +64 and +36;
- fixed (release build, CUSTOM4=1): +110 x gives −110, −110 y gives −110 and 80 then −100
  x gives −80 then +100, on `a500-1.5m`, `a1200`, `a1200-030` and `a1200-040` (FS-UAE
  sometimes spreads a move over two steps; the outputs then add up to it); −110 x gives
  +110 and three steps of +127 x give −127, −122, −1, −123 on `a1200`.

## Input choice

The options menu (hunk 90's data `$CDAC`) keeps the Red Player's device at `$CDB2` (Joy
Stick, Trackball 1, Trackball 2, Mouse), the Blue Player's at `$CDB3` (Mouse) and the Red
Player's port at `$CDB4` (Joy, Mouse; the Blue Player has the other). When the menu opens
it takes the port from `$195E1` (hunk 207; set: the Red Player on the Joy Port), and GO!
writes `$195E1` back from `$CDB4` and sets each port's reading from its device (`$C968`).
CUSTOM5 bits 1-3 (port × 4 + device), when not 0, are written to `$CDB2`, `$CDB4` and
`$195E1` in `patch_exe`, so the menu opens with that choice. Checked: the menu shows each of
4 values on `a1200` (and Mouse Port / Trackball 2 on `a500-1.5m`), and with Mouse Port /
Mouse a race started without touching the menu reads the mouse.

## Slave patches

JOTD's (`pl_main`, always):
- `$2CF0`: the idle loop calls `key_control` (Esc ends the race, F1 adds 10 s, P pauses;
  Help sets the level-completed state, which JOTD's comment says does not work because no
  player is flagged as finished);
- `$99F6`/`$99F8`: the level 1 access fault;
- `$1E684`: the level 5 access fault, when a bird hits the marble;
- `$B566`: `seconds_count`, which handles pause, the infinite-time trainer (C1) and the
  start level's time bonus;
- `$CF46`–`$CF59`: the menu's device names;
- `$33FA`: the start level (C3);
- `$1F384`: no music (C2).

After `pl_main`, the slave makes the ExpMem non-cacheable (`WCPUF_Exp_NCS`); with CUSTOM4 on
a 68020 or later, copyback again ("Caches").

Ours:
- `pl_sound_fix` (always, "Sound fixes");
- `pl_mouse_fix` (always, "Mouse");
- the Red Player's input (CUSTOM5 bits 1-3, "Input choice"; data, no patch list);
- `pl_pal_sound` (C5, "Sound timing");
- `pl_enhanced` (C4, below).

## Enhanced framerate (CUSTOM4)

68020 and up only (kick13's `_attnflags`); on a 68000 the option changes nothing. A fixed
30 Hz world, with a new, interpolated picture every field.

**Clock and jobs.**
- `$6E48`, `$6ED0` (`vsync_hook`): both per-vsync calls of the Framer first add 30 to a
  world clock, capped at two steps owed.
- `$6EB4`/`$6EBA` (`step_due`): the `minvbl` padding loop ends when the clock owes a step,
  and charges it (the field rate: 50 from `is_pal`, else 60). A step (the game's frame,
  logic and drawing) starts in 3 of every 5 PAL fields, and in every second NTSC field.
- `$6EC0` (`pad_field`): in each padding field the Framer sends the Scroller a draw-only
  job (message `+$14` = 6; the game's codes are 4, a frame, and 5, quit), when the
  Scroller is waiting at its port (`TC_SIGWAIT` has the port's signal; a step blocked in
  one of its own waits is also in `TS_WAIT`) and its last frame is out (`$5DB` clear).
- `$AA32` (`scroller_job`): the Scroller runs a draw job as the draw pass `$11704`.
- `$B292` (`step_ready`), `$7600` (`count_frame`): the frame counter `$230`, which the
  logic reads, counts only frames that a step drew.

**Presentation.** The game swaps the sprite sets and rebuilds the copper list (`$86B4`,
two Views alternated by `$7A7E`, ending in `LoadView`) at the vsync after a frame's draw.
That list is shown only from the vsync after that, while the next draw already fills the
set that the swap freed, which is still on screen. With 2 fields a frame that is harmless.
With a frame every field it shows the older set every other field. Under CUSTOM4:
- `present` (end of every draw): swap (`$38F0`), sprite pointers into the copper templates
  (`$85EC`, `$8630`), the blended row into `$226` and `$7692`, rebuild, all under
  `Forbid`. The display takes it at the next vsync.
- At most one list is built per field, because a second build would go into the list on
  screen. Fields are counted by a VERTB interrupt server (`field_irq`, priority 20, above
  graphics.library's, so a task that WaitTOF wakes already sees the new field). CIA-A's
  TOD is no substitute: in FS-UAE it ticks a little after the vblank, which made the
  menu's draws wait a second field, and some machines clock it from the mains. A draw that ends after
  one has been built is left to the game's vsync path (`$5BCA` stays set).
- `$767C` (`vsync_rebuild`): the vsync builds only after such a swap, or for a change
  (colour cycling, the `$1E20D` display) that has waited a whole field for a draw.
  Otherwise the field's draw builds it, as late as the game would have.
- `draw_wait`: no draw starts in the field in which the display still shows its target
  set.
- `$7664`: the half step `$74D4` is off; the row is blended instead.

**Interpolation**, one step behind. With α the clock's remainder over the field rate (0,
0.2, 0.4, 0.6 or 0.8 on PAL; 0 or 0.5 on NTSC):
- the nine calls of the draw routines in the draw pass (`$11850`–`$11996`) go through
  `blend_call`. It writes `prev + α·(cur − prev)` into the screen position that routine
  reads, calls it, and restores the field. The fields are `+$1E` (types 1, 2), `+$28`
  (4, `$E`), `+$4E` (5), `+$20` (7–9, `$F`), `+$6` (`$2A`) and `+$0` (`$2C`, in 1/16
  pixel). prev is that record's position at the step before; each step's draw (`$B28C`,
  `step_draw`) records the positions in one of two tables of 48, allocated at install;
- the displayed row (`$226`, mod 512) and the view distance (`$7692`) blend between the
  logic's `$224`/`$D30C` at the two steps;
- shares are rounded half away from zero, so a sprite and the playfield moved by −d and
  +d stay together;
- a position that is new, jumps more than 48 pixels, or a mode change (`$5D2`) is drawn
  unblended; so is an object whose image changed since the step before (the game moves the
  worms and slimes with a new frame). The image is `*(*(record + F))`, F = `+$64` (type 2),
  `+$62` (4), `+$42` (5), `+$1C` (7–9, `$F`), `+$3A` (`$E`); types 1, `$2A` and `$2C` are
  not checked. An unblended object still moves with the blended view: its y gains
  `bl_view` (below), so animated objects (the flags, the worms) stay on the scrolling
  playfield.

Animation frames and the depth sort of the pre-pass (`$1085C`, `$DD1C`, world positions)
stay at the step rate.

**What a step leaves for its draw.** The logic puts lists in the records, and the draw
marks each entry it uses (its first long becomes −1), so a second draw of the same state
finds them empty. Entries are 8 bytes, image.l and a screen x.w, y.w:
- `+$38` (5 entries; types 1, 2, 4; 3 for `$F`): the scenery pieces that cover the sprite.
  `$11270(list, n, x, y, sprite)` clears the sprite's pixels under each piece's image
  (`$11060`). This is the occlusion by walls. Levels 1 and 3 also mask against fixed
  pieces (`$5BE0`, `$11678`), which read the view offset `$9BA` at draw time.
- `+$AE` (4 entries, two points each): the marble's texture dots, plotted by `$6864`.
- When the marble breaks, the step sets `+$EB` and fills `+$38` and `+$AE` with the
  shards' images; the draw places them (`$10FDC(list, image, n)`) and clears `+$EB`.
  Type `$F`'s dots are such a list at `+$26` (5 entries); its draw adds `$40` to each y
  (`+$2C`, 8 apart) while `$6860` is set.

Under CUSTOM4 a step's draw saves every list as it is used (`list_call`, up to 32 a step)
and each marble's `+$EB` (`marble_flag`); a draw job puts them back first, so it leaves the
records as the step's draw left them. The pieces' screen y are the step's; for a draw at α
they move by `bl_view`, the blended `$9BA` minus the step's (it is 0 without a scroll), and
back after the call, and `$11678` reads `$9BA + bl_view` (`$116BC`). On draw jobs `dots_f`
takes type `$F`'s `$40` back first, so its dots move once a step. Two lists are redone for
the blended draw instead:
- **Covering scenery** (`rebuild`). The step picks the pieces for the sprite's position at
  the step (`$1E49A(record, kind)`: kind 0 a player and 1 another type 1 or 2, through
  `$1ED00`; 2 type 4, from `$1AB90`; 3 type `$F`, from `$1D29C`). It reads the world
  position (`+$C`/`+$10`/`+$14`, integer parts), the screen position the draw reads and
  `$9BA`, and writes only the list and the scratch `$BA2`. At a blended position a piece
  the step did not pick could cover the sprite (a column of the marble showed beside a
  wall), so for a blended sprite whose step list has a piece, `list_call` calls it again
  with the world position (recorded at each step) and `$9BA` blended, then restores them.
- **Shards** (`shard_blend`). Each step places the shards anew (images `$10044` + n, one
  per shard), and they move between the record's two lists and their entries from step to
  step; each one blends between its place now and the place of the same image at the step
  before (a second lists table, swapped each step), and is put back after the call.

**Other modes.** Every mode handler (`$B2A2`) runs as a step, so the race (0), the pause
(1), the menu (5) and the end of the game (6, a state machine at `$C478`) run at 30 Hz.
- Options menu (mode 5, `$CA14` with `$CDAC` = 2): the step reads the mouse (`$19008`,
  which only accumulates the counters; the buttons are levels) and sets the pointer
  (`$CCA`, type `$2C`, in 1/16 pixel) at `$CBB4`. A draw job does the same
  (`menu_pointer`), so the pointer follows the mouse every field; mode 5 is not blended.
- `$8DF4` (`wait_fields`): the game's waits of n vsyncs (`$8DF0`, 17 calls) last n/60 s,
  as on NTSC: n · field rate / 60 fields, with the remainder carried to the next wait.
  They time menu clicks (20), the end of a race (`$BEBC`, 180, in mode 4), the bonus count
  (`$BB2C`, 384, in mode 3) and hunk 30's sequence (10 to 60). Modes 3 and 4 run their
  whole sequence inside one step.
- `$11CBE`, the mode changes' redraw, calls the draw pass twice itself; those draws are the
  game's, with no blending and no `dots_f` (the flag `draw_job` marks a draw job's draw).
- Nothing is timed by vsyncs before the menu, and an idle menu starts no demo (4000
  fields).

MEASURED, PAL:
- the marble's dot points plotted (`$68E4`) per race field on `a1200-030` and `a1200`: 8 in
  every field; before the lists were put back, 4 in the fields without a step;
- the practice race on `a1200-030` with a rail covering the ball while it scrolls: the
  scenery mask (`$11060`) runs to its pixel loop in step and draw-only fields alike; a
  covering piece's y in `+$38` grows by the change of `$9BA` (records count y from the
  bottom: the projection `$6918` adds `$9BA`);
- the same respawn with a log of the drawn shards (check build, removed): each of the
  eight shards moves in every field (for one, x 142, 155, 167, 177, 189, 202 over a step
  and its draw jobs); with index matching, shards that changed entries swapped places;
- the re-picked covering scenery in that run (21 re-picks): with the same pieces, their y
  is the step's plus `bl_view`; at blended positions the list can hold the previous step's
  piece instead of the step's;
- the respawn after a fall off the practice course on `a1200-030`: the shards (`+$AE`,
  `+$38`) are placed in every field and converge as in the original loop;
- steps (`$230`) in 360 race fields on `a1200-030` + `CACHE`: 180 without the option, 216
  with it; with it on NTSC (`NTSC=1`), 180;
- race timer over 500 fields: 35 → 25 with it (50 fields a game second), 39 → 31 without;
- 20 traced race fields on `a1200`: a draw and a copper rebuild in every field, the race
  step in 3 of every 5, 38% idle (Intermediate start, no enemy in view);
- 30 fields with the marble rolling fast (`a1200-030`): its screen position advances in
  every field, by 1 to 2 pixels. Without blending it stands still in 2 of every 5 fields;
- a scroll at 1 row per step: the displayed row advances 0 or 1 rows a field, 3 rows per 5
  fields, one step behind `$224`;
- after the same input, the game's data hunks equal those of the `NOBLEND` check build
  (`docs/development.md`), apart from task stacks, idle counters and music bytes, and,
  in one pair of runs, the sprite-set index, its descriptors and the copper lists (one
  swap apart); the logic's records (`$230`, `$236`–`$32A`, `$224`/`$226`, the object
  tables) are equal;
- the options menu on `a1200-030` with the mouse moving 1 count a field: the pointer moves
  2 pixels in every field (without the option 4 pixels every second field); steps in 3
  of every 5 fields, a draw in every field. On `a1200`: the same, 68% idle;
- mode durations from GO! (`a1200-030`, fields; seconds in brackets):

  | Sequence | NTSC, no option | PAL, no option | PAL, option |
  |---|---|---|---|
  | GO! to the practice race | 238 (3.97) | 234 (4.68) | 203 (4.06) |
  | practice race, to the timeout | 3658 (60.97) | 3658 (73.16) | 3047 (60.94) |
  | the same, two players | 3657 (60.95) | – | 3046 (60.92) |
  | Beginner race (`CUSTOM3=1`) | 4558 (75.97) | – | 3797 (75.94) |
  | out of time (mode 4) | 184 (3.07) | 184 (3.68) | 153 (3.06) |

  GO! to the race also paints the playfield, which is not timed. Each sequence then returns
  to the options menu. The bonus count and the end of the game were not reached (no
  level was finished);
- boot to the options menu: 1.82 s in all three (load and paint bound);
- on `a500-1.5m` with the option, the game's code is byte-identical to a run without it.

## Caches

`patch_exe` calls `resload_SetCPU(WCPUF_Exp_NCS, WCPUF_Exp)` after loading the game (JOTD's;
loading runs with ExpMem copyback). Without the MMU, WHDLoad switches both caches off when
any region is non-cacheable (WHDLoad's `cache.html`), so the game runs uncached on a 68030
even with `CACHE`; with the MMU (68040, 68060) ExpMem, where the game's code runs, is
non-cacheable and serialized. A likely reason: the game loads code during play (the levels'
`*Track` and the sounds' `*Snd` files have code hunks) with Kick 1.3's `LoadSeg`, which does
not flush the caches. It has one `LoadSeg` call, in `$8CF0`.

With CUSTOM4 on a 68020 or later, `patch_exe` sets ExpMem back to copyback, and
`seg_loaded` (after `$8CF0`'s `LoadSeg`, always) calls `resload_FlushCache`. Drawing every
field needs the time: on NTSC (60 draws a second) a 68020 dropped draws and stepped late,
and a user's A4000 with a 68060 (A3660) skipped many frames with WHDLoad's `NTSC` option,
smooth on PAL.

MEASURED (release build, `CUSTOM4=1 CUSTOM5=1 CACHE`, 120 race fields after the practice
race starts; new pictures are changes of the displayed sprite set `$5B2C`, steps of `$230`):

| Setup | ExpMem non-cacheable | ExpMem copyback |
|---|---|---|
| `a1200`, PAL | 112 new pictures, no late step | 120, no late step |
| `a1200`, NTSC machine (`NTSC=1`) | 99, 10 steps a field late | 118, no late step |
| `a1200-030`, PAL and NTSC | 120 | – |

WHDLoad's `NTSC` option on a PAL machine needs an NTSC monitor driver, which the test boot
disk does not have, so that case was not run; the `a1200-060` core is not cycle-exact, so
the 68060's speed was not measured. With copyback, a Beginner race (`CUSTOM3=1`, which loads
`BegTrack`'s code) runs on `a1200-030`, `a1200-040` and `a1200-060`, and on `a1200-060` a
second Beginner race after the first one's timeout (its code loaded again) runs too.
