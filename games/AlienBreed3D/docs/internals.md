# Internals

Slave offsets are code-hunk offsets in `AlienBreed3D.slave` (the source's `Lxxxx`
labels). Game offsets are `resload_PatchSeg` offsets: the executable's hunks laid end to
end, as `tools/exe.py` writes them to `tmp/exe/abd.flat` (hunk 0, code and data, $0-$912d4;
chip hunks 1-3 from $912d4, $9b238, $9b250 to $ad9e8). Game offsets below are in the
$c4dc version.

## How it loads

A direct slave (WHDLoad 18, 68020 and AGA required): 576 KB chip (428 KB without
music) and $158000 bytes of ExpMem, so a 2 MB a1200 without fast memory cannot run it
("Can't allocate ExpMem"); the a1200-fast setup is the smallest that does.

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

- Copper lists: two, double-buffered, allocated at $44652 (their addresses at $43c38 and
  $43c3c, which the level start, $30ac, copies to `drawPt` $5dd40 and `oldDrawPt` $5dd44).
  Once a frame, after a vertical-blank wait, the main loop swaps the two and points COP2LC
  at the new `oldDrawPt` (the swap at $32bc, $3e2c and $8e48). 80 lines of 416 bytes (the source's `widthOffset`, 104 * 4). Each line is BPLCON4
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
32-pixel bank boundary (the BPLCON3 move), and 416 bytes a line. The plain floor span,
`acrossscrn` at $20f66, is typical: a texel byte, `(a0,d5.w*4)`, indexes a word shade
table, `(a1,d0.w*2)`, the word goes to `(a3)` and `a3` steps 4, with the extra 4 every
32 pixels. The textures carry their own colours: a wall tile is 32 colours at 33
brightness levels of 12-bit words ahead of its texels (the source's `walltiles` and
`PaletteAddr`). Game time does not depend on the frame rate: each frame advances the game
by the fields since the last one (`TempFrames`, at most 15), which the interrupt counts
(`FramesToDraw`, $aece).

### The frame

- The single-player main loop waits for a vertical blank by polling INTREQR bit 0
  (`btst #0,$1f(a6)` at $32fe; the other loops at $8e9e and $8efa). The copper list sets
  INTREQ bits 4 and 0 at the top of the field (`009c 8011` at $9a084) and clears them at
  line $10 (`009c 0011` at $9a24c). The slave's `_waitvbl` (`PL_PS` at $3e58) serves another
  loop.
- After the wait comes the swap of `drawPt`, then the frame is drawn. It shows at the
  next swap, at most once a field.
- The VBL handler is $415d8 (`is_Code` of the IntServer at $2ad0) and counts
  `FramesToDraw`. The keyboard handler is $3fefa (its struct at $2ae6). The music,
  `mt_music` $9b2fe and `mt_end` $9b2dc, is in chip hunk 3.
- Mouse control is the byte `PLR1MOUSE` at $5d82 (player 2's at $5d86), toggled by M in
  the key test at $401ee.
- The sky: `MAKEBACKROUT` ($1931c) copies the unrolled writer `fromback` into `backrout`
  ($18ffa-$1931a, entered at $19000), which draws the backdrop into the view each frame.
- The object pass `ObjDraw3` starts at about $21160; its object search is the loop at
  $211f0-$21234.

Where a frame's time goes is in [performance](performance.md).

### Renderer routines

The published source's names at their game offsets, found by `tools/srcmatch.py` (each
listed one matches its source instruction for instruction, or nearly; the full list is the
tool's output). These are the routines that write into the view, grouped as the plan's
writers.

| Writer | Routines (game offsets) |
|---|---|
| Walls | `itsawalldraw` $1d0b2, `CalcAndDraw` $1b660, `CurveDraw` $1b322 (curved walls), `screendivide` $1a592; strips `ScreenWallstripdraw` $1ca32 with `drawwallPACK0-2` $1ca80, $1ca9c, $1cab8 and `simplewallPACK0-2` $1cb10, $1cb3e, $1cb6e; see-through strips `ScreenWallstripdrawthru` $1cd24 with `drawwall[dim]thruPACK0-2` $1cd58-$1cdf0 and `maybeholePACK0-2` $1ce58, $1ce9e, $1cee6 |
| Floors and ceilings | `itsafloordraw` $1d440, `dofloor` $1f172, `dofloorGOUR` $1f21c, `FloorLine` $1f9fe; spans `backbefore`/`acrossscrn` $20f4c/$20f66, Gouraud `backbeforegour`/`acrossscrngour` $20fd2/$20ff4, water `texturedwater` $2107e with spans $21100/$21124; `SimpleFloorLine` $1f3d8, which patches `rts` into the unrolled fill `doacrossline` ($1f870) and calls it (the slave's `_p_flushjsr` at $1f452) |
| Bump-mapped floors | `BumpMap` $1fce2 with `OneBelow`-`TwelveBelow` $1fd4c-$20458 and `OneAbove`-`EightAbove` $2054a-$20956; smooth `SmoothMap` $20a0a with `OneBelowS`-`SevenBelowS` $20a4c-$20e58 |
| Objects | `DrawtheObject` $213cc, `glassobj` $2140e, `BitMapObj` $2174a, `PolygonObj` $21d06; textured polygons, drawn in columns: `dopoly` $220d2 (one brightness), `dopolyg` $22390 (Gouraud), `dopolyh` $22688 (with transparent texels); edges `putinlines` $228da |
| Gun | `DrawInGun` $57f4 |

Not yet looked for: anything else that writes into the copper lists (messages, the level
text, flashes); step 2 of the plan.

The CD32 version draws the same way, at other offsets: the small-view builder's loop at
$501c, the full-screen builder at $5206, keypad Enter at $404c2, and byte for byte `OneBelow` at
$1ffcc and the colour moves at $90fe.

The published AB3D I source (the 1997 Amiga Format cover CD, as
`Agrigaatti/Alien-Breed-3D-I` on GitHub) names these routines: the view's constants are
`widthOffset`, `rightclip` 96, `top` 80 and a centre x of 47. It is a development
tree, not this executable's build, so its labels are a map, not offsets: the table above
holds those found. It was released for personal use: read it in an ignored `tmp/`
(`tmp/ab3d1-src/`), never copy it into the repository.
