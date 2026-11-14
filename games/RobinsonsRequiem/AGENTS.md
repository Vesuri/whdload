# Robinson's Requiem

Silmarils' Robinson's Requiem (1994) under WHDLoad, in its two versions: the ECS/OCS game on
Kickstart 1.3 and the AGA game on Kickstart 3.1, one slave each. No improvement work has been
done yet. The original slaves are by CFou! (game.conf `AUTHOR`, `UPSTREAM`): his v1.2 install
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

The slave source is `src/` (`RobinsonSRequiemEcs.asm`, `RobinSonSRequiemAga.asm`, the
`lvo/intuition.i` bridge in `src/include/`, and CFou!'s unassembled bitplane-fix fragment
`_fixBPL1&2-InFast-Silmarils.s`); `tools/` is the development harness and never ships.
