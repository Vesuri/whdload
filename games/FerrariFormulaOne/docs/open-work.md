# Ferrari Formula One current work

## Where it stands (2026-11-08)

- **Release 2.0b (06.11.2026), unreleased.** The release slave (`376d1164…`, FR10) is the
  default-off combined performance slave (`CUSTOM2=1`, PAL, SPS 0481) with Fast RAM
  rendering on the 030/040/060 (FASTRAM_PLAN "FR10"). It reserves 1 MiB ExpMem (768 KiB
  pool), so the A500 without Fast memory and the chip-only A1200 no longer start (the
  user's decision, "add enough memory", 2026-11-06). `ff1check.py release` on it
  (2026-11-08): everything passes except lap (020+Fast) and controls (A500+Fast), which
  meet the collision problem below in the demo; reload (A500+Fast, 020+Fast), which fails
  on the pre-FR10 slave too; and season, whose runner hangs after a correct F10 exit
  (`run_release_season.py` waits for the emulator to exit, with no timeout).
- **Before a release here:** `tools/build.py` appends `$VER: FerrariFormulaOne.slave 2.0b
  (06.11.2026)` after the payloads, from `slv_info`'s version and date, so no host or payload
  byte moves. The installed icon enables performance mode: `release/Install` writes
  `CUSTOM2=1` into it (the user's decision, 2026-11-06; not yet run under Installer).
- **Release blocker: hangs on a real A1200/040 (2026-11-07, the user's report).** On an
  A1200 with a 68040, MMU and 32 MB, performance mode hung every time on Esc to pause then
  Esc to resume, and in collisions with the track edges: the game stops with the clock
  sample looping. Not reproduced in the emulator (`a1200-040` with 32 MB Zorro III,
  data-cache emulation on, the 2.0b release slave `9008bdb0…`, `CUSTOM2=1`). The user's
  emulator recording of the same situations (running off track; contact in the start
  pack) shows the view swinging from far right to far left within a few frames, the car
  bouncing, a white strip at the bottom edge and, for one frame, a large red wedge at the
  bottom left. Suspected, not tested: the 20 ms player simulation applies native
  collision impulses undivided (`FerrariFormulaOne_Velocity.s`), so a contact seen on
  several 20 ms steps kicks the car several times, into positions the original never
  reaches, where projection and polygon code can break. The only wall-contact test is one
  synthetic contact on the native paths (GAME_TIME.md). Ruled out: pause writes no game
  code (its sites are patched at install), and the opponents' pose blending never moves
  the player's view. The hanging machine had a PCMCIA network card in the slot, which has
  caused random failures with other WHDLoad installs there. The card may be the cause of
  the hangs: for example, an interrupt the card raises through Gayle that nothing
  acknowledges once WHDLoad has taken over the system. The glitches in the recording come
  from an emulator without the card, so they need explaining either way. Next: the hang
  situations on the real machine without the card; the same situations with `CUSTOM2=0`
  in the emulator and on the real machine; then a repeated-contact check on the 20 ms
  path against the native response. Do not publish the release until this is understood.
  Reproduced in the emulator (2026-11-08, `tools/demo_trace.py`, 020+Fast, the FR10 slave,
  demo race): after a contact the player's speed falls 301 → 168, rises to 361 and the car
  is thrown sideways about 90 lateral units a tick to the clamp at 604, then counts out of
  the race. The A500+Fast controls run (68000 path) ends at lateral 604 too, during the
  countdown with no input. The pre-FR10 slave misses that contact only because the demo's
  start shifts by a few fields.
- **Fast RAM rendering (docs/FASTRAM_PLAN.md)** is in the release slave since FR10:
  030-50 BCE 48.9–49.9 FPS against 12.5–25.0 on the Chip path, 040-40 BCE 22.5–31.5.
- Human playtesting (full races) and real Amiga hardware remain deferred.

## Fast RAM rendering: continuing

The user's decisions (2026-11-05): concentrate on the 68030 and leave the 68040 for now;
30–38 FPS on the 030 is a good result. The 040 is slower than the 030 on this path (FR5
already showed it: 161 against 94 ms per draw, road 67 against 24 ms), the cause is not
known and it has not been profiled since FR5, so no 040 figure follows from an 030 one.
Commit each FR step when its gates pass; push only when asked. Production is the FR10
slave `376d1164…` (1 MiB ExpMem). The hunks already load
into Fast memory (FASTRAM_PLAN "Code and data placement check"); that needs no new look.
The test matrix has no 060 and no WHDLoad 17.0, and one A500 setup except memory checks.

The current build is the FR10 production slave (`376d1164…`, `tools/fr10_build.py`, with
`-off` arms and scene fixtures). Next, in order:

1. The collision problem (Where it stands): the contact comparison, both modes.
2. FR11 (optional, FASTRAM_PLAN).

Done: FR10, checkpoint and release (2026-11-08; FASTRAM_PLAN "FR10").

Done: FR12, draw work on the 030 (FASTRAM_PLAN "FR12"; closed by the user's decision,
2026-11-06). Eight steps (one-dot lines, zero road-fill words, the car in one pass, the road
lines and the area blits on their own paths, transparent car words, WaitBlit when idle; the
copy waits for the view switch; `tools/fr12_car.py` checks the car). Normal, solo and grid
draw every field; dense is 47.85 FPS (busy 20.8 ms), and the ideas left for it are listed
there. Steady motion: the ticks match the fields on screen in 99.6–99.9 % of frames in
normal, solo and grid; the predicted-tick variant is dropped (the user's decision).

Commands, from this directory after `. ../../common/env.sh`, one emulator job at a time
(they share gdb port 2573):

```sh
python3 tools/fr2_unicorn.py 68020   # and 68030, 68040, after any kernel change:
                                     # "cases 4479 mismatches 0 kernel cases 3162"
python3 tools/fr8_build.py TAG [--scenes]
                                     # tmp/build/fr8-production (asserts the production sha), fr8-TAG,
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
is the private FS-UAE build most checks run on (`RELEASE_FSUAE`); `tools/build_observer.sh`
rebuilds it from upstream plus `tools/observer.patch` (census, the 030/040 clock fix). A
rebuild on 2026-11-08 reproduced FR12's dense 47.85 FPS exactly.

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
