# Open work

Set up from Harry's and StingRay's V1.01 slave. The build equals the shipped slave but for
the code hunk's padding word ([development.md](development.md#the-build)). It boots to the
title, landscape 0000's overview and into the landscape on the a500, the a1200 and the
a1200-060.

## Release

No improvement yet. A first release needs a dated `$VER` and info text in the slave, and a
ReadMe entry above StingRay's.

## Rendering on fast machines

The goal: correct drawing on fast machines with the MMU, the data cache and Zorro III fast
memory. On the a1200-060 (`make run SETUP=a1200-060`) landscape 0000's overview loses
faces and shows white triangles, and the landscape view misses most of its filled
polygons; the a500 and a1200 (68020) draw both correctly. Not yet looked into. Candidates:
the data cache on chip memory the blitter or CPU then reads (the slave sets only the
instruction cache), missing blitter waits other than `$30C`, self-modifying code, and
CPU-timed delays.
