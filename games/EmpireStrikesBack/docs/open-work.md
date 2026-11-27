# Open work

The game is on the repository layout: the slave is Codetapper's v1.2, reconstructed and
rebuilt byte-identically (`release/slaves.sha256` no longer records that build). On top of
it: the timing fix (`internals.md`, "Game time").

1. Bring the rest of the Star Wars fixes in (`games/StarWars/docs/internals.md`): the fast-CPU drawing fixes (self-modified plot opcodes, blitter
   waits, blitter masks), the flash fade, the music player's CPU-timed wait, then CUSTOM2
   enhanced framerate.
2. A first release needs a dated `$VER`, a ReadMe entry and an icon tooltype for any option.
