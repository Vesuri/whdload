# Legends of Valour — Amiga WHDLoad patches

WHDLoad slave patches for the original 1992 game from US Gold / Synthetic Dimensions.
The slave is reconstructed from CFou!'s v1.0 disassembly using WHDLoad 20.0's KickEmu
sources. Release **2.0b is a beta**. One slave enhances the English, German and French
games of CFou!'s preinstalled archives (0837, 0525 and 1768; [versions.md](docs/versions.md));
any other version supported by the original install runs as CFou!'s v1.0. For a German or
French install, copy `LegendsOfValour.Slave` over its `LegendsOfValourDe.Slave` or
`LegendsOfValourFr.Slave` and add `CUSTOM2=1` to its icon.

The player-facing options are:

| Option | Tooltype |
|---|---|
| Character creation | `CUSTOM1=1` |
| Enhanced frame rate | `CUSTOM2=1` |

The release's installed icon sets `CUSTOM2=1`; `CUSTOM2=0` runs the original game, apart
from one fix in every setting: the game's own graphics.library calls (`RectFill`, `SetRast`,
`Draw`) now wait for their blit. Without the wait, text drawn by the CPU straight after a
`RectFill` lost bitplanes on fast CPUs (red and green first words; [performance-patches.md](docs/performance-patches.md)).
Enhanced frame rate turns on everything at once:

- six validated rendering improvements: CPU-selected chunky-to-planar conversion,
  PUBLIC-memory chunky allocation, wall and sprite loop improvements, cached ray quotients
  and faster clearing, with automatic CPU choices and allocation fallbacks
  ([measurements and methodology](docs/profiling.md) cover the A500-equivalent and 14 MHz
  68020);
- frame-independent game timing (25 ticks/second), which can reduce rendering speed on slow
  machines;
- one-degree precision for direct mouse control (allocation failure falls back to the
  original five degrees); UI turn buttons keep their native increments and repeat;
- click inputs: a click acts once until the mouse button is released, so the U-turn and the
  other screens no longer repeat while it is held; walk, turn and the compass keep moving
  while held.
F10 quits, or use WHDLoad's `QuitKey` tooltype.

## Setup

Keep these original archives locally; they are not part of the repository and are pinned
in `inputs.sha256`:

```
LegendsOfValour_v1.0_0837.lha     preinstalled English game (the game data)
LegendsOfValour_v1.0_De_0525.lha  preinstalled German game
LegendsOfValour_v1.0_Fr_1768.lha  preinstalled French game
LegendsOfValour.lha               original installer (repackaged by make dist)
```

`make unpack ARCHIVES=<directory holding them>` copies them into `tmp/archives/`, verifies
them and installs the games into `tmp/game/LegendsOfValour/`, `LegendsOfValourDe/` and
`LegendsOfValourFr/`.

Building needs make, vasm's Motorola 68000 assembler, WHDLoad development headers, and
Amiga NDK headers, all from AmigaXDev's shared environment (the repository's
`docs/building.md`). Python 3 supports the inspection and packaging tools. Local gameplay
uses FS-UAE, the shared launcher, Workbench 2.04, WHDLoad, and Kickstart images. Tracing
additionally needs the Barto-enabled FS-UAE build and m68k GDB described in
[profiling.md](docs/profiling.md).

The game slave requires WHDLoad 17+, Kickstart 1.3 `kick34005.A500` and its `.RTB`.
It reserves 512 KiB chip memory and 656 KiB other memory, with additional memory needed
for WHDLoad, allocations and optional features. The emulator's host ROM is separate
from the Kickstart 1.3 image used by the slave; see the runtime path table in
[profiling.md §1](docs/profiling.md#1-host-setup).

## Build and play

From this directory:

```sh
make run                          # build the release slave and boot it, original game
make run WHD_ARGS=CUSTOM2=1       # Enhanced frame rate, as the installed icon sets it
make run SLAVE=original           # CFou!'s v1.0, unchanged
make run GAME_DIR=LegendsOfValourDe SLAVE_FILE=LegendsOfValourDe.Slave WHD_ARGS=CUSTOM2=1
                                  # the German game (LegendsOfValourFr for French)
```

The launcher defaults to a 68000 with 1 MiB chip and 8 MiB fast RAM (`game.conf`);
reference capture machines are specified separately in
[profiling.md §3](docs/profiling.md#3-the-machine).

An expanded 68020 trial can be launched with:

```sh
make run AMIGA_MODEL=A1200 CPU=68EC020 CHIP_KB=2048 FAST_KB=4096 SLOW_KB=0 \
  KICKSTART="$KICKSTART_A1200" WHD_ARGS=CUSTOM2=1
```

The launcher copies the game into a fresh run directory (`tmp/run/default/`) each time.
Save games written there are lost on the next launch: copy any you want to keep before
restarting. `make stop` stops it. The repository's `docs/running.md` lists every option.

## Development and validation

```sh
make developer       # tmp/build/developer/LegendsOfValour.Slave
make verify          # tmp/build/verify/LegendsOfValour.Slave
make check           # the release slave matches release/slaves.sha256; tapes, ray tables,
                     # src/offsets.s and the signatures in all three versions
```

Developer builds keep a CUSTOM2 bit for each enhancement (W1–W6, timing, mouse precision,
click inputs). VERIFY adds input tapes, pixel twins,
and simulation checks; it must not ship. `VASM_EXTRA='-DTIMING_STUDY=1'` adds a study's
defines to one build. All builds are assembled afresh, each once per language, with the
German and French differences appended as a fixup table ([versions.md](docs/versions.md)).

Use [profiling.md](docs/profiling.md) for capture commands and fixed-window A/B checks,
[performance-patches.md](docs/performance-patches.md) for rendering invariants,
[simulation-timing.md](docs/simulation-timing.md) for timing validation, and
[one-degree-turning.md](docs/one-degree-turning.md) for fine-turning checks. Captures run
one at a time with `JOY0=none` as `INSTANCE=cap` (`tmp/run/cap/`), separate from interactive
sessions.

## Release archives

```sh
make dist
```

Builds `LegendsOfValourEnhanced-2.0b-20261108.lha` (version and date from the slave's `$VER`)
from the original installer in the repository's `dist/`. Only the slave, the ReadMe and the
six game icons (`CUSTOM2=1` added to their tooltypes) are replaced; the entry list and every
other compressed record are preserved. Packaging verifies CRCs, replacement contents and the
icons' tooltypes before publishing the local output. See [releasing.md](docs/releasing.md).

Original game/ROM bytes and generated artifacts are local only, under ignored `tmp/`
and `dist/`; archives are not committed.

## Remaining acceptance and limitations

Automated checks pass on both reference CPUs. One-degree mouse precision has been accepted in
play testing; the UI buttons retain native behavior. Timing and click inputs may receive
further adjustments from play feedback. The German and French games pass the install
checks and the VERIFY twins; their gameplay has not been play-tested.
The tape cannot wait for a conversation panel's input poll, so affected routes dismiss
it with repeated EXIT clicks. See [open-work.md](docs/open-work.md) for current items.
W7's further renderer redesign was dropped by user decision.
