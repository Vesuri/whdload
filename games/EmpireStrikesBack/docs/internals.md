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

| $3f738, $3f748, $3f76a, $47e4e, $47e84, $47eb0, $47ed0, $47f48, $47f7e, $47fa4, $47fc4 | `PL_PSS FixBlitWaitA6,2` over `btst #6,2(a6); bne.s` | BBUSY polls read DMACONR once first |
| $43650, $4377c, $437b4, $437ec | `PL_PSS FixBlitWaitA0,2` over `btst #6,2(a0); bne.s` | the same, in the line drawer |
| $435b2 | `PL_PSS FixPlotStart,2` | the star plot waits for the blitter, then its two instructions |
| $438de | `PL_PS FixVlineStart` | the CPU vertical line waits for the blitter |
| $5c5ac, $5c5f2 | `PL_PS FixDigitStart` | the HUD digits wait for the blitter |
| $5c5a6 | `PL_P FixDigitColour` over `movem.l (sp)+,d1/a0-a4; rts` | the digit colour setter flushes the caches after its opcode copy |
| $43858 | `PL_PSS FixVlineColour,2` over the four moves | the vertical line flushes the caches after its opcode copy |
| $5394a, $53982 | `PL_PSS FixAudioD7,2` over `move.w #$100,d7; dbf d7,*` | the sound effects' DMA waits: 6 to 7 raster lines by the beam |
| $53864 | `PL_PSS FixAudioD0,2` over `move.w #$200,d0; dbf d0,*` | 11 to 12 lines |
| $3f63e, $3f690 | `PL_PSS FixFadeStep,4` over `move.w #$800,d2; subi.w #1,d2; bne` | the pause fade's steps: 86 to 87 lines |

The patches from $1806 on are `src/EmpireStrikesBackFixes.s`, always on.

## Fast-CPU fixes

- **Blitter waits.** The game polls BBUSY right after writing BLTSIZE: the line drawer
  $43624 between its four planes, the shared wait $3f732 that most blits call after
  theirs, the clear $3f742, the blits at $47e40. A fast CPU can read DMACONR before Agnus
  sets the bit and then load the next blit over the running one, or draw with the CPU
  under it. Each poll now reads DMACONR once first (WHDLoad's `BLITWAIT`). The CPU
  drawing (star plot $435d6, vertical line $43908, HUD digits $5c5ac/$5c5f2) waits for
  the blitter first: with the game in Chip RAM and BLTPRI set, a 68000 could not run
  during a blit, while a CPU running from its cache can, and the line drawer returns with
  its last plane's blit running.
- **Self-modified drawing code.** The digit colour setter $5c56a copies a colour's four
  per-plane opcodes (`or.b d1` sets a plane, `and.b d2` clears it; 14 bytes a colour
  at $43a8c, the colour's bits in order) into the HUD digit plots at $5c5dc, $5c62c and
  $5c640, and the vertical line $43832 copies them into its loop at $43908 when the
  colour ($940) changes: the same pattern as Star Wars' plot. With an instruction cache
  the CPU can run the previous colour's opcodes. Both now call `resload_FlushCache`
  after the copy, so the code that runs is still the original's. FS-UAE's a1200-060
  drew the HUD digits in their colours before and after (its cache emulation does not
  show the stale opcodes); a memory dump after play showed these the only code bytes the
  game rewrites.
- **CPU-timed waits.** The sound effects player $53922 switches a channel's DMA off,
  counts 257 passes of `dbf` (the wait for Paula to stop), loads the channel and
  switches DMA on, then counts 257 more before writing the repeat pointer; $53800 counts
  513 after switching one off. A fast CPU counts them in a fraction of a line, before
  Paula has taken the new sample. The pause (Esc, the task at $24e2) fades the palette
  down to $666 and back up in nine steps of $111, each timed by 2048 passes of a
  `subi`/`bne` loop ($3f63e, $3f690), so it was instant on a fast CPU. All of them wait
  by the beam's position now (`FixLines`: elapsed lines, so an interrupt cannot shorten
  them, as it only lengthened the loops), and leave the counter as the loop did. On the
  a500 (`tools/esb.py span`, `keyspan`): the 257-pass loops took 5.7 to 6.5 lines, the
  513-pass one 11.4, a fade step 83 to 88 (traced costs); the waits take 6 to 7 (6.4 to 7.0 on the a1200-060), 11 to
  12 and 86 to 87 (87.2 to 88.7 measured with the stub's overhead). The music player
  ($52690, from the VBL server) switches DMA off and on in different fields and has no
  such wait.
- **Masks.** Unlike Star Wars, every blit that uses the A channel writes BLTAFWM and
  BLTALWM (the line drawer $ffff, the rectangle $43d04 from its tables, $47e40 as a
  long); the shape blits ($47100, $5c1c2) use B, C and D only.
- **The hit flash** ($462e0) starts colour 0 at $777 and subtracts $111 before each
  write, so it ends on black: Star Wars' grey background has no counterpart here. The slave's
`ws_Version` is 17 (Codetapper's was 10), with the header fields that version reads.

The high-score table is 378 bytes at $5b000, stored in `EmpireStrikesBack.highs` with each
byte eor'd with its count down from 378 (`_Crypt`), loaded before the game starts.

## Limitations

The game runs from chip memory as the original. The game is capped at 16.7 frames a
second; scenes the A500 drew slower stay slower there.
