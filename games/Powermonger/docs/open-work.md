# Open work

Wepl's v1.4.1 slave (`wepl/winstalls` at `c12fcf04`) on the repository layout, with no
improvement work yet. Its unchanged source builds byte-identically to the shipped slave
(`make check`), and the release build boots to the title in the emulator.

## Before a first release

1. A dated `$VER:` string in the slave: `make dist` needs it.
2. A ReadMe entry for the new version above Wepl's history.

## Candidates

- The world advances once per drawn frame, so on fast Amigas the game runs too fast
  ([internals](internals.md#game-time)). Run the world at the A500's pace and draw as often
  as the machine can.
- The 3D view draws slowly even with fast memory on a 68020: the terrain renderer runs from
  chip memory.
