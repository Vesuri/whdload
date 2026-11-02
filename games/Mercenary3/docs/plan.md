# Plan

Goal: faster on every supported machine, rendering up to 50 fps, world and game logic at
their native speed. 50 fps means a frame, logic or presentation, in one field (20 ms). Steps
are in order of value; take the first one not done whose dependencies are met. Design and decisions: [open work](open-work.md). Rules:
`AGENTS.md`.

## How to work

- **One option per feature for development.** Each behaviour change has a `Custom1`
  bit in `whdload/Mercenary3.slave.asm`. VERIFY accepts these with `Custom5=0`. The
  release exposes one **Enhanced framerate** control, default On (`Custom5=1`); Off
  (`Custom5=0`) keeps the original game's behaviour: the shipped code plus fixes for the
  shipped slave's defects (bits 0 and 15; user decision). It ignores individual-feature settings. Debug aids go in the `VERIFY` build.
- **Build** with `make original slave verify` before each commit.
- **Measure** with `tools/fps.py` on `a1200-fast`, `a500-1.5m` and the existing `040-25` matrix configuration: the same build with the
  option off and on, same session. Keep a change only if it gives a repeatable measured
  gain somewhere and loses nowhere; there is no fixed percentage cutoff (user decision).
  L1 is a correctness prerequisite: accept native world speed and
  the intentional 12.5 Hz logic cap rather than requiring an FPS gain. Run
  `tools/matrix.sh` only where a step says so. The 040/060 cells give
  emulator counts that don't follow the CPU frequency. Include `040-25` in routine
  off/on comparisons (user decision), but do not treat its FPS as a hardware-speed prediction.
- **Price frame time** on `a1200-fast` with `route_profile.py` (instruction profile) and on
  the 030/040/060 with the `VERIFY` build's `Custom2` drawing bypass: `fps.py` with and
  without it ([frame budget](internals.md#frame-budget-toward-50-fps)). Those cores record no
  instruction profile. Routine-entry/return video-beam timing also measures inclusive
  elapsed costs on the 040; see the [current breakdown](internals.md#68040-frame-budget-after-p5).
  `beam_profile.py` does that for any routine on any CPU, and `render_profile.py` splits
  the 020 profile per routine ([F0](internals.md#f0-one-field-frame-budget-03050)).
  The cycle-exact 030/50 remains the reference fast machine (S0, user decision).
- **Check the game still works** with three tests, not more:
  1. **Options off:** release `Custom5=0` gives the same frame count as the VERIFY build
     with only the slave fixes (`CUSTOM5=0 CUSTOM1=32769`) in the same session on
     `a500-1.5m`. The shipped slave gives fewer frames because of its `_dmaon` wait.
  2. **World speed:** `tools/sim_speed.py` shows the native walking and turning rates per
     field (6 units, 2 heading units).
  3. **Play:** play the route, and the screens the step touches, and look at the
     screenshots.

  Build heavier checks (lockstep runs, pixel twins, static audits) only to chase a fault
  these show.
- **Done** means the step's check passes, the result is a short entry in `internals.md`,
  and the box below is ticked. Commit each step on its own.
- **(U)** marks a decision for the user: ask, record it under Decisions in `open-work.md`.

Addresses: code as `Disk.1` offsets, variables as chip addresses (a chip code address `A`
is `Disk.1` `A + $3CB0`).

## Steps

### O. Settle the existing options

**O1. Options 0–2** (one-time DMA enable; FMODE 3 on AGA; stack in expansion memory).
- Play through the screens the route doesn't reach: navigation, a vehicle, a flight,
  Quit Situation, save and load. Look for display faults. The supplied manual says the
  player is never killed; a game-over/restart screen is not an applicable check.
- Vehicle, flight and navigation checks were deferred by user decision and reached in
  P3. Navigation is the A-to-Z panel; no separate full-screen map was identified.
- For FMODE 3, if a screen shows its own copper list, check whether it sets the fetch
  window (`$0092`/`$0094`); patch it or turn FMODE off while it shows.
- Make `ws_ExpMem` optional (a negative size) and fall back to the chip stack without it.
- Check: play; options-off test.

### L. Native world speed on fast machines

**L1. Logic gating** (new bit). At the main loop head (`Disk.1` `$5DF92`, a 6-byte `jsr`),
in walking mode (chip `$7122` = 1): if fewer than 4 fields have passed since the last pass,
wait for the next field; otherwise run the pass with the true elapsed count in chip
`$52954`. The world can no longer run fast above 12.5 fps; nothing changes below it.
- Check: world speed on `a1200-fast` and the fastest cell; play.

### P. Smooth frames between logic passes

**P1. Presentation frames** (needs L1). The original prediction below is retained
for comparisons; P4 supersedes it in Enhanced framerate. Where L1 would wait,
draw a frame instead. With only one field left before logic is due, start a redraw
only if the last presentation took at most one field; the initial allowance is two.
This admission rule avoids spending a full redraw on a one-field gap on the 030.
1. save the restore set;
2. put the extrapolated player pose in chip `$7142..$7161`: committed pose + per-tick rate
   × fields since the last pass, with the rate taken from the last pass's pose change;
3. run the camera derivation (`$5D844`) and view setup (the inline block at `$5E0BA`,
   `$5DA50`, `$5A91E`);
4. publish (`$5E458`), clear (`$5E840`), set up the new back buffer (`$469C4`, `$469C8`)
   and draw (`$5410E`, `$5765E`, `$593A6`, `$5AFAA`, `$577BE`). This follows the native
   order: buffer setup belongs after publication; `$5765E` supplies scene setup;
5. restore.

The restore set is what the write audit lists for those calls ([internals](internals.md#renderer-inputs-and-writes)):
the render scratch at chip `$0340..$4000`, the drawing's variables, the object-table areas
and the self-modified code words. Leave the display state alone: copper list pointers
`$72B2`/`$72B6`, `$42C00`/`$42C01` and the copper lists. Keep `$7180` counting logic passes
(blinking).

Never run the collision test in a presentation frame. Snap to the committed pose after a
collision (`$6F56`), a mode change or a stop.

- A `VERIFY` check hashes chip `$5350..$68000` before step 1 and after step 5,
  excluding display state and normal interrupt-owned updates. Report every other changed
  address. Presentation code must restore its changes without rolling back live interrupts
  (user-approved correction: publication necessarily advances non-display timers).
- Check: the hash check holds over the route; world speed; play, and look for smooth turning
  in per-frame screenshots. Measure the frame rate on `a1200-fast` and with `matrix.sh`.

**P2. Other objects interpolated** (needs P1).
- The named `$AF36..`/`$B31E..` areas are drawing scratch. Object XYZ arrays start at
  chip `$581C`, `$5C1C`, `$601C`; vehicle headings are at `$6C1C + 4 × slot`.
- Keep the previous pass's poses. Draw objects between the last two passes, then restore.
  Apply the one-pass display delay to logic frames too: delaying only presentation frames
  would rewind from the current pose shown by each logic frame. Stage only the object
  renderer after collision; keep simulation, distance ordering and selection committed.
  Snap new or vanished objects, scene/model changes and jumps.
- Check: the P1 hash check; play near moving objects.

**P3. Other movement modes** (needs P1).
- Approved: extend native-speed logic and presentation to vehicles, flight and lifts.
- Vehicle/surface flight and space flight (`Disk.1` `$5E214`, `$5E3CA`) move a step
  per pass. Apply L1 and their respective presentation drawing paths.
- Correction: lifts stay in walking mode. Their timer (`$5A644`) already runs in
  L1's tick loop; they change height at arrival rather than moving the camera
  continuously. Keep this native timing and snap presentation at floor changes.
- These modes also cover O1's deferred vehicle, flight and A-to-Z navigation panel
  checks with options 0–2 on, including any separate fetch window under FMODE 3.
- Check: world speed in that mode; play.

**P4. Correct presentation transitions** (follow-up to the user's video).
- Bit 14 replaces player extrapolation with previous/current interpolation on all
  rendered frames. Freeze one alpha for camera and geometry after the publication wait;
  keep committed poses for input, collision and subsequent game logic.
- Render the collision routine's drawing tail in extra frames without running its
  collision decisions. Preserve the complete polygon clipping workspace.
- Check starts, stops, reversing, the mailbox approach and vehicle/flight/lift views;
  P1 restore hashes, world speed and options off. Compare bit 14 off/on with `fps.py`
  on the routine setups and reference 030. Accept this as a smoothness correction,
  with one native pass of visual delay, rather than requiring an FPS increase.

**P5. Room-local camera interpolation** (follow-up to the prison wall video).
- Bit 16 applies P4's movement delta to the room-local XYZ words during drawing,
  retaining the native room origin, transition guards and committed collision state.
- Check wall motion off/on, turning and room exit/return, P1 restores (including a
  lift arrival), native speed and options off. Compare routine FPS with bit 16 off/on.

### M. Code and data in fast RAM (68020+ with fast RAM)

**M1. Hot code in fast RAM** (new bit).
- Find the routines behind the instruction-fetch misses (`bus_audit.py` page counts:
  `Disk.1` `$4EDB0..$4EFAF` and `$5B5B0..$5B9AF` lead; 18.5 KB covers 95%).
- At boot, copy them to expansion memory, put a `jmp` to the copy at each entry, fix
  PC-relative references that leave a copied routine, and flush the caches.
- Handle self-modifying code: the drawing writes code words at chip `$459BA`, `$4F700..` and
  `$4F9C2..`. The slave's 68040 path already turns four such sites into indirect calls
  through chip `$C0..$CC`; use that variant, or point the writers at the copies.
- Only on a 68020 or later with real fast RAM; otherwise the original code.
- Check: play; options-off test; measure on `a1200-fast`, then `matrix.sh`.

**M2. Hot read-only data** used by the moved code, if `bus_audit.py` still shows worthwhile chip reads
and moving them gives a repeatable measured gain. Same checks. Implement and assess
with R1 (user decision), retaining separate options and measurements for each change.

### S. Frames in one field (the 50 fps path)

Before phase S, with all then-existing options on, drawing nothing took 2 fields per frame on
`a1200-fast` and 1.35 on the 030/50, because presentation frames carry fixed costs (save and
restore, scene setup) that pushed publication past the field boundary. With drawing,
the 030/50 needed about 4 fields. S2 reduces the fixed costs; S3 and S4 take drawing off the
chip bus. Targets, per frame on the 030/50: S2 no-draw frames in one field; S4 full frames
in two fields or fewer (25 fps); 50 fps on a real 68040/68060 is the expectation to check
in S6, not a promise.

**S0. Reference fast machine.** Decided: the cycle-exact 030/50 (`030-default` matrix
cell). S2, S4 and S6 targets are judged there; the 040/060 cells only confirm the game runs.

**S1. Restore buffer out of the slave file.** P1's 17,366-byte buffer is a `ds.b` in the
slave (22.9 KB file instead of about 6 KB). Take it from the expansion memory instead, with
presentation frames off when that memory is missing. Check: P1's hash check; slave size.

**S2. Cheaper presentation frames.** About 0.7 field per presentation on `a1200-fast` goes
to copying the restore set word by word, and 0.3 to scene setup (`$5765E`).
- Restore only what something reads before rewriting it. Test render scratch (chip
  `$0340..$4000`, most of the set) with a `VERIFY` poison fill after every presentation:
  the committed state (`state_trace.py --compare` against poison off) and the screenshots
  must not change before removing a range. The whole range and both halves failed that
  comparison in S2, so retain them; the assumption that this scratch is all rewritten
  before reading was wrong. Bulk copying the full set reaches the 030 no-draw target.
- Copy what remains with long or `movem` moves, from and to fast RAM where possible.
- Find whether scene setup can be skipped or shared when its inputs haven't changed since
  the last frame; keep it if not.
- Check: P1's hash check, the poison test, world speed, play. Measure: `a1200-fast`
  profile (cycles per presentation) and the `Custom2=31` frame rate on all cells: the 030
  must reach about 50 fps without drawing.

**S3. The rest of the hot renderer code in fast RAM** (extends M1). 20 KB covers 95% of the
remaining fetches: Disk.1 `$524B0..$53AB0`, `$48DB0..$4A5B0`, `$5B8B0..$5C4B0`,
`$575B0..$580B0`, then the smaller blocks in the frame budget. These contain the
self-modifying sites (chip `$459BA`, `$4F700..`, `$4F9C2..`): point their writers at the
copies, or use the slave's 68040 indirect-call variant, then flush. Same guard as M1.
Check: play, options off, world speed. Measure on all cells.

**S4. Draw into fast RAM, copy to chip once** (68020+ with real fast RAM, new bit).
- Give the renderer a staging bitmap in fast RAM for the 3D view (point the back-buffer
  base at chip `$42C00` used by the drawing there). The clear and the read-modify-write
  drawing then happen in fast RAM.
- After drawing, copy the view's rows into the chip back buffer with `movem` (about 22 KB),
  then publish. Find first who else writes the back buffer (the panel and text below the view): keep those writes in chip, or copy those rows too.
- The native clear covers 136 rows (21,760 bytes over four planes), not the estimated
  140; copy only those rows. Reserve 96 KB for the 32 KB bitmap and its required
  low-word `$8000` alignment.
- Check: screenshots off/on identical in a still scene, play, world speed. Measure on all
  cells; keep it only where it gains (the playbook's Powerdrome case gained only with the
  code in fast RAM too).

**S5. Publication wait.** Re-measure the publication's field wait after S4. If it is still
a large share on fast cells, decide R3 (triple buffering) with the numbers.

**S6. ✓ Budget checkpoint.** `matrix.sh` with all options, the frame budget table
again, and the S0 target check. Record what limits each cell next.

### F. One-field frames on the 030/50 (the 50 fps step)

[F0](internals.md#f0-one-field-frame-budget-03050) measured the current build. On the
030/50 a frame's work is 24.9 ms on average (21.5..27.4); presentation frames, which also
save and restore, are about 28 ms. 50 fps needs every steady frame under 20 ms: about
8 ms less on the worst frames. Measured candidates: the presentation copies (7.1 ms per
presentation) and the staging copy (3.3 ms, kept); estimated: chip-bus traffic by the CPU,
about 21,000 accesses per frame, 6..12 ms. Steps are in order of measured value and cost.
"Expected" figures are estimates for the step to confirm or refute.

For every step, on the reference 030/50: `beam_profile.py` on the routines the step changes,
before and after, and the publication intervals (roots `5e460`, as in F0); `fps.py` and
`PER_FRAME=1` cadence. On the 020: `bus_audit.py` where the step targets chip traffic. New
behaviour takes the next free `Custom1` bit (21 up); add it to the release mask (`$1FFFFF`)
once accepted.

**F0. ✓ Budget.** `render_profile.py`, `beam_profile.py`, `bus_audit.py`'s place table,
relocation-aware `route_profile.py`; results in internals.

**F1. Restore once per logic pass — tested, not retained.** A temporary bit 17
saved at the first presentation and restored before the next logic pass; the small
player/navigation/room pose still restored after every redraw. This did not remove
any copies on the measured route (one presentation per logic pass). Because publication
precedes drawing, deferring the restore to the gate still puts it before the same next
publication: the expected 3.4 ms reduction in the worst displayed-frame interval was
incorrect. Beam timing regressed and FPS did not improve; retain the existing restore
path. Reconsider copy amortisation only if later work allows multiple presentations
per pass. See [F1 results](internals.md#f1-deferred-restore-tested-not-retained).

**F2. ✓ The remaining hot code in fast RAM** (extends S3). Chip code fetches are 1,943 per
field on the 020; the room path, whose code is in chip, is 6.6% of main 3D on the 020 but
42% on the 030.
- Move the routines behind F0's fetch pages, largest first: Disk.1 page `$5F000` (room
  path `$5F438`, edges `$5FDCC`), the clear (`$5E840..`), `$5D000` (camera and view setup),
  `$5A000`, `$4B000`/`$4C000`, `$56000`, `$55000`, `$59000`, `$60000`, and the line plotters
  `$0C000..$0DFFF` with their computed-jump table. Delimit routines with `render_profile.py`
  and the disassembly; relocate with S3's tables (operands, islands, entries; moved mutable
  words join P1's restore set). Keep the main loop and the patched call sites in chip.
- Remove chip hops: point copied callers straight at copies, including M1's entry jumps
  (`$5B030`, `$5B038`, `$5B050`) and the two instructions `$4EE84` keeps in chip.
- Check: play, options off, world speed, P1 hash, still-scene screenshots off/on identical.
- Measure: `bus_audit.py` fetches (aim: a few hundred per field), beam `577be 5f438 5e840`.
- Result: mean 030 frame work 24.8 → 21.6 ms; chip-code fetches 1,963 → 430 per field.
  Accepted as bit 17; see [F2 results](internals.md#f2-remaining-hot-code-in-fast-ram).

**F3. ✓ Hot chip data reached through long operands.** Move data blocks whose every reference
is an absolute long operand or a long immediate (patchable in chip code and copies alike):
- Renderer state and projection constants at chip `$42C00..$42F3F` (513 reads per field),
  for example `movea.l #$42C44,a4` at `$5B030`. Find the writers with `write_audit.py`. The
  back-buffer pointer `$42C00` is also used by the panel, IRQ text and S4: keep it in chip
  or patch every user.
- Game-image data pages with heavy reads: `$49000` (`$498A0..$498FF`), `$0A000`
  (`$0AF20..$0AF5F`, read and written), `$28000`, `$35000`, `$37000`; measure each.
- `$C0` call vectors (136 reads per field): only if a same-length direct form exists in
  the copies; otherwise leave them.
- Check as F2. Expected: 1.5..3 ms per frame.
- Resolved scope: projection state `$42C04..$42C75`, complete mask/offset tables
  `$49880..$49B33`, and the row table `$43080..$4318F` are relocatable with long
  operands. Keep the low-word-addressed `$42E00` table in chip. `$AF36` shares
  variable-length workspaces with `$AA6E`/`$AE6E`; the model pages use relative
  offsets and embedded pointers. Those are not independent long-addressed blocks.
  Leave their broader relocation for F5. Keep dynamic `$C0` calls cache-safe.
- Result: 030 FPS 26.30 → 28.80; mean frame work 21.61 → 20.76 ms,
  below the estimated saving. Accepted as bit 18; see
  [F3 results](internals.md#f3-hot-renderer-data-in-fast-ram).

**F4. ✓ Log conversion with `bfffo`** (68020+). `$4EE84`/`$4EE88` find the leading bit with a
compare tree (5.5% of the 020's cycles). Use `bfffo` in the fast copy, giving the same shift
and exponent. Check: the two routines agree for every 28-bit input (host harness), then
play and screenshots. Expected: 0.5..1 ms on the 030.
- Result: `tools/log_harness.py` finds d1, d6, d7 and flags identical for every input of
  all three entries. Mean 030 frame work 20.70 → 19.84 ms, worst 24.64 → 22.55; 030 FPS
  28.80 → 29.60. Accepted as bit 19; see [F4 results](internals.md#f4-log-conversion-with-bfffo).

**F5. ✓ Render scratch in fast RAM (bit 20).** The scratch's operands are absolute
short words and 16-bit displacements, which a same-length copy cannot point at fast RAM.
The user approved translating the copied code: `tools/translate.py` rewrites them to
32-bit forms and re-targets the branches that the growth moves. Game variables stay in
chip, because their accessors are spread across the untranslated main loop.
- Result: mean 030 frame work 19.85 → 15.60 ms, worst 22.56 → 17.71. No interval now
  exceeds 20 ms (113 of 210 did before). 030 FPS 29.60 → 48.00 and 464 of 480 cadence
  intervals are one field. The presentation save/restore copies fall 3.41/3.30 →
  1.40/1.38 ms. Accepted as bit 20; see [F5 results](internals.md#f5-render-scratch-in-fast-ram).

**F6. ✓ Checkpoint.** F0's beam table again, `PER_FRAME=1` cadence on the 030/50 (target:
steady one-field intervals), `matrix.sh` with all options, options off. Result: the 030
walk runs at 50 fps (frame work 15.6 ms, worst 17.7); cadence is one field from field
65 on; matrix 030 48.00 fps, 040-25 44.50, 060-50 44.80, 020-fast 14.10; options off
equals shipped. The opening view's main 3D is what limits the 030/040 next; see
[F6](internals.md#f6-checkpoint).

### R. Faster drawing

**R1. Renderer inner loops.** Profile the drawing routines on `a1200-fast` and `a500-1.5m`.
Rewrite the loops worth 3% or more, one at a time, per CPU class (68000: long and `movem`
stores; 68020+: cache-sized loops). Compare screenshots with the option off and on; build
a pixel twin only if they differ. Keep each rewrite only where it gains.

**R2. Blitter back-buffer clear — tested, not retained.** A temporary option replaced
the CPU clear (`$5E840`) with four blits, waiting before drawing and preserving the
three zero planes and one filled plane. With S4 active it kept the CPU clear.
Neither shared-bus nor blitter-priority clearing gained on A500 (4.10 → 4.10 fps);
both regressed on chip-only A1200 (9.40 → 9.20). The priority comparison repeated
identically. Keep the native CPU clear; see [measurements](internals.md#r2-blitter-clear).

**R3. Triple buffering — closed, not implemented.** The user does not want triple
buffering. Retain double buffering despite the S5 measured wait; no extra chip buffer.

**R4. Data cache on 68030+ — supported.** User approved supporting available caches.
Custom1 bit 13 requests the data cache through WHDLoad alongside the instruction
cache. Route FPS is unchanged on all measured setups; retained for cache support by
user decision. See [measurements](internals.md#r4-data-cache).

**R5. Cache-safe polygon clipping** (follow-up to the reported red ground).
- Bit 15 replaces the mutable immediate clipping comparison with a data read on
  68040/060, in both chip and relocated renderer paths. Keep CACHE enabled.
- Check: the outside-prison turn/stop reproduction with the same build, bit off/on;
  P1 restore hash, world speed, options off, and routine FPS comparisons.

### X. Release

**X1. Complete.** User approved **Enhanced framerate**, default On. README updated
with requirements, expansion memory, installation and options. Matrix, release play
on every CPU class, world speed and options-off checks passed; see
[results](internals.md#x1-release). No hardware is available; the user approved finishing
without it. Real cache behaviour and 040/060 hardware performance remain unverified.

## Status

- [x] O1
- [x] L1
- [x] P1 [x] P2 [x] P3
- [x] P4
- [x] P5
- [x] M1 [x] M2
- [x] S0 [x] S1 [x] S2 [x] S3 [x] S4 [x] S5 [x] S6
- [x] R1 [x] R2 (not retained) [x] R3 (closed) [x] R4
- [x] R5
- [x] X1
- [x] F0 [x] F1 (not retained) [x] F2 [x] F3 [x] F4 [x] F5 [x] F6

P4 and P5 address the presentation defects reported after the original plan completed.
Phase F is complete: the 030/50 walk runs in one-field frames. No plan step remains open.
Hardware validation remains unavailable, outside X1.

## In place

- Byte-exact reconstruction of the shipped slave (`make original`); the performance slave
  with default-on **Enhanced framerate**; VERIFY retains `Custom1` bits 0–20.
- `route_profile.py` (instruction profile, or `MODE=counter` untraced), `fps.py`,
  `matrix.sh`, `sim_speed.py`, `state_trace.py` (per-pass state, `--compare`),
  `write_audit.py`, `bus_audit.py`, `render_profile.py`, `beam_profile.py`,
  `log_harness.py` (F4 against the original, every input),
  `translate.py` (F5's growing translation, verified by re-decoding; `--check` on a
  `memory_dump.py` dump),
  `presentation_check.py` (VERIFY restore hashes), the
  `VERIFY` build's `Custom2` drawing bypass.
- The game-time model and the renderer's inputs and writes ([internals](internals.md)).
