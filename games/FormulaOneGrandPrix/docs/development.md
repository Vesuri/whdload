# Development setup

AmigaXDev supplies the shared tools and documentation. Its `make setup` installs
`~/.local` and `~/.local/share/amiga`. Source `amiga/env.sh` to use that environment;
`AMIGA_ENV` can select a different shared environment file. Shared tool, ROM and
WHDLoad paths are supplied by that file, not by copies from other projects.
The launcher uses `KICKSTART`, `KICK13`, `RTB`, `WORKBENCH_ADF`, `WHDLOAD_BINARY`,
`FSUAE_COMMON` and, for the gdb server, `FSUAE_ARM`.

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
Do not merge into modified game data.

## Running

`amiga/run.sh` copies `tmp/game/FormulaOneGrandPrix4Disk` to the disposable
`amiga/.run/dh1`, boots Kickstart 3.1 with the Workbench 2.04 floppy and runs
`WHDLoad FormulaOneGrandPrix4Disk.Slave PRELOAD SPLASHDELAY=0 NOREQ`. The default machine
is the A500-equivalent: 68000, 512 KB chip, 1.5 MB slow, no fast RAM. `AMIGA_SETUP`,
`CHIP_KB`/`SLOW_KB`/`FAST_KB`, `WHD_ARGS` (for example `CUSTOM1=1`), `SLAVE`, `DEBUG`,
`WARP` and the other shared launcher variables apply.

`python3 tools/f1gp.py serve` boots with `DEBUG=1` on the native FS-UAE (`FSUAE_ARM`
unless `FSUAE` is set) and serves the shared `amigaxdev.gdbserve` commands
(`shot PNG`, `wait S`, `gdb TEXT`, `profile N BIN`, `quit`). Drive input with
`gdb monitor mouse DX DY`, `gdb monitor input JOY1_FIRE_BUTTON 1|0`,
`gdb monitor key RAW 1|0` and `gdb monitor fields N` while stopped. One mouse count
moves the game's pointer one screenshot pixel in both axes.
