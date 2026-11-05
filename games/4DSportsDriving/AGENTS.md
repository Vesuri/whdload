# 4D Sports Driving

4D Sports Driving 2.0b for the SPS 1461 edition: faster rendering (CUSTOM2, with a CPU
renderer on 68020+ with Fast RAM), correct game speed and race timing on every machine
(Normal 10 Hz, A2500 20 Hz, experimental A4000 50 Hz simulation on PAL 68040/68060),
saved simulation preferences and A4000 replays. The original slave is by JOTD, whose
repository it comes from (game.conf `AUTHOR`, `UPSTREAM`: jotd666/whdload_slaves
`4/4DSportsDriving/usr` at cd97d6cc). The repository's rules and shared docs are in the root
`AGENTS.md` and `docs/index.md`; this file and `docs/` here hold only what is specific to
this game.

Read `docs/open-work.md` first.

| Doc | Read it for |
|---|---|
| `docs/open-work.md` | where the work stands, builds and runs, validation evidence, the accepted limits |
| `docs/smooth-play-plan.md` | the authoritative plan P1-P7: measurements, each step's design, evidence and acceptance |

The slave source is `src/` (`4DSportsDrivingHD.s` and its modules; most `*_verify.s`
modules and the `*_cases.i` tables are VERIFY-only, and `tmp/build/release/*.deps` lists
what the release is assembled from); `tools/` is the development harness and
never ships: `tools/driving.py` (the gdb-stub server), `tools/build.sh` (fixture builds),
the benchmark cells (`tools/bench_cell.py`, `tools/bench_matrix.sh`), and the capture, model
and check tools the plan names. `release/` holds the installer package's files; `make dist`
repacks JOTD's installer archive with them.

Commit hashes in `docs/` are those of the fork branch this history was imported from
(Vesuri/jotd_whdload_slaves, branch `4dsportsdriving`), or of the harness's local docs
repository, which was not imported; the commit messages here are the same.
