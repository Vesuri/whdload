# Current work

Goal: improve the game's performance, especially on higher-end Amigas (a 68020 with
fast RAM and above).

The shipped slave is reconstructed byte for byte. A reproducible 500-field `a1200-fast`
profile of a walk out of the cell exists, with a validated frame counter, and the
game-time model is measured ([internals](internals.md)).

## Findings that shape the work

- The slave's `_dmaon` patch runs once per frame and waits for a vertical blank each
  time: 14.7% of the `a1200-fast` CPU time, on top of the game's own 6.3% wait for the
  next field. It also leaves 12 of the frame's 34 copied bytes uncopied.
- World ticks per frame are the elapsed fields clamped to 4..8. The world runs in real
  time only between 6.25 and 12.5 fps; the A500-equivalent (4–6 fps) runs slow, and any
  machine pushed above 12.5 fps would run fast.
- All game code and data are in chip RAM, even with fast RAM fitted.

## Decision for the user

Above 12.5 fps the original game speeds up. Raising the frame rate past that needs a
choice: keep the original behaviour, or lower the tick clamp's minimum (below 4) so the
world stays at real time. The latter changes the game's behaviour on fast machines.

## Next steps

1. Find out what `_dmaon` is for and whether a single DMA enable can replace the
   per-frame wait, with the 12 missing bytes restored; measure it on `a1200-fast`.
2. Make the entry breakpoint work on the 68030 (or anchor differently) and add
   `a1200-030` and `-NOMMU` 040/060 cells to the profile and game-time runs.
3. Profile the A500-equivalent on the same route, and attribute the remaining game time to
   routines (renderer, world ticks) with the self-cycle tables.
4. Evaluate moving game code and CPU-only data out of chip RAM on fast-RAM machines.
5. Start the patched slave from `whdload/original/`, with every change behind a `CUSTOMn`
   option and the original bytes untouched when it is off.
