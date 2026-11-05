# Hard Drivin'

Hard Drivin' 4.0b for the SPS 0126 edition: an Enhanced framerate simulation (elapsed-time
physics, traffic and replays, CPU-specific rendering), the arcade machine's car model as an
option (CUSTOM1=2), and arcade race timing (CUSTOM5). The original slave is by Halibut
Software / John Girvin, reworked by JOTD, whose repository it comes from (game.conf
`AUTHOR`, `UPSTREAM`: jotd666/whdload_slaves `H/HardDrivin/usr` at 7003fc6f). The
repository's rules and shared docs are in the root `AGENTS.md` and `docs/index.md`; this
file and `docs/` here hold only what is specific to this game.

Read `docs/open-work.md` first: it is a log, newest first, so its first sections are where
the work stands.

| Doc | Read it for |
|---|---|
| `docs/open-work.md` | where the work stands (arcade handling, H3c) and the history of every step |
| `docs/development.md` | inputs, builds and VERIFY fixtures, runs, every capture and check tool, the arcade harness |
| `docs/internals.md` | the program, the slave's patches, the attract and gameplay baselines |
| `docs/ARCADE_HANDLING_PLAN.md`, `docs/ARCADE_ROMS.md`, `docs/ARCADE_TIMING.md` | the arcade car model, the arcade program (MAME), arcade race timing |
| `docs/GAME_TIME.md`, `docs/motion-next.md`, `docs/PHYSICS_ACCURACY.md`, `docs/AUDIO_TIMING.md` | the game-time model and its conversion |
| `docs/PERFORMANCE.md`, `docs/PERFORMANCE_PLAN.md`, `docs/STEP4_COST_PLAN.md`, `docs/STEP5_RENDERING.md`, `docs/STEP6_RELEASE.md` | measurements, the performance plan and its steps |

The slave source is `src/` (`HardDrivinHD.s` and its modules; the `*Verify.s` modules are
VERIFY-only); `tools/` is the development harness and never ships: the capture, check and
report tools, `tools/harddrivin.py` (the gdb-stub server) and `tools/arcade/` (the arcade
model, MAME plans and ROM analysis, which read the ROM set from `tmp/archives/`).
`release/` holds the installer package's files; `make dist` repacks the original
installer archive with them.

Commit hashes in `docs/` are those of the fork branch this history was imported from
(Vesuri/jotd_whdload_slaves, branch `harddrivin`), or of the harness's local repository,
which was not imported; the commit messages here are the same.
