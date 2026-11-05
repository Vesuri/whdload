# Powerdrome

Performance and timing improvements for the Amiga PAL release. Enable the
**Enhanced framerate** checkbox (`CUSTOM1=1`) to use fast planar rendering and
fixed-step gameplay together on **68020+ with real fast RAM**. It is off by default.
Unchecked, or on unsupported machines, both rendering and timing remain original
and frame-dependent. There is no separate timing option; WHDLoad CACHE/DCACHE
remain user-controlled.

The renderer draws the original planar graphics in fast memory, then copies the
scene to chip memory. Gameplay uses 20 ms world steps and 90 ms control epochs on
the enhanced path. There is no chunky conversion or render interpolation.

```sh
make -C whdload all
CPU=68030 FAST_KB=4096 WHD_ARGS=CUSTOM1=1 SLAVE=tmp/build/Powerdrome.slave amiga/run.sh
```

The launcher otherwise defaults to a 68000 and the installed original slave.
See [development](docs/development.md) for setup, CPU configuration and testing.

## Release measurements

These measurements precede the single-checkbox UI change. Enhanced runs now
require `CUSTOM1=1` explicitly.
They are FS-UAE PAL route measurements over 500 fields from the first driving
presentation (`$bc7c`), counted with read-only breakpoints. FPS uses complete
first-to-last presentation intervals. Builds have no phase instrumentation or
renderer twins during these measurements; VERIFY/coverage supply native inputs.
The reference uses the same modern loader with native timing and rendering.
Timing changes also change motion and scene inputs, so these are end-to-end route
comparisons, not identical-scene renderer speedups or physical-board predictions.

| Machine | WHDLoad | Route | Native intervals/fields | Release intervals/fields | Native → release fps | Release ms/frame |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| M1 | NoCache | Practice | 104/456 | 104/456 | 11.404 → 11.404 | 87.69 |
| M1 | NoCache | Race | 113/492 | 113/492 | 11.484 → 11.484 | 87.08 |
| M2 | NoCache | Practice | 106/468 | 106/468 | 11.325 → 11.325 | 88.30 |
| M2 | NoCache | Race | 114/495 | 114/495 | 11.515 → 11.515 | 86.84 |
| M3 | NoCache | Practice | 153/496 | 153/497 | 15.423 → 15.392* | 64.97 |
| M3 | NoCache | Race | 162/495 | 162/495 | 16.364 → 16.364 | 61.11 |
| M4 | NoCache | Practice | 154/491 | 240/494 | 15.682 → 24.291 | 41.17 |
| M4 | NoCache | Race | 166/495 | 266/496 | 16.768 → 26.815 | 37.29 |
| M5 | CACHE | Practice | 194/496 | 389/499 | 19.556 → 38.978 | 25.66 |
| M5 | CACHE | Race | 212/497 | 424/496 | 21.328 → 42.742 | 23.40 |
| M5 | NoCache | Practice | 194/496 | 389/499 | 19.556 → 38.978 | 25.66 |
| M5 | NoCache | Race | 212/497 | 424/496 | 21.328 → 42.742 | 23.40 |
| M6 | CACHE | Practice | 368/498 | 490/499 | 36.948 → 49.098 | 20.37 |
| M6 | CACHE | Race | 325/497 | 499/499 | 32.696 → 50.000 | 20.00 |
| M6 | NoCache | Practice | 178/497 | 452/499 | 17.907 → 45.291 | 22.08 |
| M6 | NoCache | Race | 198/496 | 461/499 | 19.960 → 46.192 | 21.65 |
| M7 | CACHE | Practice | 404/499 | 490/499 | 40.481 → 49.098 | 20.37 |
| M7 | CACHE | Race | 333/499 | 498/499 | 33.367 → 49.900 | 20.04 |
| M7 | NoCache | Practice | 178/497 | 457/499 | 17.907 → 45.792 | 21.84 |
| M7 | NoCache | Race | 199/497 | 465/498 | 20.020 → 46.687 | 21.42 |

*The user accepted M3 Practice's specific 0.201207% shortfall: 153/497 versus
153/496. A fresh retry reproduces the entire field sequence exactly. This remains
an exception, not a strict pass or a general tolerance. The other 19 comparisons
meet the strict gate. Machine/memory, emulator and ROM settings match their native
references. Evidence is under `tmp/phase-f/fast-required/`; native references remain
under `tmp/phase-b/`.

M1/M2 are A500 without/with fast RAM; M3/M4 are A1200 without/with fast RAM.
M5 is 030/25, M6 040/25 and M7 060/50, all with 4 MiB fast RAM. Full settings are
in [internals](docs/internals.md#measured-machine-configurations).

## Scope and validation

Release gates are complete within the agreed scope; see [status and limits](docs/open-work.md).
The cached 060 twin reference failed comparison; its NoCache retry passed. Cached
throughput is not a claim of cached pixel equivalence.
Enhanced timing assumes PAL. Menus, external pit animation and title-camera playback
remain native. Steady A500 handling and unseeded natural-weather expiry/restoration
validation are deferred; neither is counted as passed. Physical accelerator-board
and cache certification are outside the selected scope.

Read the [timing design](docs/timing-implementation.md),
[renderer design](docs/performance-implementation.md),
[original departure profile](docs/practice-profile.md) and
[loader audit](docs/loader-equivalence.md) for mechanisms and evidence.
Game data, Kickstart, built slaves and captures are not included.
