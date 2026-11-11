# Layout

```
AGENTS.md            rules and routing for every game
Makefile             make list | new | check | dist, and every game target with GAME=<Game>
common/              shared by all games; changes here are their own commits
  lib.sh             finds the game, loads game.conf, game.sh and the shared environment
  build.sh run.sh unpack.sh dist.sh check.sh new.sh
  try.sh             unpacks and runs an archive from try/ without a game directory
  mk/game.mk         the targets every games/<Game>/Makefile includes
  tools/             package_release.py, game_server.py (gdb-stub harness on run.sh)
  template/          what `make new GAME=<Game>` copies
docs/                shared docs: true of every game here
games/<Game>/        one release package
try/                 make run here boots any installed archive ([running](running.md))
dist/                release archives (ignored)
```

## A game

```
games/<Game>/
  AGENTS.md          scope, original author, the game's docs and when to read them
  Makefile           include ../../common/mk/game.mk (and any game-specific targets)
  game.conf          configuration every common/ script reads
  game.sh            optional hooks for what game.conf cannot express
  inputs.sha256      the original archives and images, pinned
  src/               the slave source: what is assembled, and what may ship
  tools/             the development harness: captures, reports, checks; never ships
  docs/              this game's docs: open-work.md first, then any others it needs
  release/           ReadMe, release.json, slaves.sha256, other shipped non-source files
  manifest/          optional: pins the tools check (derived files, toolchain, runtime inputs)
  tmp/               ignored: archives/, game/, build/, run/, shots/, captures
```

`src/` is code; `tools/` is everything that measures, captures or checks it. A file the
assembler reads belongs in `src/`, VERIFY-only modules included; a script never does.

The directory name is the game's identity (`GAME=<Game>`, letters and digits), usually the
slave's base name.

## game.conf

Plain shell assignments, read with `$VARIANT` set, so a value can depend on the variant.
The caller's environment (make command-line variables included) beats every value.
`common/template/game.conf` lists them with their defaults:

| Variable | What |
|---|---|
| `TITLE` | the game's name |
| `AUTHOR`, `UPSTREAM` | the original slave's credited maintainer or authors, and its source ([upstream](upstream.md)) |
| `VARIANTS` | the slaves in the package, by base name; the first is the default |
| `GAME_DIR`, `SLAVE_FILE`, `SOURCE` | installed drawer under `tmp/game/`, the slave's file name in it, main source (defaults `$VARIANT`, `$VARIANT.Slave`, `src/$VARIANT.s`). Variants may share a drawer and `SLAVE_FILE` |
| `VASM_FLAGS`, `INCLUDES`, `DEFINES`, `DEFINES_<BUILD>` | the build ([building](building.md)) |
| `KICKS`, `SETUP`, `SETUPS`, `WHD_DEFAULTS`, `JOY0`, `JOY1`, `NTSC`, machine variables | the run ([running](running.md)) |

## game.sh hooks

| Hook | Called by | For |
|---|---|---|
| `game_build BUILD OUT` | build | a build vasm alone cannot do (generated tables, several passes) |
| `game_prepare` | run | defaults that depend on the machine or variant, another emulator binary |
| `game_stop` | stop | refusing to stop (`die`), such as an emulator the game cannot prove it started |
| `game_drives DH0 DH1` | run | extra files on the boot or game drive |
| `game_setup` | run | editing `FSUAE_SETUP_ARGS` after the named machine is applied |
| `GAME_FSUAE_ARGS=(...)` | run | extra FS-UAE arguments |
| `game_unpack` | unpack | installing from disk images or an installer archive |
| `game_dist DIST` | dist | packaging release.json cannot describe (changed icon images, a new installer) |
| `game_check` | check | the game's own checks, such as its `tools/` tests |
