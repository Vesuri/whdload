# Open work

`src/ZanyGolf.asm` is Bored Seal's v1.1 source with three encoding edits that make the
build byte-identical to the shipped slave (`development.md`). No slave change yet. The
first analysis is done (17.11.2026, `internals.md`, "The program" to "Measurements"): the
game runs entirely in chip RAM with the caches off, and redraws all 800 tiles of the view
with byte copies every frame. On `a1200-030` that is 13.75 frames a second (NTSC); the
renderer takes two thirds of a frame and the threaded-code interpreter most of the rest.

## Next

1. **Game time.** Confirm what the elapsed-fields sum at `FILE1` $5de4 drives
   (`internals.md`, "Interrupts and time") and whether the game's speed is independent of
   the frame rate. Check it by behaviour too: the same shot on `a500` and on `a1200-030`
   with `CACHE` (9 and 21 frames a second) must end in the same place after the same
   number of fields. Everything below assumes it is.
2. **The caches** (the user's decision). Enabling the instruction cache for BaseMem in the
   slave (`resload_SetCACR`) gives 55 % more frames on a 68030 (13.5 to 21.0) and helps a
   68020 too (not measured yet); the alternative is a ReadMe recommendation of WHDLoad's
   `Cache`. The data cache does nothing for chip RAM on hardware.
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
