# Robinson's Requiem

Silmarils' Robinson's Requiem (1994) under WHDLoad, in its two versions: the ECS/OCS game on
Kickstart 1.3 and the AGA game on Kickstart 3.1, one slave each. Both slaves are made
faster (`docs/performance.md`, "Plan": the ECS plan for the A500 done; the AGA plan done: the
world on the game's own grid, the camera and moving objects between their runs, the drawing
up to the cap, frames between world passes, the sky and objects' images in fast memory, the
landscape loop in the 68030's instruction cache and Kalms' 040/060 conversion on those CPUs,
its checks in play left; the ECS plan for fast CPUs written, not started, the 68000 to keep
working). The original slaves are by CFou! (game.conf `AUTHOR`, `UPSTREAM`): his v1.2 install
package from whdload.de, which ships their source.
The repository's rules and shared docs are in the root `AGENTS.md` and `docs/index.md`;
this file and `docs/` here hold only what is specific to this game.

Read `docs/open-work.md` first.

| Doc | Read it for |
|---|---|
| `docs/open-work.md` | where the work stands and the ordered next items |
| `docs/development.md` | inputs, the two variants, builds against the current KickEmu, booting past the language screen |
| `docs/internals.md` | how the game loads, Kickstart use, every slave patch with its code-hunk and file offsets |
| `docs/performance.md` | where the frame time goes in both games (`tools/rr_prof.py`, `tools/rr_report.py`), the pain points and the plan |

The slave source is `src/` (`RobinsonSRequiemEcs.asm` with the chunky-to-planar
conversion and the sky copy it includes, `c2p000.s` and `sky000.s`; `RobinSonSRequiemAga.asm` with its conversion, sky
copy and landscape loop, `c2p030.s`, `c2p040.s`, `sky030.s` and `land030.s`; the `lvo/intuition.i` bridge in `src/include/`, and CFou!'s unassembled bitplane-fix fragment
`_fixBPL1&2-InFast-Silmarils.s`); `tools/` is the development harness and never ships.
