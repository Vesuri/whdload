# Prince of Persia

Prince of Persia 5.0b for Broderbund's Prince of Persia (UK, US, German and French
versions): faster drawing, background restoration, room construction and game logic for
the A500, enabled by default (`CUSTOM5=16` selects the original routines), plus the
shape-expansion fallback fix that followed. The original slave is by JOTD and Harry, from
JOTD's repository (game.conf `AUTHOR`, `UPSTREAM`): his `P/PrinceOfPersia/usr` in
whdload_slaves at eb73c315. Upstream merged and released this work (5.1, then 5.2 with
the optimisations opt-in, on whdload.de since 24.10.2026), so no release is planned here.

The repository's rules and shared docs are in the root `AGENTS.md` and `docs/index.md`;
this file and `docs/` here hold only what is specific to this game.

Read `docs/open-work.md` first.

| Doc | Read it for |
|---|---|
| `docs/open-work.md` | where the work stands, upstream's status and the open items |
| `docs/development.md` | inputs, the build and its font, runs, the capture tools, what was not imported |
| `docs/PERFORMANCE_PLAN.md` | the A500 plan (A measurement, B understanding, C optimisation, D release) with each step's gate and outcome |
| `docs/internals.md` | the program: screen buffers, blitter users, tile lookup, room change, bus budget, every optimisation, the version ports, the D1-D4 evidence |
| `docs/profiling.md` | the A500 profiling setup, driving the game, the first baseline |

The slave source is `src/` (`PrinceOfPersiaHD.s` with `PrinceOfPersiaFast.s`, the version
fixups `PrinceOfPersiaVersions.i`/`.s`, the VERIFY-only `PrinceOfPersiaVerify.s`,
`ReadJoypad.s` and Wepl's `savegame.s` with its xen/8 font from the installer archive; the
imager source `PrinceOfPersia.islave.s` is not built); `tools/` is the development harness
and never ships (`tools/pop.py` is the gdb-stub server and the capture session). `release/` holds the installer package's files;
`make dist` repacks the original installer archive with the slave and ReadMe.

Commit hashes in `docs/` are those of the fork branch this history was imported from
(Vesuri/jotd_whdload_slaves, branch `princeofpersia`); the commit messages here are the same.
