# Zany Golf

Electronic Arts' Zany Golf (1988, by Will Harvey) under WHDLoad. The slave is Bored Seal's
v1.1 (23-Jul-2006; v1.0 05-Aug-2000), an OSEmu slave, with the world stepped on its own
clock at the game's intended 10 steps a second and frames drawn between the steps, at most
one a field, by a renderer that redraws only the cells that changed (the blitter copies the
scrolled view) and builds the draw list and draws the shapes in native code, and the instruction cache on. The original slave
is by Bored Seal (game.conf `AUTHOR`, `UPSTREAM`): neither JOTD's nor StingRay's repository
holds it, so `src/ZanyGolf.asm` is the source from the whdload.de install package
(`ZanyGolfHD/src/ZanyGolf.asm`). The ReadMe also thanks Jan Vieten for the disk image and
JHZ for the icon.
The repository's rules and shared docs are in the root `AGENTS.md` and `docs/index.md`;
this file and `docs/` here hold only what is specific to this game.

Read `docs/open-work.md` first.

| Doc | Read it for |
|---|---|
| `docs/open-work.md` | where the work stands and the ordered next items |
| `docs/development.md` | what differs from the shared workflow: inputs, the build, the harness and its traps |
| `docs/internals.md` | how the game loads, every slave patch, the program, display and time, measurements |

The slave source is `src/`. `tools/` is the harness and never ships: `boot.sh`, `route.py`
(routes into play and a putt), `zanygolf.py` (the gdb-stub server, with `frames`, `track` and
`frametrack`), `bench.py` (traced benchmark), `profile.py` and `thread.py` (a threaded-code
lister) ([development.md](docs/development.md), "Harness").
