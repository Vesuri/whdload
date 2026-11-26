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

- Two chip buffers of the full view's size, 288x240 in 8 planes (69120 bytes each); the
  small view uses 192x160 of them. Double-buffered: the c2p writes one while the other shows,
  and the copper list swaps them at a vertical blank.
- The slave builds the copper lists: bitplane pointers, each view's window and modulos,
  the view's palette, and in the small view the original's sprites (the frame) and its
  panel section below the view. Both stay as they are
  ([inventory](internals.md#display-inventory)).
- The panel loads all 256 colours at its split, so the view's palette is loaded again
  every field above the view, in the vertical blank. 256 MOVEs with LOCT clear set both
  nibbles (12-bit) in about 4.7 raster lines; 24-bit needs 512 and about 9.4 (DERIVED: a
  MOVE is 4 memory cycles, 227 a line).
- The c2p converts only the view rectangle (AmigaXDev's Kalms rectangle adapter).

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

- One new pixel writer for each of the original's: wall strips, floor and ceiling spans,
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

Chip grows by the two screens, 138 KB (ws_BaseMemSize from 576 KB to about 720 KB).
ExpMem grows by $28000, from $158000 to $180000, for the option's area at its top, above
the stacks (step 3). The first 58080 bytes keep the palette and the pen tables. The rest is
the palette build's scratch, free once it is done, which the chunky buffer (up to 69120
bytes) and the larger per-column tables can use. It is not allocated: the slave's fast pool has 136936
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
4. **Display skeleton** behind CUSTOM5, with the original renderer unchanged. Point it at
   a fast-memory buffer in the copper-slot layout, convert the words to pens, scale 2x2
   or 3x3 into the chunky buffer, c2p, and show the new screens, with keypad Enter
   switching.
   - This proves the whole new display path (palette, c2p, swap, sprites, panel) with the
     original's own image, and measures the c2p per view.
   - Done when both views match the original's screenshots up to the palette, through
     pause, level end and death, on a1200-030 and a1200-040, and CUSTOM5=0 leaves the
     game's patched code identical to the original slave's.
5. **The 1x1 renderer, writer by writer**, in the order of step 1's shares (walls and
   floors first are expected).
   - Prove each writer at 96x80 with an in-process differential (VERIFY): on the same
     frame state, the original draws into the copper list and ours into a slot-layout
     buffer. Zero differences over the scripted scenes.
   - Then switch it to WxH bytes, with the geometry constants beside it.
   - A VERIFY count of writes per pixel finds holes and overdraw at 1x1.
   - Done when the small view draws everything at 192x160 with no holes, play-tested
     through levels 1 and 2.
6. **Full screen at 288x240**: the same writers at the second size, with the projection
   scaled 3x from 96x80 in both directions: the original's field of view and aspect.
7. **Speed, as fast as possible.** Profile both 1x1 views on each CPU and work down the
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
- The palette: one fixed 240-pen palette for both views, popular plus farthest in CIELAB
  over the static histogram, built in the slave; every shade table remapped to pens; no
  dithering (26.11.2026; Colour).

## Open decisions

- The floppy version: in scope only if its executable is supplied (step 9).
- The slowest CPU the option runs on (from steps 4 and 7).
