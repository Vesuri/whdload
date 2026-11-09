# Running

`make run` boots the game under WHDLoad in FS-UAE through `common/run.sh`. Inside
`games/<Game>` it runs that game; at the root it needs `GAME=<Game>`. The options are
variables, on the make command line or in the environment:

```sh
make run                                     # release build, the game's default machine
make run SETUP=a1200-060 BUILD=verify WHD_ARGS='CUSTOM1=1'
make run SETUP=a500 FAST_KB=2048 NTSC=1      # a named machine with changes
make run SETUP=custom CPU=68020 CHIP_KB=1024 FAST_KB=8192
make run SLAVE=original                      # the shipped slave from the pristine install
make run SLAVE=tmp/other.Slave DEBUG=1       # any slave, with the gdb stub
make run VARIANT=Name                        # another slave of the package
make run INSTANCE=b SLAVE=original           # a second emulator beside the first
make stop [INSTANCE=b]
```

| Variable | What |
|---|---|
| `SETUP` | an AmigaXDev named machine (`a500`, `a500-1.5m`, `a500+`, `a500-020`, `a500+-020`, `a3000`, `a1200`, `a1200-fast`, `a1200-030`, `a1200-040`, `a1200-060`), or `custom` for no preset. Default: the game's `SETUP` |
| `CPU`, `CHIP_KB`, `FAST_KB`, `SLOW_KB`, `AMIGA_MODEL`, `KICKSTART` | single settings. Given by the caller they also change a named machine; `game.conf`'s apply only to `SETUP=custom` |
| `BUILD` | the build to make and run: `release` (default), `verify`, `developer` or the game's own |
| `SLAVE` | `original`, or a slave file (relative to where make started); skips the build |
| `NOBUILD=1` | run the existing build |
| `VARIANT` | the slave, for packages with several |
| `WHD_ARGS` | WHDLoad options after the game's `WHD_DEFAULTS` |
| `INSTANCE` | another emulator of the same game with its own drives, run directory and gdb-stub port |
| `DEBUG=1`, `WARP=1`, `SOUND`, `WINDOW=front\|back\|none`, `RECORD`, `DETERMINISTIC`, `EXTRA_ARGS`, `FSUAE` | AmigaXDev's launcher options (its `docs/reference/headless-fsuae.md`) |
| `NTSC=1`, `JOY0`, `JOY1`, `JOY0_MODE`, `JOY1_MODE` | video timing and ports |
| `WB=0` | boot without the Workbench floppy. It only supplies `C:` and `LIBS:`, but it changes where the game is loaded, so a game whose captures depend on addresses may set `WB=0` in `game.conf` |
| `WAIT=1` | stay until the emulator exits |
| `VERIFY_EXIT=1` | WHDLoad's result (`OK`/`FAIL`) in `tmp/run/<instance>/.run/dh0/whdload-exit.txt` |

The machine definitions are AmigaXDev's (`docs/reference/headless-fsuae.md`, "Named machine
setups"). A setup a game is tested on goes in its `SETUPS`.

## Trying a game without a directory

`try/` boots any installed WHDLoad archive (a Retroplay-style `.lha`, `.lzh`, `.lzx` or
`.zip`) before it has a `games/<Game>` directory, to judge a candidate:

```sh
cd try
curl -O 'https://.../StarWars_v2.0_0403.lha'
make run SETUP=a1200-040                     # the newest archive here, its shipped slave
make run ARCHIVE=other.lha VARIANT=Name      # another archive; another slave of it
make list                                    # the slaves the archive holds
make serve &                                 # gdb-stub server (DEBUG=1); then:
make server CMD='shot tmp/x.png'             # or CMD='wait 5', CMD=quit
make stop | make clean
```

`common/try.sh` unpacks the archive once into `try/tmp/<archive name>/tmp/game/` (again
when its SHA-256 changes, or with `FORCE=1`), writes a `game.conf` beside it and hands over
to `common/run.sh`, so every option above applies; `SLAVE=path` runs another slave. Every
Kickstart in `$AMIGA_SHARE/Kickstarts` goes to `DEVS:Kickstarts`. The icon's tooltypes are
not read: pass what they set in `WHD_ARGS`. `make serve` and `make server` drive the boot
through `common/tools/game_server.py`'s built-in commands; their relative paths are
relative to `try/tmp/<archive name>/`. `ARCHIVE=` also takes a file elsewhere
(`make -C try run ARCHIVE=<file>`). Everything under `try/` but its `Makefile` is ignored.

## What a boot does

Kickstart 3.1 and the Workbench 2.04 floppy boot `DH0`, whose startup-sequence runs
`WHDLoad <SLAVE_FILE> <WHD_DEFAULTS> <WHD_ARGS>` on `DH1`. `DH1` is a fresh copy of
`tmp/game/<GAME_DIR>` with WHDLoad and the selected slave, so saves and preferences never
reach the pristine install. `KICKS` names the Kickstart images the slave needs in
`DEVS:Kickstarts` (`kick34005.A500` for kick13 slaves); their `.RTB` comes along.

Each game and instance runs in `games/<Game>/tmp/run/<instance>/`. AmigaXDev's launcher
derives the gdb-stub port from that directory and stops only the emulator it started there,
so any number of games and instances run at once. Screenshots go to `tmp/shots/`.

## Driving it

`common/tools/game_server.py` wires AmigaXDev's gdb-stub server (`amigaxdev.gdbserve`) to
this launcher: a game tool is a few lines (the module's docstring), and
`python3 tools/<game>.py serve` boots with `DEBUG=1` and every run option above. Commands
such as `shot`, `wait`, `profile` and `quit` then go to the running server.

## Game data

`make unpack ARCHIVES=<directory>` copies each file named in `inputs.sha256` from that
directory into `tmp/archives/` (of several copies, the one whose hash matches), checks it, and unpacks the archives into `tmp/game/`. The
archives stay outside the repository; nothing records where they came from.
