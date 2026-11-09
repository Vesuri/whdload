# Development

Current release status and validation limits are in [open work](open-work.md).

## Inputs and shared tools

`inputs.sha256` pins both archives: Galahad's installer `Powerdrome.lha` and the Retroplay
pack `Powerdrome_v1.0_0140.lha`. `make unpack ARCHIVES=<directory>` installs them into
`tmp/game/`: the playable tree is `tmp/game/Powerdrome/`, the installer `tmp/game/PowerdromeHD/`.
`tmp/archive.sha256` records the hashes of the files the research used.
The research harness's own frozen slaves are in `tmp/old-build/`, out of reach of `make clean`.

Historical instruction traces, memory snapshots and raw debugger/emulator logs
may be stored as `.gz` files to reduce disk usage. Reports, configuration files and
frozen slaves remain beside them. Before rerunning an analysis, expand the files
it needs with `gzip -dk tmp/prof/CAPTURE/FILE.gz` (use the actual capture path);
the analysis tools expect uncompressed files. Remove the expanded copies afterwards.
`tmp/storage-cleanup.json` and `tmp/storage-cleanup-snapshots.json` list locally
archived files, original SHA-256 hashes and sizes. Every archive was decompressed
and checked against its original before the redundant raw copy was removed.
Current mouse steering, release-option and Phase F captures remain uncompressed.

The tools that need the shared Amiga environment source `../../common/env.sh`, which sources
the shared `env.sh` (AmigaXDev's `docs/environment.md`). Shared inputs use these overrides:

| Variable | Default under the shared Amiga directory |
|---|---|
| `KICKSTART` | `Kickstarts/kick40063.A600` |
| `KICK13` / `RTB` | `Kickstarts/kick34005.A500` / its `.RTB` |
| `KICKSTART_A1200` | `Kickstarts/kick40068.A1200` |
| `WHDLOAD` | `WHDLoad-20.0` |
| `WHDLOAD_BINARY` | `$WHDLOAD/C/WHDLoad` |
| `WORKBENCH_ADF` | `Workbenchv2.04rev37.67Workbench.adf` |

`FSUAE` overrides the executable, `FSUAE_COMMON` the shared process/port helper.
The shared directory convention is `~/.local/share/amiga`. `VASM` and `NDK` override the
assembler and Amiga include directory; `WHDLOAD` also supplies the API headers and KickEmu
sources the slave builds with.

## Build and run

```sh
make build BUILD=original
make run SLAVE=original
make run BUILD=original
```

Every build first generates the sine table `tmp/build/mouse-sine.i` (`game.sh`). The builds
are `release` (`make slave`), `verify`, `coverage`, `original` and `original_verify`;
`VASM_EXTRA` adds defines, e.g. `make build BUILD=coverage VASM_EXTRA=-DTIMING_FULL=1`.
Each lands in `tmp/build/<build>/Powerdrome.Slave`. `make check` checks the release
bytes and that every build assembles and the reconstruction equals the installed slave.

`original` assembles with optimizations disabled and compares the entire result with the
installed slave. This is the reference reconstruction. `make slave` builds the WHDLoad 20 KickEmu
slave with interface 17 and the full timing scheduler. `make verify` builds
`tmp/build/verify/Powerdrome.Slave`; `CUSTOM5=1` submits an empty pilot name through the
native name-entry routine. `CUSTOM5=2` also selects Practice and submits Space in the pit.
The normal splash has one checkbox, **Enhanced framerate** (`CUSTOM1=1`), off by
default in the slave; the installer sets `CUSTOM1=1` in the game icon. It enables fast planar rendering and the scheduler together on 68020+
with real fast RAM. Unchecked, on 68000/68010, or without real fast RAM, both paths
remain native, including original frame-dependent timing. CUSTOM3 is no longer a
user option. The normal
build contains no input or twin-drawing fixtures. The slave requests 128 KiB of guest
expansion in addition to KickEmu's 256 KiB, including when the option is off. Slow-backed
expansion does not enable the renderer. See the [implementation and measured results](performance-implementation.md)
for supported states, diagnostic options and limitations. The [loader equivalence audit](loader-equivalence.md) verifies the tested startup/Practice
state and resolves Copylock D2, with explicit allocation and timing differences. Performance
A/B tests continue to use the same development loader.

`make run` builds the release slave and boots it (the repository's `docs/running.md`):

```sh
make run CPU=68030 FAST_KB=4096 WHD_ARGS=CUSTOM1=1
```

The default machine (`game.conf`, `SETUP=custom`) is 68000, 512 KB chip and 1,536 KB slow
with no fast RAM. The host boots Kickstart 3.1 and Workbench 2.04 provides Assign for the
original slave's Kickstart files. Windowed, real speed, sound enabled. `CPU`, `CHIP_KB`,
`FAST_KB`, `SLOW_KB`, `AMIGA_MODEL`, `EXTRA_ARGS` (which beats them all), `WHD_ARGS`, `WB`,
`WARP`, `JOY0` and `JOY1` override the setup; `WHD_SPLASH=1` shows WHDLoad's options and
waits for Start. `DEBUG` and `WARP` runs are silent with the window behind the others;
`SOUND=0|1` and `WINDOW=front|back|none` (none: no video) choose explicitly.

### Release installer archive

`release/Install` and `release/ReadMe` are the maintained installer text sources.
The icons, manual and hints come from the original installer archive; no proprietary
binaries or built slaves are tracked. `make dist` builds the archive from
`release/release.json`: Galahad's twelve files, replacing only Install, ReadMe and the
slave. It needs the slave's `$VER` string, which names the archive; the slave does not
have one yet ([open work](open-work.md)).

The earlier hand-packaged 2.0 archive (`tmp/Powerdrome-2.0.lha`) passed extraction and
SHA-256 comparison: all twelve paths match the original archive, the three replacements
match their sources, and the other nine files are byte-identical. Local details are
recorded in `tmp/Powerdrome-2.0-verification.json`. Archive integrity checks do not
substitute for running the Installer end to end on AmigaOS; that installation test remains
unperformed.

### Timing instrument

`make build BUILD=coverage VASM_EXTRA="-DTIMING_FULL=1 -DVERIFY_PHASE=1"`
adds the diagnostic phase ring. `VERIFY_PHASE` is rejected outside VERIFY builds.
Use the ordinary coverage/verify builds for baseline fps: the ring adds hook overhead
and 256 KiB of requested expansion, but never changes the normal build.

`python3 tools/phase_report.py CAPTURE` reads the initial/final chip and expansion
snapshots produced by `fixed_window.sh`. It prints mean and nearest-rank p95 exclusive
milliseconds per complete `$8056` presentation interval (including incidents), a
1/2/3+ field histogram, and completed world ticks. Driving fps remains the separate
`$bc7c` counter, so interval counts can differ.
`--trace` additionally compares each phase with summed instruction costs from the
same capture. Instruction units are normalized by the trace's cycles per field.
Only the common contiguous trace/ring window is compared; missing interior samples,
ring overflow and ambiguous live headers fail explicitly.

The guest reads VBL count, beam twice, then VBL count again, retrying vertical/VBL
crossings. Each `PDPHASE1` record stores sequence, VBL count, raw beam, event and
completed-world-tick count. The ring contains 16,384 sixteen-byte records. Its header
stores the buffer pointer, next sequence, capacity, sampling PC and tick counter.
Phase costs are exclusive; render excludes the nested handshake wait and chip copy.
Render completion is recorded at the actual return, including incident paths that
skip the HUD. The wrapper preserves the original caller test for staged rendering.
World steps can contain incident presentations; step and scheduler scopes nest,
and the existing world-restore path explicitly closes aborted steps.
Other covers work between instrumented phases, including hook overhead. Presentation
wraps the native `$8056` call, including its time bookkeeping and LoadView.

### Release matrix

`tools/release_matrix.py` runs the enhanced opt-in configuration sequentially on
M1–M7, with Practice and race routes. M5–M7 run with both WHDLoad CACHE and NoCache.
It compares complete driving intervals against the matching frozen native baseline,
then checks renderer twins on M4/M5/M7 and a CACHE pit/departure/track smoke on M6.
Twins use NoCache on M4/M7 and CACHE on M5; M7's cached native reference has an
observed comparison failure described in [accelerator testing](accelerator-cache-testing.md).
The M6 smoke disables twins to exercise production static routing.
The specific M3 Practice result 153/497 versus 153/496 is a user-accepted exception;
`no_regression` remains false and `accepted_exception` records the decision. Other
comparisons have no tolerance. Completed captures are reused only when their
configuration and slave hash match.
An incomplete capture is preserved and rejected; inspect it before a distinct retry.

Freeze a fresh build set in an ignored directory:

```sh
set -e
source ../../common/env.sh
out=tmp/release-repeat
mkdir -p "$out"
make verify
cp tmp/build/verify/Powerdrome.Slave "$out/verify.slave"
make build BUILD=coverage
cp tmp/build/coverage/Powerdrome.Slave "$out/coverage.slave"
make slave
cp tmp/build/release/Powerdrome.Slave "$out/normal.slave"
python3 tools/release_matrix.py "$out" --reference tmp/phase-b
```

The reference directory holds the frozen native `baseline.json` results; it is
local evidence, not a repository dependency supplied to players. `--only REGEX`
selects individual cases. `normal.slave` is retained alongside the input fixtures
for normal-build boot checks; measured routes use VERIFY/coverage input fixtures
with drawing twins and phase instrumentation disabled. Machine definitions and
current measurements are in [internals](internals.md#current-measurements).

### Buffer audit

`python3 tools/audit_buffer_writes.py CAPTURE` decodes every observed explicit CPU
memory destination from render entry through presentation, including relocated
slave and KickEmu instructions. It lists bitmap writers, plane-relative rows and
bytes outside the copied extent, and separately lists blitter-register writes.
Unhandled operations fail explicitly. It complements `audit_code_writes.py`;
CPU destination coverage does not imply DMA coverage or cover unexecuted paths.

`python3 tools/phase_report.py CAPTURE --handshake` checks that every staged copy
with a preceding presentation follows a recorded completed wait and a later VBL.
Use an ordinary C4=0 phase build for this ordering gate. C4=1 twins intentionally
wait before their native reference drawing, which writes into chip memory early.

For chip-only M3 (`FAST_KB=0`, `--slow_memory=0`), `fixed_window.sh` stores the chip
snapshot as `code.bin` too, with `dump-base.txt` equal to zero. WHDLoad's slave and
reserved expansion are physically chip-backed in this configuration. The helper
removes old scratch dumps before reading and checks both file sizes so a failed
debugger read cannot silently reuse an earlier machine's snapshot. Older M3
auxiliary `code.bin` dumps are not valid slave-diagnostic evidence; use their chip
snapshots. Their driving counts came from the live game/VBL addresses in chip RAM.

### Timing feature configuration

```sh
make build BUILD=coverage VASM_EXTRA='-DTIMING_FULL=1'
```

This selects the full release feature set: periodic controls, fine mouse rotation, orientation,
historical input, engine, WORLD/WORLD20, repair/drop and weather effects/fade/cycle.
All test defaults are zero and seed defaults are -1 (native initialization). Add the
retained VERIFY-only pit-sync, stall, render-rate or seed options explicitly for timing regression checks.
`TIMING_FULL=0` permits explicit individual-feature experiments; WORLD requires WORLD20 and
repair requires drawing suppression. Explicit per-feature overrides retain the existing
dependency checks. Normal `make slave` includes `TIMING_FULL=1` by default. Runtime selection
requires `CUSTOM1=1`, 68020+ and real fast RAM.

### Verification-only guest chip-memory override

`make verify VASM_EXTRA='-DVERIFY_CHIPMEMSIZE=1048576'` exposes 1 MiB
of guest chip memory to exercise native resources unavailable in the normal 512-KiB
configuration. Use a host with at least `CHIP_KB=1024`; the default A500 has
only 512 KiB and cannot run this artifact. Use 030/fast with `CUSTOM1=1` for enhanced timing checks.
Set `PROBE_OFFSETS='0x17836 0x178e6'` for ordered read-only audio call checks. Freeze the verification slave
under `tmp/` before restoring `make slave`.

The override requires `VERIFY` and accepts only 524288 or 1048576 bytes. Both invalid-build
guards have been checked; explicit 524288 produces the same verification binary as the
default. The normal production build remains byte-identical. Larger-memory runtime
checks pass on A500/030: native allocation, the loaded sample descriptor, helper arguments,
mute/unmute and request delivery are observed rather than forced. The normal 512-KiB
configuration separately passes the missing-resource guard. This is a weather audio test
configuration, not a production loader memory change or evidence of audible playback.

### Native audio mute input fixture

`COVERAGE_AUDIO_KEYS=1` requires `VERIFY` and `COVERAGE_INPUT`. It adds native Tab
characters to timing routes 7/9 at PAL fields 50 and 600, retaining their existing
throttle/brake input and finishing the tape at field 650. The normal keyboard handler
performs mute/unmute; the fixture does not write the sound-suppression flag. Only 0/1
are accepted. Fixture-off and normal build bytes have been compared unchanged.

For the larger-memory seeded weather test, request audio probes `$17836/$178e6` and
native toggle boundaries `$c5fc/$c600`. `check_weather_audio.py --require-mute CAPTURE...`
requires two native toggles, one suppressed weather call followed by two resumed starts,
and complete request accounting. This is directed input coverage, not audible-output
validation or proof that every mode's sound controls are framerate independent.

## Inspection

```sh
JOY0=none DETERMINISTIC=1 WARP=1 python3 tools/powerdrome.py serve
python3 tools/powerdrome.py shot tmp/now.png
python3 tools/powerdrome.py stop
python3 tools/powerdrome.py profile 10 tmp/trace.bin
python3 tools/powerdrome.py gdb 'dump binary memory tmp/slow.bin 0xc00000 0xd80000'
python3 tools/powerdrome_report.py tmp/trace.bin tmp/slow.bin
python3 tools/powerdrome.py quit
```

The server (`common/tools/game_server.py`) boots through `common/run.sh`, so the run options
above apply to `serve`; it occupies its terminal; issue clients from another. One
server/capture per instance (`INSTANCE`).
Local command requests carry an explicit byte-length header; the server reads exactly
that payload before dispatching it, even when the client keeps the connection open.
Debugger scripts also handle partial pipe writes. This matters for large read-only probe sets: a single socket read or
pipe write is not guaranteed to contain the whole script. `tools/test_command_transport.py`
checks fragmented requests, consecutive requests over named sockets, truncated payloads
and short pipe writes. Field captures report progress in 100-field
chunks without changing target state. Each chunk independently reads back its actual field
counter before reporting completion; an aborted debugger loop cannot count as a completed
window merely because its response lacks an uppercase error marker.

For reproducible captures unplug host inputs (`JOY0=none`, both device and mode) and avoid
interacting with the emulator. The debugger cannot write guest memory. `BOOT_BREAK` arms a
read-only breakpoint from reset, but must be calibrated against the current build/memory setup.
The x86_64 profiler window uses the existing single-attach LLDB workaround; its assertion
checks the write. Emulated time stops while attached. Screenshots come from trace captures.

The server, trace parser, OFS extraction and patch-list decoding are AmigaXDev's shared
`amigaxdev` package (`gdbserve`, `barto`, `adf`, `patchlist`); `tools/_amigaxdev.py` puts it on
the path under any `python3`. `tools/powerdrome.py` adds the request framing and long captures. The reporting locator has been adapted to Powerdrome's single hunk
and either the original or development slave.

`python3 -m amigaxdev.adf` lists/extracts the local disk image; `python3 -m amigaxdev.patchlist`
decodes original lists (AmigaXDev's shared package, on the path after sourcing `../../common/env.sh`).
See `docs/open-work.md` before interpreting a capture as a benchmark.

## Fixed attract-demo window

```sh
make verify
FIELDS=100 tools/fixed_window.sh tmp/prof/demo-a
FIELDS=100 tools/fixed_window.sh tmp/prof/demo-b
python3 tools/compare_traces.py tmp/prof/demo-a/trace.bin tmp/prof/demo-b/trace.bin
SWAP_ONLY=1 FIELDS=100 tools/fixed_window.sh tmp/prof/demo-swaps
```

The first run calibrates the relocated code address. Each measurement boot arms game `$1067e`
from reset, after the first animated-inset render. The name fixture lets the native menu reach
its idle timeout. `FIELDS`, `ANCHOR`, and `SERVE_WAIT` are overridable. An explicit second
argument selects the input slave. Captures retain the slave, initial memory, anchor registers,
trace, profile, frame report, first/last images, and final memory dumps. Do not touch inputs during captures.

This is the moving inset on the title screen; its pixel workload and playback timing differ
from racing. It advances the recorded camera by two samples per rendered frame. It is useful
for renderer bring-up, but cannot establish simulation correctness or full-screen racing FPS.

For the 68020 comparison (run sequentially, after the A500 capture):

```sh
source ../../common/env.sh
AMIGA_MODEL=A1200 CPU=68EC020 KICKSTART="$KICKSTART_A1200" CHIP_KB=2048 FAST_KB=4096 \
  EXTRA_ARGS=--slow_memory=0 FIELDS=100 tools/fixed_window.sh tmp/prof/demo-a1200
```

Add `SWAP_ONLY=1` to count the same marker with read-only debugger breakpoints instead of
instruction tracing. Compare the complete `demo frame completions per field` line, not just
rounded FPS. The trace comparator checks all initial chip RAM, instruction and DMA records,
and screenshots excluding only three rightmost host-border columns.

## Ten-second practice launch profile

```sh
make verify
WHD_ARGS=CUSTOM5=2 ANCHOR=0x14764 FIELDS=500 \
  tools/fixed_window.sh tmp/prof/practice-10s
```

The route submits Enter at name entry, then the native `3` shortcut for the top-middle
Practice button, then Space at the pit's input loop. The capture anchor is the first
iteration of the pit departure animation, after the Space handling and stationary delay.
The ship then flies onto the track automatically; host inputs stay disconnected.

The stock profiler command clamps requests to 100 fields. Back-to-back requests omit one
field at each boundary (confirmed using the game's VBL counter), so they do not make a
continuous trace. For requests of 101–500 fields, the harness lifts the command cap in the
current emulator process during its existing debugger attachment. It verifies the exact
instruction bytes before and after the change. The installed emulator file and guest game
code are not modified. This workaround is specific to the documented x86_64 emulator build.

The 500 fields are recorded in one request, giving ten nominal PAL seconds without internal
gaps. The output retains the slave, anchor/memory dumps, `trace.bin`, `profile.txt` and
first/last images. Routine boundaries in the generic report are inferred. For normal driving, `$bc7c` is the
presentation marker; `tools/perf_report.py` and the independent `SWAP_ONLY=1` counter use it.
Departure animations are not counted as driving frames. `tools/perf_status.py` checks the
optional renderer's pixel/state/guard counters and static-code integrity.

## Accelerator timing checks

The shared environment is sourced by `tools/fixed_window.sh` and the matrix runner.
Captures record the effective CPU/memory/options, slave/emulator/ROM hashes, emulator log
and optional final screenshot (`CAPTURE_SHOT=1`). The screenshot is taken after the measured
window and final memory dumps.

Use the release matrix above for current accelerator measurements. Cache selection
belongs to WHDLoad: supply standard `CACHE` or `DCACHE` tooltypes or launch arguments
(`WHD_ARGS` in the emulator runner). Neither normal nor VERIFY builds add a cache
policy or cache toggle. Shared KickEmu startup remains unmodified.
`CUSTOM4=1` enables drawing twins; `CUSTOM5=2` selects Practice.
`tools/perf_status.py CAPTURE` checks drawing diagnostics and reports the first register
mismatch when present. See [accelerator testing](accelerator-cache-testing.md) for measured
results and emulator limits.

## Gameplay coverage

`make build BUILD=coverage` produces a separate `tmp/build/coverage/Powerdrome.Slave`.
`CUSTOM5=3/4` replay native inputs in Practice or qualifying/racing respectively.
`CUSTOM5=5/6` select centering/acceleration cruise routes on the default course or track
index 2. The natural-weather twin capture uses the first effect draw (`$112f4`) as its anchor.
The fixture exercises views, overlays, pause, collisions, rescue, native pit repairs and
session transitions. Its controls and diagnostic counters are absent from ordinary
`release` and `verify` builds. Keep `CUSTOM4=1` for drawing equivalence checks.

Follow the [coverage checklist and commands](gameplay-coverage.md). Read-only execution
probes and state samples are enabled with `COVERAGE_PROBES` and `COVERAGE_STATE=1`.
The field counter saves progress in 2,000-field chunks without advancing the game between
chunks. Use `coverage_status.py --require-long` to reject missing scenarios and
`--require-effects` to require natural weather rendering. Always run `perf_status.py`
as well to check pixels, registers, CCR, scratch, guards and copied-code immutability.
Coverage timings are not performance results.

## Original/development loader comparison

`make build BUILD=original_verify` builds a separate input-only original-loader reference.
The ordinary `original` target remains byte-identical to the installed slave. Both VERIFY
variants share `src/verify_input.s`; the original reference always selects Practice.
`PROBE_OFFSETS` adds ordered read-only checkpoints before `ANCHOR` in the fixed-window
runner. `tools/compare_loaders.py ORIGINAL DEVELOPMENT` checks the register lifetime,
relocated code, state and bitmap evidence. See the [loader audit](loader-equivalence.md)
for exact reproduction commands, explicit allowances and measured timing differences.

### Fine mouse steering checks

After building, source `../../common/env.sh` and run:

```sh
python3 tools/check_mouse_math.py --ticks 30000
```

This uses the shared `AMIGA_UNICORN` library and vasm, creates its harness in
`tmp/mouse-steering/math/`, and reads the locally extracted game for native fallback
checks. The mathematical sine table is generated by the regular makefile; no game
bytes or generated test inputs are tracked.

For an in-game single-count mouse tape, build coverage with
`-DCOVERAGE_MOUSE_TEST=1 -DTIMING_SETUP_SEED=1234 -DTIMING_WORLD_SEED=1234
-DTIMING_PIT_SYNC_TEST=1`. Use `CUSTOM1=1 CUSTOM5=7`, driving anchor `$bc7c`,
500 fields, `MOUSE_STATE=1 TIMING_STATE=1` and
`COVERAGE_PROBES='0xccee 0xcedc 0xd058'`. The tape applies +1/-2/+1 counts on
both axes after the render-rate fixture activates. Compare an unpaced build with
`-DTIMING_RENDER_HZ_TEST=10` using `check_mouse_steering.py CAPTURE CAPTURE`.
The checker compares complete private and native mouse/matrix states at common
world steps, and requires visible matrix changes between control epochs.

### Mouse stick checks

```sh
python3 tools/check_input_axes.py
python3 tools/check_input_axes.py --baseline 9a249e5d
```

The first runs the enhanced input layer's actual assembly under the shared Unicorn
runtime (harness in `tmp/input-axes/`, no game bytes). It pushes the stick forward 5,000
counts, applies native contact damping forty times, then the native A reset, and requires
the private stick to return to zero. It also checks that counts queued before a reset are
discarded, that later counts are kept, and that 50,800 counts in one direction saturate
the raw and private stick at ±32,767 without wrapping. `--baseline` runs the same scenario
against `timing_input.s` from an earlier revision and reports the result; before the fix
the stick ends at +4,927 after A, reversed.

The 060 single-count mouse tape above also reproduces all 501 complete mouse/matrix
states of the capture recorded before this change (`tmp/mouse-reset/tape-060` against
`tmp/mouse-steering/current-060`).

### Track collision checks

```sh
python3 tools/check_collision_depth.py
```

Runs the crash-depth hook (`timing_collision.s`) under the shared Unicorn runtime for
20,000 random planes, saved positions and step distances (harness in
`tmp/collision-depth/`, no game bytes). It requires the native `BGT.S` outcome of the
distance before the step plus 18/4 of the step's travel, exact in 64 bits, and every
register kept. `check_mouse_math.py` covers the damped control update.

For the in-game dive, build coverage from a scratch copy of `src/` whose `CUSTOM5=11`
axes push the mouse −100 counts per field for fields 300–339 after the fixture epoch and
+50 for fields 1000–1019, with a tape that accelerates and then runs to field 1400. Capture
on the 060/50 with `ANCHOR=0xbc7c FIELDS=1300 TIMING_STATE=1` and probes `0xd058 0xccb2
0xccd0 0xfc9e 0x100c2`; run it with `CUSTOM1=0` for the original.

### Opponent movement checks

```sh
python3 tools/check_opponent_motion.py
```

Runs `timing_opponent_motion.s` under the shared Unicorn runtime beside the game's own
code hunk (`tmp/extracted/pd`, in memory only; harness in `tmp/opponent-motion/`). On
random path nodes it requires the native position, heading, segment and player distance
for 10,000 progress values, the native advance of the next update for 20,000 speed, fuel,
mode and damage-countdown combinations, and, over 300 sequences of native-style updates
with random ±40 nudges, lap wraps and repositions, that every update starts from its
authoritative progress and the shown progress never goes backwards within a lap or
reaches the lap line first. `VASM_EXTRA=-DTIMING_OPPONENT_MOTION=0` builds the previous
90-ms movement for comparisons.

Contact soak: the coverage race (060/50, `CUSTOM1=1 CUSTOM4=1 CUSTOM5=4 NoCache`,
`ANCHOR=0xbc7c FIELDS=66000 SWAP_ONLY=1 COVERAGE_STATE=1`) with
`COVERAGE_PROBES='0xd3d6 0xfc9e 0x9a80 0x9b14 0x9c84 0x9d04 0x9b6a'`: opponent updates,
track crashes, player contact, opponent–opponent slowdown, player knock, player damage and
opponent bounce. The emulator's debugger stub holds about 20 breakpoints, so these replace
the `--require-long` probe set rather than adding to it.

### Cockpit departure blending checks

```sh
make build BUILD=verify VASM_EXTRA=-DDEPARTURE_INTERPOLATE=0   # step-only reference
make verify                                                    # blended (default)
```

Capture each with `CPU=68030` (25 MHz) or `68060-NOMMU` (50 MHz), A1200, fast RAM,
`WHD_ARGS='CUSTOM1=1 CUSTOM5=2 NoCache' ANCHOR=0x1020e FIELDS=150 SWAP_ONLY=1
SWAP_MARKER=0x102d0 TIMING_STATE=1` and `COVERAGE_PROBES='0x1026c 0x10322 0x10336 0xca3e
0x8056'` (add `0xcedc` for world-step states). `check_departure.py
tmp/prof/timing-liftoff-a500-native CAPTURE...` checks the nine native states, the 100 ms
period and the final state; `0x8056` events count presentations. The `PDDEPI01` tag in the
slave (the last copy in `final-code.bin`) holds the last view cost in clock units, the
number of blended views and the number of steps; `-DDEPARTURE_DIAGNOSTICS=1` adds the
view-only and native-view costs.

### Pit arrival rise checks

```sh
make build BUILD=verify VASM_EXTRA=-DTIMING_RISE=0   # native rise reference
make verify                                          # paced and blended (default)
```

Capture each with `CPU=68060-NOMMU` (50 MHz), `68040-NOMMU` (25 MHz) or `68EC020`
(14 MHz), A1200, fast RAM, `WHD_ARGS='CUSTOM1=1 CUSTOM5=2 NoCache' ANCHOR=0x1455c
FIELDS=200 SWAP_ONLY=1 SWAP_MARKER=0xe296` after clicking Practice. The frame line shows
one completion per pit frame; the rise is the first run of them (15 steps over 70 fields
on the A500). The `PDRISE01` tag (the last copy in `final-code.bin`) holds the last extra
frame cost in clock units, the deadline, the number of extra frames and the number of
rises. `ANCHOR=0x145c0 FIELDS=2` stops at the rise's return to compare game state with
the reference.
