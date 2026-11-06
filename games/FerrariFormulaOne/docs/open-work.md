# Ferrari Formula One current work

## Where it stands (2026-11-06)

- **Release 2.0b (06.11.2026), unreleased.** The release slave (`9008bdb0…`) is the default-off combined
  performance slave (`CUSTOM2=1`, PAL, SPS 0481): RC2 plus the performance-mode cache
  policy. The cache-policy build has not passed the feature checks yet: run
  `python3 tools/ff1check.py release` (or `changed --run`) on the release build before
  releasing. `ff1check.py changed` lists memory, lap, controls and reload as never passed
  on the current sources and season as changed (`ProductionHost.s`).
- **Before a release here:** `tools/build.py` appends `$VER: FerrariFormulaOne.slave 2.0b
  (06.11.2026)` after the payloads, from `slv_info`'s version and date, so no host or payload
  byte moves (`$VER` alone changed the slave from `597a74b9…`; the core smokes pass on it).
  The icons still leave `CUSTOM2` off (the earlier local candidate added a separate
  Performance icon instead); decide the icon default and the memory scheme then.
- **Fast RAM rendering (`make build BUILD=fast`, docs/FASTRAM_PLAN.md),** development only:
  FR1–FR8 done. FR8 (2026-11-06): 030-50 BCE 39.9 FPS against 24.6 native, 040-40 BCE 22.5
  against 24.5; pacing is not the limit, the draw is. The work concentrates on the 68030 (below); FR0h is still open. FR builds
  need 1 MiB ExpMem and do not boot on the 512 KiB A500 or the chip-only A1200.
- Human playtesting (full races) and real Amiga hardware remain deferred.

## Fast RAM rendering: continuing

The user's decisions (2026-11-05): concentrate on the 68030 and leave the 68040 for now;
30–38 FPS on the 030 is a good result. The 040 is slower than the 030 on this path (FR5
already showed it: 161 against 94 ms per draw, road 67 against 24 ms), the cause is not
known and it has not been profiled since FR5, so no 040 figure follows from an 030 one.
Commit each FR step when its gates pass; push only when asked. Production stays the
`9008bdb0…` slave (`597a74b9…` before the `$VER` string) with DEBUG off and ExpMem `$c0000`; the 1 MiB ExpMem is only for
`FF1_FAST_RENDER` builds and the release memory scheme is undecided. The hunks already load
into Fast memory (FASTRAM_PLAN "Code and data placement check"); that needs no new look.
The test matrix has no 060 and no WHDLoad 17.0, and one A500 setup except memory checks.

The current build is FR8's candidate (`e9ae9b3c…`, `tools/fr8_build.py`); FR6's final
build was k5 (`8ec61e11…`). `tmp/manifest/fr6-validation.json` and `fr8-validation.json`
hold the FPS, gates and measurements; `tmp/logs/fr6-*.log`, `fr7-*.log` and `fr8-*.log` the
gate, FPS, probe and profile logs. Next, in order:

1. Draw work on the 030. FR8 showed the draw alone takes 20–31 ms per frame and 50 FPS needs
   about 17.5 ms. Profile the FR8 candidate (`tools/fr6_trace.sh fr8-candidate`). The k4
   shares: per-blit overhead (FRTranslate, FRSpan, FRMarkSpan, FRKSetup and
   FF1FastRenderSize's register saves) 22 %, the ABCD `$CA` cookie-cut 13.7 %, lines 10 %,
   publish 8.7 %, fill 6.6 %. Ideas: fewer `movem` saves on the per-blit path, translate
   and span merged, the cookie-cut with the colour expansion merged so it skips the scratch
   (FR6 item 1), the cockpit cookie-cut from precomputed word runs (FR6 item 5).
2. The user's decision on steady motion (FASTRAM_PLAN "FR8 results", "Still open"): the
   tick-to-screen delay is 2 or 3 fields.
3. FR10: checkpoint and release.

Commands, from this directory after `. ../../common/env.sh`, one emulator job at a time
(they share gdb port 2573):

```sh
python3 tools/fr2_unicorn.py 68020   # and 68030, 68040, after any kernel change:
                                     # "cases 4479 mismatches 0 kernel cases 3162"
python3 tools/fr8_build.py TAG [--scenes]
                                     # tmp/build/fr8-production (asserts 9008bdb0), fr8-TAG,
                                     # fr8-TAG-pace (pacing log) and their -early0 arms
                                     # (FF1FastRenderEarly 0); --scenes: fr8-TAG-pace-{normal,
                                     # solo,grid,dense}[-early0]
H5_BUILD=$PWD/tmp/build/fr8-TAG-pace-normal C1_VARIANT=fr8-pace-normal \
  python3 tools/test_h5_fps.py 030-50-bce
python3 tools/fr8_report.py tmp/step5/c4-q03-h5-fps-030-50-bce-fr8-pace-normal
                                     # phases, histograms, tearing, tick-to-screen delay
H5_BUILD=$PWD/tmp/build/fr8-TAG C1_VARIANT=fr8-TAG python3 tools/test_h5_fps.py 030-50-bce
                                     # 300 intervals, warp off; grep "'fps':"
FF1_FINE_DEFINES=FF1_FAST_RENDER=1 python3 tools/ff1_gates.py --build tmp/build/fr8-TAG \
  --tag TAG frames/normal frames/grid timing/elapsed
FR4_BUILD=tmp/build/fr8-TAG FR4_TAG=-fr8-TAG \
  RELEASE_WHD_ARGS='CUSTOM1=0 CUSTOM2=1 ConfigDelay=0 NoWriteCache' \
  python3 tools/fr4_probe.py 030-50-bce 300
                                     # tmp/step5/fr4-probe-030-50-bce-fr8-TAG/result.json
                                     # stats_after: fr4.faults, fr4.hard, fr5, fr7;
                                     # fr7_check: Chip, shadows and views equal
python3 tools/ff1check.py run smoke --build tmp/build/fr8-TAG \
  --profiles 030-50-bce,040-40-bce,a1200-fast,a500-fast
python3 tools/ff1check.py run mmu --build tmp/build/fr8-TAG --profiles 030-50  # then 040-40
python3 tools/ff1check.py run route modal --build tmp/build/fr8-TAG \
  --profiles 030-50-bce,040-40-bce,a1200-fast
python3 tools/ff1check.py run controls --build tmp/build/fr8-TAG \
  --profiles a1200-fast,030-50-bce,040-40-bce
tools/fr6_trace.sh fr8-TAG           # 68EC030, 60 fields, cost per routine
python3 tools/fr6_sites.py tmp/step5/hi25-profile-030-50-bce-prof-fr8-TAG DRAWS
```

Pitfalls:

- `ff1_gates.py` builds its frame fixtures from the working tree with the environment;
  without `FF1_FINE_DEFINES=FF1_FAST_RENDER=1` it silently tests the non-FR path (FR5a/b
  were invalid this way). Check with `grep FF1FastRenderPrefix:` in
  `tmp/build/render-TAG-matched-stable-frames/fine/fine.list`.
- Give `ff1check.py` explicit `--profiles` on FR builds: the defaults include the A500 and
  chip-only A1200, which fail (smoke: `assert len(hits)==1, []`, no `FF1B7PUBLICROOT`).
- The first `mmu` run of a sequence sometimes fails after 3 s with `FileNotFoundError` on
  `memory.bin` (the gdb dump did not land), on either CPU; a rerun passes. Harness, not game.
- The fine payload is position-independent: address all payload data `(pc)`-relative
  (`lea X(pc),aN` before a store). An absolute reference assembles and silently hits low
  Chip memory (k1 rebuilt its fill table every blit this way).
- vasm: define a macro before its use; a local label (`.x`) does not survive a global
  label in between; references like `FRBFast\.none` fail.
- Kernels must leave FastRenderBlit's end state exactly: pointers, ADAT/BDAT/CDAT the last
  raw word, BHOLD the last shifted B, BOLD the last raw B or 0, and the line ASH/BSH/SIGN.
  `fr2_unicorn.py` checks it (it sets `uc_ctl`'s argtypes, needed on arm64).
- The owned shadows (FRMarkSpan, reads untracked) hold only because nothing else writes
  the banks while driving (FR1) and the full arm publishes every dirty row each draw;
  partial arms keep the FR5 tracking. A new writer outside the redirection breaks this
  silently. The probe's `rows_refreshed=0` is expected.
- The frame gate's capture is timed from `B8Draw`, so `ff1_gates.py` patches its FR frame
  fixtures to `FF1FastRenderEarly` 0 (the early request would show a newer frame).
- The pacing log (`FF1_FAST_RENDER_PACING`) moves the layout and shifts FPS by up to 1 %;
  compare arms built together. Native absolute addresses are bound only in code before
  `public_bind`: `FastRenderPacing.s` (at the end of `Fine.s`) gets them passed from
  `FullPresentation.s`.
- FPS runs use warp off (`test_h5_fps.py` switches it off); smokes run with `WARP=1`.
  Trace milliseconds read about 1.5–1.9× high: compare shares only.
- 040 controls pass at k5 but the test stays frame-rate sensitive (FASTRAM_PLAN FR5c–f).
- The live runners (route, modal, reload, season) default to the emulator
  `tmp/step3/fs-uae-q03-final`, which needs `data`, `share` and `fsemu` beside it (links to
  `tmp/step5-frame-observer-build`); without them FS-UAE exits at once and the runner
  reports `could not connect: Connection refused`. The frame gate needs the fixture sources
  `tmp/build/step5-b8-v3*` and the B8-PAL references `tmp/step5/c4-q03-*-b8pal-*`. All are
  local and ignored.

The evidence (measurement and validation JSON, `tmp/manifest/`, with `project.json` as the
index) and the captures (`tmp/step5/`, ...) are local and ignored. `tmp/step5-frame-observer-build/`
is the private FS-UAE build most checks run on (`RELEASE_FSUAE`).

## Release qualification (October)

Emulator release qualification and calibrated 030/040/060 analysis are complete
in the documented SPS 0481 PAL scope. The local opt-in candidate is
`tmp/release/FerrariFormulaOne-1.02-rc1.zip`; nothing has been published.
See `manifest/release-qualification.json`, `manifest/release-candidate.json`
and tracked `docs/RELEASE_QUALIFICATION.md`.

The original-option/reload matrix, all three engines, accelerated/cache/MMU,
exact-state/frame/elapsed gates, native laps and F1/F3/track/start/tow/pause/
session/results/save/repair/travel/F10 routes pass in their stated scopes.
Human playtesting (including full races) and real Amiga testing are deferred
by the user. These are the remaining qualification activities, not unfinished
emulator implementation. Irek is unavailable and retains its original route;
enabled NTSC is rejected. C4-T01 is optional further optimization; the chosen
same-workload C4 gate passed. There is no performance-triggered A500 fallback.

Use NoWriteCache for the qualified emulator save/load route. WHDLoad 20.1 on
the tested chip-only 020 requires ConfigDelay=0 and SplashDelay=0. WHDLoad 17.0
functional coverage requires the documented Fast configurations. Minimum-memory
exclusions remain explicit; original-release memory equivalence is not claimed.

The authoritative tracked builder produces the single default-off slave.
CUSTOM2=1 chooses 200 ms on 68000, 100 ms on chip020 and 20 ms player/100ms opponents
on qualified 020+Fast. CPU-only allocations are public; DMA remains Chip.
Use warp through startup and native UI; disable warp for timing measurements.
