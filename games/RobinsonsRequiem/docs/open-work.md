# Open work

Both games are profiled (`docs/performance.md`: where the frame time goes walking in the
jungle, and the plan). The AGA plan is done up to its step 1 (`docs/internals.md`, "AGA
improvements"). Both developer builds boot straight into the game
(the AGA one with detail and window at HIGH), and `tools/rr.py ingame` drives any AGA build
there through the intro and menu (`docs/development.md`). The game is on the repository layout with CFou!'s v1.2
slave source unchanged except for two include lines (`docs/development.md`); both variants
build with vasm and boot to the title screen on their default machines.

The rebuilt slaves are not byte-identical to the shipped v1.2 slaves: they carry the current
WHDLoad 20.1 KickEmu instead of the 2013 one and are assembled by vasm instead of Barfly
(`docs/development.md`, "Byte identity"). `release/slaves.sha256` records the vasm builds.

Next, in order:

1. The AGA plan in `docs/performance.md`, "Plan", from step 2 (the caches), each step
   measured with `tools/rr_prof.py` before the next.
2. The ECS plan there, from its step 1 (the chunky-to-planar conversion).
3. Play-test both variants further (loading and saving) with the rebuilt slaves, against
   the shipped ones (`make run SLAVE=original`).
