# Wing Commander

Project scaffold for fixing the Amiga OCS disk and CD32 versions through their
WHDLoad installs. Original slaves: Psygore, version 1.0. Source is unavailable.

**P13A1–P13A4, P13B1–P13B3, P13C1–P13C6 and P13D1 complete: OCS conversion/display work and native timing ownership audit.** The [ordered implementation plan](docs/ocs-plan.md)
covers an Amiga 500/Fast RAM baseline and shared CD32 timing/prediction mechanisms.
OCS has native four-plane blitter conversion. Retain it where measurements favour
it; compare 68000-safe CPU conversion and a 68020+ longword path before selecting
by CPU and memory configuration. Matched emulator windows favour native blitter on 68000 and no-Fast 68020,
and CPU/Fast longword conversion on the measured 14 MHz 68020/Fast profile.
The Fast move includes native compositor aliases. Normal OCS builds remain unchanged; CD32 release work remains paused. The 5,324-byte slave
rebuilds exactly with the 68000 assembler; input and displaced-byte rejection
checks pass. The functional display gate passes 45 conversions and ownership checks;
native checkerboard colour selection and its four edge pixels are confirmed live.
Original/rebuilt A500 boots match state and pixels through intro, menu, simulator
and the visible name prompt. The corrected stock-clock A500 model measures 5.79
displayed pictures/s in asteroid credits and 5.39 during simulator flight/fire;
observer-off state/pixel controls pass. These are short emulator baselines.
The shared build and analysis tools require an explicit variant; checked CD32
binaries and original OCS reconstruction remain byte-identical. Base-ISA assembly,
arithmetic, flag and wrapper checks pass on CPU models; C4 now links allocation
and conversion hooks in a separate OCS candidate. Timing hooks remain pending.
Shared WCFS/WCDS interfaces now separate world, render and actual display counts;
the OCS recorder passes CPU/replay checks and native observer-off controls remain
exact. Guest hooks and their measured runtime overhead remain later integration.
Experimental Kalms word/longword candidates now match native visible pixels and
an independent oracle, including checkerboard colours and four black edge pixels.
Bounds, alternating destinations and native fallback checks pass. Diagnostic-only
C2 hooks now measure complete adapters and matched live images; native QBlit remains
the normal default. The bounded C3 seam now selects once, preserves cache policy,
and supports explicit native/CPU choices with safe pre-move memory fallback.
C4 allocates the CPU source in Fast RAM before view aliases are built, unwinds
failed setup and retires native readers before freeing it. Both backends pass
controlled display teardown with DMA ownership checks. The tested launcher floor
is 512 KiB Chip plus 4 MiB Fast. C5 now queues completed pictures for safe OCS
blanking-time publication; both backends pass view transitions and display-DMA
pixel checks. C6 adds an opt-in CPU/Fast changed-block path: matched 020 intro
images improve from 13.64 to 18.76 displayed pictures/s, while the A500 retains
the faster native blitter. Two destination histories add 128 KB of Fast storage.
See the [C6 gate](docs/internals.md#p13c6-measured-changed-block-conversion), the [C5 gate](docs/internals.md#p13c5-completed-image-publication-and-display-ownership), the
[C4 ownership gate](docs/internals.md#p13c4-backend-specific-memory-ownership), the
[C3 gate](docs/internals.md#p13c3-conservative-backend-selection),
[C2 gate](docs/internals.md#p13c2-measured-ocs-converter-crossover),
[B3 gate](docs/internals.md#p13b3-shared-instrumentation-and-validation-interfaces),
[baseline and limits](docs/internals.md#p13a4-short-native-ocs-baseline), and
[reproduction commands](docs/development.md#p13c4-allocation-integrated-ocs-candidate).

**Phase 11b is in progress; C1–C3 and the C4 steady-flight gate are complete.**
The public-option candidate uses `CUSTOM1` for language and `CUSTOM5=0` for
enhanced English flight without Psygore's frame cap. Values 1–4 retain Psygore's
normal/unlimited/relaxed/slow modes. German default and other nonflight scenes retain normal pacing. The enhanced
English ship/title and asteroid intro uses the flight 10 Hz clock and extrapolation. See the [candidate ReadMe](release/ReadMe).
Enhanced flight queues completed pictures for early vertical blank and waits
only before reusing a pending display buffer. The scoped PAL gates reach 49.92
pictures/s on both tested models; the 040 core remains uncalibrated against hardware.
The reported cached-040 row corruption was traced to incorrect MMU write cache
attributes in FS-UAE. The launcher now builds a corrected local emulator; caches
remain enabled. See the [pixel checks and limits](docs/internals.md#cached-040-display-corruption-emulator-mmu-write-attributes).
Flight prediction now targets the queued picture’s display field; the scoped
PAL/NTSC gates retain 49.92/59.83 pictures/s with matching prediction times.
Player velocity and position now advance per elapsed field, without a second
position step at world ticks. C2 steady flight retains 49.92 pictures/s; held turns
measure 41.75 on the cycle-exact 040 and 54.23 on the NTSC 030. Rendering overruns
still miss prediction targets, also observed in the previous C1 build. See the
[C2 gate and limits](docs/internals.md#phase-11b-player-translation-c2-gate-complete).
Heading-aware ship forecasting preserves native inertia: the retained hard-turn
world-ship error falls to 0.26 km at p95 and 6.35 km maximum; constant-velocity
classes stay exact. C3 measures 49.92 pictures/s in steady 030 flight and 41.53
in the cycle-exact 040 held turn. See the [C3 gate and residuals](docs/internals.md#phase-11b-heading-aware-extrapolation-c3-gate-complete).
C4 confirms one displayed picture per field in steady PAL flight on both models:
median and p95 intervals are both 20.032 ms. The existing queue absorbs world-tick
work spikes; no further scheduler change was needed. Heavy-turn overruns remain
for rendering-cost work. See the [C4 measurements](docs/internals.md#phase-11b-frame-time-spikes-c4-steady-flight-gate-complete).
D1’s model profile identifies repeated geometry, cockpit composition and block
comparison as useful optimisation targets. Observer controls preserve the
recorded run exactly; no optimisation was applied. See the
[D1 costs and limits](docs/internals.md#phase-11b-rendering-costs-d1-model-profile-complete).
D2 is complete: selective pose backups and unchanged-input geometry reduce
prediction overhead. Steady flight remains 49.92 frames/s on both models; the
040 held turn improves from 41.53 to 42.09, with deadline misses still present.
See the [D2 checks and limits](docs/internals.md#phase-11b-prediction-overhead-d2-complete).
D3 is complete: faster view-region clears and cached-030 composition preserve
native pixels. Steady flight stays at 49.92 frames/s; the 040 model held turn
reaches 42.49, with 112/657 prediction deadlines still missed. See the
[D3 evidence](docs/internals.md#phase-11b-view-regions-d3-complete).
D4’s comparison-cost gate is complete: a compact full-image comparison reduces
the 040 model’s comparison/loop/history cost by 0.84 ms per picture. Drawing-based
dirty rectangles remain deferred. Steady flight stays at 49.92 frames/s; the
040 held-turn window reports 43.42 versus 42.49 for its unchanged D3 control.
See the [D4 scope and evidence](docs/internals.md#phase-11b-comparison-cost-d4-practical-gate-complete).
D5 is complete on the current models: Kalms 040 changed blocks give no meaningful
gain on either model, and full conversion remains slower than changed blocks.
The release converter selection is unchanged. See the
[D5 comparison](docs/internals.md#phase-11b-kalms-families-d5-model-evaluation-complete).
Hardware calibration is separate follow-up under A2, not a D5 completion gate.
New projectiles now extrapolate from their first presentation interval, covering
player and AI weapon constructors. Firing cooldowns no longer cause false view
cuts. Native state-restoration checks and short held-fire model gates pass
(030: 49.92 frames/s; cycle-exact 040: 48.03). See the
[spawn fix and limits](docs/internals.md#cannon-spawn-first-interval-prediction-hold).
Stop before E1; phase 12 stays paused.

**Phase 11 is complete: changed-block flight conversion.**
The timing build converts only changed view/cockpit/HUD blocks, with separate
history for each display buffer. Native/live output matches the original; measured
mean conversion time falls 80% on the 030 firing sample and 67% on the 020 turning
sample. PAL/NTSC world timing remains near 10 Hz. See the
[gate and coverage limits](docs/internals.md#phase-11-flight-rendering-gate).
Phase 11b frame-rate recovery precedes release polish and packaging.

**Phase 10 is complete: presentation between world updates.**
The experimental timing build predicts object positions and orientations for drawing,
then restores authoritative state. PAL/NTSC flight checks pass; corrections snap at
world boundaries, with hard-turn limits documented in the [gate evidence](docs/internals.md#phase-10-renderer-only-prediction-gate).
Phase 11 integrates flight conversion; release work remains deferred.

**Phase 9 is complete: D's decoupled simulation and responsive controls.**
The separate experimental timing build uses `CUSTOM1=3`. World timing stays within
0.4% of 10 updates/s across normal, delayed and diagnostic one-field schedules;
PAL/NTSC, input history, pause, targeting and draw/RNG separation are checked.
The accelerated run shows player/camera motion between world ticks. Option-off
game code remains unchanged. See the [gate evidence](docs/internals.md#phase-9-decoupled-simulation-gate).
Phase 10 adds world-object presentation; phase 11 optimises flight rendering.

**Phase 8 is complete: the user selected D, the hybrid.**
The [design](docs/timing-design.md) uses a 10 Hz world with responsive per-render
player orientation/camera and bounded world-object extrapolation to validate.
Eleven combat configurations are priced with explicit overhead and instrument
gaps. Phases 9–10 implement the simulation, player and world-object presentation paths.

**Phase 7b framerate-dependency audit is complete.**
The [audit](docs/framerate-audit.md) records 23 stable findings, the complete
world-update dispatch inventory, and implementation costs under B/C/D. Native
68000/68040 checks cover steady/changing rates, all 625 table entries and 104
bounds rejections. Live coverage and instrument limits remain documented.
Phase 8 uses this audit to compare B/C/D.

**Phase 7 gameplay timing investigation is complete.** Flight motion is coupled
to rendering; the native speed/range units imply 10 world updates/s. Reproducible
coast, combat-input and pause windows, a state/cadence map and CPU/drawing coupling
measurements are recorded. The phase-9 adapter implements the selected timing policy.

**Phase 6 rendering work is complete.**
`CUSTOM1=2` enables the experimental English renderer. Measured selection uses
Kalms c2p on cached 020/030 (about 7% / 30–32% less conversion time in the emulator)
and retains the existing converter elsewhere. It preserves WHDLoad cache choices
and waits for display end before the original swap. `CUSTOM1=0/1` keeps the original
paths. Native and live twin checks verify identical converter output.

FAST chunky storage and FMODE 3 were already present in the observed setup.
Exact intro duration neutrality is not claimed: the final 020 intro is about
0.63 seconds longer with the display-end wait. Music/text deadlines stay unchanged;
the ship/title and asteroid intro now uses the selected 10 Hz rate. Flight runtime gaps include comms, missile
locking, normal damage, autopilot and landing; these paths have static cadence
classifications, not full live validation. See [internals](docs/internals.md).

**Phase 4 is complete under the approved practical-baseline scope.**
The eleven-configuration CPU/cache baseline, source-change census, DMA/STOP idle
measurements and matched c2p, instant-blitter and scoped bitmap-drawing ceilings
are recorded. Representative profiles identify software c2p as a substantial 020
cost; eight configurations pass the combined callback checks.

General routine self/inclusive attribution, full interrupt/wait accounting,
unaccepted callback controls and a broader drawing ceiling remain documented
gaps. Accelerated timings describe the emulator model, not physical hardware.

Phase 3 completed the reproducible intro and publication counter.
Two fresh boots match all 31 milestone screenshots, live game hunks and the
reset-to-menu event ledger. Full traces and independent SWAP_ONLY counts agree.
Release changes remain outside scope.
The original and reconstructed slaves match at the menu and pilot-name prompt
for Custom5=0–3. Phase 2 is complete.
Phase 1 static findings are documented. Runtime timing and display hypotheses
remain hypotheses except for the scoped runtime findings recorded in the internals.

See [open work](docs/open-work.md), [development](docs/development.md) and
[known internals](docs/internals.md). Agent rules are in [AGENTS.md](AGENTS.md).

```sh
make fetch
make verify
make prepare
. amiga/env.sh
```

The installer and both full installs are pinned in `manifest/inputs.tsv`.
Archives and separate extracted originals live under ignored `tmp/`.
The shared development tools come from AmigaXDev's installed environment.

Intro timing is complete: the enhanced English ship/title and asteroid intro uses
the same 10 Hz world clock and extrapolated motion as flight. Asteroid generation
runs during world updates so drawing cannot discard newly created asteroids.
Music and credit deadlines remain native; the separate Origin logo remains native.
See the [intro gate](docs/internals.md#intro-10-hz-world-and-extrapolated-presentation).
