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

On the a1200-030 with `CACHE`, from the ready screen to the first hole's view takes 275
fields instead of V1.01's 655: the files load about 7 times faster (the unpacker's buffers
in fast memory and a faster unpacker, both versions), and v1.53's course view takes 55
fields instead of 167 (no cache flushes in its span loops, the picture to the screen 16
pixels a word). The slave's code was checked equal to the game's in Unicorn
(`tools/drawcheck.py`, `tools/lzwcheck.py`; [internals.md](internals.md#slave-patches)).

## Release

`make dist` builds `LinksEnhanced-2.0b`: StingRay's package with the new slave, ReadMe and
`Install`: the Install script sets `CACHE` in whichever icon is chosen (beside its `Slave`
and `PreLoad`; `Links.inf`, the default, has no tooltypes for `release.json` to add to).

## Next

- Play past the first hole with `CACHE` (putting, the next holes, the course disks).
- Capture the swing's swoosh too (the captures covered the first hole's ambient samples; the
  swoosh goes through the same player, hunk 44 `$9F4`).
- About 0.3 s after the intro is clicked away a single blip of 10 ms is left (755-901 in the
  captures before the scaling, 755-3246 before 2.0b's sample changes): the hand-over to
  `golf`, not yet traced, nor measured since the scaling.
- The intro's music still averages -120 to -220 (centred on 30); a per-sample centre would
  take the rest of that step at its start and stop.
- `DRAWING COURSE` (27 fields on the a1200-030) is spread over the 3D code; the largest parts
  are a matrix product (hunk 5 `$280`-`$2AE`, 11%) and an integer square root (hunk 25
  `$4DC`, about 8%: Newton steps from 32767, a `divu` each), which a root with the same
  results could cut to a few steps. v1.50 plots each pixel to the screen in its span
  loops and was not changed.
- The game needs 512 KB chip and 1.25 MB ExpMem in one block: 512 KB chip with 2 MB fast
  boots, 512 KB or 1 MB chip with 1.5 MB fast, and the a500-1.5m, do not. A smaller ExpMem
  would need the game's peak use measured first.
- The 68000 `custom` route stops on the course's picture (`boot.sh`) or the player screen,
  with 2.0b's earlier builds as well: its waits need retuning before it reaches the hole.
