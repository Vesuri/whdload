# Robinson's Requiem

Silmarils' Robinson's Requiem (1994) under WHDLoad, in its two versions: the ECS/OCS game on
Kickstart 1.3 and the AGA game on Kickstart 3.1, one slave each. Both slaves are made
faster (`docs/performance.md`, "Plan": the ECS plan for the A500 done, the AGA plan's world on the
game's own grid, its camera and moving objects between their runs and its drawing up to the cap done; the AGA
plan to 50 fps on a fast CPU under way, frames between world passes and the sky and objects' images in fast memory done, the rest of the chip time examined, the CPU's work next; the ECS one
written, not started). The original slaves are by CFou! (game.conf `AUTHOR`, `UPSTREAM`): his v1.2 install
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
conversion and the sky copy it includes, `c2p000.s` and `sky000.s`; `RobinSonSRequiemAga.asm` with its conversion and sky
copy, `c2p030.s` and `sky030.s`; the `lvo/intuition.i` bridge in `src/include/`, and CFou!'s unassembled bitplane-fix fragment
`_fixBPL1&2-InFast-Silmarils.s`); `tools/` is the development harness and never ships.
