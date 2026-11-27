# Internals

The program, its display and game time, every slave patch (as offsets into the game's code
hunk or file), current measurements and known limitations.

## Loading and memory

A direct slave in 512 KB of chip memory (`ws_BaseMemSize` $80000). The slave loads the boot
block's loader from disk offset 0 to $40000, patches it and jumps to $4000C; the loader
loads the main program and calls the slave's `_PatchV1` or `_PatchV2`, which patch it and
jump to its entry at $3658. Addresses here are BaseMem addresses of v1 (the Retroplay
disk): the program is loaded at fixed addresses, so they are its file layout too. In v2
the loader and part of the program sit $8C lower.

## The original slave's patches

| Where (v1) | What |
|---|---|
| loader $40030, $4007A, $401EE/$401F8 (v2 $40224) | trap #0 for the loader, `move.l a1,a2` removed, `_PatchV1`/`_PatchV2` called |
| loader at $6EE88 | the track loader replaced by `_LoadTrack0` (`resload_DiskLoad`), MFM decoding skipped |
| $394E, $3BCE | disk protection |
| $1EA84-$1EB1E | drive head moves and delays removed |
| $1EBA0, $1ED06 | highscore save (`resload_SaveFileOffset`) and track loads |
| $ACCC | keyboard: quit key, F9 |
| $1B526, $1B5F0, $1B8A2, $1B568, $1B626, $1B8C8 | the scaler's self-modifying `move.l (a4,d0.w),(a5)`/`(a6)` moved to the slave ($100, $106), after every track load |
| $6F23C/$6F428, $1EF0A/$1F118 (v2 $1EE7E/$1F08C) | the loader's and the program's decrunchers, copies in the slave |
| $89B2 (v2, with $61EE) | a second track protection |
