# Open work

Version 2.0b, from StingRay's V1.01 slave: the game runs with WHDLoad's `CACHE` and its
code runs from fast memory ([internals.md](internals.md#caches-and-fast-memory)).
Verified to the first hole, with renders equal to V1.01's without `CACHE` (but the animated
wind indicator), for v1.53 and v1.50 on the a1200-030 with Zorro III RAM
(`EXTRA_ARGS='--fast_memory=0 --zorro_iii_memory=32768'`, `WHD_ARGS='CACHE CUSTOM1=1'`),
the a1200-030 with 24-bit fast RAM, the a1200-fast and the a1200-040 (WHDLoad's MMU on, and
`NOMMU`), all with `CACHE`; the intro with `CACHE`; and the 68000 `custom` setup.
The intro's pictures were damaged at random by its music, and the game's samples popped from
fast memory ([internals.md](internals.md#slave-patches)); with 2.0b the a1200-030's
panorama matched a clean reference in every dump, and the game's sample loop runs on
cleared chip memory (checked with a breakpoint, not by ear).

## Release

`make dist` builds `LinksEnhanced-2.0b`: StingRay's package with the new slave and ReadMe.
The installed icon does not set `CACHE` (the Install script writes the tooltypes, and
`Links.inf` has none for `release.json` to add to); the player adds it.

## Next

- Play past the first hole with `CACHE` (putting, the next holes, the course disks).
- Listen to the samples on a real machine or with audio capture to confirm the pops are gone.
- On fast machines the intro can draw `COPYRIGHT ...` over the previous credit (hunk 0
  `$726` draws it straight onto the screen after the scroll loop, whose length is timer
  driven); not yet checked against a 68000.
