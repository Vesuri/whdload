# Open work

No improvement work has been done yet. The game is on the repository layout with CFou!'s v1.2
slave source unchanged except for two include lines (`docs/development.md`); both variants
build with vasm and boot to the title screen on their default machines.

The rebuilt slaves are not byte-identical to the shipped v1.2 slaves: they carry the current
WHDLoad 20.1 KickEmu instead of the 2013 one and are assembled by vasm instead of Barfly
(`docs/development.md`, "Byte identity"). `release/slaves.sha256` records the vasm builds.

Next, in order:

1. Play-test both variants further than the title (the intro, a game start, loading and
   saving) with the rebuilt slaves, against the shipped ones (`make run SLAVE=original`).
2. Decide what to improve; nothing has been measured yet.
