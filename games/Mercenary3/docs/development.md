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

No launcher, build, tracing or profiling targets exist yet: machine settings and
slave requirements must be established during the later investigation.
