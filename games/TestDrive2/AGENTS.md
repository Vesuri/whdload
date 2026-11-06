# Test Drive II

WHDLoad slave patches for the original 1989 Amiga release of Accolade's *Test Drive II: The
Duel*, run under JOTD's WHDLoad install (`duel` v1, 108 868 bytes): an optional "Enhanced
framerate" (`CUSTOM2=1`) with fixed-time simulation and sub-unit rendering, plus the intro
car fix and the overlay cache flush that apply with either setting. No game source: work
from cycle-exact FS-UAE traces and disassembly; every change to the game is a
`resload_PatchSeg` patch list in `src/`. The original slave is by JOTD (game.conf `AUTHOR`,
`UPSTREAM`): his `T/TestDrive2/usr` in whdload_slaves at 6046174e, the v1.5 source. Upstream
merged this work (43463d0e, then 840516bf and c4d0af53) and released it as 2.1.

The repository's rules and shared docs are in the root `AGENTS.md` and `docs/index.md`;
this file and `docs/` here hold only what is specific to this game.

Read `docs/open-work.md` first.

| Doc | Read it for |
|---|---|
| `docs/open-work.md` | **First.** The goal, working rules, open items and dropped decisions |
| `docs/development.md` | what the slave does, the files, inputs, builds, runs and the release |
| `docs/game.md` | reading or patching game code: addresses, tasks, time sources, state map, frame costs |
| `docs/simulation-design.md` | changing the fixed-time simulation or its VERIFY fixtures |
| `docs/subunit-rendering.md` | changing fractional road/car projection, sideways or hill smoothing |
| `docs/testing.md` | running, tracing or testing the game, or quoting any performance number |

Addresses in docs are `duel` hunk-0 offsets (`duel:OFFSET`, the slave's patch numbering).

The slave source is `src/`; `tools/` is the development harness and never ships
(`tools/td2.py` is the gdb-stub server, `tools/fixed_window.sh` the frame-rate instrument).
`release/` holds the installer's changed files; `make dist` repacks the original installer
archive with them.
