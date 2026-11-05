# Step 5 capacity profile and interval plan

**Current C4 disposition (2026-10-13): assessment complete with documented open
cases; full acceptance is not passed.** Retain the 200 ms A500 path; no
performance-triggered fallback to the original loop. Normal demo passes; dense
pack and centered native-grid regressions need work. See the final closeout
section and `manifest/step5-c4-open-cases.json`. Candidate remains default-off.
Earlier dated sections below are the measurement/decision history.

Date: 2026-10-12. Scope: SPS 0481, PAL, stock 68020 (A1200, 2 MiB chip) and
68020 + 4 MiB Fast, automatic no-input demo, drawing omitted, CUSTOM1=1.
Profiled build: the live elapsed-time diagnostic `tmp/build/step5-elapsed/fine.slave`
(sha256 `0cf9b1b9…cb52`), the same binary that `STEP5.md` reports at 58.09/45.47 ms.
No ordinary source or release change. All cycle numbers are 14.18758 MHz CPU
cycles per complete adapted update, including chip-bus waits, unless marked.

## Selected design (2026-10-12)

| Machine class | Update interval | Opponents |
| --- | --- | --- |
| 68020 or better **with Fast memory** | **20 ms** | 14 MHz 68020: native 100 ms step on the pulse quantum (Plan B). Opponents at 20 ms only after the escalation gate below passes for that profile. |
| 68020 or better **without Fast memory** | Coarse path: native 100 ms step | Native, together with the player |
| 68000, including A500 + Fast | Converted **200 ms** (current user decision, 2026-10-13) | All eight cars converted; native-tenth events receive two eligible pulses |

The user selected the Fast-memory rule and Plan B. C3 tested native 100 ms
on the A500 and failed capacity. The user subsequently authorized converted
200 ms C4 and now requires retaining that design while documenting cases
that need work; those cases must not trigger a return to the original loop.

This replaces "20 ms on every 68020+" and "68000 interval to be chosen". Stock
68020 without Fast memory is no longer a 20 ms profile. Its new-mode capacity
gate is the coarse-path gate. 030/040/060 follow the same rule but stay deferred;
the new mode is enabled only on profiles that have passed their gates.

## Method

`tools/capture_step5_profile.py NAME` boots with warp, leaves warp at car update
125, runs to loop 132 (scheduler already in debt, so it never idles in its wait
loop), removes all breakpoints and records a 48-field full instruction trace
(`monitor profile`). Analysers, all reading `tmp/step5/NAME/detail.bin`:

- `analyze_step5_profile.py NAME` – per-owner cycles (native groups / probe labels).
- `percar_step5_profile.py NAME LO HI` – per-car split using the native car-loop
  head `$671b6` (cars 7..0, then post-loop) and cost classes below.
- `classify_step5_profile.py NAME LO HI` – per-label split of probe code.
- `traps_step5_profile.py NAME LO HI` – WHDLoad privilege-trap count by trapping hook.

`LO HI` is the WHDLoad exception-handler range: `1b0f50 1b1540` on stock 020,
`5b2f50 5b3540` on 020 + Fast. Classes: **native** (game code plus the
native-equivalent division/square-root helpers), **conv_helper** (FF1* 20 ms
conversion modules), **hook_body** (ownership, context lookup, guards),
**trampoline** (`movem.l d0-d7/a0-a6` save/restore and CCR restore), **trace**
(record writes, identified dynamically by destination register inside record
buffers, plus record/snapshot labels), **sr_trap** (`move.w sr,-(sp)` plus the
WHDLoad handler it invokes).

Instruction attribution is exact per traced instruction. Record classification is
a source-line heuristic; its small misclassification moves cycles between trace
and hook_body only. Windows: 15/19 complete updates (original), 20/25 (CCR build).

## Findings

### 1. The largest overhead is privilege-trap emulation, not tracing

Every hook trampoline saves flags with `move.w sr,-(sp)`. On 68010+ this
instruction is privileged in user mode; WHDLoad's vector-$20 handler
(`$1b1442..$1b1510`) decodes and emulates it. Measured: **235 traps per update,
~873 cycles each, 219,846 cycles (25.4%) per update on stock 020**; 248 traps /
150,770 cycles (22.3%) on Fast. Steering filter hook `$6773c` alone traps 16 times
per update (twice per car).

All restores are `move.w (sp)+,ccr`, so `move.w ccr,-(sp)` (68010+, unprivileged,
same size and encoding length) is semantically identical. One-change measured A/B,
same layout (131 bytes differ):

| Profile | Original | `move ccr` | Saving |
| --- | ---: | ---: | ---: |
| 68020 | 864,705 cyc = 60.95 ms | 640,022 cyc = 45.11 ms | −224,683 (−26.0%) |
| 68020 + Fast | 676,443 cyc = 47.68 ms | 523,218 cyc = 36.88 ms | −153,225 (−22.7%) |

The CCR variant also passes the full 100-update elapsed-timer and state-replay
oracles on both profiles (2.000 s simulated, 20 pulses, all records and four native
checkpoints). Its elapsed-capture mean falls from 58.09/45.47 to **43.27/35.66 ms**.

Production 68020 code must never execute `MOVE SR,<ea>` in user mode. 68000 code
may keep it (not privileged there), but `move ccr` cannot be used on 68000; select
by CPU at patch time or avoid saving flags where they are dead.

### 2. Cost breakdown after the CCR fix (stock 68020)

| Segment | native | conv_helper | hook_body | trampoline | trace | total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| pre-car (main loop) | 22,870 | 357 | 1,282 | 331 | 747 | 25,929 |
| each opponent (car 7..1, mean) | 32,821 | 9,887 | 17,362 | 4,104 | 5,721 | 69,987 |
| player (car 0) | 39,291 | 10,243 | 19,564 | 4,864 | 6,308 | 80,365 |
| post-car (contact etc.) | 35,449 | 872 | 1,462 | 616 | 5,027 | 43,814 |
| **total** | **327,361** | **80,686** | **143,845** | **34,545** | **52,135** | **640,022** |

Fast profile totals: native 302,949, conv_helper 53,928, hook_body 102,266,
trampoline 33,240, trace 29,784; total 523,218.

Notable items inside these classes (stock, per update):

- Division helper `FF1Divide020/DivDone/DivRestore`: 33.8k (≈113 calls × 300 cyc;
  the `divs.l` itself is ~12k, the rest is call/restore overhead).
- Post-loop pairwise contact routine `$68d4e`: 27.7k (28 car pairs).
- Remaining software multiply `$29500`: 22.0k; sin/cos `$24fe0`: 12.7k.
- StingRay WaitBlit replacement `$83b46` spinning on blitter busy: 7.7k inside the
  "logic-only" update (residual UI blits still owned by the update).
- Per-hook context recomputation: `velocity_context` 5.4k, `bridge_context` 4.3k,
  `heading_context` 4.0k, `velocity_speed_array` 1.9k.
- Square roots for speed feedback: `FF1SquareRootU64` 7.4k + `U32` 6.0k + table 6.3k.
- `events_snapshot` (pure diagnostics) 9.9k; ~29 hooks per car.

### 3. Even zero-overhead conversion does not fit 20 ms for eight cars

Budgets at 14.18758 MHz (one quantum = 283,752 cycles):

- **G1 – keep pace, no drawing, 10% margin for contact/IRQ:** ≤ 255,000 cycles (18.0 ms).
- **G2 – step-5 rendering floor with today's renderer:** presentation cost per
  frame is R = 143.63 − 52.68 = 90.95 ms (stock), 87.94 ms (Fast) from GAME_TIME.md.
  Keeping 5.54 FPS needs logic ≤ 20 × (1 − 5.54 R / 1000) ms per quantum:
  **≤ 9.92 ms = 140,800 cycles (stock), ≤ 10.26 ms = 145,600 cycles (Fast).**

The native-equivalent work alone (327,361 cycles) is already 115% of the whole
quantum before any conversion, hook or drawing cost.

## Plan A – all eight cars at 20 ms (kept as the escalation target)

Cumulative projections for stock 020; each step needs a matched A/B before the
next. Measured values are marked (m); others are estimates from the profile.

| Step | Change | Δ cycles | Cumulative | ms |
| --- | --- | ---: | ---: | ---: |
| A0 | Current elapsed diagnostic (m) | | 864,705 | 60.95 |
| A1 | `move.w ccr` in all 020 trampolines (m) | −224,683 | 640,022 | 45.11 |
| A2 | Trace records/snapshots/stat counters behind VERIFY | −52,100 | 587,900 | 41.44 |
| A3 | Save only clobbered registers; drop CCR save where flags are dead | −26,500 | 561,400 | 39.57 |
| A4 | One per-car state block, pointer set once at `$671b6`; guards/shadow checks VERIFY-only | −68,800 | 492,600 | 34.72 |
| A5 | 020 conversion helpers: 64-bit MULS.L/DIVS.L, table-seeded square roots | −25,700 | 466,900 | 32.91 |
| A6 | Native exact-output: inline division at CCR-dead sites (−19.8k), more MULS.L sites (−10k), sin/cos (−6k), lookahead register loop (−8.5k, measured 0.601 ms earlier), blits out of the update (−7.7k) | −52,000 | 414,900 | 29.24 |

Result: about 1.6× G1 and 2.9× G2. On Fast, the same steps plus the already
measured −20% code placement give roughly 304k cycles (≈21.4 ms). **Plan A cannot
reach the target on a 14 MHz 68020 by optimizing hooks.** Native work would
need to drop by more than half and the renderer by more as well. This is why
the previous loop of small fixes stalled.

## Plan B – 20 ms profile: player at 20 ms, opponents on the native 100 ms step

Selected for 68020 + Fast. Run the player car (car 0) through the converted 20 ms
path every quantum. Run the seven opponents through the **unchanged native 100 ms
step** on the quantum that carries the native tenth pulse (the scheduler already
produces this pulse). Check opponent/opponent contact pairs (21 of 28) on that
quantum only, and player/opponent pairs (7) every quantum. Opponents execute
original code with no conversion, fractional state or hooks. Presentation
interpolates opponent poses (render copies only).

Per-quantum projection for **68020 + Fast** (the gating profile) after B2–B6,
from the measured CCR profile (player 66.0k, opponent 56.2k, pre 23.9k, post 40.1k):

| Item | Every quantum | Pulse quantum only |
| --- | ---: | ---: |
| Player converted update (66.0k measured → after B2–B6) | 44,000 | |
| Main loop pre-car | 19,000 | |
| Player/opponent contact pairs (7/28 of 27.7k) | 6,900 | |
| Other post-loop work | 6,600 | |
| Seven native opponents (≈25.5k each after B6) + hook early-outs | | 180,600 |
| Opponent/opponent contact pairs (21/28 of 27.7k) | | 20,800 |
| **Total** | **76,500 (5.4 ms)** | **277,900 (19.6 ms)** |

Average = (4 × 76.5k + 277.9k) / 5 = **116,800 cycles = 8.2 ms** against the
145,600 G2 limit (20% margin). B7 code placement (−20% of native work) lowers that
to about **96,000 cycles = 6.8 ms** (34% margin). Even the pulse quantum fits in
one tick. For reference, the same split on stock 020 would average 127,700 cycles
(9.0 ms, 9% margin); that profile now uses the coarse path instead. Staggering
opponents 2/2/1/1/1 across the five quanta lowers the peak further, but changes
opponent/contact phase against native ordering. It is a later option.

Semantic notes:

- Opponents keep native 10 Hz game-time fidelity. The native game itself runs
  every car at one 100 ms step per loop (about 7 Hz real on 020 today).
- Player/opponent contact is evaluated at 20 ms against opponent positions that
  advance in 100 ms steps (up to ~8 m at 300 km/h). Measure contact with the
  existing `$68d4e` forced-contact fixtures. If needed, test the player against an
  opponent pose extrapolated by elapsed phase, in collision input only.
- RNG consumption order changes against native only where player events interleave
  with opponent events; event gating to native pulses already holds rates.
- The opponent conversions already validated (position/heading/velocity/scalar/
  wear/fuel/events) are not used in Plan B, but are retained for escalation.

### Escalation: opponents at 20 ms

Switch opponents to 20 ms on a given 20 ms profile (a configuration change, not a
redesign) only when, measured without trace on that profile, all-car logic L (ms
per 20 ms quantum) and per-frame drawing cost R (ms) satisfy

- L ≤ 18 ms (keeps pace with 10% margin), and
- (1 − L / 20) × 1000 / R ≥ 5.54 FPS (the 020 drawing floor).

Examples: L = 15 ms needs R ≤ 45 ms; L = 12 ms needs R ≤ 72 ms. Today's estimate
on 020 + Fast is L ≈ 21.4 ms and R ≈ 88 ms, so this needs further native and
renderer work from step 6. Faster 030/040/060 profiles may pass when measured.

## Coarse path: 68020 without Fast, and 68000

Schedule the **unchanged native 100 ms step** for all cars by elapsed time and
draw independently. No rate conversion is needed: one native step is exactly
100 ms of game time (step 4: 100 tenths per 100 loops). What remains is the
scheduler, tick-owned input, and moving simulation work out of drawing
(recovery, boost/audio, clocks), which the 20 ms path needs too.

Drawing-floor budgets (logic per 100 ms step = 100 × (1 − floor × R / 1000)):

| Profile | Native step today (drawing omitted) | Drawing cost R | Floor | Logic budget per step | Status |
| --- | ---: | ---: | ---: | ---: | --- |
| 68020, chip only | 24.44 ms (v6 lean) | 90.95 ms | 5.54 FPS | ≤ 49.6 ms | Fits with ~50% margin |
| 68000 (A500) | 67.31 ms (v4 division) | 166.86 ms | 3.494 FPS | ≤ 41.7 ms | Needs −38% |

If the 68000 cannot reach 41.7 ms with 68000-safe work, fall back to 200 ms with ×2
conversions: demand ≈ 33.7% plus conversion overhead, fitting only if that overhead
is ≤ 16 ms per update. That fallback also needs 68000 versions of the 020-only
helpers (position/velocity rotation, 64-bit square root, speed feedback).

## Implementation plan, with gates

Each step: matched A/B with `capture_step5_profile.py`, then re-run the elapsed
timer and state-replay oracles. Record cycles per update for stock 020 and
020 + Fast; 20 ms gates apply to 020 + Fast.

### Shared

0. **S0 – Profile selection.** Choose the interval at slave start from CPU class and
   Fast memory. Fast memory must be determined from WHDLoad's side, e.g. whether the
   expansion memory WHDLoad hands the slave lies in Fast RAM (not chip, not
   `$C00000` slow RAM), as the v2 code-placement diagnostic checked. Do not use the
   guest Exec: inside KickEmu, `AllocMem(MEMF_FAST)` returned zero. Gate: correct
   selection on a500, a500-fast, a1200, a1200-fast, with the selected path recorded
   in a readable variable; CUSTOM2=0 still reproduces legacy behavior on all four.
   Decided: a500-fast uses the coarse 100 ms path (68000 rule).
1. **S1 – Trampoline macro.** One macro emitting `move.w ccr,` on 68020+ and
   `move.w sr,` on 68000 (privileged only on 68010+). Done as diagnostic
   `tmp/build/step5-elapsed-ccr`; measured 640,022 / 523,218 cycles, 0.1 residual
   traps per update, oracles pass.
2. **S2 – VERIFY split.** Trace records, `events_snapshot`, stat counters and fault
   guards only under `VERIFY`. **Passed (candidate): 576,907 stock / 488,524.8 Fast**
   against ≤ 588,000 / ≤ 493,000 on the current all-car diagnostic. VERIFY elapsed/
   replay and lean exact-state gates pass; see the acceptance log below.
3. **S3 – Simulation/presentation separation. Passed (candidate).** Recovery, boost/audio and clock
   state updates move to the simulation tick; their drawing stays in presentation.
   Residual UI blits and their WaitBlit (7.7k) leave the update. Gate: existing
   recovery/boost/clock oracles pass with drawing at 0, 1 and 3 passes per tick.

### 20 ms profile (68020 + Fast, Plan B)

4. **B3 – Opponent bypass. Passed (candidate).** At the car-loop head `$671b6`, skip cars 7..1 unless
   the native pulse is due. Player hooks use a `tst.w $32fbc`
   native early-out for opponents (actual Chip-bus-inclusive guard cost is recorded below). Split `$68d4e` pair iteration into player
   pairs (every quantum) and opponent pairs (pulse quantum). Gate: 5-quantum
   average ≤ 200,000 Fast (player still carries unconsolidated hooks), pulse quantum
   ≤ 400,000; opponent state at each pulse byte-identical to a native-step control
   replaying the same player trajectory (new fixture).
5. **B4 – Player hook consolidation. Passed (candidate).** One 64-byte player state block (position,
   heading, velocity, scalar, steering history, wear/fuel remainders). Remove
   per-hook `*_context` lookups. Save only clobbered registers. Merge adjacent hooks
   in the same basic block (e.g. `$672f0..$676e0` scalar-rate sites). Gate: player
   segment ≤ 50,000 Fast (old projection 66,008; measured B3 60,959.5 → B4 49,977.0).
6. **B5 – 020 helper tuning. Passed (candidate).** `FF1SquareRootU64/U32` via a 1024-entry seed and one
   Newton step with `divu.l`; `FF1SpeedRate20`, `FF1VelocityRotate020` with 64-bit
   `muls.l`. Each keeps its guest oracle (1,003 / 408 / 3,216 / 130 cases). Gate:
   player conv_helper ≤ 5,000 Fast.
7. **B6 – Native exact-output work**, ordered by measured share:
   1. inline `divs.l` at division call sites whose CCR result is overwritten before
      use (same audit as the 26 MULS.L sites; 113 calls/update): ≈ −19.8k;
   2. extend MULS.L inlining to further CCR-dead multiply sites (85 calls/update): ≈ −10k;
   3. integrate the validated lookahead register loop: ≈ −8.5k;
   4. sin/cos `$24fe0` direct table access where the caller ignores flags: ≈ −6k.
   Gate: 5-quantum average ≤ 145,600 Fast without trace, pulse quantum ≤ 283,750,
   debt back below one quantum within five quanta.
8. **B7 – Fast placement.** MEMF_PUBLIC loader relocation of code and CPU-only data
   (measured −20% native: 18.83 vs 23.64 ms). Gate: average ≤ 100,000 Fast;
   allocation-failure fallback selects the coarse path, not a broken 20 ms path.
9. **B8 – Presentation. Passed (candidate).** Opponent pose interpolation (render copies, 100 ms latency
   for opponents only, reset on cuts/tow/load). Then measure presented FPS against
   the 5.54 floor with real drawing, not the subtraction model.

Abort criteria: if after B4 the player segment is above 58,000 Fast, or the B6
average is above 165,000 Fast, stop and re-profile before stacking more changes.

### Coarse path (68020 chip-only, 68000)

10. **C1 – Elapsed native step. Passed (candidate).** Schedule the native step every 100 ms of elapsed
    time with the time module (interval 100 ms; native pulse every step), bounded
    catch-up and drawing skipped while behind. Gate: 60 emulated seconds within 1% of
    nominal game time on a1200 and a500; state at each step byte-identical to the
    native-step control at matched step count.
11. **C2 – 68020 chip-only acceptance. Passed (candidate).** Gate: native step ≤ 49.6 ms with S2/S3
    applied, presented FPS ≥ 5.54 with real drawing, bounded debt in contact.
12. **C3 – 68000 capacity. Implemented; capacity gates not met.** Apply the 68000-safe items: v4 division (done, 87.1 →
    67.3 ms), lookahead loop, sin/cos, blits out of the update; then profile the
    A500 untraced the same way to find the next targets. Gate: ≤ 41.7 ms per step
    and ≥ 3.494 FPS. If it stalls above 41.7 ms after these, stop and ask the user
    before starting the 200 ms fallback.
13. **C4 – 200 ms fallback (only if C3 fails).** ×2 conversions with 68000 helpers.
    Gate: conversion overhead ≤ 16 ms per update and the same FPS floor.

## Evidence

Captures `tmp/step5/{a1200,a1200-fast}-elapsed-profile` and
`tmp/step5/{a1200,a1200-fast}-elapsed-ccr-profile` (detail.bin, profile.json,
percar.json, classified.json, traps.json). The CCR variant's 100-update
elapsed/replay validation is in `manifest/step5-elapsed-ccr-validation.json`
and `manifest/step5-elapsed-ccr-replay-validation.json`.


## Implementation log: S0 startup selector (in progress)

`src/FerrariFormulaOne_Profile.s` is a 68000-safe candidate selector. It takes
CUSTOM2, WHDLoad ATTNFLAGS and the WHDLoad-owned expansion allocation address/size;
it never queries guest Exec. It returns a readable path and interval. Zero
CUSTOM2 returns legacy/0 ms; 68000 always returns coarse/100 ms; 020+ selects
player-20/opponents-100 only for a complete non-wrapping allocation in recognized
Fast address ranges. Chip, slow, empty and unqualified allocations use coarse.
The selected candidate is not yet activated; `selection_enabled` stays zero.

The ignored `step5-selection` fixture wraps WHDLoad's original startup entry,
preserves its inputs, reads the host-side control tags and expansion pointer,
then enters the original KickEmu bootstrap. Its passive load observer preserves
CCR using SR on 68000 and CCR on 020. The ordinary slave remains unchanged.
`test_step5_selection.py` runs original-entry control, CUSTOM2=0 and CUSTOM2=1
on a500, a500-fast, a1200 and a1200-fast, comparing semantic snapshots at native
loops 125/150/175. Warp is used to reach the no-input demo and disabled on resume
for the comparison window. Tests are in progress; no S0 gate claimed yet.

Equal-layout `step5-selection-elapsed/{control,fine}.slave` retains the existing
CCR all-car diagnostic solely for the required startup-only A/B. Its diagnostic
execution is not the selected production path. `profile_step5_selection.py`
uses the prescribed profile capture and per-car/classify analysers;
`selection_elapsed_step5.py` and its two analysers repeat elapsed/replay checks.
These measurements are prepared, not yet run. Do not advance to S2 until S0
results are inspected. No new cycle claim is made by this implementation log.


S0 first four-profile run completed: candidate selection passes all 12 cases
(original-entry control, CUSTOM2=0 and CUSTOM2=1 on four profiles). Actual
WHDLoad expansion addresses were 0xd35000 (A500 slow), 0x3b5000 (A500+Fast),
0x1b3000 (020 chip) and 0x5b5000 (020+Fast). CPU flags were 0x200 / 0x203.
Only 020+Fast selects path 2 / 20 ms; the others select path 1 / 100 ms.

**S0 legacy gate is NOT passed.** Matched raw-loop snapshots pass A500,
A500+Fast and 020+Fast, but chip-only 020 differs from original-entry control.
Its CUSTOM2=0 and CUSTOM2=1 runs agree with each other. At loop 125, the native
clock blocks differ by 15 tenths (control has advanced further), suggesting
startup timing changes the number of inactive driving loops; this explanation
is not yet proven. Do not weaken the exact-state gate: investigate initial
state/update alignment and repeat the comparison. Full details are retained in
`manifest/step5-selection-validation.json` (status failed), with all captures.
The S0 elapsed/replay and matched profiling batch is running separately on the
retained all-car CCR diagnostic; S2 has not started.


S0 startup-only elapsed/replay oracles now pass on both 020 profiles (100 updates,
2.000 simulated seconds, 20 pulses). Reports:
`manifest/step5-selection-elapsed-validation.json` and
`manifest/step5-selection-elapsed-replay-validation.json`. Mean traced body costs
are 43.07 ms chip-only and 35.46 ms Fast; these are retained all-car diagnostic
costs, not Plan B or coarse-path acceptance.

The prescribed A/B traces and per-car/classify analyses have completed in
`tmp/step5/{a1200,a1200-fast}-selection-profile-{control,fine}`. Both variants have
the same layout; control enters the original bootstrap and fine queries the
selection tags first. The chip-only comparison is not yet accepted as matched
work because startup has shifted demo progress. A separate capture at the
observed +15 raw-loop offset is running to test that hypothesis; its output
uses `selection-aligned` names and does not overwrite the failing evidence.


S0 A/B audit: both profiles have byte-identical semantic blocks at profile start
and end and identical per-update cycle sequences. Mean cycles are 631,121.2
(control and selector, chip-only; 20 complete updates) and 521,269.12 (control
and selector, Fast; 25 updates). Selection adds zero measured steady-update cost.
`manifest/step5-selection-profile-validation.json` passes. This supersedes the
provisional concern above about that benchmark's work alignment; the separate
native legacy test still fails.

The +15-loop legacy hypothesis test completed and FAILED full state comparison.
Clocks align but steering, RNG, positions and other state differ. Do not accept
clock alignment alone as equivalent starting state. Evidence:
`manifest/step5-selection-alignment-validation.json`. Next: trace original-entry
and selector startup through the beginning of the native demo to locate the
first divergence and establish identical input/initial state. S0 is incomplete;
S2 remains untouched. All test/profile processes have terminated.


### S0 startup RNG confirmation

The requested first-call check at race:+$589c ($6a304), on chip-only 020 with
CUSTOM1=1/CUSTOM2=0, confirms different 120-byte RNG regions ($24f60..$24fd7)
and countdowns: original entry 14, selector entry 29. Both are captured before
the first timing call. This is the known title/menu RNG consumption effect in
baseline-validation.md, not evidence that the selector modifies race physics.
Report: `manifest/step5-selection-entry-validation.json`.

The replacement control executes the same WHDLoad tag query and selector call
as the candidate, then stores the result in an unused discard slot. Only the
PC-relative destination of that result store differs; both arms have the same
layout and instruction sequence. `step5-selection-equal` repeats CUSTOM2=0 and
CUSTOM2=1 for each of four profiles, pairing controls at the same CUSTOM2 value.
No RNG state is rewritten in these tests. The original mismatching captures
remain intact. Controlled exact-state comparisons are currently running.


### S0 accepted: equal-work comparison

**S0 passed.** All 16 boot cases pass: four profiles, CUSTOM2=0/1, control and
selector. All 24 matched-state comparisons (125/150/175 native loops) are exact
across the unchanged semantic block inventory. Report:
`manifest/step5-selection-equal-validation.json`; aggregate:
`manifest/step5-s0-validation.json`.

The first-race capture confirms the uncontrolled chip-only divergence was the
known startup-timing RNG effect: different 120-byte RNG regions and countdowns
14/29 before the first race:+$589c call. Matching countdown alone was insufficient.
The accepted control performs the identical tag query and selector call, storing
its result in a discard slot; no RNG rewriting or relaxed comparison was needed.
Historical failed captures remain as evidence of the uncontrolled comparison.

CUSTOM2=0 selects legacy on every profile. CUSTOM2=1 selects native 100 ms on
68000, A500+Fast and chip-only 020, and player-20/opponents-100 on 020+Fast.
Selection is readable; activation remains off pending the later gates.
The ordinary release is unchanged. Existing S0 elapsed/replay and equal-layout
profile A/B evidence also pass: 631,121.2 cycles chip-only and 521,269.12 Fast,
identical control/selector cycle sequences and start/end semantic state.
These are all-car diagnostic costs, not Plan B or coarse acceptance.

Next is S2: put diagnostics behind VERIFY while preserving arithmetic scratch
storage. In particular, velocity_records holds live intermediate values used by
conversion helpers; it cannot simply be deleted with the trace output. Retain
necessary scratch values, remove diagnostic work, prove VERIFY equivalence and
measure the untraced gates before moving to S3.


### S2 started: first audited VERIFY split

`build_step5_verify_split.py` now builds VERIFY and lean variants from the
accepted S0 elapsed benchmark. The VERIFY slave is byte-for-byte identical to
that baseline (SHA-256 e943a734d99b3a94e83ac4421179a2213602de1b7f348a490e818539eb36c571),
so its already accepted elapsed/replay and cycle evidence remains applicable.

The first slice removes diagnostic record/snapshot work from event, clock,
counter, boost and recovery callbacks, plus wear/fuel/scalar-rate recording.
Pulse decisions, recovery/refill execution and converted arithmetic remain.
Velocity record storage is retained because it is also live arithmetic scratch.
Audit: `tmp/build/step5-verify-split/audit.json`. Lean demo captures are running
on both 020 profiles. S2 is not passed: further trace/stat/guard splitting and
lean equivalence/cycle gates remain. Do not advance to S3.


### S2 full split under validation

The candidate hooks are now in `src/FerrariFormulaOne_UpdateHooks.s`; the
ordinary slave does not include them. `VERIFY` retains all accepted records,
snapshots, statistical increments and runtime assertion branches. The lean
variant retains functional contexts, simulation serials/debt, and 80 bytes of
velocity arithmetic workspace; it emits no trace history. Install-time native
signature checks remain in both builds. The ignored build harness includes the
tracked module and emits identical machine code to the assembled fixture in
both variants (`build_step5_verify_split_module.py`).

The initial unrestricted lean run matches all four Fast semantic checkpoints,
but chip-only differs already at loop 125, before conversion-hook activation.
The final comparison applies the step-1 one-shot control (120-byte RNG region,
saved pre-race random word and countdown) identically to both arms; it uses the
S0 original-entry chip-only capture as seed. No comparison masks are changed.
This control is local fixture code, not part of the tracked hooks or release.

The first controlled VERIFY fixture (v3) was rejected by WHDLoad before the
game loaded: adding the control put its entry offset at 33092, outside the
signed 16-bit range. The retained startup screen says "Slave is illegal".
The v4 fixture moves this local control after the entry routine and asserts
entry < 32768 at build time. This is a fixture layout issue, not a gameplay
comparison failure. Captures use `*-verify-split-v4-{verify,lean}-fine`.

Controlled elapsed/replay/state gates and the prescribed full-instruction A/B
profiles are running. S2 is not yet passed; do not advance to S3.


### S2 accepted: VERIFY split

**S2 passed.** Tracked candidate: `src/FerrariFormulaOne_UpdateHooks.s`.
Aggregate: `manifest/step5-s2-validation.json`. The ordinary slave source and
release are unchanged; the new mode remains off. This finishes the shared S2
gate on the all-car diagnostic, not the later Plan B/coarse-path capacity gates.

| Profile | VERIFY cycles/update | Lean cycles/update | Saving | Lean time | Gate |
| --- | ---: | ---: | ---: | ---: | ---: |
| 68020, chip only | 641,477.6 | **576,907.0** | 64,570.6 (10.07%) | 40.663 ms | ≤ 588,000 |
| 68020 + Fast | 523,160.0 | **488,524.8** | 34,635.2 (6.62%) | 34.433 ms | ≤ 493,000 |

Method: the prescribed `capture_step5_profile.py`, then the ownership, per-car
and classification analysers. Both arms use the same startup RNG control,
warp only to reach the demo, then a 48-field full trace beginning at loop 132.
Compare the same first 20 complete updates on chip-only and 25 on Fast,
excluding partial updates. All start-state semantic blocks match exactly.
The three analyser totals agree. Lean trace cycles are zero; the 80-byte
velocity workspace is classified as functional hook work. Its trace buffers
are absent, while simulation serials/remainders/debt remain operational.

Reports/captures:

- `manifest/step5-s2-profile-validation.json` and
  `tmp/step5/{a1200,a1200-fast}-verify-split-profile-{verify,lean}`.
- `manifest/step5-s2-verify-elapsed-validation.json`: both VERIFY runs complete
  100 updates, exactly 2.000 simulated seconds and 20 native pulses.
- `manifest/step5-s2-verify-elapsed-replay-validation.json`: arithmetic/state
  replay passes both profiles (position, velocity, speed, heading, steering,
  wear/fuel, events, clocks, counters, boost and healthy recovery). Its retained
  control/bridge comparisons are prior evidence, as the report states.
- `manifest/step5-s2-state-validation.json`: VERIFY and lean are byte-exact
  across the unchanged semantic inventory at loops 125/150/175/225 on both
  profiles; all seven final fractional contexts/remainder buffers agree.
  Lean elapsed contexts are coherent, with 100 completed updates and zero
  diagnostic counter increments.

The unrestricted v2 chip-only mismatch was already present before S2 hook
activation. The common step-1 startup control resolves it without changing
comparison masks. v3's pre-game WHDLoad rejection remains documented above;
accepted v4 fixtures enforce the signed entry-offset limit.

Cycle headroom is 11,093 chip-only and 4,475.2 Fast cycles per update. These
results do not make all-car 20 ms feasible: the later player-only Plan B and
simulation/presentation work are still required. Next: **S3**, with recovery,
boost and clock oracles at 0, 1 and 3 drawing passes per simulation tick.

S2 source committed as `3a6e2ae` (personal author/committer; unsigned, hooks disabled).
The local harness, captures and reports remain ignored as required.


### S2 follow-up: lean scheduler trace guard

Committed as `cc6e9f3`: the remaining `schedule_record` call in `schedule_end`
is now VERIFY-only. Although lean record writes were already disabled, its
trace-limit guard still stopped after 100 updates. Both 020 profiles now finish
200 updates (4.000 simulated seconds, loop 325), retaining the earlier exact
checkpoints. VERIFY remains byte-identical. Evidence:
`manifest/step5-s2-scheduler-fix-validation.json`. S3 profiles use this corrected
lean build as the control.

### S3 candidate: simulation and component presentation separated

`src/FerrariFormulaOne_Presentation.s` retains native recovery/refill,
boost/audio/gear arithmetic and calendar carry behavior on simulation pulses.
Instrument rate/scroll/wheel phase updates also move to those pulses. Native
instrument, opponent projection, boost gauges and clock digits run in a separate
presentation call, preserving their native blitter waits. Clock presentation
reads current state without invoking calendar arithmetic. This is component
separation; full road rendering and opponent interpolation remain B8/integration.

The ordinary slave still does not include these candidate modules. The new
mode remains default-off. S3 runs retain the existing all-car 20 ms diagnostic
solely to isolate the split, not as the selected production profile.

All eight demo captures completed: VERIFY with 0/1/3 component drawing passes
and lean with zero passes on both 020 profiles. The unchanged S2 semantic
inventory is exact at loops 125/150/175/225; fractional contexts agree, and the
new instrument phase/rate inventory is independent of drawing count. Each
VERIFY capture passes the elapsed and replay oracles: 100 updates, 2.000
simulated seconds, 20 pulses. Reports: `manifest/step5-s3-state-validation.json`
and `manifest/step5-s3-p{0,1,3}-{elapsed,replay}-validation.json`.

The 1,008-case recovery matrix, 264-case clock rollover matrix and matched
untraced S2/S3 profiles are being checked. S3 is not yet accepted.


S3 code committed as `462d77b`. Strengthening the clock fixture exposed a real
rendering bug: the native blitter clobbers D7/A2-A5, including the new digit-loop
counter and table pointers. `59cd944` preserves D7/A2-A3 around each glyph call.
The earlier exact game-state checks did not establish correct digit rendering.
Fresh final-build demo captures use `*-s3-v2-*`; earlier captures remain intact.

The clock fixture now checks the exact number of rendered digits (calendar 10,
session 7 per pass), besides native-reference and independent calendar state.
The first 128 cases passed these stronger checks. A later stop revealed a
fixture lifetime issue: the native month-length helper replaces the race overlay,
including the plane descriptors at $66c92/$66ca2. Using those addresses afterward
fed instructions to the blitter as plane pointers and corrupted fixture code.
The isolated fixture preserves both plane lists outside that overlay. Calendar
rendering uses a fixture-owned four-entry list of live Chip planes (fourth aliases
first), testing actual DMA and state independence, not menu pixel appearance.
The fixture also flushes the instruction cache after patch installation.

Intermediate fixture failures are retained under `s3-clocks-v3` through `v6`.
The initial full-buffer fixture did not reach the race; unused trace histories
were removed from this isolated test. An attempted guest Chip allocation returned
zero (error 37), so that approach was discarded. No production allocation change
was made. Final clock acceptance and cycle audit remain outstanding.


S3 v2 passed the corrected 0/1/3 demo state/elapsed/replay checks, all 264 clock
cases (both profiles, exact 7/10 glyph counts), and both 1,008-case recovery runs.
The matched v2 lean A/B saved 7,085 cycles chip-only (578,360.09 -> 571,275.09,
22 updates) and 2,674.31 Fast (488,572.15 -> 485,897.85, 26 updates).
**These numbers are intermediate, not S3 acceptance.**

The full instruction audit initially used an obsolete absolute WaitBlit address.
Resolving the actual entry from graphics.library's live -228 vector exposes
residual busy-spin: 134,046 cycles across 22 S3 stock updates and 192,374 across
26 Fast updates. The remaining blits originate at race $66886/$668d6 inside
$66802, the status-flag selector/renderer, called before the omitted road block.

The v3 candidate retains $66802's original flag selection and session-counter
mutation in the update, latches the resulting graphic, and moves both native
blits to component presentation. Presentation bypasses that state mutation.
The final audit counts every $24ae0 native blit, not just clock/gauge entries,
and dynamically resolves each build's relocated WaitBlit loop. Fresh captures
use `*-s3-v3-*`. A 216-case flag matrix checks all requested graphics, race/session
selection, zero/nonzero counters and 0/1/3 real drawing passes, including exactly
two blits per presentation. Final v3 gates are running; S3 remains incomplete.


### S3 accepted: simulation/presentation separation

**S3 passed on both 020 diagnostic profiles.** Aggregate:
`manifest/step5-s3-validation.json`. Source commits: `462d77b` (component split),
`59cd944` (clock-loop register preservation), `ed7f126` (status-flag split).
All use the personal author/committer, with signing and hooks disabled.
The ordinary slave and release are byte-identical; the new mode stays default-off
and ordinary CUSTOM2=0 remains legacy-exact. Tracked working tree is clean.

| Profile | Corrected S2 lean cycles/update | S3 lean cycles/update | Saving | S3 time |
| --- | ---: | ---: | ---: | ---: |
| 68020, chip only | 578,059.39 | **558,777.57** | 19,281.83 (3.34%) | 39.385 ms |
| 68020 + Fast | 488,572.15 | **471,283.23** | 17,288.92 (3.54%) | 33.218 ms |

Matched first 23 complete updates on chip-only and 26 on Fast, from 48-field
traces beginning at loop 132; warp disabled before measurement. Both start-state
inventories are exact. Prescribed capture, per-car and classification analysers
agree on totals. Corrected S2 controls: `*-s3-profile-s2`; final S3 captures:
`*-s3-v3-profile-s3`. Report: `manifest/step5-s3-profile-validation.json`.

**Zero native blit calls, zero clock glyph calls, zero instrument/boost drawing
work and zero WaitBlit busy-spin cycles** occur in either final simulation-only
window. The audit resolves graphics.library's relocated WaitBlit entry for each
build. Matched S2 windows contain 56/62 native blit calls and 171,174/191,352
busy-spin cycles in total (chip/Fast).

Final verification:

- Eight demo captures (`*-s3-v3-{verify-p0,verify-p1,verify-p3,lean-p0}-fine`):
  unchanged native semantic inventory at loops 125/150/175/225, exact fractional
  contexts, and drawing-independent instrument phase/rate and flag-counter state.
  Every elapsed context is coherent; lean diagnostic counters remain zero.
- VERIFY elapsed/replay with 0/1/3 actual component presentation passes: each
  completes 100 updates, 2.000 simulated seconds and 20 native pulses. Boost/audio/
  gear records cover up/down/held responses; physics, events, fuel/wear, clocks,
  counters and healthy recovery all replay exactly.
- `s3-v3-recovery-{a1200,a1200-fast}`: 1,008 cases each, signed recovery states,
  refills, native control/candidate modes, gates and 0/1/3 recovery/projection
  passes. Isolated return boundaries exclude sorting/drawing; the demo captures
  separately execute real component rendering.
- `s3-clocks-v8-{a1200,a1200-fast}`: 264 cases each, native-reference and independent
  calendar checks through tenths/seconds/minutes/hours, midnight, leap/non-leap
  February, month ends and year wrap. Exactly 7 session or 10 calendar glyphs
  per pass. The fixture preserves plane descriptors outside the calendar helper's
  replaced overlay, as described above; this is not menu pixel acceptance.
- `s3-flags-{a1200,a1200-fast}`: 216 cases each, all flag requests and race/session
  choices, zero/nonzero session counters, and exactly two native blits per pass.
  The native flag counter changes once on its simulation call and never due to
  additional drawing passes; its prior tick semantics are retained.

S3 is a candidate component split, not full road rendering, Plan B or coarse-path
acceptance. The all-car 20 ms diagnostic still exceeds the production budget.
Next is **B3**, opponent bypass on 020 + Fast, with its own matched-state control
and five-quantum cycle gate. Coarse integration remains C1–C3; 030/040/060 stay
deferred, and a 68000 200 ms fallback still needs user agreement.


### B3 accepted: native opponents on the 100 ms pulse

**B3 passed as a default-off candidate.** Aggregate:
`manifest/step5-b3-validation.json`. Tracked implementation:
`src/FerrariFormulaOne_Opponents.s` and the conditional `FF1_PLAN_B` paths in
`src/FerrariFormulaOne_UpdateHooks.s`. The host must install the opponent
selector after the existing installers and flush the instruction cache.
The ordinary slave does not include or activate these modules.

On the selected 020 + Fast path, car 0 retains its converted 20 ms update.
Cars 7..1 execute native arithmetic in native order only on each fifth quantum.
The seven player/opponent pairs run every quantum; the 21 opponent/opponent
pairs run on that fifth quantum. Pointer-based cold writers use the actual
recipient rather than the stale loop index. Mixed contact resets the player's
longitudinal position/velocity/speed fractions from the native opponent value;
native lateral impulses retain the player's fractional tail. Opponent shadows
are neither consumed nor changed. Repair/refill and contact-counter callbacks
bypass player fractional work for opponents.

| Profile | S3 all-car cycles/quantum | B3 cycles/quantum | Saving | B3 active time |
| --- | ---: | ---: | ---: | ---: |
| 020, chip only (diagnostic) | 558,281.20 | **151,972.10** | 72.78% | 10.712 ms |
| 020 + Fast (gating profile) | 470,594.20 | **136,587.40** | 70.98% | 9.627 ms |

Fast worst rolling five-quantum average: **139,560.6**
against **200,000**; peak/pulse quantum: **359,231** against **400,000**.
No abort threshold is exceeded. These pass B3, not B6's pulse/debt gate or B8's
rendered FPS gate. Chip-only measurements are diagnostic; its selected design
remains the native 100 ms coarse path.

Matched A/B: `capture_step5_profile.py` with the same pre-activation state at
completed loop 125, warp off. Exclude the first complete interval containing
installation, then compare 20 complete quanta (four native pulse periods).
The before/after trajectories necessarily differ after B3 activation; the
unchanged semantic inventory is exact at their common starting point. Run the
ownership, per-car and classify analysers on identical windows; all three
per-quantum totals agree exactly. Captures:
`tmp/step5/{a1200,a1200-fast}-b3-v4-matched-{s3,b3}`.

Unlike the old all-car diagnostic, B3 can reach the pacing wait. The analysers
now optionally exclude **only repeated unsuccessful scheduler polls**, retaining
the final successful due check and the rest of the loop. No simulation work is
removed. Guest VERIFY is off for capacity measurements; the emulator's
instruction trace supplies cycle attribution. The instruction audit confirms
7..0 on pulse quanta, only car 0 otherwise, exactly 28/7 pair bodies, no opponent
conversion/context helper calls, and zero native simulation blits.

The original ≤8-cycle TST figure was an instruction-cost estimate, **not the
observed elapsed cost**: `$32fbc` remains in Chip RAM. The final Fast trace
measures a mean **16.04 cycles** for that instruction including bus waits;
the distribution is retained in the schedule audit. The prescribed TST early-out
is implemented, and these costs are included in the unchanged 200,000/400,000
aggregate gates. B4 still owns player hook/context consolidation.

Final semantic gates, both profiles:

- VERIFY, lean and a separate native-instruction control agree at **101 exact
  checkpoints**, including all **20 opponent pulses**, across the full existing
  semantic inventory, gear, instrument phase/rates and flag counter. All seven
  fractional buffers agree too. No comparison masks were relaxed.
- The control saves native instruction windows before conversion installation,
  restores them while opponents execute, and reinstalls player hooks before
  car 0. Thus opponents execute the original code independently of the new
  bypass trampolines. It replays the same player trajectory; exact per-quantum
  comparison verifies that trajectory as well as every opponent's state.
- Final VERIFY arithmetic replay passes for 100 player updates: velocity,
  scalar feedback, position, heading, steering, wear/fuel, events, clocks,
  counters, boost/audio/gear and healthy recovery. Elapsed oracles confirm
  **2.000 simulated seconds, 100 quanta and 20 native pulses**.
- **112 forced contact cases per profile** cover all 28 pairs, both directions
  and both pulse phases. Native position, longitudinal/lateral velocity and
  speed results are exact against the native control. Only player fractions
  change; non-due opponent pairs are skipped. Lateral impulses are measured
  explicitly, preserving their fractional tails.
- **1,008 recovery/refill cases per profile**, including signed states, gates,
  race/session modes and 0/1/3 presentation passes, pass. Native opponent
  repairs leave dormant fractional wear/fuel slots unchanged.
- **128 contact-counter cases per profile** verify native opponent decrements
  and pulse-gated player decrements, without opponent trace callbacks.

The initial large native control exceeded chip-only loader memory: its boot
screen explicitly reported AmigaDOS error 103 before the game started. The
accepted control removes unused trace histories, retaining the same native
instruction restoration and state comparison. Failed boot evidence remains in
`a1200-b3-matrix-control-fine` and `a1200-b3-control-boot-diagnostic`. The first
contact oracle omitted the native lateral impulse; the corrected fixture records
and compares that field rather than masking it. Earlier captures are retained;
final acceptance uses v4 builds/captures and their recorded SHA-256 values.

With `FF1_PLAN_B` undefined, all six S3 VERIFY/lean 0/1/3 presentation binaries
remain byte-identical. Ordinary source/release hashes are unchanged, the mode
stays default-off, and ordinary CUSTOM2=0 remains legacy-exact. No full renderer,
physical-input, modal, rendered-FPS, 68000/coarse or 030/040/060 acceptance is
claimed here. Next: **B4**, player hook consolidation (player segment ≤50,000
Fast; re-profile rather than stacking changes at the stated abort threshold).

B3 source committed as `8421cc7` (personal author and committer, unsigned, hooks
disabled). Local harness, captures and reports remain ignored.


## B4 acceptance: compact player state and consolidated hooks

B4 passes as a **default-off candidate**, selected at build time with
`FF1_PLAYER_HOOKS` alongside `FF1_PLAN_B`, for the mode-8 player path. The
ordinary slave does not include these modules. Gate profile: 14 MHz 020 + Fast;
chip-only 020 is a diagnostic comparison and retains its selected coarse design.

The player has one **64-byte primary state block**, checked by the assembler:
velocity 0..11, position 12..23, heading 24..35, scalar 36..41, steering history
42..51, steering cursor 52, fuel carry 53, steering last quantum/raw 54..59,
and four tyre carries 60..63. Cursor and condition carries have the complete
unsigned domain 0..4, so byte storage loses no information. Steering reset and
sampling preserve the adjacent fuel byte. Working arithmetic scratch, temporary
scalar/position values, scheduler metadata and saved contact position workspace
remain separate; this is not a claim that all candidate memory fits in 64 bytes.
Dormant opponent conversion arrays are no longer part of the compact candidate.

Player hooks address the state directly, with **zero context-lookup executions**
in the measured windows. Adjacent native load callbacks at $671e6/$6720e/$6721c
share the $67280 callback; stores at $68546/$68576/$685a6 share $6860e. Their
native instructions and install-time signature checks remain. The lean build
uses narrower register saves, direct scalar/wear/fuel callbacks and pulse-only
event dispatch; it omits the feedback hook whose lean body only checked state.
Heading hooks combine axis selection and wrapper work around the unchanged
signed increment helper. The scalar sites $672f0..$676e0 remain at their native
control-flow points: branches and engine calls between them prevent treating
that entire range as one straight-line block. Their wrappers are specialized.
VERIFY retains the established record ABI and independent component callbacks.
No B5 arithmetic algorithm or B6 native calculation optimization is included.

### Measured capacity

| Profile | B3 player | B4 player | B3 whole update | B4 whole update |
| --- | ---: | ---: | ---: | ---: |
| 020 + Fast (gate) | 60,959.5 | **49,977.0** | 136,587.4 | **124,247.6** |
| Chip-only 020 (diagnostic) | 72,287.4 | 58,947.7 | 151,972.1 | 138,214.3 |

All values are mean emulated cycles over 20 complete lean updates. Fast player
cost falls **18.02%**, whole-update cost **9.03%**. Fast worst rolling five is
126,642.0 cycles and peak is 337,188. The player gate passes by **23 cycles only**;
record this as a narrow pass in the measured window, not substantial headroom
or acceptance of later B6/B7, contact debt or rendered-FPS gates.

The matched A/B uses the same controlled loop-125 demo state, excludes the first
installation interval, and removes only repeated unsuccessful pacing polls.
The exact native start-state inventory is unchanged. Owner, per-car and classify
analysers agree on each update total; the player mean is stored unrounded.
Instruction audits confirm four native pulses, cars 7..0 on pulses/car 0 on
other quanta, 28/7 pair bodies, no opponent conversion, no context lookups and
zero native simulation blits. Intermediate Fast player costs were 53,429 after
the first hook pass and 50,624 after merging; both remained below the 58,000
abort threshold before the next consolidation.

### Semantic and boundary checks

- Both profiles: B3 versus B4 VERIFY/lean agree at all **101 native checkpoints**,
  including all **20 opponent pulses**, with the unchanged semantic blocks,
  gear, instrument phase/rates and flag counter. All seven live player state
  components agree after expanding the packed byte representation. Removed
  dormant opponent fractions are not runtime state; native opponent arrays
  remain compared exactly. B3's independently validated native-opponent control
  supplies the existing reference for this transitive comparison.
- Elapsed and full player arithmetic replay pass: **100 quanta, 2.000 simulated
  seconds, 20 pulses**, with velocity/scalar, position, heading, steering,
  wear/fuel, event/RNG, clocks, counters, boost/audio/gear and healthy recovery.
- **112 contact cases per profile** pass against native control: all pairs,
  both directions and pulse phases, including lateral impulses and exact
  player fractional resets. Fixture-only wide result buffers preserve the
  established oracle format while live candidate state uses the compact block.
- **1,008 recovery/refill and 128 contact-counter cases per profile** pass.
- **254 wear and 80 steering guest boundary cases** pass on chip-only 020,
  including invalid byte carries/cursors, saturation, gaps, wraparound and
  adjacent-byte canaries. The fuel byte survives steering operations.
- **80 direct hook cases per VERIFY/lean arm per profile** cover all ten
  specialized scalar sites and all four heading sites. Independent arithmetic
  expectations, D0-D7/A0-A6, CCR, native output and carried state agree exactly.

Final builds are `tmp/build/step5-b4-v4/{verify,lean}`. VERIFY is byte-identical
to v3, so its final capture records explicitly reuse that evidence. The final
macro cleanup compiles byte-identically to both v4 binaries. With B4 undefined,
both B3 binaries remain byte-identical. Ordinary source/release hashes remain
unchanged and ordinary CUSTOM2=0 remains legacy-exact.

Final captures: `tmp/step5/{a1200,a1200-fast}-b4-v4-matrix-{verify,lean}-fine`,
`{profile}-b4-v4-matched-b3`, and `{profile}-b4-v4-matched-b4-retry1`.
The first final Fast profile could not save because the filesystem was full;
it is not accepted evidence. Duplicate B4-created baseline traces were verified
by SHA-256 and hard-linked, and superseded v2/v3 candidate traces were losslessly
gzipped with round-trip hash verification. Storage actions are recorded in
`tmp/step5/b4-trace-storage.json`; decompress those older traces before replay.
The profile harness now guarantees emulator cleanup even if saving its log fails.

Aggregate acceptance: `manifest/step5-b4-validation.json`, with source/build
hashes, exact-cycle report, state/elapsed/replay/hook/contact reports, fixtures
and schedule audits. Harness, reports, captures and builds remain ignored.
Full renderer, physical input/modal acceptance, rendered FPS, coarse integration,
and 030/040/060 analysis remain outside B4. **Next: B5 helper tuning**; its Fast
player conversion-helper gate remains ≤5,000 cycles.

B4 source committed as `a63d66d` (personal author and committer, unsigned,
hooks disabled). The tracked worktree is clean.


### B5 acceptance (2026-10-12)

B5 is passed as a **default-off candidate** under `FF1_HELPERS_020`.
The Fast player `conv_helper` mean is **6,998.35 → 4,968.00 cycles**
(**29.01% lower**), meeting the 5,000-cycle gate by **32 cycles** in the
prescribed matched 20-update window. This is a narrow measured pass, not
broad capacity headroom. B6 peak/debt gates and B8 presented FPS remain open.

| Matched lean metric | 020 + Fast B4 | 020 + Fast B5 | Chip-only 020 B4 | Chip-only 020 B5 |
|---|---:|---:|---:|---:|
| Player conversion helpers | 6,998.35 | 4,968.00 | 10,461.55 | 8,609.80 |
| Complete player segment | 49,977.00 | 47,110.60 | 58,947.70 | 56,589.00 |
| Complete update mean | 124,247.60 | 122,144.50 | 138,214.30 | 135,320.50 |
| Worst rolling five | 126,642.00 | 124,019.60 | 143,617.60 | 137,489.20 |
| Peak update | 337,188 | 341,092 | 375,364 | 372,924 |

Whole-update Fast mean improves 1.69%; the peak increases with this layout
and still exceeds B6's future 283,750-cycle pulse gate. Chip-only adapted
mode remains diagnostic; its selected production design is the unchanged
native 100 ms coarse path. Measurement uses `capture_step5_profile.py`,
loop-125 matched starts, the first installation interval omitted, then 20
complete updates. Only repeated unsuccessful pacing polls are excluded.
Owner, per-car and classification totals agree exactly; the per-car analyser
now records unrounded category means so the gate is not decided by rounding.

Implementation:

- Shared 1,024-word integer seed table (2,048 bytes). U32 uses exact lookup
  below 1,024 and a bucket seed plus one `DIVU.L` Newton step otherwise.
  U64 uses `BFFFO` normalization, interpolated upper seed, one 64/32 `DIVU.L`
  Newton step and full-width square correction. The result is exact floor
  square root throughout both unsigned domains. The native bounded square
  root and native exact-CCR division helpers are unchanged.
- `FF1SpeedRate20` forms its signed 64-bit numerator with `MULS.L`, uses
  `DIVSL.L` only when the high half is the low half's sign extension, and
  retains the wide fallback, overflow rejection, clamping and carry rules.
- Rotation retains full 64-bit `MULS.L` products. Checked word shifts replace
  the longer bit-shift sequence; both outputs still commit atomically.
  Register saves follow actual clobbers, including the feedback, derivative,
  projection, carry-rotation and tyre-limit helper entries.
- Re-profiling showed that the named sqrt/rate/rotation changes alone missed
  the gate (v1: 6,621; v2: 5,823.9 Fast helper cycles). The conversion-helper
  phase therefore also removes temporary copies in `FF1VelocityApply20`
  using checked signed 32-bit division, and uses an exact 0..255 quotient/
  remainder lookup in wear/fuel with a full-domain unsigned division fallback.
  These preserve aliasing, atomic failure, invalid-input and saturation
  contracts. No B6 native call-site transformation was included.

Validation:

- Existing guest suites retained: 1,003 feedback, 408 U64 sqrt, 3,216 rotation
  cases (inside the 9,090 velocity suite), and 130 scalar-rate cases.
  Another 3,216 carry-rotation and 56 continuous-response cases pass.
- Added/expanded: 1,942 U64 seed-endpoint cases; 2,383 wide-tyre cases including
  every small-root input 0..1023; 4,244 wear cases covering every lookup
  numerator, carry, saturation and the 255/256 boundary; 1,264 scalar cases
  including 32/64-bit division selection and signed overflow boundaries.
  Independent models check 3,073,730 U64 and 1,065,536 U32 inputs. Maximum
  observed Newton correction is four and one respectively.
- On both 020 profiles, VERIFY and lean match B4 at all **101 native semantic
  checkpoints**, with the exact-state inventory unchanged, and all seven
  normalized player fractional-state blocks agree. Native opponents inherit
  the B3 native-control proof through the exact B4/B5 comparison.
- Elapsed and full arithmetic/event replay pass on both profiles: 100 player
  updates, 20 native pulses, 2.000 simulated seconds in 2.02322059 elapsed
  seconds (101 PAL fields). Field-granular traced timing is not a CPU-cost
  measurement or B6 scheduler/debt acceptance.
- Direct scalar/heading hook fixtures pass 80 cases per VERIFY/lean arm per
  profile, checking every D0-D7/A0-A6 register, CCR, native output and carried
  state. Scheduling audits retain four pulse updates, native 28/7 pair counts,
  zero simulation blits, zero opponent conversion and zero context lookups.
- B5-disabled VERIFY/lean binaries are byte-identical to committed B4.
  Authoritative ordinary source and release hashes are unchanged. New mode
  remains default-off; no CUSTOM2=0 or coarse-path behavior is activated.

The first large VERIFY builds failed to load on chip-only 020 with WHDLoad
**DOS error 103 (not enough memory)**; the live run was diagnosed and its log
retained, not accepted as a game result. The final isolated VERIFY build uses
4,000 scalar trace records instead of the default 4,096, with allocation and
its overflow guard controlled by the same `FF1_SPEED_RECORD_CAPACITY` constant.
Only 200 records are used. Its 779,640-byte slave fits; all checkpoints and
replay assertions remain. Exported unused trace padding is normalized to the
old file ABI. Default trace capacity/bytes are unchanged, and the compact
fixture's lean binary is byte-identical to the measured lean binary.
The rejected v3 word-shift experiment failed the rotation oracle and is not
part of acceptance; v4 corrected it before further profiling.

Evidence: `manifest/step5-b5-validation.json`, its linked oracle/profile
reports, `tmp/step5/*-b5-v5-matched-*`, `tmp/step5/*-b5-v5-matrix-*`,
`tmp/build/step5-b5-v5/lean`, `tmp/build/step5-b5-v5-compact/{verify,lean}`,
and `tmp/step5/b5-verify-startup/whd-output.txt`. Reproduce with
`build_step5_b5_compact.py`, `profile_step5_b5.py`,
`capture_step5_b5_matrix.py`, the `test_step5_b5v5_*` guest oracles,
`analyze_step5_b5_{states,elapsed,replay,profiles,scalar_hooks}.py`,
`check_step5_b5_disabled.py` and `accept_step5_b5.py`.

**Next: B6**, ordered native exact-output work with its unchanged average,
pulse and debt gates. B5 does not complete step 5 or rendered-game acceptance.

B5 implementation commit: `bdb67035c3fca5c99ba38a794449b332f8b724dc` (personal identity; unsigned; hooks disabled).

### B6 substep 1

Default-off candidate committed as `d4109710626f6778aba04259d55d20b2ce500f74`. Matched twenty complete lean updates from loop 125 (installation excluded; only unsuccessful pacing polls removed). Both profiles pass the unchanged 101-checkpoint exact-state inventory, player fractional state, elapsed and full replay oracles.

- a1200-fast: mean 115368.5, worst rolling five 118282.8, peak 325472 cycles.
- a1200: mean 127451.0, worst rolling five 128235.2, peak 344410 cycles.

Evidence: `manifest/step5-b6-s1-validation.json`, linked state/elapsed/replay reports and `tmp/step5/*-b6-s1-profile`. Further B6 work and final pulse/debt gate remain pending.

### B6 substep 2

Default-off candidate committed as `7c2e2d5518aaa6cc4e01edef9c157a8078b235c8`. Matched twenty complete lean updates from loop 125 (installation excluded; only unsuccessful pacing polls removed). Both profiles pass the unchanged 101-checkpoint exact-state inventory, player fractional state, elapsed and full replay oracles.

- a1200-fast: mean 112440.95, worst rolling five 115289.4, peak 307942 cycles.
- a1200: mean 124573.1, worst rolling five 126366.4, peak 334496 cycles.

Evidence: `manifest/step5-b6-s2-validation.json`, linked state/elapsed/replay reports and `tmp/step5/*-b6-s2-profile`. Further B6 work and final pulse/debt gate remain pending.

### B6 substep 3

Default-off candidate committed as `2c1036f5d2301c26c60a7ade999f5a91df216820`. Matched twenty complete lean updates from loop 125 (installation excluded; only unsuccessful pacing polls removed). Both profiles pass the unchanged 101-checkpoint exact-state inventory, player fractional state, elapsed and full replay oracles.

- a1200-fast: mean 110216.2, worst rolling five 113044.0, peak 303136 cycles.
- a1200: mean 123242.5, worst rolling five 128151.2, peak 330850 cycles.

Evidence: `manifest/step5-b6-s3-validation.json`, linked state/elapsed/replay reports and `tmp/step5/*-b6-s3-profile`. Further B6 work and final pulse/debt gate remain pending.

### B6 substep 4

Default-off candidate committed as `595a52411722802927eb25e6d4a6319ae151b3b8`. Matched twenty complete lean updates from loop 125 (installation excluded; only unsuccessful pacing polls removed). Both profiles pass the unchanged 101-checkpoint exact-state inventory, player fractional state, elapsed and full replay oracles.

- a1200-fast: mean 108902.65, worst rolling five 111006.0, peak 297111 cycles.
- a1200: mean 122241.1, worst rolling five 125485.2, peak 327262 cycles.

Evidence: `manifest/step5-b6-s4-validation.json`, linked state/elapsed/replay reports and `tmp/step5/*-b6-s4-profile`. Further B6 work and final pulse/debt gate remain pending.

### B6 substep 5

Default-off candidate committed as `8fa29e9eb870c96f103b7dbcd9a64e46973d0d08`. Matched twenty complete lean updates from loop 125 (installation excluded; only unsuccessful pacing polls removed). Both profiles pass the unchanged 101-checkpoint exact-state inventory, player fractional state, elapsed and full replay oracles.

- a1200-fast: mean 103578.8, worst rolling five 106448.6, peak 277677 cycles.
- a1200: mean 120825.0, worst rolling five 125528.0, peak 314820 cycles.

Evidence: `manifest/step5-b6-s5-validation.json`, linked state/elapsed/replay reports and `tmp/step5/*-b6-s5-profile`. Further B6 work and final pulse/debt gate remain pending.

### B6 final acceptance — passed (candidate)

The four ordered edits are complete: dead-CCR divisions, additional inline
multiplies, guarded register lookahead, and direct sine/cosine table helpers.
After substep 4 the pulse peak was still 297,111 cycles. Re-profiling identified
remaining native arithmetic; the final refinement adds 20 guarded divisions
and six inline multiplies with both branch paths audited (219 guarded proof
instructions), plus a hardware multiply preserving the native routine's full
and unusual CCR contract. All signatures are checked before any patch is made.

| 020 + Fast, matched lean window | B5 | B6 | Gate |
|---|---:|---:|---:|
| Average cycles/update | 122,144.5 | 103,578.8 | ≤145,600 |
| Worst rolling five average | 124,019.6 | 106,448.6 | ≤145,600 |
| Peak pulse cycles | 341,092 | 277,677 | ≤283,750 |

Average CPU cost falls 15.2% from B5 and peak cost 18.6%. The peak margin is
6,073 cycles. Pending time is already below one quantum at the end of each
of the four measured pulses (zero following quanta required; gate ≤5).
Chip-only diagnostic: mean 120,825, worst five 125,528, peak 314,820 cycles.
It does not enable the fine path on chip-only machines.

All five stages retain matched owner/per-car/classification totals and pass
unchanged exact native/player state, elapsed and replay checks on both 020
profiles, with VERIFY and lean arms. Final schedule audits show four native
pulses, native 28/7 pair counts, no simulation blits, no opponent conversion,
and no context lookups. Guest oracles pass 94,720 division comparisons,
1,772 lookahead cases per profile, 43,520 trig cases per profile, and 94,720
full-CCR multiply comparisons. The tested multiply machine code is identical
to the final measured helper. Division CCR is intentionally scratch only at
audited sites; the reused multiply fixture's quotient/remainder labels mean
product/D1 preservation in that run.

Final VERIFY capacity is 3,600 trace records (200 used), preserving all checks
while fitting chip-only RAM. Unused exported padding retains the trace ABI.
B6-disabled builds remain byte-identical to B5; ordinary source and release
remain unchanged. New mode stays default-off and CUSTOM2=0 remains legacy-exact.

Mean simulation cost is 7.30067 ms per 20 ms update, or 36.5033 ms CPU per
100 ms simulated, versus the original native simulation's 52.28 ms. This is
about 30% less simulation CPU while sampling the player five times as often;
it is not a measured displayed-frame improvement. Full rendering remains B8.

Evidence: `manifest/step5-b6-validation.json` and its linked per-stage,
oracle, schedule, debt and disabled-build reports. Final refinement commit:
`8fa29e9eb870c96f103b7dbcd9a64e46973d0d08` (personal identity, unsigned, no hooks).
**Next: B7 MEMF_PUBLIC placement.** Step 5 and rendered-game acceptance remain open.

### B7 implementation in progress

- `947ba07`: default-off, 68000-safe public-memory ownership helpers. Guest
  registration, repeated registration, allocation, duplicate-owner rejection,
  release/reuse and failure checks pass on a500, a500-fast, a1200 and a1200-fast.
- `a2fc13c`: transactional hunk binding engine. Twenty-two guest cases pass on
  68000 and 68020, including malformed records, pointer overflow, repeated
  application and rejection before any operand write.
- A separate native-loader diagnostic registers WHDLoad-owned memory with guest
  Exec before LoadSeg. Native hunk relocation handles code/data references and
  retains the original explicitly Chip-only audio hunk. At 125 completed demo
  updates with real drawing, all 205 other resident/race slots are in Fast RAM:
  112,144 allocation bytes. This is placement evidence, not B7 acceptance.
- The first public-loader experiment exposed an existing slave layout
  assumption: its race repairs use offsets from the first race hunk for targets
  in other hunks. Public allocation changes their spacing, so the screen-pointer
  and blitter repairs were skipped. The recorded draw trace shows blitter writes
  into low memory and a damaged Exec jump vector. Resolve the original repairs
  by native hunk identities 160, 184 and 173; the corrected native diagnostic
  reaches 125 demo updates. Failed evidence is retained in
  `tmp/step5/b7-loader-unbound`, successful placement in
  `manifest/step5-b7-native-placement.json`.
- B6 integration now generates explicit binding records from assembled operands
  and native relocation records, including split signature words. It never
  treats arbitrary numeric data as addresses. Installation must follow the
  original slave repairs; the step-1 RNG fixture otherwise replaces the timing
  instruction before its signature check. The larger host also requires a
  parameterized scheduler cache-flush offset. Both old B6 binaries remain
  byte-identical with the default offset (`step5-b7-host-default-validation.json`).

Pending: complete integration smoke tests, matched state/elapsed/replay and
cycle measurements (average ≤100,000 Fast), allocation-failure/coarse selection,
reload/deallocation and no-Fast/68000 placement checks. B7 is not yet passed;
ordinary release remains unchanged and new code is default-off.


B7 continuation (2026-10-13, still **not accepted**):

- `dd5cea8`: hunk-aware official slave repairs and parameterized scheduler host
  offset. Original B6 VERIFY/lean binaries remain exact with the default offset.
- Explicit displaced `dc.w` instructions must also be bound. Missing those
  operands caused VERIFY error 17 and a stalled lean trace; failed captures are
  retained with `missing-displaced` suffixes. Extended PC-relative operands are
  excluded using their base register, because Capstone reports some as mode 8.
  The previous bad VERIFY capture is retained with `probe-relative` suffix.
- Corrected v1 lean: 20 matched updates after loop 132, repeated pacing polls
  excluded; all three analyzers agree on **69,827.1 cycles/update**, 32.59% below
  B6's 103,578.8. Peak 178,508; all four pulse updates return below one quantum
  immediately. Capture: `tmp/step5/a1200-fast-b7-v1-profile`. Address normalization
  changes native PC/call-stack words only; original trace and raw memory retained.
- Corrected v1 VERIFY: 100 updates / 20 native pulses / 2.0 simulated seconds,
  2.0031887 elapsed seconds. Arithmetic, steering, wear, fuel, clocks, recovery
  and motion replay pass. Native hunk relocations and record pointer fields are
  normalized by explicit identity. The broad exact-state inventory is not yet
  passed: it includes dynamic resource pointers, allocation links and native
  Fast-memory availability flags (startup $19eb6..$19ef2). These are being
  audited; no blanket numeric-pointer scan or arbitrary state masking is allowed.
- Chip-only 020 v1 reaches 130 native updates, selects coarse/100 ms, installs
  no fine hooks, and reports no native public-patch error.
- `e50a23b`: owned MEMF_PUBLIC game stack. Four-profile guest fixtures verify
  placement, task bounds, original SP/bounds restoration, return registers and
  release. 68000/020 allocation-failure fixtures run the native stack and return
  correctly. Evidence: `manifest/step5-b7-stack-validation.json`.
- `fb4e263`: native patch ledger. 68000/020 guest fixtures cover overlapping
  transactions, reverse restoration, ledger-capacity rollback, repeated restore
  and cleared owners. Evidence: `manifest/step5-b7-patches-validation.json`.
  Integrated v2 uses it before true native race-overlay release, with an explicit
  zero-initialized probe-state reset inventory. Integration testing is pending.

Ordinary source/release remain unchanged. B7's four-profile, default-off,
allocation-failure, reload and complete state/cycle gates are still open.


### B7 final acceptance — passed (candidate)

Final candidate: `tmp/build/step5-b7-v3`; full evidence and hashes in
`manifest/step5-b7-validation.json`. Seven cohesive commits, ending with
`80ddb07` (native RAM-file-cache guard) and `013cdf9` (race lifecycle).
Ordinary source and release remain byte-identical; new mode remains default-off.

| 020 + Fast, same loop-132 anchor / 20 complete lean updates | B6 control | B7 | Gate |
|---|---:|---:|---:|
| Mean cycles/update | 103,957.25 | 51,546.3 | ≤100,000 |
| Worst rolling five mean | 106,581.8 | 53,305.8 | ≤145,600 |
| Peak pulse cycles | 277,479 | 134,295 | ≤283,750 |

Mean simulation CPU cost falls **50.42%**, to **3.6332 ms per 20 ms update**.
All four measured pulses end below one quantum immediately. Each of the three
analyzers agrees on every update total. All 3,409,639 trace instruction records
retain identical costs and registers after explicit native PC normalization.
Only unsuccessful repeated pacing polls are removed; guest VERIFY recording is
off in this measurement. These are simulation costs, not displayed-frame times.

All 209 live hunk slots are audited. On both Fast profiles, every CPU-only slot
is Fast; the original 456-byte audio hunk 46 stays Chip. The 32 KiB owned stack
is Fast on those profiles, Slow on A500 without Fast, and Chip on chip-only 020.
CPU allocations use MEMF_PUBLIC, not forced MEMF_FAST. Patch snapshots and
ledgers have explicit owners, exact-size release and rollback. Forty-eight live
display fields have no out-of-Chip copper, bitplane or enabled blitter pointers;
recorded copper/audio/sprite/bitplane DMA addresses also stay in Chip memory.
Full rendering and presented FPS remain B8.

The first A500 + Fast integration exposed the game's redundant RAM: file cache:
its native Fast-memory query enables startup copies, and the run stalls in DOS
Write while copying xport.scn (native return $1b5e6). Disabling the public stack
and reducing the pool do not fix it. A diagnostic hiding the Fast attribute
isolates the cache path but is not adopted. The final hunk-validated patch clears
only the RAM-file-cache initializer; its two readers select copying and RAM:/FF1:
reads. Correct Exec Fast attributes and the native overlay policy remain intact.
WHDLoad retains file caching. All four profiles then reach the native update
checkpoint with correct selection: fine only on 020 + Fast, otherwise 100 ms.
The matrix's historical `loop130` filenames actually stop at the 131st update-end
crossing (first hit plus 129 ignored hits); fine `ticks=131` confirms the count.

VERIFY and padded lean pass the unchanged 26-block inventory at all 101 matched
checkpoints and all player fractions against an equal-layout public B6 control.
No state blocks are removed or masked. Canonicalization follows explicit native
hunk identities, allocation links, relocation fields and declared record pointer
columns; all 209 live identities are refreshed per snapshot and the canonical
size remains exactly 512 KiB. Raw memory/records remain available. The original
pre-public B6 has legitimate allocation/resource-pointer and memory-policy
changes, so it is not claimed byte-identical as a raw memory image.
Elapsed/replay: 100 adapted updates, 20 native pulses, 2.000 simulated seconds,
2.0031887 elapsed seconds; arithmetic, motion, steering, wear, fuel, clocks and
recovery oracles pass. Existing non-demo branch fixtures retain their documented
scope; the ordinary no-input demo remains the measurement workload.

Lifecycle checks cover both boundaries. A guest-set native exit flag restores
all fine patches, clears both ledger owners and resets probe state before native
race cleanup; the game continues in its menu. That experiment does not establish
automatic second-demo entry. A separate bounded fixture invokes the real hooked
native unloader with fine hooks installed, holds the freed 8,568-byte primary
allocation, then uses the native overlay loader. Race moves from **$56d970 to
$56fc80**; rebinding and installation succeed, the temporary owner is released,
and the new race completes **130 updates** with no binding/runtime errors or
fallback. It stops before returning into old native frames. Malformed binding,
changed-base rebinding, overlapping ledger/rollback and stack-return/failure
fixtures also pass on their documented 68000/020 profiles.

A genuine failed ledger allocation selects coarse/100 ms, removes fine hooks
and completes the native update checkpoint. Four-profile CUSTOM2=0 comparison
against the unchanged release passes the full 26-block gate at loops 125/150/175.
Both arms have equal test allocation size/reservation and the step-1 RNG/countdown
control, accounting for the known timing-dependent title RNG consumption.

Memory-scope limit: the experimental harness reserves **768 KiB** through WHDLoad
(256 KiB Kick image + 512 KiB public pool). The default-off comparison equalizes
that reservation and does not prove the same minimum memory footprint as the
ordinary small release. Guest allocation failure is covered; failure to satisfy
mandatory WHDLoad startup memory is an admission failure, not an in-game fallback.
The ordinary release is unchanged. Physical hardware, 030/040/060, remaining
modal/input acceptance and complete rendered-game acceptance remain deferred.

**Next: B8 presentation; then C1–C3 coarse scheduling/capacity.** B7 is complete
within this candidate scope; step 5 as a whole remains open.

### B8 in progress: render-pose kernel and full-drawing bring-up

The default-off `FerrariFormulaOne_RenderPose.s` kernel blends only caller-owned
12-byte poses. At section crossings it expresses the previous endpoint in the
current section's basis using the native Q15 table, including forward/backward
lap wrapping; heading interpolation takes the shortest 1024-unit arc. Status
changes and nonadjacent sections snap. Epoch/tow/load invalidation and the native
renderer adapter remain integration work. The player must bypass delayed history.

`build_step5_b8_pose_test.py` / `test_step5_b8_pose.py` pass 462 guest-executed
68020+Fast cases, including signed-word endpoints, angle wrapping, curved section
crossings, lap boundaries, alpha endpoints/clamping and source-pose immutability.
Evidence: `tmp/step5/b8-pose-a1200-fast/result.json`.

An isolated full-road drawing bring-up (`step5-b8-probe`) measured approximately
12.14 completed frames/s over a short 37-field interval. **Not acceptance**:
interpolation is not installed, the mixed pit-status routine is omitted pending
ownership separation, and the interval ends inside drawing. No displayed-FPS
claim follows. This diagnostic identified additional native render-body writes
(wheel rates and view-direction flag) that must be simulation-owned before the
unchanged exact-state gate can compare rendered and omitted arms.
B8 and step 5 remain incomplete; ordinary source/release unchanged.


### B8 accepted: complete drawing and opponent render history (2026-10-13)

Commits `8156222` and `38b2c61`; aggregate:
`manifest/step5-b8-validation.json`. Ordinary source/release unchanged. The new
path remains default-off and confined to the selected 020 + Fast profile.

`FerrariFormulaOne_RenderPose.s` and `RenderHistory.s` retain two native 100 ms
opponent endpoints, then blend private render copies using elapsed sub-pulse
phase. Adjacent forward/backward section changes rotate the old endpoint into
the current section's basis using the native Q15 table; lap and heading wrapping
are handled explicitly. The player uses current state without this 100 ms delay.
Native projection writes only its usual rendering scratch; it never overwrites
live simulation poses. All new CPU data/code remain in the B7 public allocation.

`FullPresentation.s` retains the native road, cars, cockpit, instruments, text,
blitter waits and buffer publication. It includes the complete original slave
screen-pointer repair. Drawing runs only after simulation has caught up; it does
not discard debt. Native buffer-pointer views are saved/restored across each
presentation, allowing the existing broad exact-state inventory to remain exact.

The full-body audit completed S3 ownership: native wheel-rate calculation,
view-direction/recovery flag and pit-range flags now run in simulation, while
pit messages draw separately. Both B8 matched arms contain those corrections.
This is not a claim that B7's stale instrument rates were preserved. The exact
state gate has **no new exclusion or mask**: all prior 26 blocks plus eight pit
flags and all player fractional state agree at all 101 checkpoints for the
omitted control, VERIFY and equal-allocation lean arms.

Validated:
- 462 guest pose cases (signed limits, angles, curved sections, lap boundaries,
  alpha endpoints and source immutability); 288 wheel/view/pit ownership cases.
- History fixtures cover the 100 ms endpoints, intermediate blend, player bypass,
  explicit cut/tow invalidation, epoch changes and reseeding after reset.
- The installed native `$69496` tow hook clears populated history before its
  original position-writing body. Demo takeover changes `$1bee8/$1c1c2/$1c1c4`
  at resident `$236e8..$236fc`; the adapter detects that epoch change, including
  its following grid reset. New races/load clear private history through B7's
  explicit reset spans.
- Real native unload/reload with a deliberately moved race allocation
  (`$568970 -> $56ac80`): history becomes invalid before reload and is seeded
  again after re-entry; 130 native updates, no patch/binding/fallback errors.
- The unchanged elapsed/replay oracles pass: 100 updates, 20 native pulses,
  exactly 2.0 simulated seconds; 2.04325 elapsed seconds at the final checkpoint
  includes 43.25 ms pending after a drawing pass. No rebase or time loss.
- CUSTOM2=0 is exact against the original release under step-1 RNG/countdown
  control on 68000, A500 + Fast, chip-only 020 and 020 + Fast. Reservation and
  allocation size are matched. B8-disabled build is byte-identical to B7.

Matched lean simulation-only profile (same loop-132 anchor; 48 fields, first
complete update dropped, twenty updates retained): **52,650.25 cycles/update =
3.7110 ms**, vs B7 51,546.3. Worst rolling five **54,530.2**, peak **138,287**.
All retained gates pass. Player segment 21,003.15 cycles; its conversion helpers
3,637.4. Per-car, category and total analysers agree exactly. Raw/normalized
trace audit preserves all costs/registers across 3,826,795 instructions.
The approximately 1,104-cycle increase buys history capture and the missing
native state ownership; no abort threshold is reached.

Actual presentation gate: **300 buffer publications in 1,137 PAL fields =
22.77626 seconds: 13.17161 FPS / 75.92085 ms per frame**, exceeding 5.54 FPS.
Warp is off; no CPU trace or intervening debugger stop in this window. Endpoints
are the same instruction immediately after native buffer publication. 1,138
20 ms updates occur in that window (99.9286% simulated/elapsed ratio). The
shorter independent 100-publication capture measured 13.20646 FPS. Screenshots
at both endpoints show complete road, opponent cars and cockpit drawing.

A separate 48-field **full drawing** trace checks actual DMA, with 909,271 blitter
transfers plus copper/audio/sprite/bitplane transfers: all real DMA addresses and
applicable pointer registers remain Chip (maximum sampled pointer 368,310).
Raw/normalized costs/registers agree across 1,428,510 instructions; all three
analysers agree. Its combined simulation-plus-drawing cycles are not substituted
for the simulation-only gates; real presentation is gated by the measurement
above. Debt falls below one quantum within **1–3** completed simulation updates
of every sampled native pulse, without rebasing.

Two analyser assumptions were corrected for this new workload, with original
results retained as `*-initial-analyser.json`: line-mode BLTAPT is the signed
Bresenham error accumulator, not an address (confirmed by the local emulator's
blitter implementation); A/B are not DMA pointer checks in that mode. Every
actual DMA transfer is still checked. Debt is evaluated at completed simulation
before the optional drawing callback, retaining the next native-loop debt
separately: immediately starting another frame can add debt after catch-up.
Neither correction changes execution or relaxes the logic/FPS thresholds.

Rejected bring-up: v1 omitted the original repair's `EXT.L D1`, causing a bad
screen pointer on a later frame. v2 repaired that, then identified the two
presentation buffer-pointer views in the unchanged state inventory. v3 saves
and restores them and passes the full comparison. These failures are retained
separately; their measurements are not acceptance evidence.

Reproduction uses `build_step5_b8_source.py` (same bytes as frozen v3),
`capture_step5_b7_v2.py` for the matched checkpoint protocol,
`capture_step5_b8_profile.py` / `capture_step5_b8_render_profile.py` with the
existing total/per-car/classify tools, `debt_step5_b8.py`, and
`capture_step5_b8_fps300.py`. The precise paths/hashes and additional fixtures
are in the aggregate manifest. All harness/data/build products remain ignored.

**Next: C1**, native coarse 100 ms elapsed scheduling; then C2 chip-only 020 and
C3 68000 capacity. B8 is complete as a candidate; step 5, production integration,
physical-input/full-modal acceptance remain open. The 68000 200 ms fallback still
requires user agreement; 030/040/060 remain deferred.


### C1 accepted: elapsed native 100 ms stepping (2026-10-13)

Commits `5bd25d2, e0dcb66, ddb5826`; aggregate `manifest/step5-c1-validation.json`.
The isolated candidate schedules the unchanged all-car native step at 100 ms,
with a native tenth pulse on every completed update. Physics/rates are not
converted. Admission is before the native input head, so each admitted step
retains native input sampling. Service remains bounded through the native loop;
drawing is skipped while another tick is due, and outstanding time is never
rebased or discarded to catch up. The private two-update service counter wraps
without dropping debt or bypassing native input.

`FerrariFormulaOne_Coarse.s` and `CoarseInstall.s` reuse the time module, S3/B8
simulation ownership, complete native renderer, and B7 public loader/bindings
and patch ledger. The time module's 100 ms branch is opt-in. Presentation uses
68000-safe calls/addressing in the coarse build; flags save with SR on 68000,
CCR on 68020. Both CPU-specific harness builds are candidates; a shipping
combined slave is still production integration. The ordinary source/release
are unchanged, and the B8 fine binary remains exactly
`158403173c1d01ffdf7d13d9d6d13ab453f9afab07336374f4c19a74f0b7c493`.

The existing matched protocol retains 125 native warm-up steps and the step-1
RNG/countdown control before activation. All gates below apply after activation,
not to title/menu startup. The timer producer cannot run until its context has been initialized; the
installation transaction keeps interrupts disabled until then. Reversible native pause edges use Pause/Resume; native
race exit and unload restore the patch ledger before overlay memory is freed.
CPU-only code, state, stack and ledger allocations retain MEMF_PUBLIC ownership;
original DMA resources remain Chip.

| Profile | Simulated | Actual emulated elapsed | Difference | Gate |
|---|---:|---:|---:|---:|
| Chip-only 68020 | 60.000 s | 60.015534 s | 0.0259% | ≤1% |
| A500 68000 | 60.000 s | 60.035565 s | 0.0592% | ≤1% |

These lean windows contain 600 updates, with real drawing, warp confirmed off at
both matched endpoints, no CPU trace and no intermediate debugger stops. A
single-field screenshot is taken only after the A1200 window. The first A1200
attempt was rejected because warp-off was still queued at its initial endpoint;
the accepted rerun advances to the next checkpoint and verifies warp=0 before
starting. Its simulated/elapsed gate is unchanged.

State/replay: on **both** CPUs, all **600 consecutive steps** agree with an
equal-layout native full-render control across the unchanged 26-block inventory
**plus all eight pit flags**. The verifier records 29,722 bytes per step; its
copying cost is excluded from the lean timing/profile gates. No block, byte or
new mask was removed. Address normalization uses the same explicit native hunk
relocations and two RNG pointers as B7. Both calendar and session clocks advance
exactly one tenth on every sampled step (599 tenths between records 1 and 600).

The initial comparison exposed only native buffer-pointer views and the native
drawing flag. C1 preserves their per-step values while physical publication
remains presentation-owned; the full exact-state gate then passes. Initial
failed evidence is retained under `c1-a1200-*-initial`. A separate short omitted
control comparison also passes; the final full native control is the stronger
gate and preserves native arithmetic, RNG order and all-car ordering.

| Matched lean simulation, eighteen retained updates | Native-step control | Elapsed scheduler | Elapsed ms/update |
|---|---:|---:|---:|
| Chip-only 68020 | 659817.33 cycles | 661338.22 cycles | 46.6139 |
| A500 68000 | 518421.33 cycles | 514408.67 cycles | 72.5154 |

Profiles use the same post-warm-up anchor and 100-field captures, with repeated
unsuccessful pacing polls excluded and the first complete update dropped.
`analyze_step5_profile.py`, `percar_step5_profile.py` and
`classify_step5_profile.py` agree exactly. Raw/normalized trace audits preserve
every cost/register record. Separate full-render traces check actual DMA and
applicable pointer registers (including the documented line-mode APT rule).
Debt is measured from actual timer snapshots at completed simulation, before
rendering; the final reports retain both that debt and next-loop debt.
These numbers establish C1 scheduling overhead, **not C2/C3 acceptance**. Those
phases still require their own capacity, contact and real presented-FPS gates.

Additional checks:
- Eleven time-module cases on both CPUs, including 100 ms service, wrap, early
  consume rejection, and the retained 20/200 ms arithmetic regressions. The
  200 ms arithmetic test does not enable or authorize a gameplay fallback.
- Real native exit after ten candidate steps restores code and releases both
  ledger owners. Bounded actual native unload/reload forces the primary race
  allocation to move; binding, fresh time initialization and twenty resumed
  coarse updates succeed with zero runtime errors, on both CPUs.
- Four-profile CUSTOM2=0 is exact against the original release at native loops
  125/150/175 with equal reservation/allocation and the established RNG control.
- B8 reproduction remains byte-exact. All local harness/build/data evidence is
  intentionally ignored; only the reviewed source modules are committed.

Scope limits remain: B7's experimental 768 KiB WHDLoad reservation; no minimum
memory or physical-input claim; pause edges are wired to the existing tested
timer but full interactive modal workflows remain open. 030/040/060 remain
deferred. The new mode remains **default-off**.

**Next: C2** chip-only 68020 capacity/FPS, then C3 68000 capacity/FPS. C1 is
complete within this candidate scope; step 5 and production integration remain
open. The 68000 200 ms fallback still requires the user's agreement.


### C2 accepted: chip-only 68020 capacity and real presentation (2026-10-13)

Commit `134a18b`; aggregate `manifest/step5-c2-validation.json`.
The selected coarse candidate reuses **only B6 stage 1**, the audited 68020
native division call-site substitutions. Positive constant divisors use inline
DIVSL.L; variable divisors use the existing zero/overflow-compatible helper.
The existing signatures prove that outgoing CCR is overwritten before use.
No physics conversion, car-order change, additional B6 stage, or new rendering
optimization was needed. Installation is inside C1's interrupt-excluded patch
transaction and restoration ledger, before cache flush. The host supplies
`FF1_COARSE_NATIVE_EXACT` and `FF1_NATIVE_EXACT=1`; a compile-time guard requires
`FF1_COARSE_020`. The ordinary default remains off (CUSTOM2=0); the C2 runtime
control word exists for an equal-layout A/B. CPU-only allocations remain public.

| Gate / measurement | Equal-layout C1 control | C2 | Required |
|---|---:|---:|---:|
| Native all-car simulation, cycles/update | 662209.00 | 459958.89 | — |
| Simulation, ms/update at 14.18758 MHz | 46.6753 | 32.4198 | ≤49.6 |
| Actual presented FPS, untraced | Not used for the C2 gate | 6.62367 | ≥5.54 |
| Actual elapsed for 60.000 s simulation | — | 60.075629 s | Within 1% |

Physics cost falls **30.54%** in the matched 18-update capture, with
repeated unsuccessful pacing polls excluded, the first full update dropped,
and the same 125-step native warm-up/RNG control. Total, per-car and classify
analysers agree exactly; raw/normalized trace audits retain all cycle/register
records. The FPS gate counts **300 real publications** across
45.292097 emulated seconds, at the same post-publication
boundary, warp off at both ends, without CPU trace or intermediate debugger
stops. The screenshot is taken after that window and was visually checked.
The independent 600-update elapsed window has 0.1259%
error. VERIFY copying is not used to claim capacity or FPS.

Exact-state/replay: **600 consecutive steps** match an equal-layout unchanged
native full-render control over all **27 blocks / 29,722 bytes per step**.
No masks or exclusions were added. Only the established explicit native hunk
relocations and two RNG pointers are canonicalized. Both calendar and session
clocks advance exactly one tenth at every step. The native division guest oracle
passes **94,720 cases** (quotient/remainder and D2–D5 preservation, all 32 incoming
CCR values); outgoing-CCR equality is intentionally not claimed at these
CCR-dead call sites. Committed-source lean/VERIFY builds reproduce the measured
binaries exactly; both C2-disabled C1 CPU builds reproduce their prior hashes.

Contact gate: the established wall-input fixture applies ten penetrations at
completed steps 11–20; **eleven actual native wall-handler calls** are recorded.
One hundred contact-state records match exactly between native-arithmetic,
drawing-omitted control and optimized full-render candidate. The 100-field
full-render trace contains **17** retained complete updates (9–25), covering
all ten forced inputs and recovery; the ordinary matched A/B contains 18.
Actual producer/snapshot reconstruction gives a maximum completed-step pending
time of **103.9859 ms**, returning below 100 ms
**1 step** after the final forced input.
Every producer increment is retained, with no rebase or debt discard. This is
bounded debt for this observed contact episode, not a universal crash bound.
The full-render DMA audit passes: actual transfers and applicable pointers
remain in Chip memory, retaining the documented line-mode APT exception.

Lifecycle/default-off: native exit after ten steps restores **all 60 division
signature fragments** and releases both ledger owners. The bounded real native
unload/reload fixture moves the primary race allocation from `$186f60` to
`$1890d8`, restores the 1,350-byte ledger, rebinds and runs twenty fresh steps
without runtime errors. Four-profile controlled CUSTOM2=0 remains byte-exact
against the original release at native loops 125/150/175. Original source,
ordinary release and B8 fine artifact remain unchanged. Production integration,
minimum-memory and physical-input/full-modal acceptance remain open; the B7
experimental 768 KiB reservation is unchanged.

Reproduce with `build_step5_c2.py`, `capture_step5_c2_profile.py`, the three
existing profile analysers (`analyze_step5_c2_profiles.py` supplies matched
arguments and trace audit), `capture_step5_c2_fps.py`,
`capture_step5_c2_states.py` / `analyze_step5_c2_states.py`,
`analyze_step5_c2_clocks.py`, and `capture_step5_c2_elapsed.py`.
Contact, division, exit/reload and default-off fixtures have corresponding
`*_step5_c2_*` tools. Paths and hashes are in the aggregate; all harness/build
and measurement files remain ignored.

**Next: C3**, 68000 capacity ≤41.7 ms per native 100 ms update and ≥3.494 FPS.
C4 requires the user's agreement if C3 cannot meet its targets. C2 is complete
as a default-off candidate; step 5 and production integration remain open.
030/040/060 analysis remains deferred.


### C3 implemented: correctness passed, capacity gates not met (2026-10-13)

Commits `771663c, eb61251, 0a9dda0`;
aggregate `manifest/step5-c3-validation.json`. **C3 is not performance-accepted.**
The planned 68000-safe work is implemented. Final re-profiling still misses both
targets, so no additional optimization changes or 200 ms conversions were stacked.
The candidate remains default-off; the next decision is user approval for C4.

| Matched stage, 18 native updates | Control ms/update | Candidate ms/update | Saving |
|---|---:|---:|---:|
| 1: exact division | 72.5154 | 54.1347 | 25.35% |
| 2: register lookahead | 54.1348 | 52.4438 | 3.12% |
| 3: sin/cos addressing | 52.7351 | 52.4277 | 0.58% |

Each row is an equal-layout A/B at the same post-warm-up step count, with the
established RNG/countdown control. Stage 1 compares native arithmetic; stages 2
and 3 compare the preceding stage. Do not subtract across rows as though code
layout/bus phase were identical. Total/per-car/classify analysers agree exactly;
raw trace audits preserve all cycle/register records. Repeated unsuccessful
pacing polls and the first complete update are excluded, as in C1/C2.

The final **52.4277 ms** exceeds the **41.7 ms** physics gate.
Actual rendering is **2.54869 FPS**, below **3.494 FPS**,
over **300 native publications / 117.707368 emulated seconds**.
The untraced window uses matching post-publication endpoints, warp off throughout,
and no intermediate debugger stops. Completed = presented + skipped accounting
is exact, excluding a hidden race reset. Its screenshot was inspected after the
window. This is elapsed 10 Hz physics; the native legacy loop ran physics only
as often as frames were completed. Capacity is therefore not inferred from the
old frame-rate alone.

Implementation:
- Stage 1 installs `FF1Divide000` with the original quotient, remainder, register
  and XNZVC contract, including zero divisor and signed wrap cases. The new
  `FF1_MATH_000_ONLY` option excludes 020 instructions; default math bytes stay
  unchanged. The 68000 guest oracle passes **94,720** comparisons.
- Stage 2 reuses the audited ten-sample register lookahead. Only the inspected
  caller's value contract is changed; alternate mode and count/segment boundary
  cases retain native execution. **1,772** native-value cases pass.
- Stage 3 uses 68000-safe indexed table addressing, with the original final
  shifts, D0, A0 and all CCR bits. **43,520** oracle comparisons pass; the exact
  64-byte tested helper block matches the candidate before explicit relocation.
- Blits remain outside the simulation update through the existing C1/S3 split.
  All new code/data retain public-memory ownership. Complete native signatures
  are checked before mutation; the existing ledger owns restoration and the
  host excludes interrupts and flushes caches around installation.

Every stage passes matched native-state and clock replay plus the 60-second lean
elapsed test before the next stage is applied. Intermediate state windows have
100 steps each; final acceptance testing compares **600 consecutive steps** across
all **27 blocks / 29,722 bytes per step** with the native full-render control.
No state mask/exclusion was added; only the established explicit relocations and
two RNG pointers are canonicalized. Both clocks advance exactly one tenth per
step. Final 60.000 simulated seconds take **59.995502 s**
(0.0075% error). VERIFY copying is excluded from capacity.

Contact/lifecycle regressions pass: 100 exact state records through ten forced
wall penetrations, actual native wall-handler entries confirmed; measured pending
time peaks at **202.3915 ms**, returning below one
100 ms quantum 2 step(s) after the forced episode.
This reports the observed episode rather than inventing a new capacity gate.
Actual DMA and applicable pointers stay Chip (with the documented line-mode APT
rule). Native exit restores division, lookahead and trig signatures; actual
moved native unload/reload restores ledger ownership and resumes twenty updates.
An A500+Fast active smoke run completes twenty further 100 ms updates without
errors; it is not a separate performance acceptance. Four-profile controlled
CUSTOM2=0 remains exact at loops 125/150/175. C1 (both CPUs), C2, and B8 were
rebuilt and reproduce their accepted binaries exactly. Ordinary source/release
remain unchanged.

`manifest/step5-c3-reprofile.json` records the stop-point cost breakdown. Roughly
58.5k cycles/update remain in exact division helpers, 41.4k in native software
multiply and 53.6k in the car body; the remaining work spans contact, dynamics,
engine and native control code. The final step still needs another **20.46%**
reduction to meet 41.7 ms. No simple remaining item from C3's specified list has
been left unapplied; no universal impossibility claim is made.

Reproduction: `build_step5_c3_s1.py`, `build_step5_c3_s2.py`,
`build_step5_c3_s3.py`; corresponding `capture_step5_c3_s*_profile.py`,
state/clock/elapsed tools, the existing three profile analysers, and
`capture_step5_c3_fps.py`. Contact, helper oracles, exit/reload and default-off
have corresponding `*_step5_c3_*` tools. The aggregate retains paths/hashes;
harness, archives, builds and measurements remain ignored. Historical stage
source is preserved by the three cohesive commits.

**Decision required:** C4's 200 ms fallback may begin only with the user's
agreement. No such gameplay change is present. C3's implementation/evaluation is
finished, but the native 100 ms A500 capacity gate is **failed**, not waived.
Step 5/production acceptance remain open, including minimum-memory, full input
and modal testing. The experimental 768 KiB reservation is unchanged;
030/040/060 analysis remains deferred.


### C4 authorized and in progress (2026-10-13)

The user explicitly requested: "Implement the 200 ms fallback. This should thus
improve framerate on the A500 while keeping the proper simulation speed."
This supersedes the earlier approval-pending statements, not the capacity gates.
The target is converted 200 ms all-car physics on 68000, including A500+Fast;
chip-only 020 remains native 100 ms and 020+Fast retains Plan B. New mode remains
default-off. C4 must meet <=16 ms conversion overhead per update and >=3.494
actual presented FPS, with correct elapsed simulation and conversion replay.

Work order: validate 68000 full-width arithmetic; implement integrated rates,
velocity derivative/response and frame changes; convert eligible native-tenth
events/counters/clocks; then install behind the existing signature/ledger and
profile gates. Validate directed transitions and deterministic replay before
capacity measurement. Existing native exact-state gates remain for unchanged
paths; the 200 ms integrator intentionally cannot be byte-identical to one
100 ms native step. Do not substitute a clock-only change or two complete
native updates for the requested converted physics.

The current coarse scheduler publishes at most one frame per physics step.
Thus the 200 ms candidate has a 5 FPS ceiling. Its acceptance floor remains
3.494 FPS; independent faster presentation is outside this change.

C4 helper progress: `FerrariFormulaOne_Wide000.s` implements exact signed and
unsigned 32x32->64 multiplication and full-domain unsigned floor square root
using only MC68000 instructions. The A500 guest passes 5,786 independent Python
integer-model boundary/random comparisons with register/stack checks.
`FerrariFormulaOne_Physics200.s` adds seven checked primitives for derivative
normalization, continuous response/position integration, projection, rotation,
scalar magnitude/rate and wear. A further 2,899 A500 guest cases pass, including
atomic overflow rollback. Derivative halving floors at one Q16 unit; rotations
floor once per component and retain the supplied native coefficients.

These are prerequisites only, not live C4 gameplay acceptance. Native hooks,
all-car ownership, event/counter cadence, contacts/multi-segment crossings,
elapsed/replay, lifecycle and capacity measurements remain outstanding.
Evidence: `tmp/step5/c4-{wide,physics}-oracle-a500-1/result.json`; reproduction
uses `tools/build_step5_c4_{wide,physics}.py` and the matching `test_` runners.

Expanded C4 conversion suite: **5,198 passing A500 guest cases** (supersedes the
2,899-case subset), now including fractional position-tail frame rotation,
continuous segment-plane predicates and modular Q12 heading integration.
Zero position tails retain native integer frame-rotation answers. Overflow
leaves both positions unchanged. The segment predicate handles either cosine
sign and reports zero cosine explicitly. `FerrariFormulaOne_Position200.s`
contains these primitives; no live hook is installed by the module.

Next concrete work: wire the all-car native instruction groups to the tested
primitives, retain per-car fractional position/current velocity/scalar ownership
and all explicit reset/contact/save writers, and implement two native-tenth
event pulses with zero-transition eligibility intact. Then perform directed
replay and elapsed/capacity measurements. **C4 remains incomplete.**

Live heading integration (`501cda5`): four native continuous angular increment
sites are signature checked and patched inside the coarse host's existing
interrupt-excluded restoration transaction. No 200 ms interval is selected by
this partial stage. Directed A500 tests execute all four real patched groups
and continuations: **968 cases per native/converted arm**, checking modular
results, register preservation and complete XNZVC. The C3 candidate rebuilt
exactly to its accepted hash. Evidence: `tmp/step5/c4-heading-hooks-a500-{0,1}`.

The broader all-car motion port is currently **unaccepted bring-up only** under
`tmp/build/step5-c4-motion-port`, built by `build_step5_c4_motion.py`. It reuses
the committed all-car reset/contact/save ownership callbacks with 200 ms helper
adapters and 68000 instruction forms. Displaced native instruction operands
are bound explicitly by relocation identity. Its first run exposed an absolute
reference to the installer's private error field; that diagnostic reference was
changed to PC-relative before the next run. Runtime bring-up, independent replay
and two-pulse event/clock scheduling are still required before capacity testing.

Motion bring-up now completes **21 A500 updates, runtime error=0**, using
`capture_step5_c4_motion_smoke.py a500`; report under
`tmp/step5/c4-motion-a500-candidate`. This is memory/binding/control-flow smoke
only: it still runs the C1 100 ms clock with diagnostic 200 ms motion, so it
proves neither real-time simulation nor C4 performance. No emulator remains
running after the capture. The full port is not committed as accepted source.

**Required before enabling 200 ms: phase aliasing.** Native `$6d30a..$6d336`
and `$6daba..$6daee` suppress acceleration/drag at phase<2 for `$6f272=5`,
and at phase=0 for `$6f272=4`. Simply incrementing modulo-four phase by two
would change the latter duty cycle from 1/4 to 0 or 1/2 depending on parity.
Convert these rate gates by the number of eligible native phases in each
200 ms window (0..2), with fuel and other pre-gate effects retaining their own
audited cadence. Do not apply a phase weight indiscriminately to braking or
other scalar increments. Phase/recovery/countdown/clutch/RNG/event tests must
cover both pulse phases and zero-transition eligibility.

Next: finish the two-pulse event/phase conversion and select 200 ms only in the
complete diagnostic; independently replay all converted motion and native
writer ownership, then profile before optimizing the 68000 conversion cost.

Two-pulse timing bring-up (still not C4 acceptance): the 200 ms diagnostic
completes **300 updates / 60.000 simulated seconds in 59.9754698123 emulated
seconds**, error **0.0409004%**. Both native clocks independently advance
**600 tenths**. Warp is off at both endpoints; no trace or intermediate stops.
Runtime error remains zero. This window contains only **115 presentations**,
about **1.91745 FPS**, so the required 3.494 FPS floor is not met. This is a
diagnostic elapsed window, not the final 300-presentation performance protocol.
The screenshot was inspected: complete demo road, opponents and cockpit.

Evidence: `tmp/step5/c4-motion-a500-candidate-elapsed/result.json`, binary
`8640a7f6814450d41df2da98672080d6ac451928f06484dd842110c0bbb7d39b`, frozen
with source/listing under `tmp/build/step5-c4-motion-timing-v1`. The two-pulse
bring-up loops native failure eligibility, clutch and recovery work; advances
countdown/contact/flag counters without stepping past zero; and weights the
seven phase-gated scalar sites separately from braking/off-road changes.

**Known fix after this measurement:** the session-clock cap's pointer comparison
used an immediate CMP form intentionally excluded by the existing relocation
binder (reserved for native signature checks). It now loads the pointer with
MOVE before comparing, which the binder relocates explicitly. The elapsed
window did not reach that cap. Rebuild and directed cap tests are required;
this measurement does not establish cap correctness. A stale run launched
after an assembler failure was rejected and retained separately under
`c4-motion-a500-candidate-stale-rejected`; its output is not acceptance evidence.

`db3f808` commits only the independently tested phase-count/weighted scalar
primitives. The expanded conversion guest suite passes **5,756 cases**. The
full motion/timing integration remains in the ignored harness pending replay,
transition and lifecycle validation. Next: directed clock-cap/clutch/countdown/
phase/failure tests, conversion replay, then matched profiling and cost reduction
without relaxing the <=16 ms overhead or >=3.494 FPS gates.


C4 follow-up: the relocated clock-cap fix passes **30 directed A500 cases**
(two clock pointers, three mode/flag combinations, five boundary values), followed
by 21 live diagnostic updates with error zero. This includes the session-clock
cap and calendar carries. Evidence: `tmp/step5/c4-clock-test-a500-candidate`.

The first integrated motion profile costs **879,332.75 cycles/update** (about
123.96 ms at 7.09379 MHz), across eight complete updates in the actual capture.
The total, per-car and classification analysers agree; raw trace normalization
and DMA checks pass. This is far above the conversion-overhead gate. General
multiplication alone accounts for 107,224 unsigned plus 33,470 signed-helper
cycles/update. Evidence: `tmp/step5/c4-motion-a500-omitted-profile`.

An exact signed 32x16->64 helper now replaces general 32x32 products only where
the second operand is a native signed word coefficient. Full-width speed-square
products remain unchanged. Expanded guest oracles pass **7,155 arithmetic** and
**5,756 conversion** cases. An equal-layout slow/fast selector comparison passes
**100 complete updates**, retaining every byte in the 27-block native-state gate
(apart from established pointer relocation normalization). Profile and elapsed
measurements of this optimization are in progress; no performance acceptance is
implied. Evidence: `manifest/step5-c4-wide-ab-a500-baseline-candidate.json`.


C4 signed-word multiplication A/B complete: equal-layout lean arms cost
**894,652.25 -> 813,106.00 cycles/update**, eight matched complete updates each,
saving **81,546.25 cycles = 11.4954 ms (9.1149%)**. Both arms pass three-analyser
agreement, raw instruction/cost normalization and Chip DMA audit. The diagnostic
selector adds overhead, so compare these arms to each other, not directly to
the earlier uninstrumented 879,332.75-cycle build. The optimized arm still costs
**114.622 ms/update**, above the C4 conversion-overhead limit.

Its untraced elapsed run passes: **60 simulated seconds in 60.0956611 seconds**,
error **0.159181%**, both native clocks +600 tenths, runtime error zero, warp off.
It presents **131 frames (~2.17986 FPS)**, still below 3.494; this remains the
elapsed diagnostic window rather than the final 300-presentation protocol.
Evidence: `tmp/step5/c4-wide-ab-a500-{baseline,omitted}-profile` and
`tmp/step5/c4-wide-ab-a500-candidate-elapsed/result.json`. The exact-state gate
covered 100 updates x 27 blocks x 29,722 bytes/update. No gate was relaxed.
Next optimization must follow this new profile; C4 remains unaccepted/default-off.


C4 square-root optimization: the first 30 restoring rounds use a 32-bit trial
and remainder; the last two preserve the original full-width algorithm. After
k rounds the remainder is below 2*root+1, so the pre-subtraction remainder and
trial fit 32 bits through round 30 for every unsigned 64-bit input. This does
not reduce precision or restrict inputs. Guest oracles pass **7,250 arithmetic**
and **5,756 conversion** cases, including added base-four power boundaries.

Equal-layout root-control A/B passes **100 updates, all 27 state blocks (29,722
bytes per update)**. Eight matched lean updates cost **807,357 -> 788,912.5
cycles/update**, saving **18,444.5 cycles (~2.6001 ms, 2.2846%)**. All three
analysers agree, and raw normalization / Chip DMA audits pass. This pair has no
multiplication selector, so use within-pair comparisons. Physics remains about
**111.21 ms/update**, exceeding C4's overhead gate.

Untraced elapsed passes: **60 simulated seconds / 60.07562925 seconds**, error
**0.1258901%**, both clocks +600 tenths, runtime error zero, warp off. There are
**138 presentations (~2.2971 FPS)** in this diagnostic window, still below the
3.494 FPS requirement. Evidence: `manifest/step5-c4-root-ab-a500-baseline-candidate.json`
and `tmp/step5/c4-root-ab-a500-{baseline-profile,omitted-profile,candidate-elapsed}`.
Full conversion replay, transitions, lifecycle, unchanged-profile verification
and final presentation/capacity acceptance remain open; default-off is retained.
The new profile still attributes ~157,533 cycles to hook bodies, ~265,151 to
conversion helpers and ~350,131 to native/other work. Audit redundant native/
converted calculations and callback context/save overhead next; do not stack
untested changes or relax either capacity gate.


C4 callback-frame audit: the initial reduced-save diagnostic failed the exact
state gate (200 block mismatches over 100 updates). Do not use that artifact.
A hardware watchpoint on native `$22782` traced its writer `$685ea` to native
local `-12(a6)`. That local receives D4 at `$672a2`. The all-car heading hook
`heading_67280` copies D0 to D4; its inherited player-only save list omits D4.
The same extra scratch register is used by `heading_6860e`. The corrected
conservative masks preserve D0/D4/D7/A0 plus each callback-specific list.
The corrected 60 save/restore sites pass **100 exact 27-block updates**. No
state mask was changed. Compiled `Coarse200Save` macros emit all 60 diagnostic
masks exactly; profile and elapsed checks are in progress. Rejected evidence:
`tmp/step5/c4-save-ab-a500-candidate-rejected-d4`,
`manifest/step5-c4-save-ab-rejected-d4.json`; watchpoint traces:
`tmp/step5/c4-save-{watch,localwatch}-a500-candidate`.


Corrected callback-frame A/B complete: eight matched lean updates cost
**786,961.25 -> 763,641 cycles/update**, saving **23,320.25 cycles = 3.2874 ms**.
All three analysers agree; raw normalization and Chip DMA audits pass. Runtime
physics is still **107.6492 ms/update**, above the conversion-overhead gate.
Untraced elapsed passes: **60 simulated seconds / 60.03556547 seconds**, error
**0.0592407%**, both clocks +600 tenths, error zero, warp off. There are **143
presentations (~2.382 FPS)** in this diagnostic window, below 3.494. Evidence:
`tmp/step5/c4-save-ab-a500-{baseline-profile,omitted-profile,candidate-elapsed}`.
The tracked `FerrariFormulaOne_Coarse200Save.s` module defines the tested masks;
it installs no hooks and does not enable C4. Full integration remains diagnostic.
Reproduce its patched-mask diagnostic with `prepare_step5_c4_save.py`,
`build_step5_c4_save_ab.py`, the matching state/profile/elapsed capture scripts,
and the unchanged exact-state / three-profile-analysers. The original all-car
motion source before diagnostic labels is retained as `motion-full-save.txt`.


C4 redundant native-response audit: after the installed `velocity_project`
callback, native `$6dc9c..$6dd42` recomputes the integer velocity difference,
rotates it through four trig calls and takes a magnitude. `velocity_raw` at
`$6dd44` immediately replaces both response components and magnitude using the
converted scratch vector. The bypass changes `$6dc9c` to a word-displacement
branch to `$6dd44`, retaining that native car-id load and the converted helper.
Every word in the omitted 168-byte range is checked before writing the patch.
It skips no native global stores; frame locals -$4/-$6 are overwritten before
later reads, -$14 is dead, and physical-history locals -$e/-$10 remain intact.
The native function restores D2-D3; continuation operand definitions were
checked on both player and opponent branches. Enabled only by the diagnostic
control; source default remains zero and ordinary release does not include it.

Equal-layout, both with corrected reduced callback frames: **100 updates exact**
across all 27 native blocks. State gate unchanged. Evidence:
`manifest/step5-c4-response-ab-a500-baseline-candidate.json`.
Profile/elapsed checks are in progress; do not infer capacity acceptance.


Redundant-response bypass A/B complete: eight matched lean updates cost
**763,506.5 -> 746,038 cycles/update**, saving **17,468.5 cycles = 2.4625 ms**.
The total/per-car/classification reports agree; raw normalization and Chip DMA
checks pass. Simulation still costs **105.1678 ms/update**, above the overhead
gate. Untraced elapsed passes: **60 simulated seconds / 59.93540604 seconds**,
error **0.1077726%**, both native clocks +600 tenths, runtime error zero, warp
off. **147 presentations (~2.4526 FPS)** remain below 3.494; this is still the
elapsed diagnostic window, not the final 300-presentation acceptance run.
Evidence: `tmp/step5/c4-response-ab-a500-{baseline-profile,omitted-profile,candidate-elapsed}`.
The new module is not included by the ordinary slave. Its installation control
is zero by default. Native signature checks cover the complete omitted block;
only the existing integrated 200 ms diagnostic enables it. The remaining full
conversion replay, transition/lifecycle and capacity gates are unchanged.


C4 return-side audit: native `$6e1d2..$6e2ac` reprojects the filtered response,
integrates native velocity, computes magnitude and performs native stop/clamp.
The installed `velocity_returned` consumes the response at -$c/-$a and its
precomputed old-vector scratch; it overwrites native velocity globals and the
shadow vector, calculates converted magnitude and applies its own stop/clamp.
The native zero-path shadow reset is overwritten before any consumer. The
mutable 14(a6) argument is discarded by the caller at `$679fc`; `$679fe` stores
the replaced return D0 and sets flags before any conditional consumption.
Audio/status work through `$6e1cc` is retained. All 220 omitted bytes are
signature checked before installation of the existing `$6e2a4` hook. Source
control defaults to zero and ordinary slave does not include this module.

A/B passes **100 exact 27-block updates**. Eight matched lean updates cost
**743,407.5 -> 722,386.5 cycles**, saving **21,021 cycles (~2.9633 ms)**.
Three analysers agree; raw normalization and Chip DMA checks pass. Elapsed
check is in progress. Evidence: `manifest/step5-c4-return-ab-a500-baseline-candidate.json`
and `tmp/step5/c4-return-ab-a500-{baseline-profile,omitted-profile}`.

Next identified structural simplification: the integer 200/100 ratio needs no
heading /5 remainder or shadow ownership. The four doubled native heading adds
already implemented in `FerrariFormulaOne_Coarse200.s` (501cda5, 968 directed
cases per arm) may replace `install_heading` and its inherited fine-path load,
store, reset and contact callbacks. Reuse that code; keep ordinary native
heading writers. Prove with equal-layout full-state and directed hook checks,
then profile before retaining the change. Do not assume the rest of the fine
position/velocity fractional state can be removed.


Return-bypass elapsed check passes: **60 simulated seconds / 60.09566113 s**,
error **0.1591814%**, both clocks +600 tenths, runtime error zero, warp off.
**153 presentations (~2.546 FPS)** in the diagnostic elapsed window remain
below 3.494. Simulation is **101.834 ms/update**; the conversion-overhead gate
still fails. Evidence: `tmp/step5/c4-return-ab-a500-candidate-elapsed/result.json`.
No production or full C4 acceptance claim; ordinary profiles remain unmodified
by this opt-in module. Full directed motion replay, transitions and lifecycle
checks remain required before enabling the complete conversion.


C4 native heading storage A/B: extracted the existing four doubled increments
into `FerrariFormulaOne_Coarse200Heading.s`; the original partial-stage module
includes it unchanged. The 27,882-byte directed fixture is byte-identical to
its pre-refactor version, and **968 cases per native/converted arm** pass for
modular Q12 values, continuations, preserved registers and full XNZVC.
The integrated candidate calls this installer instead of `install_heading`,
retaining all native heading load/store/reset/contact writers. The old shadow
workspace remains allocated only to keep the diagnostic layout matched.

**100 updates match all 27 native blocks exactly.** Eight matched lean updates
cost **721,666.5 -> 704,375.25 cycles**, saving **17,291.25 cycles (~2.4375 ms)**.
All three analysers, raw normalization and Chip DMA checks pass. Physics is
about **99.3 ms/update**, still over budget. Elapsed check in progress. Evidence:
`manifest/step5-c4-heading-native-ab-a500-baseline-candidate.json`,
`tmp/step5/c4-heading-native-ab-a500-{baseline-profile,omitted-profile}`, and
`tmp/build/step5-c4-heading-hooks/refactor-equivalence.json`.


Native-heading elapsed passes: **60 simulated seconds / 59.95543793 s**, error
**0.0743253%**, both clocks +600 tenths, runtime error zero, warp off. There are
**157 presentations (~2.6186 FPS)** in this diagnostic window, below 3.494.
Evidence: `tmp/step5/c4-heading-native-ab-a500-candidate-elapsed/result.json`.
C4 remains default-off and incomplete; no capacity gate has been relaxed.


C4 product-input audit: the latest captured trace contains 2,459 signed-word
products, 418 with either operand zero and 529 with low(A)=0 (overlap included;
these are whole-trace counts, not per-update gate measurements). The candidate
shortcuts coefficient=0 and low(A)=0. For the latter, the exact product is
signed(high16(A))*signed(low16(B)) shifted by 16, needing one word multiply.
Other values retain the prior full-width routine. Upper B bits remain ignored,
all non-result registers remain preserved, and output is still full signed64.

The expanded guest arithmetic oracle passes **8,330 cases**, explicitly adding
integer-Q16 high-word boundaries/random products. All **5,756 conversion** cases
pass. Equal-layout slow/fast comparison passes **100 updates and all 27 native
state blocks**. Profile/elapsed checks in progress. Evidence:
`manifest/step5-c4-product-ab-a500-baseline-candidate.json` and existing wide /
physics oracle reports (now containing the current build hashes).


Product-shortcut A/B complete: eight matched lean updates cost **712,101 ->
702,120.75 cycles**, saving **9,980.25 cycles = 1.4069 ms**. Both arms include
an equal-layout diagnostic selector; compare within this pair. All three
analysers / raw normalization / Chip DMA checks pass. Untraced elapsed passes:
**60 simulated seconds / 60.03556547 s**, error **0.0592407%**, both clocks
+600 tenths, runtime error zero, warp off. **158 presentations (~2.6318 FPS)**
in the diagnostic elapsed window remain below 3.494. The instrumented selector
candidate costs **98.9768 ms/update**, still over budget; do not claim C4
acceptance. Evidence: `tmp/step5/c4-product-ab-a500-{baseline-profile,omitted-profile,candidate-elapsed}`.


### C4 source consolidation (experimental, capacity still not accepted)

The complete motion, adapters, timing and installer now live in repository
source as `FerrariFormulaOne_Coarse200{Complete,Motion,Adapters,Timing}.s`.
`FF1_COARSE_200_COMPLETE` explicitly selects this integration and requires the
68000 `FF1_COARSE_200` host; otherwise the existing partial-stage module and
all 100 ms / 020 paths compile as before. `CUSTOM2=0` remains the runtime
legacy route. This is not an enablement or performance-acceptance change.

The main coarse scheduler, interval initialization and presentation pulse work
now contain guarded versions of the exact previously measured code. The 60
corrected callback masks compile directly from source; no post-build mask patch
is needed. **All 12 lean/VERIFY diagnostic variants are byte-identical** to the
previous staged product A/B artifacts. Thus their existing state, cycle, DMA
and elapsed evidence applies without a behavior change. **All 13 existing
68000 C3 / chip-only 020 C2 / Fast 020 B8 artifacts rebuilt unchanged.**
Evidence: `tmp/build/step5-c4-source-ab/{equivalence,other-equivalence}.json`.
Use `tools/build_step5_c4_source_ab.py` for future integrated work. The ignored
`step5-c4-motion-port` is now historical staging, not the source of truth.
Four-profile controlled CUSTOM2=0 comparison is in progress.


Source consolidation default-off check **passes all four profiles** (A500,
A500+Fast, chip-only A1200, A1200+Fast): CUSTOM2=0 versus unchanged release,
with the established step-1 RNG/countdown control, equal slave size/reservation,
and the unchanged 26-block state inventory at native loops 125, 150 and 175.
Evidence: `manifest/step5-c4-source-default-validation.json`; reproduction:
`tools/build_step5_c4_source_default.py`, `tools/test_step5_c4_source_default.py`.
Final comment/unused-macro cleanup rebuilt all 12 C4 artifacts to the same
recorded hashes. This closes source consolidation and default-off verification
for this revision, not C4 capacity or full transition/replay/lifecycle acceptance.


### C4 phase-width regression fixed

A directed installed-hook test found a real failure hidden by the normal demo:
native `$67128` loads only D0.byte, while `FF1PhasePulses200` validates D0.word.
Input `$00000100`, phase 0, setting 0 should produce D0 `$00000102` and weight 2;
it instead produced weight `$ffff` (error 2013, after 12 passing cases).
The failed guest memory and binary hash are preserved under
`tmp/step5/c4-phase-test-a500-candidate-rejected-upper-byte`.

Normalize only the helper argument after saving native D0. Restore the original
upper 24 bits for the native continuation. All **72 installed-hook cases** pass
(six upper-bit patterns × four phases × settings 0/4/5), checking phase weights
and D0/D1-D4/A0 preservation; 21 subsequent updates report no error. Fixture
expectations were independently enumerated from the two eligible native phases.
Native continuation overwrites NZVC with MOVE.B/MOVE.W and overwrites X with
SUBQ at `$67148` before consuming it; no additional CCR contract is needed here.

Equal-layout A/B changes only the six-byte normalization instruction (three
NOPs in the control). **100 updates match all 27 native blocks exactly**.
Eight matched lean updates average **702,120.75 cycles in both arms**; all
three analysers agree, raw normalization preserves costs/registers, and DMA
stays Chip. This is no measurable cost change in the captured window, not a
claim that the instruction is free under every bus condition.

Untraced elapsed: **60 simulated seconds / 60.03556547 emulated seconds**,
**0.0592407% error**, both clocks +600 tenths, runtime error zero, warp off.
**158 presentations (~2.6318 FPS)** remain below the 3.494 floor. This is the
60-second diagnostic, not the final 300-presentation protocol. C4 remains
experimental/default-off and incomplete; full independent motion replay,
directed events/transitions, lifecycle/contact debt and capacity remain open.
Evidence: `manifest/step5-c4-phase-validation.json`; reproduce with
`tools/build_step5_c4_phase_test.py`, `tools/test_step5_c4_phase.py`, and
`tools/build_step5_c4_phase_ab.py` plus phase state/profile/elapsed captures.


### C4 quotient-length division

The phase-fix trace contains 1,166 native division entries, including 80 with
large divisors, all nonzero-quotient cases. The repeated `$3fc000 / $aae60`
needs only three quotient bits, yet the existing general loop runs 32 times.
For `FF1_COARSE_200_COMPLETE` only, align the divisor with the numerator and
emit the needed quotient bits. Signed magnitudes are <= `$80000000`; the
alignment loop stops on the sign bit before another shift could overflow.
The shared suffix retains native quotient/remainder signs and full XNZVC.
`FF1_DIV200_AB` selects the original loop in an equal-layout control.

**94,720 native oracle comparisons pass** (2,960 operand pairs × all 32 input
condition-code combinations), including quotient/remainder and D2-D5
preservation. **100 integrated updates match all 27 native state blocks**.
All **13 C3/C2/B8 artifacts rebuild byte-identically**, so their paths retain
prior behavior. Evidence: `tmp/step5/c4-div-oracle-a500-0/result.json`,
`manifest/step5-c4-div-ab-a500-baseline-candidate.json`, and
`tmp/build/step5-c4-div-ab/other-equivalence.json`.

Eight matched lean updates cost **702,415.75 -> 690,505.5 cycles**, saving
**11,910.25 cycles / 1.6790 ms per update**. The candidate costs **97.3394 ms**.
Three analysers agree, raw trace normalization preserves costs/registers,
and Chip DMA checks pass. Do not compare the A/B selector's absolute baseline
with a differently laid-out previous binary to estimate the saving.

Untraced elapsed: **60 simulated seconds / 60.07562925 emulated seconds**,
**0.1258901% error**, both clocks +600 tenths, runtime error zero, warp off.
There are **160 presentations (~2.6633 FPS)** in this diagnostic window.
The <=16 ms conversion-overhead and >=3.494 FPS gates still fail. C4 remains
default-off/incomplete; full independent replay/transitions/lifecycle/contact
and final 300-presentation acceptance are still outstanding. Reproduction:
`tools/build_step5_c4_div.py`, `tools/test_step5_c4_div.py`, and the div A/B
builder plus state/profile/elapsed capture tools.

Read-only next-target audit: 944 of 1,276 native `$29500` multiplications have
two signed-word operands (214 zero products included in the total). This is a
candidate for exact native-CCR-preserving specialization; no such change has
been stacked. A zero-vector rotation shortcut is not promising: only 1 of
418 vector rotations starts with both axes zero. Both are whole-trace counts,
not per-update gates. Inputs: `manifest/step5-c4-native-product-inputs.json`
and `manifest/step5-c4-rotation-inputs.json`.


### C4 native multiplication specialization

The experimental complete C4 build now omits a native low-32 multiplication
cross product only when its high-word operand is zero. The original signed
magnitude handling, zero cases and final ADD/TST/NEG condition-code behavior
are preserved. Installation checks all 66 original bytes and uses the existing
resident patch transaction. The equal-layout A/B selects installation, so the
control executes the untouched native routine and measured cost includes the
candidate JMP. Earlier v2 dispatch saved only 0.175 ms; this simpler v3 is used.

**127,488 native comparisons pass** (3,984 pairs × all 32 input CCR values),
checking product, full XNZVC, D1 and D2-D5. **100 integrated updates match all
27 native state blocks exactly**. All **13 C3/C2/B8 artifacts remain identical**.
After 10 updates, the exit fixture confirms the installed multiplication JMP,
then verifies native cleanup clears the ledger/binding/counters and restores
multiplication, division, lookahead and sin/cos bytes exactly.

Eight matched updates average **690,505.5 -> 686,416.25 cycles**, saving
**4,089.25 cycles / 0.5765 ms per update**; candidate **96.7630 ms/update**.
All three analysers agree; raw normalization preserves costs/registers and
DMA remains Chip. Untraced elapsed: **60 simulated / 60.11569302
emulated seconds**, **0.1924506% error**, clocks +600 tenths,
warp off and runtime error zero. **161 presentations (2.6782 FPS)** is
still below 3.494. This is the 60-second diagnostic, not final 300-presentation
acceptance; the <=16 ms overhead gate also remains unmet. Default-off remains.
Independent replay, transitions, lifecycle/contact debt and capacity remain open.

Evidence: `manifest/step5-c4-native-mul-validation.json`. Reproduce with
`tools/build_step5_c4_native_mul.py`, `tools/test_step5_c4_native_mul.py`,
`tools/build_step5_c4_native_mul_v3_ab.py` and its state/profile/elapsed tools;
exit uses `C1_FIXTURE=exit tools/build_step5_c4_native_mul_fixture.py` and
`tools/capture_step5_c4_native_mul_exit.py`.

Disk cleanup: historical raw detail traces were losslessly gzipped and their
uncompressed SHA256 verified before original removal. Compact results and state
dumps remain. Restore `.bin.gz` before rerunning trace analysers; indexes are
`manifest/disk-cleanup-traces.json`, `manifest/step5-c4-compressed-traces.json`
and `manifest/step5-c4-native-mul-v3-compressed.json`. Current traces were
recompressed immediately after analysis to limit disk growth.


### C4 race ownership reset

A directed native unload/reload after ten C4 updates demonstrated a correctness
bug: the old velocity-initialization mask (`$ff00`, all eight car bits) survived
into the next race, as did Q16 position fractions. The next activation therefore
skipped native velocity seeding, while `bridge_load` replaced only integer
position words. Native cleanup had correctly cleared its ledger/binding/counters;
the missing reset belonged to the persistent C4 state.

`FF1Coarse200Reset`, called once at C4 activation, now clears that mask and all
96 bytes of position shadow. Velocity state is seeded lazily from each car's
new native values. Speed and steering retain their existing installation-time
initializers. The change is confined to the complete experimental C4 module.

The moved reload fixture confirms zero mask/position state after activation,
checks **all eight cars' first velocity loads** against native X/Z values plus
zero carry, and completes **20 post-reload updates**, error zero and temporary
allocation released. This establishes fresh motion ownership for this native
reload path; it does not substitute for all event/contact/transition acceptance.

Fresh-race matched comparison: **100 updates, all 27 blocks exact**. All **13
other-profile binaries** rebuild byte-identically. Eight matched lean updates
cost **686,416.25 cycles in both arms**; all three analysers, raw normalization
and Chip DMA audit pass. Reset is outside the measured update window.
Untraced elapsed: **60 / 60.11569302 seconds**, **0.1924506% error**, clocks
+600 tenths, warp off, runtime error zero. **161 presentations / 2.6782 FPS**
remain below the 3.494 floor; conversion overhead also still fails. C4 remains
default-off and incomplete.

Evidence: `manifest/step5-c4-reset-validation.json`. The pre-fix observation is
preserved under `tmp/step5/c4-native-mul-v3-ab-a500-reload-before-reset`.
Reproduce with `C1_FIXTURE=reload tools/build_step5_c4_reset_fixture.py` and
`tools/capture_step5_c4_reset_reload.py`, plus `tools/build_step5_c4_reset_ab.py`
and its state/profile/elapsed tools. Completed raw profile traces are archived
as `.bin.gz`; each profile's `trace-archives.json` records verified hashes.
`tools/archive_profile_traces.py` performs verification before removing originals.


### C4 straight-segment boundary shortcut

Existing trace operand audit (`manifest/step5-c4-arithmetic-input-audit.json`)
found 94 of 235 boundary calls with sine zero and cosine 999 (whole-trace
counts). For S=0 and C!=0, X*S/C+Z>=512 is exactly Z>=512, including C<0.
The 68000 helper now compares signed Q16 Z directly in this case, retaining
its original general path for nonzero sine or undefined zero cosine. It
preserves the helper's register ABI and full fractional boundary precision.

**6,449 independent integer-model conversion cases pass**, including 693 added
straight-boundary cases covering signed limits, values immediately below/at/
above 512 Q16, positive/negative cosine and undefined zero cosine. **100
integrated updates match all 27 blocks exactly**; all **13 other-profile
binaries** rebuild identically.

Eight matched lean updates average **687,220 -> 680,694.25 cycles**, saving
**6,525.75 cycles / 0.9199 ms per update**. The candidate costs
**95.9564 ms/update**. Three analysers agree; raw normalization
and Chip DMA audits pass. Use this equal-layout A/B saving, not a subtraction
from a differently laid-out previous candidate. Traces were compressed and
verified immediately after analysis (`trace-archives.json` in each directory).

Untraced elapsed: **60 / 59.97546981 seconds**, **0.0409004%
error**, both clocks +600 tenths, warp off and runtime error zero.
**161 presentations (2.6844 FPS)** remain below the 3.494 floor. This is the
60-second diagnostic, not final 300-presentation acceptance. The <=16 ms
conversion overhead gate also remains unmet; full independent motion/event/
transition/contact acceptance remains open. Default-off is retained.

Evidence: `manifest/step5-c4-cross-validation.json`. Reproduce with
`tools/build_step5_c4_cross_physics.py`, `tools/test_step5_c4_cross_physics.py`,
`tools/build_step5_c4_cross_ab.py` and its state/profile/elapsed capture tools.
The same operand audit found all 80 square-root inputs at 49 or 50 significant
bits; reducing leading-zero work is a possible next arithmetic target, not an
implemented or validated change.


### C4 leading-zero square-root rounds

The exact 64-bit root now checks for twelve leading zero input bits. When
present, six base-four rounds would leave both partial root and remainder zero;
shift the full D1:D0 input left twelve and execute 24 narrow plus two wide
rounds. Otherwise retain all 30 narrow plus two wide rounds. No input bits or
fractional precision are discarded. The existing root-control build and the
new equal-layout `FF1_ROOTLEAD_AB` control both compile together.

**8,335 independent arithmetic comparisons pass**, including square boundaries,
full-width extremes/random inputs and five added values around 2^52, the shortcut
threshold. **100 integrated updates match all 27 state blocks exactly**;
all **13 other-profile binaries** rebuild identically.

Eight matched lean updates cost **680,987.25 -> 676,036 cycles**, saving
**4,951.25 cycles / 0.6980 ms per update**; candidate **95.2997 ms**.
All three analysers agree, normalization preserves cost/register data and
Chip DMA checks pass. Raw traces are verified gzip archives with hash indexes.
Untraced elapsed is **60 / 60.01553359 seconds**, **0.0258826%
error**, clocks +600 tenths, warp off and runtime error zero.
**162 presentations (2.6993 FPS)** remain below the 3.494 floor; this is
the 60-second diagnostic, not final 300-presentation acceptance. The <=16 ms
overhead gate also remains unmet. Full C4 motion/event/transition/contact
acceptance remains open, and the mode remains default-off.

Evidence: `manifest/step5-c4-rootlead-validation.json`. Reproduce with
`tools/build_step5_c4_rootlead_wide.py`, its generated oracle test,
`tools/build_step5_c4_rootlead_ab.py`, and rootlead state/profile/elapsed tools.
Read-only next-target observation: the complete C4 motion module still contains
31 `modeval` loads despite its fixed mode 8. Removing redundant mode dispatch
requires a fresh matched test; no such change has been stacked here.


### C4 fixed-mode guard cost audit

Read-only analysis of the retained rootlead candidate trace, using the same
pacing exclusion and dropped first update as the three profile analysers:
**8 complete updates**, **31 static guard sites**, **126.375 executions/update**.
The mode load, comparison and conditional branch together consume **4,772.25
cycles / 0.672736 ms per update**. This is an upper bound assuming all guard
work could be removed for free, not a measured optimization saving. No mode
specialization has been implemented or stacked. The restored trace was removed
after analysis; its verified gzip archive remains.

Evidence: `manifest/step5-c4-mode-cost-audit.json`. The result narrows the next
performance search toward conversion arithmetic and its surrounding code;
fixed-mode dispatch alone cannot materially close the remaining capacity gap.
The last validated candidate remains commit `4b52a59` (95.2997 ms/update,
2.6993 diagnostic FPS). Full C4 acceptance remains open with unchanged gates.


### C4 native projection bypass

Native `$6dc52..$6dc94` projects the integer speed into `$32f94/$32f96`
immediately before `velocity_project` computes its Q16 projection. When both
existing response and return bypasses are enabled, these integer projections
and the initial -4/-6 locals have no live consumers before `velocity_returned`
writes the authoritative vector. The `$6dc96` load remains, but its D0/D7 value
is not a projection input; `velocity_raw` replaces saved D0 before native
response consumption. Static direct-reference and call-site evidence is saved
in `manifest/step5-c4-projection-static-audit.json`; this is not a substitute
for full contact/event acceptance.

The complete C4 installer now validates all 68 original bytes and, only with
both earlier bypasses enabled, can branch from `$6dc52` to `$6dc96`. The
existing hunk transaction owns restoration. `C4ProjectionSkipEnabled` provides
the equal-layout control; the ordinary/default-off paths remain untouched.

**100 matched updates are exact across all 27 blocks**. After ten updates,
the exit fixture confirms the branch is installed, then checks all 68 original
bytes are restored along with the other helper routines and cleared transaction
state. All **13 other-profile artifacts** rebuild byte-identically.

Eight matched lean updates average **675,962.75 -> 671,578 cycles**, saving
**4,384.75 cycles / 0.6181 ms per update**; candidate **94.6713 ms**.
All three analysers agree; raw normalization and Chip DMA audits pass. New raw
traces were compressed with verified hashes immediately after analysis.
Untraced elapsed: **60 / 60.01553359 seconds**, **0.0258826%
error**, clocks +600 tenths, warp off, runtime error zero. **163 presentations
(2.7160 FPS)** remain below 3.494. This is the 60-second diagnostic, not final
300-presentation acceptance. The <=16 ms conversion-overhead gate still fails;
full motion/event/transition/contact acceptance remains open. C4 stays default-off.

Evidence: `manifest/step5-c4-projection-validation.json`. Reproduce with
`tools/build_step5_c4_projection_ab.py`, its state/profile/elapsed tools, and
`C1_FIXTURE=exit tools/build_step5_c4_projection_fixture.py` followed by
`tools/capture_step5_c4_projection_exit.py`.


### C4 exact small-response roots

The retained projection trace contains 80 response-root calls, all with input
below 2048 (60 below 256). `FF1SquareRootU32` now uses a **2,048-byte table of
exact floor roots** for this range, retaining the existing full unsigned-32
algorithm otherwise. The table lives with the CPU-only module in the public
owner. It introduces no approximation or new allocation lifetime.

**7,312 arithmetic comparisons pass**, including every table entry, threshold
values and large unsigned inputs. The isolated fixture extracts the actual
helper/table from the source. Its initial build put the helper beyond BSR.W
range; moving it before test data repaired the harness, without changing the
implementation. All compiled table bytes separately match Python isqrt and
no hunk relocation records touch the table. **100 integrated updates match all
27 state blocks exactly**, and all **13 other-profile binaries** rebuild
byte-identically.

Eight matched lean updates cost **674,487.5 -> 659,737.5 cycles**, saving
**14,750 cycles / 2.0793 ms per update**; candidate **93.0021 ms**.
The shared A/B includes table allocation in both arms. Three analysers agree;
raw normalization and Chip DMA checks pass. Traces were verified and compressed
immediately after analysis.

Untraced elapsed: **60 / 60.01553359 seconds**, **0.0258826%
error**, clocks +600 tenths, warp off, runtime error zero. **166 presentations
(2.7660 FPS)** remain below 3.494. This 60-second diagnostic does not replace
final 300-presentation acceptance. Conversion overhead still exceeds 16 ms;
full C4 motion/event/transition/contact acceptance remains open. Default-off
and unchanged other-profile paths are retained.

Evidence: `manifest/step5-c4-smallroot-validation.json`, input histogram
`manifest/step5-c4-response-root-inputs.json`. Reproduce with
`tools/build_step5_c4_smallroot_test.py`, its generated oracle test,
`tools/build_step5_c4_smallroot_ab.py` and smallroot state/profile/elapsed tools.


### C4 full-loop A500 profile and revised plan (2026-10-13)

The physics-only profiles omit drawing, so they cannot explain the presented
frame rate. A full instruction trace of the **drawing** smallroot candidate
(physics, B8 drawing, scheduler waits, interrupts) was taken on A500 after
warm-up with warp off: 100 fields, 10 updates, 5 draws. Evidence:
`manifest/step5-c4-fullloop-a500.json`; tools `capture_step5_c4_fullloop_profile.py`
and `analyze_step5_c4_fullloop.py`. This is diagnostic, not acceptance.

| Per second of A500 time | ms |
|---|---:|
| Physics updates (5 x 92.3 ms) | 479 |
| B8 drawing (mean draw span **187.1 ms**, 176–196) | 493 |
| Interrupts outside drawing, gaps, scheduler | 28 |
| Idle in the scheduler wait | 0.2 |

The CPU never idles. The model `F = 0.98 x (990 - 5U) / D` reproduces the 60 s
measurement (2.77 FPS). The plan's earlier `R = 166.86 ms` underestimates the real
in-loop drawing cost by 20 ms. Even with zero conversion overhead beyond the
native step, physics alone cannot reach the floor: with D = 187 ms, 3.494 FPS
needs U <= 64.5 ms per 200 ms update (-30%).

Where one 187 ms draw goes:

| Item | ms/draw |
|---|---:|
| **Blitter-finished interrupts** (1,439/s): Kick 1.3 level-3 dispatch 26.5, graphics blit handler 6.8, host ExitIntr 3.4, exception gaps 3.2 | **39.9** |
| Host `gfx_WaitBlit` polling (real blitter waits) | 19.7 |
| Native road drawing `$6a000–$6bfff` | 48.8 |
| Native `$24000–$25fff` | 32.0 |
| Native `$32000` | 10.9 |
| Native beam wait (`B8_65728`, waits for line >= 256) | 8.4 |
| Other | 27.4 |

Every one of the 2,878 traced blitter interrupts found the graphics QBlit and
QBSBlit queues empty. Neither QBlit's body nor any QBlit/QBSBlit call executes in
the race; blits are synchronous (OwnBlitter + polling WaitBlit). The interrupts do
no work, and the legacy loop pays the same cost (step 3: 15,266 blitter dispatches
per 500 fields).

Physics per 200 ms update (omitted-drawing profile, 659.7k cycles = 93.0 ms):
native 259k, module helpers 265k, hook bodies 120k, trampolines 15k. Helper calls
per update: S32x16 multiply ~232 (~237 cycles each), Native200 multiply ~136,
division ~124 (~420 cycles including restore/done), Q15 ~106, rotation ~44,
U64 square root ~8.5 (~3,400 cycles each).

#### Projection (F = 0.98 x (990 - 5U) / D)

| Change | U ms | D ms | FPS |
|---|---:|---:|---:|
| Today | 92.3 | 187 | 2.77 |
| D1 only | 92.3 | ~150 | ~3.45 |
| P1–P5 only | ~78 | 187 | ~3.14 |
| D1 + D2 | 92.3 | ~145 | ~3.57 |
| D1 + P1–P5 | ~78 | ~150 | ~3.92 |
| D1 + D2 + P1–P5 | ~78 | ~145 | ~4.06 |

D1 is required: no physics-only path reaches the floor.

#### Steps (each with equal-layout A/B, the 27-block exact-state gate and the 60 s elapsed test)

- **A0 – Feasibility gate.** Build a diagnostic that clears INTENA BLIT
  (`$0040`) at C1 activation, then rerun the full-loop trace and the 60 s elapsed
  test. Expected: draw span 187 → ~150 ms, FPS 2.77 → ~3.4. If the draw saving
  is < 25 ms, stop: 68000 stays legacy-only (see Abort).
- **D1 – Blitter-interrupt suppression in the race.** Read INTENAR at activation
  and clear BLIT only if it was set. Restore it on every C1Restore path (exit,
  unload, fault). Also audit pause and modal paths for any QBlit/QBSBlit use.
  Gates: exact state for 100 updates, identical images, contact and exit
  restoration, INTENA restored.
- **D2 – Native beam wait.** `B8_65728` waits on VPOSR V8 (8.4 ms/draw). Find
  what it protects (buffer swap or copper update). If B8 already owns that
  synchronization, drop it or move independent work before it. Target −5 ms/draw
  with no tearing in captured frames.
- **P1 – U64 square root.** Normalize, seed from a table, finish with an exact
  correction. Target 28.8k → ≤ 7k cycles/update (−3.0 ms).
- **P2 – S32x16 multiply.** Histogram the operands (as was done for the roots),
  add a one-`muls.w` path when the 32-bit operand fits in 16 bits, and inline the
  two hottest call sites. Target 55k → ≤ 33k (−3.1 ms).
- **P3 – Division call overhead.** Fold `FF1DivRestore`/`FF1DivDone` (13.9k)
  into the callers' existing saves. Target −10k (−1.4 ms).
- **P4 – Native200 multiply fast paths** from an operand histogram. Target 34k →
  ≤ 22k (−1.7 ms).
- **P5 – Hook bodies and trampolines (135k).** Consolidate per-car context saves
  (`fine_boundary`, `bridge_context`, `velocity_context`, `bridge_67b52`) as B4
  did for the 020. Target −40k (−5.6 ms).
- **Acceptance.** ≥ 3.494 FPS over 300 presentations (existing method), and
  ≥ 3.6 FPS in the 60 s demo diagnostic for heavy-scene margin. Add a fixed
  heavy workload (start grid, all cars visible) that must not fall below the
  legacy build in the same workload. Keep the ≤ 16 ms conversion-overhead gate
  as a target, not a blocker, once the FPS gates pass with margin.

**Abort / fallback.** If after A0, D1, P1 and P2 the 60 s diagnostic is below
3.5 FPS, stop. The 68000 (including A500 + Fast) keeps the legacy loop by default,
and the time-model improvements are 68020+ only. C4 stays default-off, so the
shipped A500 behaviour never regresses. D1 alone could also be offered on the
legacy A500 path as a separate user decision. It would raise legacy FPS, and with
it legacy game speed, since that speed scales with frame rate.


### C4 A0 blitter-interrupt feasibility gate (2026-10-13)

**Passed.** Equal-layout drawing binaries differ in exactly one byte of the
A0 control word. The explicit `FF1_C4_BLIT_A0` diagnostic clears INTENA BLIT
at C1 activation; ordinary builds omit it entirely. This diagnostic has no
restoration and is only used in bounded emulator runs terminated afterwards.
D1 must add and validate ownership/restoration before this can be a candidate.

Full-loop 100-field traces: baseline five complete draws average **187.05 ms**;
candidate six complete draws average **147.14 ms**, saving **39.91 ms/draw**,
above the 25 ms feasibility gate. These are short diagnostic windows, not final
300-presentation acceptance. All three analysers agree; raw normalization and
Chip DMA checks pass. Trace pairs are losslessly archived with verified hashes.

Matched untraced elapsed runs: baseline 166 presentations / 60.01553359 s
(**2.7660 FPS**); candidate 214 / 60.11569302 s (**3.5598 FPS**). Both advance
60 simulated seconds and both native clocks by 600 tenths, with warp off and
error zero; candidate elapsed error **0.1924506%**. The candidate exceeds the
original 3.494 floor diagnostically, but not the revised 3.6 margin.

**100 updates match all 27 state blocks exactly with drawing in both arms.**
INTENAR ends at 0x67ec in the control and 0x67ac in the candidate: only BLIT
is cleared. No state gate was relaxed. Continue with D1, D2 and P1-P5; retain
the explicit post-A0/D1/P1/P2 3.5 FPS abort gate and all final correctness gates.

Evidence: `manifest/step5-c4-blit-a0-validation.json`; builders/capture tools
`tools/*step5_c4_blit_a0*`, full-loop analyser `analyze_step5_c4_fullloop.py`.


### C4 D1 race blitter-interrupt ownership (2026-10-13)

**Passed as a default-off candidate.** `FF1_C4_BLIT_GUARD` requires the complete
200 ms build and is mutually exclusive with A0. Runtime `C4BlitEnabled` defaults
to zero. Acquisition reads INTENAR and clears BLIT only when enabled, recording
ownership. Exit/unload through C1Restore, C1Fault, and the separate converted
velocity/fine fault stop restore the owned bit. Pause restores before entering
native modal code; resume reacquires. No DMA address or allocation policy changes.

The initial D1 build omitted the separate motion-fault stop. It was corrected
before acceptance; final builds/evidence use **blit-d1-v2**. All final checks:

- **100 ordinary updates exact across 27 blocks**, drawing in both arms.
- **100 forced-contact updates exact across 27 blocks**: 15 injections and 12
  native wall-handler calls in each arm. Injection runs at converted fine_bounds
  and retains the complete C4 motion hook. This checks D1 equivalence, not the
  outstanding independent validation of the entire 200 ms contact model.
- **10 matched rendered images exactly equal at every RGB pixel**, with drawing
  forced at each admitted update in both fixtures; full 754x576 images retained.
- Native exit restores INTENA (0x67ac -> 0x67ec), all audited native helper bytes,
  and patch ownership. Moved reload restores before unload, resets/seeds all
  eight motion owners and reacquires BLIT after reactivation; 20 further updates
  complete with no error.
- Repeated acquire/release, initially disabled BLIT, pending completion and real
  C1Pause/C1Resume hooks pass. Only the pause fixture's native input-wait callee
  is temporarily stubbed; this is not physical-input/full-modal acceptance.
- Forced C1 and converted-motion faults restore BLIT and clear ownership before
  their error loops (codes 100 and 17).
- All 118 executable CODE hunks audited for direct QBlit/QBSBlit vector calls.
  Two offset matches resolve to Exec FindTask; no direct graphics queue calls
  found. Computed calls/library-internal use are not proven absent by this scan;
  original full-loop empty-queue evidence and restored modal entry bound scope.
- **13 other-profile artifacts and the unguarded C4 binary remain byte-identical.**

Final equal-layout drawing binaries differ only in one byte of C4BlitEnabled.
Full-loop 100-field captures contain five/six complete draws respectively:
baseline **186.83 ms**, candidate **147.11 ms**, saving **39.72 ms/draw**. All
three analyser totals, raw normalization and Chip DMA checks pass. Verified
compressed traces are retained. Full-loop generic per-update analyser totals
include drawing; use phase spans for physics-only cost.

Matched untraced 60-second tests: baseline **166 / 60.03556547 s = 2.7650 FPS**;
candidate **214 / 60.11569302 s = 3.5598 FPS**. Both clocks advance 600 tenths,
warp remains off and runtime error stays zero. Candidate elapsed error is
**0.1924506%**. This is not final 300-presentation acceptance. The >=3.6 FPS
margin, fixed heavy-workload comparison and full C4 motion/event acceptance
remain open; <=16 ms conversion overhead remains a target under the revised plan.

Evidence: `manifest/step5-c4-blit-d1-validation.json`,
`manifest/step5-c4-blit-d1-v2-images.json`, and
`manifest/step5-c4-blit-d1-queue-audit.json`. Reproduce with
`tools/build_step5_c4_blit_d1_v2_ab.py`, its states/fullloop/elapsed tools, and
`build_step5_c4_blit_d1_v2_fixture.py` with exit, reload, ownership, fault,
motion-fault, images or contact (VERIFY) followed by matching capture tools.

**Next D2:** Read-only inspection finds the beam wait immediately after
OwnBlitter and before $6b050 clears the newly selected drawing bitmap. The earlier
$2428a call requests LoadView; no additional display-publication synchronization
was found before the clear. Do not simply remove the wait: audit which independent
CPU preparation can move into it while preserving display-buffer safety.
`manifest/step5-c4-d2-beam-audit.json` records the initial inspection. No D2 change
is implemented. Then continue P1-P5 and retain the explicit post-D1/P1/P2 abort.


### C4 D2 geometry preparation during buffer handover (2026-10-13)

**Passed as a default-off candidate.** `FF1_C4_ROAD_PREFETCH` requires complete
C4, and `C4RoadPrefetchEnabled` defaults to zero. After LoadView and OwnBlitter,
perform the CPU-only $6a2d0 road transformation and $6b168 clipping early. Save
its complete register/CCR result in the existing public owner. The original
road-call boundary restores that result and resumes at $6b372, retaining the
native pushed angle word. Native clear and sky blits remain in order and touch
neither the projection input nor output arrays. No native code is patched.

A VBL counter snapshot precedes preparation. If it has not advanced, the original
VPOS >=256 wait remains. Otherwise the earlier display-switch request has passed
a field boundary, so the old buffer may be reused. The trace independently
confirms **all seven observed preparation-to-clear transitions cross one or two
hardware fields**. This avoids dropping synchronization merely because the
physics and presentation are now separated.

Equal-layout binaries differ at one control byte. **100 updates match all 27
state blocks exactly**, and **10 matched lossless rendered images are identical
at every pixel**. Selected intermediate traced fields were visually checked; no
new road tearing was observed. Extra cross-format full-trace JPEG versus
single-field PNG comparisons are not exact tests and are not used for acceptance.
The original exact matched-image gate is unchanged. Twenty intact control frames
and distinct original per-field screenshots are retained for later inspection.

Full-loop 100-field captures: six baseline draws average **147.09 ms**, seven
candidate draws **139.53 ms**, saving **7.56 ms/draw**, exceeding the 5 ms target.
Three-analyser totals, raw normalization and Chip DMA audits pass; trace pairs
are verified compressed archives. All **13 other-profile binaries and both
accepted D1 arms remain byte-identical** when this guard is omitted.

Untraced 60-second runs: control **213 / 59.99550170 s = 3.5503 FPS**; candidate
**220 / 60.01553359 s = 3.6657 FPS**. Both native clocks advance 600 tenths,
warp stays off and error stays zero; candidate elapsed error **0.0258826%**.
This clears the revised diagnostic margin, but does not replace the final
300-presentation or heavy-workload gates and full C4 correctness acceptance.

Evidence: `manifest/step5-c4-road-d2-validation.json`,
`manifest/step5-c4-road-d2-field-safety.json`, `manifest/step5-c4-d2-beam-audit.json`.
Reproduce with `build_step5_c4_road_d2_ab.py`, its state/full-loop/elapsed captures,
and `C1_FIXTURE=images build_step5_c4_road_d2_fixture.py` plus the image captures.
**Next P1**, then P2 and the explicit post-P1/P2 3.5 FPS abort checkpoint.
P3-P5 and all final C4 acceptance requirements remain open.


### C4 P1 exact U64 seeded root (2026-10-13)

**Passed as a default-off candidate.** `FF1_C4_ROOT_SEED` adds a 3072-word
(6144-byte) CPU-only table in the existing public owner, after hot code and
binding metadata. The slave grows by 6300 bytes. The fast domain is
`2^48 <= N < 2^50`; the unchanged full-domain restoring root handles other inputs.
All integer input bits contribute to the exact floor root; no physics change.

Let `s=isqrt((N>>38)<<20)`, `r=s<<9`, `R=N-r*r`, and
`q=floor((R>>10)/s)=floor(R/(2*r))`. Then `r+q` is an upper estimate.
The correction residual `E=R-2*r*q-q*q` lies in `[-q*q,2*r)`, entirely within
signed 32 bits (`q<9216`, `2*r<2^26`). Its low longword therefore gives the exact
signed residual. While negative, add `2*(r+q)-1` and decrement the estimate.
This avoids a second full-width square without discarding fractional input bits.

**524,575 independent model cases**, every seed entry, and **36,921 native
arithmetic cases** pass, including seed/square/domain boundaries, fallback inputs,
register and stack preservation. Native fixtures are split into five batches;
a single oversized fixture previously timed out before race entry and is not
counted as a pass. **100 updates match all 27 state blocks exactly** with drawing
in both arms. Equal-layout drawing binaries differ at one control byte.

The initial lean fixture exposed assembly-size instability: the table-displacement
ADDA immediate shortened in the first pass and widened after the binding table
was generated. That invalidated later binding offsets and stopped installation
with error 100 before any C1Head. Fixed-width long encoding resolves it; builders
now assert every recorded operand against the final binary. The then-passing
VERIFY binary remained byte-identical. Final evidence uses **root-p1-v2**.

Matched eight-update traces: root calls fall from **30,826.25 to 6,943.25 cycles
per update**, passing the **<=7,000** target (64 roots in each window).
Total update cost falls from **657,574.25 to 637,826.75 cycles**, saving
**2.7838 ms/update**. The root-only saving and total saving differ because
surrounding timing/interrupt costs change. Both full-loop traces and both
omitted-drawing traces pass all three analyser totals, normalization and Chip DMA
audits; verified compressed archives are retained. Full-loop phase spans are in
the manifest, rather than treating drawing-inclusive totals as physics costs.

Untraced 60-second control: **220 / 60.03556547 s = 3.6645 FPS**. Candidate:
**227 / 60.07562925 s = 3.7786 FPS**, with **0.1258901%** elapsed error,
both clocks +600 tenths, warp off and runtime error zero. All **13 other-profile
binaries and both accepted D2 arms remain byte-identical** with the guard omitted.
This is not final 300-presentation, heavy-workload or full C4 correctness acceptance.

Evidence: `manifest/step5-c4-root-p1-validation.json`, its linked native/model/state
results and `manifest/step5-c4-root-p1-other-equivalence.json`. Reproduce with
`build_step5_c4_root_p1_v2_ab.py`, its state/profile/elapsed/full-loop tools, and
`P1_CASE_BATCH=0..4 build_step5_c4_root_p1_v2_wide.py` plus its native oracle.
The superseded first revision (9,428 root cycles/update) remains documented in
`manifest/step5-c4-root-p1-v1-evaluation.json`.
**Next P2**, then apply the explicit 3.5 FPS abort checkpoint. P3-P5 and all final
gates remain unchanged. The current profile's multiply operand histogram is
retained in `c4-root-p1-v2-ab-a500-omitted-profile/multiply-operands.json`.


### C4 P2 multiply histogram and two-site inlining (2026-10-13)

**Passed as a default-off candidate; post-P2 abort checkpoint passed.** The
matched eight-update operand histogram has 1769 S32x16 calls. After existing
zero-coefficient/integer-Q16 shortcuts, 1222 need the general path; only 223 of
those fit signed 16 bits. An isolated one-MULS shortcut passes 8192 native cases
and 100 exact 27-block updates, but costs **638,647.75 -> 639,608.25 cycles/update**
(+960.5). It was **rejected before stacking inlining**, removed from repository
source, and preserved with its fixtures in `tmp/build/p2-word-source` and
`manifest/step5-c4-p2-word-rejected.json`. No elapsed acceptance is claimed for
that rejected experiment.

`FF1_C4_MUL_INLINE` instead selects an optional rotation body, with
`FF1MulInlineControl=1` (original) by default. The two cosine products are the
most expensive of the four equally frequent rotation sites; the sine sites often
hit the existing zero shortcut. Inline the exact cosine operations with D6/D7,
which the rotation's outer frame already saves. Keep sine operations on the
shared helper, with atomic output/overflow behavior and all caller registers
preserved. The candidate grows by 228 bytes in the same public owner.

**6449 independent native conversion cases pass**, including overflow rollback
and register/stack checks; **100 updates are exact across all 27 state blocks**.
Equal-layout drawing arms differ at one control byte. **13 other-profile builds
and both accepted P1 arms remain byte-identical** when the guard is omitted.

Matched eight-update cost: **638,028.25 -> 630,063.5 cycles**, saving
**1.1228 ms/update**. The shared helper is **55,029 -> 31,716
cycles**, below the nominal 33,000 target, but rotation cost rises
21,516 -> 36,089 because work moved inline. **The net saving is 1.12 ms, not
23,313 cycles or the plan's estimated 3.1 ms.** Both full-loop traces and both
omitted-drawing traces pass analyser-total, normalization and Chip DMA audits;
verified compressed archives are retained.

Untraced control: **227 / 60.11569302 s = 3.7761 FPS**. Candidate:
**230 / 60.09566113 s = 3.8272 FPS**,
**0.1591814%** elapsed error, both clocks +600 tenths, warp off and error zero.
This explicitly passes the **post-A0/D1/P1/P2 >=3.5 FPS abort gate** and the
3.6 diagnostic margin. Continue P3-P5. Final >=3.494 FPS over 300 presentations,
fixed heavy workload and full C4 motion/event/transition/contact correctness
remain open; C4 is still default-off.

Evidence: `manifest/step5-c4-p2-validation.json`,
`manifest/step5-c4-p2-inline-other-equivalence.json`, and the linked rejected
word-path evidence. Reproduce with `build_step5_c4_mul_p2_inline_ab.py`, its
state/profile/elapsed/full-loop tools and `build_step5_c4_p2_inline_physics.py` /
`test_step5_c4_p2_inline_physics.py`. P3's read-only division-call histogram is
retained in `c4-mul-p2-inline-ab-a500-omitted-profile/division-calls.json`.


### C4 P3 bounded division caller (2026-10-13)

**Scoped candidate passed; 10,000-cycle saving target not reached.** The call
histogram spans 29 division sites. Several native callers have no D2-D5 frame
at all (`$6d4cc`, `$6e9f0`); others save only D2 or D2-D3/D4. Their original
callee-preserved register contract cannot be dropped indiscriminately merely
because the outer car hook saves registers. Native caller liveness between a
call and that outer restore still matters. The general `FF1Divide000`, its
native condition codes and `FF1DivRestore`/`FF1DivDone` remain unchanged.

`FF1_C4_DIV_LIMIT` specializes only `FF1VelocityLimit020` (the existing 68000
adapter name). Its D2/D3 frame already preserves the needed scratch and original
input. Checks establish a nonnegative signed-word multiplier and divisor
1..65535. One DIVU handles quotients <65536; a high-word/divisor comparison
rejects larger quotients, which necessarily fail the existing signed-word output
bounds. The original input's **low word** supplies the sign, including cases
where its unused upper word has the opposite sign. Invalid inputs/range failures
return the original complete D0 and status -1. Both callers immediately test D1;
remainder and division CCR are not consumed. All other registers stay preserved.
`FF1DivLimitControl=1` keeps the original path by default.

**6008 independent native cases per arm (12,016 total)** cover signed-word
boundaries, upper-word garbage, zero/oversized divisors, invalid multipliers,
range rollback and register/stack preservation. **100 updates match all 27 state
blocks exactly**; equal-layout drawing binaries differ at one control byte.
All **13 other CPU-profile artifacts and both accepted P2 binaries are identical**
when the guard is omitted.

Matched eight-update cost: **632,265.75 -> 629,552.25 cycles**, saving
**2713.5 cycles = 0.3825 ms/update**. This does not claim the plan's
10,000-cycle estimate. Untraced control: **230 / 60.13572491 s =
3.8247 FPS**; candidate **231 / 60.07562925 s =
3.8452 FPS**, elapsed error **0.1258901%**, both clocks
+600 tenths, warp off and error zero. Four profile traces pass all analyser-total,
normalization and Chip DMA audits and are verified compressed. The candidate
full-loop window contains more drawing relative to updates; its drawing-inclusive
per-update average must not be interpreted as a physics regression. Use the
matched omitted-drawing cost and untraced elapsed result above.

Evidence: `manifest/step5-c4-p3-validation.json`,
`manifest/step5-c4-p3-limit-other-equivalence.json`. Reproduce with
`build_step5_c4_div_p3_limit_ab.py` and its capture tools;
`P3_MODE=0/1 build_step5_c4_p3_limit_oracle.py` plus its native test runner.
**Next P4, then P5.** Final 300-presentation, heavy workload and full C4 correctness
remain open. This modest specialization stays default-off with the rest of C4.


### C4 P4 unsigned-word native multiplication (2026-10-13)

**Scoped candidate passed; the 22,000-cycle helper target is not reached.**
`FF1_C4_MUL_WORD` adds a default-original gate. The candidate detects two
unsigned-word operands with one OR/upper-word test, uses one MULU, and preserves
native D1-D4 and XNZVC semantics. Zero operands preserve input X; nonzero products
clear X and derive final N/Z from the input XOR, as the original does. The
full-domain fallback is unchanged after restoring its scratch registers.

**127,488 native comparisons** cover all 32 input CCR combinations and register
preservation. **100 updates match all 27 state blocks exactly**. Equal-layout
arms differ only at the four-byte dispatch branch. All **13 other-profile
artifacts and both accepted P3 arms are byte-identical** without the new guard.

Eight matched updates: **629,211.5 -> 627,875.75 cycles**, saving **1335.75
cycles / 0.1883 ms**. Helper bucket: **35,642 -> 33,520 cycles**, below the
plan's estimated saving. Four traces pass analyser totals, normalization and
Chip DMA checks and are retained as verified compressed archives.

Untraced control: **230 / 60.07562925 s = 3.8285 FPS**; candidate:
**231 / 60.11569302 s = 3.8426 FPS**. Candidate elapsed error **0.1924506%**,
both clocks +600 tenths, warp off and runtime error zero. Counts are explicitly
`end.B8Frames - start.B8Frames`: P4 starts with one already-counted frame.
The P1-P3 counts were rechecked and their published FPS values were already
correct; their measurement starts differ. No historical checkpoint changes.

Evidence: `manifest/step5-c4-p4-validation.json`,
`manifest/step5-c4-p4-word-other-equivalence.json`, and the counting audit
`manifest/step5-c4-p4-fps-correction.json` (P1-P3 values unchanged).
Reproduce with `build_step5_c4_mul_p4_word_ab.py`, its capture/analyser tools,
and `build_step5_c4_p4_word_oracle.py` / its native runner.
**Next P5**, then 300-presentation, heavy-workload and full C4 correctness gates.
The candidate remains default-off.


### C4 P5 callback consolidation in validation (2026-10-13)

`FF1_C4_HOOK_P5` retains default-original dispatches. The candidate defers
velocity/position shadow loads to the speed-load hook at $6721c, and position/
speed shadow stores to the velocity-store hook at $685a6. Every displaced native
instruction still executes at its original site. Audited intervening native
spans contain only loads/stores and address arithmetic, with no calls, branches
or shadow-state consumers. Shared frames save exactly the scratch registers
used by the combined callbacks. This C4 build uses native heading hooks, so the
020 B4 heading-based fusion cannot be copied directly.

The $67b52 frame-rotation hook needs D0-D4/A0-A1, rather than all 15 registers:
bridge_context/bridge_rotate own those scratch values and the nested position/
velocity rotation adapters preserve the rest. Paired diagnostic MOVEM masks
select the reduced frame only in the candidate.

Initial gates pass: 100 exact 27-block updates; eight-update cost
**627,638.25 -> 618,602.25 cycles** (9036 cycles / 1.2738 ms). The 40k P5
saving target is not yet reached. Other 13 CPU-profile binaries and both P4
arms remain identical with the guard absent.

A new seven-continuation register comparison found apparent raw-SR differences.
All D0-D7/A0-A7 matched. The profiler source `newcpu.cpp:154-171` copies
`regs.sr` without `MakeSR()`, so those values can be stale between guest status
register instructions. Separate equal-layout fixtures explicitly execute
MOVE SR / restore CCR at each continuation. **All 488 returns then match all
16 registers and XNZVC**, including 104 frame rotations. Original performance
traces remain untouched; synchronized fixtures are correctness-only evidence.
The raw-SR rejection is retained, not reclassified as a passing flags test.
Evidence: `manifest/step5-c4-p5-v1-registers.json`,
`manifest/step5-c4-p5-v1-flags.json`,
`manifest/step5-c4-p5-v1-other-equivalence.json`.
Contact/reload and elapsed/full-loop validation are still in progress.


P5 initial consolidation validation complete: the forced-contact arms match
**100 updates / all 27 blocks**, with 15 injections and 12 wall calls in each.
Moved native unload/reload restores BLIT, re-seeds all eight cars, re-acquires
interrupt ownership and completes 20 updates without error. Untraced control:
**231 / 60.13572491 s = 3.8413 FPS**; candidate:
**233 / 60.11569302 s = 3.8759 FPS**, both clocks +600 tenths, elapsed error
**0.1924506%**, warp off and runtime error zero. Full-loop and omitted-drawing
traces pass all analyser, normalization and Chip DMA gates. The two extra
synchronized-CCR traces also pass; they are correctness fixtures, excluded from
cost claims. All six traces are verified compressed.

Evidence: `manifest/step5-c4-p5-v1-validation.json`. Reproduce with
`build_step5_c4_hook_p5_v1_ab.py` and its capture/analyser tools. Contact/reload
use `C1_FIXTURE=contact` / `reload` with the matching fixture builder; contact
also sets `C1_VERIFY=1`. The explicit flag fixture has its own flags builder,
profile captures and `analyze_step5_c4_p5_flags.py`.

This is a cohesive **initial P5 consolidation**, not completion of C4. The
remaining named hotspots still cost about 13k cycles/update in `fine_boundary`,
7.3k in `bridge_context` and 6.3k in `velocity_context`; inspect those next.
The 40k P5 target is not met. Final 300-presentation, heavy-workload and full C4
conversion/event/transition acceptance remain open. Default-off is unchanged.


### C4 P5 exact context offsets (2026-10-13)

**Passed as a default-off candidate.** Both `velocity_context` and
`bridge_context` retain their original range/error paths. For valid indices,
`FF1_C4_CONTEXT_P5` selects exact 12-byte offsets from eight-word tables in the
existing public owner. MOVEA/ADDA preserve X; the word result has the same
N/Z/V/C as MULU. No extra scratch register or runtime dispatch is needed.
Without the guard, both helpers and all other profiles remain unchanged.

The first revision retained a runtime dispatch: 620,893 -> 619,750 cycles in
its matched window, but no improvement over accepted v1's 618,602.25. It was
rejected before elapsed acceptance; source and evidence remain in
`manifest/step5-c4-p5-v2-evaluation.json`. The accepted **v2b** uses equal-width
instruction selection. Its control has MULU plus two alignment NOPs. Their
actual trace cost is explicitly subtracted when assessing the optimization.

**608 native cases per arm (1216 total)** cover all eight car indices and all
32 CCR combinations, result addresses/status, D1-D7/A1-A7 preservation, and
three invalid position indices. **100 updates match all 27 state blocks**.
All 13 other CPU-profile artifacts and both accepted P5 v1 arms are identical
when the guard is absent.

Eight matched updates: **622,003.25 -> 618,072.75 cycles**. The control's NOPs
cost **982.75 cycles/update** across 111 lookups. The adjusted saving is
**2947.75 cycles / 0.4155 ms**, not the raw 3930.5-cycle difference.
Untraced control: **232 / 60.07562925 s = 3.8618 FPS**; candidate:
**233 / 60.03556547 s = 3.8810 FPS**, elapsed error **0.0592407%**, both
clocks +600 tenths, warp off and error zero. Four traces pass analyser totals,
raw normalization and Chip DMA audits and are verified compressed.

Evidence: `manifest/step5-c4-p5-v2b-validation.json`, its cost breakdown and
other-profile equivalence manifest. Reproduce with
`build_step5_c4_context_p5_v2b_ab.py` and matching capture/analyser tools;
`P5_CONTEXT_MODE=0/1 build_step5_c4_context_p5_v2b_oracle.py` plus its runner.

**Next: fine_boundary**, then the final requirement inventory in
`manifest/step5-c4-final-acceptance.json`. The 300-presentation runner is now
`C4_ACCEPT_BUILD=<final build directory name> capture_step5_c4_acceptance_fps.py`.
It has been prepared, not run. The P5 40k target and full C4 acceptance remain
unproven; no default enablement or fallback decision changes.


### C4 P5 boundary coefficients and closeout (2026-10-13)

**Boundary candidate passed; P5's 40k-cycle saving target was not reached.**
`FF1_C4_BOUNDARY_P5` initializes 1280 signed Q15 coefficients scaled by 1000
with the exact native arithmetic shift. It covers all 1024 sine/cosine pairs
(the cosine window starts 256 entries later). The 2560-byte table is in the
same public CPU owner, appended after code/bindings to retain 68000 displacement
ranges. Fixed long offset encodings keep both assembler passes stable. Both
arms initialize the table at race activation; `C4BoundaryControl=1` keeps the
original per-call work by default. The candidate selects the table.

Every table entry matches an independent signed-floor model; both native input
and cached output remain unchanged across 100 updates. **100 updates match all
27 state blocks**; equal-layout drawing arms differ in one control byte. All
13 other profile builds and both accepted context-v2b arms remain identical
without the guard. The initial inline table placement exceeded code-reference
ranges at assembly, before any run; moving data after the code resolved it.

Eight matched updates: **618,819.25 -> 616,047 cycles**, saving
**2772.25 cycles / 0.3908 ms**. Untraced control:
**233 / 60.09566113 s = 3.8771 FPS**; candidate:
**234 / 60.03556547 s = 3.8977 FPS**, both clocks +600 tenths, elapsed error
**0.0592407%**, warp off and runtime error zero. Four traces pass analyser-total,
normalization and Chip DMA audits and are verified compressed.

Evidence: `manifest/step5-c4-p5-v3-validation.json`, its table and other-profile
manifests. Reproduce with `build_step5_c4_boundary_p5_v3_ab.py` and matching
capture tools; `analyze_step5_c4_boundary_p5_v3_table.py` checks all coefficients.

P5's named hook frames, context lookups and boundary work have now been evaluated
in three cohesive changes. Individual matched savings do not establish a matched
aggregate 40k saving, and that target is explicitly unmet. The actual FPS gate
passes with margin, so proceed to **final C4 acceptance** rather than adding more
micro-optimizations. The final 300-presentation run is in progress. Independent
integrated motion/position capture and replay tools have been prepared but not
yet run. Heavy workload, event/contact/transition, lifecycle, A500+Fast and final
controlled default-off checks remain tracked in
`manifest/step5-c4-final-acceptance.json`. C4 remains default-off.

### C4 final-candidate acceptance progress (2026-10-13)

The boundary-P5-v3 candidate (SHA256
cc2852f32bbdb578865c0c51122e30ab0fce1a47aad334e065970a5a0710ebda)
passes **300 actual presentations / 76.38158530 s = 3.92764825 FPS**,
untraced with warp off. Counter deltas give 382 updates = 300 presentations
+ 82 skips, with runtime error zero. This supersedes the earlier in-progress
status; the 3.494 FPS normal-demo floor is met.

Independent integer replay passes 800 velocity pipelines and 800 position
updates, 100 per car. This covers observed projection, normalized derivative,
limiting, response rotation, doubled integration, magnitude/clamps and native
publication. It does not prove unobserved events, contact or transitions.
Evidence: manifest/step5-c4-motion-replay-validation.json.

A500+Fast also passes: 246 presentation increments in 60.03556547 s, both
clocks advance 600 tenths, elapsed error 0.0592407%, 200 ms selection, warp off
and runtime error zero. The CPU owner is in Fast memory.
Evidence: tmp/step5/c4-boundary-p5-v3-ab-a500-fast-candidate-elapsed/result.json.

Heavy-scene performance and remaining scalar/event/contact/transition,
lifecycle and final controlled legacy checks remain open. C4 is default-off;
these results do not yet establish full C4 acceptance.

Independent integrated scalar replay now passes **3505 calls over 100 updates**:
1583 speed-rate calls, 1822 continuous-loss calls and 100 phase counts. An
independent integer model checks the input/output scalar, clamping, loss
saturation and eligible pulse count. Observed settings include 3/4/5 and rates
with 0/1/2 pulses; observed phases are 1/3 only. Native caller subtraction,
event eligibility and unobserved boundary cases remain separate acceptance work.
Evidence: manifest/step5-c4-scalar-replay-validation.json. Capture uses the
unchanged final candidate, with debugger stops for correctness only; its
timings are not performance measurements. An initial harness-only failure
was fixed by accepting lowercase 'Temporary breakpoint' replies.

Final-configuration directed fixtures pass **72 phase cases** (both parities,
settings 0/4/5, unrelated upper-register bits) and **30 clock carry/cap cases**
(two clocks, three mode/flag combinations, five boundary times). Each fixture
restores test state before 20 additional normal updates, with error zero.
Evidence: manifest/step5-c4-final-timing-validation.json. These are instrumented
correctness fixtures, not performance binaries. The clock fixture required a
test-only wider address calculation for its enlarged binding-table distance;
the production source and final performance binary are unchanged.

The final-configuration timer fixture also passes **45 cases**: 15 positive
countdown/contact/flag inputs through zero and 30 actual native clutch-body
cases across its threshold and speed/condition/mode eligibility. The clutch
oracle applies two sequential native decisions (including the 9/10 boundary),
rather than assuming a single doubled clamped increment. State is restored and
20 normal updates complete with error zero. Zero-entry bypass guards and
failure/RNG/recovery eligibility remain open; this is not full event acceptance.

Final **CUSTOM2=0 passes all four supported profiles**: A500, A500+Fast,
chip-only 020 and 020+Fast. At loops 125/150/175 every block in the unchanged
26-block inventory is exact against the unchanged release. Both arms use the
established step-1 RNG/countdown control, equal slave size and equal WHDLoad
reservation. The report records the original final-candidate hash and all
controlled artifact hashes:
manifest/step5-c4-final-default-validation.json.

Current remaining C4 acceptance: fixed heavy-scene legacy comparison; broader
event/recovery/native-writer/contact/multi-segment correctness; final
lifecycle/debt checks and documentation closeout. No production source was
changed by these acceptance fixtures, and the repository remains clean at
2def8a0. All new harnesses and evidence remain ignored as required.

### C4 late crowded-scene acceptance failure (2026-10-13)

**Failed no-regression check; full-loop re-profile in progress.** The final
candidate configuration with a test-only fixed crowded forward scene produces
**300 presentations / 103.82527055 s = 2.88946996 FPS**, versus the unchanged
native full loop's **300 / 90.86463964 s = 3.30161437 FPS** (about 12.5% slower).
Both are untraced and warp-off, with runtime error zero.

The fixture substitutes six native render arrays and three view words only
around drawing, then restores all 102 bytes exactly. Full simulation continues:
C4 completes 519 updates and skips 219 presentations; legacy completes 300
updates. Both scene snapshots are byte-identical; both equal-layout binaries
differ only in C1Control. Each of all 302 observed draws executes the native
front-view car routine once for each of cars 1..7, mask 254, with no incomplete
draw. C4 owns the suppressed BLIT interrupt; legacy retains it enabled.

This is a synthetic dense scene with overlapping cars, not a saved native
starting grid. The initial v1 fixture put opponents in the player's segment
(which the forward projection does not visit) and counted the rear-view routine;
that invalid workload is retained but rejected. V2 uses the next segment and
counts the actual front-view routine. Evidence:
manifest/step5-c4-heavy-v2-validation.json; tools/build_step5_c4_heavy_v2.py and
capture_step5_c4_heavy_v2.py (C4_HEAVY_FRAMES=300, C1_VARIANT=candidate/native).

The normal-demo final result remains 3.92764825 FPS. A0 and post-P2 abort gates
passed; this later failure must not be misreported as one of those earlier abort
conditions, nor as proof that every possible A500 implementation is incapable.
C4 remains default-off. Do not stack further changes before the matched
full-loop re-profile is complete.

The matched dense-pack full-loop traces are complete and audited. The observed
native all-car call averages **71.5132 ms**, versus **83.5366 ms** for C4;
the observed render span averages **221.5985 ms**, versus **190.6394 ms**.
C4 executes about five updates/s, while legacy updates once per frame. The
rendering saving therefore does not cover C4's higher update frequency in this
scene. These diagnostic spans include IRQ/gaps; the native render span excludes
its earlier buffer handover and later tail, so the untraced 300-presentation
comparison remains authoritative.

All three analyzers agree, raw normalization preserves every cycle/register
record, and DMA remains Chip. Both raw/normalized trace pairs are verified
compressed. The native short trace has fewer than five admitted comparison
windows; the audit's five-window statistic is explicitly null, not invented.
Evidence is linked from manifest/step5-c4-heavy-v2-validation.json.

The prescribed **native starting-grid** comparison is now being prepared from
an actual first-racing-draw capture, not chosen positions. Its cars occupy
segments 820/821/823/824/826/827/829/830, unlike the retained synthetic stress
fixture's one-segment pack. Scene source/checksum:
manifest/step5-c4-start-grid-scene.json. The stress failure remains an additional
known regression regardless of the starting-grid result.

### C4 decision: retain the 200 ms A500 design (2026-10-13)

The user superseded the earlier legacy-fallback outcome: **finish C4, retain
the 200 ms A500 path, and document the cases needing work**. Performance
failures remain failures; they no longer select the original loop. The normal
demo passes its FPS floor, while the synthetic dense pack is an open performance
regression with a completed full-loop diagnosis. This does not prove a universal
A500 limitation. The candidate remains default-off, with CUSTOM2=0 legacy exact;
production enablement and outstanding correctness coverage are separate.

The dense pack costs 83.5366 ms per C4 all-car update and 190.6394 ms per draw
in the diagnostic spans. Its higher simulation-update frequency consumes the
31 ms/draw rendering saving against native. Further work must target full-loop
capacity in dense visible-car workloads, preserving simulation speed and exact
state. Do not hide this result by replacing the workload with a lighter scene.

### C4 closeout with documented open cases (2026-10-13)

**The requested C4 implementation/performance assessment is complete; full
correctness and production acceptance are not passed.** This closes the planned
A0/D1/D2/P1–P5 work and the no-fallback assessment, not the open cases below.
The 200 ms A500 design is retained. No performance-triggered legacy selection
was introduced. CUSTOM2=0 stays legacy-exact and the candidate remains default-off.

| Workload (300 actual presentations, untraced, warp off) | C4 FPS | Legacy FPS | Result |
|---|---:|---:|---|
| Normal automatic demo | 3.927648 | — | 3.494 floor passed; separate 60 s test 3.897690 FPS passes 3.6 margin |
| Native starting-grid opponents, player camera centered | 3.750594 | 3.839047 | Floor passed; same-workload no-regression failed by 2.304% |
| Synthetic dense seven-opponent pack | 2.889470 | 3.301614 | Floor and no-regression failed; 12.483% regression |

The grid comes from the first native racing draw. Only player render X changes
from +350 to 0 because the original camera clips opponent 1. Opponent positions
remain native. Both arms use the identical 102-byte scene, invoke the forward
car renderer for all seven opponents on every observed draw, and restore all
substituted state exactly. The equal-layout binaries differ in one C1Control
byte. C4 performs 400 updates for 300 draws plus 100 skips; native performs
300 updates. No error or warp contamination was observed. Screenshot inspection
confirms the grid view. This is an explicit camera adjustment, not an unchanged
native-camera claim. Evidence: `manifest/step5-c4-start-grid-center-validation.json`.

The grid full-loop profiles average **82.3946 / 71.9254 ms** per C4/native
all-car call and **146.9451 / 181.5387 ms** per drawing span. Dense-pack costs
are **83.5366 / 71.5132 ms** and **190.6394 / 221.5985 ms**, respectively.
Five physics updates per second consume the drawing saving in both workloads.
Spans include IRQ/gaps and fixture pose save/restore; native earlier buffer
handover and later tail are outside the render span. They diagnose cost, not
replace the authoritative untraced FPS. Three analyser totals, normalization and
Chip DMA audits pass for both new grid traces, which are checksum-verified and
compressed. No raw profile trace is left outstanding by this closeout.

Final-configuration lifecycle validation passes native exit, moved unload/reload
with all-eight-car reseeding and 20 further updates, real pause/resume hooks,
BLIT ownership/idempotence and both fault restorations. A directed 20-field pause
preserves pending whole/fractional debt and rejects simulation consumption while
paused. The native input wait is stubbed; this is not physical-input or full-modal
acceptance. Evidence: `manifest/step5-c4-final-lifecycle-validation.json`.

**84 independent recovery/refill cases pass**: seven initial statuses, six
eligibility gates and two race types, checking all eight cars over two sequential
native pulses, refills/flags, remainder reset and presentation-list ownership.
Saved test state is restored and 20 further normal updates complete without
error. Together with the existing 72 phase, 30 clock and 45 timer/clutch cases,
this is **231 directed timing/recovery cases**, not full failure/RNG coverage.
Evidence: `manifest/step5-c4-final-recovery-validation.json`. The fixture's first
build exposed an assembler-pass offset change; fixed-width test addressing
resolved it without relaxing binding checks or changing production code.

Cases needing work, with reproduction evidence and closure gates in
`manifest/step5-c4-open-cases.json`:

- **C4-P01 — measured failure:** dense visible pack. Reduce full-loop rendering
  and/or all-car cost while maintaining five simulation updates/s; require the
  original absolute FPS floor and same-workload no-regression.
- **C4-P02 — measured failure:** centered native starting grid. Preserve this
  workload as a regression check alongside P01; it already clears the floor.
- **C4-Q01 — unvalidated:** failure/RNG event eligibility on each pulse and
  zero-entry caller guards. Passed decrement/recovery helpers do not prove these.
- **C4-Q02 — unvalidated:** independent all-car contact/native-writer ownership,
  fractional rebasing and multi-segment crossings, plus bounded contact debt.
  Observed motion replay and optimization A/B equality do not close this case.
- **C4-Q03 — unvalidated:** physical input and complete native modal transitions.
  Directed hook/lifecycle tests pass, but do not cover real interaction.
- **C4-T01 — unmet targets:** P5 aggregate 40k saving and <=16 ms conversion
  overhead. Retain the documented shortfalls; prioritize the measured full-loop
  regressions rather than stacking unmeasured micro-optimizations.

No universal A500 impossibility claim is made. A failed performance check is
recorded as failed, and missing correctness evidence as unvalidated. These are
follow-up work under the user's retained-200-ms decision, not reasons to silently
restore legacy behavior or to claim production acceptance. Step 5 as a whole
and production integration remain open.

Production changes are already committed through `2def8a0`; this closeout only
adds ignored local fixtures, measurements and documentation as required by the
repository rules. No source modification or empty/forced-harness commit was made.


### C4 open performance cases: closing plan (2026-10-13)

Read-only analysis of the retained full-loop traces
(`c4-heavy-v2-fullloop-a500-candidate`, `c4-start-grid-center-fullloop-a500-candidate`,
`c4-boundary-p5-v3-fullloop-a500-candidate`) and the final omitted-drawing profile.
Draw split: `tools/analyze_step5_c4_drawsplit.py <trace dir>`. No new capture or
source change.

**Sensitivity.** With the five updates/s held fixed, a cut of 1 ms per draw adds
F/D FPS and a cut of 1 ms per update adds 5/D FPS.

| Case | F now | U ms | D ms | +FPS per −1 ms draw | +FPS per −1 ms update | Gate | Needed |
|---|---:|---:|---:|---:|---:|---:|---:|
| P02 grid | 3.7506 | 82.39 | 146.95 | 0.0255 | 0.0340 | ≥ 3.839 (target 3.88) | +0.13 |
| P01 dense | 2.8895 | 83.54 | 190.64 | 0.0152 | 0.0262 | ≥ 3.302 (target 3.33) | +0.44 |
| P01 dense, absolute floor | | | | | | ≥ 3.494 | +0.61 |

**Where the dense draw differs.** Dense draws cost 44 ms more than grid draws.
35 ms of that is the native car-sprite blitter routine `$32d54–$32f0e` (52.4 vs
17.4 ms/draw). Per car it does one mask blit (A|B into `$1c1bc`); per bitplane it
does a colour blit into scratch `$1c1b8` (minterm from table `$32d48`:
`$0100`=0, `$0dc0`=Q&P, `$0d30`=Q&~P, `$09f0`=Q, where Q=`$10(a0)` and
P=`$c(a0)`), then a cookie-cut blit to the screen. Most of the cost lands on the
instructions right after each BLTSIZE write, so the CPU is stalled behind the
blitter. Sprite descriptors are static (9 in the dense window, slow memory).

**Blitter-wait overhead (every workload).** Native `$2a130` calls graphics
WaitBlit, which reaches StingRay's CIA-delayed `gfx_WaitBlit`. Calls per second:
1,296 dense, 1,886 grid. **89% complete in 100–199 cycles because the blitter is
already idle**, so for most calls the whole call chain is overhead.

#### Steps (in order; equal-layout A/B, 27-block exact state, identical frames, 300-presentation untraced FPS for normal, grid and dense)

- **R1 – WaitBlit fast path.** Replace the body of native `$2a130` (ledger-owned
  and restored like other patches) with an idle check: a dummy DMACONR read, then
  `btst #6`. Return immediately when the blitter is idle, otherwise fall through
  to the unchanged graphics call. Semantics are unchanged. Estimate: about 90
  cycles saved per idle call, which is −5.7 ms/draw grid, −5.0 dense and about −5
  normal. **Grid +0.15, dense +0.08.**
- **R2 – Exact colour-blit elision for minterms 0 and Q.** 47% of plane blits use
  these (dense 91/192, grid 136/270, normal 154/264). For Q, the colour blit is a
  straight copy into scratch with the same width and modulo 0, so the cookie-cut
  blit can take B from `$10(a0)` (plus the same d4 offset) and read identical
  words. For 0, the scratch is all zero, so use BLTCON0 `$0b0a`+shift (D = ~A·C,
  B unused). Skip the colour blit and its following `$2a130` wait. Keep the wait
  before the next register setup. First confirm nothing else reads scratch
  `$1c1b8`. Estimate: −9.5 ms/draw dense, −3.8 grid. **Grid +0.10, dense +0.14.**
- **Expected after R1+R2:** grid ≈ 3.99 (P02 closed, +3.9% over legacy).
  Dense ≈ 3.11 (still short).
- **R3 – Physics −8.5 ms/update (−60k cycles), for dense only.** Go in
  histogram ROI order; stop as soon as dense reaches ≥ 3.33 over 300
  presentations:
  - R3a, division (pool 46k including restore/done): histogram the divisors, add
    an exact reciprocal path for repeated or constant divisors, and fold the
    restore/done into the fast path. Target −20k.
  - R3b, `FF1VelocityRotate020` (36k, ~820 cycles/call): add a one-`muls.w` path
    when a component fits in signed 16 bits. Target −15k.
  - R3c, `FF1NativeMulP4Gate` (33.5k): inline the two or three hottest native
    call sites. Target −12k.
  - R3d: `FF1MultiplyS32x16_000` (31.7k) and the remaining hook frames. Target
    −13k.
- **Closure:** after each step, rerun all three workloads. Normal must keep
  ≥ 3.494 over 300 presentations and ≥ 3.6 in the 60 s test; no workload may fall.
  The legacy arm stays untouched (CUSTOM2=0 exact).

**Gate decision for P01.** Legacy itself runs the dense pack at 3.302 FPS, so the
3.494 floor (taken from the legacy normal demo) asks for more than the original
achieves there. Reaching it would need about −15.5 ms/update after R1+R2,
beyond the identified pool, and probably a simulation-structure change such as a
different opponent cadence. Recommended: close P01 on same-workload
no-regression (≥ 3.302, target 3.33) and keep the absolute floor for normal and
grid. This needs the user's decision.

### C4 closing-plan gate decision (2026-10-13)

The user selected **same-workload no-regression versus legacy** for P01.
Use the matched dense legacy result, with 3.33 FPS as the working target and
R3 stopping threshold. Keep the 3.494 normal/grid floor and normal 60-second
3.6 FPS margin. No A500 fallback; exact-state, frame, elapsed and legacy-exact
gates remain unchanged. R1 is under validation; no new performance case is
closed yet.

### R1 accepted; P02 closed (2026-10-13)

Commit `54627a3` adds the C4-only native `$2a130` idle shortcut. The busy
case uses the original graphics wait. The idle case preserves the settling
reads and original final status-byte condition flags. The existing native-hunk
ledger restores all changed bytes on exit. Compile-time absent builds reproduce
the prior final candidate SHA256 exactly; CUSTOM2=0 remains legacy exact.

| 300 untraced presentations, warp off | R1-disabled C4 | R1 | Matched legacy |
|---|---:|---:|---:|
| Normal demo | 3.934872 | 4.084026 | — |
| Centered native grid | 3.749655 | 3.882842 | 3.840031 |
| Dense pack | 2.889470 | 2.974995 | 3.299432 |

**P02 is closed. P01 remains open.** Dense uses the user-selected same-workload
no-regression gate, with 3.33 FPS as the target/R3 stopping threshold. No fallback.
Each workload improves versus its equal-layout R1-disabled control. Candidate
versus control and versus legacy differ in one selector byte each. The scene
bytes are identical; all seven opponents are drawn and scene restoration is exact.

All 100 updates match in the unchanged 27-block state inventory. Ten full RGB
frames per workload (30 total) match pixel for pixel in the draw-every-update
fixture. The independent 60-second run advances both clocks by 600 tenths, with
0.0074977% elapsed error and 243 / 59.9955017 s = 4.05030 FPS. Native exit restores
the actual WaitBlit hook and BLIT ownership. Controlled CUSTOM2=0 matches all
26 blocks on four profiles at loops 125/150/175. Both full-loop profiles pass all
three analyser totals, raw normalization and Chip DMA checks; traces are verified
compressed. Evidence: `manifest/step5-c4-wait-r1-validation.json`.

The first R1 trial lacked the final status-byte read; it was superseded before
acceptance. A test-only scene harness initially classified the R1-disabled C4
control as native; it now uses the unchanged C4 accounting equation for both C4
arms, and the full grid capture was rerun. No gate was relaxed.

R2 prerequisite audit: all SPS overlay relocation tables show five references
to `$1c1b8`: allocation guard, pointer assignment and deallocation argument in
file `$dc70`, plus colour-blit destination and cookie-cut B source in the race
sprite routine. Only the cookie-cut blit consumes scratch contents. Adjacent
word flags do not overlap the pointer and no address-of alias was found. Audit:
`manifest/step5-c4-r2-scratch-relocations.json`. Next implement R2, retaining the
wait before each plane's register setup and the unchanged mixed-colour paths.

### R2 image-capture diagnosis (validation in progress)

The first dense R2 image comparison failed by 346 pixels per frame, all in the
last two host-buffer columns. This failure is retained under
`c4-colour-r2-v2-heavy-v2-a500-{baseline-render,candidate}-images`.
A separate diagnostic emulator fills the complete host buffer with 0x55 or 0xaa
before the next profiled field and requests a full redraw. Both sentinels survive
only outside the actual 752 x 574 drawing coverage of the 754 x 576 exporter.
Every original differing pixel is in that untouched padding; every rendered
pixel matches the original capture. The first attempted sentinel after redraw
was ineffective and is retained as a rejected diagnostic, not acceptance evidence.

The corrected image-only observer initializes the complete buffer to zero before
each captured field. Full 754 x 576 RGB comparisons remain required: no cropping,
masking or pixel tolerance. The benchmark emulator is unchanged; timing, state,
elapsed and legacy-exact checks continue to use it. Reproducible proof and both
emulator checksums: `manifest/step5-c4-r2-frame-padding.json` and
`tools/audit_step5_c4_r2_frame_padding.py`. R2 performance gates remain pending.

### R2 accepted (2026-10-14); P01 requires R3

The zero/Q colour intermediate elision passes all scoped gates. Whole native
sprite table/routine signature is checked before patching; the hook is ledger
owned and restored. The larger diagnostic hosts use a nearby public-state anchor
for the binding-table address so the 68000 PC-relative displacement remains valid.
Without the R2 compile flag, the accepted R1 candidate SHA256 is unchanged.

| 300 presentations, warp off | R2-disabled C4 | R2 | Legacy |
|---|---:|---:|---:|
| Normal demo | 4.082912 | 4.139337 | — |
| Centered native grid | 3.882842 | 3.974555 | 3.839047 |
| Dense pack | 2.974995 | 3.131770 | 3.301614 |

100 updates match all 27 state blocks. Thirty full RGB frame comparisons pass
with the corrected image-only observer described above. The independent Boolean
and 5760 shift/clipping cases pass. The 60-second run takes 60.075629 seconds
(0.125890% error), advances both clocks by 600 tenths and presents 247 frames
(4.111484 FPS). Native exit restores all hook bytes and BLIT ownership. CUSTOM2=0
matches the unchanged 26-block gate on all four profiles at loops 125/150/175.
Both 100-field full-loop traces pass all three analyser totals, normalization and
Chip DMA checks; verified compressed traces are retained. No gate was relaxed.

P02 remains closed. P01 is still 5.14% below the matched legacy workload and below
3.33, so continue with R3 in histogram order. Fresh R2 division histogram:
`tmp/step5/c4-colour-r2-v2-fullloop-a500-candidate/division-histogram.json`.
Evidence: `manifest/step5-c4-colour-r2-validation.json`. The new mode remains
default-off; the 200 ms path is retained with no performance-triggered fallback.

### R3a accepted (2026-10-14); P01 requires R3b

The positive division path uses native DIVU when its quotient fits, an exact
2 KiB public-memory table for positive /10 inputs <=1023, a bounded reciprocal
for /56 inputs <=1048575, and an exact fold guarded on both operands of the
repeated 0x3fc000/700000 pair. Other inputs retain the general signed helper.
The fixed branch selector gives equal-layout A/B without a per-call memory test.
The disabled build exactly reproduces accepted R2. Default-off remains unchanged.

| 300 presentations, warp off | R3a-disabled C4 | R3a | Legacy |
|---|---:|---:|---:|
| Normal demo | 4.127928 | 4.222194 | — |
| Centered native grid | 3.966134 | 4.058570 | 3.840031 |
| Dense pack | 3.125887 | 3.196611 | 3.300887 |

145536 native comparisons cover quotient, remainder, all 32 CCR inputs and
preserved registers. The /56 model was exhausted over all 1048576 bounded inputs;
the guest oracle includes every table entry. All 100 updates match the unchanged
27-block state gate; 30 full RGB frames, native exit restoration and four-profile
CUSTOM2=0 checks pass. Elapsed error is 0.0925765%, with
4.196112 FPS and both clocks advancing 600 tenths.

Matched 100-field profiles reduce logic excluding presentation from
558903.5556 to 544464.2222 cycles/update: 14439.3333 cycles (2.03549 ms).
Division helpers save 16148 cycles; the planned 20000-cycle target is NOT met.
All three analyser totals, normalization and actual Chip DMA gates pass. Traces
are verified compressed. Evidence: `manifest/step5-c4-divide-r3a-validation.json`.

An initial diagnostic flagged a stale line-mode A pointer after the blitter had
finished. BUSY was clear, and the next setup instruction replaced it with a Chip
pointer before BLTSIZE. No actual non-Chip DMA occurred. The audit now distinguishes
inactive register contents from active DMA; every recorded DMA address remains
strictly checked. Original failure and proof are retained in
`manifest/step5-c4-r3a-idle-pointer.json`; this changes no game code or exact gate.

P02 remains closed; P01 still fails same-workload no-regression and dense <3.33.
Proceed to R3b in plan order, retaining the 200 ms path with no fallback. Rotation
histogram: only 169/666 general cosine products fit signed 16 bits, while
cosine=32767/sine=0 appears 126 times. An exact Q15 shortcut for that observed
case is independently modelled; implementation and all acceptance gates remain
pending. Do not assume zero sine means identity: Q15 rounding must be preserved.

R3a source and measured findings committed as `0010236defdef120abcc06612f6d56ebda1967bb`.

### R3b accepted (2026-10-14)

Rotation cosine products now use one signed multiply when the component fits
signed 16 bits. The measured common cosine=32767/sine=0 case uses the exact
identity floor(n*32767/32768)=n-ceil(n/32768); it preserves native Q15 shrinkage,
including negative fractions. Other coefficients and wide components retain the
existing algorithms. Three fixed branch operands select the equal-layout arms.
The compile flag absent build exactly reproduces accepted R3a.

| 300 presentations, warp off | R3b-disabled C4 | R3b | Legacy |
|---|---:|---:|---:|
| Normal demo | 4.221004 | 4.259421 | — |
| Centered native grid | 4.058570 | 4.092955 | 3.840031 |
| Dense pack | 3.196611 | 3.225527 | 3.300887 |

8527 independent integer-model arithmetic/conversion cases pass, including
signed-word transitions, coefficient extremes, negative rounding and atomic
rollback. The independent rounding identity also passes all low words at nine
signed high-word boundaries (589824 cases). All 100 updates match the unchanged
27-block state inventory; all 30 full RGB frames, native exit restoration and
four-profile CUSTOM2=0 checks pass. The 60-second test has
0.2256976% elapsed error and 4.240408 FPS.

Matched 100-field logic excluding presentation falls from
544526.6667 to 534472.6667 cycles/update:
10054.0000 cycles (1.41730 ms). The planned
15000-cycle saving is NOT met. All three analyser totals, normalization and
Chip DMA gates pass; traces are verified compressed. Evidence:
`manifest/step5-c4-rotate-r3b-validation.json`. Default-off, 200 ms and no fallback
remain unchanged. P02 remains closed. P01 same-workload gate: not passed.
Dense remains below 3.33; continue with R3c in histogram order.

R3B source and measured findings committed as `3da96797d1ffc3386d8b27c71c12effcc658d522`.

### R3c accepted (2026-10-14)

Three histogram-selected native multiply calls ($675a6, $6ea30 and $6cd5c)
now use guarded word/long products. The patch spans include the next overwrite
of D1; every register, stack value, low-32 product and XNZVC agrees at that
boundary. Nonpositive or out-of-range operands retain the previous multiply.
Native signatures are checked before patching, and the existing whole-hunk
ledger restores every changed byte on exit. All code uses the public owner.
One installation selector selects equal-layout arms. The compile flag absent
build exactly reproduces accepted R3b. The largest diagnostic hosts use an
existing near code anchor to keep installer references in 68000 PC-relative range.

| 300 presentations, warp off | R3c-disabled C4 | R3c | Legacy |
|---|---:|---:|---:|
| Normal demo | 4.259421 | 4.291153 | — |
| Centered native grid | 4.092955 | 4.116581 | 3.840031 |
| Dense pack | 3.225527 | 3.247208 | 3.300887 |

187776 native comparisons pass: 5868 operand/register cases at all 32 input
CCR combinations, checking D0-D5, SP and full CCR after the original D1 overwrite.
Cases include signed-word limits, wide range misses, zero/negative fallbacks,
independent D2 inputs and cross-product carries. All 100 updates match the
unchanged 27-block state inventory; all 30 full RGB frames, native exit restoration
and four-profile CUSTOM2=0 checks pass. The 60-second test has
0.0592407% elapsed error and 4.264139 FPS.

Matched 100-field logic excluding presentation falls from
536424.0000 to 529537.3333 cycles/update:
6886.6667 cycles (0.97080 ms). The planned
12000-cycle saving is NOT met. All three analyser totals, normalization and
Chip DMA gates pass; traces are verified compressed. Evidence:
`manifest/step5-c4-mul-r3c-validation.json`. Default-off, 200 ms and no fallback
remain unchanged. P02 remains closed. P01 same-workload gate: not passed.
Dense remains below 3.33; continue with R3d in histogram order.

R3C source and measured findings committed as `12fef219b179cf848b206fe12142be5238c34578`.

### R3d accepted (2026-10-14)

The two measured rotation sine products now use the enclosing routine's
already-saved D6/D7 scratch registers, removing nested save/restore frames and
subroutine entry/return. Zero and integer-Q16 shortcuts and the exact two-part
signed product are unchanged. Other shared-helper callers keep their D2/D3
preservation; a fixed selector skips the old per-call diagnostic memory test.
Three fixed branch operands select the equal-layout arms. CPU code remains in
the existing public owner. The compile flag absent build reproduces accepted
R3c exactly. Larger diagnostic hosts use range-safe installer references.

| 300 presentations, warp off | R3d-disabled C4 | R3d | Legacy |
|---|---:|---:|---:|
| Normal demo | 4.280115 | 4.322113 | — |
| Centered native grid | 4.107549 | 4.151961 | 3.840031 |
| Dense pack | 3.238081 | 3.273469 | 3.300887 |

8527 independent integer-model cases pass for the twelve 200 ms conversion
primitives, including full signed inputs, coefficient extremes, negative rounding,
atomic error rollback and register/stack preservation. All 100 updates match the
unchanged 27-block state inventory; all 30 full RGB frames, native exit restoration
and four-profile CUSTOM2=0 checks pass. The 60-second test has
0.0592407% elapsed error and 4.297453 FPS.

Matched 100-field logic excluding presentation falls from
532046.0000 to 524445.3333 cycles/update:
7600.6667 cycles (1.07145 ms). The planned
13000-cycle saving is NOT met. All three analyser totals, normalization and
Chip DMA gates pass; traces are verified compressed. Evidence:
`manifest/step5-c4-sine-r3d-validation.json`. Default-off, 200 ms and no fallback
remain unchanged. P02 remains closed. P01 same-workload gate: not passed.
Dense remains below 3.33; re-profile the remaining cost before further changes.

#### Measured follow-up after the original R3a-R3d sequence

The planned cycle savings were estimates; the accepted steps have not yet
closed P01. Preserve the user-selected same-workload gate and 3.33 working
stop target, with no cadence change, fallback or gate relaxation.

The fresh 100-field R3d trace contains 700 unsigned-word native products,
179 signed-word products, 220 zero cases and 83 positive word/long cases.
R3e will test guarded native products without register-save frames, preserving
D1-D7/A0-A6 and native XNZVC. The isolated mathematical model passes 1248576
comparisons; native guest execution and all integration gates remain required.

If R3e still misses the target, test direct calls to the existing idle WaitBlit
helper. The native stub accounts for 58168 instruction cycles across 4137 calls
in this entire trace (not a measured saving per update). The original and current
absolute JSR instructions match at all eligible observed native call sites;
only their destination operands would change. Retain the existing busy path,
settling reads, final status flags and ledger restoration. Tail JMP and host
callers are outside that initial candidate. Stop once the target and all exact
and same-workload gates pass.

Planning evidence: `manifest/step5-c4-native-frame-next-model.json`,
`manifest/step5-c4-wait-direct-planning.json`, and the native-multiply-groups
and wait-call-histogram files under the R3d candidate full-loop trace.

R3D source and measured findings committed as `b7de3dd8f120353b7c8cdc74990b4d443e53092d`.

### R3e accepted (2026-10-14)

Guarded unsigned-word and signed-word native products now avoid register-save
frames. Equal-input, zero-input and mixed-sign paths preserve the original
low-32 product and unusual XNZVC, including zero-input X and equal-input Z.
An exact eight-times-positive-long fold avoids the measured wide multiply.
Other inputs use the accepted general helper. D1-D7/A0-A6 stay unchanged.
One fixed branch selects equal-layout arms; the disabled build reproduces R3d.
All code remains in the existing public owner and the mode remains default-off.

| 300 presentations, warp off | R3e-disabled C4 | R3e | Legacy |
|---|---:|---:|---:|
| Normal demo | 4.318375 | 4.370039 | — |
| Centered native grid | 4.148510 | 4.197344 | 3.840031 |
| Dense pack | 3.266330 | 3.308909 | 3.300887 |

227712 native comparisons pass, including all 32 input CCR values, full-width
range misses, preserved D1-D5 and SP. The independent mathematical model passes
1248576 cases. All 100 updates match the unchanged 27-block state inventory;
all 30 full RGB frames and four-profile CUSTOM2=0 checks pass. Native exit
restores all 464 recorded patch words, including the three R3c inlined call sites. The 60-second test has
0.0258826% elapsed error and 4.348874 FPS.

Matched 100-field logic excluding presentation falls from
525592.4444 to 516861.3333 cycles/update:
8731.1111 cycles (1.23081 ms). All three analyser totals, normalization and
Chip DMA gates pass; traces are verified compressed. Evidence:
`manifest/step5-c4-native-frame-r3e-validation.json`. Default-off, 200 ms and no fallback
remain unchanged. P02 remains closed. P01 same-workload gate: passed.
Dense remains below 3.33; continue with the measured direct-WaitBlit follow-up R3f.

The first VERIFY control could not initialize the diagnostic marker: its
ws_GameLoader offset grew to 0x8020, outside the positive signed-word range.
A near entry trampoline (0x19da in that fixture) restores startup, preserves
the original entry ABI and adds a build-time range assertion. The failed slave
and memory/log evidence are retained in `manifest/step5-c4-r3e-entry-range.json`.
Both repaired arms pass all exact gates; compiling the feature out still
reproduces R3d. The generic lesson is committed in AmigaXDev as 5f9353e.

R3E source and measured findings committed as `8bf37f7592c983f5c7f093f9dd2bbc53c3515269`.

### R3f accepted (2026-10-14)

Twenty histogram-selected absolute JSR destinations now call the existing R1
WaitBlit helper directly, removing the intermediate native JMP. Every original
opcode and relocated destination is checked before any operand is changed.
The return address, registers, settling reads, final status flags and busy path
are unchanged. Tail JMP and private host callers retain the existing route.
All writes belong to the hunk ledger; both A/B arms validate the same sites.
One installation word selects equal-layout arms. Without FF1_C4_WAIT_DIRECT,
the build reproduces accepted R3e exactly. Arithmetic sources are unchanged.

| 300 presentations, warp off | R3f-disabled C4 | R3f | Legacy |
|---|---:|---:|---:|
| Normal demo | 4.370039 | 4.395692 | — |
| Centered native grid | 4.197344 | 4.221004 | 3.840031 |
| Dense pack | 3.308909 | 3.319912 | 3.300887 |

All 100 updates match the unchanged 27-block state inventory, all 30 full RGB
frames match, and CUSTOM2=0 matches the release on all four profiles. The exit
fixture confirms active direct routing and native restoration at all 20 sites,
and checks all 504 recorded patch words.
The 60-second test has 0.1258901% elapsed error and
4.377815 FPS. The 200 ms simulation interval, default-off mode
and no-fallback decision remain unchanged.

The matched 100-field traces pass all three analyser totals, instruction-cost
normalization and actual Chip DMA checks, and are verified compressed. Logic
excluding presentation measures 517602.6667 to
516959.1111 cycles/update (difference
643.5556); this is a rendering-call optimization and the
untraced workload timings above are the acceptance evidence.
Evidence: `manifest/step5-c4-wait-direct-r3f-validation.json`. P02 remains closed. P01 same-workload gate:
passed. Dense remains below the stopping target; re-profile remaining cost before another change.

Fresh R3f trace: the short-divisor path executes 662 times over 100 fields.
R3g will test guarding DIVU by swapping D0 instead of saving D2, then unpack
quotient/remainder directly without register-save frames. Preserve all native
flags and the full-domain fallback; validate against native division before
matched integration tests. The largest remaining arithmetic label is division
(35599 cycles/update in classification). Evidence: division-histogram.json in
`tmp/step5/c4-wait-direct-r3f-v1-fullloop-a500-candidate`. Stop at 3.33 and retain
the same-workload and exact gates. No interval or fallback change.

R3F source and measured findings committed as `4dd05496124235a56850f82f777383428842cb0e`.

### R3g accepted (2026-10-14)

The positive short-divisor path now checks quotient fit by swapping D0, without
saving D2. It unpacks the DIVU remainder and quotient directly into zero-extended
D1/D0. A word add clears X and a long test restores the exact native quotient
flags. A wide quotient restores D0 before entering the unchanged general path;
zero/negative operands and existing constant-divisor paths retain their logic.
The four-byte selector replaces the original save/move pair in the candidate;
the control executes those original instructions. The helper remains in the
existing public owner. Global labels expose the exact patch site; with the
feature absent, the complete slave is byte-identical to accepted R3f.

| 300 presentations, warp off | R3g-disabled C4 | R3g | Legacy |
|---|---:|---:|---:|
| Normal demo | 4.395692 | 4.407335 | — |
| Centered native grid | 4.221004 | 4.235329 | 3.840031 |
| Dense pack | 3.319912 | 3.331729 | 3.300887 |

158304 comparisons against original native division pass at all 32 input CCR
values, checking quotient/remainder, D2-D5 and SP, including directed 16-bit
quotient overflow boundaries and full-width signed range misses. All 100 updates
match the unchanged 27-block inventory, all 30 full RGB frames match, and
CUSTOM2=0 remains release-exact on all four profiles. Exit restores all
504 recorded patch words, including all 20 direct WaitBlit sites.
The 60-second test has 0.1924506% elapsed error and
4.391532 FPS; both clocks advance by 600 tenths. The 200 ms
simulation interval, default-off mode and no-fallback decision remain unchanged.

Matched 100-field logic excluding presentation falls from
516959.1111 to 513519.1111 cycles/update,
saving 3440.0000 cycles (0.48493 ms).
All three analyser totals, normalization and actual Chip DMA checks pass, and
traces are verified compressed. Evidence: `manifest/step5-c4-divide-frame-r3g-validation.json`.
P02 remains closed. P01 same-workload gate: passed.
Dense reaches 3.33; stop the R3 optimization sequence and audit P01/P02 closure.

This closes performance work only if the final closure audit passes. C4-Q01,
C4-Q02, C4-Q03, C4-T01 and production/release acceptance remain separate; no
universal FPS floor or completion of those correctness cases is claimed.

R3G source and measured findings committed as `aab718602c8a8767fd0616d549e057806b8470d0`.

### C4-P01 and C4-P02 performance closure (2026-10-14)

**P01 and P02 are closed. Stop the R3 performance sequence.** Final committed
candidate: `aab718602c8a8767fd0616d549e057806b8470d0`. P01 uses the user's same-workload no-regression
gate, not a universal dense-scene 3.494 FPS floor.

| Matched 300-presentation workload | Final C4 FPS | Legacy FPS |
|---|---:|---:|
| Normal demo | 4.407335 | — |
| Centered native grid (P02) | 4.235329 | 3.840031 |
| Dense seven-opponent pack (P01) | 3.331729 | 3.300887 |

Dense reaches the 3.33 stopping target. Normal/grid retain the 3.494 floor;
the normal 60-second run is 4.391532 FPS, above the 3.6 margin.
The final audit rechecks all nine committed stages: 100 exact 27-block updates,
30 full RGB frames per stage (retained PNG hashes recomputed), matched workload
and elapsed results, four-profile legacy-exact gates, profile normalization and
Chip DMA checks, source hashes and personal unsigned commit identities. Final
native division, selector bytes and complete exit restoration are also verified.
Evidence: `manifest/step5-c4-divide-frame-r3g-validation.json` and `manifest/step5-c4-performance-closure-audit.json`.

The 200 ms A500 simulation path remains; there is no legacy-loop fallback.
The mode stays default-off and CUSTOM2=0 stays legacy-exact. Original failures,
missed cycle estimates and the initial C4 assessment remain historical evidence.
C4-Q01/Q02/Q03 and C4-T01 are unchanged, and full Step 5 production/release
acceptance remains open. This closure covers only the two requested performance
cases; it does not claim the deferred correctness, physical input, CPU or
hardware acceptance work is finished.

### C4-Q01 correctness closure (2026-10-14)

Q01 is closed on the final R3g configuration, on both A500 and A500+Fast.
Each profile passes 420 installed event cases and 88 native caller guard cases,
then 20 ordinary updates with error zero and the 200 ms context retained.

The event oracle invokes the original native body twice from the same snapshot,
re-entering eligibility on each pulse, and compares it with one installed C4
call. It checks every native event destination, all 120 RNG bytes including
pointers, and the exact RNG call count. Cases cover all eight cars, negative,
zero and positive statuses, six tyre/component gates, all seven component
pointer entries, a healthy player, opponent tyre values 69999/70000/70001 and
three distinct RNG initializations. All 210 negative-status cases per profile
consume zero RNG calls; eligible cases consume 2 through 26 calls as expected.

The timer oracle enters the native caller before its eligibility test. It
covers signed boundaries, zero and expiration at one/two, every contact car,
and both flag states. Thus it tests bypasses as well as helper arithmetic.
The event and RNG bodies remain native; only region exits return to the test.
Timer consumers after the tested boundary are outside this fixture's scope.

No game-code defect was found. The initial test-only component pointer table
needed explicit relocation; the corrected 420-case run supersedes the initial
372-case prototype. All code/state redirects are restored before ordinary
updates resume. Game-source changes only document the verified invariants.
Evidence: `manifest/step5-c4-q01-validation.json`; fixture builders and captures
remain in the ignored harness. Q02/Q03 and production acceptance remain open.

Q01 findings committed as `9c40d4ce98a75d1491c83f770d8f0f37e19ee42f`.

### C4-Q02 native ownership checks (2026-10-14, partial)

The final C4 configuration passes 56 native position snapshot/reset/restore
cases and 40 cold velocity writer cases on A500. Independent models compare
every car's native arrays, shadow integer, fractional tail and remainder.
All 28 car pairs in both directions also pass longitudinal velocity exchange,
position tail assignment and sideways impulse ownership checks. Original native
control captures provide the native contact array reference; the transverse
integer is checked against the native writer while its fractional tail is
checked independently against the seed. Each fixture restores its changes and
completes 20 ordinary updates with error zero.

The initial contact model omitted sideways impulses and therefore failed; the
expanded model checks their native integer and preserved fractional tail. No
game defect was found in these suites. Evidence: `manifest/step5-c4-q02-ownership-validation.json`.
Q02 remains open: work/wall writers, multiple segment transitions, bounded
forced-contact debt and Fast-memory rechecks are still required. Q03 is open.

Q02-OWNERSHIP findings committed as `758fd82ec118f8baa20e987830c33c6f89a5e3b9`.

### C4-Q02 correctness closure (2026-10-14)

Q02 is closed on final R3g, on A500 and A500+Fast. Each profile passes 768
independent cases: 56 position save/reset/restore, 56 vector/scalar cold writes,
56 contacts (all 28 car pairs, both directions), 432 working wall/recovery
writers, 96 off-road writes and 72 complete multiple-segment paths. Every suite
restores native code/state and shadows, then completes 20 ordinary updates with
error zero and the 200 ms interval. No game-code defect was found.

The contact oracle checks native reference arrays plus independently seeded
scalar and vector fractions/carries, sideways integer impulses and position-tail
assignment. Work writers check every non-target owner. The segment oracle
models integration and per-product native Q15 rounding through two or more
actual native segment transitions, for straight, constant-turn and alternating
turn tracks with three transverse velocities, on every car. It is independent
of optimization A/B equality; lap wrap is outside these directed cases.

Both profiles also complete 50 warp-off updates with wall forcing restricted
to steps 11..20. Actual wall hits, all elapsed/consumed units and the return
below one pending interval are recorded; no pause exclusion or debt deletion
is used. This establishes recovery for the bounded episode, not an arbitrary
worst-case catch-up guarantee.

- a500: 11 wall hits; peak pending 1.079717612 intervals; recovered 1 update(s) after forcing ended.

- a500-fast: 11 wall hits; peak pending 0.780833659 intervals; recovered 1 update(s) after forcing ended.

Fixture failures remain documented: the initial contact model omitted sideways
impulses; the first crossing frame overlapped a native stack scratch slot; and
the combined work fixture exceeded a signed 16-bit binding-table offset. The
corrected fixtures use the same independent expected behavior. The work suite
is split into its original 432 cases and 96 added off-road cases, with a size
guard. Repeated native boundary visits are counted within the exact forcing
window rather than assuming one injection per update.

Evidence: `manifest/step5-c4-q02-validation.json` contains all suite manifests,
binary/harness hashes and debt result paths. Game-source edits are comments
only. Existing R3g exact-state/frame/elapsed/legacy gates remain applicable to
the byte-identical production candidate. Q03 actual input/modal coverage and
Step 5 production acceptance remain open; default-off and no fallback remain.

Q02 findings committed as `7e964c3728d3874c96efc39c630b460bd8c6fbe5`.

### C4-Q03 actual input and modal closure (2026-10-14)

Q03 is closed in emulator scope on A500 and A500+Fast, using the unchanged
final R3g candidate. Keyboard events pass through the emulated CIA and actual
KickEmu keyboard interrupt, keyboard.device queue, native raw consumer and
race/pause callers. Mouse motion and buttons enter the emulated hardware and
native VBL/polling paths. No game flags, native input consumer or pause wait
are replaced. This is device IRQ evidence, not a physical host or real-hardware
human play-test.

The actual route covers demo takeover, ESC pause/resume, K tow, race results,
Accept into the pit, pit clock advancement, paddock and standings panels,
Jerez qualifying-session selection, explicit calendar adjustment to 13:32,
native scripted session-clock catch-up, pit/cockpit entry and fresh driving.
Screenshots and control/readback logs identify the observed transitions.

Both profiles preserve exact active debt through a 50-field pause. Calendar,
session and completed-step counters remain fixed while paused; resume excludes
only the measured paused units. BLIT enable is checked directly through a
side-effect-free emulator query as well as the owner flag. Actual tow/exit
restores all 504 recorded patch words and releases the owner. Native pit time
continues while all 56 driving-clock bytes remain unchanged. Session/date jumps
and the native fast-forward to the selected session likewise do not add driving
debt. Qualifying calendar and session times agree to the native one-tenth call
boundary. Driving re-entry clears old pause exclusions and consumed time,
starts a fresh 200 ms epoch, and completes 21 updates with error zero.

- a500: preserved 9315800 pending clock units; 50 paused fields; pit clock advanced 17 tenths over the 120-field observation; 504 words restored; fresh 21 updates passed.

- a500-fast: preserved 7894780 pending clock units; 50 paused fields; pit clock advanced 18 tenths over the 120-field observation; 504 words restored; fresh 21 updates passed.

Input investigation resolved test-harness assumptions, not a game defect. A
pending OS keyboard request consumes the first key before the game request;
the second Space reaches the native consumer. The debugger's host-release
suppression must not discard explicit monitor releases. The final diagnostic
emulator clears that flag only for explicit monitor input and adds a read-only
INTENA query; its hash is recorded. Early retries could duplicate ESC and pause
again after resume; final runs retry only the first Space. Release events and
native caller provenance are retained. Diagnostic failures remain separate.

Evidence: `manifest/step5-c4-q03-validation.json`; full results and screenshots
under `tmp/step5/c4-q03-modal-final-{a500,a500-fast}-candidate/`. The saved replay
is `tools/step5-c4-q03-modal-replay.json`. Findings-only game-source comments
leave executable bytes unchanged; existing R3g exact-state/frame/elapsed and
four-profile CUSTOM2=0 gates remain applicable. Q01/Q02/Q03 are now closed.
C4-T01 remains a documented target shortfall; production integration, wider
version/track/save-load coverage and human hardware acceptance remain separate.
The 200 ms design, default-off policy and no-fallback decision are unchanged.

Q03 findings committed as `32226e72e55e099b624a4784efadca663f31d1d9`.

### Production integration closure (2026-10-14)

Passed in the documented SPS 0481 PAL emulator scope. A single tracked build now
combines the accepted C4 68000, C2 chip-only 020 and B8 020+Fast engines.
`tools/build.py` builds the authoritative WHD source and three
68000/020 payloads from tracked inputs plus the checksum-verified original game.
No game data or generated artifacts are committed. Binary: 260292 bytes,
SHA256 `60123fd26a8c188925c2213118f417e233ad0f883224372e87feeda477e2a836`; an independent rebuild is identical.

Mode remains default-off. CUSTOM2=0 retains the original loop and CUSTOM1 meaning;
CUSTOM2=1 supersedes the original timing callback for both CUSTOM1 settings.
Intervals remain 200 ms on 68000 (including Fast), native 100 ms on chip-only 020,
and 20 ms player / native 100 ms opponents on WHDLoad-qualified 020+Fast.
Actual Fast hunk/stack ownership is still verified. No performance-triggered A500
fallback is added. CPU allocations use MEMF_PUBLIC and DMA remains Chip.
Production activates on driving entry, without diagnostic RNG or warmup.

Integration fixes include excluding host offsets from native relocation binding,
fine pause/resume time exclusion, and restoring the patch ledger at the actual
K-tow cleanup edge ($65f48), which bypasses the ordinary loop-head exit check.
Fine B8 cache setup is retained. Runtime invariant/patch failures take the normal
WHDLoad error route instead of diagnostic spins. Actual NTSC startup reaches
TDREASON_MUSTPAL before public activation. Irek retains its original route.

Acceptance evidence (`manifest/production-integration.json`):

- Four-profile 100-update exact-state comparisons (27 full blocks), fine private
  fractions, and final coarse byte identity apart from host linkage immediates.
- Final four-profile controlled CUSTOM2=0 comparison against v1.01: unchanged
  26-block gate at native loops 125/150/175. Equal layout and step-1 RNG control
  isolate the known startup-timing divergence. CUSTOM1=0; both disabled-option
  variants and repeated overlays remain the broader Step-7 matrix.
- All three enabled engines complete error-free updates with CUSTOM1=0; the
  60-second measurements use CUSTOM1=1. Public patch installation passes a
  constant replacement mode, independent of the original timing-disable option.
- 30 exact RGB frames per engine. Fine capture uses equal endpoint poses and
  the complete second scanout. Four initial one-field images captured partial
  updates; no pixels are excluded. An intermediate attempted debugger hold is
  not relied upon; the passing final capture performs no debugger writes.
- Final A500 and fine actual device-input/modal replays: exact paused debt,
  full ledger restoration, native menu/session time exclusion, and 21 fresh
  driving updates after Jerez qualifying selection. Prior Q03 A500+Fast coverage
  and Q01/Q02 semantics remain attached to the unchanged coarse engine.
- Forced zero-capacity patch ledger reaches the production abort on 000 and fine.
  Bad build-input checksum is rejected. Both 020 listings have no emitted SR saves.

| Profile | Presented FPS | Elapsed for 60 simulated seconds | Clock error |
| --- | ---: | ---: | ---: |
| a500 | 4.557554 | 60.135725 s | 0.2257% |
| a500-fast | 4.749801 | 60.135725 s | 0.2257% |
| a1200 | 6.647192 | 60.055597 s | 0.0926% |
| a1200-fast | 13.300287 | 60.035565 s | 0.0592% |

These are 300-presentation untraced production measurements, warp disabled, with
immediate activation and the native uncontrolled demo seed. They are not a
matched speedup comparison with the original release. All clock errors are <1%.
Existing matched R3g grid/dense acceptance remains valid through engine identity;
no new production grid/dense figure is claimed.

Fine matched simulation-only audit: reference mean 51,744.7 / worst-five 52,946 /
peak 134,889 cycles; production 53,747.8 / 58,122.2 / 141,613. Mean rises 3.87%,
but all agreed gates pass (worst-five <=145,600, peak <=283,750; also B7 mean
<=100,000). All four observed opponent pulses return below one quantum within
the same update. Per-car and classification totals agree. Raw/normalized traces
preserve every cycle, register and DMA record; live DMA pointers remain Chip.
Trace trap ranges were disabled, so zero classified trap cycles are not a trap
audit. Lossless verified trace archives retain the evidence without large raw
files.

The combined slave reserves 768 KiB expansion (256 KiB Kickstart + 512 KiB public
pool), plus 512 KiB Chip and host/slave overhead. Tested A500: 512 KiB Chip +
1.5 MiB Slow, optionally 2 MiB Fast; 020: 2 MiB Chip, optionally 4 MiB Fast.
Original minimum-memory equivalence is not claimed.

Production integration is closed; broader release qualification is not. Keep
minimum-memory/runtime/cache variants, wider tracks/controls/season save-load,
Irek, human handling and real hardware explicit. Enabled NTSC is deliberately
unsupported. 030/040/060 analysis remains deferred. C4-T01 micro targets remain
unmet; the user's same-workload P01/P02 gate remains satisfied.

Final A500 replay restores all 503 recorded words (fine: 902). Initial demo
takeover required spacing the first Space retry release and press across native
fields; the failed input-delivery diagnostic is retained separately. The final
replay uses actual device events and does not replace guest input consumers.

Production source commits: `7fd47fd`, `e82dcb4`. Committed acceptance findings:
`ba23d6d` in `docs/slave.md`.

## Emulator release qualification closure (2026-10-14)

The requested emulator qualification and030/040/060 performance analysis are
complete in the documented SPS0481 PAL scope. Human playtesting and physical
Amiga testing are explicitly deferred; no public release has been made.
The accepted slave remains260292 bytes, SHA256
60123fd26a8c188925c2213118f417e233ad0f883224372e87feeda477e2a836.

All four calibrated accelerated profiles present16.640136 FPS in300-presentation
windows;60 simulated seconds take59.975470 emulated seconds (0.04090% error).
Two fresh1000-field runs per profile agree exactly. Quantization and coarse
040/060 cache charging prohibit real-hardware CPU rankings. Cache variants,
040/060 functional MMU, nine100-update state comparisons and300 full RGB images
pass. Original-release observations are separate, not matched-state speedups.

Both disabled CUSTOM1 values pass first-load state and1005-word byte gates on
four profiles, plus native overlay reloads. Native lap crossings pass all three
engines. F1/Fiorano controls, F3/Monaco pre-start grid through green and501 error-
free updates, Rio demo/transport, pause/tow/pit/session/results, matched save
roundtrips and F10 pass in the stated scopes. Native repair70-tenth requests
advance78 tenths in both arms; Monaco-to-Rio travel adds exactly4days, preserving
session clocks and leaving enabled driving context zero. Earlier directed
contact/recovery/fuel/wear acceptance remains attached to unchanged engine bytes.

Runtime/memory exclusions are part of qualification: API17 remains, WHDLoad17.0
passes functional checks with Fast memory;20.1 chip-only020 needs ConfigDelay=0
and SplashDelay=0; emulator save/load requires NoWriteCache. Smaller-memory
failures are documented, not silently treated as passing. Irek is unavailable;
enabled NTSC is rejected. Human full races and real hardware remain deferred.

Local release candidate: tmp/release/FerrariFormulaOne-1.02-rc1.zip.
Evidence: manifest/release-qualification.json, release-candidate.json,
release-final-artifact-audit.json and tracked
docs/RELEASE_QUALIFICATION.md. The candidate contains no game,
Kickstart, runtime or fixture data. Rebuild and deterministic archive checks pass.
C4-T01 remains optional optimization, not an open acceptance gate.

## Driving-control acceptance reopened (2026-10-14)

RC1 fails right-button launch from rest in the 20 ms player path. The integrated
velocity feedback incorrectly applies the native sub-4 stopping threshold after
20 ms scaling. A corrected candidate removes this redundant cutoff while leaving
the native proposal stop/reset and 500 cap intact. Basic live acceleration, coast,
brake to zero, idle and restart now pass on 020+Fast. Broader checks are ongoing.
The Monaco 32-bit speed read was invalid (two adjacent 16-bit car speeds); its
player-acceleration claim is withdrawn. See tracked CONTROLS_REGRESSION.md.

## Driving-control correction accepted (2026-10-14)

Commit 8141408 removes the redundant sub-4 integrated-speed cutoff from the
20 ms path. Native stop/reset and cap remain. Corrected production SHA256
e57c42ec5160f1771146045f81a31c59ff7942f30678e801fb5c00178dd2910d (260276 bytes).
Native 020+Fast throttle/coast/brake/idle/restart/steering and F1 manual
clutch/gears pass; legacy controls compared after braking inherited demo momentum.
User configuration represented by 040/40 MHz, enabled MMU, 32 MiB Z3 Fast passes
clutch launch (0 -> 224), brake to zero, stationary idle and right-only restart
(99), with steering and zero errors. Warp functional check, not hardware timing.
1111 arithmetic cases pass; controlled 100-update state (27 blocks and private
physics) exact; production host/coarse payloads unchanged. 60 simulated seconds
in 60.035565 emulated seconds, 13.22979 FPS/300 presentations on 020+Fast, zero
errors. Independent corrected-source rebuild exact. RC1 Monaco acceleration
claim withdrawn (combined two 16-bit car speeds). RC2 acceptance is scoped to
these new checks, not a relabelled full RC1 qualification. Full human races and
real hardware remain deferred. See manifest/drive-controls-validation.json and
tracked docs/CONTROLS_REGRESSION.md.

RC2 replacement packaged and verified: dist/FerrariFormulaOne_v1.02-rc2_0481_Performance.lha,
677063 bytes, SHA256 cdd0357047f302f1faec3584eafba5af2bfa56720452ab1f7eb1ad806a87c68b.
All 40 original game files unchanged; 53-member archive CRC and full re-extraction
comparison pass. Package BuildInfo pins source validation commit 53f32f9.

## High-end rendering profile and next work (2026-10-15)

Unmodified RC2, 020+Fast, 48 non-warp PAL fields; 11 complete draws. Mean
62.634 ms/draw: WaitBlit body 22.163, wrapper 10.558, other 28.270, IRQ 1.606,
gaps 0.036 ms. Beam stage 4.923 ms; demo-only text 7.024 ms (overlapping
other work). 444.7 waits/draw, 177 of 315 observed colour planes eligible for
zero/Q elision. Non-instruction-traced independent boot matches start/end full
Chip/Fast snapshots, scheduler contexts, every field's DMA counts and displayed
bitplanes exactly. Cycle coverage 99.999795%; 28 boundary cycles unrecorded.
Short-window complete-interval FPS 12.7703. Not a whole-race/high-end CPU timing.
Plan and gates committed in docs/RENDERING_PLAN.md; local
evidence manifest/render-profile-020-fast.json. No new optimization applied.

## H1 discarded (2026-10-15)

User requested complete removal after profiling. All H1 source/integration and
local experimental source/binaries removed; RC2 restored in the launcher.
Matched 14-draw mean 60.102745 -> 60.111022 ms: waiting mostly moved from the
Chip vector into the helper. 300-presentation 020 normal demo 13.229790 ->
13.288485 FPS, p95 unchanged 80.127548 ms. Both elapsed errors 0.092576%.
100-update state/private oracle exact. Remaining qualification stopped, including
unfinished 040 comparison; no acceptance or high-end improvement claimed.
Findings: tracked RENDERING_PLAN.md; manifest/render-h1-withdrawal.json.
H2 is next. No H1 experimental switch or implementation remains.

## H2 accepted on completed evidence (2026-10-15)

H2 now removes exact zero/Q colour intermediates on the 020+Fast fine path.
The user accepted the completed measurements: 020 dense 5.70 -> 6.24 FPS,
030 grid 14.39 -> 16.64 FPS, with no regression in the completed comparisons.
100 state updates/private fractions and 90 full RGB frame comparisons are exact;
the 60-second clock gate and independent rebuild pass. Remaining H2 controls,
lifecycle, legacy-option and 060 heavy-scene qualification were stopped at the
user's request. This is accepted development work, not a newly qualified release.
See RENDERING_PLAN.md for the complete table, scope and deferred checks.

Current H2 source builds to 261,512 bytes, SHA256
`0a26fe52fd0e27e476dacdc53401c30b923a5d7dd7099bb025d8a06ee1d798b2`.
The packaged RC2 slave above is unchanged. H1 remains removed; H3 is next.

Measured workload table:

| Emulator / scene | FPS control → H2 | Mean ms control → H2 | p95 ms control → H2 |
|---|---:|---:|---:|
| a1200-fast / normal | 13.230 → 13.300 | 75.587 → 75.186 | 80.128 → 80.128 |
| a1200-fast / grid | 12.480 → 12.480 | 80.128 → 80.128 | 80.128 → 80.128 |
| a1200-fast / dense | 5.703 → 6.240 | 175.346 → 160.255 | 180.287 → 160.255 |
| 030-50 / normal | 16.243 → 16.640 | 61.565 → 60.096 | 80.128 → 60.096 |
| 030-50 / grid | 14.386 → 16.640 | 69.511 → 60.096 | 80.128 → 60.096 |
| 030-50 / dense | 9.984 → 9.984 | 100.159 → 100.159 | 100.159 → 100.159 |
| 040-40 / normal | 16.622 → 16.640 | 60.162 → 60.096 | 60.096 → 60.096 |
| 040-40 / grid | 16.640 → 16.640 | 60.096 → 60.096 | 60.096 → 60.096 |
| 040-40 / dense | 9.984 → 9.984 | 100.159 → 100.159 | 100.159 → 100.159 |
| 060-50 / normal | 16.603 → 16.640 | 60.229 → 60.096 | 60.096 → 60.096 |

Evidence: manifest/render-h2-validation.json. User accepted results and requested moving on; unfinished H2 checks are explicitly deferred in tracked RENDERING_PLAN.md. No new release qualification or package is claimed.

## H3 accepted: safe road preparation overlap (2026-10-15)

H3 is implemented on the fine path with CCR saves, the fine VBL counter,
line-256 fallback and lifecycle-reset workspace. Native clear/sky order is
unchanged. Earlier completion exposed transient native flag-over-clock writes
to the displayed bitmap; the corrected implementation composes both final HUD
passes on the back buffer and restores the pointer view before completion.

Matched 14-draw cost 60.110256 -> 59.484553 ms (-0.625703 ms / 1.04%).
020+Fast normal remains 13.312 FPS; grid 12.480 -> 12.844; dense 6.240 -> 6.316.
Normal/grid accelerated profiles remain 16.640 FPS. 030 dense remains 9.984;
040/060 dense 9.984 -> 10.004. All twelve 300-interval mean/p95 gates pass.
100 exact state/private updates, 90 full RGB comparisons, 60-second elapsed,
both buffer alternations and 15 safe clear transitions pass. Independent
trace/census full snapshots, contexts and DMA are exact; all DMA stays Chip.
Native F1/F3 controls, 040/MMU/32 MiB controls, pause/tow/pit/menu/re-entry,
905-word patch restoration, unchanged INTENA, fresh workspace/bindings, all
four profiles with both legacy options and signature rejection pass.

One pre-existing issue is documented as B8-PAL: the unconditional B8 COLOR00=1
palette pulse from 38b2c61 (absent from the original game). H3 preserves its
values; its scanline shifts with drawing. All 15 stable RGB images and bitplane
sequences match; transition-field JPEGs differ at the palette-pulse boundary.
The completed lossless RGB gate is unchanged, with no pixel masks. Remove this
in separate cleanup before a successor package; no full intermediate-JPEG
identity is claimed. The rejected first H3 candidate's actual flag/clock
corruption was fixed and its evidence retained.

Current slave: 262,056 bytes, SHA256
ac034f9786055bcb04c45383740def6cf249bf0910260dbc322c98461f15a8c2.
The 000/chip-only 020 payloads remain byte-identical; default-off and RC2 LHA
unchanged. H4 is next. Full evidence is in manifest/render-h3-validation.json
and the tracked RENDERING_PLAN.md. Human playtesting and hardware remain deferred.

H3 implementation and findings committed as e1c5ca627ef42ce9bdcb811d4ff71f34c3edc45e.

## H4 accepted: batch demo text and remove duplicate clock writes (2026-10-15)

`RenderText.s` replaces the driving demo's 21 separate glyph operations with
one packed bitmap operation per destination. It predecodes the fixed label's
font columns but rebuilds its pixels from the live font on every draw. The
192-byte CPU workspace is public memory. After WaitBlit, it copies the packed
rows into the existing 1,020-byte Chip colour scratch; native `$24ae0` retains
shifts, masks, foreground/background minterms and first/second buffer order.
A final WaitBlit returns scratch to native ownership. H2's whole-overlay audit
establishes that the completed sprite cookie-cut is its only native data reader.
There is no new allocation, native patch site or interrupt ownership.
Changed label, position, style, view or unsupported font dimensions retain the
native text path.

The clock optimization applies during player driving as well as the demo.
H3 temporarily gives both native HUD pointer views the same back buffer.
`FF1RenderClockDigit` draws each digit once when those pointers are identical;
the native immediate second overwrite has the same source, coordinates and
colours, with no intervening writer. Its masked foreground/background operation
is idempotent. Different destinations and other native display modes retain
`$23288`. This never suppresses a later frame's draw: every clear, buffer swap,
font/value change and re-entry gets fresh pixels. No destination cache needs
to survive a view/menu/reload. The public reset table also clears the workspace.
Flag rendering is unchanged; it remains separate work for the next profile.

Fourteen complete matched endpoint draws cost **60.156836 → 55.786248 ms**,
a **4.370588 ms / 7.27%** reduction. The matched entry interval costs
**64.377998 → 60.080593 ms**. The demo label falls **7.245341 → 1.549847 ms**,
with **126 → 6** BLTSIZE operations. The clock falls **2.091870 → 1.153091 ms**,
with **42 → 21** operations. Beam waiting absorbs some primitive savings;
the reductions must not be summed and presented as additional whole-frame gain.
These endpoint fixtures are not ordinary-demo FPS measurements.

The equal-layout control disables both H4 operations with one immutable preset
byte. All 100 updates match all 27 semantic blocks and private fractions exactly.
Normal, grid and dense each pass 30 complete 754 x 576 RGB comparisons, without
cropping, masks or pixel tolerance. All 180 acceptance PNGs are independently
rehashed. The first normal image run exposed an observer scheduling issue:
its two-field capture allowed the faster arm to skip updates 2, 11 and 27;
all common update images were exact. The corrected normal/dense sampling fixes
30 update numbers (1, 5, 10, …, 145), with no writes to game state and no change
to image equality. Grid's original 30 consecutive samples already passed.

The 48-field paired trace has 15 exact shared interior bitplane-DMA sequences;
the faster arm reaches one additional frame. Repeated identical fields are collapsed; shared sequences align at zero,
with every transition retained. Native projection registers, clipping, colour
planes and clear destinations match. Both buffer banks and all observed safe
handover checks pass. All DMA stays Chip. The inherited **B8-PAL** diagnostic
pulse still changes scanline with timing, so identical full transitional RGB
fields are not claimed. H4 makes no palette change; cleanup remains separate.

The independent pixel model passes 400 random live-font/stride cases, and all
32 Boolean cases for clock overwrite idempotence. The complete emulator image
checks provide the native shift/mask check. Both 60-second clock errors remain
below 0.25%; the exact values are recorded below. Native F3 throttle/clutch,
coast/brake/restart/steering, F1 manual gears, and the 040/MMU/32 MiB control
configuration pass. Pause retains exact pending time; tow restores the owned
patch ledger, INTENA remains unchanged, and pit/menu/session re-entry clears
the H3/H4 workspaces before the fresh epoch. Both CUSTOM1 settings pass the
controlled CUSTOM2=0 exact-state gate on all four base profiles. The inherited
signature-failure path rejects a deliberately damaged signature before its hook
is installed. The 000 and chip-only 020 payloads remain byte-identical to H3.

The following are 300 complete warp-off intervals, with census-window boundaries
excluded. All twelve comparisons pass mean and p95 no-regression. These are
fresh H4 equal-layout baselines; do not combine their raw FPS with historical
H3 measurements from a different binary layout. All seven opponents remain in
the grid/dense fixtures and their incomplete-projection counter stays zero.

| Emulator / scene | FPS control → H4 | Mean ms control → H4 | p95 ms control → H4 |
|---|---:|---:|---:|
| a1200-fast / normal | 13.312 → 15.266 | 75.120 → 65.504 | 80.128 → 80.128 |
| a1200-fast / grid | 12.978 → 14.582 | 77.056 → 68.576 | 80.128 → 80.128 |
| a1200-fast / dense | 8.315 → 8.883 | 120.258 → 112.579 | 120.191 → 120.191 |
| 030-50 / normal | 16.640 → 17.057 | 60.096 → 58.627 | 60.096 → 60.096 |
| 030-50 / grid | 16.640 → 16.640 | 60.096 → 60.096 | 60.096 → 60.096 |
| 030-50 / dense | 9.984 → 12.480 | 100.159 → 80.128 | 100.159 → 80.128 |
| 040-40 / normal | 16.640 → 17.914 | 60.096 → 55.822 | 60.096 → 60.096 |
| 040-40 / grid | 16.640 → 16.640 | 60.096 → 60.096 | 60.096 → 60.096 |
| 040-40 / dense | 10.004 → 12.480 | 99.959 → 80.128 | 100.159 → 80.128 |
| 060-50 / normal | 16.640 → 17.619 | 60.096 → 56.757 | 60.096 → 60.096 |
| 060-50 / grid | 16.640 → 16.640 | 60.096 → 60.096 | 60.096 → 60.096 |
| 060-50 / dense | 10.004 → 12.480 | 99.959 → 80.128 | 100.159 → 80.128 |

60 simulated seconds, control: **59.995501699 s**, absolute error **0.007498%**.
60 simulated seconds, candidate: **60.015533586 s**, absolute error **0.025883%**.

The accelerated timing profiles use the calibrated observer and explicit
real-frequency cycle settings: 030/50, 040/40 and 060/50, 8 MiB Fast. The
040/060 timing runs have MMU off; the functional 040/MMU/32 MiB check is separate.
These emulator measurements do not establish physical CPU rankings or a
complete human-driven race. The normal high-end target remains two PAL fields
(~25 FPS); the table records the actual outcome, not an assumed target pass.

The independent ordinary trace/census boots have identical complete start/end
Chip/Fast snapshots, scheduler contexts, every field cycle count, DMA counts
and displayed bitplane addresses. Coverage is 99.999993%, with one boundary
cycle unrecorded out of 13,641,792. All DMA addresses stay below $200000.

The fresh post-H4 ordinary trace has 12 complete draws averaging **59.186521 ms**
in its own scene; this is H5 input, not a paired saving against the older
ordinary captures. Remaining scene/HUD costs **17.330322 ms**, road
**13.460200 ms**, optional scene **7.901218 ms**, clear **5.289644 ms** and
beam wait **3.246725 ms**. The label is **1.868465 ms**, clock **1.177270 ms**.
There are **303.58 WaitBlit calls/draw** (1,340 busy / 2,303 idle over those
12 draws), 78,396 CIA reads and **24.010989 ms/draw** inclusive waits. These wait
costs overlap the stage totals. Large caller totals are clear `$6b082` 3.037 ms,
bitmap `$24c28` 2.592 ms, road `$6ac16` 2.536 ms / `$6ac42` 2.303 ms and
bitmap `$24dc6` 2.300 ms. H5 should histogram actual primitive work and choose
bounded CPU alternatives; H1's discarded dispatch-only change stays removed.

The independently reproduced slave is 263,532 bytes, SHA256
`f4f09229e73699fe278df126cc9d3ab614df449b2a4d2e26384d16ca1911fa0f`.
CUSTOM2 remains default-off. The delivered RC2 LHA is unchanged. Human full
races and real hardware remain deferred. **H5 is next**, using the fresh post-H4
profile for primitive selection; **B8-PAL** remains separate pre-package cleanup.

Local evidence: `tmp/manifest/render-h4-validation.json`,
`render-h4-performance.json`, `render-h4-matched-profile.json`,
`render-h4-source-audit.json`, `render-h4-build-audit.json`,
`render-h4-text-model.json`, `render-h4-dma.json` and `render-h4-traces.json`.
Raw traces are compressed with verified decompressed hashes; harnesses and
fixture builds remain ignored. The earlier demo-only iteration and observer
sampling diagnostic remain separately labelled, not reused as final acceptance.

H4 implementation and findings committed as b2f828d4dd1e5063a0c0a1653da45a314ea4d6f9.

## H5 accepted: bounded CPU font glyphs (2026-10-15)

`RenderBitmap.s` replaces the native bitmap operation only for byte-aligned
8 x 8 glyphs from either live native font, with three destination planes and
48-byte destination rows in the driving pointer views. It reads each font row
once, then writes eight bytes per plane with the exact foreground/background
operation. Each selected glyph replaces three blits with 24 CPU byte writes.
Other sizes, shifts, source types, multi-plane sources and unsupported coordinates
retain the native routine. Road lines/fills and sprite colour operations remain
on the blitter. The post-H4 histogram, not processor speed alone, selected this
small class; it does not establish a general CPU/blitter crossover curve.

The already-owned driving path is separately covered by 268 full-plane/CCR
comparisons on 020, plus the actual rendering profiles.

The previous DMA is completed by native WaitBlit before reading the font or
writing destination pixels. Conditional native OwnBlitter/DisownBlitter remains.
The same KickEmu ownership implementation explicitly preserves its scratch
registers. No font/destination cache or new DMA allocation is introduced; the
CPU code is in the existing public/Fast payload. The existing hunk ledger owns
the six-byte entry patch and restores it on release. Both A500 and chip-only 020
payloads remain byte-identical to H4. The final path also clears X before the
native exit, matching the original final-plane subtraction; it never reads SR.

The equal-layout control validates the same entry signature but leaves that
entry untouched. All new hook/selection overhead is charged to the candidate.
The preset is the sole differing binary byte. An earlier dispatch-bearing
control was retained as a diagnostic, not reused as final acceptance.

Each CPU profile passes 268 directed native-versus-CPU comparisons of all 30,960
destination bytes and the complete CCR: all 64 foreground/background pairs,
both fonts and byte positions, screen edges, and 12 shifted/size fallback cases.
The independent bit-level model passes 3,072 whole-row cases. The benchmark
executes 20,000 glyph calls per arm, acquiring/releasing native ownership per
call, after two settled VBLs with warp off;
readback verifies the control's original entry and the candidate's hook.
VBL endpoint resolution is approximately 1.002 μs/glyph. These are calibrated
emulator results, not physical CPU rankings or predictions for larger bitmaps.
The actual matched driving trace selects seven clock glyphs per draw; their
CPU function mean is approximately 82 μs with ownership already held.

| Emulator | Native μs/glyph | CPU μs/glyph | Reduction |
|---|---:|---:|---:|
| a1200-fast | 159.254 | 121.193 | 23.9% |
| 030-50 | 200.319 | 47.075 | 76.5% |
| 040-40 | 173.276 | 39.062 | 77.5% |
| 060-50 | 173.276 | 39.062 | 77.5% |

The 15 complete matched draws average **55.884396 → 55.790830 ms**, a
**0.093565 ms / 0.17%** reduction. Whole-loop matched entry intervals are
**60.081409 → 60.081141 ms**.
The 16 shared interior bitplane-DMA sequences match from the first sequence
after collapsing repeated identical fields. Native projection registers, clipping,
colour planes, clear destinations and safe buffer handovers remain exact.
Beam waiting absorbs some primitive savings; the draw result is not an assumed
whole-frame speedup.

All 100 simulation updates and private fractions match exactly. Normal, grid and
dense each pass 30 complete RGB images without pixel masks or tolerance. Both
60-second elapsed tests pass the 0.25% gate. All twelve 300-interval performance
pairs below pass mean and p95 no-regression; retain their fresh equal-layout
baselines rather than summing speedups across older binary layouts. Accelerated
profiles use the calibrated real-frequency emulator settings; the functional
040/MMU/32 MiB check is separate from MMU-off timing.

| Emulator / scene | FPS control → H5 | Mean ms control → H5 | p95 ms control → H5 |
|---|---:|---:|---:|
| a1200-fast / normal | 15.297 → 15.392 | 65.371 → 64.970 | 80.128 → 80.128 |
| a1200-fast / grid | 14.304 → 14.597 | 69.911 → 68.509 | 80.128 → 80.128 |
| a1200-fast / dense | 7.131 → 7.145 | 140.223 → 139.956 | 140.223 → 140.223 |
| 030-50 / normal | 17.077 → 17.354 | 58.560 → 57.625 | 60.096 → 60.096 |
| 030-50 / grid | 16.640 → 16.640 | 60.096 → 60.096 | 60.096 → 60.096 |
| 030-50 / dense | 12.480 → 12.480 | 80.128 → 80.128 | 80.128 → 80.128 |
| 040-40 / normal | 18.000 → 18.264 | 55.555 → 54.754 | 60.096 → 60.096 |
| 040-40 / grid | 16.640 → 16.640 | 60.096 → 60.096 | 60.096 → 60.096 |
| 040-40 / dense | 12.480 → 12.480 | 80.128 → 80.128 | 80.128 → 80.128 |
| 060-50 / normal | 17.619 → 18.022 | 56.757 → 55.488 | 60.096 → 60.096 |
| 060-50 / grid | 16.640 → 16.640 | 60.096 → 60.096 | 60.096 → 60.096 |
| 060-50 / dense | 12.480 → 12.480 | 80.128 → 80.128 | 80.128 → 80.128 |

Native F3 throttle/clutch/coast/braking/restart/steering, F1 manual gears,
040/MMU/32 MiB controls, pause/tow/pit/menu/re-entry and patch restoration pass.
The new entry is verified after reload. The CPU-write audit matches every
selected write to an actual byte bus write.
Matched-scene destinations are not fetched in the same field. Three ordinary
trace fields also update a visible HUD glyph, but all affected rows and planes
have already been fetched before any update (minimum margin 21,709 Chip slots).
No selected write overlaps the affected display fetch interval. Both CUSTOM1
settings retain the controlled four-profile CUSTOM2=0 exact-state gate. A deliberately damaged
bitmap signature exits before installing its hook. The independent ordinary
trace/census audit retains exact full snapshots, contexts and DMA; all DMA
addresses stay in Chip memory.

The historical H4 dense run recorded 8.883 FPS; the fresh H5 control already
records 7.131 FPS before the H5 hook is installed. Their performance windows
start after 557 versus 695 simulation updates even though both warm up 100 draws.
All 30 shared normal/dense completed images and seven shared grid images match
at fixed updates across H4-candidate/H5-control. The live-physics performance
fixtures and binary layouts are not identical historical timing experiments;
the cause of that absolute-rate shift remains unassigned. Acceptance uses the
fresh native-entry control pair; historical raw FPS values are reported separately.
See `tmp/manifest/render-h5-historical-baseline.json`.

The fresh ordinary trace has 288.58 WaitBlit calls/draw,
24.301731 ms/draw inclusive waits, and
1.530963 ms/draw of interrupt-level instructions.
The remaining IRQ budget is not empty-queue BLIT service: INTENA bit $40 is
already clear at every captured field start and throughout all recorded CPU/
copper INTENA writes, including conflict records. The fine path therefore
already satisfies C4's interrupt-disable condition; no ownership port is needed.
IRQ ownership remains unchanged. The histogram leaves larger bitmap, road and
sprite work native; further optimization needs a new measured case rather than broader
unvalidated CPU thresholds. H1's discarded dispatch-only experiment stays absent.

The existing **B8-PAL** diagnostic COLOR00 pulse remains separate cleanup.
Exact bitplane sequences and completed RGB images do not claim identical full
transitional RGB fields while that timing-dependent pulse exists. No palette
masks or edits were used. The normal ~25 FPS target is not reached.

The independently reproduced slave is 264,520 bytes, SHA256
`57900954b6eb18f1691f3ff8f9b51bcb4beb8a6c3456b6d33f1268cc810c9316`.
CUSTOM2 stays default-off. RC2 LHA is unchanged;
no successor packaging or broad release qualification is claimed. Human full
races and real hardware remain deferred. H1–H5's implementation work is closed
(H1 discarded); B8-PAL cleanup and successor packaging remain separate work.

Local evidence: `tmp/manifest/render-h5-validation.json`, `render-h5-histogram.json`,
`render-h5-oracles.json`, `render-h5-matched-profile.json`,
`render-h5-performance.json`, source/build/model/DMA audits and compressed traces.

H5 implementation and findings committed as 25ca4b9dcfab2474750f3506bd0dc16539f9a921.
