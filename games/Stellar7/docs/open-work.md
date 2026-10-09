# Stellar 7: current work

## Chosen design

Separate simulation timing from rendering. Use an explicit simulation clock;
rendering cost must not decide movement, AI, spawning, firing or power timers.
The initial opt-in implementation is in `whdload/timing.s` (`CUSTOM1=1`).
Its provisional default is five updates per second, based on the measured
A500 early scene. This is a reference choice, not proof of the designers'
intended pace. `CUSTOM2=1..25` chooses another fixed rate.

## Implemented

- Integer clock accumulator using the native VBL callback and Exec's 50/60 Hz
  field-rate value. Fractional credit is retained; no render-time timestep.
- Native simulation passes remain in order. Catch-up passes omit mesh drawing
  and presentation while retaining projection, star updates and shared RNG use.
- Native resume path resets elapsed-time credit after modal input.
- VERIFY-only native movement/firing route and reduced-presentation test.
- Optional VERIFY-only rendering delay; snapshots at later simulation steps.
- Separate simulation-completion and presentation counts, and a mapped-state
  comparator covering player, world/active objects, power timers, RNG and stars.

This is experimental and disabled by default. It does not generate interpolated
frames or run simulation in an interrupt. Residual HUD drawing remains in
catch-up passes; not all render work has been removed from them.

## Validation

The original stationary baseline is documented in `docs/internals.md`.
Moving/firing snapshots match mapped state at simulation steps 115, 140 and
160 between the timing-disabled route, fixed A500 and deliberately slowed
68020. The comparison includes visibility flags and object links, not just
player position. The 68020 half-presentation test also matches at step 115.

- Fixed A500: ten simulation completions / 100 PAL fields, about 5 fps.
- Final fixed 68020 build: independent read-only breakpoints confirm ten
  simulation completions / 100 fields and 5 fps; all three state checks match.
- 68020 drawing every second step: ten completions / 100 fields, 2.5 fps.
- 68020 with 20 fields of extra drawing delay: nine completions / 100 fields,
  about 1.9 fps. Across checkpoints 115–160 it starts 45 updates over 452
  fields (about 4.98 Hz). Clock-credit accounting is conserved exactly.

The slow draw blocks the main task, so updates catch up in bursts rather than
arriving at uniform wall-clock intervals. This preserves fixed simulation
increments but does not remove input latency caused by a long render.

## Remaining work

1. Test native pause, preferences, death, level transitions and new-game clock
   reset. Modal resume reanchors the clock; these paths are not yet playtested.
2. Establish full original/reconstructed-loader behavioral equivalence. The
   modern KickEmu loader is not a byte-identical reconstruction of the 2008 slave.
3. Validate NTSC execution and longer, heavier scenes. Broaden state coverage:
   the comparator intentionally excludes pointers and renderer scratch values.
4. Confirm the preferred gameplay cadence through playtesting/reference evidence.
5. Separate remaining presentation side effects, then consider interpolation
   and measured renderer optimizations. No rendering speedup is claimed.
