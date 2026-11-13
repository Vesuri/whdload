# Test Drive

Test Drive 2.0b for Accolade's Test Drive (the 1.3 installs): optional Enhanced framerate
(`CUSTOM2=1`, set in the installer's Normal icon) with fixed-time PAL simulation, fractional
road and traffic rendering, unused blitter interrupts suppressed, shorter blitter waits and
triple buffering, plus fixes that apply
with either setting (the overlay cache flush for accelerated Amigas, the opening-music
samples, close traffic and the rev counters). The original slave is by JOTD (game.conf `AUTHOR`, `UPSTREAM`): his
`T/TestDrive/usr` in whdload_slaves at 48557a5f. Upstream merged this work (3e2d99b5) but has
not released it.

The repository's rules and shared docs are in the root `AGENTS.md` and `docs/index.md`;
this file and `docs/` here hold only what is specific to this game.

Read `docs/open-work.md` first.

| Doc | Read it for |
|---|---|
| `docs/open-work.md` | where the work stands, upstream's status and the open items |
| `docs/development.md` | inputs, builds, runs, every phase's tools and checks, what was not imported |
| `docs/testing.md` | the reference machines, harness acceptance commands and evidence |
| `docs/internals.md` | the program: hunks and overlays, every slave patch, the state map |
| `docs/ENHANCEMENT_PLAN.md` | the plan, phases 1-12, and each phase's outcome |
| `docs/phase3.md` to `docs/phase11.md` | each phase's evidence: gameplay, profiling, timing, fixes, VERIFY fixtures, simulation, blitter, rendering, release regression |
| `docs/release-2.0b.md` | the 2.0b installer and ReadMe, installer coverage, packaging |
| `docs/road-shift.md`, `docs/corner-jump.md`, `docs/steer-reversal.md`, `docs/handling-collision.md`, `docs/rpm-needle.md`, `docs/audio-repeat.md`, `docs/dead-code.md` | the later 2.0b corrections, each with its reproduction and checks |
| `docs/draw-rate.md` | Enhanced framerate's blitter waits and the drawer's third screen buffer |
| `docs/wheel-dot.md` | the open post-crash steering-dot report |

The slave source is `src/` (`TestDriveHD.s`, `simulation.s`, `render.s`, `buffers.s`, their patch lists
and the VERIFY-only `simulation-verify.s`); `tools/` is the development harness and never
ships (`tools/td.py` is the gdb-stub server); `manifest/` pins the harness's inputs and
evidence. `release/` holds the installer package's files; `make dist` repacks the original
installer archive with them.

Commit hashes in `docs/` and `manifest/` are those of the fork branch this history was
imported from (Vesuri/jotd_whdload_slaves, branch `testdrive`); the commit messages here
are the same.
