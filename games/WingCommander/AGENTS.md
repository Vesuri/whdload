# Wing Commander

WHDLoad improvements for the OCS disk (SPS 1657) and CD32 versions, two variants of one
package. Current status: P13A1–P13A4, P13B1–P13B3, P13C1–P13C6, P13D1–P13D4 and P13E1–P13E3 are complete.
D1 verifies OCS timing owners and 10 Hz units with native CPU checks; its input
queue/edge ABI differs from CD32. D2 integrates the opt-in 10 Hz flight clock with retained catch-up debt and
world-owned side effects. D3 adds field input and bounded renderer prediction;
D4 adds the title/asteroid intro clock with native credit deadlines. E1 adds
opt-in exact arithmetic/collision shortcuts and closes its focused measurement
gate with documented heavy-scene limits. E2 passes the bounded compatibility and
functional model gate. E3 records the candidate support and later release hand-off
in docs/ocs-release.md. A500 coasting sustains
10 Hz; asteroid credits and sustained fire remain overloaded, with low display
throughput.
The OCS public candidate now gates all enhancements with CUSTOM5=1 and verified
68020+/true Fast memory; its generated icon enables the toggle. Off/ineligible
keeps original behaviour; only E1's bit-exact arithmetic/collision shortcuts,
the waypoint marker order, the TrainSim key fix and the mouse hooks run on every path. Legacy diagnostic candidates remain reproducible.
Normal OCS reconstruction and CD32 slaves remain byte-identical. C2 recommends
native blitter on the measured 68000 and no-Fast 68020 profiles; CPU/Fast longword
conversion wins the measured 14 MHz 68020/Fast profile. These are scoped emulator
results, not a universal threshold.
C4 provides a separate OCS candidate with creation-time source allocation,
native registry cleanup, safe fallback and checked display teardown. C5 queues
completed images for OCS blanking-time publication and drains ownership before
conversion, direct planar writes and View teardown. C6 adds opt-in changed-block
CPU conversion with separate destination histories and scratch-loan invalidation; it wins the measured 020/Fast intro but loses to
the A500 blitter. The default candidate remains unchanged. The shared
Chip workspace stays in its combined allocation to support native fallback.
Exec MEMF_FAST also labels slow expansion RAM; identify the physical bank.
The OCS guest recorder remains CPU-tested, not live-hooked; correctness runs use
the host observer. Automatic production selection stays native without a clock
certificate; explicit CPU selection requires verified Fast storage. The tested
launcher floor is 512 KiB Chip plus 4 MiB Fast; smaller tested configurations fail.
Required baseline for later work: Amiga 500 with Fast RAM. Share verified CD32
mechanisms with 68000-safe paths. Retain native blitter C2P wherever matched
CPU/memory measurements favour it; CPU type alone is not a crossover measurement.
CD32 E1/phase 12 remain paused. See `docs/ocs-plan.md` for the ordered work.
The CD32 intro 10 Hz timing and first-interval projectile fixes are complete;
phase 11b D1–D5 are complete on current models. A2 calibration remains separate.
OCS live evidence is limited to the documented emulator gate; no OCS hardware
performance or broader compatibility claim follows from it.
Psygore authored the original v1.0 slaves (`game.conf` `AUTHOR`); they shipped without
source (`UPSTREAM=none`), so `tools/reconstruct.py` and `tools/ocs_reconstruct.py`
reassemble them byte for byte from the pinned originals.

The repository's rules and shared docs are in the root `AGENTS.md` and `docs/index.md`;
this file and `docs/` here hold only what is specific to this game. Keep the two
variants separate: do not assume their code or timing matches.

Read `docs/open-work.md` first.

| Doc | Read it for |
|---|---|
| `docs/open-work.md` | current scope and deferred work |
| `docs/development.md` | builds and runs, inputs, every phase's tools and reproduction commands |
| `docs/internals.md` | verified knowledge and unknowns |
| `docs/ocs-plan.md` | the ordered OCS work |
| `docs/ocs-release.md` | the OCS candidate, its support and the release hand-off |
| `docs/timing-design.md`, `docs/framerate-audit.md` | the CD32 timing design and its audit |
| AmigaXDev `docs/playbooks/new-game-playbook.md` | WHDLoad workflow and validation |
| AmigaXDev `docs/reference/measurement-method.md` | measurement discipline |
| AmigaXDev `docs/reference/validation-harness.md` | correctness checks |

The slave source is `src/`: the modules the generators in `tools/` add to the
disassembled original slaves (no main source file; `game.sh` `game_build` runs the
generators). `tools/` is the development harness and never ships; `tools/manifest/`
holds its pinned tables. `tools/wc_run.py` boots captures through `common/run.sh`.
