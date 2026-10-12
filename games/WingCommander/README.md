# Wing Commander

Project scaffold for fixing the Amiga OCS disk and CD32 versions through their
WHDLoad installs. Original slaves: Psygore, version 1.0. Source is unavailable.

**Phase 4 is in progress; the full-matrix gate has not passed.**
Cache audits, corrected-clock NOMMU scene figures and scoped 020/030 costs are
recorded. Both 020 cache states and the 030 default pass profiler-neutrality
controls. DMA accounting has an independently checked 030 capture with a measured
small timing effect. The CPU/cache scene matrix is captured and the matched c2p
and instant-blitter ceilings are recorded, along with a scoped bitmap-drawing
ceiling. Blanket clear bypass is invalid. CPU STOP accounting passes a neutral
020 control and independent instruction-count check; full-matrix accounting
captures are running. Preserving CIA wait stepping makes DMA recording exactly
neutral on both 020 cache states and the default 030 MMU pair. The three game
VBL callback scopes have validated 020 durations; remaining matrix controls are
running. General routine/interrupt costs and remaining validation
are still open.
Phase 3 completed the reproducible intro and publication counter.
Two fresh boots match all 31 milestone screenshots, live game hunks and the
reset-to-menu event ledger. Full traces and independent SWAP_ONLY counts agree.
Stop at the phase 4 gate; phase 5 is not authorised.
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
