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

## Benchmark

`tools/bench.py OUT` is the repeatable race window: `tools/boot.sh` boots a server stopped at
the program's entry (`PROG_BASE`, default `$400`; `WARP=1 DETERMINISTIC=1 JOY0=none`),
`tools/route.py race` plays the route (fire on the title, fire on the course select for
Offroad, joystick up held from the race loop's first pass, `$158`, then 100 fields), and
the next `WINDOW` fields (default 500; the figures in [internals.md](internals.md) are 200)
are traced in 100-field chunks and reduced. Results go to `OUT/report.txt` (fps, fields
between swaps, work per frame without the waits, DMA slots, hot PCs, the race loop's
routines), `OUT/profile.pkl.gz`, `OUT/chip.pkl.gz` with `OUT/chip.txt` (the CPU's chip
accesses per routine and the pages each DMA channel touches; `tools/chipprofile.py`, from
Encounter) and `OUT/end.png`.

```sh
SETUP=a500 python3 tools/bench.py tmp/prof/a500
SETUP=a1200-030 EXTRA_ARGS=--uae_mmu_model=0 WHD_ARGS="CUSTOM2=1 CACHE" python3 tools/bench.py tmp/prof/030
```

- Traces need a cycle-exact CPU without an MMU: `--uae_mmu_model=0` on the a1200-030.
- Markers are program offsets; the tools find the program from the level-3 vector (`$6C`
  holds base + `$4DAC`) and the slave from `$BC` (trap #15, `_SaveHighScores`), with
  offsets from the selected build's listing (`BUILD`).
- The route anchors on the race loop, not on a field count, because the start sequence
  takes a different time on each machine. The game state at the window's end differs
  between machines anyway: the game runs faster on a faster one.
- `tools/states.py N OUT.npy`, on a server stopped in a race, records the state block
  (`$9860`–`$9D6F`) at the swap for N frames, with the fields between them.

### Experiment: the program in fast memory

Not in `src/`; a scratch copy of the slave (`SOURCE=tmp/exp/BuggyBoyHD.s BUILD=exp`) with:
`ws_ExpMem` `-$10000`; `_DOSVersion` loads `bug.p` to the ExpMem instead of `$3E0` when it
was allocated; `_LoadHighs` calls `$5D4` and returns to `$106` relative to a saved program
base instead of `$400`; before DMA is enabled, `resload_SetCPU` with
`WCPUF_Base_NC|WCPUF_Exp_CB|WCPUF_Slave_CB|WCPUF_IC|WCPUF_DC`. All four allocations stay in
chip. On the a1200-030 the program then runs at `$9E6020`
(`PROG_BASE=0x9E6020 tools/boot.sh`); the title, menus and the race run and draw as with 1.3.

## Traps

- The ReadMe: do not use `NOWRITECACHE`, or the game locks up after saving the high scores.
- `bug.p` is encrypted. Patch offsets are into the decrypted and relocated program
  ([internals.md](internals.md)), not into the file.
- No release is possible from 1.3 as it is: the packager needs a dated `$VER` and a ReadMe
  that differs from the original and names the version. 1.3's `$VER` is `slave 1.3` with
  no game name.
