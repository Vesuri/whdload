# Open work

The game is on the repository layout: the slave is Codetapper's v1.2, reconstructed and
rebuilt byte-identically (`release/slaves.sha256` no longer records that build). On top of
it: the timing fix (`internals.md`, "Game time"), the blitter waits, the cache
flushes after the self-modified drawing code, and beam waits for the sound effects' DMA
and the pause fade (`internals.md`, "Fast-CPU fixes").

The enhanced framerate (CUSTOM1, `internals.md`) is in, for states 0, 1, 2 and $0a, the
wave select ($0b), the roster ($0e) and the attract's pages ($11-$14); release 2.0b has
the dated `$VER`, the ReadMe entry and the icons' `CUSTOM1=1` (it had the waves only).

1. Compare the waves' later phases ($03, $08, $09, $0d, $15) with the `check` build
   (`sweep` reaches them, not every run) and add them to `SM_STATES`, with sites for any
   direct screen writer a mismatch shows (candidates: $1ed8, $1f0c, $461cc, $46220,
   $47108, $49af0, $5c010, $5d342).
2. The user's recording (27.11.2026): at 1:06 some dots stayed in place for several
   frames (not interpolated), and at 1:50 play ran at about 12.5 frames a second with
   little on screen: find the scene (a state not presented, or direct mode) and the dots'
   key (unpaired, or moved more than SM_T).
3. Frames cost about 250 lines on the 030 (heavy scenes far more; the roster about 330,
   most of it glyphs, each a few chip-RAM writes per plane and row): the line drawer
   blits all four planes of every line (zeros into the planes its colour lacks), which
   in-between frames could skip with a line routine of their own; and the data cache
   for ExpMem (CACHE leaves it off; Chip RAM must stay uncached, the blitter writes it).
4. Late ticks in heavy scenes still put the game into direct mode for 50 ticks.
