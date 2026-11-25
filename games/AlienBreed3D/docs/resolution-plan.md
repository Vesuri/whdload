# Enhanced resolution plan

The goal (decided 26.11.2026): replace the copper chunky view with real 1x1 pixels in both
views, behind one option, and make both run as fast as we can.

- **Enhanced resolution**, CUSTOM5 (`C5:B:Enhanced resolution`; CUSTOM1-4 are the
  original's). Off, the game is the original byte for byte.
- The small view becomes 192x160 at 1x1 (4x the original's 96x80 pixels), full screen
  288x240 at 1x1 (9x). Keypad Enter still switches between them.
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
  panel section below the view. Both stay as they are, so their pens stay out of the view's
  palette.
- The c2p converts only the view rectangle (AmigaXDev's Kalms rectangle adapter).

### Colour

The original shows each pixel in its own 12-bit colour, so there is no palette to keep.
Every texture brings its own shade table (a wall: 32 colours at 33 brightness levels),
so the view can show thousands of colours. The 1x1 modes:

- take every colour the loaded shade tables can produce, quantise them to the free pens
  (256 less the sprites' and panel's), and remap every shade table to pen bytes once, when
  the tables load. The renderer then writes bytes.
- compute the palette in the slave at run time, never as a file: it is derived from the
  game's data, which the repository must not hold.
- dither (ordered, by pixel parity, through two tables) only if the colour census (step 3)
  shows banding a plain palette cannot avoid.

HAM8 is out: AmigaXDev's two HAM8 converters are 68040-only, and both trade away horizontal
resolution.

### Renderer

- One new pixel writer for each of the original's: wall strips, floor and ceiling spans,
  bump-mapped floors, objects (bitmaps, glass, flat and Gouraud polygons), the gun, and
  whatever else step 2 finds writing into the view. They are our own code. The published
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
ExpMem grows by the chunky buffer (up to 69120 bytes), the remapped tables and the larger
per-column tables. Everything is allocated at install. When an allocation fails, the
option's patches are skipped and the game runs as the original. The ReadMe's memory line
follows.

Game time is per field (`TempFrames`), so a slower frame does not slow the game; frames
just step further, up to 15 fields.

## Steps

0. **Tooling.** `tools/exe.py` unpacks and flattens the executable (done). Still to do:
   - `tools/ab3d.py` on the shared game server, with named commands: menu to level, the
     full-screen toggle, frame and field counts from `FramesToDraw`, and fixed input
     scripts for repeatable scenes;
   - the published source's renderer routines matched to game offsets by signature, listed
     in internals.
1. **Baseline the original**, both views, on a1200-030 and a1200-040 (a1200 for
   reference). Scenes: standing at level 1's start, a scripted walk, and the heaviest
   place found (many aliens and objects).
   - Frame rate from `FramesToDraw` over at least 500 fields.
   - An aprof profile split into geometry and visibility, walls, floors, bump mapping,
     objects, gun, game logic and interrupts.
   - Report ms per frame with p50 and p95 (AmigaXDev `reference/measurement-method.md`).
2. **Inventory the display.** Read all of the copper template: the panel split, the
   sprites' pens, and the colour effects (damage and pickup flashes, fades, level text,
   pause, messages). List every routine that writes into the view, with its game offset.
   Step 5 works from that list.
3. **Colour census.** A `tools/` script reads the installed data at analysis time only:
   distinct colours per level, and the error of one palette against per-level palettes at
   the free pen count, with and without dithering. Then decide, and write the slave's
   palette builder and table remap, checked against the tool's figures.
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
   scaled 3x from 96x80 in both directions. That is the original's field of view and
   aspect; a wider screen is a later option, not this step.
7. **Speed.** Profile both 1x1 views on each CPU and work down the shares: the writers'
   inner loops (on the 030, keep them inside the 256-byte instruction cache), tables and
   textures in fast memory, the c2p choice and its overlap with rendering. Report against
   step 1, per view and per CPU, and stop at the agreed bar.
8. **Machines and play.** a1200, a1200-030 and a1200-040, plus an ACA1221-class 28 MHz
   68020 (`EXTRA_ARGS`), both variants, two-player link at least not broken, and CUSTOM5
   off unchanged. Decide from the measurements which CPUs the option applies on; below
   that it is ignored.
9. **The other versions**: the floppy ($23d2) and CD32 ($fd78) executables, which only
   the original disks and CD hold. Port the patches by finding the same routines.
10. **Release**: a dated `$VER` and ReadMe entry, CUSTOM5=1 in the installed icon, the new
    memory figures, and the reconstructed source in place of the encrypted archive (decided).

## Open decisions

- The bar: which frame rate, for which view, on which machine (needed by step 7).
- Versions: the Aminet 8-channel one alone (all we have), or the floppy and CD32 as well
  (step 9 needs their files).
- Full screen: 288x240 as the original, or wider once 288x240 works.
- The slowest CPU the option runs on (from steps 4 and 7).
- The palette method (from step 3).
