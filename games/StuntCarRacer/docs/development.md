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
(the import commits record it). `-devpac` (no optimisation) matches; the slave has no
relocations. The `INCDIR SOURCES:Include/` line stays; vasm finds `whdload.i` through `-I`.

`src/relocs.s`, the fast copy's relocation table (internals.md), is generated; regenerate it
after changing the tool's lists:

1. `python3 -I tools/scr_extract.py Disk.1 tmp/scr/pal.bin` writes the decrypted main program
   as it lies at $e700 (`--ntsc` for Stunt Track Racer's disk).
2. Build Stunt Car Racer Unleashed at tag 1.1 (`git archive 1.1` of that project into
   `tmp/unleashed`) as a hunk executable with a listing:
   `vasmm68k_mot -m68000 -x -Fhunkexe -nosym -DWHDLOAD=1 -L tmp/ul/pal.lst -o tmp/ul/pal.exe
   StuntCarRacer.s`. vasm needs its two `jmp (pc,dN.w)` written `jmp *+2(pc,dN.w)`.
3. `python3 -I tools/unleashed_diff.py tmp/scr/pal.bin tmp/ul/pal.exe tmp/ul/pal.lst
   --report tmp/ul/pal-diff.txt --relocs tmp/ul/pal-relocs.txt --asm src/relocs.s`.

`--report` is also the list of everything Unleashed changed, beside its source lines.

The Unleashed blob (`src/unleashed.s`, internals.md) is built by `tools/ulblob.py` from
`game_build` (game.sh) into the ignored `tmp/include/`. `src/unleashed_syms.i` names the
original's addresses with Unleashed's labels. After changing the blob, check its patch
table against the original: `python3 -I tools/ulblob.py tmp/include --original
tmp/scr/pal.bin` must report no problems (a patch that splits an instruction or covers a
branch target corrupts the copy silently). Stunt Track Racer builds the same blob for NTSC and includes
`src/relocs.s`: a change here changes its slave too.

## Driving it

`INSTANCE=<name> python3 tools/scr.py serve &` boots with the gdb stub (run options through
the environment); then `python3 tools/scr.py fields N`, `keys K[:N] ...`, `peek ADDR N`,
`shot x.png`, `gdb CMD`, `quit`. Both variants reach the main menu in about 1100 fields.
From there `keys 1:150 44:150 44:150 44:150 44:150 44:400 44:400` reaches a practice race
on the Little Ramp; hold RETURN (`44+`) to drive, S and D steer.

To look for missed relocations, drive the verify build on `SETUP=a1200-030` with
`WHD_ARGS='CUSTOM3=1 MMU'`: a read or write of the chip copy stops with an access fault, and
the core dump (`python3 -m amigaxdev.whdldump tmp/run/<instance>/.run/dh1`) names the
accessor.
