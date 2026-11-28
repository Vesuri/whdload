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

The patches from $1806 on are `src/EmpireStrikesBackFixes.s`, always on. With CUSTOM1
on a 68020 or better (and the optional ExpMem) `_PL_Smooth` adds the enhanced
framerate's (below, `src/EmpireStrikesBackSmooth.s`):

| Address | Patch |
|---|---|
| $226c | `PL_PS SmTick` over `lea $90e.w,a0; move.w (a0)+,d0`: a tick begins (recording) |
| $5dc02 | `PL_P SmSwap` over `jsr $40ac4`: the tick's frames presented |
| $1806 | `PL_PS SmVbl` over `jsr $52690` (FixVblCount): the field count, then the queued frame shown from its field |
| $2256 | `lea $70000,sp`: `SmInit` writes the main loop's new stack top into $2258 before the patch list (4 KB at the end of ExpMem) |
| $435f2, $43832, $435a0, $43d04, $3f742 | `PL_P` the line, vertical line, plot, horizontal line and clear: recorded |
| $5c56a, $5c5ac, $5c5f2 | `PL_P` the text colour and the glyphs: recorded |
| $47de6, $47f0a, $4630a, $494aa, $5bf90, $5c008, $5b428, $2d04, $470fa, $5c1bc, $5d2c0, $1ed0, $44ccc | `PL_P` the sites (code that writes the screen itself): recorded with its registers |

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

## Enhanced framerate

CUSTOM1 (the icons set it), on a 68020 or better: 50 frames a second at the game's own
speed, in the waves (states 0, 1, 2 and $0a), the wave select ($0b), the roster ($0e)
and the attract's pages ($11 to $14); the later phases of a wave run as without it. The
slave asks for an optional ExpMem of about 90 KB (two recordings, a work area and the
main loop's stack); without it, or on a 68000, nothing is patched.

- **Recording.** Each tick (one pass of the main loop, from $226c to the swap) still runs
  once, but the drawing routines record their calls instead of drawing (a 16-byte op:
  type, colour, a key, four coordinates, the paired op). Code that writes the screen
  directly is hooked as a site: its registers (screen-relative ones as offsets) and the
  words it reads are recorded, and at replay it runs again from the hook to its `rts`
  with them put back. A site declares its rows (or a routine that works them out from
  the registers: the shape blits), its input registers, and a fixup for what it does
  besides drawing when it is not run (the shield gauge sets the star colour $76a). The
  icons at $5c008 animate after drawing, and the scoring page's scrolling table ($1ed0,
  state $12) steps its scroll $1cae after drawing, so their sites are copies of the
  drawing loops. The roster's badges ($5d2c0) and the wave select's documents ($44ccc)
  work out their rows from a0.
  The cannons read the crosshair ($47db6, $47db8) as it is at the replay: they follow
  it at 50 frames a second, as the crosshair (a sprite) does.
- **Pairing.** Ops are keyed by the object drawn and the place in its model's display
  list (model lines, return $3fab6/$3fb34, object $752), by the lattice cell (the star
  field, $5c3ba), else by the code address and its count in the tick; a hash table
  pairs each with the previous tick's op of the same key. Pairs that moved more than 40
  pixels (96 for keyed ones) are not interpolated.
- **Presenting.** At the swap the recording is drawn at 1/3 and 2/3 of the way from the
  previous one, then exactly. The exact frame goes into the game's back screen
  ($70000/$78000), as the game would have drawn it, and the game's screens are left as
  its swap leaves them. The in-between frames go into two more screens in free Chip RAM,
  $60000 and $67d00: the image ends at $5e500 and the stack sat below $70000, and the
  line drawer adds its offset to the screen's low word, so each screen lies in one 64 KB
  bank. The main loop's stack moves to the end of ExpMem (4 KB; it used 326 bytes in
  every state reached): in Chip RAM, with no data cache, every call and `movem` of the
  replay waited for the chip bus. Each frame is drawn for the first field it can make (by the last frame's
  drawing time) and queued, one at most, while the next is drawn; the VBL server ($1806)
  shows it from its field, writing BPL1PT-BPL4PT before the display starts (the copper
  list at $1bc4 loaded the old pointers at line 0) and the copper list's words. So the
  swap returns once the exact frame is queued, and the next tick's logic overlaps the
  frames still to be shown. An in-between frame is drawn only if the exact frame still
  makes its field after it, and only for a recording that starts with the clear. A tick
  that draws directly (a state not presented, or direct mode) first waits until no frame
  is queued. When more than half of about the last 16 ticks are late, ticks run as the
  default runs them (direct) until a direct tick's work plus a frame fits again, or the
  state changes: direct mode is the scene's (the logo's flight, $14, is late at first;
  the roster after it, smooth, would otherwise have stayed direct: its direct ticks,
  with the game's own glyphs, take about 680 lines).
- **Bands.** A frame is drawn only where it differs from what its screen shows: each of
  25 bands of 8 rows of each of the four screens has a signature (the ops drawn in it,
  as drawn), and only bands whose signature changed are cleared (by the CPU, 32 bits at a
  time: half the time of the four 16-bit blits) and drawn again, with every band of any
  op drawn. Anything else that draws into the game's screens (a direct tick, the
  attract's frames, a draw outside the tick's screen) invalidates their signatures.
- **Glyphs.** The HUD's glyphs are replayed by the slave's own routine: the font at
  $5c658, each plane set or cleared by the colour's bit, as the opcodes $5c56a copies
  from $43a8c do, without copying them or flushing the caches. After the exact frame the
  game's setter runs once with the tick's last text colour, as the tick would leave it.
  The half-byte glyphs ($5c5f2) clear their second byte, in the planes the colour lacks,
  by the previous row's first byte (`not.b d2` complements only the low byte, and the
  swaps bring the old one back; row 0 by the caller's d2 bits 16-23, recorded): stars
  next to text are cleared as the game clears them. The glyphs of a string (same
  routine and colour, the next byte) are drawn together, up to the four bytes from the
  first's even address, by longs: in each plane every glyph of a colour only sets or
  only clears, so their masks combine.

Checked with the `check` and `verify` builds (`development.md`): the exact replay
compared with what the tick drew, and each frame drawn by bands (the extra screens'
included) with the same frame drawn whole. In state 0 on the a1200-030 all 530 exact
frames matched; on the a1200-040 (`verify`, wave 1 picked, then its later phases) all
783, in states 0, 1, 2 and $0a, and all 1289 frames drawn by bands. With the stack in
ExpMem and the glyph runs, on the a1200-030 all 1247 exact frames from the boot
through the wave select into wave 1 and $0a, and all of the attract's 1394 ($0e, $11,
$12, $13, $14); the a1200-040 (`verify`) all 259, in states 0, 1, 2, $0a, $0b, $0e, $12
and $13.

Measured on the a1200-030 in wave play (`tools/esb.py sm` per 250 fields), with the
queue: 2.3 to 2.9 frames a tick in most rounds (before it, with only the game's two
screens, 1.78 over 2008 ticks: half the CPU's time waited for a screen to be free).
A frame costs about 250 raster lines (the `timing` build: lines 50-90, the clear 42,
glyphs 52-67, most of them the blitter's line time, SmPrep 20); heavy scenes (large
models across the screen) still fall to the exact frame only. The a1200-040: 1.75 to
2.3. The stock a1200 presents some in-between frames in light scenes. The game's speed
is the default's: fields a tick against the `direct` build, 3.11/3.08 on the 030,
3.14/3.21 on the a1200 (the same route, different play).

The attract on the a1200-030 (`tools/esb.py sm`, release build): the pages $11 to $14
2.93 to 3.0 frames a tick, the roster 2.69 to 2.73 over three visits (before, as the
default: 1, every third field; with the stack in Chip RAM and each glyph drawn alone,
1.2 to 1.7). A roster frame (the `timing` build) costs about 330 lines, 200 to 220 of
them glyphs: 1.1 lines a glyph alone, 1.54 a run of about two; before, 390 lines, with
SmPrep twice as long. In wave play: 2.42 to 2.82 frames a tick. The stock a1200 falls
to direct mode in many scenes, as before (the build before, the same route: 0.5 to 2.1
frames a smooth tick).

## Limitations

The game runs from chip memory as the original. The game is capped at 16.7 frames a
second; scenes the A500 drew slower stay slower there. The enhanced framerate covers the
states checked (0, 1, 2, $0a, $0b, $0e, $11 to $14); the later phases of a wave ($03,
$08, $09, $0d, $15) were reached in play but not compared, so they run as without it.
