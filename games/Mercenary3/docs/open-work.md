# Current work

Goal: improve the game's performance, especially on higher-end Amigas (a 68020 with
fast RAM and above).

Inputs are pinned and extracted. The shipped slave is reconstructed so that vasm
rebuilds it byte for byte ([internals](internals.md)). The original game boots under
WHDLoad on the A500-equivalent machine, and the native debugger server takes
screenshots and traces with PCs. No reproducible window, frame counter, baseline or
patch exists yet.

## Next steps

1. Find the game's controls and a reproducible gameplay route from the prison cell
   (`monitor key`/`input` with `WARP=1 DETERMINISTIC=1 JOY0=none`), and the game's
   entropy sources.
2. Find the frame-publication point and count frames per field (playbook §7).
3. Baseline profile on the A500-equivalent, a 68020 with fast RAM and the faster CPUs
   (playbook §8), with each machine's cache state, then the game-time model (§9).
   The whole game runs from the slave's 512 KB chip BaseMem, so on fast-RAM machines
   its code and data still sit on the chip bus.
4. Start the patched slave from `whdload/original/`, with every change behind a
   `CUSTOMn` option and the original bytes untouched when it is off.
