# Indianapolis 500

Optional high frame rate support (`CUSTOM1`, off by default) for the SPS 0686 Indianapolis 500
on a 68020+ with the game in fast memory: no 15 fps limit, smooth motion between the game's
ticks, CPU drawing where it beats the blitter; the game logic is untouched. The original
slave is StingRay's v3.0 from his WHDLoad patches repository (game.conf `AUTHOR`,
`UPSTREAM`); this work was a branch of it and its pull request upstream is still open.
The repository's rules and shared docs are in the root `AGENTS.md` and `docs/index.md`;
this file and `docs/` here hold only what is specific to this game.

Read `docs/open-work.md` first.

| Doc | Read it for |
|---|---|
| `docs/open-work.md` | what is left to check, accept and decide for the release |
| `docs/slave.md` | the options, every patch, how motion and drawing work, verification results |
| `docs/profiling.md` | builds, runs, machine settings, the capture tools, release packaging, traps; read before quoting any number |
| `docs/game.md` | how the original game works: loading, memory, timing, renderer, cars |
| `docs/simulation-feasibility.md` | the analysis of a faster player simulation (not pursued) |

The slave source is `src/` (`Indianapolis500_WHD.s` and its modules; `PixelVerify`,
`DrivingTest` and `SoftTiming` are instruments only diagnostic builds assemble); `tools/` is the
development harness and never ships.
