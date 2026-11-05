# Mercenary 3 — Enhanced framerate

Version **2.0b (04.11.2026)**.

Performance WHDLoad slave for **Mercenary III: The Dion Crisis** (Novagen), based on
install version 1.2 by Harry, Graham and Wepl, whose source came with the official installer.
**Enhanced framerate** is enabled by default in the installed icon (`CUSTOM5=1`): rendering can run up to
50 fps PAL while world simulation and game logic keep their native rates. Actual
frame rate depends on the machine and scene.

The WHDLoad startup screen has one control: **Enhanced framerate** checkbox.
Off keeps the original game's behaviour, with the old slave's display bugs fixed. On selects the supported optimisations for the
CPU, chipset and available memory, including smoother walking, vehicles and flight.
Smooth frames interpolate completed movement, adding about 80 ms of visual delay
on fast machines instead of predicting past stops and collisions.

## Requirements and installation

- The version 1.2 WHDLoad installation of the game and WHDLoad 17 or later.
- A 68000 or later, 512 KB chip RAM, and additional memory for WHDLoad and preloading.
  The tested A500 setup has 1.5 MB slow RAM in addition to its 512 KB chip RAM.
- An optional 288 KB workspace. If unavailable, code and stack stay in chip RAM and
  smooth intermediate frames are disabled; native-rate logic remains enabled.
- A 68020 or later with real fast RAM is needed for code/table/scratch relocation, object
  interpolation and drawing into fast RAM. AGA fetch optimisation is AGA-only.

Build with the shared Amiga environment described in [development](docs/development.md),
after `make unpack ARCHIVES=<directory holding the two archives>`:

```sh
make slave verify original check
```

To build the release archive, run `make dist`. It writes the repository's `dist/Mercenary3-2.0b.lha`:
the original WHDLoad installer archive with the slave and the `ReadMe` replaced and
`CUSTOM5=1` added to the two game icons (`Mercenary3.inf`, `Mercenary3.romicon`).
The ReadMe is built from the WHDLoad Install Template and `release/readme-body.txt`.
Open its Install icon on the Amiga to install from the original disk. The original
installer then adds `PRELOAD` to the chosen game icon, so Enhanced framerate starts checked. See [release packaging](docs/development.md#release-packaging).

To update an existing installation manually, back up the installed slave, then copy `tmp/build/release/Mercenary3.Slave` into a writable
copy of the game drawer. Keep its `Disk.1` and other game files. No game data or built
slaves are distributed in this repository.

Use `CACHE PRELOAD` in the game icon's tooltypes or launch from the Amiga Shell:

```text
WHDLoad Mercenary3.Slave CACHE PRELOAD CUSTOM5=1
```

`CUSTOM5=1` checks the box; `CUSTOM5=0` or omission
unchecks it. The release ignores
`CUSTOM1`, including older individual-feature settings. `NOCACHE` remains available
for cache troubleshooting; WHDLoad also supports `BRANCHCACHE` on 68060.
Backspace quits WHDLoad. Keep a writable game drawer for saved situations.

For the repository's emulator launcher (`docs/running.md` at the repository root):

```sh
make run WHD_ARGS=CUSTOM5=1 WHD_DEFAULTS='CACHE PRELOAD SPLASHDELAY=-1'
```

It builds the release slave and supplies `CACHE PRELOAD`; `SPLASHDELAY=-1` shows the
WHDLoad options and waits for Start. Use `WHD_ARGS=CUSTOM5=0` to start with the enhancement
off, and `SLAVE=original` to run the installed original. Its game drawer is a scratch copy,
so saves made there are not copied back to the original installation.

## Validation and limitations

Emulator checks cover 68000, 68020, 68030, 68040 and 68060, including the 030 MMU
configuration. The reference fast machine is the cycle-exact 68030/50. The 040/060
emulator timing is not a hardware-speed prediction.

No real hardware was available for this release check. Real-hardware cache behaviour
with relocated/self-modifying code and 040/060 performance remain unverified.
See [release validation](docs/internals.md#x1-release), the
[current 68040 frame budget](docs/internals.md#68040-frame-budget-after-p5), and
[current decisions](docs/open-work.md).

Developers can use `make verify` with `CUSTOM5=0 CUSTOM1=<feature mask>` for individual
feature comparisons. The VERIFY build also contains the measurement instruments;
use the regular slave to play. [Development](docs/development.md) describes the tools.

## Version 2.0b (04.11.2026) — Vesuri

- New **Enhanced framerate** option, enabled in the installed icon (`CUSTOM5=1`): faster
  rendering, and smoother walking, vehicles, flight, doors and shots, without speeding up
  the game world. With it, `CACHE` also enables the data cache on 68030 and later.
- Fixed the display routine, which waited for a vertical blank every frame and left part
  of each frame's colour update undone.
- Fixed intermittently missing ground with caches on 68040/68060.
- WHDLoad 17 is required.
