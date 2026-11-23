# Open work

Set up from Mr.Larmer's and CFou's v1.4 slaves (the import builds byte-identically to them).
The slaves now run with the caches on: the self-modifying code is made cache-safe on 68020+,
and the blitter queue no longer overruns on fast CPUs (`docs/internals.md`, "Fixes" and
"Self-modifying code"). Vroom's demo race renders correctly, with no WHDLoad dump, on the
a500, the a1200 with `CACHE`, the a1200-040 with `DCACHE`, and the a1200-060 with every
cache option on. The data disk reaches its title ("Insert VROOM disk then click") on the
a1200 and the a1200-060.

## Next

1. **Play-test with the mouse.** Only the demo race has run. Still to drive: the menus
   (left button), a real race, the data disk's tracks past its click, and the second race
   start that reloads part of the program to $439C (`SMC_Decrunched` covers it; never
   observed). Then a long `SNOOPAGA CHKBLTWAIT` run with `DCACHE`.
2. **Flickering roadside objects** in play.
3. **50 fps** on capable machines with a fixed simulation tick.

## Release

2.0b (23.11.2026): `$VER` and info text in both slaves, the ReadMe entry above CFou's;
`make dist` builds `VroomEnhanced-2.0b-20261123.lha` (`lha t` passes). The 2.0b slave
runs the demo race on the a1200-040 with `DCACHE`. Not published.
