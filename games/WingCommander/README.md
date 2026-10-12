# Wing Commander

Project scaffold for fixing the Amiga OCS disk and CD32 versions through their
WHDLoad installs. Original slaves: Psygore, version 1.0. Source is unavailable.

**Phase 5 analysis is complete; the intro-rate decision is pending.**
The supplied PC video gives approximately 14–15 visible ship/explosion advances
per second and 20–25 asteroid advances per second. The Amiga ship loop runs two
updates per drawn frame; asteroids use one. Motion displacement, clock sources
and a matched drawing-slowdown test are documented. Music and text timing stay
unchanged; no new rate has been installed.

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
Phase 6 and rendering release changes are not authorised.
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
