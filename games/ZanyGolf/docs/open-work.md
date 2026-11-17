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
passes skip $4fd0 unless a step ran or the view drawn moved; the draw list and the shape drawer are native code
(`NewList`, `NewShape`); the instruction cache is on for BaseMem. Frames a second
with the pointer moving: `a500` 9.25 to 37, `a1200` 13.25 to 58.5, the 68030 setups 57 to 60
(one a field). No buffer is drawn into while it is on screen (`Hidden`): a frame that ends
while the playfield shows waits for its end, which costs the `a500` a fifth of its frames.
The verify build found no cell differing from its tile on every CPU from 68000 to 68060,
with `DCACHE` too, and no draw list or shape differing from the game's on the 68030 and the
68000. The debug option `CUSTOM1=N` starts every game on hole
N+1, for measuring the later holes (`internals.md`, "Slave patches").

The pointer is a pair of hardware sprites (17.11.2026, `internals.md`, "The pointer"),
placed by the interrupt every field from the mouse's counts the next step will take, on
the frame on screen; the game's shape for it is taken out of the draw list. A step's move
is clamped to ±100 pixels instead of the game's ±31, so a fast stroke stays straight. At
rest the sprite covers the same pixels as the game's shape on every hole.

The frames between the steps are interpolated (17.11.2026, `internals.md`, "Game time"):
the view and the objects are drawn between the last two steps, a step behind the world at
most, with each object's animation frame switched halfway and, when its frame changes, its
frame's bottom interpolated for an object that has moved, so the hamburger's bottom bun
stays put as it grows; the course pieces drawn over
the ball are drawn in every frame, not only the first after a step; while the player
points or draws a stroke back, the frames draw what the next step will make of the
pointer's predicted point (the scroll, the aiming line), so they move with the sprite. The
world is unchanged: the `a500` putt rests at 156, 226 as before, and the verify build
found no cell, list or shape differing on the 68000. Frames a second from the flips
(`frametrack`): the same with the hole still; on the `a500` the putt's roll 43.7 against
45.38. The cursor keys are not predicted (the pointer moves with them at the step), and
a cut (a new state or hole, a late step) shows the last step at once.

The waits that were CPU loops (17.11.2026, `internals.md`, "Slave patches"): Esc or the
mouse button ends the credits; the hole's sign loads without the loader's delay, so the
title no longer stays frozen after 1-4 (3.5 s on the `a500`); the game's delay $290c (the
timer bonus screen, the stroke award, game over) and the palette fades wait the A500's time
by the beam on every CPU. The loads after the sign keep the loader's delay, which on a fast
CPU is what shows the sign.

## Next

1. **The A500's frame.** The native draw list (`NewList`) took hole 1 from 37 to 44.25
   frames a second with the pointer moving, and the native shape drawer (`NewShape`) hole
   2 from 12.5 to 25. Each hole on `a500`, 17.11.2026, before `NewShape` (`CUSTOM1`, the
   view still for the trace, 60 fields; frames from `frames 240` and `frames 240 5 3`),
   with the frames after it. The columns but the frames are per cent of all the A500's
   time:

   | Hole | Still | Moving | Shapes ($16ec) | Cells (`NewDraw`) | Draw list | $4fd0 | Waits | `NewShape`: still | moving |
   |---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
   | 1 | 47.25 | 44.25 | 17.5 | 24.4 | 10.7 | 3.9 | 16.1 | 47.5 | 45.75 |
   | 2 | 12.5 | 12.75 | 56.3 | 7.8 | 4.5 | 1.5 | 5.0 | 25 | 24.75 |
   | 3 | 30 | 30 | 18.2 | 18.8 | 11.3 | 3.2 | 22.2 | 30 | 30 |
   | 4 | 40 | 38.5 | 14.1 | 13.5 | 9.5 | 5.7 | 26.1 | 40 | 38.5 |
   | 5 | 30 | 30 | 18.2 | 15.6 | 11.9 | 5.3 | 23.5 | 30 | 30 |
   | 6 | 40 | 40 | 18.5 | 13.5 | 9.1 | 4.1 | 27.9 | 48.25 | 47 |
   | 7 | 38.5 | 39.5 | 32.4 | 16.3 | 12.1 | 5.1 | 7.3 | 40 | 40 |
   | 8 | 30.25 | 31.75 | 17.7 | 17.0 | 11.8 | 6.1 | 20.6 | 33 | 32 |
   | 9 | 22 | 21 | 32.7 | 11.4 | 11.0 | 6.6 | 9.9 | 28.5 | 28.25 |
   | 10 | 20 | 20 | 35.2 | 9.1 | 6.4 | 14.4 | 5.0 | 30 | 29.75 |

   The frames are one run each, and a run's frames depend on where it reaches the hole
   (hole 2 gave 20 and 25 with one slave; `development.md`, traps). On holes 1, 2 and
   10 the sprite pointer's frames stayed within that.
   "Draw list" is `NewList` and the threaded sort and draw calls after it; "Waits" is
   `FrameCap`'s and `Hidden`'s busy waits. Holes 3-8 draw a frame in about a field, and
   `Hidden` rounds a frame up to one or two fields, so their rates move in steps with
   small changes: hole 3 measured 50 and hole 6 40 with an earlier `NewShape`. With
   `NewShape` the drawer is still 51.5 % of hole 2's time (75 shapes in 60 fields, about
   280 pair bytes a shape), 32.3 % of hole 9's and 26.3 % of hole 10's: building the 16
   pixels is 19 % of hole 2's, the masked writes 14 %. Candidates:
   - the shape drawer again: the blitter could draw the rows (a mask and four planes a
     shape, made once per frame of a shape and kept), or shapes could be kept as planes;
   - a third buffer: with two, a frame that ends while the playfield shows waits for its
     end (`Hidden`), a fifth to a quarter of the time on holes 3-6 and 8, which run at
     exactly 2 fields a frame. With three, the next frame could start at once (32 KB more
     chip RAM);
   - $4fd0's own threaded code on hole 10 (14.4 %, after each step);
   - the steps (10 a second) are threaded code throughout.
   A 68000 must still draw correctly whatever the 68020+ path does.
2. **Fast memory.** In fast memory now: the slave's code (the renderer, `Split`), the
   renderer's caches and the tile copy (ExpMem). What cannot move: `FILE1` is the 65xx
   machine's bank 0, and every other address the game uses is a4-relative too (the hole
   block at a4+$11d0a, the screen buffers at a4+$30000, the copper list inside `FILE1` at
   $2272), so moving `FILE1` would move an address space with chip-only data in it. Native
   code also reads its variables PC-relative and resets a4 with `lea (pc)`, and the
   dispatch takes the primitives' bank from a4. Hot threaded or native routines can move
   only as slave copies (item 1). The game's user stack ($9570) could move: small gain, not
   tried.

## Also seen

- The `bra.s *+4` at loader $48 executes the low word of a relocated address
  (`internals.md`, "Slave patches"): check what it decodes to, and branch to $4e.
- F10 is both the quit key and the trainer key (`internals.md`, "Keys").
- The keyboard delay is nine `VHPOSR` line-byte changes, counted by polling; a CIA timer
  would be exact on any CPU.

## Release

2.0b (17.11.2026): `$VER` and the info text in the slave, the ReadMe entry above Bored
Seal's.
