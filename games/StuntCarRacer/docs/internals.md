# Internals

## Loading

The slave (`ws_BaseMemSize` $80000, a 4 KB ExpMem for the stack) has two paths.

- **Disk** (`Disk.1`): it loads the intro, $9800 bytes from disk offset $2c00, to $59e8.
  On the original disk that starts `bra` ($6000007a) and is Rob Northen encrypted: the slave
  decrypts $22b6 longwords from +$c98 and moves them down to $59e8. The intro is patched
  (`_PL_Intro`) and run. Its loader is replaced by `_Loader`, which reads the main program
  ($dc00 on the disk, loaded to $e700) with `resload_DiskLoad`. Before the main program runs,
  `_PatchMain` decrypts it the same way ($18ef8 longwords, three keys from Harry) and moves it
  down to $e700, clearing the $c9c bytes left at its end; a cracked disk is already plain.
- **TNT** (`SCR-TNT` present): the executable is loaded to $1000 and relocated. Its loader
  copies a patch to $7e000, which the slave copies into ExpMem instead; then it jumps to
  `_TNTSpecific`, which turns the track preview's reds to blues and joins the disk path's
  `_GameCommon` at $e700.

Both then apply `_PL_Game` to the program at $e700 and move the game's two stacks to the top
of ExpMem.

## Slave patches

Addresses are the program's runtime addresses ($e700 + file offset of the decrypted main
program).

| Address | Patch |
|---|---|
| intro +$5a | a delay before the title picture removed |
| intro +$86 | black screen instead of red |
| intro +$f8 | level 2 interrupt (keyboard) installed by the slave |
| intro +$124 | `_PatchMain` before the main program |
| intro +$570 | Rob Northen loader to `_Loader` |
| $e70e | the checksum skipped |
| $f036 | keyboard: quit key, F6 infinite boost, F7 turbo, Help wins the race |
| $59846 | the "insert disk" request removed |
| $5b6bc | fire skips the name entry (`Player`) |
| $5c960 | the copylock's result ($9cedcd02 to $24) |
| $5dac0, $64516 | turbo: the frame delay at $616d8 skipped, `TURBO` drawn in the panel |
| $5f2f8 | the lap and track times saved to `StuntCarRacer.times` after a race |
| $62d1c | the times loaded to $7a61a instead of $7a21a |
| $62e86 | the game's loader to `_Loader` (save slots in `StuntCarRacer.save`) |
| $69fea, $6a06e | two 24-bit address faults fixed |

`_RefreshBoost` (F6, CUSTOM1) toggles the `bcs` at $60836 that ends the boost.

## Limitations

The game runs from chip memory and draws at its original rate (about 8 frames a second
on PAL).
