# Wing Commander

Project scaffold for fixing the Amiga OCS disk and CD32 versions through their
WHDLoad installs. Original slaves: Psygore, version 1.0. Source is unavailable.

**Phase 8 is complete: the user selected D, the hybrid.**
The [design](docs/timing-design.md) uses a 10 Hz world with responsive per-render
player orientation/camera and bounded world-object extrapolation to validate.
Eleven combat configurations are priced with explicit overhead and instrument
gaps. Stopped at the phase 8 gate; timing implementation has not begun.

**Phase 7b framerate-dependency audit is complete.**
The [audit](docs/framerate-audit.md) records 23 stable findings, the complete
world-update dispatch inventory, and implementation costs under B/C/D. Native
68000/68040 checks cover steady/changing rates, all 625 table entries and 104
bounds rejections. Live coverage and instrument limits remain documented.
Phase 8 uses this audit to compare B/C/D.

**Phase 7 gameplay timing investigation is complete.** Flight motion is coupled
to rendering; the native speed/range units imply 10 world updates/s. Reproducible
coast, combat-input and pause windows, a state/cadence map and CPU/drawing coupling
measurements are recorded. Timing fixes remain deferred.

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
