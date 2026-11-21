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

50 frames a second at a 25 Hz tick, and three and four frames a tick at 16.7 and 12.5 Hz:
on the fields between two ticks' frames, frames interpolated between the two ticks, with
the game state byte-identical. Tick N's own frame then shows P−1 fields later (20 ms at
25 Hz). The design and the code behind it are in
[internals](internals.md#frames-between-ticks).

It needs Enhanced framerate and fast memory (the drawing buffer). Which machines it can
help: the a3000, a3000-50 and the a1200-030, -040 and -060 draw a whole pass in a field in
the demo (50.0 fps with Enhanced off), and a frame between ticks leaves out the simulation;
the 14 MHz 68020s draw 35.8 and 37.8 fps, 26 to 28 ms a pass, so at 25 Hz only light scenes
leave room. Both are still to be measured.

Steps, each checked before the next:

1. **Pairing** (done): tools/pairs.py, in the demo and in play, found every source that
   exists on two ticks paired by its slot and the dispatchers' moves, and no record changed
   between ticks ([internals](internals.md#frames-between-ticks)). Not met yet: the
   attractor's lightning and 12 of the 18 object handlers.
2. **Record.** The hooks at the 7 stores and 2 removals, and the two tables in ExpMem.
   Checks: no game state changes (tools/callwrites.py `compare` at demo tick 200 against
   Enhanced without it); the recorded entries are the native lists'.
3. **Draw between.** Staging, the six skipped calls, the restore, the renderer and the swap.
   Checks:
   - a frame at α = 1 is tick N's own, pixel for pixel;
   - the game state is byte-identical with frames between ticks on and off, at demo tick 200
     and at the demo's end;
   - screenshots of consecutive fields show the moving things midway.
4. **Pace.** Frame k only while it can show on its field; CUSTOM3 ("Frames between ticks")
   turns it on. Measure with tools/pace.py, extended to count frames between ticks.
   Even holds look smooth; a mix of one and two fields can look worse than a steady 25.
5. **The death sequence.** Its 51 passes (the explosion's debris) get the same.
6. **Play-test.**
   - Matrices blended word by word: an object that turns fast looks smaller midway?
   - Unpaired entries (new particles, the screen's edge) pop by a field.
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
- **50 frames a second.** The a3000 and up draw 50 in the demo, but a frame a tick holds
  them at 25. A 50 Hz tick at today's pace is on the order of 80 patch sites in integer code
  and still another game ([internals](internals.md#a-50-hz-tick)). Frames interpolated
  between ticks are the plan instead ([above](#frames-between-ticks)).
- Run on a 512 KB chip A500: find the render writes past `$80000` (a write watchpoint
  above `$80000`) and clip them, so `ws_BaseMemSize` can be `$80000`. The unused `_clamp`
  shows where the original author started.
- The benchmark's trace reduction (`tools/bench.py`, `tools/report.py`) still assumes the
  code at `$57000`; `pace.py`, `aprof.py`, `chipaccess.py` and `gametime.py` find it
  (`tools/codebase.py`). The game waits for the blitter only through the clear flag `$606ac`.
