# Development

## Inputs

Three archives are the inputs: Psygore's v1.0 installer (`WingCommander.lha`) and the
pre-installed OCS (SPS 1657, `WingCommander_v1.0_1657.lha`) and CD32
(`WingCommander_v1.0_CD32.lha`) drawers. `inputs.sha256` pins the received files; the
fingerprints are not an independently authenticated upstream release.

`make unpack ARCHIVES=<directory>` copies them into `tmp/archives/`, checks them and
unpacks them into `tmp/game/`: `WingCommanderHD` (the installer), `WingCommander` (OCS)
and `WingCommanderCD32`, each with its `.info`. A drawer already there is kept unless
`FORCE=1`; its contents are not revalidated. Tools that read an archive check it against
its pin first (`tools/archives.py`).

The drawers in `tmp/game/` are reference copies: the generators read the original
slaves and game files there, and every boot copies a drawer to a fresh drive under
`tmp/run/`. Never commit archives or extracted contents.

## Shared environment

The make targets load the shared environment themselves. The tools run in
`games/WingCommander` after `. ../../common/env.sh`, which sources `${AMIGA_ENV}` or the
conventional `~/.local/share/amiga/env.sh`. The shared environment supplies toolchain,
WHDLoad, ROM and launcher variables. Install shared prerequisites through AmigaXDev;
ROM/OS sources are user supplied.

## Builds and runs

`game.conf` names the two variants, `WingCommanderCD32` (the default) and
`WingCommander` (OCS); `game.sh` builds them with the generators in `tools/`:

| Build | CD32 (`WingCommanderCD32`) | OCS (`WingCommander`) |
|---|---|---|
| `release` (`make slave`) | `reconstruct.py --variant cd32 --release` | `ocs_memory_build.py --public` |
| `verify` | `reconstruct.py --variant cd32 --verify` | none |
| `reconstruct` | `reconstruct.py --variant cd32`: the original, byte for byte | `reconstruct.py --variant ocs` |
| `render`, `render-control`, `render-verify` | `--render`, `--render-control`, `--render --render-verify` | none |

`make build BUILD=<name> [VARIANT=<variant>]` writes `tmp/build/<name>/<variant>.Slave`
and the generator's whole output directory beside it as `tmp/build/<name>/<variant>/`
(`build.json`, `slave.lst`, `payload.bin`, the release ReadMe and the OCS icon), which the
checking tools take as their build argument. `make verify` exists only for CD32:
`make verify VARIANT=WingCommanderCD32`. Other diagnostic builds (timing, ceiling, cache
audit, frame statistics, OCS candidates) call the generators directly with a new
`--output` below `tmp/`, as the sections below show. `make check` checks the release
build against `release/slaves.sha256`, rebuilds both reconstructions (each asserts
byte identity with the pinned original) and runs `release_check.py`,
`ocs_options_check.py` and the installer staging check.

`make run` boots the release build (common/run.sh, the repository's `docs/running.md`):
CD32 on `a1200-fast` with `WHD_ARGS` defaulting to `CUSTOM5=0 DCACHE`, OCS
(`VARIANT=WingCommander`) on `a3000` with `CUSTOM5=1 DCACHE`. An explicitly empty
`WHD_ARGS=` selects the original behaviour. A run with `SLAVE` (`SLAVE=original`, the
shipped slave, or any build) gets no default options, and for OCS boots the `a500`
baseline unless `SETUP` is given. On `a500` the OCS variant gets 4 MB of Zorro II Fast RAM
and no slow RAM. `a1200-040` and `a1200-060` boot `FSUAE_MMU` (AmigaXDev's build with the
MMU write-cache correction, the same binary `tools/build_mmu_fix.py` builds), everything
else `FSUAE_ARM`, unless `FSUAE` is given. The boot drive keeps the archive's slave
beside a replaced one as `<drawer>.original`, and a public OCS slave gets the generated
icon with its Enhanced framerate tooltype. The machine edits the harness selects
(`INTRO_STOCK_CLOCK`, `OCS_STOCK_CLOCK`, `WC_NOMMU_CORE`, `WC_BASELINE_CACHE_MODEL`,
`WC_CPU_SPEED`, `WC_INSTANT_BLITTER`) are `game.sh`'s `game_setup`; the sections below
describe each.

The harness boots through `tools/wc_run.py`: every capture directory below `tmp/` is its
own run instance, so its emulator, drives (`tmp/run/<instance>/.run/dh0`, `dh1`),
screenshots and gdb-stub port are its own. `python3 tools/wc.py serve` runs in the
instance `cap` unless `INSTANCE` names another.

## Current commands

Input verification and unpacking, static identification, reconstruction,
windowed boots, a state-driven A/B gate and experimental phase-6 rendering
builds/checks are implemented.
The phase 2 launcher and byte-identical reconstruction are available; the phase 2 boot gate is complete. All shell tooling is written
for `/bin/bash` 3.2.

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
. ../../common/env.sh
make unpack
python3 tools/cd32_static.py --output tmp/cd32-static
```

The output directory must be new and below `tmp/`; use a different name on
subsequent runs. The script verifies the installer/CD32 archives against
`inputs.sha256` **before extraction**, extracts fresh copies only inside
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
. ../../common/env.sh
python3 tools/reconstruct.py --variant cd32 --output tmp/reconstructed
make run SLAVE=tmp/reconstructed/WingCommanderCD32.Slave
make stop
WHD_ARGS=CUSTOM5=0 WINDOW=front python3 tools/wc.py serve
# In a second shell with the same environment:
python3 tools/wc.py shot tmp/boot.png
python3 tools/wc.py quit
```

The CD32 defaults: native `FSUAE_ARM`, shared `a1200-fast`, PAL, 68EC020, 2 MiB chip
plus 8 MiB fast, windowed, real speed. `WHD_ARGS` selects the original Custom options.
Each boot copies the pristine `tmp/game/WingCommanderCD32` to a fresh drive; no game
tree is changed. `kick40068.A1200` with its `.RTB`, `WORKBENCH_ADF` and
`WHDLOAD_BINARY` come from the supplied shared environment. The interactive and
debugger runs are the instances `default` and `cap` under `tmp/run/`. Process cleanup
uses `FSUAE_COMMON`; a recorded emulator that another directory started is never
stopped.

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
revision and modified-file digests in `tools/manifest/debugger.tsv`, copies that build
under `tmp/`, recompiles the two changed translation units and links locally.
It does not install or overwrite shared files. This is a rebuild from the supplied
configured toolchain, not a self-contained emulator release. Every capture records
the actual emulator and slave SHA-256.

```sh
. ../../common/env.sh
python3 tools/build_debugger.py --output tmp/debugger
export FSUAE="$PWD/tmp/debugger/fs-uae"
python3 tools/reconstruct.py --variant cd32 --output tmp/control
python3 tools/reconstruct.py --variant cd32 --verify --output tmp/verify
python3 tools/reconstruct.py --variant cd32 --verify-control --output tmp/verify-control

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
four-byte call at `S:14da` with a call to the appended seam in `src/verify.s`.
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
bytes are unchanged. The added source input is pinned in `tools/manifest/debugger.tsv`.
The `trace-window-all` monitor command explicitly enables RAM instruction PCs;
its acknowledgement is mandatory. The observer runs in the cycle-exact 68020
interpreter and records selected PCs, registers, physical fields, emulator cycle
stamps and game music state. It does not insert guest instructions or change
registers, memory, clocks or inputs. Other CPU backends are not validated.

From the project root, with new output names:

```sh
. ../../common/env.sh
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
. ../../common/env.sh
python3 tools/reconstruct.py --variant cd32 --cache-audit --output tmp/cache-audit-slave
python3 tools/reconstruct.py --variant cd32 --output tmp/stock-recheck
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
. ../../common/env.sh
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
. ../../common/env.sh
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
. ../../common/env.sh
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
python3 tools/reconstruct.py --variant cd32 --ceiling control --output tmp/ceiling-control-slave
python3 tools/reconstruct.py --variant cd32 --ceiling c2p --output tmp/ceiling-c2p-slave
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

Independent runs may use distinct `INSTANCE` names and explicit
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
python3 tools/reconstruct.py --variant cd32 --ceiling drawing-control --output tmp/drawing-control-slave
python3 tools/reconstruct.py --variant cd32 --ceiling drawing-bitmap --output tmp/drawing-bitmap-slave
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
. ../../common/env.sh
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
. ../../common/env.sh
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
. ../../common/env.sh
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
. ../../common/env.sh
python3 tools/reconstruct.py --variant cd32 --render --output tmp/render
python3 tools/reconstruct.py --variant cd32 --render-control --output tmp/render-control
python3 tools/reconstruct.py --variant cd32 --render --render-verify --output tmp/render-twin
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
. ../../common/env.sh
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
`tmp/phase7-fixture-repro-verified/`. Source `../../common/env.sh` first: the assembler
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
. ../../common/env.sh
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
. ../../common/env.sh
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
. ../../common/env.sh
python3 tools/reconstruct.py --variant cd32 --timing --output tmp/timing-candidate
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
. ../../common/env.sh
python3 tools/reconstruct.py --variant cd32 --timing --output tmp/scene-candidate
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
flight. It reserves 128000 history bytes in the slave, outside the fixed native
game-memory pool. Other geometries, inactive flight and non-Fast history storage
use the original converter.
Original reconstruction and the separate `--render` intro experiment remain
available. No cache request, gameplay instruction or motion rate is changed by
this rendering pass. The original limiter is retained.

Build and native checks (fresh output directories are required):

```sh
. ../../common/env.sh
python3 tools/reconstruct.py --variant cd32 --timing --output tmp/flight-render-candidate
python3 tools/history_storage_check.py tmp/flight-render-candidate
python3 tools/flight_render_check.py tmp/flight-render-candidate \
  --output tmp/flight-render-native.json
python3 tools/timing_adapter_check.py tmp/flight-render-candidate \
  --output tmp/flight-render-install
python3 tools/timing_scene_check.py tmp/flight-render-candidate \
  --output tmp/flight-render-scene-native
python3 tools/reconstruct.py --variant cd32 --output tmp/flight-render-original
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
. ../../common/env.sh
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
. ../../common/env.sh
python3 tools/reconstruct.py --variant cd32 --release --output tmp/b1-release
python3 tools/release_check.py tmp/b1-release --negative-controls --output tmp/b1-native-gate.json
python3 tools/flight_render_check.py tmp/b1-release --output tmp/b1-flight-native.json
python3 tools/timing_adapter_check.py tmp/b1-release --output tmp/b1-install
python3 tools/reconstruct.py --variant cd32 --timing --output tmp/b1-legacy-timing
python3 tools/reconstruct.py --variant cd32 --output tmp/b1-original
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
. ../../common/env.sh
python3 tools/reconstruct.py --variant cd32 --release --output tmp/b2-final
python3 tools/buffer_check.py tmp/b2-final --output tmp/b2-buffer-final.json
python3 tools/release_check.py tmp/b2-final --negative-controls --output tmp/b2-options-final.json
python3 tools/flight_render_check.py tmp/b2-final --output tmp/b2-pixels-final.json
python3 tools/timing_adapter_check.py tmp/b2-final --output tmp/b2-install-final
python3 tools/reconstruct.py --variant cd32 --timing --output tmp/b2-legacy
python3 tools/reconstruct.py --variant cd32 --output tmp/b2-original
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


## Cached 040 visual regression and local emulator correction

`make run` boots `FSUAE_MMU` on a1200-040 and a1200-060 when `FSUAE` is unset. It fixes
six MMU write-attribute lookups in the pinned core. `FSUAE_MMU` is the binary
`tools/build_mmu_fix.py` builds (the same SHA-256, `b668456f…`, recorded in its
`mmu-fix.json`), installed by AmigaXDev; the tool remains for rebuilding it and for the
audit builds. `FSUAE_SOURCE` selects the configured source tree; the default,
`$AMIGA_SHARE/fs-uae-aprof-build/fs-uae`, is no longer installed by AmigaXDev. Revision
and source hashes are checked against `tools/manifest/mmu-fix.tsv` before copying.
Existing outputs and the shared source remain untouched. `--ensure` accepts only the
recorded intact normal binary.

```sh
. ../../common/env.sh
python3 tools/build_mmu_fix.py --ensure
python3 tools/build_mmu_fix.py --audit --output tmp/mmu-fixed-audit-final
python3 tools/build_mmu_fix.py --audit --unfixed-control --output tmp/mmu-control-audit

# Calibrate each slave with the same setup used by the pixel observer.
FSUAE="$FSUAE_MMU" DEBUG_PORT=2499 \
SLAVE="$PWD/tmp/b2-final/WingCommanderCD32.Slave" \
WHD_ARGS='CUSTOM1=0 CUSTOM5=0 CACHE DCACHE' \
AMIGA_SETUP=a1200-040 WARP=0 DETERMINISTIC=0 \
python3 tools/boot_gate.py --calibrate --output tmp/mmu-intro-layout

python3 tools/visual_capture.py --emulator tmp/mmu-fixed-audit-final \
  --slave tmp/b2-final/WingCommanderCD32.Slave \
  --layout tmp/mmu-intro-layout/layout.json --output tmp/mmu-intro-check
python3 tools/visual_capture.py --emulator tmp/mmu-control-audit \
  --slave tmp/b2-final/WingCommanderCD32.Slave \
  --layout tmp/mmu-intro-layout/layout.json --frames 20 \
  --expect-corruption --output tmp/mmu-control-check
```

For the short in-game check, calibrate the existing B2 direct Nav-1 fixture
`tmp/b2-frames-compact/WingCommanderCD32.Slave` the same way, adding
`CUSTOM2=2 CUSTOM3=1 CUSTOM4=0` to the calibration options to select direct flight.
Then pass that slave
and its layout to `visual_capture.py --frames 120`. The observer runner selects
those startup options automatically for a manifest marked `direct_flight`. The fixture generation is in
the B2 instructions above. Choose fresh output directories on repeats. The observer
validates the slave's build hash and the emulator's recorded hash, requires both
caches enabled, checks CPU and DMA pixels, and saves a normal frontend screenshot.
It uses the current cached MMU/indirect-board configuration with `DETERMINISTIC=0`;
the older deterministic boot setup stalled in this configuration. Layout calibration
may use that override; the original phase-2 acceptance gate still forces its fixed
configuration. The observer is a correctness tool and supplies no frame-rate claim.

Launch the corrected normal build for play-testing:

```sh
unset FSUAE
make run SLAVE=tmp/b2-final/WingCommanderCD32.Slave \
  SETUP=a1200-040 WHD_ARGS='CUSTOM1=0 CUSTOM5=0 CACHE DCACHE'
```


## C1: prediction at the displayed field

Build from the C1 commit, preserving unrelated work separately. The normal
candidate stays 2.0b (19.10.2026). All outputs and recordings remain below `tmp/`.

```sh
. ../../common/env.sh
python3 tools/reconstruct.py --variant cd32 --release --output tmp/c1-final
python3 tools/flight_fixture.py --release --frame-stats --nav 1 --output tmp/c1-final-frames
python3 tools/display_predict_check.py tmp/c1-final --output tmp/c1-final-native.json
python3 tools/timing_scene_check.py tmp/c1-final --output tmp/c1-final-scene-full.json
python3 tools/frame_stats_check.py tmp/c1-final-frames --output tmp/c1-final-recorder.json
python3 tools/buffer_check.py tmp/c1-final --output tmp/c1-final-buffer.json
python3 tools/release_check.py tmp/c1-final --negative-controls --output tmp/c1-final-options.json

export FSUAE="$PWD/tmp/phase7-debugger-v2/fs-uae"
DEBUG_PORT=2499 SLAVE="$PWD/tmp/c1-final-frames/WingCommanderCD32.Slave" \
WHD_ARGS='CUSTOM1=0 CUSTOM2=2 CUSTOM3=1 CUSTOM4=0 CUSTOM5=0' \
WARP=1 INTRO_STOCK_CLOCK=1 AMIGA_SETUP=a1200-fast \
python3 tools/boot_gate.py --calibrate --output tmp/c1-layout
```

Run the B2 three-cell loop with `tmp/c1-final-frames`, `tmp/c1-layout` and
`tmp/c1-final-$cell` in place of its B2 paths. Retain `--debugger --observer
--display-sample`; these are the independent A1 and ownership/copper checks.
For each completed run, also execute:

```sh
python3 tools/display_time_check.py "tmp/c1-final-$cell" \
  --output "tmp/c1-final-$cell/prediction.json"
```

The 32-byte display ledger records immutable prediction metadata at the actual
VBL handoff. The checker requires exact un-clipped display-time fractions, zero
missed deadlines and every steady phase, including the phase beyond one world
tick. Wrong target/fraction negative controls must fail. Its coverage is the
recorded flight window; a late or stalled path is not waived by this gate.
`frame_report.py` continues to read both older 16-byte and C1 32-byte ledgers.

The corrected emulator is now shared through AmigaXDev as `FSUAE_MMU`; its native
build recipe includes the MMU write-cache fix. Verify the normal cached 040 setup
without a debugger (or use the local corrected binary if that shared installation
is unavailable):

```sh
FSUAE="$FSUAE_MMU" DEBUG_PORT=2501 WARP=0 DETERMINISTIC=0 \
python3 tools/frame_capture.py --fixture tmp/c1-final-frames/WingCommanderCD32.Slave \
  --machine a1200-040 --options 'CACHE DCACHE' --custom5 0 \
  --output tmp/c1-final-cached040 --timeout 180
python3 tools/display_time_check.py tmp/c1-final-cached040 \
  --output tmp/c1-final-cached040/prediction.json
python3 tools/frame_report.py tmp/c1-final-030 tmp/c1-final-040 tmp/c1-final-ntsc \
  tmp/c1-final-cached040 --output tmp/c1-fps.json
```

`frame_capture.py` defaults remain warped/deterministic for the established
instrumented model gates; explicit `WARP=0 DETERMINISTIC=0` selects the normal
cached-MMU boot. No C2 player-translation change or release packaging is included.

## C2: per-field player translation

Use fresh `tmp/` destinations. The native motion oracle needs the pinned English
snapshot `tmp/phase7-combat-controls/start-fast.bin` from the phase-7 capture
instructions; `locate()` verifies its game identity. No snapshot is committed.

```sh
. ../../common/env.sh
python3 tools/reconstruct.py --variant cd32 --release --output tmp/c2-candidate
python3 tools/flight_fixture.py --release --frame-stats --nav 1 --output tmp/c2-frames
python3 tools/translation_check.py tmp/c2-candidate --output tmp/c2-native-complete.json
python3 tools/translation_contract_check.py tmp/c2-frames --output tmp/c2-contracts-complete.json
python3 tools/timing_adapter_check.py tmp/c2-candidate --output tmp/c2-install
python3 tools/timing_scene_check.py tmp/c2-candidate --output tmp/c2-scenes.json
python3 tools/release_check.py tmp/c2-candidate --negative-controls --output tmp/c2-options.json
python3 tools/buffer_check.py tmp/c2-candidate --output tmp/c2-buffer-native.json
python3 tools/frame_stats_check.py tmp/c2-frames --output tmp/c2-recorder.json
python3 tools/display_predict_check.py tmp/c2-candidate --output tmp/c2-display-native.json

export FSUAE="$PWD/tmp/phase7-debugger-v2/fs-uae"
DEBUG_PORT=2499 SLAVE="$PWD/tmp/c2-frames/WingCommanderCD32.Slave" \
WHD_ARGS='CUSTOM1=0 CUSTOM2=2 CUSTOM3=1 CUSTOM4=0 CUSTOM5=0' \
WARP=1 INTRO_STOCK_CLOCK=1 AMIGA_SETUP=a1200-fast \
python3 tools/boot_gate.py --calibrate --output tmp/c2-layout
```

The following loop runs under `/bin/bash` 3.2. It records steady PAL on both
required models, a held-right 040 turn and a held-right NTSC 030 turn. The 040
core remains uncalibrated; the observer uses the established cache-model settings.

```bash
for cell in 030-gate 040-steady 040-gate ntsc-gate; do
    machine=a1200-030
    options='CACHE DCACHE'
    extra=()
    case "$cell" in
        040-*) machine=a1200-040; options=NoMMU; extra+=(--timing-core) ;;
    esac
    case "$cell" in
        040-gate) extra+=(--held-key 4e) ;;
        ntsc-gate) extra+=(--held-key 4e --ntsc) ;;
    esac
    DEBUG_PORT=2499 python3 tools/frame_capture.py \
        --fixture tmp/c2-frames/WingCommanderCD32.Slave \
        --machine "$machine" --baseline-cache-model --options "$options" \
        "${extra[@]}" --custom5 0 --debugger --observer --display-sample \
        --layout tmp/c2-layout/layout.json --output "tmp/c2-$cell" --timeout 180
    python3 tools/translation_report.py "tmp/c2-$cell" --build tmp/c2-frames \
        --layout tmp/c2-layout/layout.json --output "tmp/c2-$cell/translation.json"
    python3 tools/frame_check.py "tmp/c2-$cell" --output "tmp/c2-$cell/check.json"
    python3 tools/buffer_report.py "tmp/c2-$cell" --build tmp/c2-frames \
        --layout tmp/c2-layout/layout.json --output "tmp/c2-$cell/buffers.json"
done
python3 tools/frame_report.py tmp/c2-030-gate tmp/c2-040-steady \
    tmp/c2-040-gate tmp/c2-ntsc-gate --output tmp/c2-fps.json
for cell in 030-gate 040-steady; do
    python3 tools/display_time_check.py "tmp/c2-$cell" \
        --output "tmp/c2-$cell/prediction.json"
done
```

`translation_report.py` verifies fixture identity and requires at least 500 player
fields, 100 actual native world boundaries and zero player/camera-position
corrections. Native negative controls deliberately bypass the scaler and inject
position corrections. The native trajectory comparison documents its speed and
travel tolerances, including the separate action-3 expiry allowance; fuel and
bookkeeping must match exactly.

Run `display_time_check.py` on the held-turn windows to reproduce the known C1
failure: 122/657 target misses on 040 and 72/663 on NTSC in this run. It exits with
an assertion and does not write a passing report. For the prior-build control,
repeat the 040 held-turn capture with `tmp/c1-final-frames` and `tmp/c1-layout`,
writing `tmp/c2-control-c1-turn040`. That C1 fixture must come from commit
`b16f1a2`, not a rebuild with the current C2 sources. It also misses 112/657 targets.
This is recorded C4 work; ownership correctness does not waive display-time
accuracy. The phase-12 save/load stash stays separate and must not be applied as
part of these checks. C3 follows below.


## C3: heading-aware ship forecasts

Use fresh output destinations below `tmp/`. `heading_check.py` needs the retained
phase-10 hard-turn snapshots produced by the Phase 10 commands above. It runs the
candidate against all 120 recorded inputs on native 68020/68040 models, compares
with the original motion routine, then measures one-tick error against the recorded
next states. It also checks fractional normal/afterburn/braking motion, fallback
boundaries, whole-data isolation and a disabled-solver negative control. It does
not measure performance. No extra long gameplay capture is needed for this gate.

```sh
. ../../common/env.sh
python3 tools/reconstruct.py --variant cd32 --release --output tmp/c3-final
python3 tools/flight_fixture.py --release --frame-stats --nav 1 --output tmp/c3-frames
python3 tools/heading_check.py tmp/c3-final --output tmp/c3-heading-final.json
python3 tools/timing_scene_check.py tmp/c3-final --output tmp/c3-scenes-final
python3 tools/translation_contract_check.py tmp/c3-frames --output tmp/c3-contracts.json
python3 tools/timing_adapter_check.py tmp/c3-final --output tmp/c3-install
python3 tools/release_check.py tmp/c3-final --negative-controls --output tmp/c3-options.json
python3 tools/reconstruct.py --variant cd32 --timing --output tmp/c3-experimental
python3 tools/timing_scene_check.py tmp/c3-experimental --output tmp/c3-experimental-scenes

export FSUAE="$PWD/tmp/phase7-debugger-v2/fs-uae"
DEBUG_PORT=2499 SLAVE="$PWD/tmp/c3-frames/WingCommanderCD32.Slave" \
WHD_ARGS='CUSTOM1=0 CUSTOM2=2 CUSTOM3=1 CUSTOM4=0 CUSTOM5=0' \
WARP=1 INTRO_STOCK_CLOCK=1 AMIGA_SETUP=a1200-fast \
python3 tools/boot_gate.py --calibrate --output tmp/c3-layout
DEBUG_PORT=2499 python3 tools/frame_capture.py \
  --fixture tmp/c3-frames/WingCommanderCD32.Slave --machine a1200-030 \
  --baseline-cache-model --options 'CACHE DCACHE' --custom5 0 \
  --debugger --observer --display-sample --layout tmp/c3-layout/layout.json \
  --output tmp/c3-030-gate --timeout 180
DEBUG_PORT=2499 python3 tools/frame_capture.py \
  --fixture tmp/c3-frames/WingCommanderCD32.Slave --machine a1200-040 \
  --baseline-cache-model --options NoMMU --timing-core --held-key 4e --custom5 0 \
  --debugger --observer --display-sample --layout tmp/c3-layout/layout.json \
  --output tmp/c3-040-gate --timeout 180
for cell in 030-gate 040-gate; do
  python3 tools/frame_check.py "tmp/c3-$cell" --output "tmp/c3-$cell/check.json"
  python3 tools/buffer_report.py "tmp/c3-$cell" --build tmp/c3-frames \
    --layout tmp/c3-layout/layout.json --output "tmp/c3-$cell/buffers.json"
  python3 tools/translation_report.py "tmp/c3-$cell" --build tmp/c3-frames \
    --layout tmp/c3-layout/layout.json --output "tmp/c3-$cell/translation.json"
done
python3 tools/frame_report.py tmp/c3-030-gate tmp/c3-040-gate --output tmp/c3-fps.json
python3 tools/display_time_check.py tmp/c3-030-gate --output tmp/c3-030-gate/prediction.json
```

The same display-time check on `tmp/c3-040-gate` intentionally fails: 119/656
held-turn pictures miss their target field/fraction. It must not be reported as
a passing C1 result; C4 retains this work. Both frame-rate counts and buffer
ownership checks pass. The observer uses the established cache-model settings;
this is not a calibrated physical 040 measurement.

Static reproduction of the native solver uses the pinned English hunk:

```sh
python3 -m amigaxdev.disasm dis --cpu 68020 \
  tmp/cd32-static/wing.english.h0.bin 0 0x7d1a 0x80f0
```

The C3 change is drawing-only and does not apply the deferred phase-12 save/load
stash. Stop before C4; release remains paused.

## C4: displayed cadence around world ticks

Use the C3 fixture and layout above. Its production code is unchanged: C4 checks
whether the existing queue absorbs world-tick work spikes before considering any
scheduler changes. Reuse the retained current-build 030 steady and 040 turn windows;
only the current-build 040 steady window needs a new capture. Fresh output paths
are required; the same fixture hash is enforced across all three windows.

```sh
. ../../common/env.sh
export FSUAE="$PWD/tmp/phase7-debugger-v2/fs-uae"
DEBUG_PORT=2499 python3 tools/frame_capture.py \
  --fixture tmp/c3-frames/WingCommanderCD32.Slave --machine a1200-040 \
  --baseline-cache-model --options NoMMU --timing-core --custom5 0 \
  --debugger --observer --display-sample --layout tmp/c3-layout/layout.json \
  --output tmp/c4-040-steady --timeout 180
python3 tools/frame_spike_report.py \
  --steady tmp/c3-030-gate tmp/c4-040-steady --turn tmp/c3-040-gate \
  --output tmp/c4-spikes.json
python3 tools/frame_check.py tmp/c4-040-steady --output tmp/c4-040-steady/check.json
python3 tools/buffer_report.py tmp/c4-040-steady --build tmp/c3-frames \
  --layout tmp/c3-layout/layout.json --output tmp/c4-040-steady/buffers.json
python3 tools/translation_report.py tmp/c4-040-steady --build tmp/c3-frames \
  --layout tmp/c3-layout/layout.json --output tmp/c4-040-steady/translation.json
python3 tools/display_time_check.py tmp/c4-040-steady \
  --output tmp/c4-040-steady/prediction.json
python3 tools/frame_report.py tmp/c3-030-gate tmp/c4-040-steady tmp/c3-040-gate \
  --output tmp/c4-fps.json
```

`frame_spike_report.py` gates actual display-to-display intervals from the IRQ
ledger. It also reports queue-to-queue intervals and world work, grouped by ticks
between queue submissions. It must not substitute the older report's draw-to-draw
`frame_ms` for visible cadence. Negative controls reject deliberate missed fields,
a uniform half-rate cadence and absent world coverage. Putting the held-turn
capture under `--steady` correctly fails the gate; `--turn` reports it without
claiming it passes. The held-turn C1 display-time failure remains unchanged.

No multi-tick interval occurred in these captures: the reported catch-up count is
zero, not evidence for smoothness after an artificial long stall. Both PAL steady
cells pass at one displayed picture per field; no scheduler change was needed.
Stop before D1. Heavy-scene overruns remain for rendering-cost work and acceptance;
release and the phase-12 stash remain paused.

## D1: read-only rendering-cost profile

Use the unchanged C3 release frame fixture and its calibrated **address layout**
above. Address calibration does not calibrate CPU performance. Generate fresh
scope/output files below `tmp/`; no guest code or emulator rebuild is needed.

```sh
. ../../common/env.sh
python3 tools/render_cost.py --build tmp/c3-frames \
  --layout tmp/c3-layout/layout.json --output tmp/d1-scopes-new.json
export FSUAE="$PWD/tmp/phase7-debugger-v2/fs-uae"
DEBUG_PORT=2499 python3 tools/frame_capture.py \
  --fixture tmp/c3-frames/WingCommanderCD32.Slave --machine a1200-040 \
  --baseline-cache-model --options NoMMU --timing-core --custom5 0 \
  --debugger --observer --layout tmp/c3-layout/layout.json --held-key 4e \
  --cost-scopes tmp/d1-scopes-new.json --output tmp/d1-turn-new --timeout 180
python3 tools/render_cost.py --run tmp/d1-turn-new --control tmp/c3-040-gate \
  --output tmp/d1-turn-new/costs.json
python3 tools/frame_check.py tmp/d1-turn-new --output tmp/d1-turn-new/check.json
```

For the matching 040 steady run, omit `--held-key 4e` and compare against
`tmp/c4-040-steady`. For the 030 steady gate, use `--machine a1200-030
--options 'CACHE DCACHE'`, omit `--timing-core` and the held key, and compare
against `tmp/c3-030-gate`. Keep the other flags, fixture and layout unchanged.
Use fresh output names each time. If the fixture/settings change, capture a
matching ordinary `--observer` control first instead of reusing these controls.
The reporter requires identical fixture/settings/emulator, frame records and
completed-display ledgers; it fails on differences, not just an FPS change.

Final retained reports: `tmp/d1-030-steady/costs.json`,
`tmp/d1-040-steady/final-costs.json`, and
`tmp/d1-040-turn-final/final-costs.json`. Recompute the frame-rate summary with:

```sh
python3 tools/frame_report.py tmp/d1-030-steady tmp/d1-040-steady \
  tmp/d1-040-turn-final --output tmp/d1-fps-new.json
python3 tools/display_time_check.py tmp/d1-040-turn-final \
  --output tmp/d1-040-turn-final/prediction-new.json
```

The final command **must still fail**; the ledger has 119/656 missed targets. D1 measures
those overruns and does not fix them. Report visible FPS separately from internal
work intervals. The cost report includes inclusive per-frame/per-call distributions,
call counts, and the group of internal intervals longer than one field. Nested
rows overlap; do not sum them. Comparison/loop/history is a residual after
subtracting changed-block calls, not pure comparison time. Four call-pairing
negative controls run whenever the tool is invoked. Generated scopes contain
live addresses and stay in `tmp/`; documentation uses hunk/file offsets.

D1 is the baseline for D2 below. The calibrated-040 follow-up remains blocked
by A2; these are model baselines. No release or phase-12 stash work is included.

### D2: selective prediction backups and unchanged-input geometry

Use fresh output directories under `tmp/`. The tests compare whole native data
hunks and allocator registers, including empty/reused slots, render-only flames,
range history, unchanged pad queues and every byte of a queued transition.
Unicorn proves correctness, not performance. `timing_scene_report.py` understands
both backup layouts; the C3 heading checker remains the forecast oracle for the
current release's heading-aware, extended prediction interval.

```sh
. ../../common/env.sh
python3 tools/reconstruct.py --variant cd32 --release --output tmp/d2-final
python3 tools/flight_fixture.py --release --frame-stats --nav 1 --output tmp/d2-final-frames
python3 tools/prediction_cost_check.py tmp/d2-final --output tmp/d2-final-equivalence.json
python3 tools/timing_scene_check.py tmp/d2-final --output tmp/d2-final-scenes
python3 tools/heading_check.py tmp/d2-final --output tmp/d2-final-heading.json
python3 tools/translation_contract_check.py tmp/d2-final-frames --output tmp/d2-final-contracts.json
python3 tools/timing_adapter_check.py tmp/d2-final --output tmp/d2-final-install
python3 tools/release_check.py tmp/d2-final --negative-controls --output tmp/d2-final-options.json

export FSUAE="$PWD/tmp/phase7-debugger-v2/fs-uae"
DEBUG_PORT=2499 SLAVE="$PWD/tmp/d2-final-frames/WingCommanderCD32.Slave" \
WHD_ARGS='CUSTOM1=0 CUSTOM2=2 CUSTOM3=1 CUSTOM4=0 CUSTOM5=0' \
WARP=1 INTRO_STOCK_CLOCK=1 AMIGA_SETUP=a1200-fast \
python3 tools/boot_gate.py --calibrate --output tmp/d2-final-layout
python3 tools/render_cost.py --build tmp/d2-final-frames \
  --layout tmp/d2-final-layout/layout.json --output tmp/d2-final-scopes.json

# One held-turn pair: inclusive costs and the matching observer control.
DEBUG_PORT=2499 python3 tools/frame_capture.py \
  --fixture tmp/d2-final-frames/WingCommanderCD32.Slave --machine a1200-040 \
  --baseline-cache-model --options NoMMU --timing-core --held-key 4e --custom5 0 \
  --debugger --observer --display-sample --layout tmp/d2-final-layout/layout.json \
  --cost-scopes tmp/d2-final-scopes.json --output tmp/d2-final-040-turn-cost --timeout 180
DEBUG_PORT=2499 python3 tools/frame_capture.py \
  --fixture tmp/d2-final-frames/WingCommanderCD32.Slave --machine a1200-040 \
  --baseline-cache-model --options NoMMU --timing-core --held-key 4e --custom5 0 \
  --debugger --observer --display-sample --layout tmp/d2-final-layout/layout.json \
  --output tmp/d2-final-040-turn --timeout 180
python3 tools/render_cost.py --run tmp/d2-final-040-turn-cost \
  --control tmp/d2-final-040-turn --output tmp/d2-final-040-turn-cost/costs.json

DEBUG_PORT=2499 python3 tools/frame_capture.py \
  --fixture tmp/d2-final-frames/WingCommanderCD32.Slave --machine a1200-030 \
  --baseline-cache-model --options 'CACHE DCACHE' --custom5 0 \
  --debugger --observer --display-sample --layout tmp/d2-final-layout/layout.json \
  --output tmp/d2-final-030 --timeout 180
DEBUG_PORT=2499 python3 tools/frame_capture.py \
  --fixture tmp/d2-final-frames/WingCommanderCD32.Slave --machine a1200-040 \
  --baseline-cache-model --options NoMMU --timing-core --custom5 0 \
  --debugger --observer --display-sample --layout tmp/d2-final-layout/layout.json \
  --output tmp/d2-final-040-steady --timeout 180
for cell in 030 040-steady 040-turn 040-turn-cost; do
  python3 tools/frame_check.py "tmp/d2-final-$cell" --output "tmp/d2-final-$cell/check.json"
  python3 tools/buffer_report.py "tmp/d2-final-$cell" --build tmp/d2-final-frames \
    --layout tmp/d2-final-layout/layout.json --output "tmp/d2-final-$cell/buffers.json"
  python3 tools/translation_report.py "tmp/d2-final-$cell" --build tmp/d2-final-frames \
    --layout tmp/d2-final-layout/layout.json --output "tmp/d2-final-$cell/translation.json"
done
for cell in 030 040-steady; do
  python3 tools/display_time_check.py "tmp/d2-final-$cell" --output "tmp/d2-final-$cell/prediction.json"
done
python3 tools/frame_report.py tmp/d2-final-030 tmp/d2-final-040-steady \
  tmp/d2-final-040-turn --output tmp/d2-final-fps.json
```

`buffer_report.py` resolves the conversion event by symbol, so extra cost scopes
cannot be mistaken for a conversion. The cost pair must retain byte-identical
frame and display ledgers. Initial active-slot backup excludes lazy attachment
backup inside native drawing; restore includes every saved slot. Do not sum
nested costs or equate their reduction with an identical frame-rate gain.
The held-turn display-time check still fails and must not be labelled a C1 pass.
The observer uses the established baseline cache models; hardware calibration
remains blocked on A2. D3 follows below; keep phase 12 paused.

### D3: native view-region clear and composition

D3 preserves the native row/span map and exact pixel coverage. The copy selection
uses the existing cached 020/030 renderer selection; other selections retain
native composition. Use fresh output names under `tmp/`. Native twins include
byte tails, overlap, crop/colour/bulk fallbacks and rejecting clear/span controls.

```sh
. ../../common/env.sh
python3 tools/reconstruct.py --variant cd32 --release --output tmp/d3-gate
python3 tools/view_regions_check.py tmp/d3-gate --output tmp/d3-gate-native.json
python3 tools/timing_adapter_check.py tmp/d3-gate --output tmp/d3-gate-install
python3 tools/release_check.py tmp/d3-gate --negative-controls --output tmp/d3-gate-options.json
python3 tools/flight_fixture.py --release --frame-stats --nav 1 --output tmp/d3-gate-frames
python3 tools/flight_fixture.py --release --frame-stats --nav 1 --view-control --output tmp/d3-gate-control

export FSUAE="$PWD/tmp/phase7-debugger-v2/fs-uae"
DEBUG_PORT=2499 SLAVE="$PWD/tmp/d3-gate-frames/WingCommanderCD32.Slave" \
WHD_ARGS='CUSTOM1=0 CUSTOM2=2 CUSTOM3=1 CUSTOM4=0 CUSTOM5=0' \
WARP=1 INTRO_STOCK_CLOCK=1 AMIGA_SETUP=a1200-fast \
python3 tools/boot_gate.py --calibrate --output tmp/d3-gate-layout
for arm in frames control; do
  python3 tools/render_cost.py --build "tmp/d3-gate-$arm" \
    --layout tmp/d3-gate-layout/layout.json --output "tmp/d3-gate-$arm-scopes.json"
done

# Sequential runs: one same-size A/B pair per affected model/workload.
d3_capture() {
  d3_name="$1"; d3_arm="$2"; d3_machine="$3"; d3_options="$4"
  shift 4
  DEBUG_PORT=2499 python3 tools/frame_capture.py \
    --fixture "tmp/d3-gate-$d3_arm/WingCommanderCD32.Slave" \
    --machine "$d3_machine" --options "$d3_options" --baseline-cache-model \
    --custom5 0 --debugger --observer --display-sample \
    --layout tmp/d3-gate-layout/layout.json --output "tmp/$d3_name" --timeout 180 "$@"
}
d3_capture d3-gate-030 frames a1200-030 'CACHE DCACHE' --cost-scopes tmp/d3-gate-frames-scopes.json
d3_capture d3-gate-control-030 control a1200-030 'CACHE DCACHE' --cost-scopes tmp/d3-gate-control-scopes.json
d3_capture d3-gate-040-turn-cost frames a1200-040 NoMMU --timing-core --held-key 4e --cost-scopes tmp/d3-gate-frames-scopes.json
d3_capture d3-gate-control-040-turn control a1200-040 NoMMU --timing-core --held-key 4e --cost-scopes tmp/d3-gate-control-scopes.json
# Required steady 040 gate and one explicit observer-neutrality control.
d3_capture d3-gate-040-steady frames a1200-040 NoMMU --timing-core
d3_capture d3-gate-040-turn frames a1200-040 NoMMU --timing-core --held-key 4e

python3 tools/render_cost.py --run tmp/d3-gate-040-turn-cost \
  --control tmp/d3-gate-040-turn --output tmp/d3-gate-040-turn-cost/costs.json
for cell in 030 control-030 control-040-turn; do
  python3 tools/render_cost.py --run "tmp/d3-gate-$cell" \
    --without-neutrality-control --output "tmp/d3-gate-$cell/costs.json"
done
for cell in 030 040-steady 040-turn 040-turn-cost control-030 control-040-turn; do
  python3 tools/frame_check.py "tmp/d3-gate-$cell" --output "tmp/d3-gate-$cell/check.json"
done
for cell in 030 040-steady 040-turn; do
  python3 tools/buffer_report.py "tmp/d3-gate-$cell" --build tmp/d3-gate-frames \
    --layout tmp/d3-gate-layout/layout.json --output "tmp/d3-gate-$cell/buffers.json"
  python3 tools/translation_report.py "tmp/d3-gate-$cell" --build tmp/d3-gate-frames \
    --layout tmp/d3-gate-layout/layout.json --output "tmp/d3-gate-$cell/translation.json"
done
for cell in 030 040-steady; do
  python3 tools/display_time_check.py "tmp/d3-gate-$cell" --output "tmp/d3-gate-$cell/prediction.json"
done
python3 tools/frame_report.py tmp/d3-gate-030 tmp/d3-gate-control-030 \
  tmp/d3-gate-040-steady tmp/d3-gate-040-turn tmp/d3-gate-control-040-turn \
  --output tmp/d3-gate-fps.json
python3 tools/view_regions_check.py tmp/d3-gate --run tmp/d3-gate-030 \
  --layout tmp/d3-gate-layout/layout.json --output tmp/d3-gate-current-pixels.json
```

`--view-control` changes only the two conditional native-fallback branches to
unconditional branches in the diagnostic slave. It preserves file size and
layout and is not a public option. Verify the pair differs only at those two
bytes before comparing. The final 040 turn has an explicit read-only observer
on/off check; other scoped reports deliberately say observer neutrality was not
separately checked for that capture. `--without-neutrality-control` does not
waive fixture/hash, call-pairing, timestamp or per-frame coverage checks.
The held-turn `display_time_check.py` still rejects missed targets and must not
be reported as a C1 pass. The ordinary frame recorder and independent display
observer remain the FPS instruments. Do not add nested costs or treat these model timings as hardware
calibration. D4 follows below; phase 12 remains paused.

### D4: compact complete-source comparison

The practical D4 gate retains full source coverage and independent histories for
both planar buffers. Drawing-based dirty rectangles are deferred; see the scope
and writer/invalidation requirements in `internals.md`. `--comparison-control`
is a diagnostic build of the old loop with identical size and symbol placement;
it is byte-identical to D3. Its metadata prevents treating it as a normal release.
Use fresh output names below `tmp/`.

```sh
. ../../common/env.sh
python3 tools/reconstruct.py --variant cd32 --release --output tmp/d4-final
python3 tools/reconstruct.py --variant cd32 --release --comparison-control --output tmp/d4-final-control
python3 tools/flight_render_check.py tmp/d4-final --output tmp/d4-final-native.json
python3 tools/comparison_check.py tmp/d4-final --control tmp/d4-final-control --output tmp/d4-final-boundaries.json
python3 tools/reconstruct.py --variant cd32 --timing --flight-verify --output tmp/d4-timing-twin
python3 tools/flight_render_check.py tmp/d4-timing-twin --output tmp/d4-timing-twin-check.json
python3 tools/release_check.py tmp/d4-final --negative-controls --output tmp/d4-options.json
python3 tools/timing_adapter_check.py tmp/d4-final --output tmp/d4-install
python3 tools/flight_fixture.py --release --frame-stats --nav 1 --output tmp/d4-frames
python3 tools/flight_fixture.py --release --frame-stats --nav 1 --comparison-control --output tmp/d4-frames-control

export FSUAE="$PWD/tmp/phase7-debugger-v2/fs-uae"
# D4 preserves the D3 layout exactly. Reuse its calibration for retained builds;
# for a fresh setup obtain the layout with this normal pre-window calibration.
DEBUG_PORT=2499 SLAVE="$PWD/tmp/d4-frames/WingCommanderCD32.Slave" \
WHD_ARGS='CUSTOM1=0 CUSTOM2=2 CUSTOM3=1 CUSTOM4=0 CUSTOM5=0' \
WARP=1 INTRO_STOCK_CLOCK=1 AMIGA_SETUP=a1200-fast \
python3 tools/boot_gate.py --calibrate --output tmp/d4-layout
for arm in frames frames-control; do
  python3 tools/render_cost.py --build "tmp/d4-$arm" \
    --layout tmp/d4-layout/layout.json --output "tmp/d4-$arm-scopes.json"
done

d4_capture() {
  d4_name="$1"; d4_arm="$2"; d4_machine="$3"; d4_options="$4"
  shift 4
  DEBUG_PORT=2499 python3 tools/frame_capture.py \
    --fixture "tmp/d4-$d4_arm/WingCommanderCD32.Slave" \
    --machine "$d4_machine" --options "$d4_options" --baseline-cache-model \
    --custom5 0 --debugger --observer --display-sample \
    --layout tmp/d4-layout/layout.json --output "tmp/$d4_name" --timeout 180 "$@"
}
# Sequential matched workloads; one explicit cost-observer neutrality pair.
d4_capture d4-040-turn-cost frames a1200-040 NoMMU --timing-core --held-key 4e --cost-scopes tmp/d4-frames-scopes.json
d4_capture d4-control-040-turn frames-control a1200-040 NoMMU --timing-core --held-key 4e --cost-scopes tmp/d4-frames-control-scopes.json
d4_capture d4-030 frames a1200-030 'CACHE DCACHE' --cost-scopes tmp/d4-frames-scopes.json
d4_capture d4-control-030 frames-control a1200-030 'CACHE DCACHE' --cost-scopes tmp/d4-frames-control-scopes.json
d4_capture d4-040-steady frames a1200-040 NoMMU --timing-core
d4_capture d4-040-turn frames a1200-040 NoMMU --timing-core --held-key 4e

python3 tools/render_cost.py --run tmp/d4-040-turn-cost \
  --control tmp/d4-040-turn --output tmp/d4-040-turn-cost/costs.json
for cell in 030 control-030 control-040-turn; do
  python3 tools/render_cost.py --run "tmp/d4-$cell" \
    --without-neutrality-control --output "tmp/d4-$cell/costs.json"
done
for cell in 030 control-030 040-steady 040-turn 040-turn-cost control-040-turn; do
  python3 tools/frame_check.py "tmp/d4-$cell" --output "tmp/d4-$cell/check.json"
done
for cell in 030 040-steady 040-turn; do
  python3 tools/buffer_report.py "tmp/d4-$cell" --build tmp/d4-frames \
    --layout tmp/d4-layout/layout.json --output "tmp/d4-$cell/buffers.json"
  python3 tools/translation_report.py "tmp/d4-$cell" --build tmp/d4-frames \
    --layout tmp/d4-layout/layout.json --output "tmp/d4-$cell/translation.json"
done
for cell in 030 040-steady; do
  python3 tools/display_time_check.py "tmp/d4-$cell" --output "tmp/d4-$cell/prediction.json"
done
python3 tools/frame_report.py tmp/d4-030 tmp/d4-control-030 tmp/d4-040-steady \
  tmp/d4-040-turn tmp/d4-control-040-turn --output tmp/d4-fps.json
python3 tools/comparison_check.py tmp/d4-frames --control tmp/d4-frames-control \
  --run tmp/d4-030 --run tmp/d4-040-steady --run tmp/d4-040-turn-cost \
  --layout tmp/d4-layout/layout.json --output tmp/d4-live-pixels.json
# Expected to reject the still-missed held-turn prediction deadlines:
python3 tools/display_time_check.py tmp/d4-040-turn --output tmp/d4-040-turn/prediction.json
```

Retained captures used `tmp/d3-gate-layout/layout.json`, `tmp/d4-scopes.json` and
`tmp/d4-control-scopes.json`; only names differ from the fresh recipe above.
The strict held-turn prediction check must still fail; do not relax it into a
D4 or global C1 success. Live pixel snapshots prove both destinations match their
own histories, not every intermediate frame or subjective visual acceptance.
The native checker deliberately omits the final longword comparison and requires
rejection; it also checks every byte of the first/last blocks and the entire
candidate/control binary layout. Do not treat Unicorn execution as timing.
Stop before D5; calibrated 040 measurements and phase 12 remain blocked/paused.

### D5: Kalms CPU-family comparison

`--c2p-experiment` is diagnostic only and never changes a normal release build.
The five equal-layout arms reserve the same 720-byte block-converter slot:
`control` uses the existing 030 block path, `block040` substitutes the 040 family;
`full-original`, `full030` and `full040` force full conversion on every flight
picture, with the same history copy. Both full families are already embedded.
This tests 320×200 flight, not a new intro speed or cache-policy choice.

From the project root in `/bin/bash`, with new output names if rerunning:

```sh
. ../../common/env.sh
for arm in control block040 full-original full030 full040; do
  python3 tools/flight_fixture.py --release --frame-stats --nav 1 \
    --c2p-experiment "$arm" --output "tmp/d5-$arm"
  python3 tools/flight_render_check.py "tmp/d5-$arm" \
    --output "tmp/d5-$arm-native.json"
done
export FSUAE="$PWD/tmp/phase7-debugger-v2/fs-uae"
DEBUG_PORT=2499 SLAVE="$PWD/tmp/d5-control/WingCommanderCD32.Slave" \
WHD_ARGS='CUSTOM1=0 CUSTOM2=2 CUSTOM3=1 CUSTOM4=0 CUSTOM5=0' \
WARP=1 INTRO_STOCK_CLOCK=1 AMIGA_SETUP=a1200-fast \
python3 tools/boot_gate.py --calibrate --output tmp/d5-layout
for arm in control block040 full-original full030 full040; do
  python3 tools/render_cost.py --build "tmp/d5-$arm" \
    --layout tmp/d5-layout/layout.json --output "tmp/d5-$arm-scopes.json"
done
for cpu in 030 040; do
  options='CACHE DCACHE'; extra=()
  if [ "$cpu" = 040 ]; then options=NoMMU; extra=(--timing-core); fi
  for arm in control block040 full-original full030 full040; do
    DEBUG_PORT=2499 python3 tools/frame_capture.py \
      --fixture "tmp/d5-$arm/WingCommanderCD32.Slave" --machine "a1200-$cpu" \
      --options "$options" --baseline-cache-model --custom5 0 --debugger \
      --observer --display-sample --held-key 4e --layout tmp/d5-layout/layout.json \
      --cost-scopes "tmp/d5-$arm-scopes.json" --output "tmp/d5-$cpu-$arm" \
      --timeout 180 "${extra[@]}"
    python3 tools/render_cost.py --run "tmp/d5-$cpu-$arm" \
      --without-neutrality-control --output "tmp/d5-$cpu-$arm/costs.json"
    python3 tools/frame_check.py "tmp/d5-$cpu-$arm" \
      --output "tmp/d5-$cpu-$arm/check.json"
  done
done
runs=()
for cpu in 030 040; do
  for arm in control block040 full-original full030 full040; do
    runs+=(--run "tmp/d5-$cpu-$arm")
  done
done
python3 tools/c2p_experiment_check.py --prefix tmp/d5 \
  --layout tmp/d5-layout/layout.json "${runs[@]}" --output tmp/d5-pixels.json
python3 tools/frame_report.py tmp/d5-030-*/ tmp/d5-040-*/ --output tmp/d5-fps.json
python3 tools/reconstruct.py --variant cd32 --release --output tmp/d5-release-check
cmp tmp/d5-release-check/WingCommanderCD32.Slave tmp/d4-final/WingCommanderCD32.Slave
```

The integrity checker rejects missing converters, enforces identical shared
symbols and allowed binary changes, and compares both live planar buffers with
independent packing of their own histories. Retained buffer ownership reports
were also generated with `buffer_report.py` for `tmp/d5-030-block040` and
`tmp/d5-040-block040`, using `--build tmp/d5-block040` and the D5 layout.
Native checks cover alternation,
replacement, inactive flight, smaller geometries and allocation failure. Costs
are inclusive model elapsed time; full-arm `delta_total` includes the common
history copy, while changed-block cost excludes comparison/history. Never compare
these as identical leaf operations or treat these 040 timings as hardware proof.

### Player cannon muzzle presentation

```sh
. ../../common/env.sh
python3 tools/reconstruct.py --variant cd32 --release --output tmp/muzzle-cd32-v2
python3 tools/ocs_memory_build.py --public --output tmp/muzzle-ocs-v3
python3 tools/projectile_spawn_check.py tmp/muzzle-cd32-v2 --output tmp/muzzle-cd32-path-final.json
python3 tools/ocs_prediction_check.py tmp/muzzle-ocs-v3 --output tmp/muzzle-ocs-check-final
python3 tools/intro_shot_check.py cd32 tmp/muzzle-cd32-v2 \
  --native-intro-capture tmp/intro-pal-a/title-animation-fast.bin --output tmp/muzzle-cd32-intro
python3 tools/intro_shot_check.py ocs tmp/muzzle-ocs-v3 --output tmp/muzzle-ocs-intro
python3 tools/ocs_intro_check.py tmp/muzzle-ocs-v3 --output tmp/muzzle-ocs-clock
python3 tools/timing_adapter_check.py tmp/muzzle-cd32-v2 --output tmp/muzzle-cd32-install
```

Use fresh output names when rerunning. The constructor checks share
`projectile_path_check.py`: actual native birth and movement are the reference,
with six intervals across PAL/NTSC, regular-speed movement, endpoint bounds and
whole-data restoration. Each variant adds 360 path samples. Running the updated
CD32 check against the preceding intro-contact build rejects its first player
shot position. No large recordings or live emulator run are required for this gate.

### Intro cannon contact prediction

```sh
. ../../common/env.sh
python3 tools/reconstruct.py --variant cd32 --release --output tmp/intro-shot-cd32-final
python3 tools/ocs_memory_build.py --public --output tmp/intro-shot-ocs-v2
python3 tools/intro_shot_check.py cd32 tmp/intro-shot-cd32-final \
  --native-intro-capture tmp/intro-pal-a/title-animation-fast.bin \
  --output tmp/intro-shot-cd32-impact-verified
python3 tools/intro_shot_check.py ocs tmp/intro-shot-ocs-v2 --output tmp/intro-shot-ocs-verified
python3 tools/intro_clock_check.py tmp/intro-shot-cd32-final --output tmp/intro-shot-cd32-clock.json
python3 tools/ocs_intro_check.py tmp/intro-shot-ocs-v2 --output tmp/intro-shot-ocs-clock
python3 tools/timing_adapter_check.py tmp/intro-shot-cd32-final --output tmp/intro-shot-cd32-install
python3 tools/ocs_options_check.py tmp/intro-shot-ocs-v2 --output tmp/intro-shot-ocs-options
python3 tools/modal_clock_check.py cd32 tmp/intro-shot-cd32-final --output tmp/intro-shot-cd32-modal
python3 tools/modal_clock_check.py ocs tmp/intro-shot-ocs-v2 --output tmp/intro-shot-ocs-modal
python3 tools/projectile_spawn_check.py tmp/intro-shot-cd32-final --output tmp/intro-shot-cd32-spawn.json
export FSUAE="$PWD/tmp/p13d3-debugger/fs-uae"
python3 tools/intro_shot_live_check.py cd32 tmp/intro-shot-cd32-final \
  --port 2495 --output tmp/intro-shot-cd32-live-final
python3 tools/intro_shot_live_check.py ocs tmp/intro-shot-ocs-v2 \
  --port 2496 --output tmp/intro-shot-ocs-live-final
```

Use fresh output names on repeats. The optional native-intro input is the original
CD32 title-animation checkpoint from the existing intro capture workflow. Omit
that argument to run the standalone native contact/staging checks without the
retained live capture. The replay retains native world updates; its render
checks inspect poses and state restoration, not DMA pixels or frame rate.
The live checker needs the project diagnostic emulator selected above. It samples
three moving-contact pictures and saves one screenshot per variant; it leaves
the separate interactive run untouched.

### Newly spawned projectile prediction

Build a fresh normal release and execute the native constructor/snapshot checks.
The retained combat fixture is the same one used by `timing_scene_check.py`.
All derived output stays under `tmp/`; choose fresh names when rerunning.

```sh
. ../../common/env.sh
python3 tools/reconstruct.py --variant cd32 --release --output tmp/projectile-fix-final
python3 tools/projectile_spawn_check.py tmp/projectile-fix-final \
  --output tmp/projectile-fix-final-spawn.json
python3 tools/timing_adapter_check.py tmp/projectile-fix-final \
  --output tmp/projectile-fix-final-install
python3 tools/timing_scene_check.py tmp/projectile-fix-final \
  --output tmp/projectile-fix-final-scene
python3 tools/release_check.py tmp/projectile-fix-final --negative-controls \
  --output tmp/projectile-fix-final-options.json
python3 tools/flight_render_check.py tmp/projectile-fix-final \
  --output tmp/projectile-fix-final-pixels.json
```

The spawn check covers player/enemy constructors, bolts, guided launches,
class-10 missiles/effects, alternate AI shots, simultaneous mounts and rejection
boundaries. It compares complete native constructor data/registers/CCR and
restoration after each render. Sound is stubbed; collisions and the full AI world
loop are outside this isolated check. Unicorn supplies semantics, not timing.

The short held-fire model gate uses the normal diagnostic recorder:

```sh
python3 tools/flight_fixture.py --release --frame-stats --nav 1 \
  --output tmp/projectile-fix-frames2
export FSUAE="$PWD/tmp/phase7-debugger-v2/fs-uae"
DEBUG_PORT=2499 SLAVE="$PWD/tmp/projectile-fix-frames2/WingCommanderCD32.Slave" \
WHD_ARGS='CUSTOM1=0 CUSTOM2=2 CUSTOM3=1 CUSTOM4=0 CUSTOM5=0' \
WARP=1 INTRO_STOCK_CLOCK=1 AMIGA_SETUP=a1200-fast \
python3 tools/boot_gate.py --calibrate --output tmp/projectile-fix-layout
for cpu in 030 040; do
  options='CACHE DCACHE'; extra=()
  if [ "$cpu" = 040 ]; then options=NoMMU; extra=(--timing-core); fi
  DEBUG_PORT=2499 python3 tools/frame_capture.py \
    --fixture tmp/projectile-fix-frames2/WingCommanderCD32.Slave \
    --machine "a1200-$cpu" --options "$options" --baseline-cache-model \
    --custom5 0 --debugger --observer --display-sample --held-key 40 \
    --layout tmp/projectile-fix-layout/layout.json \
    --output "tmp/projectile-fix-$cpu-fire" --timeout 180 "${extra[@]}"
  python3 tools/frame_check.py "tmp/projectile-fix-$cpu-fire" \
    --output "tmp/projectile-fix-$cpu-fire/check.json"
  python3 tools/buffer_report.py "tmp/projectile-fix-$cpu-fire" \
    --layout tmp/projectile-fix-layout/layout.json --build tmp/projectile-fix-frames2 \
    --output "tmp/projectile-fix-$cpu-fire/buffers.json"
done
python3 tools/frame_report.py tmp/projectile-fix-030-fire tmp/projectile-fix-040-fire \
  --output tmp/projectile-fix-fps.json
```

These are 030 baseline and cycle-exact 040 model measurements; the latter remains
uncalibrated against hardware. Native prediction assertions establish the fix;
FPS and buffer ownership checks establish the scoped live gate, not subjective
hardware acceptance or every intermediate pixel.


### Intro world timing

Use fresh output names; the capture/report tools reject existing output paths.
The normal build checks native semantics. The diagnostic build supplies measured
end-to-end display cadence; do not time Unicorn instruction execution.

```sh
. ../../common/env.sh
python3 tools/reconstruct.py --variant cd32 --release --output tmp/intro-clock-release-r2
python3 tools/reconstruct.py --variant cd32 --release --frame-stats --output tmp/intro-clock-stats-r2
python3 tools/intro_clock_check.py tmp/intro-clock-release-r2 --output tmp/intro-clock-native-r2.json
python3 tools/timing_adapter_check.py tmp/intro-clock-release-r2 --output tmp/intro-clock-install-r2
python3 tools/release_check.py tmp/intro-clock-release-r2 --negative-controls --output tmp/intro-clock-options-r2.json
python3 tools/projectile_spawn_check.py tmp/intro-clock-release-r2 --output tmp/intro-clock-projectiles-r2.json
python3 tools/timing_scene_check.py tmp/intro-clock-release-r2 --output tmp/intro-clock-flight-r2
export FSUAE="$PWD/tmp/phase7-debugger-v2/fs-uae"
DEBUG_PORT=2499 SLAVE="$PWD/tmp/intro-clock-stats-r2/WingCommanderCD32.Slave" \
WHD_ARGS='CUSTOM5=0' WARP=1 INTRO_STOCK_CLOCK=1 AMIGA_SETUP=a1200-fast \
python3 tools/boot_gate.py --calibrate --output tmp/intro-clock-layout-r2
DEBUG_PORT=2499 python3 tools/intro_clock_capture.py --build tmp/intro-clock-stats-r2 \
  --layout tmp/intro-clock-layout-r2/layout.json --machine a1200-030 \
  --full-cycle --output tmp/intro-clock-030-r2
DEBUG_PORT=2499 python3 tools/intro_clock_capture.py --build tmp/intro-clock-stats-r2 \
  --layout tmp/intro-clock-layout-r2/layout.json --machine a1200-040 \
  --output tmp/intro-clock-040-r2
python3 tools/intro_clock_report.py tmp/intro-clock-030-r2 tmp/intro-clock-040-r2 \
  --output tmp/intro-clock-report-r2.json
for cpu in 030 040; do
  for section in title credits; do
    python3 tools/frame_check.py "tmp/intro-clock-$cpu-r2/$section" \
      --output "tmp/intro-clock-$cpu-r2/$section/check.json"
  done
done
python3 tools/intro_pose_check.py --build tmp/intro-clock-stats-r2 \
  --capture tmp/intro-clock-040-r2 --output tmp/intro-clock-live-poses-r2.json
```

The harness owns its emulator/debugger processes and stops only that run. It
records the unskipped title and first credit page; `--full-cycle` also waits for
all 18 pages and native repetition before skipping to the menu. It uses cached
030 and cycle-exact 040/NoMMU model settings. Raw memory, state streams, observer
ledgers and all build products remain in `tmp/`. The native pose check executes
real drawing at five render fractions on both ISA models, asserting projected
motion and restoration; it excludes C2P/publication. The full-cycle observer's
page-end entries and terminal dumps permit separate exit-state inspection.


## Phase 13: OCS static investigation

This procedure boots no emulator and changes no game tree. Use the shared
Python/tool environment described above. `make unpack` must pass for the archives
and supplies the reference drawers if absent. The OCS
inspector independently checks the pinned archives, a fresh extraction against
the entire reference tree, and the installer's `WingCommanderECS.slave` against
the installed `WingCommander.Slave`. It refuses an existing output directory or
one outside `tmp/`. Choose a fresh suffix for repeated runs.

```sh
. ../../common/env.sh
python3 tools/ocs_static.py --output tmp/phase13-static-repro
python3 -m amigaxdev.disasm dis --cpu 68000 \
  tmp/phase13-static-repro/Wing.english.h0.bin 0 0x3291e 0x329e4
python3 -m amigaxdev.disasm dis --cpu 68000 \
  tmp/phase13-static-repro/Wing.english.h0.bin 0 0x31de2 0x31e3a
python3 -m amigaxdev.disasm dis --cpu 68000 \
  tmp/phase13-static-repro/WingCommander.Slave.h0.bin 0 0x10de 0x11e8
```

Outputs include file fingerprints, hunk allocation/file offsets, the three
revision patch lists, relocation records, extracted hunk bytes and 68000 linear
disassemblies. Follow relocation targets and known entry points: embedded data
can misalign a linear sweep, and the game entry jump targets hunk 3. To inspect
other evidence rows in the internals notes, substitute the corresponding hunk
file and start/end **hunk offsets** into the same disassembler command.
PatchSeg coordinates must be mapped using allocated hunk lengths, not file sizes.
All generated material remains under `tmp/`.

The conversion candidates were inspected from the shared Kalms checkout, not
vendored into this project. Verify the complete candidate set against the
manifest before assembling. `OCS_KALMS_ROOT` can override the shared location;
this does not modify or reset that checkout. Both candidates should assemble
under the base ISA, even though the longword-write version is a candidate for
68020+ selection. This probe is not a correctness or performance benchmark.
Run this block with `/bin/bash`:

```sh
set -e
. ../../common/env.sh
export OCS_KALMS_ROOT="${OCS_KALMS_ROOT:-$AMIGA_SHARE/kalms-c2p}"
python3 - <<'PYVERIFY'
import hashlib
import os
from pathlib import Path
root = Path(os.environ['OCS_KALMS_ROOT'])
for line in Path('tools/manifest/ocs-c2p-candidates.tsv').read_text().splitlines():
    if not line or line.startswith('#'):
        continue
    name, expected, upstream = line.split('\t')
    actual = hashlib.sha256((root / name).read_bytes()).hexdigest()
    if actual != expected:
        raise SystemExit('candidate differs; preserved unchanged: ' + name)
    print('verified ' + name)
PYVERIFY
if test -e tmp/phase13-c2p-repro; then
  echo 'Choose a fresh output directory; nothing overwritten' >&2
  exit 1
fi
mkdir -p tmp/phase13-c2p-repro
for routine in c2p1x1_4_c5_bm_word c2p1x1_4_c5_bm; do
  "$VASM" -m68000 -Fhunk -I"$NDK" \
    -o "tmp/phase13-c2p-repro/$routine.o" \
    "$OCS_KALMS_ROOT/bitmap/$routine.s"
done
```

The investigation passed verified extraction, the English `00e8` CRC and hunk
inventory, installer identity, all three eight-entry revision patch lists, base
ISA assembly of both pinned candidates, and rejection of output reuse/outside
scratch. Repeated inventory/file/patch/relocation reports matched exactly.
No OCS emulator run or backend crossover measurement is part of phase 13.
[P13C2](ocs-plan.md#c--choose-conversion-from-measured-cpu-and-memory-behaviour)
specifies the matched experiment required before choosing blitter versus CPU;
retain the blitter until that gate establishes which configurations benefit.

## P13A1: OCS slave reconstruction

Use the shared environment's Python (Capstone and amigaxdev), `VASM`, `WHDLOAD`
headers and `NDK`. From the project root, with fresh output names:

```sh
make unpack
python3 tools/reconstruct.py --variant ocs --output tmp/p13a1-reconstruct
make check-ocs-reconstruction OUT=tmp/p13a1-check
```

The first target uses the pinned original OCS slave and English game from
`tmp/game/WingCommander`. It validates their SHA-256 identities, the
English CRC, all three native selector/list structures, and the eight displaced
source windows in `tools/manifest/ocs-patch-sites.tsv` before creating build output.
It emits `WingCommanderOCS.s`, `slave.lst`, `payload.bin`, `WingCommander.Slave`
and `report.json` below the chosen `tmp/` directory. Vasm assembles with
`-m68000 -spaces -no-opt -Fbin`; the complete HUNK file must equal the original.
No generated source, patch list bytes or built slave belongs in git.

The check target performs two fresh builds and compares their generated source,
payload, slave and report. It exercises invalid inputs (including changed game
bytes with the original CRC), each protected source window, selector corruption,
an actual assembly sabotage and output-path rejection. `checks.json` records the
result. Rejected fixtures and failed assembly evidence stay under its output;
reference installs are checked for preservation. It also uses the supplied CD32
English file as a wrong-variant negative input. No emulator is started.

For explicit source selection, use the same Python entry point after sourcing
the shared environment (the same strict identities still apply):

```sh
. ../../common/env.sh
python3 tools/ocs_reconstruct.py --output tmp/p13a1-explicit \
  --input tmp/game/WingCommander/WingCommander.Slave \
  --game tmp/game/WingCommander/data/Wing.english
```

These guards operate at build time. The byte-identical slave retains its original
runtime CRC handling; new hooks and runtime guards belong to later implementation.
Boot equivalence is P13A3, not part of this reconstruction gate.

## P13A2: native display contract check

Use the shared Python dependencies and `AMIGA_UNICORN` from `../../common/env.sh`, with
the pinned English OCS input prepared as above. No Kickstart, OS boot or FS-UAE
run is needed. Use a fresh output directory:

```sh
make check-ocs-display OUT=tmp/p13a2-check
```

The target verifies the executable SHA before loading/relocating its four hunks
into an isolated M68000 instruction engine. Original descriptor, callback,
allocator, direct-writer and publication instructions execute against a functional
blitter and explicit OS service stubs. The independent pixel oracle uses scalar
checkerboard high/low-nibble selection and bit packing. This is functional
execution evidence, **not static-only evidence**, a full emulator boot or timing.

`pixels.json` records 15 fixtures / 45 positive conversions and rejecting controls;
`blits.json` retains one 320×200 command ledger and source-relative read extents.
`allocation.json`, `publication.json` and `queue.json` record native ownership
checks and the stubbed services; `report.json` records input identity and limits.
All output stays below `tmp/`. Existing output paths and symlink escapes are
rejected by the same output guard used in P13A1. Original inputs are read only.

A host that restricts native JIT execution must permit Unicorn for this command;
otherwise a host instruction fault is not an OCS game failure. The model accepts
only the ascending area operations used here, completes blits synchronously,
and does not simulate bus contention, beam timing, cache or OS queue scheduling.
Four native-model edge pixels and an unsafe odd-height control are reported
explicitly in the [contract](internals.md#p13a2-native-display-and-allocation-contract).
Their real display behaviour needs P13A3 confirmation. Stop at this gate; no
launcher, timing patch, CPU converter or backend selection is part of P13A2.


## P13A3: OCS launcher and live-layout gate

Select the install independently of the machine: `VARIANT=WingCommander` selects the
OCS drawer and slave; omission retains CD32. Original trees and runtime drives remain
separate. The launcher creates fresh drives every time from `tmp/game/`. A selected
`SLAVE` replaces only the slave in that new runtime copy, with the archive's original
retained alongside it.

```sh
. ../../common/env.sh
python3 tools/reconstruct.py --variant ocs --output tmp/ocs-reconstructed
make run VARIANT=WingCommander SLAVE=original WINDOW=front
make stop
```

An OCS run with an explicit `SLAVE` defaults to the shared A500 preset with the
project baseline override:
68000, OCS, PAL, 512 KiB Chip, 4 MiB Zorro-II Fast, no slow/trapdoor RAM, real
CPU speed and cycle-exact CPU/memory/blitter. Other machine selections remain
explicit experiments. The host boots directory drives with the shared 3.1 ROM;
the unchanged slave uses the shared `kick34005.A500` and its `.RTB` in
`devs/Kickstarts`. Workbench and WHDLoad use the existing
`WORKBENCH_ADF` and `WHDLOAD_BINARY` variables. No ROM/OS downloads are added.

The gate needs the existing project debugger's native `key-raw-v1` capability,
not merely the shared preset. Rebuild that debugger with the existing pinned
`tools/build_debugger.py --ocs-pixels --output tmp/ocs-debugger` recipe if needed. Set `FSUAE`
to that build, or a compatible existing project build. It fails before emulated
boot progress when the native key route is absent.

```sh
export FSUAE="$PWD/tmp/p13a3-debugger/fs-uae"
python3 tools/ocs_boot_gate.py --calibrate --output tmp/ocs-layout
python3 tools/ocs_boot_gate.py --layout tmp/ocs-layout/layout.json \
  --simulator --output tmp/ocs-original
SLAVE="$PWD/tmp/ocs-reconstructed/WingCommander.Slave" \
  python3 tools/ocs_boot_gate.py --layout tmp/ocs-layout/layout.json \
  --simulator --output tmp/ocs-rebuilt
python3 tools/ocs_boot_compare.py tmp/ocs-original tmp/ocs-rebuilt
python3 tools/ocs_runtime_check.py tmp/ocs-original/menu-fast.bin
```

Use fresh output names below `tmp/`. The layout is validated again at every
capture, including A4 against its OCS startup relocation. The locator rejects
preload copies using DOS segment sizes/links, two startup relocations, two
independent slave helper targets and the slave header. The negative check
corrupts each relationship and removes the live code while retaining preload.

The native input route uses Escape to leave Origin and, after the title and
first credits picture, to reach the menu. OCS initializes its pointer over the
unavailable Secret Missions option; native Up moves it into Vega's rectangle
before Return. The selected menu index is asserted. The simulator runs to the
name-input loop without entering a name. No game state or instructions are
written by the route. Each capture saves all four game hunks, Chip/Fast RAM,
registers and a lossless trace screenshot. At name entry it waits for the final
blitter completion/publication, returns to the input poll, then captures two
fields so the displayed prompt is complete. The comparison allows no byte or
pixel differences. These debugger captures prove scoped state/pixel agreement,
not performance or uninterrupted visual acceptance.

Cleanup kills the owned GDB child and calls the shared launcher stop route for
that run directory. Failed runs retain their diagnostic files; no failure is
converted into a successful endpoint. P13A4 measurements are separate.


`--ocs-pixels` initializes the **host** chipset image buffer with `calloc`
instead of `malloc` and exports PNG for multi-field captures as well. It changes
neither guest RAM nor CPU/blitter execution. The old exporter exposed untouched
right-border host bytes and used lossy JPEG for two or more fields. The gate
rejects a non-PNG screenshot; it never crops or masks mismatches.

The shared configured source has since changed its CPU implementation. The
existing manifest correctly rejects it. For this gate, a fresh staging copy uses
the preserved CPU source with the exact existing manifest hash; other pinned
files already match. To reproduce that preparation without overwriting shared
inputs (requires the retained configured build and frozen CPU source):

```sh
. ../../common/env.sh
export OCS_SHARED_BUILD="${FSUAE_SOURCE:-$AMIGA_SHARE/fs-uae-aprof-build/fs-uae}"
export OCS_FROZEN_CPU="${OCS_FROZEN_CPU:-$PWD/tmp/debugger/src/newcpu.cpp}"
python3 - <<'PYOCS'
import hashlib, os, shutil
from pathlib import Path
source = Path(os.environ['OCS_SHARED_BUILD'])
frozen = Path(os.environ['OCS_FROZEN_CPU'])
expected = dict(line.split('\t') for line in
    Path('tools/manifest/debugger.tsv').read_text().splitlines()
    if line and not line.startswith('#'))['src/newcpu.cpp']
assert hashlib.sha256(frozen.read_bytes()).hexdigest() == expected
out = Path('tmp/ocs-debugger-source')
shutil.copytree(source, out)  # fails if destination exists
(out/'.replaced').mkdir(exist_ok=True)
(out/'src/newcpu.cpp').rename(out/'.replaced/newcpu.cpp')
shutil.copyfile(frozen, out/'src/newcpu.cpp')
PYOCS
FSUAE_SOURCE="$PWD/tmp/ocs-debugger-source" \
  python3 tools/build_debugger.py --ocs-pixels --output tmp/ocs-debugger
export FSUAE="$PWD/tmp/ocs-debugger/fs-uae"
```

The builder then verifies every manifest entry and the source commit before
copying or compiling. This reuses configured host dependencies/objects, as the
existing debugger recipe does; it is not a self-contained toolchain release.
The tested retained build is `tmp/p13a3-debugger/fs-uae`.

## P13A4: short native OCS baseline

Use the P13A3 pinned source staging procedure above; retain its frozen input and
choose new output directories. Build the read-only **68000** observer locally:

```sh
. ../../common/env.sh
FSUAE_SOURCE="$PWD/tmp/ocs-debugger-source" \
  python3 tools/build_debugger.py --ocs-pixels --ocs-observer \
  --output tmp/ocs-baseline-debugger
export FSUAE="$PWD/tmp/ocs-baseline-debugger/fs-uae"
python3 tools/ocs_boot_gate.py --calibrate --baseline on --output tmp/ocs-baseline-layout
python3 tools/ocs_boot_gate.py --layout tmp/ocs-baseline-layout/layout.json \
  --baseline on --output tmp/ocs-baseline-on
python3 tools/ocs_boot_gate.py --layout tmp/ocs-baseline-layout/layout.json \
  --baseline off --output tmp/ocs-baseline-off
python3 tools/ocs_baseline_report.py tmp/ocs-baseline-on tmp/ocs-baseline-off \
  > tmp/ocs-baseline-report.json
```

The baseline option adds two **250-field** windows to the A3 route: immediately
after its first-credit capture, and immediately after its first simulator capture
with native Space held. Space is released after the flight capture. The run then
reaches the name prompt and cleans up its owned emulator. No guest data, RNG,
instructions or timing logic are patched. No turn or machine matrix is included.

`OCS_STOCK_CLOCK=1` is set by the baseline harness. It replaces the preset's numeric
frequency/multiplier with zero, selecting the pinned core's native PAL 68000 clock.
This is necessary: the old numeric-frequency expression overflows to a cycle unit
of **231**; stock 68000 requires **256** internal units per CPU clock. Ordinary A3
runs retain their existing configuration; their state/pixel evidence was not a
performance measurement. A baseline report rejects the wrong unit. The field
clock is independent: 512 units per colour clock, 227 × 313 colour clocks per
observed field, 49.920409 Hz. Times use that clock, never host wall time.

The debugger's `ocs-window` command aligns to the next field, runs uninterrupted
for the requested count, freezes all records at the last field edge, then replies.
There are **no breakpoints, profiles, screenshots or input changes inside either
measurement window**. The surrounding A3 screenshots are outside the windows.
Observer-off disables PC scopes, instruction charges, source comparisons and DMA
observations; identical field-boundary bookkeeping/counter reads remain enabled.
All eight checkpoint hunk/Chip snapshots and full PNG pixels must match exactly.

Each window produces `*-events.txt` below its run output: B/F/E are clock edges,
P native PC landmarks, S/R entry/stack-validated return scopes, D actual plane-0
DMA buffer observations, C source byte/block comparisons, and M native free-memory
samples. Raw game-derived captures stay in `tmp/`. The report rejects missing
landmarks, incomplete fields, publication/display disagreement, malformed scopes,
wrong clocks, missing instruction accounting and corrupt state/pixels. Its built-in
negative controls deliberately break those checks. It also checks the pinned slave,
effective machine, matching actions and run fingerprints.

Only complete scope/conversion pairs contribute durations. DMA changes count new
buffers; merely rewriting the same pointer is not another picture. Publication
and display counts are reconciled with explicitly bounded pending edge work.
Conversion stage spans include native callback/interrupt dispatch and contention;
they are not isolated DMA-engine throughput. The inter-stage residual and explicit
field wait are reported separately. Drawing, world and asynchronous conversion
can overlap; do not add their inclusive durations.

Memory high-water values are samples at every field plus native allocation-return/free-entry
landmarks. The report separates the KickEmu memory-pool capacity/usage from memory
outside those pools. Physical capacity minus native free bytes includes reservations
and preload; it is not all game allocations, a complete boot allocation census, or
proof of minimum RAM. Those later acceptance gates remain separate.

## P13B1: compile-time variants and byte-preserving sharing

The generic builder now requires `--variant cd32|ocs`; the generic Make targets
require `VARIANT=cd32|ocs`. OCS currently supports only native reconstruction:
`--release`, `--timing` and renderer options reject before creating output.
Explicitly named OCS tools remain available. Existing CD32 capture/check tools
remain CD32-specific; selecting a map does not port their observers or native ABI.

```sh
. ../../common/env.sh
python3 tools/reconstruct.py --variant cd32 --release --output tmp/b1-release
python3 tools/reconstruct.py --variant ocs --output tmp/b1-ocs
python3 tools/analyze.py --variant cd32 definitions
python3 tools/analyze.py --variant ocs definitions
python3 tools/analyze.py --variant cd32 static --output tmp/b1-cd32-static
python3 tools/analyze.py --variant ocs static --output tmp/b1-ocs-static
python3 tools/analyze.py --variant ocs layout tmp/p13a4-stock-on/credits-fast.bin
```

For the before/after gate, preserve artifacts from the parent revision before
editing generators. To recreate that independent reference later, stage the
tracked parent tree below `tmp/`, link the already verified original inputs, and
build there. This does not change the working checkout or install trees. Run in
Bash with fresh directory names (the initial `mkdir` must fail if reused):

```sh
set -e
. ../../common/env.sh
mkdir tmp/b1-parent
git archive 817c787:games/WingCommander | tar -x -C tmp/b1-parent
mkdir -p tmp/b1-parent/tmp/originals/cd32 tmp/b1-parent/tmp/originals/ocs
ln -s ../../../../game/WingCommanderCD32 tmp/b1-parent/tmp/originals/cd32/WingCommanderCD32
ln -s ../../../../game/WingCommander tmp/b1-parent/tmp/originals/ocs/WingCommander
(
  cd tmp/b1-parent
  for mode in release timing render native; do
    args=()
    if [ "$mode" != native ]; then args=("--$mode"); fi
    python3 tools/reconstruct.py "${args[@]}" --output "tmp/before-$mode"
  done
)
for mode in release timing render native; do
  args=()
  if [ "$mode" != native ]; then args=("--$mode"); fi
  python3 tools/reconstruct.py --variant cd32 "${args[@]}" --output "tmp/b1-after-$mode"
done
python3 tools/reconstruct.py --variant ocs --output tmp/b1-after-ocs
python3 tools/variant_check.py --before-prefix tmp/b1-parent/tmp/before \
  --after-prefix tmp/b1-after \
  --cd32-memory tmp/phase7-combat-controls/start-fast.bin \
  --ocs-memory tmp/p13a4-stock-on/credits-fast.bin --output tmp/b1-variants
python3 tools/ocs_reconstruct_check.py --output tmp/b1-ocs-reconstruction
python3 tools/timing_adapter_check.py tmp/b1-after-release --output tmp/b1-install
python3 tools/intro_clock_check.py tmp/b1-after-release --output tmp/b1-intro.json
python3 tools/flight_render_check.py tmp/b1-after-release --output tmp/b1-pixels.json
```

The layout checks use retained native memory captures from the phase-7 controls
and P13A4, with each locator's own identity and relocation checks. Recreate those
captures using their documented gates if absent; no new emulator run is needed
when retained captures exist. `variant_check.py` also assembles each map's equates
on its declared ISA, checks hunk metadata against the native files, rejects
malformed and cross-variant segment chains, and rebuilds with a deliberately
wrong clock-field definition to prove that the byte-identity gate detects it.
The accepted results are in `tmp/p13b1-accepted-variants/report.json`,
`tmp/p13b1-ocs-reconstruction/checks.json`, `tmp/p13b1-timing-install/report.json`,
`tmp/p13b1-intro.json` and `tmp/p13b1-pixels.json`. Static front-door outputs are
`tmp/p13b1-ocs-static` and `tmp/p13b1-cd32-static-final`. No timing/backend selection
or performance measurement is part of this refactor.


## P13B2: shared base-ISA and execution gate

This gate uses the existing shared vasm and Unicorn tools; it does not boot a game.
All generated assembly, listings, fixtures and reports stay in a fresh `tmp/`
directory. The 68000 selector is an ISA layer; requesting an enhanced OCS slave
still rejects until its native hooks/ABIs are implemented in later work.

```sh
. ../../common/env.sh
python3 tools/shared_cpu_check.py --output tmp/b2-cpu
for mode in release timing render native; do
  args=()
  if [ "$mode" != native ]; then args=("--$mode"); fi
  python3 tools/reconstruct.py --variant cd32 "${args[@]}" --output "tmp/b2-after-$mode"
done
python3 tools/reconstruct.py --variant ocs --output tmp/b2-after-ocs
python3 tools/variant_check.py --before-prefix tmp/p13b1-final \
  --after-prefix tmp/b2-after \
  --cd32-memory tmp/phase7-combat-controls/start-fast.bin \
  --ocs-memory tmp/p13a4-stock-on/credits-fast.bin --output tmp/b2-variants
python3 tools/timing_adapter_check.py tmp/b2-after-release --output tmp/b2-install
python3 tools/intro_clock_check.py tmp/b2-after-release --output tmp/b2-intro.json
```

If the retained P13B1 reference is absent, build the four modes from `0710118`
using the isolated `git archive` recipe in the B1 section (with that commit and
fresh directory names), and pass that reference prefix to `variant_check.py`.
The locator inputs can likewise be regenerated using their original documented
routes. Never substitute a mutated/game-derived fixture into a source directory.

`shared_cpu_check.py` assembles all 13 audited units under four conditional
profiles with explicit fixture-only external placeholders. It then executes
actual scheduler/scaling/translation routines, flag/address/call contracts and
publication/recorder wrappers on CPU models. The report lists the placeholder
boundaries; they are not an OCS linker implementation. The 68000 flag routine is
also tested in user mode on later CPUs. Original accelerated instructions supply
an independent operand/flag differential, while Python integer and elapsed-time
ledgers supply the arithmetic/clock oracle. Deliberate ISA, flag and arithmetic
failures prove those checks reject. No guest time or performance is measured.

For later OCS integration, `shared_cpu.unit(root, name, '68000')` emits an audited
unit and `shared_cpu.preamble(root, '68000')` supplies its macros once per image.
Use the variant's own verified definitions and actual callbacks, then assemble
the **entire linked image** with `-m68000 -no-opt`; per-unit fixtures do not prove
final branch reach or the native ABI. The 020+ selector preserves source verbatim.
Arithmetic helpers have bounded positive-factor/rate contracts and scratch CCR;
do not use this selector as a general game-code translator.

Accepted evidence: `tmp/p13b2-accepted/report.json`,
`tmp/p13b2-variants/report.json`, `tmp/p13b2-install/report.json` and
`tmp/p13b2-intro.json`; matching binaries are in `tmp/p13b2-final-*`.
See [contracts and limits](internals.md#p13b2-shared-68000-execution-safety).

## P13B3: shared instrumentation and validation gate

Use an explicit variant. The OCS path reuses the calibrated P13A4 observer and
matched on/off controls, not CD32's IRQ deadline or display assumptions. If the
retained inputs are absent, recreate them with the P13A4 commands above. No new
live capture is required when the observer, game and retained inputs are unchanged.
Every output directory must be new and below `tmp/`.

```sh
. ../../common/env.sh
python3 tools/instrumentation_check.py --variant ocs \
  --run tmp/p13a4-stock-on --control tmp/p13a4-stock-off \
  --output tmp/b3-ocs
python3 tools/instrumentation_unit_check.py --output tmp/b3-cpu \
  --replay tmp/b3-ocs --capture tmp/p13a4-stock-on
python3 tools/instrumentation_check.py --variant cd32 \
  --run tmp/d3-final-040-turn-cost --output tmp/b3-cd32
python3 tools/reconstruct.py --variant cd32 --release --output tmp/b3-release
python3 tools/reconstruct.py --variant ocs --output tmp/b3-native
cmp tmp/b3-release/WingCommanderCD32.Slave tmp/p13b2-final-release/WingCommanderCD32.Slave
cmp tmp/b3-native/WingCommander.Slave tmp/p13b2-final-ocs/WingCommander.Slave
```

The named CD32 input is the retained D3 held-turn capture; another accepted
`--frame-stats`/observer pair can be supplied instead. Its original capture
procedure is documented under D3. B2 build reproduction is above if comparison
binaries are absent. Do not substitute a different capture for the OCS control:
machine, slave, emulator, actions, clocks and every checkpoint must match.

The OCS report separates completed world ticks, draw entries, rendered sources,
Copper publications and actually displayed buffer changes. Exports
`asteroids-framestats.bin`, `fire-framestats.bin` and their `*-displaystats.bin`
companions share WCFS/WCDS with CD32, but their report records **host-observer**
provenance and independent field-edge timestamps. They are not game-generated
recorder output. `frame_schema.py` reads either format; `frame_report.py` remains
the CD32 policy/cost summariser. The common wire reader imposes no CD32 beam deadline.

`recorder_source.source('ocs', capacity=2048)` generates the callable owned
recorder and state. The CPU gate writes the source, base-ISA binary and symbols
under its output; `ocs-replay.*` uses the default capacity. The small lifecycle
fixtures use capacity eight to exercise saturation. Assembly uses `-m68000
-spaces -no-opt -Fbin`; the generated source includes B2's flag/addressing macros.
Begin ABI: A0 = validated Fast buffer of `16+4*capacity` bytes, A1 = OCS data hunk,
D0 = nominal 50/60 Hz. `frame_stat` takes event.w after the return address, as in
the shared FSTAT call convention. `recorder_end` freezes and writes the completed
header; export exactly `16+4*frame_stats_count` bytes. Check
`frame_stats_dropped == 0` and `frame_stats_count < capacity` before accepting a
window. `frame_stats_first` retains the native field epoch. The first sample only
arms the epoch. All calls preserve registers and CCR; valid setup/lifetime and
main-task serialisation remain the caller's responsibility.

This component does not allocate memory, install hooks, save files, or support
reentrant IRQ callers. Use a separate publication observer/ledger. The test's
native-data replay supplies field/beam samples synthetically and labels the result
as CPU semantics, not live guest instrumentation or elapsed-time performance.
The four-attempt limit and executed instruction counts bound the recorder loop;
measure guest overhead when later OCS components actually install it.


## P13C1: experimental OCS converter gate

Use the shared environment, the pinned Kalms checkout and the supplied English
OCS executable prepared above. `OCS_KALMS_ROOT` overrides the default
`$AMIGA_SHARE/kalms-c2p`. Both manifest hashes are verified before sources are used;
changed inputs are preserved and rejected. No download or checkout reset occurs.
Every output must be a fresh directory below `tmp/`.

```sh
. ../../common/env.sh
python3 tools/ocs_c2p.py --output tmp/c1-components
python3 tools/ocs_c2p_check.py --output tmp/c1-check
python3 tools/reconstruct.py --variant cd32 --release --output tmp/c1-release
python3 tools/reconstruct.py --variant ocs --output tmp/c1-native
cmp tmp/c1-release/WingCommanderCD32.Slave tmp/p13b3-release/WingCommanderCD32.Slave
cmp tmp/c1-native/WingCommander.Slave tmp/p13b3-native/WingCommander.Slave
```

The checker also builds its own converters. `build.json` records source hashes,
binary hash/size and entry offsets; `converters.bin`, `converters.s` and its listing
are standalone component artifacts, **not WHDLoad slaves**. `report.json` records
the native/oracle/CPU pixel, memory-access, ABI, fallback and rejection checks.
Deliberate mutations are assembled only into that scratch directory. Missing B3
comparison builds can be recreated with the commands in the previous section.
The accepted run is `tmp/p13c1-accepted`, with unchanged standard builds under
`tmp/p13c1-release` and `tmp/p13c1-native`.

Both CPU entries take A0=source, A1=destination, D0.L=width and D1.L=height.
Native layout is dense width-byte source rows, width/8 planar rows, four contiguous
planes of `(height+2)*width/8` bytes. They write only visible rows after two leading
rows. D0 returns 0=complete, 1=native request, 2=invalid; all other general registers
are preserved, CCR is clobbered. The native-request entry returns 1 immediately.
See [contract and ownership preconditions](internals.md#p13c1-experimental-four-plane-converters)
before using these components. A return of 1 must dispatch the native queue and
its completion protocol; a return of 2 must not publish an unconverted image or
blindly invoke the unsafe native geometry.

The wrapper includes shared checkerboard selection in a private 320-byte staging
row and preserves the native four edge pixels. Include its full cost and 512-byte
minimum stack reservation in later experiments, with additional interrupt stack
headroom. No full-screen staging allocation is required. These checks execute
functional CPU/blitter models and provide no bus-contention, queue-latency or
performance measurement. Native slave defaults and the CD32 release are untouched.
Stop before P13C2's matched crossover experiment.

## P13C2: measured converter comparison

This builds a **diagnostic-only** slave reservation and installs experimental
hooks into a stopped guest for one bounded window. It never changes normal builds
or game trees. Keep every generated file below `tmp/`. Use the canonical shared
`WHDLoad` directory through `../../common/env.sh`; there is no version-suffixed path.
The C1 Kalms pins and A3 debugger-source pins remain required.

```sh
. ../../common/env.sh
FSUAE_SOURCE="$PWD/tmp/p13a3-source" \
  python3 tools/build_debugger.py --ocs-pixels --ocs-observer \
  --output tmp/c2-meter
export FSUAE="$PWD/tmp/c2-meter/fs-uae" WARP=1
python3 tools/ocs_crossover_run.py --calibrate --output tmp/c2-fast-layout
python3 tools/ocs_crossover_run.py --calibrate --memory slow --output tmp/c2-slow-layout
```

`tmp/p13a3-source` is the pinned, configured source staging described under A3;
reproduce it there if absent. The builder copies it locally. The observer covers
the actual cycle-exact 68000/020 dispatch, native conversion/publication PCs,
bitplane fetches and occupied-slot CPU waits in `dma_cycle`. Its optional
`ocs-load` monitor command loads bounded files into RAM **only while stopped**;
C2 uses it before measurement and verifies the installed path afterwards. Ordinary
GDB memory writes are unsupported by this debugger and must not be used instead.

Run the ten asteroid cells sequentially under Bash 3.2:

```bash
for cpu in 68000 68020; do
    candidate=word
    [ "$cpu" = 68000 ] || candidate=long
    for memory in fast slow; do
        layout=tmp/c2-fast-layout/layout.json
        [ "$memory" = fast ] || layout=tmp/c2-slow-layout/layout.json
        arms="native chip-$candidate"
        [ "$memory" = slow ] || arms="$arms fast-$candidate"
        for arm in $arms; do
            python3 tools/ocs_crossover_run.py --cpu "$cpu" --memory "$memory" \
                --layout "$layout" --arm "$arm" \
                --output "tmp/c2-$cpu-$memory-$arm"
        done
    done
done
```

Both CPU models used the same discovered layout within each memory configuration
in the accepted runs; the runner verifies it against live hunks/A4. If a changed
input changes layout, calibrate that configuration separately and use its file.
`fast` configures 4 MiB Zorro-II Fast and no slow memory; `slow` configures 1.75 MiB
slow expansion and zero true Fast. Both retain 512 KiB Chip/OCS. The audit must
report CPU unit 256/128 and native PAL defaults, never an overflowing numeric
frequency. Warp affects only host duration, not the emulated-time denominator.

The focused flight/fire confirmation keeps native controls and compares the
required baseline and accelerated Fast profile:

```bash
for cpu in 68000 68020; do
    arms='native fast-word'
    [ "$cpu" = 68000 ] || arms='native chip-long fast-long'
    for arm in $arms; do
        python3 tools/ocs_crossover_run.py --cpu "$cpu" \
            --layout tmp/c2-fast-layout/layout.json --scene fire --arm "$arm" \
            --output "tmp/c2-flight-$cpu-$arm"
    done
done
```

All writes finish before `ocs-window` aligns to a field edge. There are no interior
breakpoints, input changes or profiles. The installer retires QBlit first, retains
its allocations, validates the active source/view and rebases the flight
compositor's shadow rows and copy-command pointers for Fast arms. The run stops
at its 250-field cap and cleans up only its own emulator. This bounded rebase is
not production allocation, view-transition or cleanup code.

Analyze individual windows and matched groups separately. The first emits full
field-window counters/costs; the second verifies equal initial hunks/Chip RAM and
compares byte-exact source images, completed conversions and actual displayed
pictures. Do not substitute different progressed workloads for matched pictures.
For example:

```sh
python3 tools/ocs_crossover_report.py \
  tmp/c2-68020-fast-native tmp/c2-68020-fast-chip-long tmp/c2-68020-fast-fast-long \
  --output tmp/c2-020-windows.json
python3 tools/ocs_crossover_report.py --matched \
  tmp/c2-68020-fast-native tmp/c2-68020-fast-chip-long tmp/c2-68020-fast-fast-long \
  --output tmp/c2-020-matched.json
python3 tools/ocs_crossover_report.py --matched \
  tmp/c2-flight-68020-native tmp/c2-flight-68020-chip-long tmp/c2-flight-68020-fast-long \
  --output tmp/c2-020-flight-matched.json
```

Repeat these reports for the other groups, always putting native first. Source
streams are `*-events.txt.sources`, packed as W×H bytes per `H` record; `X` records
contain independent visible-pixel comparisons, `T` occupied-slot wait counts.
A source mismatch ends the eligible prefix; fewer than four completed matching
pictures fails. A pending publication is permitted only in the last field, when
its next Copper latch can lie beyond the cap. Interior publication loss fails.
The report checks actual selected backend, memory placement, clock, source coverage,
code/source guards and absence of stale writes to the retired Chip source.

Run observer-off controls with the same options, adding `--baseline off` and a new
output directory. Accepted controls cover native 000 asteroids and CPU/Fast flight
on both CPUs. For example:

```sh
python3 tools/ocs_crossover_run.py --cpu 68020 --layout tmp/c2-fast-layout/layout.json \
  --scene fire --arm fast-long --baseline off --output tmp/c2-020-off
python3 tools/ocs_crossover_check.py tmp/c2-flight-68020-fast-long tmp/c2-020-off \
  --output tmp/c2-020-control.json
```

The checker compares native game hunks, complete Chip RAM, Fast source, field
clocks/counters and machine/build fingerprints. It also deliberately corrupts
eight report inputs and requires rejection. The retained incomplete source-move
runs `tmp/p13c2-flight-68020-fast-long` and `tmp/p13c2-flight-fixed-68020-fast-long`
are **not accepted measurements**: current reporting rejects their stale source
writers, and source matching rejects their compositor mismatch. Accepted Fast
flight runs are `tmp/p13c2-flight-owned-*`.

Finally rebuild both normal slaves and compare with the C1 outputs:

```sh
python3 tools/reconstruct.py --variant ocs --output tmp/c2-native-control
python3 tools/reconstruct.py --variant cd32 --release --output tmp/c2-release-control
cmp tmp/c2-native-control/WingCommander.Slave tmp/p13c1-native/WingCommander.Slave
cmp tmp/c2-release-control/WingCommanderCD32.Slave tmp/p13c1-release/WingCommanderCD32.Slave
```

See [the decision, measurements and limits](internals.md#p13c2-measured-ocs-converter-crossover).
Stop before C3 selection and C4 production memory ownership. Do not distribute
the diagnostic reservation/slave or resume paused CD32 release work.


## P13C3: selection and fallback

These commands exercise the selector in the bounded C2 fixture, not an installed
release. Use a fresh output name on repeats. All generated code, game bytes,
dumps and screenshots remain in `tmp/`. Shared WHDLoad comes from `$WHDLOAD`
(the stable `~/.local/share/amiga/WHDLoad` directory).

```sh
. ../../common/env.sh
python3 tools/ocs_backend_check.py --output tmp/c3-unit
# Use the C2 instrument build procedure above if the instrument is absent.
export FSUAE="$PWD/tmp/p13c2-debugger-measured/fs-uae" WARP=1
python3 tools/ocs_crossover_run.py --calibrate --output tmp/c3-layout
python3 tools/ocs_crossover_run.py --calibrate --memory slow --output tmp/c3-slow-layout
python3 tools/ocs_crossover_run.py --backend auto --cpu 68020 --scene fire \
  --layout tmp/c3-layout/layout.json --output tmp/c3-auto020
python3 tools/ocs_crossover_run.py --backend cpu --cpu 68020 --scene fire \
  --profile unknown --layout tmp/c3-layout/layout.json --output tmp/c3-forced020
python3 tools/ocs_crossover_run.py --backend auto --cpu 68000 \
  --layout tmp/c3-layout/layout.json --output tmp/c3-auto000
python3 tools/ocs_crossover_run.py --backend cpu --cpu 68000 \
  --layout tmp/c3-layout/layout.json --output tmp/c3-forced000
python3 tools/ocs_crossover_run.py --backend cpu --cpu 68020 --unavailable \
  --layout tmp/c3-layout/layout.json --output tmp/c3-unavailable020
python3 tools/ocs_crossover_run.py --backend auto --cpu 68020 --profile unknown \
  --layout tmp/c3-layout/layout.json --output tmp/c3-unknown020
python3 tools/ocs_crossover_run.py --backend cpu --cpu 68020 --memory slow \
  --layout tmp/c3-slow-layout/layout.json --output tmp/c3-slow020
python3 tools/ocs_backend_gate.py --auto tmp/c3-auto020 --forced tmp/c3-forced020 \
  --runs tmp/c3-auto000 tmp/c3-forced000 tmp/c3-unavailable020 \
  tmp/c3-unknown020 tmp/c3-slow020 --output tmp/c3-live-gate
python3 tools/reconstruct.py --variant ocs --output tmp/c3-native
python3 tools/reconstruct.py --variant cd32 --release --output tmp/c3-release
```

`--backend auto|native|cpu` selects once using the guest 68000-safe initializer.
It is mutually exclusive with C2's direct `--arm` experiments. `--backend native`
always retains the native queue; `cpu` uses word writes on 000/010 and longword
writes on 020+ only if the required storage is ready. This is a harness override,
not a new public WHDLoad CUSTOM option. Existing cheat/language/mission options
are untouched. `--profile measured` is the fixed harness profile (default);
`unknown` removes that certificate, so auto retains native. `--unavailable`
models missing required storage before changing any source owner. Real allocator
failure/rollback and transition handling remain C4.

The acceptance tool requires the automatic/forced source streams and complete
starting/ending game/Chip state to match, validates every run through the strict
C2 pixel/display report, and rejects a copied uninitialized-selector result.
The unit gate checks register/stack preservation, exact decision boundaries,
once-only flush/commit and deliberate implementation mutations. These tests do
not establish performance on unknown accelerators or compatibility across scenes.

## P13C4: allocation-integrated OCS candidate

The original reconstruction remains the native control. Build the separate C4
candidate and validate its owned allocation code as follows; use new output
names on repeats. No game or slave output belongs outside ignored `tmp/`.

```sh
. ../../common/env.sh
python3 tools/ocs_memory_build.py --backend auto --output tmp/c4-auto
python3 tools/ocs_memory_build.py --backend cpu --output tmp/c4-cpu
python3 tools/ocs_memory_check.py --output tmp/c4-memory-check
python3 tools/ocs_memory_install_check.py tmp/c4-cpu --output tmp/c4-install-check

export FSUAE="$PWD/tmp/p13c2-debugger-measured/fs-uae" WARP=1
export SLAVE="$PWD/tmp/c4-cpu/WingCommander.Slave"
python3 tools/ocs_boot_gate.py --ownership --calibrate --output tmp/c4-layout
python3 tools/ocs_boot_gate.py --ownership --cpu 68020 --baseline on --simulator \
  --layout tmp/c4-layout/layout.json --output tmp/c4-live020
python3 tools/ocs_boot_gate.py --ownership --baseline on --simulator \
  --layout tmp/c4-layout/layout.json --output tmp/c4-forced000
export SLAVE="$PWD/tmp/c4-auto/WingCommander.Slave"
python3 tools/ocs_boot_gate.py --ownership --baseline on --simulator \
  --layout tmp/c4-layout/layout.json --output tmp/c4-live000
python3 tools/ocs_memory_report.py tmp/c4-live020 --build tmp/c4-cpu \
  --output tmp/c4-report020
python3 tools/ocs_memory_report.py tmp/c4-forced000 --build tmp/c4-cpu \
  --output tmp/c4-reportword
python3 tools/ocs_memory_report.py tmp/c4-live000 --build tmp/c4-auto \
  --output tmp/c4-report000
```

`auto` and `native` retain native conversion without a measured runtime profile
certificate. `cpu` is the explicit override, selecting word writes on 000/010
and longword writes on 020+. A missing Fast allocation, an unaudited bank or an
unverified main-source geometry retains the original Chip/native path. A failed
mandatory source/row/display allocation unwinds and exits with a clear message.
The original language/cheat/system/mission options and cache policy are unchanged.
The 68000 CPU override is a correctness test, not a speed recommendation.

For a controlled display-subsystem exit, build a diagnostic candidate with an
additional name-input wrapper. It calls the original input routine until the
host sets its owned trigger. It then executes the native source/view/display
teardown and stops. This is not an interactive whole-game quit test.

```sh
python3 tools/ocs_memory_build.py --backend cpu --exit-probe --output tmp/c4-exitcpu
python3 tools/ocs_memory_build.py --backend auto --exit-probe --output tmp/c4-exitauto
python3 tools/ocs_memory_install_check.py tmp/c4-exitcpu --output tmp/c4-exit-install
export SLAVE="$PWD/tmp/c4-exitcpu/WingCommander.Slave"
python3 tools/ocs_boot_gate.py --ownership --calibrate --output tmp/c4-exit-layout
python3 tools/ocs_boot_gate.py --ownership --cpu 68020 --baseline on --simulator \
  --teardown-build tmp/c4-exitcpu --layout tmp/c4-exit-layout/layout.json \
  --output tmp/c4-exit020
export SLAVE="$PWD/tmp/c4-exitauto/WingCommander.Slave"
python3 tools/ocs_boot_gate.py --ownership --baseline on --simulator \
  --teardown-build tmp/c4-exitauto --layout tmp/c4-exit-layout/layout.json \
  --output tmp/c4-exit000
python3 tools/ocs_memory_report.py tmp/c4-exit020 --build tmp/c4-exitcpu \
  --output tmp/c4-exit-report020
python3 tools/ocs_memory_report.py tmp/c4-exit000 --build tmp/c4-exitauto \
  --output tmp/c4-exit-report000
python3 tools/ocs_memory_report_check.py tmp/c4-exit020 --build tmp/c4-exitcpu \
  --output tmp/c4-reject-report
```

The pinned debugger does not support register writes. The gate uses its bounded
RAM loader to set a data trigger, with readback, rather than trying to call guest
functions through register changes or replacing cached instructions. All probe
code is installed and flushed at startup. The native input path is preserved
until the trigger. The DMA check excludes the profiler's initial partial field,
requires a positive old-buffer read control before teardown, then checks complete
fields after teardown for stale reads. The native path can reuse its former
source for the restored OS Copper list: the checker verifies that new View,
Copper-list and allocation ownership before accepting those Copper reads.

For the memory boundary, repeat calibration and the native-backend simulator run
with `--ownership --fast-kib 2048`, then `1024`, using separate layouts for each.
The smaller configurations do not pass the current gate: 1 MiB fails the WHDLoad
expansion reservation, while 2 MiB stalls in a native QBlit wait. Reproduce the
2 MiB control using `SLAVE="$PWD/tmp/game/WingCommander/WingCommander.Slave"`
and a fresh calibration. The original stalls too. These failures do not prove
an absolute hardware minimum; 512 KiB Chip plus 4 MiB Fast is the smallest tested
passing configuration with this launcher. Ownership waits have a bounded timeout,
which interrupts only their own debugger to preserve failure diagnostics.

The reports show sampled pool/registry memory, not boot-wide peaks. No new FPS
claim follows from the ownership runs. Use normal reconstruction commands for
unchanged OCS and CD32 controls; C5's general publication/transition acceptance
and later compatibility work remain separate.

## P13C5: OCS publication ownership

The allocation candidate builder now includes C5 publication by default. Original
OCS reconstruction and the CD32 release remain separate controls. Use fresh output
names; all derived artifacts stay under `tmp/`.

```sh
. ../../common/env.sh
python3 tools/ocs_memory_build.py --backend auto --output tmp/c5-normal
python3 tools/ocs_publication_check.py --output tmp/c5-unit
python3 tools/ocs_memory_install_check.py tmp/c5-normal --output tmp/c5-install
python3 tools/ocs_memory_build.py --backend auto --exit-probe --output tmp/c5-native
python3 tools/ocs_memory_build.py --backend cpu --exit-probe --output tmp/c5-cpu
python3 tools/ocs_memory_install_check.py tmp/c5-cpu --output tmp/c5-probe-install
python3 tools/ocs_publication_debugger.py --output tmp/c5-debugger
```

The debugger extension uses the retained C2 local build tree by default (override
with `--source`). It verifies `tools/manifest/ocs-publication-debugger.tsv`, copies the
tree and replaces only the read-only observer plus its optimized DMA span hook.
It never edits the shared emulator. Reconstructing the C2 input uses the earlier
[C2 instrument workflow](#p13c2-measured-converter-comparison); its pinned local tree is
required because the shared build may have changed since that measurement.

```sh
export FSUAE="$PWD/tmp/c5-debugger/fs-uae" WARP=1
export SLAVE="$PWD/tmp/c5-native/WingCommander.Slave"
python3 tools/ocs_boot_gate.py --ownership --calibrate --output tmp/c5-layout
python3 tools/ocs_boot_gate.py --ownership --views --view-fields 100 \
  --baseline on --simulator --teardown-build tmp/c5-native \
  --layout tmp/c5-layout/layout.json --output tmp/c5-native-live
python3 tools/ocs_boot_gate.py --ownership --views --view-fields 100 \
  --baseline off --simulator --teardown-build tmp/c5-native \
  --layout tmp/c5-layout/layout.json --output tmp/c5-native-off
export SLAVE="$PWD/tmp/c5-cpu/WingCommander.Slave"
python3 tools/ocs_boot_gate.py --ownership --cpu 68020 --views --view-fields 40 \
  --baseline on --simulator --teardown-build tmp/c5-cpu \
  --layout tmp/c5-layout/layout.json --output tmp/c5-cpu-live
python3 tools/ocs_publication_report.py tmp/c5-native-live --build tmp/c5-native \
  --observer-off tmp/c5-native-off --output tmp/c5-native-report
python3 tools/ocs_publication_report.py tmp/c5-cpu-live --build tmp/c5-cpu \
  --output tmp/c5-cpu-report
python3 tools/reconstruct.py --variant ocs --output tmp/c5-original-control
python3 tools/reconstruct.py --variant cd32 --release --output tmp/c5-cd32-control
```

`--exit-probe` now also provides the diagnostic view-request entry used by
`--views`. The simulator suppresses the normal view keys; the probe invokes the
native view change from its normal task/input boundary, then resumes untouched
input handling. The driver verifies the resulting mode before observing it.
This is not interactive campaign-control acceptance. Shorter CPU windows keep
all four requests ahead of scripted death; the native final window can include
its death-camera transition. Name entry waits on the recurring input loop.

The report combines C4 memory/teardown checks with queued/forecast/display
reconciliation, actual Copper-restart bounds, captured copinit/game-list shape
and independent source-to-DMA pixel checks. It explicitly counts unverified
padding/final-row/initial/direct-writer words and rejects corrupted evidence.
The CPU unit gate substitutes beam reads and graphics metadata, while executing
the native VBL and completion instructions; live gates supply actual beam/DMA
evidence. Neither warp/debugger timing nor these correctness windows is an FPS
performance comparison. See the [accepted scope](internals.md#p13c5-completed-image-publication-and-display-ownership).

## P13C6: changed-block evaluation

The ordinary allocation candidate remains byte-identical to C5. Select
`--backend cpu --changed blocks` explicitly for the measured 020/Fast candidate;
`--changed full` creates an equal-size history-reservation control that still
converts every pixel. The A500 recommendation remains native, without histories.
This is not a WHDLoad tooltype or a release-package change.

```sh
. ../../common/env.sh
python3 tools/ocs_memory_build.py --backend cpu --changed blocks --exit-probe --output tmp/c6-blocks
python3 tools/ocs_memory_build.py --backend cpu --changed full --exit-probe --output tmp/c6-full
python3 tools/ocs_memory_build.py --backend native --changed full --exit-probe --output tmp/c6-native
python3 tools/ocs_changed_check.py --build tmp/c6-blocks --output tmp/c6-unit
python3 tools/ocs_memory_install_check.py tmp/c6-blocks --output tmp/c6-install
python3 tools/ocs_publication_debugger.py --output tmp/c6-debugger
export FSUAE="$PWD/tmp/c6-debugger/fs-uae" WARP=1
SLAVE="$PWD/tmp/c6-blocks/WingCommander.Slave" \
  python3 tools/ocs_boot_gate.py --ownership --cpu 68020 --calibrate --output tmp/c6-layout
```

The C5 pinned local debugger input is reused; the builder adds the C6 host-only
instruction counters. `ocs_changed_run.py` supplies three disjoint owned-code
ranges from the build symbols and discovered slave base through
`WC_OCS_COST_RANGES`. `K` events at conversion completion report exclusive cycles
in the full adapter, changed adapter and Kalms leaves. No guest timer, code patch,
interior breakpoint or custom-register read is introduced by this instrument.
The changed-adapter charge includes comparison/history **and** staging/control;
it is not a pure comparison measurement. All output stays in a fresh `tmp/` tree.

Run controls sequentially; each traverses the same native milestones and records
one 250-field asteroid window plus one 250-field flight/fire window:

```bash
for arm in native full blocks; do
    python3 tools/ocs_changed_run.py --cpu 68020 --build "tmp/c6-$arm" \
        --layout tmp/c6-layout/layout.json --output "tmp/c6-020-$arm"
done
for arm in native blocks; do
    python3 tools/ocs_changed_run.py --cpu 68000 --build "tmp/c6-$arm" \
        --layout tmp/c6-layout/layout.json --output "tmp/c6-000-$arm"
done
python3 tools/ocs_changed_run.py --off --build tmp/c6-blocks \
    --layout tmp/c6-layout/layout.json --output tmp/c6-off
python3 tools/ocs_changed_run.py --views --build tmp/c6-blocks \
    --layout tmp/c6-layout/layout.json --output tmp/c6-views
```

The last run uses four 20-field diagnostic native-view requests. Ten fields do
not reliably capture a complete refreshed image; 40 can pass simulator death
before the final request on this faster path. These are renderer/view checks,
not interactive campaign-control acceptance.

```sh
python3 tools/ocs_changed_report.py \
    --run tmp/c6-020-native tmp/c6-native --run tmp/c6-020-full tmp/c6-full \
    --run tmp/c6-020-blocks tmp/c6-blocks --output tmp/c6-020.json
python3 tools/ocs_changed_report.py \
    --run tmp/c6-000-native tmp/c6-native --run tmp/c6-000-blocks tmp/c6-blocks \
    --output tmp/c6-000.json
python3 tools/ocs_publication_report.py tmp/c6-020-blocks --build tmp/c6-blocks \
    --observer-off tmp/c6-off --output tmp/c6-neutrality
python3 tools/ocs_publication_report.py tmp/c6-views --build tmp/c6-blocks \
    --output tmp/c6-view-report
python3 tools/ocs_memory_build.py --backend auto --output tmp/c6-default-control
python3 tools/reconstruct.py --variant ocs --output tmp/c6-original-control
python3 tools/reconstruct.py --variant cd32 --release --output tmp/c6-cd32-control
```

The C6 report checks source-stream hashes, clock calibration, actual publication,
independent DMA pixels, history allocation and exact instruction ranges. It allows
at most one initial image of capture-boundary alignment, then measures the entire
common contiguous asteroid prefix. It does not select convenient interior frames.
Flight costs are explicitly descriptive: different intro-window progression
prevents a matched flight-speed claim. Missing/inflated cost records and changed
source hashes must fail. See [results and limits](internals.md#p13c6-measured-changed-block-conversion).

## P13D1: OCS timing and side-effect audit

This gate executes the pinned original OCS instructions in the functional CPU
oracle. It does not boot an emulator or change a slave. No new performance
matrix is needed. The OCS unit/input/state owners and named scene exclusions
are in [internals](internals.md#p13d1-ocs-timing-and-side-effect-map).

```sh
. ../../common/env.sh
make unpack
python3 tools/ocs_timing_inventory.py --output tmp/p13d1-inventory-final
python3 tools/ocs_timing_check.py --output tmp/p13d1-native-final-v2
```

Use new names for subsequent runs; outputs must be fresh directories below
`tmp/`. Run without Python `-O` because assertions are the native oracle.
The installed `AMIGA_UNICORN` library requires executable JIT memory. The tool
records its SHA-256 and uses explicit M68000/M68020 models (enum values 1/2).
Both tools hash-check `tmp/game/WingCommander/data/Wing.english` before
loading, relocate its original hunks into a private fixture, and never overwrite
an input. Obtain missing inputs with `make unpack ARCHIVES=<directory>`.

`inventory.json` records roots, direct edges, decoded tables and classified
indirect boundaries; `reachable.dis` is derived scratch output. The common
walker is shared with CD32, with OCS-specific callback tables, selected helpers
and boundaries supplied explicitly. Native tests execute all 791 dispatch
entries, 140 bounded word-switch rejections and two action-ID rejections. A
broken switch signature must be rejected by the inventory.

`report.json` records six call-count schedules, local world/render timer
reproductions, unit conversions, keyboard queue wrap, joystick edge consumption,
held-axis clamping/release, simulator score/time/exit, gun reload versus reset,
field wrap/countdown, joystick hold/click field timers, audio tempo accumulation
and fault-poll RNG behavior. Its 23 responsibility records
link actual test paths to code-hunk/file and data-hunk offsets; a missing result
fails coverage. Whole routines and bounded slices are identified in the checker.
The reversed lifetime decrement is a rejecting control. The known high-bit
memory-shift discrepancy is reported as an instrument limitation, not accepted
as original hardware semantics. No report value is a CPU speed measurement.

The shared walker regression uses the retained, pinned CD32 flight capture:

```sh
python3 tools/timing_inventory.py tmp/phase7-combat-controls \
  --output tmp/p13d1-cd32-inventory-control
```

It retains 30,384 instructions, 6,118 edges, 54 tables and 625 entries. Its semantic
inventory matches the retained phase-7b result; decoder-version metadata is
recorded independently. This is a tooling regression, not renewed CD32 work.
D1's functional checks do not establish complete campaign, device or UI behavior.
The D2 integration and its separate live gate follow below.


## P13D2: OCS flight clock candidate

The opt-in English OCS candidate adds flight timing to the existing native
blitter/publication path. Default builds and CD32 are unchanged. Input is
currently polled at ticks; responsive input/prediction remains D3 and the intro
remains native until D4. See [the clock contract and measured limits](internals.md#p13d2-ocs-authoritative-flight-clock).

```sh
. ../../common/env.sh
make unpack
python3 tools/ocs_memory_build.py --clock --output tmp/p13d2-candidate
python3 tools/ocs_clock_check.py tmp/p13d2-candidate --output tmp/p13d2-clock-final
python3 tools/ocs_memory_install_check.py tmp/p13d2-candidate --output tmp/p13d2-install-final
```

Use fresh output names on repeats. The functional CPU requires executable JIT
memory. It tests M68000 and M68020 explicitly; these results are not timing
measurements. The local world fixture executes native arithmetic but stubs assets
and devices; the live comparisons below supply the separate simulator evidence.

Use the current `--ocs-pixels --ocs-observer` debugger from the C6 procedure,
which includes corrected actual DMA-pixel observation. For the retained build:

```sh
export FSUAE="$PWD/tmp/p13c6-debugger/fs-uae" WARP=1
export SLAVE="$PWD/tmp/p13d2-candidate/WingCommander.Slave"
python3 tools/ocs_boot_gate.py --ownership --calibrate --output tmp/p13d2-layout
python3 tools/ocs_boot_gate.py --ownership --simulator \
  --clock-build tmp/p13d2-candidate --baseline on \
  --layout tmp/p13d2-layout/layout.json --output tmp/p13d2-final-on
python3 tools/ocs_boot_gate.py --ownership --simulator \
  --clock-build tmp/p13d2-candidate --draw-every 5 --baseline on \
  --layout tmp/p13d2-layout/layout.json --output tmp/p13d2-final-sparse
python3 tools/ocs_boot_gate.py --ownership --simulator \
  --clock-build tmp/p13d2-candidate --baseline off \
  --layout tmp/p13d2-layout/layout.json --output tmp/p13d2-final-off
python3 tools/ocs_clock_report.py tmp/p13d2-final-on tmp/p13d2-final-sparse \
  --build tmp/p13d2-candidate --output tmp/p13d2-timing-final
python3 tools/ocs_publication_report.py tmp/p13d2-final-on \
  --build tmp/p13d2-candidate --observer-off tmp/p13d2-final-off \
  --output tmp/p13d2-publication-final
```

The driver selects the stock-clock A500 with 512 KiB Chip plus 4 MiB Fast,
validates effective settings and pins the slave/emulator hashes. WARP changes
host waiting, not the calibrated emulated-time denominator. It traverses the
native intro/menu into simulator flight and ends at the name prompt. Clock builds
use a 100-field firing window to avoid mixing active flight with native
post-flight calls; the unchanged intro control remains 250 fields. Cadence reports
reject a normal-arm endpoint outside the adapter. A sparse-arm window that has
already left flight is explicitly excluded from speed acceptance, not used to
infer overload. Tick comparisons precede that boundary.

The diagnostic `--draw-every 5` changes only the candidate's draw-budget data
before flight. It does not rewrite game code. Equality is checked at completed
ticks 11, 21 and 31 after both arms have drawn a first HUD, with a negative position
control and a required actual draw-count contrast. `ocs_clock_report.py` lists
the compared OCS data ranges and the native visual-annunciator exclusion. It
reports retained backlog, batch limits, complete native-world cost and actual
display changes separately. `ocs_publication_report.py` keeps the existing pixel,
blanking/ownership and observer-off controls; no display gate is waived for D2.

Normal-build regressions:

```sh
python3 tools/ocs_memory_build.py --output tmp/p13d2-default-control
python3 tools/reconstruct.py --variant ocs --output tmp/p13d2-original-control
python3 tools/reconstruct.py --variant cd32 --release --output tmp/p13d2-cd32-control
```

The hashes remain `172d3297…`, `eec155c9…` and `fdd92fbb…` respectively. Live NTSC,
full campaign/modal/UI compatibility and heavier scenes remain later acceptance;
PAL/NTSC scheduler arithmetic and a native pause return are covered locally.

## P13D3: OCS input and presentation candidate

`--prediction` implies `--clock`. The default candidate, original OCS and CD32
release remain the controls; this is not a release archive. The native checker
uses the retained D2 simulator fixture (`tmp/p13d2-final-on`), which can be
regenerated with the preceding D2 procedure. All generated material remains in
`tmp/`. Use fresh output names for repeat runs.

```sh
. ../../common/env.sh
make unpack
python3 tools/ocs_memory_build.py --prediction --output tmp/p13d3-candidate
python3 tools/ocs_prediction_check.py tmp/p13d3-candidate --output tmp/p13d3-native-final5
python3 tools/ocs_memory_install_check.py tmp/p13d3-candidate --output tmp/p13d3-install-final
python3 tools/ocs_memory_build.py --prediction --backend cpu --output tmp/p13d3-cpu-candidate
python3 tools/ocs_publication_debugger.py --output tmp/p13d3-debugger
```

The last command reuses the pinned C2 source input and C5/C6 DMA correction,
adding the D3 read-only queue-target observation. It does not edit the shared
emulator. Native CPU tests require executable JIT memory; live checks require the
project-owned local debugger connection.

```sh
export FSUAE="$PWD/tmp/p13d3-debugger/fs-uae" WARP=1
export SLAVE="$PWD/tmp/p13d3-candidate/WingCommander.Slave"
python3 tools/ocs_boot_gate.py --ownership --calibrate --output tmp/p13d3-layout-final
```

The A500 driver traces ten fields after completed tick two, then observes a
200-field **coasting** window. The legacy output name `fire` is retained, but
`flight_input` records the actual input. The 68020 driver holds fire for 150 fields
after tick two, compares completed ticks 41/51, and traces ten fields after tick
41. Both reach name entry. These windows exclude native post-flight calls from
scheduler cadence. The observer reads actual queue targets from the verified
candidate symbol map. Default `--prediction-mode auto` uses measured service
cost; `on` and `off` are diagnostic data controls with identical code/layout.

```sh
python3 tools/ocs_boot_gate.py --ownership --simulator \
  --clock-build tmp/p13d3-candidate --baseline on \
  --layout tmp/p13d3-layout-final/layout.json --output tmp/p13d3-final-a500
python3 tools/ocs_boot_gate.py --ownership --simulator \
  --clock-build tmp/p13d3-candidate --baseline off \
  --layout tmp/p13d3-layout-final/layout.json --output tmp/p13d3-final-a500-off
python3 tools/ocs_prediction_report.py tmp/p13d3-final-a500 \
  --build tmp/p13d3-candidate --output tmp/p13d3-a500-final-report
python3 tools/ocs_publication_report.py tmp/p13d3-final-a500 \
  --build tmp/p13d3-candidate --observer-off tmp/p13d3-final-a500-off \
  --output tmp/p13d3-a500-final-observer
export SLAVE="$PWD/tmp/p13d3-cpu-candidate/WingCommander.Slave"
python3 tools/ocs_boot_gate.py --ownership --cpu 68020 --calibrate \
  --output tmp/p13d3-layout-cpu
python3 tools/ocs_boot_gate.py --ownership --cpu 68020 --simulator \
  --clock-build tmp/p13d3-cpu-candidate --prediction-mode on --baseline on \
  --layout tmp/p13d3-layout-cpu/layout.json --output tmp/p13d3-final-cpu-on
python3 tools/ocs_boot_gate.py --ownership --cpu 68020 --simulator \
  --clock-build tmp/p13d3-cpu-candidate --prediction-mode off --baseline on \
  --layout tmp/p13d3-layout-cpu/layout.json --output tmp/p13d3-final-cpu-off
python3 tools/ocs_prediction_report.py tmp/p13d3-final-cpu-on \
  --build tmp/p13d3-cpu-candidate --compare-off tmp/p13d3-final-cpu-off \
  --output tmp/p13d3-cpu-comparison
python3 tools/ocs_publication_report.py tmp/p13d3-final-cpu-on \
  --build tmp/p13d3-cpu-candidate --output tmp/p13d3-cpu-pixels
python3 tools/ocs_publication_report.py tmp/p13d3-final-cpu-off \
  --build tmp/p13d3-cpu-candidate --output tmp/p13d3-cpu-off-pixels
```

The stock-clock checks and 512 KiB Chip/4 MiB Fast selection remain mandatory.
The cost report measures complete owned calls in the ten-field Barto trace,
including native callees/interrupts and excluding boundary calls; it does not
misattribute tail-dispatched input as an owned RTS scope. Native tests separately
cover PAL/NTSC arithmetic, keyboard FIFO wrap, field gaps/overflow, modal resets
and view-cut invalidation. Live all-view/NTSC/campaign acceptance remains E2.
Repeat the preceding normal-build regressions with fresh D3 output names: hashes
remain `172d3297…`, `eec155c9…` and `fdd92fbb…`. D4 intro work is separate.

## P13D4: OCS title and asteroid credits

`--intro` implies `--prediction --clock`; it is an opt-in candidate, not a release
build. It shares the title-loop and prediction algorithms with CD32 while using
OCS script constants, field addresses and native calls. Use fresh output names.
The existing D3 fixture and debugger prerequisites above still apply.

```sh
. ../../common/env.sh
make unpack
python3 tools/ocs_memory_build.py --intro --output tmp/p13d4-candidate5
python3 tools/ocs_memory_build.py --intro --backend cpu --output tmp/p13d4-cpu5
python3 tools/ocs_intro_check.py tmp/p13d4-candidate5 --output tmp/p13d4-native-final2
python3 tools/ocs_memory_install_check.py tmp/p13d4-candidate5 --output tmp/p13d4-install5
python3 tools/ocs_prediction_check.py tmp/p13d4-candidate5 --output tmp/p13d4-d3-regression5
export FSUAE="$PWD/tmp/p13d3-debugger/fs-uae" WARP=1
export SLAVE="$PWD/tmp/p13d4-cpu5/WingCommander.Slave"
python3 tools/ocs_boot_gate.py --ownership --cpu 68020 --calibrate \
  --output tmp/p13d4-layout-cpu5
python3 tools/ocs_boot_gate.py --ownership --cpu 68020 \
  --clock-build tmp/p13d4-cpu5 --intro-cycle --simulator --baseline on \
  --layout tmp/p13d4-layout-cpu5/layout.json --output tmp/p13d4-live-cpu5
python3 tools/ocs_intro_report.py tmp/p13d4-live-cpu5 \
  --build tmp/p13d4-cpu5 --output tmp/p13d4-cpu-intro-final
python3 tools/ocs_publication_report.py tmp/p13d4-live-cpu5 \
  --build tmp/p13d4-cpu5 --output tmp/p13d4-cpu-pixel-report5
export SLAVE="$PWD/tmp/p13d4-candidate5/WingCommander.Slave"
python3 tools/ocs_boot_gate.py --ownership --calibrate --output tmp/p13d4-layout-a5005
python3 tools/ocs_boot_gate.py --ownership --clock-build tmp/p13d4-candidate5 \
  --simulator --baseline on --layout tmp/p13d4-layout-a5005/layout.json \
  --output tmp/p13d4-live-a5005
python3 tools/ocs_boot_gate.py --ownership --clock-build tmp/p13d4-candidate5 \
  --simulator --baseline off --layout tmp/p13d4-layout-a5005/layout.json \
  --output tmp/p13d4-live-a5005-off
python3 tools/ocs_intro_report.py tmp/p13d4-live-a5005 \
  --build tmp/p13d4-candidate5 --output tmp/p13d4-a500-intro5
python3 tools/ocs_publication_report.py tmp/p13d4-live-a5005 \
  --build tmp/p13d4-candidate5 --observer-off tmp/p13d4-live-a5005-off \
  --output tmp/p13d4-a500-observer5
python3 tools/ocs_prediction_report.py tmp/p13d4-live-a5005 \
  --build tmp/p13d4-candidate5 --output tmp/p13d4-a500-flight5
```

`--intro-cycle` requires the baseline and simulator options. It traverses every
credit page without skipping, then repeats the title and reaches credits again
before using native Escape/menu input to enter the simulator. The short A500
control uses identical checkpoints with observation enabled/disabled. Reports
pin effective machine settings and emulated-time denominators; WARP affects host
waiting only. The full cycle is scoped to PAL 020/Fast, and the A500 intro remains
a measured E1 overload. See [D4 results and limits](internals.md#p13d4-ocs-title-and-asteroid-credit-timing).

Control builds (same hashes as before D4):

```sh
python3 tools/ocs_memory_build.py --prediction --output tmp/p13d4-d3-control
python3 tools/ocs_memory_build.py --output tmp/p13d4-default-control
python3 tools/reconstruct.py --variant ocs --output tmp/p13d4-original-control
python3 tools/reconstruct.py --variant cd32 --release --output tmp/p13d4-cd32-control
```

## P13E1: focused arithmetic and collision optimisation

`--math-fast` implies `--intro --prediction --clock`. It is an opt-in OCS
candidate, not a release. It adds no data history/allocation and retains the
measured native-blitter A500 and CPU/Fast 020 choices. Heavy A500 scenes remain
below the 10 Hz target; see [results and limits](internals.md#p13e1-focused-ocs-performance-gate).
Use fresh output names. D3's pinned debugger and simulator fixture remain the
prerequisites described above.

```sh
. ../../common/env.sh
make unpack
python3 tools/ocs_memory_build.py --math-fast --output tmp/p13e1-final2
python3 tools/ocs_memory_build.py --math-fast --backend cpu --output tmp/p13e1-cpu-final2
python3 tools/ocs_math_check.py tmp/p13e1-final2 --output tmp/p13e1-native-final3
python3 tools/ocs_memory_install_check.py tmp/p13e1-final2 --output tmp/p13e1-install-final2
python3 tools/ocs_prediction_check.py tmp/p13e1-final2 --output tmp/p13e1-prediction-final2
python3 tools/ocs_intro_check.py tmp/p13e1-final2 --output tmp/p13e1-intro-native-final2
export FSUAE="$PWD/tmp/p13d3-debugger/fs-uae" WARP=1
export SLAVE="$PWD/tmp/p13e1-final2/WingCommander.Slave"
python3 tools/ocs_boot_gate.py --ownership --calibrate --output tmp/p13e1-layout-final2
python3 tools/ocs_boot_gate.py --ownership --clock-build tmp/p13e1-final2 \
  --simulator --baseline on --held-fire --cost-profile \
  --layout tmp/p13e1-layout-final2/layout.json --output tmp/p13e1-final-live
python3 tools/ocs_boot_gate.py --ownership --clock-build tmp/p13e1-final2 \
  --simulator --baseline on --layout tmp/p13e1-layout-final2/layout.json \
  --output tmp/p13e1-coast
python3 tools/ocs_boot_gate.py --ownership --clock-build tmp/p13e1-final2 \
  --simulator --baseline off --layout tmp/p13e1-layout-final2/layout.json \
  --output tmp/p13e1-coast-off
python3 tools/ocs_publication_report.py tmp/p13e1-coast --build tmp/p13e1-final2 \
  --observer-off tmp/p13e1-coast-off --output tmp/p13e1-observer-final
python3 tools/ocs_prediction_report.py tmp/p13e1-coast --build tmp/p13e1-final2 \
  --output tmp/p13e1-coast-flight
python3 tools/ocs_intro_report.py tmp/p13e1-final-live --build tmp/p13e1-final2 \
  --output tmp/p13e1-final-intro
python3 tools/ocs_performance_report.py tmp/p13e1-final-live --build tmp/p13e1-final2 \
  --output tmp/p13e1-accept-a500
python3 tools/ocs_performance_report.py tmp/p13e1-coast --build tmp/p13e1-final2 \
  --output tmp/p13e1-accept-coast
export SLAVE="$PWD/tmp/p13e1-cpu-final2/WingCommander.Slave"
python3 tools/ocs_boot_gate.py --ownership --cpu 68020 --calibrate \
  --output tmp/p13e1-layout-cpu-final2
python3 tools/ocs_boot_gate.py --ownership --cpu 68020 \
  --clock-build tmp/p13e1-cpu-final2 --simulator --baseline on --held-fire --cost-profile \
  --layout tmp/p13e1-layout-cpu-final2/layout.json --output tmp/p13e1-cpu-live
python3 tools/ocs_publication_report.py tmp/p13e1-cpu-live --build tmp/p13e1-cpu-final2 \
  --output tmp/p13e1-cpu-pixels
python3 tools/ocs_performance_report.py tmp/p13e1-cpu-live --build tmp/p13e1-cpu-final2 \
  --output tmp/p13e1-accept-cpu
```

`--held-fire` selects native Space during the A500 measurement too. Without it,
A500 remains the existing coasting correctness window. `--cost-profile` adds a
20-field instruction trace after the asteroid window and a ten-field trace after
pressing fire, before the flight window. Neither trace has debugger stops inside
it; the existing pre-fire/coasting trace is retained separately. Profiling changes
where subsequent flight input falls, so controls use the same flags. The normal
A500 workload is 200 fields; 020 fire remains 150. Do not merge their denominators
or claim that the coasting pixel gate accepts the overloaded held-fire workload.

The performance report records overload rather than relaxing the separate D3
cadence or C5 pixel gate. A500 held fire has only one completed image and cannot
satisfy the existing three-image publication gate; coasting and 020 do satisfy it.
It reports null interval distributions when fewer than two pictures appear,
checks actual field/counter accounting, and labels OS memory as sampled pools.
Instruction costs are only interpreted on the calibrated 68000, with complete
entry/RTS scopes, stack matching and boundary exclusions. Nested costs must not
be summed. The extra 020 traces are only part of the matched driving protocol.

Fresh unchanged controls use the same bounded heavy-workload flags:

```sh
export SLAVE="$PWD/tmp/p13d4-candidate5/WingCommander.Slave"
python3 tools/ocs_boot_gate.py --ownership --clock-build tmp/p13d4-candidate5 \
  --simulator --baseline on --held-fire --cost-profile \
  --layout tmp/p13d4-layout-a5005/layout.json --output tmp/p13e1-reference
python3 tools/ocs_performance_report.py tmp/p13e1-reference --build tmp/p13d4-candidate5 \
  --output tmp/p13e1-accept-reference
export SLAVE="$PWD/tmp/p13d4-cpu5/WingCommander.Slave"
python3 tools/ocs_boot_gate.py --ownership --cpu 68020 --clock-build tmp/p13d4-cpu5 \
  --simulator --baseline on --held-fire --cost-profile \
  --layout tmp/p13d4-layout-cpu5/layout.json --output tmp/p13e1-cpu-reference
python3 tools/ocs_performance_report.py tmp/p13e1-cpu-reference --build tmp/p13d4-cpu5 \
  --output tmp/p13e1-accept-cpu-reference
python3 tools/ocs_memory_build.py --intro --output tmp/p13e1-d4-control
python3 tools/ocs_memory_build.py --output tmp/p13e1-default-control
python3 tools/reconstruct.py --variant ocs --output tmp/p13e1-original-control
python3 tools/reconstruct.py --variant cd32 --release --output tmp/p13e1-cd32-control
```

The D4/default/original OCS/CD32 controls retain `e32ece47…`, `172d3297…`,
`eec155c9…` and `fdd92fbb…`. The native/CPU E1 candidates are 40,352 bytes, hashes
`7485ed46…` and `ad33a2a1…`. All generated bytes, traces and captures stay in `tmp/`.

### P13E2 compatibility checks

Use the E1 candidates and their matching calibrated layouts. `--compat` omits
instruction profiling, retaining the bounded display observer and CPU audits.
All paths below refer to local scratch outputs; choose a new output directory
when repeating a run.

```sh
. ../../common/env.sh
export FSUAE="$PWD/tmp/p13d3-debugger/fs-uae"
export SLAVE="$PWD/tmp/p13e1-cpu-final2/WingCommander.Slave"
WARP=1 python3 tools/ocs_boot_gate.py --ownership --cpu 68020 \
  --clock-build tmp/p13e1-cpu-final2 --simulator --baseline on --held-fire \
  --compat --ntsc --layout tmp/p13e2-layout-ntsc/layout.json \
  --output tmp/p13e2-ntsc
python3 tools/ocs_compatibility_report.py tmp/p13e2-ntsc \
  --build tmp/p13e1-cpu-final2 --output tmp/p13e2-ntsc-compat-final
```

Replace `--ntsc` with `--aga` for the accelerated A1200/020 instruction-cache
check, using its own calibrated layout. The AGA preset explicitly uses 2 MiB
Chip and 4 MiB Fast; a CPU multiplier is not a hardware MHz measurement.
The 68000 CPU override uses `--cpu 68000 --flight-fields 400` and its own layout.
Use `--functional` for native name editing, campaign save/load and flight
controls. The final functional route additionally exercises missile-follow and
external fighter/carrier subject cycling; partial UI checkpoints alone do not
constitute this acceptance.

The accepted first-mission functional route uses:

```sh
WARP=1 python3 tools/ocs_boot_gate.py --ownership --cpu 68020 \
  --clock-build tmp/p13e1-cpu-final2 --simulator --baseline on --held-fire \
  --compat --functional --layout tmp/p13e1-layout-cpu-final2/layout.json \
  --output tmp/p13e2-functional6
python3 tools/ocs_compatibility_report.py tmp/p13e2-functional6 \
  --build tmp/p13e1-cpu-final2 --output tmp/p13e2-functional6-compat
```

The driver waits for a native target within range before F7. All control inputs
use the native keyboard route; there are no injected mission/target/save records.
Save files remain in the run's disposable game tree. Inspect `quit.png` for the
DOS return in addition to the automated record and flush checks.


The report checks all native save blocks, paused world state, actual selected
cameras, input overflow counters and detected field frequency. It records unknown
DMA words without counting them as verified pixels. Corrupted-evidence controls
must fail; their scratch trees link to unchanged accepted captures to avoid
copying large traces. Keep those captures while the reports are needed.

Focused fallback/startup and shared-code checks (use new output paths on repeat):

```sh
python3 tools/ocs_memory_check.py --output tmp/p13e2-memory
python3 tools/ocs_memory_install_check.py tmp/p13e1-cpu-final2 --output tmp/p13e2-install
python3 tools/ocs_prediction_check.py tmp/p13e1-cpu-final2 --output tmp/p13e2-prediction
```

These native checks need the shared CPU-test runtime. The allocation suite stubs
Exec and tests failure/rollback with the native registry; it is not a live
low-RAM machine run. The D2-only `ocs_clock_check.py` rejects D3/E1 prediction
builds; use the input-aware check above. Retain the original shared CD32 focused
commands and fixtures documented in their sections, especially
`tmp/phase7-combat-controls/start-fast.bin`.


```sh
python3 tools/projectile_spawn_check.py tmp/p13e1-cd32-control --output tmp/p13e2-cd32-spawn.json
python3 tools/timing_scene_check.py tmp/p13e1-cd32-control --output tmp/p13e2-cd32-scene
python3 tools/release_check.py tmp/p13e1-cd32-control --negative-controls --output tmp/p13e2-cd32-options.json
python3 tools/flight_render_check.py tmp/p13e1-cd32-control --output tmp/p13e2-cd32-pixels.json
```

### P13E3 reproducible hand-off

The [OCS hand-off](ocs-release.md) defines the exact candidate pair, support
limits, options and the release packaging. Rebuild without generating more live
captures; E2 acceptance carries over only if both binaries remain identical.
Use fresh output names on repeats. All generated material stays in `tmp/`.

```sh
. ../../common/env.sh
make unpack
python3 tools/ocs_memory_build.py --math-fast --output tmp/p13e3-native
python3 tools/ocs_memory_build.py --math-fast --backend cpu --output tmp/p13e3-cpu
shasum -a 256 tmp/p13e3-native/WingCommander.Slave tmp/p13e3-cpu/WingCommander.Slave
cmp tmp/p13e3-native/WingCommander.Slave tmp/p13e1-final2/WingCommander.Slave
cmp tmp/p13e3-cpu/WingCommander.Slave tmp/p13e1-cpu-final2/WingCommander.Slave
```

Both comparisons passed at the hand-off. SHA-256 values match the full values
in the candidate table. `build.json` must show `changed=off`, `exit_probe=false`
and clock/prediction/intro/math enabled. These are fresh builds of the accepted
code, not new emulator measurements. If E1 scratch copies are unavailable,
compare against the recorded hashes; the documented E2 reports retain their
original evidence scope. Use the E2 commands above when code changes invalidate
that evidence, rather than making fresh multi-gigabyte captures for a doc edit.

To run a candidate interactively using the existing separate OCS launcher:

```sh
make run VARIANT=WingCommander SLAVE=tmp/p13e3-native/WingCommander.Slave \
  SETUP=a500 OCS_STOCK_CLOCK=1 WARP=0
```

The explicit CPU candidate is at `tmp/p13e3-cpu/WingCommander.Slave`; select the
appropriate measured setup explicitly rather than assuming CPU type proves the
crossover. The launcher creates a disposable runtime copy; it does not package
or replace the reference installation. Preserve the accepted E1/E2 captures
referenced by reports while they remain the evidence for this hand-off.

### OCS public Enhanced framerate toggle

The user-facing build is now distinct from the preserved ungated diagnostic
builds used by P13C–E. `--public` implies all E1 enhancements, defaults to the CPU
backend, leaves changed-block histories off, and emits an OCS launch icon with
`CUSTOM5=1` plus an OCS ReadMe. An absent or zero option means original behaviour;
the icon, not an implicit slave default, requests enhancements. CPU and true-Fast
checks always apply. Existing original/CD32 input trees are not modified.

```sh
. ../../common/env.sh
python3 tools/ocs_memory_build.py --public --output tmp/ocs-public-final2
python3 tools/ocs_options_check.py tmp/ocs-public-final2 --output tmp/ocs-public-options-accepted
python3 tools/ocs_prediction_check.py tmp/ocs-public-final2 --output tmp/ocs-public-prediction-final2
```

Use new output names on repeats. The public slave is 40,808 bytes, SHA-256
`4e7149536d54b55b692b6a659b967f20680615cc2e3e20d7daf419595288b6f4`.
The startup checker executes option values 0/1/2/-1, CPU flags through 060,
English/other patch lists, valid/corrupt hooks, Zorro II/high Fast, Chip, slow,
empty and invalid memory lists. It checks skipped relocation/hook/flush work,
register preservation, original slave bytes and icon artwork/tooltypes. Mutating
the option, CPU mask or slow-memory exclusion must fail. Exec list fixtures and
WHDLoad calls are bounded native tests, not a hardware or speed measurement.

A short eligible-machine live gate uses the existing local debugger:

```sh
export FSUAE="$PWD/tmp/p13d3-debugger/fs-uae"
export SLAVE="$PWD/tmp/ocs-public-final2/WingCommander.Slave"
WARP=1 python3 tools/ocs_boot_gate.py --ownership --cpu 68020 --enhanced 1 \
  --calibrate --output tmp/ocs-public-layout2
WARP=1 python3 tools/ocs_boot_gate.py --ownership --cpu 68020 --enhanced 1 \
  --clock-build tmp/ocs-public-final2 --baseline on --simulator --compat \
  --layout tmp/ocs-public-layout2/layout.json --output tmp/ocs-public-live2
python3 tools/ocs_compatibility_report.py tmp/ocs-public-live2 \
  --build tmp/ocs-public-final2 --output tmp/ocs-public-compat2
python3 tools/ocs_publication_report.py tmp/ocs-public-live2 \
  --build tmp/ocs-public-final2 --output tmp/ocs-public-pixels2
```

For original-mode smoke checks, use `--enhanced 0` on 68020 or `--enhanced 1`
on 68000. Calibrate each configuration independently, then boot with its layout
and `--ownership --compat`, omitting `--clock-build --baseline --simulator`.
A clock fixture requires installed enhancements and is deliberately rejected for
a public build with an off option or 68000. These original-mode runs stop at the
menu, sufficient to inspect unchanged hook sites and native intro rendering.

Interactive launches use `WHD_ARGS='CUSTOM5=1'` explicitly with `VARIANT=WingCommander`
and the selected public `SLAVE`; clearing that argument selects original mode.
The runtime preparer only enables the icon in a fresh OCS tree when a public
slave is selected. CD32 and original OCS icon contents remain unchanged. Merely
copying the slave over an old installation does not silently change its tooltypes.

Check original-mode live evidence without new captures:

```sh
python3 tools/ocs_options_live_check.py tmp/ocs-public-final2 tmp/ocs-public-off-live \
  --output tmp/ocs-public-off-check.json
python3 tools/ocs_options_live_check.py tmp/ocs-public-final2 tmp/ocs-public-000-live \
  --output tmp/ocs-public-000-check.json
```

The checker relocates the pinned original game to each capture's hunk bases,
compares all enhancement hook/NOP/modal windows and requires inactive state.
A changed-hook negative control must be rejected. It does not claim complete
screen or game-state equality across machines with different rendering speeds.
The four bit-exact E1 sites and two waypoint sites must instead hold their
always-on hooks.

### Always-on exact E1 shortcuts and original-mode A500 profile

The public build installs E1's arithmetic/collision hooks on every path; see
[results](internals.md#always-on-exact-e1-shortcuts-in-original-mode). Validate
a new public build with the startup matrix, E1 equivalence and prediction checks
above plus `ocs_math_check.py`, then the live gates. Original-mode captures use
the P13A4 route with a public slave; calibrate each slave separately:

```sh
. ../../common/env.sh
export FSUAE="$PWD/tmp/p13d3-debugger/fs-uae"
python3 tools/ocs_math_check.py tmp/exact-ocs-v1 --output tmp/exact-ocs-v1-math
export SLAVE="$PWD/tmp/exact-ocs-v1/WingCommander.Slave"
WARP=1 python3 tools/ocs_boot_gate.py --calibrate --baseline on --output tmp/a500-exact-v1-layout
WARP=0 python3 tools/ocs_boot_gate.py --layout tmp/a500-exact-v1-layout/layout.json \
  --baseline on --output tmp/a500-exact-v1
```

Repeat with a public build from the previous commit as the control. The strict
`ocs_baseline_report.py` pairs observer on/off runs of the pinned original slave
only, and rejects a window containing a picture replaced before display; count
published and displayed pictures separately for such comparisons.

`--cost-profile` with `--baseline on --simulator` and no clock build adds
original-mode instruction traces: 20 asteroid-credit fields, 20 coasting
simulator fields, and 20 fields after native fire is pressed, each outside the
measurement windows. Use the unpatched original slave (no `SLAVE`) for the
native profile. The trace interpretation follows the P13E1 rules: complete
entry/RTS scopes with matching stack pointers, calibrated 68000 only, nested
scopes never summed.

### OCS interactive launcher

`make run VARIANT=WingCommander` is the OCS entry point. It builds the current public
candidate (`tmp/build/release/WingCommander/`), then boots the A3000 preset with
`CUSTOM5=1 DCACHE` (instruction and data caches). Each boot uses a fresh game drive.

```sh
make run VARIANT=WingCommander
make stop
make run VARIANT=WingCommander SETUP=a500
make run VARIANT=WingCommander WHD_ARGS='CUSTOM5=0'
make run VARIANT=WingCommander INSTANCE=ocs    # beside a CD32 run
```

A500 automatically retains original behaviour despite the requested toggle.
`SLAVE` replaces the automatic build; it also drops the default `WHD_ARGS` and selects
the A500 baseline unless `SETUP` is given, so a diagnostic slave on the A3000 with the
toggle is `SLAVE=... SETUP=a3000 WHD_ARGS='CUSTOM5=1 DCACHE'`. `SETUP`, `WHD_ARGS`,
`INSTANCE` and the shared sound/window settings remain overridable. An explicitly
empty `WHD_ARGS=` also selects original behaviour. `make stop` does not build a slave.
`make run` builds and runs the latest enhanced CD32 slave by default
(`tmp/build/release/WingCommanderCD32/`), with `CUSTOM5=0 DCACHE`. An explicit
`SLAVE` (`SLAVE=original` for the shipped slave) bypasses this build for original or
diagnostic runs; explicit `WHD_ARGS` overrides the defaults.

The OCS generated launch icon also adds `DCACHE` unless an explicit CACHE,
DCACHE or NOCACHE choice already exists. The launcher default can be replaced
with `WHD_ARGS='CUSTOM5=1 NOCACHE'`. These defaults do not change slave bytes or
restart an already-running game. The slave retains its existing SetCPU policy;
WHDLoad applies the user cache override. `CACHE` alone is not the equivalent:
it requests instruction caching while disabling data caching.

### Shared opening clock and smooth zooms

The OCS public build and CD32 release include the opening adapter. Diagnostic
OCS candidates without `--public` and normal reconstructions remain unchanged.
Use fresh output directories; all binaries, screenshots and reports stay in `tmp/`.

```sh
. ../../common/env.sh
python3 tools/ocs_memory_build.py --public --output tmp/opening-ocs
python3 tools/reconstruct.py --variant cd32 --release --output tmp/opening-cd32
python3 tools/opening_check.py ocs tmp/opening-ocs --output tmp/opening-ocs-clock-check
python3 tools/opening_check.py cd32 tmp/opening-cd32 --output tmp/opening-cd32-clock-check
python3 tools/ocs_options_check.py tmp/opening-ocs --output tmp/opening-ocs-option-check
python3 tools/timing_adapter_check.py tmp/opening-cd32 --output tmp/opening-cd32-option-check
python3 tools/release_check.py tmp/opening-cd32 --negative-controls --output tmp/opening-release-check-new
export FSUAE="$PWD/tmp/p13d3-debugger/fs-uae"
python3 tools/opening_live_check.py ocs tmp/opening-ocs --output tmp/opening-ocs-live-new
python3 tools/opening_live_check.py cd32 tmp/opening-cd32 --output tmp/opening-cd32-live-new
```

The native checker executes PAL/NTSC clocks, wrap, input skip, retained overdue
steps, both zoom trajectories and every guarded-word rejection. The option
checkers also compare untouched startup-hunk bytes in original modes. The live
gate calibrates its own segment chain, reboots deterministically, samples 20
positions in each zoom, captures four images, and stops at the world intro.
It does not skip the opening, alter guest state, or retain large profiling files.
Its fixed PAL machines are OCS 020/4 MiB Fast and CD32 A1200/Fast, with DCACHE and
host warp; it records emulated field counts, not host-time performance.

Accepted artifacts are `tmp/opening-ocs-v3` and `tmp/opening-cd32-final`
(the latter is byte-identical to the live-tested `tmp/opening-cd32-v4`). Native
reports are `tmp/opening-{ocs,cd32}-final-clock` and
`tmp/opening-{ocs,cd32}-final-options`; full opening reports/screenshots are
`tmp/opening-{ocs,cd32}-live`. Launch the current OCS code through
`make run VARIANT=WingCommander`, which builds the public candidate by default.

### Wing Commander title zoom and rotation

The shared title loop now samples its own sprite scale and rotation between world
ticks. Build and test both variants with fresh output directories:

```sh
. ../../common/env.sh
python3 tools/ocs_memory_build.py --public --output tmp/title-ocs-new
python3 tools/reconstruct.py --variant cd32 --release --output tmp/title-cd32-new
python3 tools/title_motion_check.py ocs tmp/title-ocs-new --output tmp/title-ocs-native-new
python3 tools/title_motion_check.py cd32 tmp/title-cd32-new --output tmp/title-cd32-native-new
python3 tools/ocs_intro_check.py tmp/title-ocs-new --output tmp/title-ocs-intro-new
python3 tools/intro_clock_check.py tmp/title-cd32-new --output tmp/title-cd32-intro-new.json
export FSUAE="$PWD/tmp/p13d3-debugger/fs-uae"
python3 tools/opening_live_check.py ocs tmp/title-ocs-new --title-only --output tmp/title-ocs-live-new
python3 tools/opening_live_check.py cd32 tmp/title-cd32-new --title-only --output tmp/title-cd32-live-new
```

`--title-only` skips the opening through native Escape handling, releases the key
at the world-intro entry, then records 20 calls to each native title bitmap
renderer. It requires differing render parameters within one unchanged script
tick, captures approach/rotation images, and reaches the native title-loop exit.
It retains the bounded PAL/DCACHE setups and field-based observations of the
opening gate. Native tests additionally cover NTSC and fractional projection at
phase boundaries without modifying authoritative geometry.

Accepted builds are `tmp/title-ocs-v2` and `tmp/title-cd32-v2`; their native
sampler reports are `tmp/title-{ocs,cd32}-native/report.json`. Full-loop checks
are `tmp/title-ocs-intro-final/report.json` and `tmp/title-cd32-intro-final.json`.
Both live runs pass in `tmp/title-{ocs,cd32}-live/report.json`, with two PNG
captures each. The existing OCS launcher builds these changes automatically.


### Exhaust attachment motion

Build the public OCS candidate and check native placement/restoration:

```sh
. ../../common/env.sh
python3 tools/ocs_memory_build.py --public --output tmp/exhaust-ocs-v2
python3 tools/exhaust_check.py tmp/exhaust-ocs-v2 --output tmp/exhaust-native-final
python3 tools/ocs_prediction_check.py tmp/exhaust-ocs-v2 --output tmp/exhaust-prediction
python3 tools/ocs_intro_check.py tmp/exhaust-ocs-v2 --output tmp/exhaust-intro
python3 tools/ocs_options_check.py tmp/exhaust-ocs-v2 --output tmp/exhaust-options
export FSUAE="$PWD/tmp/p13d3-debugger/fs-uae"
python3 tools/opening_live_check.py ocs tmp/exhaust-ocs-v2 \
  --exhaust-only --output tmp/exhaust-ocs-fast-live2
python3 tools/opening_live_check.py cd32 tmp/title-cd32-v2 \
  --exhaust-only --output tmp/exhaust-cd32-live
```

Use fresh output names on repeat runs. The CD32 command uses the existing enhanced
build; rebuild it with `tools/reconstruct.py --variant cd32 --release` when needed.
`--exhaust-only` skips the opening with native keyboard input, then observes up to
200 intro pictures until eight parent/exhaust movement pairs occur within unchanged
world ticks. It uses the established `a1200-030` observer profile for both variants,
with its explicit legacy cache-model compatibility setting, PAL and DCACHE. It
changes no guest poses. Reports contain coordinates sampled at native sort entry;
the one-field screenshot may lag this render sample. This is functional evidence,
not a frame-rate measurement. All owned observer processes stop on exit.


### Running-pilot background regression

Build fresh enhanced candidates and run the bounded cinematic fixture:

```sh
. ../../common/env.sh
python3 tools/ocs_memory_build.py --public --output tmp/running-ocs
python3 tools/reconstruct.py --variant cd32 --release --output tmp/running-cd32
export FSUAE="$PWD/tmp/p13d3-debugger/fs-uae"
python3 tools/cinematic_live_check.py ocs tmp/running-ocs --timing --output tmp/running-ocs-live
python3 tools/cinematic_live_check.py cd32 tmp/running-cd32 --timing --output tmp/running-cd32-live
python3 tools/cinematic_background_check.py ocs tmp/running-ocs tmp/running-ocs-live --output tmp/running-ocs-native
python3 tools/cinematic_background_check.py cd32 tmp/running-cd32 tmp/running-cd32-live --output tmp/running-cd32-native
```

Use new output directories. The live fixture needs the project's existing
`key`, `ocs-load` and lossless profile-image observer commands. It uses the
known 030/cache observer profile with 4 MiB Fast RAM, keeping the menu-call
fixture inside the observer's supported address range. It invokes the native
running cinematic from the initialized menu, restores that call on completion,
and stops only its own emulator. This is a scene fixture, not a campaign replay.
It keeps eight PNGs and a 6 MiB native replay snapshot per variant, deleting
transient instruction captures. The native checker verifies complete 320×128
background pixels, alternating tile identity, register/stack contracts and
missing-wrap rejection. It makes no performance claim.

### Intro camera orientation

The focused native test checks small pitch/yaw/roll motion against samples of
native whole-tick basis endpoints, plus restoration and view-cut/disabled guards.
Use fresh output directories:

```sh
. ../../common/env.sh
python3 tools/ocs_memory_build.py --public --output tmp/camera-ocs-new
python3 tools/reconstruct.py --variant cd32 --release --output tmp/camera-cd32-new
python3 tools/intro_camera_check.py ocs tmp/camera-ocs-new --output tmp/camera-ocs-native-new
python3 tools/intro_camera_check.py cd32 tmp/camera-cd32-new --output tmp/camera-cd32-native-new
python3 tools/ocs_intro_check.py tmp/camera-ocs-new --output tmp/camera-ocs-clock-new
python3 tools/intro_clock_check.py tmp/camera-cd32-new --output tmp/camera-cd32-clock-new.json
export FSUAE="$PWD/tmp/p13d3-debugger/fs-uae"
python3 tools/opening_live_check.py ocs tmp/camera-ocs-new --camera-only --output tmp/camera-ocs-live-new
python3 tools/opening_live_check.py cd32 tmp/camera-cd32-new --camera-only --output tmp/camera-cd32-live-new
```

`--camera-only` skips the music opening through native Escape handling, then
samples 40 pictures in the actual ship/title intro on the cached 030 model. It
requires at least three camera orientations within a single moving world tick,
checks restoration after every draw, records the exact slave hash, and stops its
owned emulator. It retains one screenshot, not an instruction trace. Accepted
native reports are `tmp/camera-{ocs,cd32}-native-final/report.json`; live reports
are `tmp/camera-ocs-live2/report.json` and `tmp/camera-cd32-live/report.json`.

### Simulator, room and running-pilot timing

```sh
. ../../common/env.sh
python3 tools/ocs_memory_build.py --public --output tmp/modal-ocs
python3 tools/reconstruct.py --variant cd32 --release --output tmp/modal-cd32
python3 tools/modal_clock_check.py ocs tmp/modal-ocs --output tmp/modal-ocs-native
python3 tools/modal_clock_check.py cd32 tmp/modal-cd32 --output tmp/modal-cd32-native
python3 tools/ocs_options_check.py tmp/modal-ocs --output tmp/modal-ocs-options
python3 tools/timing_adapter_check.py tmp/modal-cd32 --output tmp/modal-cd32-install
export FSUAE="$PWD/tmp/p13d3-debugger/fs-uae"
python3 tools/modal_live_check.py ocs tmp/modal-ocs --output tmp/modal-ocs-live
python3 tools/modal_live_check.py cd32 tmp/modal-cd32 --output tmp/modal-cd32-live
python3 tools/cinematic_live_check.py ocs tmp/modal-ocs --timing --output tmp/modal-ocs-running
python3 tools/cinematic_live_check.py cd32 tmp/modal-cd32 --timing --output tmp/modal-cd32-running
```

Use fresh output directories. The modal live gate takes native menu/input paths
through simulator, name entry, bar and barracks, retaining a handful of images
and field-clock samples. It uses the cached 030 model, 4 MiB Fast for OCS and the
normal 8 MiB CD32 profile. The running fixture redirects the initialized menu
call as described above; `--timing` samples by elapsed fields instead of expecting
the old per-render displacement. These are bounded functional timing checks,
not hardware throughput or whole-campaign acceptance.

The room regression checks four native foreground rectangle copies before
intermediate publication, 25 Hz PAL/NTSC cursor polling, exactly-once sampled
click handling, and repainting cached hover titles after each composition while
preserving transparent backgrounds. The live check
samples held-direction cursor positions between 10 Hz room ticks and captures
the bar at an intermediate publication.

```sh
. ../../common/env.sh
python3 tools/ocs_memory_build.py --public --output tmp/room-hover-ocs-v2
python3 tools/reconstruct.py --variant cd32 --release --output tmp/room-hover-cd32-v2
python3 tools/modal_clock_check.py ocs tmp/room-hover-ocs-v2 --output tmp/room-hover-ocs-check
python3 tools/modal_clock_check.py cd32 tmp/room-hover-cd32-v2 --output tmp/room-hover-cd32-check
python3 tools/ocs_options_check.py tmp/room-hover-ocs-v2 --output tmp/room-hover-ocs-options
python3 tools/timing_adapter_check.py tmp/room-hover-cd32-v2 --output tmp/room-hover-cd32-options-v2
export FSUAE="$PWD/tmp/p13d3-debugger/fs-uae"
python3 tools/modal_live_check.py ocs tmp/room-hover-ocs-v2 --output tmp/room-hover-ocs-live
python3 tools/modal_live_check.py cd32 tmp/room-hover-cd32-v2 --output tmp/room-hover-cd32-live
```

Each output must be fresh. Only small screenshots/reports are retained;
single-field capture files are removed immediately after extracting their image.

### Mission launch clocks

```sh
. ../../common/env.sh
python3 tools/ocs_memory_build.py --public --output tmp/launch-ocs
python3 tools/reconstruct.py --variant cd32 --release --output tmp/launch-cd32
python3 tools/launch_clock_check.py ocs tmp/launch-ocs --output tmp/launch-ocs-native
python3 tools/launch_clock_check.py cd32 tmp/launch-cd32 --output tmp/launch-cd32-native
python3 tools/ocs_options_check.py tmp/launch-ocs --output tmp/launch-ocs-options
python3 tools/timing_adapter_check.py tmp/launch-cd32 --output tmp/launch-cd32-options
export FSUAE="$PWD/tmp/p13d3-debugger/fs-uae"
python3 tools/launch_live_check.py ocs tmp/launch-ocs --output tmp/launch-ocs-live
python3 tools/launch_live_check.py cd32 tmp/launch-cd32 --output tmp/launch-cd32-live
```

Use fresh output directories. The bounded live fixture invokes native ship/pack
loading, exterior launch, first-mission initialization and cockpit tunnel from
the initialized menu. It temporarily uses the unused ejection entry for its
fixture and restores both that span and the menu call afterwards. This checks
scene integration, not a complete briefing/campaign traversal. It retains four
images and field/script/scale samples, stops only its owned emulator, and uses
the established cached 030 PAL observer profile. Native tests also exercise NTSC,
slow rendering, script trajectories, fractional scales, abort and exact
restoration of the exterior pose state.

For the incoming-ship flicker regression, add `--exterior-samples` to each
`launch_live_check.py` invocation. It retains five short incoming-ship screenshots
and `incoming.json`, checks monotonic bounded X/Y movement, then completes the
existing exterior/tunnel fixture. No instruction trace is retained. The native
clock check asserts both coordinates at every PAL/NTSC subfield and verifies
that compositor actor-table mutations do not escape render-only calls. This
rejects the old partial-word dividend that sent the ship offscreen between ticks.


### Mission asteroid and mine fields

```sh
. ../../common/env.sh
python3 tools/reconstruct.py --variant cd32 --release --output tmp/field-objects-cd32
python3 tools/ocs_memory_build.py --public --output tmp/field-objects-ocs
python3 tools/field_objects_check.py cd32 tmp/field-objects-cd32 --output tmp/field-objects-cd32-classes
python3 tools/field_objects_check.py ocs tmp/field-objects-ocs --output tmp/field-objects-ocs-classes
python3 tools/timing_adapter_check.py tmp/field-objects-cd32 --output tmp/field-objects-cd32-options
python3 tools/ocs_options_check.py tmp/field-objects-ocs --output tmp/field-objects-ocs-options
python3 tools/intro_clock_check.py tmp/field-objects-cd32 --output tmp/field-objects-cd32-intro.json
python3 tools/ocs_intro_check.py tmp/field-objects-ocs --output tmp/field-objects-ocs-intro
export FSUAE="$PWD/tmp/p13d3-debugger/fs-uae"
python3 tools/field_objects_live_check.py cd32 tmp/field-objects-cd32 --output tmp/field-objects-cd32-live
python3 tools/field_objects_live_check.py ocs tmp/field-objects-ocs --output tmp/field-objects-ocs-live
python3 tools/field_objects_live_check.py cd32 tmp/field-objects-cd32 --mine --output tmp/field-mines-cd32-live
```

Use fresh output directories. The live fixture invokes native mission setup for
system 1 / mission 0 (Enyo 1), then native Nav 2 loading. It records the actual
hazard field and places the player at its centre, leaving detection, allocation,
cleanup and rendering native. This is a bounded encounter fixture, not a full
mission replay. `--mine` changes only the field type to native type 23 to exercise
the shared mine constructor; it does not claim Enyo 1 contains mines. The check
requires replenishment beyond the three entry attempts and between-tick rendered
motion, retaining compact reports, data snapshots and one image. No long traces
are retained. Running the ownership check against the previous builds rejects
CD32's missing world dispatch and OCS's render-counter cleanup dependency.

### Waypoint autopilot clock

```sh
. ../../common/env.sh
python3 tools/ocs_memory_build.py --public --output tmp/autopilot-ocs
python3 tools/reconstruct.py --variant cd32 --release --output tmp/autopilot-cd32
python3 tools/autopilot_clock_check.py ocs tmp/autopilot-ocs --output tmp/autopilot-ocs-native
python3 tools/autopilot_clock_check.py cd32 tmp/autopilot-cd32 --output tmp/autopilot-cd32-native
python3 tools/ocs_options_check.py tmp/autopilot-ocs --output tmp/autopilot-ocs-options
python3 tools/timing_adapter_check.py tmp/autopilot-cd32 --output tmp/autopilot-cd32-options
export FSUAE="$PWD/tmp/p13d3-debugger/fs-uae"
python3 tools/launch_live_check.py ocs tmp/autopilot-ocs --autopilot --output tmp/autopilot-ocs-live
python3 tools/launch_live_check.py cd32 tmp/autopilot-cd32 --autopilot --output tmp/autopilot-cd32-live
```

Use fresh output directories and run the emulator checks sequentially. The
`--autopilot` option extends the existing bounded launch fixture with a native
waypoint-autopilot call. It checks the 240-field deadline, eight staged player
positions, movement between world ticks and successful native arrival return.
It retains one extra screenshot and JSON samples, deleting the single-field
instruction capture immediately. The fixture restores its temporary menu/stub
patches and stops only its owned emulator. This is not a full campaign replay.

### Ejection and helmet camera

```sh
. ../../common/env.sh
python3 tools/ocs_memory_build.py --public --output tmp/ejection-ocs-build
python3 tools/reconstruct.py --variant cd32 --release --output tmp/ejection-cd32-build
python3 tools/ejection_clock_check.py ocs tmp/ejection-ocs-build --output tmp/ejection-ocs-check
python3 tools/ejection_clock_check.py cd32 tmp/ejection-cd32-build --output tmp/ejection-cd32-check
python3 tools/ocs_options_check.py tmp/ejection-ocs-build --output tmp/ejection-ocs-options-check
python3 tools/timing_adapter_check.py tmp/ejection-cd32-build --output tmp/ejection-cd32-options-check
export FSUAE="$PWD/tmp/p13d3-debugger/fs-uae"
python3 tools/launch_live_check.py ocs tmp/ejection-ocs-build --ejection --output tmp/ejection-ocs-run
python3 tools/launch_live_check.py cd32 tmp/ejection-cd32-build --ejection --output tmp/ejection-cd32-run
```

Use fresh output directories and sequential live runs. The native check compares
script registers and effect counts against the original loop instructions,
checks PAL/NTSC cadence with skipped renders and field-counter wrap, intermediate
bitmap positions, aborts, stack/register preservation and mutated hook rejection.
OS/world/render callees are stubbed in this functional test; it is not a timing
or whole-game emulator. The tumble sampler is checked independently for stage,
slot and camera selection.

`--ejection` extends the bounded launch fixture through all three ejection stages,
including the helmet camera after tick 75. It checks field deadlines, intermediate
pilot positions and changing camera basis within a single world tick, then waits
for cleanup and return. It temporarily uses the unused ending-cinematic entry
instead of the ejection entry for its fixture, restoring both code spans on return.
Only screenshots and compact samples are retained; instruction captures are
removed after extracting the screenshot. The checks use the cached 030 PAL
profile, not a full mission/death trigger or hardware performance test.

### Carrier return and hangar landing

```sh
. ../../common/env.sh
python3 tools/ocs_memory_build.py --public --output tmp/landing-ocs-build
python3 tools/reconstruct.py --variant cd32 --release --output tmp/landing-cd32-build
python3 tools/landing_clock_check.py ocs tmp/landing-ocs-build --output tmp/landing-ocs-check
python3 tools/landing_clock_check.py cd32 tmp/landing-cd32-build --output tmp/landing-cd32-check
python3 tools/ocs_options_check.py tmp/landing-ocs-build --output tmp/landing-ocs-options-check
python3 tools/timing_adapter_check.py tmp/landing-cd32-build --output tmp/landing-cd32-options-check
export FSUAE="$PWD/tmp/p13d3-debugger/fs-uae"
python3 tools/launch_live_check.py ocs tmp/landing-ocs-build --landing --output tmp/landing-ocs-run
python3 tools/launch_live_check.py cd32 tmp/landing-cd32-build --landing --output tmp/landing-cd32-run
```

Use fresh output directories and run the live checks sequentially. Native tests
compare final script registers, scroll, local motion, actor records and sound
counts with the original loop instructions. They also check PAL/NTSC cadence,
clock wrap, slow-render cases, early skip, fractional depth and mutated hooks.
The actual native actor interpreter checks image selection across extra redraws,
including repeated images, script loops, stop commands and static actors.
Graphics/OS services are stubbed; this is a functional CPU check, not hardware
performance evidence.

`--landing` extends the existing launch fixture with native slot allocation and
carrier-model initialization, followed by the native return wrapper. The short
launch fixture does not otherwise contain a carrier. It checks both stages'
field/script progression, fractional sampling and successful cleanup/return,
recording whether the renderer produces multiple pictures within a tick. The
foreground crew member's native image selection must match its extra redraws.
It retains only compact reports and two additional screenshots. This exercises
the cinematic with native assets, not docking permission, collision detection,
mission completion or the subsequent debriefing.

## Explosion size sampling

Build separate enhanced candidates and compare their render-only size sampler
against the original effect interpreters. Use fresh output names on repeats.

```sh
. ../../common/env.sh
python3 tools/reconstruct.py --variant cd32 --release --output tmp/effect-cd32-build
python3 tools/ocs_memory_build.py --public --output tmp/effect-ocs-build
python3 tools/effect_size_check.py cd32 tmp/effect-cd32-build --output tmp/effect-cd32-check
python3 tools/effect_size_check.py ocs tmp/effect-ocs-build --output tmp/effect-ocs-check
python3 tools/modal_clock_check.py cd32 tmp/effect-cd32-build --output tmp/effect-cd32-modal
python3 tools/modal_clock_check.py ocs tmp/effect-ocs-build --output tmp/effect-ocs-modal
python3 tools/timing_adapter_check.py tmp/effect-cd32-build --output tmp/effect-cd32-options
python3 tools/ocs_options_check.py tmp/effect-ocs-build --output tmp/effect-ocs-options
```

For the bounded live check, select the corrected debugger emulator described
above through `FSUAE`, then run these sequentially:

```sh
python3 tools/modal_live_check.py cd32 tmp/effect-cd32-build --simulator-only --output tmp/effect-cd32-live
python3 tools/modal_live_check.py ocs tmp/effect-ocs-build --simulator-only --output tmp/effect-ocs-live
```

The short mode follows the actual simulator route, records 55 native/rendered
explosion-size pairs, checks intermediate growth, verifies Ready/Game Over
clock durations and reaches the name prompt. It stops its own emulator. Reports
and three screenshots stay in `tmp/`; it does not record a large instruction trace.
This is a cached 030 PAL functional check, not a throughput or hardware claim.

Accepted evidence: `tmp/explosion-{ocs,cd32}-v4` builds,
`tmp/explosion-{ocs,cd32}-final-check`, `-final-modal`, `-final-options`,
and `tmp/explosion-{ocs,cd32}-live-v4/report.json`. Both live runs pass.

## Autopilot camera sampling

Camera 12 has both sideways drift and subject tracking. The focused native test
compares against these original routines and checks full restoration. Use fresh
output directories on repeats.

```sh
. ../../common/env.sh
python3 tools/reconstruct.py --variant cd32 --release --output tmp/flyby-cd32-build
python3 tools/ocs_memory_build.py --public --output tmp/flyby-ocs-build
python3 tools/autopilot_camera_check.py cd32 tmp/flyby-cd32-build --output tmp/flyby-cd32-camera
python3 tools/autopilot_camera_check.py ocs tmp/flyby-ocs-build --output tmp/flyby-ocs-camera
python3 tools/intro_camera_check.py cd32 tmp/flyby-cd32-build --output tmp/flyby-cd32-intro
python3 tools/intro_camera_check.py ocs tmp/flyby-ocs-build --output tmp/flyby-ocs-intro
python3 tools/autopilot_clock_check.py cd32 tmp/flyby-cd32-build --output tmp/flyby-cd32-clock
python3 tools/autopilot_clock_check.py ocs tmp/flyby-ocs-build --output tmp/flyby-ocs-clock
python3 tools/timing_adapter_check.py tmp/flyby-cd32-build --output tmp/flyby-cd32-options
python3 tools/ocs_options_check.py tmp/flyby-ocs-build --output tmp/flyby-ocs-options
```

With the corrected debugger emulator selected through `FSUAE`, run sequentially:

```sh
python3 tools/launch_live_check.py cd32 tmp/flyby-cd32-build --autopilot --output tmp/flyby-cd32-live
python3 tools/launch_live_check.py ocs tmp/flyby-ocs-build --autopilot --output tmp/flyby-ocs-live
```

This retains the existing first-mission launch/arrival fixture, adding 20
projected player coordinates across fly-by ticks. It requires the tracked ship
to stay within three pixels of the view centre. This is a bounded cached-030 PAL
functional test, not a campaign replay or performance claim.

### Room title composition regression

Build and check the title replay independently of the 25 Hz input sampler:

```sh
. ../../common/env.sh
python3 tools/reconstruct.py --variant cd32 --release --output tmp/room-compose-cd32
python3 tools/ocs_memory_build.py --public --output tmp/room-compose-ocs
python3 tools/modal_clock_check.py cd32 tmp/room-compose-cd32 --output tmp/room-compose-cd32-check
python3 tools/modal_clock_check.py ocs tmp/room-compose-ocs --output tmp/room-compose-ocs-check
```

The checks require repainting on repeated compositions while preserving the
transparent-background sentinel, text context, cursor rate and pending clicks.
Use `modal_live_check.py` with either build for the bounded room navigation gate.

## Waypoint marker layering

Build both enhanced candidates and run the native ordering/visibility checks:

```sh
. ../../common/env.sh
python3 tools/reconstruct.py --variant cd32 --release --output tmp/waypoint-always-cd32
python3 tools/ocs_memory_build.py --public --output tmp/waypoint-always-ocs
python3 tools/waypoint_check.py cd32 tmp/waypoint-always-cd32 --output tmp/waypoint-always-cd32-check
python3 tools/waypoint_check.py ocs tmp/waypoint-always-ocs --output tmp/waypoint-always-ocs-check
python3 tools/timing_adapter_check.py tmp/waypoint-always-cd32 --output tmp/waypoint-always-cd32-install
python3 tools/ocs_options_check.py tmp/waypoint-always-ocs --output tmp/waypoint-always-ocs-options
```

Use fresh output names on repeat runs. `waypoint_check.py` executes native flight
and marker instructions with explicit camera/drawing boundary stubs. It checks
unpatched versus patched order with the clock active and inactive, marker
eligibility, projection arguments, scene argument forwarding, stack balance and
data isolation. `timing_adapter_check.py` covers the two CD32 Psygore's-mode
hooks and their changed-site fallback. It does not claim pixel validation.

The live overlap capture uses `flight_fixture.py --release --nav 1` served by
`tools/wc.py` with `CUSTOM2=2 CUSTOM3=1 CUSTOM4=0` and `CUSTOM5=1` or `0`. It
needs debugger memory writes, which the stock stub lacks; add a diagnostic `M`
packet handler to a `tmp/` copy of the debugger build. Write nav index
`D:3894.w` (A4−18282) = 3, the player position `D:919a` and basis
(`D:a148/b450/b750`, forward/up/right), then capture. Repeat enhanced-mode
writes at the world-update entry `E:02a8` until they survive prediction
restores.

## Swept player cannon contacts with fields

```sh
. ../../common/env.sh
python3 tools/reconstruct.py --variant cd32 --release --output tmp/field-shot-cd32
python3 tools/ocs_memory_build.py --public --output tmp/field-shot-ocs
python3 tools/field_shots_check.py cd32 tmp/field-shot-cd32 --output tmp/field-shot-cd32-check
python3 tools/field_shots_check.py ocs tmp/field-shot-ocs --output tmp/field-shot-ocs-check
python3 tools/field_objects_check.py cd32 tmp/field-shot-cd32 --output tmp/field-shot-cd32-objects
python3 tools/field_objects_check.py ocs tmp/field-shot-ocs --output tmp/field-shot-ocs-objects
python3 tools/timing_adapter_check.py tmp/field-shot-cd32 --output tmp/field-shot-cd32-install
python3 tools/ocs_options_check.py tmp/field-shot-ocs --output tmp/field-shot-ocs-options
python3 tools/projectile_spawn_check.py tmp/field-shot-cd32 --output tmp/field-shot-cd32-spawn
python3 tools/ocs_prediction_check.py tmp/field-shot-ocs --output tmp/field-shot-ocs-prediction
python3 tools/intro_shot_check.py cd32 tmp/field-shot-cd32 --output tmp/field-shot-cd32-intro
python3 tools/intro_shot_check.py ocs tmp/field-shot-ocs --output tmp/field-shot-ocs-intro
```

Choose fresh output directories on repeat runs. The new check uses native game
instructions with synthetic bounded geometry and pins RNG only to cover each
asteroid response branch. It checks swept detection, contact sampling, native
impact conversion and complete restoration after rendering. It makes no emulator
throughput claim. `field_objects_live_check.py` with either build provides the
bounded native Enyo 1 setup/field smoke check; `--mine` selects its mine fixture.
Use the shared debugger-capable emulator through `FSUAE`. That smoke check covers
field spawning and sampling, not shot impacts or uninterrupted campaign play.

## Funeral background redraw checks

```sh
. ../../common/env.sh
python3 tools/reconstruct.py --variant cd32 --release --output tmp/funeral-cd32
python3 tools/ocs_memory_build.py --public --output tmp/funeral-ocs
python3 tools/funeral_check.py cd32 tmp/funeral-cd32 --output tmp/funeral-check-cd32
python3 tools/funeral_check.py ocs tmp/funeral-ocs --output tmp/funeral-check-ocs
```

Use fresh output directories. The checks execute native ceremony/star routines,
compare whole data-hunk state with one native pass, and check intermediate star
positions including boundary respawn, PAL/NTSC and field-counter wrap. Graphics
backends are intercepted; this does not replace a visual funeral-scene check.

## Afterburner prediction continuity

Build and check both enhanced variants in fresh scratch directories:

```sh
. ../../common/env.sh
python3 tools/reconstruct.py --variant cd32 --release --output tmp/afterburn-cd32
python3 tools/ocs_memory_build.py --public --output tmp/afterburn-ocs
python3 tools/afterburn_prediction_check.py cd32 tmp/afterburn-cd32 --output tmp/afterburn-check-cd32
python3 tools/afterburn_prediction_check.py ocs tmp/afterburn-ocs --output tmp/afterburn-check-ocs
python3 tools/translation_check.py tmp/afterburn-cd32 --output tmp/afterburn-translation.json
python3 tools/translation_contract_check.py tmp/afterburn-cd32 --output tmp/afterburn-contract.json
python3 tools/timing_adapter_check.py tmp/afterburn-cd32 --output tmp/afterburn-install.json
python3 tools/ocs_options_check.py tmp/afterburn-ocs --output tmp/afterburn-options
```

The focused regression includes native control-preview isolation, intermediate
camera rotation and suppression of duplicate world rotation during normal thrust,
afterburner and braking, with script-action rejection. It must fail against the
preceding scene-reset build on afterburner steering, even though that build passes
the positional checks. Retained passing reports are
`tmp/burn-turn-final-{cd32,ocs}/report.json`.
For visual acceptance, hold Tab while turning in flight with other objects
visible, then release Tab and continue turning; verify that they and the camera
retain intermediate motion. Functional reports do not establish display throughput.

### Side-view cockpit regression

Use normal campaign entry for this check. Direct mission-call fixtures bypass
allocation lifetimes from the simulator, rooms, briefing and launch and did not
reproduce the missing cockpit.

```sh
. ../../common/env.sh
python3 tools/reconstruct.py --variant cd32 --release --output tmp/sideview-candidate
python3 tools/history_storage_check.py tmp/sideview-candidate
python3 tools/flight_render_check.py tmp/sideview-candidate \
  --output tmp/sideview-conversion.json
python3 tools/release_check.py tmp/sideview-candidate \
  --output tmp/sideview-release.json
make run SLAVE=tmp/sideview-candidate/WingCommanderCD32.Slave \
  SETUP=a1200-030 WHD_ARGS='CUSTOM5=0 CUSTOM3=1 CUSTOM4=0 CACHE'
```

Advance opening scenes with Enter, start the Vega campaign, complete the
simulator/name entry, go from the bar to the barracks and then the briefing room.
Advance briefing/launch scenes with Enter. In first-mission flight, switch
F1 → F2 → F3 → F2 and inspect the cockpit while stars/debris move. Exercise
F1–F9 as well. Repeat normal entry with `AMIGA_SETUP=a1200-030` and
`WHD_ARGS='CUSTOM5=1 DCACHE'` using `VARIANT=WingCommander` for OCS. The checked OCS
run uses 4 MiB Fast RAM. Its public build and startup check are reproducible with:

```sh
python3 tools/ocs_memory_build.py --public --output tmp/sideview-ocs-candidate
python3 tools/ocs_options_check.py tmp/sideview-ocs-candidate \
  --output tmp/sideview-ocs-options
make run VARIANT=WingCommander SLAVE=tmp/sideview-ocs-candidate/WingCommander.Slave \
  SETUP=a1200-030 WHD_ARGS='CUSTOM5=1 DCACHE' EXTRA_ARGS='--fast_memory=4096'
```

A memory-assisted check must verify that the saved cockpit allocation is
nonzero and that CD32's `flight_history` points into the slave's
`flight_history_storage`, rather than accepting a clean fallback-only picture.
The history initializer must not allocate from the fixed native game pools.

### External flight camera regression

```sh
. ../../common/env.sh
python3 tools/reconstruct.py --variant cd32 --release --output tmp/external-candidate
python3 tools/ocs_memory_build.py --public --output tmp/external-ocs-candidate
python3 tools/external_camera_check.py cd32 tmp/external-candidate \
  --output tmp/external-check
python3 tools/external_camera_check.py ocs tmp/external-ocs-candidate \
  --output tmp/external-ocs-check
python3 tools/afterburn_prediction_check.py cd32 tmp/external-candidate \
  --output tmp/external-cockpit-check
python3 tools/afterburn_prediction_check.py ocs tmp/external-ocs-candidate \
  --output tmp/external-ocs-cockpit-check
```

Use the normal campaign-entry procedure above with A1200-030 and Cache enabled.
Exercise F5 chase, F6, repeated F9 subject cycling, F7 after selecting a contact
with T, and F8 followed by Enter to launch a missile. Confirm camera and ships
move between world ticks, then return to F1/F2/F3. A screenshot alone cannot
prove smooth motion: a debugger observer can sample `timing_scene_end` before
restoration, recording the native world counter, `timing_scene_fraction`,
`external_valid` and slot-61 camera position. Require distinct positions on
successive pictures with the same world counter and valid camera history.
Use native keyboard input to reach views; do not inject mission or target state.
Retain the small samples/screenshots and stop only the isolated test process;
remove its disposable boot tree after shutdown.

## Simulator star stability after intro skip

```sh
. ../../common/env.sh
python3 tools/reconstruct.py --variant cd32 --release --output tmp/sim-stars2-cd32
python3 tools/ocs_memory_build.py --public --output tmp/sim-stars2-ocs
python3 tools/external_camera_check.py cd32 tmp/sim-stars2-cd32 --output tmp/sim-stars2-cd32-check
python3 tools/external_camera_check.py ocs tmp/sim-stars2-ocs --output tmp/sim-stars2-ocs-check
export FSUAE="$PWD/tmp/p13d3-debugger/fs-uae"
python3 tools/modal_live_check.py cd32 tmp/sim-stars2-cd32 --simulator-only --skip-turn --output tmp/sim-stars-fixed-cd32
python3 tools/modal_live_check.py ocs tmp/sim-stars2-ocs --simulator-only --skip-turn --output tmp/sim-stars-fixed-ocs
```

Use fresh output names; live runs are sequential. `--skip-turn` waits for the
native opening camera pitch, presses Return, and follows the normal menu into
the simulator. It injects no camera/world state. Twenty-four render samples in
each screen must retain the nonzero stale pitch while keeping the stationary
camera orientation and star-42 projection fixed. The existing explosion-size
sampling, four-second deadlines and native name-entry endpoint are also checked.
The run uses cached A1200-030 PAL (OCS 4 MiB Fast) and stops only its own emulator.
Reports and three screenshots are small; no full instruction traces are retained.
CPU tests cover PAL/NTSC arithmetic; this is functional evidence, not an FPS claim.

Accepted live reports: `tmp/sim-stars-fixed-{cd32,ocs}/report.json`. Both pass
48 camera samples, 55 explosion samples, and name entry. Each screen lasts
200 fields on CD32 and 202 on OCS, within the bounded four-second deadline gate. The old CD32 candidate reproduces the oscillation after the same
Return skip (`tmp/sim-stars-skip3/`); an early skip did not. Native checks are in
`tmp/sim-stars2-{cd32,ocs}-{check,intro,modal,ejection,options}/`.


## Scene-boundary prediction reset

Rebuild and run the bounded CPU regressions (outputs must be fresh directories):

```sh
. ../../common/env.sh
python3 tools/reconstruct.py --variant cd32 --release --output tmp/scene-reset-cd32
python3 tools/ocs_memory_build.py --public --output tmp/scene-reset-ocs
python3 tools/external_camera_check.py cd32 tmp/scene-reset-cd32 --output tmp/scene-reset-cd32-check2
python3 tools/external_camera_check.py ocs tmp/scene-reset-ocs --output tmp/scene-reset-ocs-check2
python3 tools/field_shots_check.py cd32 tmp/scene-reset-cd32 --output tmp/scene-reset-cd32-shots
python3 tools/field_shots_check.py ocs tmp/scene-reset-ocs --output tmp/scene-reset-ocs-shots
```

The camera regression includes a transition with staged poses and poisoned
contact certificates, exact native-data restoration, a cold first snapshot,
and resumed camera history on the second snapshot. See
[prediction state ownership](internals.md#prediction-state-at-scene-boundaries).

## Cockpit death reaction timing

Build both enhanced candidates and run the native eight-frame loop checks:

```sh
. ../../common/env.sh
python3 tools/reconstruct.py --variant cd32 --release --output tmp/death-cels-cd32
python3 tools/ocs_memory_build.py --public --output tmp/death-cels-ocs
python3 tools/death_clock_check.py cd32 tmp/death-cels-cd32 --output tmp/death-cels-check-cd32
python3 tools/death_clock_check.py ocs tmp/death-cels-ocs --output tmp/death-cels-check-ocs
python3 tools/modal_clock_check.py cd32 tmp/death-cels-cd32 --output tmp/death-cels-modal-cd32
python3 tools/modal_clock_check.py ocs tmp/death-cels-ocs --output tmp/death-cels-modal-ocs
python3 tools/timing_adapter_check.py tmp/death-cels-cd32 --output tmp/death-cels-install
python3 tools/ocs_options_check.py tmp/death-cels-ocs --output tmp/death-cels-options
```

Use fresh output directories for subsequent runs. The focused check compares the
native bitmap arguments and frame order, checks 50/60 Hz deadlines, clock wrap,
render overruns, abort and fresh entry. It models drawing and interrupts; it does
not replace visual checking of a campaign death on an emulator or real hardware.

The death reaction uses three fields per frame (24 fields for eight frames).
The funeral also updates every three fields with fractional salute motion; run
`tools/funeral_check.py` for each variant against the same fresh builds.
These cadence choices still require visual acceptance.

The running-pilot, exterior cockpit-entry and carrier-return bitmap scripts also
update every three fields, retaining fractional movement. The cockpit tunnel remains
10 Hz. Reproduce the focused native checks with fresh output directories:

```sh
. ../../common/env.sh
python3 tools/reconstruct.py --variant cd32 --release --output tmp/cels3b-cd32
python3 tools/ocs_memory_build.py --public --output tmp/cels3b-ocs
for variant in cd32 ocs; do
  for check in death_clock funeral modal_clock launch_clock landing_clock opening; do
    python3 "tools/${check}_check.py" "$variant" "tmp/cels3b-$variant" --output "tmp/cels3b-$check-$variant"
  done
done
```

PAL and NTSC both use three fields per update (50/3 and 20 updates/s).
Fireworks and bar/barracks use the same cadence; orchestra and opening zooms
retain their prior 10 Hz clock, and room cursor input remains 25 Hz. These checks cover native state
restoration and intermediate movement; live visual acceptance remains pending.

### Briefing crowd timing

```sh
. ../../common/env.sh
python3 tools/reconstruct.py --variant cd32 --release --output tmp/crowd3b-cd32
python3 tools/ocs_memory_build.py --public --output tmp/crowd3b-ocs
for variant in cd32 ocs; do
  python3 tools/briefing_clock_check.py "$variant" "tmp/crowd3b-$variant" --output "tmp/crowd3b-check-$variant"
  python3 tools/modal_clock_check.py "$variant" "tmp/crowd3b-$variant" --output "tmp/crowd3b-modal-$variant"
done
python3 tools/timing_adapter_check.py tmp/crowd3b-cd32 --output tmp/crowd3b-install
python3 tools/ocs_options_check.py tmp/crowd3b-ocs --output tmp/crowd3b-options
```

Use fresh output directories on reruns. The crowd fixture compares native frame
and actor calls against paced calls; it does not replace watching both briefing
transitions through normal campaign flow.

## Template-based release installer

`release/ReadMe` and `release/Install` adapt the shared WHDLoad Install Template.
The input fingerprints are in `tools/manifest/install-template.tsv`; template paths
are relative to `WHDLOAD`. Psygore's pinned installer supplies the WingDisk1-3
copy filters, German executable detection, Bundle:Wingco CD32 files, unpacking,
original icons, Manual and QuickDocEN/DE/FR/IT. The old QuickDocED/QuickDocIt
spelling is corrected. The combined ReadMe also supplies the OCS build's ReadMe.
Both enhanced slaves report 2.0b (19.10.2026); original reconstruction is untouched.

```sh
. ../../common/env.sh
python3 tools/reconstruct.py --variant cd32 --release --output tmp/release-docs2-cd32
python3 tools/ocs_memory_build.py --public --output tmp/release-docs2-ocs
python3 tools/release_install.py --cd32 tmp/release-docs2-cd32 --ocs tmp/release-docs2-ocs --output tmp/release-docs-package
python3 tools/release_check.py tmp/release-docs2-cd32 --output tmp/release-docs-cd32-check
python3 tools/ocs_options_check.py tmp/release-docs2-ocs --output tmp/release-docs-ocs-check
```

The staging tool checks pinned input archives, script parentheses/procedures,
ReadMe/slave version agreement and build hashes. It copies only installer assets,
documentation and the two slaves to a fresh directory, with a file-hash report;
no game data or ROM is included. The installer enables DCACHE and the appropriate
variant's enhancement tooltype, and refuses an existing destination to preserve
saves. The template's media/drive handling and icon selection remain available.
Amiga Installer execution from floppy/CD media remains an interactive release
check; structural/package checks are not evidence of that execution.

The release archive retains the pinned `WingCommander.lha` member list exactly,
including `WingCommanderHD.info` and the original installer/slave filenames.
Only `Install-WingCommander`, `ReadMe`, `WingCommanderCD32.slave` and
`WingCommanderECS.slave` are replaced. The staging report is a sibling JSON file,
not an archive member. `make dist` (`game_dist` in `game.sh`) packs the staged
output as `dist/WingCommanderEnhanced-<version>-<YYYYMMDD>.lha`, the version and
date taken from the CD32 slave's `$VER`, requires the ReadMe's
"Wing Commander Enhanced <version> (<date>)" line, re-extracts the archive and
compares every file hash and relative filename with the staging report, then
writes the `.sha256`. This combined installer is the only release archive; no
preinstalled archive is made.

## Runtime workspaces in public slaves

Build fresh public candidates and check their unstored allocation tails:

```sh
. ../../common/env.sh
python3 tools/reconstruct.py --variant cd32 --release --output tmp/runtime-buffers3-cd32
python3 tools/ocs_memory_build.py --public --output tmp/runtime-buffers3-ocs
for variant in cd32 ocs; do
  python3 tools/runtime_buffers_check.py "$variant" "tmp/runtime-buffers3-$variant" --output "tmp/runtime-buffers3-startup-$variant"
  python3 tools/field_objects_check.py "$variant" "tmp/runtime-buffers3-$variant" --output "tmp/runtime-buffers3-fields-$variant"
  python3 tools/opening_check.py "$variant" "tmp/runtime-buffers3-$variant" --output "tmp/runtime-buffers3-opening-$variant"
  python3 tools/modal_clock_check.py "$variant" "tmp/runtime-buffers3-$variant" --output "tmp/runtime-buffers3-modal-$variant"
  python3 tools/funeral_check.py "$variant" "tmp/runtime-buffers3-$variant" --output "tmp/runtime-buffers3-funeral-$variant"
  python3 tools/runtime_buffers_live_check.py "$variant" "tmp/runtime-buffers3-$variant" --output "tmp/runtime-buffers3-live-$variant"
done
python3 tools/ocs_prediction_check.py tmp/runtime-buffers3-ocs --output tmp/runtime-buffers3-prediction
python3 tools/timing_input_check.py tmp/runtime-buffers3-cd32 --output tmp/runtime-buffers3-input
python3 tools/flight_render_check.py tmp/runtime-buffers3-cd32 --output tmp/runtime-buffers3-conversion
python3 tools/release_check.py tmp/runtime-buffers3-cd32 --output tmp/runtime-buffers3-release
python3 tools/ocs_options_check.py tmp/runtime-buffers3-ocs --output tmp/runtime-buffers3-options
```

Outputs must be fresh; change the suffix when repeating. Live checks use isolated
project-owned runs and delete their temporary memory dumps. They validate actual
WHDLoad allocation and startup, not full gameplay. `runtime_buffers.load` expands
the hunk allocation for native test fixtures; reading only file bytes omits the
workspace. The final `.Slave` files contain no workspace bytes, while the ignored
flat assembler outputs retain the complete memory image for analysis.

## Intro death-explosion order

Build both public variants and run the native sort/tie regression:

```sh
. ../../common/env.sh
python3 tools/reconstruct.py --variant cd32 --release --output tmp/intro-order-cd32
python3 tools/ocs_memory_build.py --public --output tmp/intro-order-ocs
for variant in cd32 ocs; do
  python3 tools/effect_order_check.py "$variant" "tmp/intro-order-$variant" --output "tmp/intro-order-check-$variant"
  python3 tools/intro_shot_check.py "$variant" "tmp/intro-order-$variant" --output "tmp/intro-order-shots-$variant"
done
python3 tools/release_check.py tmp/intro-order-cd32 --output tmp/intro-order-options-cd32
python3 tools/ocs_options_check.py tmp/intro-order-ocs --output tmp/intro-order-options-ocs
```

The bounded live check boots an isolated cached A1200-030, lets the opening play
naturally and samples 40 pictures around the first death explosion. It checks
that every visible equal-depth ship/death-effect pair draws in the right order,
saves small H1 snapshots/screenshots and deletes each single-field trace after
extracting its picture. It stops only its own emulator. Run variants serially:

```sh
python3 tools/effect_order_live_check.py cd32 tmp/intro-order-cd32 --output tmp/intro-order-live-cd32
python3 tools/effect_order_live_check.py ocs tmp/intro-order-ocs --output tmp/intro-order-live-ocs
```

For retained pre-fix evidence, add `--capture tmp/intro-blink-explosion` to the
CD32 native regression with a fresh output directory. That capture reproduced
11 reversed ties across 40 pictures; the model checks do not require it.
The older `ocs_intro_check.py` currently has a stale slot-61 motion expectation
for native camera modes 0/8; it fails identically on the pre-fix runtime-buffer
build and this candidate. It is not counted as a passing gate for this fix.

Cached A1200-030 live captures passed in both variants: 11 CD32 and 20 OCS
visible depth ties, with screenshots confirming the explosion overlays the ship.
Final OCS packaging keeps the pass in the intro-enabled build only; its build
and checks use the `tmp/intro-order-final-*` prefix. Historical `--clock` builds
still build without intro symbols.

## Smooth player steering precision

Build both public candidates and run the bounded functional regressions:

```sh
. ../../common/env.sh
python3 tools/reconstruct.py --variant cd32 --release --output tmp/steering-fix-cd32
python3 tools/ocs_memory_build.py --public --output tmp/steering-fix-ocs
for variant in cd32 ocs; do
  python3 tools/player_basis_check.py "$variant" "tmp/steering-fix-$variant" --output "tmp/steering-check-$variant"
  python3 tools/afterburn_prediction_check.py "$variant" "tmp/steering-fix-$variant" --output "tmp/steering-afterburn-$variant"
done
python3 tools/timing_player_check.py tmp/steering-fix-cd32 --output tmp/steering-player-cd32
python3 tools/release_check.py tmp/steering-fix-cd32 --output tmp/steering-release-cd32
python3 tools/ocs_options_check.py tmp/steering-fix-ocs --output tmp/steering-options-ocs
```

Use fresh output directories on repeats. The precision check uses actual assembled
helpers and native routines, with an independent floating-point mixed-axis oracle
and an original small-rotation negative control. It checks zero vertical-axis drift
during yaw, pose replacement, scene/inactive reset and register preservation.
The older player fraction check now compares against real-number rotations;
bit equality with the native low-precision result would preserve the bug.
No long emulator trace or new capture is required for these checks.

Interactive acceptance: pitch down, release and coast for a second, then alternate
Left/Right around a star near the reticle. The star should not steadily climb as
horizontal steering continues. Repeat after scene transitions and with afterburner.
This interactive confirmation remains separate from the passing native CPU checks.

### Flight-boundary steering reset regression

From the project root, build fresh candidates and run the focused CPU checks:

```sh
. ../../common/env.sh
python3 tools/reconstruct.py --variant cd32 --release --output tmp/flight-reset-cd32
python3 tools/ocs_memory_build.py --public --output tmp/flight-reset-ocs
python3 tools/player_reset_check.py tmp/flight-reset-cd32 --variant cd32 --output tmp/flight-reset-check-cd32
python3 tools/player_reset_check.py tmp/flight-reset-ocs --variant ocs --output tmp/flight-reset-check-ocs
python3 tools/timing_player_check.py tmp/flight-reset-cd32 --output tmp/flight-reset-preview-check
```

Use new output names for repeated runs. Interactive acceptance: hold Right until
simulator game over, release it, then follow the normal bar/briefing path into
the first mission. With no steering input the ship must not initially turn.
A direction held in the new flight must still respond normally.
