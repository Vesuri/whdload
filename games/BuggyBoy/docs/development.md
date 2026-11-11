# Development

Only what differs from the repository's `docs/running.md` and `docs/building.md`.

## Inputs

`inputs.sha256` pins two archives; `make unpack ARCHIVES=<directory>` installs both, no
`game_unpack` needed:

| Archive | Unpacks to | What |
|---|---|---|
| `BuggyBoy.lha` | `tmp/game/BuggyBoyInstall` | the whdload.de install package: slave 1.3, `BuggyBoy.islave` (RawDIC), Install, icons, ReadMe, `source/` (`BuggyBoyHD.s`, `ReadJoypad.s`, `BuggyBoy.islave.s`, JOTD's `Makefile_windows.mak`) |
| `BuggyBoy_v1.3_0465.lha` | `tmp/game/BuggyBoy` | the installed game (Retroplay 0465), the DOS version: `data/` (`bug.p`, `bug.o`, `graphics`, `COURSES.DAT`, ...), the same 1.3 slave as `BuggyBoy.slave` |

The two archives' slaves and ReadMes are identical. The package's three `.s` files are
byte-identical to upstream's `B/BuggyBoy/usr/source` at eb73c315 (and at every commit since
b6abf976, 2022-11-25); only its makefile is a different revision of upstream's.

## Build

`-m68000 -pic -x -devpac -Fhunkexe -nosym`, no defines. Two things differ from the shipped
build:

- **`keyboard.s`.** The slave includes WHDLoad's `whdload/keyboard.s`. The 20.1 file reads
  `_resload` absolute in two places (the debug key's `resload_Control` and the quit path's
  `resload_Abort`; its history: "21.03.12 pc-relative for _resload access removed"). That
  gives the slave a relocation hunk, and WHDLoad refuses it at start ("Slave is illegal,
  contains relocations"). The shipped slave has both PC-relative. `game.sh`'s `game_build`
  writes a copy of the installed 20.1 file with `,pc` added to those two operands to the
  ignored `tmp/include/whdload/keyboard.s`, which `INCLUDES` puts ahead of
  `$WHDLOAD/Src/sources`. It stops if the file no longer has exactly two such operands.
  `-pic` makes any relocation a build error. The release's `source/` drawer gets only the
  game's own files, so a user rebuilding it against a stock 20.1 tree meets the same refusal.
- **The date.** JOTD's makefile passes `-DDATETIME` and writes the build time to a
  `datetime` file the version macro includes. Without it ours says `1.3` in `$VER` and in the
  info text, 48 bytes shorter (3440 bytes; `release/slaves.sha256`).

With the shipped date string the build is byte-identical to the shipped slave (3488 bytes):

```sh
printf '(13-apr-2022  23:45:41)' > tmp/datetime
make build BUILD=shipped VASM_EXTRA="-DDATETIME -Itmp"
cmp tmp/build/shipped/BuggyBoy.Slave tmp/game/BuggyBoy/BuggyBoy.slave
```

## Running

`SETUP=a500` (the default) and `a1200` (`SETUPS`). Direct slave: `KICKS` is empty.

```sh
make serve WARP=1 WINDOW=none &
make server CMD='wait 18'; make server CMD='shot tmp/shots/x.png'; make server CMD=quit
```

Under `WARP=1` both machines are in the attract sequence by 10 to 18 s: the course select
(T1 Offroad to T5 South) and the high-score table. `SLAVE=original` boots the shipped 1.3.
`WHD_ARGS=BUTTONWAIT` holds the title picture; `CUSTOM1` (trainer), `CUSTOM2` (frame rate)
and `CUSTOM3` (CD32 pad) are the slave's options ([internals.md](internals.md)).

## Traps

- The ReadMe: do not use `NOWRITECACHE`, or the game locks up after saving the high scores.
- `bug.p` is encrypted. Patch offsets are into the decrypted and relocated program
  ([internals.md](internals.md)), not into the file.
- No release is possible from 1.3 as it is: the packager needs a dated `$VER` and a ReadMe
  that differs from the original and names the version. 1.3's `$VER` is `slave 1.3` with
  no game name.
