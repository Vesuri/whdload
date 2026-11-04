# Development

## Inputs

- [Official WHDLoad page](https://whdload.de/games/Mercenary3.html).
- [Official installer](https://whdload.de/games/Mercenary3.lha).
- [User-supplied full install](https://ftp2.grandis.nu/turran/FTP/Retroplay%20WHDLoad%20Packs/Commodore_Amiga_-_WHDLoad_-_Games/M/Mercenary3_v1.2_0356.lha).

`manifest/inputs.json` pins archive URLs and SHA-256 hashes. File manifests record
relative names and hashes only. Downloaded and extracted bytes remain ignored:

| Path | Purpose |
| --- | --- |
| `tmp/archives/` | Original archives and SHA-256 sidecars |
| `tmp/game/Mercenary3_v1.2_0356/Mercenary3/` | Pristine installed game |
| `tmp/installer/Mercenary3/` | Pristine official installer, including source |

`make check` checks every archive and extracted file against the pinned manifests,
including unexpected files. It never runs the game or inspects code.
For restoring inputs, download the exact named archives from the recorded URLs,
verify their SHA-256 hashes before extracting, then extract each into its recorded
extraction directory. Preserve any differing existing files separately first.

## Shared environment

Source `amiga/env.sh` from the repository root. `AMIGA_ENV` can override the shared
environment file, whose default is `~/.local/share/amiga/env.sh`. Missing shared
environment files fail explicitly. Shared tool and ROM paths are inherited from it;
no local copies or paths into other projects are used.

## Running

`amiga/run.sh` boots Kickstart 3.1 from a generated `DH0` that runs
`WHDLoad Mercenary3.Slave CACHE PRELOAD` on `DH1`, a disposable copy of the pristine drawer
under ignored `amiga/.run/`. The default machine is the A500-equivalent (68000, 512 KB
chip, 1.5 MB slow, no fast RAM); the slave needs 512 KB chip and WHDLoad needs other
memory beside it. Variables: `SLAVE`, `WHD_SPLASH=1`, `WHD_ARGS`, and the shared
launcher's (`AMIGA_SETUP`, `CPU`, `CHIP_KB`, `SLOW_KB`, `FAST_KB`, `DEBUG`, `WARP`,
`DETERMINISTIC`, `JOY0`, `JOY1`, `SOUND`, `WINDOW`). Defaults: mouse in port 0,
keyboard joystick in port 1. `CACHE PRELOAD` are supplied for normal and measured runs;
`WHD_ARGS=NOCACHE` overrides cache use for an explicit cache-off test. Route results
record the complete launch command, including these defaults.

The debugger server uses the native build:

```sh
. amiga/env.sh
FSUAE="$FSUAE_ARM" JOY0=none python3 tools/merc3.py serve > tmp/serve.log 2>&1 &
python3 tools/merc3.py gdb 'monitor fields 400'
python3 tools/merc3.py shot tmp/shots/now.png
python3 tools/merc3.py quit
```

## Building

`make original` assembles `whdload/original/Mercenary3.slave.asm` with vasm
(`-no-opt`, the shared `WHDLOAD` includes) into `tmp/build/` and requires it to equal
the shipped slave byte for byte. `BUILD` overrides the output directory.

`make slave` builds the performance slave `whdload/Mercenary3.slave.asm` into
`tmp/build/Mercenary3.Slave`, `make verify` its VERIFY build `Mercenary3.verify.Slave`.
Run the instrumented build with `SLAVE=tmp/build/Mercenary3.verify.Slave WHD_ARGS='CUSTOM5=0 CUSTOM1=1' amiga/run.sh`; the
profile and game-time tools take the same `SLAVE` and `WHD_ARGS` and record them.

The release shows only **Enhanced framerate**, a boolean checkbox, enabled by `CUSTOM5=1`. Off
(`CUSTOM5=0`) keeps the original game's behaviour: it clears every feature except the
fixes for shipped-slave defects (bits 0 and 15, `CUSTOM1=32769` in VERIFY); release builds
ignore `CUSTOM1`. For individual
features in VERIFY, supply `CUSTOM5=0 CUSTOM1=<mask>`; with Custom5 omitted, VERIFY
uses only the individual feature mask. Custom2–4 remain VERIFY-only instruments.

## Profiling and game time

Both tools boot the shipped slave with the native build (`FSUAE_ARM`), `WARP=1`,
`DETERMINISTIC=1` on the 020 and `JOY0=none`, stop at the game's entry and drive the same route
with the port-1 joystick through `monitor input`: wait 175 fields for the cell door,
walk 185 fields through it and outside, then turn right for 140 (500 fields, 10 s PAL).
`ROUTE` overrides it (`ROUTE='175:,185:JOY2_UP,140:JOY2_RIGHT'`).

```sh
. amiga/env.sh
python3 tools/route_profile.py                       # tmp/prof/a1200-fast-route/
AMIGA_SETUP=a1200-fast python3 tools/sim_speed.py tmp/sim/a1200-fast.json
AMIGA_SETUP=a500-1.5m python3 tools/sim_speed.py tmp/sim/a500-1.5m.json
python3 tools/sim_speed.py --compare tmp/sim/a500-1.5m.json tmp/sim/a1200-fast.json
PER_FRAME=1 AMIGA_SETUP=a500-1.5m python3 tools/sim_speed.py tmp/sim/frames.json
python3 tools/sim_speed.py --frames tmp/sim/frames.json
```

`route_profile.py` (default `AMIGA_SETUP=a1200-fast`) traces the window in `CHUNK`-field
captures (default 50), reduces each with `amigaxdev.callprofile` and deletes it
(`KEEP_TRACE=1` keeps them). It locates the live slave in fast RAM to name its code, counts
frames at the frame publication routine, and writes `report.txt`, `profile.pkl.gz`,
`route.json`, a screenshot per chunk and `sheet.png`. A run takes under a minute.

`sim_speed.py` runs the route untraced and samples position, heading, the in-game clock and
the frame and VERTB counters every `STEP` fields (default 5), or at every frame with
`PER_FRAME=1`. `--compare` tabulates machines side by side with per-segment rates.

`tools/fps.py` measures the route without traces. Store results under `tmp/`; choose a
new filename for each run (existing results are refused):

```sh
SLAVE=tmp/build/Mercenary3.verify.Slave WHD_ARGS='CUSTOM5=0 CUSTOM1=1' python3 tools/fps.py tmp/fps/count.json
SLAVE=tmp/build/Mercenary3.verify.Slave WHD_ARGS='CUSTOM5=0 CUSTOM1=1' PER_FRAME=1 python3 tools/fps.py tmp/fps/cadence.json
python3 -m unittest discover -s tools -p test_fps.py
```

Routine comparisons include the existing `040-25` matrix configuration. Run it directly
without running the full matrix, using the same VERIFY build and route for both options:

```sh
AMIGA_SETUP=a1200-030 DETERMINISTIC=0 \
EXTRA_ARGS='--cpu=68040-NOMMU --uae_cpu_frequency=25000000' \
SLAVE=tmp/build/Mercenary3.verify.Slave WHD_ARGS='CUSTOM5=0 CUSTOM1=255' \
python3 tools/fps.py tmp/fps/040-on.json
```

Change `WHD_ARGS` and the output name for the matching off run. This is the existing
cycle-exact matrix cell, not the separate `a1200-040` preset.

`AMIGA_SETUP`, `SLAVE`, `WHD_ARGS` and `ROUTE` work as in the profiler. `BOOT_TIMEOUT=120`
covers launch through the verified entry breakpoint; `RUN_TIMEOUT=180` covers the route
(host seconds). Failure produces no result JSON and stops the owned processes. The validated
anchor is `ANCHOR=entry`; the 030 now reaches it too, so no counter fallback is needed. The default result uses
counter delta over the exact-field route. `PER_FRAME=1` samples publication field stamps
where breakpoints work, shifts input boundaries to those stops, and reports the resulting
overshoot; use it for cadence, not as an exact-field reference. See
[A2 validation](internals.md#a2-frame-counting-without-traces) for the current measurements
and the unresolved difference from the old 89/38-frame references.

`tools/write_audit.py` attributes every memory write in kept traces to the main-loop
call site running at the time (interrupt code separately):
`KEEP_TRACE=1 ROUTE='175:,135:JOY2_UP,40:JOY2_RIGHT' python3 tools/route_profile.py tmp/prof/audit`
then `python3 tools/write_audit.py tmp/prof/audit 175` (the kept chunks take about 2 GB;
delete them afterwards).

`tools/bus_audit.py` splits the CPU's chip-bus accesses by kind (instruction fetch, data
read, write) and region, counts misaligned longwords and compares slot use inside and
outside the bitplane lines: `KEEP_TRACE=1 python3 tools/route_profile.py tmp/prof/bus` then
`python3 tools/bus_audit.py tmp/prof/bus 175` (about 3 GB of chunks; delete them afterwards).
Its last table names the remaining traffic by place: code fetches per Disk.1 4 KB page and
data per named chip range (vectors, render scratch, game variables) or 4 KB page, with the
VERTB counter poll and display writes apart. A 275-field route
(`ROUTE='175:,60:JOY2_UP,40:JOY2_RIGHT'`) keeps about 1.4 GB.

`tools/render_profile.py PROFILE_DIR [ROOT ...]` turns a route profile into cycles per
published frame for each drawing call and a callee tree (Disk.1 offsets; `SLAVE_LST=` names
slave routines from a vasm listing, `-L FILE`). `route_profile.py` records the live
`ws_ExpMem` in `route.json` and reads code the slave copied there (M1, S3, F2; mapped by
`tools/relocation.py`) as its chip original, so calls inside copies are recognised.

`tools/beam_profile.py OUT.json ROOT ...` times routines on any CPU from beam positions at
entry and return: the instrument for the 030/040/060, which record no instruction profile.
Roots are Disk.1 offsets or slave symbols (`SLAVE_LST=`); copies in expansion memory are
caught too. Nested roots are not counted inside an outer root, so probe each level in its
own run. `PROBE_FIELDS=175:500` limits probing to gameplay (not `WINDOW`, which `run.sh`
uses). Example, reference 030/50:
`AMIGA_SETUP=a1200-030 SLAVE=tmp/build/Mercenary3.verify.Slave WHD_ARGS='CUSTOM1=131071' SLAVE_LST=tmp/f1/slave.lst PROBE_FIELDS=175:500 python3 tools/beam_profile.py tmp/f1/top.json 577be 5765e 5afaa 593a6 5e840 5e458 _savepresent _restorepresent`
(about 20 s per run).

`tools/log_harness.py` checks F4's `bfffo` log conversion (`whdload/log-f4.i`) against the
original Disk.1 code under the shared Unicorn: every input of the `$4EE88`, `$4EE84` and
`$4EE76` entries, comparing d1, d6, d7 and flags (about three minutes; `--quick` samples
1/257). Source `amiga/env.sh` first.

`tools/translate.py` generates F5's `whdload/translate-f5.i` from the game's Disk.1
(shared capstone; source `amiga/env.sh`): it decodes the copied blocks, rewrites every
render-scratch operand to 32-bit form, re-targets the branches the growth moves and
re-decodes the whole translation to verify each operand. Regenerate it after changing
M1/S3/F2's blocks, entries or operand lists, or the moved range:
`python3 tools/translate.py --dump DUMPDIR`. The dump comes from `tools/memory_dump.py`
on a running VERIFY game with F5 off. From it the generator learns which chip words the
slave patches before copying, and it refuses to edit those words. `--check DUMPDIR`
compares an F5-on dump with the generator's simulation, operand by operand. `tools/relocation.py` maps both ways
between chip and translated addresses (`Map(expmem, f5=True)`), so the profilers and
`beam_profile.py` follow F5's copies. `presentation_check.py` also hashes the expansion
ranges that hold restored data: F2/F5 code and the moved scratch.

The `VERIFY` build's `Custom2` makes drawing routines return at once (see
[the frame budget](internals.md#frame-budget-toward-50-fps)): compare `fps.py` runs with
and without it to price drawing on the 030/040/060, whose cores record no instruction
profile. Rebuild VERIFY before measuring: the main-3D bypass now survives the
object-interpolation hook. `CUSTOM5=1 CUSTOM2=1` skips main 3D;
`CUSTOM5=1 CUSTOM2=31` skips all five drawing calls. The clear bypass also disables
fast bitmap staging, so it does not isolate clearing cost. For inclusive routine
costs and publication wait/copy timing, see the
[current 040 beam measurements](internals.md#68040-frame-budget-after-p5).

`route_profile.py` finds the live slave in fast RAM, or in slow RAM on the `a500` setups.
For a one-off play screenshot after an untraced advance, record two fields and use the
last screenshot: the first captured field can be incomplete. Longer route-profile chunks
already provide complete fields. FS-UAE's screenshots can carry non-Amiga colours in the right border on the A500 setup;
they are not game output (OCS colours are multiples of 17 per channel).

All three route tools share `route_runtime.py`: checked entry, PAL configuration,
boot/route deadlines, runtime hashes and process cleanup. `a1200-030` defaults explicitly
to `DETERMINISTIC=0`: deterministic directory I/O deadlocks with its indirect UAE board
before the game entry. This keeps the 68030 MMU, 50 MHz and data-cache emulation settings.
Other setups retain `DETERMINISTIC=1`; an explicit environment value is honored and
recorded. Do not override it through `EXTRA_ARGS` or `RECORD`. Threaded boot I/O is not
an assertion of deterministic boots or hardware timing; compare route evidence from the
checked game entry. A3 completes their routes but fails the frequency sanity check; see below.

```sh
AMIGA_SETUP=a1200-030 MODE=counter python3 tools/route_profile.py tmp/routes/030-count
AMIGA_SETUP=a1200-030 python3 tools/sim_speed.py tmp/routes/030-state.json
AMIGA_SETUP=a1200-030 PER_FRAME=1 python3 tools/fps.py tmp/routes/030-cadence.json
python3 -m unittest discover -s tools -p 'test_*.py'
```

`MODE=counter` writes `route.json` and `report.txt` with frames/fps and explicitly no
instruction costs. The normal `MODE=profile` refuses unsupported CPU backends rather than
interpreting an empty instruction trace. Output directories/files must be new and inside
`tmp/`. See [A1 validation](internals.md#a1-anchor-investigation).

## Machine matrix

```sh
tools/matrix.sh tmp/game/Mercenary3_v1.2_0356/Mercenary3/Mercenary3.Slave '' tmp/matrix/shipped
# Revalidate existing evidence and render its table without booting again:
tools/matrix.sh --report-only tmp/game/Mercenary3_v1.2_0356/Mercenary3/Mercenary3.Slave '' tmp/matrix/shipped
```

The Bash 3.2 entry point sources the shared environment. Pass the slave, a single quoted
WHDLoad argument string (empty for none), and a new directory under `tmp/`. The runner
uses the fixed 500-field route and runs seven target cells plus an 8 MHz 040 frequency
sanity cell, one at a time. It preserves logs and per-cell JSON and writes `table.md`
and `matrix.json`, even when a cell fails. It never retries a cell automatically.
`--report-only` replaces only the aggregate reports, preserving the captured cell files.
`BOOT_TIMEOUT` and `RUN_TIMEOUT` retain the route tools' limits; `FSUAE` may explicitly
select an emulator, whose hash must remain identical across cells.

Unset machine/route overrides (`AMIGA_SETUP`, `CPU`, `EXTRA_ARGS`, memory variables,
`DETERMINISTIC`, `PER_FRAME`, `ROUTE`, etc.) before running: the matrix owns them and
rejects conflicts. Caller `MMU`/`NoMMU` arguments are rejected because the 030 pair tests
its default mode and explicit `MMU`. The 040/060 use the 030 cycle-exact preset with
explicit non-MMU CPU and frequency overrides; the stock 040/060 presets are not used.

The command succeeds when every cell completes and its effective configuration validates.
The 8 MHz / 25 MHz 040 frequency check is advisory: both give 118 frames on the measured
runtime, a known emulator limitation accepted by the user. `matrix.json` records
`sanity_passed=false` and `sanity_advisory=true` separately from overall `passed=true`.
The 040/060 counts remain emulator measurements, not calibrated hardware-speed baselines.
See [A3 evidence](internals.md#a3-machine-matrix). A3 is complete.

## Committed-state traces

```sh
. amiga/env.sh
python3 tools/state_trace.py tmp/state/boot-a.json
python3 tools/state_trace.py tmp/state/boot-b.json
python3 tools/state_trace.py --compare tmp/state/boot-a.json tmp/state/boot-b.json
```

The two unchanged boots are A6's required repeatability test. The recorder uses the
shared checked entry, runtime hashes, PAL validation, deadlines and owned-process
cleanup. `AMIGA_SETUP`, `SLAVE`, `WHD_ARGS` and `ROUTE` work as in the other route tools.
Output must be new and under `tmp/`; scratch dumps are removed on success or failure.
No guest memory is written and no instruction recording is required.

Every main-loop-head stop produces one record, capturing the preceding pass's committed
state. Route lengths remain fields, but inputs change after the first head reaching a
cumulative boundary. The final capture can overshoot 500 fields. This is not the exact
FPS route. Ranges in JSON use exclusive ends. The two raw
object windows are provisional until P2 maps the objects; the full game-image hash has no exclusions
inside its range. Compare reports the first differing pass and field names (exit 1),
or identical records (exit 0). Trace definitions must match; build/machine identities
remain available in metadata and must be checked separately for repeatability claims.
See [A6 evidence](internals.md#a6-committed-state-recorder).

## Presentation restore check

P1 keeps the game's frame word counting logic passes. Its separate displayed-frame
counter and restore markers exist only in `make verify`. Use that same VERIFY build
with `CUSTOM5=0 CUSTOM1=15` and `CUSTOM5=0 CUSTOM1=31` for P1's `fps.py`/`matrix.sh` comparisons; the tools
reject an enabled P1 release build instead of mistaking logic passes for displayed frames.
`sim_speed.py PER_FRAME=1` skips staged presentation poses and samples logic publications.

`tools/presentation_check.py tmp/p1/check.json`, with the VERIFY slave and bit 4 enabled,
compares SHA-256 hashes and reports changed addresses around every presentation restore.
The report lists the display and interrupt-owned exclusions. These allow live field,
clock, panel and text updates; they are never restored to old values. At least one
presentation frame must execute for a passing result. Use the fast cell when the 020
has no spare interval. No instruction recording is needed.

## Release packaging

Layout: `release/` holds the maintained release text (`readme-body.txt`); `dist/`
(ignored) receives the archives. `make dist` runs the input check and all three slave
builds, then `tools/package_release.py` writes `dist/Mercenary3-<version>.lha`.
The version and date come from the release slave's `Version <version> (<date>)` line and
must match the ReadMe's history entry; a VERIFY slave is refused.

The archive has exactly the members of `tmp/archives/Mercenary3.lha` (verified against
`manifest/inputs.json`). Only `Mercenary3 Install/Mercenary3.Slave` and
`Mercenary3 Install/ReadMe` change; the original Install script, icons, imager and
documents are copied byte for byte, so the installed icon gets the original
`SLAVE` and `PRELOAD` tooltypes and no `CUSTOM5`. The ReadMe is the WHDLoad Install
Template's (pinned in `manifest/release-templates.json`, read from `$WHDLOAD`) with
`release/readme-body.txt` and the original ReadMe's version 1.2 history entry inserted at
build time, so no template or original text is tracked. LHa for UNIX (`LHA`) packs with
level-1 LH5 headers; the original stores generic headers, the repack UNIX ones.

The packager stages a fresh extraction under `tmp/`, tests the result with `$LHA t`,
re-extracts it and requires the same member names, every member equal to its staged
copy, the two replacements different from the originals and every other member
byte-identical. This checks the package, not gameplay. Installation from an original
floppy has not been exercised.
