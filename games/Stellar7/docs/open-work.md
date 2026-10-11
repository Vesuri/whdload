# Stellar 7: current work

## Performance plan (active)

Target: **60 Hz simulation (N=12), no interpolation**, on the supplied NTSC
Stellar 7. Every machine uses the same 1/60-second simulation timestep.
Rendering consumes the latest completed simulation state and runs as fast as
hardware permits, capped at the display rate. Do not add a previous/current
pose blend, extrapolation or an intentional one-tick display delay.

Separate 68000 and 68020+ implementation paths are allowed where measurements
justify them. They must preserve the same simulation timing and mapped gameplay
state. A slower CPU does not automatically select a lower tick rate. If the
A500 cannot meet the target after measured changes, report the remaining cost
and tradeoff to the user rather than silently reducing the rate.

Each implementation step ends with measurements in `docs/internals.md`,
commands in `docs/development.md` and a coherent commit following AGENTS.md.
The source default is N=12. Steps 1 and 2 are complete; simulation cost is
the next step.

### Existing evidence and limitations

The baseline matrix, substep parameterization and lower-rate experiments are
complete and retained in internals. N=12 release and VERIFY matched the original
baseline bytes. All 78 private fixture combinations across six rates passed;
285 cross-N comparisons have classified differences. Lower rates change some
encounter trajectories, not just presentation frequency.

N=1 met the former A500 native-presentation threshold, but its 200 ms timestep
is rejected for responsiveness. Native FPS remains a comparison, not a gate
that permits lowering the required 60 Hz simulation rate. The lower-rate
measurements remain useful cost evidence, not the active gameplay design.

Retained N=12 heavy-combat profiling reports about 90004 main-context cycles
per A500 update, 97.4k main-context cycles available per NTSC field and about
1.03M cycles for a heavy render. Those captures show a substantial cost problem;
they do not prove that a different 60 Hz implementation is impossible. Small
isolated instruction savings alone are unlikely to close that measured gap.
Re-measure through the updated toolchain before making new performance claims.

### Step 1: Restore and verify the 60 Hz baseline

Status: complete. The restoration reference release/VERIFY match the retained
N=12 bytes; current input-history builds add ABI 30 and new hooks. All 72
reference baseline cells, A500 heavy-combat capture, 56 cross-CPU/PAL
and 64 retained-baseline state comparisons pass. The 16 SLOW_DRAW/lifecycle
comparisons, disabled-code preservation, hook audits, actual play60 smoke and
19 tooling tests pass. Accepted emulator settings and observed clocks cover
all eight configurations. Evidence and measurements are in internals and
`tmp/restore60`. The known A500 performance limitation remains; restoring the
60 Hz default does not imply sustained 60 Hz in heavy combat.

- Smoke-test the shared AmigaXDev launcher, debugger and trace readers. Verify
  observed NTSC timing and actual chip/slow/fast memory, including stock A1200.
- Restore S60_SUBSTEPS=12 as the SIM60 default and its displayed 60 Hz label.
  Compare release and VERIFY with the retained N=12 baseline bytes before
  making gameplay changes. Keep explicit lower-rate builds as diagnostics.
- Run native/SIM60 baselines serially on A500, stock A1200, A1200 + fast RAM,
  68030/50, 68040/25 and 68060/50. Use SOL 600→1500, type-10 1800→2400 and
  4500→5400, boss 3500→4100, and A500 heavy combat 600→5400. Retain the PAL
  A500/68060 timing checks as compatibility checks; the game target is NTSC.
- Report updates/s, presentations/s, pending counts over time and update-start
  gaps with the appropriate instruments. Separate backlog repayment from
  sustained real-time performance and window-local gaps from global bounds.
- Recheck matched-tick cross-CPU/SLOW_DRAW state, death/Continue, exits,
  disabled bytes, hook audits and the actual play60 launcher.

### Step 2: Input belonging to each tick

Status: complete. The native field callback records controls, and each tick
selects its own field sample. The native key queue retains its capacity and
ordering while deferring future presses. Modal entry/return atomically exclude
paused fields from both clocks; menus keep live controls. Session resets and
finite-history recovery are explicit and instrumented.

Elapsed-field held, press/release and firing edges pass across A500, stock
A1200, 68020 + fast RAM, 68060/50, delayed drawing and PAL compatibility checks.
Native-reference queue, decoding, direction and button checks pass. Long-pause,
overflow, preference, death/Continue/No, exit, disabled-byte, hook and actual
launcher checks are recorded in internals. No unexplained mapped gameplay
differences remain in these comparisons; deferred projection scratch varies.

Input-consumption and render-handoff delays are measured in fields. They are
not physical-device or display-scanout latency bounds. Input history fixes
which controls overdue ticks receive; reducing catch-up delay remains part of
the performance work. Physical-control and visible-response playtesting remains
in step 6. No interpolation has been added.

### Step 3: Reduce the cost of the 60 Hz simulation

Profile complete updates in SOL, type-10 combat and boss scenes on 68000 and
68020+. Separate integration, collision/geometry, AI, native-cadence work,
projection and presentation bookkeeping. Identify repeated work and dependencies
before caching, moving or eliminating any of it. Preserve collision frequency,
RNG ordering, native decision cadence, rounding and all gameplay effects.
Do not make the simulation cheaper by skipping owed ticks or slowing game time.

Prioritize structural savings established by profiles. Use separate 68000 and
68020+ paths when beneficial; dispatch safely and retain a correct fallback.
Validate each path with native-reference fixtures, matched-tick gameplay/HUD/
fresh-projection state and SLOW_DRAW. Compare against the N=12 reference;
no unexplained gameplay divergence is accepted. Report complete-update and
whole-scene effects, including drawing and interrupt costs.

### Step 4: Reduce rendering cost without interpolation

Render the latest completed state. Avoid an extra draw of the same completed
state on fast machines, using measured pacing that still advances the simulation
clock correctly. Preserve native VBL presentation and buffer ownership.
Rendering must not mutate gameplay state or introduce a one-tick pose delay.

Profile complete renders on A500 and stock A1200, extending capture windows
when needed. Candidates include the polygon pipeline at $14a9e, transforms,
vertex cache, perspective division, blitter work and interrupts; star/sprite
work at $18340/$1bc94; background fill; HUD; and redundant projection.
Use CPU-specific paths where measured faster, pixel/display-DMA comparisons
and matched-tick state checks. Sound-handler changes require identical Paula
writes and separate audio validation. Apply the measured 3% whole-frame rule;
retain original code where a replacement is slower.

### Step 5: Fast-CPU presentation ceiling and sustained-load checks

Measure field boundaries, buffer handshakes, blitter/chip-bus contention and
cache policy on 68030/040/060 at N=12. Determine the cause of the presentation
ceiling rather than extrapolating from CPU clock speed. Use SWAP_ONLY and
complete-call timing where applicable; check actual cache configuration.

Re-run the full matrix and extended combat. Require sustained 60 Hz game time
with no accumulating pending-update trend, preserving gameplay across CPUs.
Report presentation rates and input latency alongside that result. Native FPS
is a performance comparison; do not trade away the 60 Hz requirement to match
it. Any unresolved A500 limitation must be explicit before release decisions.

### Step 6: Release validation and playtest

Run native twins, full encounters, boss kills/ending, natural deaths,
Continue/No, level/UI transitions, powers, jump and preferences at N=12 on
both CPU paths. Repeat disabled-byte preservation, hook/indirect-entry checks,
diagnostic exclusion and play60 smoke tests. Keep PAL timing coverage separate
from claims about the supplied NTSC game's audiovisual behavior.

Playtest real controls, sound, original-reference pace and responsiveness.
Only after correctness and performance validation consider enabling SIM60 in
the normal loader. Update current docs and remove unused tools.

## Remaining release validation

The conversion remains experimental. The plan above replaces lower-rate
selection and interpolation. Input history is complete; broader coverage includes:

- Broaden full-encounter coverage at 60 Hz: boss kills and ending,
  later natural deaths, level and UI transitions, lethal shield/type-43 hits,
  boss helpers and mine detonation. Controlled placement, native twins and
  sampled mapped-state comparisons do not cover every encounter branch.
- Extend power checks to active-power cycling and combat effects, and jump
  checks to arbitrary terrain and midair impacts. Check combined preference
  changes, re-enabling settings and additional native dialog paths.
- Confirm original-reference gameplay pace and the reconstructed loader's
  behavior through playtesting. The modern KickEmu loader is not a byte-identical
  rebuild of the supplied 2008 slave.
- Finish replacement-semantic and indirect-entry coverage before enabling
  SIM60 in the normal loader. Static patch-boundary checks and observed
  calls/returns leave exceptions, external-source returns and unseen paths
  outside coverage. Keep disabled-code preservation and diagnostic exclusion
  in the final release checks.
