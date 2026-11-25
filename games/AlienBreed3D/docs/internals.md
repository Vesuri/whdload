# Internals

Slave offsets are code-hunk offsets in `AlienBreed3D.slave` (the source's `Lxxxx`
labels). Game offsets are `resload_PatchSeg` offsets: the executable's hunks laid end to
end, as `tools/exe.py` writes them to `tmp/exe/abd.flat` (hunk 0, code and data, $0-$912d4;
chip hunks 1-3 from $912d4, $9b238, $9b250 to $ad9e8). Game offsets below are in the
$c4dc version.

## How it loads

A direct slave (WHDLoad 18, 68020 and AGA required): 576 KB chip (428 KB without
music) and $158000 bytes of ExpMem.

- Stacks: SSP at ExpMem+$157e00, USP 1 KB below.
- Caches (`resload_SetCPU`): instruction and data cache on; on a 68040/060 also copyback for
  ExpMem and the slave, the store buffer, branch cache and superscalar dispatch; base
  memory stays non-cacheable.
- Interrupts: level 2 (keyboard, quit key, the game's PORTS server), level 3 (VBL reads
  the joypad, holding Reverse+Forward+Play 1 s quits; COPER calls the game's copper
  interrupt server), level 5,
  level 6 (CIA-B timer for the end part's HackAB3D music; not in the no-music slave).
- `team` (the Team 17 picture) is shown from chip $40000 for 4 s.
- Exec and dos are 2048 words of ILLEGAL each, at the start of ExpMem, with only what
  the game calls: exec AllocMem/FreeMem on the slave's own allocator (`_allocmem`,
  `_freemem`; a chip pool after the loaded executable, a fast pool in ExpMem), and
  Forbid, Permit, SuperState, UserState as RTS; dos Open (the name is the handle), Read
  (loads the whole file with `resload_LoadFileDecrunch`, dropping a 5-character volume
  prefix), ExamineFH (`resload_GetFileSizeDec`), Close and Delay as RTS. ExpMem then
  starts $2000 further on.
- Without NOMUSIC, `HackAB3D` is loaded when present, relocated, patched (`_pl_hack`) and
  initialised; the game follows 12 KB after it.
- The executable: `abd8ch` with CUSTOM3=1, else `abd.pk`, else `abd`, else `abd8ch`.
  `resload_LoadFileDecrunch`, then its CRC16 picks the patch list: $23d2 `_pl_v1`,
  $fd78 `_pl_v2`, $c4dc `_pl_v3` (another CRC aborts with TDREASON_WRONGVER). It is
  relocated (`resload_Relocate`, chip hunks into the chip pool, 8-byte alignment,
  LoadSeg layout), `prefs` is loaded, the list applied with `resload_PatchSeg`, and the
  game started with `jmp 8(a6)`.
- The installed `ABD.PK` (RNC-packed, 749824 bytes unpacked) is the same file as
  `abd8ch`: the $c4dc version, which `_pl_v3` patches. It is the Aminet 8-channel version:
  its list has none of the end-part patches, and the ReadMe says that version has no end
  part. The CD32 drawer's `data/abd` (RNC, 765368 bytes unpacked, a fifth hunk of 6140
  bytes) is the $fd78 version, which `_pl_v2` patches. No archive holds the floppy one,
  $23d2.

## Slave patches

Each version's list (game offsets differ; `_pl_v1` shown): CUSTOM1 bit 0 unlimited
energy, bit 1 unlimited shots, bit 2 F1 skips the level (`PL_IFC1X`); CUSTOM2 mouse
button layouts (`_p_control`); the game's VBL and keyboard handlers taken as callbacks
(`_p_setvblcb`, `_p_setkeycb`); copper and beam access through the slave (`_p_setcop2`,
`_p_vhposr`, `_waitvbl`, `_p_waitlines`); the joypad read through the slave
(`_p_readjoyport`); two bounds checks that skip the game's code on an out-of-range read
(`_p_boundsread`: an index outside 0-511; `_p_boundsl13`: an address past
ExpMem+$153000, the level 13 access fault fixed in 1.3); `prefs` saved by
`resload_SaveFile` (`_p_saveprefs`); the end part's scroll replaced by the slave's
(`_endpart`: a copper list of its own, scrolled until a button, then quit); music on and off around the end part (`_p_musicon`,
`_p_musicoff`, not in the no-music slave). Item by item: the `PL_` lists in the source.

## Display

The 3D view is a copper chunky screen of 96x80 pixels in 12-bit colour (4096 colours, no
palette): the renderer writes each pixel's colour word straight into a copper MOVE.

- Copper lists: two, double-buffered, allocated at $44652 (pointers at $43c38 and
  $43c3c), 80 lines of 416 bytes (the source's `widthOffset`, 104 * 4). Each line is BPLCON4
  with bit 15 flipped every line, then for palette banks 1, 2 and 3 a BPLCON3 bank
  select and 32 COLOR moves (built by $8f3a), then two words a view needs: in the small
  view BPLCON3 $0c42 and a COLOR15 from a per-line table at $93f5c, in full screen two
  WAITs that step three raster lines.
- Pixel x of a line is colour register x of banks 1-3: a static 7-plane pattern written
  by $52da (192 pixels, from the table at $9af18) or $54f4 (320, from $9add8), shown on
  every line by bitplane modulos of -24 or -40. BPLCON4 bit 15 (BPLAM) XORs the pens with
  $80 on alternate lines, so the copper loads one line's colours into banks 5-7 while the
  other line shows banks 1-3.
- The copper template in chip hunk 1 (DIWSTRT at $9a08c, FMODE $000f, BPLCON0 $7201 at
  $9a200) gets the window, modulos and sprite pointers from the builders.
- Small view, $5134 (loop at $5148): each chunky pixel 2x2, 192x160 lores pixels (DDFSTRT
  $48, DDFSTOP $88, DIWSTRT $2cb1, DIWSTOP $2c91). The frame left and right of it is
  sprites 0-3 (64-pixel AGA sprites, data at $912dc, 2592 bytes apart); the panel is
  below.
- Full screen, $534e: the same 96x80 image at 3x3, 288x240 lores pixels, no panel, every
  sprite pointer at the null sprite ($912d4).
- Keypad Enter (raw $43, the key table is at $6434) is read in each player's control
  routine, $4023c and $4104c: it flips the byte at $40279 and rebuilds both copper lists
  with $534e or $5134. Nothing in the renderer reads that byte: both views draw the same
  96x80 frame.

The renderer writes 12-bit colour words at a pixel stride of 4 bytes, 4 more at each
32-pixel bank boundary (the BPLCON3 move), and 416 bytes a line. The horizontal span
routine at $1fd4c (variants up to $20458) is typical: a texel byte, `(a0,d5.w*4)`,
indexes a word shade table, `(a1,d0.w*2)`, and variants store the pixel down one to four
lines. The textures carry
their own colours: a wall tile is 32 colours at 33 brightness levels of 12-bit words
ahead of its texels (the source's `walltiles` and `PaletteAddr`). Game time does not
depend on the frame rate: each frame advances the game by the fields since the last one
(`TempFrames`, at most 15), which the interrupt counts (`FramesToDraw`).

The CD32 version draws the same way, at other offsets: the small-view builder's loop at
$501c, the full-screen builder at $5206, keypad Enter at $404c2, and byte for byte the span
routine at $1ffcc and the colour moves at $90fe.

The published AB3D I source (the 1997 Amiga Format cover CD, as
`Agrigaatti/Alien-Breed-3D-I` on GitHub) names these routines: the view's constants are
`widthOffset`, `rightclip` 96, `top` 80 and a centre x of 47. It is a development
tree, not this executable's build, so its labels are a map, not offsets. It was released
for personal use: read it in an ignored `tmp/`, never copy it into the repository.
