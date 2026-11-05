# Ferrari Formula One

A performance mode (`CUSTOM2=1`, default off) for the SPS 0481 PAL Ferrari Formula One:
elapsed-time scheduling with a converted 200 ms simulation on the 68000, the native 100 ms
on a 68020 without Fast memory and a 20 ms player simulation on a 68020+ with Fast memory,
faster rendering, Fast-memory allocation and CPU caches; `CUSTOM2=0` is the original game.
The original slave is StingRay's v1.01 (game.conf `AUTHOR`, `UPSTREAM`); his repository does
not hold it, so the source is his installer's. This work was a branch of the Vesuri fork of
his WHDLoad patches repository and was never offered upstream.
The repository's rules and shared docs are in the root `AGENTS.md` and `docs/index.md`;
this file and `docs/` here hold only what is specific to this game.

Read `docs/open-work.md` first.

| Doc | Read it for |
|---|---|
| `docs/open-work.md` | where the work stands, what a release still needs |
| `docs/slave.md` | the slave: build, options, schedulers, memory, qualification summary |
| `docs/RELEASE_QUALIFICATION.md` | the test matrix (`tools/ff1check.py`), qualified machines and launch options |
| `docs/CONTROLS_REGRESSION.md` | the RC1 launch bug and the driving-control acceptance |
| `docs/FASTRAM_PLAN.md` | the Fast RAM rendering work (FR0–FR8), its gates and results |
| `docs/RENDERING_PLAN.md` | the rendering optimisation plan and its results (H series) |
| `docs/game.md` | how the original game works |
| `docs/profiling.md` | builds, runs, captures and traps for measurements |
| `docs/PERFORMANCE.md`, `docs/PERFORMANCE_PLAN.md`, `docs/GAME_TIME.md`, `docs/STEP5*.md`, `docs/HI25_PLAN.md`, `docs/baseline-validation.md`, `docs/RELEASE_QUALIFICATION_HANDOFF.md` | the history of the analysis and the step-by-step plans, as written then |

The slave source is `src/`: `FerrariFormulaOne_WHD.s` (the host) and its modules, and the
payload sources (`Fine.s`, `Coarse.s`, `Render*.s`, `FastRender*.s`, `Production*.s`).
`tools/build.py` with `bindings.py`, `native.py`, `reset.py` and `layout.json` builds the
slave (game.sh `game_build`). The rest of `tools/` is the development harness and never
ships: `ff1check.py` runs the test matrix, `run.sh` is the captures' launcher,
`ff1layout.py` stages the pre-import layout for scripts that copy it, and `attic/` keeps the
retired scripts the older evidence cites (their paths are the pre-import ones).
