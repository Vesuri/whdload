# Open work

The slave is Codetapper's and StingRay's v1.4 with an always-on check for an unknown main
program and, behind CUSTOM3 on a 68020 or better, the game running from a relocated copy in
ExpMem with Stunt Car Racer Unleashed 1.1's enhanced framerate (internals.md): 50 frames a
second at the original game speed, for the disk and the TNT version. The copy is checked
through the menus and a practice race with the chip copy read- and write-protected.

1. Drive more of the game on the verify build: league races, results, save and load.
2. A cracked disk (Quartex): the slave runs a plain intro and main program. A synthetic
   image (the original's intro and program stored decrypted, as they lie in memory) races
   with and without the copy; the real crack is not pinned, so its intro is untested.
3. A first release needs a dated `$VER`, a ReadMe entry and an icon tooltype for the option.
