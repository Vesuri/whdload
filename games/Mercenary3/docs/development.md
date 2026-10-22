# Development

## Inputs

- [Official WHDLoad page](https://whdload.de/games/Mercenary3.html).
- [Official installer](https://whdload.de/games/Mercenary3.lha).
- [User-supplied full install](https://ftp2.grandis.nu/turran/FTP/Retroplay%20WHDLoad%20Packs/Commodore_Amiga_-_WHDLoad_-_Games/M/Mercenary3_v1.2_0356.lha).

`manifest/inputs.json` pins archive URLs and SHA-256 hashes. File manifests record
relative names and hashes only. Downloaded and extracted bytes remain ignored:

| Path | Purpose |
| --- | --- |
| `tmp/archives/` | Original archives and SHA-256 sidecars |
| `tmp/game/Mercenary3_v1.2_0356/Mercenary3/` | Pristine installed game |
| `tmp/installer/Mercenary3/` | Pristine official installer, including source |

`make check` checks every archive and extracted file against the pinned manifests,
including unexpected files. It never runs the game or inspects code.
For restoring inputs, download the exact named archives from the recorded URLs,
verify their SHA-256 hashes before extracting, then extract each into its recorded
extraction directory. Preserve any differing existing files separately first.

## Shared environment

Source `amiga/env.sh` from the repository root. `AMIGA_ENV` can override the shared
environment file, whose default is `~/.local/share/amiga/env.sh`. Missing shared
environment files fail explicitly. Shared tool and ROM paths are inherited from it;
no local copies or paths into other projects are used.

## Running

`amiga/run.sh` boots Kickstart 3.1 from a generated `DH0` that runs
`WHDLoad Mercenary3.Slave PRELOAD` on `DH1`, a disposable copy of the pristine drawer
under ignored `amiga/.run/`. The default machine is the A500-equivalent (68000, 512 KB
chip, 1.5 MB slow, no fast RAM); the slave needs 512 KB chip and WHDLoad needs other
memory beside it. Variables: `SLAVE`, `WHD_SPLASH=1`, `WHD_ARGS`, and the shared
launcher's (`AMIGA_SETUP`, `CPU`, `CHIP_KB`, `SLOW_KB`, `FAST_KB`, `DEBUG`, `WARP`,
`DETERMINISTIC`, `JOY0`, `JOY1`, `SOUND`, `WINDOW`). Defaults: mouse in port 0,
keyboard joystick in port 1.

The debugger server uses the native build:

```sh
. amiga/env.sh
FSUAE="$FSUAE_ARM" JOY0=none python3 tools/merc3.py serve > tmp/serve.log 2>&1 &
python3 tools/merc3.py gdb 'monitor fields 400'
python3 tools/merc3.py shot tmp/shots/now.png
python3 tools/merc3.py quit
```

## Building

`make original` assembles `whdload/original/Mercenary3.slave.asm` with vasm
(`-no-opt`, the shared `WHDLOAD` includes) into `tmp/build/` and requires it to equal
the shipped slave byte for byte. `BUILD` overrides the output directory.

No patched build, fixed-window or profiling targets exist yet.
