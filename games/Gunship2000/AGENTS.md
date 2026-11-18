# Gunship 2000

MicroProse's Gunship 2000 (1991-1994) under WHDLoad, in its three Amiga releases: the floppy
ECS version (kick13), the floppy AGA version and the CD32 version (both kick31). `src/` is
JOTD's v3.1 (28.03.06) source made to assemble with vasm; the AGA flight is profiled, with
a plan toward 50 fps on the a1200-030; the AGA slave keeps the flight's stack and model data in
fast RAM and turns the instruction cache on, fills the polygons (68030+) and the one-colour rectangles with
the CPU (the same pixels, checked frame by frame), `CUSTOM2=1` lifts the flight's frame cap
(the simulation kept at its rate, checked by the coupling test), and its VERIFY build pins
the mission.
The original slave is by JOTD (game.conf `AUTHOR`, `UPSTREAM`): his `G/Gunship2000/usr` in
whdload_slaves at 6046174e, the same source as in the whdload.de install package. Its
ECS slave starts from Wepl's Wild West World slave and KickStarter 34.005, its
protection removal is adapted from a crack, and its icons are Exoticons (ReadMe).

The repository's rules and shared docs are in the root `AGENTS.md` and `docs/index.md`;
this file and `docs/` here hold only what is specific to this game.

Read `docs/open-work.md` first.

| Doc | Read it for |
|---|---|
| `docs/open-work.md` | where the work stands and the ordered next items |
| `docs/development.md` | inputs, the build against the shipped slaves, running each variant, the in-flight profile, traps |
| `docs/internals.md` | how each version loads, memory, every slave patch; the AGA flight's frame loop, timing, renderer and memory |

The slave source is `src/`: one `Gunship2000<Variant>HD.s` per variant, `fakepad.s` (the
CD32 pad emulation, included by the CD32 slave), `slave_version` and the include bridge
`include/lvo/lowlevel.i`. `tools/` is the harness: `gunship2000.py` (the session),
`profile_flight.py` (the front-end route and the in-flight profile), `aprof_report.py`,
`coupling.py` (the frame-rate coupling test), `screens.py` (the drawn frames),
`gs2.py` (the flight program in memory) and `route.py`.
