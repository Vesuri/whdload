# Development setup

AmigaXDev supplies the shared tools and documentation. Its `make setup` installs
`~/.local` and `~/.local/share/amiga`. Source `amiga/env.sh` to use that environment;
`AMIGA_ENV` can select a different shared environment file. Shared tool, ROM and
WHDLoad paths are supplied by that file, not by copies from other projects.

`make check` verifies the retained archives against `manifest/SHA256SUMS`.
The hashes pin the downloaded inputs; they are not independently authenticated
publisher checksums. `manifest/inputs.json` records their source URLs.

Local layout:

- `tmp/archives/`: original installer and complete four-disk install archives.
- `tmp/installer/`: pristine installer extraction.
- `tmp/game/`: pristine full-install extraction.
- `tmp/extracted-files.sha256`: local extraction inventory.

To recreate the extractions, download the named archives from their manifest URLs
into `tmp/archives/`, run `make check`, then extract the installer into an empty
`tmp/installer/` and the complete install into an empty `tmp/game/` using `lha x`.
Do not merge into modified game data. Future launches must use a disposable copy.

No launch configuration is selected yet. Read AmigaXDev `docs/index.md` and the
relevant setup guidance when investigation is authorized.
