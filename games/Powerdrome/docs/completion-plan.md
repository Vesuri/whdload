# Completion plan: smooth rendering and correct game speed on every Amiga

This plan finishes the performance and timing work and ships it. An agent can follow it
step by step. Each step has a **gate**. When the gate passes, commit and move on. When a
gate fails twice, write the finding into `docs/open-work.md` and stop for the user.
Do not add new verification work that the gates below do not ask for.

## Where the project stands

The complete Phase B baseline is in [Current measurements](internals.md#current-measurements):
60 uninstrumented route measurements, 14 separate phase captures and three frequency
sanity runs. These are emulator results; cache labels are requested WHDLoad options.

| Machine | Native fps | Fast planar fps | Full timing + fast fps | Cache |
| --- | ---: | ---: | ---: | --- |
| M1 A500 | 11.404 | 11.404 (fallback) | 10.465 | NoCache |
| M2 A500 + fast | 11.325 | 9.355 | 8.710 | NoCache |
| M3 stock A1200 | 15.423 | 15.392 (fallback) | 14.575 | NoCache |
| M4 A1200 + fast | 15.682 | 22.110 | 21.881 | NoCache |
| M5 030/25 | 19.556 | 30.221 | 31.552 | NoCache / CACHE |
| M6 040/25 | 17.907 | 41.566 | 41.984 | NoCache |
| M6 040/25 | 36.948 | 49.098 | 49.098 | CACHE |
| M7 060/50 | 17.907 | 42.986 | 42.886 | NoCache |
| M7 060/50 | 40.481 | 49.098 | 49.098 | CACHE |

These are Practice rates from 500 PAL fields at `$bc7c`, using `SWAP_ONLY`.
Timing changes motion, so comparisons represent route throughput rather than identical
scene workloads. The full interval counts, histograms and race results are in internals.

- **Rendering.** Fast planar rendering remains off by default. Its existing coverage
  campaign passed 30,623 twins. With CACHE, M7 now measures 50.000 fps on the race route
  and M6 measures 49.900. B1/B2 attribute the remaining time: rendering is the largest
  active cost; copy and HUD exceed the Phase C candidate threshold; presentation
  including LoadView is below 1% on M6/M7. At near-50 fps the handshake also provides
  display pacing, so its entire measured share is not available as a throughput gain.
  The A500 has not been sped up: its original track profile is 54% polygon rasterization,
  8.5% CPU fill and 9.6% Kickstart, with the blitter idle (0.24% of DMA slots).
- **Timing.** The normal `CUSTOM3` build contains only the 20 ms minimum delta and the
  cockpit liftoff pacing. The complete scheduler remains a compile-only prototype, consolidated by Phase A
  under `TIMING_FULL=1`: the 20 ms world tick (`TIMING_WORLD20`),
  90 ms controls, carried movement remainders, logical opponents, laps, messages, repair
  pacing and weather. Cross-CPU logical equivalence and pause/rescue/restart regressions
  pass. Work stalled on gates that ask for an exact match with native A500 *histories*,
  and those cannot pass: the native A500 is itself scene-dependent. In the brake audit the
  A500 slowed to 160 ms frames and ended at speed 108, against 53 at a steady cadence.
  Native impulses lasted 800, 900 and 1,120 ms. Pilot 1's visibility differs.
- **Lesson from other projects.** Stellar 7 stalled the same way, in an open-ended
  validation spiral on a tick rate the A500 could not sustain. Test Drive II and Legends
  of Valour shipped because they bounded the work. They chose a tick rate the slowest
  machine sustains, kept native behaviour on the 68000 where the replacement measured
  worse, enabled rendering optimizations automatically where they measured better, and
  checked a fixed set of gates.

## Decisions (confirmed by the user)

| # | Decision | Reason |
| --- | --- | --- |
| D1 | **Reference policy: representative A500 handling.** Fixed 20 ms world ticks and 90 ms control/resource/engine/opponent epochs, the cadences already measured. Scene-dependent A500 slowdown is not reproduced. | The goal is that the game always feels the same. Native A500 histories are a tolerance reference on steady routes, never an exact oracle. The brake (108 vs 53), impulse (1,120 ms) and pilot 1 visibility differences are expected results of this policy. Document them and do not gate on them. |
| D2 | **68000/68010 keep native timing; 68020+ uses the world scheduler.** B3 retains this decision: full timing loses 8.23% fps in Practice and 6.64% in race, above the 3% limit. | The A500 is the reference, so native timing on it is correct by definition. On the measured Practice route its frame deltas (60–160 ms) never reach the 40 ms clamp. LoV's fixed tick cut A500 fps by about 60%, and TD2 kept the native period on the 68000. |
| D3 | **Ship defaults: fast planar on for 68020+ with real fast RAM, and the world scheduler on for 68020+.** The options become opt-outs: `C1` original renderer, `C3` original timing. | This is the LoV release shape. On the 68000 the renderer measures slower (9.36 vs 11.33 fps), so it stays off there. |
| D4 | **No render interpolation.** | The world tick (20 ms) equals the PAL field, so every 50 fps frame shows a new tick, and at lower rates every frame shows the latest tick. Interpolation would add latency for no visible gain. |
| D5 | **Finite gates.** Use only the gates in this plan. New checker scripts are allowed only when a listed gate cannot be evaluated without one. | This stops the validation spiral. |

The user has confirmed D1–D5, including the D3 defaults.

## Operating rules for the agent

- Follow AGENTS.md. Never commit game bytes or captures. Use `fsuae_common.sh`, never
  `pkill`. Run one capture at a time with `JOY0=none`. Put all output under `tmp/`.
- **Instruments.** Measure fps only with `SWAP_ONLY=1`, 500 fields from `$bc7c`, through
  `tools/fixed_window.sh`, and report intervals/fields as well as fps. For changes too small
  to show in fps, use cycles per completed call from a 68020 instruction trace or VERIFY
  twins. Use the guest phase timer from step B1 on 030/040/060, because those emulator
  backends give no instruction trace. Skip any candidate worth under 3% of a frame.
- Record the cache state with every 020+ figure. Measure both `NoCache` and WHDLoad
  `CACHE`, because users run with caches on. Sanity-check 040/060 speed at 8 MHz against
  25/50 MHz.
- Do not read `docs/timing-implementation.md` in full (4,500 lines). Grep it for the
  section you need.
- Commit as `Vesa Halttunen <vesuri@jormas.com>`, unsigned, with `-c core.hooksPath=/dev/null`,
  no Co-Authored-By lines, one commit per step group below.

### Machine set (`M1`–`M7`)

All use `source amiga/env.sh`. On M5–M7, add to `EXTRA_ARGS` the cycle-exact options
`--uae_cpu_speed=real --uae_cpu_multiplier=0 --uae_cpu_frequency=HZ --uae_cpu_cycle_exact=true`.

| Id | Machine | Variables |
| --- | --- | --- |
| M1 | A500 | defaults of `fixed_window.sh` (68000, 512 KB chip, 1.5 MB slow) |
| M2 | A500 + fast | `FAST_KB=4096` |
| M3 | Stock A1200 | `AMIGA_MODEL=A1200 CPU=68EC020 KICKSTART=$KICKSTART_A1200 CHIP_KB=2048 FAST_KB=0 EXTRA_ARGS=--slow_memory=0` |
| M4 | A1200 + fast | M3 with `FAST_KB=4096` |
| M5 | 030/25 | M4 with `CPU=68030`, HZ=25000000 |
| M6 | 040/25 | M4 with `CPU=68040-NOMMU`, HZ=25000000 |
| M7 | 060/50 | M4 with `CPU=68060-NOMMU`, HZ=50000000 |

Routes: Practice `CUSTOM5=2` (VERIFY build) and coverage race `CUSTOM5=4` (coverage build),
which has opponents on screen and is the heavier scene.

## Phase A: Consolidate the timing prototype (no behaviour change)

Status: **A1 and A2 complete**, byte-equivalence gates passed. Phase B is also complete; Phase C is in progress and Phases D–F remain untouched.
See [open work](open-work.md) for the exact configuration and file hashes.

**A1. Pick one release configuration.** Find the flag set behind the most recent complete
prototype: the `timing-weather-cycle-cadence2` slave. It includes WORLD20, input, engine,
repair with drop, laps, messages and weather. The flags are in the commit messages and in
`timing-implementation.md` around the matrix and weather sections. Put that set, with every
`*_TEST` and seed fixture off, behind one umbrella symbol, `TIMING_FULL=1`, in `timing.s`.
Turning it on must set the existing symbols, so the individual flags keep working for now.
*Gate:* `TIMING_FULL=1` in a coverage build produces the same bytes as the existing
per-flag build of cadence2, minus its fixtures. `make -C whdload all` stays byte-identical
to the current normal build.

**A2. Delete what nothing ships.** Remove the code paths that the release configuration
never assembles: the 90 ms-only `TIMING_WORLD` pilot mode (where WORLD20 replaces it),
`TIMING_MOVE_CLOCK`, uniform repair pacing without drop, the deferred weather sound path,
and any flag whose only use is a superseded experiment. Keep the VERIFY fixtures that the
gates below reuse: pause, sessions, rescue, stall, render rate, pit sync and seeds. Delete
the `tools/check_*.py` scripts that only check removed paths. *Gate:* the `TIMING_FULL=1`
coverage build and the normal build are byte-identical before and after the deletion,
which proves that only dead code went. Commit: "Consolidate timing prototype into one
release configuration".

## Phase B: The instrument and an honest baseline

Status: **B1–B3 complete**. B1 phase/trace disagreement is at most 0.00571%
(2% gate); normal and uninstrumented full coverage bytes are unchanged. All 77 B2
captures are complete, all six existing native references match exactly, and all
8 MHz checks are slower. B3 measures 10,357.86 mean / 18,778 p95 cycles per complete
A500 world body; the 8.23% Practice fps loss retains D2's native 68000/68010 timing.
See [Current measurements](internals.md#current-measurements) and [open work](open-work.md).
Phase C is now in progress.

**B1. Guest phase timer (VERIFY only).** Add a ring of `PDPHASE` records. Each holds the
VBL count, `VPOSR`/`VHPOSR` and a phase id, written at hooks that already exist, plus these:

- world scheduler begin and end, with the tick count;
- render entry at `$10df2`;
- the VBL handshake wait at `$112a6`, entry and exit;
- staged copy begin and end;
- HUD at `$d8ea`;
- timer at `$f0dc`;
- present at `$8056`, entry and exit, around LoadView.

Read the beam position twice, the way TFH does it. Add `tools/phase_report.py CAPTURE`. It
reports milliseconds per frame per phase (mean and 95th percentile) and the frame-interval
histogram (1, 2, 3+ fields). *Gate:* on M4 the phase totals agree within 2% with the
instruction-trace attribution of the same window. The normal build stays unchanged.

**B2. Baseline matrix.** Run M1–M7 × {native, `CUSTOM1=1`, `CUSTOM1=1` with `TIMING_FULL`}
× {Practice, race}. On M5–M7 run both `NoCache` and `CACHE`, then add the B1 phase capture
on M4–M7. Write one table into `docs/internals.md`, under "Current measurements": fps,
intervals/fields, field histogram, cache state, and phase breakdown for M4–M7.
*Gate:* the table exists, the native numbers reproduce the earlier ones within one
interval per 500 fields, and the 8 MHz sanity runs are slower.

**B3. Simulation capacity on the 68000.** On M1, from a full trace, measure the cycles per
completed 20 ms world step, and the fps with `TIMING_FULL` on and off. *Decision gate for
D2:* if the M1 fps loss is above 3%, the 68000 keeps native timing, which is the default.
Commit B1–B3: "Add frame phase timer and baseline performance matrix".

## Phase C: 50 fps on 68020+ with fast RAM

Status: **in progress**. C1 passes and is retained. C3 is assessed with no change:
copy already uses aligned MOVEM blocks, HUD exceeds the staging extent, and LoadView
is below threshold. C2 and C4 remain. See [measurements](internals.md#phase-c-measurements-and-decisions).

Work through these in order of their B2 phase share. Measure each one on M4–M7 and keep it
only if it measures better.

**C1. Overlap the flip wait with fast-RAM drawing.** This is the main hypothesis for the
~43 fps ceiling. `$8056` calls LoadView, and the renderer then waits at `$112a6` for the
VBL that makes the new view visible before it draws into the old front buffer. Once
staging is active the scene is drawn into fast RAM, so the wait is only needed before the
first write to chip RAM, which is the staged copy. Move it there in the `planar.s` wrapper.
With a frame workload of T ms between 20 and 40, frames then take about T ms instead of
being forced to two fields. No buffer is added, so latency does not grow (I500's user
rejected triple buffering for that reason). Before the change, list every write into the
chip back buffer between render entry and present: run the code-write/effective-address
audit on an M4 trace, including weather effect draws at `$112f4`. A write that happens
before the copy needs the wait moved only after it. *Gate:* twins are clean on M4/M5/M7
(`perf_status.py`, 100 fields), the beam position at copy start is always after the
handshake VBL (B1 records), and fps improves on M5–M7.

**C2. Remove native self-modifying code on 68020+.** With `C1` on, unsupported scenes (pit,
title, views) still use the native rasterizer. It rewrites the branch displacements at
`$16080`/`$1608a` on every polygon, which is unsafe with 040/060 copyback caches on real
hardware, and the emulator does not model that. The fast static-dispatch rasterizer writes
to whatever bitmap the caller passes, so route those calls through it as well, drawing
directly into chip RAM, whenever the fast code is installed. *Gate:* `audit_code_writes.py`
on an M4 Practice trace (pit, departure and track) reports no game-code writes. Twins are
clean, and pit/title screenshots are unchanged.

**C3. Chip copy, HUD and LoadView.** Act on these only if B2/B1 shows one of them at 3% or
more of a frame on M6/M7. Copy: make sure longword alignment and `MOVEM` blocks are used on
AGA. Do not use `MOVE16` to chip RAM. HUD: draw in fast staging if `$d8ea` writes only
inside the copied extent, otherwise leave it. LoadView: measure its cost through KickEmu
before considering a narrower replacement. *Gate:* each retained change measures 3% or
better and keeps twins clean.

**C4. Stock A1200 without fast RAM (M3).** The fast code is installed only into fast RAM.
Try installing the static-dispatch rasterizer (only the code, not the bitmap) into chip RAM
when no fast RAM exists. Its loops fit the 020 instruction cache. *Gate:* M3 measures 3% or
better with `CACHE`, and twins are clean. Otherwise drop it.

Commit each retained item separately, for example "Overlap flip wait with fast-RAM drawing".

## Phase D: A500 (68000, chip only)

The aim is no regression and a correct feel. 50 fps is not reachable with this renderer on
a 7 MHz 68000. Judge candidates by cycles per completed frame on a fixed-input M1 route,
because game time depends on frame time there.

- **D1. Blitter background fill.** At render entry, start a blitter fill of the four planes
  over the clear extent, so it overlaps the CPU transform and clipping. Wait for the blitter
  before the first polygon write. The upper bound is the 8.5% CPU fill share, less blitter
  contention.
- **D2. Kickstart share on track (9.6%).** Attribute it per call (LoadView, interrupt
  server, other) from the existing A500 trace. Act only on a single item worth 3% or more.
- **D3. 68000 span loops in chip RAM without branch rewriting.** Try this only if a twin
  measurement shows 3% or more. The earlier 68000 refinement failed its gate.

*Gate per candidate:* 3% or better, M1 twins clean, fps not lower. If none passes, record
"A500 unchanged at N fps" with the measurements and move on, as TD2 did at 7.1 fps.

## Phase E: Close the timing work under the D1 policy

**E1. Replace the unbounded gates.** In `docs/timing-implementation.md`, rewrite the
acceptance section as the release gates below. Mark the brake-history, impulse-history
and pilot 1 visibility differences as accepted policy outcomes. Treat opponent word `$54`
as presentation-owned, recomputed by every projection. Do not change cadences, tolerances
or code in this step.

**E2. Run the release gates once on the `TIMING_FULL` build.** Use the existing fixtures
and checkers only:

| Gate | Route and check | Machines |
| --- | --- | --- |
| Cross-CPU logical equivalence | `timing_cpu_matrix.sh` with pit sync | M5, M6, M7 (and M1, M4 when D2 enables timing there) |
| Equal elapsed time accounting | `check_timing_world20.py` and `check_timing_capacity.py` on every run above | same |
| Steady A500 tolerances | Existing frozen bounds: straight-line speed within 5%; acceleration to 130 and stop within 10% or 90 ms; fuel within 10%; weather onset, duration and fade within 10% | M5 vs native M1 |
| Pause, rescue, restart, finish | `CUSTOM5=8`, `13`, `12`, `14` and natural ten-lap finish with their existing checkers | M5 |
| Stalls | 100/250/500 ms stall fixture, no lost or duplicated work | M5 |
| Render-rate independence | 10/15/25/50 Hz fixture plus unpaced | M5, M7 |
| Endurance | 600 s pair, debt bounded, zero at end | M5 (and M1 if timing is on there) |
| Weather on screen | One directed fade: screenshots at three logical phases match the Copper palette expected for that phase | M5 |
| Natural weather race | 10 min unseeded race: no debt growth, effects expire, palette restored | M5 |
| Renderer twins | All of the above with `CUSTOM4=1` report zero mismatches | M4, M5, M7 |

*Gate:* every row passes. A failure is fixed in code or escalated. Never weaken a tolerance
to make a row pass.

**E3. Title demo pacing (small, optional).** `$107d6` advances the recorded camera by 2 per
rendered frame, so the demo plays faster on every machine faster than the A500. Advance it by elapsed PAL fields
at the measured A500 rate (18 frames per 93 fields) with a carried remainder. *Gate:* the
demo duration on M7 is within 5% of M1.

Commit E1–E3: "Close timing gates under representative A500 policy".

## Phase F: Integrate, set defaults, release

**F1. Promote.** Make the `TIMING_FULL` code part of the normal build behind the timing
option. Every hook carries its `TIMING_RANGE` comment. *Gate:* `check_disabled.py` proves
native bytes with the option off, on M1 and on M7.

**F2. Defaults (D3).** At install time, read
`WHDLTAG_ATTNFLAGS_GET` and the real fast RAM test that `reserve_arena` already does.
Enable fast planar on 020+ with real fast RAM, and the scheduler on 020+ (and on the 68000
too if B3 allowed it). Change `slv_config` to opt-outs:
`C1:B:Original renderer;C3:B:Original timing;`. Update `slv_info` and `slv_Version` as needed.
*Gate:* the normal build boots to name entry on M1, M3, M4 and M7. M1 with default options
has native hook bytes. M7 with default options has staging and the scheduler active (perf
and timing status records).

**F3. Release matrix.** Use the final normal build plus the matching VERIFY build. Run
M1–M7 Practice and race fps (`SWAP_ONLY`, with `CACHE` on 030+), and twins on M4/M5/M7.
Add one `CACHE` run on M6 through pit, departure and track as a self-modifying code smoke
test, and the no-fast-RAM fallback on M3. *Gate:* no machine is slower than its B2 native
figure. Put the final table in `README.md` and `docs/internals.md`.

**F4. Docs to current state.** Rewrite `docs/open-work.md` as a short status: what ships,
the measured table and the remaining limits (NTSC not handled, real-hardware cache testing
not done, menus/pit animations native). Cut `docs/timing-implementation.md` to the design
and gates (aim under 400 lines). Fold `framerate-independence.md` and `performance-plan.md`
into it or delete them, delete this plan, and leave the history to git. Delete unused tools.
Remove the "paused" banners. *Gate:* `make -C whdload original` still matches the shipped
slave, and no doc references a deleted file.

Commit F1–F2 ("Ship timing scheduler and automatic renderer selection") and F3–F4
("Record release measurements and current documentation") separately.

## Expected outcome (targets, not claims)

- 040/060 with fast RAM: 50 fps on Practice is the target of C1. Heavy race scenes may stay
  below 50 if chip RAM is the limit, as I500's heavy views stayed at 25.
- 030/25: above the current 30 fps after C1.
- 020 + fast: at or above 22 fps.
- A500: unchanged or slightly faster, with original timing.
- On every 020+ configuration the same world ticks advance at the same real-time rate, so
  speed, handling, fuel, opponents and weather do not depend on frame rate.

Report the measured figures from F3, not these targets.
