# Open work

Release 2.0b is Codetapper's and StingRay's v1.4, less the turbo mode, with an always-on
check for an unknown main program and, behind CUSTOM3 on a 68020 or better, the game
running from a relocated copy in ExpMem with Stunt Car Racer Unleashed 1.1's enhanced
framerate (internals.md): 50 frames a second at the original game speed, for the disk and
the TNT version. The installer sets CUSTOM3=1 in the icon (`release/Install`). The copy is
checked through the menus and a practice race with the chip copy read- and write-protected.

1. Drive more of the game on the verify build: league races, results, save and load.
2. A cracked disk (Quartex): the slave runs a plain intro and main program. A synthetic
   image (the original's intro and program stored decrypted, as they lie in memory) races
   with and without the copy; the real crack is not pinned, so its intro is untested.
3. The TNT version with CACHE stops taking keys at the main menu: seen on the 68030 and
   68040 with CUSTOM3 and on the 68040 with v1.4, so it predates 2.0b. The disk version runs with CACHE, and the enhanced
   framerate does not need it, so the icon leaves it off.
