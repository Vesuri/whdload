# Open work

`src/ZanyGolf.asm` is Bored Seal's v1.1 source with three encoding edits that make the
build byte-identical to the shipped slave (`development.md`), and since then the world on
its own clock and a new renderer. The first analysis is done (17.11.2026, `internals.md`,
"The program" to "Measurements"): the game runs entirely in chip RAM with the caches off,
and redraws all 800 tiles of the view with byte copies every frame.

Game time is confirmed (17.11.2026, `internals.md`, "Game time"): the game counts each
step as 6 fields, 10 steps a second at NTSC. The slave steps the world each 6 fields by the
field counter and draws frames between the steps, at most one a field (`Split`,
`FrameCap`); a click between two steps is kept (`ReadButton`). Game speed is 1.00x on every
machine tried.

Rendering (17.11.2026, `internals.md`, "Display" and "Game time"): with an optional ExpMem
the slave redraws only the cells whose map word changed or that a shape covered, and copies
the other buffer with the blitter when the view scrolled (`NewDraw`, `ShapeHook`); draw-only
passes skip $4fd0 between steps; the instruction cache is on for BaseMem. Frames a second
with the pointer moving: `a500` 9.25 to 46.5, `a1200` 13.25 to 57.5, the 68030 setups 60
(one a field). The verify build found no cell differing from its tile on every CPU from
68000 to 68060, with `DCACHE` too.

## Next

1. **Interpolate the frames between steps** (decided 17.11.2026): the moving things must be
   drawn between the last two steps, at the fraction of the step the frame shows (the
   fields since the step's due time, which `Split` keeps, over 6). What is needed, in order:
   - the presented state: the view position ($0e9c/$0e9e, the fine scroll), the ball
     (object table at $5c7a), the other objects the shape drawer ($16f2) draws, and the
     animations the clock drives. Each needs its previous and current step kept, and the
     renderer drawing from interpolated copies without the world seeing them.
   - what may not be interpolated: cuts (a new hole, the ball sunk or reset), and
     anything drawn into the tile map.
   - $4fd0 reads the view, so with an interpolated view it must run whenever the view
     moved, not only after a step (`Split`'s `_stepped`).
   - cost: an interpolated view scrolls nearly every frame, so each frame pays the scroll
     copy (about 7 % of the A500's time now). The A500 draws about 4.7 frames a step.
   Acceptance: the putt's world steps as now (6 fields apart), and each presented frame
   between the two steps around it.
2. **The A500's frame**, about 1.3 fields. With the view still, per frame: $48d4's threaded
   code (the object draw list) 0.33 fields, the shape drawer it calls 0.22 (it plots each
   pixel with four `bclr` and up to four `bset`), the renderer 0.25. Candidates:
   - the shape drawer in the slave, writing a byte of each plane at a time with a mask;
   - $48d4 as native code in the slave: it must build the same draw list ($46a2-$4782) and
     call the drawer as the game does;
   - steps (10 a second, about 1.2 fields each) are threaded code throughout.
   A 68000 must still draw correctly whatever the 68020+ path does.
3. **Fast memory.** In fast memory now: the slave's code (the renderer, `Split`), the
   renderer's caches and the tile copy (ExpMem). What cannot move: `FILE1` is the 65xx
   machine's bank 0, and every other address the game uses is a4-relative too (the hole
   block at a4+$11d0a, the screen buffers at a4+$30000, the copper list inside `FILE1` at
   $2272), so moving `FILE1` would move an address space with chip-only data in it. Native
   code also reads its variables PC-relative and resets a4 with `lea (pc)`, and the
   dispatch takes the primitives' bank from a4. Hot threaded or native routines can move
   only as slave copies (item 2). The game's user stack ($9570) could move: small gain, not
   tried.

## Also seen

- The `bra.s *+4` at loader $48 executes the low word of a relocated address
  (`internals.md`, "Slave patches"): check what it decodes to, and branch to $4e.
- F10 is both the quit key and the trainer key (`internals.md`, "Keys").
- The keyboard delay is nine `VHPOSR` line-byte changes, counted by polling; a CIA timer
  would be exact on any CPU.

## Before a first release

A dated `$VER` in the slave and the info text, and a ReadMe entry above Bored Seal's.
