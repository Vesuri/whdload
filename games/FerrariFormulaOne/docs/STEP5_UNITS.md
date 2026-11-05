# Step 5 integrator conversion audit — in progress

Addresses below refer to the retained SPS 0481 driving image, not production
patch addresses. Resolve actual hunks and validate bytes before installation.
This document records inspected instructions, not completed conversion tests.

Native reference interval: 100 ms. Requested fine interval: 20 ms. The coarse
68000 interval remains provisional (200 ms in isolated timer tests). Use separate
continuous integration and elapsed-time event cadence; do not call the whole
native car routine five times as often unchanged.

## Position and segment frame

- `$67a04..$67a12` adds `$32f94.w` to lateral `$32fc2.w`.
- `$67a18..$67a26` adds `$32f96.w` to longitudinal `$32fc4.w`.
- `$67a2c..$67a30` clamps negative longitudinal position to zero.
- `$67a36..$67aaa` reads segment rotation from `$1dc24[segment]`, computes a
  sloped crossing coordinate `longitudinal + lateral * sin(angle,1000) /
  cos(angle,1000)`, then compares it with 512.
- `$67aac..$67b38` rotates `(lateral, longitudinal-512)` into the next segment
  frame. `$67b40..$67bcc` rotates the velocity vector into that same frame.
  Subsequent code adjusts heading and segment bookkeeping; inspect it before
  replacing the crossing loop. A scaled displacement can cross several segments.

Fine updates must integrate displacement at 1/5 native quantum and keep separate
fractional lateral/longitudinal state for each of eight cars. Segment coordinates
are a rotating frame, not independent wraparound counters: rotate the fraction
alongside the integer position at each crossing. Rotate stored velocity history
as well, otherwise the slip derivative will see a fictitious impulse. Negative
position clamps and collision/pit/tow resets must also handle the fractional
state. A simple per-car remainder reset at every segment crossing is not a
validated substitute. Coarse steps must retain the multi-segment crossing loop
and be tested for skipped contact, lap and sector events.

## Heading

`$678de/$67900` add recovery-spin increments; `$67948/$67976` add ordinary
steering/spin increments into Q12 heading accumulators `$32fb4/$32fb8`.
Scale continuous increments by elapsed interval and retain any extra fraction.
Do not scale coordinate-frame changes, collision impulses or angle wrapping.
Audit every writer of these accumulators, their per-car storage, and the derived
word angles `$32fc6/$32fc8` before adding persistent fractional state.

## Velocity and slip

`$6dc38` reads previous vector `$32f94/$32f96`, computes the new heading/speed
vector, subtracts old from new, rotates this change into the car frame, then
measures its magnitude and applies tyre/contact response. Merely reducing the
position increment does not convert this model. With a 20 ms step, an unchanged
velocity difference represents five times the native-reference acceleration.
Normalize this derivative to the native 100 ms reference before using native
thresholds/tyre curves, then integrate continuous response at the selected step.
Keep collision discontinuities distinct from continuous acceleration.

The function also reduces player tyre conditions `$66c52..` and opponent
condition `$22356[car]` according to this magnitude. These are elapsed wear
increments, not five-times-more-frequent probability trials. Preserve fractional
wear, clamping, difficulty scaling and player/opponent differences.

## Acceleration and response

`$6d4cc` computes drag/RPM/gear effects; it is not the complete accelerator.
Player accelerator/brake/clutch changes occur at `$673c4..$67476`; AI changes
occur at `$67500..$676e6`. Correction from the full writer sequence:
`$6773c..$67752` averages current and previous RAW AI steering requests, not
speed and not a recursive retention filter. `$6c958` returns the new request;
`$67740` stores its mean with `$32f7a[car]` to steering `$1c6a2[car]`, and
`$67752` stores the unfiltered current request to `$32f7a[car]`. Applying an
exponential retention coefficient here would change the controller model.
Preserve a 100 ms history separation with elapsed-time history; decide and
validate controller sampling/interpolation separately from physics cadence.
Fractional speed state is still required for the acceleration conversion.
A smaller Euler step changes displacement even when final speed is identical;
define endpoint and braking-distance tolerances from the measured quantities
before judging a converted path.

## Elapsed events and drawing ownership

Use the timer's native-tenth pulse output for event cadences whose original
meaning is one trial per 100 ms, rather than treating each fine update as a new
trial. Rotating wear `$6ea3e/$6ef52`, failure helpers, clutch/countdown counters,
audio phase and RNG consumption still need individual classification.

Drawing `$6bbfc` changes boost/audio state; `$6c20c..$6c21a` increments negative
player recovery status toward -1. Both need simulation ownership. The existing
omission fixture retains the former but not the latter. Add a prolonged recovery
fixture and decide its elapsed cadence before treating omission as independent
presentation. Native clocks at `$65dca/$65dd8` must keep their eligibility rules
and get tenth-second pulses from elapsed time, not drawing frequency.

## Required next evidence

1. Enumerate all writers/reset paths for each persistent fraction and history.
2. Extract the simulation mutations from drawing, including recovery; validate
   native-step equivalence with the existing contact fixture plus recovery.
3. Implement the fine/coarse updates quantity by quantity and test acceleration,
   braking, turning, segment crossings and contacts with explicit tolerances.
4. Measure those adapted updates; native-integrator arithmetic benchmarks are
   capacity guidance only. Keep the normal slave unchanged until integration
   has the version/CPU gating and disabled-path controls described in the plan.

## Fractional scaling primitive

`src/FerrariFormulaOne_Step.s` now implements exact rational 1/5 scaling of
signed continuous increments with an independent signed remainder per quantity,
and provisional integer ×2 scaling. Both report signed overflow without modifying
the input/remainder. They are not yet hooked into car state, and do not establish
that simply scaling a whole native update is a valid integrator. The unit audit,
filter/derivative conversions and frame/reset ownership above remain required.

The scaling primitive now passes 56 A1200 fine/reversal/fixed-point/overflow cases
and 11 A500 coarse/overflow cases. It has no live car-state hooks yet.

## Position writer audit and fractional accumulation

`FF1Position20` in `src/FerrariFormulaOne_Position.s` integrates one signed
word native displacement into a signed Q16 coordinate plus signed /5 remainder.
Its six-byte axis state holds integer, unsigned fraction, and remainder. Sixteen
axes require 96 bytes, allocated with MEMF_PUBLIC during eventual integration.
Both displacement scaling overflow and position overflow leave all six bytes
unchanged. The caller must handle the error, not discard the update. This is a
68020 helper and has no production hook yet. Guest tests pass 49 cases covering
positive/negative five-step movement, small increments and reversals, signed
limits and unchanged state on overflow. See `tmp/step5/position-scale-a1200/`.

Native position writers inspected from the active disassembly:

- $671fa/$6720e load per-car word positions into the shared work state;
  $68532/$68546 store them back. Shadow fractions must follow the car index,
  not remain attached to shared scratch storage.
- $67a12/$67a26 perform integrated displacement; $67a30 clamps longitudinal
  position to zero. A clamp clears that axis fraction and rational remainder.
- $67b38/$67b52 commit segment-frame rotation: x'=cos*x-sin*(z-512),
  z'=sin*x+cos*(z-512). Both fractional axes and rational remainders need the
  same frame transform. The following velocity rotation ends at $67bcc.
- Native sine/cosine at $24fe0/$25000 multiply signed word values by table
  coefficients and shift 15 bits. The integer callers consume only the low
  word. Preserve this per-product integer rounding in native-step controls;
  a whole-vector high-precision replacement will not be bit-identical.
- $68306/$68352 clamp lateral position to track boundaries plus 100 while
  the per-car $32f30 counter is active. Clear only the clamped axis fraction.
- $68376/$683b8 place a stopped car at x=350,z=0 when that counter expires;
  clear both position fractions/remainders and associated velocity history.
- $694c8 resets longitudinal position; $69568/$6956a reposition lateral
  coordinate and $694fc/$69528 select a segment. These are explicit reset
  writers, not ordinary frame rotations.
- $69b8c/$69b9e shift lateral position by 20 toward the centre under the
  surrounding condition. Determine whether this is a per-time correction or
  discrete contact response before scaling it; do not infer from ADD/SUB alone.

This audit is incomplete for indirect array writers, initialization, save/load,
pits and contacts. No live position hook is enabled until ownership, all resets
and frame rotation are handled. Fractional crossing/clamp comparisons must also
account for the rational remainder near an exact boundary.

## Fraction/remainder segment-frame rotation implemented

`FF1PositionRotate20` takes the two old six-byte axis states, native rotated
integer coordinates, and native signed Q15 sine/cosine coefficients. For each
axis it forms tail = fraction*5 + remainder in units of 1/327680 of a native
position unit. Four signed 64-bit products rotate those tails; floor once per
output axis to the tail unit, then divide by five to recover Q16 displacement
and a signed remainder. Add to the native rotated integers and commit both
axes only after both additions pass signed overflow checks. A failed rotation
leaves all twelve bytes unchanged. Zero tails reproduce the supplied native
integer results exactly; existing integer product rounding is not changed.

The extra rotation rounding is strictly less than 1/327680 position unit per
axis per crossing. This is a local bound, not a trajectory or handling error
bound; accumulated integration and native-table errors require live validation.
The helper uses 68020 long multiplication/division and is not a 68000 path.

The data-driven guest fixture checks all 1024 angles from the captured game
tables with zero, large and mixed tails, plus negative sub-unit remainders and
four overflowing updates. All 3086 cases pass on A1200. See
`manifest/step5-position-rotation-validation.json`,
`tools/build_step5_rotation_test.py` and `tools/test_step5_rotation.py`.

Next integration requirement: keep the per-car tails attached to their integer
state through shared work-buffer loads/stores, add explicit resets at every
clamp/teleport writer, and evaluate fractional segment boundary predicates.
Do not activate the accumulator before those paths and the force/velocity
conversion are complete. No live physics patch is installed by this fixture.

## Explicit reset and contact-relative ownership

The position module now supplies two 68000-safe operations. FF1PositionReset
sets one six-byte axis to a new integer and clears both fraction and remainder,
even when the integer is unchanged. FF1PositionAssign sets the native destination
integer and copies the source axis fraction/remainder. Self-assignment is valid.
Both preserve registers and alter only the destination axis.

Guest tests pass 144 cases on both A500 and A1200: same-integer resets on all
16 axes and all 64 car pairs on both axes. Each case starts with distinct
nonzero fractions/remainders and compares the entire 96-byte state, including
all unrelated cars and axes. Reports: tmp/step5/position-ownership-{a500,a1200}.

Native contact routine $68d4e uses local -6(a6) for the first car and -8(a6) for
the second. At $691c4 it places the first longitudinal coordinate from the
second plus an integer separation and segment-count offset; at $692ae it does
the reverse. Consequently copy the source longitudinal tail; do not reset it.
The v2 bridge derives the destination from the actual array pointer, checks its
range/alignment and reads the appropriate source index from this function's
locals. These callbacks cannot use the unrelated main-loop $32fbc index.

The v2 bridge patches 14 signature-qualified sites and calls the new reset
helper at previously hooked reset sites. Native-step demo states match on both
020 profiles, but both runs record ZERO resets and ZERO contact placements.
This is compatibility evidence only; native-branch coverage with seeded tails
remains outstanding. The helper tests do not establish callback mapping.

Additional initialization/reposition array writers identified (not hooked yet):
$6886e lateral (followed by relative branch to $6895e; do not blindly copy it),
$688e2 longitudinal, $68918 lateral, $68ab8 lateral zero, $68b26 longitudinal
zero, and $68c12 longitudinal restore from per-car $227ca. The last requires
audit of the save writer and persistence of its corresponding fraction, not
an automatic reset. Native cold paths may run before diagnostic installation;
production setup must cover initialization and every later reload/reset.

Next verification: force a qualifying two-car contact in $68d4e with separate
source tails, record which assignment branch runs and compare the destination
tail against the source while checking unaffected cars. Then finish the cold
writer/save-state ownership audit before enabling live fine-step positions.

## Native contact callbacks verified with nonzero fractions

`build_step5_native_contact.py` seeds only one eligible pair at a time, in each
longitudinal ordering with closing speeds, and calls the original $68d4e routine.
All 28 pairs are covered in both directions. Control and bridge use identical
integer inputs; every car has distinct fractional X/Z state and /5 remainders.
Both 020 profiles pass all 56 cases: first and second native assignment branches
each execute 28 times, exactly one contact is recorded per case, native captured
positions/speeds/longitudinal velocities match the control, and the complete
96-byte shadow matches the expected one-axis assignment. Every unrelated car
and axis is preserved. This verifies callback source/destination mapping, not
converted 20 ms collision dynamics or physical handling.

Two Fast-profile attempts timed out at initial demo entry. The corrected runner
waits in bounded intervals on the same confirmed-live debugger command, and
only reuses completed captures whose slave hash matches. Final captures for
both profiles completed and passed. The earlier fixture counter/trigger
addressing was also corrected before accepted results were collected.

A separate restore path now has a concrete owner: $663f4 copies each native
longitudinal position into $227ca after saving the segment at $663e2 into
$227da. $68c12 restores that saved longitudinal value. Pair the former with a
per-car saved fractional tail and the latter with its restore; do not clear
the fraction at $68c12. Allocation/reset/version/save-file lifecycle still
needs integration. These instructions are not hooked yet.

## Cold writers and saved-position sidecar implemented in v3 diagnostic

The native-step bridge now covers 21 signature-qualified sites. Pointer-based
callbacks cover $6886e, $688e2, $68918, $68ab8 and $68b26 without assuming the
main-loop car index. The displaced relative branch after $6886e is explicitly
replaced by a jump to its original target $6895e. Static inspection found no
external branch into a replaced instruction interior.

The $663f4 snapshot callback saves a complete six-byte longitudinal axis into
a separate 48-byte per-car sidecar. $68c12 restores its fraction and remainder
with the native restored integer. Snapshot/restore and array-writer callbacks
validate pointer range/alignment before indexing the sidecars. Total diagnostic
position storage is now 96 live + 48 saved bytes. Production storage must be
MEMF_PUBLIC with explicit initialization and epoch/load ownership.

The native writer instruction-group fixture passes 56 cases on each 020
profile: eight snapshots, eight restores after mutating the current coordinate
and tail, and 40 cold-writer resets with newly seeded nonzero tails. Whole live
and saved sidecars match a host model; native arrays match both explicit seeded
expectations and the control run. Unrelated car/axis state remains unchanged.
The fixture redirects the continuation after each tested instruction group;
it does not prove full menu, initialization or load transition correctness.
See manifest/step5-native-position-writers-validation.json.

An earlier fixture used a word write to initialize a long address index, leaving
stale upper bits and failing to seed the native integer arrays. Those captures
failed validation and are not accepted. The corrected fixture initializes the
whole index and the verifier now checks the explicit expected native arrays.
Both profiles were rerun with matching build hashes.

The v3 native-step demo still matches four decoded-state checkpoints on both
020 profiles, including all eight final shadow integer positions. These runs
exercise ordinary loads/stores/rotations; the directed writer fixture supplies
coverage for the cold hooks. No emulator batch remains running.

Remaining before a complete live position conversion: fractional crossing and
clamp predicates, rate/discrete classification of the $69b8c/$69b9e centreward
correction, native-step/coarse-step entry ownership, and production epoch/load
integration. Non-position forces, velocity/history, filters, heading and events
still require conversion; this bridge is not an accepted 20 ms integrator.

## Continuous fractional boundary and clamp predicates

FF1PositionCrossed020 evaluates X*S/C + Z >= 512 without division or intermediate
rounding, including both Q16 coordinates and signed /5 remainders. S/C are the
native sin(angle,1000)/cos(angle,1000) integer coefficients. With Q16 integers
Xq/Zq and remainder Rx/Rz, compare the signed 64-bit quantity
`5*(Xq*S + (Zq-512*65536)*C) + Rx*S + Rz*C` against zero, reversing the
comparison for C<0. The implementation avoids overflowing Zq-512*65536 by
subtracting its separate product in 64 bits. C=0 returns an explicit error.
No coordinate state is modified. Full signed coordinate/coefficient products
fit the 64-bit accumulator.

The original native predicate first truncates integer X*S/C toward zero, then
adds integer Z. The converted continuous predicate intentionally omits that
rounding; it must NOT replace the native-step control predicate. At zero tails
the discarded native quotient fraction has magnitude less than one native
longitudinal unit. With nonzero tails, the continuous predicate also includes
the intended fractional X and Z contributions; the less-than-one-unit statement
is not a general bound on full trajectory or integer-only/fractional differences.

A1200 passes 2661 guest cases: three near-boundary tail-unit positions for each
of 836 demo track angles, full signed coordinate/coefficient limits, zero cosine
errors, negative cosine direction and exact-plane remainder signs. Demo angles
range -29..35; the minimum native crossing cosine is 977 and max |S/C| is
0.21801433. These track observations are not universal geometry assumptions.

FF1PositionClampLower/Upper are 68000-safe full-axis comparisons with an integer
bound. They clear the fraction/remainder only when clamping, including a zero
integer/fraction with a negative remainder below a lower bound of zero. Both
A500 and A1200 pass 234 cases spanning lower/upper bounds, signed extremes,
fraction endpoints and signed remainders. They return whether state changed.
Report: manifest/step5-position-boundaries-validation.json.

Next: wire these into a position-only VERIFY path. Replace displacement and its
longitudinal clamp together, preserve the segment angle local needed by native
rotation, route converted crossings through the continuous predicate, and apply
fractional lateral bounds only under their native eligibility condition. Keep
the native-step control unchanged. The centred lateral correction at $69b8c/
$69b9e still needs rate-versus-event classification. Force/velocity/heading/filter
conversions remain mandatory before calling the result 20 ms gameplay.

## Live position-only fine-step diagnostic

`step5_fine_position.s` and `build_step5_position_fine.py` add a VERIFY-only
mode 8 to the equal-layout control/native-bridge/fine family. Each car's native
word displacement is converted through FF1Position20 on a temporary 12-byte
pair; commit only after both axes succeed and the fractional longitudinal lower
clamp has run. Record car, input velocities, both old axes, both new axes and
clamp result for every update. No failed axis update partially changes live
position state. A diagnostic fault halts explicitly instead of dropping motion.

The patched crossing path retains the native segment-angle local, obtains the
original sin/cos(angle,1000) coefficients and uses the continuous predicate.
After a native segment transition, it checks again before leaving the crossing
phase, allowing multiple crossings with a diagnostic limit of 64 per car.
This limit is a fault guard, not an accepted production stepping bound. Pending
crossing/count state resets at each per-car load. Existing native per-segment
logic remains between crossings. Lateral fractional clamps execute only while
the native $32f30 recovery counter is positive. Native off-road predicates and
the $69b8c/$69b9e correction still need converted-path review.

Both 020 profiles pass 800 live integration records, exactly 100 per car,
against a host exact-arithmetic model of velocity/5 with carried remainder and
longitudinal clamping. All final shadow integer positions match native arrays
and all remainders are within -4..4. Nonzero fractions and segment rotations
are exercised; counters and per-profile details are recorded in
manifest/step5-position-fine-validation.json. Control/native-bridge captures
still match decoded native states at all four checkpoints.

THIS IS POSITION-ONLY: other physics and clocks still execute unchanged native
updates, and no 20 ms scheduler is active. Trajectories therefore differ and
this is not a correct-speed game, a handling result or a 50 Hz capacity claim.
The 800-record diagnostic stops on overflow of its trace buffer; it is not a
playable release. No ordinary slave change is made.

Next integrated conversions: heading/steering increments and their persistent
remainders, force/velocity history and derivatives, retention filters, wear/RNG
cadence and collision/recovery timing. Then compose with the elapsed-time source
and historical input before accepting either CPU-specific interval.

## Heading conversion and native writer ownership

`src/FerrariFormulaOne_Heading.s` supplies a Q12 angular axis with a signed
/5 remainder. Each car owns relative and world axes (12 bytes per car).
`FF1Heading20` scales integrated steering/spin increments through Step20Delta,
preserving native 32-bit angular wrap. A 2^32 wrap is an integer multiple of
the native 2^22-unit revolution. Increment-plus-remainder overflow rejects the
operation without changing state. Do not apply this scaling to a controller
input, filter retention or derivative.

`FF1HeadingZeroRelative` subtracts relative angle AND remainder from world
angle, normalizes a remainder difference outside -4..4 into a +/-1 Q12 carry,
and clears relative state. `Reset` clears the destination remainder;
`Assign` copies a source remainder with a new integer Q12 frame offset.
The ownership operations are 68000-safe; fine increment scaling is 68020+.
Unit tests pass 267 ownership/normalization cases on A500 and 312 total cases
on A1200, including 45 fine increment/wrap/overflow cases. Reports are
`tmp/step5/heading-scale-{a500,a1200}/result.json`.

The VERIFY-only heading+position diagnostic owns 13 heading sites:
- `$67280/$6860e`: synchronize working angles and per-car shadow integers.
- `$678de/$67900/$67948/$67976`: scale integrated increments.
- `$67320/$683ac`: coupled relative-zero/world-subtraction groups.
- `$69590/$695e8`: recovery resets.
- `$68a5e/$68c24`: cold relative resets.
- `$68d0e`: relative-to-world assignment with track offset.

`$67be8` changes relative angle by an integer Q12 frame offset, retaining its
remainder. All hooks qualify displaced words before installation. A static
branch-interior check found that the original proposed `$68d14` hook would
consume the `$68d16` target of `$68cec`; it was moved to `$68d0e` with an
8-byte displaced group and the original target remains intact. All accepted
captures were rebuilt/rerun after this correction; runner and analyzer require
matching slave hashes. The static scan covers direct branches/calls in the
captured disassembly, not arbitrary computed targets.

Both 020 profiles pass the corrected automatic-demo comparison: native control
and native bridge match at loops 125/150/175/225; each fine run records 800 exact
position integrations and 1600 exact heading increments (100 per car per axis),
127 position frame rotations, matching final native/shadow integers and valid
remainders. Report: `manifest/step5-heading-fine-validation.json`. No reset,
assignment or coupled-zero callback occurred naturally in this demo window.

Seeded full native `$69496` recovery calls pass for all eight cars on both
020 profiles. Both angle remainders clear only for the destination car, all
other shadow bytes remain unchanged, and native heading arrays/working fields
match the control and explicit fixture expectations. Each run executes 16
heading resets. Report: `manifest/step5-native-heading-reset-validation.json`.

These are arithmetic/ownership diagnostics, not a scheduled 20 ms simulation.
Forces, velocity/history, filters, events and clocks remain unconverted. Neither
capacity nor handling is accepted. Storage belongs in MEMF_PUBLIC; custom-chip
DMA/blitter buffers remain MEMF_CHIP. No ordinary slave change is enabled.

Targeted native instruction-group tests now pass 40 cases on each 020 profile:
eight cars times the two coupled-zero groups, two cold relative resets and
relative-to-world assignment. Every case begins with distinct nonzero signed
remainders; complete 96-byte shadow, 64-byte native heading arrays and both
working angles match independent expectations. Coupled zeroes normalize
world-minus-relative tails with the expected +/-1 Q12 carry; cold resets clear
only the target relative tail; world assignment copies its relative tail.
Per run: 16 coupled zeroes, 16 resets, eight assignments. The fixture redirects
continuations after the original instruction groups; full modal transitions
are not covered. Report: manifest/step5-native-heading-writers-validation.json.
All heading demo, recovery and writer batches have finished.

## Velocity writer audit and fractional primitives

Native velocity is displacement per 100 ms, not displacement per the selected
physics tick. Keep that unit when changing the interval; scale position
integration separately. The native per-car arrays are X `$6f13c` and Z `$6f14c`.
The main loop loads them at `$671d2/$671e6` and stores `$32f94/$32f96` at
`$68592/$685a6`.

Inspected writers that require explicit ownership before enabling fine history:
- `$67bc6/$67bcc`: segment-frame rotation. Rotate both current and previous
  fractional vectors in the same frame, without treating it as acceleration.
- `$68380/$68386`: clear both working components.
- `$68990/$689a0`: cold zero array components; `$68b98/$68baa`: cold X=0/Z=200.
- `$6916a/$6917a`: exchange two cars' longitudinal velocity, saving the first
  in D4. Transfer full fractional components, not only native words. This is a
  contact discontinuity, not a continuous force to multiply by five.
- `$6993a/$6998e/$69a0a/$69a5e`: off-road working velocity response.
- `$69b36/$69b50`: explicit longitudinal clamps to 10/100 after speed clamps.
- `$6dc72/$6dc90`: new projected heading/speed velocity; the old words have
  already been saved to locals -14/-16 at `$6dc42/$6dc4a`.
- `$6e258/$6e266`: add transformed tyre-limited response to those old vectors.
  `$6e29e/$6e2a4` stop both components when returned speed falls below four.
- `$6e2d2/$6e2ec`: alternate direct projection helper `$6e2ba`.
- `$6e95e/$6e968`: whole-field initialization clears both arrays for eight cars.
- `$6ee00/$6ee16`: add/subtract a lateral collision impulse to two array entries.
  The impulse is `2*argument + 20` in native integer units; retain the existing
  fractional tail when adding an integer impulse, with explicit history policy.

`$6dc38` first constructs a target velocity, rotates target-minus-old velocity
into car coordinates, then passes its magnitude through tyre response `$6cd00`.
It later rotates that limited response back and adds it to OLD velocity. Thus
multiplying the difference by five alone is incorrect: the limited continuous
response must subsequently integrate over 20 ms, with independent remainder.
Tyre wear branches also consume the normalized magnitude and need elapsed-rate
scaling. Projection, response, speed and wear conversions are still outstanding.

`src/FerrariFormulaOne_Velocity.s` now provides:
- `FF1VelocityDerivative20`: Q16 vector output `5*(new-old)`, transactional across
  both components, with output permitted to alias either input. Signed overflow
  leaves all output bytes unchanged. 68000-safe arithmetic; this entry represents
  a 20 ms derivative and does not select a 68000 interval.
- `FF1VelocityRotate020`: full Q16 vector rotation using native Q15 coefficients,
  signed 64-bit products, one floor per output component, checked signed range,
  and all-or-nothing commit. Added local rounding is <1/65536 native velocity
  unit per component; coefficient quantization and accumulated trajectory error
  are excluded. Unlike the position tail helper, this rotates the whole vector;
  it is not intended as a bit-exact replacement for native word trig rounding.
- `FF1VelocityReset`: integer X/Z reset that clears both fractional components,
  including same-integer resets; 68000-safe.

The corrected 68020 guest fixture passes 3967 cases: 726 derivative cases with
separate/old/new output aliasing and both-axis failure coverage, 3216 rotation
cases covering all 1024 native angles plus coefficient/extreme-vector cases,
and 25 integer resets. The initial fixture had an output-sentinel typo (132
rollback checks differed by one in the unchanged sentinel); corrected and
rerun with a different binary hash. All math results passed after correction.
Report: `tmp/step5/velocity-scale-a1200/result.json`.

These routines are not hooked into live gameplay. Required next work includes
fractional target projection, velocity/history lifecycle for the writers above,
continuous force/response integration, and full fine simulation validation.

The A500 also passes 751 derivative/reset cases, confirming the documented
68000-safe operations; this does not validate a coarse physics interval.
The first A500 fixture build had an incorrect loop count and was stopped;
the corrected build passed with a matching capture hash. Consolidated report:
`manifest/step5-velocity-primitives-validation.json`. All velocity guest tests
are finished. Ordinary WHD source remains byte-identical.

## Fractional projection and continuous response

`FF1VelocityProject020` projects Q16 speed through supplied native Q15 sine and
cosine, preserving Q16 output and flooring once per component. The eight output
bytes commit together; signed overflow leaves them untouched. Coefficients are
still native-quantized; this does not implement interpolation of fractional
heading or validate its effect on tyre-response jitter. Guest coverage now adds
5123 projection cases (five speeds at every native angle plus -32768 coefficient
overflow cases). The complete primitive suite passes 9090 cases on A1200;
751 safe derivative/reset cases also pass on A500 with the current module.

`FF1VelocityApply20` integrates continuous Q16 response into the current Q16
vector, retaining separate signed /5 remainders in -4..4. Both vector components
and both remainders commit atomically; failure rolls back all twelve bytes.
Response may alias the input vector. Five equal successful responses sum exactly
to one native-reference response, with reversals carrying through zero. It must
not be used to reduce collision impulses. Callers still need to transform or
transfer the remainders at frame changes/contacts and clear them at true resets.
The 56 guest response cases pass, covering equal-response sequences, reversal,
either-axis overflow (including response-plus-remainder), aliasing and full-state
rollback. Report: `tmp/step5/velocity-apply-a1200/result.json`.

These helpers remain diagnostic building blocks. Full target projection and
limited tyre-response hooks, speed state, impulse/history ownership and elapsed
wear are not yet integrated. No updated game speed or performance is claimed.

`FF1Position20Q16` now accepts the full Q16 velocity directly, retaining the
existing signed /5 position remainder and overflow rollback. The original
`FF1Position20` word entry converts its input and falls through to the same
implementation. On A1200, all 49 original position cases and 53 fractional-input
cases pass after the final rebuild. Fractional cases cover five-step accumulation,
reversals, response-plus-remainder overflow and position-add overflow. Report:
`manifest/step5-position-q16-validation.json`. The live fine-position diagnostic
still calls the original word entry until the velocity hooks own fractional state;
its earlier captures refer to the earlier build and are not rerun/current live
validation of this new entry. All current emulator tests have finished.

## Native velocity diagnostic in the automatic demo

`build_step5_velocity_bridge.py` installs six signature-qualified observation
sites in a separate VERIFY build: `$671e6` load, `$685a6` store, `$67bcc` completed
frame rotation, `$6dc96` completed projection, `$6dd44` raw body-space magnitude,
and `$6e2ae` completed tyre response. Displaced instructions execute before each
callback; registers and resulting CCR are restored. The builder checks known
direct branches/calls for entry into displaced instruction interiors. Native
velocity and game state are not changed by these callbacks.

A 64-byte shadow follows the native word velocity in Q16 form. This diagnostic
resets its fractional parts when synchronizing; it is observation scaffolding,
NOT the eventual fractional history ownership implementation. The latter must
retain/rotate response remainders and cover the cold/contact/off-road writers
listed above. Eight hundred bounded records retain native old/target/final
velocity, raw and limited body-space changes, speed and Q16 projected target.
The record limit faults explicitly; this is not a playable unlimited build.

Both 020 profiles pass all four native game-state comparisons at completed loops
125, 150, 175 and 225. Each records 800 complete tyre-response calls, 100 per car;
all projected Q16 values, native word projections, raw body transformations,
bounded square roots, transformed limited response and final speed clamps agree
with independent arithmetic. Final shadow matches all native velocity arrays.
There are 570 segment rotations on stock 020 and 565 with Fast memory. Projection
has fractional output in 1558/1600 and 1561/1600 components respectively.
Maximum observed native component delta and raw body component are both 38;
maximum limited body component is 26. These are observed demo ranges, not global
bounds and not validation of multiplying native ticks' differences by five.

Report: `manifest/step5-velocity-bridge-validation.json`. Captures require current
slave hashes. Startup uses warp; recorded native comparisons use matched loops.
The later one-field cache census can advance gameplay, so printed end-state
values after that census are not the comparison checkpoints. All four runs are
finished. This provides integration evidence for hooks and projection arithmetic,
not adapted force/velocity cadence, fractional ownership or performance.


## Rotate the complete velocity and response carry

`FF1VelocityRotateCarry020` rotates the physical quantity `5*Q16_velocity +
remainder` for both axes, using signed 64-bit products and sums. It floors once
after the Q15 transform, then performs signed 64/32 division by five to recover
Q16 velocity and normalized signed remainders. The full twelve bytes commit
atomically, including when only the second axis overflows. The vector and
remainder buffers must be disjoint. Registers other than D1/CCR are preserved.
The local added rounding is less than 1/(5*65536) native velocity unit per
component, excluding native coefficient quantization and accumulated error.

The 68020 guest passes 3216 independently modeled cases: three seeded vectors
at each of 1024 native angles, plus coefficient/extreme-vector combinations.
Cases include mixed-sign remainders, sub-Q16 motion, negative values, and
whole-state rollback on range overflow. Report:
`manifest/step5-velocity-carry-validation.json`.

This closes the arithmetic gap between `FF1VelocityApply20` and frame rotation.
The live velocity observer still follows native words and does not call this
routine or own persistent fractional state. Its prior capture hashes refer to
the earlier module/build. Next integration must preserve per-car vector/carry
state at loads/stores, use complete rotation in the fine path, explicitly
transfer contact components and clear true reset/clamp state. Fractional target
projection, body-response quantization and force/speed/wear conversion remain
open. The current guest batch has finished; ordinary release is unchanged.

## Velocity ownership bridge: cold resets and contact exchange

The new diagnostic `build_step5_velocity_ownership.py` extends the observation
bridge with 12 bytes per car: X Q16 at +0, Z Q16 at +4, X remainder at +8,
Z remainder at +10. Six explicit cold writer hooks clear the destination axis's
fraction and remainder: `$68990/$68b98/$6e95e` for X=0,
`$689a0/$6e968` for Z=0, and `$68baa` for Z=200. Callbacks run before displaced
instructions where those instructions overwrite the destination address register.
The native word writer still executes with original registers/CCR.

The `$6917a` contact hook exchanges full longitudinal Q16 values AND their
remainders between the two affected cars. It derives the first word index from
D3 and the second from the native destination pointer, validates aligned array
indices, and preserves lateral state. It runs before the second native word
store; the first native store has already occurred but the independent fractional
state still holds both pre-exchange values. Same-car exchange is harmless.

Both 020 automatic-demo comparisons pass: four matched state checkpoints,
800 valid arithmetic records per profile and unchanged native velocity shadow.
Neither cold writes nor contact exchange occurred in this window, so this is
compatibility coverage only. Native seeded contact coverage is being recorded
separately; cold writer instruction groups and all other velocity writers remain
outstanding. Report: `manifest/step5-velocity-ownership-validation.json`.
The main-loop sync still follows native words; full fractional simulation is not
activated by this diagnostic.

The full native `$68d4e` contact fixture now passes 56 seeded cases on EACH
020 profile, covering all 28 distinct car pairs in both approach directions.
Native positions, speeds and longitudinal velocities match the control; all
96 bytes of fractional state match an independent component-exchange model.
Distinct nonzero fractions and signed remainders transfer only for the two
longitudinal components, and every call executes exactly one exchange hook.
The control's entire seed state is checked independently, preventing agreement
between accidentally mis-seeded builds from passing. Report:
`manifest/step5-native-velocity-contact-validation.json`.
Cold writer seeded coverage, off-road and working resets/impulses, plus full
fine-step collision behavior remain outstanding. All eight ownership-demo and
contact captures have finished; no batch remains running.


## Seeded cold velocity writer coverage

All six cold velocity hooks pass seeded native instruction-group coverage on
both 020 profiles: 40 cases per profile (five groups for each of eight cars),
48 executed hooks because the whole-field initialization group clears both
axes. Native arrays match explicit expected values and control; all 96 bytes
of sidecar state match the reset model. Fractions and remainders are nonzero
at entry. X resets write zero over an existing integer zero; the Z=200 writer
also retains its existing integer. Both still clear the target fraction and
remainder. Unrelated cars and axes remain unchanged.

The `$6e95e` group runs through the adjacent `$6e968` hook before returning,
so the fixture does not overwrite that second hook with an early return.
Continuations are redirected after native instruction groups; this is not
whole modal/initialization flow coverage. Report:
`manifest/step5-native-velocity-writers-validation.json`.
All four current captures have finished; ordinary release is unchanged.

Further off-road audit: callers `$68446/$684d4` pass side and penetration beyond
the corresponding track width to `$6988c`. `$69938/$69a08` add/subtract the signed
lookup `$2aaa6` to lateral velocity on qualifying updates. The longitudinal
changes at `$6998e` and `$69a5e` subtract penetration
/ `$2aaae`, also reducing speed in the preceding paired branch when speed >10.
These are repeated per-update response terms, not the cold resets above; they
require elapsed-step scaling and carries. Do not infer a once-only collision
impulse from the helper's use near a boundary. Its eligibility, clamp and RNG
branches remain part of the conversion audit.

## Working velocity ownership hooks

`build_step5_velocity_ownership_v2.py` adds seven qualified sites:
- `$68386/$6e2a4`: after both working components have been cleared, reset both
  Q16 components and both response remainders for the current car.
- `$6e2ec`: native alternate direct-projection replacement; synchronize its
  integer vector and clear old fractions/remainders in the native bridge.
  The fine path must instead preserve its fractional projected result.
- `$69b36/$69b50`: longitudinal clamps; clear Z fraction/remainder only.
- `$6ee00/$6ee16`: lateral collision writes; retain X fraction/remainder and
  replace only its native integer word. Preserve Z and all other cars.

The impulse callback executes before displaced instructions overwrite D1 and
uses the native destination array address, not `$32fbc`. It retains the native
word result and is not a checked arbitrary-range Q16 impulse integrator; the
fine production path still needs explicit range policy at signed boundaries.

Both 020 native demos remain exact at the four recorded checkpoints, with 800
valid velocity records and matching sidecar integers. These new callbacks do
not occur in the demo window; seeded native instruction-group coverage is being
recorded separately. Report: manifest/step5-velocity-ownership-v2-validation.json.

Next fine-velocity integration sequence: retain per-car current Q16 vector and
response carries at loop load/store; save that complete old vector at tyre entry;
project a fractional target; normalize and rotate target-minus-old into body
space before the native tyre curve; rotate its continuous response back and
apply through FF1VelocityApply20; use FF1Position20Q16 for displacement and
FF1VelocityRotateCarry020 at segment crossings. The intermediate body-space
word quantization, speed magnitude, fractional heading coefficient selection,
wear rates and off-road changes need explicit treatment. Existing native control
runs must remain available alongside this bounded diagnostic. Do not enable a
production scheduler while these quantities still use mixed time units.

The seeded native working-writer fixture now passes 56 cases per 020 profile,
seven groups for each car: two full clears, alternate direct projection, two
longitudinal clamps and both lateral impulse writers. All 96 sidecar bytes,
native arrays and working vector match independent expectations. Each run
executes 24 full replacements, 16 clamps and 16 impulse hooks. Impulses retain
fraction and signed carry; clamps preserve the lateral component; replacements
clear both carries. Continuations are redirected after the instruction groups,
so complete event/modal flow and arbitrary signed-range impulse handling are
not covered. Report: manifest/step5-native-velocity-working-validation.json.
All eight v2 demo and working-writer captures finished. Ordinary source unchanged.

## Parallel fractional velocity calculation chain

`build_step5_velocity_pipeline.py` runs the fractional arithmetic alongside the
native tyre routine using 80-byte bounded records. It copies the per-car old
vector/carries, projects the target in Q16, computes `5*(target-old)`, and rotates
that normalized change to car coordinates. At native return it rotates the
NATIVE limited body response back to track coordinates in Q16 and applies it
over 20 ms to a private copy of the old state, retaining /5 carries.

The normalized change does NOT feed the native tyre curve in this diagnostic,
and the trial vector/carries are NOT committed to gameplay. The curve still
uses its original native change. These are deliberately separate recorded
values; do not describe the trial as a fully converted tyre-response result.
The native inputs also advance at native cadence. No 20 ms timing, handling or
capacity claim follows from this check.

This joins the projection, derivative, coordinate-transform and response
integration helpers with real call-site data, exposing arithmetic/interface
errors before activation. Independent analysis checks every intermediate Q16
value and trial carry, as well as the original native computations and the
matched native state checkpoints. Both 020 profiles pass all 800 records and the four native state checkpoints.
Report: `manifest/step5-velocity-pipeline-validation.json`. All four captures
have finished.


## Persistent fractional velocity diagnostic (not physics acceptance)

`build_step5_velocity_fine.py` adds mode 8 alongside native control/observer
modes 6/7. It preserves per-car Q16 velocity and response carries, commits the
integrated result, uses complete velocity/carry frame rotation, and makes the
normalized body change drive the native tyre routine. The derivative includes
the old carry: `5*(targetQ16-oldQ16)-oldRemainder`. Load/store checks fault on
unowned integer changes rather than silently discarding fractional state.

The first persistent run stopped at tick 164, car 7, on a lateral mismatch:
native working X=-16, shadow integer X=-144, caused by an unconverted +128
off-road increment. Four off-road hooks now use the 20 ms response integrator
for lateral lookup increments and longitudinal penetration drag. Native observer
mode preserves tails while syncing the appropriate native WORD address (the
word-array stride differs from the Q16 vector stride). Final accepted arithmetic
captures were rebuilt after correcting that observer index.

Both 020 profiles now complete 800 committed velocity records. Independent
arithmetic checks pass for projection, carried normalized change, body/world
transforms and integrated state; native comparison modes remain exact at four
checkpoints, and final shadow integers match native arrays. Fine runs exercise
contacts, resets, clamps, impulses and off-road responses. All six final captures
finished. Report: `manifest/step5-velocity-fine-validation.json`.

CRITICAL LIMIT: this is not accepted physics. Position and heading still run at
native cadence in this standalone velocity diagnostic; speed/forces/wear/events
are not converted. Normalized body magnitudes exceed the original 1023-bounded
square-root range. At `$6e05c..$6e06e`, native component rescaling also executes
EXT.L after MULS.W, narrowing the product before division; the enlarged normalized
inputs need a wide replacement. Current arithmetic checks deliberately describe
these retained native limitations and do not approve them. Fix exact magnitude
and wide limited-component rescaling next, then reconcile low-speed stopping,
scalar speed fractions, controller timing and the combined fine position/heading
path. No timing, handling, capacity or playable 20 ms claim is made.

## Remaining slip-wear conversion sites

Inspection after the combined-motion merge identifies final, unscaled wear
subtractions. Player tyre fields are `$66c52 + 4*tyre`; opponent aggregate
condition is `$22356 + 4*car`. Scale the final decrement, after difficulty
and left/right weighting, with a remainder owned by the affected condition.
Do not divide an already-clamped before/after loss: that slows depletion
incorrectly when the native decrement exceeds the remaining condition.

Candidate interception groups (not installed or runtime-validated):
- `$6de74` and `$6defa`: multiply-by-three calls immediately before the two
  D0 player subtractions at `$6de7a` and `$6df00`. The short branches following
  those subtractions make a naive six-byte patch at SUB unsafe.
- `$6de96..$6de9a`, `$6ded4..$6ded8`: load final D1 decrement, then subtract.
- `$6df2a..$6df30`: load, double and subtract the D1 straight-line decrement.
- `$6e018`: opponent D0 decrement.
- `$6df62..$6df68` and `$6e034..$6e03a`: explicit zero-clamp groups; clear the
  relevant carry when condition reaches zero.

Cold initialization, repairs, discrete damage, rotating wear and save/reload
writers still need ownership/cadence treatment. Byte signatures and external
branch targets must be checked before any of these candidate groups is used.


## Slip wear implementation and remaining event cadence audit

`FF1Wear20Delta` now divides the nonnegative final native loss plus a
condition-owned remainder by five, before saturation at the remaining condition.
It clears the remainder on depletion and rejects negative condition/loss or a
remainder outside 0..4 atomically. The condition itself is read-only; the native
SUB performs the write. All 254 guest arithmetic cases pass on 68020, including
large unsigned numerators, exact depletion, invalid inputs and repeated tiny
loss. Report: `manifest/step5-wear-validation.json`.

The separate `step5-wear-fine` fixture adds the six final slip-loss interception
groups listed above to combined motion/steering. Initialization/repair groups
at `$64b4c`, `$687f4` and `$6c67c` clear corresponding remainder slots. Nine groups
are checked for signatures, overlap and branches into displaced instructions.
The exact-multiply pass has already changed `$6de74/$6defa` to MULS.L plus NOP;
these signatures and displaced instructions must use that installed form.
Both 020-profile captures now pass 1,100 records each, covering all six slip-loss
branches and all eleven physical conditions. Independent replay verifies loss,
carry continuity, native condition continuity and final condition/carry values.
Prior combined motion/steering checks and all four native comparison checkpoints
also pass. Report: `manifest/step5-wear-fine-validation.json`. No live reset or
depletion occurred; those integration paths remain unaccepted.

Further inspection distinguishes rotating/stochastic wear from continuous slip:
`$6d5f2` calls `$6ea3e` for the eligible player. This calls random trial helper
`$6ec94` repeatedly, advances rotating component index `$6ef52` modulo nine,
subtracts a fixed nine from `$66c42`, and makes another random trial. Gating
only the final loss would still consume RNG and rotate components five times
as quickly. The complete eligible call needs the native 100 ms pulse cadence.
Opponent eligible random failures call `$6ee70` at `$6d67e`; preserve one trial
per native pulse there as well. Call eligibility is controlled by preceding
player/opponent status checks in `$6d4f8..$6d67c`. The loss helper `$6ec94` is
also used for contact damage elsewhere, so it must not be globally gated.
These cadence hooks have not yet been installed or runtime-tested. Discrete
contact damage must retain its own event semantics and condition remainder
ownership; generic-pointer repair/save/reload writers still require coverage.


## Follow-up cadence sites after random-event gating

The eligible `$6d5f2/$6d67e` call gates are now validated on both 020 demo profiles;
see `manifest/step5-events-fine-validation.json`. Remaining adjacent rates:

- `$67172..$67174`: countdown `$66f94` decreases once
  before the eight-car loop, with zero-crossing side effects at `$6717c..$67196`.
  Gate the decrement using the native-tenth pulse; preserve the native zero
  transition and eligibility. The racing demo window does not exercise it.
- `$6734e..$6739e`: player clutch charge `$32f2e` grows toward ten when eligible,
  otherwise decrements and clamps at zero. This entire state update needs the
  pulse, while current input/continuous acceleration remains sampled at 20 ms.
  Its four accelerator calls already have scalar-rate conversion; do not gate
  all four and also divide their increments (double scaling).
- `$6712e..$67134`: phase byte `$1be42` advances modulo
  four once before the car loop. Consumers at `$6d30a/$6d322` and
  `$6daba/$6dad0` use it to suppress accelerator/drag results for certain
  `$6f272` values. It is not merely cosmetic/audio state. Preserve its native
  100 ms dwell time when converting the phase.
- `$65dca/$65dd8`: eligible native ten-byte clock calls; separate clock fixture
  passes both 020 short demo windows. Hour/calendar rollover, countdown, session cap, pause
  and clock drawing ownership need additional transition coverage.

The address ranges above are descriptions, not safe patch lengths. Validate
complete instruction groups and external branch targets before installation.


## Counter cadence implementation evidence

The three counter groups above now have pulse gates in the combined fixture:
phase `$6712e` (six bytes), countdown `$67172` (eight bytes), and clutch block
entry `$6734e` (ten bytes), with a six-byte end observer at `$673a4`. Native
condition flags are preserved across diagnostic wrappers; the skipped countdown
still sets flags from its unchanged nonzero value, preserving the following
branch and suppressing premature zero-crossing effects. Both 020 demo profiles
validate phase dwell time and legacy state comparisons. 256 controlled guest
cases per profile validate phase, countdown and clutch branches separately.
See `manifest/step5-counters-fine-validation.json` and
`manifest/step5-counter-transition-validation.json`.

## Next continuous fuel-loss interception

The inspected final fuel decrement is `$6d164` SUB.L D0,(A0), followed by
`$6d166` MOVE.L D0,-4(A6), forming a six-byte candidate group. A0 points to
`$22376 + 4*car`; D0 is the final difficulty/RPM/boost-scaled native decrement.
Scale before saturation, with per-car carry, as for slip wear. Do not globally
gate `$6d066`: it also computes acceleration and is called repeatedly for clutch.

Candidate reset groups: player setup `$64ae6` absolute MOVE.L (six bytes);
opponent initialization `$6881e` multiply plus MOVE (six bytes, ending at the
external branch target `$68824`); refuel `$6c6a2` multiply plus MOVE (six bytes);
explicit emptying `$66942` ADDA plus CLR (eight bytes); and native fuel clamp
`$6d242` ADDA plus CLR (eight bytes). Signatures/overlap/branch checks remain
required before using them. Generic save/reload ownership still needs coverage.
These fuel hooks have NOT been installed or validated.


## Fuel implementation evidence

The six fuel groups listed above are now installed in `step5-fuel-fine` and
validated by exact demo replay on both 020 profiles. Carry storage is eight
words owned per car. `$64ae6` requires an explicit `$22376` pointer inside the
saved-register callback because its displaced MOVE is absolute; other reset
groups already leave A0 at the affected fuel field. The source helper
`FF1Wear20Delta` is reused without a duplicate implementation.

`step5-fuel-transition` executes these actual hooks for 246 cases per profile,
using temporary return boundaries after the displaced groups. All pass. This
is group-level fuel writer ownership evidence, not full pit/save-load or
out-of-fuel race-transition acceptance. Reports:
`manifest/step5-fuel-fine-validation.json` and
`manifest/step5-fuel-transition-validation.json`.


## Boost/audio and next recovery ownership

`step5-boost-fine` now calls the drawing-omission version of `$6bbfc` only on
native-tenth pulses. This version already skips gauge blits at `$6bcc8` and gear
blits at `$6bf26`; the retained boost/audio head and gear-state section are
replayed independently and pass both 020 profiles. This is diagnostic cadence
validation, not an assumption that the original full function is render-free.

Remaining recovery sites inspected after this merge:
- `$682c0..$682c4`: LOAD/SUBQ/STORE six-byte group decrements the positive
  contact counter `$32f30[car]`. Keep collision inputs as events; gate elapsed
  countdown only. The zero transition at `$6836e..$683be` resets position,
  vector, scalar and heading state, so reuse/verify their existing ownership hooks.
- `$6c20c..$6c21a`: player negative status `$2268e` advances toward -1 during
  drawing. The existing `FF1AdvanceRecovery` helper has separate timer tests,
  but is not yet called by this combined fixture. Move it into simulation on
  native-tenth pulses while preserving original outer eligibility.
- `$6c5c6`: opponent recovery/refill is also embedded in drawing. Its initial
  loop (`$6c5ea..$6c7c4`) updates status, fuel and tyre condition plus projection
  lists; `$6c7c8` begins sorting/drawing work (calls `$6bf90`, later `$6a696`).
  Do not call the full routine from simulation without separating that boundary.
  Existing fuel/wear refill hooks lie inside the first loop. Preserve checks on
  `$66c7c`, `$66f94`, `$2260c[car]`, `$1c222` and the caller's `$1c21e` gate.
- Projection h170 `$69d40/$69d56` merely reads recovery status in the inspected
  section; it is not another recovery increment.
These remaining recovery changes are NOT implemented or runtime-accepted yet.
