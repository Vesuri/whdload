# Formula One Grand Prix

Real-time simulation independent of frame rate, smooth presentation up to 50 fps and
better performance (especially on 68020+ with fast RAM) for the supplied four-disk
Formula One Grand Prix. The original slave is by Codetapper (game.conf `AUTHOR`,
`UPSTREAM`): his v1.0 shipped without source, so `src/F1GP.s` is a rebuilt loader. The
work follows the steps in `docs/plan.md`; take them when the user asks.
The repository's rules and shared docs are in the root `AGENTS.md` and `docs/index.md`;
this file and `docs/` here hold only what is specific to this game.

Read `docs/open-work.md` first. The relevant AmigaXDev workflow is
`docs/playbooks/new-game-playbook.md`.

| Doc | Read it for |
|---|---|
| `docs/open-work.md` | the scope, where each step stands (G, the release, in progress) and next work |
| `docs/plan.md` | the plan: real-time speed, up to 50 fps, performance (steps A to H) |
| `docs/development.md` | inputs, the build, the gdb server and its routes, every capture recipe, F1GP-Ed, packaging |
| `docs/internals.md` | the loader, executable layout, game time, every slave patch, the evidence |
| `README.md` | the summary |

The slave source is `src/`; `tools/` is the development harness and never ships.
`game.sh` builds the slave (`game_build`: tables generated from the pinned game into
`tmp/slave/`, then vasm), packages the release (`game_dist`) and runs the unit tests
(`game_check`). `manifest/` pins the derived game files, the toolchain, the runtime and
F4's edited files, which the build and the tools verify. `make ed` boots F1GP-Ed;
`make snapshot BUILD=... OUT=tmp/...` keeps a build for a capture.
