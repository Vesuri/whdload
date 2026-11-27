# Vroom Multiplayer

Lankhor's Vroom Multiplayer (1993) under WHDLoad: a direct slave that loads the disk image
(`Disk.1`) with `resload_DiskLoad`, removes the disk protection, moves the self-modifying
scaler stores and the decrunchers into the slave and saves the highscores. Two game versions
are supported (the slave's "v1" and "v2", the NTSC one). The original slave is by Mr.Larmer
(v1.0-1.3), updated to v1.4-1.6 (03.06.2006) by CFou (game.conf `AUTHOR`, `UPSTREAM`); the
whdload.de install package ships its source.
This slave adds Vroom's fixes for CPU caches and fast CPUs (`src/fixes.i`, `src/smc.i`).
The game is Vroom's engine rebuilt: the same code with its data and variables moved, so the
work on `games/Vroom` is the reference for every fix here.
The repository's rules and shared docs are in the root `AGENTS.md` and `docs/index.md`;
this file and `docs/` here hold only what is specific to this game.

Read `docs/open-work.md` first.

| Doc | Read it for |
|---|---|
| `docs/open-work.md` | where the work stands and the ordered next items |
| `docs/development.md` | what differs from the shared workflow: inputs, tools, captures, traps |
| `docs/internals.md` | the program, game time, every slave patch, measurements, limitations |

The slave source is `src/`; `tools/` is the development harness and never ships.
