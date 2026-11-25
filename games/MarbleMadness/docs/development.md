# Development

Only what differs from the repository's `docs/running.md` and `docs/building.md`: the inputs
and how they are installed, game-specific tools, captures and traps.

## Inputs

`inputs.sha256`: the Retroplay archive (installs `MarbleMadness/`) and the whdload.de
install package (unpacks `MarbleMadnessHD/` with the shipped slaves and source).

## The build against the shipped slave

The build is not byte-identical to the shipped slave. Ours is 6940 bytes against 7140,
and the Image variant 4156 against 4188. The code hunks are identical from inside
`patch_exe` to the end: JOTD's patch list, routines and tags. Before that point they differ
in three ways:
- the `kick13.s` is the newer one from the WHDLoad developer package, where JOTD's build
  used an older copy;
- the PC-relative displacements into it change accordingly;
- `$VER` and `slv_info` carry no build date (`DECL_VERSION` adds one only under Barfly or
  with `DATETIME`).

The shipped slave (`SLAVE=original`) reaches the options menu on `a500-1.5m` after about
1800 fields. Our build reaches the race on `a500-1.5m`, `a1200` and `a1200-030`.

## Driving it

`tools/marblemadness.py` is the game server with field-exact input steps (its docstring):

```sh
INSTANCE=mine SETUP=a1200-030 WHD_ARGS=CACHE WARP=1 WINDOW=none python3 tools/marblemadness.py serve &
python3 tools/marblemadness.py menu          # Mouse Port + Mouse selected, pointer on GO!
python3 tools/marblemadness.py go            # into the practice race
python3 tools/marblemadness.py chain 100 2 1 $PWD/tmp/prof/race/f   # 100 one-field traces
```

Traps:
- The built-in commands resume the emulator after each call, so a run of `gdb monitor ...`
  calls lets an unknown number of warp fields pass between them; a held mouse button then
  repeats in the menu. The tool's commands stop first and stay stopped.
- A menu click needs at least about 6 fields of press; a longer press repeats.
- The `a1200-030` preset's MMU-model core records no instructions: trace with
  `EXTRA_ARGS=--uae_mmu_model=0` (same cycle-exact 68030).
- Where the hunks load depends on the setup: in fast memory on the fast-memory setups, in
  chip RAM on `a1200`, which has no fast memory. Map a
  trace through the seglist of a memory dump from the same run. Search for the `Framer`
  task name, and check that the word at +`$A` of the struct points back at it: a stale copy
  of the name also turns up in chip RAM.
- Ghidra headless needs `JAVA_HOME` set to Homebrew's `openjdk@21`. The installed 12.x has
  no native decompiler, so use listings and call graphs. Import the flat PatchSeg-addressed
  image (`docs/internals.md`, "Program") as a raw 68000 binary at base 0, with each code
  hunk's start marked as a function.
