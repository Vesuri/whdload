# Development

## Inputs

The [official install page](https://whdload.de/games/WingCommander.html) identifies
Psygore's v1.0 installer. The user supplied the Retroplay OCS (SPS 1657) and CD32
full-install URLs. Exact URLs and initial-download SHA-256 fingerprints are in
`manifest/inputs.tsv`; these fingerprints pin the received files, not an
independently authenticated upstream release.

`make fetch` downloads missing inputs and checks them before accepting them.
`make verify` checks every cached archive. `make prepare` verifies each archive
before extracting to separate `tmp/originals/installer`, `tmp/originals/ocs` and
`tmp/originals/cd32` directories. Extraction requires `lha` on PATH. Existing
extractions are left untouched; their contents are not revalidated by this target.
Failed downloads or extractions are retained in ignored scratch storage.

The originals are reference copies. Later emulator work should use separate
working copies under `tmp/game/`. Never commit archives or extracted contents.

## Shared environment

Source `amiga/env.sh`, which sources `${AMIGA_ENV}` or the conventional
`~/.local/share/amiga/env.sh`. The shared environment supplies toolchain, WHDLoad,
ROM and launcher variables. This scaffold makes no project-specific overrides.
Install shared prerequisites through AmigaXDev; ROM/OS sources are user supplied.

## Current commands

Fetch, checksum verification, archive preparation and CD32 static identification
are implemented.
The phase 2 launcher and byte-identical reconstruction are available; the boot gate is in progress. All shell tooling is written
for `/bin/bash` 3.2 and supports the project name's space.

## Phase 1: reproducible CD32 static identification

Use the shared environment's Python/amitools and `amigaxdev` modules,
`AMIGA_TOOLCHAIN` objdump, and `lha` on PATH. `WHDLOAD/Include/whdload.i`,
`WHDLOAD/Src/sources/whdload/kick31.s` and the `NDK/lvo/*_lib.i` headers supply
API/patch names. The installed KickEmu source is a reference for naming only,
not a claim that it is the 2014 slave's exact source. `hunktool` is not required
(the installed CLI currently depends on unavailable machine68k); this tool
imports the non-executing HunkReader directly.

From the project root, in `/bin/bash` 3.2:

```sh
. amiga/env.sh
/bin/bash tools/inputs.sh verify
python3 tools/cd32_static.py --output tmp/cd32-static
```

The output directory must be new and below `tmp/`; use a different name on
subsequent runs. The script verifies the installer/CD32 archives against
`manifest/inputs.tsv` **before extraction**, extracts fresh copies only inside
that output directory, compares every reference game-directory file and its
file set, and checks that the two slaves match. A differing reference or input
causes failure and is preserved. Failed scratch runs are also retained. It
checks the game's CRCs against the slave selectors and validates hunk payload
file offsets, patch extents/counts and helper destinations before emitting the
inventory. No emulated CPU, game routine,
Kickstart image, or WHDLoad executable is run.

Outputs, all ignored:

- `inventory.json`: file hashes, CRCs, hunk records, file offsets and allocations.
- `patches.json`: all seven static lists (three ROM, two game common, two
  Custom5=4 prefixes). NEXT is recorded and its target listed separately.
- `*.h0.bin`, `*.h1.bin`, `*.h3.bin`: extracted file-backed hunks, using the
  **actual hunk index** (hunk 2 is BSS and has no file).
- `*.dis`, `*.strings`, `*.candidates`: linear disassembly, strings and a raw
  constant/negative-vector-call census; code/data mixtures can give false hits.
- `slave-START-END.dis`: entry-aligned slave code regions, avoiding data islands.
- `cd32/` and `installer/`: fresh verified archive trees.

To reproduce an individual code inspection (all numbers are hunk offsets;
zero is the artificial disassembly base, not a runtime address):

```sh
python3 -m amigaxdev.disasm dis --cpu 68020 \
  tmp/cd32-static/wing.english.h0.bin 0 0x33618 0x33848
python3 -m amigaxdev.disasm dis --cpu 68020 \
  tmp/cd32-static/WingCommanderCD32.Slave.h0.bin 0 0x178a 0x17ee
python3 -m amigaxdev.disasm dis --cpu 68020 \
  tmp/cd32-static/wing.english.h3.bin 0 0x1530 0x1562
python3 -m amigaxdev.patchlist \
  tmp/cd32-static/cd32/WingCommanderCD32/WingCommanderCD32.Slave 0x15e6
python3 -m amigaxdev.patchlist \
  tmp/cd32-static/cd32/WingCommanderCD32/WingCommanderCD32.Slave 0x1cf4
```

To list every reference to the VBL counter and countdown (A4-relative and
relocated absolute), for the inventory in `internals.md`:

```sh
python3 -I tools/clock_refs.py tmp/cd32-static/cd32/WingCommanderCD32/data/wing.english \
  tmp/cd32-static/wing.english.h0.dis 7f00 7f07
python3 -I tools/clock_refs.py tmp/cd32-static/cd32/WingCommanderCD32/data/wing.german \
  tmp/cd32-static/wing.german.h0.dis 7f2c 7f33
```

Both print 32 lines. Any data-hunk range works the same way.

Do not run the shared patch-list CLI over the Custom5 prefixes: its decoder
prints NEXT but continues linearly with the old base. The inventory tool stops
at NEXT and records the destination common list separately.

Search both languages and all file-backed hunks; then inspect instruction
boundaries and establish each library/hardware base before naming a hit:

```sh
rg 'library|device|resource|interrupt' tmp/cd32-static/*.strings
rg 'constant|candidate call' tmp/cd32-static/*.candidates
rg 'dff|bfe|bfd|cacr|stop|rte' tmp/cd32-static/*.dis
rg 'WaitTOF|WaitBlit|AllocBitMap|ChangeVPBitMap|GetColorMap' \
  "$NDK/lvo/graphics_lib.i"
rg 'Timer|ElapsedTime|VBlank|ReadJoyPort|SetJoyPort' \
  "$NDK/lvo/lowlevel_lib.i"
```

The raw scan includes all CIA register addresses, the custom-register range,
Akiko and the level-3 vector constant, and negative calls via any address
register. Base-relative accesses must be followed manually: e.g. CIA-B TOD at
`E:27e5c`, graphics base at `E:33858`, lowlevel base at `E:33d8e`. Search results
are candidates, not a control-flow proof. Computed addresses, OS/library code,
resource-loaded code and generated copper contents remain coverage limits.
No assets were unpacked to infer script timing.

Phase 1 verification: archive digests and fresh/reference tree identity passed;
English/German CRC-16s matched `88e7/ced7`; hunk records parsed successfully;
all 22 common patch targets per language and both prefix writes fit game hunk 0;
all slave helper destinations fit its code hunk; ROM lists have 54/54/58 entries.
Existing-output/outside-tmp refusal and a deliberately bad archive digest are
checked without changing the real inputs. These checks validate static tooling
and provenance; they do not validate game behavior or measure speed.

## Phase 2: reconstruction and first boots

The reconstruction generator verifies the original slave SHA-256 before decoding
its code islands with Capstone and emitting Motorola source under a new `tmp/`
directory. vasm assembles every instruction with optimisation disabled; offset
assertions and a full-file comparison reject any drift. Data islands remain data,
including the original KickEmu tables. No replacement KickEmu version is used.

```sh
. amiga/env.sh
python3 tools/reconstruct.py --output tmp/reconstructed
SLAVE="$PWD/tmp/reconstructed/WingCommanderCD32.Slave" /bin/bash amiga/run.sh
/bin/bash amiga/run.sh stop
WHD_ARGS=CUSTOM5=0 WINDOW=front python3 tools/wc.py serve
# In a second shell with the same environment:
python3 tools/wc.py shot tmp/boot.png
python3 tools/wc.py quit
```

`amiga/run.sh` is adapted from Legends of Valour. Defaults: native `FSUAE_ARM`,
shared `AMIGA_SETUP=a1200-fast`, PAL, 68EC020, 2 MiB chip plus 8 MiB fast, windowed,
real speed. `WHD_ARGS` selects the original Custom options. Each boot extracts a
fresh pinned CD32 archive into a new scratch drive directory; no existing game
or boot tree is replaced. `KICKSTART_A1200`, `RTB_A1200` (default ROM path + `.RTB`),
`WORKBENCH_ADF` and `WHDLOAD_BINARY` come from the supplied shared environment.
`FSUAE_RUN` must resolve below project `tmp/`; interactive and debugger defaults
are `tmp/run` and `tmp/cap`. Process cleanup uses `FSUAE_COMMON`.

The `wc.py` adapter uses `amigaxdev.gdbserve`; disassembly and trace readers remain
shared modules. `until` is bounded by `UNTIL_TIMEOUT` (60 seconds by default).
The installed native build supports one-field trace screenshots but rejects
`monitor key` with E01. AmigaXDev currently lists shared debugger input as open
work; do not silently substitute host input or write game control variables.
Instruction profiling on the native build needs a separately validated profiler
window; phase 2 does not make performance claims.

