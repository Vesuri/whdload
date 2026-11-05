# Step 5 implementation checkpoint

Current status: production integration passed in documented SPS 0481 PAL emulator
scope; see STEP5_CAPACITY.md's final closure and manifest/production-integration.json.
The authoritative source now includes the opt-in combined engines. Emulator release qualification and030/040/060 analysis also pass; human
playtesting and real Amiga hardware testing are deferred. The sections below are historical
implementation checkpoints, not the current integration status.

## Live VBL integration diagnostic

`build_step5_vbl.py` installs the tested timer at the verified native field-counter
store `$24946` (`move.w d1,$24ad2`). It preserves the displaced write and interrupt
registers/CCR, initializes before installation, disables interrupts around the
patch and calls WHDLoad FlushCache before enabling interrupts. This is still an
ignored SPS fixture, not a production loader/version integration.

All 12 runs pass: clock disabled, normal drawing, three-extra-field slow drawing
and omitted drawing, on A500/A1200/A1200+Fast. At six snapshots per run, the new
32-bit field counter agrees modulo 65536 with the native counter since install,
and its 64-bit elapsed units equal fields * 710510 exactly. All nine matched-state
comparisons against the disabled control pass. Report:
`manifest/step5-vbl-validation.json`; runner `vbl_step5.py`; comparator
`analyze_step5_vbl.py`. Whole-loop observations with native physics (not FPS gates):
A500 disabled/enabled 254.004/256.008 ms, A1200 143.428/143.829 ms, Fast
140.223/140.223 ms. These include native wait/DMA phase effects, not just hook cost.

Next fixture: `build_step5_recovery.py` plants synthetic player status -8 at loop
126. It compares original drawing, omission without recovery (negative control),
and omission retaining recovery before boost/audio work. `recovery_step5.py`
captures every loop 126–132. `analyze_step5_recovery.py` expects
the fixed path to match all semantic blocks and the broken path to disagree.
The original fixture waited beyond the native recovery exit and was stopped;
its incomplete capture is not accepted. The corrected v2 stops at loop 132,
where status reaches -1; the game then leaves driving. All three profiles match
at every recovery tick with extraction, while the negative control remains -8.
The v3 fixture uses the actual new `src/FerrariFormulaOne_Logic.s` helper and
also passes all three profiles and negative controls. Reports are versioned:
`manifest/step5-recovery-v{2,3}-validation.json`.

The same helper passes timer-driven guest tests on A500 and A1200 at 20 ms and
provisional 200 ms, both with zero and 40 ms starting clock phase. At 20 ms,
recovery reaches -1 at the seventh native-tenth pulse (700 ms, or 660 ms with the
starting phase). At provisional 200 ms the first observing update is at 800 ms;
that deadline quantization is documented, not a handling acceptance. See
`build_step5_logic_test.py`, `test_step5_logic.py`, `tmp/step5/logic-time-*`.

`STEP5_UNITS.md` records the inspected position-frame and velocity-derivative
conversion requirements. `detail_step5.py` captured the updated optimized
instruction trace successfully. It selects the v6 gauge-free slave
and explicit A1200 profile, 100 survey fields, FULL_TRACE=1; do not run alongside recovery.

## Requirement and scope

Use 20 ms physics/game-logic intervals on 68020 and 68020 + Fast. Select a separate
coarser interval for 68000 from measured adapted-update capacity. A 200 ms value
in the timer tests is provisional, not an accepted physics configuration.
030/040/060 remain deferred. Use warp for startup and the automatic no-input demo;
turn warp off for measurements. Do not call unchanged native ticks at 50 Hz.

## Implemented and tested in isolation

`src/FerrariFormulaOne_Time.s` implements PAL elapsed/consumed/pending accounting
with a monotonic 64-bit timestamp and native 100 ms clock pulse accumulation.
PAL fields are converted using 3546895/71051 fields per second, not rounded to
50 Hz. The module accepts 20 ms and provisional 200 ms intervals, refuses early
consumption, records explicitly rebased time and preserves tenth-second phase.
It installs no hooks. Pause/Resume preserves whole pending work and partial update debt, excludes only
paused wall time, and is idempotent. Rebase remains an explicit loading/new-epoch
operation; it must not be used for ordinary pause or overload handling.

`tools/build_step5_time_test.py` and `tools/test_step5_time.py` execute eight guest
unit cases on A500 and A1200: 6000 fields at each interval, limited draining,
field-counter and 64-bit low-word wrap, pause/rebase, early consume rejection,
unsupported interval rejection and preservation of context after rejection, and real pause with outstanding work.
Both profiles pass. Reports: `tmp/step5/time-{a500,a1200}/result.json`.
These tests are warped arithmetic tests, not 60-second gameplay acceptance.
A sticky-Z SUBX high-word comparison was corrected before accepted captures.

`src/FerrariFormulaOne_Math.s` contains candidate signed 32-bit division helpers.
68020 uses hardware long division; 68000 uses one or two safe word divisions for
small divisor magnitudes, otherwise a restoring loop. Native zero, sign, overflow,
register and CCR behavior is deliberately retained. CPU selection/version checks,
cache coherency and lifetime-safe installation are not integrated yet.
`tools/build_step5_div_test.py` / `tools/test_step5_div.py` provide a native oracle
covering 2960 operand pairs and all 32 input CCR combinations per implementation.
All 94,720 comparisons pass for the 68000 implementation on A500 and A1200, and
for the hardware-long implementation on A1200. Guest reports are under
`tmp/step5/div-oracle-*`. The in-game 68000 verifier additionally passes 11,302
observed calls; all four matched-loop snapshots agree with the control.

## Capacity evidence (native integrator, drawing omitted)

All accepted comparisons use the same layout and identical decoded logical state
at completed loops 125, 150, 175 and 225. Ordinary release remains frozen.

| A1200 diagnostic | Mean loop cost | Scope |
| --- | ---: | --- |
| v2/v3 control | 52.684 ms | Original division, no drawing |
| v2 hardware division | 35.056 ms | No drawing, cache off |
| v3 division + instruction cache | 29.046 ms | No drawing; CACR=1 observed |

The v2 oracle matched 11,306 actual game divisions including CCR. Its verification
overhead is not a performance result. The initial v1 control had a different code
layout because VASM changed an immediate-zero move into CLR; reject that control.
The v2 SetCACR attempt left CACR=0 and established no cache gain. v3 uses the
WHDLoad SetCPU API and the observer confirms CACR=1. Do not treat that experiment
as a completed cache/reload audit or a playable improvement.

Reports live under `tmp/step5/a1200-math-v{2,3}-*`. Builders and capture tools are
`build_step5_math.py`, `capture_step5_math.py`, `math_step5.py`. The retained v3
builder is the latest diagnostic, not a production patcher.

29 ms exceeds the entire 20 ms interval before rendering. Further capacity work
and remeasurement of the adapted integrator are required. The old rendering floor
is 5.541 FPS on 020 and 3.494 FPS on 68000. No 50 Hz capacity claim is justified.

## Additional capacity work

v4 division helpers produce 87.139 -> 67.307 ms/update on 68000 (22.8% reduction
in the whole logic-only loop), with exact matched-loop state. On 68020 the v4
cache result remains 29.046 ms; on 68020 + Fast it is 28.045 versus 52.283 ms.
All four semantic checkpoints agree for both 020 profiles. End-state values
sampled after an extra census field are not matched-loop comparisons: the faster
variant can have advanced further during that field.

`src/FerrariFormulaOne_Sqrt.s` retains the native bounded binary search but uses
a 1024-entry square table on 68020. All D0-D3 outputs (including upper words) and
CCR match in 114,688 native-oracle comparisons, spanning all bounded perfect
squares and neighbors, random full-width values and all input CCR combinations.
See `build_step5_sqrt_test.py`, `test_step5_sqrt.py` and the guest report.

The v5 diagnostic additionally identifies 26 multiply calls followed by an
instruction sequence that overwrites all five CCR bits before use. These can use
inline MULS.L plus NOP while preserving product modulo 2^32 and other registers.
Do not replace the entire native multiply routine: its returned flags differ.
94,720 product/register oracle comparisons pass. The audited sites/signatures
are saved in `tmp/build/step5-math-v5/inline-sites.json`; the builder validates
all site signatures before writing the inline patches. A1200 v5 measurements at matched layout: division+cache control 29.247 ms,
square-root 29.046 ms (0.68% saving), multiply 27.844 ms (4.79%), combined
27.644 ms (5.48%). All four semantic checkpoints match for every comparison.
The square table has a small isolated return; retain it as an experiment, not
an accepted production optimization. Neither candidate is installed by the
normal slave. `manifest/step5-math-measurements.json` and
`tools/analyze_step5_math.py` retain the comparisons. Do not compare v5's seed/
layout directly with an earlier layout to attribute small differences.

## Newly found drawing ownership issue

Race drawing at $6c20c..$6c21a increments player recovery status $2268e toward -1
when it is below -1. This is simulation state and must be moved to elapsed-time
logic, alongside retained boost/audio work at $6bbfc. The previous omission
captures did not exercise prolonged negative recovery. Their recorded traffic/
contact matches remain valid for their scope, but do not establish full drawing
independence. Add a prolonged recovery fixture before accepting extraction.

## Outstanding gates

- CPU/version-qualified default-off CUSTOM2 integration; preserve CUSTOM1 legacy.
- VBL time hook, tick-owned historical inputs, explicit modal entry/exit handling.
- Quantity-by-quantity time conversion: engine acceleration/braking, heading,
  coordinates and fractional carries, tyre/slip derivatives and filters, wear,
  rotating events, boost/audio state, recovery timers and native clocks.
- Exact-output capacity improvements and measured capacity for each adapted path.
- Independent safe presentation with all blitter/DMA ownership retained.
- Native-step controls, elapsed-time fixtures, slow drawing, 60-second bounded
  debt/error tests, contacts, controls, pits/tow/season/save transitions.
- Human handling acceptance and physical input delivery remain unvalidated.

Do not call step 5 complete on the strength of the isolated modules or omission
benchmarks. See PERFORMANCE_PLAN.md step 5 for the full acceptance contract.

## Residual gauge drawing and Fast code experiment

The earlier "logic-only" omission retained all of `$6bbfc`, including its gauge
blits. v6 keeps its boost/audio head and gear-animation state, but skips
`$6bcc8..$6be6a` gauge preparation/drawing and `$6bf26..$6bf60` final gauge draw.
It preserves full function stack setup/epilogue. All semantic checkpoints match,
including newly added `$6bf84/$6bf86` gear-animation state. A1200 control/lean:
27.444/24.439 ms; Fast control/lean: 26.242/23.437 ms (about 11% savings).
These remain native-integrator benchmarks, not adapted-physics capacity gates.

`build_step5_fastcode.py` prepares a separate Fast-only diagnostic: copy race
hunks 167 and 203 into a confirmed MEMF_FAST allocation, preserving low PC cache
index bits, keep every data reference at its original address, and redirect 21
verified C entry points. The inspected hunks have no PC-relative data operands
or relative branches leaving their own copied region. Control allocates/copies
identically but does not redirect calls. This is a fixed-layout capture-only
experiment, not lifetime-safe production relocation. The first Exec AllocMem(MEMF_FAST) attempt returned zero: the guest KickEmu OS
has no exposed Fast-memory allocation pool. This attempt is rejected as a
capacity comparison. v2 instead requests 20 KiB extra in the slave ws_ExpMem
(0x40000 -> 0x45000), uses the space after the emulated Kickstart image, and
checks it is inside the explicit 4 MiB Fast profile's physical address range.
Both arms have identical reservation/copy work. It does not claim guest
TypeOfMem verification; the measured buffer starts at 0x5ec000.

v2 succeeds: 23.638 -> 18.830 ms per native loop (20.34% reduction), with exact
semantic state at all four checkpoints and all 21 redirects installed only in
the fast arm. Report: `manifest/step5-fastcode-validation.json`. Ordinary slave
source/release remains unchanged; production memory-profile gating, reload and
fallback still require implementation.

## Latest optimized profile / next capacity work

`tmp/step5/optimized-detail-v6/detail.bin` and `profile_step5_optimized.py` now
provide 25 complete stock-020 loops, averaging 349,999 cycles. The group report
is `manifest/step5-optimized-costs.json`. Largest groups per loop: car body
59,062 cycles, AI/contact 39,814, other main-loop work 35,517, engine forces
32,784, velocity/slip/tyres 30,640, fast division 29,804, other physics 26,724,
remaining software multiply 25,755, drag/RPM/gear 25,476, sin/cos 16,910.
This is measured after arithmetic and gauge extraction, not the old profile.

A concrete remaining hotspot is `$6977a`: in normal track mode (`$1ed8a=0`),
it sums ten read-only curvature words starting at input segment+2 with native
wrap and returns absolute sum. The demo track has 836 segments. Its only observed
static caller is `$67514`, which consumes D0 then overwrites scratch registers.
The other mode has a different eight-pair rule and speed>350 lookahead offset;
do not apply a normal-mode-only table there. A per-track precomputed normal-mode
table could remove the repeated loop; it must be rebuilt at track initialization,
retain unsupported-mode fallback, and be compared to native results at every
segment before being accepted. No table optimization has been implemented yet.

The updated input audit confirms `$227f8` is a function, not a raw-key global.
It maps the keyboard.device event consumed by `$23696` through GetMsg/SendIO.
The InputEvent buffer pointer is `$2379a`; its code word is +6 and it is cleared
before reposting the request. Preserve event timestamps and one-shot behavior;
calling this once per catch-up tick with today's input is not historical input.
Mouse position is updated in VBL; native buttons are sampled separately from
CIA/POT at `$24a1a`. Both paths still need scheduler-owned history.

## Normal-mode lookahead and continuous-step primitive

`src/FerrariFormulaOne_Track.s` uses a register accumulator and advancing table
pointer for the ten-sample normal-mode lookahead. This replaced the proposed
precomputed table: it avoids track-cache lifetime/invalidation entirely. The
helper's domain is 12 <= segment count <= 32767 and a valid nonnegative segment.
The diagnostic wrapper retains a copied native routine for alternate mode or
out-of-domain inputs. It promises the C caller's value contract, not incidental
native scratch-register/stack writes. The inspected caller drops the argument,
uses D0, then overwrites the relevant scratch values/flags.

The fixture compares every one of 836 demo-track segments against native before
patching at update 126. Both 020 profiles pass the oracle and four full semantic
checkpoints. Stock control/fast: 24.439/23.838 ms; Fast profile without code
relocation: 23.437/22.836 ms. Roughly 0.601 ms is saved (2.46–2.56%). The helper
is small and avoids added per-track storage/lifetime rules; it remains a candidate
until production integration. Report: `manifest/step5-lookahead-validation.json`;
builder/runner: `build_step5_lookahead.py`, `lookahead_step5.py`.

`src/FerrariFormulaOne_Step.s` adds signed 1/5 increment scaling with a separate
-4..4 remainder per quantity, and provisional ×2 coarse scaling. It explicitly
rejects signed overflow without modifying the input or stored remainder.
`build_step5_step_test.py` / `test_step5_step.py` pass 56 fine/fixed-point/reversal/
overflow cases on A1200 and 11 coarse/overflow cases on A500. These primitives
are not yet hooked into car state and do not convert filters/derivatives/events.

The next integrator component is position: add scaled displacement with persistent
fractions for each car/axis, preserve native-step controls, then transform those
fractions through the native segment-frame rotation. A native step with zero
fractions must preserve original integer behavior. Existing integer rotations
round individual products; retain that native control behavior and explicitly
bound additional fine-step rounding. Separate the integrated fractional position
from the scale helper's sub-unit rational remainder, transform both at a frame
change, and audit clamp/contact/pit/reset writers. Do not enable a position-only
prototype as completed fixed-step physics; force, velocity-history/derivative,
heading, filters and event conversions remain outstanding.

## Public/Fast memory policy (user requirement)

All code and data that can safely live outside chip RAM must prefer public Fast
memory when it is available. This includes cold code, resident and overlay code,
lookup tables, persistent game state, stacks and CPU work buffers, not just the
two hot code hunks already measured. Use MEMF_PUBLIC for eligible allocations,
letting the allocator prefer available Fast memory and naturally fall back on
no-Fast machines. Do not require MEMF_FAST or a separate Fast-first allocation
scheme. Handle allocation failure cleanly. Keep custom-chip DMA and
blitter buffers in chip memory, including blitter source data. Mixed blocks need
an ownership/reference audit and separation before moving their CPU-only parts.

The existing two-hunk diagnostic (19,624 bytes copied into a 20 KiB reservation)
retains original data addresses and original code storage. It is not the intended
final memory layout. Full integration requires loader relocation, pointer and
cache repair, overlay unload/reload handling, allocation-failure fallback and
actual placement checks. The guest Exec allocation experiment did not expose
the configured Fast pool, so production integration must resolve WHDLoad/KickEmu
ownership so the allocator can use the configured memory. MEMF_PUBLIC is the
selected allocation policy; recorded addresses validate the resulting placement.
The broader placement requirement remains open; no production code is changed
by recording this policy.

## Fractional position accumulator

The new candidate `src/FerrariFormulaOne_Position.s` implements atomic 20 ms
position accumulation with Q16 coordinates and per-axis /5 carry. The A1200
guest fixture passes 49 movement, reversal and overflow cases. This advances
the continuous-position conversion but is not hooked into the car integrator.
The writer audit in STEP5_UNITS.md now identifies shared/per-car transfers,
segment rotation, boundary clamps and explicit reposition/reset sites. Next:
implement and validate fraction/remainder frame rotation, then cover indirect
writers and integrate the position path alongside force/velocity conversion.
No emulator batch remains running after these tests. Step 5 remains incomplete.

## Fractional rotation validation

The 68020 position module now rotates both Q16 fractions and their /5
remainders across a track-segment frame change while retaining native integer
rotation results. All 3086 isolated guest cases pass, covering every native
angle, zero-tail compatibility, signed tails and atomic overflow rollback.
The accumulator and rotation are ready for per-car integration, but no live
position hook is enabled: indirect writers, resets and fractional boundary
predicates remain outstanding along with the other physics conversions.
The emulator fixture has finished; no batch is running.

## Native-step live per-car position bridge

A qualified diagnostic now hooks twelve exact SPS instruction sites for shared
work-state loads/stores, native displacement commits, segment rotation and known
axis resets. It owns separate six-byte X/Z states for all eight cars (96 bytes).
Every trampoline executes the displaced instruction and preserves its resulting
registers/CCR around the callback. The rotation callback executes the tested
FF1PositionRotate20 helper using the native table coefficients and native
integer rotation results. No fine-step displacement is enabled yet.

Equal-layout control/bridge builds pass four decoded-state checkpoints on
stock 68020 and 68020+Fast. Each exercises 800 loads and stores; the final shadow
integer coordinates match all eight cars and all fractional tails remain zero.
See `manifest/step5-position-bridge-validation.json` for rotation counts. The
demo exercises no reset hook, so these runs do not validate recovery/clamp
coverage or nonzero fraction lifetimes. Indirect position writers remain to be
connected before enabling the 20 ms position path. The diagnostic uses private
slave storage; production allocation still follows the MEMF_PUBLIC policy.

The initial control capture failed on a Python reporting assertion after its
snapshots; that run was not accepted. The corrected script reran the control
and completed all four runs. No emulator batch remains running.

Next: cover seeded fractional resets and indirect per-car array writers, including
$6886e/$688e2 initialization and $691c4 contact-relative longitudinal placement.
A simple integer-difference detector at the next load is insufficient: an
explicit reset can write the same integer while invalidating its old fraction.

## Reset/contact position ownership

Explicit position reset and source-relative assignment helpers pass 144 seeded
whole-state tests on each of 68000 and 68020. The v2 diagnostic uses them at
known resets and both native contact placement sites. Both 020 demo comparisons
remain exact, but neither reaches a reset or contact-placement callback.
Native seeded contact coverage and initialization/save-writer coverage remain
open; no 20 ms live position path has been enabled. All test batches finished.

## Native contact and recovery branch coverage

Forced native $68d4e contact tests pass 56 cases on each 020 profile, covering
all car pairs in both directions with distinct nonzero fractions/remainders.
Both native assignment branches run 28 times. Captured integer positions,
speeds and longitudinal velocities match control; the complete shadow state
changes only as required by source-relative assignment.

Forced native $69496 recovery tests pass for all eight cars on both profiles.
Each invokes both the longitudinal reset and lateral reposition hook (16 total
per run). The destination integer state follows native recovery, both tails
are cleared, unrelated cars/axes remain unchanged, and captured native fields
match control. These establish contact and recovery ownership in the native
step; fine-step collision behavior and all other reset writers remain open.

Reports: manifest/step5-native-contact-validation.json and
manifest/step5-native-reset-validation.json. Test runners use startup warp and
these results carry no performance claim. All emulator batches have finished.
The authoritative WHD source SHA remains unchanged. Next: finish the saved
longitudinal snapshot and cold array-writer hooks, then enable the position
conversion in the diagnostic integrator alongside the remaining physics work.

## Saved position and cold writer coverage

The v3 diagnostic bridge owns 21 position-write sites and a per-car saved
longitudinal sidecar. Both 020 native-step demos remain exact. Both profiles
also pass 56 targeted native instruction-group cases for snapshot/restore and
five cold writers, with nonzero tails, explicit expected native arrays and
complete live/saved sidecar comparison. See STEP5_UNITS.md for the corrected
fixture setup and coverage limits. Full modal/loader lifecycle and fractional
boundary predicates remain incomplete; no 20 ms gameplay path is enabled.
All emulator batches have finished.

## Fraction-aware position boundary helpers

The 020 continuous segment predicate passes 2661 guest cases using all demo
angles and signed extremes; it retains the native quantized geometry coefficients
but includes both coordinate fractions and /5 remainders. Native-step controls
will continue using the original rounded integer predicate. Full-axis integer
bound clamps pass 234 cases on both 68000 and 68020. No live fine-step path
is enabled yet. Next is the position-only diagnostic integration; correct
20 ms gameplay still requires the other physics and scheduling work. All
current emulator tests have finished.

## Fine-step position path running in the demo

The new VERIFY-only position path is integrated with per-car storage, fractional
segment crossing, rotation and eligible clamps. On each 020 profile, all 800
recorded updates (100 per car) match independent arithmetic expectations; final
shadow coordinates match game arrays and remainder ranges hold. Native-step
controls remain exact. Both runs exercise nonzero fractions and segment changes.
This is not yet 20 ms gameplay: force/velocity/heading/other state and clocks
still run at native cadence. No performance or handling acceptance is claimed.
See STEP5_UNITS.md and manifest/step5-position-fine-validation.json.
All six emulator captures completed; no batch remains running.

## Fine heading path running with fine position

The corrected VERIFY-only heading+position diagnostic passes on both 020
profiles: 800 exact position updates and 1600 exact heading increments per
profile, with unchanged native control comparisons. Angular wrap and signed
remainders are covered by guest unit tests. Targeted native recovery calls
also pass all eight cars on each profile, clearing only the reset car's tails.
A cold-hook branch-boundary defect was caught statically and corrected before
all accepted demo captures were rebuilt and rerun. See STEP5_UNITS.md for
addresses, evidence and limits. Force/velocity/history and the production
scheduler remain incomplete; this is not yet 20 ms gameplay.

The two coupled-zero groups, two cold resets and world assignment additionally
pass 40 seeded native instruction-group cases on each 020 profile. Full modal
transitions are still outstanding. All current emulator batches have finished.
Next: force/velocity history and derivative conversion, including frame changes
and impulses, followed by filters/events and integration with the scheduler.


## Fractional velocity arithmetic

Added Q16 continuous-derivative, frame-rotation and explicit-reset primitives.
The 68020 guest tests pass 3967 cases including all native rotation angles,
aliasing and overflow rollback. Native velocity writer ownership is now mapped
in STEP5_UNITS.md. These helpers are not yet live physics hooks.

The AI audit also corrected a material earlier assumption: `$6773c..$67752`
averages current and previous raw STEERING requests, then stores the current
raw request. It is not exponential speed retention. Preserve its elapsed
history separation rather than applying the previously proposed retention
coefficient. This correction does not change the requested 20 ms interval.

The A500 also passes 751 derivative/reset cases, confirming the documented
68000-safe operations; this does not validate a coarse physics interval.
The first A500 fixture build had an incorrect loop count and was stopped;
the corrected build passed with a matching capture hash. Consolidated report:
`manifest/step5-velocity-primitives-validation.json`. All velocity guest tests
are finished. Ordinary WHD source remains byte-identical.


## Fractional projection, response and position interface

Fractional speed projection adds 5123 passing guest cases to the velocity suite
(9090 total on 68020). Continuous response integration passes 56 cases with
per-axis carry and atomic rollback. Position now has a Q16 velocity input entry;
its 53 cases and the 49 original integer-entry cases pass on 68020. These close
arithmetic interfaces needed for integration, not the live integrator itself.
Projection still uses supplied native-quantized coefficients; fractional heading
interpolation and resulting derivative jitter remain to be assessed. The next
integration must own current/previous velocity, response carries, all audited
writers and frame transforms before enabling these entries in the demo path.
All current test batches have finished; ordinary release source is unchanged.

## Native velocity hooks validated in the demo

The new native velocity diagnostic passes both 020 profiles: four matched
checkpoints remain exact; all 800 per-car velocity records match independent
projection/tyre-response arithmetic; final shadow matches native arrays. It also
observes every normal frame crossing (570 stock, 565 Fast). This validates the
hook locations and arithmetic in real gameplay. It does not yet activate the
fractional velocity simulation. Response remainders must still follow frame
changes and every velocity writer, and force/speed/wear conversion remains open.
All current emulator runs have finished. See STEP5_UNITS.md and
manifest/step5-velocity-bridge-validation.json.


## Velocity response carry across segment frames

Added combined Q16 velocity/remainder rotation with atomic range checking.
All 3216 68020 guest cases pass, covering every native angle and signed extremes.
The live integration still needs per-car ownership of this state and the audited
reset/contact writers; the new helper alone does not enable adapted physics.
See manifest/step5-velocity-carry-validation.json. All current tests are finished.


## Per-car velocity ownership hooks

The diagnostic now has 12 bytes per car for two Q16 velocity components and
independent response remainders. Six cold-reset hooks and the native contact
exchange hook are installed with qualified instruction boundaries. Both native
demo comparisons remain exact. Full native contact fixtures pass 56 cases per
020 profile with seeded nonzero tails, transferring longitudinal state only.
Cold reset seeded tests and the remaining velocity writers are not yet covered;
this does not enable the fractional simulation or complete step 5. All current
captures have finished. See STEP5_UNITS.md for exact scope and reports.


## Cold velocity reset coverage complete for the installed sites

Both 020 profiles pass 40 seeded native writer-group cases, exercising all six
installed cold reset sites (48 callbacks per run). Explicit expected arrays and
whole sidecar state pass, including same-integer resets. Full initialization
flows and the remaining live velocity/force writers remain open. Off-road
response is now identified as repeated penetration-dependent change requiring
elapsed-step scaling, rather than a cold reset. All current captures finished.


## Working velocity reset/clamp/impulse ownership

Seven further native sites are hooked. Both 020 demos remain exact; 56 seeded
writer-group cases per profile verify full replacements, axis-only clamps and
fraction-preserving lateral impulse writes. This establishes ownership behavior
at those native sites, not adapted forces or full event flows. The next fine
velocity integration sequence is recorded in STEP5_UNITS.md. Continuous off-road
response, force/speed/wear conversion and scheduler/presentation work remain.
All current captures finished; no playable 20 ms mode is claimed.


## Fractional velocity helpers joined at native call sites

The diagnostic now runs fractional projection, normalized velocity change,
body/world transforms and trial response integration together. Both 020 profiles
pass 800 independently checked records and retain exact native comparison states.
The normalized change does not yet drive the tyre curve; the trial integrates
the recorded native limited response and does not commit to gameplay. This is
interface/arithmetic integration evidence only. The next change must feed the
normalized body change through the curve and own the persistent result, alongside
force/speed/wear conversion. All captures finished; step 5 remains incomplete.


## Persistent velocity activated in a bounded diagnostic

Mode 8 now commits fractional velocity/carry and feeds normalized change through
the native tyre path. Both 020 profiles complete 800 arithmetic-checked records;
native comparison modes remain exact. A consistency fault identified unconverted
off-road increments, which now use the fine response integrator.

Physics acceptance is explicitly withheld: larger normalized changes exceed the
old magnitude range and expose a narrowing multiply/divide sequence in native
response rescaling. Widen those calculations next. Mixed position/heading timing,
force/speed/wear conversion and scheduler/presentation integration remain open.
All final captures finished; authoritative WHD source remains unchanged.

### Wide tyre arithmetic unit validation

The persistent velocity diagnostic exposed normalized magnitudes beyond the
native square-root limit of 1023 and a native `EXT.L` that discards the high
word after a signed component multiplication. Separate candidate helpers now
provide full unsigned 32-bit floor square root and signed full-product tyre
rescaling with checked input/output ranges. The 68020 guest fixture passed all
1,359 cases, including square boundaries, large magnitudes, signed components
and rejected inputs. Evidence: `manifest/step5-wide-tyre-validation.json`.
The square-root instructions are 68000-compatible but this fixture executed
on 68020 only. Integration in the persistent demo diagnostic is pending; this
is not acceptance of physics, handling, timing or the ordinary release.

The widened demo integration passed stock 68020: 800 records, four exact
native-control checkpoints, 135 magnitudes above 1023 (maximum 9054), and
82 records requiring full component products. The Fast-profile run stopped
at the explicit invalid-response guard on tick 162, record 289, car 6.
Its native tyre curve returned -5099 with input speed -182 and magnitude
2838; the captured tyre-capacity word was also -5099. The fault memory and
registers are retained under `tmp/step5/a1200-fast-velocity-fine-fine/`.
This does not establish the cause of the negative speed; trace scalar-speed
ownership and the curve's speed lookup before relaxing any guard. Scalar
speed/off-road conversion remains incomplete. Both-profile integration is
not accepted. The ordinary slave is unchanged.

### Scalar rate conversion after the wide-tyre fault

A separate guest trace of scalar speed stores reproduced the Fast-profile
fault at tick 162, record 289, car 6. The first negative speed was written at
`$672f0`, immediately after `$6d4cc` (engine/drag processing): previous output
492 became -182. It was not the later off-road decrement. The resulting
negative tyre-curve input selected a negative speed-table index. Trace:
`tmp/step5/a1200-fast-speed-trace-fine/fault-speed.bin`, interpreted as a
512-entry ring of 16-byte writer/tick/car/speed/D0/D1 records, with total
count in `result.json`. This instrumentation changes no arithmetic.

`src/FerrariFormulaOne_Speed.s` now implements a Q16 scalar 20 ms rate
helper with signed fractional carry and speed bounds 0..500. It scales the
proposed native result minus the integer current speed by one fifth, using
a full 64-bit numerator. The captured 492 -> -182 proposal becomes 357.2.
All 130 guest unit cases passed on 68020, including repeated increments,
signed decrements, clamps and invalid states. See
`manifest/step5-speed-rate-validation.json`.

The diagnostic applies this helper at twelve continuous scalar writers:
`$672f0`, `$673fc`, `$67426`, `$67438`, `$6744a`, `$67476`, `$675c0`,
`$6766c`, `$6768e`, `$676e0`, `$69970`, `$69a42`. Discrete loads, feedback,
resets and clamps initialize the scalar working state separately. The
projection consumes its Q16 speed; native speed lookup consumers see the
integer component. Scalar fractions currently persist within each update
only: the native load and velocity-magnitude feedback still reset them.
Engine side effects, wear, gear history and event timing are not converted
by this arithmetic helper. Player-only/boost wrapper sites still need
execution coverage beyond the automatic demo. Integration validation is
pending completion of both profiles.

The scalar-rate integration completed both profiles. Stock 68020 passed
1,583 scalar records and 800 velocity records; 68020 + Fast passed 1,607
scalar and 800 velocity records. Both retain exact native control/observer
states at ticks 125, 150, 175 and 225. There were 495 / 532 fractional
projection speeds and no scalar clamp events in these runs. Seven of the
twelve rate sites executed; player-only paths remain uncovered. The
previous Fast-profile negative-speed fault did not recur. Both runs reached
tick 225 without the diagnostic range guards firing. Evidence:
`manifest/step5-velocity-fine-validation.json`. These are arithmetic and
ownership checks, not 20 ms physical-time or handling acceptance.

### Fractional scalar feedback and persistence

`FF1SpeedFromVelocity020` derives scalar speed from the physical velocity
components `5*Q16 + remainder`, using full 64-bit squares and floor square
root. The scalar result retains fifth-of-Q16 precision. Speed below 4
requests a full stop; speed above 500 is capped. Invalid carries or scaled
components outside signed 32 bits are rejected without changing output.
This bound is explicit; it has not been justified for every production
transition. All 1,003 guest fixture cases passed on 68020. Evidence:
`manifest/step5-speed-feedback-validation.json`.

The demo diagnostic now keeps six bytes of scalar state per car, initialized
from native speed at installation. Loads/stores check that native integer
speed matches the fractional state's integer part. Cold assignments at
`$6897e` and `$68b84` reset the complete scalar state. The existing collision
swap callback now swaps all six scalar bytes along with fractional Z
velocity. Feedback uses the physical vector magnitude, and a fine-path stop
clears both vector components and carries. Scalar rate fractions survive
ordinary load/store instead of being cleared each update. Independent
records cover scalar feedback, stop decisions and final native/shadow
agreement. Both-profile integration validation is pending. Native-only
position/heading timing, side effects and production scheduling remain
unconverted in this diagnostic.

Persistent-feedback integration passed on both 020 profiles: 800 vector and
feedback records each; 1,577 / 1,576 scalar-rate records; 52 / 31 stops;
587 / 657 fractional feedback speeds; 20 / 12 complete scalar collision
swaps. Scalar and vector sidecars matched native integer arrays at the
end, and native controls matched at all four checkpoints. Cold scalar
assignments were not executed in these demo captures. The report remains
`physics_accepted: false`: position and heading are not yet combined here,
and event/wear timing, scheduler, presentation and 68000 conversion remain
open. Full scalar carry is retained by rate integration and feedback;
projection currently rounds its scalar input to Q16, omitting less than
one Q16 unit from its additional fifth-of-Q16 remainder.

Next integration boundary: combine the existing heading/position diagnostic
with the velocity/scalar path. Position needs a /25 remainder when integrating
velocity that itself carries fifth-of-Q16 precision. Use an explicit /25
position entry and matching fractional segment rotation; do not pass /25
state to the existing /5 rotation helper. Ordinary position assignment,
reset and fractional boundary predicates must be checked for this state.

The separate 64-bit square-root fixture also passed all 408 cases on 68020,
including full-width square boundaries, maximum unsigned input, random
values and preserved D1/D2 registers. Evidence: `manifest/step5-sqrt64-validation.json`.

### Combined motion integration

`FF1Position20Velocity` integrates `(5*velocity_Q16 + velocity_remainder +
position_remainder)/25`, rejecting invalid carries and overflow atomically.
The matching `FF1PositionRotate25` and `FF1PositionCrossed25` use /25 position
remainders. Existing /5 entries remain available. Reset and assignment copy
or clear the entire tail; integer clamp comparisons depend on its sign.

Guest checks passed: 130 integration, 3,086 /25 rotation and 2,661 /25 boundary
cases, plus rebuilt /5 regressions of 3,086 rotation and 2,661 boundary cases.
Evidence: `manifest/step5-position-velocity-validation.json`.

`build_step5_motion_fine.py` combines position, heading, velocity and scalar
speed through 83 non-overlapping patch sites. Position consumes the exact
velocity and carry produced by the same car update; analysis checks that
producer/consumer state byte for byte. Combined demo captures are pending.
Events, wear, real-time scheduling and independent presentation are not
implemented by this merge.

Combined motion validation completed on both 020 profiles. Each passed 800
position updates, 1,600 heading updates, 800 velocity/feedback updates and
1,600 scalar-rate operations. Position consumed exactly the velocity and
carry produced by the same update in every record. Native controls matched
at ticks 125, 150, 175 and 225. Position and velocity crossed 119 / 121 segment
frames, respectively; all final integer/sidecar states matched. Normalized
body magnitude was at most 20 in both captures. No contacts, off-road changes,
recovery or cold resets occurred in this short combined window; previous
standalone fixtures do not prove their combined behavior.

Evidence: `manifest/step5-motion-fine-validation.json`. This is a combined
20 ms arithmetic path executed by the diagnostic's existing loop, not an
accepted real-time 50 Hz game. Controller history, wear and event cadence,
clock/scheduling, safe independent presentation and capacity remain open.
The 68000 interval is still unselected; retaining the native 100 ms physics
quantum is a candidate worth measuring before considering a longer step.

### Steering history at the fine quantum

The fine controller is evaluated every 20 ms. Its native two-tap mean keeps
a 100 ms separation: current raw steering plus the raw request five physics
quanta earlier, with native signed-word addition/shift semantics. Per-car
state has five samples, a cursor, last simulation quantum and last raw request
(18 bytes). Inactive controller intervals hold the last raw request; duplicate
or backwards quantum calls are rejected. Explicit initialization seeds all
five history slots from the native previous raw request. That is a startup
history assumption, not reconstructed pre-install samples.

`FF1SteeringSample20` and `FF1SteeringReset` passed 80 guest cases on 68020,
including both signed and unsigned counter boundaries. The instructions are
68000-safe, but this test did not execute them on 68000. Evidence:
`manifest/step5-steering-validation.json`.

The combined steering diagnostic replaces the filter at `$6773c` only in
fine mode. Native control modes execute the displaced filter unchanged.
The cold-history reset at `$68788` resets all per-car history. The diagnostic
uses its simulation-update serial; eventual scheduler integration must supply
this serial from fixed physics quanta, not frames or elapsed VBL counts.
Combined demo validation is pending. Handling comparisons, wear/events,
real-time scheduling and independent presentation remain open.

Steering integration passed both 020 profiles: 800 replayed samples per
profile, exact complete history state and native latest-raw agreement.
The 100 ms delayed sample differed from the previous 20 ms sample in
247 / 266 records, demonstrating the intended history separation. All
combined position, heading, velocity and scalar checks still pass, and
native controls match at four checkpoints per profile. These short demo
windows did not exercise inactive gaps or cold resets; those semantics are
covered only by helper tests so far. Evidence:
`manifest/step5-steering-fine-validation.json`. Handling and elapsed-time
acceptance remain outstanding.


### Continuous slip-wear conversion (both 020 profiles validated)

Added `src/FerrariFormulaOne_Wear.s`: 20 ms condition loss divides the final
native 100 ms decrement plus condition-owned carry by five before saturation.
254 guest helper cases pass. The combined motion/steering fixture now installs
six slip-loss interception groups and three explicit initialization/repair
carry resets, with exact signatures and external-branch/overlap validation.

The stock 68020 automatic-demo capture passes: 1,100 wear records (100 for each
of four player tyres and seven opponents), all six branch sites exercised,
zero arithmetic or carry-continuity failures, and exact final native condition
values. The existing 800 velocity/position/steering, 1,600 heading and 1,600
scalar-rate checks pass too; disabled observer comparisons match at all four
checkpoints. The Fast profile also passes all 1,100 wear records and the combined checks.
Report: `manifest/step5-wear-fine-validation.json`. Live reset/depletion paths
are absent in this short window; helper tests alone do not accept those hooks.

The first fixture attempt correctly rejected old JSR signatures at two sites
already changed by the exact-multiply pass. The current fixture validates and
preserves their installed MULS.L/NOP form. Ordinary release/source unchanged.

Next: gate eligible rotating component wear
and opponent random-failure calls at native 100 ms pulses; cover repair and
other condition writers. This is not real-time 20 ms gameplay or capacity
acceptance. Full step-5 scheduler/presentation/transition/68000 gates remain.


### Rotating wear and random-failure pulse gating

`step5-events-fine` extends the combined fixture with two eligible call gates:
player rotating wear at `$6d5f2` and opponent random failures at `$6d67e`.
Call-site gates retain native eligibility checks and preserve all original
register/stack behavior on the disabled observer path. The RNG entry is
instrumented only to count consumption, with the displaced instructions intact.

Both 020 profiles pass 800 decisions each. For every car, 100 fine updates
produce 20 accepted native-tenth calls and 80 skips. All 640 skips per profile
leave the 64-byte condition/status snapshot, component index and RNG call
counter unchanged. Accepted player calls advance the index modulo nine once;
opponent calls consume one or two native random values. Four disabled-path
checkpoints remain exact and the combined motion/steering/slip-wear replay passes.
Report: `manifest/step5-events-fine-validation.json`.

Gating RNG changes the subsequent demo trajectory. The stock-020 window now
covers four slip-wear branches; the Fast window covers all six. The report
explicitly lists absent branches rather than claiming coverage in both windows.
The earlier wear-only fixture remains the separate six-branch evidence.

The diagnostic advances a shared phase once per declared 20 ms simulation step,
independently of drawing and call eligibility. It is NOT an elapsed wall-clock
scheduler: production must obtain the same pulse from the time context, retaining
pause/debt rules. No real-time 50 Hz, capacity or complete event conversion claim.

The separate `step5-clocks-fine` fixture passes both 020 profiles. It gates only the eligible
`$65dca/$65dd8` native clock calls on the same pulse, leaving their surrounding
countdown/session-cap checks intact. Each profile validates 200 clock-call decisions: 100 eligible calls per clock,
of which 20 run on the fine path. Both clocks advance exactly two simulated
seconds across 100 fine updates. Digit replay, continuity and final values pass,
as do all combined motion/event checks and four native comparison checkpoints.
Report: `manifest/step5-clocks-fine-validation.json`. Native clock drawing side effects
remain to be separated for independent presentation.


### Countdown, clutch charge and engine phase cadence

The `step5-counters-fine` combined fixture gates the engine phase increment,
countdown decrement and player clutch state-update block with the shared native
100 ms pulse. The countdown keeps native zero-crossing side effects. Clutch
acceleration calls remain fine updates with their existing scalar /5 conversion;
only charge accumulation/decay is gated. Native instruction-group signatures,
overlap and external branch targets are checked before installing four hooks.

Both 020 profiles pass the short automatic-demo replay. The engine phase advances
20 times over 100 fine updates; disabled observer mode advances 100 times and
matches four native checkpoints. Combined clocks, event gates, wear, steering,
heading, position and velocity replays still pass. The demo does NOT cover
countdown or clutch changes. Report: `manifest/step5-counters-fine-validation.json`.

A separate controlled guest fixture executes those installed hooks and actual
native code with temporary return boundaries, rather than simulating their
branches on the host. All 256 cases pass on each 020 profile: four phase values;
countdowns 0/1/2/10/32767; matching/nonmatching start segments; input states;
previous launch-latch values; clutch values 0/1/9/10; and each eligibility failure
(condition/fuel/input/speed). Both native observer and fine modes run with pulses
zero and one. This catches the native clutch-at-ten behavior: it decays to nine
on an eligible native update, rather than saturating at ten. Zero-pulse fine
updates retain the charge. Report: `manifest/step5-counter-transition-validation.json`.

The first transition build exceeded a 16-bit branch displacement because its
inline case table is large; the isolated 020 fixture now uses a long branch to
its stop point. Both test processes exited successfully. Ordinary source and
release remain unchanged; no real-time scheduling or complete transition claim.

Next: continuous fuel loss, boost/audio filtered state and remaining recovery
counters; then real-time scheduler/presentation integration and capacity gates.


### Continuous fuel consumption and explicit fuel assignment hooks

The combined `step5-fuel-fine` fixture divides the final native consumption at
`$6d164` by five with a per-car remainder, using the already-tested unsigned
condition-loss helper. Saturation happens after division; depletion clears the
fraction. Setup/refill/emptying groups reset the corresponding carry. All six
patch groups pass signature, overlap and external branch-target checks.

Both 020 demo profiles pass exact fuel replay and final state/carry checks:
800 consumption records on stock 020, 763 on 020+Fast. All eight cars are
covered, and all prior combined checks plus four native comparisons pass.
Different accepted counts follow the demo's accelerator/braking choices; a
fuel decrement is attached to each actual accelerator call, including repeated
clutch calls, rather than charged unconditionally per physics step. Report:
`manifest/step5-fuel-fine-validation.json`.

Direct guest tests pass 246 cases per profile against the actual installed
hooks: all eight cars, native and fine modes, fractional/small/large loss,
depletion, zero fuel, player setup, opponent setup, refuelling, explicit
emptying and native zero-clamp groups. These test carry reset and the preserved
native D0 result as well as stored fuel. Report:
`manifest/step5-fuel-transition-validation.json`. Full pit/save/load workflows
are not accepted by these isolated return-boundary tests.

The `step5-boost-fine` fixture now passes both 020 profiles. Within the existing drawing
omission diagnostic, it gates the remaining boost/audio/gear state call to native
100 ms pulses and records its before/after state. This must not be interpreted
as final separation of the complete native renderer from simulation.


Boost/audio/gear replay validates 100 decisions per profile: 20 accepted calls
and 80 skips on the fine path. The independent oracle checks the native target
calculation, signed word dead band, +/-9 state changes, clamped audio parameter,
audio direction and gear transition steps. Rising, falling and held states all
occur in the stock-020 window. Skips retain the entire observed state. Native
comparison checkpoints and all prior combined checks pass. Report:
`manifest/step5-boost-fine-validation.json`. Audible sound, extreme-input cases,
full drawing separation and real-time execution are not accepted by this run.

Next recovery work must include logic currently omitted with drawing: player
negative status advancement and opponent recovery/refill updates. A healthy
short demo does not reveal those missing transitions.


### Recovery cadence and ownership separation

The combined recovery fixture passes both 020 automatic-demo profiles, including
all prior combined replay checks and four native comparison checkpoints. Its
healthy window contains no nonzero recovery or contact countdown, so it does not
establish transition behavior. Report: `manifest/step5-recovery-fine-validation.json`.

Controlled guest tests execute the actual recovery dispatcher/native opponent
loop: 336 cases per profile cover positive/negative status, pulse/no-pulse,
outer/freeze/countdown/session/per-car gates, race type, refills and fractional
carry reset. A separate 128 cases per profile tests all eight contact countdown
hooks and native result preservation. Contact zero-expiry position/vector/scalar
reset chains are not covered. Reports: `manifest/step5-recovery-transition-validation.json`
and `manifest/step5-contact-counter-validation.json`.

The new `step5-recovery-separation` fixture removes two ownership conflicts:
fine-mode presentation skips player/opponent recovery updates, and simulation
no longer clears the opponent drawing list. Observer mode retains native
presentation updates. Installed hooks check original signatures, overlaps and
external branch targets before mutation.

All 1,008 controlled cases per profile pass on stock 020 and 020+Fast. Each
combines a simulation decision with zero, one or three presentation passes;
fine-mode recovery/refills/carries remain unchanged by those presentation calls.
The simulation preserves a sentinel drawing-list count, while eligible native
presentation clears it. Projection selection executes for out-of-range opponents;
temporary test return boundaries exclude sorting/drawing and the rest of the
player renderer. This is recovery ownership evidence, NOT full safe presentation
or real-time capacity acceptance. Report:
`manifest/step5-recovery-separation-validation.json`.

The original recovery fixtures/results remain intact. The compact isolated
fixtures discard unused motion trace storage; one earlier larger recovery test
timed out at startup, without a confirmed cause. Current recovery test runners
wait again on the same live debugger command after observation timeouts.

Step 5 still needs integrated elapsed-time scheduling, complete independent
presentation (including clocks, instruments and wheel phases), longer combined
and modal/save-load/contact-expiry validation, measured 20 ms capacity, a measured
68000 interval, MEMF_PUBLIC relocation/lifetime work and default-off release
integration with legacy-path verification. No playable performance claim yet.


### First elapsed-time combined execution

`build_step5_elapsed.py` derives from the recovery-separation fixture. It installs
the previously verified PAL VBL timer at `$24946`, with signature verification,
interrupt exclusion and cache flush. The update entrance waits for one due 20 ms
quantum; the end of the completed logic loop consumes that quantum. Native
100 ms pulses are previewed from the context phase and checked against the
commit result. Outstanding time is retained, never rebased to hide overload.
This diagnostic still omits drawing and does not implement bounded catch-up
with presentation, modal epochs or production CPU/version/load integration.

Both profiles complete 100 adapted updates. The timer and independent combined
state replay pass: exactly 2.000 simulated seconds and 20 native pulses, no
unexpected rebase/pause, correct consumed/elapsed/debt accounting. New fine
captures are checked against the existing state oracles. The replay's native
control/bridge comparison uses retained recovery-fine captures; it is prior
comparison evidence, not a new disabled-path check of this build.

Measured diagnostic results (includes extensive trace recording):

| Profile | Mean traced update | Elapsed time for 100 updates | Outstanding debt |
| --- | ---: | ---: | ---: |
| 68020 | 58.09 ms | 6.110 s | 4.110 s |
| 68020 + Fast | 45.47 ms | 4.768 s | 2.768 s |

These costs fail the 20 ms target in this instrumented drawing-omission build.
They do not prove the production algorithm's capacity: trace overhead remains.
The update cost covers the measured update body, while total elapsed includes
work between updates. Field-resolution timings are averaged across 100 updates.
No 60-second, overload-recovery, final-renderer or real-time gameplay acceptance.

Reports: `manifest/step5-elapsed-validation.json` and
`manifest/step5-elapsed-replay-validation.json`. Captures are
`tmp/step5/{a1200,a1200-fast}-elapsed-fine`; runner `elapsed_step5.py`.
All processes finished. Next capacity work should remove detailed tracing while
retaining state equivalence and lightweight elapsed/debt observations, then
measure and optimize the actual integrated update cost.


## Precise capacity profile (2026-10-12)

See `STEP5_CAPACITY.md`. Full instruction traces of the elapsed diagnostic show
25% of each update is WHDLoad emulating the privileged `move.w sr,-(sp)` in hook
trampolines (235 traps/update), not trace recording (6%). The one-change
`move.w ccr` variant passes the elapsed and replay oracles and measures 640,022 /
523,218 cycles per update (45.1 / 36.9 ms traced) on stock 020 / Fast. The
native-equivalent work for eight cars alone (327k cycles) exceeds one 20 ms
quantum (283.75k), so all-car 20 ms cannot meet the target on a 14 MHz 020.
The user selected the revised design: 20 ms only on 68020+ with Fast memory,
player at 20 ms and opponents on the native 100 ms step (Plan B, projected
8.2 ms average on 020 + Fast, 6.8 ms with code placement); chip-only 68020 and
68000 run the native 100 ms step. Ordered steps and gates: STEP5_CAPACITY.md.
