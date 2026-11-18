# Open work

Set up from StingRay's v1.2 slave; no improvement work yet. The build equals the shipped v1.2
slave, and both variants boot to the title and into archipelago 1: SPS 627 on the a500 and
SPS 628 (NTSC) on the a1200, where F10 also quits cleanly.

## Before a first release

- A dated `$VER` string and a version (`2.0b`), and the ReadMe's entry for it above
  StingRay's history ([releasing](../../../docs/releasing.md)).
- Play-test both versions on every machine in `SETUPS`, including saving and loading a game.

## Candidates

Not measured yet; each needs the playbook's profiling before any claim.

- The 3D landscape drawing: how many frames a second it reaches on a 68000 and on faster
  CPUs, and whether game time is tied to the frame rate (AmigaXDev's
  `playbooks/fixed-time-simulation.md`).
- Blitter waits and self-modifying code under caches on 68020+ (the slave sets no cache
  options and has no blitter fixes).
