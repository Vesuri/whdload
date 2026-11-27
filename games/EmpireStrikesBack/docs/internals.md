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

## The program

Hand-written assembly with absolute addresses. The main loop at $224a runs a state
machine: the state $73a indexes a table at $79e of 16-byte entries (update, draw, enter,
leave), and a task list at $90e runs every pass. States seen: 0 play (and the attract's
demo), $0a the title, $0b the wave select, $0e the high-score roster, $11-$13 the
scoring and text pages.

The level 3 server at $17a0 counts the frames drawn each second ($1884 into $1886, shown
when $742 is set), cycles the text colours $194 and $198, reads the mouse ($188e) or
joystick ($19e0) and calls the music player ($52690). The level 2 server at $1724 is
the keyboard.

## Game time

Every scene ends its frame in the swap at $5dc02: the hit flash ($40ac4), the frame
count, then it clears INTREQ's COPER bit and waits for the copper list ($1bc4) to set it
again at line $e0 before writing the new bitplane pointers. That is the only pacing, and
the game moves by the frame, so it ran as fast as the CPU drew. Fields a frame, measured
with `tools/esb.py frames` (100-field traces):

| Machine | Wave select | Play | Roster page |
|---|---|---|---|
| a500, original | 3 | 2-7, mostly 3-4 | 6 |
| a1200-060, original | 1 (50 frames a second) | 1 | 1 |

On the a1200-060 the attract's whole cycle took about 7 s against the a500's 40. The fix
(below) makes the swap wait until three fields have passed since the last one: at most
16.7 frames a second (PAL), as the Star Wars timing fix does. With it the a1200-060 shows
16-17 frames a second in every state; the a500 keeps its frames of three fields or more,
and the few that took two now take three.

## Slave patches

| Address | Patch |
|---|---|
| $175c | `PL_PS _Keybd` over `lea $1ac4.w,a0`: the keyboard handler's raw key in d0; F10 (`ws_keyexit` $59) quits |
| $455d6 | `PL_PS _SaveHighs` over `move.w #$800e,$73a.w`: saves the high-score table |
| $1806 | `PL_PS FixVblCount` over `jsr $52690`: counts the fields, then the music player |
| $5dc0c | `PL_PSS FixSwapWait,16` over the COPER wait: three fields a frame at least |

The last two are the timing fix (`src/EmpireStrikesBackFixes.s`), always on. The slave's
`ws_Version` is 17 (Codetapper's was 10), with the header fields that version reads.

The high-score table is 378 bytes at $5b000, stored in `EmpireStrikesBack.highs` with each
byte eor'd with its count down from 378 (`_Crypt`), loaded before the game starts.

## Limitations

The game runs from chip memory as the original. The game is capped at 16.7 frames a
second; scenes the A500 drew slower stay slower there.
