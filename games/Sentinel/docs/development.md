# Development

Only what differs from the repository's `docs/running.md` and `docs/building.md`.

## Inputs

`inputs.sha256` pins two archives. Both hold a `Sentinel/` drawer, so `make unpack` installs
the first and keeps it:

| Archive | Holds | Slave |
|---|---|---|
| `Sentinel_v1.01_3025.lha` (Retroplay) | `tmp/game/Sentinel/`: `Disk.1` (SPS 3025, RawDIC, 160 KB), the slave | V1.01 (15.09.2017) |
| `Sentinel.lha` (whdload.de) | installer, RawDIC imager (`Sentinel.islave`), source, ReadMe | the same bytes |

The install package is not unpacked into `tmp/game/`; extract it by hand to read it
(`$LHA xqw=tmp/pkg tmp/archives/Sentinel.lha`). The release packager reads it from
`tmp/archives/`.

## The build

`src/Sentinel.s` is the package's `Source/Sentinel.s` (the import commit has it unchanged)
with one commented edit: `cmp.w #$67e7,d0` written as `cmpi.w`, which StingRay's assembler
emits and vasm would optimise to the Dn form. The build then equals the shipped slave in
every byte but the last word of the code hunk, the padding to a longword after the final
`rts`: vasm pads with `nop` (`$4E71`), the shipped slave has `$CF50`, never executed.
`release/slaves.sha256` records the vasm build.

`-devpac` (no optimisation) matches: the source sizes its branches. StingRay's
`INCDIR SOURCES:Include/` stays; vasm finds `whdload.i` through `-I`. `DEBUG` stays
commented out (it would set `ws_CurrentDir` to his development drawer).

## Driving it

`make serve WARP=1 WINDOW=none &`, then `make server CMD=...`; keys go through the stub,
`CMD='gdb monitor key 40 1'` then `... 40 0` (raw codes: space `$40`, return `$44`, F10 `$59`).
From boot, 20 s in warp reaches "Press any key" on the title; space asks for the landscape
number; return with nothing typed gives landscape 0000's overview and "Press any key";
return again starts the landscape, which draws the first view about 10 s later.
