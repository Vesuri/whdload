# Battlehawks 1942

A performance study of the original 1989/1990 Lucasfilm Games flight game (PAL v1.0), run
under Galahad/Fairlight's WHDLoad install (slave v1.0, 12.05.2003, Retroplay pack
`Battlehawks1942_v1.0_0053.lha`). There is no game source: work from cycle-exact FS-UAE
traces and disassembly. Galahad's slave shipped without source; `src/original/` reconstructs
it byte for byte, so the slave is credited to Galahad/Fairlight (game.conf `AUTHOR`,
`UPSTREAM`). The slave that is built and patched is `src/Battlehawks1942.s` (WHDLoad 20
KickEmu, 512 KB chip + 516 KB fast memory, caches on; BH writes code, `bh:18360` and its span
loop, and the slave flushes the caches after each write, or on a 68020 or 68030 replaces
the written words' cache lines). Any change to the game ships as
patches in that slave; the Enhanced framerate (`CUSTOM2=1`, `src/timing.s`, ported from
Their Finest Hour with `tools/xmatch.py`) makes game time follow real time. Goal:
frame-rate-independent gameplay, 50 fps on faster Amigas. Released as Battlehawks 1942
Enhanced 2.0b (09.11.2026, `make release`); `make dist` packages Galahad's installer with the release slave (`release/`, the icons
from `tools/icons.py`); `tools/install_run.sh` and `install_check.py` run it under
Installer 43.3.
The repository's rules and shared docs are in the root `AGENTS.md` and `docs/index.md`;
this file and `docs/` here hold only what is specific to this game.

- Addresses in docs are `bh:` hunk-0 offsets of the game executable `BH` (on `Disk.1`),
  `bh-data:` data-hunk offsets, `kick:` ROM addresses (`$FC0000`-based), or `slave:` offsets
  (the reconstruction's `Lxxx` labels), never absolute addresses.
- Instruments (the input tape, experiments, anything that changes behaviour for measurement)
  go in the `VERIFY` build only. Game patches for players go behind an option.
- Only what DMA needs belongs in chip RAM; everything else in public memory (fast when there
  is any). BH already allocates that way; keep it so in any patch.
- Never edit a script while a capture is running it (bash reads scripts as it goes).

Read `docs/open-work.md` first.

| Doc | Read it for |
|---|---|
| `docs/open-work.md` | what is known, what Their Finest Hour's work gives this one, and the Enhanced framerate plan |
| `docs/profiling.md` | running the game, driving it, tracing it, or quoting any performance number |
| `docs/c2p.md` | touching the chunky-to-planar pass |

The slave source is `src/` (`Battlehawks1942.s`, `timing.s` the Enhanced framerate with
`combat.s` its timers and combat and `render.s` its rendering, the VERIFY-only `tape.s` and `c2p_full.s`, `original/`
the reconstruction); game.conf and game.sh define the builds (release, verify, c2pfull,
tscale, rectime, mouse, spancheck, original). `tools/` is the development harness and never ships: `bh.py`
is the gdb-stub server, `fixed_window.sh` the capture runner, `bh_report.py`, `frames.py`,
`c2p_stats.py` and the `compare_*.py` scripts read its captures; `record.sh` and
`speed.py` record and read flights (game time against real time); `timing_check.py`,
`combat_check.py` and `render_check.py` (Unicorn) and `pl_check.py` are part of `make check`; `xmatch.py` maps
Their Finest Hour's code, patch sites and globals to BH's.
