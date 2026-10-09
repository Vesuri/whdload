# Stellar 7: current work

The initial measurement harness works. No performance patch is enabled.
Both supplied slaves are identical; the reconstructed loader uses WHDLoad
20.0 KickEmu and reaches gameplay. This is not a byte-identical reconstruction
of the original KickEmu binary and full original/rebuild equivalence remains
an explicit validation item.

## Established

- Original boot and executable/slave identification; original Kickstart patch list.
- VERIFY/CUSTOM5 menu fixture with original-byte guards; no gameplay patches.
- SOL frame-90 anchor at hunk 0:$2c16; snapshots and exact slave retained per capture.
- Two A500 runs: identical whole data hunk, all 50 images and PC/cycle streams.
  Raw register/DMA records still differ; the strict comparison reports that.
- 50-field traces: A500-equivalent 5.0 fps; 68020 + 4 MB fast RAM 11.4 fps.
  Independent breakpoint captures match every field on both CPUs.
- Frame-coupled gameplay counters: five versus eleven simulation-loop advances
  in the same fifty timer ticks. Player/RNG state at frame 90 matches.

## Next work, in order

1. Establish original/rebuild behavioral equivalence and a byte-identical
   source reconstruction of the original slave if maintaining that reference.
2. Add a moving/firing route, broaden the state map to enemies and projectiles,
   compare equal elapsed fields, and test deliberately slowed drawing.
3. Choose the timing design before introducing performance changes.
4. Profile a heavier scene and bound candidate savings before implementing.

## Design recommendation

Separate simulation cadence from rendering before aiming for higher frame
rates. The existing tick only caps the loop; counters still progress once per
frame. A renderer-only change therefore changes part of game speed.

A timing-first design should keep input, AI, spawning and power timers at an
explicit cadence, then render the latest state (with interpolation only if
needed). The intended cadence needs evidence from the original game on the
chosen reference machine. This is a design proposal, not an implemented fix.

The alternative is to keep original frame-coupled behavior and ship only
optional rendering optimizations, documenting the speed change. Current
candidates are vertex transform/projection work and blitter/OS overhead;
there is no measured optimization gain yet.
