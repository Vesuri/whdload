# Current status and limits

The release has a single **Enhanced framerate** checkbox (`CUSTOM1=1`), off by
default in the slave. The installer sets `CUSTOM1=1` in the game icon, so an installed
copy starts with it on (user decision). It enables fast planar rendering and fixed-step timing together on
68020+ with real fast RAM. Unchecked, on 68000/68010, or without real fast RAM,
both paths stay original and gameplay remains frame-dependent. CUSTOM3 is no
longer a user option. WHDLoad CACHE/DCACHE remain user-controlled.

The splash and `$VER` version is **2.0b (09.11.2026)**. The single-checkbox revision is built
and checked. Evidence is
under `tmp/release-opt-in/`: M7 enabled runs the scheduler and passes 29 completed
drawing twins; M7 unchecked, M3 checked without fast RAM and M2 checked on 68000
retain all original renderer/timing hook bytes. The normal splash has exactly one
checkbox. The original slave still rebuilds byte-identically.
The earlier Phase F gates below remain evidence for the implemented paths and
include the accepted stock A1200 Practice exception; their captures predate this
UI/default-selection change. Enhanced runs now require `CUSTOM1=1` explicitly.

The release installer text is maintained in `release/`. `make dist` packages it
(`release/release.json`) as `dist/PowerdromeEnhanced-2.0b-20261109.lha`, named from the
slave's `$VER` string. The installer writes `CUSTOM1=1` into the game icon. The earlier
hand-packaged archive is `tmp/Powerdrome-2.0.lha`
([packaging](development.md#release-installer-archive)). End-to-end AmigaOS Installer
execution, including that tooltype, has not been tested.

## Fine mouse steering

Implemented behind **Enhanced framerate**. Mouse rotation uses fractional rates
and a precise private orientation matrix, applied every 20 ms. Calibration gain is
unchanged; input/control decisions remain at 90 ms. The normal build is available
at `tmp/build/release/Powerdrome.Slave`.

- All 2,949,120 signed Q12 angles and 2,056 mouse/calibration combinations pass
  the assembly arithmetic checks. Ten-minute constant-turn tests stay within
  0.003 degree heading error and 0.011% matrix row-length error.
- Three single-count tapes (020, 060, and 060 capped to 10 Hz after 200 world steps)
  match all 499 common complete mouse/matrix states. Both axes turn in both
  directions; each capture has 126 between-control matrix changes and no overflow.
- Rejected turns, native matrix replacement, joystick fallback and session reset
  pass isolated assembly checks. The unchecked normal build and a checked-option
  A500/no-fast-RAM boot retain all native renderer/timing hooks in both name-screen
  snapshots. The 68000 never installs the new 68020 arithmetic.
- Normal, VERIFY, coverage and phase-instrumented builds assemble; original slave
  reconstruction remains byte-identical. The static patch-boundary audit passes.

Evidence is in `tmp/mouse-steering/`. [Timing design](timing-implementation.md#fine-mouse-rotation)
and [development](development.md#fine-mouse-steering-checks) describe the patch and
reproduction. This establishes precision, cadence and measured throughput; it is
not a subjective handling verdict or a repeat of all earlier release gates.

| Practice, 500 PAL fields | Complete intervals / fields | FPS |
| --- | ---: | ---: |
| A1200 + fast, NoCache, prior coarse mouse (`TIMING_MOUSE=0`) | 240 / 494 | 24.291 |
| A1200 + fast, NoCache, fine mouse | 238 / 494 | 24.089 |
| 060/50 + fast, NoCache, fine mouse | 455 / 499 | 45.591 |
| 060/50 + fast, CACHE, fine mouse | 490 / 499 | 49.098 |

The paired A1200 route is 0.833% slower with fine mouse integration. It is an
explicit cost of this feature, not a strict no-regression pass or an extension of
the earlier stock-A1200 exception. These runs contain no state probes, phase timer
or drawing twins. Their hunk placement matches. The full release matrix below
predates fine mouse steering and has not been repeated for it.

## Mouse stick

Part of **Enhanced framerate**; the unchecked and fallback paths are unchanged. The
enhanced input layer queues only the per-field mouse counts. Native writes to the stick
(contact damping, the A reposition and the other resets) reach the private stick the
controls read, and every stick sum saturates at ±32767. Before, a damped stick reversed
to full deflection after A. [Design](timing-implementation.md#inputs-pause-and-sessions).
`tools/check_input_axes.py` checks it and reproduces the old reversal with `--baseline`.
The 060 single-count mouse tape matches all 501 recorded mouse/matrix states.

A nose-first dive into the floor now crashes and repositions as in the original. Before,
the ship stayed pinned with the stick damped and the mouse ignored. A damped control update
uses native whole-degree rates. [Track collision](timing-implementation.md#track-collision);
`tools/check_collision_depth.py`. Not yet played by hand, and the release matrix has not
been repeated for these changes.

## Liftoff blending

Part of **Enhanced framerate**. One blended view is drawn between each pair of 100 ms
cockpit liftoff steps on 030/25 and 060/50 (20 instead of 10 presentations per second);
native states, step period and final state are unchanged.
[Design and measurements](timing-implementation.md#pit-departure-and-repair-display).
Not yet watched by hand, and the release matrix has not been repeated for this change.

## Pit arrival blending

Part of **Enhanced framerate**. The 15-step ship rise when the pit view opens is paced to
the A500's 100 ms per step (natively it ran 40% fast on 040/060 and 25% fast on 020/14),
and extra frames with blended heights are presented between steps: 24 instead of 15
frames on 040/25 and 060/50, about 16.7 fps, which is the pit frame's own limit of three
fields. [Design and measurements](timing-implementation.md#pit-departure-and-repair-display).
The pit departure (`$14764`, paced already), the rescue arrival (`$1464c`) and the `$102`
sprite flicker (`$145e2`) are still step-only. Not yet watched by hand.

## Release baseline measurements

All 20 measurements of the pre-steering release baseline are complete. The full intervals/fields, fps and mean
frame intervals are in [README](../README.md#release-measurements) and
[internals](internals.md#current-measurements). These compare the same modern loader
with the frozen native baseline, using uninstrumented 500-PAL-field driving windows.

| Machine | WHDLoad | Practice native → release fps | Race native → release fps |
| --- | --- | ---: | ---: |
| A500 | NoCache | 11.404 → 11.404 | 11.484 → 11.484 |
| A500 + fast | NoCache | 11.325 → 11.325 | 11.515 → 11.515 |
| Stock A1200 | NoCache | 15.423 → 15.392* | 16.364 → 16.364 |
| A1200 + fast | NoCache | 15.682 → 24.291 | 16.768 → 26.815 |
| 030/25 + fast | CACHE / NoCache | 19.556 → 38.978 | 21.328 → 42.742 |
| 040/25 + fast | CACHE | 36.948 → 49.098 | 32.696 → 50.000 |
| 040/25 + fast | NoCache | 17.907 → 45.291 | 19.960 → 46.192 |
| 060/50 + fast | CACHE | 40.481 → 49.098 | 33.367 → 49.900 |
| 060/50 + fast | NoCache | 17.907 → 45.792 | 20.020 → 46.687 |

*The user accepted the specific 0.201207% stock A1200 Practice shortfall:
153/497 versus native 153/496, reproduced exactly twice. It remains an exception;
all other throughput rows pass the strict no-regression gate. No baseline or general
tolerance was changed. Timing changes also change scene inputs, so route gains are
not isolated renderer speedups. These are emulator results, not physical-board claims.

## Pre-steering release gates

- Normal-build name-entry boots pass on M1/M3/M4/M7. M4/M7 have timing and static
  renderer hooks installed; fallback and disabled-option cases retain native hooks.
- M1/M3 defaults and M7 with both enhancements disabled pass original relocated renderer/timing
  hook-byte checks in initial and final snapshots. M3 gameplay also passes.
- M7 default gameplay in the matching input-only VERIFY build advances 501 world
  steps and completes 491 staged scenes during the window; timing records are active.
- M4 NoCache, M5 CACHE and M7 NoCache drawing twins pass 17/26/29 completed scenes,
  with zero pixel/register/CCR/scratch/guard failures and unchanged raster code.
- M6 CACHE production-path smoke reaches ordered pit/departure/track checkpoints
  and completes 100 staged scenes with unchanged raster code. It uses no twins.
- All timing patches carry range annotations; the static layout audit passes.
- Committed source rebuilds normal, VERIFY and coverage slaves byte-identically to
  the frozen release inputs. The original slave still matches its supplied reference.

Evidence: `tmp/phase-f/fast-required/`. `tools/release_matrix.py` is the current
sequential matrix runner; obsolete prototype wrappers and completion plans are
removed. [Development](development.md) describes reproduction. Historical work is in git.

## Design decisions

The user approved these when the completion plan was made:

- **A500:** representative behaviour, not exact matching of native A500 histories.
- **CPU split:** native timing on 68000/68010; the fixed-step scheduler on 68020+,
  selected at run time from AttnFlags.
- **No interpolation** between simulation states. Presentation-only blending is allowed
  where it keeps the original duration and final state; the user asked for it on
  09.11.2026 for the cockpit liftoff and the pit animations.
- **Bounded gates:** every check has a finite, stated bound. Open-ended exact matching
  against native histories is not a release gate.
- Changes worth under 3% of a frame are skipped. Caches stay under WHDLoad's own
  options. No performance claim without a measurement.

The plan originally switched the enhancements on automatically on 68020+, with opt-outs.
After the stock A1200 regression the user chose a single opt-in checkbox instead:
`CUSTOM1=1` is off by default in the slave and set in the icon the installer writes.

## Known limits and deferred work

- **Cached 060 twin reference:** the M7 CACHE twin capture fails pixel/register
  comparison; the NoCache retry passes. The verifier deliberately calls the native
  self-modifying polygon code, unlike the production static path. The failed capture
  is preserved and is not a pass. A specific cache/emulator instruction cause has not
  been isolated. Cached throughput and production smoke do not prove cached pixel
  equivalence. See [accelerator testing](accelerator-cache-testing.md).
- Enhanced timing assumes PAL; NTSC is not handled. Native fallbacks remain
  frame-dependent. Menus, external pit animation and title-camera playback stay native.
- Physical accelerator-board/cache certification is outside the selected scope.
- Steady A500 handling and unseeded natural-weather expiry/restoration were deferred
  by the user. Neither gate is passed, and their original bounds remain unchanged.

## Phase E gate ledger

| Gate | Accepted result |
| --- | --- |
| Cross-CPU state | Six captures match 501 common world states and 111 control/input/fuel updates |
| Lifecycle | Pause, restart, initialized-lap pause, rescue and natural ten-lap finish pass |
| Stalls | Observed 100/260/500 ms holds recover exact state with zero endpoint debt |
| Render cadence | Ten requested-rate/unpaced cases match 651 common states and 144 control/input/fuel updates |
| Endurance | 600-second pair matches 30,001 common world/RNG states and 6,666 control/input/fuel updates; zero endpoint debt |
| Visible weather | Directed fade/memory and three visible logical phases pass |
| Steady A500 handling | Deferred: acceleration passes; stop reference/fuel unresolved; straight-line speed not evaluated |
| Natural weather | Deferred: no episode in the ten-minute retry; expiry/restoration untested |

See [timing design and validation](timing-implementation.md) for contracts and accepted
native-history differences. Correctness-capture playback rates are not performance
results, and requested render rates are not claims of achieved scanout rates.
