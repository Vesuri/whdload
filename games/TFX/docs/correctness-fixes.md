# Step 7: missing correctness fixes

The two correctness fixes are implemented and committed. All addresses below
are pristine tfx.020 code-hunk offsets. Full-state replay diagnostics are separate
from the passing targeted correctness checks; their remaining failures are explicit
below and are not newly accepted exceptions.
Evidence lives under `tmp/step7/`; fixtures and private emulator are ignored.

## Scope audit

The step 6 inventory covers all 60 active address-bearing plain-TFX patch rows.
The missing independent correctness patches are the maximum-object sort and the
joystick keyboard-synthesis bypass. Both belong outside the rendering options.
The other missing rows are fast-memory relocation (step 8), rendering helpers,
uncapped/one-frame timing and the zoom/model adapters needed by those options
(step 10). Existing 060 arithmetic hooks remain unchanged.

## Maximum-object sort

The original full AddObject path sets D1=348 and quicksorts indices 1..348,
although the arrays have only 348 elements (0..347). It then invokes the old
insertion pass with a similarly excessive bound. The regular DrawObjects call
also uses the original insertion code. The port reuses the existing `do_sort`
with hooks at $5efbe (32 bytes) and $5f03e (14 bytes), and sets `depth_ptr` to
$5bf16. `_obcount` is six bytes before depth; the parallel index array is 696
bytes after depth. No new sort implementation or CPU-specific behavior is added.

Tests execute the loaded game's hook sequences, not a Python implementation.
The baseline fixture has count 348, D1=348, a minimum sentinel at index zero,
348 depth/index pairs, and an eight-byte guard after the index array. Four
patterns cover ascending, descending, equal and seeded random depths. Candidate
checks additionally execute the complete AddObject full-array path, validate
its returned replacement index, and test DrawObjects counts 0,1,2,6,7,14,15,
347,348. Checks cover signed ordering, permutation, depth/index pairing,
unused array tails, guard bytes, preserved registers and stack balance.

## Joystick double launch

The original ReadMouse copies the configured fire key from $40f62 to the keyboard
queue byte at $40d16, after it has already set the joystick fire bits. The existing
integer-build fix branches from $4e080 to $4e0a6, skipping this redundant key
synthesis. The fixture selects a weapon with Return, presses joystick fire at
swaps 5 and 15, and releases at 7 and 17. It also presses the configured keyboard
fire key at swaps 25..27 (stored key code minus one: Space in this fixture). Breakpoints record FireWeapon and actual
LaunchMissile entry/completion, rather than treating input bits as launches.

## Test harness pitfalls

- HDF seeds contain the installed slave. A copied replacement file in the host
  runtime drawer does not replace the slave inside an existing seed. Candidate
  runs use fresh seeds; baseline probes explicitly reuse the preserved step 5
  seed. Runtime hook bytes distinguish the actual installed code. A baseline
  launch manifest's host slave hash alone is not proof of the disk-image slave.
- The shared gdb stub cannot write registers/memory. The local step 7 emulator
  adds fixture-only `tfxmem`, `tfxreg`, and `tfxsync` monitor commands, derived
  from the configured step 5 observer tree. Shared tools remain untouched.
- The stub's receive buffer is only 512 bytes and does not assemble large
  packets. Writes use 32-byte chunks; every fixture is read back before use.
- Debugger reads bypass CPU caches. Fixture writes push and invalidate dirty
  data first; result reads explicitly synchronize caches. The inherited
  `cpu_invalidate_cache` 040 helper passes a zero cache mask and does not perform
  this operation, so the fixture uses the existing CPUSHA/CINVA data-cache
  operations explicitly. On 030 it uses the 030 invalidation helper.
- Fixture cache operations affect timing and are excluded from ordinary replay
  and fixed-window measurements. Normal runs never call these commands.
- Early directories `sort-before*`, `sort-after`, `sort-cases-040`,
  `sort-verified-040`, `sort-final-040`, and `sort-baseline` are discarded harness experiments.
  Only the final cache-coherent baseline and successful final case reports are
  evidence. No conclusion rests on the failed command-length/cache experiments.

The full AddObject ABI already changes D7 before saving registers: at the maximum
count its low word becomes 348. The fixture checks that existing clobber explicitly;
it does not require a register the original function never preserved to survive.

## Sort results (candidate)

`sort-baseline-coherent/results.json`: all four full-array baseline fixtures
corrupt the index permutation and the guard. `sort-pass-{040,030,060}/results.json`:
all 39 candidate cases pass. The 020 configuration has no FPU and cannot execute
tfx.020; plain-TFX flight regression is separate.

`sort-window/counts.json`: 57 publications in [2,252), unchanged from strict
step 5 (nominal PAL 11.4 fps; emulator A/B only). Publication cadence does change:
for example swap 4 publishes at vblank 11 instead of 12; swap 20 at 71 instead of
72. Recorded right-bank input still starts at vblank 32 and stops at 71. The
end-of-window cockpit image differs slightly in flight values and bank angle.
This is not byte/image equivalence or an extension of the step 2 clock-origin
waiver. The game samples elapsed time during updates; changing sort execution
cost changes those sample boundaries even without changing the total frame count.
The independently checked sort contract preserves every depth/index pair and
array bound. A repeated candidate window is checked separately below.

Sort committed as `7a9ea96`. Reusing the exact `sort-window-seed` for
`sort-window-same-seed` gives identical event counts, screenshot and all three
captured end hunks. The separately packed `sort-window-repeat` also gives 57
publications but differs at one swap/vblank boundary; it is not the deterministic
repeat. Freeze the candidate seed once, then reuse it for repetitions.

## Fire results (candidate)

`fire-control-before` (frozen step 5 slave): distinct completed missile allocations
at swaps 6,15,16,25. The second joystick press creates two missiles. The keyboard
control at swap 25 creates one. The completion marker is $27040, after missile
initialization returns and before A2 is restored; A2 identifies the newly created
missile. Entry/completion counts match and every recorded missile pointer differs.

Candidate `fire-after-{040,030,060}`: three distinct completed launches, at swaps
5,16,25 — one for each press. `fire-original-040` (CUSTOM4=30, original renderer
plus FPS marker): swaps 6,16,25, also one per press. The source hook is outside
all rendering conditions. `fire-hook.bin` verifies the installed $6024 branch.
The event label `synthesis` denotes reaching the hook address, including the
replacement branch; it is not evidence that the skipped byte copy executed.
`fire-before` and `fire-baseline` were exploratory joystick traces before the
configured keyboard-fire control was added; use `fire-control-before` for the
complete before case.

Fire fix committed as `18f4c42`. The isolated sort-only baseline,
`fire-sort-only-before-checked`, creates five distinct missiles at swaps
5,6,15,16,25: two per joystick press and one from Space. This separates the fire
fix from the sort change. An earlier `fire-sort-only-before` run stopped while
attempting to read A4-relative globals at the asynchronous ReadMouse hook: A4
can belong to an interrupted renderer there. The final probe records registers
and the actual launch's A2 pointer, without assuming a global A4 in interrupts.

`final-window` and `final-window-repeat` both present 57 frames and have identical
publication/vblank/input events. They do **not** have identical final pixels or
game state. At flight entry their only differences are the five absolute clock
values (one vblank apart); by the end, additional dynamic game state differs.
The step 2 clock-origin waiver does not cover this 040 NOMMU result. No new waiver
or exact final-window equivalence is claimed. Frame totals remain reproducible;
strict MMU functional replay is checked separately. Before step 8's identical-
screenshot exit check, retain a controlled game-time/scene comparison alongside
ordinary throughput measurement; matching publication events is insufficient.

## Reproduction

From the game directory, build the private fixture backend once:

```
python3 tools/build_fixture_emulator.py
bash tools/build.sh
export FSUAE="$PWD/tmp/step7-emulator/fs-uae/fs-uae"
```

The builder refuses to overwrite its existing directory. It copies the configured
step 5 private observer tree, applies `tools/step7-fixture.patch`, and rebuilds.
These fixtures never modify pristine executable files or the shared emulator.

Use new output names. For a new full-array baseline run, keep the preserved step
5 image (runtime hooks are checked, since that seed contains the original slave):

```
TEST_SEED="$PWD/tmp/step5/seed-strict" python3 tools/probe_sort.py tmp/step7-new-sort-before
python3 tools/check_sort_cases.py tmp/step7-new-sort-040
python3 tools/check_sort_cases.py tmp/step7-new-sort-030 030
python3 tools/check_sort_cases.py tmp/step7-new-sort-060 060
```

Run the fire tape against the retained sort-only seed and the current build:

```
TEST_SEED="$PWD/tmp/step7/sort-window-seed" python3 tools/probe_fire.py tmp/step7-new-fire-before
python3 tools/probe_fire.py tmp/step7-new-fire-040
python3 tools/probe_fire.py tmp/step7-new-fire-030 030
python3 tools/probe_fire.py tmp/step7-new-fire-060 060
CUSTOM4=30 python3 tools/probe_fire.py tmp/step7-new-fire-original
```

Normal performance and functional runs contain no fixture injection/cache flush:

```
python3 tools/step7_window.py tmp/step7-new-window
TEST_SEED="$PWD/tmp/step7-new-window-seed" python3 tools/step7_window.py tmp/step7-new-window-repeat
python3 tools/step7_regression.py tmp/step7-new-regression
python3 tools/check_step7.py
```

The final command validates the retained canonical `tmp/step7/` evidence, not the
newly named runs. It reports the NOMMU state/image mismatch explicitly, checks
completed launch counts and missile identities, checks sort boundaries and ABI,
and reports each backend's full-state gate separately. It does not reinterpret
a failed state gate as a passed equivalence test. `step7_regression.py` itself
returns nonzero when the original state rules are not met.

## Full replay diagnostics

Each pair uses one frozen seed and checkpoints 1,10,20,30. The shared
emulator hash remains identical to step 2. Both full-state matrix commands
return nonzero; this is retained as a failed diagnostic, not waived.

| Backend | CPU | Images equal | Raw state equal | Clock-relative state equal | Clock delta |
|---|---|---|---|---|---|
| regression | 040 | True | False | True | -1 |
| regression | 020 | True | False | False | -2 |
| regression | 030 | True | False | False | 1 |
| regression | 060 | True | False | False | 1 |
| regression-shared | 040 | True | False | True | 1 |
| regression-shared | 020 | True | True | True | 0 |
| regression-shared | 030 | True | False | False | 4 |
| regression-shared | 060 | True | True | True | 0 |

On the shared backend, 020 and 060 pass exact raw-state replay. Strict 040
differs only in the five timer values, by one vblank. 030 additionally differs
in the audio queue near $4d72e/$4d77a..$4d7ef, which is updated by the channel-3
audio code; these bytes are not masked out. The old timer waiver is not extended.
Both CPU matrices repeat all four images. Targeted correctness fixtures and
launch counts pass independently of these broader state-equivalence failures.
