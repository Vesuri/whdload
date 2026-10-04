Test Drive II: The Duel — local fixed-time study build

Based on JOTD's public-domain v1.5 slave source. This is a local study build,
not an official installer release. Only duel v1 receives the new options;
v2's patch list and timing are unchanged.

History — 2026-10-04
* CUSTOM2 bit 0: three-field simulation (~16.67 Hz nominal PAL), independently
  of drawing. Continuous rates are scaled; race time follows video fields.
  Animation phases and random updates no longer depend on drawing frequency.
* Nonfatal crash/engine-damage recovery is 240 fields with a 20-second penalty.
  Opponents and race time continue; the player stops at idle pitch. The trainer
  remains supported. Fatal/last-life events use the original game-over path.
* CUSTOM2 bit 1: suppress unused blitter-finished interrupts. Original waits,
  blitter ownership and JOTD's beam/display fix remain intact. The fixed first-
  race window repeats 5.6 -> 6.5 fps; other scenes have not been given that gain.

Set CUSTOM2=3 for both options, CUSTOM2=1 for simulation only, or CUSTOM2=2
for rendering overhead only. Leave CUSTOM2 unset for original behavior.
CUSTOM1=1 enables the existing infinite-lives trainer.

Higher-rate integration changes handling: the measured demo was about 5.4%
further and 3.4% faster at field 999. PAL is validated; NTSC is not validated.
Both CPUs and deliberately slowed drawing have matching fixed-field state.
The normal build has no scripted input or forced events.

Use the slave with the existing licensed game and WHDLoad installation.
No game, Kickstart or WHDLoad program files are included. Source and detailed
evidence: whdload/TestDrive2HD.s, docs/open-work.md and docs/simulation-design.md
in the study repository. Build with make -C whdload.
