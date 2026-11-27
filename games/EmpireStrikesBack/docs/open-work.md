# Open work

The game is on the repository layout: the slave is Codetapper's v1.2, reconstructed and
rebuilt byte-identically (`release/slaves.sha256` no longer records that build). On top of
it: the timing fix (`internals.md`, "Game time") the blitter waits and the cache
flushes after the self-modified drawing code (`internals.md`, "Fast-CPU fixes").

1. Bring the rest of the Star Wars fixes in (`games/StarWars/docs/internals.md`): the sound effects' CPU-timed DMA waits ($5394a, $53982, $53864), the pause
   fade's CPU-timed steps ($3f63e, $3f690), then CUSTOM2 enhanced framerate.
2. A first release needs a dated `$VER`, a ReadMe entry and an icon tooltype for any option.
