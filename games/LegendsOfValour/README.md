# Legends of Valour — Amiga WHDLoad patches

WHDLoad slave patches for the original 1992 game from US Gold / Synthetic Dimensions.
The slave is reconstructed from CFou!'s v1.0 disassembly using WHDLoad 20.0's KickEmu
sources. Release **1.1b is a beta**, validated with the English game in the 0837 archive.
Other versions supported by the original install have not been revalidated.

Release builds automatically enable the six validated rendering improvements:
CPU-selected chunky-to-planar conversion, PUBLIC-memory chunky allocation, wall and sprite
loop improvements, cached ray quotients and faster clearing. CPU-specific choices and
allocation fallbacks are automatic. [Measurements and methodology](docs/profiling.md)
cover the A500-equivalent and 14 MHz 68020.

The player-facing options are:

| Option | Tooltype |
|---|---|
| Character creation | `CUSTOM1=1` |
| Frame-independent game timing (25 ticks/second) | `CUSTOM2=64` |
| Fine turning (one-degree taps and rendering) | `CUSTOM2=128` |
| Both timing and fine turning | `CUSTOM2=192` |

Timing and fine turning are off by default. Fixed-rate simulation can reduce rendering
speed on slow machines. Fine turning preserves the held-turn rate after a short delay.
F10 quits, or use WHDLoad's `QuitKey` tooltype.

## Setup

Keep these original archives locally; they are not part of the repository:

```
tmp/LegendsOfValour_v1.0_0837.lha   preinstalled game
tmp/LegendsOfValour.lha             original installer (needed for packaging)
```

Extract the preinstalled game with Lhasa/LHA:

```sh
mkdir -p tmp/game
(cd tmp/game && lha xq ../LegendsOfValour_v1.0_0837.lha)
```

Building needs make, vasm's Motorola 68000 assembler, WHDLoad development headers, and
Amiga NDK headers. Python 3 supports the inspection and packaging tools. Local gameplay
uses FS-UAE, the shared launcher, Workbench 2.04, WHDLoad, and Kickstart images. Tracing
additionally needs the Barto-enabled FS-UAE build and m68k GDB described in
[profiling.md](docs/profiling.md).

| Setting | Default |
|---|---|
| `VASM` (make variable) | native assembler in `tmp/vasm-native-src/vasm/`, else `~/.local/vasmm68k_mot` |
| `WHDLOAD` (make variable) | `~/.local/share/amiga/WHDLoad` (development headers) |
| `NDK` (make variable) | `~/.local/opt/m68k-amiga-elf/sys-include` |
| Shared runtime files | `~/.local/share/amiga`, defaults and overrides in [amiga/env.sh](amiga/env.sh) |
| `FSUAE` | `fs-uae` on PATH |
| `FSUAE_COMMON` | `~/.local/share/amiga/fsuae_common.sh` |
| `GAME` | `tmp/game/LegendsOfValour` (use an absolute path when overriding) |

The game slave requires WHDLoad 17+, Kickstart 1.3 `kick34005.A500` and its `.RTB`.
It reserves 512 KiB chip memory and 656 KiB other memory, with additional memory needed
for WHDLoad, allocations and optional features. The emulator's host ROM is separate
from the Kickstart 1.3 image used by the slave; see the runtime path table in
[profiling.md §1](docs/profiling.md#1-host-setup).

## Build and play

From the repository root:

```sh
source amiga/env.sh
make -C whdload
SLAVE="$PWD/tmp/build/LegendsOfValour.Slave" WHD_ARGS=CUSTOM2=0 amiga/run.sh
```

This explicitly selects the new release with optional timing and fine turning off.
Use `WHD_ARGS=CUSTOM2=192` to try both. The launcher defaults to a 68000 with 1 MiB
chip and 8 MiB fast RAM; reference capture machines are specified separately in
[profiling.md §3](docs/profiling.md#3-the-machine).

An expanded 68020 trial can be launched with:

```sh
AMIGA_MODEL=A1200 CPU=68EC020 CHIP_KB=2048 FAST_KB=4096 \
KICKSTART="$KICKSTART_A1200" EXTRA_ARGS=--slow_memory=0 \
SLAVE="$PWD/tmp/build/LegendsOfValour.Slave" WHD_ARGS=CUSTOM2=192 amiga/run.sh
```

The launcher uses `amiga/.run` and copies the game into a fresh run directory each time.
Save games written there are lost on the next launch: copy any you want to keep before
restarting. Optional local preferences are described in
[amiga/performance.env.example](amiga/performance.env.example); explicit `SLAVE` and
`WHD_ARGS` take precedence. Do not launch over an existing interactive session.

## Development and validation

```sh
make -C whdload developer OUT='../tmp/build developer'
make -C whdload verify OUT='../tmp/build verify'
```

Developer builds retain individual W1–W6 switches. VERIFY adds input tapes, pixel twins,
and simulation checks; it must not ship. `OUT` is relative to `whdload/` unless absolute;
paths containing spaces are supported. All build variants are assembled afresh.

Use [profiling.md](docs/profiling.md) for capture commands and fixed-window A/B checks,
[performance-patches.md](docs/performance-patches.md) for rendering invariants,
[simulation-timing.md](docs/simulation-timing.md) for timing validation, and
[one-degree-turning.md](docs/one-degree-turning.md) for fine-turning checks. Captures run
one at a time with `JOY0=none` in `amiga/.cap`, separate from interactive sessions.

## Release archives

```sh
python3 tools/release.py
```

Builds `dist/LegendsOfValour-1.1b.lha` and `dist/LegendsOfValour_v1.1b_0837.lha`.
Only the slave and ReadMe are replaced; entry lists and every other compressed record
are preserved. Packaging verifies CRCs and replacement contents before publishing the
local outputs. See [releasing.md](docs/releasing.md).

Original game/ROM bytes and generated artifacts are local only, under ignored `tmp/`
and `dist/`. The preinstalled distribution contains game data; archives are not committed.

## Remaining acceptance and limitations

Automated checks pass on both reference CPUs. One-degree turning still needs normal
interactive acceptance; timing may receive further adjustments from play feedback.
The tape cannot wait for a conversation panel's input poll, so affected routes dismiss
it with repeated EXIT clicks. See [open-work.md](docs/open-work.md) for current items.
W7's further renderer redesign was dropped by user decision.
