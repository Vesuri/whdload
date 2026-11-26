# AlienBreed3D

Alien Breed 3D (1995, Team 17, AGA) under WHDLoad: Psygore's direct slave 1.3
(08.01.2020), which loads the floppy, CD32 or Aminet 8-channel executable from `data/`,
relocates it into fast memory, gives it a minimal exec and dos of its own and patches it per
version. The original slave is by Psygore (game.conf `AUTHOR`, `UPSTREAM`); the install
package's source is encrypted, so `src/AlienBreed3D.s` is a reconstruction of both shipped
slaves ([development.md](docs/development.md)).
The repository's rules and shared docs are in the root `AGENTS.md` and `docs/index.md`;
this file and `docs/` here hold only what is specific to this game.

Read `docs/open-work.md` first.

| Doc | Read it for |
|---|---|
| `docs/open-work.md` | where the work stands and the ordered next items |
| `docs/development.md` | what differs from the shared workflow: inputs, the build, driving it |
| `docs/internals.md` | how it loads, memory, every slave patch, the display, limitations |
| `docs/resolution-plan.md` | Enhanced resolution: the design, the steps, the open decisions |
| `docs/performance.md` | the original's measured frame rates and where a frame's time goes |

The slave source is `src/`; `tools/` is the development harness and never ships
(`tools/exe.py` unpacks the game executable for analysis, `tools/ab3d.py` drives the game on
the shared server, `tools/srcmatch.py` finds the published source's routines,
`tools/baseline.sh` and `tools/frametime.py` measure the frame rate and where a frame's time
goes).
