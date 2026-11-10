# Development

Only what differs from the repository's `docs/running.md` and `docs/building.md`.

## Inputs

`inputs.sha256` pins two archives; `make unpack ARCHIVES=<directory>` installs both, no
`game_unpack` needed:

| Archive | Unpacks to | What |
|---|---|---|
| `Encounter.lha` | `tmp/game/EncounterHD` | the whdload.de install package: slave 1.2, Patcher imager, Install, ReadMe, `source/` (`EncounterHD.asm`, Harry's `encounterimager05.asm`, a Barfly `Makefile`) |
| `Encounter_v1.2_0651.lha` | `tmp/game/Encounter` | the installed game (SPS 0651): `disk.1`, the same 1.2 slave as `Encounter.slave` |

The two archives' slaves and ReadMes are identical, and the package's `EncounterHD.asm` is
byte-identical to upstream's `E/Encounter/usr/source/EncounterHD.s` (`src/`).

## Build

The default vasm build (`-m68000 -x -devpac -Fhunkexe -nosym`), no defines. It is not
byte-identical to the shipped slave (672 bytes; ours is 656, recorded in
`release/slaves.sha256`), and cannot be without changing the source: JOTD assembled it
with Barfly (`IFD BARFLY`), which

- appends the build date to `DECL_VERSION`, twice (`1.2 (07-jan-08  22:52:49)` in the
  info text and in `$VER`), from `INCBIN "T:date"` under `IFD BARFLY`; vasm cannot take that
  branch (`OUTPUT`, `BOPT`, `SUPER`, `DOSCMD` are Barfly directives), so ours says `1.2`;
- optimises (`BOPT O+`): `moveq` for `move.l #1`, `moveq #$6F; not.b` for `move.l #$90`,
  `bsr.s` for the explicit `bsr.w DBFD1`, `addq` for `add.l #resload_Abort`, `clr` for the
  `move #0` stores to `$DFF101`, `$DFF104`, `$DFF106`, and `andi`/`cmpi` encodings where
  vasm uses `and #`/`cmp #`.

Compared after the strings (shipped code from file offset `$CC`, ours from `$A0`,
disassembled with objdump): the same instruction sequence, differing only in those
encodings and the PC-relative offsets they move. The header differs only in the offsets of
the code and strings (`ws_GameLoader`). vasm's own optimiser (`-opt-clr`, no `-devpac`)
gets closer (628 bytes) but still not identical; the repository default is kept.

## Running

`SETUP=a500` (the default) and `a1200` (`SETUPS`). Direct slave: `KICKS` is empty.

```sh
WARP=1 WINDOW=none python3 tools/encounter.py serve &   # boot with the gdb stub
python3 tools/encounter.py wait 8
python3 tools/encounter.py shot tmp/shots/x.png
python3 tools/encounter.py quit
```

Without `BUTTONWAIT` the title picture is up only during the main load and the game
starts its attract-mode demo (in play, score counting) within a few seconds under `WARP=1`;
`WHD_ARGS=BUTTONWAIT` holds the title screen ("Loading - please wait") for a screenshot.
`SLAVE=original` boots the shipped 1.2.

## Benchmark

`tools/bench.py OUT` is the repeatable level-1 profiling run: `tools/boot.sh` boots a
server stopped at the game's entry (`BOOT_BREAK=0xD7E2`, `WARP=1 DETERMINISTIC=1 JOY0=none`),
`tools/route.py` plays the route (`start`: fire on the 60th pass of the title loop, which
seeds the level; `aim`: 25 fields, 8 fields of right turn, fire held), and the next 500
fields (10 s) are traced in 100-field chunks and reduced. Results go to `OUT/report.txt`
(fps, fields per frame, work per frame and its timeline, pacing wait, DMA slots, hot PCs, the
main-loop routines), `OUT/profile.pkl.gz`, `OUT/chip.pkl.gz` with `OUT/chip.txt`, and
`OUT/end.png`.

```sh
EXTRA_ARGS=--uae_mmu_model=0 python3 tools/bench.py tmp/prof/030   # a1200-030 (the default SETUP)
SETUP=a500 INSTANCE=a500 python3 tools/bench.py tmp/prof/a500
```

- Traces need a cycle-exact CPU without an MMU model, hence `--uae_mmu_model=0` on the
  a1200-030 (WHDLoad does not use a 68030's MMU without its `MMU` option). Two such runs give
  byte-identical reports.
- In the window the level-1 enemy appears ahead, fires one shot that misses, and is destroyed
  at fields 140–200 (a1200-030) or 200–300 (a500). The run ends at score 15, targets 16,
  shield 4 on the a1200-030 with and without MMU emulation and on the a500. Check
  `end.png` after any change: the world is stepped per frame, so a build that changes the frame
  timing can change what happens ([internals.md](internals.md), "Frames and time").
- `start` anchors fire on the title loop, not on a field count, because the title calls the
  RNG once per pass and its setup takes a different number of fields on each machine.
  Anchored this way the a500 and the a1200-030 get the same level (17 targets).
- `tools/chipprofile.py` reduces the same chunks to the CPU's chip accesses per routine.
  It splits them into code fetches, data reads and writes and custom-register accesses,
  assigning each colour-clock slot to the instruction running at that point of the field
  (accurate to a few slots). Kept per top-level routine are the 16-byte granules read,
  written and fetched with their counts, and per DMA channel the 256-byte pages it
  touched. `python3 tools/chipprofile.py OUT/chip.pkl.gz` prints the summary (`chip.txt`).
  Interrupt context is told by the SR mask (IPL above 2), not by trace gaps, which on the
  68020/030 core also follow `rte`.
- `route.py` also takes `sheet N K NAME` (a contact sheet) for finding new routes; each
  screenshot traces one field, which changes the frame timing on the 68030 core.

## Traps

- The program region `$6000`–`$13000` is encrypted in `disk.1`; read patched instructions
  from a decrypted image (the loop in `src/EncounterHD.s`, [internals.md](internals.md)),
  not from the file.
- No release is possible from 1.2 as it is: the packager needs a dated `$VER` and a ReadMe
  that differs from the original and names the version. `release/release.json` replaces
  the slave, the ReadMe and `source/EncounterHD.asm` by name and keeps the imager source
  and Makefile as shipped (the `source` drawer option would drop them).
