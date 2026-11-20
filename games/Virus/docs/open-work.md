# Open work

Set up from John Selck's V1.0 slave; no improvement work yet. The demo benchmark has a
baseline on the a1200-030 ([internals](internals.md#measurements)): 23.4 fps, with 31% of
the time spent waiting for the blitter clear of the back buffer. The reconstruction rebuilds the
shipped slave byte for byte. It boots to the game's attract mode on the a500+ and the a1200,
and F10 quits with `OK`.

## Before a first release

- A dated `$VER` string and a version (`2.0b`), and the ReadMe's entry for it above the
  original text ([releasing](../../../docs/releasing.md)).
- Play-test on every machine in `SETUPS`, including saving a highscore.

## Candidates

Each needs an A/B on the demo benchmark (same machine, same window) before any claim.

- The clear wait (31% on the a1200-030). The clear of the old front buffer starts only at
  the VBL after the swap and takes 11.9 ms, and nothing is drawn until it ends. With a
  third buffer the clear would overlap drawing into another buffer (32 KB more chip
  memory: fine on 1 MB+ chip, not on a 512 KB A500). Cheaper things to measure first:
  whether the renderer's polling (`tst.w $606ac` in chip, every few cycles) slows the
  blitter (11.9 ms is about 186 lines for 14720 words; the free slots would allow about 105),
  and whether doing more of the frame's CPU work before the wait shortens it.
- CPU work that is chip-bus bound on fast CPUs: every data access (the vertex arrays at
  `$1000`, the slope table at `$14b06`, the maps) and every span write is in chip memory.
  Measure what share of the fill, object and particle cycles is chip wait (aprof) before
  choosing.
- Game speed: game time follows the frame rate (the demo ran ahead on the a1200 in the
  first boots); AmigaXDev's `playbooks/fixed-time-simulation.md` before changing the rate.
- Run on a 512 KB chip A500: find the render writes past `$80000` (a write watchpoint
  above `$80000`) and clip them, so `ws_BaseMemSize` can be `$80000`. The unused `_clamp`
  shows where the original author started.
- Blitter waits and self-modifying code under caches on 68020+; a newer slave version
  (WHDLoad 17 header, `slv_config` for options).
