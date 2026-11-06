# Step 9: native 040 maths

Completed. Evidence is under
`tmp/step9/`, relative to this harness. No real Apollo timing claim is made.

## Baseline and scope

The step-8 slave, retained in `tmp/step8/final-window-seed`, presents 73 frames
in the strict 040 NOMMU [2,252) vblank window and enters FPSP 3,066 times: 42 per
frame at six sites. `baseline-retry` is the original observer; `baseline-operands`
uses a private read-only operand/result observer. Both have 73 publications and
the same final image. Some raw state/cadence differs between these cold boots;
this is not a new state waiver. The first sandboxed attempt could not connect to
the local debugger; its failed output is retained as `baseline`.

The seed contains the actual baseline slave. The harness's copied host build in
`baseline-operands/slave.slave` was already newer; it is not the slave inside that
retained seed. Use the seed and live opcode evidence to identify that run.

Default FPCR is zero throughout the captured flight. Input magnitudes are below
0.46. `step9-math-observer.patch` records the source register immediately before
each original instruction and destination immediately afterward, including all
80-bit value bits. It changes no guest memory or execution semantics. It is
built privately from the retained step-8 backend by `build_math_emulator.py`.

## Complete FINTRZ/FMOVECR coverage

Commit `ee06330`. `generate_native_fpu.py` reads the pristine hunk and retained
step-6 disassembly, guards all original bytes and emits `native_fpu_sites.i`.
There are 146 FINTRZ and 93 FMOVECR instructions. An independent aligned-word
scan finds exactly the same 239 offsets, with no duplicates or missing sites.
The ROM constants are $0f=0, $32=1 and $34=100; all are exactly representable in
single precision, and all destination-register combinations are tested.

The 16 FINTRZ register combinations truncate the extended significand, preserving
signed zero and all finite integer magnitudes. They do not overflow through a
32-bit integer conversion. Discarded fractional bits set INEX2 and accrued INEX.
FPCR, integer registers/CCR and non-destination FPU registers are preserved.
NaN/infinity use the original instruction and installed FPSP safety net.

`static-tests2` compares all 31 helpers against the original instructions in the
strict emulator. All 1,147 cases match every FPU register, FPCR and FPSR, covering
signed zero, fractions, random values, 32-bit boundaries, 64-bit significand
boundaries and large finite values. The earlier `static-tests` exposed missing
INEX2 status; that was corrected before committing. Extended-memory padding is
unspecified and is excluded from value comparisons.

Only the 040 new-FPU patch list is expanded. The 060 continues using its original
list. CUSTOM5 still disables FPU patches. Existing other executables keep their
original helpers. No FPSP executable/source has been changed.

## Native transcendental implementation

Six four-byte instructions call native helpers through existing-style low-page
JSR trampolines:

| Site | Operation | Source -> destination |
|---|---|---|
| $50f82 | tan | FP7 -> FP0 |
| $5169e | sin | FP7 -> FP0 |
| $516b6 | cos | FP7 -> FP0 |
| $517a4 | atan inside atan2 | FP1 -> FP5 |
| $517f2 | atan | FP7 -> FP0 |
| $5183c | asin | FP7 -> FP0 |

The surrounding library wrappers and their error/atan2 quadrant handling remain.
Sine/cosine reduce by a three-piece pi/2 and evaluate Taylor polynomials on
[-pi/4,pi/4]; tan divides their results. Atan uses a reciprocal above one, two
half-angle reductions and a convergent odd series. Asin uses
atan(x/sqrt((1-x)*(1+x))), with explicit endpoints. Arithmetic uses supported
040 operations. Non-default FPCR, nonfinite inputs, trig arguments beyond 2^20
and out-of-domain asin fall back to their original FPSP instruction. Extreme
underflow/denormal operations may also invoke the retained safety net. This is
zero traps in the measured flight, not removal of FPSP for every possible input
or replacement of every unobserved transcendental site.

`test_native_math.py` tests all 801 distinct captured operands against every
helper, plus 65 additional unique boundary/random inputs: 5,196 cases. It executes
the candidate and original FPSP instruction on the guest, retaining complete
register results. `math_oracle.py` independently evaluates at 80 decimal digits;
`check_native_math.py` compares the actual extended values, not merely host
float prints. All final cases meet 2e-15 absolute error for |result|<=1 and 2e-15
relative error otherwise. The observed maximum is 2.54e-16. All untouched FPU
registers and FPCR match, including signed-zero results. Game disassembly has
no FPSR/FPIAR reads; it initializes FPCR to zero at $50f4c.

The broad tests found 28 FPSP outliers outside the recorded gameplay operands:
asin(+/-1), tan near +/-pi/2, and sin/cos/tan at large arguments. The candidate
passes the independent oracle for these. The current FPSP source's `asinbig`
line has its intended comparison after a comment, consistent with the endpoint
failure. The large-angle FPSP failures have not been fully diagnosed. They are
reported, not used as truth or changed in this step. The initial native tan test
also exposed insufficient reduction accuracy near pi/2; adding the third pi/2
piece fixed that before final validation. Earlier failed fixtures remain saved.

The candidate sets INEX2/accrued INEX for nonzero transcendental inputs and keeps
zero cases exact. Small low-order result differences from FPSP are expected;
these are not bit-identical arithmetic replacements. Real-040 accuracy and
speed still need the planned hardware check.

## Reproduction

From the game directory, use fresh output directories and only one emulator run
at a time:

```
bash tools/build.sh
FSUAE="$PWD/tmp/step9-emulator/fs-uae/fs-uae" \
  python3 tools/test_native_math.py tmp/step9-math-repeat
python3 tools/check_native_math.py tmp/step9-math-repeat/results.json
python3 tools/step9_runs.py tmp/step9-flight-repeat
```

The private backend requires local debugger socket access. Never reuse a seed
across changed builds, except deliberately running a retained baseline; record
that distinction explicitly. Fixture memory writes and register changes exist
only in test runs. Normal performance runs use read-only observation.

## Timing and regression evidence

`final/profile` and `final/profile-repeat` both present 73 frames/250 vblanks
(nominal PAL 14.6 fps), with zero FPU exceptions of any kind. Only level-2/3/4
interrupts are observed. All 245 patched opcodes are checked in live code.
The unchanged baseline has 3,066 F-line exceptions. No measured frame-throughput
increase is claimed: the frame total remains 73. Emulator scheduler costs are
not native 040 instruction latency or real Apollo FPS.

The native timing pair has identical publication/input events and final image.
Raw hunk 2 matches; hunks 0/1 differ only in the five known absolute timers
(two-vblank origin) and three masked-sprite scratch pointers at $4e52e/$4e532/
$4e536. Those pointers are overwritten at $4e402..$4e414 before each sprite-plane
render, and may describe different in-progress work when the vblank breakpoint
interrupts the CPU. This is an explicit raw-state failure, not a waiver.

Baseline versus candidate timing runs have different publication cadence and
final screenshots despite identical 73-frame totals. Changed code/relocation
addresses, elapsed clocks, simulation cadence and low-order maths affect raw
hunks. `final/baseline-state.json` is an exploratory pointer/patch/clock-normalized
diff, not an equivalence proof or an exclusion mask accepted for testing.

At a controlled simulation timestep and synchronous input, all five original
step-8 baseline/candidate images match byte-for-byte at publications 1,10,30,45,57.
`final/baseline-scene` and `final/native-scene` use the step-8 fixture: CPU held
after COP1LC publication while DMA captures the selected buffer. Each validates
all eight bitplane sources. These fixtures are absent from timing/release builds.

The shared-emulator ordinary cold-boot matrix in `final/regression` is retained
including its nonzero exit status:

| CPU | Pair images | Raw state | Clock-relative state | Clock delta |
|---|---|---|---|---|
| 040 MMU | first three match; swap 30 differs | differs | differs | -3 |
| 020 | all match | equal | equal | 0 |
| 030 + 68882 | all match | differs | equal | +1 |
| 060 | all match | differs | equal | +1 |

The 040 pair's initial vblank phase differs; subsequent real-time simulation
can diverge. It is not reported as passing repeatability. All 245 FPU sites on
060 are byte-identical to step 8, including the existing 060-specific behavior.
No 030/060 allocation or arithmetic path changed. The 020/030/060 image checks
pass; no new full-state mismatch acceptance is inferred. The final checker
reports the failed gates separately instead of hiding them behind a pass label.

## Fully accounted controlled end state

`controlled-off` and `controlled-on` run the same final slave with CUSTOM5=1/0,
matching memory layout, fixed delta=5, resolved input and publication 57 as the
end checkpoint. This also verifies that the disable option and FPSP safety net
remain functional. The three game-hunk bases are identical.

After accounting for the 245 intentional instruction replacements, only four
known clock fields and 20 double-precision cells differ. The clock fields are
code $4d85a/$4d884 and data $10678/$13de0, each two vblanks earlier in the native
run. No other code or BSS byte differs. All five screenshots match again.

`controlled-numerics.json` lists each changed double, both values and its error.
These include alpha, tail lift coefficient, forces/moments, angular acceleration,
angular velocity, pitch/heading, left/right angles and stream velocity. Names
come from the beta data-hunk mapping; data $f760 is left unnamed and its double
loads/stores are verified at code $2b02e/$2b05a/$2b06a. Most changes are a few
least-significant bits. Largest accumulated absolute difference after 57 updates:
7.276e-12; largest abs(diff)/max(1,abs(reference)): 2.219e-14. Per-call error and
accumulated simulation error are distinct measurements. `check_step9.py` accounts
for every changed byte in this comparison; no unspecified state is excluded.
This explains arithmetic state differences rather than claiming bit equivalence
or extending the user's earlier replay waiver.

A further `modes` fixture runs 1,147 static helper cases across all twelve FPCR
precision/rounding combinations ($00..$b0), matching FPSP values, FPCR and FPSR.
Normal and CHIP_ONLY source builds pass. Final rebuilt normal slave bytes equal
the tested build; both FPSP binaries remain byte-identical to step 8. The 060
live instruction comparison confirms unchanged FPU patches.

Implementation commits: `ee06330` (complete FINTRZ/FMOVECR coverage) and `29a6c7e`
(native transcendental helpers). Step 9's exit is complete: zero FPSP entries,
explained arithmetic/end-state differences and measured throughput. Ordinary
040 MMU replay repeatability remains a documented failing gate, not waived.
Step 10 is the rendering port; use the step-6 ABI mappings for the fill routines.
