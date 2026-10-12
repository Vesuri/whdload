# Wing Commander

Project scaffold for fixing the Amiga OCS disk and CD32 versions through their
WHDLoad installs. Original slaves: Psygore, version 1.0. Source is unavailable.

**Phase 4 is in progress; the full-matrix gate has not passed.**
The CPU/cache scene baseline and matched c2p, instant-blitter and scoped
bitmap-drawing ceilings are recorded. DMA slot accounting and exact recorder
controls pass on all eleven configurations; STOP idle accounting and its exact
on/off controls also pass throughout. Consolidated checks validate DMA slots,
stopped-CPU idle and three VBL callback scopes on both 020 cache states, both
030 MMU cache states, 030 NoMMU NoCache and both 040 cache states. These are scoped measurements, not complete CPU accounting.
General routine attribution remains unresolved. The 040 callback beam check
passes with an explicit debugger-boundary allowance; 060 callback neutrality
remains unaccepted.
Work now prioritises consolidation and representative profiles over further
full-matrix instrument development. Phase 5 remains unauthorised.
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
