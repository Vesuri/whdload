# Wing Commander

Project scaffold for fixing the Amiga OCS disk and CD32 versions through their
WHDLoad installs. Original slaves: Psygore, version 1.0. Source is unavailable.

**Phase 11b is in progress; C1 is complete.**
The public-option candidate uses `CUSTOM1` for language and `CUSTOM5=0` for
enhanced English flight without Psygore's frame cap. Values 1–4 retain Psygore's
normal/unlimited/relaxed/slow modes. German default and enhanced nonflight scenes
retain normal pacing. See the [candidate ReadMe](release/ReadMe).
Enhanced flight queues completed pictures for early vertical blank and waits
only before reusing a pending display buffer. The scoped PAL gates reach 49.92
pictures/s on both tested models; the 040 core remains uncalibrated against hardware.
The reported cached-040 row corruption was traced to incorrect MMU write cache
attributes in FS-UAE. The launcher now builds a corrected local emulator; caches
remain enabled. See the [pixel checks and limits](docs/internals.md#cached-040-display-corruption-emulator-mmu-write-attributes).
Flight prediction now targets the queued picture’s display field; the scoped
PAL/NTSC gates retain 49.92/59.83 pictures/s with matching prediction times.
Phase 12 stays paused; C2 and broader visual acceptance remain open.

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
intro rate selection remains deferred. Flight runtime gaps include comms, missile
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
