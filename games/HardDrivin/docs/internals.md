# Hard Drivin’ internals

The source declares version 3.0, WHDLoad interface 16, KickEmu `kick13.s`,
512 KiB chip memory and 512 KiB game expansion memory. The shipped slave header
requires 768 KiB expansion memory including the Kickstart allocation.
It enables CACHE, BOOTEARLY, CBDOSLOADSEG, HDINIT and SETPATCH.
`slv_CurrentDir` is `data`; the LoadSeg callback recognizes `HardDrivin`.
The installed executable is 81,656 bytes. The shipped slave is 8,428 bytes.

CUSTOM2 controls the existing frame delay; zero is maximum speed. F10 is the
source’s quit key. Existing code handles loading, keyboard, CPU delay loops,
self-modifying graphics/text routines and high scores. Version 3.0 fixes the
SPS 0126 keyboard handling. The supplied installation is the SPS 0126 variant.

4.0b's slave keeps no arrays: they are allocated at install (exec AllocMem, cleared), only
for CUSTOM1 nonzero. `_time_install` allocates `_time_mem` (layout `TM_*` in
`HardDrivinTime.s`): the engine power table that `_phase_power_build` computes (8 KB, the
assembled table's bytes exactly), the record and replay pose frames, the mouse ring and the
loop's road points; without it CUSTOM1 acts as 0. The others are `_depth_mem` (depth
order), the record's pending samples and the traffic lists. Small state structs stay in the
slave, several behind the signatures the capture tools search for.

The local build uses shared WHDLoad 20.0 KickEmu sources. Its successful assembly
is not evidence of gameplay equivalence to the shipped slave. The attract route and A500 performance baseline are now validated below. The
player-physics time model is documented in GAME_TIME.md; the full step-2 machine
matrix and 68020 costs are now measured in PERFORMANCE.md. No performance
optimization has been made.

## Profiling calibration

The SPS 0126 live decompressed code has size $11a4e. The slave publishes the
code-start pointer followed by this size; verify the executable JMP at that
pointer when locating it in a slow-RAM dump. Game code uses a4-relative globals
and `link a5` function prologues. Offsets use this decompressed code origin.

The title wait at $08520 calls the keyboard reader, tests its result, then tests
the mouse-button word at a4-$6a0a and loops. On the observed untouched boot the
word was zero. No timeout appears in that wait loop. Whether a screenshot key
advanced the user's original run needs confirmation.

The VBL service at code $00044 writes the display pointers. At $000a4 it reads
a pointer from a4-$703e and tests its byte; when set, $000b4–$000be exchange the
buffers at a4-$6a12 and a4-$6a0e. This frame-publication counter is validated by an independent read-only
breakpoint run: all 129 swaps match the full trace field-for-field. The pointer writes at $000e0 onward
also occur when no swap happens, so counting those writes alone is incorrect.

Short x86_64 Barto calibration traces contain real instruction PCs, 142102
CPU clocks per steady PAL field, and a header base clock of 28375160. The host capture-length control is now validated: a one-shot host breakpoint
sets the requested field count after the command clamp and before recording.
Lengths are passed explicitly as hexadecimal to LLDB; the saved trace header
is checked. This changes only profiler control, not guest execution or the
installed emulator binary.

## Validated attract window

Anchor $10844 follows the initial eight-step dissolve. Profiling begins on the
next PAL field boundary, within one field. The first clean scene matches the
user's `FS-UAE_Full_261011-0114_02.png` game area pixel-for-pixel. VERIFY_ATTRACT
supplies one space on the first empty title-keyboard poll at $08520; only that
six-byte startup call/test sequence is replaced, and normal builds exclude it.

Two 1,000-field captures are identical in every instruction, DMA record and
screenshot, and in full chip/slow RAM before and after the capture. Elapsed time
is 20.031887 seconds (142,102,000 clocks at 7,093,790 Hz). There are 129 displayed
frames, 6.4397 FPS over the window; the first-to-last-swap rate is 6.4609 FPS.
Frame intervals are 6–11 fields. The demo continues driving while its high-score
text overlay scrolls in at about ten seconds; this is part of the benchmark.

The largest call-target-aware self group is game $0329a (20.15%). Vertex rotation
at $02a2e uses 7.94%; fill code at $03a28 uses 6.85%. Complete self/inclusive
attribution is in `tmp/prof/attract-a500-run1/routines.txt`. The existing slave's
blitter-check/wait routine occupies 2.657% of the measured clocks, including
1.729% in its polling/CIA-wait body. No STOP or missing-PC cycles were observed.
See `tmp/prof/benchmark-report.txt` for configuration, evidence and limitations.

## Rendering and timing reference

The tracked `docs/PERFORMANCE.md` records the verified planar
CPU renderer, measured per-profile memory placement, frame-stepped attract movement and
VBL-driven clocks. Player-physics timing remains unresolved. Refer to that file
for code offsets, evidence limits and the equivalent-scene comparison requirement.

## Normal rebuild versus shipped slave

The normal build (no VERIFY defines) and shipped slave both occupy 8,428 file
bytes and load the game and globals at the same addresses in the A500 setup;
no padding was needed. Both use the same native raw-space input at the title
poll. The Barto stub silently ignores guest register/memory writes, so input
was written through the host debugger with guest readback before resuming.

`tmp/prof/equivalence-{original,rebuilt}-fields-v4` retain 1,001 VBL-entry samples
covering 1,000 fields after the first-cockpit anchor. The sampled globals cover
`a4-$6800` through `a4+$100`; both complete 32,000-byte planar buffers are retained.
The earlier calibration directories are failed/incomplete experiments, not evidence.

Functional attract outcomes match: identical sequences of 130 distinct sampled
position/orientation states and 129 stable full screen images. A stable image
means a buffer is unchanged for at least five consecutive sampled VBLs; both
buffers are examined. Pose observation differs by at most one field. See
`equivalence-outcomes.json` and `equivalence-comparison.json`.

This is NOT cycle-exact/per-field whole-memory equality: 626 globals snapshots
and 513 buffer snapshots differ, including renderer workspace and partially drawn
back buffers. The decompressed game differs at 36 bytes, all in slave patch-call
targets; the main game layout is the same. The normal rebuild uses current shared
KickEmu includes and differs from the shipped slave binary. Do not attribute these
small timing differences to a performance patch or silently discard them.
Clocks lie outside the sampled globals interval; this check does not establish
per-field clock equality or player-physics equivalence. The initial attract
state and functional output sequence establish functional attract equivalence; use the
rebuilt baseline for subsequent patch comparisons. This is not a claim that the
shipped and rebuilt slaves have identical per-field execution.

## VERIFY_DRIVE input tape and gameplay windows

Step 1 items 1–3 are complete for the fixed A500 baseline. The only committed
changes are the VERIFY_DRIVE hooks and source input fixture; no performance patch
is included. The normal binary matches the rebuild used for equivalence exactly,
and VERIFY_ATTRACT matches the previous attract capture binary exactly.

`HardDrivinVerify.s` is included only with VERIFY_DRIVE. Both VERIFY modes together
are rejected at assembly time. Only SPS 0126 (`_pl0_v1`) is patched; the second
variant is unchanged. Hook ranges are marked with PERF_RANGE in the main source.
The native VBL input accumulation is followed by absolute X/Y/button publication
at game $003d8. The keyboard hook at $01382 is the return from $01212, and supplies
a pending decoded key only when the native reader has no key. Native title entry
at $08520 arms the menu tape; $10ecc establishes the first-race epoch after its
displaced native button reset and mouse centring calls.

Fixture state layout: phase.w, key-overflow.b, reserved.b, field.l, next-record.l,
X.w, Y.w, buttons.w, pending-key.w (20 bytes). Phase 0 is idle, 1 menus, 2 gameplay.
Field 1 is the first VBL after arming an epoch. The gameplay counter is never reset
by crash/replay recovery. Each 12-byte record contains field.l, X/Y.w, buttons.w and
decoded-key.w. Values hold until the next record; field $ffffffff ends the tape.
A nonzero overflow byte fails acceptance. The 97 gameplay records are field-indexed,
not rendering-pass-indexed. No guest code, car pose, speed, gear, checkpoint,
collision or replay state is injected during replay of the frozen fixture.

Controls: X=320 is centred, Y=200 held; native button word 4 increases throttle,
1 decreases throttle, 5 brakes, and 0 releases buttons. Releasing buttons does
not cut the throttle, but it is necessary before instant replay because a held
button skips playback. Menus use one decoded space then a held native click to
select automatic transmission. The fixture runs with both host input ports off.

The route first reaches the main checkpoint at field 1198. An initial approach
crash (2095–2254) and full replay (2255–2917) position the car by native recovery;
this transition is deliberately outside both benchmark windows. The successful
second approach stays on the ramp, reaches its lip at field 4364 (position
31873,189,17363), and becomes airborne beyond it with zero wheel contacts and
height above 190. The landing collision begins at field 4553. All countdown
values 25 through 1 are observed, followed by replay 4749–5504 (90 iterations),
then native recovery. The acceptance script checks the road geometry at the lip
and airborne motion; passing beside the ramp does not qualify.

Windows are half-open intervals between AFTER-publication VBL samples at $003f2:

| Window | Fields [first,end) | Duration | Swaps | Physics returns | Replay iterations |
|---|---|---:|---:|---:|---:|
| A: straight/checkpoint | [1,1251) | 25.039859 s | 108 | 108 | 0 |
| B: stunt/jump/crash/replay | [3000,5600) | 52.082906 s | 325 | 235 | 90 |

These are fixture baselines (4.3131 and 6.2401 whole-window FPS),
not performance improvements. Physics counts are returns at $0cdae; they include
native passes during crash/recovery and are not a count of independent fixed ticks.
A swap at $000b4 precedes input publication in the next VBL; its logged counter
still names the interval that started at the previous $003f2 boundary.

`tmp/prof/drive-a500-jump1` and `drive-a500-jump2` are the accepted fresh-boot pair.
All 6,000 per-field global dumps (a4-$7100 through a4+$100, end exclusive), complete
32,000-byte front buffers and 20-byte fixture states match exactly. All swap,
physics-return and replay-iteration event sequences match too. Globals include
pose, controls, velocities, clocks, crash/replay state and replay-ring contents;
this is not an assertion that all Chip/slow memory or instruction traces match.
Each window's concatenated-state/image/tape SHA-256 is in `windows.json`.
`state-summary.json`, `capture.json`, `capture.log`, source-matched slave copies,
and decoded front-buffer images retain the evidence. Input/output paths are local
and ignored. Calibration directories, `drive-a500-run{1,2}` (side-of-ramp departure)
and `drive-a500-ramp1` (opposite-side departure) are NOT accepted jump evidence.

The original physics is still rendering-pass-dependent. Identical field-indexed
inputs on another CPU can produce a different route. These windows have only been
validated on deterministic PAL A500/68000, 512K Chip + 1536K slow, no Fast RAM,
PRELOAD and CUSTOM2=0. Full machine-matrix/menu calibration, controlled timing-coupling tests,
per-physics-step state capture and timing decoupling remain future work.

## VERIFY_SLOW / CUSTOM4 delay instrument (step 1 item 4)

Build with `-DVERIFY_SLOW=1`; combine with VERIFY_DRIVE or VERIFY_ATTRACT, or use
manually. CUSTOM4=0 installs neither hook. Nonzero CUSTOM4 values add that many
VBL transitions before each completed frame is marked ready, saturating at 255.
The option is developer-only and is absent from the normal build and user option
list. CUSTOM2 retains its original meaning. Only SPS 0126 is instrumented; the
other code lengths skip installation. The existing final cache flush follows the
additional patch writes.

The independent 32-bit counter increments at $003e2, replacing three palette
writes that are faithfully re-executed. This is separate from VERIFY_DRIVE's title
and race epochs. The $00756 hook runs after the original $00740 wait and before
the ready-byte store. It polls counter changes, using DBF for the bounded count,
then executes the displaced `move.b #$ff,-$69ff(a4)`. No STOP, host-time sleep,
physics/state mutation or field-counter reset is used. Input and clocks continue
through native VBL processing. CMP/DBF preserve X, and the native final MOVE sets
NZVC. Counter equality polling handles the 32-bit wrap without signed arithmetic.
All callers of $00750 are slowed, including menus, attract, gameplay and replay.

Native emulator checks (`slow-unit-*`) cover CUSTOM4=0, 1, 4, 255 and 256.
Zero retains the original six bytes at both patch ranges. Six submissions each
at 1 and 4 waited exactly N counter transitions; two each at 255 and 256 waited
255. The ready byte remained zero until publication and became 255 afterward.
D0–D7, A0–A6 and the expected stack balance match across the call. Raw SR readings
are retained but are not used as CCR evidence: debugger SR observations differ
from the final MOVE's expected flags. CCR preservation is established by the
instruction sequence, not by these SR snapshots.

Gameplay evidence covers [1,1251), the same 1,250-field measurement interval:
CUSTOM4=0 produced 108 swaps and 108 physics returns; CUSTOM4=4
produced 75 swaps and 75 physics returns. Two fresh slowed boots
(`slow-drive-four1`, `slow-drive-four2`) match all 1,251 captured per-field global,
front-buffer and fixture-state snapshots, plus every recorded event and timing.
`slow-drive-zero` is the off run. The slowed tape collides at field 594, runs
the crash countdown through 1009, then skips replay with its still-held button.
Thus these counts describe different scenes, not an isolated renderer-cost
comparison; direct hook checks establish the N-field delay. See `tmp/prof/slow-delay-results.json` for counts
and hook checks. The existing normal, VERIFY_DRIVE-only and VERIFY_ATTRACT-only
binaries are byte-identical to their accepted pre-instrument baselines. Manual
VERIFY_SLOW and VERIFY_SLOW+VERIFY_ATTRACT build successfully as well.

These checks validate the slowdown instrument, not frame-independent physics or
the full step 3 timing model. A field-indexed tape delivers a different sequence
of inputs per physics step when drawing is slowed; per-step comparisons must
account for that. Do not require the unchanged tape to reach the same checkpoint
or jump at the original field number when CUSTOM4 is nonzero.

## Step 1 machine/state harness (2026-10-11)

Local `machine_profiles.py`, `capture_session.py` and `game_image.py` now supply a
single calibration path to `capture_demo.py`, `count_demo_swaps.py`,
`state_fields.py` and `capture_disabled.py`. Each capture retains its exact slave,
input hashes, effective emulator configuration, loaded hunk images and metadata.
Calibration discovers the slave's published (code start, $11a4e length) pair in
configured memory, checks a native code signature, reads the relocated A4 setup
operand at code+$11a76, and follows the LoadSeg link for the last BSS hunk. It then
reboots with the requested game-relative breakpoint armed before guest execution.
No cached absolute address or guest register/memory write is used.

The local executable is a normal three-hunk executable: full code allocation
$12d3c, globals allocation $7ccc (only $f44 initialized), trailing BSS 4 bytes.
The published $11a4e is the main engine extent, not the full code allocation.
A4 = globals base+$7ffe. The full code includes the C runtime after the published
extent. This distinction matters for relocation-aware comparisons and range checks.

Named profiles are a500 (512 KiB Chip/1536 KiB slow), a500-fast (512 KiB Chip/2 MiB
Fast), a1200-020 (68EC020, 2 MiB Chip/4 MiB Fast), a1200-030-50 (68030/50, same
memory), a4000-040-25, a4000-040-40 and a4000-060-50 (NOMMU, 2 MiB Chip/8 MiB Z2
Fast plus the model's explicit 8 MiB motherboard Fast). Fixed-frequency profiles
use real speed, multiplier 0 and CPU/memory cycle-exact timing. Slave cache policy
is unchanged; the separate step-2 WHDLoad cache logs record actual CACR. Above 020, `capture_demo.py`
automatically uses breakpoint counts. `--swap-only` or SWAP_ONLY=1 also selects
counts. SERVE_WAIT defaults to 300 seconds on trace profiles and 600 above 020,
with an environment override. All requested settings and actual `emulator.uae`
files are retained; the default A4000 motherboard bank is included in calibration.

Seven independent 100-field counter smoke runs reached the clean cockpit anchor
$10844: swaps 15/15/45/65/57/57/58 in the order above. These are harness tests,
not step 2 baseline FPS figures. The A500 per-field sequence exactly matches the
first 100 fields of the accepted 1,000-field attract instruction trace. Evidence:
`tmp/prof/matrix-*-smoke`, aggregate `step1-matrix-smoke.json`.

`state_fields.py` anchors native gameplay at $10ed4. It saves the whole allocated
globals hunk plus the final BSS (31,952 bytes per snapshot), first at each VBL
ENTRY ($44) and separately at every $cda4 common return ($cdb0, before RTS).
It captures N+1 boundary samples for N elapsed fields and records the preceding
field boundary for each physics return. VBL sample 0 precedes race field 1's
input publication: do not silently compare it with the old AFTER-publication
$3f2 window boundaries. Physics-domain comparisons align by completed call index;
VBL-domain comparisons align by boundary index. The JSON convenience view covers
pose/angles, velocity/speed, gear/throttle, native mouse/buttons, clocks, replay
pointer/mode, crash counter and the RNG state. Raw full-hunk bytes remain authoritative.

The random recurrence at $a36 uses the longword a4-$6fc4: if nonzero, multiply by
31415926, add 1, arithmetic-shift right 8 and store it. This known RNG state remains
zero throughout both measured gameplay runs; capturing it does not prove active
randomness, nor complete identification of every possible randomness source.
The complete globals/BSS capture avoids limiting comparison to identified fields.

Two fresh full runs (`state-a500-full1`, `state-a500-full2`, 6,000 fields each)
match every byte in all 6,001 VBL snapshots and 551 physics-return snapshots.
Both include the checkpoint, jump, collision, crash countdown and replay. This
adds the requested physics-exit and VBL-entry domains to the previously accepted
window/image/tape evidence; it does not assert equivalence across different CPUs.

`compare_state.py` ports Their Finest Hour's generic full-hunk comparison, with
metadata-derived region bases/sizes. Default comparison is strict. `--relocate`
accepts even-aligned longwords only when both point into the same named game hunk
at the same relative offset. It reports raw equality separately. This heuristic
must not be used to mask unexplained scalar differences; same-build/same-profile
repeats should use strict mode. Missing snapshots, incompatible schemas and wrong
lengths fail; differing state exits nonzero. Unit checks exercise relocations,
wrong target regions, changed scalar bytes, truncation and missing sample sets.

`check_disabled.py` reads every source PERF_RANGE declaration, builds expected
bytes from the pristine executable and its relocation records, checks complete
instruction ranges, and compares the retained live code hunk. Enabled gates must
be explicit; overlapping title fixture ranges are skipped together when either
fixture is enabled. Seven attract-profile range checks pass with VERIFY_ATTRACT
explicitly enabled. Omitting that gate fails, and flipping a disabled-range byte
fails. It also rejects changed pristine-file hashes and truncated code dumps.
`capture_disabled.py` supplies a fresh boot at $8520 for normal/manual builds.
All tools, binaries, traces and raw game content remain under ignored tmp/.

The 100-field 68EC020 trace (`trace-a1200-020-smoke`) contains instruction records
and all 45 swaps match `matrix-a1200-020-smoke` field-for-field. Its Barto header
cycle unit is 128 versus the A500's 256: the old fixed 7 MHz conversion incorrectly
reported double elapsed time. The summary now converts elapsed cycles using the
retained cycle unit and checks the result against PAL field duration. Both profiles
report 2.003188704 seconds for 100 fields. This trace has 99.9999859% cycle coverage;
its metadata records the independent frame-counter validation.

Fresh normal and VERIFY_SLOW-manual/CUSTOM4=0 builds (`disabled-normal-final`,
`disabled-slow-zero-final`) pass every declared range with no enabled-gate skips.
Normal, attract, drive and slow+drive rebuilds remain byte-identical to the preceding
builds; this step's tracked edits are comments only. Six local failure-path tests pass.

The additional 68040-NOMMU clock sanity control (`clock-040-8-check`, using the
same memory layout and 100-field attract interval) produces 54 swaps at 8 MHz
versus 57 at 25 MHz. Timing responds to CPU frequency. Equal 25/40 MHz totals in
these short smoke windows do not establish a bottleneck; leave that attribution
for step 2's full profiles/ceiling tests. `step1-clock-sanity.json` records the check.
