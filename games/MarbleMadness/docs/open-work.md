# Open work

Where the work stands, then the next items in order.

JOTD's v2.3 source is imported and set up on the repository layout. The slave builds with
vasm and differs from the shipped one only in `kick13.s` and the `$VER` date
(`docs/development.md`). The performance
investigation is done (`docs/internals.md`, "Frame pacing and game time"): the game is not
CPU-bound on a 68020+; it is frame-locked at one logic step per two vsyncs, written for
NTSC, so PAL plays at 5/6 speed and 25 fps. Music and sound effects are also clocked by the
vblank and play at 5/6 tempo on PAL ("Sound timing").

1. Enhanced framerate (the plan below).
2. The idle task's keyboard poll writes CIA-A SDR about 1950 times a field; harmless for
   speed, but worth moving to the keyboard interrupt if it is ever touched.

## Enhanced framerate: 30 Hz world, presented every field

The goal is 30 logic steps a second on PAL and NTSC (the speed the game was written for),
drawn every field (50 fps PAL, 60 fps NTSC), with positions interpolated between the last
two steps.

**Why it is practical** (`docs/internals.md`, "Tasks and the frame pipeline" and
"Display"):
- The step and the drawing are already separate calls. The logic is the mode handler
  (`$AF9E` for the race); the draw pass `$11704` reads object records and builds sprites.
- Everything that moves is a hardware sprite over a single playfield bitmap. Drawing again
  costs only the sprite pass and a copper rebuild, with no playfield blitting.
- World positions are 16.16 fixed point, so interpolation has its sub-pixel precision
  already, and the game's own projection (`$6918`) can turn blended positions into screen
  positions.
- The game already smooths scrolling once per frame (`$6658`). Positions are
  view-relative, and the code to shift every sprite with the view exists.

**Budget** (PROJECTED from the `a1200` measurement, not yet measured): 30 steps of 97k,
plus 50 × (21k draw + 29k copper + 48k rest), is about 7.9M of 14.2M cycles a second
(55%). A field that also runs a step needs about 196k of 284k. This is only from the
Intermediate start with no enemies in view, so busy scenes are a gate in step 9. The 68030
and faster have a wide margin.

**Configuration:** two options; C1–C3 are JOTD's.
- `C4:X:Enhanced framerate (68020+):0`: the 30 Hz world with interpolated drawing. On a
  68000, or with it off, the game's loop is the original.
- `C5:X:Music and sound at NTSC tempo on PAL:0`: its own toggle (step 3), on any CPU.

The installed icon sets `CUSTOM4=1` and `CUSTOM5=1`. With both off, the patch list is
exactly the original.

**Decided:** interpolation, one step behind, with no prediction. The per-vsync colour
cycling stays as it is.

Steps, each verified before the next:

1. **Tools.** Move the analysis scripts into `tools/`. They build the flat PatchSeg-addressed
   image and its Ghidra import, map hunks to runtime addresses from a memory dump (the
   layout differs between `a1200`, chip only, and fast-memory setups), and split a trace
   by task with a call tree for one task. Add harness commands that count, per field, the
   entries to a set of offsets (step, draw, copper, sound ticks) and that dump a state
   snapshot.
2. **Option plumbing.** Add the C4 and C5 tags and a 68020 check (AttnFlags). Measure the field
   rate from the beam (the highest line, 312 or 262) rather than trusting the PAL flag,
   because WHDLoad's `NTSC` option changes it. Gate: with both options off, and with C4
   alone on a 68000, the game memory after `patch_exe` is byte-identical to the original
   slave's.
3. **Sound tempo on PAL** (C5). Music: use 125 instead of 150 at
   `$1F3D6` when the field rate is 50. Effects: run `$21740` six times per five fields
   (an accumulator in the SfxTask loop at `$20B1A`), or switch its request to
   `UNIT_MICROHZ`. Gate: over 300 PAL fields, 360 music steps and 360 effect steps, with
   the same note sequence as an NTSC run.
4. **30 Hz world clock, no interpolation yet.** Replace the Framer's pacing (the kick at
   `$6E2C` and the `minvbl` padding `$6E68`–`$6ED8`) with an accumulator: each field adds
   30, and a step runs when it reaches the field rate. That gives 3 steps per 5 PAL fields
   and 1 per 2 NTSC fields. A step is the original logic plus draw, and fields without a
   step show the last frame. Gates: one game second (`$B566`) is 50 PAL / 60 NTSC fields.
   `$230`, `$794` and `$D320`'s every-8th-step decision count steps. Scrolling and the
   mid-frame half step (`$6658`, which runs on the second field of a 2-field frame) still
   look right with 1- and 2-field frames. This is a usable fallback on its own: correct
   speed, with 2-2-1 frame spacing on PAL.
5. **Separate the step from the draw.** The Scroller takes two jobs: step (the mode
   handler, the reply and the `$794` countdown) and draw (`$11704`, then set `$5DB`). Keep
   the native order inside a step. Gate: with one draw per step, the decoded state at
   matched steps (player records `$236`/`$32A`, the object tables, `$224`, `$9BA`, the clock)
   and the screenshots equal step 4's.
6. **Draw every field, same state.** On fields without a step, send a draw job with
   unchanged state. Audit what the draw pass and the Framer's new-frame path change, and
   make those count steps, not draws:
   - the frame counter `$230` (read by the logic);
   - the vsync index `$7690`;
   - player `+$EB` (resets both dot lists);
   - `$5BCB`;
   - the placement counter `$638`.
   Gate: repeated draws leave matched-step state identical to step 5's, both sprite sets
   show the same picture, and nothing flickers across set swaps.
7. **Interpolation.** After each step, snapshot each listed object's world position
   (`+$C`/`+$10`/`+$14`) and the scroll state (`$224`, `$9BA`, the remaining distance
   `$7692`/`$D30C`). For each draw:
   - blend each position by α, the time since the latest step in steps (0, 0.6, 0.2, 0.8,
     0.4 on PAL; 0, 0.5 on NTSC);
   - project the blend with `$6918` into the fields each draw routine reads. The marble's
     are `+$1E`/`+$20`; for the other types, take them from the projection's callers
     (`$E7E4`, `$104A4`, `$1ABB6`, `$1BDCC`, `$1CD3C`, `$1D2C0`);
   - set the displayed row and the sprite offset from the blended scroll, in place of the
     game's half step;
   - run the draw pass, then restore the records.

   Do not blend an object that is new in the list, changed type, or jumped further than a
   threshold (a respawn after a fall, the level start), and clear the history on mode
   changes. Animation frames and the marble's texture dots stay at the step rate. Gates:
   - field-by-field screenshots of the marble, an enemy and a running scroll show even
     steps, and the ball does not wobble against the playfield while scrolling;
   - a snapshot taken at α = 0 equals the native pose;
   - obscuring by the scenery still matches at blended positions.
8. **Other modes.** Options menu (mode 5, `$B18C` → `$CA14`): find the pointer's position
   fields and blend them the same way, or move the pointer every field from the mouse.
   Every other mode (level intro, bonus count `$B05A`, game over, high scores, demo) gets
   30 Hz steps and plain redraws. Gate: each mode's durations in fields equal NTSC timing,
   and the transitions into and out of the race work, including two players.
9. **Budget and matrix.** On `a500` (the original loop), `a1200`, `a1200-030` and
   `a1200-040`, measure step, draw and copper cycles, draws per second and fields per game
   second, in the busiest scenes (Aerial, Silly, Ultimate, two players). When behind, steps
   come first and draws are skipped; cap the step debt at 2. If the `a1200` drops draws,
   make the copper rebuild cheaper first: `$86B4` rebuilds the whole list, but per field
   only the plane pointers and the wrap split change.
10. **Release.** The ReadMe credits JOTD and adds about five player-facing lines. The icon
    gets `CUSTOM4=1` and `CUSTOM5=1`.
