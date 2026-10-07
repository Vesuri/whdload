Test Drive II: The Duel — local fixed-time study build

Based on JOTD's public-domain v1.5 slave source. This is a local study build,
not an official installer release. Only duel v1 receives the new options;
v2's patch list and timing are unchanged.

History — 2026-10-07 (1.6b, unreleased beta of 1.6: all changes since 1.5)
* The enhancements below are one option, "Enhanced framerate" (CUSTOM2).
  WHDLoad options have no default value: add the tooltype CUSTOM2=1 to the
  game icon to enable it by default. CUSTOM2=0 runs the original game.
* Sideways motion (steering, lane position and mountains) and hill crests are
  smooth as well when Enhanced framerate is enabled.
* Built from the official WHDLoad 20.0 API headers and KickEmu sources, but
  declares slave version 17 and runs with WHDLoad 17.2 or later (PL_IFCx);
  it uses no version 20 feature. The installer source package includes them.
* Sub-unit road and car position in both views (duel v1).
  Uses frame-latched 16.16 positions and fractional curve/hill integration;
  sprite size selection is unchanged.
* Fixed the intro cars jumping 16 pixels left for one frame (duel v1, always
  on). The copper changed DDFSTOP after that line's stop had passed, so the
  car's first line fetched an extra word.

History — 2026-10-04
* Fixed-time simulation, independently of drawing: every
  6 fields on a 68000 (the original rate), every 2 fields on a 68020+. Continuous rates are scaled; race time follows video fields.
  Animation phases and random updates no longer depend on drawing frequency.
* Nonfatal crash/engine-damage recovery is 240 fields with a 20-second penalty.
  Opponents and race time continue; the player stops at idle pitch. The trainer
  remains supported. Fatal/last-life events use the original game-over path.
* Blitter bus priority and no unused blitter-finished
  interrupts. Original waits, blitter ownership and JOTD's beam/display fix
  remain intact.

* First-race window: A500 7.1 fps (original 6.1), A1200 16.7 fps;
  68030/25 MHz reaches the 25 fps chip-bus cap until the car is at speed.

CUSTOM1=1 enables the existing infinite-lives trainer.

Finer integration changes handling slightly: over 1,500 demo fields the two
periods differ by about 1% in distance; race clocks agree. CPUs with the same
period have identical fixed-field state. PAL is validated; NTSC is not.
The normal build has no scripted input or forced events.

Use the slave with the existing licensed game and WHDLoad installation.
No game, Kickstart or WHDLoad program files are included. Source and detailed
evidence: whdload/TestDrive2HD.s, docs/open-work.md and docs/simulation-design.md
in the study repository. Build with make -C whdload.
