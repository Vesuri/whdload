# Mercenary 3 — Enhanced framerate

Version **2.0 (23.10.2026)**.

Performance WHDLoad slave for **Mercenary III: The Dion Crisis** (Novagen), based on
install version 1.2. **Enhanced framerate** is enabled by default in the installed icon: rendering can run up to
50 fps PAL while world simulation and game logic keep their native rates. Actual
frame rate depends on the machine and scene.

The WHDLoad startup screen has one control: **Enhanced framerate** checkbox.
Off restores shipped game behaviour. On selects the supported optimisations for the
CPU, chipset and available memory, including smoother walking, vehicles and flight.

## Requirements and installation

- The version 1.2 WHDLoad installation of the game and WHDLoad 17 or later.
- A 68000 or later, 512 KB chip RAM, and additional memory for WHDLoad and preloading.
  The tested A500 setup has 1.5 MB slow RAM in addition to its 512 KB chip RAM.
- An optional 200 KB workspace. If unavailable, code and stack stay in chip RAM and
  smooth intermediate frames are disabled; native-rate logic remains enabled.
- A 68020 or later with real fast RAM is needed for code/table relocation, object
  interpolation and drawing into fast RAM. AGA fetch optimisation is AGA-only.

Build with the shared Amiga environment described in [development](docs/development.md):

```sh
. amiga/env.sh
make check original slave verify
```

To build the complete template-based WHDLoad installer drawer, run `make release`.
It writes `tmp/release-2.0/Mercenary3 Install/`, including the Amiga `ReadMe` and
`Install` script, the release slave, imager, icons and original documentation.
Open its Install icon on the Amiga to install from the original disk. The game icon
gets `CACHE PRELOAD`; the installer retains source-drive and icon selection.
Existing output is preserved; use `make release RELEASE=tmp/another-release` for a
new build. See [release packaging](docs/development.md#release-packaging).

To update an existing installation manually, back up the installed slave, then copy `tmp/build/Mercenary3.Slave` into a writable
copy of the game drawer. Keep its `Disk.1` and other game files. No game data or built
slaves are distributed in this repository.

Use `CACHE PRELOAD` in the game icon's tooltypes or launch from the Amiga Shell:

```text
WHDLoad Mercenary3.Slave CACHE PRELOAD CUSTOM5=1
```

`CUSTOM5=1` checks the box (set by the installer); `CUSTOM5=0` or omission
unchecks it. The release ignores
`CUSTOM1`, including older individual-feature settings. `NOCACHE` remains available
for cache troubleshooting; WHDLoad also supports `BRANCHCACHE` on 68060.
Backspace quits WHDLoad. Keep a writable game drawer for saved situations.

For this workspace's emulator launcher:

```sh
SLAVE=tmp/build/Mercenary3.Slave WHD_ARGS=CUSTOM5=1 WHD_SPLASH=1 amiga/run.sh
```

It supplies `CACHE PRELOAD`. Use `WHD_ARGS=CUSTOM5=0` to start with the enhancement off.
Without `SLAVE`, the launcher still runs the installed original. Its game drawer is a
scratch copy, so saves made there are not copied back to the original installation.

## Validation and limitations

Emulator checks cover 68000, 68020, 68030, 68040 and 68060, including the 030 MMU
configuration. The reference fast machine is the cycle-exact 68030/50. The 040/060
emulator timing is not a hardware-speed prediction.

No real hardware was available for this release check. Real-hardware cache behaviour
with relocated/self-modifying code and 040/060 performance remain unverified.
See [measured results](docs/internals.md#x1-release) and [current decisions](docs/open-work.md).

Developers can use `make verify` with `CUSTOM5=0 CUSTOM1=<feature mask>` for individual
feature comparisons. The VERIFY build also contains the measurement instruments;
use the regular slave to play. [Development](docs/development.md) describes the tools.

## Version 2.0 (23.10.2026) — Vesuri

- Faster rendering and smoother walking, vehicles and flight without speeding up
  the game world.
- Default-on **Enhanced framerate** option; Off restores original behaviour.
- Updated installer with CACHE and PRELOAD enabled in the game icon.
