# Open work

2.0b (20.11.2026) on John Selck's reconstructed V1.0 slave. Enhanced framerate (CUSTOM1)
gives the game fixed-rate game time, a tick every 2, 3 or 4 fields (CUSTOM2), with drawing
left out while behind; off, the game runs as the original
([internals](internals.md#game-time)). With fast memory everything the CPU alone uses runs
from it ([internals](internals.md#cpu-only-data-in-fast-memory)), and its main loop draws into a
buffer there, so nothing waits for the blitter clear
([internals](internals.md#drawing-in-fast-memory)): the demo went from 23.4 to 46.7 fps on
the a1200-030 ([internals](internals.md#measurements)). It boots to the game's attract
mode on the a500+ and the a1200, and F10 quits with `OK`.

## Game speed

Which rate the game was meant for is not known: 25, 16.7 or 12.5 Hz (CUSTOM2 0, 1, 2;
0 is the default only because it comes first in the list). The originals ran the demo
at 12.0 fps on the a500+ and 22 to 23 fps on the a1200 and the a1200-030. The A500 holds
12.5 Hz, 97% of 16.7 Hz and 91% of 25 Hz. Choose by play; reordering the `C2` list in
`_config` and `_speed`'s mapping in `_start` changes the default.

## Before a first release

- Play-test Enhanced framerate at each speed, including pause, a wave's end, game over
  and the highscore entry (only the demo, the attract screen, pause and a wave's end are
  tested so far).
- Play-test on every machine in `SETUPS`, including saving a highscore (the moved table
  loads; saving it is not tested). The scripted play reaches game over with 17526 points
  every time (`tools/coverage.py ... wander 2500 wander 2000` from the demo, then
  crashes with `thrust`, no shots); the game-over screen took SPACE only on a
  second press, and RETURN in the entry was not reached yet.
- The death sequence is paced by ticks now; its game-over text (the last life's death)
  is not seen yet. A second sound of the crash (on another channel than the explosion,
  sound 29) still has about 50 fields to go when the death sequence ends at 25 Hz, and the
  next life's sounds cut it after about 15. Making the next life wait for it would
  change the game, not its pace: decide by play.
- Without Enhanced framerate the game is the original, tied to the frame rate; with fast
  memory light scenes now run it at up to 50 fps, twice the pace it had before.
- The chip copy of the moved block stays filled with `ILLEGAL` for now (a code reference
  `src/reloc.i` missed then stops at once rather than misbehaving later): revisit before
  the release.

## Candidates

Each needs an A/B on the demo benchmark (same machine, same window) before any claim. The
analysis behind them, against the repository's direction for 68020+ with fast memory (CPU
only, everything not DMA in fast memory, every cache on), is in
[internals](internals.md#what-must-be-in-chip-memory) and its measurements:

- **Caches.** `DCACHE` changes no frame rate in the demo (47.6 on the a1200-030, -040,
  -060 and a3000-50 with either; the a3000 46.6 to 46.7) and leaves about 1% more time
  waiting on the a1200-030 ([internals](internals.md#drawing-in-fast-memory)); not worth
  the slave enabling it.
- **The copy.** It goes by rows now, skipping zero rows, the score draws without leaving the
  mode and the clear only clears nonzero rows: the a500+-020 31.7 to 35.7 fps, the
  a1200-fast 36.0 to 37.4, the a3000 46.6 to 47.6; the others were at the window's ceiling
  already. What is left on the 68020s is mostly the game itself; on a 68040/060 `move16`
  is untried, but those wait for the display.
- Enhanced framerate's speeds stop at 25 Hz; the a1200-030 could now draw a 50 Hz tick
  (a tick every field), but that is a faster game, not a smoother one. Smoother needs
  drawing between ticks (interpolation).
- The game speed still waits for whole fields; drawing between ticks (interpolation) or
  a tick shorter than the drawing would need the renderer faster still.
- Run on a 512 KB chip A500: find the render writes past `$80000` (a write watchpoint
  above `$80000`) and clip them, so `ws_BaseMemSize` can be `$80000`. The unused `_clamp`
  shows where the original author started.
- The benchmark's trace reduction (`tools/bench.py`, `tools/report.py`) still assumes the
  code at `$57000`; `pace.py`, `aprof.py`, `chipaccess.py` and `gametime.py` find it
  (`tools/codebase.py`). The game waits for the blitter only through the clear flag `$606ac`.
