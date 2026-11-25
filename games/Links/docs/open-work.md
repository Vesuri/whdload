# Open work

Version 2.0b, from StingRay's V1.01 slave: the game runs with WHDLoad's `CACHE` and its
code runs from fast memory ([internals.md](internals.md#caches-and-fast-memory)).
Verified to the first hole, with renders equal to V1.01's without `CACHE` (but the animated
wind indicator), for v1.53 and v1.50 on the a1200-030 with Zorro III RAM
(`EXTRA_ARGS='--fast_memory=0 --zorro_iii_memory=32768'`, `WHD_ARGS='CACHE CUSTOM1=1'`),
the a1200-030 with 24-bit fast RAM, the a1200-fast and the a1200-040 (WHDLoad's MMU on, and
`NOMMU`), all with `CACHE`; the intro with `CACHE`; and the 68000 `custom` setup.
The intro's pictures were damaged at random by its music, and the game's samples popped
([internals.md](internals.md#slave-patches)): its sample data sits on +35, and the channels
were left holding a level when stopped. With 2.0b the a1200-030's panorama matched a clean
reference in every dump, and in audio captures the sounds are centred (the birds average -3
to -16 instead of +1640 to +1900) and scaled to about the full 8 bits, and the outputs rest at
0 between them and after the intro ([internals.md](internals.md#samples)).

On v1.53 the course view is drawn in 89 fields instead of 137 on the a1200-030 with
`CACHE` (the picture to the screen in 2 instead of 27), with code checked equal to the
game's in Unicorn ([internals.md](internals.md#slave-patches)).

## Release

`make dist` builds `LinksEnhanced-2.0b`: StingRay's package with the new slave and ReadMe.
The installed icon does not set `CACHE` (the Install script writes the tooltypes, and
`Links.inf` has none for `release.json` to add to); the player adds it.

## Next

- Play past the first hole with `CACHE` (putting, the next holes, the course disks).
- Capture the swing's swoosh too (the captures covered the first hole's ambient samples; the
  swoosh goes through the same player, hunk 44 `$9F4`).
- About 0.3 s after the intro is clicked away a single blip of 10 ms is left (755-901 in the
  captures before the scaling, 755-3246 before 2.0b's sample changes): the hand-over to
  `golf`, not yet traced, nor measured since the scaling.
- The intro's music still averages -120 to -220 (centred on 30); a per-sample centre would
  take the rest of that step at its start and stop.
- The course view's set-up is mostly hunk 23's LZW unpacking (26 of 34 fields on the aprof
  68030), half of it chip memory time: its input, output and dictionary are in chip
  memory. Where the game allocates them, and whether they can be fast memory, is not yet
  known. v1.50 plots each pixel to the screen in its span loops and was not changed.
- The 68000 `custom` route stops on the course's picture (`boot.sh`) or the player screen,
  with 2.0b's earlier builds as well: its waits need retuning before it reaches the hole.
