# Open work

`src/ZanyGolf.asm` is Bored Seal's v1.1 source with three encoding edits that make the
build byte-identical to the shipped slave (`development.md`). No slave change yet. The
first analysis is done (17.11.2026, `internals.md`, "The program" to "Measurements"): the
game runs entirely in chip RAM with the caches off, and redraws all 800 tiles of the view
with byte copies every frame. On `a1200-030` that is 13.75 frames a second (NTSC); the
renderer takes two thirds of a frame and the threaded-code interpreter most of the rest.

Game time is confirmed (17.11.2026, `internals.md`, "Game time"): the world advances one
fixed step a drawn frame, and the game counts that step as 6 fields, so the intended speed
is 10 frames a second at NTSC. Nothing limits the frame rate. The stock A500 plays at 0.96x
in the measured putt (0.90x with the view scrolling), an A1200 at 1.24x and a 68030/50 at
1.38x. Every speed-up so far planned makes the game faster, not smoother: `CACHE` alone
takes the 68030 to 2.11x.

## Next

1. **The time model** (the user's decision; it gates items 2 to 4). The candidates:
   - *A frame cap*: start a frame's draw no sooner than 6 fields after the previous one.
     The intended speed exactly on every machine that draws faster than 10 frames a
     second; the A500 unchanged (it never waits). The simplest change and faithful to the
     original, but a faster renderer then buys idle time, not smoothness.
   - *A cap plus catch-up on slow machines*: when a frame took more than 6 fields, run
     world-only passes until game time catches up. The main loop already skips the draw
     while the flag at $0ea0 is clear, but the clock then counts real fields, so the
     passes need their own switch. That would bring the A500 to 1.00x. It needs the cost
     of a world-only pass on the 68000 (not measured yet), and input applied once.
   - *10 steps a second, presented at the display rate*: draw extra frames between steps
     with the ball, scroll and animations interpolated. Smooth on fast machines, the
     original physics untouched. It needs every moving thing's state found and the
     renderer fast enough for more than 10 frames a second (21 with `CACHE` on the 68030
     already).
   - *A finer step* (3 or 2 fields, 20 or 30 steps a second) on fast CPUs: rescale every
     per-frame quantity in the translated 65816 code: the position update, friction every
     fifth frame (`internals.md`), the $5d12 accumulator, the clock's 6, collisions,
     slopes and the obstacles' timing. The most work and a change of feel to verify in
     play; the 68000 keeps the native step.
   Acceptance for any of them: the putt (`tools/route.py hole1 putt`, with the friction
   timer in phase, `internals.md`) still takes 44 steps and comes to rest at 154, 229, and
   wherever the machine is fast enough it lasts 44 x 6 = 264 fields, within a frame.
2. **The caches** (the user's decision, after item 1). Enabling the instruction cache for
   BaseMem in the slave (`resload_SetCACR`) gives 55 % more frames on a 68030 (13.5 to
   21.0) and helps a 68020 too (not measured yet); the alternative is a ReadMe
   recommendation of WHDLoad's `Cache`. Either one, without item 1, runs the game at 2.1x
   on a 68030. The data cache does nothing for chip RAM on hardware.
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
