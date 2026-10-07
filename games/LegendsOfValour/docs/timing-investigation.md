# Simulation timing investigation and implementation (2026-10-07)

Rendering patches W3–W6 keep the existing clock, movement and AI behaviour.
The separate optional CUSTOM2 bit-6 implementation is now validated and the
normal interactive trial is launched. Persistent preferences still enable only
W1–W6. Current status/evidence is summarized in `simulation-audit.md` and
profiling §8. The following sections are a chronological research log: earlier
“pending” and “unvalidated” statements describe the builds named in those
sections, not the final candidate. Animation pacing was subsequently tuned to
8 ticks and the visual divisor to 2 following the user's play feedback.

The earlier h12:14b78 movement-step reader is more specific than previously described:
it belongs to actor initialization, not a per-frame player movement update. The single
relocated caller of h12:14b64 is h12:14c56. It adds a random value in −3..1 to the current
frame-clock step, adjusts one actor type, clamps to at least one, then stores that speed
in actor fields at offsets 28 and 30. Consequently actor speed can depend on the frame
clock at creation as well as on update frequency. An elapsed-time design must distinguish
stored actor speeds from the rendering frame's compensation value.

The persistent actor table is h12:0a2f0: 56 records of 128 bytes. The code uses
A0 = h12:0de5e and signed record offset −15214, increments the offset by 128, and iterates
56 times (h12:14110 and h12:14b42). These records are distinct from the visible-object
render records currently reported by lov_state.py. The welcoming townsman is record 43; see the live pause check below.

Observed record fields (names remain provisional):

| Offset | Observed use |
|---|---|
| 0 | actor flags; bit 0 excludes a record from active updating |
| 2 / 4 | two position words updated by adding fields 30 / 32 |
| 6 | packed cell location derived from the updated position words |
| 10 / 11 | region and actor-type filters |
| 28 / 30 | initialized from randomized frame-clock-dependent speed |
| 32 | second motion component, initialized to zero |
| 34 / 35 | replacement position fractions when the countdown expires |
| 36 / 37 | byte countdown and reload value |
| 76 | word countdown decremented during an actor state |

h12:140e6 checks an enable byte and calls h12:14108. That update adds the motion
components at h12:141ae–141ba, decrements the byte countdown at h12:141c6, writes
positions/cell at h12:141f0–141f8, and separately decrements a state countdown at
h12:141a0. These operations have no local elapsed-field scaling. The renderer calls h12:140e6
unconditionally at h12:027da, once per rendered frame (subject to the update enable byte).
There is also a caller at h12:14a96, so direct calls must be audited before changing update
ownership. At h12:027c4 the renderer decrements a counter and calls h12:15b1a every
sixteen rendered frames. That periodic work also needs classification and timing mapping.
The actor-to-render-record mapping still needs runtime confirmation.

Remaining: finish the call/pause audit and compare moving-player input across render
rates. This must include actors created at different frame-clock steps. Preserve position
fractions and collision order when evaluating elapsed-field scaling or fixed simulation
ticks. The rendering cap and beam wait remain separate constraints.

## Equal-time coupling experiment

A VERIFY-only `TIMING_STUDY` build wraps the renderer at h12:027bc. Both
members of each pair install the same wrapper; CUSTOM5 bit 8 adds eight PAL
fields before drawing, only after the tape anchor. It changes no simulation
step. The normal and ordinary VERIFY builds remain byte-identical to their
pre-experiment builds when TIMING_STUDY is absent.

Four serial captures used JOY0=none, the stationary wall route and CUSTOM2=63:
`tmp/prof/timing-coupling-wall-{a500,a1200}-{normal,delayed}`. Each pair begins
with identical decoded player, actor, RNG and animation state. The initial
sample is at the tape anchor, after the VBL counter increment; the following
100 samples in these captures are at h12:06404 **before** its increment.
Their counter endpoints therefore differ by 99 fields. This sampling detail
is not a 100-field FPS measurement. Future samples use h12:0640a after the
increment, and record their actual counter interval in metadata.

| Machine | Counter interval, both runs | Actor records differing at endpoint | RNG, normal / delayed |
|---|---|---|---|
| A500 equivalent | 5559–5658 | 52 of 56 | 53934 / 14480 |
| 14 MHz 68020 with fast RAM | 4983–5082 | 52 of 56 | 32755 / 48081 |

On the 020, actor 22 starts at x=6302 and ends at x=6635 normally versus
x=6401 with delayed drawing. Actor comparisons cover the interpreted fields
in `tools/lov_timing_state.py`. The player is stationary in this route; these
pairs establish AI coupling and do not validate player movement. No FPS or
performance improvement is claimed from these state-only captures.

Reproduce with the same retained TIMING_STUDY slave in both runs, the machine
settings from profiling §7, KEEP_SLAVE=1, STATE_ONLY=1, STATE_FIELDS=100,
CUSTOM2=63 and TAPE_OPTIONS=1 / 257. Analyse a pair with
`tools/lov_timing_compare.py NORMAL_CAPTURE DELAYED_CAPTURE`.

## Broader state and call map

h12:0fc12 maps persistent actor i to render record i at h11:08c44 + 26*i.
It publishes position words divided by four and actor type plus one. The
mapping is statically established; the live encounter check below identifies
the welcoming townsman as record 43.

The main gameplay loop is h1:02496–02724. In addition to renderer-owned actor
updates, it calls these frame-driven routines:

- h12:06b54 changes an animated texture phase.
- h2:06198 advances view bobbing.
- h5:0135c combines object-list construction with projectile motion, collision,
  vertical motion and events, and advances h11:00df4/00df8 animation counters.
- h5:01a74 processes movement/turn commands. Turning adds or subtracts
  h11:06012; translation uses fixed shifted trigonometric components.
- h5:01e58 consumes accumulated mouse displacement once, but advances held
  forward movement once per call.

Player x/y words contain six fractional cell bits. Actor positions use four
times the player's units; actor fields 34/35 are replacement fractions used
when their grid-turn countdown expires. Scaling a whole frame's displacement
would change intermediate collision and countdown ordering.

The VBL also increments the active game clock h11:004d6 when actor updating is
enabled. That field-based clock must remain distinct from fixed simulation
steps and the display clock. The explicit actor-update loop h12:14a8e has no external relocated or direct
PC-relative caller found in the code-hunk scan so far. Its purpose remains
unclassified; any explicit calls must not acquire elapsed-time gating. Other renderer callers redraw outside
the main gameplay loop, so simulation ownership cannot be changed globally
without auditing those contexts.

## Approved direction; implementation in progress

Use fixed simulation ticks with an elapsed-field accumulator, retaining each
original small motion/collision step in its original order. Drawing runs once
per selected output frame; overdue simulation ticks advance without repeatedly
running wall/sprite rasterization or chunky-to-planar conversion. Existing
25 fps display pacing and beam synchronization remain in the output path.

The user selected 25 ticks/second on 2026-10-07, matching the original game at its
rendering ceiling, with canonical movement-step 10 and animation pacing 4.
The rate applies
to player movement, turning, projectiles, actor countdowns and periodic AI.
It will change gameplay speed on machines whose original rendering runs below
the selected reference. This is a separate optional patch; W1–W6 keep their bits.

The reference-rate decision is resolved. CUSTOM2 bit 6 is reserved for this
optional patch; it is disabled in local preferences until validation passes.
The initial catch-up hooks are implemented. Input history,
paused/dialog/loading clock rebasing, and long-stall handling remain open. Measure catch-up cost on the A500 and validate equal-time progression
on both CPUs, including W1 off/on, before enabling or claiming a fix.

## Pause and townsman check (2026-10-07)

The first greeting enters h12:132e6 after clearing h12:0a0c3. Its target is
h12:09714 (A0−18250), not the separate h12:09716 conversation selector.
The live value −9710 selects actor 43: (−9710 + 15214) / 128 = 43. Both
machines report position (20644,14416) at this encounter, with player position
(5216,3616). The A500 screenshot shows the townsman saying “Welcome friend”.

| Capture under tmp/prof | Counter interval | Game clock at both endpoints | Actor states across all 101 samples |
|---|---|---|---|
| timing-pause-a1200-2 | 2238–2338 | 32904 | Identical |
| timing-pause-a500 | 2723–2823 | 33244 | Identical |

The enable byte is zero throughout both 100-field intervals. The initial
sample is at h12:132e6; later samples are immediately after h12:06404 increments
the VBL counter (PC h12:0640a). The older 020 metadata erroneously calls its
initial sample the tape anchor; `pause-enter-gdb.txt` and the sampler's GDB log
establish the actual points. The observer now records the explicit initial PC.
The 020 report predates the encounter-selector correction; its retained
`conversation-enter.bin` confirms h12:09714 = −9710. No guest memory was edited.
Both captures pass all eighteen VERIFY flag-capture opcode checks (SR on
68000, CCR on 020). Both capture emulators exited; no interactive emulator ran.

The game-clock pause gate is h12:0a0c3, also published through h11:05ff8.
Observed disabling/enabling sites include h2:026c4/0282a, 04db8/04eec,
0589e/05ca2 and h12:1090a/10994, 10b8c/10bdc, 132e0/13b66,
17028/17072. The VBL at h12:0640a skips the game-clock increment when this byte
is zero. **Do not use differences of h11:004d6 as the simulation accumulator:**
h2:04ecc and 05da4 explicitly add time to that clock. Instead count unpaused
VBL intervals separately, preserving deliberate game-clock jumps without
turning them into simulation catch-up. Loading and scripted advances still
need their own audit; this evidence covers the initial greeting pause.

The main renderer also has callers h1:00690/006d6 and h9:00226 outside the
ordinary loop. h9's actor interaction loop uses actor record fields and draws
through the same renderer. Those redraws must not accidentally consume extra
world ticks when paused. The actor/world update prefix, projectile update and
input handling must keep coherent tick ownership across these contexts.

Turn step h11:06012 is set by view geometry: 15 degrees for the large view,
10 for medium/small (h1:00218, 00248, 00278). It is not a frame-clock delta.
Preserving those steps at 25 ticks/s gives a held large-view button turn of
375 degrees/s; at 12.5 ticks/s it gives 187.5 degrees/s. These are proposed
reference behaviors, not measured performance claims, and explain why the
reference-rate decision changes game feel.


The initial implementation runs the existing main loop once per tick. An
independent VBL counter advances only while the main loop is active and the
original pause gate is enabled. The main task consumes one two-field quantum
per iteration and catches up without wall/sprite rasterization or display.
Renderer calls outside the main tick publish/draw actors without advancing AI;
object-builder redraws project existing projectiles without moving them.
The original display wait and beam synchronization stay in the output path.

This implementation is not yet validated. Input history, interaction loops,
load/stall boundaries, catch-up CPU cost, equal-tick state and equal-time
progression all remain validation gates. The rate, canonical movement step
and animation pacing are adjacent constants in `whdload/simulation.s`.


## Initial 25 Hz prototype checks (not a completed fix)

`sim-proto3-wall-a500-normal` and `sim-proto3-wall-a1200-normal` retain
identical TIMING_STUDY builds, CUSTOM2=127 / CUSTOM5=1. All captures were
serial in amiga/.cap with JOY0=none. The stationary wall route now defers its
study anchor until the original pause gate is enabled, using ordinary EXIT
input if the greeting is still open. This avoids measuring a paused world.

| CPU | VBL counter interval | Completed-tick counter interval | Enabled snapshots |
|---|---|---|---|
| A500 equivalent | 5364–5464 | 1112–1162 | 101 / 101 |
| 14 MHz 020 | 5246–5346 | 1283–1333 | 101 / 101 |

Each window completed 50 simulation ticks over 100 PAL fields. This is an
initial scheduler cadence check, not an FPS measurement or proof of equal
world state. A VBL snapshot can interrupt a simulation tick, and the two CPUs
reach the anchor with different world state. Both captures pass the legal
VERIFY flag-opcode checks. Normal and VERIFY study builds assemble for 68000;
the optional timing patch remains disabled in preferences.

Retained VERIFY SHA256: `352e5fc3b207f3fe2febf75b9963edb1c64a4b04bd2e885a3efc3099e8e695ad`.

`STATE_TICKS=50 STATE_ONLY=1` additionally samples 51 consecutive main-loop
tick completions at `_sim_end_tick`, before its diagnostic counter increment.
Use `tools/lov_timing_compare.py NORMAL_CAPTURE DELAYED_CAPTURE --ticks` to
compare the same absolute tick numbers. Game-clock differences remain visible;
wall-field and scheduler bookkeeping are reported separately from world state.
The observer also retains projectile records and view-bob state. Tick and VBL
observations answer different questions and must not be substituted for one another.

Changing the reference rate requires rebuilding and revalidating the slave.
The current integer PAL-field interval directly supports rates dividing 50;
other rates would need a fractional accumulator. Movement and animation
reference constants are adjacent to the interval and must be reviewed together.


The first completed-tick drawing-delay pair is retained as
`sim-proto3-ticks-a1200-{normal,delayed}`, with the same build and startup
anchor (field 5246), CUSTOM2=127 and CUSTOM5=1/257. Tick snapshots 1284–1334
are consecutive and begin with identical decoded world state. Every snapshot
matches for decoded actors, player, RNG, periodic countdown, animation,
projectile records and view bob. The normal run spans 101 VBL fields between
these completed ticks; the delayed run spans 108. The game clock first differs
at tick 1286. Its VBL-based advancement still needs reconciliation with
clock-driven events during catch-up; this result is not full determinism proof.
The stationary route does not exercise moving input or active projectiles.
A500 drawing-delay comparison, input transitions, modal/interaction ownership,
save/load and long-stall behavior, disabled-byte checks and final performance
measurements remain outstanding. No simulation feature commit or preference
change has been made.


## Input history and combat follow-up

The A500 completed-tick delay pair `sim-proto3-ticks-a500-{normal,delayed}`
also starts identically and matches all decoded world categories except the
VBL game clock across ticks 1113–1163. Those tick intervals span 100 / 101
VBL fields. The clock first differs at tick 1130. This repeats the stationary
020 result, with the same limits on input and projectile coverage.

The next VERIFY fixture uses CUSTOM5 bit 9 to hold the normal turn button at
(143,148) for 20 fields after the active anchor, then release it. Bit 8 still
adds drawing delay. `simulation_input.s` is an unvalidated candidate that
samples pointer/buttons at the VBL tail, after native debounce or VERIFY tape
input, and selects the historical sample for each main-loop tick. Modal polls
keep their native input path. Relative mouse and keyboard handling remain open.
The prototype retains 512 field samples and aborts on an overwritten sample;
modal ownership and an appropriate long-stall policy must be completed before
shipping. This is a diagnostic bound, not an approved gameplay limitation.

The h9 combat loop already has its own four-field minimum: h9:001b2 stores
h11:0602c + 4, and h9:0059e waits until that deadline before looping. Enemy
script/countdown steps (h9:001be), attack animation and hit resolution share
this loop. Its fast-machine ceiling is therefore 12.5 Hz, independently of
the display's two-field minimum. Preserve that pacing as one combat step per
two 25 Hz ticks while separating catch-up from drawing; do not blindly apply
the main loop's one-step-per-tick policy to this context. This still needs
runtime combat coverage and implementation.


The first historical-input boot, `sim-input-history-a1200-normal`, stopped
before the anchor at the input-history guard: private fields=556, consumed=12,
completed ticks=6. The main options dialog had kept the original clock gate
open while blocking gameplay. The computer button is command 37, dispatched
through h5:01cf8 / h5:0266e to h2:04678. That no-argument routine has no gameplay
pause gate and polls native input until return. The candidate now wraps that
thunk with a private suspension depth. VBL still advances the original game
clock, but neither the simulation accumulator nor input-history sampling
advances during the options call. The original real-time dialog behavior is
retained, without replaying its elapsed time as gameplay catch-up.

`sim-input-modal-a1200-normal` passes that startup route and records exactly
ten pressed tick samples for the 20-field turn pulse (ticks 961–970). Heading
advances by ten 15-degree steps, from 180 to 330. The settled heading differs
from the old unbuffered route because historical input after the heading-wait
condition is now consumed; do not assume that this fixture still settles at
150 degrees. Comparisons must use each pair's actual identical initial state.

The original 20-field legacy-input pair did not expose a rendering-dependent
turn difference for its particular phase. The current stronger TIMING_STUDY
bit-9 fixture waits eight fields, presses for four fields, then releases.
CUSTOM5 bit 10 bypasses input buffering in that same VERIFY study build to
provide a legacy-input control; it has no effect in normal builds. Options
suspension remains active in both controls. Short-pulse comparison results
are still pending. Other modal contexts and history-overrun policy remain open.

Remaining clock work must distinguish the real-time UI clock from logical
step time. A candidate step timestamp is original game clock minus outstanding
active-field debt, sampled consistently at tick start. This preserves explicit
rest/time jumps and the original UI clock while giving overdue world updates
their appropriate time. It is not implemented or validated yet. Relevant
readers include h12:173b2/173c4/173d8 (calendar and periodic events), h5:01a1a
(projectile/action cooldown), and h1:01112/01140/025e8 (timed player state).
Do not globally stop h11:004d6: modal loops also use it for their own deadlines.


## Short-pulse input result (2026-10-07)

The identical-build VERIFY input control now exposes the bug that the longer
pulse happened not to trigger. `sim-pulse-legacy-a1200-{normal,delayed}` starts
at heading 150. A four-field press after eight idle fields turns to 180 with
normal drawing but stays at 150 with delayed drawing: the press is missed.
The first player-state difference is at tick 1093.

With historical input enabled, `sim-pulse-buffered-a1200-{normal,delayed}`
starts at heading 180 and both runs finish at 210. Exactly ticks 904 and 905
consume the pressed samples, at private fields 1806 and 1808. All 31 decoded
world snapshots across ticks 899–929 match except the original game clock.
The tick interval spans 61 / 62 VBL fields in the normal / delayed runs.
The A500 counterpart `sim-pulse-buffered-a500-{normal,delayed}` also matches
all decoded world snapshots except the original clock across ticks 1173–1203;
the tick interval spans 49 / 57 VBL fields. These are completed-tick intervals,
not fixed-wall-time or FPS measurements. Both retained buffered builds pass
the legal flag-opcode checks. The pair starts identically within each CPU;
startup world state and pose differ across CPUs and input-control variants.

These captures all use `tmp/build-simulation-input-pulse`, CUSTOM2=127,
CUSTOM5=513 / 769 for buffered normal / delayed, and 1537 / 1793 for the
020 legacy controls. They precede the relative-mouse extension below. Only
normal builds may ship; neither these controls nor the current unvalidated
simulation feature has been enabled in preferences or committed.

`simulation_mouse.s` now implements a candidate for relative motion. It
observes the original JOYDAT deltas at h12:06460, keeps separate cumulative
positions during active gameplay, and stores those in the per-field history.
Each tick consumes a difference once, even when drawing is skipped. Mode
entry still discards prior motion, and mouse-look held buttons use the same
historical sample. The sole relocated h5:01e58 caller is h1:02aaa, reached
at h1:026e4. The adapter reproduces the heading ADD and its following BGE
internally to avoid returning flags through a continuation push.

This mouse extension assembles but has not booted yet. The next retained build
is `tmp/build-simulation-mouse-probe`; its TIMING_STUDY bit 11 injects four
+5-count X increments through the game's original JOYDAT delta calculation.
Bit 9 supplies the study interval but suppresses its button pulse when bit 11
is set. A route entering mouse look before the anchor is retained as
`tmp/timing/mouse-look.txt`. Use CUSTOM5=2561 / 2817 for buffered normal / delayed,
with CUSTOM2=127; bit 10 adds the legacy control. Validate mode entry and the
actual motion samples before interpreting the heading comparison.

Remaining gates include keyboard timing, other modal/load boundaries, combat
cadence, logical timestamps for clock-driven events, history overflow/stalls,
full moving/collision/projectile cases, all views and W1 off/on on both CPUs,
disabled-hook verification and final fixed-window performance measurements.


## Relative mouse comparison and clock audit

The retained `sim-mouse-a500-{normal,delayed}` and
`sim-mouse-a1200-{normal,delayed}` captures use the same mouse-probe build
and CUSTOM2=127, CUSTOM5=2561/2817. Each pair begins with identical decoded
world state. All 31 completed-tick snapshots agree except the original live
clock: ticks 1235–1265 on A500 and 1027–1057 on 020. Heading advances
240→260 on A500 and 180→200 on 020. The cumulative mouse sample reaches
20 in both runs of each pair. Actual observation intervals span 71/74 VBL
fields on A500 and 58/62 on 020. These are completed-tick comparisons,
not equal-elapsed-time proof or performance measurements. Reverse motion,
wrap, movement buttons and mode transitions remain open.

`simulation_clock.s` is a built, not yet boot-tested candidate. Gameplay
readers subtract outstanding active-field debt from the original clock;
menus keep the live clock, and explicit time jumps remain visible. The
observer now prefers `_sim_tick_complete`, after refreshing the diagnostic
logical clock but before incrementing the completed counter. Retained older
builds still use `_sim_end_tick`. Logical-clock equality is reported as a
world category only at the new completed-tick observation point.

The relocation at h1:029ec resolves the main-loop thunk h1:029ea to
h2:0411c. Its caller consumes h11:00006, populated by the VBL upper-clock
rollover detector at h12:06430. This is gameplay work, not keyboard input:
the routine decrements timed records, clears expired entries, updates
sixteen 56-byte records and consumes random values. Its scheduling therefore
needs logical-time ownership as well as the individual clock-reader patches.
The current candidate does not yet fix this path. Also, h1:025e8 checks a
notification-expiry deadline and clears its display through h1:0117c;
classifying that deadline as player health would be incorrect.

The day-counter audit finds its initialization at h1:02434, its sole
relocated VBL increment at h12:06430, and the main consume/decrement loop
at h1:0265a–0266e. Modal loops also inspect the same counter at
h2:00796/00a54/00d7c/0109c. Consequently, a replacement must retain the
real counter for modal behavior and defer only the main-loop consumption
until the logical clock reaches each pending day. Globally delaying the
VBL producer would change the modal exit conditions.


## Initial logical-clock boot results

`sim-clock-a1200-{normal,delayed}` uses the retained
`build-simulation-clock-observer` (SHA256
`f8043e7d6dccd77aef7ef8297ba8464cd912e5126c4fb37afd6b38191047779c`).
All 31 completed-tick snapshots, ticks 1010–1040, agree in logical clock
and other decoded world categories except the original live clock. Logical
clock advances exactly two fields per tick, starting at 35201. The actual
intervals span 59/64 VBL fields. The delayed build passes the legal flag
opcode check. This remains a short mouse-motion test, not coverage of
cooldowns or calendar boundaries.

The A500 pair with that same build is **inconclusive**: normal begins at
tick 1224, heading 180, logical clock 35980; delayed begins at tick 1233,
heading 225, logical clock 35998. Anchor fields are 5477/5482. The comparison
tool correctly refuses different tick-number intervals. Slave and tape hashes
match between these captures; their startup divergence must be investigated
before using this pair as evidence. Both captures exited normally; no
emulator remains intentionally running. They have not been discarded or
presented as a passing A/B.

The subsequent `build-simulation-days` candidate adds a guarded six-byte
hook at h1:0265a. It compares the original pending-day count with the number
of day boundaries between the logical and live clocks, allowing only due
entries through the unchanged consume loop. Modal readers and the VBL
producer remain original. A coherent read retries if the live clock changes;
word arithmetic handles the upper-word wrap and SUBA preserves X. Normal
and VERIFY variants assemble, but this new day gate has not booted and
requires explicit boundary, time-jump and modal tests.


## Day-boundary fixture and bounded observation

The next VERIFY fixture introduces tape flag `D`, valid only with `A`, to
select the drawing delay at the anchor. Both controls can now use identical
CUSTOM5 startup options; the two generated tapes differ only in that final
anchor flag. This removes the startup option difference as a possible source
of the inconclusive A500 pair, but has not yet proved its cause.
CUSTOM5 bit 12 sets the original clock's low word to $fff0 at the active
anchor, leaving its day and the VBL producer intact. This is an explicit
VERIFY-only time jump; it is not part of the shipping simulation behavior.
The observer additionally records daily timers, sixteen daily records,
calendar/event state and the real pending-day count.

The first `sim-days-a500-normal` observation reached its anchor and saved
one completed tick (1232, logical clock 65513, real clock 65520, no pending
day), then stopped making tick-sample progress. Its partial raw snapshots
are retained under `partial-ticks`. The cause is not established: the time
jump can exercise hourly scripts and modal paths before the daily boundary.
Do not treat this as a passing daily-event test or launch another emulator
while the current capture/observer is live.

The subsequent `build-simulation-days-watch` adds a VERIFY-only breakpoint
point after 512 post-anchor VBL calls. The sampler now breaks on that point
or `_c2p_abort`, records the stopped registers and memory, retains partial
snapshots directly in the output directory and rejects incomplete results.
This watchdog does not change gameplay or dismiss dialogs. The comparison
tool also refuses metadata explicitly marked incomplete. This newer observer
and fixture build still require runtime validation.

Growth of the VERIFY fixture crossed the 68000's signed PC-relative reach
to the C2P scratch buffer. Its four VERIFY-only references now use a nearby
bitmap address plus the constant long offset to scratch; address-register
arithmetic preserves flags. The normal C2P implementation is unchanged.


## Day fixture: modal diagnosis and first rollover result

The unbounded observer eventually timed out. A targeted interrupt identified
h2:06388 (the original h12:05288 button thunk). The capture emulator was
then deliberately terminated by its verified .cap PID; the shell, server
and debugger exited. The first bounded-observer attempt failed to dump
because this old GDB does not accept spaces in dump filenames, even quoted.
The observer now uses temporary paths without spaces and retains their
contents in a `finally` block, including incomplete observations.

`sim-days-watch2-a500-normal` demonstrates the corrected watchdog: one tick
completed, then the 512-field breakpoint stopped in VBL and retained all
registers and memory. The main stack identifies h1:0002a → h2's message
handler → h2:05c76 → h2:0007e, the native release/press/release wait. Its
original pause gate is closed. At the stop: tick 1233 is in progress,
logical clock 65515, real clock 65561, private fields 2510, consumed 2464,
and one pending day. This is a click-to-dismiss modal, not evidence of an
endless simulation catch-up loop. The observer metadata is incomplete and
the comparison tool explicitly refuses it.

The VERIFY bit-12 fixture now sends a short native click pulse only when
the original game pause gate is closed. This dismisses the time-jump
message without changing the game pause implementation. The isolated day
pair uses CUSTOM5=4097 (tape + day fixture), with no mouse-motion pulse;
`A`/`AD` selects normal/delayed drawing. Both use the exact retained
`build-simulation-days-modal` build.

`sim-days-modal-a500-{normal,delayed}` completes 41 snapshots, ticks
1232–1272, spanning 164 VBL fields in each run. All decoded categories,
including daily records, calendar, logical/live clocks, actors and RNG,
match. Logical time increases by two fields every tick. The pending day
appears at tick 1233 while logical time is only 65515, but the daily records
change at tick 1244, logical clock 65537, when the pending count becomes
zero. This directly exercises deferral to the logical boundary and return
from the native paused message.

**This short pair does not prove drawing-delay independence:** all its
sampled ticks skip rendering, and the retained study-delay count is zero
in both runs. Longer 120-tick windows on both CPUs are the next test; their
render/delay counts must be checked before interpreting equal world state.
No performance result or simulation feature commit follows from this test.


## Extended rollover and drawing-delay comparison

`sim-days-long-{a500,a1200}-{normal,delayed}` uses 120 completed-tick
intervals and the same retained VERIFY SHA256 `aa5f0ffb6ea5d522bb4c6dd1a754cbca83fc9b8924b14393d8e76a7678c0db0b`.
All four runs complete; their observers report complete metadata. Reproduce
with the §7 CPU settings, KEEP_SLAVE=1, STATE_ONLY=1, STATE_TICKS=120,
CUSTOM2=127 and TAPE_OPTIONS=4097. Use the retained day-normal/day-delayed
tapes, differing only in the final A/AD flag. The message-dismissal clicks
operate only during the original paused state. Captures remain serial in
amiga/.cap with JOY0=none.

| CPU | Completed ticks | Actual VBL intervals, normal/delayed | Ticks selecting rendering | Executed study delays |
|---|---|---|---|---|
| A500 | 1232–1352 | 316 / 325 | 4 / 3 | 0 / 3 |
| 020 | 978–1098 | 274 / 274 | 60 / 20 | 0 / 19 |

Both pairs start with identical decoded world state. All 121 snapshots per
pair match in logical clock, player, actor records, RNG, animation, daily
records/timers and calendar/event state. The live game clock first differs
at tick 1295 on A500 and 984 on 020. The real pending-day count also differs
temporarily on 020 from tick 984; it remains a VBL/modal counter, so that is
expected before logical consumption. No gameplay-state category is excluded
to obtain these results.

A500 daily records update at tick 1244, logical time 65537. The 020 update
occurs at tick 987, logical time 65536, in both runs despite real clocks
65539/65544. The different parity comes from each CPU's initial fixture
phase; this is within-CPU equivalence, not a claim of identical startup
state across CPUs. Both delayed builds pass the legal flag-opcode checks.

These are completed-tick correctness observations, including native modal
pause/resume and actual drawing delays. Rendering selections are not FPS
measurements, and the different actual observation intervals do not prove
arbitrary equal-wall-time snapshots. Equal-horizon movement/collision/input,
keyboard, combat, remaining modal/load boundaries, long stalls, all views,
W1 off/on, disabled-byte checks and final performance measurements remain
required before the simulation patch can ship. It remains disabled in local
preferences and uncommitted.


## Held forward movement and blocked travel

A source audit corrected the mouse adapter's signed branch: the original
h5:01e6c opcode is BGE ($6c06), not BPL. The adapter now preserves that
condition, including signed overflow semantics. Earlier small positive
mouse pulses did not distinguish the two conditions. Negative/wrapping
mouse input still needs explicit runtime coverage.

`sim-forward-{a500,a1200}-{normal,delayed}` retains VERIFY SHA256
`5a2d53267de894dcd2d2aac0803af5dad7dab8530cfe520d2f8dcd70fd3d5217`. The mouse-look route holds eight fields at its A/AD anchor,
presses L for 64 fields, then releases indefinitely. Both controls use
CUSTOM5=1, CUSTOM2=127, STATE_TICKS=120 and the same slave. No study button
pulse or time jump overrides this tape. All captures complete normally.

| CPU | Tick interval | VBL intervals normal/delayed | Rendering selections | Executed drawing delays | Pressed ticks |
|---|---|---|---|---|---|
| A500 | 1232–1352 | 243 / 252 | 9 / 6 | 0 / 6 | 1240–1271 (32) |
| 020 | 1003–1123 | 239 / 240 | 77 / 21 | 0 / 20 | 1009–1040 (32) |

Within each CPU pair, all 121 decoded completed-tick world snapshots match
except the live clock (first divergence 1238 / 1005). Logical time, sampled
input, player pose, actors, RNG, animation, projectiles and calendar/daily
state agree. Both begin at player (5216,3616). A500 heading 225 ends at
(5064,3831); 020 heading 180 ends at (5216,3703). They are separate matching
pairs, not identical-heading cross-CPU tests. Travel stops while L remains
held, exercising blocked movement before release; this does not exhaust
collision geometries. Both delayed captures pass legal flag-opcode checks.
Normal and VERIFY builds assemble.

These establish held mouse-look translation, blocked travel and release
under different drawing schedules. They do not cover backward movement,
mode transitions, keyboard, combat or equal-wall-time endpoint equivalence.
Rendering selections are not FPS measurements. The simulation patch remains
uncommitted and disabled in preferences pending the remaining gates.


## Reverse-input contamination and another modal boundary

The first reverse-movement route extends the forward tape with eight released
fields, 32 fields holding L+R, then release. The main toggle at h1:02684
requires exactly button value 2, so value 3 retains mouse-look mode and uses
the reverse branch in h5:01e58.

`sim-reverse-a500-{normal,delayed}` is **not a valid identical-input pair**.
It begins with equal world state, but the delayed input history gains X=121,
Y=-65 at tick 1236 and X=128,Y=-66 one tick later. The normal run remains
at zero. This precedes forward movement and changes heading and later AI.
Both used JOY0=none and no synthetic mouse injection. The precise source
of the unexpected JOYDAT change is not established. The result is retained,
not represented as a patch failure with matching inputs or discarded silently.
The corresponding first 020 pair matches all decoded categories except the
live clock, but the fixture still requires explicit relative-input isolation.

TIMING_STUDY now supplies zero hardware X/Y counters unless its explicit
synthetic motion fixture adds X. It preserves the upper half of D0, as the
original MOVE.W did. This affects only the scripted study build: ordinary
VERIFY and normal slaves retain the real hardware read. All captures still
use JOY0=none. The retained `build-simulation-input-isolated` and
`sim-reverse-isolated-*` runs are the replacement comparison.

A separate audit identifies the blocking h2:01ca0 panel, called with one
stack argument from h2:024d0. It uses the original clock for repeat timing
and has one normal exit, h2:0222e. `simulation_modal.s` adds guarded entry
and epilogue hooks. The entry reproduces LINK and the stack-limit branch
before increasing private suspension; the epilogue decreases it and restores
the original saved registers/frame. Stack arguments remain in place, and
the original clock/input remain native. This path assembles and its install
guards are exercised by startup, but the panel itself still needs a runtime
hold/resume test longer than the history capacity. Do not count it as validated.


## Isolated reverse-movement result

`sim-reverse-isolated-{a500,a1200}-{normal,delayed}` retains identical
VERIFY SHA256 `32c842e0a3570485072b360398323a0bca7799fe3dc4c131949ad7ac00d21878`. All four captures complete. Each pair begins
identically and matches all 121 decoded completed-tick world snapshots
except the live clock. Relative X/Y remains zero throughout; mouse-look
mode remains 1. Exactly 32 ticks consume L and 16 consume L+R in each run.

| CPU | Tick interval | VBL intervals normal/delayed | Rendering selections | Executed delays | Final player x,y |
|---|---|---|---|---|---|
| A500 | 1232–1352 | 244 / 242 | 8 / 5 | 0 / 5 | 5229,3639 |
| 020 | 1027–1147 | 238 / 241 | 75 / 21 | 0 / 20 | 5216,3464 |

The A500 retains heading 225 and 020 heading 180. The live clock first
differs at ticks 1238 / 1029; input, logical clock, actors, RNG, movement,
animation, projectile and calendar/daily state match. Both delayed runs
pass legal flag-opcode checks. The different VBL intervals are retained;
these are completed-tick comparisons, not FPS or arbitrary equal-wall-time
claims. This covers forward-to-reverse transitions, blocked travel and
release, but not mode toggling or negative/wrapping mouse deltas.

This retained build includes the new h2:01ca0 panel hooks. Startup passes
their signatures, but this movement route does not enter that panel. A
long hold/resume test remains necessary; the hooks are not yet validated
for shipping. No simulation feature commit or local preference change has
been made.


## Native panel long-hold result

`sim-panel-{a500,a1200}` uses `build-simulation-panel-probe`, CUSTOM2=127,
CUSTOM5=8193 and the stationary wall route. Both retain 41 completed-tick
snapshots with complete metadata. The VERIFY fixture enters h2:01ca0 with
record index zero, holds it for at least 600 real VBL fields, and dismisses
it through its native button path. Entry/exit assertions require unchanged
private fields and consumed time, at least 600 fields of native VBL and
calendar time, exactly one successful return, and zero suspension depth.
Continued tick sampling passes those assertions on both CPUs.

| CPU | Completed tick interval | Total VBL intervals | Interval spanning panel | Private-field increase across that interval |
|---|---|---|---|---|
| A500 | 1177–1217 | 684 | 602 | 1 |
| 020 | 948–988 | 679 | 601 | 1 |

Consumed time advances by two fields across the panel interval, and suspension
is zero at every retained tick. Thus the hold does not accumulate 600 fields
of simulation debt or overflow the input history. The native calendar and
logical clock still advance across this particular panel; this test does not
claim that calendar time freezes with actor simulation. The fixture directly
calls the native panel, so it does not validate the preceding item-selection
route. Before/after fixture arrays were not retained separately; assertion
success and the surrounding tick snapshots are the retained runtime evidence.
The normal slave is byte-identical with and without these VERIFY probes.

Keyboard, combat, other modal/load boundaries and equal elapsed-time world
comparison remain open. This is a correctness check, not a performance result.


## Keyboard ownership audit

The current mouse history does not timestamp console characters. h1:01e56
submits CMD_READ for one byte at h11:05fa4 through the request at h11:05f5c.
Both h1:01e86 (blocking) and h1:01eb6 (nonblocking) retrieve that request from
h11:05f60, read the byte and reissue the request. Main-loop callers are
h1:0258a and the space-key drain at h1:025ae. h1:01ee0 creates/opens these
resources and h1:01f30 aborts/closes/deletes them. Any replacement collector
must own this complete lifetime, including the blocking readers outside play.

The installed NDK `Autodocs/console.doc` CMD_READ specifies a buffered ANSI
byte stream with keymap conversion. Merely observing one completed request
at VBL does not recover timestamps of characters still inside that stream.
`exec.doc` GetMsg is nonblocking and SendIO starts asynchronous device work,
but those descriptions do not establish that console resubmission is safe
inside the game's VBL interrupt. Do not infer that safety from nonblocking IO.

Kick13's `_cb_keyboard` callback sees hardware raw key bytes before the normal
keyboard path. It is not an equivalent source of console characters: generated
repeat, keymap conversion and multi-byte sequences still require handling.
The input.device handler interface and console RawKeyConvert are documented
alternatives, but a new raw-key path must preserve those semantics and must
not also deliver the same characters through the existing console queue.

A task-context collector with explicit ownership of the original request and
both reader adapters is the next implementation candidate. It must preserve
native dialog blocking, input ordering, cancellation and close, and timestamp
completion independently of rendering. This is an audited design direction,
not an implemented or validated keyboard fix.


## Negative relative-motion result

`sim-negative-{a500,a1200}-{normal,delayed}` uses the identical retained
`build-simulation-negative` study slave, CUSTOM2=127, CUSTOM5=18945 and
`tmp/timing/mouse-negative-{normal,delayed}.txt`. A/AD selects drawing delay
with identical options and startup input. Bit 14 extends the bit-11 mouse
fixture to 48 negative five-count hardware increments; bit 9 advances its
field schedule. It drives the original hardware-delta calculation and tests
negative cumulative history across the 16-bit boundary.

All four captures complete. Every decoded category at all 81 completed-tick
samples matches within each pair except the native calendar clock. Both
delayed captures pass legal flag-opcode checks. The normal build remains
byte-identical to `build-simulation-panel-probe-normal`.

| CPU | Ticks | VBL intervals normal/delayed | Rendering selections normal/delayed | Heading |
|---|---|---|---|---|
| A500 | 1229–1309 | 156 / 163 | 5 / 4 | 240 → 0 |
| 020 | 1003–1083 | 158 / 167 | 50 / 15 | 180 → 300 |

The 020 crosses heading 5 → 355 at tick 1026. A500 reaches zero exactly,
so this route does not prove a negative heading crossing on that CPU.
Both consume cumulative X=-240 (word 65296), with equal input samples,
logical clocks, player state, actors, RNG and animation. Native clock first
differs at ticks 1244 / 1005. Rendering selections are not FPS, nor a retained
count of executed delay calls. The observer now retains `final-code.bin` at
successful completion as well as stopped state on failure, so subsequent
fixtures can inspect their final counters instead of inferring them from
control-flow assertions. The four runs above precede that observer addition.
Mode transitions, active combat/projectiles, keyboard and equal elapsed-time
endpoint verification remain open.


## Interactive feedback: animation and turning

The user tested the retained pre-keyboard normal timing prototype on the
28 MHz 68020 play-test setup. World translation looks reasonable, but fire
and character walking animations look too fast. Turning is too coarse.
Keep the live play-test session untouched while implementing corrections.
This feedback overrides treating unchanged per-tick animation as acceptable
merely because it matches across rendering rates.

Source checks distinguish the paths:

- h12:06b54 advances the three-frame animated texture every main tick. At
  25 ticks/s this changes frames 25 times/s; it needs its own animation cadence.
- h12:14224–14234 adds actor byte 42 to fractional animation byte 43 and,
  on carry, increments the four-frame animation index at byte 12. This is
  separate from position updates at h12:141ae–141f8. Slow visual animation
  without reducing world movement or AI updates.
- h5:01934–1950 has another shared animation counter, presently normalized
  to pacing four. Audit its consumers separately rather than assuming that
  this constant controls the texture and actor paths above.
- h1 view setup writes turn increments of 15 degrees for large, 10 for
  medium/small; h5:01b94 and 01bca consume these increments. The 25 Hz
  loop therefore permits very fast held turns as well as coarse taps.
- h1 sets heading quantization h11:06010 to five degrees for these views.
  Relative mouse input explicitly divides then multiplies by it at
  h5:01e8e–1e96 before publishing h11:08c22. Renderer h12:028f8 also indexes
  angle-dependent data through a division. Sub-five-degree display precision
  requires auditing/rebuilding the associated tables; it is not established
  by the raw heading accepting integer degrees.

Next targeted correction: separate visual-animation cadence from the 25 Hz
world step, and use five-degree button turns as the first control improvement
within existing angle granularity. Start evaluation at half the current
texture/actor animation cadence; retain independently adjustable constants.
Neither adjustment has been implemented or measured yet. Keyboard-collector
work remains an unvalidated worktree prototype and is not in the live game.


## Play-test adjustment implementation

`simulation_feel.s` adds guarded bit-6 patches for five-degree button turning
at all larger view setups, and an independent two-tick visual divider.
The texture thunk advances on alternate ticks. The actor adapter gates only
its fractional animation add/frame-index increment; movement, AI countdowns
and sprite selection still execute every world tick. Shared object-animation
pacing is eight rather than four. These knobs are adjacent to the simulation
constants; world cadence remains 25 ticks/s and movement step remains ten.

The user reported the live prototype exiting with `input history exceeded`.
The exact interaction that caused the backlog has not been identified. The
selector now recovers on a missing history tag: with interrupts briefly
excluded it samples current input, resynchronizes consumed time, discards
accumulated relative motion, and increments a recovery counter. This is an
explicit loss-of-history policy: unrecoverable elapsed simulation time is
abandoned, not replayed. It prevents the diagnostic abort but does not prove
all modal boundaries correct or claim time equivalence through that stall.
The VERIFY bit-16 study deliberately holds the main task for 600 fields to
exercise recovery. Its result is recorded separately after completion.

The unfinished task-based keyboard collector is now compiled only with
SIM_KEYBOARD_EXPERIMENT. It is excluded from this play-test build. Source
remains uncommitted and the full timing goal remains incomplete.


`sim-feel-stall-a1200` completed 41 tick snapshots using the retained
`build-simulation-feel`, CUSTOM2=127 and CUSTOM5=65537. The first interval
spans 600 VBL fields; consumed time resynchronizes from 2512 to 3117.
The retained final slave state has stalled=1 and input_recoveries=1. Use
slave base from anchor.txt when reading these symbols (regions() requires
the matching SLAVE environment to identify the current slave correctly).
The subsequent 40-tick window completes, totaling 682 VBL fields including
the deliberate stall. Turn step is five, object pacing eight and movement
ten. Actor 18 animation-fraction deltas alternate 70,0 throughout the sampled
sequence, confirming half-cadence animation with the world loop still active.
This is a targeted recovery/feel check, not full timing acceptance or FPS data.


## Animation-delay regression found after user feedback

The previous play-test adjustment did not fix the shared sprite animation.
The adapter for h5:01934 incremented the counter but returned at h5:01940,
skipping CMP.W at 0193c and entering BLT with flags overwritten by pushing
its continuation address. Consequently the phase advanced every tick,
regardless of the pacing word. The earlier check of pacing=8 and an unrelated
actor fraction was insufficient evidence of displayed sprite animation speed.

`sim-feel-stall-a1200` contains 40 phase advances in 40 ticks, counter always
zero, despite pacing=8. `tools/lov_animation_check.py` rejects it at tick 1258.
The corrected adapter performs the comparison and signed branch internally,
then resumes at 01942 for an advance or 01954 to hold. New signature guards
cover the skipped comparison and branch too. `sim-animation-fix-a1200`
passes all 40 consecutive transitions with five advances, a genuine eight-tick
hold. h5:02264 reads this phase for the ordinary actor sprite-image selection
and h5:022fc passes the selected frame to the drawing routine.

A further renderer audit found random image selection at h5:002dc/002fc and
an associated random visual choice at 00310. All route through h5:02698.
The new adapter intercepts only their three return addresses and keeps the
original random routine for all other callers. A private cosmetic generator
updates their choices every four simulation ticks; rendering itself neither
advances that generator nor consumes the gameplay random sequence. This
removes a separate per-render animation source. It changes cosmetic random
sequencing deliberately; it is not pixel-equivalent to the original sequence.
Runtime draw-call coverage is recorded separately below when available.

Finer-than-five-degree turning is deferred until these animation corrections
are checked, as requested by the user.


`sim-animation-fire-a1200` also passes 40 ticks/five sprite-phase advances
and records zero history recoveries. However, `_sim_fire_draw_calls` is zero:
the spin route does not exercise the newly intercepted scenery random choices.
Do not count that hook as runtime verified or identify those choices as the
user's particular fire without locating the scene. The user was asked where
the fire is. The next interactive session deliberately uses the verified
`build-simulation-animation-fix-normal`, which fixes the skipped sprite delay
but predates the unexercised cosmetic-random hook.


## Native save/load: queued buttons reopen options

After the standalone one-degree patch passed native save/load on both CPUs,
the identical route with CUSTOM2=255 stalled in the options panel. The
`sim-load-observer-a1200` negative control adds VERIFY-only entry/return counters.
It stops with four entries but three returns; the last return is at consumed
field 2152 and the unwanted next entry at 2154, exactly one simulation tick
later. The private clock is suspended, fields=2158, consumed=2154, and no
history recovery occurred. This is stale historical button input reopening a
panel which has already consumed the live release, not evidence of lost saves.
The observer alone leaves the normal slave SHA256 unchanged at
`8ea3d1773ca76844c98a39b19ec4384f86fdefd712b927df2487f67e4cf9cd54`.

The prototype now records the private-field boundary before leaving the
outermost options/item-panel suspension. Historical samples through that
boundary retain their time, pointer and cumulative relative motion, but their
buttons are cleared because those transitions have already been handled by
the live UI. Future samples retain ordinary input semantics. The change does
not advance `_sim_consumed`, clear simulation debt or invoke history recovery.
Keyboard ownership remains a separate open item.

`sim-load-fixed-a1200` completes three genuine tape checkpoints with headings
41° before save, 172° before load, then 41° after load. Its three option entries
have three matching returns, and four stale button samples were suppressed.
`tools/lov_load_check.py` verifies checkpoint PCs, exact heading restoration,
balanced modal entries, zero recoveries and forty consecutive resumed ticks
advancing consumed time by exactly two fields each. The shared-animation
checker passes forty ticks/five phase advances. A500 and drawing-delay
comparisons follow separately; this result alone is not full timing acceptance.
The active interactive build has not been replaced or restarted.


`sim-load-fixed-a500` also passes: headings 41° → 172° → 41°, exactly three
balanced option visits, seven suppressed UI-consumed button samples, forty
consecutive two-field ticks, no input recovery, and five shared-animation phase
advances. Thus the modal fix works on both CPUs. The subsequent TIMING_STUDY
route needed explicit EXIT pulses after loading: its first attempt reached
three balanced option returns but waited before the final gameplay anchor,
with a restored NPC conversation. That rejected window is not comparison data.


The corrected `sim-load-pair2-a1200-{normal,delayed}` pair uses identical study
slave SHA256 `a3e311aa32334834a4d003a787d9d6086edc3d33203a6ca654b5bf6a05a1168a`,
CUSTOM2=255/CUSTOM5=1, with A versus AD selecting delay only at the final
post-load anchor. Across ticks 1530–1650, all 121 player/actor/RNG/animation
snapshots match; only the independent live game clock differs. Logical clock
values match at every sample, from 36691 to 36931, as do consumed-field
endpoints. Final RNG is 45786. The normal/delayed runs execute 0/20 actual
delay calls, select rendering on 79/21 sampled ticks, and span 238/239 VBL
intervals. Neither run recovers input history. Both animation checks pass
120 ticks/fifteen phase advances. Rendering selections are not FPS and this
completed-tick comparison does not assert identical wall-time display latency.


`sim-load-pair3-a500-{normal,delayed}` completes the A500 comparison with the
same study slave. CUSTOM5=3 enables the existing wait-rescue pulses and conversion
twin in both controls; this additional drawing work is explicit. The preceding
short EXIT pulses missed the A500's greeting, leaving the private clock paused
inside a tick with three balanced options visits; that window was rejected.
The rescued pair covers ticks 1844–1964. All 121 decoded categories except the
native live clock match, including all 56 actors, player, RNG and animation.
Logical clocks match at every sample (38289–38529), as do consumed-field
endpoints. There are zero recoveries, 0/2 actual drawing-delay calls, and 4/3
render-selected ticks. The observed VBL spans are 230/214 because the endpoints
have different outstanding drawing debt; these are not FPS measurements.
Both animation regressions pass 120 ticks/fifteen phase advances.

The native round-trip regression is now exposed through tracked tools:
ordinary VERIFY plus VERIFY_WAIT_RESCUE, CUSTOM2=255, CUSTOM5=1,
`TAPE_CHECKPOINTS="before-save before-load" STATE_TICKS=40 STATE_ONLY=1`, and
`tools/fixed_window.sh OUT tools/tapes/timing-load.txt` under each §7 CPU setup.
Then run `tools/lov_load_check.py OUT --base BASE` and
`tools/lov_animation_check.py OUT`. Intermediate anchors must be real tape
stops; the harness rejects combining checkpoints with TIMING_STUDY or the
profiler handshake. The broader timing goal remains incomplete.


`sim-load-harness-a1200` verifies the tracked checkpoint harness against the
same retained fixed build: 41° → 172° → 41°, three balanced option visits,
four suppressed samples, forty exact two-field resumed ticks and five sprite
phase advances. Normal and VERIFY builds pass the 68000/PIC assembler after
the modal fix. These changes remain in the timing worktree pending the broader
keyboard/combat/mode-boundary validation and final performance matrix.

## Native console collection and queue backpressure

The guarded `SIM_KEYBOARD_EXPERIMENT` collector now has native input-device
coverage. VERIFY's `timing_keys.s` owns a separate task which writes timestamped
raw-key InputEvents using Kickstart 1.3 `IND_WRITEEVENT`; VBL only signals the
task. Events pass through the real keymap/console conversion and outstanding
CMD_READ, rather than being inserted directly in the collector ring. The
fixture's own task/stack allocation is retained until teardown of the guest;
no fixture is present in normal builds.

`sim-key-events-{a1200,a500}-{normal,delayed}` delivers `aBcc` exactly once,
including shifted input and an explicitly repeat-qualified event. This does
not measure the hardware held-key repeat cadence. Each pair covers 81 samples
(80 completed-tick intervals); player, all 56 actors, RNG, animation and logical
clock agree throughout. The independent live clock differs. Actual drawing-delay
calls are 0/14 on 020 and 0/3 on A500. These letters are ignored by the gameplay
command dispatcher, so this is input transport coverage, not combat coverage.

`sim-key-ansi-{a1200,a500}-{normal,delayed}` adds cursor up, converted natively to
CSI (`$9b`) followed by `A`. Both bytes are delivered exactly once, on successive
polling ticks, with identical arrival and consumption fields within each pair.
The 020 pair covers ticks 1024–1104 and A500 1266–1346. All decoded world
categories except the independent live clock match; logical clocks also match
at every sample. Actual drawing-delay calls are again 0/14 and 0/3. Differing
VBL spans (160/165 and 151/160) reflect outstanding rendering debt, not FPS.

`sim-key-blocking-{a1200,a500}-{normal,delayed}` calls the native blocking-read
entry before the first event. The adapter demonstrably waits, wakes, returns
`a`, then ordinary historical polls receive `Bcc`. All four records agree
within each CPU pair. A blocking/UI read intentionally has no historical tick
cutoff. This tests the adapter contract; a real text-entry dialog remains a
separate route to cover.

`sim-key-exit-{a1200,a500}` requests exit through the game's native exit flag.
`lov_keyboard_exit.py` observes the pending read cancelled, worker removed,
owned memory freed and original message-port owner restored. It then stops
at h1:02740 after the original console close returns. Both CPUs pass.

Reproduce with a retained VERIFY build using
`VASMFLAGS='-DTIMING_STUDY=1 -DSIM_KEYBOARD_EXPERIMENT=1'`, CUSTOM2=127,
STATE_ONLY=1, STATE_TICKS=80 and the normal/AD delayed stationary tapes retained
with the captures. CUSTOM5 is 16777217 for ordinary events, 150994945 for ANSI,
and 50331649 for the blocking test. `lov_keyboard_check.py` checks delivery;
use `--ansi` or `--blocking` and `--compare OTHER` as appropriate. Native exit
uses CUSTOM5=83886081 and KEYBOARD_EXIT=1 instead of STATE_TICKS.
All captures are serial, JOY0=none, in amiga/.cap, with §7 machine settings.

The collector previously aborted when its 511-byte usable ring filled. It now
retains the completed byte and its arrival field, waits for the consumer to
free space, and only then submits another console read. A consumer dequeue
signals the worker; shutdown also wakes it. This avoids dropping a completed
byte or converting a temporary backlog into a fatal error. It cannot promise
unlimited input storage: further bytes remain subject to the native console's
own buffering limits. A VERIFY-only queue-size override exercises this path
with a two-slot ring (one usable entry); normal builds always use 512 slots.

`sim-key-pressure-{a1200,a500}` both pass with two slots, CUSTOM5=150994945,
and the delayed tape. The identical retained slave SHA256 is
`7ed31c115a491a213d8af5150f4a9de2520bac6aaeec941f8148245efafec49d`.
The worker enters its full-queue wait three times on 020 and five on A500,
then resumes and delivers all six bytes (`aBcc`, CSI, `A`) exactly once with
no collector error. Head and tail wrap correctly and agree at the end; full
is cleared and a new console read is pending. Both captures pass eighty
ticks/ten sprite-phase advances. Reproduce with the same build flags plus
`-DSIM_KEYS_SLOTS=2`, and check using
`lov_keyboard_check.py OUT --base BASE --ansi --slots 2 --require-full`.
The 020 arrival fields remain intact even while a completed byte waits for
space. Some A500 bytes arrive at the collector later because further reads
wait behind a full ring; this is expected backpressure, not a claim of unlimited
historical input equivalence. Normal-size builds also assemble with 68000/PIC
checks. The collector remains explicitly experimental pending remaining UI
and lifecycle regression coverage; the user's interactive slave is unchanged.

## Combat scheduler audit and native observer

The main-loop scheduler does not yet make combat frame independent. The sole
relocated entry into h9:000e6 is h2:0634c, called by the wrapper h2:0506a.
Its native caller h12:10b8c clears the world-clock gate at h12:0a0c3, selects
an existing actor through h12:09716, calls the wrapper, and reopens the gate
at h12:10bdc. Combat is therefore a separately advancing mode while ordinary
world simulation is paused. Its clock must use elapsed fields independently
of `_sim_fields`, which intentionally stops at that gate.

Inside combat, h9:001b2 recomputes a deadline as current field + 4 on every
iteration. h9:0059e waits for that deadline, then polls for the space-key escape.
The next step starts at 001b2. Rendering longer than four fields consequently
slows enemy script/countdown and attack progression; the original deadline
cannot retain overdue combat time. Enemy countdown/frame are D6/D7, player
attack countdown is D5, actor health is byte 111 of A3. The drawing paths
include h9:00642 (world renderer), 0062a (sprite drawing), 005fa (enemy frame),
00000 (attack overlay) and 0064e (display). Hit resolution and RNG are interleaved
with these, so skipping the whole body would also skip combat logic.

Combat input also needs its own historical interval. h9:00404 reads live pointer
state; h6:007da consumes h11:0603a button state. h9:00618 polls the console, a
caller not covered by the existing main-loop keyboard historical cutoff.
The ordinary pointer ring stops sampling while the world gate is clear. A
combat adapter therefore needs explicit mode ownership and elapsed-field
input sampling; merely reusing the paused world tick would be incorrect.

The VERIFY-only bit-28 `timing_combat.s` observer selects existing actor 43,
retains its native health/script, invokes h12:10b8c including the pause envelope,
and records up to 64 original combat iterations. After 32 polls it supplies the
ordinary space-key escape to the native combat poll. It does not patch combat
pacing. `lov_combat_report.py` requires a completed capture and an actual return,
then reports field intervals, private/world clocks, attack/script countdowns
and enemy health. This is controlled native-path coverage, not proof of normal
UI selection or frame-independent combat.

The earlier `sim-combat-observer-a1200-*` captures called h2:0506a directly and
omitted the outer pause envelope. They are rejected as representative timing
measurements: their world gate remains enabled. The corrected captures use
`sim-combat-envelope-*`, a separately retained build. Build with VERIFY and
TIMING_STUDY, CUSTOM2=127, CUSTOM5=268435457, STATE_ONLY=1, STATE_TICKS=10,
and the stationary normal/AD tapes retained with the captures. Keyboard's
experimental collector is excluded from this baseline.

Additional VERIFY record buffers now follow the large scratch areas, with
explicit position-independent address construction, to keep executable code
within the 68000 PC-relative displacement limit. Both combat-only and combined
keyboard/combat study builds assemble with 68000/PIC checks. Normal builds
exclude the observer and its storage.

The corrected 020 normal capture completes 27 combat iterations, with enemy
health falling from 16 to zero. The first-to-last iteration span is 105 PAL
fields: one five-field interval and twenty-five four-field intervals. Every
record has world_enabled=0; the saved game clock, private fields and consumed
fields are each constant throughout combat. No input-history recovery occurs.
This confirms active attack/death progression inside the native pause envelope;
the 32-poll escape limit is not reached in this run. The delayed and A500
comparisons are being retained separately and must be checked before deriving
any cross-rate conclusion.

The corrected 020 delayed capture also completes 27 iterations. Every recorded
logical combat value matches its normal counterpart, but the first-to-last
span grows from 105 to 290 fields. There are 28 drawing-delay calls across the
whole retained observation (including surrounding main-loop work). This is
positive evidence that combat still slows with drawing despite the main-world
fixed-step patch. It is not a completed combat fix.

`sim-combat-envelope-a500-normal` reaches the existing 512-field study watchdog
inside combat: 28 iterations observed, requested=1, returned=0. Its incomplete
main-tick capture is rejected by the reporter. Bit 28 now shares the existing
2048-field long observation limit, and the new `sim-combat-long-a500-*` pair
uses a separately retained build. The timeout did not indicate a game crash
or permission problem; the native A500 drawing cost simply exceeded the short
fixture budget. The rerun remains pending until its native return is observed.

Both corrected A500 baseline captures now complete 32 iterations and return
normally. First-to-last spans are 544/777 fields, with identical recorded
logical combat states under normal/delayed drawing. World and private clocks
remain frozen; neither run invokes input-history recovery.

### Combat catch-up candidate

`SIM_COMBAT_EXPERIMENT` adds a candidate under CUSTOM2 bit 6. It maintains a
separate elapsed-field combat deadline, advancing by four fields (two world
ticks) each iteration rather than resetting from the current field. Native
attack/script, RNG, damage and sound code still runs in order. Only h9-local
world/sprite/enemy-frame/display calls and attack-overlay drawing are omitted
on overdue iterations. The native rendering cap and beam wait remain in the
original display target. Combat exit clears ownership at the common epilogue.
The clock starts after combat setup and resource loading, matching the original
first deadline location rather than accumulating setup IO time.

The clock-only candidate `sim-combat-clock-{a1200,a500}-{normal,delayed}` passes
32 native combat iterations per capture. All recorded logical combat states
match within each CPU pair. First-to-last spans are 124/133 fields on 020 and
134/139 on A500; catch-up counts are 0/20 and 25/27 respectively. Ownership is
cleared at return, and no world input-history recovery occurs. These endpoint
spans retain outstanding drawing latency and do not claim identical state at
every wall-clock instant, equal UI input behavior, or FPS. The corresponding
original-deadline baselines above demonstrate the regression being addressed.

The next candidate adds a separate 512-field pointer/button history which stays
active during the native world pause. Each combat tick selects its own elapsed
field, and h9's manual attack hit-test receives that position/button state.
The Intuition window itself is not overwritten by the shipping adapter. Long
history loss is an explicit counted rebase, matching the world-input policy;
normal comparisons must require zero recoveries. Combat keyboard escape still
needs integration with the collector's separate time domain.

VERIFY bit 29 temporarily selects manual combat (saving/restoring h11:060be)
and presses attack button 26 at (174,150) for four fields every 32 fields,
starting eight fields after the first combat iteration. It changes neither
health nor script data. Additional records retain every logical combat field,
deadline and selected input. `lov_combat_report.py --scheduled` requires native
return, ownership release, zero recoveries, four-field increments and exact
input timestamp selection. The `sim-combat-manual-*` captures use CUSTOM5=
805306369 with both study/candidate build flags, otherwise the observer commands
above. Their results remain pending until the complete paired runs are checked.

The four `sim-combat-manual-{a1200,a500}-{normal,delayed}` captures now pass
`--scheduled --manual`. Every pair has identical selected input records and
logical combat observations. All 32 logical deadlines advance by exactly four
fields, each input tag matches its combat tick, ownership is released, and no
combat history recovery occurs. Four-field presses land at the intended logical
fields and native attacks cause damage: enemy health 16→0 on 020 and 16→12 on
A500. Different boot/initial RNG state means the two CPUs are not asserted to
have identical outcomes to each other. Normal/delayed first-to-last field spans
are 124/126 (020) and 130/142 (A500), including outstanding drawing latency.
All four use retained slave SHA256 `7a38b6d92df464827010d26625fbbf4d1b89cfdaabffe0599dd3bd5a3e19eac5`.

Normal combat-only and combined combat/keyboard candidates assemble under
68000/PIC checks without VERIFY instruments. The combat collector time-domain
integration is still pending, so the combined build alone is not runtime proof.
The experimental flags remain explicit; no user's running slave or preferences
were replaced. Pending work includes combat keyboard escape, mode-exit input
ownership, active projectiles, wider pause/mode coverage, the final disabled-byte
and display-cap/beam-wait checks, both-CPU performance measurements and a verified
source commit. These results do not close the full simulation timing goal.

### Combat console time domain and return to world input

The collector now tags each completed byte with its clock domain. World keys
retain private active-field timestamps. During combat, arrival uses elapsed VBL
fields and h9:005ac polling uses the current combat deadline, preserving the
native end-of-step poll order. Older bytes queued before a mode transition stay
in FIFO order. Blocking/UI readers still have no historical cutoff. A byte held
by queue backpressure retains both its original timestamp and domain.

Combat's common epilogue also marks the frozen world-field boundary as already
handled by the UI. Resumed historical world samples through that boundary have
buttons suppressed, retaining their timestamps and motion. This reuses the
save/load modal policy without dropping queued simulation ticks.

VERIFY bit 30 sends one space down/up through input.device, 24/26 fields after
combat begins. The native console maps and queues it; the bit-28 fixture's
synthetic 32-step escape is disabled. All four `sim-combat-key-{a1200,a500}-
{normal,delayed}` captures pass `lov_combat_report.py --scheduled --keyboard-exit`.
Combat ends after exactly seven iterations in every run. Within each CPU pair,
all scheduled pointer/button inputs, logical combat states, key arrival times
and key consumption deadlines are identical. The 020 arrival/cutoff fields are
4976/4979; A500 5393/5396. Each key is consumed once at its first eligible deadline,
with the collector still live and a console read pending after return. Thirty
resumed-world observations pass: no suspension or history recovery and exact
two-field consumed-time increments. This is one combat/keyboard transition;
it does not establish every text-entry UI or repeated mode transition.

The identical retained slave SHA256 is `442eb82f7a83b41327b58818739035ca82c6ccf586faaeb440169bae0fad1c27`.
Reproduce with both SIM_COMBAT_EXPERIMENT and SIM_KEYBOARD_EXPERIMENT plus
TIMING_STUDY, CUSTOM2=127, CUSTOM5=1895825409, STATE_TICKS=30, STATE_ONLY=1,
and the normal/AD tapes retained in each capture. The current combined normal
build also assembles under 68000/PIC checks. VERIFY-only loader references use
explicit position-independent address construction where the growing study
code exceeds the 16-bit displacement to resload; normal code is unaffected.
The user's interactive slave and preferences remain unchanged.

### Active projectile integration

VERIFY-only TIMING_PROJECTILE calls the native h5:019aa launch routine with
its type-130 selector once after the anchor. The native allocator, initial
position, horizontal velocity and region setup execute unchanged. This is a
projectile-physics test, not a spell-menu or resource-cost test; it does not
write fabricated projectile records into game memory.

All four `sim-projectile-{a1200,a500}-{normal,delayed}` captures cover 81
completed-tick snapshots. The native launch uses previously empty slot 40.
It remains active for 42 snapshots, moving at velocity (-16,0) until the native
wall probe shortens its final approach. Sample 43 records collision response:
velocity reverses, height becomes zero and the slot type is cleared. Every
logical world snapshot (all actors, projectile slots, player, RNG, input,
animation and logical clock) matches within each normal/delayed CPU pair.
Neither pair recovers input history. Both normal captures also pass eighty
ticks/ten shared-animation phase advances.

Actual drawing-delay counts for 020 normal/delayed and A500 normal/delayed are
[0, 14, 0, 3], respectively. Identical retained slave SHA256:
`966fb5ad83544c0f7bbadac8c8814b48119c8feee70684c57d7bd240eaa1da8f`.
Build VERIFY with TIMING_STUDY, TIMING_PROJECTILE, SIM_COMBAT_EXPERIMENT and
SIM_KEYBOARD_EXPERIMENT; use CUSTOM2=127, CUSTOM5=1, STATE_ONLY=1,
STATE_TICKS=80, the retained normal/AD stationary tapes and §7 CPU settings.
`lov_projectile_check.py NORMAL --compare DELAYED` requires a real moving
launch, observed collision/despawn, zero recovery and complete logical-state
equality. Game-derived artifacts remain under ignored tmp. This covers a
horizontal spell projectile against a wall; thrown-item vertical motion and
other hit targets remain separate coverage limits.

### Vertical throw and display-code invariants

`sim-throw-{a1200,a500}-{normal,delayed}` adds TIMING_THROW to the projectile
fixture. It temporarily selects native item 55, calls h5:0195c and restores the
previous equipped item. This controlled physics fixture does not claim normal
inventory acquisition or UI selection. The native throw routine allocates and
initializes the projectile; no projectile positions or velocities are fabricated.
All four retained slaves have SHA256 `8df2e5b34babe7e2bb069c21ed664fb236c00d72e0838b7a634efb037d89cc24`.

Each pair passes 51 completed-tick snapshots with identical logical world state.
The thrown item rises through heights 29,33,36,38,39, then falls and lands at
sample 14. Horizontal and vertical velocities become zero and the item stays
stationary for the remainder. `lov_projectile_check.py --thrown --compare OTHER`
requires the upward arc, observed landing, stable rest and exact logical-state
comparison. Capture settings match the horizontal fixture except STATE_TICKS=50.

`check_disabled.py --display-timing` now compares original relocated instructions
at h12:05e2a–05e79 (frame cap), h12:05ea6–05eb1 (display-clock call/dispatch),
and h12:063ce–063ef (beam wait). Both normal projectile captures pass with
CUSTOM2=127, including all seven disabled one-degree hook ranges. This proves
those instruction ranges remain original; it is not a high-speed tearing or
frame-rate measurement. A final runtime performance matrix is still required.

The normal build now includes keyboard and combat components behind runtime
CUSTOM2 bit 6. Historical experiment macro names are retained for reproducible
old commands, but they default to enabled compilation. With bit 6 off their
installers perform no writes and create no tasks or allocations. The default
normal binary compares byte-identical to the already built combined candidate.
Normal, ordinary VERIFY, TIMING_STUDY and PROFILER_WINDOW builds all pass
68000/PIC assembly. Local preferences remain mask 63. The final `simulation-final`
fixed-window off/on matrix uses CUSTOM2=63/127 on spin/wall and both CPUs;
its results must be analyzed separately in profiling §8 before performance claims.


### Final measurement route correction

The first `simulation-final` matrix is incomplete and must not be presented as
final A/B evidence. Its 020 timing-off spin window caught the townsman's native
conversation: zero display steps, with the screenshot still showing his message.
The report correctly stopped on zero complete C2P calls. The two preceding A500
windows completed, but their renderer-call means mix logic-only catch-up with
drawing when timing is enabled.

`tools/tapes/timing-perf-{spin,wall}.txt` retain the original route and add another
1500 fields of EXIT pulses before turning. The first revised 020 timing-off spin
window reaches unobstructed large-view gameplay. The replacement matrix is
`simulation-final-long`, CUSTOM2=63/127, both routes and both CPUs, guest profiler,
with KEEP_TRACE=1. Results are pending; its longer startup makes it a separate
benchmark from previous sections.

`tools/lov_simulation_cost.py` splits retained complete renderer calls and whole
simulation ticks according to whether they enter h12:027e6, the drawing
continuation. Logic-only renderer calls still update actors/world state. Whole
ticks additionally include input, physics, sprite/display work when applicable,
and any scheduler wait. Partial boundary calls are excluded. Stack-distance
interrupt exclusion follows the existing renderer reporter. This is cost evidence,
not a claim that different elapsed-time scenes are pixel-identical.


### Elapsed-time debt audit of the projectile pairs

All 81 observations in each projectile capture satisfy both identities:
`delta(consumed) = 2 * delta(started_ticks)` and
`delta(simulation fields) = delta(native VBL field)`. No active elapsed time
is lost. Eighty ticks advance exactly 160 logical fields in every capture.
The observed wall-time intervals differ because the first/last observations
land at different points in the drawing/catch-up cycle:

| CPU / drawing | Elapsed fields | Debt first → last | Debt min–max |
|---|---:|---:|---:|
| 020 normal | 159 | 3 → 2 | 2–4 |
| 020 delayed | 167 | 3 → 10 | 2–11 |
| A500 normal | 151 | 15 → 6 | 3–15 |
| A500 delayed | 160 | 15 → 15 | 3–22 |

Debt is `simulation fields - consumed`. This explains the wall-time differences
exactly: elapsed fields equal logical fields plus the change in debt. Identical
logical states at each tick establish deterministic progression, but do not
establish identical instantaneous world state at the same wall-clock field:
synchronous drawing temporarily delays simulation. The observed maximum debt
in this test is 440 ms on the delayed A500. These are finite-window observations,
not a global latency bound or proof that any arbitrarily slow machine can keep up.


### Native save-name editing on the integrated collector

`sim-text-a1200` and `sim-text-a500` exercise the actual save-name UI, not a
standalone blocking-reader call. The VERIFY-only `TIMING_KEYS_TEXT` fixture
observes the h8:00800 console-poll thunk after the panel is active, then sends
native input.device events. The console produces `aBcc`, backspace and Return;
the native editor retains `aBc`. Its first character uses the panel's polling
path and subsequent characters use the blocking reader. All six reads are UI
reads without a simulation cutoff, with the private world clock frozen.

Both CPUs pass `lov_text_check.py`: eleven raw events, six console bytes,
real blocking waits, no collector error, no input-history recovery, balanced
options suspension and resumed simulation. The 020 has 77 post-dialog tick
intervals and the A500 71. The edited slot is 1 on 020 and 0 on A500 because
a pending native row click can select a different slot after editing returns;
the checker inspects the edited string independently of the final selection.
This checks text editing and return-to-world behavior, not which slot the user
intended to save. Only the isolated capture disk is written.

Both retained slaves have SHA256 `d02f65916d9dc5fed774bd3af15a276c837263bd656958eb3a4b5a947f66c0e3`. Reproduce with a VERIFY build containing
TIMING_STUDY and TIMING_KEYS_TEXT, the `timing-text.txt` tape, CUSTOM2=127,
CUSTOM5=16777217, KEEP_SLAVE=1, STATE_ONLY=1, STATE_TICKS=80 and §7 machine
settings. The fixture is excluded from normal and PROFILE builds.

The final repeated-mode matrix uses `tools/timing_modes_validate.sh`: eight
serial captures, both CPUs, CUSTOM2=126/127 (W1 off/on, timing on), normal versus
eight-field drawing delay. The native tape requests four mouse-look transitions,
while the VERIFY hardware-counter fixture supplies negative motion through both
modes. `lov_modes_check.py` requires four transitions, motion, no recovery,
complete tick samples and identical decoded logical states within each pair.
This matrix is currently pending; its existence is not evidence of a pass.


### Completed W1/mode matrix

All eight `sim-modes-final-{a1200,a500}-{126,127}-{normal,delayed}` captures
pass. Each retains 121 completed-tick observations, four native mouse-look
transitions, a negative heading wrap, no transition motion jump, no relative
motion in pointer mode, and no history recovery. Every decoded logical state
matches within each normal/delayed pair, including actors, player, keyboard/
pointer state, projectiles, animation, RNG and logical clock. The native live
clock and simulation debt are reported separately, not asserted equal.

| CPU / CUSTOM2 | Transition sample numbers | Drawing delays normal / delayed | Maximum debt normal / delayed | Elapsed fields normal / delayed |
|---|---|---:|---:|---:|
| 020 / 126 (W1 off) | 6,30,54,78 | 0 / 20 | 6 / 13 | 242 / 250 |
| 020 / 127 (W1 on) | 7,31,55,79 | 0 / 21 | 5 / 12 | 242 / 249 |
| A500 / 126 (W1 off) | 8,32,56,80 | 0 / 5 | 20 / 27 | 251 / 254 |
| A500 / 127 (W1 on) | 10,34,58,82 | 0 / 5 | 18 / 26 | 235 / 250 |

Every run consumes exactly 240 logical fields for 120 ticks. At every sample,
active fields track native elapsed fields exactly; endpoint differences are
entirely changes in outstanding debt. Maximum observed debt is 27 fields
(540 ms) in the deliberately delayed A500 W1-off run. This tests rendering-rate
independence for both W1 settings on both CPUs; startup and sampling phase differ
between settings, so cross-setting sample indices are not asserted identical.

All eight slaves share SHA256
`76236fa79402bb5b30f0024520b6ed66e84dcb61d2c0075548052d51258773f2`.
All pass original frame-cap, display dispatch and beam-wait byte comparisons.
CUSTOM2=126 additionally leaves the original C2P entry untouched; both masks
leave every bit-7 range unchanged. Reproduce with
`tools/timing_modes_validate.sh PREFIX`; check retained results with
`lov_modes_check.py NORMAL DELAYED`.

### Equal elapsed-field observations of the final candidate

`sim-fields-final-a1200-normal`, `sim-fields-final-a1200-delayed-retry` and
`sim-fields-final-a500-{normal,delayed}` retain 241 world observations over
exactly 240 native PAL fields. They use the same `76236fa7…` mode-fixture build,
CUSTOM2=127, CUSTOM5=2049 and normal/delayed mode tapes, with STATE_FIELDS=240
instead of STATE_TICKS. The original 020 delayed observation failed in the
remote debugger (`Invalid hex digit 79` / EOF) and is excluded; the fresh retry
completed. No game source changed to obtain the retry.

| CPU / drawing | Completed tick increase | Drawing delays | Pending-field range at VBL observations | Final heading |
|---|---:|---:|---:|---:|
| 020 normal | 120 | 0 | 0–4 | 170 |
| 020 delayed | 120 | 20 | 0–11 | 170 |
| A500 normal | 121 | 0 | 1–17 | 170 |
| A500 delayed | 119 | 5 | 1–25 | 170 |

`lov_elapsed_check.py` verifies equal field intervals, no pause or history
recovery, and correct active-field accounting. Sample zero is late in the
anchor VBL; later samples are h12:0640a, before the private clock increment.
The resulting one-field counter phase is explicit in its assertions.

Initial decoded non-clock world state agrees in both pairs. The 020 retry's
live/logical clock epochs are one field later than its normal control; the
A500 epochs match exactly. That offset is reported, not silently normalized.
These observations therefore quantify actual wall-time behavior and pending
work; the pure determinism proof is the separately matched completed-tick
matrix above, including logical-clock equality.

At equal elapsed fields, actor positions can differ while one CPU is drawing
or partway through a tick. This occurs in 226/241 020 samples and 195/241 A500
samples. The normal-minus-delayed completed-tick gap ranges from −1 to +5 on
020 and −7 to +11 on A500. Even equal completed counters do not imply equal
instantaneous actor records when the next tick is in progress. This feature
provides fixed-rate logical progression and catches up after drawing; it does
not make the synchronous renderer preemptible or guarantee zero input latency.

### Final movement-step reader audit

The native display-clock table writes h12:0cdd6 at h12:05e5e. The h12 data-base
relative displacement is −4232 from h12:0de5e. The code-hunk scan identifies
three readers of that displacement: h12:10a80, h12:10abc and h12:14b78. The
first initializes motion components in the private state around h12:0cdc8;
the second advances its accumulator. Their in-game role remains provisionally
classified as scripted motion. The third initializes actor speeds as described
at the start of this log. All receive the same constant step 10, set before
startup and from every compensation-table entry. Player command translation,
mouse displacement, turn constants and animation pacing are mapped separately
above; they are not additional readers of this word. Native fractional fields
and collision order are retained rather than scaling whole displacements.
