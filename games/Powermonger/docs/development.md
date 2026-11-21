# Development

Only what differs from the repository's `docs/running.md` and `docs/building.md`: the inputs
and how they are installed, game-specific tools, captures and traps.

## Inputs

`inputs.sha256` pins two files in `tmp/archives/`:

- `Powermonger.lha`: the whdload.de install package v1.4.1, with the slave and the docs.
- `PowerMonger.ipf`: an image of the original disk.

The slave is a DIC install, so it needs a plain sector image, `Disk.1`. `make unpack` runs
`game_unpack` in `game.sh`. It builds `tmp/game/Powermonger` from the install package and
decodes the IPF with `tools/ipf2adf.py`. That tool uses the SPS capsimg library at
`$AMIGA_SHARE/capsimg/capsimg.so` (set `CAPSIMG` to use another one). All 1760 sectors decode
with valid checksums.

AmigaXDev's setup does not install capsimg. Build it from FrodeSolheim's `capsimg`
repository (`./bootstrap`, `./configure` in `CAPSImg/`, `make`) and copy `capsimg.so` to
`$AMIGA_SHARE/capsimg/`. Its structures are packed (`#pragma pack(1)`), which
`tools/ipf2adf.py` follows.

A cracked image is not tested and not pinned. The slave accepts both decruncher variants of
`RUN_PROG`, but a crack changes the program that the patches expect.

## Build

`game.conf` sets `VASM_FLAGS` to Wepl's winstalls flags. The template's flags include
`-devpac`, which turns off vasm's optimizations: the slave then keeps absolute references, and
WHDLoad refuses it with "Slave is illegal, contains relocations". `src/.date` holds the
version date that the source includes with `INCBIN` in the info text and the `$VER:` string.
`make dist` needs the `$VER:` string.

## Running

`WB=0` boots without the Workbench 2.04 floppy, for a setup without `$WORKBENCH_ADF`. The
game does not need it.

## Builds

| `BUILD` | Defines | For |
|---|---|---|
| `release` | none | the slave that ships |
| `quick` | `QUICKSTART=1` | scripted runs: no name entry, a random land, a constant random seed, frames drawn counted at `$f8` (with CUSTOM4), the address of the partial copy's shadows at `$f4` |
| `norel` | `QUICKSTART=1 NORELOC=1` | the same without the renderer relocation, for comparisons |
| `spin` | `QUICKSTART=1 SPIN=1` | the camera turns on every frame drawn: every frame differs |

## Tools

- `tools/ticks.sh [SECONDS] [N]`: ticks, fields, fields per tick and frames per second of a
  running `make serve BUILD=quick`.
- `tools/state_at_tick.sh BUILD SETUP "WHD_ARGS" TICK OUT`: boots, stops at the world step
  of a tick and dumps chip memory.
- `tools/pass_writes.sh BUILD "WHD_ARGS" [TICK] [PASSES]`: which call sites of the main loop
  change the world state, pass by pass.
- `tools/defeat.sh BUILD SETUP "WHD_ARGS"`: the tick and field at which the hands-off game is
  lost, a check of the game pace.
- `tools/shadowcheck.sh SETUP "WHD_ARGS" [SAMPLES] [EXTRA_ARGS]`: checks the partial copy's shadows
  against the chip buffers during play (`BUILD=spin` for the turning view).
- `tools/ipf2adf.py`: the IPF decoder for `make unpack`.
- A Furia-like machine: `SETUP=a500-020 EXTRA_ARGS=--uae_cpu_frequency=37500000`.

## Traps

- `make server CMD='...'` passes the command through the shell, so a gdb expression with
  parentheses fails. The tools call `common/tools/game_server.py` directly.
- A `gdb` command to a running machine resumes it afterwards. Send `stop` first to keep it
  stopped at a breakpoint.
- After `quit` the tools run `make stop`, which stops this game's emulator through the
  shared pid-scoped `fsuae_common.sh`.
- The game seeds its random numbers from the beam position, so compare runs only with the
  QUICKSTART build, and expect differences across machines anyway (field timers).
- FS-UAE gdb watchpoints are slow: set one only for a short span, for example from `$129b6`
  to the swap, and delete it after it triggers. The gdb stub ignores memory writes (`set`):
  change the game state through a test build (`SPIN=1`, QUICKSTART's seed).
- The 68030 MMU core records no instructions in a profile.
