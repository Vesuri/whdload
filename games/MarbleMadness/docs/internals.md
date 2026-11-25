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
  `$68B6`), with one dot list per sprite set (record `+$38` and `+$AE`).
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

After `pl_main`, the slave makes the ExpMem non-cacheable (`WCPUF_Exp_NCS`).

Ours:
- `pl_pal_sound` (C5, "Sound timing");
- `pl_enhanced` (C4, below).

## Enhanced framerate (CUSTOM4)

68020 and up only (kick13's `_attnflags`); on a 68000 the option changes nothing. A fixed
30 Hz world, with a new picture every field (no interpolation yet):
- `$6E48`, `$6ED0` (`vsync_hook`): both per-vsync calls of the Framer first add 30 to a
  world clock, capped at two steps owed;
- `$6EB4`/`$6EBA` (`step_due`): the `minvbl` padding loop ends when the clock owes a step,
  and charges it (the field rate: 50 from `is_pal`, else 60). A step (the game's frame:
  logic and drawing) therefore starts in 3 of every 5 PAL fields, and in every second NTSC
  field;
- `$6EC0` (`pad_field`): in each padding field, the Framer sends the Scroller a draw-only
  job (message `+$14` = 6; the game's codes are 4, a frame, and 5, quit). It is sent only
  when the Scroller is waiting for a message and its last frame has been shown (`$5DB`
  clear), so a late draw costs one picture instead of making every later one spin a field
  in `$1179C`;
- `$AA32` (`scroller_job`): the Scroller runs a draw job as the draw pass `$11704`, then
  sets `$5DB`. It sends no reply;
- `$B292` (`step_ready`) and `$7600` (`count_frame`): the frame counter `$230`, which the
  logic reads, counts only frames that a step drew.

MEASURED, PAL:
- steps (`$230`) in 360 race fields on `a1200-030` + `CACHE`: 180 without the option, 216
  with it; with it on NTSC (`NTSC=1`), 180;
- race timer over 500 fields: 35 → 25 with it (50 fields a game second), 39 → 31 without;
- 20 traced race fields, on `a1200-030` and on `a1200`: a draw pass and a copper rebuild in
  every field, and the race step in 3 of every 5. `a1200` is 38% idle there (Intermediate
  start, no enemy in view), `a1200-030` 92%;
- after the same input, at the same step, the game's data hunks equal those of a run with
  one picture per step, apart from task stacks and structures, the copper-list and
  sprite-set double-buffer pointers and counters, and the placement count;
- the practice race times out and the game returns to the options menu;
- on `a500-1.5m` with the option, the game's code differs from a run of the original slave
  only in the targets of JOTD's `jsr` patches into the slave.

## Caches

`patch_exe` calls `resload_SetCPU(WCPUF_Exp_NCS, WCPUF_Exp)` after loading the game.
Without the MMU, WHDLoad switches both caches off when any region is non-cacheable
(WHDLoad's `cache.html`), so the game runs uncached on a 68030 even with `CACHE`. It does
not limit the frame rate: the CPU is idle most of each field.
