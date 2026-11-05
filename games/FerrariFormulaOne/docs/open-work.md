# Ferrari Formula One current work

## Where it stands (2026-11-05)

- **Release 2.0b (16.10.2026), unreleased.** The release slave is the default-off combined
  performance slave (`CUSTOM2=1`, PAL, SPS 0481): RC2 plus the performance-mode cache
  policy. The cache-policy build has not passed the feature checks yet: run
  `python3 tools/ff1check.py release` (or `changed --run`) on the release build before
  releasing. `ff1check.py changed` lists memory, lap, controls and reload as never passed
  on the current sources and season as changed (`ProductionHost.s`).
- **Before a release here:** the slave has no `$VER` string (only `Version 2.0b
  (16.10.2026)` in its info), which `make dist` needs for the archive name;
  `release/ReadMe` and `release/release.json` follow the repository's convention but the
  icons still leave `CUSTOM2` off (the earlier local candidate added a separate Performance
  icon instead); decide the version, date and icon default then.
- **Fast RAM rendering (`make build BUILD=fast`, docs/FASTRAM_PLAN.md),** development only:
  FR1–FR6 done. FR6 (2026-11-05): 030-50 BCE 35.8 FPS against 24.6 native, 040-40 BCE 22.0
  against 24.5. Next: the per-blit overhead and the cookie-cut loop on the 040, then FR7
  (publish copy) and FR8 (pacing); FR0h is still open. FR builds need 1 MiB ExpMem and do
  not boot on the 512 KiB A500 or the chip-only A1200.
- Human playtesting (full races) and real Amiga hardware remain deferred.

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
