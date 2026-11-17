# Open work

`src/ZanyGolf.asm` is Bored Seal's v1.1 source with three encoding edits that make the
build byte-identical to the shipped slave (`development.md`), and since then the world on
its own clock. The
first analysis is done (17.11.2026, `internals.md`, "The program" to "Measurements"): the
game runs entirely in chip RAM with the caches off, and redraws all 800 tiles of the view
with byte copies every frame. On `a1200-030` that is 13.75 frames a second (NTSC); the
renderer takes two thirds of a frame and the threaded-code interpreter most of the rest.

Game time is confirmed (17.11.2026, `internals.md`, "Game time"): the world advances one
fixed step a drawn frame, and the game counts that step as 6 fields, so the intended speed
is 10 frames a second at NTSC. The original has no limit, so an A1200 played at 1.24x and a
68030/50 at 1.38x (2.11x with `CACHE`). The slave now steps the world each 6 fields by the field
counter and draws frames between the steps, at most one a field (`Split`, `FrameCap`;
`internals.md`, "Game time"): game speed is 1.00x on every machine tried, the A500
included, and the 68030 with `CACHE` draws 24.75 frames a second. The frames between steps
show the last step again until item 1 interpolates them.

## Next

1. **Interpolate the frames between steps** (decided 17.11.2026): the world steps at 10 a
   second and the passes between draw only (done, `Split`); the moving things must be drawn
   between the last two steps, at the fraction of the step the frame shows (the fields
   since the step's due time, which `Split` keeps, over 6). What is needed, in order:
   - the presented state: the view position ($0e9c/$0e9e, the fine scroll), the ball
     (object table at $5c7a), the other objects the shape drawer ($16f2) draws, and the
     animations the clock drives. Each needs its previous and current step kept, and the
     renderer drawing from interpolated copies without the world seeing them.
   - what may not be interpolated: cuts (a new hole, the ball sunk or reset), and
     anything drawn into the tile map.
   - cost: on the 68030 a frame takes 2.4 fields with `CACHE` and 4.1 without, so without
     items 2 to 4 this gives about 2 frames a step at best; the renderer work (item 3) is
     what turns it into one frame a field.
   Acceptance: the putt's world steps as now (44 steps from the release, 6 fields apart on
   average), and each presented frame between the two steps around it.
2. **The caches** (the user's decision). They no longer change the game's speed, only the
   frames drawn between steps. Enabling the instruction cache for BaseMem in the slave (`resload_SetCACR`) gives 55 % more frames on a 68030 (13.5 to
   21.0) and helps a 68020 too (not measured yet); the alternative is a ReadMe
   recommendation of WHDLoad's `Cache`. The data cache does nothing for chip RAM on hardware.
3. **The renderer**, two thirds of a frame. Candidates, to price one at a time with the
   bench:
   - draw only the tiles that differ from what the back buffer holds (it was drawn two
     frames ago); a still view then costs almost nothing, but a change of the coarse
     scroll changes every tile;
   - copy the tile set ($21d0a) to fast memory, which halves the chip accesses;
   - write longwords: four horizontally adjacent tiles' bytes per plane row in one write,
     a quarter of the writes;
   - the blitter, or scrolling by the bitplane pointers instead of redrawing.
   A 68000 must still draw correctly whatever the 68020+ path does.
4. **The interpreter**, a third of a frame with the caches off. Its code and the 65xx
   machine's memory are the one 64 KB bank at $10000 in chip RAM (threaded addresses are
   16-bit, the high word from a4), so moving it to fast memory means moving the whole bank
   to a 64 KB boundary there and finding every absolute reference into it (the slave's
   FixKey writes $15ca2).

## Also seen

- The `bra.s *+4` at loader $48 executes the low word of a relocated address
  (`internals.md`, "Slave patches"): check what it decodes to, and branch to $4e.
- F10 is both the quit key and the trainer key (`internals.md`, "Keys").
- The keyboard delay is nine `VHPOSR` line-byte changes, counted by polling; a CIA timer
  would be exact on any CPU.

## Before a first release

A dated `$VER` in the slave and the info text, and a ReadMe entry above Bored Seal's.
