# Red Baron development setup

The slave source is `src/` (`RedBaronHD.s` and its modules); it came from JOTD's repository
(game.conf `UPSTREAM`). Paths below are relative to `games/RedBaron`, and the tools expect it
as the working directory, with the shared environment loaded (`. ../../common/env.sh`) for
the tools that read `VASM`, `WHDLOAD`, `AMIGA_SHARE` or `KICKSTART_A1200`.

- Inputs, pinned in `inputs.sha256`: `RedBaron.lha` (JOTD's WHDLoad installer 2.1,
  `RedBaronHD/`) and `RedBaron_v2.1.lha` (the game installed with it, `RedBaron/`).
  `make unpack ARCHIVES=<directory>` verifies them into `tmp/archives/` and unpacks them into
  `tmp/game/`; the run uses `tmp/game/RedBaron`.
- Builds (`docs/building.md` at the root): `make slave`, `make verify` (`-DVERIFY=1`) and
  `make developer` (`-DDEVELOPER=1`: the individual `CUSTOM2` bits, no instruments) into
  `tmp/build/<build>/RedBaron.Slave`. The tools build through `tools/build.sh`, which keeps
  the harness's interface: the environment selects the build (`VERIFY=1`, `DEVELOPER=1`) and
  the VERIFY options (`VERIFY_D5_SCENARIO`, `VERIFY_WORLD_QUANTUM_TWIN`, `VERIFY_BANK_CYCLE`,
  `VERIFY_SPAN_TWIN_FAULT`, `VERIFY_FAST_FRAME_TWIN`, `VERIFY_FAST_FRAME_FAULT`,
  `VERIFY_ALLOC_LOG`, `VERIFY_CACHE_PROBE_FLAGS`, `VERIFY_CACHE_PROBE_RESULT`, `PANEL_CHECK`),
  and the slave is copied to `tmp/build/RedBaron.slave`, `RedBaron-verify.slave` or
  `RedBaron-developer.slave` with its listing beside it (`<slave>.lst`).
- `make check`: the release bytes match `release/slaves.sha256`, then every host unit test
  (`tools/test_*.py`; none needs the game, a build or a capture; log in
  `tmp/check-unittest.log`).
- `make dist`: `release/release.json` repacks `RedBaron.lha` with the slave, the new ReadMe,
  Install and icons (`CUSTOM2=1` in their tooltypes), and the source the release build was
  assembled from.

## Running

- `make run SLAVE=original`: JOTD's 2.1 slave. `make run` builds and boots the release slave;
  add `WHD_ARGS=CUSTOM2=1` for the enhancements, which the installed icons enable.
  `SLAVE=path` boots any slave. Boots `WHDLoad RedBaron.slave PRELOAD` from a disposable copy
  of `tmp/game/RedBaron/` in `tmp/run/default/.run/dh1`.
- Default machine (game.conf, `SETUP=custom`): the harness's A500 (68000) with 1 MB chip,
  2 MB fast and no slow RAM, PAL, mouse in port 0. `tools/completion_machines.py` defines the
  measurement matrix (`a500`, `020`, `030`, `030-nommu`, `040`, `060`) as run options for
  this machine; shared setup names also work (`SETUP=a1200-040`).
- `tools/redbaron.py serve` boots with the gdb stub (common `game_server`), and
  `python3 tools/redbaron.py <command>` sends `shot`, `wait`, `gdb`, `profile`, `until` or
  `quit` to it. The socket is `tmp/run/<instance>/.run/redbaron.sock`; tools that connect to
  it directly use the default instance's path, which must stay within the 104-byte socket
  limit (a shallow checkout).
- Drivers that boot their own runs (`reach_flight.py`, `completion_boot.py`, `w*_boot.py`,
  `*_case.py`, ...) build through `tools/build.sh`, set `SLAVE`, the machine and `WHD_ARGS`,
  and start `tools/redbaron.py serve`. Benchmark drivers use a prepared copy of the game in
  `tmp/game/completion-benchmark/RedBaron` (`GAME_DIR=completion-benchmark/RedBaron`), and
  the D5 fixtures copy one per case to `tmp/game/d5-<case>/RedBaron`.
- `tools/playtest.sh a500|060`: the D5 player candidate at real speed with sound.
- aprof captures need AmigaXDev's profiler emulators (`$AMIGA_SHARE/fs-uae-aprof`,
  `fs-uae-aprof040`), as `tools/aprof_flight.py` describes.

## The harness

The tools that were tracked on the fork branch (`R/RedBaron/tools`, imported with their
history) and the local harness the work kept in the fork's ignored `tmp/dev/tools` are
merged in `tools/`. Where both had a file of the same name, the tracked one is kept. Paths
were rewritten for this layout (`tmp/dev` is the game directory, `amiga/.run` is
`tmp/run/default/.run`, `GAME` naming a drawer is `GAME_DIR` under `tmp/game/`); the
emulator-driven tools were not all rerun after the move. The harness's preinstalled-archive
packager and its commit helper were replaced by `make dist` and the repository's rules. The
`tools/barto.py` copy is the trace reader the tracked tools were written against; the harness
tools use AmigaXDev's `amigaxdev.barto`.
