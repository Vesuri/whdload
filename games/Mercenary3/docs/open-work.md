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
   - the player is extrapolated from the native per-tick rates (walking 6 units, turning
     2 heading units per tick with the input held): no added delay; it can overshoot when
     the player stops, turns back or collides, and snaps back to committed state then;
   - other objects are interpolated between the last two committed passes: never an
     uncommitted pose, one pass (80 ms) of display delay.
   Snap at teleports, transport changes, lifts and new objects.
4. **Publication**: at most one frame per field, as now (the game waits for the VERTB
   counter after each `COP1LC` write, which caps it at 50 fps PAL). `_dmaon`'s per-frame
   wait goes, with the copy restored.
5. Everything behind a `CUSTOMn` option; with it off, the original bytes.

## Decisions

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
- The player's presented pose is extrapolated from the native per-tick rates; other
  objects are interpolated between the last two committed passes (the user's choice).
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

## Next steps

Phase S and P1–P3 are complete; R3 is closed without implementation by user decision.
P3 extends native-rate logic and presentation to vehicles and flight, preserves lift
arrival timing and closes the deferred vehicle/flight/navigation play coverage. The
030 Eagle view retains 50 fps with 12.5 logic passes/s; the standard route remains
24.80 fps. Options-off matches shipped. See [P3](internals.md#p3-vehicles-flight-and-lifts).
R2's blitter clear was measured and rejected: A500 unchanged, chip-only A1200 slower,
including a repeated blitter-priority trial. Keep the native CPU clear.
Next is R4's data-cache decision (U). See [plan.md](plan.md).
