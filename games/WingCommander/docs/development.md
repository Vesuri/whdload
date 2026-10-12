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
ROM and launcher variables. The launcher selects the shared A1200-fast preset unless overridden.
Install shared prerequisites through AmigaXDev; ROM/OS sources are user supplied.

## Current commands

Fetch, input verification, archive preparation, static identification, reconstruction,
windowed boots and a state-driven A/B gate are implemented.
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


### Native debugger input and the extended phase 2 gate

The installed shared native emulator does not yet implement AmigaXDev's planned
common input API. `tools/build_debugger.py` adapts the existing 4D Sports Driving
raw-key route onto a **local copy** of the configured shared aprof build. It uses
the native Amiga keyboard queue, never host events or writes to game state.
`monitor inputcaps` must return `key-raw-v1`; `monitor key HEX 1|0` queues a press
or release. The gate sends Escape (`45`) and Return (`44`) only. An unsupported
emulator fails before the route starts.

The builder requires `FSUAE_SOURCE` (default `${AMIGA_SHARE}/fs-uae-aprof-build/fs-uae`),
its configured dependencies/objects and the host compiler. It checks the source
revision and modified-file digests in `manifest/debugger.tsv`, copies that build
under `tmp/`, recompiles the two changed translation units and links locally.
It does not install or overwrite shared files. This is a rebuild from the supplied
configured toolchain, not a self-contained emulator release. Every capture records
the actual emulator and slave SHA-256.

```sh
. amiga/env.sh
python3 tools/build_debugger.py --output tmp/debugger
export FSUAE="$PWD/tmp/debugger/fs-uae"
python3 tools/reconstruct.py --output tmp/control
python3 tools/reconstruct.py --verify --output tmp/verify
python3 tools/reconstruct.py --verify-control --output tmp/verify-control

# Locate the live patched LoadSeg chain; reject file/PRELOAD copies.
python3 tools/boot_gate.py --calibrate --output tmp/calibration
# Fresh original/reconstruction boots, Custom5=0,1,2,3, sequentially:
/bin/bash tools/ab_boots.sh tmp/ab tmp/calibration/layout.json \
  tmp/control/WingCommanderCD32.Slave
```

The A/B driver retains both the campaign menu and the simulator's name prompt.
It skips the logo and credits with **separate** Escape presses, because the game
clears its skip flag between them. It selects the Vega campaign with Return and
then supplies no input through the simulator. It stops before entering a name.
This is the user-selected extension of phase 2; it does not introduce phase 3's
unskipped intro window, frame counter or performance profile.

Checkpoints use English hunk-0 offsets, converted through a calibrated live
segment chain: `1898a` input poll, `1fbba` credits entry, `20164` menu entry,
`20214` menu ready, `20226` selection accepted, `1744c` name prompt call, and
`16fc6` the first name-input-loop iteration. A run that never reaches its next
checkpoint fails after a bounded timeout; it never counts as a pass.
`--simulator` enables the extended route for an individual `boot_gate.py` run.
All output directories must be new and below `tmp/`; previous runs are preserved.

Each checkpoint dumps the complete four live game hunks before advancing one
field for its Barto screenshot. These screenshot traces are not instruction-cost
profiles. The comparison checks **291,288 bytes and every RGB pixel**, without
clock masks, pointer normalisation, excluded rows or ignored data ranges. It
also requires identical placements, checkpoint/input routes and emulator config.
The source image, running register dump, action log, raw fast-RAM snapshots and
emulator logs remain under each run directory. GDB dump paths stay relative to
support checkout names containing spaces.

```sh
python3 tools/compare_boots.py tmp/ab/original-0 tmp/ab/reconstructed-0
python3 tools/compare_boots.py --name tmp/ab/original-0 tmp/ab/reconstructed-0
```

### VERIFY seam

The ordinary reconstructed slave is byte-identical. `--verify` replaces only the
four-byte call at `S:14da` with a call to the appended seam in `whdload/verify.s`.
It still calls the original resload_PatchSeg and preserves its register/CCR outputs.
`CUSTOM1=0` is English, `CUSTOM1=1` remains German; diagnostic `CUSTOM1=2` uses
English and sets the marker at `S:1e34` to one. With the option disabled the marker
stays zero. No new game patch or timing/rendering change is installed.

The larger VERIFY file changes allocation placement. `--verify-control` appends
the same unused tail while retaining **every original payload byte**, so it gives
an equal-size control for exact live-state/picture comparisons without relocation
heuristics. Calibrate this size separately, then use that layout for both builds:

```sh
SLAVE="$PWD/tmp/verify-control/WingCommanderCD32.Slave" \
  python3 tools/boot_gate.py --calibrate --output tmp/verify-calibration
SLAVE="$PWD/tmp/verify-control/WingCommanderCD32.Slave" WHD_ARGS=CUSTOM5=0 \
  python3 tools/boot_gate.py --simulator --layout tmp/verify-calibration/layout.json \
  --output tmp/verify-reference
SLAVE="$PWD/tmp/verify/WingCommanderCD32.Slave" WHD_ARGS=CUSTOM5=0 \
  python3 tools/boot_gate.py --simulator --layout tmp/verify-calibration/layout.json \
  --output tmp/verify-off
SLAVE="$PWD/tmp/verify/WingCommanderCD32.Slave" WHD_ARGS='CUSTOM1=2 CUSTOM5=0' \
  python3 tools/boot_gate.py --simulator --layout tmp/verify-calibration/layout.json \
  --output tmp/verify-on
python3 tools/check_verify.py tmp/verify-reference tmp/verify-off tmp/verify-on
```

The marker is in the retained `fast.bin`, at `result.json`'s slave base minus
`0x200000` plus `0x1e34`. It is not part of the game hunk comparison. A changed
input hash, lost live patch, truncated hunk, one changed data byte or one changed
pixel must fail its respective gate.

Phase 2 gate complete: all four Custom5 cases pass at both endpoints; VERIFY
off/on match the equal-size control and their markers are 0/1 respectively.
The full retained matrix is `tmp/phase2-ab/`. Scope and code/file offsets are
recorded in `internals.md`. Stop here; phase 3 needs separate authorisation.
