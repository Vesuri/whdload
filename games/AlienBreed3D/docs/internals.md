# Internals

Slave offsets are code-hunk offsets in `AlienBreed3D.slave` (the source's `Lxxxx`
labels). Game offsets are `resload_PatchSeg` offsets: the executable's hunks laid end to
end, as `tools/exe.py` writes them to `tmp/exe/abd.flat` (hunk 0, code and data, $0-$912d4;
chip hunks 1-3 from $912d4, $9b238, $9b250 to $ad9e8). Game offsets below are in the
$c4dc version.

## How it loads

A direct slave (WHDLoad 18, 68020 and AGA required): 576 KB chip (428 KB without
music) and $158000 bytes of ExpMem, so a 2 MB a1200 without fast memory cannot run it
("Can't allocate ExpMem"); the a1200-fast setup is the smallest that does. Ours asks for
$20a000 of ExpMem, whose top $b2000 is Enhanced resolution's area
([below](#the-1x1-palette)), and $27000 more chip (732 KB; 584 KB without music) for its
screens ([below](#the-1x1-display)), with the option off too.

- Stacks: SSP at ExpMem+$157e00, USP 1 KB below.
- Caches (`resload_SetCPU`): instruction and data cache on; on a 68040/060 also copyback for
  ExpMem and the slave, the store buffer, branch cache and superscalar dispatch; base
  memory stays non-cacheable.
- Interrupts: level 2 (keyboard, quit key, the game's PORTS server), level 3 (VBL reads
  the joypad, holding Reverse+Forward+Play 1 s quits; COPER calls the game's copper
  interrupt server), level 5,
  level 6 (CIA-B timer for the end part's HackAB3D music; not in the no-music slave).
- `team` (the Team 17 picture) is shown from chip $40000 for 4 s, through a copper list
  at $1000 (8 planes, FMODE $f). Psygore's list sets neither `BPLCON1`, `BPLCON2`,
  `BPLCON4` nor `DIWHIGH`, so they stay as the system left them; on a real A1200 (68040,
  MMU, Zorro III memory) the picture showed as blue garbage. Ours writes all four, with
  the system's values: `BPLCON4` $0011 (no bitplane XOR remaps the pens; sprites from pen
  16), `BPLCON2` $0024, `BPLCON1` 0, `DIWHIGH` $2100. The menu's list sets neither
  `BPLCON2` nor `BPLCON4` and its text is sprites: with `BPLCON2` 0 the picture covers it.
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

Ours adds, with CUSTOM5, to `_pl_v3` (a `PL_IFC5` block; the CD32 version's
`_pl_v2` gets the same, [mapped](#the-cd32-version)):

- `_p_loaded`, a `PL_PS` at $44aa4, the jsr to `LoadObjects` ($436d6, the last of the
  game's loads before the menu): the load, then the 1x1 palette ([below](#the-1x1-palette));
- `_p_coplists` at $4463e (`InitCopperScrn`, with a `PL_S` past both AllocMems to $44672):
  the two copper lists in the area instead of chip, and `PL_R` at $43c40, their FreeMem;
- `_p_cop1` at $31a0 (the level start's `COP1LC` = template, a `PL_S` past its last 4
  bytes): the new display's heads instead ([below](#the-1x1-display));
- `_p_show` at $32d2, $3e42 and $8e5e, each swap's `move.l d0,$dff084`: the finished frame
  onto the new screens.

Without `-DORIGINAL` the source assembles these; with it (`BUILD=original`), Psygore's
bytes. Outside the `PL_IFC5` block both slaves' lists patch the same offsets the same way
(`python3 -m amigaxdev.patchlist`, which stops at `PL_IFC5`), but for two fixes ours adds to
`_pl_v2` and `_pl_v3`, with or without CUSTOM5:

- `_p_waitvb` at the game's four field waits ($c4dc: $2830, $317a, $49020 and $490b4;
  $fd78: $2862, $3176, $49388 and $4941c; a `PL_S` past each one's 18 bytes). Each polls
  INTREQR for VERTB (`btst #5,$dff01f`) and then acks it, but the slave's `_level3` acks
  VERTB as soon as the interrupt is taken, so a poll sees the bit only if it happens to
  read it before the CPU takes the interrupt. On the emulated 28 MHz 68020 the no-music
  slave's never did: the title's fade-in ($49008) waited for ever on a black screen
  (Psygore's slave too). `_p_waitvb` waits for the next field's line 0 on the beam (V8 set,
  then clear), as `_waitvbl` does. The floppy version's (`_pl_v1`) are not patched: no
  archive holds it.
- The menu's fades ($49008 in, $4909c out; $48f98 scales each 8-bit channel by the step)
  wait there through `_p_waitfade`, which then waits for line $20 too: each step writes its
  colours' high and LOCT low moves into the menu's list, which loads them in its first
  lines. Writing from line 0 the CPU trailed the copper, which read most colours' old high
  and new low nibbles: off by 16 for a frame wherever a step carried into the high
  nibble, a speckle in the dark colours (the original's).
- The polygon objects' vertex divides ($c4dc: $21e44 and $21e46; $fd78: $220ca and $220cc),
  line-a words for `_t_linea` ([the 1x1 renderer](#the-1x1-renderer)): a vertex close beside
  the eye overflowed `divs.w`, and a face lay across the view, one flat colour a row. Not in
  `_pl_v1`: no archive holds the floppy version.

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
32-pixel bank boundary (the BPLCON3 move), and 416 bytes a line (1188 with the
option on, [below](#the-lines)). The plain floor span,
`acrossscrn` at $20f66, is typical: a texel byte, `(a0,d5.w*4)`, indexes a word shade
table, `(a1,d0.w*2)`, the word goes to `(a3)` and `a3` steps 4, with the extra 4 every
32 pixels. The textures carry their own colours: a wall file is 32 rows of 32 12-bit
colour words (2048 bytes) ahead of its texels, three 5-bit texels a word (the source's
`walltiles`, `PaletteAddr` and `ChunkAddr`); a brightness of 0-64 picks the row through the
source's `SCALE` table, two levels a row. Game time does not depend on the frame rate: each frame advances the game
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
| Floors and ceilings | `itsafloordraw` $1d440, `dofloor` $1f172, `dofloorGOUR` $1f21c, `FloorLine` $1f9fc; spans `backbefore`/`acrossscrn` $20f4c/$20f66, Gouraud `backbeforegour`/`acrossscrngour` $20fd0/$20ff4, water `texturedwater` $2107e with spans $21100/$21124; `SimpleFloorLine` $1f3d8, which patches `rts` into the unrolled fill `doacrossline` ($1f870) and calls it (the slave's `_p_flushjsr` at $1f452) |
| Bump-mapped floors | `BumpMap` $1fce0 with `OneBelow`-`TwelveBelow` $1fd4c-$20458 and `OneAbove`-`EightAbove` $2054a-$20956; smooth `SmoothMap` $20a0a with `OneBelowS`-`SevenBelowS` $20a4c-$20e58 |
| Objects | `DrawtheObject` $213cc, `glassobj` $2140e, `BitMapObj` $21748, `PolygonObj` $21d06; textured polygons, drawn in columns: `dopoly` $220d2 (one brightness), `dopolyg` $22390 (Gouraud), `dopolyh` $22688 (with transparent texels); edges `putinlines` $228da |
| Gun | `DrawInGun` $57f4 |

The rest of what writes into the view is in the [inventory](#display-inventory).

The CD32 version draws the same way, at other offsets: the small-view builder's loop at
$501c, the full-screen builder at $5206, keypad Enter at $404c2, and byte for byte `OneBelow` at
$1ffcc and the colour moves at $90fe.

### The CD32 version

Enhanced resolution is written for the $c4dc version and carried to the CD32 one ($fd78)
by mapping each offset (plan step 9). `tools/port.py` finds a $c4dc offset in the CD32
image by the bytes around it (relocated longs masked), or as the n-th of n equal places,
or from a neighbour with the same bytes between; data by the code that references it. Its
`check` maps every site the option uses (the `PL_IFC5` block, `stride.s`, `sites.s`,
`port.s`'s offsets and the tables of offsets in `display.s` and `hires.s`: 691) and compares the bytes each patch
replaces; `make check` runs it. `port.py gen` writes from the $c4dc sources:

- `src/cd32.s`, `_pl_v2`'s `PL_IFC5` block: `_pl_v3`'s with every offset mapped and
  `stride.s` inline;
- `src/cd32segs.s`, segments of (a $c4dc start, its distance to the CD32 offset), one where
  the distance changes (18).

The code reads its game offsets from `_gofs` (`src/port.s`, one entry a `G_` name, the
$c4dc value). When the slave picks `_pl_v2`, `_port` translates them through the segments,
and with them the tables of offsets (`_ds_stridetabs`, `_t_ptrs`, `_t_penptrs`,
`_t_halve`) and the geometry sites (`_ds_sites`), once, before the game starts.

Two differences are not offsets, and `_pl_v2` has them by hand:

- the wall files' table (`wallchunkdata`, $42d52): (name, unpacked size, packed size), 12
  bytes an entry where the $c4dc one has 8 (`_gwall`, which `_port` sets to 12);
- the level start points COP1LC at the template a second time, after the CD audio starts
  ($31ec): a `PL_S` past it, or it shows the game's template over the heads (black).

Its textured polygons' textures and their palette (`TextureMaps`, `TexturePal`) differ
from the $c4dc version's; the palette is built from what is loaded either way.

The published AB3D I source (the 1997 Amiga Format cover CD, as
`Agrigaatti/Alien-Breed-3D-I` on GitHub) names these routines: the view's constants are
`widthOffset`, `rightclip` 96, `top` 80 and a centre x of 47. It is a development
tree, not this executable's build, so its labels are a map, not offsets: the table above
holds those found. It was released for personal use: read it in an ignored `tmp/`
(`tmp/ab3d1-src/`), never copy it into the repository.

### Display inventory

Read from the running game with `ab3d.py copper` in level 1 on the a1200-030, both views
(plan step 2). The offsets are in chip hunk 1.

**The template**, from $9a07c, is the start of every field:

| Offset | Moves | What |
|---|---|---|
| $9a080-$9a098 | DMACON $8020, INTREQ $8011 (the frame wait's flag), FMODE $000f, DIW and DDF | the window: small $2cb1-$2c91, DDF $48-$88; full $2c81-$2cc1, DDF $38-$b8 |
| $9a09c-$9a120 | BPLCON3 $0000 then $0200, COLOR00-15 | bank 0's pens 0-15, both nibbles: the frame sprites' colours (`borderpal`) |
| $9a124-$9a160 | SPR0-7PT | small view: the frame, sprites 0-3 at $912dc + n * 2592 (64 wide, 160 lines from line $34; 0+1 and 2+3 attached); full screen and sprites 4-7: the null sprite $912d4 |
| $9a164-$9a1ec | BPLCON3 $0c42, the same 32 colour moves again | |
| $9a1f0-$9a1fe | BPLCON3 $8c42, COLOR00 at $9a1f4; BPLCON3 $0c42, COLOR00 at $9a1fc | the damage flash: pens 128 and 0 (the source's `hitcol2`, `hitcol`, value words $9a1f6 and $9a1fe) |
| $9a200-$9a244 | BPLCON0 $7201, BPLCON1, the modulos (-24 small, -40 full), BPL1-7PT | 7 planes of the static pattern |
| $9a248-$9a254 | WAIT line $10, INTREQ $0011, WAIT $2a11, COPJMP2 | into the view list `oldDrawPt` |

**The view list** (two, `drawPt` and `oldDrawPt`, 80 lines of 416 bytes, then a tail):

- Each line: BPLCON4 $0000 or $8000, then three banks of 32 COLOR moves. Even lines'
  moves go to banks 5-7 (BPLCON3 $ac42, $cc42, $ec42), odd lines' to banks 1-3 ($2c42,
  $4c42, $6c42). `fromPt`
  ($5dd48) is the first colour word, drawPt+10. `midpt` ($1d256) is fromPt + 40 lines.
- Then, in the small view, BPLCON3 $0c42 and COLOR15 from the line's word of `HealthPal`
  ($93f5c, 80 words: green to yellow to red), the colour of the vitality and ammunition bars.
  In full screen, two WAITs (from $29df and $2b01, $300 on each line) hold each line for
  three rasters.
- The tail at line 80: BPLCON3 $0c42, COP1LC = the panel list $9a262, COPJMP1.
- The bitplane pattern gives the small view pens 32-127, two pixels each ($9af18). It gives
  full screen pens 32-127, three pixels each, between 16 pixels of pen 0 at each side ($9add8).

**The panel** ($9a262, small view only): COP1LC back to the template, two NOPs (in full
screen the list ends here: BPLCON0 0 and end, written at $9a26a by the builders), BPLCON4 0, then
all 256 colours in both nibbles (512 moves), 8 planes and the panel's window.

**Pens on the view's lines in the small view.** The view shows banks 1-3 or 5-7: 96 colour
registers rewritten every line, 192 in all. The frame is two attached sprite pairs, and
BPLCON4's sprite bits are 0, so they draw with pens 1-15 of bank 0. They use all 15: the
pixel data of both sides was decoded. Pen 15 is the bars' colour, rewritten every view
line from `HealthPal`. Pen 0 is the border colour and the flash. Pens 16-31 and 129-159
show nothing.

**Everything that writes into the view**, by the source's names (game offsets; the
renderer's own writers are in the table above). Readers of `drawPt`, `oldDrawPt` and
`fromPt` were found by disassembly, and the baseline's profiles have no other PC with chip
time in the view's scenes:

| What | Routine | Effect |
|---|---|---|
| Builders | `InitCopperScrn` $4463e (allocates both lists, 33296 bytes of chip each, fills them with NOPs, writes the tail), small view $5134, full screen $534e, colour moves $8f3a | the list's structure; called at level start and by keypad Enter ($40258, $40262, $41068, $41072, $446d0) |
| Sky | `backrout` $18ffa (written by `MAKEBACKROUT` $1931c), fromPt at $19356 | the backdrop above the horizon, each frame before the walls |
| Walls, floors, bump, objects | see [Renderer routines](#renderer-routines); `pstit` $1a3ac, `outofcalc` $1a616, `pastsides` $1daac, `glassobj` $2153e, `objfitsonbot` $2194c, `dontusegour` $2202e take fromPt | the frame's pixels |
| Glass | `glassobj` $2140e | reads the pixels behind and rewrites them through a table |
| Light beams | `LightDraw` $8aa6 (a zone's light-beam element, called from $6dda) | rewrites every pixel of a column span through `brightentab` (brighter) |
| Gun | `DrawInGun` $57f4, `DrawChunk` $5858 | the gun, last, over the bottom lines |
| Water | $68e4 (after `noGunLook`, flag byte $6534) | head under water: `and.w #$ff` on every pixel of lines 0-79, or 40-79 half under, which leaves green and blue |
| Pause | `PAUSEOPTS` $3e0c, `DRAWPAUSESCRN` $41b2, `DRAWPAUSEBLOCK` $41e8 | halves the shown frame's brightness (`and #$eee`, `lsr`) into the other list, draws the option text in a 12x10 grid of 8x8 letters, and swaps |
| Damage flash | `USEPLR1` $5694, `USEPLR2` $590e set $f00; the main loop at $321e takes $100 off each frame; cleared at level start $312a | COLOR00 of banks 0 and 4: the border, and full screen's 16-pixel side strips |
| Bars | `EnergyBar` $8c46 and the ammunition bar, `FullEnergy` $8c02 | the frame sprites' data (pen 15 rows), not the view |

Not in the view: the level text is its own text screen before the level, and the panel's
picture is in its own planes. At death or level end, `quitGame` ($8e1c) swaps once, then
waits for the tune with the last frame shown ($8e9e, $8efa). Its exit to the menu ($9acf4)
frees the panel's planes (chip, where the menu then loads 64 KB) but sets the blank list
only for the next field, so a load while the beam was above the panel showed that data in
the panel's top rows for a field; `_p_setcop2` (at $9ad00, outside ORIGINAL) also jumps
the copper to the blank list at once.

### The 1x1 palette

Enhanced resolution's palette and pen tables (plan step 3, `src/palette.s`; the method is
in the [plan](resolution-plan.md#colour)). `_p_loaded` builds them once into the area,
the top $b2000 of ExpMem (ExpMem+$158000, above the stacks). Everything the view can show comes
from these shade tables (game offsets; a table's rows are brightness, row 0 the brightest):

| Table | Where | Shape | Texel counts from |
|---|---|---|---|
| Walls | `walltiles` $42a66, a pointer to each loaded wall file; `wallchunkdata` $42b06, (name, unpacked size) pairs ended by zeros | 32 rows of 32 | the file after its 2048 bytes of colours |
| Floors and ceilings | `floorScaleCols` $536e6 | 15 rows of 256 | the texture at `floortile` $55cee (a pointer), 64 KB |
| Textured polygons | `TexturePal` $3e066 | 15 rows of 256 | `TextureMaps` $2e066, 64 KB |
| Objects | `Objects` $2974a, 18 entries of (wad, ptr, frames, pal) | a pal is 15 rows of 32 | none; the gun (entry 9) draws from its pal's first row only (`DrawInGun`) |
| Sky | `BackPicture` $55d00 | 16416 words | none |
| Water, light beams | `brightentab` $766d2 | 5632 words: `texturedwater` reads 13 rows of 256 by distance and texel, `LightDraw` indexes it by colour | the water's `waterfile` $812d2, 64 KB |

The area, by offset from its start:

| Offset | Bytes | What |
|---|---|---|
| 0 | 2 | pens built (240) |
| 2 | 2 | state: 2 when done; $11-$17 while building, the step |
| 4 | 480 | pen 16 + k's 12-bit colour, k = 0-239 |
| 512 | 4096 | each 12-bit colour's pen |
| 4608, 4864, 5120 | 256 each | pen to pen: light beams (`brightentab` by colour), the water tint (red removed), the pause screen (half brightness); pens 0-15 to themselves |
| 5376 | 14 x 1024 | the walls' tables in pens (a wall not loaded stays 0) |
| 19712, 23552 | 3840 each | floors and ceilings, textured polygons |
| 27392 | 18 x 480 | each `Objects` entry's pal |
| 36032 | 16416 | the sky |
| 52448 | 5632 | `brightentab` |
| 58080 | to 156412 | the build's scratch (histogram, every colour's CIELAB, the sorted pens, a table of squares), free once the build is done |
| 58080 | 69120 + 16 | after the build: the display's chunky buffer, 288x240 pens at most ([below](#the-1x1-display)) |
| 127216 | 144 | the c2p's scratch, half a row |
| 127360 | 8 | the frame last shown's stride, width and height, for the tools |
| 127368 | to 136912 | the 1x1 renderer's tables, built at each level's load ([below](#the-1x1-renderer)): the slots of 288 columns, 241 line offsets, `doacrossline`, the polygons' column edges, the floors' line edges |
| 156416 | 2 x 286308 | the game's two copper lists (`InitCopperScrn`, allocated in chip by the original; [241 lines of 1188 bytes](#the-lines)), to 729032 |

### The lines

With the option on, the game's lists have lines of 1188 bytes (`DS_STRIDE`, 9 banks of
32 pixels) instead of 416, the same in both views, so that the renderer can draw 288
pixels a line (plan step 6), on 241 lines. Every place that steps a whole number of
lines is patched to the same number of lines of `DS_STRIDE`:

- `src/stride.s`, generated by `tools/sites.py` from the step 5 site analysis: 404 row
  steps, unrolled displacements and line offsets as `PL_W` and `PL_L` of the CUSTOM5
  patch list, each `k*DS_STRIDE`. Not `midpt` (fromPt + 40 lines, $32e8 and $3e58):
  nothing reads it, and the slave's `_waitvbl` jsr is at $3e58. The sky's unrolled
  displacements (38 lines) do not fit a signed word at 1188, but the game's sky is not
  drawn there (ours is); a `VASM_EXTRA=-DLORES` build, which draws it, keeps lines of 800.
- `src/AlienBreed3D.s`: the gun's `muls.w #416` at $5828, the water tint's first line at
  $690e, the sky's `adda.w #416` at $1935c.
- `_ds_stride` (`src/display.s`, at the load): the row tables `timeslarge` ($1cbe2,
  $1cf6a; walls, line y + 1) and the polygons' ($22214, $224b6, $2276e; 90 entries).

What differs between the views is a table of sites, `_ds_sites` (`src/sites.s`, also
generated by `tools/sites.py`), each with the game offset of its field and a value for
each view, which `_ds_geom` writes into the game's code at each switch. A build with
`VASM_EXTRA=-DLORES` leaves the 1x1 renderer out: both views take the 96x80 values and the
frames are identical to the original's (`tools/display.sh`).

### The 1x1 renderer

Both views are drawn by the game's own writers at S times the original's 96x80 in both
directions (plan steps 5 and 6, `src/hires.s`): the small view at 192x160 (S = 2), full
screen at 288x240 (S = 3), with the original's field of view. `_ds_geom` sets S with the
sites at each switch. The projection is x = X * 128 / Z + 47 and y = (H - eye) / Z + 40
(internals of each writer differ in their scales); at S:

- **Sites** (61, `src/sites.s`): the centres (47 to 95 and 143, 40 to 80 and 120, 39 to
  79 and 119, 41 to 81 and 121), the clips (`rightclip` 96 to 192 and 288, the bottom 79
  to 159 and 239, 95 to 191 and 287), the floors' `muls #64` to `#128` and `#192` and
  their first line ($1dab4, 41 lines to 81 and 121). Each is linear in S, so the 288x240
  value is twice the 192x160 one less the original's.
- **Times S in code**, where the game has a shift that cannot multiply by 3: the points'
  and objects' X (`asl.l #7`, $84aa and $8a76: `_t_x128`), the polygon objects' vertices
  ($21dd6: `_t_pvert`), and heights above or below the eye after the eye is subtracted
  (scaling before it would scale the eye too): a wall's top and bottom ($1d13a, $1d146,
  and the curved walls' $1b3b0, $1b3b6), and the glass, bitmaps and polygon objects'
  heights and zone clips ($2142e-$21e28).
- **Divided by S**: FloorLine's steps across a span (`asr.l #6`, $1fb96 and $1fbc4), a
  wall strip's texture step (from the same start), and glass and bitmaps' index into the
  linear step table ($214dc, $214f6, $218f8, $21914). At S = 3 with `divs.l #3`.
- **Walls**: a column's slot for any x ($1a616, $1a3ac, over `XTOCOPX`), a strip's line
  for any y ($1cb8a, $1cf18, over `timeslarge`).
- **Floors**: FloorLine's split of a span at the bank boundaries ($1fbf6, unrolled for 3
  banks in the game) for any number; its fills already continue a bank at a time.
  SimpleFloorLine's unrolled `doacrossline` ($1f870, 96 moves; an rts is written at the
  span's end) is 288 moves in the area. The polygons' per-line edges (`leftsidetab`,
  `rightsidetab`, `leftbrighttab`, `rightbrighttab`, 180 lines each from $1db5a, too few
  for 240) are 256 lines each in the area, at every reference ($1d65e-$1f356).
- **Objects and polygons**: the slot and line tables they index ($21b74, $22214) are 288
  and 241 entries in the area; the polygons' line lookups ($221c6, $2271c, $22466) are
  computed. Glass and bitmaps scale their half sizes after the divide (`_t_size`, $2149a,
  $21884: an 8-bit size shifted 8 would be negative in the word). One so close that its
  width or height would not fit the game's words is dropped (a wrapped width ran the
  column loop on through memory). The polygons' edge buffers (8 bytes a column, the top
  1536 bytes before the bottom at $28b46 and $29146) are in the area, 300 columns apart:
  the fillers write one column past the right clip, which at 192 columns was the bottom's
  column 0 and the objects' graphics table at $2974a (aliens, corpses and blood then drew
  from address 2).
- **The projections' divides**: 24 `divs.w Dz,Dn` before a centre's `addi.w` (a point's x
  at $84de, a wall's ends, top and bottom at $1b464-$1b4d4 and $1b682-$1b69c, the floors at
  $1d5ec-$1d892, glass and bitmaps at $21434-$21870, the polygon objects' vertices at
  $21e44 and $21e46, these two in both displays: [above](#slave-patches)) put x / z or a
  height / z in a word. Close to the eye the quotient overflows, and `divs.w` then leaves
  Dn as it was: the original drops or misdraws such a wall. Ours scales x and the heights
  by S, so it happened at S times the distance: a wall close by not drawn, the sky (drawn
  first) and the list's two-frame-old pixels showing in its place, flickering between the
  lists. A polygon object beside the eye, its nearest vertices at z 1 or 2, took x's low
  word for x / z and put them across the view, a face filling the view's middle with one
  colour a row (the original's too: level 1's storage room, left after the first door,
  player 1 at x -1529, z 1823, angle 2122: object 49, vector object 7, vertices at x -99078
  to -105211, z 1 and 2, on screen at x 32089 and 25956). Each is a line-a word, $a000 | n
  << 9 | z (`PL_W`), and `_t_linea` (the vector $28, `WHDLF_EmulLineA`; set at the
  version's check, before the game starts) divides in 32 bits, the quotient held to +-16383
  so the centre's add cannot wrap; Dn's upper word the remainder, so where `divs.w` does
  not overflow the result is its own. Turning in level 1's start: 33268 unwritten pixels to
  134 (small view), 19293 to 2717 (full screen; `ab3d.py holes`, `-DHOLES`).
- **Ours, S x S**: the gun (`DrawInGun` $5826, a fixed-size image) and the sky ($1933e, 96
  of its 432 columns, as the original's field of view; with pen bytes a line a texel row,
  each texel's S pens in one word or long from `DA_SKYTAB`, then the line copied S - 1
  times), a column at a time from their images, each texel at the slots of its S pixels (at S = 3 a texel can span a 32-pixel
  bank boundary); the pause screen's letters ($41b2; its dimmed frame at 1x1); the water
  tint over the view ($6900).
- The list's line 0 is drawn by no writer, as in the original (black there); `_ds_one`
  shows it black, since the builders' moves are in it.

Lines the original leaves undrawn: one-line gaps along floor and ceiling steps' edges,
where a wall strip ends a line short of the floor or ceiling that meets it (the strip
draws the lines after its top `d5` down to its bottom, the floor its first line to the
line before its last; each rounds its own projection). At S times the lines the gap is up
to S - 1 lines, so `_t_stripw` (the PL_PS at $1cb8a, solid strips only) makes a strip S - 1
lines longer at both ends within the zone's clip lines (`topclip`, `botclip`, $1d270
and $1d272), the texture continuing (its row is linear in the start line). Unwritten
pixels on level 1's walk (`ab3d.py holes`, `-DHOLES`, a1200-030): 10634 in 209 of 1304
frames to 119 in 5 (192x160), 33269 in 956 of 1009 to 3 in 2 (288x240). The original
display keeps its gaps (on the walk 3500 pixels in 351 frames of the small view, 224 in
200 of full screen's).

### Pen bytes

The release build (`PENS`, plan step 7's first stage; `-DWORDS` builds the colour-word
lists of steps 5 and 6, which the next section describes): the game's writers write pen
bytes straight into the lists, and the convert (`_ds_one`) is gone. A list's pixel x is at
`fromPt` + x (no banks; `DA_SLOT` is linear), lines of 288 bytes in both views, from 2
bytes into the list so that `fromPt` is long-aligned for the c2p, which reads the list
itself (`DA_INFO`'s pens pointer and row stride). `_p_show` fills line 0, which no writer
draws, with black's pen (pen 0 is the border, which the damage flash turns red).

- **Stores**: each `move.w (table),(a3)` becomes `move.b` from a table of pens, and each
  `addq.w #4` after it `#1` (walls $1ca8c-$1cefe, bitmaps $21a18-$21a6c, polygons $221dc-$22752; the list in
  `src/AlienBreed3D.s`). Glass ($215fc-$2165c) and light beams ($8aea) are patched too,
  though no level is seen to draw them.
- **The frame flag**: with the option the main loop no longer waits for the game's frame
  flag after a frame ($32fe, `PL_S`): `_p_show` paces the switches (one a field at most,
  into a screen no longer shown), and the game times its moves itself.
- **Wall strips** ($1caf4, $1cbd4, after the game's `cmpi.b` of the packing, whose flags
  choose the loop): ours (`_t_wsimple`, `_t_wdraw`), 8 pixels a pass at displacements
  k * `DS_STRIDE`, entered at the pixel that leaves whole passes; each pass is under the
  020/030's 256-byte instruction cache. Magnified, a pixel is 3 instructions while its
  texel holds, the texel reloaded inline (`bcc.s *+n`).
- **Spans**: the floors', Gouraud floors' and water's span loops ($20f52-$20f7c,
  $20fe0-$21014, $2110a-$2113e, two of each, whose branches choose the next step by the x
  error's carry) store with `move.b (a1,d0.w),(a3)+`, one instruction in place of the
  store and the `addq`. Rewritten in place: each loop is a word shorter, its branches are
  retargeted, and a `nop` past each pair takes the spare word, so every entry stays where
  it was.
- **Tables**: the walls' through `_t_wallpal` (`PA_WALLS`, 32 rows of 32 pens a wall); the
  objects' pal pointers ($2974a + 12) to `PA_OBJS`; the sky through `PA_SKY`, the water
  tint through `PA_TINT`, the pause screen through `PA_MAP` and `PA_PAUSE`; the
  SimpleFloorLine colours ($1f46c) and its black ($1f3d5) as pens.
- **Floor and polygon rows**: the floors' and textured polygons' shade rows, 15 of 256 in
  the game, are read past row 14 when far away (into whatever follows `floorScaleCols`
  and `TexturePal`). `_t_pens` copies 24 rows of each, the game's memory as it is,
  through `PA_MAP` into the area (`DA_FLOOR`, `DA_POLY`), so the pens match the reference
  build there too.
- **Water** (`texturedwater` $2107e): the reflection's index is the water texel's high byte
  and the reflected pixel's low byte, into `brightentab`. Its table (`DA_WATER`, 22 rows of
  256) is the pen of `brightentab`'s colour for the low byte of each pen's colour (the
  words build reads the exact colour word on screen, which can be a colour the palette
  does not hold). The main loop advances its animation and scroll every frame drawn
  ($3338-$3376), so builds of different speed show it at different phases;
  `-DWATERFREEZE` stops them for comparing. Its far row is clamped at 12 by a signed compare,
  where the original's doubled distance turns negative from $4000 and reads before
  `brightentab`.
- **Halved**: four tables of brightness row offsets into the colour tables ($1a4f0,
  $1a772, $1faae, $217ca), halved once by `_t_pens`: a row of pens is half a row of
  words.

`tools/pencheck.sh` grabs still frames of each build's pens (`ab3d.py chunky`) at level
starts and 40 fields in, turned 8 times in both views, and `tools/pendiff.py` compares two
runs (the release against `BUILD=words`). With `-DHOLES=2` in both (holes filled with pen 16, black, which the palette maps
exactly) levels 1 and 2 are equal; level 3 too with `-DWATERFREEZE` in both, but for 1-8
pixels in 6 of its frames, at x = 96, 160 and 256 (the words build's bank seams); level
4's aliens move differently between the builds' timings.

### The 1x1 display

Enhanced resolution's display (plan step 4, `src/display.s`, with Kalms' c2p in
`src/c2p.s`), as built with `-DWORDS` or LORES (the release build's lists hold pens, which
the c2p reads in place: [Pen bytes](#pen-bytes)). The renderer draws its frame of colour words, 192x160 or 288x240 (96x80
with LORES), into its two copper lists, which are now in the area and never shown. At
each swap (`_p_show`; the main loop $32d2, the pause screen $3e42, `quitGame` $8e5e) the
finished list (the new `oldDrawPt`) is converted through the palette's map to pens into
the chunky buffer (`_ds_one`, 1x1; with LORES 2x2 or 3x3), then a row at a time through
`c2p1x1_8_c5_030_2` into the back screen (with pen bytes, below a 68040, full screen's
frame in one call), and shown from the next field by writing that
screen's head to `COP1LCL`.

- **Chip**, above the slave's chip pool ($90000, or $6b000 without music): two screens of
  76800 bytes, 8 planes in one of three layouts: the small view's rows of 24 bytes (160
  rows), full screen's of 36 (240 rows) below a 68040, of 40 (320 pixels) from the 68040
  on; then two copper heads of $800, to $b6800 ($91800). Only `COP1LCL` is
  switched, so the heads share a high word (an assembly check).
- **A head**: DMACON $8020, INTREQ $8013 (the game's frame flag and COPER as the template
  sets them, and DSKBLK, ours), FMODE $000f ($000d for full screen's 36-byte rows), the template's window and fetch, pens 0-15
  (both nibbles) and sprite pointers copied from the template, the 240 pens (12-bit, LOCT
  clear) in banks 0-7, COLOR00 = the damage flash (`hitcol`, copied each frame), BPLCON0
  $0211, BPLCON1, BPLCON4 0, the modulos, 8 plane pointers, WAIT $10 and INTREQ $0011.
  Then in the small view pen 15 from `HealthPal` at the end of lines $2b, $2d, ... (the
  bars), and both views jump into the game's panel list ($9a262) through `COP2LC` and
  `COPJMP2`, whose `COP1LC` words (set at the level start, $2ea6) `_p_cop1` and each
  switch point at the head shown. So `COP1LC` only ever holds a head's address: with the
  jump through `COP1LC`, a switch's `COP1LCL` write between the head's `COP1LC` = panel and
  its `COPJMP1` sent the copper into the game's data, a garbled screen for the rest of the
  level (seen on every CPU after minutes of play).
- **Small view**: the template's window and fetch (DIW $2cb1-$2c91, DDF $48-$88), rows
  of 192 pixels (modulo 0), BPLCON1 0. The panel's list from the end of line $c9 (WAIT
  $c9df), right after the last bar, where the game's view list reaches it: chunky row 79
  is never shown, as in the original. On line $ca the panel's list rewrites the frame
  sprites' colours, and the original's view list, paced by its moves (it has no WAITs),
  reaches it at a time no WAIT matches: 88 pixels of the frame sprites on that line differ
  (`tools/display.py` leaves the line out).
- **Full screen**: DIW $2c81-$2cc1, DDF $38-$b8: 320 pixels at FMODE 3, 288 at FMODE 1
  (32-pixel fetches), both modulo 0. Below a 68040 the rows are 36 bytes, so the frame
  is one run per plane and the c2p converts it in one call; a 68040's c2p is bound by
  its Chip writes and FMODE 1 takes twice the display's slots, so from the 68040 on they
  are 40 bytes at FMODE 3, converted a row at a time (`_ds_wide`). The game's pattern has its 288 pixels 16
  in from the left, so BPLCON1 $4400 delays the planes 16 pixels and pen 0 (the border)
  shows on either side, as in the original. The game's full-screen rows are 3 rasters from
  line $2b and its list turns the display off at $118, so the planes start one row in and
  the head waits for $118: rows 0-78 shown, as in the original.
- **The field flag**: the copper sets INTREQ DSKBLK at the top of each field, and no
  interrupt is enabled for it. A switch clears it after writing `COP1LCL`, and the next
  frame waits until it is set again (or about two fields) before converting into the other
  screen, which by then is no longer shown.
- **Keypad Enter**: each head remembers the view it was built for, and the back head is
  rebuilt from the template when the view differs.
- `_p_cop1` fills both lists with black's pen, clears both screens and builds both heads
  at each level start: the first swap hands over a list no frame was drawn in yet.
- **The builders**: the view switches ($5134 small, $534e full screen, at the level start
  and at keypad Enter, which calls them as soon as the key is read, within a frame) write
  each line's copper moves into both lists; in pen lists those are pixels, over the frame
  being drawn and the one shown next (striped garbage for a frame or two, and the level's
  first frame). Their loops are skipped (`PL_S` $5178 and $5392); the template writes
  around them stay.
- Pixels that flicker every other frame while standing still (level 1, seen on the
  a1200-030) are the game's own: the original slave shows them too, and the frames ours
  shows equal the renderer's (`HOLES` finds no unwritten pixel).
