# Development

Project status: Phases A–E are complete within the agreed scope, with steady A500 handling and natural-weather validation deferred by the user. Neither deferred gate is counted as passed. Phase F is untouched.
See the [current handoff](open-work.md) for completed checks, open gates and resume priorities.

## Inputs and shared tools

Keep both supplied archives in ignored `tmp/`. Extract the installer to `tmp/installer/`
and Retroplay pack to `tmp/game/`; the playable tree is `tmp/game/Powerdrome/`.
`tmp/archive.sha256` records local input hashes. Never commit proprietary inputs or captures.

Source `amiga/env.sh` for the shared Amiga environment that AmigaXDev installs (`make setup`);
it sources the shared `env.sh`, whose variables AmigaXDev's `docs/environment.md` describes.
Shared inputs use these overrides:

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
assembler and Amiga include directory in the makefile; `WHDLOAD` also supplies the API headers
and KickEmu sources the slave builds with.

## Build and run

```sh
make -C whdload original
amiga/run.sh
SLAVE=tmp/build/Powerdrome-original.slave amiga/run.sh
```

`original` assembles with optimizations disabled and compares the entire result with the
installed slave. This is the reference reconstruction. `make -C whdload all` builds the WHDLoad 20 KickEmu
development slave with interface 17. `make -C whdload verify` additionally saves
`tmp/build/Powerdrome-verify.slave`; `CUSTOM5=1` submits an empty pilot name through the
native name-entry routine. `CUSTOM5=2` also selects Practice and submits Space in the pit.
`CUSTOM1=1` enables the optional fast planar renderer; it is off by default. The normal
build contains no input or twin-drawing fixtures. The slave requests 128 KiB of guest
expansion in addition to KickEmu's 256 KiB, including when the option is off. Slow-backed
expansion does not enable the renderer. See the [implementation and measured results](performance-implementation.md)
for supported states, diagnostic options and limitations. The [loader equivalence audit](loader-equivalence.md) verifies the tested startup/Practice
state and resolves Copylock D2, with explicit allocation and timing differences. Performance
A/B tests continue to use the same development loader.

To launch the new slave explicitly (the runner otherwise uses the installed original):

```sh
make -C whdload all
FAST_KB=4096 WHD_ARGS=CUSTOM1=1 SLAVE=tmp/build/Powerdrome.slave amiga/run.sh
```

The default machine is 68000, 512 KB chip and 1,536 KB slow with no fast RAM. The host boots
Kickstart 3.1 and Workbench 2.04 provides Assign for the original slave's Kickstart files.
Windowed, real speed, sound enabled. `CPU`, `CHIP_KB`, `FAST_KB`, `AMIGA_MODEL`, `EXTRA_ARGS`,
`WHD_ARGS`, `WB`, `SILENT`, `WARP`, `JOY0` and `JOY1` override the setup. `DEBUG` and `WARP` runs
are silent with the window behind the others; `SOUND=0|1` and `WINDOW=front|back|none` (none:
no video) choose explicitly.

### Phase B timing instrument

`make -C whdload coverage VASMFLAGS="-DTIMING_FULL=1 -DVERIFY_PHASE=1"`
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

`tools/baseline_matrix.py tmp/phase-b` runs the prescribed machine/cache/route matrix
sequentially using frozen slaves in that output directory; `--only REGEX` selects a
subset. Completed captures can be resumed. Incomplete captures require inspection
and a distinct retry directory. It stops on a native reference mismatch rather than
silently accepting new numbers. The A500 calibration supplies an exact 104/456 reference; M3 has no published
reference, so historical reproduction cannot be claimed for that machine.

To freeze a fresh matrix set (use a new ignored output directory):

```sh
set -e
source amiga/env.sh
out=tmp/phase-b-repeat
mkdir -p "$out"
for target in verify coverage; do
  make -C whdload "$target" VASMFLAGS=
  cp "tmp/build/Powerdrome-$target.slave" "$out/$target.slave"
  make -C whdload "$target" VASMFLAGS=-DTIMING_FULL=1
  cp "tmp/build/Powerdrome-$target.slave" "$out/full-$target.slave"
done
make -C whdload coverage VASMFLAGS="-DTIMING_FULL=1 -DVERIFY_PHASE=1"
cp tmp/build/Powerdrome-coverage.slave "$out/full-phase.slave"
make -C whdload all
python3 tools/baseline_matrix.py "$out"
python3 tools/baseline_matrix.py "$out" --report
python3 tools/baseline_matrix.py "$out" --gates
```

For B3, generate a listing with the exact uninstrumented full-verify flags:
`make -C whdload verify VASMFLAGS="-DTIMING_FULL=1 -L ../tmp/phase-b/full-verify.lst"`.
Compare that slave with the frozen `full-verify.slave` before capturing. Then
`phase_report.py CAPTURE --world-listing tmp/phase-b/full-verify.lst` attributes
instruction costs from world-step entry through the committed world-clock update.
The listing reader accepts VASM’s Latin-1 text and checks the live game patch targets.
The B3 capture uses M1, 100 fields, `SWAP_ONLY=0`, anchor `$bc7c`, and
`WHD_ARGS="CUSTOM5=2 NoCache CUSTOM1=1 CUSTOM3=1"`. Costs include interrupts;
frame allocation, rendering/HUD-owned work and the post-commit restore tail are outside
that explicitly bounded body. B3's fps decision uses the uninstrumented 500-field
matrix, which includes all costs.

### Phase C buffer audit

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

### Full timing development configuration

```sh
make -C whdload coverage VASMFLAGS='-DTIMING_FULL=1'
```

This selects the fixture-free cadence2 feature set: periodic controls, orientation,
historical input, engine, WORLD/WORLD20, repair/drop and weather effects/fade/cycle.
All test defaults are zero and seed defaults are -1 (native initialization). Add the
retained VERIFY-only pit-sync, stall, render-rate or seed options explicitly for Phase E.
Individual feature flags still work without the umbrella; WORLD requires WORLD20 and
repair requires drawing suppression. Explicit per-feature overrides retain the existing
dependency checks. Normal `make -C whdload all` is unchanged; promotion/defaults are Phase F.
The Phase A full/normal byte-equivalence checks are recorded in [open work](open-work.md).

### Verification-only guest chip-memory override

`make -C whdload verify VASMFLAGS='-DVERIFY_CHIPMEMSIZE=1048576'` exposes 1 MiB
of guest chip memory to exercise native resources unavailable in the normal 512-KiB
configuration. Use a host with at least `CHIP_KB=1024`; the default A500 timing-matrix
case supplies only 512 KiB and cannot run this artifact. `CASE_SET=weather-audio` selects
030/fast and a 1-MiB-chip A500 for a frozen larger-memory coverage slave. Use
`TIMING_EXTRA_PROBES='0x17836 0x178e6'` for the read-only audio call checks. Freeze the verification slave
under `tmp/` before restoring `make -C whdload all`.

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

The server occupies its terminal; issue clients from another. Only one server/capture per repo.
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
decodes original lists (AmigaXDev's shared package, on the path after sourcing `amiga/env.sh`).
See `docs/open-work.md` before interpreting a capture as a benchmark.

## Fixed attract-demo window

```sh
make -C whdload verify
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
source amiga/env.sh
AMIGA_MODEL=A1200 CPU=68EC020 KICKSTART="$KICKSTART_A1200" CHIP_KB=2048 FAST_KB=4096 \
  EXTRA_ARGS=--slow_memory=0 FIELDS=100 tools/fixed_window.sh tmp/prof/demo-a1200
```

Add `SWAP_ONLY=1` to count the same marker with read-only debugger breakpoints instead of
instruction tracing. Compare the complete `demo frame completions per field` line, not just
rounded FPS. The trace comparator checks all initial chip RAM, instruction and DMA records,
and screenshots excluding only three rightmost host-border columns.

## Ten-second practice launch profile

```sh
make -C whdload verify
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

```sh
source amiga/env.sh
make -C whdload verify
tools/accelerator_matrix.sh timing tmp/prof/accelerator-matrix
make -C whdload all
```

Use fresh output directories. Each matrix freezes its input slave and runs sequentially.
Cache selection belongs to WHDLoad: users can supply its standard `CACHE` or `DCACHE`
options through tooltypes or launch arguments (`WHD_ARGS` in the emulator runner).
Neither normal nor VERIFY builds add a custom cache policy or cache toggle. Shared KickEmu
startup remains unmodified. The timing matrix explicitly supplies `NoCache` to keep its
uncached comparisons reproducible; ordinary launches preserve the user's WHDLoad options.
`CUSTOM4=1` enables drawing twins; `CUSTOM5=2` selects Practice.
`tools/perf_status.py CAPTURE` checks drawing diagnostics and reports the first register
mismatch when present. See [accelerator testing](accelerator-cache-testing.md) for measured
results and emulator limits.

## Gameplay coverage

`make -C whdload coverage` produces a separate `tmp/build/Powerdrome-coverage.slave`.
`CUSTOM5=3/4` replay native inputs in Practice or qualifying/racing respectively.
`CUSTOM5=5/6` select centering/acceleration cruise routes on the default course or track
index 2. The natural-weather twin capture uses the first effect draw (`$112f4`) as its anchor.
The fixture exercises views, overlays, pause, collisions, rescue, native pit repairs and
session transitions. Its controls and diagnostic counters are absent from ordinary
`all` and `verify` builds. Keep `CUSTOM4=1` for drawing equivalence checks.

Follow the [coverage checklist and commands](gameplay-coverage.md). Read-only execution
probes and state samples are enabled with `COVERAGE_PROBES` and `COVERAGE_STATE=1`.
The field counter saves progress in 2,000-field chunks without advancing the game between
chunks. Use `coverage_status.py --require-long` to reject missing scenarios and
`--require-effects` to require natural weather rendering. Always run `perf_status.py`
as well to check pixels, registers, CCR, scratch, guards and copied-code immutability.
Coverage timings are not performance results.

## Original/development loader comparison

`make -C whdload original-verify` builds a separate input-only original-loader reference.
The ordinary `original` target remains byte-identical to the installed slave. Both VERIFY
variants share `whdload/verify_input.s`; the original reference always selects Practice.
`PROBE_OFFSETS` adds ordered read-only checkpoints before `ANCHOR` in the fixed-window
runner. `tools/compare_loaders.py ORIGINAL DEVELOPMENT` checks the register lifetime,
relocated code, state and bitmap evidence. See the [loader audit](loader-equivalence.md)
for exact reproduction commands, explicit allowances and measured timing differences.
