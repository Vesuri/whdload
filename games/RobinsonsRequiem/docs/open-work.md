# Open work

No improvement work has been done yet. The AGA developer build boots straight into the
game with detail and window at HIGH, and `tools/rr.py ingame` drives any build there through
the intro and menu (`docs/development.md`). The game is on the repository layout with CFou!'s v1.2
slave source unchanged except for two include lines (`docs/development.md`); both variants
build with vasm and boot to the title screen on their default machines.

The rebuilt slaves are not byte-identical to the shipped v1.2 slaves: they carry the current
WHDLoad 20.1 KickEmu instead of the 2013 one and are assembled by vasm instead of Barfly
(`docs/development.md`, "Byte identity"). `release/slaves.sha256` records the vasm builds.

Next, in order:

1. Measure why the AGA game runs slowly on `a1200-030` at HIGH/HIGH, from the developer
   build's direct start (`reference/measurement-method.md`): where the frame time goes.
2. Play-test both variants further (loading and saving) with the rebuilt slaves, against
   the shipped ones (`make run SLAVE=original`).
