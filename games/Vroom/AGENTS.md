# Vroom

Lankhor's Vroom (1991) and its data disk (1992) under WHDLoad: two direct slaves that load
the disk images (`Disk.1`, and `Disk.2` for the data disk) with `resload_DiskLoad`, remove
the disk protection, add blitter waits and save the highscores. The original slaves are by
Mr.Larmer (v1.0 and v1.3, 2000), updated to v1.4 by CFou (2006) (game.conf `AUTHOR`,
`UPSTREAM`); the whdload.de install package ships their source.
These slaves add the fixes for CPU caches and fast CPUs (`src/fixes.i`, `src/smc.i`).
The repository's rules and shared docs are in the root `AGENTS.md` and `docs/index.md`;
this file and `docs/` here hold only what is specific to this game.

Read `docs/open-work.md` first.

| Doc | Read it for |
|---|---|
| `docs/open-work.md` | where the work stands and the ordered next items |
| `docs/development.md` | what differs from the shared workflow: inputs, tools, captures, traps |
| `docs/internals.md` | the program, game time, every slave patch, measurements, limitations |

The slave source is `src/`; `tools/` is the development harness and never ships.
