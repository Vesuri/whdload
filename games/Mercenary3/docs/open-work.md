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

- Off keeps the original game's behaviour, not the shipped slave's (user decision:
  "Our intent is not to keep the old slave's behavior intact when the enhancements are
  off but to keep the original game's behavior intact"). Fixes for shipped-slave defects
  apply in both settings: bit 0 (`_dmaon`'s short palette copy and per-frame field wait)
  and bit 15 (R5's 68040/060 cache fix). Off otherwise runs the shipped code.

- The Enhanced framerate control is a boolean checkbox (user correction).
  CUSTOM5=1 checks it; CUSTOM5=0 or omission leaves it unchecked.

- 2.0b archive: exactly the original installer archive's files, with the slave and
  ReadMe replaced (user direction) and `CUSTOM5=1` added to the two game icons so
  Enhanced framerate is on by default (user decision). The Install script is unchanged.

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

These counts predate a correction: F5 translated one read of the edge byte array at
`$4070..$416F` (Disk.1 `$593D6`) and dropped edges, giving a dotted or gray ground line.
Corrected, the 030 measures 27.60 → 44.70 fps in one session; the other rows and F6's
figures are from the uncorrected build. F2 also no longer relocates the four doorway
`lea $97DC,a1`: their table lies outside the copy, and the player stuck on the first
room's doors.

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

Since F6, Off keeps the original game's behaviour rather than the shipped slave's: it
keeps bit 0 (`_dmaon`) and bit 15 (R5). The A500 Off count rises from the shipped 37 to
41 frames, equal to VERIFY with bits 0 and 15; the options-off check now compares
those. See [Off](internals.md#off-original-game-behaviour).

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

P6 (bit 21) draws door motion on P4's timeline. Doors move one unit per tick, but
natively the drawn door jumped a pass's four units at 12.5 Hz. At the prison cell door
on the reference 030 its edges now change on 140 frames of one or two pixels instead of
34 of about five; restore checks pass and the route measures 44.70 → 44.50 fps. See
[P6](internals.md#p6-door-motion-on-the-presentation-timeline).

P7 (bit 22) turns the passenger-ship cockpit with the full camera angles. Natively its
heading, pitch and roll used 256 steps against the view's 1024, so it swung by
`angle & 3` and snapped back. In the slot 1 flight the console edge now holds one
position through the turn (five before), the pitch phase (four rows before) and the
roll phase (two). See [P7](internals.md#p7-camera-attached-model-angles).

P8 (bit 23) transforms camera-attached vertices exactly. The view's log-table
arithmetic left the cockpit flickering one pixel and back while the angles changed,
most visibly while banking. In the slot 1 flight the canopy's horizontal line now holds
through pitch and bank (7 one-frame reversals before), and the turn no longer moves it.
See [P8](internals.md#p8-exact-camera-attached-vertices).

Bit 24 paces passenger-flight replays at eight fields a pass. The trip is a fixed
number of logic passes, and the release ran them one per field on the 030: the slot 1
flight landed after 21 seconds and the pilot talked for at least 99 seconds more. It now
lands after 148 seconds, as the pilot finishes, close to the A500's 185. See
[P3](internals.md#p3-vehicles-flight-and-lifts).

Bit 25 moves traffic at the A500's speed. Vehicles step a fixed distance per logic
pass, so at the release's 12.5 Hz they drove 2.6–3.3 times faster than on the A500, and
the slot 3 taxi reached Metis Spaceport after 38 seconds while the driver talked for another
minute. Steps now scale with elapsed fields against the A500's ten a pass: the taxi takes
101 seconds (A500 99.5) and the driver's farewell follows the stop. The standard route
loses 41 frames because a vehicle now stays near the prison exit for longer. See
[P9](internals.md#p9-traffic-at-the-a500s-speed).

P4 corrects presentation transitions with a shared, delayed camera/geometry timeline;
starts, stops, reversals and the mailbox approach have been checked. Frame rates are
unchanged on the routine setups; native world speed and options-off checks pass.
See [P4](internals.md#p4-presentation-transitions). Release 2.0b (04.11.2026) is
`dist/Mercenary3-2.0b.lha`, made by `make dist`: the original installer archive with the
new slave, a template-based ReadMe and CUSTOM5=1 in the game icons. The release exposes
**Enhanced framerate**, default On. Off keeps the original game's behaviour, with the shipped slave's defects fixed. README includes installation, requirements,
memory fallback and options; the release was played on every supported CPU class.
Same-session route FPS Off → On: A500 3.70 → 4.10, 020-fast 7.50 → 12.50,
reference 030/50 8.90 → 24.80. The matrix, native world-speed and options-off checks
passed. See [X1](internals.md#x1-release).

No hardware is available. Real-hardware cache behaviour and 040/060 performance remain
unverified; the user explicitly accepted completing X1 without those tests. R2's blitter
clear remains rejected and R3's triple buffering remains closed without implementation.

## To investigate

- Save message stays on screen. After HELP, F1, a digit and Return, Benson's
  "PRESS RETURN WHEN READY" stays in the message line until another message replaces
  it, though the game keeps running and the save file is written (it appears when
  WHDLoad quits and loads correctly). Seen in the release slave with `CUSTOM5=1` on
  `a1200-030`, for saves in flight, hovering and on the ground. Possibly the interaction
  between `_savegame` (patch at `$5F26`) and the game's message handling; not yet
  checked against the shipped slave or with options off.
- Enclosed rooms run at 12.5 fps. `_presentgate` (label `.screen`) skips presentation
  frames while the room word `$71CC` is not negative, so inside enclosed rooms only the
  4-field logic passes are drawn. Same VERIFY build with `CUSTOM5=1` on `a1200-030`,
  displayed-frame counter, saves in the Eris 15-15 Mineral Trading building: in the
  corridor behind the salesperson (`$71CC` = 1) 12.50 fps standing and through a full
  turn, every 10-field window one frame per 4 fields; in the trading room, open to the
  street (`$71CC` = `$8000`), 50 fps standing and 44 turning. The player sees the drop as
  a bad frame rate in buildings. The check dates from the first presentation commit
  ("special screens keep their native path"), later relabelled "enclosed rooms" with no
  recorded reason or measurement. Six other `$71CC` checks follow the same rule:
  `_stageclear`, `_stagepublish`, `_objectdraw`, `_doorstage`, `_interpolateplayer`
  and `_present`. Find out why
  rooms were excluded: if there is a good reason, document it; otherwise draw
  presentation frames in rooms, with the restore checks passing there.
