# Open work

The game is on the repository layout: the slave is Codetapper's v1.2, reconstructed and
rebuilt byte-identically (`release/slaves.sha256` no longer records that build). On top of
it: the timing fix (`internals.md`, "Game time"), the blitter waits, the cache
flushes after the self-modified drawing code, and beam waits for the sound effects' DMA
and the pause fade (`internals.md`, "Fast-CPU fixes").

1. CUSTOM2 enhanced framerate, as in Star Wars (`games/StarWars/docs/internals.md`,
   "Enhanced framerate"): record the drawing primitives of a frame (the line drawer
   $43624, the vertical line $43832, the star plot $435a0, the shape blits $47100 and
   $5c1c2, the rectangle $43d04, the digits, the clear $3f742) and draw interpolated
   frames between the game's at 50 a second.
2. A first release needs a dated `$VER`, a ReadMe entry and an icon tooltype for any option.
