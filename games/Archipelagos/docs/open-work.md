# Open work

Set up from StingRay's v1.2 slave; no improvement work yet. Both variants boot to the title
and into archipelago 1, SPS 627 on the a500 and SPS 628 (NTSC) on the a1200, and F10 quits
cleanly on both.

## Release

2.0b (18.11.2026): StingRay's v1.2 code, which the whdload.de install package lacked, with
`$VER` and the info text in the slave and the ReadMe entry above StingRay's. Still to do:
play-test both versions on every machine in `SETUPS`, including saving and loading a game.

## Candidates

Not measured yet; each needs the playbook's profiling before any claim.

- The 3D landscape drawing: how many frames a second it reaches on a 68000 and on faster
  CPUs, and whether game time is tied to the frame rate (AmigaXDev's
  `playbooks/fixed-time-simulation.md`).
- Blitter waits and self-modifying code under caches on 68020+ (the slave sets no cache
  options and has no blitter fixes).
