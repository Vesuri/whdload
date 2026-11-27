# Open work

The game is on the repository layout: the slave is Codetapper's v1.2, reconstructed and
rebuilt byte-identically (`release/slaves.sha256` no longer records that build). On top of
it: the timing fix (`internals.md`, "Game time"), the blitter waits, the cache
flushes after the self-modified drawing code, and beam waits for the sound effects' DMA
and the pause fade (`internals.md`, "Fast-CPU fixes").

The enhanced framerate (CUSTOM1, `internals.md`) is in, for states 0, 1, 2 and $0a, and
release 2.0b has the dated `$VER`, the ReadMe entry and the icons' `CUSTOM1=1`.

1. Compare the waves' later phases ($03, $08, $09, $0d, $15) with the `check` build
   (`sweep` reaches them, not every run) and add them to `SM_STATES`, with sites for any
   direct screen writer a mismatch shows (candidates: $1ed8, $1f0c, $461cc, $46220,
   $47108, $49af0, $5c010, $5d342).
2. Frames cost 170 to 250 lines on the 030/040, mostly blitter lines and the chip bus:
   fewer redrawn bands (a line's rows, not its bands) would give more in-between frames.
