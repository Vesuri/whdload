# Internals

## Loading

A direct slave (`ws_BaseMemSize` $80000, no ExpMem, no Kickstart). It reads the title
picture (5 planes of 8000 bytes and a 32-colour palette, $9c80 bytes) to $73000 from disk
offset $2c00, or from $2800 when the long at +12 is not $f9f0fa07 there (the second
version; a mismatch at both quits with "wrong version"). It shows the picture through its
own copper list, fades it in, loads the game image ($5e000 bytes from disk offset $dc00, or
$c800 in the second version) to $500, waits 76 frames (or for a button with ButtonWait),
fades out, clears the picture, loads the high scores, patches and jumps to $500.

Addresses here are the game's runtime addresses: disk image offset = address - $500 +
$dc00 or $c800. The image is position-dependent code with absolute addresses; there is no
hunk file.

## Slave patches

| Address | Patch |
|---|---|
| $175c | `PL_PS _Keybd` over `lea $1ac4.w,a0`: the keyboard handler's raw key in d0; F10 (`ws_keyexit` $59) quits |
| $455d6 | `PL_PS _SaveHighs` over `move.w #$800e,$73a.w`: saves the high-score table |

The high-score table is 378 bytes at $5b000, stored in `EmpireStrikesBack.highs` with each
byte eor'd with its count down from 378 (`_Crypt`), loaded before the game starts.

## Limitations

The game runs from chip memory as the original. Nothing from the Star Wars work is in yet
(`open-work.md`).
