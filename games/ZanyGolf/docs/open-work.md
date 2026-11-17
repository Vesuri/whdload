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
with the pointer moving: `a500` 9.25 to 37, `a1200` 13.25 to 58.5, the 68030 setups 57 to 60
(one a field). No buffer is drawn into while it is on screen (`Hidden`): a frame that ends
while the playfield shows waits for its end, which costs the `a500` a fifth of its frames.
The verify build found no cell differing from its tile on every CPU from 68000 to 68060,
with `DCACHE` too. The debug option `CUSTOM1=N` starts every game on hole
N+1, for measuring the later holes (`internals.md`, "Slave patches").

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
2. **The A500's frame.** The native draw list (`NewList`) took hole 1 from 37 to 44.25
   frames a second with the pointer moving. Each hole on `a500`, 17.11.2026, this slave
   (`CUSTOM1`, the view still for the trace, 60 fields; frames from `frames 240` and
   `frames 240 5 3`). The columns are per cent of all the A500's time:

   | Hole | Still | Moving | Shapes ($16ec) | Cells (`NewDraw`) | Draw list | $4fd0 | Waits |
   |---:|---:|---:|---:|---:|---:|---:|---:|
   | 1 | 47.25 | 44.25 | 17.5 | 24.4 | 10.7 | 3.9 | 16.1 |
   | 2 | 12.5 | 12.75 | 56.3 | 7.8 | 4.5 | 1.5 | 5.0 |
   | 3 | 30 | 30 | 18.2 | 18.8 | 11.3 | 3.2 | 22.2 |
   | 4 | 40 | 38.5 | 14.1 | 13.5 | 9.5 | 5.7 | 26.1 |
   | 5 | 30 | 30 | 18.2 | 15.6 | 11.9 | 5.3 | 23.5 |
   | 6 | 40 | 40 | 18.5 | 13.5 | 9.1 | 4.1 | 27.9 |
   | 7 | 38.5 | 39.5 | 32.4 | 16.3 | 12.1 | 5.1 | 7.3 |
   | 8 | 30.25 | 31.75 | 17.7 | 17.0 | 11.8 | 6.1 | 20.6 |
   | 9 | 22 | 21 | 32.7 | 11.4 | 11.0 | 6.6 | 9.9 |
   | 10 | 20 | 20 | 35.2 | 9.1 | 6.4 | 14.4 | 5.0 |

   "Draw list" is `NewList` and the threaded sort and draw calls after it; "Waits" is
   `FrameCap`'s and `Hidden`'s busy waits. Candidates:
   - the shape drawer ($16f2), the largest on holes 2, 7, 9 and 10: it plots each pixel with
     four `bclr` and up to four `bset`. In the slave it could write a byte of each plane at a
     time with a mask;
   - a third buffer: with two, a frame that ends while the playfield shows waits for its
     end (`Hidden`), a fifth to a quarter of the time on holes 3-6 and 8, which run at
     exactly 2 fields a frame. With three, the next frame could start at once (32 KB more
     chip RAM);
   - $4fd0's own threaded code on hole 10 (14.4 %, after each step);
   - the steps (10 a second) are threaded code throughout.
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
