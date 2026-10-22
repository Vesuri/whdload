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
- All game code and data are in chip RAM, even with fast RAM fitted. On `a1200-fast`, 80%
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

- The player's presented pose is extrapolated from the native per-tick rates; other
  objects are interpolated between the last two committed passes (the user's choice).
- On fast machines logic passes run at the minimum native pass length, 4 fields (12.5 Hz).

## Next steps

1. **Logic gating** at the main loop head (`$5E992`, a 6-byte `jsr`): with the option on
   and the walking mode active, run the native pass only once 4 fields have passed since
   the previous one, giving it that elapsed count in `$52954` so its tick count and
   velocity scaling are native; otherwise run a presentation frame. VERIFY control: the
   same gating with no drawing in between must give identical committed state.
2. **Presentation frame**: stage the extrapolated player pose in `$7142..$7161`, run the
   camera derivation and view setup, publish, clear and draw, then restore every byte the
   drawing chain writes outside the display (the audit's union: image variables, render
   scratch below the image, self-modified code words), except the display state that must
   follow the real screen: copper list pointers, buffer toggle, back buffer pointer and the
   copper list contents. Keep `$7180` at the logic-pass count so blinking keeps its rate.
3. **Player extrapolation** from the per-tick rates with the input held; snap to committed
   state at collisions, mode changes and position jumps.
4. Other objects: find their pose fields (object tables near `$AF36`, `$B31E`, the lists the
   drawing walks) and interpolate them between the last two passes.
5. Extend the audit to the other movement modes (vehicles, lifts) before enabling the
   option there; until then they run natively.
6. Make the entry breakpoint work on the 68030 (or anchor differently) and add
   `a1200-030` and `-NOMMU` 040/060 cells, where higher frame rates are reachable.
7. **Hot code into fast RAM** on a 68020+ with real fast RAM: the largest remaining chip
   cost (half of the CPU's chip accesses). Copy the hot routines (18.5 KB covers 95% of
   the fetches) and enter them through jumps; first redirect the renderer's writes to its
   own code words (the write audit lists them) to the copies, and check every absolute
   reference into the moved ranges. Then the CPU-only data the hot code reads.
8. Smaller candidates: clear the back buffer with the blitter while the CPU works
   (`$5E0E6` call, about 3.5% of a pass); triple buffering to drop the publication wait,
   which needs 32 KB of chip RAM beyond the 512 KB BaseMem (a user decision: it would drop
   512 KB chip machines); the data cache on 68030+ (the slave asks for the instruction
   cache only), measurable once the 68030 entry breakpoint works.
