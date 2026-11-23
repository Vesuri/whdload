# Open work

Set up from Harry's and StingRay's V1.01 slave. Without the version strings the build
equals the shipped slave but for the code hunk's padding word
([development.md](development.md#the-build)). It boots to the
title, landscape 0000's overview and into the landscape on the a500, the a1200 and the
a1200-060.

## Release

2.0b (23.11.2026): V1.01's code with `$VER` and the info text in the slave and the ReadMe
entry above StingRay's; `make dist` builds `SentinelEnhanced-2.0b-20261123.lha`. No
improvement yet: the ReadMe entry's one line ("no changes to the game yet") is replaced by
the fixes' lines when they land. Not published.

## Rendering on fast machines

The goal: correct drawing on fast machines with the MMU, the data cache and Zorro III fast
memory. On the a1200-060 (`make run SETUP=a1200-060`) landscape 0000's overview loses
faces and shows white triangles, and the landscape view misses most of its filled
polygons; the a500 and a1200 (68020) draw both correctly. Not yet looked into. Candidates:
the data cache on chip memory the blitter or CPU then reads (the slave sets only the
instruction cache), missing blitter waits other than `$30C`, self-modifying code, and
CPU-timed delays.
