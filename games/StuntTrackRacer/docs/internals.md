# Internals

## Loading

The slave (`ws_BaseMemSize` $80000, an optional $70000-byte ExpMem) loads the intro, $9800 bytes from disk
offset $2c00, to $9448 and decrypts its Rob Northen encryption in place ($22b5 longwords
from +$c9c, moved down to $9448). It points the intro's call before the main program
(intro +$126) at `_PatchMain` and its loader ($99b8) at `_Loader`, which reads the main
program ($dc00 on the disk, to $e700) with `resload_DiskLoad`. `_PatchMain` decrypts the main
program the same way ($19e40 longwords), patches it and jumps to $e700, or with the
enhanced framerate to its copy in ExpMem (below).

The main program's layout matches the PAL Stunt Car Racer's at every address the slave
patches: Codetapper's PAL slave patches the same addresses. Decrypted, the two programs
differ only in the checksum ($e718), the display window ($edfe-$ee0f: diwstrt $2c81,
diwstop $f4c1 and the sprite offset), the title logo ($2506a-$265f7) and the frame delay at
$5dadf (7 fields instead of 6); every one of the 5995 relocation sites holds the same
value.

## The enhanced framerate (CUSTOM3, 68020 or better)

The same as Stunt Car Racer's (its docs/internals.md, "The fast copy" and "The enhanced
framerate"): with CUSTOM3 on a 68020 or better and the ExpMem there, `_Enhance` copies the
decrypted program ($e700-$722e0) to ExpMem+$1000, relocates it with Stunt Car Racer's
`relocTable` and puts Unleashed's blob behind it, built for NTSC (`FRAMERATE_MULTIPLIER`
7, as Stunt Track Racer Unleashed: the time step $22, the counters and cooldowns scaled by
7). The slave's patches then go to the copy, less the turbo and the two 24-bit fixes (the
blob fixes those for any memory). The copper list, the samples and the frame buffers stay
in chip memory at $e700's addresses. On a fast machine it draws 60 frames a second at the
original game speed: 200 frames in 200 fields on the emulated 68040, 179 on the 68030; the
race clock advances 8.50 s in 500 fields with the copy and 8.49 s without.

The verify build read- and write-protects the chip program less those parts
(`resload_ProtectReadWrite`, `MMU` on a 68030 or better).

## Slave patches

Addresses are the program's runtime addresses ($e700 + file offset of the decrypted main
program).

| Address | Patch |
|---|---|
| $e716, $e71a | the checksum skipped |
| $f036 | keyboard: quit key, F6 infinite boost, F7 turbo, Help wins the race |
| $1ba60 | two `nop`s (copylock) |
| $59846 | the "insert disk" request removed |
| $5c8f0 | the copylock: its result ($9cedcd02) in d0 and a branch past it |
| $5dac0, $64516 | turbo: the frame delay at $616d8 skipped (not with the copy) |
| $62e86 | the game's loader to `_Loader` (save slots in `StuntTrackRacer.save`) |
| $69fec, $6a06e | two 24-bit address faults fixed (not with the copy) |

With the copy the patches go to the same addresses in it, and the trainer and the key tables
too. `_RefreshBoost` (F6, CUSTOM1 at the start) toggles the `bcs` at $60836 that ends the
boost, or with the copy Unleashed's flag. Codetapper's v1.0 had the trainer on F1 and F2;
the game redefines its keys with F1 while paused, so they moved to F6 and F7, as in his
Stunt Car Racer slave. With WHDLoad 12 or later, `_KeyTrans` fills the game's two key tables
($1b8a8, $1b960) from WHDLoad's rawkey table (international keyboards). ButtonWait holds the
title picture.

## Limitations

Without CUSTOM3 the game runs from chip memory and draws at its original rate (about 8
frames a second on NTSC). The lap times are not saved. Link play over the serial port is
untested with the copy; Unleashed does not support it.
