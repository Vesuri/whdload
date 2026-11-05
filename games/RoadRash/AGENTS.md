# Road Rash

Road Rash 3.0b for the version 2.0 (SPS 1313) install: Enhanced framerate (`CUSTOM2=1`, set
in the installed icon) that renders as fast as the machine allows, vsynced, while the
simulation keeps fixed 20 ms PAL steps, with the game's code, stacks and CPU data moved to
Fast RAM, reduced blitter and CPU work, and fixes that apply in both modes (rider visibility, hill projection,
steering and pause, loading on uncached 68030s, ECS/AGA border). The original slave is by
JOTD, whose repository it comes from (game.conf `AUTHOR`, `UPSTREAM`: jotd666/whdload_slaves
`R/RoadRash/usr` at ce5a2a25). JOTD merged this work upstream (e72e067b, then changed it in
8c35810f; `docs/open-work.md`) but has not released it. The repository's rules and shared
docs are in the root `AGENTS.md` and `docs/index.md`; this file and `docs/` here hold only
what is specific to this game.

Read `docs/open-work.md` first.

| Doc | Read it for |
|---|---|
| `docs/open-work.md` | where the work stands, upstream's changes after the merge, the open items |
| `docs/development.md` | inputs, builds, runs, the harness and its VERIFY builds, traps |
| `docs/performance-plan.md` | the plan (A–H), each item's status, evidence and limitations |
| `docs/simulation-timing.md` | the fixed-step simulation: audit, design and validation |
| `docs/memory-performance.md`, `docs/memory-assets.json` | Fast RAM relocation (D) and the asset inventory |
| `docs/blitter-performance.md`, `docs/cpu-performance.md` | blitter (E) and CPU (F) work |
| `docs/visual-fixes.md`, `docs/visibility-investigation.md`, `docs/height-investigation.md` | the fixes in both modes and their investigations |
| `docs/framerate-comparison.md`, `docs/release.md` | measurements and the 3.0b release validation |
| `docs/a-baseline.md`, `docs/b-correctness.md` | the A baseline and B correctness work |

The slave source is `src/` (`RoadRashHD.s` and its modules); `tools/` is the development
harness and never ships, with its fixtures in `tools/fixtures/` and the FS-UAE patches its
emulator build needs in `tools/patches/`. `release/` holds the installer package's files;
`make dist` repacks the original installer archive with them.

Commit hashes in `docs/` are those of the fork branch this history was imported from
(Vesuri/jotd_whdload_slaves, branch `roadrash`); the commit messages here are the same. The
last commit of that history, "Road Rash 3.0b: optional enhanced framerate", is the tree
submitted upstream (branch `roadrash-merge`, 383477cc).
