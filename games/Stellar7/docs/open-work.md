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
N=3. Steps 1–6 are complete; step 6 retained two exact 68000 interrupt changes.
Steps 7–11 remain, in order: a fresh baseline on the three validation machines, encounter
coverage, final build checks, playtesting and the release.

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
and physical-control playtesting remain in steps 8 and 10.

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
in step 10. No interpolation has been added.

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
in steps 8 and 10.

Measure field boundaries, buffer handshakes, blitter/chip-bus contention and
cache policy on 68030/040/060 at N=12. Determine the cause of the presentation
ceiling rather than extrapolating from CPU clock speed. Use SWAP_ONLY and
complete-call timing where applicable; check actual cache configuration.

Re-run the full matrix and extended combat. Require sustained real-time game speed at each selected fixed rate
with no accumulating pending-update trend, preserving gameplay across CPUs
at the same rate.
Report presentation rates and input latency alongside that result. Native FPS
is a performance comparison; retain 60 Hz on the 68020+ path. Any unresolved A500 limitation must be explicit before release decisions.

## Remaining work

Steps 7–11 run in order; step 6 is complete. Each change ends with its measurements in
`docs/internals.md`, its commands in `docs/development.md` and its own commit.

### Validation machines

Every remaining step uses three NTSC machines, the AmigaXDev named setups in
`game.conf` `SETUPS` (`tools/machines.py`, `docs/development.md` "Validation
machines"):

| Setup | Build | Role |
|---|---|---|
| `a500-1.5m` | Sim68000, 15 Hz | the 68000 path and the performance limit |
| `a1200-fast` | Sim60, 60 Hz | the typical 68020 path |
| `a1200-060` | Sim60, 60 Hz | the fast end: MMU, data cache, not cycle-exact |

They replace the earlier eight-configuration matrix. Its recorded results remain
references, but its fast-RAM A1200 (4 MB) and 68060 (no MMU, cycle-exact, data cache
off) differ from these setups, so steps 6 and 7 measure afresh (step 6 on `a500-1.5m`). The coverage that
already passes (step 8) ran on the earlier explicit 68000 A500 and 68020 A1200
(4 MB fast) configurations. Raw captures behind earlier evidence were pruned on
2026-11-04; recorded verdicts stand, but any re-check needs a fresh capture.

### Step 6: A500 interrupt and sound-handler cost

Status: complete. Fresh 100-field profiles on `a500-1.5m` with the 15 Hz VERIFY
build (`tools/interrupt_profile.py`) put interrupt dispatch at 17.4% of cycles in
SOL, 20.7% in late type-10 combat and 14.9% at the boss. The 68000 build now
frees 6.6%, 6.6% and 4.3% of all cycles there (interrupt share 10.9%, 14.1%
and 10.6%):

| Source | SOL | Type-10 | Boss | Retained |
|---|---:|---:|---:|---|
| Blitter-finished (Kickstart handler, no-op) | 5.4% | 4.7% | 3.0% | masked while Kickstart's queue is idle: all removed |
| Sound timer (CIA-B timer A, hunk $1126) | 7.2% | 11.1% | 7.0% | exact channel pass: 1.3%, 1.9%, 1.4% saved |
| Frame interrupt (VERTB) | 4.9% | 4.9% | 4.9% | unchanged: slave share under 1% |

Kickstart 1.3 enables the blitter interrupt itself whenever it queues a blit and
disables it when its queue empties. The game queues none, so the interrupt
only costs dispatch time. `BLIT_IRQ_IDLE` (`src/blit60.s`) masks it from the
field callback whenever Kickstart's queue is idle, rechecking after the write.
It supersedes the step 4 polygon wrapper. VERIFY counters show one mask per run
and the queue never active, over 4250–26353 fields per route.

The sound timer is the Sonix music driver. `SOUND_FAST` (`src/sound60.s`)
replaces its per-channel pass at $134c with an exact inline version. It caches
the divide and the volume, and computes no volume for silent channels. The
VERIFY twin compared it with native $134c on 121283 timer calls across SOL,
type-10 and boss: identical channel records and 795705 identical written Paula
words. The altered build fails. Alone, its gain is below the 3% rule, so it is
retained only together with the blitter change. Caching the period or the whole
update does not pay on the 68000.

Mapped gameplay state matches the native references at every checkpoint. Both
changes are 68000-only. The original and Sim60 slaves are byte-identical to step 5,
and `-DBLIT_IRQ_IDLE=0 -DSOUND_FAST=0` rebuilds the step 5 68000 slave. In the
frame interrupt, the slave's input sample costs about 0.9%; a movem copy would
save 0.25%, so it is unchanged. Whether the freed time raises the A500 frame rate
or allows 20 Hz is measured in step 7. Measurements are in internals ("A500
interrupts and the sound timer").

### Step 7: Fresh baseline on the three machines

Status: not started. Step 6 changed only the 68000 slave (blitter interrupt and
sound pass). Check here whether its freed time raises the A500 frame rate.

1. Run the matrix with selected rates on all three machines
   (`tools/rate_matrix.sh tmp/three/main --selected-rates`), plus native-combat
   and the A500 heavy route; verify it with `rate_matrix_report.py`.
2. Run extended combat to natural death (`tools/sustained_combat.py`) on all
   three. Require the selected average rate with no accumulating pending trend.
3. Port the earlier release-validation runners still needed from untracked
   `tmp/release60` into
   `tools/`, selecting machines with `SETUP` instead of explicit CPU and memory
   variables.
4. Re-run the input-history fixtures (recorded controls, native key queue),
   same-rate state comparisons (`a1200-fast` against `a1200-060` at N=12),
   delayed-draw and lifecycle comparisons (death, Continue, No, exits), the
   buffer-reuse display-stability check on `a1200-060`, and the build and
   off-byte identities.

### Step 8: Encounter coverage at both rates

Status: in progress. Run each item on `a500-1.5m` (15 Hz) and `a1200-fast`
(60 Hz), with `a1200-060` for the final full run.

Already passing on the earlier configurations: all 26 native-reference fixture
groups; combined preference changes and re-enabling through the native menus;
input-driven cycling through six overlapping powers; a jump and landing; lethal
shield contact; controlled airborne and landed terrain contact; lethal mine
contact and native mine destruction; incoming-projectile midair impacts; the full
SOL wave, its full-strength boss and the native exit to level 1, with direct
native-event verification; full-health final-boss kills and native ending entry
and return after explicit earlier-level and wave shortcuts; natural combat death,
Continue and No/menu/new-game after fixture-controlled exits to level 6.

Still to run:

1. Full waves and full-strength boss kills in levels 1–6 without wave shortcuts,
   including each level transition and the ending.
2. Boss helpers in each boss encounter.
3. Mine detonation checked by display capture and recorded audio.
4. Jumps and landings over arbitrary terrain, not only the controlled contacts.
5. Each power active during combat: its effect on hits, shots and contacts.
6. Natural deaths in later levels, with Continue and No.
7. The remaining native dialog paths.

### Step 9: Final build checks

Status: not started; repeat after the last fix.

1. Disabled-code preservation and the normal loader byte-identical to the
   original timing (it stays without SIM60 unless step 11 decides otherwise).
2. Hook and indirect-entry checks on the exact release builds. Static
   patch-boundary checks and observed calls and returns leave exceptions,
   external-source returns and unseen paths outside coverage; close what can be
   closed before step 11 considers SIM60 in the normal loader.
3. Diagnostic exclusion: no VERIFY-only code in the release builds.
4. `make play60` launcher checks on all three machines and
   `tools/test_play60_launcher.py`.

### Step 10: Playtest

Status: not started; needs you to play. Automated checks cannot settle these.

1. On each machine, play `make play60 SETUP=<machine> WINDOW=front` with sound,
   and the original slave (`make run SLAVE=original`) on the same machine.
2. Check controls and visible response, music and sound effects, and pace against
   the original. On the A500, check that 15 Hz control feels acceptable; try
   `SIM68000_SUBSTEPS=4` (20 Hz) for comparison.
3. Check the reconstructed loader's behaviour: the modern KickEmu loader is not a
   byte-identical rebuild of the supplied 2008 slave.
4. Record each observation, and the machine it came from, in internals.

### Step 11: Release

Status: not started.

1. Remove tools no longer used by a current check; update the docs in place.
2. Decide the release and whether the normal loader gets SIM60.
3. The slaves' `$VER`, the ReadMe and the local
   `dist/Stellar7Enhanced-2.0b-20261105.lha` carry a provisional 2.0b label dated
   05.11.2026. Nothing is published. Set the version and date when releasing,
   then `make dist`, and `make release` only on your go.
