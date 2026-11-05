# Red Baron

Red Baron 3.0b for sim v1 of Sierra/Dynamix's Red Baron: one Enhanced framerate option
(`CUSTOM2=1`, 68020 and Fast RAM) with CPU-specific cockpit, scene and geometry rendering and
game speed independent of the rendering framerate. The original slave is by JOTD, whose
repository it comes from (game.conf `AUTHOR`, `UPSTREAM`: jotd666/whdload_slaves
`R/RedBaron/usr` at cd97d6cc). JOTD merged this work upstream as 94ee5451 ("Red Baron 3.0b:
optional enhanced framerate", PR #37) but has not released it.

The repository's rules and shared docs are in the root `AGENTS.md` and `docs/index.md`; this
file and `docs/` here hold only what is specific to this game.

Read `docs/open-work.md` first, then `docs/profiling.md` and `docs/performance-plan.md`.

| Doc | Read it for |
|---|---|
| `docs/open-work.md` | where the work stands: the open items, release status, what is postponed |
| `docs/development.md` | inputs, builds, runs, the harness and its tools |
| `docs/profiling.md` | every measurement and final release check: the single results record |
| `docs/performance-plan.md`, `docs/completion-plan.md`, `docs/fast-cpu-plan.md` | the plans and their item IDs (W, C, E, FC) |
| `docs/game-time.md`, `docs/game-time-plan.md` | the game-time model and consistent game speed (W6) |
| `docs/rendering-analysis.md` | the 030/040/060 rendering investigation |
| `docs/verification.md`, `docs/w1-verification.md` … `docs/w6-verification.md` | VERIFY instruments, twins and per-step verification |

The slave source is `src/` (`RedBaronHD.s` and its modules; the `*-verify.s`, `*-cases.i`,
`tape.s`, `observe.s` and similar modules are VERIFY-only, while `time-terrain-verify.s` and
`time-flag-verify.s` are in every build); `tools/` is the development harness and never ships:
the capture, twin, census and report tools, their host models and unit tests, and
`tools/redbaron.py` (the gdb-stub server). `release/` holds the installer package's files;
`make dist` repacks the original installer archive with them.

Commit hashes in `docs/` are those of the fork branch this history was imported from
(Vesuri/jotd_whdload_slaves, branch `redbaron`); the commit messages here are the same.
