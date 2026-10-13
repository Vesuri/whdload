# CD32 framerate-dependency audit

Phase 7b is complete for the pinned English CD32 executable. This is an inventory
and native reproduction gate, not an implementation of timing changes. Phase 8 selected D; the phase-9 implementation closes its clock ownership below. The
phase-7 flight-unit anchor is **10 world updates/s**. No new emulator matrix or
live run was required for this audit.

`E:` means English code hunk 0, `D:` data hunk 1, and `S:` slave code hunk 0.
Code file offsets are `E + 0x2c`; file-backed data offsets are `D + 0x3a048`.
Data beyond `D:8464` is allocated state, not stored executable payload. In
particular the callback table `D:0372` is at executable file offset `0x3a3ba`.
These are never relocated runtime addresses. The input and reproduction commands
are in [development](development.md#phase-7b-native-framerate-dependency-audit).

## Coverage and boundaries

The world root is `E:02a8`: housekeeping `0260`, object lifecycle `76e4`, two-pass
world work `7b4e`, camera/control state `680e`, conditional encounter work `1568`,
and the update counter at `02d6`. Its callers include the ordinary flight loop
(`06b8`) and modal loops such as the VBL-deadline loop at `0e8a`. Drawing follows
at `06bc`; input is sampled earlier at `069e → 19330`.

`timing_inventory.py` follows both sides of branches, direct calls, and every
entry of the decoded dispatch tables. The retained closure contains **30,384
instructions, 6,118 direct/selected-helper edges, 54 tables and 625 entries**.
All entries reach their decoded targets on both native CPU models. The 52 bounded
word switches also reject the first out-of-range index and `65535`: **104 bounds
checks**. Callback and image tables have separately inspected index construction.
This establishes target coverage; it does not claim every semantic branch of every
handler ran in a live mission.

| Dispatch family | Dispatch instruction offsets and entry counts |
|---|---|
| Cockpit, communication and presentation selection | `04562:10`, `045c2:10`, `04648:7`, `0469c:7`, `04dd4:13`, `05808:14` |
| Effects, camera, construction and lifecycle | `0675c:8`, `070a6:16`, `0767e:16`, `07b3a:10` |
| Collision and AI entry | `08938:6`, `08a9e:4`, `09b94:19` |
| Damage, outcome and weapon selection | `0aacc:9`, `0aece:9`, `0b384:14`, `0b418:13`, `0bdbe:4`, `0beac:4`, `0c876:4`, `0c8f8:8` |
| AI/action and class-1 state | `0d6c6:11`, `0d7f8:11`, `0dac4:11`, `0de0e:8`, `0e016:8`, `0e2a8:11`, `0e498:8`, `0e696:12`, `0eaa0:12`, `0fbc4:4`, `10308:8`, `10438:9`, `10676:10` |
| Ship-script actions and their substates | `12544:5`, `128da:4`, `12abe:4`, `12b60:4`, `12d6a:11`, `12e28:4`, `13190:6`, `1398a:6`, `13a68:4`, `13d60:47`, `140cc:5`, `141aa:5` |
| Encounter, camera script and mission selection | `146a6:10`, `14a88:5`, `18900:17`, `1bcc0:8`, `21baa:11` |
| Arithmetic/presentation helpers reached transitively | `2d2e4:5`, `2e06a:8`, `2fdde:128` |

The lifecycle selector subtracts four from the class before using `E:7b18`.
Classes 4, 6, 7, 8, 10, 11 and 12/13 enter `776c`, `77ac`, `76fc`, `7728`,
`77da`, `7808` and `78dc`, respectively; 5 and 9 return without lifecycle work.
This includes projectile expiry, missile launch/guidance delay, dying ships and
removal. The effect selector `E:673e` sends classes 5/6/7/9/10 to the script
interpreter, 8/11 to no effect work, and 12 to damaged-ship emission.

`E:7b4e` first clears distance caches. Class 1 uses `eaa8`; classes 0–3 otherwise
skip ordinary object processing. Active classes above 3 enter effects; classes
8 and above enter collision and rotation. Non-player AI enters `8940`. Ship slots
below ten with class at least 11 enter the angular controller `9ed4`; class 12
also regenerates gun energy. The second pass integrates all active classes above
3, and adds shield/fuel work for classes at least 12. Collision therefore sees
sampled positions **before** that pass's position integration.

The action selector `E:13d26–13d60` guards signed action `D:baf2` to 0–46 and
loads a long pointer from `D:0372`. All 47 entries, including duplicate/no-op
entries, are followed. Actions share the `D:c272` elapsed/countdown word and
`D:c288` phase byte; `E:11620` resets both. The 16 arithmetic writer sites checked
separately are `d37c`, `dcae`, `dd70`, `126fc`, `12804`, `12848`, `12902`,
`129fc`, `12afa`, `12b32`, `12ba2`, `12d02`, `12db8`, `1333e`, `13964`,
`13a06`. Other action callbacks issue movement, targeting, firing, random choices
or phase transitions using the shared systems below. Phase advancement at `127b2`
and bytecode-pointer advancement are events, not additional elapsed-time clocks.

The closure has **52 explicitly classified leaf transfers**, not silently ignored
indirect calls. They are resource byte-copy runs (`28a40/28a50`), image copy/fill
and bitstream kernels, formatted text callbacks, C memory-copy/runtime callbacks,
and OS library vectors. The complete per-site classification is in the generated
inventory. Selected music decoders (`277b4`) and memory allocators
(`309a4/30b02`) are followed to both alternatives. The two external code edges
are known slave adapters `S:16fc/176a`. No unidentified simulation callback remains.
OS implementations, slave internals and resource data are boundaries, not a claim
of whole-machine disassembly coverage. An unclassified indirect transfer fails the
inventory command.

The clock census follows this call/dispatch closure, then checks data writers and
initialisers, including byte counters and register-mediated writes. Arithmetic
alone would miss the effect opcode interpreter, direct counter reloads, input
latches, random choices and sampled predicates. It would also misclassify score,
list length, ammunition and damage accumulation as clocks.

## Stable findings

**Reproduced** means original native instructions demonstrate the stated local
dependency on both CPU models. It is not a live-game timing guarantee. A full
routine is distinguished from a bounded slice below. **Static finding** extends
that local evidence through the inspected callers/initialisers. **Verified
unaffected** closes a candidate only in the stated scope. These IDs remain stable
when fixes arrive; add cases to an item rather than renumbering it.

### FR-01 — Translation and acceleration: reproduced

`E:7d1a` computes velocity changes, `807a–809a` writes them, and `80b6–80e0`
adds velocity to `D:919a + 12*i`. Velocity is `D:9d6c + 12*i`; both retain eight
fractional bits. One second of unchanged native velocity 5120 produces displacement
51,200 at ten calls and 256,000 at fifty. A controlled +256 acceleration writeback
followed by the actual integration produces 14,080 versus 326,400. Tests execute
the real vector routines, not a rewritten motion model. The nonlinear acceleration
coefficient computation remains static coverage; merely scaling position leaves
acceleration and its clamps rate-dependent. Tiny signed velocities ±1 survive the
native position addition; there is no basis to discard that existing fraction.

### FR-02 — Orientation, angular damping and steering: reproduced

`E:7c86` applies three axis rotations and `2b66c` moves each angular step one unit
toward zero. `D:9578/95f8/9678` hold the steps. From a controlled orthogonal basis,
repeated one-unit yaw gives forward vector `(27,0,-254)` after ten calls and
`(110,0,-231)` after fifty; the test executes the complete angular-update routine.
The independent damping fixture moves 100 to 90 versus 50. AI steering at
`9ed4 → 9dc4` also uses per-call integer division, minimum increments and clamping;
that controller needs fractional treatment or its own fixed sub-clock, not just
rescaled final rotation. Its complete feedback response is a live gap.

### FR-03 — Fuel expenditure: reproduced

`E:cb78 → 15900` subtracts speed-derived fuel per update from `D:a7cc + 4*i`.
At the controlled speed 5120, fuel 100,000 becomes 99,950 versus 99,750 after ten
versus fifty calls. The whole fuel routine runs. Separate afterburn expenditure
at `E:7ebc` is an additional path; charging fuel per rendered frame is incorrect.

### FR-04 — Afterburn duration: reproduced

`D:bb14 + 2*i` is decremented at `E:7e1c/7ee0`. `E:cb4c` installs ten for action
3; `cad8` can supply the action-1 duration. The `7e10–7e1e` slice reproduces the
countdown. Its zero transition changes action/speed, so an elapsed-time conversion
must preserve the residual interval and transition once. The afterburner input
was exercised live in phase 7; all alternate action branches were not.

### FR-05 — Object life, death and shrinking: reproduced

`E:76a8` decrements `D:94c6 + 2*i`, except the permanent `-1` sentinel. Constructors
include the literal five at `c710` and the missile duration copied at `ca9e–cab4`;
`9af2` also installs model-specific state. Lifecycle dispatch uses the resulting
value to remove objects or progress death effects. Full-routine tests give 90/50
from life 100 and preserve `-1`. In the ship despawn action, `E:790e` halves size
each update: positive size 16,384 becomes 16 after ten calls and zero after fifty.
This nonlinear shrink needs a sub-clock or an explicitly equivalent decay policy.
See FR-23 for the high-bit instrument limitation.

### FR-06 — Missile launch/guidance byte: reproduced

`E:c71a` and `ca9e–caa8` install `D:baa8 + i` (default 20). `77da/7808` interpret
it as a signed positive byte before decrementing and changing lifecycle/guidance
behaviour. The native predicate/decrement slice leaves 128 and 255 unchanged;
127 becomes 126. Enlarging the stored duration for a finer tick can therefore
turn it into a non-decrementing negative value. The real default lasts one second
at 20 calls/s, 0.4 seconds at 50, and 0.333333 at 60. The changing-rate experiment
expires at 0.8 seconds for 10→50 and 0.4 for 50→10, each switching at half a second.
These are local timer expiries, not measured missile flight lifetimes.

### FR-07 — Shield and gun-energy recovery: reproduced

`E:cba4` gates shield recovery with world counter `D:914c` and the model's period
at `D:53a4 + 104*model + 12`. `E:cc36` adds gun energy to `D:9546 + 2*i`, with
system-damage and shield-dependent conditions. Controlled whole-routine fixtures
produce shields 2/12 and gun energy 20/100 at ten/fifty calls. Firing spends energy
at `c538`; firing eligibility at `c9d2` also depends on weapon selection and energy.
The hardpoint byte tested at `ca12` is selected/disabled state written by
`1a5a2/1a5aa`, not an inferred reload countdown. Fire opportunities must be assigned
to a simulation/input boundary; per-shot costs must remain per shot (FR-22).

### FR-08 — Damage response and death delay: reproduced

`E:9d2c` installs four in the signed byte `D:c06c`; `a598` decrements it, with
player exit/death and non-player action side effects. Collision adds four to the
response byte `D:be84` at `827c`; AI consumes it at `e6aa`. The native writer slices
show both shorten with update frequency. Damage values themselves are per-hit
quantities; rescaling those would change damage per projectile. Live ordinary
combat damage and every damage-dispatch outcome remain unvalidated.

### FR-09 — AI decisions, staggering and random stream: reproduced

`E:89c6` offers a decision every fourth world update, with a selected-missile
exception. The native predicate gives 2/12 eligible opportunities at ten/fifty
calls for an ordinary controlled slot. `E:fa64` consumes the signed stagger byte
`D:c2c8`, reloads it from `D:c2d2` and advances the AI phase `D:c1f0`; `21898`
initialises staggered phases from the model table. `E:2cb56` mutates the shared
random seed `D:6f18` once per draw. The full RNG fixture and stagger-writer slice
reproduce call-count dependence. Keep decision cadence and random consumption
order explicit; a probability multiplier alone does not preserve the sequence.

### FR-10 — Ship-action elapsed state: reproduced

The 47-entry action table and nested switches share `D:c272/c288`. Native checks
cover all 16 arithmetic writer sites listed above, plus the full reset at
`E:11620`. Examples include the `>20` manoeuvre at `126fe`, `>10`/`>5` phases at
`12806/1284a`, and `>3` phases at `12afc/12b34`. Increment/decrement slices prove
the clock dependency; they stop before unrelated firing/movement side effects.
A variable-step fix must cross thresholds and emit transitions exactly once,
including multiple expired phases. A byte phase ID is not a duration to rescale.

### FR-11 — Target/contact hysteresis: reproduced

The shared target counter at `D:38b6` moves toward its trigger at `E:d46c/d47a`.
The contact hold at `D:c2dc` is loaded with three by `10a20` and consumed by
`10a52`; the encounter hold `D:00ec` is loaded with ten at `167a` and consumed at
`169e`. Native countdown slices reproduce frequency dependence. The positive and
negative/sentinel meanings must remain distinct. The end-to-end player missile
lock and encounter interaction are static findings with the phase-7 live gap intact.
D additionally moves draw-called target selection `E:3b8e` to each world boundary,
refreshes native geometry `2a086` there, and uses world modulo eight for its lock
failure trial at `3bca`. Extra rendered frames cannot commit targeting changes.

### FR-12 — Sampled collision and tunnelling: reproduced

`E:1597e`, reached through `8196`, tests overlap at the current positions against
collision masks and summed radii. A controlled class-8 projectile and class-12
ship, each radius five, return no collision at relative x = -20 and +20 but a hit
at zero. These are complete calls to the original overlap routine. Thus a step
joining those endpoints can cross the target without either sample detecting it.
The test demonstrates the point-sampling defect mechanism, not an observed missed
shot in a live mission. Swept tests or bounded collision substeps must cover the
selected integration policy; changing lifetimes alone cannot close this item.

### FR-13 — Sampled range/angle transitions: reproduced

The complete `E:1187c` predicate compares cached range `D:bb10` and angle `D:ac68`
with thresholds. A prescribed equal-time pass through its qualifying region
produces zero accepted samples at 10 calls/s and one at 20/50/60. The 10→50
schedule also misses it; 50→10 sees it. The fixture supplies samples to isolate
predicate sampling from FR-01's integration error. Related inspected consumers
include landing conditions `7af2–7b0a`, action thresholds `12866/12982`, and
encounter geometry `15ce–1674`. Those callers are static coverage; actual approach
paths still need live validation. Detect crossing or retain bounded sampling.

### FR-14 — Effect script clock and quantisation: reproduced

`E:28f96` consumes `D:c076 + 2*i`, reloads the model period at
`D:53a4 + 104*model + 36`, and advances index `D:c0f6`. A period-four script
advances 2/12 times at ten/fifty calls. Full-routine fixtures separately cover frame,
jump (`0x9...`), removal (`0xa...`), grow and shrink operations. Growth/shrink at
`29062/29088` computes `floor(size/64) * factor`: size 63 remains 63 for factor one,
where size 64 grows to 65. Fraction carry cannot be discarded in a scaled version.
Removal changes world membership; these scripts cannot all be labelled decorative.

### FR-15 — Draw-counter-dependent world emission: reproduced

Damaged class-12 ships enter `E:65e0`; `65f4–65fc` permits emission only when
**draw counter** `D:9150 & 3` is zero. The branch then uses hull/model thresholds,
allocates a world slot and draws random values. Native mask checks give 3/13
eligible samples when supplied ten/fifty consecutive draw counts starting at zero.
This is a gate test, not a count of emitted objects. Even retaining a fixed world
rate leaves a coupling if rendering advances that counter independently. Bind
emission to a world sub-clock and preserve allocation/RNG order.

### FR-16 — HUD, communications and transient indicators: reproduced

`E:22a0` decrements message duration `D:a956` (set by `2298`) per draw;
`4b16` consumes cockpit/selection duration `D:b2aa`, reloaded with 20 or two at
`4c28/4c3c`. `E:16084` decrements six hit-indicator bytes `D:c4f4–c4f9`, set to
four by `15ffc–1607a`, per world update. Native routines/slices reproduce each
countdown. Communications animation gates on odd draw counts at `435c`, then
`43e8–43f4` calls the same RNG as gameplay. That original slice changes the shared
seed differently for ten/fifty draw schedules. Separate presentation time without
letting extra portrait frames consume gameplay randomness. VBL-based blink at
`1a78` is separately unaffected by update count (FR-21).

Phase-9 schedule comparisons also exposed the HUD call `E:46ea → af84`
(files `4716 → afb0`). It makes per-call random trials at `af9c/afae` and can
change cockpit subsystem damage via `af14`. This is gameplay fault/repair polling,
not purely visual noise. D moves the whole polling call to the world tick and
suppresses its draw call. Native whole-routine checks and live equal-tick state
comparisons cover this additional FR-16 dependency. Simulator draw tail
`E:0530–057e` likewise contains a countdown and exit/position event and is moved
to the world tick, together with score/time bookkeeping at `E:0438`.
The complete ordinary render call has a private random stream; star/debris
regeneration must not leak extra draws into the gameplay seed. These paths were
not safe to leave coupled to a faster renderer.

### FR-17 — Mission and encounter polling: reproduced

`E:0260` polls `061c → 2124c` on world-counter modulo 32 and `99a2` on modulo 16
when its encounter list is non-empty. The native mask slices produce respectively
1/2 and 1/4 opportunities in ten/fifty ticks starting at zero. `D:914e` counts
encounter records (`9998`); it is not itself elapsed time. Mission state, spawning
and encounter crossing must preserve the sub-clock, its initial phase and event
ordering. Native gate arithmetic is proven; full campaign progression is not.

### FR-18 — Camera, scripted wait and class-1 state: reproduced

`E:680e` dispatches camera/control modes. Its wait `D:ba50` increments at `6c2c`
and tests the previous value against 20. When enabled, it also calls the script
runner `18910`: opcode 14 decrements `D:9540` (`1891c`), whose count was read
from the script at `18626`. Script data/operand pointers advance per command, not
per elapsed second. Class-1 work at `eaa8` increments `D:c292`; `1417a` consumes
the same storage for a different state. Native slices reproduce all these writers.
Keep modal/script and class-specific interpretations distinct. No claim is made
that the camera script is a general deterministic gameplay replay recorder.

### FR-19 — Input edges and replay boundary: reproduced; replay scope static

`E:19334–19342` copies 16 current-input bytes `D:c6c8` to previous-input
`D:c6d8`, then polls devices and queued events before the ordinary world step.
The original edge predicate `19130–19142` delivers an unchanged current/previous
pair five times if reused across five ticks, once if the native latch is advanced.
This is the boundary a catch-up loop must define for held axes, edges, gun/missile
launch and menu commands. FS-UAE input recordings are field-indexed external
inputs; matching them is not proof of equal simulation inputs after decoupling.
The world closure contains the camera script above, but no general gameplay-replay
contract has been established. Replay compatibility therefore remains a candidate
requiring a specified format/consumer before a stronger claim.

### FR-20 — Modal loops and pause: reproduced locally; live gaps retained

`E:0e64` uses a VBL deadline while repeatedly calling world update and drawing;
`0e82–0e88` correctly reports ten remaining ticks for deadline 60 and clock 50.
Landing has a separate direct update-counter writer at `1b498` and a size decrement
at `1b49c`: the original slice shrinks 200 to 180/100 for ten/fifty iterations.
It is not controlled solely by replacing the ordinary flight loop. Phase 7 verified
pause freezes mapped world state while VBL advances. Autopilot, landing and all
modal entry/exit routes still need live tests. Do not accumulate catch-up debt
across pause, loading or transitions into these loops.

### FR-21 — VBL music/calendar clock: verified unaffected in tested scope

`E:34166` increments `D:7f02` independently of world-call count: 50 native producer
calls always give 50 for all tested world schedules. Phase 7 supplies the actual
live VBL/pause evidence; native scheduling alone cannot prove interrupt delivery.
Static readers include blink `1a78` and calendar `22c32`, whose divisor is 3300.
Music/text timing is not a candidate for wholesale simulation scaling. Preserve
the existing clock and deadlines; do not reinterpret the calendar as a world delta.

### FR-22 — Event quantities: verified unaffected in tested scope

The statistics writer `E:b388` receives an event amount; five +1 events give five
in `D:9128` irrespective of the idle update schedule. Related inspected writers
include damage/hull updates `a338/a7f8/a842/a8fa`, damage-state bytes
`a978/aa1c/acf6/ade2`, energy spent `c538`, kill/outcome counters `b48a/b496`,
list counts `5352/943a/9998/ec52/edd6`, and script/list pointers. Their event
frequency may depend on other FR items; the amount of one event must not be
multiplied by elapsed time. This closure is per-event arithmetic, not proof that
all gameplay event frequencies are unaffected.

### FR-23 — Width, sentinels and integer remainders: reproduced, with a limitation

Beyond FR-06's signed byte, `D:c272` wraps 32767 to -32768 after one original
increment. `D:94c6 = -1` remains the permanent-life sentinel. Byte counters, word
comparisons, exact equality transitions and initialised frame counts need a shared
conversion policy; enlarging every literal is unsafe. Step-scaled fuel, steering,
size and acceleration must carry remainders in suitably wide storage, with explicit
clamping and threshold crossing. Native checks cover these word/sentinel boundaries
and FR-14's lost size fraction.

**Instrument limitation:** an exploratory size `0x8000` through memory `LSR.W`
at `E:790e` produces `0xffe0` after ten calls in the installed Unicorn models,
rather than the logical-shift expectation `0x0020`. The report records both values.
Positive sizes are used for FR-05's timing reproduction. This discrepancy is not
classified as a game defect or physical-CPU behaviour; high-bit shift semantics
require another instrument if a future change relies on them.

## Clock-policy and implementation-cost implications

These are audit costs, **not CPU-cycle prices or a design recommendation**.
B is variable elapsed step; C is a finer fixed world tick; D keeps the 10 Hz world
and advances selected player/camera/presentation work between ticks. “Retain” still
requires a correct scheduler and the explicit shared-state hand-offs below.

| Item | Possible policy | B: variable step | C: finer fixed tick | D: hybrid |
|---|---|---|---|---|
| FR-01 | Scaled increments with carried fraction; bounded substeps | High: velocity, acceleration, clamps and integration order | High: rescale quantities and preserve response/precision | Medium: retain world; interpolate views and hand off player state |
| FR-02 | Scaled rotation/decay or fixed steering sub-clock | High: axes, controller and damping | High: rescale nonlinear controller without losing small steps | High for player/camera; retain other ships' controller |
| FR-03 | Elapsed fuel charge with remainder | Medium: both ordinary and afterburn paths | Medium: fractional charges | Low: retain world charge; define player afterburn duty |
| FR-04 | Elapsed timer with remainder or native sub-clock | Medium: expiration and residual motion | Medium: counter width and transition | Low: retain timer; latch player command once |
| FR-05 | Fixed lifecycle sub-clock, or elapsed life plus equivalent decay | Medium: expiry, sentinel and shrink | Medium: scaled life and nonlinear shrink | Low: retain world lifecycle; present between ticks |
| FR-06 | Wide elapsed delay or native missile sub-clock | Medium: signed byte, guidance hand-off | Medium: byte cannot simply hold enlarged constants | Low: retain delay; launch once at world boundary |
| FR-07 | Fixed recovery sub-clock or fractional regeneration | Medium: both recovery paths and fire opportunities | Medium: modulo period and fractional energy | Low: retain world recovery; hand off firing |
| FR-08 | Fixed response sub-clock or elapsed hold | Medium: all death/response paths | Medium: signed byte and resets | Low: retain world; interpolate visual response |
| FR-09 | Fixed AI/RNG sub-clock | High: preserve opportunities/order amid variable steps | Medium with sub-clock; high if AI also accelerated | Low: retain AI and RNG sequence |
| FR-10 | Fixed action sub-clock or elapsed state machine | High: every state reset, crossing and emitted event | High if fully rescaled; medium with sub-clock | Low: retain action interpreter |
| FR-11 | Elapsed hold/hysteresis or fixed targeting sub-clock | Medium: signed semantics and resets | Medium: widen/rescale correctly | Medium: player targeting and world lock hand-off |
| FR-12 | Swept collision or bounded collision substeps | High: variable displacement and event order | Medium: prove maximum displacement is safe | Medium: collision against world, never interpolated display state |
| FR-13 | Threshold crossing or bounded predicate sub-clock | High: range/angle crossings and multi-transition steps | Medium: preserve detection envelope | Medium: player approaches must use agreed world samples |
| FR-14 | Native effect sub-clock; presentation interpolation | Medium: scripts also remove world objects | Medium: avoid quantisation and changed script semantics | Low/medium: retain script; interpolate visuals only |
| FR-15 | World-bound emission sub-clock | Medium: detach draw counter, allocation and RNG | Medium: replace draw gate | Medium: must detach even when world stays 10 Hz |
| FR-16 | Elapsed presentation clocks; isolated visual randomness | Medium: split HUD timers/RNG from gameplay | Medium: avoid accelerating indicators | Medium: faster draws must not consume gameplay RNG |
| FR-17 | Fixed mission/encounter sub-clock | Medium: preserve modulo phase and events | Medium: rescale/rebase scheduling | Low: retain polling; verify crossings with player hand-off |
| FR-18 | Native modal/script sub-clock | Medium: distinct camera/class-1/script clocks | Medium: protect modal and script states | Medium: camera ownership must be explicit |
| FR-19 | Timestamped/latching input boundary | Medium: held input versus one-shot events | High: catch-up ticks must not duplicate edges | High: render-rate control versus tick-rate launches/replay |
| FR-20 | Explicit modal scheduler; no accumulated world debt | Medium: audit alternate update loops | Medium: audit alternate loops and catch-up | Medium: gate player/world clocks at transitions |
| FR-21 | Preserve existing VBL clock | Low: keep separate | Low: keep separate | Low: keep separate |
| FR-22 | Per-event amounts, never time-scaled | Low: preserve amounts, fix upstream frequency | Low: preserve amounts, fix upstream frequency | Low: deliver events once |
| FR-23 | Wide accumulators, remainders, explicit sentinels | High: cross-cutting conversion and equality audit | High without sub-clocks; byte/word limits still apply | Medium: mainly new player/presentation state and hand-offs |

## Gate evidence and limits

`tmp/phase7b-native-verified/report.json` passes on Unicorn 68000 and 68040 with
identical results. It includes steady and changing schedules, constructor/reset
and sentinel cases, all dispatch entries/bounds checks, and two rejecting negative
controls. The complete inventory is `tmp/phase7b-inventory-gate/inventory.json`.
The native run executes original code from the retained live dump; controlled
state and synthetic trajectories deliberately isolate each mechanism.

The audit is complete for the world root and dispatch inventory at the stated
subsystem boundaries. It identifies each clock family and the work each design
would require. It does **not** claim complete mission-path execution, physical CPU
performance, a proven gameplay replay contract, high-bit Unicorn shift fidelity,
or live validation of comms, missile locking, ordinary damage, autopilot, landing
and campaign progression. These limits do not conceal an unidentified world
callback: they distinguish static inventory/native reproduction from later live
validation of a chosen fix. Stop at phase 7b.
