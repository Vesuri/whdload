# Mercenary 3

A performance slave for Mercenary III: The Dion Crisis (Novagen), from install version 1.2:
the Enhanced framerate option (`CUSTOM5=1`) renders up to 50 fps PAL while the world and
the game logic keep their native rates. The original slave is by Harry, Graham and Wepl
(game.conf `AUTHOR`); it shipped with its source in the official installer, and
`src/original/` reconstructs the shipped bytes from it (`UPSTREAM` none).
The repository's rules and shared docs are in the root `AGENTS.md` and `docs/index.md`;
this file and `docs/` here hold only what is specific to this game.

Read `docs/open-work.md` first.

| Doc | Read it for |
|---|---|
| `docs/open-work.md` | current scope, findings and decisions |
| `docs/plan.md` | the step-by-step plan (step IDs, dependencies, done criteria) |
| `docs/development.md` | inputs, running, the route and profiling tools, the machine matrix, packaging |
| `docs/internals.md` | the slave, the boot, the game's memory layout, every patch, measurements |
| `README.md` | the release summary and how to install and play it |

The slave source is `src/` (`Mercenary3.slave.asm` with its included tables, and
`original/Mercenary3.slave.asm`, the reconstruction); `tools/` is the development harness
and never ships. Both variants in `game.conf` run as the installed `Mercenary3.Slave`;
`make original` requires the rebuilt original to equal the shipped slave.
`manifest/` pins the archives and every file they unpack to (`tools/check_inputs.py`).
