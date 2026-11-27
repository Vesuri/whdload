# Internals

## Loading

The slave (`ws_BaseMemSize` $80000, no ExpMem) loads the intro, $9800 bytes from disk
offset $2c00, to $9448 and decrypts its Rob Northen encryption in place ($22b5 longwords
from +$c9c, moved down to $9448). It points the intro's call before the main program
(intro +$126) at `_PatchMain` and its loader ($99b8) at `_Loader`, which reads the main
program ($dc00 on the disk, to $e700) with `resload_DiskLoad`. `_PatchMain` decrypts the main
program the same way ($19e40 longwords), patches it and jumps to $e700.

The main program's layout matches the PAL Stunt Car Racer's at every address the slave
patches: Codetapper's PAL slave patches the same addresses.

## Slave patches

Addresses are the program's runtime addresses ($e700 + file offset of the decrypted main
program).

| Address | Patch |
|---|---|
| $e716, $e71a | the checksum skipped |
| $f036 | keyboard: quit key, F1 infinite boost, F2 turbo, Help wins the race |
| $1ba60 | two `nop`s (copylock) |
| $59846 | the "insert disk" request removed |
| $5c8f0 | the copylock: its result ($9cedcd02) in d0 and a branch past it |
| $5dac0, $64516 | turbo: the frame delay at $616d8 skipped |
| $62e86 | the game's loader to `_Loader` (save slots in `StuntTrackRacer.save`) |
| $69fec, $6a06e | two 24-bit address faults fixed |

`_RefreshBoost` (F1) toggles the `bcs` at $60836 that ends the boost. With WHDLoad 12 or
later, `_KeyTrans` fills the game's two key tables ($1b8a8, $1b960) from WHDLoad's rawkey
table (international keyboards). ButtonWait holds the title picture.

## Limitations

The game runs from chip memory and draws at its original rate (about 8 frames a second on
NTSC). The lap times are not saved.
