# Open work

No slave changes yet. `src/` is Codetapper's 1.3 source as upstream has it; the game
directory only sets it up on the repository layout: it unpacks, builds (byte-identical to
the shipped slave given its date string, [development.md](development.md)), and boots to the
attract sequence on the a500 and the a1200.

Nothing is released from here. A release needs a new slave version with a
`$VER: <name> <version> (dd.mm.yyyy)` string (the packager reads the version and date from
it; 1.3's has neither a name nor, in our build, a date) and a ReadMe entry above
Codetapper's history.

## Candidates

Not started and not measured; each needs its own investigation first.

1. **Game time and frame rate.** The game runs at the rate `_LockFrameRate` caps it to,
   10 fps by default ([internals.md](internals.md), "Frame rate control"). Find what
   `$4DB0` is (the counter's source), how the game's speed depends on its frame rate, and
   what an A500 reaches uncapped. The playbooks' fixed-time and simulation/presentation
   docs apply.
2. **The trainer option does nothing as configured.** Nothing tests `CUSTOM1`: the DOS
   version (the installed archive's) never applies `_PL_BugOP_Tr`, the disk versions always
   apply theirs, and `_SetCheat` is never called, so scores are saved with the trainer on
   ([internals.md](internals.md), "Slave header"). From reading; confirm in a run.
3. **Disk versions.** The second Tenstar release lacks the frame-rate patch and its
   trainer. There is no image of any disk version here to test them.
