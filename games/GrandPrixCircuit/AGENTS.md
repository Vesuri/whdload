# Grand Prix Circuit

Grand Prix Circuit 2.0b for the v1.0 game: an Enhanced framerate option (`CUSTOM2=1`, set
in the installed icon) with a higher simulation rate on 68020 and later and sub-unit road,
car, sign and horizon drawing, plus always-on fixes for the display handoff, the horizon,
Monza's grid and car visibility, music on fast CPUs and queued menu keys. The original
slave is by JOTD (game.conf `AUTHOR`, `UPSTREAM`): his `G/GrandPrixCircuit` in
whdload_slaves at 48557a5f.

The repository's rules and shared docs are in the root `AGENTS.md` and `docs/index.md`;
this file and `docs/` here hold only what is specific to this game.

Read `docs/open-work.md` first.

| Doc | Read it for |
|---|---|
| `docs/open-work.md` | where the work stands: what the release still lacks |
| `docs/PERFORMANCE_PLAN.md` | the plan (phases 0–8, the beta follow-ups, menu input), each step's evidence and limits |
| `docs/GAME_TIME.md` | the game-time model: clocks, rates, the gates that depend on drawing |
| `docs/internals.md` | the executable, the slave's patches, the measurement fixtures and baselines |
| `docs/development.md` | inputs, builds, runs and every capture and check tool, phase by phase |

The slave source is `src/` (`GrandPrixCircuitHD.s` and its modules; `verification*.s`,
`render-verify.s` and `simulation-verify.s` are VERIFY-only); `tools/` is the development
harness and never ships, with `tools/gpc.py` its gdb-stub server. `release/` holds the
installer package's files; `make dist` repacks the original installer archive with them.

Commit hashes in `docs/` are those of the fork branch this history was imported from
(Vesuri/jotd_whdload_slaves, branch `grandprixcircuit`); the commit messages here are the
same.
