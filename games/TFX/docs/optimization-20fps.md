# Further 040 optimization toward 20 fps

Active goal: 20 fps average on Apollo 1240/40, with vsync and unchanged detail,
simulation and 060 compatibility. Plan: PERFORMANCE_PLAN.md, ff094922.

Evidence root: tmp/opt20 (relative to this harness). First shadow-copy optimization committed as 4b81b5ff.
Fresh baseline-retry repeats 73 publications/250 vblanks, zero FPSP/cache flushes.
Completed publication intervals: 3 at two fields, 37 at three, 32 at four.
20 fps requires 100 publications/250 fields: 37% more than current throughput.
For only two/three-field frames, 20 fps requires equal counts, not mostly threes.

Presentation: do_swap_screen calls SetPage without a CPU sync wait. SetPage only
writes COP1LC; the private emulator's COP1LCH/COP1LCL update that pointer, without
restarting copper execution. check_vblank_copjmp performs COPJMP(1,1) on frame
start. Step 3's complete trace confirms next-field bitplane adoption. Thus the
lack of an explicit CPU wait is not proof of unsynchronized visible presentation.
Do not add another wait without testing buffer reuse and actual display adoption.

Experiments:
- sprite-on / sprite-v1.s: XOR mask merge and aligned word path. 192 native twins
  match the original, independent byte oracle, full guarded output and preserved
  caller registers. 73 frames, no aggregate gain. Only 6,920 aligned words versus
  380,200 shifted words in this fixture; aligned specialization has little impact.
- sprite-zero-on / sprite-zero.s: also skips zero shifted masks. 73 frames, no
  aggregate gain. Not retained; this revision has not run the twin suite.
- delta-on: per-chip-buffer fast shadows compare 16-byte blocks and write only
  changed blocks. Prototype and 040-gated candidate both produce 77/250 (15.4
  nominal fps). Actual helper passes 80 native buffer-history/guard/pointer cases.
  Longer same-build A/B, game coherence, controlled scenes and regression gates
  pass for the final lifecycle-safe build; see final results below.

First baseline attempt could not connect to the local debugger under sandbox
permissions. Its PID had exited before the authorized retry; no process killed.
Successful fresh baseline and subsequent emulator runs use permitted local sockets.

Next: measure shadow-copy candidate; retain only if timing and native buffer
comparisons justify it. Gate any accepted implementation to new-renderer 040,
check allocation failure/off paths and other CPUs, and measure longer same-build
A/B windows. Examine flat spans and geometry if copying offers no useful win.

Longer preliminary same-build measurement (delta-long-off/on, identical seed):
546 vs 578 publications/2,000 fields = 13.65 vs 14.45 nominal fps (+5.86%).
Enabled completed intervals: 11 two-field, 291 three-field, 275 four-field.
Disabled: 3 two-field, 179 three-field, 363 four-field. These different simulation
cadences are not a state-equivalence result. Both remain visibly in cockpit flight.

The extended window newly reaches tfx.020:$51682 FETOX: 204 FPSP entries with
copy disabled, 142 enabled. This was outside the earlier short zero-trap window.
Do not extend the short-window zero-FPSP claim to all flight. Investigate its
operands and native arithmetic separately from rendering; do not alter FPSP safety.
Hardware measurements are explicitly postponed: the user has no Amiga available.

Lifecycle reset hook at PlayLevel $16de replays its six-byte prologue and resumes
at $16e4; only new-renderer 040 installs it. No branch to an interior instruction
was found in the accepted disassembly. It invalidates both shadows on entering a
flight after menus or a previous flight. Final verification is in progress.
One reset draft produced slave relocation records and WHDLoad rejected it before
loading the game. Corrected to PC-relative access, with a no-relocation build
check. The first scene attempt after an assembler failure used the previous
binary and failed before observation; neither is accepted evidence.

## Accepted shadow-copy result

Final code: delta-final.s / delta-final.slave, normal build delta-final.lst.
Final same-build pair final-long-off/on repeats 546 vs 578/2,000 fields (+5.86%).
The unchanged [2,252) prefix is 73 vs 77. Final enabled intervals: 12 two-field,
289 three-field, 276 four-field. Counts in earlier prototypes differ slightly.
Logical CPU chip writes: 8,967,382 off vs 3,108,888 on; not physical bus counts.
Both final captures use identical build, emulator and HDF seed hashes.

Final native helper suite: delta-final-twins (80 cases); check_opt20_delta.py
passes and rejects four deliberately corrupted result/guard/pointer/output inputs.
Scene pairs scene-on/off-coherent and views-on/off use fixed simulation timesteps
and synchronously resolved joystick inputs solely for correctness, never timing.
The view tape sends native F2/F3/F5/F6/F1 requests by swap index. Captures visibly
include turned cockpit and external views. Every completed destination matches
all 64,000 rendered bytes (114 checks); before reuse every valid shadow matches
its chip destination (110 checks). Cache-aware debugger reads are confined to
these functional runs. Ten corresponding complete displayed buffers and PNGs
match enabled/disabled. Both scenes retain the existing next-field DMA checks.

Gates gate-020/030/040/060 and gate-040-original all reach flight. Shadow pointers
are nonzero only on new-renderer 040; the six original PlayLevel prologue bytes
remain untouched on 030/060 and original 040. All 245 inspected 060 FPU sites match
step 10. All gate copies match the final slave bytes. Normal and CHIP_ONLY builds
pass with no relocation records; both FPSP files remain unchanged.

No simulation or drawing-detail changes are made. Reset consumes the exact
original fmove.x FP2 and D2 save prologue before continuing at $16e4. The original
control flow has one entry call at $1f6a and no branch into the replaced six bytes.
Shadows use 128,000 extra fast bytes. Optional allocation failure leaves their
pointer zero and selects the original full-copy loop; the same loop is exercised
by the disabled timing/scene controls. Real allocation exhaustion was not induced.

Reproduce from the game directory with a fresh output path:

    bash tools/build.sh -L "$PWD/tmp/opt20-new.lst"
    FSUAE="$PWD/tmp/step9-emulator/fs-uae/fs-uae" \
      DELTA_LISTING="$PWD/tmp/opt20-new.lst" END_FIELD=2002 \
      python3 tools/opt20_profile.py "$PWD/tmp/opt20-new-on"

For its same-build control set DELTA_OFF=1 and TEST_SEED to the same seed directory;
never reuse a seed across changed slave bytes. opt20_scene.py uses SCENE_NOMMU=1,
optional VIEW_TAPE=1, and the same DELTA_OFF control. opt20_delta_test.py consumes
DELTA_LISTING; run check_opt20_delta.py on its output. opt20_gate.py OUT CPU
[original] checks live activation. The gate boot divides its startup wait into
250-field commands for 030. Run one emulator session at a time, and keep the build
fixed for a suite. Final tool snapshots are under tmp/opt20/tools/.

Next optimization candidates: reduce changed-block copy overhead, improve wide
flat spans, and capture FETOX operands from the extended flight. Two masked-sprite
rewrites had no aggregate gain and remain discarded. Hardware target is pending.

Changed-block MOVEM batching (delta-movem-on) still gives 77/250, so it is
discarded without retaining a code change or claiming pixel equivalence.

## Native exponential follow-up

The separate opt20-exp-emulator extends only read-only operand logging at $51682
and its continuation. exp-operands reproduces final-long-on counts, image, all
entry/start/end game hunks and the entire non-math profile exactly. It records
142 FETOX inputs in [-1.3445751106473476, -1.0025375355083193], all FPCR=0.

A native helper is under test for finite |x|<=64 with FPCR=0. It uses split-ln(2)
range reduction, degree-17 exp(r), and an exactly constructed power of two; other
arguments/modes execute the original FETOX. Low-page slot $220 is 040-only and
CUSTOM5 retains its off path. Both source generators reproduce the includes.
1,248 default-mode cases pass an independent 80-digit Decimal.exp oracle (maximum
relative error 1.5381e-16), including recorded inputs, reduction boundaries,
random values and range fallbacks. All FPSR/FPCR and non-destination FP registers
agree with FPSP. Another 726 non-default precision/rounding cases match every
FP register and both status/control registers exactly. Four checker corruptions
are rejected. This is arithmetic validation, not yet an accepted feature.

The first 600-update controlled fixture reached additional SetPage calls without
intervening flight swaps at update 436, entering a gray fade. The harness's later
comparison incorrectly treated these as flight copies. Prior flight copies passed;
this is not evidence of a faulty copy. Retain that failed run separately. The
observer now rejects duplicate/unpaired publications, and the fixed comparison
ends at 400 updates, before the transition. FETOX execution coverage must be
confirmed in the resulting profiles before accepting its scene comparison.


Final scene pair: exp-scene400-off/on passes all 400 updates. It executes 440
exponentials between updates 176 and 395, with identical input sequences and
inputs [-2.9500336168733794, -1.002719511310615]. FPSP entries fall 440 to zero.
Seven complete displayed buffers and PNGs match at updates 1,10,30,45,57,200,400.
Maximum per-call error against Decimal.exp is 1.4063e-16. End-state changes are
fully accounted in exp-scene-comparison.json: intentional four-byte opcode patch,
five known clocks (+2 fields), and two double cells. Data+$f760 changes by
1.4210854715202004e-14; data+$149c4 by 4.742722294522476e-178. The latter is a
verified double operand at A4+6936, not a named symbol. BSS and all other bytes
match. No general clock-origin waiver or exact simulation-state claim is made.

Final timing pair exp-long-off/on uses the same slave, emulator and seed:
578/2,000 fields on both paths (14.45 nominal fps); FPSP 142 off, zero on.
All measured cache flush counts remain zero. This native-maths change has no
additional aggregate emulator speed gain; hardware latency remains unmeasured.

Reproduce arithmetic with opt20_exp_test.py OUT then check_opt20_exp.py OUT;
opt20_exp_modes.py OUT covers non-default FPCR modes. For controlled scenes use
SCENE_NOMMU=1 SCENE_SWAPS=400 EXP_AUDIT=1 and opt20_scene.py with DELTA_LISTING;
EXP_OFF=1 restores the original FETOX in the same slave before the fixture.
Use the same TEST_SEED for the on run. Timing uses END_FIELD=2002 with
opt20_profile.py and the same EXP_OFF control. All exponential tests use
opt20-exp-emulator; its creation script and logging patch are retained locally.
The normal math/FPU generators now reproduce both updated source includes.

Final 040/CUSTOM5/060 gates pass; all 246 inspected 060 FPU sites remain
unchanged. Normal and CHIP_ONLY builds have no relocation records, the normal
build matches the tested bytes, and both shipped FPSP files remain unchanged.


## Two-block flat-span experiment (running)

Baseline exp-long-on records 300,450 unaligned two-block spans, 2,403,600 plane
iterations. The pointer-add and branch instructions together account for 0.8466%
of scheduler time. flat-two-baseline-analysis.json records the pre-patch trace
counts and the only static inward branch into the replaced instructions (the
old loop's own back edge). A trial patches $6c5d4 only on new-renderer 040.
It unrolls eight plane operations with two -32,000 pointer adjustments, preserves
the original ninth colour/sentinel shift, and leaves all edge preparation intact.
The short run flat-two-on is unchanged at 77/250. Longer same-build off/on timing
and 512 guarded native comparisons are running; this is not an accepted change.

The broad SetColor profile bucket includes DoRotPt0. Exact nested symbol spans
attribute about 8.54% of the extended profile to DoRotPt0, so do not interpret
the broad bucket as colour-setting cost. exact-symbol-costs.json retains the
breakdown. This does not change the raw measured timings.


Two-block experiment rejected: flat-two-long-off reproduces 578/2,000, but
flat-two-long-on falls to 567/2,000 (14.175 nominal fps, -1.90%). The short window
was unchanged at 77/250. This does not justify retaining the unroll. The native
fixture stopped before executing because it compared the relocated absolute
PlayLevel/flat return-storage operand against unrelocated source bytes; no native
buffer-equivalence result is claimed. Correct that guard if reusing this harness.
Source archived as flat-two-rejected.s; production source restored to 91eb7410.


## Projection investigation (active)

The current Project pair of DIVS.W instructions at $55e6c/$55e72 accounts for
about 4.91% of the extended profile. Rotation already keeps packed matrix values
in registers and specializes partial-coordinate transforms; no simple rotation
rewrite has yet been justified. A private projection observer captures D0/D1/D2
before the first DIVS, with no guest memory reads or model/timing modifications.
The first capture project-operands has 578 publications but differs from the
historical exp-long-on in entry state and detailed cadence; it is NOT observer
invariance evidence. Its operands are provisional only (827,939 points, no
quotient overflow, numerator range -1,361,707..1,373,615, divisors 17..8,445).
A fresh same-binary observer-off/on pair is running with TFX_PROJECT_OPERANDS
controlling only logging. opt20_projection_analysis.py requires exact counts,
image, all captured hunk bytes and the entire profile excluding added operands.

An unbuilt draft is kept only at tmp/opt20/project-fpu-candidate.s. It sketches
native FDIV with FPCR round-to-zero, saves FP state once per point array, retains
the original clipping and saturation, and keeps integer division for the final
point to preserve returned packed remainder registers. It is not installed or
accepted. For signed 32-bit numerators and positive divisors >=17, the nearest
noninteger quotient is at least 1/32767 from an integer, far larger than extended
precision rounding error over this range. Native execution and boundary tests
are still required. No performance improvement is claimed from this draft.


Observer resolved: captures fall into two startup states. exp-long-on and
project-observer-on match exactly in counts, image, entry/start/end hunks and all
non-projection-operand profile rows. project-operands and project-observer-off
also match exactly on all those checks. The two pairs have clocks 1556 and 1554
at first swap, respectively; do not compare across these states or waive their
subsequent simulation differences. project-operand-analysis.json records both
validated pairs. The historical-baseline state has 827,603 points / 1,655,206
divisions, 8,392 distinct positive divisors, and zero quotient overflows.

The native projection draft now assembles and is installed only in the current
experimental build for a short screening run (project-fpu-short). No correctness
or speed claim yet. Preserve the committed exp-final.slave for the accepted build.


Projection validation progress: project-tests-v1 passes 160 complete array,
GPR/CCR and FP-register/control-state cases. The final candidate adds CUSTOM5
fallback and comments; project-tests-final2 passes 275 cases, including sampled
recorded operands and nonzero translations with 32-bit wrapping. The independent
integer oracle agrees for every point, and four deliberate corruptions fail.
The first expanded fixture stopped at its conservative 0x3b000 code-area bound
before execution; the checked 0x4d000 bound leaves the original Project function
and its global parameters untouched. Only final2 is accepted expanded evidence.

Preliminary long timing project-long-off/on gives 563 vs 598 frames, but entry
clocks differ (1555 vs 1556); this is NOT an accepted percentage comparison.
opt20_project_timing.py now admits a same-build candidate run only when all three
entry hunks equal the control, masking just the six-byte Project entry patch.
It rejects nonmatching startup states before timing, retains those attempts,
and stops after four failures; it never selects a run by observed FPS.


## Verified projection result

The final same-build pair project-final-off / project-final-on-1 has identical
entry-hunk bytes after masking only the six-byte Project patch, identical seed
and slave bytes, and no rejected startup attempts. Counts improve 563 to 598 over
2,000 fields (+6.2167%, 14.075 to 14.95 nominal fps). The short prefix is 76 to 80
(15.2 to 16.0); do not substitute the historical 77-frame prefix for this control.
The earlier committed build's historical extended result is 578/2,000 (14.45),
which is a separate build/startup comparison, not this feature's matched control.
Completed intervals change from {2:9,3:232,4:321} to {2:12,3:366,4:219}.
Both final profiles have zero measured FPSP entries and zero cache flushes.

project-scene-off/on completes 400 fixed-simulation updates. All seven complete
64,000-byte displayed buffers and PNGs agree, with next-field DMA checks. The
strict whole-state comparison initially fails and is not claimed as a pass:
five clocks differ, $4d692 is the current audio-channel-2 period, and record 9
of the 10-byte queue at $4d782 differs. Both queue counts ($4d77c) are zero, so
that record is inactive. Requested period $4d694 is 160 in both; current period
is 386 off / 160 on. Original audio interrupt code at $4d67e copies the requested
period to current, and $4d660 writes current to AUD2PER. The faster fixture ends
at a different interrupt phase. All remaining game-hunk bytes match apart from
the intentional Project patch. project-scene-comparison.json retains raw changed
bytes and explicitly marks strict_game_state_equal=false. This is no new general
state-equivalence waiver. The native differential fixture and integer oracle
separately establish exact projection outputs and register/FP-state preservation.


Final gates project-gate-040, project-gate-040-off (CUSTOM5),
project-gate-040-original and project-gate-060 pass. All 246 inspected 060 FPU
sites match the earlier accepted 060 path, and its Project entry is original.
Normal and CHIP_ONLY builds have no relocation records; both FPSPs are unchanged.
All final test, scene, gate and timing captures use the identical normal slave.
Frozen artifact project-verified.slave and source/listing preserve the accepted
candidate. project-final-checks.json records these checks. Run
opt20_project_timing.py for an automatically state-matched extended pair;
opt20_project_test.py OUT then check_opt20_project.py OUT for arithmetic;
SCENE_NOMMU=1 SCENE_SWAPS=400 opt20_scene.py with PROJECT_OFF=1 for its control,
then enabled with the same TEST_SEED, followed by check_opt20_project_scene.py.
Use the exact build listing in DELTA_LISTING and the private project emulator.


## In-place edge extraction experiment (active)

ScanFillDown's edge setup has about 2.1 million visits in the accepted projection
profile. Replace MOVEQ #31 / AND.W with BFEXTU on register bits 27:5 for left and
right edges. The left three-instruction sequence remains eight bytes and the
right extraction remains four bytes, avoiding a jump or lookup-table allocation.
Current experimental source adds three PL_L records ($6c534/$6c538/$6c53c) only in
the 040 new-renderer patch list. Original/add-after-extraction flags and all values
should be identical. Static disassembly has no targets inside the replaced range.
The short screening run flat-edge-short remains 80/250. No gain claimed yet.
opt20_flat_edge_test.py tests all 65,536 low-word pairs with changing high words;
opt20_flat_edge_timing.py requires matching startup hunks, masking only the exact
12-byte edge switch. Current tmp/build is experimental; project-verified.slave
is still the accepted build. Reject the candidate if the extended pair gains none.


Edge-extraction fixture flat-edge-tests2 passes all 65,536 edge-word pairs,
with changing upper words, identical GPR outputs/CCR, an independent input/value
oracle, and four rejected corruptions. The first fixture stopped before execution
because its binary listing uses relocatable labels rather than the absolute label
format expected by that parser; the corrected fixture verifies its final BRA.S
encoding directly. No result from the first fixture is claimed.

The first long control flat-edge-off yields 597/2,000. Four candidate boots are
rejected before timing due to startup clocks 1556 versus control 1554. All four
rejected boots have the same recorded game state. flat-edge-common-state records
that state, selected before any candidate timing. A fresh control/candidate pair
flat-edge-match-off/on must both match its complete hunks (mask only the 12-byte
edge switch); the control gives 598/2,000. Keep all rejected attempts as evidence.


The common-state timing pair completed: flat-edge-match-off/on = 598/601 frames
(+0.5017%, 14.95/15.025 nominal fps); both short prefixes remain 80/250. Both
pre-timing checks match all three game hunks after masking only the 12-byte edge
patch. Slave, emulator and seed hashes are identical. Enabled profile has zero
FPSP entries and cache flushes. This is a small emulator gain, not a hardware
speed claim. Scene/CPU/build checks are underway before accepting the change.


Edge extraction accepted after final checks: five full displayed buffers/PNGs
match at controlled updates 1/10/30/45/57; each run retains next-field DMA and
shadow-copy coherence checks. 040/new, 040/original and 060 activation checks pass.
Normal and CHIP_ONLY builds have no relocation records; final normal bytes match
all native, timing, scene and gate captures. Both FPSPs and 246 inspected 060 FPU
sites are unchanged; 060 edge instructions remain original. Final files are
flat-edge-verified.slave/.s/.lst; checks in flat-edge-final-checks.json.
Reproduce with FLAT_EDGE_OFF=1 for the original edge bytes, MATCH_EDGE=1 plus
MATCH_ENTRY for the common-state timing filter, and END_FIELD=2002. The common
state is recorded in flat-edge-common-state with provenance; the initial failed
matching pair and all four rejected boots remain retained. Native fixture:
opt20_flat_edge_test.py OUT, then check_opt20_flat_edge.py OUT. Scene control:
FLAT_EDGE_OFF=1 SCENE_NOMMU=1 with opt20_scene.py; enabled uses the same TEST_SEED.
The historical flat-edge timing driver stops on four mismatches; the accepted
pair explicitly references the common state instead of relaxing comparison.


## Word-granularity shadow copy (active)

Current profile's leading slave costs are chip writes, not CMPM; listing checks
identify offsets $2472/$2478/$247e/$2484 as MOVE.L D1,(A0)+. Saved coherent
frames show only 1-2 changed longwords in many changed 16-byte blocks. Host
comparison of shadow-before versus fast-after predicts 40-55% fewer longword
chip writes for those particular frames (delta-word-baseline-analysis.json),
not a throughput prediction. Candidate compares each longword and writes only
changed words to chip and shadow; first-use initialization is unchanged.

Unpadded short trial delta-word-short remains 80/250. The final candidate pads
the shortened loop to its original 90-byte span, so every other byte of the
slave's code/data is identical to committed flat-edge-verified.slave. Benchmark
WORD_COPY_OFF restores the exact old 90-byte loop at the same address before
measurement. MATCH_ALL requires all three starting hunks equal without masking.
The current source/build is experimental and uncommitted; accepted build remains
flat-edge-verified.slave. Native copy/history/guard and matched timing tests run
before deciding whether this reduced chip traffic is worth the extra comparisons.


Word-copy native validation delta-word-tests passes all 80 full-buffer/history,
guard and pointer cases; the checker rejects four corruptions. Same-build control
delta-word-off reproduces the committed 601/2,000 result. Candidate on-1 is rejected
before timing for startup-state mismatch; on-2 matches all three complete hunks
without any masked bytes and proceeds. No timing conclusion yet.


Word-copy experiment rejected: the exactly matched-start pair gives 601 frames
for the old loop versus 600 for word-granularity copying (15.025 vs 15.0 nominal
fps). The reduced chip traffic does not overcome extra comparison/control cost
in this emulator. Native correctness tests pass, but no in-game image-equivalence
claim is made for the discarded candidate. Keep delta-word-rejected.s/.slave and
its tools for possible hardware investigation; do not present it as a speedup or
use it as the default build. Source restored to committed 3fafdb93.


## Eight-byte shadow-copy experiment (active)

The word-copy trial nearly halved measured CPU chip writes (3,110,105 to
1,563,831) but lost one frame. Test the intermediate 8-byte granularity using
the original CMPM/rewind/copy structure, two longwords per changed unit. Keep
the 90-byte loop span fixed with unreachable padding; all other slave code/data
bytes remain identical to committed 3fafdb93. Native copy/history/guard tests
and a same-build, full-startup-hunk-matched pair run before acceptance. Controls
restore the original 16-byte loop at the same address with WORD_COPY_OFF.
The source/build is currently experimental. The retained build is still
flat-edge-verified.slave. delta-eight-baseline-analysis.json compares expected
chip-write counts for 16/8/4-byte units in saved coherent frames.


## Benchmark cache-setup audit (active)

Source inspection of the private emulator's barto_gdbserver.cpp lines 739-745
shows that tfxmem flushes/writebacks 040 caches and invalidates instruction caches
before and after its write. Earlier optional-off controls performed that write
only on the disabled side. A pre-window instruction change therefore made cache
setup asymmetric even when game-hunk bytes matched; the early raw hunk snapshots
could also differ through dirty cache writeback. Do not assume all startup-state
variation is real game-state variation. Native functional checks explicitly
synchronize cached data, so their correctness evidence remains valid.

The legacy 8-byte matched run measured 601/607; it is not accepted as a balanced
performance result. opt20_balanced_profile.py now performs exactly ONE same-address,
same-length tfxmem write on either side (including rewriting the enabled bytes),
then checks full startup hunks and all reported CPU registers. Copy experiments
mask no game bytes. Edge/Project/exp comparisons mask only their exact instruction
patch. Balanced 8-byte off/on runs are in progress; recheck retained edge/projection
margins after this, rather than extrapolating earlier percentages. The original
recordings and rejected states remain retained. No guest logic or emulator timing
model has changed in this harness correction.


## Eight-byte copy retained with symmetric cache setup

balanced-eight-off/on uses exactly one same-address 90-byte tfxmem write on both
sides, identical slave/emulator/HDF hashes, and exact matching of all three startup
hunks and the complete reported CPU register state. Counts are 601/607 over 2,000
fields (+0.9983%, 15.025/15.175 nominal fps), short prefixes 80/81 (16.0/16.2).
Logical CPU chip writes fall 3,110,105 to 2,139,708 (31.2%); both profiles record
zero FPSP entries and zero in-window cache flushes. This supersedes the legacy
601/607 comparison as attribution evidence; hardware performance is unmeasured.

Native 80-case helper/history/guard/pointer checks and four negative controls pass.
Five complete displayed buffers and PNGs match through 57 controlled updates,
with next-field DMA and copy/shadow coherence checks in both runs. 040, original
rendering and 060 gates pass. Normal/CHIP_ONLY builds have no relocation records;
both FPSPs are unchanged. Every final capture uses the verified normal build.
Only bytes $2434..$248d of the slave code hunk differ from flat-edge-verified;
all surrounding code/data remains identical. Frozen delta-eight-verified.slave,
source/listing and delta-eight-final-checks.json preserve the result.

Reproduce: PATCH_KIND=copy CONTROL=1 opt20_balanced_profile.py OUT for control,
then omit CONTROL and use its TEST_SEED plus MATCH_ENTRY for enabled. Set
DELTA_LISTING to the exact new listing. Defaults to 2,000 measured fields. Native
helper tests use opt20_delta_test.py and check_opt20_delta.py. Controlled scenes
use COPY_BENCH=1, WORD_COPY_OFF=1 only on the control, SCENE_NOMMU=1 and the same
seed; check_opt20_delta_eight_scene.py compares the five complete displayed images.
Retained edge/projection gains still need the same corrected cache setup.


## Pause checkpoint, 2026-10-21

Symmetric edge recheck is verified: recheck-edge-off/recheck-edge-on-2 yields
598/601 publications over 2,000 fields, 80/80 over the first 250. All manifest
input hashes agree, one same-address/length tfxmem write is used on each side,
and all three entry hunks (only the tested instructions masked) plus reported
CPU registers match. Exact flat-edge-verified.lst reports zero FPSP exceptions
and cache flushes in both windows. Both captured slaves match the frozen build.
Summary: recheck-edge-summary.json. recheck-edge-on failed its entry guard before
timing; the bounded retry accepted on-2. No performance-based selection occurred.

Projection recheck-project-off gives 563/2,000. recheck-project-on fails the
entry guard [false,false,true,true] before timing. Its corrected A/B comparison
is incomplete; the historical +6.22% remains subject to the cache-setup audit.
Resume using project-verified.slave, PATCH_KIND=project, the existing control seed
and MATCH_ENTRY, keeping current production build unchanged. The retry helper
recheck_balanced_retry.py limits retries to three and only retries entry mismatch.

Pause requested by user. Current production build remains delta-eight-verified
(e0cd1fe7), rechecked byte-identical to tmp/build/release/TFX.Slave. Best corrected
extended result remains 15.175 nominal fps; short prefix is 16.2. No hardware
20 fps claim. Earlier entries describing running experiments are historical.
