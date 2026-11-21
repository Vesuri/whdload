# Open work

2.0b (20.11.2026) on John Selck's reconstructed V1.0 slave. Enhanced framerate (CUSTOM1)
gives the game fixed-rate game time, a tick every 3, 2 or 4 fields (CUSTOM2), with drawing
left out while behind; off, the game runs as the original
([internals](internals.md#game-time)). With fast memory everything the CPU alone uses runs
from it ([internals](internals.md#cpu-only-data-in-fast-memory)), and its main loop draws into a
buffer there, so nothing waits for the blitter clear
([internals](internals.md#drawing-in-fast-memory)): the demo went from 23.4 to 46.7 fps on
the a1200-030 ([internals](internals.md#measurements)). With fast memory, Enhanced framerate also draws
frames between ticks ([below](#frames-between-ticks)). It boots to the game's attract
mode on the a500+ and the a1200, and F10 quits with `OK`.

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
- With Enhanced framerate a pass that leaves the drawing out also leaves out the
  renderer's RNG draws (the attractor's lightning) and smoke
  ([internals](internals.md#game-time)): the game state then differs from the original's
  at the same tick, though it plays alike. Accept, or make those draws when not drawing.
  (The ship's terrain test, which the renderer also runs, such a pass now runs itself.)
- Play-test a crash into a slope (a wing, not the ship's centre) on the a500+ at 25 Hz,
  where passes leave the drawing out: the check build only made contacts by lowering the
  ship's entry.
- Without Enhanced framerate the game is the original, tied to the frame rate; with fast
  memory light scenes now run it at up to 50 fps, twice the pace it had before.
- The chip copy of the moved block stays filled with `ILLEGAL` for now (a code reference
  `src/reloc.i` missed then stops at once rather than misbehaving later): revisit before
  the release.

## Frames between ticks

Always with Enhanced framerate when there is fast memory: on the fields between two ticks'
frames, frames interpolated between the two ticks, with the game state byte-identical; tick
N's own frame then shows P−1 fields later (20 ms at 25 Hz). The a1200-030 and the a3000
draw 50 frames a second at every speed, the 14 MHz 68020s 36 to 39 at 25 Hz instead of 25;
the death sequence too ([internals](internals.md#frames-between-ticks)). Still open:

1. **Not met yet** in tools/pairs.py's runs: the attractor's lightning and 12 of the 18
   object handlers. Their entries pair the same way; a run that meets them checks it.
2. **Play-test.**
   - Matrices are blended word by word: an object that turns fast looks smaller midway?
   - Unpaired entries (new particles, the screen's edge) appear a field late or leave a
     field early.
   - On the 14 MHz 68020s frames show for one field or two in a mix: smoother than 25, or
     worse? If worse, draw frames between only where they fit every tick, decided over a
     window.
   - 16.7 and 12.5 Hz, with two and three frames between ticks.
   - A pause, a wave's end, game over.

Input is still read once a tick, and tick N's frame comes P−1 fields later than without it:
the controls answer that much later.

## Candidates

Each needs an A/B on the demo benchmark (same machine, same window) before any claim. The
analysis behind them, against the repository's direction for 68020+ with fast memory (CPU
only, everything not DMA in fast memory, every cache on), is in
[internals](internals.md#what-must-be-in-chip-memory) and its measurements:

- **Caches.** `DCACHE` changes no frame rate in the demo (the a1200-030, -040, -060 and
  a3000-50 at the old window's ceiling with either; the a3000 46.6 to 46.7) and leaves
  about 1% more time waiting on the a1200-030 ([internals](internals.md#drawing-in-fast-memory)); not worth
  the slave enabling it.
- **The copy.** It goes by rows now, skipping zero rows, the score draws without leaving the
  mode and the clear only clears nonzero rows: the a500+-020 31.7 to 35.7 fps, the
  a1200-fast 36.0 to 37.4, the a3000 46.6 to 47.6, the old window's ceiling. In the window
  now (after the fade-in, ending with the demo) the a3000, a3000-50, a1200-030, -040 and
  -060 draw 50.0, a frame every field, and the a500+-020 35.8, the a1200-fast 37.8. What is
  left on the 68020s is mostly the game itself.
- **50 frames a second.** A 50 Hz tick at today's pace is on the order of 80 patch sites
  in integer code and still another game ([internals](internals.md#a-50-hz-tick)); frames
  between ticks give the frames instead ([above](#frames-between-ticks)).
- Run on a 512 KB chip A500: find the render writes past `$80000` (a write watchpoint
  above `$80000`) and clip them, so `ws_BaseMemSize` can be `$80000`. The unused `_clamp`
  shows where the original author started.
- The benchmark's trace reduction (`tools/bench.py`, `tools/report.py`) still assumes the
  code at `$57000`; `pace.py`, `aprof.py`, `chipaccess.py` and `gametime.py` find it
  (`tools/codebase.py`). The game waits for the blitter only through the clear flag `$606ac`.
