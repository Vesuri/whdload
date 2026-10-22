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
- All game code and data are in chip RAM, even with fast RAM fitted.

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

- The player's presented pose is extrapolated from the native per-tick rates; other
  objects are interpolated between the last two committed passes (the user's choice).
- On fast machines logic passes run at the minimum native pass length, 4 fields (12.5 Hz).

## Next steps

1. Classify the main loop's calls: drawing (`$577BE`, `$5410E`, `$5AFAA`, `$593A6`,
   `$5E840` candidates) versus logic, and find every renderer input: player pose, camera
   values derived per pass (such as chip `$42C6C`), object records, lifts and vehicles.
2. Prototype presentation frames for the player only on `a1200-fast`, behind a VERIFY
   check that committed world state at every logic pass equals the original game's at
   12.5 fps.
3. Make the entry breakpoint work on the 68030 (or anchor differently) and add
   `a1200-030` and `-NOMMU` 040/060 cells, where higher frame rates are reachable.
4. Evaluate moving game code and CPU-only data out of chip RAM on fast-RAM machines.
