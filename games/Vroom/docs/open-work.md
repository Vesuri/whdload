# Open work

Set up from Mr.Larmer's and CFou's v1.4 slaves; both variants rebuild byte-identically.
Vroom boots to the title and its demo race on the a500 and the a1200-060 (WHDLoad's
default, caches off), the data disk to its title on the a1200.

## Next

1. **Caches.** With `DCACHE` on the a1200-040 (MMU, Zorro III) the screen stays black:
   WHDLoad stops with an access fault at $F984, writing past BaseMem. The 3D renderer
   rewrites its own code; with the instruction cache on the routines run stale code.
2. **Flickering roadside objects** in play.
3. **50 fps** on capable machines with a fixed simulation tick.

## Release

A first release needs a dated `$VER` in both slaves and a ReadMe entry above CFou's.
