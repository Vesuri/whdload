Test Drive II: The Duel — local fixed-time study build

Based on JOTD's public-domain v1.5 slave source. This is a local study build,
not an official installer release. Only duel v1 receives the new options;
v2's patch list and timing are unchanged.

History — 2026-10-05
* CUSTOM2 bit 2: sub-unit road and car position in both views (duel v1).
  Uses the frame-latched 16.16 positions; sprite size selection is unchanged.

History — 2026-10-04
* CUSTOM2 bit 0: fixed-time simulation, independently of drawing: every
  6 fields on a 68000 (the original rate), every 2 fields on a 68020+. Continuous rates are scaled; race time follows video fields.
  Animation phases and random updates no longer depend on drawing frequency.
* Nonfatal crash/engine-damage recovery is 240 fields with a 20-second penalty.
  Opponents and race time continue; the player stops at idle pitch. The trainer
  remains supported. Fatal/last-life events use the original game-over path.
* CUSTOM2 bit 1: blitter bus priority and no unused blitter-finished
  interrupts. Original waits, blitter ownership and JOTD's beam/display fix
  remain intact.

* First-race window with CUSTOM2=3: A500 7.1 fps (original 6.1), A1200
  16.7 fps; 68030/25 MHz and faster reach the 25 fps chip-bus cap.

Set CUSTOM2=7 for all three options, CUSTOM2=3 for simulation and bus priority, CUSTOM2=1 for simulation only, or CUSTOM2=2
for rendering overhead only. CUSTOM2=4 enables fractional rendering alone. Leave CUSTOM2 unset for original behavior.
CUSTOM1=1 enables the existing infinite-lives trainer.

Finer integration changes handling slightly: over 1,500 demo fields the two
periods differ by about 1% in distance; race clocks agree. CPUs with the same
period have identical fixed-field state. PAL is validated; NTSC is not.
The normal build has no scripted input or forced events.

Use the slave with the existing licensed game and WHDLoad installation.
No game, Kickstart or WHDLoad program files are included. Source and detailed
evidence: whdload/TestDrive2HD.s, docs/open-work.md and docs/simulation-design.md
in the study repository. Build with make -C whdload.
