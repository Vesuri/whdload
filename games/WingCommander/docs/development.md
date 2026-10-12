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

## Phase 4: cache audits and profiling preflight

The phase 4 gate is open. The tools below collect cache evidence and diagnose
instrument coverage; they do **not** establish calibrated accelerated timing.
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

Only the stock-multiplier 020 backend is admitted by this collector. It checks
model, MMU backend, cycle-exact mode and actual cycle unit 128. Its cache audit
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
unmatched returns and difference from phase 3 must be resolved before accepting
routine percentages or a rendering ceiling. The negative test creates damaged
fixtures below its fresh `tmp/` output and requires rejection of every one.

Retained phase 4 results and binary digests are listed in `internals.md`. No
accelerated FPS, routine-cost comparison, full-scene DMA/idle result or rendering
ceiling has yet passed the phase 4 gate.


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
