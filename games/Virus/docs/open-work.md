# Open work

Set up from John Selck's V1.0 slave; no improvement work yet. The reconstruction rebuilds the
shipped slave byte for byte. It boots to the game's attract mode on the a500+ and the a1200,
and F10 quits with `OK`.

## Before a first release

- A dated `$VER` string and a version (`2.0b`), and the ReadMe's entry for it above the
  original text ([releasing](../../../docs/releasing.md)).
- Play-test on every machine in `SETUPS`, including saving a highscore.

## Candidates

Not measured yet; each needs the playbook's profiling before any claim.

- Run on a 512 KB chip A500: find the render writes past `$80000` (a write watchpoint
  above `$80000`) and clip them, so `ws_BaseMemSize` can be `$80000`. The unused `_clamp`
  shows where the original author started.
- Game speed: whether game time is tied to the frame rate. In the same 15 s warp wait the
  a1200's attract mode had finished wave 1 and the a500+'s had not (warp, so unmeasured);
  AmigaXDev's `playbooks/fixed-time-simulation.md`.
- The filled-polygon renderer's frame rate on a 68000 and on faster CPUs; fast memory for
  code and data that need not be in chip memory.
- Blitter waits and self-modifying code under caches on 68020+; a newer slave version
  (WHDLoad 17 header, `slv_config` for options).
