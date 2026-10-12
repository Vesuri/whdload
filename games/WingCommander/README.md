# Wing Commander

Project scaffold for fixing the Amiga OCS disk and CD32 versions through their
WHDLoad installs. Original slaves: Psygore, version 1.0. Source is unavailable.

**Phase 2 complete: CD32 reconstruction and simulator equivalence verified.**
The original and reconstructed slaves match at the menu and pilot-name prompt
for Custom5=0–3. Work is stopped at the phase 2 gate.
Phase 1 static findings are documented. Runtime timing and display hypotheses
remain unconfirmed except where an explicit phase 2 boot check records evidence.

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
