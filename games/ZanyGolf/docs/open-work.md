# Open work

`src/ZanyGolf.asm` is Bored Seal's v1.1 source with three encoding edits that make the
build byte-identical to the shipped slave (`development.md`). No improvement work has been
done; the slave boots to the title and starts hole 1 on a500 and a1200.

## Next

- Decide what to improve. Candidates seen so far:
  - The `bra.s *+4` at loader $48 executes the low word of a relocated address
    (`internals.md`, "Slave patches"): check what it decodes to, and branch to $4e.
  - F10 is both the quit key and the trainer key (`internals.md`, "Keys").
  - The keyboard delay is nine `VHPOSR` line-byte changes, counted by polling; a CIA timer
    would be exact on any CPU.
  - A version for 68020 and faster machines: measure first (game time, frame rate) before
    any claim.
- Before a first release: a dated `$VER` in the slave and the info text, and a ReadMe entry
  above Bored Seal's.
