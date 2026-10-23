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
`WHDLoad FormulaOneGrandPrix4Disk.Slave PRELOAD SPLASHDELAY=0 NOREQ`. The default machine
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
