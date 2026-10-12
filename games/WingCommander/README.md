# Wing Commander

Project scaffold for fixing the Amiga OCS disk and CD32 versions through their
WHDLoad installs. Original slaves: Psygore, version 1.0. Source is unavailable.

**Setup only; analysis has not started.** No fixes, reconstructed slave, launcher,
profiles or gameplay validation exist yet.

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
