# Simulation timing investigation (2026-10-07, ongoing)

Rendering patches W3–W6 keep the existing clock, movement and AI behaviour.
This investigation is separate; no simulation patch is enabled.

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

## Proposed direction; rate choice pending

Use fixed simulation ticks with an elapsed-field accumulator, retaining each
original small motion/collision step in its original order. Drawing runs once
per selected output frame; overdue simulation ticks advance without repeatedly
running wall/sprite rasterization or chunky-to-planar conversion. Existing
25 fps display pacing and beam synchronization remain in the output path.

The proposed reference is 25 ticks/second, matching the original game at its
rendering ceiling, with canonical movement-step 10 and animation pacing 4.
A 12.5-tick/second reference is a slower gameplay alternative. The rate applies
to player movement, turning, projectiles, actor countdowns and periodic AI.
It will change gameplay speed on machines whose original rendering runs below
the selected reference. This is a separate optional patch; W1–W6 keep their bits.

The user has been asked to choose the reference rate before implementation,
as the playbook §9 requires a design decision after the coupling verdict.
Implementation still needs concrete hooks for simulation-only catch-up,
input consumption, paused/dialog/loading clock rebasing, and long-stall
handling. Measure catch-up cost on the A500 and validate equal-time progression
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
