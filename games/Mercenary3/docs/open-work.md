# Current work

Inputs are pinned and extracted. The shipped slave's source has been read
([internals](internals.md)), the original game boots under WHDLoad on the
A500-equivalent machine, and the native debugger server takes screenshots and traces
with PCs. No reproducible window, frame counter, baseline or patch exists yet.

## Next steps

1. Rebuild the shipped slave from `src/Mercenary3.slave.asm` and establish whether
   the bytes match; otherwise confirm the rebuild by behaviour.
2. Find the game's controls and a reproducible gameplay route from the prison cell
   (`monitor key`/`input` with `WARP=1 DETERMINISTIC=1 JOY0=none`), and the game's
   entropy sources.
3. Find the frame-publication point and count frames per field (playbook §7).
4. Baseline profile on the A500-equivalent and a 68020 (playbook §8), then the
   game-time model (§9). Patches come after these.
