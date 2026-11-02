# Ferrari Formula One 2.0b (16.10.2026)

Player-facing changes and activation: [ReadMe](ReadMe).

RC2 fixes the confirmed RC1 20 ms player launch bug; see
[driving-control regression](CONTROLS_REGRESSION.md) for the corrected build
and native-input acceptance. Historical qualification figures below identify
their original binary; they are not new measurements of the correction.

Build the single slave from `Games/FerrariFormulaOne_WHD.s` with:

```
python3 Games/FerrariFormulaOne/build.py --game /path/to/data/racemenu --out /path/to/build
```

The build needs vasm (`VASM`), WHDLoad includes/sources (`WHDLOAD`), NDK includes
(`NDK`), Python capstone and amitools. Output and game data must remain outside
tracked source. The build reads SPS 0481's relocation records; it does not copy
game data into the distribution. `layout.json` identifies canonical hunk
addresses used in the audited assembly. Every live game address is bound through
the game's current hunk table, including reloads. Build offsets are not game
addresses and must never receive native relocation bindings.

`CUSTOM2=0` (the default) selects the original loop. `CUSTOM1` retains its
original meaning there: disable the original slave's timing repair.
`CUSTOM2=1` enables elapsed-time scheduling for SPS 0481 in PAL mode; it supersedes that
repair, so both CUSTOM1 settings select the same performance behavior:

| Machine | Simulation interval |
| --- | --- |
| 68000, with or without Fast memory | Converted 200 ms |
| 68020+, no qualified Fast memory | Native 100 ms |
| 68020+ with qualified Fast memory | Player 20 ms; opponents native 100 ms |

Selection uses WHDLoad's CPU flags and expansion allocation, followed by actual
CPU-hunk and stack placement checks for the fine path. CPU allocations use
MEMF_PUBLIC; DMA resources retain Chip placement. An overloaded A500 retains its
200 ms scheduler and pending time. There is no performance-triggered return to
the legacy loop. Irek's version retains its original path even with CUSTOM2 set.

The combined slave reserves 768 KiB through WHDLoad (256 KiB Kickstart image plus
512 KiB public pool), in addition to 512 KiB Chip memory and host/slave overhead.
This reservation also applies with CUSTOM2 disabled: identical minimum memory
requirements to the small v1.01 release are not claimed. The documented A500
emulator configuration has 512 KiB Chip plus 1.5 MiB Slow memory; the Fast variant
also has 2 MiB Fast. The 020 configurations have 2 MiB Chip, with/without 4 MiB Fast.
These configurations are qualified with WHDLoad 20.1; A500 with 512 KiB Chip
and 2 MiB Fast also passes without Slow memory. Smaller configurations are
documented in RELEASE_QUALIFICATION.md. WHDLoad 17.0 and 68060 are not tested.

The elapsed clock is PAL-calibrated. Enabled SPS mode requires WHDLoad to report
PAL; NTSC is rejected with the normal WHDLoad PAL requirement message. The
disabled path and Irek's original path retain their existing video behavior.
Allocation or invariant failures in enabled mode exit WHDLoad with an error;
production never enters a diagnostic halt loop.

Production starts on entry to driving and contains no pinned RNG seed, delayed
demo activation, VERIFY tape or forced-workload fixture. Payloads are assembled
separately to retain 68000-safe instructions on both A500 profiles. The build
selects the accepted R3g arithmetic branches explicitly and verifies all binding
operands after its final assembly pass. Original diagnostic builders remain in
the ignored local development harness.

Integration acceptance passed on 2026-10-14 for SPS 0481 PAL on the four documented emulator
profiles. Controlled exact-state comparisons, 30 exact frames per engine,
CUSTOM2=0 legacy comparisons, 60-second clocks, enabled CUSTOM1 options,
pause/menu/re-entry, failure routes and reproducible builds pass. Fine-path
cycle/debt and DMA audits pass. The RC1 untraced 300-presentation figures
are 4.56 / 4.75 / 6.65 / 13.30 FPS for A500 / A500+Fast / chip-only 020 / 020+Fast;
all 60-second clock errors are below 0.23%. These are historical RC1 demo measurements,
not matched speedup claims against the original release.

Fine simulation averages 53,747.8 cycles/update; worst rolling five is 58,122.2,
against the 145,600 gate. Peak is 141,613 against 283,750. The matched reference
averages 51,744.7: integration costs about 3.9%, with substantial capacity margin.
Actual tow restores all 503 coarse / 902 fine patch words before native cleanup; pause and
menu/session time do not enter driving debt. Full local evidence is indexed by
`tmp/dev/manifest/production-integration.json` and `tmp/dev/docs/STEP5_CAPACITY.md`.

The historical RC1 260,292-byte build has SHA256
`60123fd26a8c188925c2213118f417e233ad0f883224372e87feeda477e2a836`.
It was reproduced from its original committed sources. The corrected RC2 build
is 260,276 bytes, SHA256
`e57c42ec5160f1771146045f81a31c59ff7942f30678e801fb5c00178dd2910d`;
an independent rebuild of the corrected source reproduces it exactly.

This is an unreleased, opt-in emulator-qualified candidate. The accelerated,
cache/MMU, original-option/reload, track, save/load and
clock checks are complete in [RELEASE_QUALIFICATION.md](RELEASE_QUALIFICATION.md).
Its first section defines the current, reduced test matrix and which checks
run on every change versus only when the code they cover changes.
Accelerated profiles present about 16.64 FPS with less than 0.041% clock error in
the measured automatic demo. Those are emulator observations, not physical CPU
rankings. The original-loop observations are reported separately.

For the qualified emulator save/load route, use `NoWriteCache`. Chip-only 020
with WHDLoad 20.1 also needs `ConfigDelay=0` and `SplashDelay=0`. The slave keeps
API 17, but only WHDLoad 20.x is tested; historical 17.0 results are in
RELEASE_QUALIFICATION.md. Use the shared `~/.local/share/amiga/WHDLoad`
installation for development. The local candidate package and hash manifest
remain ignored under `tmp/dev/`; nothing is published.

Human playtesting and real Amiga hardware testing are deferred. Irek is
unavailable and retains its original route. Enabled NTSC is rejected. C4-T01
micro targets remain documented shortfalls; the user-selected C4 matched-
workload no-regression gate has passed. There is no A500 performance fallback.

A local Retroplay-based preinstalled candidate is also available at
`tmp/dev/dist/FerrariFormulaOne_v1.02-rc2_0481_Performance.lha`.
All 40 original game-data files, the manual and icon artwork are preserved.
The normal FerrariFormulaOne icon keeps CUSTOM2=0; the added Performance icon
selects CUSTOM2=1. Both carry NoWriteCache and disabled splash delays. The
updated ReadMe includes the original text as historical documentation, with
current memory requirements and qualification limits above it. New icons use
automatic placement. The 53-member level-1 LH5 archive passes CRC testing and
complete extraction/content comparison; its inventory and hashes are recorded
in `tmp/dev/manifest/preinstalled-rc2.json`. Game data and packaging tools remain
ignored and local; this archive is not published.

The RC2 preinstalled archive is 677,063 bytes, SHA256
`cdd0357047f302f1faec3584eafba5af2bfa56720452ab1f7eb1ad806a87c68b`.
Its corrected slave is the exact independently rebuilt and control-tested binary
identified above. Replace the RC1 installation; saved game data can be retained.

The short RC2 020+Fast rendering profile and prioritized high-end optimization
work order are in [RENDERING_PLAN.md](RENDERING_PLAN.md). This is measured
follow-up work; the delivered RC2 archive remains unchanged.

H2 now removes exact zero/Q colour intermediates on the 020+Fast fine path.
The user accepted the completed measurements: 020 dense 5.70 -> 6.24 FPS,
030 grid 14.39 -> 16.64 FPS, with no regression in the completed comparisons.
100 state updates/private fractions and 90 full RGB frame comparisons are exact;
the 60-second clock gate and independent rebuild pass. Remaining H2 controls,
lifecycle, legacy-option and 060 heavy-scene qualification were stopped at the
user's request. This is accepted development work, not a newly qualified release.
See RENDERING_PLAN.md for the complete table, scope and deferred checks.

The accepted H2 revision built to 261,512 bytes, SHA256
`0a26fe52fd0e27e476dacdc53401c30b923a5d7dd7099bb025d8a06ee1d798b2`.
The packaged RC2 slave above is unchanged. H1 remains removed.

H3 overlaps road preparation with safe display handover and composes the final
flag/clock on the back buffer. Matched draw cost falls 1.04% (0.626 ms); 020+Fast
grid improves 12.48 -> 12.84 FPS and dense 6.24 -> 6.32. Normal accelerated
presentation remains 16.64 FPS. All twelve performance pairs have no mean/p95
regression. State/private fractions, 90 full RGB comparisons, native controls
(including 040/MMU/32 MiB), lifecycle, both legacy options and failure checks pass.
See RENDERING_PLAN.md for scope and the separately documented inherited B8-PAL
palette pulse; intermediate transition JPEGs are not claimed identical.

The accepted H3 source independently builds to 262,056 bytes, SHA256
`ac034f9786055bcb04c45383740def6cf249bf0910260dbc322c98461f15a8c2`.
CUSTOM2 remains default-off, and the packaged RC2 above is unchanged. H4 is the
next optimization at that checkpoint; human full races and real-hardware testing remain deferred.

H4 batches the demo label (126 → 6 blits) and removes the clock's immediate
duplicate back-buffer overwrite (42 → 21 blits, including player driving).
Matched draw cost falls 7.27% (4.371 ms). All twelve 300-presentation performance
pairs pass no-regression, with exact state/private fractions, 90 complete RGB
comparisons, elapsed, native controls, lifecycle, legacy and failure checks.
See RENDERING_PLAN.md for the FPS table and the inherited B8-PAL limitation.

The accepted H4 source independently builds to 263,532 bytes, SHA256
`f4f09229e73699fe278df126cc9d3ab614df449b2a4d2e26384d16ca1911fa0f`.
CUSTOM2 remains default-off and RC2 remains unchanged. H5 was next
at that checkpoint; human races and physical hardware testing remain deferred.

H5 draws bounded aligned 8x8 font glyphs with the CPU after native DMA
synchronization, retaining the general blitter fallback. Matched draw cost falls
0.17% (0.094 ms). All twelve performance pairs pass mean/p95
no-regression, with exact state, frames, pixels/CCR primitive oracles, elapsed,
controls, lifecycle, legacy and signature-failure checks. See RENDERING_PLAN.md
for the measured results and scope. IRQ ownership is unchanged.

The H5 source independently builds to 264,520 bytes, SHA256
`57900954b6eb18f1691f3ff8f9b51bcb4beb8a6c3456b6d33f1268cc810c9316`.
CUSTOM2 remains default-off and RC2 is unchanged.
B8-PAL cleanup and successor packaging are separate work; human full races and
real hardware remain deferred.

H6 establishes the cycle-exact-blitter baseline. H7 adds fine-path BLIT
interrupt ownership with exact lifecycle restoration; it passes the
user-reduced emulator checks documented in [RENDERING_PLAN.md](RENDERING_PLAN.md).
Grid reaches 24.96 FPS on 030/040/060 with the default blitter model and
19.97 FPS with cycle-exact blitting. 020 normal/dense show no regression.
The coarse payloads and RC2 archive are unchanged; CUSTOM2 remains default-off.
H8 ranked the remaining costs. H9 now narrows the road fills exactly and passes
the reduced state/image/elapsed/lifecycle gates. On cycle-exact 040, dense improves
12.04 → 12.47 FPS; grid remains 19.97 FPS with a 0.34 ms draw-time saving.
H10 was next at that checkpoint; H12 was subsequently dropped. The H9 source reproducibly builds
to 265,512 bytes, SHA256
`b313710c295498f9a798728850c4b215d4eb0c412c2dd3cd9e0586baaceb3c5e`.

H10 now uses CPU background stores on 030/040/060 + Fast after per-CPU
cycle-exact benchmarks. Reduced correctness, lifecycle, elapsed and no-regression
checks pass. Cycle-exact grid reaches 24.96 FPS on 030, 24.71 on 040 and 24.88
on 060; only 030 has all 300 intervals at two fields. The fresh 040 pair improves
19.97 -> 24.71 FPS; dense remains 12.48, and 020 is unchanged. H13 is next.
The 266,080-byte source build is independently reproducible, SHA256
`b4cbad2eb95c8e679a43c0cc6c8ad08065bbf11a0515301aa1ad68baacb23d50`.
See [RENDERING_PLAN.md](RENDERING_PLAN.md) for exact scopes and histograms.
CUSTOM2 stays default-off and RC2 is unchanged.

H13 adds bounded CPU gauge background strips on 030/040/060+Fast; native gauge
calculations and foreground drawing remain unchanged. Reduced exact-state,
RGB, native primitive, elapsed, lifecycle, legacy and performance gates pass.
040BCE grid improves 24.67236 → 24.75392 FPS.
See the H13 closure in [RENDERING_PLAN.md](RENDERING_PLAN.md) for scope and
remaining H6c work. H12 is dropped; RC2 packaging remains unchanged.

H11 prepares the live session-clock glyphs in 56 bytes of public Fast memory
on 030/040/060, then copies them to Chip at the original HUD point. Reduced
exact-state, native bitmap, RGB, elapsed, lifecycle, fault, legacy and performance
checks pass. Matched 040BCE post-wait draw time improves 37.13179 → 36.81414 ms;
grid improves 24.71307 → 24.91867 FPS. The 030/060 grid confirmations reach
24.96020 FPS with all 300 intervals at two fields. Dense remains 12.48010 FPS.
The reproducible 267,960-byte build has SHA256
`84783350ad9b1b5a23d3ac28862e53fbb0fb9cc6fdf553edb6289afcbe8bcb26`.
See the H11 closure in [RENDERING_PLAN.md](RENDERING_PLAN.md) for scope and
histograms. H6c now passes the revised common-scene gate: at least 95% of
300 intervals at two PAL fields, with none longer than three fields. Normal
030/040/060 BCE scenes achieve 96.3–96.7%; solo/grid achieve 99.7–100%.
The original all-300 target remains unmet. No further common-scene optimization
is needed for the revised goal; dense retains its no-regression result.
H12 is dropped.
The H13 preinstalled snapshot and RC2 archive are unchanged.

### H13 local preinstalled snapshot

On request, the Retroplay-based development snapshot is available locally at
`tmp/dev/dist/FerrariFormulaOne_v1.02-h13_0481_Performance.lha` (686,119 bytes).
It contains source commit `7017177da0c9370756cf0cc5c9a363aedb4e9ab2` and the
267,064-byte H13 production slave. SHA256 of the archive:
`9a09fbb8715fe5fe382de07c328cfaf284e5c4e996677c1a3edbcdcf98ad8780`.

All 40 game files remain exact to Retroplay. Both launch icons are retained:
Performance enables CUSTOM2=1; FerrariFormulaOne selects CUSTOM2=0. CRC testing
and complete re-extraction pass for all 53 members. BuildInfo.json records the
source identity; Qualification.txt distinguishes reduced H-series acceptance
from historical release qualification. This is a development snapshot, not a
new release-qualified RC. B8-PAL cleanup, full human races and hardware testing
remain separate. The older RC2 archive is unchanged. Local packaging evidence:
`tmp/dev/manifest/preinstalled-h13.json`.

### B8-PAL cleanup

The inherited diagnostic COLOR00 write is removed from all performance paths.
Real palette setup and the frozen CUSTOM2=0 host patch remain unchanged.
Focused exact-state/RGB, elapsed, palette trace, DMA and 040BCE grid timing checks
pass; see the B8-PAL closure in [RENDERING_PLAN.md](RENDERING_PLAN.md).
The reproducible production build is 267,940 bytes, SHA256
`5db5a4c4fb42360578a38aa61c5cdcb3c7524fb4c5bed948f51d305050e1663e`.
This supersedes earlier B8-PAL cleanup notes for current source. The existing
preinstalled archives still contain their documented older builds.

### Performance-mode CPU caches

With CUSTOM2=1 the slave now requests every CPU cache WHDLoad can safely
provide, following Secret Weapons of the Luftwaffe. The policy lives in
`FerrariFormulaOne_Cache.s`. It applies when a performance path activates
(fine path start and coarse activation). Boot, loading and menus keep
kick13's caches-off setup, which keeps the automatic demo identical to the
previous build. A boot-time variant changed the course of the long elapsed-
clock demo on 040.

- 68040: Chip noncacheable; ExpMem, slave and WHDLoad copyback; instruction
  and data caches. The 060 bits (branch cache, store buffer, superscalar
  dispatch) are requested too, but 060 is not tested. If WHDLoad cannot
  separate Chip from ExpMem, the policy reads CACR back and falls back to
  the setup below.
- 68020/030: instruction cache on Chip and ExpMem, 030 instruction burst;
  no data cache. The 030 data cache (WHDLoad's MMU option) crashes
  performance-mode startup, also with the previous build.
- 68000: nothing to set.

Emulator results against the previous build (300 presentations, CUSTOM1=0
CUSTOM2=1):

| Profile | Previous FPS | Cache policy FPS | CACR |
| --- | ---: | ---: | --- |
| chip-only 020 | 6.6266 | 8.1127 | 0 → 1 |
| 020 + 4 MiB Fast | 15.3601 | 15.3444 | 1 → 1 |
| 030 50 MHz BCE | 24.5510 | 24.5510 | 2011 → 2011 |
| 040 40 MHz BCE | 24.5108 | 24.5108 | 8000 → 80008000 |

Only the chip-only 020 gains: its coarse path ran with every cache off. The
030 and 040 scenes are already at the presentation ceiling here. Exact
states, the normal and grid frames and the elapsed clock (0.025883% error)
match the B8-PAL references. 20-update smokes pass on all core profiles, 030
with WHDLoad's MMU option and data-cache emulation, and 040 with the MMU.
Removing the old fine-path SetCPU also removed the cache flush after the fine
installs; the policy's SetCPU now provides it. Without it, 020+Fast froze
mid-race.
