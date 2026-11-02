# Current work

Goal: improve the game's performance, especially on higher-end Amigas (a 68020 with
fast RAM and above): frame rates up to 50 fps with smooth movement and rotation of the
player and other objects, while world simulation and game logic keep their native rates.

The shipped slave is reconstructed byte for byte. A reproducible 500-field `a1200-fast`
profile of a walk out of the cell exists, with a validated frame counter, a main-loop cost
split and the measured game-time model ([internals](internals.md)).

## Findings that shape the work

- World ticks per frame are the elapsed fields clamped to 4..8. The world runs in real
  time only between 6.25 and 12.5 fps; above 12.5 fps the original runs fast.
- Per-frame logic outside the tick loop, and the collision test that undoes a whole pass's
  movement, run once per main loop pass. Running passes at the render rate would change
  game behaviour even with one tick per field, so the pass rate must stay native.
- World logic costs about 1% of a frame on `a1200-fast`; drawing about 1.4 million cycles
  (5 fields). Decoupling alone therefore removes the speed-up, not the drawing cost: higher
  frame rates also need faster drawing (faster CPUs, code and CPU-only data out of chip RAM,
  renderer work).
- The slave's `_dmaon` waits for a vertical blank on every frame (14.7% of the CPU time)
  and leaves 12 of the frame's 34 copied bytes uncopied. The performance slave's `Custom1`
  bit 0 fixes both: 7.40 to 8.98 fps on `a1200-fast`, same build.
- In the shipped game, all code and data are in chip RAM, even with fast RAM fitted. On `a1200-fast`, 80%
  of the CPU's chip accesses are code fetches (50%), CPU-only data (21%) and the stack
  (7%); only the display buffers (20%) need chip RAM. The instruction cache hits about 43%
  of fetched longwords; 95% of the misses come from 18.5 KB of code.
- Measured on `a1200-fast`, one build, `Custom1=1` as the reference (8.93 fps): 64-bit
  bitplane fetch (bit 1) 9.45 fps, the stack in fast RAM (bit 2) 9.49, both 9.62. The A500
  is unchanged by both (FMODE is AGA-only; its slow RAM is chip-bus memory).
- The publication waits for the next field after each `COP1LC` write (7-10% of the CPU's
  time on `a1200-fast`): double buffering quantises frames to whole fields.
- No blitter, no misaligned longwords, the panel is not redrawn, interrupts cost 1.6%.

## Design: native logic passes, separate presentation frames

1. **Logic passes stay native.** Run the unchanged main loop pass (per-frame logic, n
   ticks, collision test) only when at least 4 fields have passed since the previous pass,
   with n = clamp(elapsed, 4, 8) as now. On a fast machine the world then advances exactly
   as on a native machine at 12.5 fps: one tick per field, input sampled per pass, the same
   collision granularity. Slower than 4 fields per frame, nothing changes.
2. **Presentation frames in between.** When fewer than 4 fields have passed, draw and
   publish only: stage presented poses into the renderer's inputs, run the drawing calls,
   then restore the committed state. Nothing in a presentation frame writes world state.
3. **Presented poses**, with alpha = fields since the last pass / the pass length:
   - the player and other objects are interpolated between the last two committed
     passes, on logic frames as well as extra frames;
   - camera and geometry share one alpha sampled after the publication wait. The display is
     one pass (80 ms at 12.5 Hz) behind logic, avoiding prediction overshoot when
     starting, stopping or colliding.
   Snap at teleports, transport changes, lifts and new objects.
4. **Publication**: at most one frame per field, as now (the game waits for the VERTB
   counter after each `COP1LC` write, which caps it at 50 fps PAL). `_dmaon`'s per-frame
   wait goes, with the copy restored.
5. Everything behind a `CUSTOMn` option; with it off, the original bytes.

## Decisions

- Bug fixes for shipped defects apply in both settings: Off keeps R5's 68040/060
  cache fix (user decision: "Fixing bugs is never a bad thing"). Off otherwise runs
  the shipped code, and stays the A500 options-off regression gate.

- The Enhanced framerate control is a boolean checkbox (user correction). The
  installer sets CUSTOM5=1 so it starts checked; CUSTOM5=0 or omission is unchecked.

- X1: player-facing **Enhanced framerate**, default on (user approval). No real
  hardware is available; finish X1 with emulator checks and record hardware cache
  behaviour and 040/060 speed as unverified.

- R4: support whatever caches can be supported (user decision before measurement).
  Retain the cache option for compatibility even if these emulator routes show no gain;
  real-hardware cache performance remains unverified (X1 accepted without hardware).

- P3: extend native-speed logic and smooth presentation frames to vehicles, flight
  and lifts (user approval). Check each mode and the deferred navigation/vehicle/flight screens.

- Use `CACHE PRELOAD` for normal and measured runs (user direction). PRELOAD was
  already enabled; `NOCACHE` remains available for explicit cache-off comparisons.

- Close R3 without implementing triple buffering: the user does not want it. Keep
  double buffering and continue to S6 (user decision after S5 measurements).

- The reference fast machine for the 50 fps path is the cycle-exact 68030/50
  (`030-default` cell) (user decision, S0). The 040/060 emulator cells only confirm the
  game runs there.

- Include the existing `040-25` matrix configuration in routine FPS comparisons,
  alongside `a1200-fast` and `a500-1.5m` (user decision). Keep that configuration;
  do not substitute the separate `a1200-040` preset.

- Combine M2 with R1 to investigate what limits the hot drawing loops (user decision).
  Measure table relocation and loop rewrites separately, then commit the combined step.

- Remove the fixed 2% gain cutoff (user decision: "2% is too high of a requirement").
  Retain changes with a repeatable measured gain and no measured regressions.

- Correct P1's restore check to allow normal interrupt-owned state to advance while
  checking that presentation code restores its changes (user decision). A publication
  probe advanced VERTB 178 → 179 and changed timers at chip `$7236` and `$727E`;
  an unchanged hash excluding display state alone would incorrectly reject this.

- Defer O1's map, vehicle and flight play checks until those modes are reached in
  later steps (user decision). P3 reached vehicles, flight, lifts and the A-to-Z
  navigation panel; no separate full-screen map was identified.
- Accept A3 despite the known 040 emulator frequency-timing limitation (user decision).
  Keep the frequency sanity advisory; no shared-emulator timing fix is required. The
  68030 MMU backend remains unchanged.
- P4: replace player prediction with interpolation following the user's report of
  start/stop jumps, uneven walking and mailbox flicker, and request to fix those
  defects. Use the same delayed timeline for player and objects; simulation stays
  native. This supersedes the earlier extrapolation design.
- Keep the 68030 MMU backend unchanged; route tools run untraced there (user request).
- The plan is practical, not formal: three checks (options off, world speed, play) plus
  P1's restore hash; heavier verification only to chase a fault (user direction).
- On fast machines logic passes run at the minimum native pass length, 4 fields (12.5 Hz).

## Measurement notes

- The S6 build (`Custom1=2047`) measures 24.80 fps on the reference 030/50 and
  24.90 on the 040/060 cells. Main 3D bypass reaches 49.60 on 030/040; all-drawing
  bypass reaches 49.60 on 060. Publication waits remain by the R3 closure decision.
  These are emulator measurements; see [S6](internals.md#s6-budget-checkpoint).

- Frame counts drift between sessions (the A500 route gave 38 frames, now 37, with the same
  slave), so compare builds only within one session.
- The 040/060 cells don't follow the configured frequency (118 frames at 8 and 25 MHz):
  emulator counts, not hardware speed.
- The 68030 runs with `DETERMINISTIC=0`; it has no instruction profile.

Details: [internals](internals.md#a3-machine-matrix).

## Current status

Phase F works toward one-field frames on the reference 030/50. F0 measured the budget:
frames take 24.9 ms of work on average (worst 27.4), against 20 ms per field. The
presentation copies cost 7.1 ms per presentation and the staging copy 3.3 ms. The CPU's
remaining chip-bus traffic, about 21,000 accesses per frame from chip-resident code,
game variables, render scratch and renderer data, costs an estimated 6..12 ms.

F3 is complete: 1,078 bytes of projection state, line masks and row offsets move
into spare fast workspace, with no allocation increase (268 KB). Same-build off/on
FPS, repeated twice: A500 4.10 → 4.10, 020-fast 13.30 → 13.50, reference 030/50
26.30 → 28.80, 040 emulator 25.00 → 26.50. Mean 030 frame work falls 21.61 →
20.76 ms; worst remains about 24.65 ms, so steady 50 fps is still out of reach.
The moved blocks lose about 400 chip reads and 16.5 writes per field on the 020.
Native speed, restore hashes, play, identical still images and options-off checks
pass. Enhanced framerate includes bit 18. Low-word-addressed/shared/model data
need broader relocation in F5. See [F3](internals.md#f3-hot-renderer-data-in-fast-ram).

F4 is complete: `bfffo` replaces the log conversion's compare tree in M1's copy, with
results identical to the original for every input (`tools/log_harness.py`, Unicorn).
Same-build off/on FPS, repeated twice: A500 4.10 → 4.10, 020-fast 13.50 → 13.70,
reference 030/50 28.80 → 29.60, 040 emulator 26.50 → 26.90. Mean 030 frame work falls
20.70 → 19.84 ms, worst 24.64 → 22.55 ms; 113 of 210 intervals still exceed a field.
Enhanced framerate includes bit 19. See [F4](internals.md#f4-log-conversion-with-bfffo).

F5 is complete. The render scratch (chip `$0340..$407F`) moves to fast RAM. The copied
code is translated by `tools/translate.py`: 544 scratch operands become 32-bit forms, and
its 16 blocks grow by 2,538 bytes. Every instruction is verified by re-decoding.
Optional workspace grows to 288 KB. Same-build off/on FPS, repeated twice:

| Setup | F5 off fps | F5 on fps |
| --- | ---: | ---: |
| A500 | 4.10 | 4.10 |
| 020-fast | 13.70 | 14.10 |
| Reference 030/50 | 29.60 | 48.00 |
| 040 emulator | 26.90 | 44.50 |

On the 030, mean frame work falls 19.85 → 15.60 ms and the worst 22.56 → 17.71 ms. No
interval exceeds a field, and 464 of 480 cadence intervals are one field. The
presentation copies fall to about 1.4 ms each. Game variables stay in chip, because
their accessors are spread across the untranslated main loop. Enhanced framerate
includes bit 20. See [F5](internals.md#f5-render-scratch-in-fast-ram).

F6 closes phase F. On the 030/50 the walk runs at 50 fps: frame work averages 15.6 ms
(worst 17.7) against 24.9 (worst 27.4) at F0, and every cadence interval from field 65
to 500 is one field. All eight matrix cells pass with all options: A500 4.10, chip-only
020 9.30, 020-fast 14.10, 030 48.00 (also with MMU), 040-25 44.50, 060-50 44.80 fps.
Options off equals shipped (37 A500 frames). The route's opening view, standing still for
175 fields, draws more than the walk: on the 030 its main 3D (7.3..9.0 ms) pushes 16
frames just past a field (worst 20.15 ms), and the 040 cell misses more. Main 3D is the
next reduction there; on the 020 it is computation in the drawing. See
[F6](internals.md#f6-checkpoint) and the
[plan](plan.md#f-one-field-frames-on-the-03050-the-50-fps-step).

The post-P5 68040 investigation measures 24.80 fps: steady frames spend about
25.6 ms working, then wait for the next field, producing two-field delivery.
Main 3D drawing costs 10.9 ms; bitmap copying, scene setup and presentation
save/restore also matter. A VERIFY-only bypass hook error is corrected; skipping
main 3D reaches 49.60 fps. Release behaviour is unchanged. See the
[current 040 frame budget](internals.md#68040-frame-budget-after-p5).

R5 fixes intermittent missing ground with caches enabled on 68040/060. The
outside-prison reproduction also fails in the shipped slave; it was not introduced
by P4. The mutable clipping instruction is replaced with a data comparison while
keeping caches enabled. Same-build captures show 10 missing-ground fields → zero
in 600 fields; routine FPS, native speed, restore and options-off checks pass.
See [R5](internals.md#r5-cache-safe-polygon-clipping).

P5 includes room-local XYZ in P4 camera interpolation. The prison wall camera now
advances on every rendered frame with the spiderweb; sampled repeated wall-edge
positions fall from 8/17 to 2/17 intervals. The separate door-animation timing is
unchanged. See [P5](internals.md#p5-room-local-camera-interpolation).

P4 corrects presentation transitions with a shared, delayed camera/geometry timeline;
starts, stops, reversals and the mailbox approach have been checked. Frame rates are
unchanged on the routine setups; native world speed and options-off checks pass.
See [P4](internals.md#p4-presentation-transitions). Release 2.0 (23.10.2026) has a
template-based WHDLoad ReadMe and installer, generated by `make release` under
`tmp/` with the original imager, icons and documentation. The release exposes **Enhanced framerate**,
default On. Off restores shipped behaviour, keeping only the 68040/060 cache fix. README includes installation, requirements,
memory fallback and options; the release was played on every supported CPU class.
Same-session route FPS Off → On: A500 3.70 → 4.10, 020-fast 7.50 → 12.50,
reference 030/50 8.90 → 24.80. The matrix, native world-speed and options-off checks
passed. See [X1](internals.md#x1-release).

No hardware is available. Real-hardware cache behaviour and 040/060 performance remain
unverified; the user explicitly accepted completing X1 without those tests. R2's blitter
clear remains rejected and R3's triple buffering remains closed without implementation.
