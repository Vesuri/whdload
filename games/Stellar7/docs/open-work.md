# Stellar 7: current work

## Performance plan (active)

Target: **fixed real-time simulation, with separate CPU rates and no
interpolation**, on the supplied NTSC Stellar 7. The 68020+ path retains
60 Hz (N=12). The selected 68000 default is
15 Hz (N=3), preserving real-time game speed; 20 Hz remains an explicit
playtest option. A rate is fixed for a session;
it does not vary with rendering speed. The 5 Hz / 200 ms timestep is rejected.

Rendering consumes the latest completed state and runs as fast as hardware
permits, capped at the display rate. Do not add a previous/current pose blend,
extrapolation or an intentional one-tick display delay. Owed ticks must still
run with their recorded controls. CPU paths must preserve elapsed game time;
cross-rate trajectory differences must be identified and explained.

Each implementation step ends with measurements in `docs/internals.md`,
commands in `docs/development.md` and a coherent commit following AGENTS.md.
The source default remains N=12; the 68000 playable build explicitly selects
N=3. Steps 1–5 are complete. Step 6 remains: broader release validation and
physical-control, pace and audio playtesting.

### Existing evidence and limitations

The baseline matrix, substep parameterization and lower-rate experiments are
complete and retained in internals. N=12 release and VERIFY matched the original
baseline bytes. All 78 private fixture combinations across six rates passed;
285 cross-N comparisons have classified differences. Lower rates change some
encounter trajectories, not just presentation frequency.

N=1 met the former A500 native-presentation threshold, but its 200 ms timestep
is rejected for responsiveness. Native FPS remains a comparison. Fresh
selected-rate measurements establish real-time A500 throughput in the tested
heavy route; older lower-rate captures remain state references, not current
performance evidence.

Fresh N=12 profiling measures about 90258 cycles per A500 heavy-combat update.
The lower 68000 rate resolves the measured update-debt problem in this route,
with current early/late presentation comparisons recorded in internals.
Step 5 now measures the fast-CPU drawing limit and extended combat through
natural death. The corrected selected-rate matrix passes; broader encounters
and physical-control playtesting remain in step 6.

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

### Step 3: CPU-specific fixed rates and simulation optimization

Status: complete. Fresh 10/15/20/30 Hz A500 measurements select 15 Hz (N=3)
for combat throughput and tick granularity; 20 Hz remains a playtest override.
The rate-selection reference sustains 15.0 updates/s and 3.675 presentations/s over
80 seconds, with pending updates 1→1. The launcher selects separate 68000 and
68020+ builds; the latter remains 60 Hz. No interpolation, discarded ticks or
render-dependent rate is added.

Complete-update profiles cover SOL, type-10 and boss on both CPUs. The
stationary-star candidate is not retained: its selected-rate presentation
benefit does not justify the extra state/hooks. Measurements and the retained
ordinary implementation are described in internals. Cross-rate encounter
trajectories remain different for the classified timing/integration reasons;
no new unexplained same-rate differences occur at the checked boundaries.

Selected-rate input, delayed-render state, death/Continue/No, normal/early exits,
disabled bytes, hook audits, diagnostic exclusion and both actual launcher
paths pass. All six rate builds and the 20 Hz override pass. Full-encounter,
physical-control and audible-output playtesting remain release work. Rendering
measurements and validation follow in step 4.

### Step 4: Reduce rendering cost without interpolation

Status: complete. The 68000 build batches BLIT completion interrupts inside
native polygon ownership, restoring the saved enable bit before DisownBlitter.
The 68020+ polygon path stays native: stock A1200 traces contain no BLIT IRQs.
Both builds avoid drawing an already-presented tick and refresh the native
reticle cache on its simulation clock, removing a render-dependent stale flag.
No interpolation, pose delay, sound-handler change or rate change is added.

Current A500 heavy-combat presentation rises from 3.675 to 4.031 FPS while
completing 1200 updates in 80.133 seconds; pending samples remain bounded and
recovering (1–5). Lossless held-display comparisons pass SOL, boss and combat,
with the reticle included. Same-rate CPU/delayed-draw state, reticle native
fixtures and negative controls pass. Final build, input, lifecycle, disabled-byte,
hook and launcher evidence is recorded in internals. Step 5 records the
68030/040/060 presentation investigation and sustained-load evidence.

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

Status: complete. Read-only beam timing, independent scanout traces and
live CACR observations are recorded in internals. SOL and late-combat windows
on 030/040/060 do not enter the optional VBL wait; drawing dominates the
observed presentation call. The 040/060 configurations have instruction caching
enabled and data caching disabled. These are emulator observations, not real
accelerator timing guarantees.

All eight corrected extended-combat runs reach natural death at the selected
average rate, with 174 same-rate CPU/PAL and 228 before/after comparisons passing.
A500 covers 114.133 active seconds at 14.982 updates/s and 3.934 presentations/s;
sampled debt is 1–3, starting at 1 and ending at 3. Stock A1200 maintains average game speed but shows large catch-up
bursts and low presentation rate. All eight corrected input fixtures pass their recorded-control and native queue
assertions, with eight same-rate and sixteen before/after state comparisons.
Corrected build identities, hook checks, 38 delayed-draw comparisons and sixteen
lifecycle comparisons pass, including both disabled-code checks. Matched rendering-bypass and instant-blitter diagnostics also pass: the native
handoff can sustain 60 presentations/s without full drawing, and instant blits
nearly double ordinary 68060 SOL presentation. The corrected matrix passes all 40 SIM60 cells and 350 same-rate/before-after
comparisons, with 40 native measurements reused after exact-byte verification.
The buffer-reuse correction is enabled. The boss display check exposed a native
cockpit update with a partial scanout transition: exact native icon images and
read-only routine timing classify the 23 changed words. It is explicitly not a
stable-pixel pass; no general HUD mask is added. A second finding in
PAL A500 late combat is classified as the native energy-bar draw/copy (28 words),
confirmed by routine timing and native instruction guards. All 18 display windows are reviewed (16 strict stable, two classified native HUD
updates). Extended combat, input, lifecycle and both actual-launcher smoke checks pass.
Both fixed rates remain unchanged.

The reported blinking has a captured buffer-reuse hazard: in the 68060 SOL
trace, nine consecutive-field pairs still fetching the same bitmap contain
changed pixel words. The phase observer starts the next draw in the presentation
field, before scanout changes bitmap in the following field. Native code
$2b96–$2ba0 waits for the field counter to advance before drawing; SIM60 bypasses
that wait. Complete bitmap addresses per field therefore did not prove safe
buffer ownership. The normal-speed comparison has zero unstable fields for native/candidate
and 20 for the control across 100 fields each. The source now defers the next
draw until the native saved field changes, without stopping simulation polling.
Build/off-byte identities and final-source normal-speed checks on A500/68060
pass, with 100 stable displayed fields each and matching endpoint gameplay.
The completed matrix records both current corrected performance and
the measured presentation cost against the unfixed build. The final source
identity matches all forty fresh matrix cells; both launcher releases match
the audited builds. Broader encounter, physical-control and audio checks remain
in step 6.

Measure field boundaries, buffer handshakes, blitter/chip-bus contention and
cache policy on 68030/040/060 at N=12. Determine the cause of the presentation
ceiling rather than extrapolating from CPU clock speed. Use SWAP_ONLY and
complete-call timing where applicable; check actual cache configuration.

Re-run the full matrix and extended combat. Require sustained real-time game speed at each selected fixed rate
with no accumulating pending-update trend, preserving gameplay across CPUs
at the same rate.
Report presentation rates and input latency alongside that result. Native FPS
is a performance comparison; retain 60 Hz on the 68020+ path. Any unresolved A500 limitation must be explicit before release decisions.

### Step 6: Release validation and playtest

Status: in progress. All 26 native-reference fixture groups pass on the
selected 15 Hz A500 and 60 Hz 68020 paths. Combined preference changes and
re-enabling pass through the native menus at both rates. Input-driven cycling
through six overlapping powers and a jump/landing also pass at both rates;
lethal shield contact passes at both rates. Mine effects and terrain/midair
interactions remain open. Powered input-only pilots now clear the full SOL wave, kill its full-strength
boss and take the native exit to level 1 at both rates; direct native-event
verification passes. Later bosses and ending remain open. Natural
combat death, Continue and No/menu/new-game pass at both rates after
fixture-controlled earlier exits to level 6. Evidence is retained under
`tmp/release60`; completed step-5 measurements remain the current performance
reference. The normal loader still excludes SIM60.

Completion requires the following evidence on both selected paths:

- Native-reference replacement checks and full encounter runs, including
  full-strength boss kills, ending, natural deaths and Continue/No. Existing
  shortened-wave and reduced-health fixtures retain their narrower scope.
- Level/UI transitions, combined preference changes and re-enabling, active
  power cycling and combat effects, jumps over terrain and midair impacts,
  lethal shield/type-43 hits, boss helpers and mine detonation.
- Exact-build disabled-code, hook and indirect-entry checks, diagnostic
  exclusion and actual playable-launcher checks after any fixes.
- Playable controls, visible response, sound and original-reference pace.
  Automated input/state checks alone do not establish subjective control feel
  or audible output; record the actual observation used for each conclusion.
- Current documentation, removal of unused tools, a release decision supported
  by those checks, and commits following the repository conventions.


Run native twins, full encounters, boss kills/ending, natural deaths,
Continue/No, level/UI transitions, powers, jump and preferences at each selected rate on
its CPU path. Repeat disabled-byte preservation, hook/indirect-entry checks,
diagnostic exclusion and play60 smoke tests. Keep PAL timing coverage separate
from claims about the supplied NTSC game's audiovisual behavior.

Playtest real controls, sound, original-reference pace and responsiveness.
Only after correctness and performance validation consider enabling SIM60 in
the normal loader. Update current docs and remove unused tools.

## Remaining release validation

The conversion remains experimental. The plan above includes lower-rate
68000 selection and excludes interpolation. Input history is complete; broader coverage includes:

- Broaden full-encounter coverage at both selected rates: boss kills and ending,
  later natural deaths, level and UI transitions, type-43 hits,
  boss helpers and mine detonation. Lethal shield ramming passes at both rates. Controlled placement, native twins and
  sampled mapped-state comparisons do not cover every encounter branch.
- Extend the passing input-driven power-cycle checks to combat effects, and
  jump checks to arbitrary terrain and midair impacts. Combined preference
  changes and re-enabling pass; additional native dialog paths remain.
- Confirm original-reference gameplay pace and the reconstructed loader's
  behavior through playtesting. The modern KickEmu loader is not a byte-identical
  rebuild of the supplied 2008 slave.
- Finish replacement-semantic and indirect-entry coverage before enabling
  SIM60 in the normal loader. Static patch-boundary checks and observed
  calls/returns leave exceptions, external-source returns and unseen paths
  outside coverage. Keep disabled-code preservation and diagnostic exclusion
  in the final release checks.
