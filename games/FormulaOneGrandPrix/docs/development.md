# Development setup

AmigaXDev supplies the shared tools and documentation. Its `make setup` installs
`~/.local` and `~/.local/share/amiga`. Source `amiga/env.sh` to use that environment;
`AMIGA_ENV` can select a different shared environment file. Shared tool, ROM and
WHDLoad paths are supplied by that file, not by copies from other projects.
The launcher uses `KICKSTART`, `KICK13`, `RTB`, `WORKBENCH_ADF`, `WHDLOAD_BINARY`,
`FSUAE_COMMON` and, for the gdb server, `FSUAE_ARM`.

`make check` verifies the retained archives against `manifest/SHA256SUMS`.
The hashes pin the downloaded inputs; they are not independently authenticated
publisher checksums. `manifest/inputs.json` records their source URLs.

Local layout:

- `tmp/archives/`: original installer and complete four-disk install archives.
- `tmp/installer/`: pristine installer extraction.
- `tmp/game/`: pristine full-install extraction.
- `tmp/extracted-files.sha256`: local extraction inventory.

To recreate the extractions, download the named archives from their manifest URLs
into `tmp/archives/`, run `make check`, then extract the installer into an empty
`tmp/installer/` and the complete install into an empty `tmp/game/` using `lha x`.
Do not merge into modified game data.

## Running

`amiga/run.sh` copies `tmp/game/FormulaOneGrandPrix4Disk` to the disposable
`amiga/.run/dh1`, boots Kickstart 3.1 with the Workbench 2.04 floppy and runs
`WHDLoad FormulaOneGrandPrix4Disk.Slave PRELOAD SPLASHDELAY=0 CONFIGDELAY=0 NOREQ`. The default machine
is the A500-equivalent: 68000, 512 KB chip, 1.5 MB slow, no fast RAM. `AMIGA_SETUP`,
`CHIP_KB`/`SLOW_KB`/`FAST_KB`, `WHD_ARGS` (for example `CUSTOM1=1`), `SLAVE`, `DEBUG`,
`WARP` and the other shared launcher variables apply.

`python3 tools/f1gp.py serve` boots with `DEBUG=1` on the native FS-UAE (`FSUAE_ARM`
unless `FSUAE` is set) and serves the shared `amigaxdev.gdbserve` commands
(`shot PNG`, `wait S`, `gdb TEXT`, `profile N BIN`, `quit`). Drive input with
`gdb monitor mouse DX DY`, `gdb monitor input JOY1_FIRE_BUTTON 1|0`,
`gdb monitor key RAW 1|0` and `gdb monitor fields N` while stopped. One mouse count
moves the game's pointer one screenshot pixel in both axes.

To reach gameplay without manual input:

```sh
. amiga/env.sh
WARP=1 DETERMINISTIC=1 JOY0=none JOY1=none python3 tools/f1gp.py serve > amiga/.run/serve.log 2>&1 &
python3 tools/f1gp.py quickrace tmp/route.jsonl   # stops at the first race field
python3 tools/f1gp.py shot "$PWD/tmp/race.png"
python3 tools/f1gp.py quit
```

`quickrace` waits for each screen (language, protection, startup, track, race) by
sampling fixed screenshot pixels every 25 fields, presses fire while waiting for the
first one (skipping the intro), homes the pointer to its top-left clamp before each
click, and fails after 6000 fields on any screen. The optional file logs every input
command and reply. `ROUTE_SHOTS=DIR` in the server's environment saves each polled
screenshot, which is how to re-derive a signature if a screen stops matching.
It works with any `AMIGA_SETUP` and with or without `CUSTOM1=1`. `tools/f1gp.py` sets
`BOOT_BREAK=0xf800d6` (the second instruction of the Kickstart 3.1 reset code), so the
server holds the CPU from reset until a command advances it; `cont` resumes free running.

## Profiling the race

`tools/race_profile.py` captures cycle-exact Barto traces of one race phase and reduces
them, through the same server (start it with `AMIGA_SETUP=a1200-fast` and the options
above):

```sh
python3 tools/f1gp.py raceprofile green tmp/prof/a1200-green 500   # or tow, follow
python3 tools/race_profile.py report tmp/prof/a1200-green          # also writes report.txt
```

The server holds the CPU from reset (`BOOT_BREAK`), and the route only advances it through
gdb commands, so a given command sequence repeats exactly: two tow captures gave identical
per-PC cycles, frame events and per-field screenshots. Different sequences diverge, even
over the same span (`monitor fields N` and `monitor profile N` do not leave identical
states), so anchor field numbers are per-command counts for that sequence, and windows
from different phases need not show one continuous race. Consecutive `monitor profile`
chunks are contiguous (the harness's gapless-profile).

Each capture runs `quickrace` and then finds its anchor field exactly: `green` is the first
field with green start lights, `tow` the first non-cockpit field after it (the retired car
being pushed away, "Viewing Nigel Mansell") and `follow` the first field with the green
"Viewing" banner after that ("Viewing Riccardo Patrese"). It runs a lead
without polling (`LEADS`, calibrated on `a1200-fast`; `RACE_LEADS=0,0,0` polls throughout on
other machines), then checks a screenshot every field, and fails if the lead overshoots.
The window is the given number of fields after the anchor field, traced 50 fields at a time
(about 7.5 MB per field), reduced and deleted. The directory keeps `profile.pkl.gz`, the
chip and fast RAM images, anchor, first and last screenshots and `meta.json`; nothing in it
may be committed.

`RACE_KEEP_TRACES=1` (server environment) keeps the raw chunks as `DIR/trace-NNNN.bin`
(about 7.5 MB per field) for `tools/dma_census.py DIR`, which counts chip-bus slots per
field: the CPU's instruction fetches, data reads and writes by region (hunk 2 by 4 KB
page), every other DMA channel by region, and the display registers. Without fast RAM
the capture also saves `slow.bin` (hunk 0 then lives in slow RAM at `$C00000`), and the
report reads it.

The reducer (`StackReduction`) follows one call stack per CPU stack, because the game's
task and its interrupts run on different stacks, and follows JSR/BSR in fast RAM. The
report locates hunks 0 and 2 and the Kickstart 1.3 image in the saved RAM and labels PCs
`h0+offset`, `h2+offset` or `kick+offset`. It gives cycle accounting, DMA slot shares,
per-frame time and work from the frame pacer (below), self time per function (each PC
charged to the nearest preceding call target), inclusive time per call target and the
call tree. Interrupts are charged to their own roots. Self time per "function" is only
as good as that nearest-call-target heuristic: check a large entry with
`python3 -m amigaxdev.disasm disd DIR/fast.bin 0x200000 <h0 base> START END`.

## Race clock across machines

```sh
AMIGA_SETUP=a500-1.5m WARP=1 DETERMINISTIC=1 JOY0=none JOY1=none python3 tools/f1gp.py serve > amiga/.run/serve.log 2>&1 &
python3 tools/f1gp.py raceclock tmp/clock/a500-1.5m
python3 tools/f1gp.py quit
```

`raceclock` runs `quickrace` and then the race to the results screen in 200-field steps,
reading the pacer's words in hunk 0 (located in RAM by its minimum-field tables and the
relocated instruction after them) and saving a screenshot per step. It opens Race
Finishing Times and saves `times.png`; `samples.json` has the frame count per step. Its
RAM regions per `AMIGA_SETUP` are listed in the tool. The 68030 cycle-exact preset timed
out in the route on a loaded host; it has no result yet.

Field counts need the harness's `exact-fields` and `gapless-profile` (`quickrace` checks
`monitor harness`): after a `fields` or `profile` stop, `monitor fields N` runs exactly N
fields and `monitor profile N` traces the next N with no gap. Older builds ran N + 1 and
left one field untraced before each profile, so counts from them are not comparable.

## Reconstructing the original slave (B1)

After `make check`, the retained install archive was extracted into a separate scratch
folder and its game and slave compared with `tmp/game`. Their verified standalone
hashes are in `manifest/game-inputs.json`. Do not update those pins to accept changed data.

```sh
. amiga/env.sh
python3 tools/slave_inputs.py
"$VASM" -m68000 -no-opt -devpac -Fbin -o tmp/slave/reassembled.bin tmp/slave/original.s
cmp tmp/slave/original.bin tmp/slave/reassembled.bin
```

The comparison covers the entire loaded slave, including the separated old KickEmu.
Both generated assembly and binaries contain derived bytes and stay in ignored `tmp/`.

## Building the reconstructed loader (B2)

`make slave` invokes `whdload/build.sh` under bash 3.2 and writes `tmp/build/F1GP.Slave`
and its listing. `OUT="tmp/build spaced" make slave` is supported. The build verifies
the assembler, NDK trees, WHDLoad headers and shared KickEmu against
`manifest/slave-toolchain.json`, then verifies the original game and slave before
extracting the names payload. Tree hashes cover sorted relative filenames, a NUL,
and each file's raw SHA-256 digest; no machine paths are stored in the manifest.

`NDK_ASM` defaults to `$AMIGA_SHARE/ndk/Include_I`; the installed assembly LVO headers
use `_lib.i` names, so the build generates four include-name adapters under `tmp/slave`.
The normal `NDK` and shared environment overrides remain supported. To deliberately
repin a reviewed toolchain update, source `amiga/env.sh`, set/export `NDK_ASM`, and run
`python3 tools/slave_toolchain.py --record`. A differing input is otherwise a build error.

Run with `SLAVE=tmp/build/F1GP.Slave` in the server environment. Do not interpret a
successful boot as B3 acceptance. All slave builds, listings and captures stay in `tmp/`.

## Slave acceptance captures (B3)

The retained B3 set belongs to the 6100-byte baseline. B4 changes the build and launcher;
`slave_accept.py` correctly rejects that old set against the current binary. The commands
below are the recipe for a fresh full B3 set, not a request to overwrite accepted evidence.
B4 has its own gate below; its shorter captures do not replace the B3 paired windows.

B3 uses the modern shared KickEmu with `IOCACHE = 10000`. Build normally with
`make slave`; local device-description adaptations are diagnostic rejects, not inputs
to that build. Rejected captures must not be promoted into the baseline.

```sh
. amiga/env.sh
make slave
python3 tools/slave_compare.py capture baseline green
python3 tools/slave_compare.py capture repeat green
python3 tools/slave_compare.py capture baseline tow
python3 tools/slave_compare.py capture repeat tow
python3 tools/slave_compare.py capture baseline follow
python3 tools/slave_compare.py capture repeat follow
python3 tools/slave_quit.py
python3 tools/slave_accept.py
```

Each capture starts a fresh project server, waits for its new `serving on` message,
runs the screen-anchored route/window and quits through that server. Stale project
sockets are removed before launch. The normal project launcher owns process cleanup;
no name-wide termination is used. The desktop sandbox may require permission for the
emulator/debugger's local connection. The default window is 500 fields. Capture names
are immutable: move a rejected local attempt aside explicitly before retrying.

The comparison requires all three pairs to contain 500 identical screenshot digests,
identical routes/anchors and actual hunk bases, matching slave/emulator/input/tool
hashes, and passing captured-memory loader checks. Missing or short captures fail.
`slave_compare.py compare` writes `tmp/b3/comparison.json` and returns nonzero until
every window passes. `slave_accept.py` additionally requires one coherent capture set,
the current built slave and a successful quit probe; its combined B3 report is
`tmp/b3/acceptance.json`.
The names check uses the verified original green capture as its independent oracle;
retain `tmp/b3/original/green`, or recreate it with `capture original green`.

The driver uses `RACE_LEADS=0,0,400` for every case: green and tow are polled from their
preceding anchors; follow retains the 400-field separation from tow and rejects an
overshoot. This comparison establishes repeatability of the new baseline. It does not
prove original-slave equivalence, other CPU behavior or the two unavailable game variants.

Original-reference diagnostics remain available as `capture original|rebuilt|padded`
and `compare-original`; their report is `tmp/b3/original-comparison.json`. Equal slave
file sizes never establish equal game allocations. The original comparison is not the
modern-baseline acceptance command.

`tools/slave_quit.py` performs the separate real-input quit check with `CUSTOM1=1`.
For a manual check, set `VERIFY_EXIT=1` in the server environment,
enter the race and send raw key `$59` (F10) through the native harness. The launcher
records WHDLoad's return as `OK` or `FAIL` in `amiga/.run/dh0/whdload-exit.txt` after it
returns. A missing marker is not a pass. Save that evidence in ignored `tmp/b3/` before
another launch replaces the disposable hard drive. Check the returned screen as well,
then quit the project server normally.

## Other live modes and call counts (A2)

From a fresh deterministic server using the B3 slave, use `practice LOG` or
`qualifying LOG` in place of `quickrace LOG`. Both recognize the main menu,
circuit selector and track; qualifying also recognizes the Grand Prix menu.
`startup LOG` stops before selecting either startup option. `menuclick X Y` and
`tap RAW [FIELDS]` expose the same native input helpers for modal transitions.

At a screen-anchored cockpit stop, dump fast RAM with the debugger, then capture:

```sh
python3 tools/f1gp.py gdb 'dump binary memory tmp/a2/fast.bin 0x200000 0xa00000'
python3 tools/f1gp.py profile 50 "$PWD/tmp/a2/session.bin"
python3 tools/loop_profile.py tmp/a2/session.bin tmp/a2/fast.bin
```

The raw trace, same-run RAM dump, JSON counts and endpoint screenshots stay in `tmp/`.
The reducer locates actual code hunks; it does not borrow addresses from another build.
It verifies game input pins and records capture hashes. Save the route log, setup and
slave hash alongside each fresh-boot capture. The example RAM range is for the 8 MB
fast-RAM preset; it is a debugger capture range, not a documented game-code address.

Replay: in qualifying, press Space (`tap 40`), advance 10 fields to consume its release,
then R (`tap 13`); confirm the red R before profiling. Return: leave replay, press Escape
(`tap 45`), wait for **Qualifying Frozen**, then `menuclick 395 214` (Return to Cockpit).
Start contiguous profiles immediately after that click; the redraw occurs during the
transition, before the stable cockpit. Six 50-field chunks captured it exactly once.
Do not start the trace at a breakpoint on the draw: the profiler begins at a field
boundary and can omit the call at the breakpoint. Use screen-anchored transitions.

## Build variants and disabled-hook gate (B4)

```sh
make slave                 # release -> tmp/build
make slave-developer       # DEVELOPER=1 -> tmp/build-developer
make slave-verify          # DEVELOPER=1 VERIFY=1 -> tmp/build-verify
make slave-verify OUT='tmp/verify with spaces'
make slave-clean OUT='tmp/verify with spaces'
. amiga/env.sh
python3 tools/slave_gate.py
python3 tools/slave_gate.py --check
make check-disabled CAPTURE=tmp/b4/verify-off
make test-disabled
```

Each build writes the slave, listing and `build.json` into its selected `tmp/` directory.
`OUT` accepts relative or absolute paths, including spaces; paths outside `tmp/` fail.
Cleanup removes only those three generated files. The normal target excludes VERIFY
code, even if a VERIFY build previously occupied that output directory. Never release
an artifact based only on its filename; inspect the build manifest and rebuild normally.

`slave_gate.py` requires fresh capture directories under `tmp/b4`; it refuses to overwrite
prior evidence. Move a rejected attempt aside explicitly before retrying. It starts and
stops only project servers, verifies input/source/build hashes, reaches Quick Race and
captures 50 fields for each of release-off, developer-off, VERIFY-off and VERIFY-on.
Each case also checks the B3 loader patches/names and real F10 return. The enabled case
uses only `CUSTOM5=1`, a VERIFY relay to the original pacer. `--check` audits retained
captures against current binaries, runs adversarial checker tests and writes the combined
`acceptance.json`; it does not launch an emulator. Missing or stale evidence is a failure.
The original B3 names oracle in `tmp/b3/original/green` is still required.

A new optional hook must carry a comment immediately before the patch, for example
`PERF_RANGE h0:3c9d2 6 custom=5 bit=0 variant=582992`, inside the matching `PL_IFC5X 0`
gate, with its bit declared in `slv_config`. Do not put new optional patches inside the
mandatory baseline delimiters. The current checker deliberately supports only the one
present form (six-byte hunk-0 `PL_PS`); extend its audit and negative tests together when
adding another patch form, hunk or source file. Unsupported forms fail closed. Original
bytes are read from the verified local game, never copied into tracked fixtures.

`CONFIGDELAY=0` is needed alongside `SPLASHDELAY=0` for automated boots now that options
are exposed. Otherwise the route's repeated fire presses can keep WHDLoad's configuration
window open. This is a launcher setting; the slave's ordinary interactive options remain
available when launched elsewhere.

## State-map evidence (A4)

The native record/view map is in [internals](internals.md#state-map-a4). Reproduce its
static-path and retained-snapshot checks with Capstone 5 available:

```sh
python3 tools/state_map.py tmp/a3 tmp/a4/state-map.json
```

This verifies `manifest/game-inputs.json`, reconstructs relocations directly from the
original executable, decodes the selected pose/camera paths and checks all 50
camera-return snapshots from each of A3's five captures. It checks hashes, sizes,
source/target selection and camera publication relationships. Output starts INCOMPLETE
and becomes PASS only when all checks succeed. Derived disassembly and snapshot details
stay in `tmp/`; no emulator is launched and no current runtime pin is changed.

The report retains each capture's original emulator/slave identities. Its dynamic
coverage is cockpit and rear chase (including another selected car), plus cockpit replay;
TV/front chase and track-relative pose conversion are static findings. Do not treat this
as an all-view gameplay test or an extrapolation/restore check. Those belong to D/G.

## Call-boundary state and drawing ownership (A3)

`state_diff.py` is exposed as the server command `statediff live|replay DIR [FRAMES]`.
It currently requires `a1200-fast` (8 MB fast RAM), an explicit `SLAVE`, and a stopped
native-route game. Use the B4 release slave with all five CUSTOM values explicitly zero,
`WARP=1 DETERMINISTIC=1 JOY0=none JOY1=none`. Wait for the **new** server's `serving on`
message; reject an active socket rather than connecting to a different run. All capture
names must be new directories under `tmp/`.

From a fresh server, one race sample is:

```sh
# Set RACE_LEADS=0,0,400 in the server environment for the accepted A3 route.
python3 tools/f1gp.py raceprofile green tmp/a3/green-anchor 1
python3 tools/f1gp.py statediff live tmp/a3/green 50
python3 tools/f1gp.py quit
python3 tools/state_diff.py tmp/a3/green
```

Repeat from fresh boots with `tow` and `follow` replacing `green`. The one-field profile
is for the screen anchor and layout, not the 50-frame write audit. For the garage and
replay samples, from another fresh server:

```sh
python3 tools/f1gp.py qualifying tmp/a3/qualifying-route.jsonl
python3 tools/f1gp.py statediff live tmp/a3/qualifying 50
python3 tools/f1gp.py gdb 'monitor fields 2000'  # populate replay history in this session
python3 tools/f1gp.py tap 40
python3 tools/f1gp.py gdb 'monitor fields 10'
python3 tools/f1gp.py tap 13
python3 tools/f1gp.py shot "$PWD/tmp/a3/replay.png"  # confirm the red R
python3 tools/f1gp.py statediff replay tmp/a3/replay 50
python3 tools/f1gp.py quit
```

The collector discovers the four hunks through the loaded code and DOS segment chain,
verifies bitmap bounds, stops at the selected loop head, and snapshots before each actual
call and at its return. It uses **one breakpoint at a time**: this debugger rejects a
large simultaneous breakpoint set. Non-call instructions between sites are single-stepped.
It fails if a call does not return, the loop exits, or a frame does not complete. Pausing
or exiting during capture is therefore not a valid steady-loop sample. Emulated time is
halted during the reads; host capture duration is not a performance measurement.

The four complete hunks are concatenated into each `.bin.gz`, with paired events and
SHA-256 hashes in `events.jsonl`. Keeping all h0/h2 bytes captures interleaved data;
keeping all h3 bytes permits auditing screen exclusions. `diff.json` reports every
call, including zero-count conditional sites, changed intervals, screen counts and
reviewed ownership classes from `state_classes.py`. It validates captured layout, screen
exclusions, hashes, pairing, frame coverage and call targets. Failed/partial captures
cannot pass. A malformed hexadecimal memory reply may retry the same halted read up to
three times; continue, input and stepping commands are never retried implicitly.

`state_audit.py` and `state_access.py` require the available Python **Capstone 5** package.
The former walks the pinned executable and enumerates renderer stores, including reviewed
indirect dispatches; the latter uses instruction/register traces to resolve memory reads
and writes and identify potential cross-call consumers. It separates interrupt stacks,
not merely the CCR (KickEmu virtualizes SR). An unresolved decoder/address or an unclassified
store is a failure. Neither a byte intersection nor a missing net delta proves dependence
or independence: use the writer/consumer discussion in internals.

```sh
python3 tools/state_audit.py tmp/a3/static-audit.json
python3 tools/state_access.py tmp/raw/green/trace-0000.bin tmp/raw/green/fast.bin tmp/a3/green-access.json
python3 tools/state_access.py tmp/raw/tow/trace-0000.bin tmp/raw/tow/fast.bin tmp/a3/tow-access.json
python3 tools/state_access.py tmp/raw/follow/trace-0000.bin tmp/raw/follow/fast.bin tmp/a3/follow-access.json
python3 tools/state_access.py tmp/a2/route-practice/trace.bin tmp/a2/route-practice/fast.bin tmp/a3/practice-access.json
python3 tools/state_access.py tmp/a2/replay.bin tmp/a2/fast.bin tmp/a3/replay-access.json
python3 tools/test_state_diff.py tmp/a3/probe3
python3 tools/state_gate.py tmp/a3
```

The retained one-frame `probe3` is the successful collector smoke test; recreate it with
`statediff live tmp/a3/probe3 1` in a separate native-route session. Negative tests copy
its evidence into a temporary directory and leave originals unchanged. They reject failed,
short, unpaired, corrupt, missing-frame and forged-screen evidence, plus an injected change
outside the renderer's classified ranges.

For the combined gate, `tmp/a3/access-sources.json` maps `green`, `tow`, `follow`,
`practice`, `replay` to `[trace_path, fast_dump_path]` arrays (paths under project `tmp/`,
as in the commands). The gate rechecks all five 50-frame captures, hashes the auxiliary
trace inputs, requires every observed renderer store PC to appear in the static inventory,
runs the negative checks and writes `acceptance.json`. It starts as `INCOMPLETE`, never
retaining an old PASS after a failed rerun. It does not start an emulator. The auxiliary
traces are explicitly separate from the breakpoint captures; retain their same-run dumps.

## Cache and machine-matrix pilot (B5/A7)

B5 has not passed. See [current status](open-work.md). The runner needs the pinned
emulator with AmigaXDev's TOOL1 fix: older builds hang at boot on every 030/040/060 cell
under `DETERMINISTIC=1` ([cause](internals.md#startup-failures-cause-and-fix-68030-68040)).
The commands below are
capture recipes, not evidence that the matrix has passed. The cache option is
`CUSTOM2=1`. Build with the existing release/developer/VERIFY targets. VERIFY uses
API 18 solely for `resload_Log`; enable `FileLog` (a switch in the pinned runtime).
The cache register is logged after the policy request, before loading the intro/game.
It is a point observation, not proof of every later memory page's cacheability.

```sh
. amiga/env.sh
make check slave slave-developer slave-verify
python3 tools/machine_matrix.py 020 on clock tmp/b5/new-020-on-clock
python3 tools/machine_matrix.py 020 off green tmp/a7/020-off-green 100
```

The serial runner accepts machines `a500`, `a1200`, `020`, `030`, `030-mmu`, `040`,
`040-mmu`, `060`, `060-mmu`; cache policy `on|off`; and `clock|green|tow|follow|all`.
It defaults to the VERIFY slave; `MATRIX_SLAVE` selects another built variant.
It checks the game, runtime and build hashes before boot, rejects active sockets and
existing output directories, removes stale sockets, and waits for the new server's
`serving on` message. Evidence includes runtime/build/tool hashes, options, screenshots,
logs, clean-quit status and failure text. `CAPTURED` means capture succeeded, **not** gate
acceptance. The runner does not yet implement an A7/A8 acceptance report.

The 030 non-MMU timing cell explicitly removes the emulator MMU model as well as passing
WHDLoad `NOMMU`: `--cpu=68030 --uae_mmu_model=0` (either order; `68EC030` also works,
without an FPU). The pinned shared launcher refuses unknown CPU names such as
`68030-NOMMU` before starting the emulator (AmigaXDev TOOL2). `f1gp.py serve` then shows
only a traceback; run `amiga/run.sh` with the same variables to see the message. The
runner also rejects effective-CPU/MMU mismatches before advancing the route. The 040/060 timing cells explicitly select the non-MMU, cycle-exact cores.
MMU cells are functional tests, not fixed-clock speed claims. Check effective emulator
settings in the retained debug log before using measurements. 040/060 results describe the emulator model, not real accelerator timing.

Local input field commands now allow 1800 seconds by default (`F1GP_FIELD_TIMEOUT`
overrides it); this does not repair an emulator semaphore wait. Screenshot collection
requires a new one-field trace and fails after a debugger disconnection instead of
reusing a stale image. The pinned shared `shot`/`profile` commands do the same
(AmigaXDev TOOL3). `raceclock` retains the route, actual four-hunk layout and partial
samples with `INCOMPLETE` status; only reaching results and the finishing-times screen
sets `COMPLETE`. Read `capture.json` as well: a complete clock capture with failed quit
is not an accepted run.

All uncalibrated profiles request `RACE_LEADS=0,0,0`. The follow anchor now requires
an actual change in the yellow driver name inside the Viewing banner. It records the tow
name and rejects that same banner, scene motion below it, and incomplete banners. This
predicate passes tests against retained tow/follow sets and a fresh 030 zero-lead
repeat. Existing B3/A3 calibrated
evidence remains tied to its original capture tools.

`race_profile.py` uses the shared checked profile writer, retains all four hunk bases and
marks complete car-update and drawing calls as well as the pacer. Run:

```sh
python3 tools/test_profile_anchor.py tmp/raw/follow tmp/b3/baseline/follow tmp/prof/a1200-follow
python3 tools/matrix_report.py tmp/a7/CAPTURE
```

The report saves `metrics.json`: complete-frame fps/work, complete-call drawing/tick ms
(including interrupts within each call), and chip slots per field by DMA type. Partial
calls at the window edges are excluded. The game-clock ratio uses the captured Q32.16
increment at `h0+3A7DE`, rather than rounding it to 128 ms. The separate native increment
at `h0+3A7E4` is also reported. These are emulator figures; 040/060 cycle-exact timing
models instruction throughput plus chip accesses, not real accelerator clock rates.

Whole-race repeat comparison:

```sh
python3 tools/matrix_compare.py tmp/b5-final/030-on-clock-d tmp/b5-final/030-on-clock-e
```

The comparator requires completed captures, clean quit, matching configuration/build/runtime
and capture-dependency hashes, all clock samples (or profile anchors/digests), actual hunk
layout and every retained PNG. It does not mask pointer pixels. The matrix runner explicitly
disables automatic mouse switching as well as setting both joystick sources to `none`.

For a fully uncached control the runner appends `NoCache`, including MMU cells. All
CUSTOM bits zero alone preserve the original policy, which can cache Fast RAM under
an MMU. `matrix_compare.py` requires the override for off arms and audits CACR.
Use `all` for green/tow/follow in one boot with zero leads; reduce each child window
with `matrix_report.py`. Repeat comparisons include all child profiles and PNGs.

For A8 use one current VERIFY build for all four arms. For a new 030 set:

```sh
export RACE_ANCHOR=start-state MATRIX_SKIP_INTRO=1 MATRIX_CUSTOM4=1
for repeat in a b; do
  MATRIX_CUSTOM3=0 MATRIX_INSTANT_BLITTER=0 python3 tools/machine_matrix.py 030 on green "tmp/a8-new/030-control-$repeat" 100
  MATRIX_CUSTOM3=1 MATRIX_INSTANT_BLITTER=0 python3 tools/machine_matrix.py 030 on green "tmp/a8-new/030-no-wait-$repeat" 100
  MATRIX_CUSTOM3=3 MATRIX_INSTANT_BLITTER=0 python3 tools/machine_matrix.py 030 on green "tmp/a8-new/030-no-fill-$repeat" 100
  MATRIX_CUSTOM3=1 MATRIX_INSTANT_BLITTER=1 python3 tools/machine_matrix.py 030 on green "tmp/a8-new/030-instant-$repeat" 100
done
python3 tools/ceiling_report.py tmp/a8-new 030
python3 tools/test_disabled.py tmp/b4/prefs-verify-off tmp/b4/prefs-verify-on
```

`MATRIX_CUSTOM4=1` selects the developer-only startup control: `SetPrefs` gets a false
notification argument. Use it for **every** arm of a 030 comparison, including the normal
pacer control. The default zero preserves the original argument. Release contains no
C4 option or conditional code. The runner rejects this option outside developer/VERIFY
green start-state captures; it is not a player mode or simulation change.

Each arm needs a fresh repeat, effective-config review, original-versus-enabled hook
byte checks and clean quit. `start-state` selects the native start transition, removes
the breakpoint, and advances to a complete field before profiling. It accepts only
the green ceiling window. The instant arm requests only `immediate_blits=true`, retaining the control
wait policy. Inspect `debug.uae` rather than trusting the requested options; the ceiling
audit compares `waiting_blits` across all arms.

`matrix_report.py` distinguishes `MEASURED` from `UNAVAILABLE`: exact repeated empty
CPU records are not timings. DMA counts can still be valid. The current selected
040/060 timing cores expose this limitation; do not substitute zero for missing values.

For a common-layout A8 comparison set `MATRIX_SKIP_INTRO=1` on **every** arm, including
the control. This maps to the existing `CUSTOM1=1`; it removes the observed 020 frontend allocation
difference. On 030 also use `MATRIX_CUSTOM4=1` to suppress the notification-related Fast allocation
difference. Keep the original-route
menu/whole-race evidence separately. After collecting both repeats of all four arms:

```sh
python3 tools/ceiling_report.py tmp/a8 MACHINE
```

Directories must be named `MACHINE-{control,no-wait,no-fill,instant}-{a,b}`. The audit
requires exact repeats, common binary/layout, enabled and disabled hook bytes compared
with the pinned relocated original, effective instant-blitter settings, and a measured
frame rate in every arm. Use `MATRIX_SKIP_INTRO=1` together with the A8 variables above;
never mix old-route and intro-skipping arms in one result.

To recheck the current all-off captures without replacing the older B4 evidence:

```sh
python3 tools/slave_gate.py --check --prefix prefs-
```

The prefix selects all four named cases and the corresponding negative-test fixtures;
without `--check` it creates fresh captures with that prefix. Existing directories remain
protected from replacement.

The completed A7 table is in internals. Reproduce baseline captures with the recorded
B5 VERIFY binary/source identity; the larger current A8 developer build has a different
layout and requires a new baseline if used for A7. Scratch worker directories isolated
sockets, debugger ports, boot volumes and PIDs while using the same immutable game
inputs. A worker name containing `mmu` is not an effective CPU selection: read each
capture's `machine`, WHDLoad arguments and retained effective configuration.

A7's gate permits explained missing timings, so it is complete with 040/060 failures
explicit. B5 and A8 require those measurements and remain open. Shared-profiler work is
deferred by the user; do not replace the cores or present missing records as zero cost.

The current accepted A500/A1200/020 audits use `tmp/a8-single-setting`: existing control,
no-wait and no-fill captures are linked there, alongside fresh single-setting instant
pairs. Old instant captures that also changed the wait policy are reference only, even
where their measured fps happens to agree. The 030 allocation probes are diagnostic captures; its accepted four-arm timing set is
`tmp/matrix-workers/prefs/tmp/a8-stable-prefs/`. The new build has its own hash,
all-off acceptance in `tmp/b4/prefs-acceptance.json`, and C4-on MMU functional pairs in
`tmp/a8-mmu-prefs/`. Do not relabel old A7 or B3 evidence as the new build.


## World-clock design checks (C1)

```sh
python3 tools/test_world_clock.py
```

This host-only executable specification checks the integer elapsed-VBL schedule and
accounting contract in [Game time](internals.md#elapsed-vbl-world-clock-c1). It uses no
game assets, emulator, CIA timer or fractional simulation updates. Five tests pass
for both PAL and NTSC, including counter wrap, debt cap and rebase. It does not install
a clock hook or validate the C2 assembly. C2 adds optional hook ranges to
the disabled-byte gate and verify live callback counts, completed ticks, field debt,
sound and publication alongside C3/C4 transitions and input handling.


## C2 developer validation

C2 is implemented and its scoped checks pass. It is confined to developer/VERIFY builds
and the supplied executable variant. `CUSTOM2` bit 1 enables the VBL clock; bit 0
still controls caches. `CUSTOM4` bit 1 introduces a 20-field batch delay for tests;
bit 2 retains native painting (catch-up raster work, CPU HUD operations and tick-time replay R) as a
comparison control. These
bits do not enable a release feature or waive the C5 gate.

```sh
make slave-verify OUT=tmp/c2/build-verify
. amiga/env.sh
python3 tools/c2_capture.py tmp/c2/new-pal --custom4 1 --ticks 160 --profile 50
python3 tools/c2_capture.py tmp/c2/new-ntsc --ntsc --custom4 1 --ticks 160
python3 tools/c2_capture.py tmp/c2/new-delayed --custom4 3 --ticks 160
python3 tools/c2_capture.py tmp/c2/new-raster --custom4 7 --ticks 160
python3 tools/c2_compare.py tmp/c2/new-delayed tmp/c2/new-raster tmp/c2/comparison.json
```

Use fresh output names. The collector verifies pinned inputs and runtime, refuses
stale builds, starts its own emulator, routes by screen signatures, and stops at
the requested tick's pacer entry. At this point that tick's native calls have run,
but the slave's completed-tick count is one lower. It records the actual layout,
clock credit/accounting and picture counts, then requires F10's `OK` handback.
Failures remain `INCOMPLETE`; never promote them based on a screenshot alone.
`--ntsc` selects an NTSC emulator display and adjusts the screen-signature search
origin; the slave detects the rate independently from the beam. The native word
and observed maximum line are recorded under `rate_detection`.

The comparator checks selected authoritative A3/A4 ranges at common tick/layout
and build/runtime. It is neither whole-program equivalence nor C5 acceptance.
`--route qualifying` exercises pit animation; `--replay` is an experimental route.
Optional profiles cover 50 or 100 fields after the route, not the final tick
snapshot. `--profile-tick N` instead anchors the window at tick N's pacer. Longer
windows are useful when slow batches leave no complete publication interval in 50
fields; retain the insufficient-coverage result as failed evidence. Raw artifacts stay in ignored `tmp/`.

`--publish` stops immediately before submission with the requested number of ticks
completed, after queued HUD operations have painted. It records and hashes the
32,000-byte bitmap in `paint.bin`; the comparator then requires pixel equality as
well as the selected state ranges. Choose a tick that ends a batch in both arms.
If a batch crosses that tick, the collector stops at the next publication and
rejects the mismatch instead of waiting forever. The ordinary pacer boundary
remains useful for comparing tick state independently of batch size.

The HUD queue retains prepared register inputs and text state for twelve CPU raster
regions, including conditional background clear/copy. It drains before the final scene and publication; parser updates, dirty
flags and instrument state still run on every native tick. Its 2048 slots reserve
192 KiB in developer builds. Capture metadata includes queued/painted counts,
pending count, high-water mark and overflow count. Overflow stops the probe and
fails acceptance; it must never be treated as a partial successful picture.
The collector preserves diagnostics for failed captures and still stops only its
own emulator. Background-clear/copy counters show whether each path was exercised.

Run `python3 tools/check_hud_hooks.py` after changing these hooks. It traverses
original HUD control flow and rejects patches that overwrite another branch's
entry, including a negative fixture reproducing the rejected glyph placement.
Run the disabled-byte suite on fresh captures after rebuilding all three variants.
These checks complement the runtime comparisons; they do not prove all UI paths.

The replay-overlay comparison uses one common build and changes only painting policy:

```sh
python3 tools/c2_capture.py tmp/c2/new-replay --replay --custom4 1 --ticks 40 --profile 50
python3 tools/c2_capture.py tmp/c2/new-replay-control --replay --custom4 5 --ticks 40 --profile 50
python3 tools/c2_compare.py tmp/c2/new-replay tmp/c2/new-replay-control tmp/c2/replay-state.json
python3 tools/c2_publication.py tmp/c2/new-replay tmp/c2/replay-publication.json
```

`c2_publication.py` verifies capture hashes and checks each recorded field's actual
bitplane DMA buffer against CPU and blitter-destination writes. It also requires
one VBL callback per field, at most one submission per field and one R paint per
complete publication interval in replay. It excludes partial intervals at trace
edges and requires exercised CPU, blitter and publication paths. Running that
cadence check on the native-painting replay control is expected to fail: the control
paints R per tick, leaving some zero-tick publications without a repaint. This is an
intentional negative control, not a successful enhanced-mode acceptance run.

`--view rear|tv|front|cockpit` sends the corresponding native view key after the
route, records the request and checks the resulting view code at capture. The
comparator requires matching requests. This is a view-path probe, not C4 input
acceptance. Published bitmap captures use the remembered base at h0+$1256, never
h0+$1252's external-view viewport offset.

`python3 tools/c2_sound.py CAPTURE REPORT` checks the recorded elapsed-field
handoff and native pitch arithmetic, including per-field VBL cadence. It requires
nonzero pitch inputs and both short and overrun tick spacing; an idle-only window
is INCOMPLETE. The checker verifies trace/build hashes and finds the timing store
in that slave's verified bytes. This is not an audio-quality or whole-race claim.

## C3 modal-boundary validation

The C3 probes reuse the pinned fresh-boot collector and deterministic native inputs.
They run with `CUSTOM2=3`, keeping caches and the developer clock enabled; `CUSTOM4=1`
uses the common-layout preference control. Build products and evidence remain in `tmp/`.

```sh
. amiga/env.sh
make slave-verify OUT=tmp/c3/build-verify
python3 tools/check_modal_hooks.py
python3 tools/check_hud_hooks.py
python3 tools/c2_capture.py tmp/c3/pause --build tmp/c3/build-verify --modal pause --custom4 1
python3 tools/c2_capture.py tmp/c3/ntsc --build tmp/c3/build-verify --modal pause --custom4 1 --ntsc
python3 tools/c2_capture.py tmp/c3/menu --build tmp/c3/build-verify --modal menu --custom4 1 --route qualifying
python3 tools/c2_capture.py tmp/c3/pit --build tmp/c3/build-verify --modal pit --custom4 1 --route qualifying
python3 tools/c2_capture.py tmp/c3/replay --build tmp/c3/build-verify --modal replay --custom4 1
python3 tools/c2_capture.py tmp/c3/race --build tmp/c3/build-verify --modal race --custom4 1
```

Use fresh output directories. `--build` selects an ignored build directory and rejects
stale source/build hashes. `--modal` dispatches to `tools/c3_capture.py`; these probes
capture transitions rather than using `--ticks`, `--publish` or `--profile`.
Each saves native command logs, hashes, actual hunk layout, clock/car/session snapshots,
screenshots, a modal report and F10 quit evidence. Failure keeps INCOMPLETE metadata.

Pause tests hold the native wait for 250 fields, require unchanged car state and clock
accounting, and stop at the resume epilogue before the reserved tick continues. They
require zero credit/phase/batch, no extra completed tick or overload drop, and the
rebased sound interval. Replay tests also wait for natural completion and resume live.
The menu probe recognizes the frozen menu and waits for actual initialized clock entry,
not a copied field number. The pit probe uses harness `JOY2_UP`, matching the supplied
joystick control selection, to enter and leave native accelerated time. The race probe
polls every 25 fields until green, then every 250 fields until results; scene anchors
must actually be observed. These are modal checks, not C5 clock-ratio acceptance.

Queue accounting is checked only at quiescent snapshots: during a flush the full
pending count is retained while the painted counter increases. The static hook checker
verifies all seven C3 calls and rejects interior branch-entry overlap. After assembly
changes, rebuild all three variants and run `tools/slave_gate.py --prefix c3-` for the
four-arm disabled-feature gate and its byte-by-byte negative checks.

`--modal pause-menu --route qualifying` covers Escape from a paused race, including
its paused cockpit return. `--modal pause --custom4 3` covers forced catch-up;
`--modal pause --setup a500-1.5m --custom4 1` covers the 68000. Additional input-latency
and one-shot acceptance remains C4.

Validate saved snapshots and closed-epoch accounting with:

```sh
python3 tools/c3_report.py tmp/c3/race --out tmp/c3/race-report.json
python3 tools/c3_report.py tmp/c3/pause --repeat tmp/c3/pause-repeat --out tmp/c3/pause-repeat-report.json
```

The repeat form requires matching pins, build, machine/options, actual layout, route,
clock and car snapshot hashes, and every corresponding screenshot. Capture the repeat
with the same command sequence into a fresh output directory first.

A steady C2 regression on the same C3 build can be collected with:

```sh
python3 tools/c2_capture.py tmp/c3/steady --build tmp/c3/build-verify --custom4 1 --ticks 240 --profile 50 --profile-tick 200
python3 tools/c2_publication.py tmp/c3/steady tmp/c3/publication.json
python3 tools/c2_sound.py tmp/c3/steady tmp/c3/sound.json
```


### C4 input acceptance

The C4 probe uses the current C3 build, with forced catch-up enabled. It injects real
keyboard and joystick events and stops at native keyboard-IRQ stores, input returns
and view-consumption returns. It never writes game memory. Use fresh capture names:

```sh
. amiga/env.sh
make slave-verify OUT=tmp/c4/build-verify
python3 tools/c2_capture.py tmp/c4/input --build tmp/c4/build-verify --input --custom4 3
python3 tools/c2_capture.py tmp/c4/repeat --build tmp/c4/build-verify --input --custom4 3
python3 tools/c4_report.py tmp/c4/input --repeat tmp/c4/repeat --out tmp/c4/report.json
python3 tools/c2_capture.py tmp/c4/suite --build tmp/c4/build-verify --input-suite --custom4 3 --setup a1200-030
python3 tools/c2_capture.py tmp/c4/suite-repeat --build tmp/c4/build-verify --input-suite --custom4 3 --setup a1200-030
python3 tools/c4_report.py tmp/c4/suite --repeat tmp/c4/suite-repeat --out tmp/c4/suite-report.json
```

`--input-suite` taps every view key, Space (pause, then a new tap to resume), a double
tap and a replay tap, each between two scans, and records the scans and view consumers
around them. `c4_report.py` recomputes every check from the saved, hash-verified
snapshots. `--setup a1200-030` selects the primary target (68030/50 without an MMU,
`NOMMU`) and refuses to run unless the emulator reports that CPU.

`--input` requires Quick Race and `CUSTOM4=3`; it rejects other probe modes. Metadata
records the build/runtime/input pins, layout, native route, snapshots and clean quit.
The saved report checks the held-key edge against actual sampled masks, not the host
injection time. The first tick may have scanned before the keyboard interrupt arrives.
It also checks controller press/release and a full press/release between scans.
`CAPTURED` means the experiment finished; `input.status=FAIL` means C4 acceptance failed.
The reporter prints and saves that acceptance result without treating a reproduced game
failure as a corrupt capture. Check the result, not merely its process exit status.

With the buffer (VERIFY build, `CUSTOM2` bit 1) the probe also follows the held-back
release to the next scan and requires one view event, a rearmed latch and the slave's
deferral counters (`c4_deferred`, `c4_applied`). The report accepts the older unbuffered
captures, which still verify as FAIL. If the
slave changes, rebuild and collect fresh evidence, including the disabled-feature
gate; retain the current captures as evidence of the original failure.

### C5 real-time acceptance

C5(a) runs a whole Quick Race with no input and samples the clock every 250 fields.
It requires `CUSTOM4=1` and no other probe option. Run each machine twice:

```sh
. amiga/env.sh
make slave-verify OUT=tmp/c5/build-verify
python3 tools/c2_capture.py tmp/c5/rate-030 --build tmp/c5/build-verify --rate --custom4 1 --setup a1200-030
python3 tools/c2_capture.py tmp/c5/rate-030-repeat --build tmp/c5/build-verify --rate --custom4 1 --setup a1200-030
python3 tools/c5_report.py tmp/c5/rate-030 --repeat tmp/c5/rate-030-repeat --out tmp/c5/rate-030-report.json
```

Replace `a1200-030` with `a1200` or `a500-1.5m` for the slow machines. Each race takes
about a minute. `c5_report.py` recomputes the result from the hash-verified samples:
PASS, FAIL, or OVERLOADED when the run drops so much debt that no fitting time is
left to measure. Like C4, check the printed acceptance, not the exit status.
