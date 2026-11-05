# Current status and limits

The release has a single **Enhanced framerate** checkbox (`CUSTOM1=1`), off by
default. It enables fast planar rendering and fixed-step timing together on
68020+ with real fast RAM. Unchecked, on 68000/68010, or without real fast RAM,
both paths stay original and gameplay remains frame-dependent. CUSTOM3 is no
longer a user option. WHDLoad CACHE/DCACHE remain user-controlled.

The splash version is **2.0 (13.10.2026)**. The single-checkbox revision is built
and checked. Evidence is
under `tmp/release-opt-in/`: M7 enabled runs the scheduler and passes 29 completed
drawing twins; M7 unchecked, M3 checked without fast RAM and M2 checked on 68000
retain all original renderer/timing hook bytes. The normal splash has exactly one
checkbox. The original slave still rebuilds byte-identically.
The earlier Phase F gates below remain evidence for the implemented paths and
include the accepted stock A1200 Practice exception; their captures predate this
UI/default-selection change. Enhanced runs now require `CUSTOM1=1` explicitly.

## Release baseline measurements

All 20 release baseline measurements are complete. The full intervals/fields, fps and mean
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

## Completed release gates

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
