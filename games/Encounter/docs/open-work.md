# Open work

No improvement work has been done yet. `src/EncounterHD.s` is JOTD's 1.2 source as
upstream has it; the game directory only sets it up on the repository layout: it unpacks,
builds (to the same code as the shipped slave, not the same bytes: [development.md](development.md)),
and boots to the title screen and the attract-mode demo on the default a500.

Nothing is released from here. A release would need a new slave version with a
`$VER: <name> <version> (dd.mm.yyyy)` string (the packager reads the version and date from
it; 1.2 has no date) and a ReadMe entry above JOTD's history.

## Candidates

Not started and not measured; each needs its own investigation before it is planned.

1. The ReadMe's open bug: rarely the colours turn white, and the slave's numeric `]` key
   (`$5B`) works around it by rewriting the AGA bitplane control registers
   ([internals.md](internals.md), "Keyboard"). The cause is unknown.
2. The keyboard handshake wait the slave inserts (`DBFD1`, three raster-line changes)
   and the game's own timing on fast CPUs have not been examined.
