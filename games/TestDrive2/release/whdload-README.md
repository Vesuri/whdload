# WHDLoad source baseline

Public-domain KickEmu sources and API headers from the official WHDLoad developer
archive (https://www.whdload.de). The build takes them from the WHDLoad tree it is
built against (`$WHDLOAD`); the release's source/ ships verbatim copies of
`kick13.s`, `kickfs.s`, `segtracker.s`, `kick.readme`, `include/whdload.i` and
`include/whdmacros.i`. The small `include/lvo/` aliases adapt the official
source's include names to the host NDK.

The slave follows `Src/slave-examples/kick13.asm`, but declares `slv_Version = 17`
(without `slv_MemConfig`) so WHDLoad 17.2 and later run it: it uses no version-20
feature. KickEmu supplies `WHDLF_EmulPriv`, sizes the expansion memory and handles
cache setup and flushes. CACHE is retained for DMA-safe noncached chip memory and cached fast
memory; CACHECHIPDATA is not appropriate for the game's blitter buffers.

WHDLoad executables and the developer archive are not part of this repository.
