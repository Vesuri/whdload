# Prince of Persia development setup

Paths are relative to the game directory (`games/PrinceOfPersia`). The harness that lived in
the fork's ignored `tmp/dev/` is now `tools/` and `docs/`; its runner and environment
(`amiga/run.sh`, `amiga/env.sh`) and its build script are replaced by `common/`.

## Inputs

`make unpack ARCHIVES=<directory>` copies the five archives `inputs.sha256` pins into
`tmp/archives/` and unpacks each into its own drawer under `tmp/game/`:

| Archive | Drawer | What |
|---|---|---|
| `PrinceOfPersia.lha` | `PrinceOfPersiaInstall` | the WHDLoad installer package (v4.4); `make dist` repacks it |
| `PrinceOfPersia_v4.4_1823.lha` | `PrinceOfPersia` | the installed UK version (UK 1b), the default run |
| `PrinceOfPersia_v4.4_NTSC_1407.lha` | `PrinceOfPersiaNTSC` | the installed US version |
| `PrinceOfPersia_v4.4_De_0082.lha` | `PrinceOfPersiaDe` | the installed German version |
| `PrinceDePerse_v4.4_Fr_2290.lha` | `PrinceDePerseFr` | the installed French version |

The slave tells the versions apart by their disk and loads `prince_<version>.reloc` from the
drawer (`fix_version_addresses` in `src/PrinceOfPersiaVersions.s` adjusts the patch addresses).

## Build

`make slave` and `make verify` give `tmp/build/release/PrinceOfPersia.Slave` and
`tmp/build/verify/PrinceOfPersia.Slave`, each with its listing `PrinceOfPersia.lst`, from
`src/PrinceOfPersiaHD.s` (`game.conf`: vasm `-pic`, the shared WHDLoad includes plus its
`Src/` for `macros/ntypes.i`, `AMIGA_SHARE/ndk/Include_I`). The VERIFY build defines
`VERIFY` and adds `src/PrinceOfPersiaVerify.s`: the input tapes (`CUSTOM4=n`), the frame log,
the time pin and the A4 hooks. Extra defines for one VERIFY build go in `VASM_EXTRA`
(`make verify VASM_EXTRA=-DEXPLORE_LEVEL=4`; the fork's `VERIFY_DEFINES`).

`src/savegame.s` INCBINs `xen_8.bin`, the xen/8 font. It is a binary from the installer
archive, so it is not tracked: `game_build` (`game.sh`) copies it from
`tmp/game/PrinceOfPersiaInstall/source/` into `src/` (ignored), checked against its pinned
hash, so every build needs `make unpack` first. The release packager ships it in the source
drawer as the original did. `src/PrinceOfPersia.islave.s` is JOTD's RawDIC imager source;
the release ships the original imager binary, and the project does not build it.

The slave carries a fixed version and date, `5.0b (17.10.2026)`, so builds are reproducible.
`make check` proves the release build still gives `release/slaves.sha256` and compiles every
tool. The import's baseline (the fork's own Makefile, from the imported tree) gave the same
release and VERIFY bytes:

| Build | SHA-256 |
|---|---|
| release | `25bd788177488079ec67334b63c70e20df59eea765a2dbc69b899a04909eb58c` |
| verify | `fb929429b0eb995942c9af0fa827848651d43d829cdcce43c393db0a833b2c1c` |

These include the shape-expansion fallback fix made after 5.0b; the 5.0b normal slave that
`internals.md` (D4) records, `2a3b2fe9…`, is the one before it.

## Run

`make run` boots the release build on `a500-1.5m` (the slave needs 0.5 MB chip and ~0.8 MB
ExpMem; plain `a500` is too small); `make run SLAVE=original` boots the shipped v4.4 slave.
`POP_VERSION=us|de|fr` selects the other installs (`us` runs NTSC unless `NTSC=0`).
The enhancements are on by default; `WHD_ARGS=CUSTOM5=16` selects the original routines.
`make run BUILD=verify WHD_ARGS='CUSTOM4=1'` plays VERIFY tape 1.

Debug: `WARP=1 python3 tools/pop.py serve`, then `shot`, `wait`, `stop`, `cont`, `gdb`,
`until`, `profile` and `quit` from another shell (the shared server, `common/tools/game_server.py`).

## Capture tools

The capture tools (`tools/pop.py`'s `Session`) boot their own emulator: a `common/run.sh`
`INSTANCE` named after the output directory, which must be under `tmp/`; its `.run` links to
the instance's run directory. They run on `a500-1.5m`, warp, deterministic, port 0 empty
(`docs/profiling.md` says why port 1 keeps a joystick), and on the private native FS-UAE
`tmp/native-emulator/fs-uae` (sha256 `3627080a…`, 4D Sports Driving's contact-write build,
`source.patch` beside it), which has `monitor key`, `monitor fields`, a full profiler window
and the frequency fix. It is not tracked; copy it into `tmp/native-emulator/` or select
another build with `POP_FSUAE=PATH`. The release-build tools boot the existing
`make slave` build, the VERIFY tools the existing `make verify` build; `SLAVE=path` boots
another (its listing beside it gives the symbols).

| Tool | What |
|---|---|
| `route.py OUT STEP...` | a scripted keyboard route (`f:N`, `t:KEY[:N]`, `d:`/`u:`, `s:NAME`, `S:N:EVERY`) |
| `spikes_route.sh OUT` | the level-1 spikes route, profiled (`PLAIN=1`: untraced) |
| `explore.py OUT STEP COUNT` | a screenshot every STEP fields |
| `profile_run.py OUT STEP...` | a route with `P:N` traced steps, reduced by `amigaxdev.callprofile` |
| `report.py`, `tree.py`, `frames.py`, `prof.py`, `dis.sh` | reports on a `profile_run.py` capture |
| `tape_run.py OUT TAPE STEP...` | plays a VERIFY tape, screenshots at gameplay steps |
| `tape_from_route.py OUT STEP...` | turns a field-timed keypad route into tape entries |
| `timing_run.py`, `frame_log.py`, `check_frame_log.py` | A3: the VERIFY frame log, and its gate against a trace |
| `state_run.py OUT TAPE CUSTOM5 LAST` | A4: state and pixel hashes at every gameplay step |
| `hash_cmp.py A B` | compares two `state_run.py` runs |
| `dump_run.py`, `snap.py`, `mem_diff.py` | memory at chosen steps, and their differences |
| `trace_at.py`, `blit_touch.py`, `bus_budget.py`, `frame_profile.py` | B2, B4, B6: raw traces and their analyses |
| `sameshots.py`, `sheet.py` | screenshot comparison, contact sheets |
| `verify.py` | the VERIFY block (`PrinceOfPersiaVerify.s`) in a running session |

`PERFORMANCE_PLAN.md` gives each step's commands and gates; `internals.md` the results.

## What was not imported

The fork harness's ignored `tmp/dev/tmp/` (captures, traces, reports, the retained builds,
the native emulator, the D1 emulator build, ad-hoc scripts) and its `dist/` (a preinstalled
5.0b test package) hold game-derived or local data and stay out of git; the reports
`internals.md` and `PERFORMANCE_PLAN.md` cite are there. `setup.json` and `manifest/inputs.json`
(the archives and the source commit) are replaced by `game.conf` and `inputs.sha256`.
Commit hashes in the docs are those of the fork branch (Vesuri/jotd_whdload_slaves,
branch `princeofpersia`); the commit messages here are the same.
