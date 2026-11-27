# Open work

The slave is Codetapper's and StingRay's v1.4 with an always-on check for an unknown main
program and, behind CUSTOM3 on a 68020 or better, the game running from a relocated copy in
ExpMem (internals.md, "The fast copy"). The copy is checked through the menus and a practice
race with the chip copy write-protected; it draws at the original rate.

1. Bring the Stunt Car Racer Unleashed 1.1 features into the fast copy as patches that run
   Unleashed's own routines: the unlocked frame rate (50 FPS PAL) at the original game speed
   (its timing variables, several physics steps per frame, the scaled constants and
   cooldowns), the fast render buffer, the infinite-boost toggle without self-modifying
   code. Variable addresses come from the original code, not Unleashed's equates.
2. TNT under CUSTOM3: check the copy with `SCR-TNT` (the TNT patch's pointers into ExpMem
   are left alone by design).
3. Stunt Track Racer (NTSC, frame delay 7): the same table applies to its program.
4. Drive more of the game on the verify build: league races, results, save and load.
5. A first release needs a dated `$VER`, a ReadMe entry and an icon tooltype for the option.
