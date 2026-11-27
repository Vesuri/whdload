# Development

Only what differs from the repository's `docs/running.md` and `docs/building.md`.

## Inputs

`inputs.sha256` pins two archives, both installed by `make unpack`:

| Archive | Drawer under `tmp/game/` | What |
|---|---|---|
| `EmpireStrikesBack.lha` | `EmpireStrikesBackHD` | Codetapper's v1.2 install package from whdload.de: the slave, the Install script (RawDIC with `EmpireStrikesBack.islave`), icons, a high-score file; no source. `make dist` repacks it |
| `EmpireStrikesBack_v1.2_1235.lha` | `EmpireStrikesBack` | the Retroplay install: `Disk.1` (440320 bytes) and the same slave; the run's drawer |

The two archives' slaves are the same file (SHA-256
`aeea2c6ba89739e8d94c6a609b222fbf15aee159afc4228ee50a91f2097daf7e`, 1044 bytes).
The Retroplay `Disk.1` is the second version the slave knows (title picture at $2800).

## The build

The v1.2 slave shipped without source. `src/EmpireStrikesBack.s` is a reconstruction from
its disassembly that builds it byte for byte (`release/slaves.sha256` records it): the labels
and comments are new, the instructions are the slave's. `-devpac` (no optimisation)
matches; the slave has no relocations.

## Driving it

`make serve WARP=1 WINDOW=none INSTANCE=<name> &`, then `make server INSTANCE=<name> CMD=...`
(give the server a few seconds to come up). `wait 45` reaches the attract's high-score page.
