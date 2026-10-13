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
windowed boots, a state-driven A/B gate and experimental phase-6 rendering
builds/checks are implemented.
The phase 2 launcher and byte-identical reconstruction are available; the phase 2 boot gate is complete. All shell tooling is written
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
recorded in `internals.md`. Phase 3 is now separately authorised.

## Phase 3: unskipped intro and frame counter

Use the original English slave, `CUSTOM5=0`, and PAL A1200-fast with its stock
020 multiplier (4).
The phase 3 tools set `INTRO_STOCK_CLOCK=1`: the project launcher replaces numeric
frequency with multiplier 4/frequency 0 in the shared preset result. It neither
modifies shared files nor changes the phase 2 default. The pinned core overflows
its numeric-frequency calculation (observed cycle unit 115); the stock setting
yields 128. Both tools reject a boot whose emulator log does not confirm 128.
Do not use duplicate `EXTRA_ARGS` CPU options: this core reparses even options
that the frontend reports as ignored.

The route plays the complete Origin animation, title animation and all 18
flight/credits pages. The credits repeat indefinitely without input: after
page 17 completes at `E:1fe48`, the harness waits for the next input poll, presses
Escape, and releases it on menu entry. No earlier input is sent.

Build a fresh local debugger with the read-only observer. Shared files and game
bytes are unchanged. The added source input is pinned in `manifest/debugger.tsv`.
The `trace-window-all` monitor command explicitly enables RAM instruction PCs;
its acknowledgement is mandatory. The observer runs in the cycle-exact 68020
interpreter and records selected PCs, registers, physical fields, emulator cycle
stamps and game music state. It does not insert guest instructions or change
registers, memory, clocks or inputs. Other CPU backends are not validated.

From the project root, with new output names:

```sh
. amiga/env.sh
python3 tools/build_debugger.py --intro-observer --output tmp/intro-debugger
export FSUAE="$PWD/tmp/intro-debugger/fs-uae"
INTRO_STOCK_CLOCK=1 python3 tools/boot_gate.py --calibrate --output tmp/intro-layout
python3 tools/intro_counter.py --layout tmp/intro-layout/layout.json \
  --output tmp/swap-only
python3 tools/intro_capture.py --layout tmp/intro-layout/layout.json \
  --output tmp/intro-one
python3 tools/intro_capture.py --layout tmp/intro-layout/layout.json \
  --output tmp/intro-two
python3 tools/intro_check.py tmp/intro-one --repeat tmp/intro-two \
  --counter tmp/swap-only > tmp/intro-check.json
python3 tools/intro_report.py tmp/intro-one > tmp/intro-report.json
python3 tools/intro_negative.py tmp/intro-one --output tmp/intro-negative \
  > tmp/intro-negative.json
```

Run sequentially. Each tool stops its owned emulator even on failure. A missing
checkpoint times out and cannot pass. The default full-trace windows are 20
fields each, in Origin animation and the first flight/credits page. Keep
`intro_counter.py --fields` and `intro_capture.py --trace-fields` equal when
changing the validation window.

`intro_counter.py` is the independent **SWAP_ONLY** arm: GDB observes the game
VBL entry and publication entry with read-only breakpoints, using debugger-local
variables only. The host observer is disabled for this run. `intro_check.py`
requires the same game-clock interval and identical per-field publication counts
as the full trace. It also compares all watched PCs/registers against the host
ledger, with one constant physical-field offset and no missing edge events.

The long-run ledger counts publications without stopping at each frame. Scene
screenshots advance emulation normally while the ledger keeps recording, so those
intervals are included. The title image is sampled at animation index 185, not at
a wall-clock delay. All 18 credits pages are checked against the game's page
index. Each screenshot retains its full one-field trace (20 fields at validation
points) and fast-RAM snapshot. The repeat gate compares every ledger row from
reset through the first menu-ready instruction, every RGB pixel at all milestones
and all 291,288 allocated game-hunk bytes per snapshot. Debugger-disconnect and
shutdown events are outside that window; the separate menu screenshot is still
checked exactly.

`intro_report.py` rejects broken entry/store/return accounting, missing VBLs,
nonmonotonic timestamps and unexpected video clocks. It reports each scene's
physical-field span, emulated seconds, publication count, within-scene field-gap
histogram, other copper writes and tracker position at both cuts. Seconds use
UAE's cycle stamps and clock conversion, not host time or an assumed exact 50 Hz.
Loading and holds are included in scene duration; the gap mean uses consecutive
publications inside that scene and is absent with fewer than two publications.
Palette-only changes are not buffer publications.

`intro_negative.py` requires rejection after removing a publication event, moving
one to the wrong field, changing one screenshot pixel, or changing one allocated
game-hunk byte. It writes damaged fixture copies only below its new `tmp/` output.

All captures, generated observer configuration, input logs, register records and
reports stay in `tmp/`. Retained phase 3 evidence uses `tmp/intro-pal-a/`,
`tmp/intro-pal-b/`, and `tmp/intro-pal-counter/`. Phase 4 profiling is a separate gate.

## Phase 4: practical baseline and reproducibility

The practical-baseline gate is complete under the scope approved on 2026-10-12.
The commands below include both accepted measurements and diagnostic preflights;
read their stated limits before reusing a result. Early preflights alone do not
establish calibrated accelerated timing.
See `internals.md` for the observed limitations. Use fresh output names and run
emulators sequentially. Shared source files, CPU presets and game inputs remain
unchanged; all generated files stay below `tmp/`.

```sh
. amiga/env.sh
python3 tools/reconstruct.py --cache-audit --output tmp/cache-audit-slave
python3 tools/reconstruct.py --output tmp/stock-recheck
python3 tools/build_debugger.py --matrix-observer --output tmp/matrix-debugger
export FSUAE="$PWD/tmp/matrix-debugger/fs-uae"
```

The stock rebuild must report `byte_identical: true`. `--cache-audit` is a separate
terminating VERIFY build, mutually exclusive with the earlier VERIFY modes. It
runs the original cache request before read-only API/CACR queries and logs its
result. It cannot be used for a performance capture.

Run the 15 cache audits (Bash 3.2 compatible):

```sh
for cell in 020 030 030-mmu 040 060; do
    case "$cell" in
        020)     machine=a1200-fast; base_options='' ;;
        030)     machine=a1200-030;  base_options='' ;;
        030-mmu) machine=a1200-030;  base_options=MMU ;;
        040)     machine=a1200-040;  base_options=NoMMU ;;
        060)     machine=a1200-060;  base_options=NoMMU ;;
    esac
    for mode in default dcache nocache; do
        case "$mode" in
            default) options="$base_options" ;;
            dcache)  options="${base_options:+$base_options }DCache" ;;
            nocache) options="${base_options:+$base_options }NoCache" ;;
        esac
        python3 tools/cache_audit.py --machine "$machine" --options "$options" \
          --slave tmp/cache-audit-slave/WingCommanderCD32.Slave \
          --output "tmp/cache-$cell-$mode" || break 2
    done
done
```

Each audit preserves the WHDLoad log, numeric fields and slave/emulator digests.
The audit runner checks the supplied build digest and stops its owned emulator
on success or failure. A changed input is never overwritten.

Probe the original slave's backend coverage separately:

```sh
python3 tools/matrix_probe.py --machine a1200-fast --output tmp/probe-020
python3 tools/matrix_probe.py --machine a1200-030 --output tmp/probe-030
python3 tools/matrix_probe.py --machine a1200-030 --options MMU --output tmp/probe-030-mmu
python3 tools/matrix_probe.py --machine a1200-040 --options NoMMU --output tmp/probe-040
python3 tools/matrix_probe.py --machine a1200-060 --options NoMMU --output tmp/probe-060
python3 tools/matrix_trace.py tmp/probe-020/credits.bin > tmp/probe-020/trace-report.json
```

The probe calibrates relocated hunks, stops at `E:1fdd6`, reads the actual CPU/cache
configuration via `monitor wc-audit`, enables `trace-window-all`, and captures five
fields. Its `complete` field means the **preflight completed**, not that profiling
is valid. Require nonempty instruction coverage and a supported aggregate profiler
before interpreting costs. An accelerated trace with no PC records must be rejected
by `matrix_trace.py`, not reported as zero utilisation. The phase 4 preflights retain
this negative control. `NoMMU` here is a WHDLoad option, not an emulator-model override.

### Experimental 020 scene census

The stock-multiplier 020 capture checks model, MMU backend, cycle-exact mode
and actual cycle unit 128. Accelerated capture modes are documented below. Its cache audit
must match the requested options. The same original slave plays the complete
intro and credits cycle, then takes the phase 3 state-driven Escape route to the
menu. There are no debugger stops inside individual scene windows.

```sh
python3 tools/matrix_capture.py --layout tmp/probe-020/result.json \
  --audit tmp/cache-020-default/result.json --output tmp/profile-020-default
python3 tools/matrix_capture.py --layout tmp/probe-020/result.json \
  --audit tmp/cache-020-nocache/result.json --options NoCache \
  --output tmp/profile-020-nocache
python3 tools/matrix_report.py tmp/profile-020-default > tmp/profile-020-default/report.json
python3 tools/matrix_report.py tmp/profile-020-nocache > tmp/profile-020-nocache/report.json
python3 tools/matrix_negative.py tmp/profile-020-default --output tmp/matrix-negative
```

`matrix_observer.inc` observes scene cuts, publication entry and chunky c2p input;
it writes no guest memory/registers and inserts no guest instructions. It uses
`WC_MATRIX_CONFIG`/`WC_MATRIX_DIR`, generated by the capture runner, and stays
inactive when both are absent. Its aggregate profile is reset at every cut.
Change comparisons reset at scene or geometry changes; unchanged first frames
are not counted as comparison evidence.

Reports check scene order, profile/ledger clocks, PC/context accounting, PAL clock
conversion, cache state and change-count bounds. They retain raw self/inclusive
contexts and unmatched-return counters but explicitly report
`validated_baseline: false`. Structural agreement alone cannot certify the context
attribution, interrupt/idle classification or observer neutrality. The current
unmatched returns must be resolved before accepting general routine percentages.
Independent scene counters support the separately checked ceiling comparisons. The negative test creates damaged
fixtures below its fresh `tmp/` output and requires rejection of every one.

Retained phase 4 results, per-instrument validation and binary digests are listed
in `internals.md`. General routine accounting remains a documented deferred gap.


### Diagnosing aggregate instruction addresses

`--matrix-observer` now includes the stable executing-PC correction described in
`internals.md`. Standalone probes can request it with `--aprof-stable-pc`.
`--aprof-diagnostics` logs unmatched returns and the top four saved contexts to
the run's `fsuae/Cache/Logs/fs-uae.log.txt`; use it only for short diagnostic runs.
This logger does not resolve context attribution.

```sh
. amiga/env.sh
python3 tools/build_debugger.py --aprof-diagnostics --output tmp/pc-control-debugger
FSUAE="$PWD/tmp/pc-control-debugger/fs-uae" python3 tools/matrix_probe.py   --machine a1200-fast --output tmp/pc-control
python3 tools/build_debugger.py --aprof-diagnostics --aprof-stable-pc   --output tmp/pc-fixed-debugger
FSUAE="$PWD/tmp/pc-fixed-debugger/fs-uae" python3 tools/matrix_probe.py   --machine a1200-fast --output tmp/pc-fixed
python3 tools/matrix_pc_check.py tmp/pc-control tmp/pc-fixed > tmp/pc-check.json
```

The checker requires identical instruction PC/cost/register streams, field
cycle/idle totals, screenshots, colours and the trace's memory snapshots. Every
trace PC's instruction count and cost must be covered by the wider aggregate
window. It records DMA/custom snapshot differences without erasing them and does
not certify context accuracy or complete observer neutrality. As a negative
control, use `tmp/pc-control` as both arguments: the old aggregate must fail the
PC-coverage check. Raw traces do not include fast RAM, so trace snapshot equality
must not be described as a full-memory comparison.


### Checking modified slave return addresses

Continue from the stable-PC diagnostic control above. This is still a short
instrument check, not a routine-cost baseline:

```sh
python3 tools/build_debugger.py --aprof-diagnostics --aprof-stack-returns \
  --output tmp/stack-return-debugger
FSUAE="$PWD/tmp/stack-return-debugger/fs-uae" python3 tools/matrix_probe.py \
  --machine a1200-fast --output tmp/stack-return-probe
python3 tools/matrix_stack_check.py tmp/pc-fixed tmp/stack-return-probe \
  > tmp/stack-return-check.json
```

The checker combines unchanged trace execution with direct inspection of each
observed call/return around `S:0596–05b6`. It requires the original saved stack
slot to be consumed, the successor to advance four bytes, exactly five recovered
returns, and unchanged aggregate clocks/chip accounting. The other unmatched
returns remain explicit. Do not enable this experimental option to claim a
passing whole-scene call-context gate.


### Independently checking a chunky-census sample

Build the current matrix observer, which includes the stable-PC correction. Use
fresh output names and the existing completed 020 layout/cache audit:

```sh
python3 tools/build_debugger.py --matrix-observer --output tmp/census-debugger
FSUAE="$PWD/tmp/census-debugger/fs-uae" python3 tools/matrix_capture.py \
  --layout tmp/probe-020/result.json --audit tmp/cache-020-default/result.json \
  --chunky-oracle --output tmp/census-oracle
python3 tools/matrix_census_check.py tmp/census-oracle > tmp/census-check.json
```

`--chunky-oracle` takes six GDB memory snapshots at the first six Origin-animation
c2p entries, before the read-only observer processes each call. It then finishes
the same intro/credits/menu route. The snapshots and metadata stay under the
output directory. This option deliberately introduces debugger stops and must
not be used as a timing baseline. The checker compares independent source bytes
and blocks with the corresponding observer records; its verified scope is the
sampled 320×128 inputs. The retained negative control changes one source byte and
must fail at that sample.


### Recomputing every source-buffer change

The current observer can save all chunky inputs in one sequential stream. This
adds no debugger stops. It writes only under the run's `tmp/` directory and flushes
at scene cuts, including the final cut. Use the same local binary for the raw arm
and its control:

```sh
python3 tools/build_debugger.py --matrix-observer --output tmp/raw-debugger
export FSUAE="$PWD/tmp/raw-debugger/fs-uae"
python3 tools/matrix_capture.py --layout tmp/probe-020/result.json \
  --audit tmp/cache-020-default/result.json --raw-chunky --output tmp/raw-census
python3 tools/matrix_capture.py --layout tmp/probe-020/result.json \
  --audit tmp/cache-020-default/result.json --output tmp/raw-control
python3 tools/matrix_raw_check.py tmp/raw-census --control tmp/raw-control \
  --oracle tmp/census-oracle > tmp/raw-check.json
```

`--oracle` cross-checks the six independently captured GDB source buffers from the
preceding section. The full-stream checker separately recomputes every native
byte/block count, checks exact stream consumption, and rejects a truncated,
changed or extra buffer. The control comparison requires identical configuration,
every ledger record, every scene profile, final allocated game hunks and menu RGB
pixels. It tests raw-recording neutrality; both arms still have aggregate profiling
active. A changed-byte and a changed-profile negative control are retained under
`tmp/phase4-raw-negative/` and `tmp/phase4-raw-profile-negative/`.

The census is useful source-change evidence even while calling-context costs are
unvalidated. Do not reinterpret a passing raw-recording check as a complete
machine-matrix or aggregate-profiler-off gate.


### Isolating aggregate profiling from the counter/census

`--no-profiles` keeps the state-cut, publication and chunky census hooks but never
starts the aggregate profiler. It produces no `.aprof` files; `matrix_report.py`
explicitly rejects such a control as a routine-cost input. Change exactly one
feature within a comparison. For the default-cache pair, leave raw recording off
in both arms:

```sh
python3 tools/build_debugger.py --matrix-observer --output tmp/profile-control-debugger
export FSUAE="$PWD/tmp/profile-control-debugger/fs-uae"
python3 tools/matrix_capture.py --layout tmp/probe-020/result.json \
  --audit tmp/cache-020-default/result.json --output tmp/profile-on
python3 tools/matrix_capture.py --layout tmp/probe-020/result.json \
  --audit tmp/cache-020-default/result.json --no-profiles --output tmp/profile-off
python3 tools/matrix_raw_check.py tmp/profile-on --control tmp/profile-off \
  --compare-only > tmp/profiler-control.json
```

For NoCache, keep raw recording on in both arms to compare every source buffer as
well as the ledger, final hunks and menu pixels:

```sh
python3 tools/matrix_capture.py --layout tmp/probe-020/result.json \
  --audit tmp/cache-020-nocache/result.json --options NoCache --raw-chunky \
  --output tmp/nocache-profile-on
python3 tools/matrix_capture.py --layout tmp/probe-020/result.json \
  --audit tmp/cache-020-nocache/result.json --options NoCache --raw-chunky \
  --no-profiles --output tmp/nocache-profile-off
python3 tools/matrix_raw_check.py tmp/nocache-profile-on \
  --control tmp/nocache-profile-off > tmp/nocache-profiler-control.json
```

`aggregate_profiler_neutrality_pass` requires that only the `profiles` feature
changes. `recording_neutrality_pass` requires that only `raw_chunky` changes.
A combined comparison can pass `matched_execution_pass` without certifying either
isolated control. When both arms retain raw sources, the checker compares every
byte of those streams. None of these checks certifies the calling-context tree.


### Source-range costs for the call-free routines

After the preceding controls pass, compute the converter/limiter instruction
costs without using the unvalidated context tree:

```sh
python3 tools/matrix_leaf_report.py tmp/profile-on > tmp/default-leaf-costs.json
python3 tools/matrix_leaf_report.py tmp/nocache-profile-on > tmp/nocache-leaf-costs.json
```

The reporter verifies the pinned original, fully decoded leaf boundaries and
internal branches, absence of calls/external jumps, unchanged live routine bytes,
corrected executing-PC accounting, and entry counts against the per-height source
census. It deliberately excludes reset, when the slave's eventual address range
is not established. It reports instruction-body cost including its memory stalls,
not entry-to-return time including asynchronous work. All per-scene raw units and
entry counts remain in the output. The old pre-correction profile is retained as
a negative control and must be rejected.

`matrix_trace.py` now exposes application idle-marker units separately and labels
missing PCs without inferring STOP. Its zero `application_idle_marker_units` is
not a measured zero for CPU idle; `cpu_idle_measured` remains false. No idle claim
may be based on that optional trace field without a validated marker/hardware
instrument.

### Accelerated NOMMU-core preflight

The WHDLoad `NoMMU` option does not select the emulator CPU core. Use the explicit
project-local selector, following Hard Drivin' and Red Baron's timing setups:

```sh
. amiga/env.sh
export FSUAE="$PWD/tmp/phase4-profile-control-debugger/fs-uae"
python3 tools/matrix_probe.py --machine a1200-030 --nommu-core --output tmp/nommu-probe-030
python3 tools/matrix_probe.py --machine a1200-040 --nommu-core --options NoMMU --output tmp/nommu-probe-040
python3 tools/matrix_probe.py --machine a1200-060 --nommu-core --options NoMMU --output tmp/nommu-probe-060
```

`--nommu-core` sets `WC_NOMMU_CORE=1`; it replaces preset arguments instead of
adding duplicate options. The same switch is accepted by `cache_audit.py` for
separate matching VERIFY boots. It rejects WHDLoad `MMU` and the stock 020 preset.
The probe records effective settings, coverage and the selector in `result.json`.
Nominal frequency is still uncalibrated; these are preflights, not baseline FPS.

For a diagnostic 040 scene/census capture without instruction costs:

```sh
python3 tools/build_debugger.py --matrix-observer --matrix-nommu-counters \
  --output tmp/nommu-counter-debugger
export FSUAE="$PWD/tmp/nommu-counter-debugger/fs-uae"
python3 tools/cache_audit.py --machine a1200-040 --nommu-core --options NoMMU \
  --slave tmp/phase4-cache-slave/WingCommanderCD32.Slave --output tmp/nommu-audit-040
python3 tools/matrix_capture.py --machine a1200-040 --nommu-core --no-profiles \
  --options NoMMU --layout tmp/nommu-probe-040/result.json \
  --audit tmp/nommu-audit-040/result.json --raw-chunky --output tmp/nommu-scenes-040
```

This instrumentation is under validation. `matrix_capture.py` requires matching
core/cache options; 040/060 require `--no-profiles`. Accelerated results explicitly
record `clock_validated=false`. The existing 020 profile report cannot be used to
certify these counter-only captures. Repeat and counter-neutrality checks remain
required before using the new observer as a baseline instrument.

Validate a completed counter-only run and recompute its raw census:

```sh
python3 tools/matrix_scene_report.py tmp/nommu-scenes-040 > tmp/nommu-scenes-040/scene-report.json
python3 tools/matrix_raw_check.py tmp/nommu-scenes-040 > tmp/nommu-scenes-040/raw-check.json
```

Repeat the same capture into a fresh output directory without `--raw-chunky`, then
compare it with the raw capture using `matrix_raw_check.py --compare-only --control`.
The comparison now supports two counter-only runs and requires matching effective
CPU settings, ledgers, final game hunks and menu pixels. It does not infer CPU costs.
`--warp` changes host collection speed only; it is recorded separately and needs
its own matched comparison before being used for faster matrix collection.

The isolated 040 warp check passed with identical ledger/state/pixels. Reproduce
by repeating the recording-off capture with `--warp`, then comparing it against
the real-speed recording-off run:

```sh
python3 tools/matrix_raw_check.py tmp/nommu-warp-040 --compare-only \
  --control tmp/nommu-control-040 > tmp/nommu-warp-check-040.json
```

The changed-feature list must contain only `host_warp` and
`warp_neutrality_pass` must be true.

### Numeric-clock reference check

Build a local correction candidate and compare its numeric 020 clock to the
existing stock-multiplier trace:

```sh
. amiga/env.sh
python3 tools/build_debugger.py --matrix-observer --matrix-nommu-counters \
  --frequency-clock --output tmp/frequency-debugger
export FSUAE="$PWD/tmp/frequency-debugger/fs-uae"
python3 tools/matrix_probe.py --machine a1200-fast --numeric-clock \
  --output tmp/frequency-probe-020
python3 tools/matrix_pc_check.py tmp/phase4-stablepc-probe tmp/frequency-probe-020 \
  > tmp/frequency-stock-check.json
python3 tools/matrix_probe.py --machine a1200-030 --nommu-core --warp \
  --layout tmp/phase4-nommu-probe-030/result.json --output tmp/frequency-probe-030
```

`--layout` rechecks the previously verified segment chain with one dump at the
checkpoint, avoiding repeated boot dumps. `--numeric-clock` bypasses the stock
020 multiplier override. The successful reference comparison must report identical
instruction/memory/picture streams and zero DMA/custom differences. Clock units
are integer-quantised; see internals for the realised rates and model limits.

For the corrected 030 full capture, use the same binary for a fresh
`cache_audit.py --machine a1200-030 --nommu-core` run, then
`matrix_capture.py --machine a1200-030 --nommu-core --warp --raw-chunky` with its
matching audit and layout. `matrix_report.py` and `matrix_leaf_report.py` accept
covered 030 profiles; all reports retain incomplete-baseline status. Repeat with
only `--no-profiles` added and use `matrix_raw_check.py --compare-only --control`
to test aggregate-profiler neutrality. Failed runs have no `result.json` and must
never be substituted for a completed control.

### Prepare the VERIFY c2p ceiling fixture

```sh
python3 tools/reconstruct.py --ceiling control --output tmp/ceiling-control-slave
python3 tools/reconstruct.py --ceiling c2p --output tmp/ceiling-c2p-slave
```

Both builds have identical size/alignment; the control is the original bytes.
The builder rejects any unexpected difference outside the three converter entry
words. `matrix_capture.py --ceiling-slave PATH` accepts only these verified
fixtures, checks their digest/size, and records the arm in the result. Use the
same machine, cache audit and options for both arms once the fastest matrix cell
has been selected. This is a ceiling experiment, not a release rendering patch or
a picture-equivalence comparison.

The selected cell is 030 MMU/default. With the MMU-counter debugger described below built
and `FSUAE` set to its executable, reproduce the matched pair as follows (each
output directory must be new):

```sh
python3 tools/matrix_capture.py --machine a1200-030 --mmu-core --no-profiles \
  --warp --options MMU --audit tmp/phase4-mmu-audit-030/result.json \
  --layout tmp/phase4-mmu-scenes-030/result.json \
  --ceiling-slave tmp/ceiling-control-slave/WingCommanderCD32.Slave \
  --output tmp/ceiling-control-030-mmu
python3 tools/matrix_capture.py --machine a1200-030 --mmu-core --no-profiles \
  --warp --options MMU --audit tmp/phase4-mmu-audit-030/result.json \
  --layout tmp/phase4-mmu-scenes-030/result.json \
  --ceiling-slave tmp/ceiling-c2p-slave/WingCommanderCD32.Slave \
  --output tmp/ceiling-c2p-030-mmu
python3 tools/matrix_ceiling_report.py tmp/ceiling-control-030-mmu \
  tmp/ceiling-c2p-030-mmu > tmp/ceiling-c2p-comparison.json
```

`matrix_ceiling_report.py` validates both scene ledgers, matched settings,
retained fixture hashes, exact allowed byte differences and the three live
converter entry words in each arm. It compares scene 2 entry through scene 33
entry, excluding startup and the second-cycle/menu exit. A separate
`matrix_raw_check.py --compare-only --control` comparison of the original matrix
capture with the ceiling control verifies repeatability; do not use that
picture-equivalence checker on the intentionally incorrect bypass output.

### DMA summaries and the 030 MMU interpreter

```sh
python3 tools/build_debugger.py --matrix-observer --matrix-nommu-counters \
  --matrix-mmu030-counters --frequency-clock --matrix-dma --output tmp/matrix-dma-debugger
export FSUAE="$PWD/tmp/matrix-dma-debugger/fs-uae"
```

Add `--dma` to `matrix_capture.py` for experimental per-field DMA recording, then
run `matrix_dma_check.py RUN`. This checks coverage and the final field against
`RUN/menu.bin`; malformed totals, missing scene coverage and altered histograms
must be rejected. Compare a same-binary capture without `--dma` separately. The
current 030 pair fails exact timing neutrality but matches fields, publications,
change counts, game hunks and pixels; see the measured timing effect in internals.
Do not substitute an exact-neutrality pass for that result or label free bus slots
as CPU idle.

For the 030 MMU-capable interpreter, obtain separate cache audits for `MMU` and
`NoMMU` without `--nommu-core`, then capture with
`--machine a1200-030 --mmu-core --no-profiles --options MMU` (or `NoMMU`). Use the
corresponding previously verified layout: the MMU option changes placement.
The `tc030` audit field records actual translation control. These counter hooks
are under validation; general instruction profiling remains unavailable on this
interpreter.

Independent runs may use distinct `FSUAE_RUN` directories and explicit
`DEBUG_PORT` values. The strict ownership check must remain enabled; a busy port
must fail without stopping its listener. Current MMU diagnostics use port 2457,
separate from the NOMMU batch on 2456.


### Instant-blitter ceiling

Rebuild the local debugger using the matrix flags above to include
`immediate_blits` in `wc-audit`. Obtain a fresh matching cache audit, then run two
captures with the same control slave, emulator, audit, layout and options. Add
`--instant-blitter` only to the intervention arm. The runner explicitly requests
normal blits for the control and checks the effective setting at boot and the
menu. CPU and memory cycle-exact settings remain enabled in both arms.

```sh
python3 tools/cache_audit.py --machine a1200-030 --options MMU \
  --slave tmp/phase4-cache-slave/WingCommanderCD32.Slave \
  --output tmp/phase4-instant-audit-030
python3 tools/matrix_capture.py --machine a1200-030 --mmu-core --no-profiles \
  --warp --options MMU --audit tmp/phase4-instant-audit-030/result.json \
  --layout tmp/phase4-mmu-scenes-030/result.json \
  --ceiling-slave tmp/ceiling-control-slave/WingCommanderCD32.Slave \
  --output tmp/instant-control-030-mmu
python3 tools/matrix_capture.py --machine a1200-030 --mmu-core --no-profiles \
  --warp --options MMU --audit tmp/phase4-instant-audit-030/result.json \
  --layout tmp/phase4-mmu-scenes-030/result.json \
  --ceiling-slave tmp/ceiling-control-slave/WingCommanderCD32.Slave \
  --instant-blitter --output tmp/instant-on-030-mmu
python3 tools/matrix_ceiling_report.py tmp/instant-control-030-mmu \
  tmp/instant-on-030-mmu > tmp/instant-comparison.json
```

The checker requires identical original slave bytes and CPU settings except for
`immediate_blits=0/1`. It does not accept a command-line request without effective
readback. The pinned emulator permits immediate blits with cycle-exact CPU/memory;
its blitter start path copies the preference and completes the operation
immediately when blitter DMA is enabled. The intervention is a diagnostic bound,
not a supported hardware configuration.

The completed pair is retained under `tmp/phase4-instant-{control,on}-030-mmu/`.
The same report also compares final allocated game hunks and menu pixels; those
are observed equal for the instant-blitter pair, while incorrect converter-bypass
pixels are expected. For the debugger-readback extension's control repeat, compare
the complete ledgers directly:

```sh
cmp tmp/phase4-ceiling-control-030-mmu/matrix-events.txt \
  tmp/phase4-instant-control-030-mmu/matrix-events.txt
```


### Bitmap drawing ceiling

Build the matched drawing fixtures and calibrate their layout separately:

```sh
python3 tools/reconstruct.py --ceiling drawing-control --output tmp/drawing-control-slave
python3 tools/reconstruct.py --ceiling drawing-bitmap --output tmp/drawing-bitmap-slave
python3 tools/matrix_probe.py --machine a1200-030 --options MMU --warp \
  --ceiling-slave tmp/drawing-control-slave/WingCommanderCD32.Slave \
  --output tmp/drawing-layout
python3 tools/matrix_capture.py --machine a1200-030 --mmu-core --no-profiles \
  --warp --options MMU --audit tmp/phase4-instant-audit-030/result.json \
  --layout tmp/drawing-layout/result.json \
  --ceiling-slave tmp/drawing-control-slave/WingCommanderCD32.Slave \
  --output tmp/drawing-control
python3 tools/matrix_capture.py --machine a1200-030 --mmu-core --no-profiles \
  --warp --options MMU --audit tmp/phase4-instant-audit-030/result.json \
  --layout tmp/drawing-layout/result.json \
  --ceiling-slave tmp/drawing-bitmap-slave/WingCommanderCD32.Slave \
  --output tmp/drawing-bitmap
python3 tools/matrix_ceiling_report.py tmp/drawing-control tmp/drawing-bitmap \
  > tmp/drawing-bitmap-comparison.json
```

Use the same instant-blitter-audit-capable debugger and cache audit as above.
The probe is diagnostic and is not a timed ceiling capture. The checker verifies
same size/placement, the allowed patch-table difference, unchanged original
code outside the installation detour, one installation in each arm, and the
actual game entry words. It checks c2p entries remain unchanged as well.

`--ceiling drawing-clear` and `--ceiling drawing` (both drawing entries) are
retained **failed diagnostic arms**, not accepted performance comparisons. The
clear bypass permits an invalid pixel-derived rectangle and a destructive stack
clear during title loading; see internals. Do not report its partial ledger as a
ceiling. The accepted bitmap comparison leaves surface clearing enabled.


### CPU STOP accounting and matrix collection

```sh
python3 tools/build_debugger.py --matrix-observer --matrix-nommu-counters \
  --matrix-mmu030-counters --frequency-clock --matrix-dma --matrix-idle \
  --output tmp/accounting-debugger
export FSUAE="$PWD/tmp/accounting-debugger/fs-uae"
```

Add `--idle` to a normal `matrix_capture.py` invocation. Its exact recording-off
control uses the same emulator, slave, layout, audit, core and options, omitting
only `--idle`. Verify it with:

```sh
python3 tools/matrix_idle_check.py tmp/phase4-idle-on-020 \
  --profile-control tmp/phase4-profile-on-no-raw > tmp/idle-crosscheck.json
python3 tools/matrix_raw_check.py tmp/phase4-idle-on-020 --compare-only \
  --control tmp/phase4-idle-off-020 > tmp/idle-neutrality.json
python3 tools/matrix_idle_negative.py tmp/phase4-idle-on-020 \
  --output tmp/idle-negative
```

`--profile-control` is optional and only applies to a supported stable-PC
instruction capture with an identical full ledger. New builds also write the
two game STOP PC counts into each idle boundary, checked against entries plus
wait calls after startup. The reset interval remains a separate STOP-state
measurement because game code is not loaded throughout it. Wait-loop units must
be a lower bound on stopped-state units; the report retains their difference.

For the complete matrix, provide a JSON list of objects with `name` and
`reference` fields. Each reference is a completed scene capture's `result.json`,
whose machine, core, options and verified layout define the cell. Use fresh batch
output; existing captures are never overwritten. The runner uses two separate
ports and project-owned run directories, preserving the launcher's strict
ownership checks. It continues unaffected cells after a failed cell and retains
per-command logs and error results.

```sh
python3 - <<'PYPLAN'
import json
from pathlib import Path
cells = [
    ('020-default', 'profile-on-no-raw'),
    ('030-mmu-default', 'mmu-scenes-030'),
    ('020-nocache', 'nocache-on'),
    ('030-nommu-default', 'mmu-off-scenes-030'),
    ('030-mmu-nocache', 'mmu-nocache-scenes-030'),
    ('030-nommu-nocache', 'mmu-off-nocache-scenes-030'),
    ('040-default', 'frequency-scenes-040'),
    ('040-dcache', 'frequency-scenes-040-dcache'),
    ('060-default', 'frequency-scenes-060'),
    ('060-dcache', 'frequency-scenes-060-dcache'),
    ('060-nocache', 'frequency-scenes-060-nocache'),
]
plan = [{'name': name, 'reference': 'tmp/phase4-'+ref+'/result.json'}
        for name, ref in cells]
with Path('tmp/accounting-plan.json').open('x') as output:
    json.dump(plan, output, indent=2)
PYPLAN
python3 tools/matrix_accounting_batch.py --plan tmp/accounting-plan.json \
  --output tmp/accounting-matrix --ports 2456 2457 \
  --audit-slave tmp/phase4-cache-slave/WingCommanderCD32.Slave
```

The current plan covers 020 default/NoCache; 030 MMU/NoMMU with default/NoCache;
040 NoMMU default/DCache; and 060 NoMMU default/DCache/NoCache. Each cell receives
a new cache audit, then `bare`, `idle` and `dma` runs with full raw chunky sources.
The latter two use STOP accounting; only `dma` enables DMA recording. The batch
recomputes source changes, checks STOP accounting, compares bare/idle exactly,
checks DMA against the independent menu trace, and quantifies DMA effects:

```sh
python3 tools/matrix_dma_effect.py tmp/phase4-dma-off-030 tmp/phase4-dma-on-030 \
  > tmp/dma-effect-check.json
```

A completed batch cell means acquisition and its listed checks finished; it does
not certify the entire phase 4 gate. Inspect the DMA effect report, including
state/source equality and any changed fields or publications. A changed clock
is reported as a measured effect, not an exact-neutrality pass.

### Isolating CIA wait changes during DMA recording

This recorder variant preserves the DMA-off CIA delay stepping. It omits wait-phase
annotations, not actual CIA access or DMA ownership records. Both 020 cache states
pass exact recording neutrality and independent slot checks. Other cores require
their own matched controls before accepting their DMA figures.
Use a fresh output directory and debugger ports not owned by another capture.

```sh
. amiga/env.sh
python3 tools/build_debugger.py --matrix-observer --matrix-nommu-counters \
  --matrix-mmu030-counters --frequency-clock --matrix-dma --matrix-idle \
  --aprof-stable-pc --dma-cia-unsplit --output tmp/phase4-dma-cia-debugger
export FSUAE="$PWD/tmp/phase4-dma-cia-debugger/fs-uae"
python3 - <<'PYPLAN'
import json
from pathlib import Path
plan = [
    {'name': '020-default', 'reference': 'tmp/phase4-profile-on-no-raw/result.json'},
    {'name': '020-nocache', 'reference': 'tmp/phase4-nocache-on/result.json'},
]
with Path('tmp/phase4-dma-cia-plan.json').open('x') as output:
    json.dump(plan, output, indent=2)
    output.write('\n')
PYPLAN
python3 tools/matrix_accounting_batch.py \
  --plan tmp/phase4-dma-cia-plan.json --output tmp/phase4-dma-cia-matrix \
  --audit-slave tmp/phase4-cache-slave/WingCommanderCD32.Slave --ports 2458 2459
```

The batch creates fresh cache audits, recomputes all raw source-change records,
checks STOP accounting and exact idle neutrality, and reports DMA recording
changes. A cell's `complete` flag means acquisition/checks finished; inspect
`dma-effect.json` before treating its DMA arm as baseline evidence.

For each completed corrected cell, also require exact recording neutrality:

```sh
python3 tools/matrix_raw_check.py tmp/phase4-dma-cia-matrix/020-default/dma \
  --compare-only --control tmp/phase4-dma-cia-matrix/020-default/idle
python3 tools/matrix_raw_check.py tmp/phase4-dma-cia-matrix/020-nocache/dma \
  --compare-only --control tmp/phase4-dma-cia-matrix/020-nocache/idle
```

To check the remaining cores, filter the full `tmp/accounting-plan.json` from
above for names that do not start with `020-`, write it to a fresh plan file, and
run `matrix_accounting_batch.py` with the corrected debugger and a new output
root. The retained run uses `tmp/phase4-dma-cia-accelerated/`.

### Complete game VBL callback scopes

Build the read-only callback observer and obtain a fresh cache audit:

```sh
. amiga/env.sh
python3 tools/build_debugger.py --matrix-observer --matrix-nommu-counters \
  --matrix-mmu030-counters --frequency-clock --matrix-dma --matrix-idle \
  --dma-cia-unsplit --matrix-irq --output tmp/phase4-irq-debugger
export FSUAE="$PWD/tmp/phase4-irq-debugger/fs-uae"
export DEBUG_PORT=2460
python3 tools/cache_audit.py --machine a1200-fast \
  --slave tmp/phase4-cache-slave/WingCommanderCD32.Slave \
  --output tmp/phase4-irq-pair-020/audit
for arm in off on; do
  flags=()
  if [ "$arm" = on ]; then flags=(--irq-scopes); fi
  python3 tools/matrix_capture.py --machine a1200-fast --no-profiles \
    --warp --raw-chunky --audit tmp/phase4-irq-pair-020/audit/result.json \
    --layout tmp/phase4-profile-on-no-raw/result.json "${flags[@]}" \
    --output "tmp/phase4-irq-pair-020/$arm"
  python3 tools/matrix_raw_check.py "tmp/phase4-irq-pair-020/$arm"
done
python3 tools/matrix_irq_test.py
python3 tools/matrix_irq_check.py tmp/phase4-irq-pair-020/on \
  --profile-control tmp/phase4-profile-on-no-raw
python3 tools/matrix_raw_check.py tmp/phase4-irq-pair-020/on --compare-only \
  --control tmp/phase4-irq-pair-020/off
```

Use an available port and fresh output paths. The optional independent profile
must have identical scene/publication/census records and matching effective CPU
settings. That comparison validates entry counts only. The interval checker
separately checks matched returns, scene accounting and nested-scope totals;
recording neutrality is reported explicitly as `irq_scope_neutrality_pass`.
Do not call these elapsed scopes self CPU cost or total interrupt cost. A separate
020 instruction trace checks durations against complete instruction/gap sums.
The debugger writes `F` field clocks beside scope records so alignment is by field,
entry PC and stack slot, not by searching for similar durations.

```sh
python3 tools/build_debugger.py --matrix-observer --matrix-nommu-counters \
  --matrix-mmu030-counters --frequency-clock --matrix-dma --matrix-idle \
  --dma-cia-unsplit --matrix-irq --output tmp/phase4-irq-v2-debugger
export FSUAE="$PWD/tmp/phase4-irq-v2-debugger/fs-uae"
python3 tools/cache_audit.py --machine a1200-fast \
  --slave tmp/phase4-cache-slave/WingCommanderCD32.Slave \
  --output tmp/phase4-irq-v2-audit-020
python3 tools/matrix_capture.py --machine a1200-fast --no-profiles \
  --warp --raw-chunky --irq-scopes --irq-trace \
  --audit tmp/phase4-irq-v2-audit-020/result.json \
  --layout tmp/phase4-profile-on-no-raw/result.json \
  --output tmp/phase4-irq-v2-trace-020
python3 tools/matrix_irq_trace_check.py tmp/phase4-irq-v2-trace-020 \
  --control tmp/phase4-irq-pair-020/on
python3 tools/matrix_irq_trace_negative.py tmp/phase4-irq-v2-trace-020 \
  --output tmp/phase4-irq-v2-negative-clock
```

The trace capture is explicitly diagnostic: it stops at credits entry and records
five fields, then completes the usual route. Ordinary baseline/neutrality reports
continue to reject diagnostic captures. The trace checker explicitly permits
that ledger for calibration, requires exact callback duration agreement, and
optionally compares all callback intervals and final state with the uninterrupted
control. The trace file and all mutation fixtures stay under `tmp/`.

For matching callback controls across the machine matrix, use the full matrix
plan format above and select IRQ mode. This mode performs a fresh cache audit,
bare and `--irq-scopes` captures, full raw-source checks, callback-scope accounting
and exact on/off comparison. It does not repeat the DMA/idle arms.

```sh
export FSUAE="$PWD/tmp/phase4-irq-v2-debugger/fs-uae"
python3 tools/matrix_accounting_batch.py --kind irq \
  --plan tmp/accounting-plan.json --output tmp/irq-matrix \
  --audit-slave tmp/phase4-cache-slave/WingCommanderCD32.Slave \
  --ports 2460 2461
```

Use free ports. The retained `tmp/phase4-irq-matrix/` plan excludes the already
validated 020 default cell. `settings.json` records mode and ports; each cell
retains exact commands, fresh audit and comparison results. IRQ acquisition and
neutrality do not replace independent timing validation for each interpreter.

If a cell's launcher rejects a busy debugger port, keep its failed result and
choose free ports for a fresh retry. `matrix_capture.py` retains the launcher's
captured stdout/stderr, including ownership errors. Never stop another project's
emulator to free a port. Build a retry plan only from terminal failed cell results;
missing results can still belong to active captures.

```sh
python3 - <<'PYRETRY'
import json
from pathlib import Path
root = Path('tmp/phase4-irq-matrix')
failed = {p.parent.name for p in root.glob('*/result.json')
          if not json.loads(p.read_text())['complete']}
plan = json.loads(Path('tmp/phase4-irq-matrix-plan.json').read_text())
with Path('tmp/phase4-irq-retry-plan.json').open('x') as output:
    json.dump([cell for cell in plan if cell['name'] in failed], output, indent=2)
PYRETRY
python3 tools/matrix_accounting_batch.py --kind irq \
  --plan tmp/phase4-irq-retry-plan.json --output tmp/phase4-irq-retry \
  --audit-slave tmp/phase4-cache-slave/WingCommanderCD32.Slave \
  --ports 2470 2471
```

### Callback beam calibration

The same callback debugger supports independent read-only beam observations,
including configurations without Barto instruction records. Calibrate first on
the covered 020 core; use the matching audit and an uninterrupted callback control.

```sh
export FSUAE="$PWD/tmp/phase4-irq-v2-debugger/fs-uae"
export DEBUG_PORT=2472
python3 tools/matrix_capture.py --machine a1200-fast --no-profiles \
  --warp --raw-chunky --irq-scopes --irq-beam \
  --audit tmp/phase4-irq-v2-audit-020/result.json \
  --layout tmp/phase4-profile-on-no-raw/result.json \
  --output tmp/phase4-irq-beam-020
python3 tools/matrix_irq_beam_check.py tmp/phase4-irq-beam-020 \
  --control tmp/phase4-irq-pair-020/on
python3 tools/matrix_irq_beam_negative.py tmp/phase4-irq-beam-020 \
  --output tmp/phase4-irq-beam-negative
```

For the machine matrix, `--kind irq-beam` performs fresh audits and one diagnostic
beam capture per cell using the normal matrix-plan format. It checks scene/scope
accounting and the nine beam intervals; it does not claim recorder neutrality or
perform the ordinary uninterrupted raw-source report on a diagnostic capture.

```sh
python3 tools/matrix_accounting_batch.py --kind irq-beam \
  --plan tmp/accounting-plan.json --output tmp/irq-beam-matrix \
  --audit-slave tmp/phase4-cache-slave/WingCommanderCD32.Slave \
  --ports 2472 2473
```

Choose free ports. The retained `tmp/phase4-irq-beam-matrix/` excludes the already
calibrated 020 default cell. For each completed cell, rerun
`matrix_irq_beam_check.py CELL/beam --control MATCHING_IRQ_CONTROL` to require
identical callback intervals, full publication/census ledger, raw source buffers,
game hunks and menu pixels. Beam agreement alone does not satisfy that control.

### Consolidate existing instrument captures without rerunning the emulator

`tools/matrix_instrument_accept.py` takes a JSON array of cell mappings and
writes a fresh report directory under `tmp/`. Each mapping names a reference
`result.json`, six capture directories (`dma_bare`, `idle`, `dma`, `irq_bare`,
`irq`, `beam`) and three audit `result.json` files (`dma_audit`, `irq_audit`,
`beam_audit`), plus a simple unique `name`. Paths are repository-relative.
The saved manifest in the report directory preserves the exact inputs.

With the existing capture manifest:

```sh
python3 tools/matrix_instrument_accept.py \
  --manifest tmp/phase4-instrument-manifest.json \
  --output tmp/phase4-instrument-accept-02
python3 tools/matrix_instrument_negative.py \
  --manifest tmp/phase4-instrument-manifest.json \
  --output tmp/phase4-instrument-negative-02
```

Use fresh output names. This recomputes every raw source buffer and can take
several minutes; do not repeat it when inputs are unchanged. No emulator is
launched. `validated` means only the stated DMA/idle/callback scope, not the
phase 4 gate. Missing captures produce `pending`; rejected evidence produces
`invalid` and a nonzero exit. A zero exit alone does not mean all cells passed:
inspect `summary.json`. The negative check requires a complete first cell.
The first completed consolidation and negative reports use the `-01` and
`phase4-instrument-negative` output directories recorded in the internals.

The representative cost figures use the existing leaf reports documented above;
no fresh boot is required. To check the 040 beam capture with its explicit endpoint model and inspect its original
samples:

```sh
python3 tools/matrix_irq_beam_check.py \
  tmp/phase4-irq-beam-matrix/040-default/beam
cat tmp/phase4-irq-beam-matrix/040-default/beam/irq-beam.json
```

The reviewed 040/060 build permits one extra colour clock of debugger endpoint
skew, reported separately from beam quantisation. Other builds require source
review before using that model. Match the nine
samples in order to callback entries after scene 15 in `irq-events.txt`, as the
checker does; subtract entry from return clocks and compare with the decoded
beam interval times 512. Do not treat a diagnostic residual census as acceptance
or increase the tolerance solely to make the fixture pass.

To reproduce the 040 control comparison and corruption checks without a boot:

```sh
python3 tools/matrix_irq_beam_check.py \
  tmp/phase4-irq-beam-matrix/040-default/beam \
  --control tmp/phase4-irq-retry/040-default/irq
python3 tools/matrix_irq_beam_negative.py \
  tmp/phase4-irq-beam-matrix/040-default/beam \
  --output tmp/phase4-040-beam-boundary-negative-02
```

Quantify the existing 060 callback-recorder differences without another capture:

```sh
python3 tools/matrix_dma_effect.py \
  tmp/phase4-irq-retry/060-default/bare \
  tmp/phase4-irq-retry/060-default/irq --feature irq_scopes \
  > tmp/phase4-060-default-irq-effect.json
python3 tools/matrix_dma_effect.py \
  tmp/phase4-irq-retry/060-nocache/bare \
  tmp/phase4-irq-retry/060-nocache/irq --feature irq_scopes \
  > tmp/phase4-060-nocache-irq-effect.json
```

The default feature remains DMA for existing commands. Configuration checks
require only the selected recording feature to change. Effect reports describe
observed differences and do not override failed exact-neutrality checks.

The completed corrected 060 DMA pairs also support the unchanged exact check:

```sh
python3 tools/matrix_raw_check.py \
  tmp/phase4-dma-cia-accelerated/060-default/dma \
  --control tmp/phase4-dma-cia-accelerated/060-default/idle --compare-only
python3 tools/matrix_raw_check.py \
  tmp/phase4-dma-cia-accelerated/060-dcache/dma \
  --control tmp/phase4-dma-cia-accelerated/060-dcache/idle --compare-only
```

The last corrected DMA cell, 060 NoCache, is complete. Its existing-data checks
use the same commands as the other cells:

```sh
python3 tools/matrix_dma_check.py \
  tmp/phase4-dma-cia-accelerated/060-nocache/dma
python3 tools/matrix_raw_check.py \
  tmp/phase4-dma-cia-accelerated/060-nocache/dma \
  --control tmp/phase4-dma-cia-accelerated/060-nocache/idle --compare-only
```

Both corrected batch roots now contain completed per-cell `dma-report.json`,
`dma-effect.json` and audited capture metadata for all eleven configurations.
DMA completion does not certify general CPU/interrupt attribution.

### Practical-baseline closeout

Phase 4 is complete for the user-approved practical scope. No further emulator
runs are needed for closeout. The gate audit and explicit deferrals are in
`internals.md`; the next phase requires a separate request.

The accepted corrected baseline is under `tmp/phase4-dma-cia-matrix/` (two 020
cells) and `tmp/phase4-dma-cia-accelerated/` (nine accelerated cells). Each cell
retains `audit/result.json`, bare/idle/DMA captures, per-arm raw-census checks,
`idle-neutrality.json`, `dma-report.json` and `dma-effect.json`. Existing commands
above reproduce their scene, source-change, DMA and idle measurements.
Consolidated callback acceptance is recorded in `phase4-instrument-accept-01/`,
`phase4-instrument-accept-02/`, `phase4-instrument-040-dcache.json` and
`phase4-instrument-060-dcache.json`, all under `tmp/`. Only rows marked
`validated` count; failed/pending rows are retained as limitations.

Recheck the three accepted ceiling pairs from existing captures:

```sh
python3 tools/matrix_ceiling_report.py \
  tmp/phase4-ceiling-control-030-mmu tmp/phase4-ceiling-c2p-030-mmu
python3 tools/matrix_ceiling_report.py \
  tmp/phase4-instant-control-030-mmu tmp/phase4-instant-on-030-mmu
python3 tools/matrix_ceiling_report.py \
  tmp/phase4-drawing-v2-control-030-mmu tmp/phase4-drawing-bitmap-030-mmu
```

All three were rechecked at closeout. Their fixture/readback checks pass, while
the original limiter and the stated drawing scope remain part of the experiment.
They establish neither a release-patch speedup nor complete routine accounting.

## Phase 5: motion timing and the supplied PC video

Use the existing calibrated phase 4 debugger; the retained phase 5 captures use
`tmp/phase4-irq-v2-debugger/fs-uae`, SHA-256
`c30ad609dc1141b47d3b9cfbf7d5a86666445fee7985907beef60b095679d940`.
There is no new emulator instrument or matrix. All captures below use original
`CUSTOM5=0`, PAL, explicit cycle-exact CPU settings, and warp only to shorten host
time. Durations come from emulated cycle stamps. Choose free debugger ports;
the shared launcher refuses foreign listeners and stops only owned processes.
Every output directory must be new and below `tmp/`.

```sh
. amiga/env.sh
export FSUAE="$PWD/tmp/phase4-irq-v2-debugger/fs-uae"
export DEBUG_PORT=2483
python3 tools/intro_timing_fixture.py --iterations 0 \
  --output tmp/phase5-control-slave
python3 tools/intro_timing_fixture.py --iterations 100000 \
  --output tmp/phase5-slow-slave
SLAVE="$PWD/tmp/phase5-control-slave/WingCommanderCD32.Slave" \
  INTRO_STOCK_CLOCK=1 WHD_ARGS=CUSTOM5=0 \
  python3 tools/boot_gate.py --calibrate --output tmp/phase5-fixture-layout
python3 tools/intro_timing_capture.py --output tmp/phase5-control \
  --layout tmp/phase5-fixture-layout/layout.json \
  --fixture tmp/phase5-control-slave/WingCommanderCD32.Slave
python3 tools/intro_timing_capture.py --output tmp/phase5-slow \
  --layout tmp/phase5-fixture-layout/layout.json \
  --fixture tmp/phase5-slow-slave/WingCommanderCD32.Slave
python3 tools/intro_timing_capture.py --machine a1200-030 \
  --output tmp/phase5-030 --layout tmp/phase4-mmu-scenes-030/result.json
for arm in control slow 030; do
  python3 tools/intro_timing_report.py "tmp/phase5-$arm" \
    > "tmp/phase5-$arm/timing-report.json"
done
```

The fixtures preserve the original slave except for the declared c2p-wrapper
call and equal-size appended diagnostic tail. Both are VERIFY-only; ordinary
reconstruction and release behaviour are unchanged. The runner verifies fixture
hashes and the final live layout, records effective CPU/cache/MMU state, and sends
Escape only after all eighteen credit pages. The reporter rejects missing or
reordered pages, incorrect title update/publication counts, clock drift,
unpaired publications or waits, and CIA-A TOD/field disagreement. No screenshot
matrix or DMA collection is performed. A zero-delay fixture still has call
overhead and is not claimed exactly timing-neutral against the original slave.

For the external motion reference, set `VIDEO` to the user-supplied `wcpc.mov`.
The tool verifies its SHA-256 before decoding. It requires ffmpeg, NumPy and Pillow. The existing
phase 4 raw-source capture supplies the original Amiga pictures and timestamps;
this analysis does not boot an emulator.

```sh
: "${VIDEO:?set VIDEO to the supplied wcpc.mov}"
python3 tools/intro_motion_reference.py "$VIDEO" \
  --amiga-run tmp/phase4-dma-cia-matrix/020-default/bare \
  --output tmp/phase5-motion-evidence
```

Inspect `ships.jpg`, `explosion.jpg`, `asteroids.jpg`, `asteroid-poses.jpg`,
`amiga-motion.jpg` and `motion.json` in that output. Contacts are labelled in video
seconds; the Amiga contact is labelled with source-frame indices and emulated
seconds. Amiga indexed pixels are shown in grayscale solely to inspect geometry,
not as a faithful palette rendering. Source frames 21–26 and 29–36 refer to the
`title-animation` scene, not the entire intro's frame index.

The asteroid cadence uses the explicitly selected distinct poses, reviewed
visually. Its whole-image change scores are retained for diagnosis but must not
be counted as frames: optical refresh mixtures make that count unreliable.
Bounding boxes and short displacements use the recorded crop/thresholds; they
are approximate projected-motion evidence. Do not infer world velocity, a flight
tick rate or a uniform FPS cap from them. Music and text deadlines are kept
separate. The decision and limitations are recorded in `internals.md`.

## Phase 6 rendering builds and checks

These are experimental English-only builds, not release archives. `CUSTOM1=2`
enables rendering changes and leaves cache configuration to WHDLoad; `CUSTOM1=0/1`
keeps the original language/rendering behaviour. Automatic selection uses Kalms
030 only on cached 020/030 and retains the existing converter elsewhere.
`CUSTOM5=0–3` retains the existing
limiter choices. Enabled rendering rejects `CUSTOM5=4` (old blitter converter).

```sh
. amiga/env.sh
make render-slave OUT=tmp/render
make render-control OUT=tmp/render-control
make render-verify OUT=tmp/render-twin
python3 tools/c2p_check.py tmp/render \
  --capture tmp/phase4-dma-cia-matrix/020-default/bare \
  --output tmp/render-native.json
```

The checker uses the shared fixed Unicorn library (`AMIGA_UNICORN`), executes
both native algorithms and an independent pixel model, and hooks every write.
It also rejects three deliberately damaged local converter fixtures. The optional
capture supplies the first recorded source of each intro scene. The 060 dispatch
is exercised on Unicorn's 040 ISA because the 060 model rejects MOVEM; this does
not replace an FS-UAE 060 run. No native-harness result measures performance.

Calibrate the task-owned build and inspect a short credits trace:

```sh
FSUAE="$PWD/tmp/phase4-irq-v2-debugger/fs-uae" \
python3 tools/render_probe.py --render-slave tmp/render/WingCommanderCD32.Slave \
  --output tmp/render-probe --machine a1200-fast --options 'CUSTOM1=2 DCache' --warp
```

The probe records boot/live cache state, chip/fast memory and a five-field
instruction trace. Use a separate calibration for the twin build: its reference
allocation changes the live layout. Full intro capture, without profiling stops
inside the intro:

```sh
FSUAE="$PWD/tmp/phase4-irq-v2-debugger/fs-uae" \
python3 tools/render_capture.py --fixture tmp/render/WingCommanderCD32.Slave \
  --layout tmp/render-probe/result.json --output tmp/render-intro \
  --options 'CUSTOM1=2 DCache'
```

Use the equal-size control with `CUSTOM1=2` for comparison: it retains the
existing converter while applying the same WHDLoad cache policy. `CUSTOM1=0`
also restores the original SetCPU request. Record and match live
CACR rather than assuming identical option names imply identical cache states.
The capture logs converter boundaries, original scene/music/publication markers,
CPU settings, a menu screenshot, hashes and final memory. A twin capture additionally
requires a nonzero verified-frame count. Its timings include reference conversion
and comparison and are unsuitable for performance comparisons.

Compare uninterrupted ledgers with matched CPU/cache state:

```sh
python3 tools/render_report.py tmp/render-intro --control tmp/control-intro \
  > tmp/render-comparison.json
```

Converter figures are **elapsed service time**, including any interrupt that
occurs between the native converter entry and return. They exclude the original
limiter and the new display-end wait. They are not self/inclusive CPU attribution
and are not hardware benchmarks. The full-intro report also records the unchanged
296 title updates / 148 publications, game/music interrupt cadence, one copper
publication per completed frame, source/destination placement, scene durations,
and wait duration. CPU-bound scene durations remain subject to frame coupling.

Unlike the stricter phase-5 calibration report, this report records CIA-TOD versus
field-sample disagreements without rejecting the entire capture: an interrupt can
separate the TOD read from the observation at `S:17e6`. It still requires the
existing limiter's minimum two-tick threshold on every completed wait. These
observations are not presented as a new timing-backend calibration.

To evaluate the other Kalms family on the same CPU without changing allocation
size or the control, use `--render-family 030` or `--render-family 040` with
`--render`. These are diagnostic overrides, recorded in `build.json`. Never infer
a routine's suitability from its upstream CPU suffix; compare actual measurements.


The completed selection is based on the scoped measurements in `internals.md`.
For 030 MMU, calibrate with `render_probe.py --machine a1200-030 --options
'CUSTOM1=2 DCache MMU' --warp`, then capture with `--machine a1200-030 --mmu
--options 'CUSTOM1=2 DCache'`. Other accelerated captures select the NoMMU timing
interpreter; pass `--machine a1200-040` or `a1200-060` and `NoMMU` in options.
Use `NoCache` to check the conservative original-converter selection. Calibration
is specific to build size and MMU setup; do not transplant a different layout.

Final normal/control/twin fixtures are `tmp/phase6-render-v6/`,
`tmp/phase6-control-v6/` and `tmp/phase6-twin-v6/`. Rebuilding the renderer after
the source-only diagnostic adjustment is byte-identical (`tmp/phase6-render-repro/`).
The final cached 020 pair uses `tmp/phase6-final-probe/result.json` and lives in
`tmp/phase6-final-{control,render}-020/`. Final 060 NoCache twin calibration and
capture are `tmp/phase6-final-twin-probe/` and `tmp/phase6-final-twin-060/`.
These fixtures and every derived capture remain ignored.

## Phase 7 flight windows and time model

The flight tools use diagnostic slaves under `tmp/`; they do not enable the
phase-6 renderer or change release defaults. Use fresh output names on reruns.
The fixture builder verifies the original input through the existing reconstruction
and timing-fixture path. `--iterations 0` and `100000` have equal allocation sizes;
only the latter delays the existing c2p. The extra argument uses the game's
native direct-flight parser. `--nav 1` starts at the first combat navpoint.

```sh
. amiga/env.sh
python3 tools/flight_fixture.py --output tmp/flight-control --iterations 0
python3 tools/flight_fixture.py --output tmp/flight-delay --iterations 100000
python3 tools/flight_fixture.py --output tmp/flight-combat --nav 1
python3 tools/build_debugger.py --output tmp/flight-debugger \
  --intro-observer --matrix-observer --aprof-stable-pc \
  --matrix-nommu-counters --frequency-clock --matrix-mmu030-counters --matrix-irq
export FSUAE="$PWD/tmp/flight-debugger/fs-uae"
SLAVE="$PWD/tmp/flight-control/WingCommanderCD32.Slave" \
WHD_ARGS='CUSTOM2=2 CUSTOM3=1 CUSTOM4=0 CUSTOM5=0' \
WARP=0 INTRO_STOCK_CLOCK=1 \
python3 tools/boot_gate.py --calibrate --output tmp/flight-layout
```

The retained Nav-1 fixture also rebuilds byte-identically in
`tmp/phase7-fixture-repro-verified/`. Source `amiga/env.sh` first: the assembler
path is supplied through `VASM`.

Calibration only locates the loaded hunks/slave; it does not run the phase-2
menu/name gate. The verified phase-7 command reproduced the retained layout in
`tmp/phase7-layout-verified/layout.json`. The same allocation layout works for
these matched fixtures on the selected 020 and 030 NoMMU configurations; each
capture checks it again from live memory and fails on a mismatch.

```sh
python3 tools/flight_capture.py --output tmp/flight-020 \
  --layout tmp/flight-layout/layout.json \
  --fixture tmp/flight-control/WingCommanderCD32.Slave
python3 tools/flight_capture.py --output tmp/flight-repeat \
  --layout tmp/flight-layout/layout.json \
  --fixture tmp/flight-control/WingCommanderCD32.Slave
python3 tools/flight_capture.py --output tmp/flight-slow \
  --layout tmp/flight-layout/layout.json \
  --fixture tmp/flight-delay/WingCommanderCD32.Slave
python3 tools/flight_capture.py --output tmp/flight-030 --machine a1200-030 \
  --layout tmp/flight-layout/layout.json \
  --fixture tmp/flight-control/WingCommanderCD32.Slave
python3 tools/flight_capture.py --output tmp/flight-input --controls \
  --layout tmp/flight-layout/layout.json \
  --fixture tmp/flight-combat/WingCommanderCD32.Slave
```

Each run waits for the first normal flight-loop entry `E:0698`, then captures
three 100-field no-input windows. `--controls` adds 100 fields each of Space,
Right and Tab, followed by a state-gated pause, ten paused fields and twenty
resumed fields. Raw key codes are hexadecimal `40`, `4e`, `42`, `19`; Space resumes
pause. This is the shared `monitor key` route, not host keyboard automation.
The script records key edges and window boundaries in `actions.json` and
`result.json`. Stops occur between windows, never inside the measured interval.
The script always requests stopping only its own project run in cleanup.

Configuration is fixed: deterministic PAL, 8 MiB FAST, `Custom2=2`, system 1,
mission 0, `Custom5=0`, software c2p, no instant blitter, no extra arguments.
The 020 uses stock exact unit 128; 030 uses calibrated NoMMU unit 36.
Boot/live CPU audits, fixture hashes and emulator SHA-256 are in each result.
Warp affects host execution speed; reported seconds come from the emulated
clock, not host time. Full traces are large (roughly 1 GB per 100-field window).
Use the retained runs for additional analysis instead of collecting another matrix.

```sh
python3 tools/flight_report.py tmp/flight-repeat --compare tmp/flight-020 \
  --validate-trace coast-1
python3 tools/flight_report.py tmp/flight-slow --compare tmp/flight-020
python3 tools/flight_report.py tmp/flight-030 --compare tmp/flight-020
python3 tools/flight_report.py tmp/flight-input
```

Reports are saved as `flight-report.json` in the run. Comparisons require matching
world trajectories by update index (including all world positions/velocities and
ten-ship state ranges), not by field or elapsed time. Use settled `coast-1/2`;
`coast-0` includes loading/acceleration. `--validate-trace` independently matches
PC/register/field records for flight entry, completed update, publication and
VBL. Only complete trace fields are compared; report intervals exclude partial
updates at window edges. The retained trace has 20 updates/publications and 100
VBLs, while its cadence estimate uses 19 complete entry-to-entry intervals.

The report checks adjacent update counters and one publication per interval.
Pause checks require unchanged mapped world state and a ten-tick VBL advance.
Source-change percentages compare complete 320×200 sources; a missing census
is null, never zero. `census_samples` shows coverage. PC buckets are scoped
address ranges, not general self/inclusive routine accounting.

The optional observer-neutrality check disables only hunk-1 snapshots:

```sh
python3 tools/flight_capture.py --output tmp/flight-observer-control --no-states \
  --layout tmp/flight-layout/layout.json \
  --fixture tmp/flight-control/WingCommanderCD32.Slave
python3 tools/flight_report.py tmp/flight-repeat --compare tmp/flight-020 \
  --observer-control tmp/flight-observer-control --validate-trace coast-1
```

`states.bin` consists of guest-order hunk-1 blocks of `0xfda0` bytes; block N
matches event N at `E:0698` in `events.txt`. The reader enforces this alignment.
The observer never writes guest memory. Explicit flushes preserve short-window
census records when the owned emulator is stopped. The retained no-snapshot
control also checks this flush change: all three window event streams and
screenshot pixels match the earlier observer exactly. Startup/shutdown events
outside the windows are excluded.

Retained measurements are `tmp/phase7-coast-{020,repeat,delay,030}/`,
`tmp/phase7-observer-control/` and `tmp/phase7-combat-controls/`.
`tmp/phase7-validation.json` contains repeat, observer and full-trace checks.
The older delayed run predates the census flush fix and has no source census;
its timing/state evidence is intact. The corrected combat capture uses the key
codes above and supersedes exploratory control attempts. All derived material
stays in `tmp/`. This gate does not require full campaign, landing or conversation
runs; their static cadence classifications and live-coverage gaps are recorded
in `internals.md`. The phase-7b native audit below complements those live checks.

## Phase 7b: native framerate-dependency audit

Use the retained phase-7 combat dump; no new emulator run is needed. These tools
execute or decode the English CD32 executable only. Load the shared environment
for Capstone and the installed Unicorn library, as for the existing native c2p
checks. Run Python without `-O`: assertions are the native test oracle.

```sh
. amiga/env.sh
python3 tools/timing_inventory.py tmp/phase7-combat-controls \
  --output tmp/timing-inventory
python3 tools/timing_audit_check.py tmp/phase7-combat-controls \
  --output tmp/timing-audit
```

Both output directories must be fresh and inside `tmp/`; differing results are
never overwritten. The input is `start-fast.bin` from the named run. The reader
verifies the original English executable SHA-256 and identifies its live patched
hunk chain, rather than a PRELOAD copy. Both reports record the dump SHA-256. The inventory records the Capstone version;
the native report records the shared Unicorn library SHA-256.
The retained input used for the gate is
`9ba523f262405ce1ff743e65fa897a341c48a7b4b0c2a2d9ec36894f97880902`.
Other captures may locate successfully but are not substitutes for that evidence
without rerunning the checks and reviewing changed fixtures.

The inventory produces `inventory.json` and `reachable.dis`. It follows direct
calls and branches, all bounded switches, the 47-entry ship-action callback table,
the image decoder's 128-entry table, and the selected resource helpers. Classified
copy/format/OS boundaries are explicit leaves; a new unclassified indirect transfer
fails the command. The two slave leaves are named by slave-hunk offset. The complete
derived call graph and decoded entry lists stay under `tmp/`.

The native checker maps the retained image into separate Unicorn 68000 and 68040
instances. Full routines and explicitly bounded original-code slices use controlled
data, with fresh hunk-1 state for each fixture. Code is unchanged in the positive
checks. Every call has instruction/time limits and must reach its specified return
or slice end. Translation caches are flushed between calls so a previous slice's
stop address cannot contaminate the next one.

Schedules cover one second at 10, 20, 50 and 60 calls/s, plus half a second at each
of 10→50 and 50→10. Native routines have no elapsed-time argument: changing the
number and timing of calls is the experiment, not a timing fix. Tests assert the
current dependencies. When a fix is introduced, change that item's oracle to equal
elapsed-time outcomes while retaining the old-defect negative control. Per-event
and clock-source controls have different oracles, described in the audit.

`report.json` contains both CPU-model results, all 625 dispatch entry checks,
104 unsigned bounds rejections, and negative controls. The controls corrupt a
switch signature in a private memory copy and reverse a lifetime decrement in the
private Unicorn image; neither changes the retained dump or game tree. They must
reject the corresponding good-code expectations. No game-derived output is tracked.

The final gate evidence is in `tmp/phase7b-inventory-gate/` and
`tmp/phase7b-native-verified/`. Native execution is correctness evidence, not a cycle,
DMA or wall-clock performance instrument. The high-bit memory-shift probe records
an instrument discrepancy separately; it is not asserted to be game behaviour.
See [the audit](framerate-audit.md) for each fixture's scope and the live gaps.

## Phase 8 design pricing

`simulation_capture.py` reuses the phase-7 Nav-1 fixture and read-only observer.
It holds fire for three 100-field windows and records exact world entry/return,
draw return, publication and loop entry. The report selects updates 10–39 and
rejects any frame crossing a debugger stop. Each retained phase-4 cell supplies
its machine, MMU backend and WHDLoad options; the live audit must match every
field, including CACR and TC. The flight fixture changes the slave allocation,
so loaded game hunks are checked independently of the slave address.

Reproduce with fresh output directories (the retained run used
`tmp/phase7-debugger-v2/fs-uae` and `tmp/phase7-fixture-repro-verified/`):

```sh
. amiga/env.sh
python3 tools/flight_fixture.py --output tmp/design-flight --nav 1
python3 tools/build_debugger.py --output tmp/design-debugger \
  --intro-observer --matrix-observer --aprof-stable-pc \
  --matrix-nommu-counters --frequency-clock --matrix-mmu030-counters --matrix-irq
export FSUAE="$PWD/tmp/design-debugger/fs-uae"
for ref in tmp/phase4-dma-cia-matrix/020-*/bare/result.json \
           tmp/phase4-dma-cia-accelerated/*/bare/result.json; do
  cell=$(basename "$(dirname "$(dirname "$ref")")")
  python3 tools/simulation_capture.py --reference "$ref" \
    --fixture tmp/design-flight/WingCommanderCD32.Slave \
    --output "tmp/design-combat/$cell" || break
done
python3 tools/simulation_report.py tmp/design-combat/*/ \
  --output tmp/design-combat/report.json
python3 tools/simulation_capture.py \
  --reference tmp/phase4-dma-cia-matrix/020-default/bare/result.json \
  --fixture tmp/design-flight/WingCommanderCD32.Slave \
  --output tmp/design-repeat/020-default
python3 tools/simulation_report.py tmp/design-repeat/020-default \
  --output tmp/design-repeat/report.json
```

Matrix inputs come from the phase-4 procedure above; do not silently substitute
030 NoMMU interpreter results for the 030 MMU-backend/NoMMU-option cell. The retained
fixture SHA-256 is `cc4e6a177a567aaa4059206988fba2512d021995add3d7fded5c38d767ad6eb9`;
the retained debugger SHA-256 is
`08360549c392f07b1fb3393bf1e071cd0bd5ffcb4048f229d528a1ce628c1313`.
Both are recorded in each capture. No additional downloads or instrument builds
were needed for the retained pricing run. All captures, snapshots and reports
remain in `tmp/`. The machine-readable report includes input hashes and per-range
state comparisons with 020; use directory globs ending in `/` to exclude reports.

These are inclusive elapsed world reservations and arithmetic render budgets.
Do not label them exclusive CPU utilisation or measured B/C/D frame rates.
The [design comparison](timing-design.md) defines formulas, assumed overhead and
limits; full interrupt subtraction and real-hardware timing remain gaps.

## Phase 9 decoupled simulation

Phase 9 is complete. The separate experimental `--timing` build enables the
10 Hz world and elapsed-field player/camera path with English `CUSTOM1=3`.
It is not combined with the phase-6 renderer or enabled by default. See the
[gate results and remaining coverage](internals.md#phase-9-decoupled-simulation-gate).
All commands require fresh output directories under `tmp/`.

Build the candidate and run native component checks:

```sh
. amiga/env.sh
python3 tools/reconstruct.py --timing --output tmp/timing-candidate
python3 tools/timing_clock_check.py --output tmp/timing-clock-check
python3 tools/timing_adapter_check.py tmp/timing-candidate --output tmp/timing-install-check
python3 tools/timing_player_check.py tmp/timing-candidate --output tmp/timing-player-check
python3 tools/timing_input_check.py tmp/timing-candidate --output tmp/timing-input-check
python3 tools/timing_presentation_check.py tmp/timing-candidate --output tmp/timing-presentation-check
python3 tools/timing_modal_check.py tmp/timing-candidate --output tmp/timing-modal-check
```

The clock check covers 4,400 native assembly steps on Unicorn 68020/68040,
including 50/60 Hz, wrap, modal resume and overload, with a wrong-rate negative
control. Installer checks cover eight option/model cases and changed-operand
rejection before writes. Player checks cover 664 preview/isolation/signed-rate
cases. Input checks cover publication, wrap, overflow, captured command boundaries
and multiple pad edges. Presentation checks vary draws per world tick and verify
native timers, targeting and gameplay RNG isolation. Modal checks verify both
pause and autopilot wrappers. These establish native correctness, not performance.
Player checks use the retained phase-7 memory dump; generated native code and
reports remain in `tmp/`.

Build equal-size VERIFY fixtures for the live scheduling gate:

```sh
for schedule in normal slow one-field; do
  python3 tools/flight_fixture.py --timing --timing-verify --nav 1 \
    --schedule "$schedule" --output "tmp/timing-flight-$schedule"
done
export FSUAE="$PWD/tmp/phase7-debugger-v2/fs-uae"
SLAVE="$PWD/tmp/timing-flight-normal/WingCommanderCD32.Slave" \
WHD_ARGS='CUSTOM1=3 CUSTOM2=2 CUSTOM3=1 CUSTOM4=0 CUSTOM5=0' \
WARP=1 INTRO_STOCK_CLOCK=1 AMIGA_SETUP=a1200-fast \
python3 tools/boot_gate.py --calibrate --output tmp/timing-layout
for schedule in normal slow one-field; do
  python3 tools/timing_capture.py \
    --fixture "tmp/timing-flight-$schedule/WingCommanderCD32.Slave" \
    --layout tmp/timing-layout/layout.json --schedule "$schedule" \
    --windows 20 --held-key 40 --output "tmp/timing-run-$schedule"
done
python3 tools/timing_capture.py \
  --fixture tmp/timing-flight-normal/WingCommanderCD32.Slave \
  --layout tmp/timing-layout/layout.json --windows 20 --held-key 4e \
  --ntsc --pause --output tmp/timing-run-ntsc
python3 tools/timing_capture.py \
  --fixture tmp/timing-flight-normal/WingCommanderCD32.Slave \
  --layout tmp/timing-layout/layout.json --windows 20 --held-key 4e \
  --machine a1200-030 --presentation-states --output tmp/timing-run-responsive
python3 tools/timing_report.py tmp/timing-run-normal tmp/timing-run-slow \
  tmp/timing-run-one-field tmp/timing-run-ntsc tmp/timing-run-responsive \
  --output tmp/timing-report.json
```

The retained observer executable has SHA-256
`08360549c392f07b1fb3393bf1e071cd0bd5ffcb4048f229d528a1ce628c1313`.
Verify it before use. Captures check the live layout and effective CPU settings;
recalibrate if a changed build no longer matches. The final gate additionally
used `--pause` on the normal PAL capture. The report excludes two warm-up windows,
uses the observer's PAL/NTSC clock, requires at least 200 completed updates,
rejects clock errors above 1%, input overflow and schedule mismatch, and compares
state at matching world ticks. Publication snapshots establish responsive camera
movement while collidable positions stay at world boundaries.

Schedules are pinned in fixture bytes and metadata. Normal draws the native scene
and HUD; slow imposes a ten-field minimum. One-field replaces drawing with a wait
only in VERIFY: it tests the scheduler and makes no renderer frame-rate claim.
The default capture retains compact observer events; use `--trace` only when
full instruction profiles are needed. WARP changes host execution speed, not the
observed emulated-time denominator.

The current shared 030 preset's emulated data-cache/indirect-board combination
does not boot with the retained observer. The 030 capture automatically selects
`WC_BASELINE_CACHE_MODEL=1`, restoring the established phase-8 emulation settings
(data cache off, no indirect board). Effective configuration is checked and
hashed; WHDLoad's requested cache policy is unchanged. This is confined to the
measurement harness, and default setup is unchanged.

Final evidence is retained in `tmp/phase9-final-normal/`,
`tmp/phase9-final-slow/`, `tmp/phase9-final-one-field/`,
`tmp/phase9-final-ntsc-020-turn/` and `tmp/phase9-final-pal-030-baseline/`.
The consolidated report is `tmp/phase9-complete-verified-report.json`.
Native checks and the non-VERIFY candidate are recorded in the internals gate.
The current timing build also includes phase 10; use its gate below for predicted poses.

## Phase 10 renderer-only prediction

The normal `--timing` candidate includes bounded prediction under `CUSTOM1=3`.
The original reconstruction and options 0/1/2 remain unchanged. Rebuild and retain
fresh output directories; all derived material stays in `tmp/`:

```sh
. amiga/env.sh
python3 tools/reconstruct.py --timing --output tmp/scene-candidate
python3 tools/flight_fixture.py --timing --timing-verify --nav 1 --output tmp/scene-flight
export FSUAE="$PWD/tmp/phase7-debugger-v2/fs-uae"
SLAVE="$PWD/tmp/scene-flight/WingCommanderCD32.Slave" \
WHD_ARGS='CUSTOM1=3 CUSTOM2=2 CUSTOM3=1 CUSTOM4=0 CUSTOM5=0' \
WARP=1 INTRO_STOCK_CLOCK=1 AMIGA_SETUP=a1200-fast \
python3 tools/boot_gate.py --calibrate --output tmp/scene-layout
python3 tools/timing_capture.py \
  --fixture tmp/scene-flight/WingCommanderCD32.Slave \
  --layout tmp/scene-layout/layout.json --windows 20 --machine a1200-030 \
  --held-key 40 --scene-samples 120 --pause --output tmp/scene-fire-pal
python3 tools/timing_capture.py \
  --fixture tmp/scene-flight/WingCommanderCD32.Slave \
  --layout tmp/scene-layout/layout.json --windows 20 --machine a1200-030 \
  --held-key 4e --ntsc --scene-samples 120 --output tmp/scene-turn-ntsc
python3 tools/timing_scene_report.py tmp/scene-fire-pal tmp/scene-turn-ntsc \
  --negative-controls --output tmp/scene-report.json
python3 tools/timing_report.py tmp/scene-fire-pal tmp/scene-turn-ntsc \
  --output tmp/scene-clock-report.json
python3 tools/timing_scene_check.py tmp/scene-candidate \
  --flame-run tmp/scene-turn-ntsc --output tmp/scene-native-check
python3 tools/timing_adapter_check.py tmp/scene-candidate --output tmp/scene-install-check
python3 tools/timing_presentation_check.py tmp/scene-candidate --output tmp/scene-ownership-check
python3 tools/timing_player_check.py tmp/scene-candidate --output tmp/scene-player-check
python3 tools/timing_input_check.py tmp/scene-candidate --output tmp/scene-input-check
python3 tools/timing_modal_check.py tmp/scene-candidate --output tmp/scene-modal-check
```

Use the pinned retained observer hash and the established 030 compatibility setting
from phase 9. No new instrument or CPU matrix is required. Native checks also use
the retained `tmp/phase7-combat-controls/start-fast.bin` fixture. The flame check
selects a real class-7 frame from the supplied flight and executes its native
allocator on both CPU models; absence of an exercised frame fails the check.

`--scene-samples` collects at most 160 pictures after the uninterrupted timing
windows. At the post-render boundary it retains the data hunk and slave snapshot,
then the data hunk again after restoration. The scene report validates independent
position arithmetic, every saved range, unchanged gameplay fields within a tick,
projected movement, and one-tick forecast error against the next authoritative
update. Native axis routines independently supply the next-orientation oracle.
These breakpoint-separated snapshots must not be used to report FPS.
`--negative-controls` retains corrupted copies under the report's `tmp/` directory
and requires rejection of both a wrong predicted position and a failed restoration.

Final retained outputs are `tmp/phase10-isolated-fire-pal/` and
`tmp/phase10-isolated-turn-ntsc/`, with `tmp/phase10-complete-scenes.json` and
`tmp/phase10-gate-clock.json`. The non-VERIFY build is
`tmp/phase10-isolated-candidate/`; native evidence and exact hashes are listed in
[internals](internals.md#phase-10-renderer-only-prediction-gate). The first turning
fixture exposed native flame allocations surviving extra pictures; only the
isolated final fixtures pass the complete state-restoration gate.

For static inspection, the new guarded game seam is `E:28c86` (file `28cb2`),
while `E:2914c` (file `29178`) supplies native temporary flame construction:

```sh
python3 -m amigaxdev.disasm dis --cpu 68020 \
  tmp/cd32-static/wing.english.h0.bin 0 0x28c86 0x28f96
python3 -m amigaxdev.disasm dis --cpu 68020 \
  tmp/cd32-static/wing.english.h0.bin 0 0x2914c 0x294fa
```

Phase 10 passes its gate. Flight conversion is integrated in phase 11 below; full visual,
campaign, device and hardware play-throughs remain later coverage.


## Phase 11 flight conversion

`--timing`, `CUSTOM1=3` includes changed-block conversion during active 320×200
flight. It reserves 128000 bytes of FAST history before game startup. Other
geometries, inactive flight and failed allocation use the original converter.
Original reconstruction and the separate `--render` intro experiment remain
available. No cache request, gameplay instruction or motion rate is changed by
this rendering pass. The original limiter is retained.

Build and native checks (fresh output directories are required):

```sh
. amiga/env.sh
python3 tools/reconstruct.py --timing --output tmp/flight-render-candidate
python3 tools/flight_render_check.py tmp/flight-render-candidate \
  --output tmp/flight-render-native.json
python3 tools/timing_adapter_check.py tmp/flight-render-candidate \
  --output tmp/flight-render-install
python3 tools/timing_scene_check.py tmp/flight-render-candidate \
  --output tmp/flight-render-scene-native
python3 tools/reconstruct.py --output tmp/flight-render-original
```

The native converter check executes the original binary and the candidate on
020/040 models and independently checks pixel-to-plane packing. It covers
alternating/replaced destinations, unchanged and sparse/dense source changes,
128/166-row fallback, inactive/disabled flight, allocation-failure fallback,
source/register preservation and write bounds. It checks complete outputs, not
just dirty blocks. Native execution is correctness evidence, never a timer.

For the live same-picture gate, `--flight-verify` allocates an additional 64000-byte
**CHIP** reference, runs the original converter on exactly the same source, and
compares every planar longword. A mismatch aborts. The read-only retained observer
brackets candidate and original conversion separately, excluding the limiter,
comparison and WaitBOVP. Both destinations must be CHIP and the source FAST.
The report discards first-use full conversions and a final comparison still in
progress. Native sabotage of an unchanged planar byte must trigger the twin abort.

```sh
python3 tools/flight_fixture.py --timing --flight-verify --nav 1 \
  --output tmp/flight-render-twin
python3 tools/flight_render_check.py tmp/flight-render-twin \
  --output tmp/flight-render-twin-native.json
export FSUAE="$PWD/tmp/phase7-debugger-v2/fs-uae"
SLAVE="$PWD/tmp/flight-render-twin/WingCommanderCD32.Slave" \
WHD_ARGS='CUSTOM1=3 CUSTOM2=2 CUSTOM3=1 CUSTOM4=0 CUSTOM5=0' \
WARP=1 INTRO_STOCK_CLOCK=1 AMIGA_SETUP=a1200-fast \
python3 tools/boot_gate.py --calibrate --output tmp/flight-render-twin-layout
python3 tools/timing_capture.py \
  --fixture tmp/flight-render-twin/WingCommanderCD32.Slave \
  --layout tmp/flight-render-twin-layout/layout.json --windows 4 \
  --machine a1200-030 --held-key 40 --output tmp/flight-render-twin-030
python3 tools/timing_capture.py \
  --fixture tmp/flight-render-twin/WingCommanderCD32.Slave \
  --layout tmp/flight-render-twin-layout/layout.json --windows 6 \
  --machine a1200-fast --held-key 4e --output tmp/flight-render-twin-020
python3 tools/flight_render_report.py \
  tmp/flight-render-twin-030 tmp/flight-render-twin-020 \
  --output tmp/flight-render-conversion.json
```

Use the pinned phase-7 observer and the established 030 cache-model compatibility
setting, applied by the capture tool. The twin is diagnostic and cannot establish
normal-build FPS. `--flight-control` is a same-size diagnostic that forces full
conversion plus history refresh; its extra copy must not be counted as the original
converter's cost. Neither diagnostic belongs in a release.

For normal-build timing, build a fresh `flight_fixture.py --timing --nav 1` fixture,
calibrate that fixture separately, and capture 20 windows on 030: held right (`4e`)
in PAL with `--scene-samples 40 --pause`, then held fire (`40`) with `--ntsc`.
Run `timing_report.py` on both and `timing_scene_report.py --negative-controls` on
the PAL capture. These are the phase-10 commands above with the new fixture; no
new emulator or full CPU matrix is necessary.

Accepted artifacts: `tmp/phase11-candidate/`, `tmp/phase11-native-bounds.json`,
`tmp/phase11-twin-native-bounds.json`, `tmp/phase11-conversion-final.json`,
`tmp/phase11-clock-gate.json`, `tmp/phase11-scene-gate.json`,
`tmp/phase11-scene-native/` and `tmp/phase11-install/`. Live inputs are
`tmp/phase11-twin-final-{fire,turn-020}/`, `tmp/phase11-turn-pal/` and
`tmp/phase11-fire-ntsc/`. The normal source rebuild is byte-identical to the tested
candidate. All captured/derived material stays in `tmp/`.

Stop at the phase-11 gate. Full campaign, visual/hardware acceptance, unified
options and release packaging are phase 12.

## Phase 11b frame budget (A1–A3)

`--frame-stats` (with `--timing`) adds a diagnostic recorder to the slave. Each
frame part writes one longword: event id, the game's VBL count relative to the
start, and the beam line. After 150 active fields it fills 16384 records and the
next loop entry saves `framestats.bin` with `resload_SaveFile`. The normal timing
build is unchanged byte for byte. Because the slave records and saves the data
itself, it works with any emulator configuration, and on real hardware with
WHDLoad's `NoWriteCache` option (WHDLoad otherwise keeps saved files in memory
until exit).

```sh
. amiga/env.sh
python3 tools/flight_fixture.py --timing --frame-stats --nav 1 --output tmp/a1-fixture
# Shared preset, emulated data cache and indirect board off (they do not boot here):
python3 tools/frame_capture.py --fixture tmp/a1-fixture/WingCommanderCD32.Slave \
  --machine a1200-040 --baseline-cache-model --custom5 1 --output tmp/a3-040-c5-1
# Debugger builds wait for gdb: use --debugger with a calibrated layout.
export FSUAE="$PWD/tmp/phase7-debugger-v2/fs-uae"
SLAVE="$PWD/tmp/a1-fixture/WingCommanderCD32.Slave" \
WHD_ARGS='CUSTOM1=3 CUSTOM2=2 CUSTOM3=1 CUSTOM4=0 CUSTOM5=1' \
WARP=1 INTRO_STOCK_CLOCK=1 AMIGA_SETUP=a1200-fast \
python3 tools/boot_gate.py --calibrate --output tmp/a1-layout
python3 tools/frame_capture.py --fixture tmp/a1-fixture/WingCommanderCD32.Slave \
  --machine a1200-040 --timing-core --options NoMMU --custom5 1 \
  --debugger --layout tmp/a1-layout/layout.json --output tmp/a3-040core-c5-1
python3 tools/frame_report.py tmp/a3-*/ --output tmp/a3-report.json
```

A1 cross-check against the read-only observer (030, held fire):

```sh
python3 tools/frame_capture.py --fixture tmp/a1-fixture/WingCommanderCD32.Slave \
  --machine a1200-030 --baseline-cache-model --custom5 1 --debugger --observer \
  --layout tmp/a1-layout/layout.json --held-key 40 --output tmp/a1-030-observer-fire
python3 tools/frame_check.py tmp/a1-030-observer-fire --output tmp/a1-030-observer-fire/check.json
```

The check requires the same number of pictures per displayed field as observed
publications (`E:3378e`). The only exceptions allowed are pictures published
exactly on a field edge, which the recorder flags as ambiguous. Elapsed time
must agree within one field. `WC_CPU_SPEED=max` (`--cpu-speed max`) is available
but is not an upper bound: in these runs it was slower than `real`.

## Phase 11b public options and uncapped flight (B1)

The `--release` builder now means the public-option **candidate**, not an approved
release. `CUSTOM1=0/1` selects English/German; `CUSTOM5=0` selects enhanced English
(or normal German), and 1–4 select Psygore's former 0–3. The experimental
`--timing` and `--render` builders keep their earlier options and binary behavior.
The authored `release/ReadMe` documents the changed numbering and fallbacks.

```sh
. amiga/env.sh
python3 tools/reconstruct.py --release --output tmp/b1-release
python3 tools/release_check.py tmp/b1-release --negative-controls --output tmp/b1-native-gate.json
python3 tools/flight_render_check.py tmp/b1-release --output tmp/b1-flight-native.json
python3 tools/timing_adapter_check.py tmp/b1-release --output tmp/b1-install
python3 tools/reconstruct.py --timing --output tmp/b1-legacy-timing
python3 tools/reconstruct.py --output tmp/b1-original
```

The native gate covers language/mode boundaries, WHDLoad cache requests, full
converter pixels and counted limiter calls. TOD waits are stubbed only in the
CPU oracle: both active-flight paths (changed blocks and full-conversion fallback)
must bypass the wait, while nonflight and Psygore modes must dispatch it as
specified. Wrong mode mapping, uncapped nonflight and capped flight fallbacks
are deliberate negative controls and must fail. These checks do not measure time.
The installation gate compares the whole code hunk and registers/CCR with the
existing patch contract, including unchanged option-off code.

Build a separate diagnostic Nav-1 fixture for frame measurements. Its recorder
is absent from the normal candidate. The public-option recorder supports only
`CUSTOM5=0`; Psygore modes do not install the timing hooks that drive it.

```sh
python3 tools/flight_fixture.py --release --frame-stats --nav 1 --output tmp/b1-frames-v2
export FSUAE="$PWD/tmp/phase7-debugger-v2/fs-uae"
DEBUG_PORT=2499 SLAVE="$PWD/tmp/b1-frames-v2/WingCommanderCD32.Slave" \
WHD_ARGS='CUSTOM1=0 CUSTOM2=2 CUSTOM3=1 CUSTOM4=0 CUSTOM5=0' \
WARP=1 INTRO_STOCK_CLOCK=1 AMIGA_SETUP=a1200-fast \
python3 tools/boot_gate.py --calibrate --output tmp/b1-layout-v2
python3 tools/frame_stats_check.py tmp/b1-frames-v2 --output tmp/b1-recorder-native.json
DEBUG_PORT=2499 python3 tools/frame_capture.py \
  --fixture tmp/b1-frames-v2/WingCommanderCD32.Slave --machine a1200-030 \
  --baseline-cache-model --options 'CACHE DCACHE' --custom5 0 --debugger --observer \
  --layout tmp/b1-layout-v2/layout.json --output tmp/b1-030-gate
python3 tools/frame_check.py tmp/b1-030-gate --output tmp/b1-030-gate/check.json
DEBUG_PORT=2499 python3 tools/frame_capture.py \
  --fixture tmp/b1-frames-v2/WingCommanderCD32.Slave --machine a1200-040 \
  --timing-core --baseline-cache-model --options NoMMU --custom5 0 --debugger \
  --layout tmp/b1-layout-v2/layout.json --output tmp/b1-040core-gate
python3 tools/frame_report.py tmp/b1-030-gate tmp/b1-040core-gate \
  --output tmp/b1-frame-gate.json
```

Use fresh output names on reruns. The 040 core requires the same
`--baseline-cache-model` compatibility setting used in A3 (indirect board and
emulated data cache off); it is still not a calibrated hardware model. WHDLoad's
cache policy and emulated hardware-cache modeling are distinct. Each capture
records actual CACR. No key is held in these bounded Nav-1 windows.
The B1 evidence predates B2 below. The current public candidate defers buffer
reuse, retains two buffers and keeps the existing prediction policy; the reported horizontal-row glitches remain
unresolved. No archive is built by these commands.

The recorder now requires two agreeing beam-line reads. VPOSR/VHPOSR longword
reads are not atomic on the chipset bus: an initial 040 capture contained line
255, torn line 0, then line 260 in the same VBL interval. The unchanged report
rejected it. `frame_stats_check.py` injects torn forward/backward boundary reads,
checks register/CCR preservation, and rejects a sabotaged single-read recorder.
The corrected live recorder is cross-checked against the independent publication
observer on 030. This diagnostic-only fix does not change the normal slave.

## Phase 11b deferred buffer reuse (B2)

`--release` enables the B2 queue/early-VBL handoff in enhanced English flight.
It preserves B1's public options; the separate experimental `--timing` binary
still retains the earlier display wait. Normal builds allocate no new display
buffers or recorder memory. Use a fresh output directory for each build/run.

```sh
. amiga/env.sh
python3 tools/reconstruct.py --release --output tmp/b2-final
python3 tools/buffer_check.py tmp/b2-final --output tmp/b2-buffer-final.json
python3 tools/release_check.py tmp/b2-final --negative-controls --output tmp/b2-options-final.json
python3 tools/flight_render_check.py tmp/b2-final --output tmp/b2-pixels-final.json
python3 tools/timing_adapter_check.py tmp/b2-final --output tmp/b2-install-final
python3 tools/reconstruct.py --timing --output tmp/b2-legacy
python3 tools/reconstruct.py --output tmp/b2-original
python3 tools/flight_fixture.py --release --frame-stats --nav 1 --output tmp/b2-frames-compact
python3 tools/frame_stats_check.py tmp/b2-frames-compact --output tmp/b2-recorder-budget.json
export FSUAE="$PWD/tmp/phase7-debugger-v2/fs-uae"
DEBUG_PORT=2499 SLAVE="$PWD/tmp/b2-frames-compact/WingCommanderCD32.Slave" \
WHD_ARGS='CUSTOM1=0 CUSTOM2=2 CUSTOM3=1 CUSTOM4=0 CUSTOM5=0' \
WARP=1 INTRO_STOCK_CLOCK=1 AMIGA_SETUP=a1200-fast \
python3 tools/boot_gate.py --calibrate --output tmp/b2-layout-compact

for cell in 030 040 ntsc; do
  case "$cell" in
    030)  machine=a1200-030; options='CACHE DCACHE'; extra=() ;;
    040)  machine=a1200-040; options=NoMMU; extra=(--timing-core) ;;
    ntsc) machine=a1200-030; options='CACHE DCACHE'; extra=(--ntsc) ;;
  esac
  DEBUG_PORT=2499 python3 tools/frame_capture.py \
    --fixture tmp/b2-frames-compact/WingCommanderCD32.Slave \
    --machine "$machine" --baseline-cache-model --options "$options" \
    --custom5 0 --debugger --observer --display-sample "${extra[@]}" \
    --layout tmp/b2-layout-compact/layout.json --output "tmp/b2-$cell-gate"
  python3 tools/frame_check.py "tmp/b2-$cell-gate" \
    --output "tmp/b2-$cell-gate/check.json"
  python3 tools/buffer_report.py "tmp/b2-$cell-gate" \
    --layout tmp/b2-layout-compact/layout.json --build tmp/b2-frames-compact \
    --output "tmp/b2-$cell-gate/buffer-check.json"
done
python3 tools/frame_report.py tmp/b2-030-gate tmp/b2-040-gate tmp/b2-ntsc-gate \
  --output tmp/b2-final-gate.json
```

Run the loop with `/bin/bash` (including macOS 3.2). Captures stop only their owned
emulator through the shared helper. The accepted 030/040 PAL snapshots were taken
before the display-trace pathname fix; their frame/ownership/copper checks use
complete memory snapshots and ledgers, not screenshots. The NTSC sample includes
three actual display fields in `display.bin`. Current `--display-sample` saves
both RAM regions and the trace, and rejects a missing trace.

`buffer_check.py` executes the original publisher/teardown and authored request
path on native 020/040 models. It proves pending buffers block reuse, blank-window
and lock failures defer, IRQ registers/CCR survive, inactive publication is
unchanged, and teardown drains before release. It rejects removed ownership waits
and a removed COPJMP2 strobe. Converter checks independently cover every output
pixel, including allocation fallback and nonflight.

The public diagnostic records **8192 main events** to `framestats.bin` and a
separate IRQ-only `displaystats.bin` ledger. Both fit the original 65552-byte
FAST allocation; allocating another large FAST block changes game memory
placement and is not an acceptable timing fixture. Native budget checks and the
live FAST-source assertion guard against this. The old experimental timing
recorder remains 16384 events. Frame reports derive displayed FPS/histograms from
the new ledger, and call the pre-conversion ownership span `display_wait`.

`frame_check.py` anchors the comparison to `frame_epoch`, read from the actual
recorder state, and fails on mismatches. A search for a best offset is ambiguous
when every field contains one picture, so it is not used for B2. The first accepted
030 record's epoch was recovered from its complete FAST snapshot; the capture tool
now saves it directly for every buffered debugger run.

`buffer_report.py` checks converter targets against actual displayed planes,
requires FAST chunky/CHIP planar placement, checks both lists' eight planes/FMODE,
confirms the copinit setup and blank deadline, and reports late deferrals/input
overflows. Its scope is continuous Nav-1 flight on the pinned KickEmu display
path. Full modal/mission and visual acceptance remain open. The normal B2 artifact
has no recorder, ownership diagnostic abort or extra allocation. Stop before C1.
