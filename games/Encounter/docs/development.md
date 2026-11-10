# Development

Only what differs from the repository's `docs/running.md` and `docs/building.md`.

## Inputs

`inputs.sha256` pins two archives; `make unpack ARCHIVES=<directory>` installs both, no
`game_unpack` needed:

| Archive | Unpacks to | What |
|---|---|---|
| `Encounter.lha` | `tmp/game/EncounterHD` | the whdload.de install package: slave 1.2, Patcher imager, Install, ReadMe, `source/` (`EncounterHD.asm`, Harry's `encounterimager05.asm`, a Barfly `Makefile`) |
| `Encounter_v1.2_0651.lha` | `tmp/game/Encounter` | the installed game (SPS 0651): `disk.1`, the same 1.2 slave as `Encounter.slave` |

The two archives' slaves and ReadMes are identical, and the package's `EncounterHD.asm` is
byte-identical to upstream's `E/Encounter/usr/source/EncounterHD.s` (`src/`).

## Build

The default vasm build (`-m68000 -x -devpac -Fhunkexe -nosym`), no defines. It is not
byte-identical to the shipped slave (672 bytes; ours is 656, recorded in
`release/slaves.sha256`), and cannot be without changing the source: JOTD assembled it
with Barfly (`IFD BARFLY`), which

- appends the build date to `DECL_VERSION`, twice (`1.2 (07-jan-08  22:52:49)` in the
  info text and in `$VER`), from `INCBIN "T:date"` under `IFD BARFLY`; vasm cannot take that
  branch (`OUTPUT`, `BOPT`, `SUPER`, `DOSCMD` are Barfly directives), so ours says `1.2`;
- optimises (`BOPT O+`): `moveq` for `move.l #1`, `moveq #$6F; not.b` for `move.l #$90`,
  `bsr.s` for the explicit `bsr.w DBFD1`, `addq` for `add.l #resload_Abort`, `clr` for the
  `move #0` stores to `$DFF101`, `$DFF104`, `$DFF106`, and `andi`/`cmpi` encodings where
  vasm uses `and #`/`cmp #`.

Compared after the strings (shipped code from file offset `$CC`, ours from `$A0`,
disassembled with objdump): the same instruction sequence, differing only in those
encodings and the PC-relative offsets they move. The header differs only in the offsets of
the code and strings (`ws_GameLoader`). vasm's own optimiser (`-opt-clr`, no `-devpac`)
gets closer (628 bytes) but still not identical; the repository default is kept.

## Running

`SETUP=a500` (the default) and `a1200` (`SETUPS`). Direct slave: `KICKS` is empty.

```sh
WARP=1 WINDOW=none python3 tools/encounter.py serve &   # boot with the gdb stub
python3 tools/encounter.py wait 8
python3 tools/encounter.py shot tmp/shots/x.png
python3 tools/encounter.py quit
```

Without `BUTTONWAIT` the title picture is up only during the main load and the game
starts its attract-mode demo (in play, score counting) within a few seconds under `WARP=1`;
`WHD_ARGS=BUTTONWAIT` holds the title screen ("Loading - please wait") for a screenshot.
`SLAVE=original` boots the shipped 1.2.

## Traps

- The program region `$6000`–`$13000` is encrypted in `disk.1`; read patched instructions
  from a decrypted image (the loop in `src/EncounterHD.s`, [internals.md](internals.md)),
  not from the file.
- No release is possible from 1.2 as it is: the packager needs a dated `$VER` and a ReadMe
  that differs from the original and names the version. `release/release.json` replaces
  the slave, the ReadMe and `source/EncounterHD.asm` by name and keeps the imager source
  and Makefile as shipped (the `source` drawer option would drop them).
