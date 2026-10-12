# Development

## Inputs

The [official install page](https://whdload.de/games/WingCommander.html) identifies
Psygore's v1.0 installer. The user supplied the Retroplay OCS (SPS 1657) and CD32
full-install URLs. Exact URLs and initial-download SHA-256 fingerprints are in
`manifest/inputs.tsv`; these fingerprints pin the received files, not an
independently authenticated upstream release.

`make fetch` downloads missing inputs and checks them before accepting them.
`make verify` checks every cached archive. `make prepare` verifies each archive
before extracting to separate `tmp/originals/installer`, `tmp/originals/ocs` and
`tmp/originals/cd32` directories. Extraction requires `lha` on PATH. Existing
extractions are left untouched; their contents are not revalidated by this target.
Failed downloads or extractions are retained in ignored scratch storage.

The originals are reference copies. Later emulator work should use separate
working copies under `tmp/game/`. Never commit archives or extracted contents.

## Shared environment

Source `amiga/env.sh`, which sources `${AMIGA_ENV}` or the conventional
`~/.local/share/amiga/env.sh`. The shared environment supplies toolchain, WHDLoad,
ROM and launcher variables. This scaffold makes no project-specific overrides.
Install shared prerequisites through AmigaXDev; ROM/OS sources are user supplied.

## Current commands

Only fetch, checksum verification and archive preparation are implemented.
No build, run, tracing or release target exists yet. All shell tooling is written
for `/bin/bash` 3.2 and supports the project name's space.
