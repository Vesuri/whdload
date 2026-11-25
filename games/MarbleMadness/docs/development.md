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
python3 tools/marblemadness.py dump $PWD/tmp/ana/mem/run.bin 0x940000 0xa00000   # for the map
python3 tools/marblemadness.py watch 0x9bfc8e 4000   # fields where a word (here $5D2) changes
```

`watch` reads a game address, so map a dump of the same slave and setup first. The mode
word `$5D2` is hunk 3 + `$3AE`.

`tools/mmtrace.py` (its docstring) works at PatchSeg offsets:
- `image`: the flat image;
- `ghidra`: its listing, with library calls named, and call graph;
- `segmap`: the hunk map of a dump;
- `split`: cycles by task;
- `tree`: one task's call tree;
- `count`: entries per field to given offsets.

```sh
python3 tools/mmtrace.py image && python3 tools/mmtrace.py ghidra
python3 tools/mmtrace.py segmap tmp/ana/mem/run.bin 940000
python3 tools/mmtrace.py tree tmp/ana/mem/run.bin.segmap.json Scroller 3 tmp/prof/race/f.0*
python3 tools/mmtrace.py count tmp/ana/mem/run.bin.segmap.json AF9E,11704,86B4 tmp/prof/race/f.0*
```

Checking CUSTOM4: `make build BUILD=noblend DEFINES_noblend=-DNOBLEND=1` draws every picture
unblended with the same allocations, so a dump of its data hunks after the same input must
equal the release build's (apart from task stacks and idle counters). The release build's
table allocation moves the game's later allocations, so compare against this build, not
against a build without interpolation. A larger slave also moves where the hunks load: map
every dump with `segmap`, and compare code only between runs of the same slave.

Traps:
- The built-in commands resume the emulator after each call, so a run of `gdb monitor ...`
  calls lets an unknown number of warp fields pass between them; a held mouse button then
  repeats in the menu. The tool's commands stop first and stay stopped.
- A menu click needs at least about 6 fields of press; a longer press repeats.
- The `a1200-030` preset's MMU-model core records no instructions: trace with
  `EXTRA_ARGS=--uae_mmu_model=0` (same cycle-exact 68030).
- Where the hunks load depends on the setup: in fast memory (`$940000`–`$A00000`) on the
  fast-memory setups, in chip RAM on `a1200`, which has no fast memory (`dump`'s default
  range), and in slow memory (`$C00000`–`$D80000`) on `a500-1.5m`. The plain `a500` has
  too little memory for the slave. Map each trace with a dump from the same run. `segmap` checks that the Framer
  task's name pointer points back at the name, because a stale copy of the name also turns
  up in chip RAM.
- Ghidra headless needs Homebrew's `openjdk@21` (`ghidra` sets `JAVA_HOME`). The installed
  12.x has no native decompiler, so work from the listings and the call graph.
