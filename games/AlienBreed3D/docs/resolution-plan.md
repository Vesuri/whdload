# Enhanced resolution plan

The goal (decided 26.11.2026): replace the copper chunky view with real 1x1 pixels in both
views, behind one option, and make both run as fast as possible: there is no fixed frame
rate to reach, the work goes on while measured gains remain.

- **Enhanced resolution**, CUSTOM5 (`C5:B:Enhanced resolution`; CUSTOM1-4 are the
  original's). Off, the game is the original byte for byte.
- The small view becomes 192x160 at 1x1 (4x the original's 96x80 pixels), full screen
  288x240 at 1x1 (9x), the original's size and field of view (decided, for now). Keypad
  Enter still switches between them.
- Both are bitplane screens (8 planes) fed by a Kalms c2p from a chunky buffer in fast
  memory, replacing the copper chunky lists.

How the original draws is in [internals](internals.md#display). The rest of this doc is
the design and the steps, in order.

## Design

### Screens

- Two chip screens of 8 planes of 240 rows of 40 bytes (76800 bytes each; built at step 4).
  A row is 320 pixels, the full view's fetch at FMODE 3, which needs whole 64-pixel
  fetches: full screen shows 288 of them, delayed 16 pixels by BPLCON1 to where the
  original has its view, and the small view 192 (modulo 16). Double-buffered: the c2p
  writes one while the other shows, and `COP1LCL` switches between their copper heads,
  taking effect at the next vertical blank.
- The slave builds the copper heads: bitplane pointers, each view's window and modulos
  (the template's), the palette, and in the small view the original's sprites (the frame)
  and pen 15 a line pair (the bars), then the game's own panel list below the view
  ([internals](internals.md#the-1x1-display)).
- The panel loads all 256 colours at its split, so the view's palette is loaded again
  every field above the view, in the vertical blank. 256 MOVEs with LOCT clear set both
  nibbles (12-bit) in about 4.7 raster lines; 24-bit needs 512 and about 9.4 (DERIVED: a
  MOVE is 4 memory cycles, 227 a line).
- The c2p converts only the view rectangle, a row at a time (as AmigaXDev's Kalms
  rectangle adapter does), so full screen's rows convert 288 pixels, not 320.

### Colour

The original shows each pixel in its own 12-bit colour, so there is no palette to keep.
Every texture brings its own shade table (a wall: 32 colours at 33 brightness levels),
so the view can show thousands of colours. The 1x1 modes:

- One fixed palette for both views, built once when the game has loaded its tables, and
  every shade table remapped to pen bytes then (`src/palette.s`). The renderer still does
  the original's one table read a pixel and writes the byte. No colour is chosen while a
  frame is drawn.
- The palette (decided at step 3, from the census below): an integer histogram of every
  shade-table entry the game can show. Each class has its share (walls 45, floors 30,
  objects 8, gun 5, polygons 4, water 3, sky 2), each table an equal part of it, each
  brightness row (R - r)^2 (row 0 the brightest), each entry its texel count. The 200
  heaviest colours are pens. Then 40 more, each the colour with weight farthest in
  CIELAB from the pens so far, which keeps rare colours near a pen. Every 12-bit colour
  takes its nearest pen in CIELAB. The pens are 12-bit colours, so the copper loads them as
  the original's moves do. The pens are 16-255, 240, in both views: the extra 15 of full
  screen gain about 0.5% of pixels shown exactly, not worth a second set of tables.
- The free pens: in the small view 240. The frame's two attached sprite pairs use all of
  pens 1-15 (pen 15 changes every line, the bars' gradient), and pen 0 is the border and the
  damage flash. BPLCON4 can move that block of 16 but not shrink it. In full screen there
  are no sprites, so 255 (all but pen 0). The panel needs none, because it loads its own.
- The effects that rewrite pixels' colours need pen-space versions, which the build makes
  as 256-byte pen-to-pen tables: light beams (`brightentab` by colour), the water tint (red
  removed, on all lines or the bottom half) and the pause screen's half brightness. Glass
  also reads pixels through a table, not yet identified (step 5). The damage flash stays
  the border's pen 0.
- The palette is computed in the slave at run time, never kept as a file: it is derived
  from the game's data, which the repository must not hold.
- No dithering: the census found no banding to fix (below).

The census (step 3; `tools/census.sh`, `tools/colours.py census`) grabbed 14551 frames
over all 16 levels, walking and fighting. They show 491 distinct colours, at most 220 in
one level, all of them colours the static tables can produce (1744 in all). Over those
frames' pixels:

| Palette (240 pens) | Shown exactly | Mean delta E | Over 2.3 | Brightness steps kept | Max delta E |
|---|---|---|---|---|---|
| The slave's | 99.3% (worst level 97.9%) | 0.06 | 0.7% | 99.8% | 18.5 |
| Wu's quantiser, each box's heaviest colour | 98.6% | 0.14 | 1.4% | 99.3% | 35.9 |
| The same, dithered in pairs | 98.6% | 0.11 | 1.4% | 99.6% | 23.4 |
| Wu, boxes' means (24-bit) | 55.3% | 0.41 | 3.2% | 99.4% | 22.0 |
| A 6x8x5 RGB cube | 9.9% | 13.75 | 90.1% | 41.3% | 34.6 |
| Wu on each level's own frames (a palette a level) | 100% | 0.00 | 0% | | 0.0 |

A palette per level would show every pixel exactly, but needs the level's colours, which
only parsing the level would give: 0.7% of pixels, mostly within one 12-bit step, is not
worth that now. A pen cache filled while drawing was dropped: what it would need cannot be
measured from frames, and it puts a colour choice in the drawing. k-means refinement, a
CIELAB metric's alternatives (redmean, YUV, RGB) and the frame sprites' 14 pens as fixed
entries measured no better.

HAM8 is out: AmigaXDev's two HAM8 converters are 68040-only, and both trade away horizontal
resolution.

### Renderer

- First (step 5, decided 26.11.2026) the game's own writers draw the 1x1 views: their
  geometry is patched to the new size (the immediates in `_ds_sites`, the row and column
  addressing, the heights' and texture steps' scale), and they still write colour words
  into the copper-slot layout, which the display converts to pens. Only the gun, the sky
  and the water tint, which draw from fixed-size images, have 2x2 writers of our own.
  This makes the new resolution playable early and leaves the faster writers below to
  step 7.
- Then one new pixel writer for each of the original's: wall strips, floor and ceiling spans,
  bump-mapped floors, objects (bitmaps, glass, textured polygons plain, Gouraud and with
  holes), the gun, and whatever else step 2 finds writing into the view. They are our own code. The published
  source is only a map of what each original routine does.
- Each writer is assembled two ways: at 96x80 in the copper-slot layout with 12-bit words
  (VERIFY only), to prove it equal to the original, and at WxH into pen bytes for the
  release.
- The projection and clipping move to the new size: the centre, the scales, `rightclip`,
  `top`, and every per-column and per-line table, which grows and is allocated at install.
  The slave holds no buffers.
- Output goes to a byte buffer in fast memory, row by row. Today every pixel is a word
  write into chip memory. In the 1x1 path chip is written only by the c2p, and for the
  small view that is 30720 bytes, about as many chip writes as the original's 7680 words.
  That is the hope the measurements must confirm or refute; it is not a promise.

### c2p and the frame

Render into the chunky buffer, c2p into the back screen, swap at the next vertical blank.
Which Kalms routine runs is chosen per CPU by measurement:

- `c2p1x1_8_c5_030` or `_030_2` (CPU only);
- `c2p1x1_8_c3b1_030` (CPU plus blitter): the blitter's last pass runs while the CPU
  renders the next frame;
- `c2p1x1_8_c5_040` on the 68040 and 68060.

### Memory

Chip grows by $27000 for the two screens and their heads (ws_BaseMemSize from 576 KB to
732 KB, 428 to 584 KB without music), above the slave's chip pool. ExpMem grows by $66000,
from $158000 to $1be000, for the option's area at its top, above the stacks (steps 3 and
4). The first 58080 bytes keep the palette and the pen tables. Then the palette build's
scratch, free once it is done, where the chunky buffer (up to 69120 bytes) and the c2p's
half row go, and the larger per-column tables can. Past the scratch are the game's two
copper lists (2 x 128800 bytes: 161 lines of 800, room for the 192x160 view), which the
original allocates in chip (2 x 33296 bytes)
([internals](internals.md#the-1x1-palette)). It is not allocated: the slave's fast pool has 136936
bytes free once the game has loaded, too little, and an area above the stacks leaves the
game's pool and hunk offsets as they were. WHDLoad asks for it with the option off too.
Anything further is allocated at install; when that fails, the option's patches are
skipped and the game runs as the original. The ReadMe's memory line follows.

Game time is per field (`TempFrames`), so a slower frame does not slow the game; frames
just step further, up to 15 fields.

## Steps

0. **Tooling** (done). `tools/exe.py` unpacks and flattens the executable;
   `tools/ab3d.py` drives the game on the shared server: menu to level, the full-screen
   toggle, frame counts from the `drawPt` swaps, and input scripts, `walk` the named one
   ([development](development.md#driving-it)). `tools/srcmatch.py` matched the published
   source's routines to game offsets; the renderer's are in
   [internals](internals.md#renderer-routines).
1. **Baseline the original** (done; [performance](performance.md), `tools/baseline.sh`).
   Both views, standing at level 1's start and on the scripted walk, on the 68020 (the
   a1200-fast: the plain a1200 cannot run the game), 68030 and 68040. Each had frame
   counts over 500-550 fields, and aprof profiles with ms of work a frame (p50, p95) by
   category.
   - Walk, small view, 68020 / 68030 / 68040 on aprof: 9.96 / 19.7 / 25 fps, 93 / 43 /
     32 ms of work a frame. Walls take 42-43% and floors 25-27%, then objects, geometry
     and the sky. The view's pixel writers spend 35-44%, 69% and 100% of their time on
     the Chip bus.
   - Both views cost the same: both draw 96x80.
   - The a1200-030 and a1200-040 setups' own frame rates come from their MMU models,
     not the CPUs: speed comparisons use the aprof machines.
   - No scene heavier than level 1's start was found; the heaviest place is still to add.
2. **Inventory the display** (done; [internals](internals.md#display-inventory),
   `ab3d.py copper`). The template, the view lists, the panel split, the sprites' pens and
   every writer into the view are listed with game offsets.
   - Beyond the renderer, the writers are the sky, glass, light beams, the gun, the water tint
     and the pause screen.
   - The damage flash only changes pen 0, the border. There are no pickup flashes, fades
     or messages in the view: the level text is its own screen.
   - The free pens: 240 in the small view, 255 in full screen (Colour above).
3. **Colour census** (done; Colour above, [internals](internals.md#the-1x1-palette)). A
   `tools/` script reads the installed data at analysis time only:
   distinct colours per level, and the error of one palette against per-level palettes at
   the free pen count, with and without dithering. Then decide, and write the slave's
   palette builder and table remap, checked against the tool's figures.
   - `tools/colours.py`'s integer model is the builder's, bit for bit. A dump of the area
     equals it on the a1200-fast, a1200-030 and a1200-040 setups, both variants
     (`ab3d.py palette`, `colours.py check`).
   - The build runs once, before the menu: 119 fields on the a1200-fast setup (14 MHz
     68EC020), 21 on the a1200-030 and 66 on the a1200-040 setup (the MMU models'
     speed). The nearest-pen searches go through the pens sorted by CIELAB a, with a table
     of squares: 461 fields on the a1200-fast before that.
   - The game plays with CUSTOM5=1, and CUSTOM5=0 adds no patch.
4. **Display skeleton** (done; [internals](internals.md#the-1x1-display),
   [performance](performance.md#the-display-skeleton), `tools/display.sh`). The game's two
   copper lists are in fast memory; at each swap the finished one is converted to pens,
   2x2 or 3x3 into the chunky buffer, through `c2p1x1_8_c5_030_2` onto two new 8-plane
   screens, and shown from the next field. Keypad Enter switches.
   - On the a1200-030 and a1200-040, each scene (level 1's start, the pause screen in both
     views, level 1's end, and with the option on a death in level 2 in both views and
     level 2's end) shows its frame, through the palette with the option on, with no pixel
     different. Against the original's screenshots every pixel is
     the same or its colour through the palette, but for line $ca of the small view (88
     pixels of the frame sprites, where the panel's list loads its colours) and line $ff
     of the original's full screen (its early row 71). The deaths and level 2's end
     follow different game time and are checked against their own frames only.
   - CUSTOM5=0: the patch list is unchanged, and the ORIGINAL build is still Psygore's
     slaves byte for byte.
   - The c2p a frame (MEASURED): 30 / 10 / 5 ms in the small view and 65 / 22 / 13 ms in
     full screen on the 68020 / 68030 / 68040; the frame rate standing at the start is
     7.1 / 16.7 / 16.7 fps in the small view (the original 10 / 16.7 / 25).
5. **The small view at 192x160 by the game's writers** (decided 26.11.2026: patch the
   originals' geometry; [internals](internals.md#the-1x1-renderer),
   [performance](performance.md#the-192x160-small-view)). The release build draws it;
   `VASM_EXTRA=-DLORES` builds the 96x80 small view of step 4.
   - Each view's geometry is a table of sites (`src/sites.s`, from `tools/sites.py`),
     written into the game's code at each switch; the row and column addressing for any
     width, the heights' doubling, the texture steps and the objects' sizes are patches
     in `src/hires.s`. The gun, the sky and the water tint have 2x2 writers of our own.
   - `VASM_EXTRA=-DHOLES` marks every pixel not written in a frame (`ab3d.py holes`).
     The original's writers leave some at 96x80 too: one line where a floor meets the
     edge of the step below it, where the list still holds
     an older frame's pixel. Ours are the same
     kind, one line of 160. Level 1's walk: 115 of 351 frames with holes, at most 125
     pixels, at 96x80 (`-DLORES`); 152 of 310, at most 289, at 192x160. The fight: 56 of
     496, at most 28; 71 of 419, at most 191. Filling them is for our own writers
     (step 7).
   - `tools/display.sh`: each scene shows its frame; against the original's frames 88-94%
     of the pixels are found at 2x2 (level 1's start, pause and end), and level 2's deaths show their frames. With `-DLORES` every
     scene equals the original's as in step 4.
   - Played through level 1's first fights (aliens, corpses, blood, the gun, doors).
     Still to play: level 2 (walk, fight, pause, a death, its end).
   - Speed, the small view standing at the start: 3.85 / 10.00 / 12.50 fps on the 68020 /
     68030 / 68040 (step 4 7.14 / 16.67 / 16.67; the original 10 / 16.67 / 25).
6. **Full screen at 288x240**: the same writers at the second size, with the projection
   scaled 3x from 96x80 in both directions: the original's field of view and aspect.
7. **Speed, as fast as possible.** Our own pen writers (Renderer above) in place of the
   patched originals, writer by writer in the order of the shares, each proven at 96x80
   against the original's with an in-process differential (VERIFY) before it replaces it;
   they remove step 5's conversion. Profile both 1x1 views on each CPU and work down the
   shares: the writers' inner loops (on the 030, keep them inside the 256-byte instruction
   cache), tables and textures in fast memory, the c2p choice and its overlap with
   rendering. Report each step against step 1, per view and per CPU. With no bar to meet,
   stop by AmigaXDev's `reference/measurement-method.md` §9: when the profile is flat
   and experiments move the totals by about 1% or less, change the structure or close the
   scope.
8. **Machines and play.** a1200-fast, a1200-030 and a1200-040, plus an ACA1221-class 28 MHz
   68020 (`EXTRA_ARGS`), both variants, two-player link at least not broken, and CUSTOM5
   off unchanged. Decide from the measurements which CPUs the option applies on; below
   that it is ignored.
9. **The other versions.** The work is done on the Aminet 8-channel version ($c4dc, the
   AGA drawer), then ported to the CD32 one ($fd78, the CD32 drawer). The CD32 version
   draws the same way, with its routines byte for byte or with only their addresses changed
   ([internals](internals.md#display)), so the port is finding them. The floppy version
   ($23d2) is in no archive; it needs the original disks.
10. **Release**: a dated `$VER` and ReadMe entry, CUSTOM5=1 in the installed icon, the new
    memory figures, and the reconstructed source in place of the encrypted archive (decided).

## Decided

- Full screen 288x240, as the original, for now (26.11.2026).
- Performance: as fast as possible, no fixed frame rate (26.11.2026).
- The 1x1 views first by the game's own writers, their geometry patched; our own pen
  writers in step 7 (26.11.2026).
- The palette: one fixed 240-pen palette for both views, popular plus farthest in CIELAB
  over the static histogram, built in the slave; every shade table remapped to pens; no
  dithering (26.11.2026; Colour).

## Open decisions

- The floppy version: in scope only if its executable is supplied (step 9).
- The slowest CPU the option runs on (from steps 4 and 7).
