# Development

## Inputs

`inputs.sha256` pins three archives:

- `StuntCarRacer.lha`: Codetapper's and StingRay's v1.4 install package from whdload.de,
  with the slave's source (`StuntCarRacerHD/Source/StuntCarRacer.s`), the Install script
  (DIC for the disk, file copy for TNT), the icons, a save file and two lap-time files.
- `StuntCarRacer_v1.4_0222.lha`: the Retroplay install of the original disk (`Disk.1`, a
  468480-byte DIC image of the start of the disk).
- `StuntCarRacerTNT_v1.4.lha`: the Retroplay install of AmiGer/CARE's TNT version
  (`SCR-TNT`, an AmigaDOS executable).

`make unpack` installs all three; the two Retroplay drawers are the `StuntCarRacer` and
`StuntCarRacerTNT` variants. Both run the same slave.

## The build

`src/StuntCarRacer.s` is the package's source (the import commit has it unchanged) with nine
`cmp`/`add`/`and #imm,Dn` written as `cmpi`/`addi`/`andi`: StingRay's assembler emits the
immediate forms, vasm the Dn forms. With that it builds the v1.4 slave byte-identically
(`release/slaves.sha256` records it). `-devpac` (no optimisation) matches; the slave has no
relocations. The `INCDIR SOURCES:Include/` line stays; vasm finds `whdload.i` through `-I`.

## Driving it

`make serve WARP=1 WINDOW=none INSTANCE=<name> &`, then `make server INSTANCE=<name> CMD=...`.
Both variants reach the main menu within about 25 s of warp.
