# Development

Only what differs from the repository's `docs/running.md` and `docs/building.md`.

## Inputs

`inputs.sha256` pins two archives, which `make unpack` installs side by side in `tmp/game/`:

| Archive | Installs | Slave |
|---|---|---|
| `Virus.lha` (whdload.de) | `Virus-install/`: installer, RawDIC imager (`Virus.islave`), README | V1.0 (15.01.99) |
| `Virus_v1.0_0004.lha` (Retroplay) | `Virus/`: `Disk.1` (184320 bytes, the whole disk), ReadMe, icons | the same bytes |

The runs boot the Retroplay drawer `Virus/`.

## The build

`src/Virus.s` is a reconstruction: the package has no source, and neither JOTD's nor
StingRay's repository holds the slave. It was disassembled from the shipped `Virus.slave`
and rebuilds it byte for byte (`release/slaves.sha256`). `-no-opt` keeps the shipped
encodings (`move.l #1,d0` rather than `moveq`, `lea ($1000).w`). The labels and comments are
ours; the header, code and data are the shipped slave's, including an unreferenced routine
(`_clamp`, [internals](internals.md#slave-patches)).

## Driving it

`make serve WARP=1 WINDOW=none &`, then `make server CMD=...`. About 15 s in warp reaches the
attract mode on the a500+. Keys go through the stub as raw hex codes:
`CMD='gdb monitor key 59 1'` presses F10, `... 59 0` releases it; with `VERIFY_EXIT=1`,
F10 leaves `OK` in `tmp/run/default/.run/dh0/whdload-exit.txt`.

## Traps

- `ws_BaseMemSize` is 544 KB, all chip memory, so WHDLoad cannot run it on a 512 KB chip
  machine: `SETUP=a500` stops with "you need chipmem up to $88000 (544 Kbyte)". The
  default setup is the `a500+` (1 MB chip).
