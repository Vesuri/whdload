# Wing Commander

Project scaffold for fixing the Amiga OCS disk and CD32 versions through their
WHDLoad installs. Original slaves: Psygore, version 1.0. Source is unavailable.

**Phase 6 rendering work is complete; timing calibration remains deferred.**
`CUSTOM1=2` enables the experimental English renderer. Measured selection uses
Kalms c2p on cached 020/030 (about 7% / 30–32% less conversion time in the emulator)
and retains the existing converter elsewhere. It preserves WHDLoad cache choices
and waits for display end before the original swap. `CUSTOM1=0/1` keeps the original
paths. Native and live twin checks verify identical converter output.

FAST chunky storage and FMODE 3 were already present in the observed setup.
Exact intro duration neutrality is not claimed: the final 020 intro is about
0.63 seconds longer with the display-end wait. Music/text deadlines stay unchanged;
intended movement rates and further timing investigation remain deferred.
**Phase 7 gameplay timing and state investigation is in progress.** See the evidence and limits in [internals](docs/internals.md).

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
