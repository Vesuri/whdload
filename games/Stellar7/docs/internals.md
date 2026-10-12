# Stellar 7 internals

## Active performance work

The experimental launcher selects **15 Hz (N=3) on 68000/68010 and 60 Hz
(N=12) on 68020+**, without interpolation. These are separate compiled slaves;
the launcher selects using its CPU setting. A slave's timestep does not change
at runtime. Movement, input quanta and game clocks scale with N, retaining
real-time game speed. History assigns controls to their tick; native menus stay live.

The displayed-buffer reuse correction is enabled in both playable source paths.
Build, matrix, extended-combat, input, delayed-draw and lifecycle checks pass.
Both actual-launcher smoke checks also pass.
Fast-CPU timing diagnostics and extended-combat checks pass within the scopes below;
the corrected selected-rate matrix and its 350 state comparisons pass. Broader encounters and physical-control
playtesting remain open. The normal loader still omits this experimental conversion.

## Release validation

Step 6 is in progress. All thirteen native-reference fixture groups pass on both the
selected N=3 A500 and N=12 68020 paths, for 26 completed groups with the
displayed-buffer correction enabled. Exact captures, listings, installed-hook results
and checker output are under `tmp/release60/native-fixtures`. These private
oracles are distinct from full encounters and physical-control playtesting.

The current-build A500 SOL trace also passes 4971 observed indirect JSR/JMP
executions and 21768 verified RTS/RTR/RTD transitions. Twenty-two return
boundaries have discontinuous register snapshots and remain unverified.
The source trace is the retained 100-field step-5 normal-speed preflight;
this is a new audit of that trace, not a fresh capture or whole-program proof.
Exceptions, external-source returns and unobserved paths remain outside this
check. Evidence: `tmp/release60/a500-sol-entry-audit.json`.

The complementary all-PC audit passes 7288722 observed instruction PCs across
five retained current-build windows: A500 SOL, late combat and boss, and 68020
with fast RAM SOL and late combat. It checks destinations irrespective of their
origin, admitting only installed entries and declared NOP padding inside patch
ranges. The 1591757 missing-PC records remain gaps, and this does not prove exception-stack
semantics or unseen paths. Exact-build indirect and stack-return audits also
pass these windows. Evidence: `tmp/release60/a500-sol-all-entry-audit.json` and
`entry-audits/*.json`.

All 42 host-tool tests pass (`tmp/release60/host-tests-expanded.log`). Named machine
presets now resolve before the launcher chooses a fixed-rate slave; the
selection regression rejects the prior order and passes all seven presets,
explicit/default CPUs and an invalid-preset case. This argument-level test does
not replace an actual launcher smoke test.

The PF62 combined-preferences fixture passes on N=3 A500 and N=12 68020.
Native menu buttons toggle Mouse, Joystick, Music and Sounds off in that order,
then restore each to one. All nine intermediate setting snapshots match the
expected sequence. Entry and return remain at tick 100; modal credit stays
150 on A500 and 480 on 68020. Settings remain restored at completed ticks
101, 150 and 300, with no missing input samples or queue drops. Installed-hook
checks pass (109/108). Both playable releases remain byte-identical to step 5,
including when the sequence definitions are supplied without VERIFY. Existing
single-toggle fixture bytes also match at both rates. Evidence:
`tmp/release60/preferences/validation.json` and `build-validation.json`.
These settings checks do not establish audible output.

## Fast-CPU presentation and sustained combat

### Displayed-buffer reuse finding

The retained 68060 SOL trace has nine consecutive-field pairs with unchanged
bitmap addresses but changed fetched words (32–1003 words per affected pair).
Each affected field is the last field scanning that bitmap before the buffer
switch. The matching phase capture starts the next draw in the same field as
the preceding presentation, with the old displayed bitmap selected for drawing.
The A1200-with-fast-RAM trace contains no same-buffer word changes in its
50-field window. Evidence: `tmp/fast60/scanout-word-stability.json` and the
retained `probes/*-sol-trace` / phase captures.

Native $2b96–$2ba0 waits for the field counter to differ from the value saved
after the previous presentation at $2c1a. SIM60 bypasses that wait. These
observations identify premature buffer reuse in the captured 68060 path;
complete scanout addresses alone did not establish an untouched visible buffer.
The correction restores this field check before drawing while continuing the
simulation poll. Installation checks the native compare/store instructions and
their shared field-counter operand. No tick is discarded and neither fixed rate
changes. The matrix below compares unfixed and corrected builds; the drawing
and handoff diagnostics explicitly describe the unfixed reference.

A matched scratch candidate checks the current field against native `-22(a5)`
before starting another draw, returning to the simulation poll while they are
equal. Both arms retain identical layout and differ only in the four-byte
BEQ/NOP sequence. In the first 50-field 68060 SOL scanout capture, the control
has eleven unstable same-bitmap fields; the candidate has zero. All eight mapped
state comparisons across both arms and observers at ticks 600 and 1500 pass,
allowing only deferred projection scratch. Across that 900-tick interval, presentation falls from 23.893 to
20.579 FPS. Candidate debt falls 2→0 over 898 fields, so its 60.134 updates/s
average includes repayment, not a faster simulation clock. The independent phase
capture observes 16/16 next draws in the presentation field for the control;
the candidate starts all 12 observed next draws in the following field.
The uninterrupted normal-speed comparison captures 100 fields per arm: native
and candidate each have zero unstable same-bitmap fields, while the control has
20. Recorded running commands establish warp-off, and mapped candidate/control
state agrees apart from deferred projection scratch. This is fixture-controlled
gameplay, not physical-control or audible-output validation.
Evidence: `tmp/fast60/buffer-reuse/validation.json`,
`tmp/fast60/buffer-reuse/normal-speed-validation.json`, the scanout reports and
exact matched binaries/listings.

`BUFFER_REUSE=1` now enables the correction in the source. All six rate builds,
both playable targets, the 20 Hz override, diagnostic exclusion and static hook
audits pass. Disabling only this guard reproduces the preceding release/VERIFY
bytes; the normal loader stays byte-identical. Native comparison fixtures rebuilt
with the guard disabled also match the previously measured binaries exactly.
Evidence: `tmp/fast60/corrected/builds/validation.json`.

The final-source normal-speed checks pass on A500 and 68060: each captures 100
uninterrupted fields with zero unstable same-bitmap fields, and mapped gameplay
matches the reference at both endpoints, allowing deferred projection scratch.
The actual process command confirms warp-off. SOL presentation is 4.023 FPS on
A500 and 20.646 FPS on 68060 in these windows. Both repay initial debt (5→0
and 2→0 respectively), so their above-target average update rates are not
sustained-throughput claims. Evidence: `tmp/fast60/corrected/preflight/validation.json`.

### Corrected selected-rate matrix

All 40 corrected SIM60 captures pass runtime-setting and installed-hook checks.
The 40 native comparator captures are retained measurements: fresh guard-off
fixture builds reproduce their exact bytes. All 150 same-rate CPU/PAL and
200 before/after mapped-state comparisons pass, allowing only deferred projection
scratch. Missing input samples and queue drops are zero at every heavy checkpoint.
Evidence: `tmp/fast60/corrected/matrix-validation.json` and `matrix.md`.

Presentation rates below are unfixed → corrected. SOL spans nominal ticks
600→1500, early type-10 1800→2400, late type-10 4500→5400, boss 3500→4100,
and heavy type-10 600→5400; N=3 tick numbers scale by one quarter.

| Configuration | Fixed Hz | SOL FPS | Early type-10 FPS | Late type-10 FPS | Boss FPS | Heavy FPS |
|---|---|---|---|---|---|---|
| A500 | 15 | 4.023 → 4.023 | 4.684 → 4.684 | 3.946 → 3.955 | 2.412 → 2.416 | 4.031 → 4.033 |
| Stock A1200 | 60 | 5.174 → 5.174 | 3.458 → 3.452 | 2.959 → 2.959 | 2.600 → 2.600 | 3.409 → 3.409 |
| A1200 + fast RAM | 60 | 8.812 → 8.667 | 9.045 → 9.070 | 8.906 → 8.923 | 5.700 → 5.752 | 8.988 → 8.988 |
| 68030/50 | 60 | 18.800 → 17.305 | 22.575 → 19.800 | 22.267 → 19.756 | 14.348 → 13.746 | 22.175 → 19.512 |
| 68040/25 | 60 | 23.653 → 20.401 | 29.052 → 20.268 | 29.000 → 20.044 | 19.132 → 15.947 | 28.594 → 20.883 |
| 68060/50 | 60 | 23.893 → 20.646 | 29.300 → 21.100 | 29.465 → 20.200 | 19.400 → 17.186 | 29.012 → 21.254 |
| PAL A500 | 15 | 4.043 → 4.038 | 4.771 → 4.771 | 3.995 → 4.016 | 2.410 → 2.515 | 4.100 → 4.103 |
| PAL 68060/50 | 60 | 25.300 → 18.467 | 29.341 → 24.950 | 28.628 → 24.967 | 18.900 → 16.499 | 29.443 → 24.587 |

The guard has a measurable presentation cost on the fast CPUs. Heavy-combat
throughput remains near the selected fixed rate; the observed pending counts
fluctuate within the sampled ranges below. Positive endpoint growth is included
in the reported average. Stock A1200 retains substantial catch-up bursts, with
38 updates owed at the sampled peak. These are scene measurements, not bounds
for every encounter or continuous response-time maxima.

| Configuration | Seconds | Updates/s | Presentations/s | Pending range | Pending start→end |
|---|---|---|---|---|---|
| A500 | 80.083 | 14.984 | 4.033 | 1–3 | 1→2 |
| Stock A1200 | 80.083 | 59.938 | 3.409 | 5–38 | 5→10 |
| A1200 + fast RAM | 80.000 | 60.000 | 8.988 | 1–6 | 5→5 |
| 68030/50 | 80.000 | 60.000 | 19.512 | 0–2 | 2→2 |
| 68040/25 | 80.017 | 59.988 | 20.883 | 0–2 | 1→2 |
| 68060/50 | 80.033 | 59.975 | 21.254 | 0–2 | 0→2 |
| PAL A500 | 79.940 | 15.011 | 4.103 | 0–4 | 1→0 |
| PAL 68060/50 | 80.000 | 60.000 | 24.587 | 1–3 | 1→1 |

Native reference presentation rates follow. These corresponding scene windows
have different trajectories and measurement lengths from the fixed-rate runs;
they are not identical per-frame workloads.

| Configuration | SOL frame 90 FPS | SOL frame 240 FPS | Early type-10 FPS | Late type-10 FPS | Boss FPS |
|---|---|---|---|---|---|
| A500 | 5.000 | 4.000 | 4.444 | 4.054 | 1.765 |
| Stock A1200 | 8.000 | 6.000 | 7.500 | 7.021 | 3.117 |
| A1200 + fast RAM | 12.000 | 7.912 | 10.000 | 9.545 | 5.783 |
| 68030/50 | 20.000 | 15.464 | 20.000 | 18.125 | 13.548 |
| 68040/25 | 30.000 | 18.947 | 20.000 | 20.000 | 16.875 |
| 68060/50 | 30.000 | 18.947 | 20.000 | 20.000 | 17.053 |
| PAL A500 | 5.000 | 3.896 | 4.545 | 4.070 | 1.852 |
| PAL 68060/50 | 25.000 | 20.408 | 25.000 | 25.000 | 16.489 |

All 18 corrected scanout windows are reviewed: SOL and late combat on all eight
configurations, plus boss on A500 and 68060, with 100 complete fields per window.
Sixteen pass strict unchanged-bitmap checks; two are individually classified
native HUD updates. Exact build/settings/hook checks and mapped starting-state
comparisons pass, allowing deferred projection scratch. A500/68060 SOL reuse
the exact normal-speed preflight captures; 68060 late combat and boss also run
at normal speed with recorded process commands. Other captures use accelerated
host execution. Evidence: `tmp/fast60/corrected/scanout/validation.json`.

The normal-speed
68060 boss window has one classified native cockpit update: 23 words change in
field 20, confined to x=243–263, y=170–174. Native $d2be–$d334 redraws the
24×10 indicator at (243,170); read-only breakpoints observe that routine's copy
in field 20. A normal-speed native boss capture changes the same indicator in
four fields and another cockpit region in two fields. Corrected fields 19 and
21 match exact native indicator images; field 20 contains a partial transition.
This is preserved native HUD behavior, not an unchanged-bitmap pass or evidence
that every visible write has been eliminated. The strict scanner remains
unchanged: only this retained capture is classified, with no general HUD mask.
Build identities, runtime settings, mapped state, native opcode guards and
normal-speed commands pass. Evidence: `tmp/fast60/corrected/boss-hud-classification.json`,
`boss-pixel-comparison.json`, `boss-icon-states.json` and `boss-hud-phase`.
PAL A500 SOL also passes strict stability. PAL A500 late combat has a second
classified native HUD update: 28 words change in field 10 within the energy bar
at x=158–164, y=189–195. The read-only observer sees five native bar-line draws
across fields 9–10 and the $c1a4 copy in field 10. Coordinate/operation guards
match the native comparator; exact builds, settings and mapped state pass. The
native PAL comparison window itself is stable, so it does not establish the same
event timing. The first normal-speed observer timed out and is excluded; the
successful observer uses accelerated host execution, as did the original failed
pixel check. This retained capture is classified individually, not accepted by
a general energy-bar mask. Evidence: `tmp/fast60/corrected/pal-energy-classification.json`,
`pal-late-pixel-comparison.json` and `pal-energy-phase-retry`.
No unexplained fetched-pixel changes remain in these windows. The scanout test
does not rule out writes restored before fetch and does not cover every scene.
Extended-combat, input, delayed-draw and lifecycle validation pass.
Both actual-launcher smoke checks also pass.

### Native drawing and handoff observations

Read-only native breakpoints retain beam positions and field epochs over
50 NTSC fields, starting at tick 600 in SOL or 4500 in late combat. Timings
below include interrupt execution and wrapper overhead;
the parent drawing scope overlaps its children. Partial boundary calls are
excluded, so scope call counts can differ. Hunk $2bb4 starts drawing, $2bec–$2bf0
brackets actors and $6a0a–$2c1a brackets presentation.

| Configuration / scene | Complete draws | Before actors ms | Actors ms | After actors ms | Drawing before presentation ms | Presentation call ms |
|---|---:|---:|---:|---:|---:|---:|
| A1200 + fast / SOL | 5 | 21.525 | 94.084 | 20.050 | 135.671 | 0.086 |
| 68030/50 / SOL | 11 | 14.628 | 40.317 | 11.953 | 66.896 | 0.026 |
| 68040/25 / SOL | 14 | 13.640 | 28.657 | 10.084 | 52.378 | 0.013 |
| 68060/50 / SOL | 15 | 13.611 | 28.286 | 10.026 | 51.964 | 0.013 |
| 68030/50 / late type-10 | 17 | 14.434 | 14.399 | 12.826 | 41.708 | 0.025 |
| 68040/25 / late type-10 | 23 | 13.494 | 9.686 | 10.353 | 33.561 | 0.013 |
| 68060/50 / late type-10 | 23 | 13.489 | 9.336 | 10.023 | 32.816 | 0.016 |

None of these windows enters the optional VBL handoff at $1c986–$1c996 or the
copper-build branch at $1c8c0–$1c8da. The request remains clear while native
front/back indices alternate. Presentation is a small part of the observed
cost, not a mandatory multi-field wait. On 68060, work outside the actor pass
is about 23.5 ms in both sampled scenes; this is a scene-window observation,
not a universal lower bound for every frame.

In 68060 SOL, complete graphics WaitBlit wrappers ($2510c–$2511a) account for
144.222 ms and polygon waits ($1db8c–$1dbb2) for 272.347 ms of the 833.333 ms
window. The late-combat values are 201.315 and 94.772 ms. These elapsed scopes
include polling instructions, wrapper overhead and interrupts: they must not
be labeled pure blitter DMA cost. Clock/blitter sensitivity diagnostics provide
separate evidence about causation.

The 68020 calibration uses an independent Barto instruction trace of the same
exact binary and route. Every presentation field matches; mapped gameplay and
reticle state agree at ticks 600 and 1500. Mean whole-draw time differs by
0.115%; small helper means differ by up to 2.083%, with boundary call-count
variation in the polygon wait. The observer is therefore suitable for the
large stage differences here, not sub-percent optimization claims.

Actual bitplane DMA in separate 68020/68060 SOL traces fetches all 16000 words
of one native four-plane bitmap in every one of 50 fields. Buffer changes
match presentation calls in the following field. This checks complete scanout
addresses, not writes to displayed memory between fetches. Mixed-buffer,
missing-fetch and repeated-address negative controls are rejected
(`tmp/fast60/buffer-controls.json`). The 68060 trace has
zero CPU instruction records and no blitter DMA records: its backend does not
supply validated instruction timing and has non-cycle-exact blitter recording.
Absence of those records is not evidence of zero CPU or blitter work.

Evidence: `tmp/fast60/probes/*-report.json`, `calibration.json`, both
`*-sol-buffers.json` reports and their exact listings/binaries, raw beam events,
GDB scripts, retained trace files and endpoint states. Milliseconds use the
repository's nominal 60-fields/s NTSC convention; this is emulator evidence,
not a measured real-accelerator performance bound.

### Clock and blitter sensitivity

These are whole SOL 600→1500 field/counter intervals on the identical ordinary
N=12 VERIFY binary. Only the requested emulator frequency or instant-blitter
setting changes. Runtime options are checked and mapped gameplay state matches
at both boundaries, with only deferred projection scratch differing.

| 68060 diagnostic configuration | Updates/s | Presentations/s | Pending start→end |
|---|---:|---:|---:|
| 50 MHz, ordinary blitter | 60.067 | 23.893 | 2→1 |
| 8 MHz, ordinary blitter | 60.201 | 22.609 | 3→0 |
| 50 MHz, instant blitter | 60.000 | 46.600 | 0→0 |

Above-target update averages repay initial debt; they do not change game time.
The 8 MHz check is slower, but the modest response must not be extrapolated
into physical accelerator scaling. Instant blits nearly double presentation
rate. In its separate 50-field beam window, mean drawing before presentation
falls from 51.964 to 24.886 ms; before/after-actor work falls from approximately
23.6 to 5.0 ms. Complete graphics/polygon wait scopes total 11.860/22.638 ms,
compared with 144.222/272.347 ms in the ordinary window. Presentation itself
remains approximately 0.012 ms, with no optional VBL handoff observed.

This identifies modeled blitter-side drawing as a major limit, alongside the
remaining actor work. It does not separate serial blit latency from Chip-bus
contention on the fast backend, whose blitter DMA records are unavailable.
The instant setting is a counterfactual diagnostic, not a hardware result or a
playable optimization. Short-window stage times and whole-route FPS cover
different spans and must not be substituted for one another.

Evidence: `tmp/fast60/probes/060-50-sol-{trace,8mhz,instant}` and their retained
settings, beam reports, exact common binary and matched endpoint states.
The incomplete instant-blitter attempt ending with a debugger protocol error
is preserved separately and excluded; the accepted retry contains all 50 fields.

### Matched presentation-only controls

The scratch SWAP_ONLY experiment retains the simulation, RNG save/restore and
native presentation call, including its signed word argument. Both arms contain
the same wrapper and all code. Each retained pair differs in exactly one
two-byte instruction: a NOP for full rendering or a short branch to the
presentation-only path. The control, not the ordinary differently laid-out
slave, is the timing reference. The bypass deliberately displays stale pixels.

| CPU / scene | Matched full-render control FPS | Presentation-only FPS |
|---|---:|---:|
| 68030/50 / SOL | 18.800 | 60.000 |
| 68030/50 / late type-10 | 22.284 | 60.000 |
| 68060/50 / SOL | 23.920 | 60.000 |
| 68060/50 / late type-10 | 29.467 | 60.000 |

All four bypass intervals complete at exactly 60 updates and presentations per
second, with zero pending debt at both boundaries. Both CPUs can therefore
run this simulation and native handoff at the display rate in these scenes;
full drawing imposes the lower observed presentation rate. This is a ceiling
experiment, not a candidate to ship. Together with the instant-blitter result,
it identifies drawing, substantially blitter-side work, rather than a mandatory
multi-field publication wait as the limit in the measured fast-CPU scenes.

Twenty mapped-state comparisons across the matched arms, clock and blitter
variants pass at both interval boundaries; only deferred projection scratch
differs. All four pairs pass exact two-byte-difference checks and installed-hook
audits. Evidence: `tmp/fast60/swap`, `diagnostic-validation.json` and the paired
field observations, settings, listings and binaries. Probe code is excluded from
the normal and playable builds. The diagnostic reference builds match the
rendering-optimization baseline (`tmp/fast60/builds/validation.json`); the new
buffer guard is independently checked in `tmp/fast60/corrected/builds/validation.json`.
All 31 host-tool tests pass, including beam rollover, delayed VBL
entry, invalid scope nesting, displayed-bitmap pixel changes and contradictory runtime settings
(`tmp/fast60/tool-tests-final.log`). These checks validate the measurement tools;
they do not replace the gameplay-state and runtime observations below.

### Extended active combat and input timing

These are current corrected-build combat and input measurements.
The type-10 route starts at nominal tick 600 and continues through natural
death, stopping at the first inactive completed update before menu time or a
session reset. Checkpoints are five nominal seconds apart, plus the terminal
update. No invulnerability is used. Active-actor samples range from seven to
twelve across these runs; terminal energy is negative. Rates use native
observed fields and completed tick/presentation counters, not host wall time.

| Configuration | Fixed Hz | Active seconds measured | Updates/s | Presentations/s | Sampled pending range | Pending start→end | Death tick |
|---|---|---|---|---|---|---|---|
| A500 | 15 | 114.133 | 14.982 | 3.934 | 1–3 | 1→3 | 1860 |
| Stock A1200 | 60 | 143.750 | 59.910 | 3.353 | 5–38 | 5→18 | 9212 |
| A1200 + fast RAM | 60 | 143.567 | 59.986 | 8.818 | 1–7 | 5→7 | 9212 |
| 68030/50 | 60 | 143.517 | 60.007 | 19.461 | 0–2 | 2→1 | 9212 |
| 68040/25 | 60 | 143.550 | 59.993 | 20.529 | 0–2 | 1→2 | 9212 |
| 68060/50 | 60 | 143.533 | 60.000 | 20.824 | 0–2 | 0→0 | 9212 |
| PAL A500 | 15 | 114.020 | 14.997 | 3.999 | 0–5 | 1→1 | 1860 |
| PAL 68060/50 | 60 | 143.520 | 60.006 | 24.714 | 0–3 | 1→0 | 9212 |

All eight runs sustain the selected average game speed in this encounter;
pending samples fluctuate and recover rather than showing persistent growth.
Stock A1200 is a responsiveness concern: its sampled peak is 38 owed ticks
(about 0.63 s), followed later by recovery to seven, and it ends at 18. The
small endpoint growth is shown rather than hidden by rounding the average to
60 Hz. These sampled ranges are not continuous latency maxima, and this
encounter is not a bound for every level or boss.

All 174 same-rate CPU/PAL mapped-state comparisons pass through natural death,
including the reticle and fresh projection. Only deferred projection scratch
differs. N=3 and N=12 follow different encounter trajectories; these checks
compare CPUs at the same rate, not cross-rate equivalence. All 228 before/after
comparisons also pass, including unchanged lethal ticks and terminal state.
Each extended binary matches its corrected heavy-matrix binary. Input-history
missing-sample and queue-drop counts remain zero at every extended checkpoint.

The separate elapsed-field input fixture passes 200 recorded ticks, eight
held/press/release/fire edges and 96 native key-queue assertions on each of the
eight configurations. Eight NTSC same-rate and sixteen before/after mapped-state
comparisons also pass. PAL
fixtures are checked against their own elapsed-field schedule. Delays below
are the ranges among those eight synthetic edges, not combat-wide maxima or
physical-device latency. Render handoff ends at render completion, before
actual scanout. One field is nominally 16.667 ms NTSC or 20 ms PAL.

| Configuration | Input consumption delay, fields | Render handoff delay, fields | Render handoff delay, ms |
|---|---|---|---|
| A500 | 7–16 | 32–37 | 533.3–616.7 |
| Stock A1200 | 7–21 | 19–40 | 316.7–666.7 |
| A1200 + fast RAM | 3–11 | 10–22 | 166.7–366.7 |
| 68030/50 | 1–4 | 4–9 | 66.7–150.0 |
| 68040/25 | 0–3 | 3–7 | 50.0–116.7 |
| 68060/50 | 1–3 | 4–7 | 66.7–116.7 |
| PAL A500 | 2–14 | 17–30 | 340.0–600.0 |
| PAL 68060/50 | 0–2 | 1–5 | 20.0–100.0 |

Correct historical input does not eliminate catch-up and drawing delay. The
slow configurations can sustain average game speed while still handing off a
visible response several hundred milliseconds after its synthetic input edge.

Extended evidence: `tmp/fast60/corrected/extended-validation.json` and the exact
per-machine captures/listings/binaries. Corrected input evidence is
`tmp/fast60/corrected/input/validation.json`. The first 68060 input capture failed
at tick zero after a debugger “Invalid hex digit 79” condition error; it is
retained and excluded. The successful retry has identical slave bytes.
The effective clocks, private UAE CPU/memory options, input integrity and
terminal boundaries are checked independently. FS-UAE's logger first writes
a shared startup file and then copies it into its private log; simultaneous
project boots can contaminate only that copied frontend header. The current
checker uses private runtime option records and the observed Exec clock;
new captures also retain the effective `debug.uae` configuration. The shared
logger source (`libfsemu/src/log.c`) explains the discrepant headers in two
extended captures; their private options and observed clocks agree.

### Corrected-build regression checks

All 38 delayed-draw mapped-state comparisons pass: N=3 SOL, boss and heavy
combat, plus N=12 heavy combat, with SLOW_DRAW=20 on the 68020. Reticle and
fresh projection are included; only deferred projection scratch differs.
Death/Continue, declining Continue, normal level exit and early exit pass at
both selected rates, with sixteen endpoint state comparisons. N=3 compares
A500 against delayed 68020 drawing; N=12 compares delayed 68020 captures with
the retained input-history reference. Both CUSTOM1-off preservation checks pass.
Evidence: `tmp/fast60/corrected/cross/validation.json`,
`lifecycle-n3/validation.json` and `lifecycle-n12/validation.json`.
Both actual `play60.sh` paths reach the native menu with their selected rate,
installed hooks and no menu-test fixture. Their release bytes match the audited
builds. Evidence: `tmp/fast60/corrected/play60-smoke-68000/validation.json` and
`play60-smoke-68020/validation.json`. These smoke tests use silent, accelerated
execution and disconnected controls; they establish neither audible output nor
physical-control behavior. Final source identities match all forty fresh matrix
cells, and retained audited build hashes match their binaries.
These fixtures do not replace step 6's full-encounter and physical-control tests.

### Observed cache configuration

A scratch-only probe samples CACR immediately after SetCPU and at completed
SIM60 tick 200. It preserves registers and uses Exec Supervisor to execute
MOVEC CACR,D0 and RTE; no cache-control write is added. The 68000 guard never
executes MOVEC. The probe adds timing overhead, so its captures supply no
performance measurements. Normal and playable sources do not include it.

| Configuration | After SetCPU / tick 200 CACR | Instruction cache | Data cache |
|---|---|---|---|
| A500 | unsupported / unsupported | absent | absent |
| Stock A1200 | $00000000 / $00000000 | disabled | disabled |
| A1200 + fast RAM | $00000000 / $00000000 | disabled | disabled |
| 68030/50 | $00002000 / $00002000 | disabled | disabled |
| 68040/25, NOMMU | $00008000 / $00008000 | enabled | disabled |
| 68060/50, NOMMU | $20808000 / $20808000 | enabled | disabled |
| PAL 68060/50, NOMMU | $20808000 / $20808000 | enabled | disabled |

The relevant enable bits are CACR bit 0 for 020/030 instruction cache, bit 8
for 030 data cache, and bits 15/31 for 040/060 instruction/data caches. The
030 value $2000 is not a cache-enable bit. Interpretation is corroborated by
the emulator's MOVEC masks and cache-enable checks in `newcpu.cpp` and
`newcpu_common.cpp`. The observed enable bits do not establish hardware cache
coherency or validate the emulator's fast-CPU instruction timing.
Evidence: `tmp/fast60/cache/validation.json`, the separate captures and the
exact scratch probe listing/binary under `tmp/fast60/cache-build`.

## Rendering cost and presentation

Both paths draw only newly completed ticks (`RENDER_NEW_TICK=1`) and call the
native presentation routine. The `BUFFER_REUSE=1` field-counter guard also
protects the displayed bitmap while simulation polling continues. Its matrix,
scanout and gameplay regression results are recorded above. The 68000 target additionally enables
`POLYGON_BLIT_IRQ=1`; 68020+ retains the native polygon call. No interpolation,
extrapolation, intentional pose delay or simulation-rate change is involved.

### Measured opportunity and implementation

One hundred Barto fields per scene contain these complete `s60_render` calls.
Main-context cycles include attributable gaps, exclude interrupt execution and
boundary partials. Inclusive helper costs overlap. The two CPUs have different
field-cycle budgets, so these cycle counts are not cross-CPU speed ratios.

| CPU / selected rate | SOL calls / mean cycles | Type-10 calls / mean cycles | Boss calls / mean cycles |
|---|---:|---:|---:|
| A500 / N=3 | 4 / 1626920 | 3 / 1729340 | 2 / 2666654 |
| Stock A1200 / N=12 | 6 / 2429054 | 3 / 2226416 | 3 / 3833014 |

The A500 SOL window records 2421 BLIT interrupts inside 90 polygon scopes.
All interrupt cycles inside those scopes total 1794240 of 11966452 recorded
cycles (14.99%). This is an opportunity upper bound, including unrelated
interrupts, not the measured saving. Stock A1200 records zero BLIT interrupts
in all three scenes; its observed BLIT enable bit is already clear.

The guarded caller at hunk $14c50 waits, owns the blitter, calls the polygon
routine at $17e88, then disowns. Only the $14c5c call is redirected. The wrapper
waits again after ownership (the previous owner's final blit may remain), saves
the BLIT enable bit, masks that bit during the unchanged polygon routine, and
restores its saved value before native DisownBlitter at $14c62. It neither clears
the pending request nor synchronizes away the native asynchronous final blit.
Other interrupt enables, native geometry, blitter commands and buffer ownership
remain unchanged. No sound-handler patch is made.

### Whole-route measurements

These are field/counter interval measurements, not instruction-profile FPS.
A500 uses NTSC, 512 KB chip / 1536 KB slow RAM, N=3. Nominal N=12 route ticks
scale to N=3: SOL 150→375, heavy type-10 150→1350, early 450→600, late
1125→1350, boss 875→1025. Early/late are intervals within the contiguous heavy
run. `Previous` is the preceding playable implementation. `Corrected reference`
adds the simulation-clock reticle and duplicate-draw guard but leaves polygon
interrupts untouched. `Optimized` enables the polygon wrapper too. This third
build isolates the speedup from the corrected reticle workload.

| A500 scene | Previous ms/presentation | Corrected reference ms/presentation | Optimized ms/presentation | Optimized FPS |
|---|---:|---:|---:|---:|
| SOL | 290.196 | 294.333 | 248.588 | 4.023 |
| Type-10, nominal 80 s | 272.109 | 272.981 | 248.091 | 4.031 |
| Early type-10 | 239.837 | 238.889 | 213.475 | 4.684 |
| Late type-10 | 278.395 | 278.704 | 253.390 | 3.946 |
| Boss | 466.667 | 461.905 | 414.583 | 2.412 |

Whole-combat presentation improves 9.68% against the previous build and 10.03%
against the corrected reference, exceeding the 3% retention gate. The final
run completes 1200 updates in 4808 fields (80.133 s), 14.975 updates/s, with
323 presentations. Pending samples are
`1,1,2,3,2,1,3,3,5,2,2,2,2,3,1,2,3`: bounded and recovering, without a
sustained upward trend. Short SOL/boss windows include backlog repayment and
must not be used to claim a faster simulation clock.

Native early/late spot references remain 225/243 ms. Current early presentation
is faster and late presentation slower, but these are corresponding scene
windows with different trajectories and measurement lengths, not identical
per-frame workloads. No universal native-frame-rate claim follows.

Stock A1200 (2 MB chip, no fast/slow RAM, N=12) heavy combat changes from
3.38468 to 3.40895 FPS (+0.72%, unresolved noise). The current run completes
4800 updates in 4805 fields (59.938 updates/s), pending 5→10 with an intermediate
peak of 38 followed by recovery to 10. This is not a worst-case response bound.
The fast-CPU investigation and buffer-reuse correction are described above;
these polygon-optimization comparisons precede that correction.

Evidence: `tmp/render60/baseline-*`, `baseline-cost-summary.json`,
`irq-bound-sol.json`, `perf-0`, `final-reference`, `final-perf`, `stock-{0,1}`
and `final-comparison.json`. All matrices retain exact builds/listings, accepted
machine settings, field observations and endpoint state. The preceding A500
reference reproduces the rate-selection reference's three route results.

### Reticle state and redundant drawing

Pixel validation exposed a native render-dependent cache: hunk $bd02 refreshes
data-hunk $46e0 only when counter $1e96 is divisible by eight. Skipping that
render leaves a stale target-reticle flag. The first uncorrected SOL pair differed
by 162 reticle pixels, despite agreement in the older mapped-state checker.
`RETICLE_CLOCK=1` now runs the unchanged native target test $f954 after simulation
projection, on the native logic boundary with the same counter gate. Rendering
reads the cache. Inactive callers retain the native gate. The eight-native-update
cadence (1.6 s), counter wrapping and native reset behavior remain; no private
clock or RNG change is added. `simulation_state --presentation` now includes
`target_reticle`; older comparisons did not check it.

The native-reference fixture passes 64 cases / 128 comparisons at both selected
rates, spanning counter boundaries/wrap and running/rendering/logic gates. It
uses the actual original gate and unchanged target test with an empty active
list, then restores code and globals. The deliberately wrong render gate gives
16 errors and is rejected. This checks clock routing, not every target-test
input; live scene/state and pixel comparisons provide separate coverage.

On 68020 + 4 MB fast RAM, a diagnostic N=1 pacing trace changes ten renders
(six duplicates) to three (zero duplicates), with three observed updates in
both. The 75-update interval remains exactly 900 fields; presentations fall
283→75 because stale states are no longer redrawn. N=1 is diagnostic only and
remains rejected as a playable rate. At N=12 neither arm has duplicate draws;
131 presentations in 893→895 fields is within noise (-0.22%). The guard keeps
polling the elapsed-field clock and discards no ticks. This is correctness of
pacing, not a measured N=12 speedup. A 68060 instruction-capture attempt returned
no instruction records, so it supplies no attribution evidence.

### Validation and limits

Lossless held-display pairs pass A500 SOL/boss/type-10 and stock-A1200 type-10:
all 16000 fetched words, beam positions, effective palette/control state and
matched presentation state agree. Both comparison arms include the reticle fix.
The checker accepts bounded native viewport shake and equal scroll nibbles;
it replaces stale initial viewport register values only while display output
is blank and before copper programs every control ahead of pixel fetches.
Actual writes and all fetched pixels remain compared. Pixel/palette/valid-scroll
changes are detected; unsupported plane counts, unequal scroll and nonblank
starts are rejected. The old reticle mismatch is still detected.

Observed ownership checks pass 29 SOL, 34 boss and 16 combat polygons on A500;
all restore the originally enabled BLIT bit with unchanged callee-saved
registers/stack, and no BLIT IRQ inside the masked scope. Earlier stock-A1200
wrapper diagnostics cover 15 already-disabled entries, although that wrapper
is not selected there. Wrong restoration, stack imbalance and an injected BLIT
IRQ fail the checker. These are observed-path checks, not proof of every
possible external graphics-library caller.

Thirty-eight final matched-tick CPU/delayed-draw comparisons pass, including
reticle state. Fifty-nine previous/reference/optimized and stock comparisons
have only deferred projection scratch differences, with no reticle differences
at these sampled boundaries. The separate uncorrected held-display pair exposes
the stale reticle flag described above. Same-rate final state includes input history,
HUD and fresh actor projection. Cross-rate trajectory classifications remain
unchanged; this work does not equate different N trajectories.

The polygon/reticle implementation passes input fixtures, death/Continue,
No/restart, normal/early exits, disabled native-code preservation, release
diagnostic exclusion, all six rate builds, the 20 Hz override and both actual
launcher paths. Its static
audits cover 107 patches / 81 ranges on 68000 and 106 / 80 on 68020+, with
663 native relocated code pointers and no detected interior entries. With all
four rendering switches off, N=12 release/VERIFY reproduce the preceding
input-history bytes; the normal loader is unchanged. Launcher checks use
silent warp mode and disconnected controls, and do not replace audible-output
or physical-control playtesting.

Evidence: `tmp/render60/reticle-frames`, `reticle-fixtures`, `pacing`,
`final-display-controls.json`, `irq-checker-controls.json`, `final-cross`,
`final-input`, `final-lifecycle-n3`, `final-builds`, `play60-smoke-*` and
`final-tool-tests.log`. These captures precede the buffer-reuse correction;
its validation is described above. Broader encounters and real controls/audio
remain release work.

## CPU-rate selection

The rate-selection A500 captures use 512 KB chip and 1536 KB slow RAM, NTSC,
with input history and the stationary-star candidate enabled. The ordinary-pass
rate-selection reference measurements follow the table; current rendering
measurements are in the rendering section above.
SOL covers nominal 600→1500 ticks,
boss 3500→4100, and type-10 combat 600→5400 with checkpoints every 300 nominal
ticks. Boundaries and fixture triggers scale to each N. Each heavy window is
80 seconds of intended game time. Measured rates near the target and bounded,
recovering pending counts establish real-time throughput in this fixture.
They are not game-wide latency or performance guarantees.

| Fixed rate | SOL FPS | Combat FPS (80 s) | Early combat ms/frame | Late combat ms/frame | Boss FPS | Pending start→end |
|---|---:|---:|---:|---:|---:|---:|
| 10 Hz | 3.763 | 4.002 | 259.4 | 236.0 | 2.339 | 1→0 |
| 15 Hz | 3.400 | 3.690 | 234.5 | 279.2 | 2.195 | 1→1 |
| 20 Hz | 3.694 | 3.197 | 281.0 | 368.3 | 2.055 | 3→4 |
| 30 Hz | 3.115 | 3.037 | 288.6 | 319.5 | 1.837 | 8→8 |

The retained pre-optimization 60 Hz run averages 0.768 FPS over the same
nominal combat route; early/late presentation intervals are 1594/2913 ms.
Native early/late spot references are 225/243 ms, with boss presentation at
1.818 FPS. These are corresponding route windows, not identical trajectories;
the native figures use complete intervals from 100-field observations, whereas
the new early/late values aggregate the contiguous combat checkpoints.

**15 Hz is the selected playtest default.** Its 66.7 ms step gives better combat
and boss presentation than 20 or 30 Hz in these runs. Twenty Hz is faster in SOL.
Ten Hz gains about 8.5% in whole-combat presentation over 15 Hz but increases the
step by 50% to 100 ms. This is a measured tradeoff, not proof of a universal optimum.
An explicit N=4 build remains available for 20 Hz playtesting. The 200 ms N=1
step is not selected. No ticks are discarded and no interpolation is added.

The **15 Hz reference before rendering optimization** completes 1200 updates
in 4800 fields (80.0 s):
15.0 updates/s, 294 presentations (3.675 FPS), pending 1→1. Its early/late
combat presentation intervals are 239.8/278.4 ms. SOL averages 3.446 FPS and
boss 2.143 FPS. The 17 pending samples are
`1,2,2,1,3,3,1,3,3,2,2,2,2,1,4,3,1`.
All 84 checked boundaries across the four rates have complete input history
and no queue drops. All 84 same-rate comparisons against the retained lower-rate
captures agree for mapped gameplay, HUD and fresh projection; only deferred
projection scratch differs. The existing cross-N birth/admission, integration,
collision and RNG-order difference classifications therefore still apply to
these boundaries. The routes are not asserted identical across different rates.

Evidence: `tmp/optimize60/rates-n{2,3,4,6}`, `rate-comparison.json` and
`retained-rate-comparisons.json`. Ordinary-pass reference evidence is
`baseline-n3/`. Each
capture retains the exact binary, listing,
accepted emulator settings, field observations and endpoint state.

### Selected-rate validation

At N=3, all eight matched-tick scene comparisons pass against delayed 68020
rendering, covering SOL, early/late type-10 and boss. Death/Continue, No/restart
and normal/early level exits pass on A500 and delayed 68020, with eight further
matched-state comparisons. Only deferred projection scratch differs. Disabled
simulation preserves the audited native bytes with the explicit menu fixture
allowance. Input checks pass in all eight configurations listed below.

The rate-selection reference builds all six rates and passes the 104-hook static audit
(79 ranges, 663 relocated code pointers, no detected native interior entries).
The 20 Hz override matches the explicit N=4 build. The actual launcher reaches
the native menu at N=3 on 68000 and N=12 on 68020, with the audited release
bytes, default CUSTOM1 and no VERIFY menu fixtures. These smoke tests use silent
warp mode and disconnected input, so they do not establish audible output or
physical-control behavior. Nineteen host-tool tests pass. The normal loader
remains byte-identical. The all-off rendering reference
reproduces the input-history N=12 release and VERIFY bytes.

Evidence: `tmp/optimize60/input/validation.json`, `routes-n3/validation.json`,
`lifecycle-n3/validation.json`, `final-builds/validation.json`, the two
`play60-smoke-*` records, and `tool-tests.log`. Normal and playable builds are
restored after checking. Current rendering checks are above; broader playtesting remains.

## Simulation cost and stationary-star decision

Complete-call profiles cover SOL 600→1200, type-10 4500→5100 and boss
3500→4100 at N=12. Mean update costs include attributable same-context gaps
and exclude interrupts. These helpers overlap; their inclusive costs cannot
be summed as independent shares.

| CPU | SOL update cycles | Type-10 update cycles | Boss update cycles |
|---|---:|---:|---:|
| A500 / 68000 | 40860.2 | 90258.1 | 62153.4 |
| 68020 + 4 MB fast | 24560.5 | 52682.3 | 36834.2 |

The 68020 configuration uses the emulator's default CPU timing, not a fixed-MHz
hardware claim. In the A500 combat profile the native collision pass averages
50382.5 cycles, AI geometry 874.8 per call, sorting 4031.6 per update and stars
4489.4 per update. Input handling/history selection also consume time outside
the measured update entry. These are complete observed calls, not static bounds
or frame-rate predictions. Exact traces and cost reports are in
`tmp/optimize60/baseline-*`.

A writer-invalidated stationary-star shortcut is **not retained**. It reduced
N=12 complete-update means by 3.05/4.49/7.91% on A500 and 2.93/2.94/6.69% on
68020 in SOL/combat/boss. However, 68020 presentation changes were only
0.34/1.27/0.27%. At the selected A500 15 Hz, the same-build comparison is:

| Scene | Ordinary pass FPS | Shortcut FPS | Change |
|---|---:|---:|---:|
| SOL | 3.446 | 3.400 | -1.33% |
| Type-10, 80 seconds | 3.675 | 3.690 | +0.40% |
| Boss | 2.143 | 2.195 | +2.44% |

Those effects do not establish the playbook's required 3% frame benefit on
the selected paths. The ordinary pass is therefore retained, with no new
star cache, native hooks or memory requirements. Small FPS changes should not
be treated as resolved gains or regressions. The 15 Hz rate change, rather
than this shortcut, supplies the substantial A500 improvement.

The experiment passed 240 differential cases and three native/reset writer
checks on both N=12 CPUs and at all five lower rates. Its deliberate invalidation
failure and four altered-result controls were rejected. Twenty-six native-reference
groups passed on the tested N=3/N=12 candidate; the final builds remove the
candidate and preserve the prior ordinary implementation exactly. Twenty-one
selected-rate off/on gameplay/HUD/fresh-projection comparisons pass, allowing
only deferred projection scratch. The reference without the rendering changes
is byte-identical to the
preceding input-history release at N=12 and the measured ordinary-pass build
at N=3. Evidence is in `tmp/optimize60/low-n3-comparison.json`,
`profile-comparison.json`, `regress/` and `fixed-star-prototype/`; experimental
source and diagnostics remain in ignored scratch, not the active code.

## Input during catch-up

`history60.s` records controls in the native field callback at $11748. Each
world tick consumes the sample at `floor((tick-1)*field_hz/S60_RATE)`, using an
integer accumulator. The initial tick uses the session-entry sample. This
keeps the selected simulation rate on PAL as well as NTSC; at 60 Hz, a PAL
sample may serve two ticks.
There is no interpolation or deliberate presentation delay.

The collector copies the native 128-byte held-key array, both joystick port
words and CIA button bits. It never drains the key queue or runs gameplay.
The readers at $22730/$22746, port decoder at $1d20e, button-pointer load at
$1d2ee and modifier reads at $19600/$19606/$1960e use the selected copy while
world logic owns input. The input APIs preserve their native callee-saved
registers and do not require callers to retain the game data register.

The native keyboard interrupt still decodes presses/releases and updates its
held-key array. The accepted-press path at $19506 timestamps each existing
queue slot with its first eligible field. The reader at $195c8 removes the
newest eligible entry, leaving future entries in order. The native 32-entry
LIFO capacity and producer drop policy remain; the collector adds no repeat
or dequeue behavior. Native key translation uses the tick's modifier state.
Main-context copies and queue removals use short nested Disable/Enable pairs.

Modal entry/return atomically change both clock ownership and history ownership.
The native field clock continues for UI deadlines while the active-field
sequence stops. Menus, preferences and shutdown use live native input; the
pre-modal debt survives. Session entry resets the history epoch and reanchors
queued keys. Preferences remain simulation state, so historical raw controls
are interpreted by the mode active at that tick.

The game's gameplay analogue fallback calls the joystick driver at $1968c;
its raw-port path is covered by history. The separate input.device mouse
handler at $1dbb4–$1dde6 and pointer APIs at $1df1a/$1df80/$1df9c retain native
relative-event accumulation, clipping and pointer positioning for the UI.
The collector neither consumes mouse deltas nor changes those native modes.
Physical mouse/keyboard/joystick playtesting remains release work.

### Capacity and debugger state

The default ring holds 256 active fields in 36864 bytes allocated once before
play. It is reused across sessions, with no interrupt-time allocation. Allocation
failure reports an explicit message. Pauses do not consume ring capacity. If
an owed field has been overwritten, that tick receives neutral held controls,
directions and button bits; timestamped queued commands retain their own
eligibility. No simulation debt is discarded, no rate is lowered and the game
does not abort. Every affected tick increments a recovery counter. Such recovery
is intentionally distinguishable from an exact replay and may change gameplay.

ABI 30 preserves the previous prefix and rate tag. Entry+136/+138 describe the
32-byte `IH60` state: signature at +0, buffer pointer +4, produced active field
+8, next field +12, fractional field credit +16, capacity +18, missing-sample
ticks +20, native queue drops +24 and selected field +28. A selected 144-byte
sample follows: field +0, port words +4/+6, CIA byte +8, 128 held-key bytes +12.
Ring samples use the same layout. Readers retain support for ABI 29 references.

### Validation and response timing

The elapsed-field fixture changes held left/right, hardware direction and fire
at fields 20,40,60,80,100,120,140,160 through real gameplay readers with CUSTOM3
off. All eight selected-rate configurations pass 200 recorded ticks and **96
private native-reference assertions each**. At N=3, NTSC edges reach ticks
6,11,16,21,26,31,36,41; at N=12 they reach 21,41,61,81,101,121,141,161.
PAL N=12 edges reach 25,49,73,97,121,145,169,193. Same-rate NTSC gameplay/HUD/
fresh-projection comparisons agree across CPUs and delayed drawing; only deferred
projection scratch differs. The N=3 preference fixture also retains input/clock
accounting after modal return. The retained deliberate live-sample negative
control is rejected at tick 2 (field 29 instead of field 1).

Private cases cover queue ordering, removing old entries underneath future ones, full
capacity and one dropped press, all eight modifier combinations, live modal
and inactive ownership, keyboard direction precedence, all sixteen electrical
joystick direction combinations, twelve button cases and caller register
independence. These checks enter the native accepted-press tail after CIA
hardware decoding; they do not test physical keyboard hardware.

For these eight edges, the observed delays are in emulated fields:

| Configuration | Rate | Event to input consumption | Event to first subsequent render completion |
|---|---:|---:|---:|
| A500 | 15 Hz | 3–26 | 25–53 |
| 68020 + fast RAM, diagnostic N=3 | 15 Hz | 0–8 | 9–17 |
| 68020 + fast RAM, diagnostic N=3, SLOW_DRAW=20 | 15 Hz | 2–22 | 32–52 |
| 68020 + fast RAM | 60 Hz | 3–11 | 10–22 |
| 68020 + fast RAM, SLOW_DRAW=20 | 60 Hz | 8–31 | 35–64 |
| Stock A1200 | 60 Hz | 7–20 | 19–39 |
| 68060/50 | 60 Hz | 0–3 | 3–7 |
| PAL 68060/50 | 60 Hz | 0–3 | 3–6 |

NTSC fields are 1/60 s; the PAL row uses 1/50 s fields while simulating at 60 Hz.
These are window-local observations, not maximum latency bounds. The second
column records completion of input handling; the third records the first render
completed after that tick. It does not prove physical-device latency, scanout
completion or pixel-level visibility of every press/release edge. Slow drawing
can span both edges. History corrects input assignment; it cannot remove the
rendering and simulation backlog shown here.

The retained N=12 long-pause test observes native dialog entry/return at fields 1250/1856:
606 excluded fields, including cleanup after the 600-field requested wait.
Pending updates change 31→30 while one tick completes and no active field
passes. History remains intact. Forced capacity 16 with SLOW_DRAW=80 reports
190 recovered samples by tick 200, continues the owed updates and fails the
ordinary exact-input gate as intended.

Movement-quanta/braking and preference fixtures pass. SOL checkpoints 600/1500
match the restoration reference on A500 and 68020. Death/Continue, No/restart
and normal/early exits pass on A500 and delayed 68020, with eight matched-state
comparisons. Disabled code and relocations match with only the explicit menu
fixture allowed. Static release auditing finds 104 patches in 79 ranges,
663 relocated code pointers and no detected native interior entries. Installed
hooks, all six rate builds, diagnostic exclusion, default/explicit N=12 identity,
19 tool tests and the actual play60 release/menu smoke pass. Release and VERIFY
now intentionally differ from the pre-history restoration binaries.

### A500 heavy-combat check

The retained N=12 input-history reference takes 4924 NTSC fields (82.066667 s),
averaging **58.489033 updates/s and 0.767669 presentations/s**. Pending updates
grow 24→148; checkpoint samples are
`24,27,36,73,100,120,74,65,79,70,43,52,124,174,203,159,148`.
The pre-history reference was 59.113300 updates/s, 0.948276 presentations/s,
pending 23→95. This is not sustained real-time simulation. The selected 15 Hz A500
measurements above replace it as the playable throughput target.

At tick 5400, cumulative missing-sample and queue-drop counts remain zero; matched
600/5400 gameplay state agrees with the reference apart from deferred projection
scratch. The performance route retains the existing tick-indexed CUSTOM3 pilot,
so it measures that fixture's whole-scene throughput and history usage, not
physical-control latency or isolated history-handler cycles.

Evidence is under `tmp/input-history`: `verified/validation.json`,
`final/validation.json`, `lifecycle/validation.json`, `heavy/matrix.json`,
`heavy/history.json`, `build-validation.json`, `play60-smoke/validation.json`
and the exact per-capture listings, slaves and records. Captures remain ignored.

## 60 Hz reference before input history

These retained reference captures use the migrated AmigaXDev launcher,
debugger and shared trace/patch readers. Builds use the default N=12; the release and VERIFY
SHA-256 values remain those in the parameterization section. The accepted
UAE memory/timing options are retained in `emulator-settings.log`; Exec
VBlankFrequency independently agrees with every requested display standard.
These reference captures retain the requested SetCPU policy; current live register
observations are documented under Fast-CPU presentation and sustained combat.
Configuration checks use private UAE options and the observed clock; the
shared startup-log race described in the current investigation can contaminate
copied frontend headers. The retained reference uses its checked replacement
capture rather than the excluded log-mismatch artifact.

A500 heavy combat 600→5400: **59.113300 updates/s**,
**0.948276 presentations/s**, 4872 fields over
81.200000 seconds; pending 23→95.
Pending samples at ticks 600,900,…,5400: `23, 21, 26, 61, 86, 92, 50, 53, 65, 60, 37, 46, 103, 158, 154, 109, 95`.
This is measured throughput, not a claim that the restored A500 keeps up.
Short intervals above 60 updates/s can repay existing debt. Gap figures below
are local to their 100-field observations, not game-wide latency bounds.

All 56 cross-CPU/PAL and 64 comparisons against the retained N=12 baseline
agree in mapped gameplay, HUD and fresh projection, apart from deferred
projection scratch. All 16 SLOW_DRAW/lifecycle endpoint comparisons also pass.
Death/Continue, No/menu/restart and normal/early exits to level six pass on
A500 and delayed 68020. CUSTOM1-off code/relocations pass with only the menu
fixture allowed. The release audit finds 89 patches in 69 merged ranges,
663 relocated code pointers and no detected native interior entries.
The actual play60 release reaches the native menu with N=12 and 89 installed
hooks, no menu fixture and an exact release match. The one-field screenshot
also exercises the shared trace reader. This silent, disconnected-input smoke
does not establish audible output or physical-control playtesting.

Evidence: `tmp/restore60/build-validation.json`, `restoration-validation.json`,
`release-audit.json`, `regression/validation.json`, `play60-smoke/validation.json`,
`matrix/cross-cpu-validation.json` and individual cell reports. Captures remain
ignored. Normal and playable builds are restored after validation.

The shared trace reader also matches the retained project reader on all
467689 instruction records across 50 retained fields,
including DMA, registers and screenshots (465747 records have instruction PCs).
This is parser compatibility evidence, not a new instruction-cost measurement;
see `tmp/restore60/trace-reader-validation.json`.

### Native and SIM60 matrix

| Machine | Route | Updates/s | Presentations/s | Pending growth | Largest observed update-start gap (fields) |
|---|---|---:|---:|---:|---:|
| a500 | sol | 61.224 | 2.517 | -18 | 26 |
| a500 | type10-early | 63.830 | 0.745 | -36 | 14 |
| a500 | type10-late | 64.516 | 0.430 | -63 | 1 |
| a500 | boss | 68.311 | 1.025 | -73 | 36 |
| a500 | native-90 | 4.800 | 5.000 | — | 12 |
| a500 | native-240 | 3.600 | 4.000 | — | 17 |
| a1200-stock | sol | 61.155 | 5.504 | -17 | 11 |
| a1200-stock | type10-early | 60.504 | 3.832 | -5 | 8 |
| a1200-stock | type10-late | 61.433 | 3.345 | -21 | 13 |
| a1200-stock | boss | 61.644 | 2.774 | -16 | 22 |
| a1200-stock | native-90 | 7.800 | 8.000 | — | 8 |
| a1200-stock | native-240 | 5.400 | 6.000 | — | 11 |
| a1200-fast | sol | 60.134 | 8.953 | -2 | 9 |
| a1200-fast | type10-early | 60.201 | 9.231 | -2 | 6 |
| a1200-fast | type10-late | 60.134 | 9.087 | -2 | 6 |
| a1200-fast | boss | 60.606 | 5.859 | -6 | 13 |
| a1200-fast | native-90 | 12.000 | 12.000 | — | 5 |
| a1200-fast | native-240 | 7.800 | 7.912 | — | 10 |
| 030-50 | sol | 60.134 | 18.909 | -2 | 5 |
| 030-50 | type10-early | 59.900 | 22.662 | 1 | 3 |
| 030-50 | type10-late | 59.933 | 22.375 | 1 | 3 |
| 030-50 | boss | 60.403 | 14.396 | -4 | 6 |
| 030-50 | native-90 | 19.800 | 20.000 | — | 3 |
| 030-50 | native-240 | 15.600 | 15.464 | — | 5 |
| 040-25 | sol | 60.067 | 23.626 | -1 | 4 |
| 040-25 | type10-early | 59.900 | 29.052 | 1 | 3 |
| 040-25 | type10-late | 59.933 | 29.101 | 1 | 3 |
| 040-25 | boss | 60.100 | 19.132 | -1 | 4 |
| 040-25 | native-90 | 30.000 | 30.000 | — | 2 |
| 040-25 | native-240 | 18.600 | 18.947 | — | 4 |
| 060-50 | sol | 60.000 | 23.933 | 0 | 4 |
| 060-50 | type10-early | 60.000 | 29.400 | 0 | 3 |
| 060-50 | type10-late | 60.067 | 29.499 | -1 | 3 |
| 060-50 | boss | 59.900 | 19.368 | 1 | 4 |
| 060-50 | native-90 | 30.000 | 30.000 | — | 2 |
| 060-50 | native-240 | 18.600 | 18.947 | — | 4 |
| a500-pal | sol | 61.141 | 2.514 | -17 | 21 |
| a500-pal | type10-early | 64.103 | 0.748 | -38 | 11 |
| a500-pal | type10-late | 62.762 | 0.488 | -40 | 17 |
| a500-pal | boss | 69.124 | 1.037 | -79 | 21 |
| a500-pal | native-90 | 5.000 | 5.000 | — | 10 |
| a500-pal | native-240 | 3.500 | 3.896 | — | 15 |
| 060-50-pal | sol | 60.080 | 25.300 | -1 | 3 |
| 060-50-pal | type10-early | 59.880 | 30.739 | 1 | 2 |
| 060-50-pal | type10-late | 60.000 | 28.600 | 0 | 2 |
| 060-50-pal | boss | 60.120 | 18.938 | -1 | 4 |
| 060-50-pal | native-90 | 25.000 | 25.000 | — | 2 |
| 060-50-pal | native-240 | 20.500 | 20.408 | — | 3 |

SIM60 rates use completed-tick endpoints; native presentations use complete inter-presentation intervals in a 100-field window. Gap values are window-local, not game-wide maxima. Pending growth is not applicable to native timing.

### Native combat comparisons

| Machine | Route | Updates/s | Presentations/s | Pending growth | Largest observed update-start gap (fields) |
|---|---|---:|---:|---:|---:|
| a500 | native-type10-early | 4.200 | 4.444 | — | 14 |
| a500 | native-type10-late | 3.600 | 4.110 | — | 15 |
| a500 | native-boss | 1.800 | 1.818 | — | 35 |
| a1200-stock | native-type10-early | 7.200 | 7.500 | — | 8 |
| a1200-stock | native-type10-late | 7.200 | 7.021 | — | 9 |
| a1200-stock | native-boss | 3.000 | 3.117 | — | 22 |
| a1200-fast | native-type10-early | 9.600 | 10.000 | — | 6 |
| a1200-fast | native-type10-late | 9.000 | 9.545 | — | 8 |
| a1200-fast | native-boss | 6.000 | 5.783 | — | 13 |
| 030-50 | native-type10-early | 19.800 | 20.000 | — | 3 |
| 030-50 | native-type10-late | 18.000 | 18.125 | — | 4 |
| 030-50 | native-boss | 13.800 | 13.548 | — | 6 |
| 040-25 | native-type10-early | 19.800 | 20.000 | — | 3 |
| 040-25 | native-type10-late | 19.800 | 20.000 | — | 3 |
| 040-25 | native-boss | 16.800 | 16.875 | — | 4 |
| 060-50 | native-type10-early | 19.800 | 20.000 | — | 3 |
| 060-50 | native-type10-late | 19.800 | 20.000 | — | 3 |
| 060-50 | native-boss | 16.800 | 17.053 | — | 4 |
| a500-pal | native-type10-early | 4.500 | 4.545 | — | 11 |
| a500-pal | native-type10-late | 4.000 | 4.070 | — | 13 |
| a500-pal | native-boss | 2.000 | 1.852 | — | 29 |
| 060-50-pal | native-type10-early | 25.000 | 25.000 | — | 2 |
| 060-50-pal | native-type10-late | 25.000 | 25.000 | — | 2 |
| 060-50-pal | native-boss | 16.500 | 16.489 | — | 4 |

SIM60 rates use completed-tick endpoints; native presentations use complete inter-presentation intervals in a 100-field window. Gap values are window-local, not game-wide maxima. Pending growth is not applicable to native timing.

<!-- rate-candidates:start -->
## Lower-rate comparison evidence

**Retained lower-rate references; current CPU defaults are N=3 and N=12.** The full
N=2,3,4,6 matrices rejected every requested candidate on presentation rate,
so the remaining supported lower value N=1 was measured with the same gates.
N=12 also fails the presentation gate. N=1 is therefore the largest supported
N that meets the former throughput conditions in these captures.
That selection does not meet the current responsiveness requirement. The simple cost model did
not predict the measured scene-dependent presentation rates accurately enough
to select N=3 or N=4. Selection uses measurements, not that prediction.

Route names retain the nominal N=12 schedule; captures scale tick numbers to
the same game-time windows at each N. Cross-N encounters can differ as
classified below; these are matched route/time windows, not identical actor
trajectories across rates. Every machine within one N shares identical
matched-tick gameplay, HUD and fresh projection state.

Native A500 frame ranges 150–200 and 375–450 measure **4.411765 and
4.083485 presentations/s** (50/680 and 75/1102 presentations/fields at 60 Hz).
Their 301 contiguous presentation-anchor observations pass original-code,
setup-removal, exact-slave and initial mapped-state checks. The step-0
100-field spot references remain 4.444/4.110; both reference methods give
the same pass/fail decisions. Native game pace remains variable.

| N | Tick rate | A500 early fps | A500 late fps | At least native in both? |
|---:|---:|---:|---:|---|
| 1 | 5 Hz | 4.723618 | 4.385382 | yes |
| 2 | 10 Hz | 3.953871 | 4.342984 | no |
| 3 | 15 Hz | 4.300000 | 3.656885 | no |
| 4 | 20 Hz | 3.624161 | 2.793792 | no |
| 6 | 30 Hz | 3.517588 | 3.203560 | no |

N=1 heavy combat completes 400 ticks in 4811 NTSC fields (80.183333 s):
4.988568 updates/s and 4.340054 presentations/s. Endpoint pending is 0→1;
five-simulation-second samples remain 0–1 with no accumulating trend.
The finite observation ends with one owed update; it does not indicate a
different configured timestep. These samples are not an instantaneous global
backlog bound. All candidate heavy-window samples are retained below.

The tick is 200 ms. Faster CPUs can present more often than 5 Hz, but poses
repeat between ticks. This 200 ms timestep is rejected as the target; the
active plan selects 15 Hz on 68000 and 60 Hz on 68020+, excluding interpolation.

### Retained N=1 regression

The retained N=1 release is identical to explicit N=1 and differs from the measured
N=1 release only in its displayed rate digits. Explicit N=12 release and VERIFY
still match the original SHA-256 values in the parameterization section.
All four SLOW_DRAW=20 routes match the N=1 A500 at both completed-tick
endpoints. Death/Continue, No/menu/new game, normal exits and early exits
also pass on A500 and delayed 68020; all 16 endpoint comparisons agree in
mapped gameplay, HUD and fresh projection, allowing only deferred projection
scratch. The normal/early fixtures reach level six.

The CUSTOM1-off capture passes the original-code/relocation checker with only
its explicit menu fixture allowed. The release audit covers 89 patch commands,
69 merged ranges and 663 relocated code pointers, with no detected native
interior entries. All 89 simulation hooks are installed in the actual
`play60.sh` release smoke capture; the native menu is reached, menu fixtures
are absent, and the ABI reports N=1. The menu image is also visually checked.
The smoke uses debug/warp/silent observation and disconnected input, so it does
not establish physical controls or audible output. Static hook coverage is
not proof of every indirect entry or replacement semantic.

Evidence: `tmp/rate-selected-n1/build-validation.json`, `validation.json`,
`release-audit.json`, individual lifecycle/disabled reports and
`play60-smoke/validation.json`. The 19 tooling tests pass. Normal and playable
builds are restored after validation. The remaining 60 Hz performance and release work is in
`docs/open-work.md`; interpolation is excluded.

### Before → after presentation matrix

Each entry is N=12 → N=1 presentations/s, from completed-tick endpoints.
Full updates/s, pending growth and window-local update-start gaps appear in
the candidate and baseline tables. Machine settings and cache policy are
unchanged; these are emulator measurements under the documented SetCPU policy.

| Machine | SOL | Type-10 early | Type-10 late | Boss |
|---|---:|---:|---:|---:|
| a500 | 2.517 → 5.479 | 0.745 → 4.724 | 0.430 → 4.385 | 1.025 → 2.517 |
| a1200-stock | 5.504 → 12.428 | 3.832 → 11.900 | 3.345 → 10.733 | 2.774 → 4.214 |
| a1200-fast | 8.953 → 18.976 | 9.231 → 18.200 | 9.087 → 17.219 | 5.859 → 7.005 |
| 030-50 | 18.909 → 35.533 | 22.662 → 35.058 | 22.375 → 34.572 | 14.396 → 18.869 |
| 040-25 | 23.626 → 40.800 | 29.052 → 40.568 | 29.101 → 40.200 | 19.132 → 25.158 |
| 060-50 | 23.933 → 41.000 | 29.400 → 40.800 | 29.499 → 40.467 | 19.368 → 25.957 |
| a500-pal | 2.514 → 5.653 | 0.748 → 4.771 | 0.488 → 4.424 | 1.037 → 2.532 |
| 060-50-pal | 25.300 → 44.467 | 30.739 → 38.700 | 28.600 → 38.451 | 18.938 → 26.347 |

The heavy route covers nominal 600–5400 (80 simulation seconds), with
pending sampled every five simulation seconds. Update-start gaps below
cover only the separate 100-field observation at each route start.

Native reference binaries remain byte-identical after parameterization
(`tmp/native-rate-baseline-reuse.json`). Evidence: `tmp/rate-nN`,
`tmp/rate-nN-heavy`, `tmp/rate-native-exact` and
`tmp/rate-selection-evidence.json`. Selected release code differs from the
measured N=1 code only in the two menu-label rate digits; explicit N=12
release and VERIFY bytes still match the step-0 baseline.

### N=1: 5 Hz

A500 heavy window: 4.988568 updates/s, 4.340054
presentations/s over 80.183333 observed seconds. Sampled pending updates:
`0, 0, 1, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 1`.
All 56 matched-tick cross-CPU/PAL comparisons pass, allowing only deferred
projection scratch; gameplay, HUD and fresh projection state match.

| Machine | Route | Updates/s | Presentations/s | Pending growth | Largest observed update-start gap (fields) |
|---|---|---:|---:|---:|---:|
| a500 | sol | 5.073 | 5.479 | -1 | 15 |
| a500 | type10-early | 5.025 | 4.724 | -1 | 13 |
| a500 | type10-late | 4.983 | 4.385 | 1 | 14 |
| a500 | boss | 5.245 | 2.517 | -2 | 35 |
| a1200-stock | sol | 5.011 | 12.428 | 0 | 14 |
| a1200-stock | type10-early | 5.000 | 11.900 | 0 | 14 |
| a1200-stock | type10-late | 5.000 | 10.733 | 0 | 15 |
| a1200-stock | boss | 5.017 | 4.214 | 0 | 21 |
| a1200-fast | sol | 5.011 | 18.976 | 0 | 14 |
| a1200-fast | type10-early | 5.000 | 18.200 | 0 | 13 |
| a1200-fast | type10-late | 5.006 | 17.219 | 0 | 14 |
| a1200-fast | boss | 5.076 | 7.005 | -1 | 19 |
| 030-50 | sol | 5.000 | 35.533 | 0 | 13 |
| 030-50 | type10-early | 5.008 | 35.058 | 0 | 12 |
| 030-50 | type10-late | 5.006 | 34.572 | 0 | 12 |
| 030-50 | boss | 4.992 | 18.869 | 0 | 14 |
| 040-25 | sol | 5.000 | 40.800 | 0 | 13 |
| 040-25 | type10-early | 5.008 | 40.568 | 0 | 13 |
| 040-25 | type10-late | 5.000 | 40.200 | 0 | 12 |
| 040-25 | boss | 4.992 | 25.158 | 0 | 13 |
| 060-50 | sol | 5.000 | 41.000 | 0 | 13 |
| 060-50 | type10-early | 5.000 | 40.800 | 0 | 13 |
| 060-50 | type10-late | 5.000 | 40.467 | 0 | 13 |
| 060-50 | boss | 4.992 | 25.957 | 0 | 13 |
| a500-pal | sol | 5.047 | 5.653 | -1 | 12 |
| a500-pal | type10-early | 4.970 | 4.771 | 1 | 11 |
| a500-pal | type10-late | 5.027 | 4.424 | 0 | 12 |
| a500-pal | boss | 5.274 | 2.532 | -2 | 22 |
| 060-50-pal | sol | 5.000 | 44.467 | 0 | 11 |
| 060-50-pal | type10-early | 5.000 | 38.700 | 0 | 11 |
| 060-50-pal | type10-late | 5.007 | 38.451 | 0 | 11 |
| 060-50-pal | boss | 4.990 | 26.347 | 0 | 11 |

SIM60 rates use completed-tick endpoints; native presentations use complete inter-presentation intervals in a 100-field window. Gap values are window-local, not game-wide maxima. Pending growth is not applicable to native timing.

### N=2: 10 Hz

A500 heavy window: 9.995835 updates/s, 4.085798
presentations/s over 80.033333 observed seconds. Sampled pending updates:
`1, 1, 1, 0, 0, 1, 1, 2, 1, 1, 1, 1, 1, 1, 2, 0, 1`.
All 56 matched-tick cross-CPU/PAL comparisons pass, allowing only deferred
projection scratch; gameplay, HUD and fresh projection state match.

| Machine | Route | Updates/s | Presentations/s | Pending growth | Largest observed update-start gap (fields) |
|---|---|---:|---:|---:|---:|
| a500 | sol | 10.022 | 3.808 | 0 | 19 |
| a500 | type10-early | 9.885 | 3.954 | 1 | 15 |
| a500 | type10-late | 10.022 | 4.343 | 0 | 14 |
| a500 | boss | 10.417 | 2.396 | -4 | 33 |
| a1200-stock | sol | 10.147 | 6.967 | -2 | 11 |
| a1200-stock | type10-early | 9.934 | 7.351 | 0 | 9 |
| a1200-stock | type10-late | 10.033 | 7.960 | -1 | 8 |
| a1200-stock | boss | 9.983 | 4.093 | 0 | 21 |
| a1200-fast | sol | 10.022 | 9.688 | 0 | 9 |
| a1200-fast | type10-early | 9.967 | 11.860 | 0 | 8 |
| a1200-fast | type10-late | 10.000 | 13.000 | 0 | 8 |
| a1200-fast | boss | 10.017 | 6.611 | 0 | 13 |
| 030-50 | sol | 9.989 | 26.371 | 0 | 7 |
| 030-50 | type10-early | 10.000 | 30.800 | 0 | 7 |
| 030-50 | type10-late | 10.000 | 31.733 | 0 | 7 |
| 030-50 | boss | 10.000 | 16.900 | 0 | 9 |
| 040-25 | sol | 9.989 | 33.496 | 0 | 6 |
| 040-25 | type10-early | 10.000 | 37.500 | 0 | 7 |
| 040-25 | type10-late | 10.000 | 38.000 | 0 | 7 |
| 040-25 | boss | 10.017 | 23.139 | 0 | 8 |
| 060-50 | sol | 10.000 | 33.800 | 0 | 6 |
| 060-50 | type10-early | 10.017 | 37.863 | 0 | 7 |
| 060-50 | type10-late | 10.000 | 38.400 | 0 | 7 |
| 060-50 | boss | 10.000 | 23.900 | 0 | 8 |
| a500-pal | sol | 10.302 | 3.915 | -4 | 16 |
| a500-pal | type10-early | 9.960 | 3.984 | 0 | 13 |
| a500-pal | type10-late | 9.973 | 4.388 | 0 | 11 |
| a500-pal | boss | 10.395 | 2.391 | -4 | 28 |
| 060-50-pal | sol | 10.000 | 36.667 | 0 | 6 |
| 060-50-pal | type10-early | 10.000 | 40.800 | 0 | 5 |
| 060-50-pal | type10-late | 10.000 | 41.467 | 0 | 6 |
| 060-50-pal | boss | 10.000 | 23.900 | 0 | 6 |

SIM60 rates use completed-tick endpoints; native presentations use complete inter-presentation intervals in a 100-field window. Gap values are window-local, not game-wide maxima. Pending growth is not applicable to native timing.

### N=3: 15 Hz

A500 heavy window: 15.018773 updates/s, 3.754693
presentations/s over 79.900000 observed seconds. Sampled pending updates:
`2, 1, 2, 4, 1, 2, 1, 4, 2, 1, 3, 0, 2, 4, 2, 0, 0`.
All 56 matched-tick cross-CPU/PAL comparisons pass, allowing only deferred
projection scratch; gameplay, HUD and fresh projection state match.

| Machine | Route | Updates/s | Presentations/s | Pending growth | Largest observed update-start gap (fields) |
|---|---|---:|---:|---:|---:|
| a500 | sol | 15.393 | 3.558 | -5 | 25 |
| a500 | type10-early | 15.000 | 4.300 | 0 | 13 |
| a500 | type10-late | 15.237 | 3.657 | -4 | 21 |
| a500 | boss | 15.075 | 2.211 | -1 | 35 |
| a1200-stock | sol | 15.017 | 6.407 | 0 | 15 |
| a1200-stock | type10-early | 14.925 | 8.060 | 0 | 8 |
| a1200-stock | type10-late | 15.186 | 6.952 | -2 | 13 |
| a1200-stock | boss | 15.203 | 3.953 | -2 | 21 |
| a1200-fast | sol | 15.169 | 8.966 | -2 | 8 |
| a1200-fast | type10-early | 15.025 | 11.920 | 0 | 6 |
| a1200-fast | type10-late | 15.050 | 10.903 | -1 | 8 |
| a1200-fast | boss | 15.254 | 6.508 | -3 | 13 |
| 030-50 | sol | 15.017 | 19.488 | 0 | 5 |
| 030-50 | type10-early | 14.975 | 29.850 | 0 | 4 |
| 030-50 | type10-late | 15.017 | 28.365 | 0 | 5 |
| 030-50 | boss | 15.075 | 14.774 | 0 | 6 |
| 040-25 | sol | 15.000 | 28.200 | 0 | 5 |
| 040-25 | type10-early | 14.975 | 36.439 | 0 | 5 |
| 040-25 | type10-late | 15.000 | 35.533 | 0 | 5 |
| 040-25 | boss | 15.000 | 20.900 | 0 | 6 |
| 060-50 | sol | 15.000 | 28.600 | 0 | 5 |
| 060-50 | type10-early | 15.000 | 36.800 | 0 | 5 |
| 060-50 | type10-late | 15.000 | 36.000 | 0 | 5 |
| 060-50 | boss | 15.050 | 21.472 | 0 | 6 |
| a500-pal | sol | 15.306 | 3.537 | -5 | 21 |
| a500-pal | type10-early | 14.881 | 4.365 | 1 | 11 |
| a500-pal | type10-late | 15.162 | 3.706 | -2 | 17 |
| a500-pal | boss | 14.881 | 2.183 | 1 | 27 |
| 060-50-pal | sol | 15.000 | 31.133 | 0 | 5 |
| 060-50-pal | type10-early | 15.000 | 39.800 | 0 | 4 |
| 060-50-pal | type10-late | 15.000 | 35.600 | 0 | 5 |
| 060-50-pal | boss | 15.030 | 20.541 | 0 | 5 |

SIM60 rates use completed-tick endpoints; native presentations use complete inter-presentation intervals in a 100-field window. Gap values are window-local, not game-wide maxima. Pending growth is not applicable to native timing.

### N=4: 20 Hz

A500 heavy window: 19.975031 updates/s, 3.295880
presentations/s over 80.100000 observed seconds. Sampled pending updates:
`2, 4, 2, 3, 4, 7, 2, 3, 4, 5, 1, 4, 3, 3, 2, 3, 4`.
All 56 matched-tick cross-CPU/PAL comparisons pass, allowing only deferred
projection scratch; gameplay, HUD and fresh projection state match.

| Machine | Route | Updates/s | Presentations/s | Pending growth | Largest observed update-start gap (fields) |
|---|---|---:|---:|---:|---:|
| a500 | sol | 20.293 | 3.720 | -4 | 26 |
| a500 | type10-early | 20.134 | 3.624 | -2 | 13 |
| a500 | type10-late | 19.956 | 2.794 | 1 | 20 |
| a500 | boss | 20.067 | 2.107 | 0 | 34 |
| a1200-stock | sol | 20.247 | 6.952 | -4 | 11 |
| a1200-stock | type10-early | 19.900 | 7.065 | 1 | 8 |
| a1200-stock | type10-late | 19.934 | 5.581 | 1 | 13 |
| a1200-stock | boss | 20.168 | 3.832 | -2 | 21 |
| a1200-fast | sol | 20.022 | 9.611 | 0 | 9 |
| a1200-fast | type10-early | 20.000 | 11.000 | 0 | 6 |
| a1200-fast | type10-late | 19.978 | 8.923 | 1 | 7 |
| a1200-fast | boss | 20.270 | 6.385 | -2 | 13 |
| 030-50 | sol | 20.022 | 19.689 | 0 | 4 |
| 030-50 | type10-early | 20.000 | 25.400 | 0 | 4 |
| 030-50 | type10-late | 19.978 | 20.377 | 0 | 4 |
| 030-50 | boss | 20.000 | 14.700 | 0 | 6 |
| 040-25 | sol | 19.978 | 25.172 | 0 | 4 |
| 040-25 | type10-early | 20.000 | 33.500 | 0 | 4 |
| 040-25 | type10-late | 19.978 | 28.701 | 0 | 4 |
| 040-25 | boss | 19.967 | 19.268 | 0 | 4 |
| 060-50 | sol | 20.000 | 25.467 | 0 | 4 |
| 060-50 | type10-early | 20.000 | 33.900 | 0 | 4 |
| 060-50 | type10-late | 20.000 | 29.267 | 0 | 4 |
| 060-50 | boss | 20.033 | 19.533 | 0 | 4 |
| a500-pal | sol | 20.270 | 3.784 | -4 | 21 |
| a500-pal | type10-early | 19.881 | 3.678 | 1 | 11 |
| a500-pal | type10-late | 20.027 | 2.804 | 0 | 17 |
| a500-pal | boss | 20.080 | 2.108 | -1 | 27 |
| 060-50-pal | sol | 20.027 | 27.637 | 0 | 3 |
| 060-50-pal | type10-early | 20.040 | 32.064 | 0 | 4 |
| 060-50-pal | type10-late | 20.000 | 27.800 | 0 | 3 |
| 060-50-pal | boss | 19.960 | 19.860 | 0 | 4 |

SIM60 rates use completed-tick endpoints; native presentations use complete inter-presentation intervals in a 100-field window. Gap values are window-local, not game-wide maxima. Pending growth is not applicable to native timing.

### N=6: 30 Hz

A500 heavy window: 29.950083 updates/s, 3.107321
presentations/s over 80.133333 observed seconds. Sampled pending updates:
`4, 4, 4, 7, 7, 7, 5, 13, 4, 6, 11, 3, 7, 9, 7, 5, 8`.
All 56 matched-tick cross-CPU/PAL comparisons pass, allowing only deferred
projection scratch; gameplay, HUD and fresh projection state match.

| Machine | Route | Updates/s | Presentations/s | Pending growth | Largest observed update-start gap (fields) |
|---|---|---:|---:|---:|---:|
| a500 | sol | 30.134 | 3.214 | -2 | 19 |
| a500 | type10-early | 30.151 | 3.518 | -2 | 13 |
| a500 | type10-late | 30.033 | 3.204 | -1 | 14 |
| a500 | boss | 31.088 | 1.865 | -10 | 36 |
| a1200-stock | sol | 30.337 | 6.202 | -5 | 11 |
| a1200-stock | type10-early | 30.252 | 7.160 | -3 | 7 |
| a1200-stock | type10-late | 30.067 | 6.548 | -1 | 8 |
| a1200-stock | boss | 30.050 | 3.606 | 0 | 21 |
| a1200-fast | sol | 29.967 | 9.057 | 1 | 9 |
| a1200-fast | type10-early | 29.900 | 11.462 | 1 | 5 |
| a1200-fast | type10-late | 29.967 | 10.855 | 0 | 6 |
| a1200-fast | boss | 30.100 | 6.321 | -1 | 13 |
| 030-50 | sol | 30.000 | 18.533 | 0 | 4 |
| 030-50 | type10-early | 30.050 | 24.040 | 0 | 3 |
| 030-50 | type10-late | 30.000 | 23.467 | 0 | 3 |
| 030-50 | boss | 30.050 | 15.025 | 0 | 6 |
| 040-25 | sol | 30.033 | 23.359 | 0 | 4 |
| 040-25 | type10-early | 30.000 | 30.000 | 0 | 2 |
| 040-25 | type10-late | 30.000 | 29.533 | 0 | 3 |
| 040-25 | boss | 29.950 | 19.567 | 1 | 5 |
| 060-50 | sol | 30.033 | 23.560 | 0 | 4 |
| 060-50 | type10-early | 30.000 | 30.000 | 0 | 3 |
| 060-50 | type10-late | 29.967 | 29.767 | 0 | 2 |
| 060-50 | boss | 30.050 | 19.933 | 0 | 4 |
| a500-pal | sol | 30.949 | 3.301 | -14 | 16 |
| a500-pal | type10-early | 29.940 | 3.593 | 1 | 10 |
| a500-pal | type10-late | 30.283 | 3.230 | -4 | 11 |
| a500-pal | boss | 32.120 | 1.820 | -20 | 27 |
| 060-50-pal | sol | 30.040 | 26.435 | -1 | 3 |
| 060-50-pal | type10-early | 30.000 | 30.000 | 0 | 3 |
| 060-50-pal | type10-late | 30.000 | 29.733 | 0 | 3 |
| 060-50-pal | boss | 30.000 | 19.500 | 0 | 4 |

SIM60 rates use completed-tick endpoints; native presentations use complete inter-presentation intervals in a 100-field window. Gap values are window-local, not game-wide maxima. Pending growth is not applicable to native timing.

<!-- rate-candidates:end -->

## Substep parameterization

`S60_SUBSTEPS` supports N=1,2,3,4,6,12; `S60_RATE=5*N`. N=12 is
the source default; the 68000 target explicitly selects N=3. The retained
parameterization-reference N=12 release and VERIFY were byte-identical to their
baseline (SHA-256 `c2a1d0ad93a0f3255155a14950fb2b74a7cced43a52fb8cefca94dbf54a82628`
and `d6f8107c3211089f06b03491e4489f2b292c432c379605ea1d678c449c7cb6f4`).
All six rates compile. Thirteen private native-reference fixture groups
compile at each rate, and all thirteen N=12 variants retain baseline bytes.

Runtime results are retained in
`tmp/substeps-prototype/fixture-runtime-validation.json`. All 78 group/rate
combinations pass against their retained exact builds. All matched-boundary gameplay
captures and their difference-family review are complete. The boss
pitch/acceleration mask 12 denotes bits 2 and 3, not a timestep.
No unexplained first divergence or unclassified difference family remains;
full encounters are not asserted identical across rates.
The input-play group checks the preferences modal, not its later control gesture.
At lower rates it waits one tick of actual field time before modal entry,
so the unchanged checker verifies nonzero pending-credit preservation. All
six rates pass this nested-dialog check; N=12 retains its original fixture bytes.
Full-duration power checks pass at all six rates;
they bracket clone activation, same-value speed-power refresh, and the
200/500/900-unit expiry deadlines. The extended refresh checker passes six
retained N=12 boundaries and the fresh lower-rate runs.
The power runs check 85 captured samples. Six direct jump builds additionally
check all 45 native height boundaries and apex/landing neighbors; all 298
captured samples pass. The 15 existing tooling tests and static native input
inventory pass. Both step-0 matrices still pass the rate-aware report checker.
Cross-N scene builds use trigger 17*N (executed inside the next update),
aligning the count of prior native decisions across rates. All 18 scene/rate
captures are complete: SOL, type-10 and boss at native boundaries 1–16, 50,
125 and 300, yielding 285 comparisons against N=12. This correctness setup is
separate from the baseline performance route. The first gameplay divergence is
at native boundary 1 for every lower N in every scene; no unsampled interval
precedes that first divergence. These routes are not bit-identical across rates.

The first actual SOL tick has identical mapped gameplay at all six rates.
Substep snapshots explain the initial divergence:

| N | SOL type-1 X/Z at boundary 1 | Boss carrier Z at boundary 1 | Type-10 player yaw / yaw velocity at boundary 1 |
|---:|---:|---:|---:|
| 1 | -2048 / 2048 | -28672 | 0 / 0 |
| 2 | -1945 / 2005 | -28672 | 0 / 0 |
| 3 | -1910 / 1990 | -28539 | 9 / 27 |
| 4 | -1893 / 1983 | -28472 | 15 / 40 |
| 6 | -1876 / 1976 | -28406 | 22 / 54 |
| 12 | -1859 / 1969 | -28339 | 30 / 67 |

These are captured values, independently checked against integer formulas:

- The SOL enemy is born on tick 1. Its native movement is (+207, -87), so
  boundary 1 includes only N-1 movement substeps. At tick N+1, after a full
  actor-relative interval, every rate reaches exactly (-1841, 1961).
- The carrier is created by the post-update boss gate on tick 1, admitted to
  the active list on tick 2 and first moved on tick 3. Its native Z step is
  +400; boundary 1 includes max(0,N-2) substeps.
- The type-10 pilot finds no target on tick 1 and a zero distance before
  tick 2. Turning starts on tick 3. Summing the native 80-unit input quanta
  and integrating them with signed remainders gives the yaw/velocity table.
- Star respawn $9bd4 consumes two draws from native RNG $116ec. Its signed
  remainders can produce another out-of-bounds star, so another simulation
  pass retries it. All 80 observed startup intervals replay exactly against
  the guarded native RNG and stationary-star rules. At N=12, retries finish
  on tick 5 before the next generic decision. At lower rates AI calls can
  intervene between retries. All 342 scene-boundary RNG tables and indices
  lie on the same native random stream, within 1813 draws of the common
  first-tick state; no altered generator or unexplained RNG state is observed.

The remaining difference families follow the already different simulated
states. Position, angle and velocity differ through birth/admission timing,
input sampling, curved-path sampling and integer rounding. Native heading,
distance, fresh projection and behavior values are recomputed from those
states. Collision/contact timing and native AI branches then change damage,
shake, kills, score, spawn progress and later actor membership. Once membership
differs, normalized object indices can name different actors, explaining type,
radius, owner/link and world/active-list differences. This is not a claim that
arbitrary encounter branches stay identical across N. The independent curved
boss model passes at every N, with maximum coordinate error 0, 7/8, 8/9,
31/32, 71/72 and 287/288 world units for N=1,2,3,4,6,12 respectively.

Internal records retain tick-valued clocks, last-substep rollback positions,
remainders and cached vectors; they are reported separately and are not expected
to be byte-identical across N. Deferred projection scratch also retains render
history. All 285 comparisons keep equal frame counters, level/session, game
activity/counters, preferences, inactive power state/inventory/selection and
HUD oscillator. No difference family is silently removed from the report.
Full-duration active power and jump checks also pass at every N.

Evidence: `tmp/substeps-prototype/cross-runtime-validation.json`,
`cross-summary.json`, `startup-cross-validation.json`, `startup-n*-replay.json`,
`rng-stream-validation.json`, `birth-boundary-validation.json`,
`carrier-boundary-validation.json` and `input-boundary-validation.json`.
The retained N=1 comparison evidence is above; N=1 is not a playable default.
The HUD installer always copies 48 native instruction bytes. Its twelve-longword
copy count is not a timestep constant. Input/HUD and knockback/shake
runtime groups pass at every supported N.

<!-- rate-matrix-baseline:start -->
## Retained N=12 baseline matrix

This reference uses N=12 (60 Hz). All 48 initial cells are complete and pass
the strict report checker. The additional 24 native combat cells below also pass.
Exact builds, settings and observations are retained under
`tmp/rate-baseline`. The table is regenerated with
`tools/rate_matrix_report.py`; its strict mode rejects missing cells.

| Machine | Route | Updates/s | Presentations/s | Pending growth | Largest observed update-start gap (fields) |
|---|---|---:|---:|---:|---:|
| a500 | sol | 61.224 | 2.517 | -18 | 26 |
| a500 | type10-early | 63.830 | 0.745 | -36 | 14 |
| a500 | type10-late | 64.516 | 0.430 | -63 | 1 |
| a500 | boss | 68.311 | 1.025 | -73 | 36 |
| a500 | native-90 | 4.800 | 5.000 | — | 12 |
| a500 | native-240 | 3.600 | 4.000 | — | 17 |
| a1200-stock | sol | 61.155 | 5.504 | -17 | 11 |
| a1200-stock | type10-early | 60.504 | 3.832 | -5 | 8 |
| a1200-stock | type10-late | 61.433 | 3.345 | -21 | 13 |
| a1200-stock | boss | 61.644 | 2.774 | -16 | 22 |
| a1200-stock | native-90 | 7.800 | 8.000 | — | 8 |
| a1200-stock | native-240 | 5.400 | 6.000 | — | 11 |
| a1200-fast | sol | 60.134 | 8.953 | -2 | 9 |
| a1200-fast | type10-early | 60.201 | 9.231 | -2 | 6 |
| a1200-fast | type10-late | 60.134 | 9.087 | -2 | 6 |
| a1200-fast | boss | 60.606 | 5.859 | -6 | 13 |
| a1200-fast | native-90 | 12.000 | 12.000 | — | 5 |
| a1200-fast | native-240 | 7.800 | 7.912 | — | 10 |
| 030-50 | sol | 60.134 | 18.909 | -2 | 5 |
| 030-50 | type10-early | 59.900 | 22.662 | 1 | 3 |
| 030-50 | type10-late | 59.933 | 22.375 | 1 | 3 |
| 030-50 | boss | 60.403 | 14.396 | -4 | 6 |
| 030-50 | native-90 | 19.800 | 20.000 | — | 3 |
| 030-50 | native-240 | 15.600 | 15.464 | — | 5 |
| 040-25 | sol | 60.067 | 23.626 | -1 | 4 |
| 040-25 | type10-early | 59.900 | 29.052 | 1 | 3 |
| 040-25 | type10-late | 59.933 | 29.101 | 1 | 3 |
| 040-25 | boss | 60.100 | 19.132 | -1 | 4 |
| 040-25 | native-90 | 30.000 | 30.000 | — | 2 |
| 040-25 | native-240 | 18.600 | 18.947 | — | 4 |
| 060-50 | sol | 60.000 | 23.933 | 0 | 4 |
| 060-50 | type10-early | 60.000 | 29.400 | 0 | 3 |
| 060-50 | type10-late | 60.067 | 29.499 | -1 | 3 |
| 060-50 | boss | 59.900 | 19.368 | 1 | 4 |
| 060-50 | native-90 | 30.000 | 30.000 | — | 2 |
| 060-50 | native-240 | 18.600 | 18.947 | — | 4 |
| a500-pal | sol | 61.141 | 2.514 | -17 | 21 |
| a500-pal | type10-early | 64.103 | 0.748 | -38 | 11 |
| a500-pal | type10-late | 62.762 | 0.488 | -40 | 17 |
| a500-pal | boss | 69.124 | 1.037 | -79 | 21 |
| a500-pal | native-90 | 5.000 | 5.000 | — | 10 |
| a500-pal | native-240 | 3.500 | 3.896 | — | 15 |
| 060-50-pal | sol | 60.080 | 25.300 | -1 | 3 |
| 060-50-pal | type10-early | 59.880 | 30.739 | 1 | 2 |
| 060-50-pal | type10-late | 60.000 | 28.600 | 0 | 2 |
| 060-50-pal | boss | 60.120 | 18.938 | -1 | 4 |
| 060-50-pal | native-90 | 25.000 | 25.000 | — | 2 |
| 060-50-pal | native-240 | 20.500 | 20.408 | — | 3 |

SIM60 rates use completed-tick endpoints; native presentations use complete inter-presentation intervals in a 100-field window. Gap values are window-local, not game-wide maxima. Pending growth is not applicable to native timing.

Negative pending growth means the sampled interval repays earlier debt.
Update averages above 60 Hz therefore do not imply a faster game clock or
prove sustained real time across the complete heavy-combat route.
The native frame-90/240 references use SOL, not matching type-10/boss scenes.
The native type-10 and boss setup fixtures pass A500 runtime validation:
151969 original code bytes and 4833 relocations match with no unexpected
changes, setup hooks are removed, and SIM60 has executed zero ticks. The
intended scene and live enemy types are checked. The full 24-cell native
combat matrix is retained under `tmp/rate-native-combat`. These scenes supply
the presentation comparators; their actor trajectories need not equal SIM60
because the native simulation advances only once per rendered frame.

The completed SIM60 cells pass 56 matched-tick comparisons against the NTSC
A500, covering the other CPUs and the completed PAL routes. Mapped gameplay,
HUD and fresh projection state match; only deferred projection scratch from
the preceding draw differs. The retained comparison report is
`tmp/rate-baseline/cross-cpu-validation.json`. These checks establish state
equality at sampled ticks, not sustained throughput.

Cache request: the loader calls SetCPU with value $393d and mask $7f3f:
BaseMem non-cacheable, expansion/slave copyback, instruction cache requested
and data cache off. This request alone does not establish live cache state.
The current diagnostic observations below find instruction caching enabled
on the 68040/060 NOMMU configurations and disabled on 68020/030. Data caching
is disabled in all observed configurations. These readings do not retroactively
measure the register state of the retained baseline runs.

<!-- rate-matrix-native-combat:start -->
### Native combat comparators

All 24 cells pass the strict checker. Frames 150/375 select early/late type-10
combat; frame 292 selects the boss scene. These are original-timing runs,
with the native approach pilot and no active setup hook during measurement.

| Machine | Route | Updates/s | Presentations/s | Pending growth | Largest observed update-start gap (fields) |
|---|---|---:|---:|---:|---:|
| a500 | native-type10-early | 4.200 | 4.444 | — | 14 |
| a500 | native-type10-late | 3.600 | 4.110 | — | 15 |
| a500 | native-boss | 1.800 | 1.818 | — | 35 |
| a1200-stock | native-type10-early | 7.200 | 7.500 | — | 8 |
| a1200-stock | native-type10-late | 7.200 | 7.021 | — | 9 |
| a1200-stock | native-boss | 3.000 | 3.117 | — | 22 |
| a1200-fast | native-type10-early | 9.600 | 10.000 | — | 6 |
| a1200-fast | native-type10-late | 9.000 | 9.545 | — | 8 |
| a1200-fast | native-boss | 6.000 | 5.783 | — | 13 |
| 030-50 | native-type10-early | 19.800 | 20.000 | — | 3 |
| 030-50 | native-type10-late | 18.000 | 18.125 | — | 4 |
| 030-50 | native-boss | 13.800 | 13.548 | — | 6 |
| 040-25 | native-type10-early | 19.800 | 20.000 | — | 3 |
| 040-25 | native-type10-late | 19.800 | 20.000 | — | 3 |
| 040-25 | native-boss | 16.800 | 16.875 | — | 4 |
| 060-50 | native-type10-early | 19.800 | 20.000 | — | 3 |
| 060-50 | native-type10-late | 19.800 | 20.000 | — | 3 |
| 060-50 | native-boss | 16.800 | 17.053 | — | 4 |
| a500-pal | native-type10-early | 4.500 | 4.545 | — | 11 |
| a500-pal | native-type10-late | 4.000 | 4.070 | — | 13 |
| a500-pal | native-boss | 2.000 | 1.852 | — | 29 |
| 060-50-pal | native-type10-early | 25.000 | 25.000 | — | 2 |
| 060-50-pal | native-type10-late | 25.000 | 25.000 | — | 2 |
| 060-50-pal | native-boss | 16.500 | 16.489 | — | 4 |

SIM60 rates use completed-tick endpoints; native presentations use complete inter-presentation intervals in a 100-field window. Gap values are window-local, not game-wide maxima. Pending growth is not applicable to native timing.
<!-- rate-matrix-native-combat:end -->

<!-- rate-matrix-baseline:end -->

## Supplied version

The installed pack contains English Stellar 7, labelled NTSC, with Psygore's
1.0 slave (2 January 2008). Both archives contain an identical 3980-byte slave.
The installer contains no source. The `s7` executable is 186796 bytes.

Slave SHA-256: `b241c2656184ba17a6e5bfad3c335379b1e677c1df23731ceec296fc2aeef91d`.
Game SHA-256: `2360196317fc1d2a507c987834e9308f7368110194523c34b9376d606b606eb0`.

## Loader

The shipped slave requires WHDLoad 16, 512 KB base and 768 KB expansion RAM
(the latter includes the 256 KB Kickstart image). Its flags are NoError,
EmulPriv, ClearMem and Examine. It uses Kickstart 34.005, CRC $f9e3, and
current directory `data`. Keypad asterisk ($5d) quits. No CUSTOM options exist.

This is an OS game. The slave boots KickEmu 1.3, reads/decrunches `s7`, accepts
CRC16 $b9ea or $fcc4, frees the temporary file buffer, and LoadSegs `s7`.
It passes a newline argument and calls the loaded program. It applies no
patches to the game's hunks. Its patch list at slave:$60 instead adapts the
Kickstart image and filesystem. The game-specific loader is slave:$eb4–$f64.
It explicitly calls SetCPU with value $393d and mask $7f3f; the current
fast-CPU investigation separately records actual CACR state.

## Executable

| Hunk | Kind | File offset | File-backed bytes | Allocated bytes |
|---|---|---|---|---|
| 0 | Code | $24 | $25360 | $25360 |
| 1 | Data/BSS | $29f2c | $3558 | $823c |

Hunk 0 has 4833 relocation entries; hunk 1 has 323. Startup sets A4 to
hunk 1 + $8000. The code contains Aztec C `link a5` prologues and handwritten
assembly. Loaded-hunk identification must reject WHDLoad's PRELOAD file copy
and validate A4 against the next LoadSeg segment.

## Gameplay capture

The VERIFY-only CUSTOM5 fixture selects Escape through the intro's native
input paths and Begin through the main menu. It does not alter simulation,
RNG or rendering. Guarded hook ranges are hunk 0 $4582–$4587, $b1f4–$b1f9 and
$b8c4–$b8c9. Each replaces a four-byte PC-relative call plus its following
two-byte instruction. The normal build contains none of these fixture hooks.
The original pack's idle menu enters the briefing display; that is not the
real-gameplay route used here.

The anchor is hunk 0 $2c16 at gameplay counter hunk 1:$1e96 = 90, level SOL,
no player movement or firing. The call reaches the buffer-swap routine at
$1c84c; the gameplay counter increments at $2d4e and resets at $a0b6.
The three markers occurred equally often in the exploratory gameplay trace.
Independent read-only breakpoint captures reproduce the complete 50-field
swap pattern exactly on both CPUs.

Two fresh A500-equivalent runs have identical whole data-hunk snapshots at
the anchor, identical screenshots in all 50 fields, and identical PC/cycle
streams in all 50 fields. Raw traces are **not** fully identical: some saved
register values and DMA data values differ. The first observed register
difference is in Kickstart code; no claim of full machine-state identity is
made. Both captures have the same frame pattern and cycle/DMA totals.

## Measurements

Current frame-90 window, 50 PAL fields, reconstructed development slave,
CUSTOM5 enabled; no performance changes. Capture directories are local only.

| Machine | Fields/frame | fps | STOP | Interrupt-context cycles |
|---|---:|---:|---:|---:|
| A500-equivalent: 68000, 512 KB chip + 1536 KB slow | 10.00 | 5.0 | 0% | 21.4% |
| A1200: 68EC020, 2 MB chip + 4 MB fast | 4.40 | 11.4 | 0% | 20.4% |

The A500 window contains five swaps, with four complete inter-swap intervals;
the 68020 window contains eleven swaps, with ten complete intervals.
It is a stationary early-game scene, not a representative benchmark suite.
The earlier arbitrary gameplay capture measured 3.1 fps: do not compare those
scenes as an A/B result.

A500 self-cycle shares: $1bc94 7.01%, $1d51c 5.51%, $17c02 4.74%,
$14a9e 3.83%, $16c52 3.63%, $17cea 3.39%, $14d1e 2.32%.
$16c52 performs fixed-point vertex transforms; $17c02 caches transformed
vertices; $17cea performs perspective divisions. $1d51c is in the blitter
rendering path. These names are from static inspection, not source symbols.
The high interrupt share includes 1844 blitter-finished interrupts and 50
vertical blanks (1894 level-3 entries total) in 50 fields.

DMA slots: free 28.7%, refresh 1.8%, CPU 38.7%, copper 1.6%, audio 0.6%,
blitter 6.1%, bitplanes 22.5%. The native blitter-wait routine $1db8c–$1dbb1
accounts for 38180 / 7105050 cycles (0.54%); this excludes OS blitter waits.
The $2b96–$2bb3 tick wait and 750-iteration delay cost 220620 cycles (3.11%).
Do not confuse either figure with total renderer or total blitter overhead.

## Game time: mapped behavior

Hunk 1 offsets:

| Offset | Meaning |
|---|---|
| $1e96 (word) | Gameplay loop counter; also used by some non-gameplay paths |
| $24a8 (long) | Timer callback counter |
| $2434, $2436 (words) | RNG indices |
| $2438–$24a7 | 56-word additive RNG table |
| $43c0 (pointer) | Player object; x/z at +8/+12, heading at +$18, speed at +$40 |
| $46a0 (word) | Current level (0 = SOL) |
| $46c4 (word) | Player energy/shield value |
| $6870 (word) | Timer scale; observed 234 |
| $2946 (word) | Countdown used by intro, menu and swap waits |

The callback at hunk 0:$11748 increments $24a8; it ran exactly 50 times in
50 PAL fields. Setup at $8ca4 passes 13 to $1a6e4, which stores 13*18 = 234
in $6870. $1bab0 schedules callbacks with rounded `period*60/scale`, clamped
to at least one VBL; $1c6e8 dispatches them and decrements $2946 by
`scale/58` (4 at this setting). The sound driver separately installs CIA-B
timer interrupts through cia.resource at $25f0–$2666.

The gameplay loop waits for $24a8 to differ from its saved value at $2b96,
then runs a fixed 750-iteration delay. At the swap it records the current tick.
Several simulation counters decrement **once per gameplay iteration**: the
power timer at $3dc4 and object timers at $2cf2/$2d2c are examples. Enemy
spawning tests the gameplay counter modulo 16/64 at $2c96/$2cb2. Therefore at
least these behaviors are frame-coupled. The tick wait provides a ceiling,
not a fixed-rate simulation. A faster renderer can change game speed.

Over the same 50 PAL fields, the A500 executes five gameplay counter increments
and the 68020 eleven; both execute fifty timer callbacks. At frame 90, both
have identical mapped player state, energy (680), RNG state and timer scale,
but the timer counters are 3786 and 1628 respectively (including boot).
This confirms frame-coupled counters; it is not a complete motion-rate study.

The fixed-step implementation below adds a moving/firing route and controlled
render-cost variation. Full state coverage and PAL/NTSC validation remain open.

## Opt-in fixed-step simulation

The chosen design is simulation timing independent of rendering. `CUSTOM1=1`
installs guarded hooks; `CUSTOM2` chooses 1–25 updates/second (default 5).
The default reflects the measured early A500 scene, not an established universal
original cadence. The standard mode remains unchanged when CUSTOM1 is absent.

The main-task entry at $2af6 accumulates elapsed native callback ticks multiplied
by the chosen frequency. It consumes one field-rate unit per simulation pass
(50 or 60 from Exec `VBlankFrequency`), retaining fractional credit. The fixed
750-iteration delay and previous-frame tick wait at $2b96–$2bb3 are replaced.
This is a cooperative scheduler, not interrupt-context simulation. If the
simulation itself exceeds the CPU budget, debt can grow; it is not silently
converted into larger physics steps or discarded.

When another complete step is already owed, mesh rasterization at $132b2 and
presentation at $6a0a are omitted. Native projection and visibility work in
$12aa4 remains: gameplay uses that data. The starfield at $9a2a also remains
once per simulation pass, including its calls to the shared RNG via $9bd4.
Some HUD/background work is still performed on catch-up passes. Additional
interpolated pictures are not implemented; presentation can be less frequent
than simulation, but does not exceed the configured simulation frequency.

The native Permit path at $313e resets clock credit following modal input.
A restarted/reset gameplay counter reanchors the scheduler. These paths need
explicit pause/death/transition playtesting before enabling the mode by default.

Hook ranges (whole displaced instructions): $2af6–$2afb, $2b96–$2bb3,
$2c16–$2c21, $313e–$3143, $132b2–$132b9. CRC checks precede opcode/displacement
guards; relocated absolute operands are not compared to file addresses.
VERIFY input hooks cover $22730–$22735 and $22746–$2274d. The native joystick
mask and key-status APIs consume the scripted input normally.

The timing entry includes a read-only debugger signature, `S7TM`. Its counters
are decoded by `tools/timing_state.py`. The mapped-state comparator ignores the
unused third word of each six-byte star record: allocation is uncleared, while
$9bd4 initializes only x/y and $9a2a reads only those two words.

### Moving/firing timing validation

Snapshots at steps 115, 140 and 160 match mapped state for the original game
loop (timing disabled), fixed A500 and fixed 68020 with a 20-field drawing
delay. All use the same native-input fixture. At step 115 there are eight
world/active objects plus player and clone; the later route turns, fires and
returns to rest. A second 68020 test presenting every other step also matches
at 115. These are mapped-state checks, not full machine-state equivalence.

| Mode | Completed updates / 100 PAL fields | Presentation fps |
|---|---:|---:|
| Fixed A500, moving/firing | 10 | 5.0 |
| Fixed 68020, independent breakpoint count | 10 | 5.0 |
| Fixed 68020, every second presentation | 10 | 2.5 |
| Fixed 68020, 20 extra fields per drawn frame | 9 | 1.9 |

The slow run has bursty catch-up. Checkpoints 115 to 160 span 452 clock fields
for 45 simulation starts (4.98 Hz); residual credit is retained. The invariant
`last_field * simulation_hz - step * field_hz - credit` is unchanged at all
three checkpoints. A short completion-count window can differ by a step while
one slow draw is in flight. No renderer speedup is claimed.

## Replacement behavior and retained N=12 validation

The numerical captures in this section use N=12 unless explicitly stated
otherwise. Current parameterized formulas use N; lower-rate acceptance and
performance results are recorded in the active sections above.

The `SIM60` build has its own update/draw loop and debugger ABI. It is still
experimental; remaining requirements are listed in `docs/open-work.md`.
At completed tick 1500, moving/firing captures with normal rendering and
20 extra fields per render match mapped gameplay state, including fractional
motion records and star remainders. Their render counts are 150 and 37.
The slow window completes 72 ticks over 60 PAL fields, with one presentation;
there is no complete inter-presentation interval for an FPS estimate.
The genuine NTSC replacement run also matches the PAL state at tick 1500,
including fractional records, after 146 renders. Its observed clock is 60 Hz,
and its captured gameplay view was inspected.

The original 68000 NTSC reference window at native frame 90 completes five
updates over 60 NTSC fields. Four inter-swap intervals span 48 fields:
12 fields/frame, 5.0 fps. Exec reports 60 Hz. A separate two-field scan capture
records approximately 119665 CPU cycles per field, versus 142102 in PAL.
This confirms the selected video mode. Four further 100-field stationary
opening-level windows show that native cadence varies: frames 90/120 have
12-field intervals (5.00 updates/s), frame 180 has 18–19-field intervals
(3.30 updates/s), and frame 240 has 14–17-field intervals (4.00 updates/s).
Rates here use complete update intervals, avoiding partial-window rounding.
World counts are 6/6/6/7 and energy is 680/680/600/600 at the anchors.
The retained native loop instructions are unchanged and Exec reports 60 Hz;
see `tmp/native-pace-expanded-validation.json`. The twelve-substep conversion
holds the early-scene 5 Hz reference pace even where native rendering slowed
gameplay. This is not scene-by-scene historical wall-clock equivalence, nor a
comparison against the original 2008 loader.

Use the emulator core option `uae_ntsc=true`. The earlier frontend option
`ntsc_mode=1` left this build in PAL; its nominal 60 Hz-derived reports are
invalid. GLib queue warnings occur even during successful captures.

### Collision separation versus rollback

The native loop $3740–$377a doubles the player's bounce velocity, supplies ten
when stopped, and calls $87ea repeatedly until $85f6 finds no overlap. This is
spatial separation, not reversal of one timed movement step. Reusing the last
fractional displacement here can loop forever when that displacement is zero,
and changes the native correction endpoint even when nonzero.

The replacement recognizes return offset $3768 (guarded caller at $3764),
restores the pre-movement linear remainders and delegates that correction to
native $87ea. Other rollback calls still subtract the exact applied XYZ step
and restore their prior remainders. A bounded VERIFY fixture compares the real
separation fragment against native undo using four isolated actor pairs:

| Input speed | Native/corrected iterations | Final z | Bounce speed |
|---|---:|---:|---:|
| 0 | 3 | -30 | -10 |
| 1 | 11 | -22 | -2 |
| -1 | 11 | 22 | 2 |
| 12 | 1 | -24 | -24 |

All pass on the 68000 and a 68020 with twenty fields of added rendering delay,
including ordinary fractional rollback checks. Mapped gameplay state matches
at ticks 201, 600 and 1500, despite 12 versus 43 renders by the last boundary. The
pre-fix reproduction hits the diagnostic watchdog after 64 unsuccessful tries
for the first three; the fourth takes 21 corrections and ends at z=-21.
The watchdog and synthetic actors are absent outside VERIFY. They are not a
runtime collision workaround. Broader contact damage/response tests remain.

### Special enemy integration

The AI table at hunk 1:$21b0 maps behavior 4 to callback $f328. The replacement
recognizes that callback at the existing dispatch hook and separates its motion
from its decision interval. Type-13 climb/fall, type-47/48 descent and type-47
extra charge movement run every physics tick. Steering, counter changes,
animation, transformations and random heading selection run once per twelve
active callback ticks. Native type-13 mutual-contact deletion remains delegated
to the original function.

These non-projectile actors reuse motion-record word 4 for interval phase
(bit 15 marks extra charge), word 6 for the signed vertical increment and word
62 for its fractional remainder. The extra charge calls the same scaled motion
routine as ordinary movement; its return marker is explicitly recognized.
Descent retains the native endpoint even when a fifty-unit interval crosses
zero. Type-13 motion retains the native ground/1000-unit clamps.

A twelve-case oracle on both the 68000 and a 68020 with twenty fields of added
rendering delay compares four native callbacks against 48 physics ticks per case: exact intermediate XYZ and full actor/RNG state at each twelfth
tick. Cases include type-13 climb, clamps, fall and player contact; type-47
charge, expiry and steering; and type-48 animation and transformation. The
reference calls the untouched native callback with fractional integration off.
The ordinary SOL route matches pre-change state at ticks 201 and 1500 and
matches across those CPU/render configurations at ticks 201, 600 and 1500. The
last captures have 11 versus 43 renders and outstanding clock debt, not a proof
of sustained rate. That route alone does not exercise special enemies or bosses.

### Boss movement and callback audit

AI callback $10904 sends type 7 to $11498; other types use seven level-indexed
entries at hunk 1:$2408. The table ends at $2424, where projectile height words
begin. The adapter in `boss60.s` calls these native handlers once per twelve active
callback ticks, then integrates audited direct increments at 60 Hz. Ordinary
motion through $8682 is independently integrated at 60 Hz.

| Native level index | Handler | Motion and distinct side effects |
|---|---|---|
| 0 | $10bf8 | Steering/banking; temporary Y collision tests; contact and firing |
| 1 | $10e60 | Steering/banking; type-44/45 changes and creation of type-46 actors |
| 2 | $10a22 | Y descent/ascent by 100, altitude clamp, banking, firing/spawning |
| 3 | $10d2a | Steering/banking; temporary Y collision tests; contact and firing |
| 4 | $1093a | Direct sideways motion through $110be; far-target yaw assignment; banking/firing |
| 5 | $113c0 | Steering/banking; random target at hunk 1:$473c; type-46 spawning |
| 6 | $10f66 | Steering/banking and timed firing; player-position copy to the aim target |
| Type 7, any level | $11498 | Entry/exit sequence, speed decay, beam countdown, boss creation, pitch/acceleration |

Shared $11136 sets angular velocity at actor offset $38, which the existing
motion integrator already scales. The adapter captures and distributes its separate bank increment at $111a2;
scaling the angular velocity again would be wrong. Level-2
Y writes at $10aec/$10b8c are continuous descent/ascent, while $10a7e assigns an
altitude of 2100 as a state-dependent clamp. Sideways helper $110be writes real
X/Z movement at $110f6/$11120/$1112a, with its own native trigonometric rounding.

The Y writes at $10c3c/$10d6e temporarily put the boss at a projectile's height
for collision testing. Restores at $10c6c/$10d9a must remain in that same native
call, not be distributed across ticks. Their restore sign-extends the saved low
word, so blindly treating all net Y changes as real motion is also unsafe for
out-of-range heights. Spawn copies at $11230–$1124c, $11346–$11374 and $11488–$1148c
initialize other actors. The full placement calls returning at $11262/$1138e
are deliberately absent from `s60_is_motion` and must retain full displacement.

Type-7 state 1 subtracts five from forward speed at $114f8. Its exit state adds
144 to pitch at $115ac and fifty to speed at $115b2. Pitch is distributed over N ticks, including signed-word wraparound.
Speed now advances by signed fractions of -5 or +50 per tick. Discrete speed
assignments in the other handlers remain immediate. The beam transition at $1157a
calls $93fc, which creates the actual type-44 boss and stores it at hunk 1:$1e48;
it is not removal of the type-7 actor. Entry/exit counters and creation/removal
must remain discrete events when motion is split.

The adapter records the pre-call state to select continuous axes: Y only for
level-2 states 1/2, X/Z only for level 4, and pitch only for type-7 state 4.
Bank is captured for every boss callback. Native state-0 altitude clamps and
far-target heading assignments take effect immediately. Each selected increment
is removed after the native call and distributed with signed remainders. A native
removal invalidates the record and stops integration. Native code remains intact;
the existing AI dispatch hook selects this adapter by callback address $10904.

ABI version 14 uses 144-byte records. Boss phase/Y/bank reuse offsets 4, 6/62,
and 64/66; words 92/94 contain X/Z increments, 96/98 their remainders, and
100/102 the pitch increment/remainder. Words 104/106/108 hold acceleration,
interval-start speed and speed remainder. Words 110/112 hold the substep coefficient
and temporary saved speed; 114 is reserved. Words 116/118/120 hold X/Z/Y vector
remainders, and 122/124/126 preserve them for collision rollback.
All resets/removals clear the full stride.
The VERIFY result offset is published at entry+88. Its 34 callback cases compare
four native calls with 48 substeps each, including full actor/RNG state, the
animation byte, random-heading word and copied aim-target XYZ at native boundaries.
Allocation returns null only during this fixture and is restored with a cache
flush. Full encounter geometry, projectile spawning, actor creation/removal and
temporary-Y collision queries are outside this isolated oracle's coverage.

The gameplay path moves active actors in $352e before calling their AI through
$4154/$ee08. For interval-start speed V, acceleration A and substep k=1..12,
published speed after AI is V + trunc(A*k/12). Movement computes native axis
increments D(V) and D(V+A) at the current substep orientation, then integrates
[2*N*D(V) + (2*k-N-1)*(D(V+A)-D(V))]/(2*N*N) with signed per-axis remainders.
The N correction coefficients sum to zero. At fixed orientation, the
interval therefore travels exactly D(V), including native trig rounding and
signed speed wraparound. The second native call applies no additional rotation;
both speed and angular velocities are restored afterward. Constant-speed type-7
movement needs only one native call. Collision rollback restores vector remainders.

Rounding a corrected scalar speed before native projection was insufficient:
the six added diagonal cases exposed two native-boundary position mismatches
in the retained B763 probe. The vector formula passes those cases. Eighteen
coupled move-before-AI cases now cover straight, diagonal and pitched directions,
stopping, zero crossing, reverse motion and signed speed wraparound. Each checks
speed on 48 substeps and complete native actor/position bytes at four boundaries.
A rollback/replay check verifies identical first-step displacement and restored
vector remainder. The 34 callback cases check boss height, bank,
pitch, decisions and per-tick entry/exit speed. B766 adds starting speeds
32717, 32718, 32742 and 32763 in type-7 exit state, including pitch wrapping.
All 52 cases pass on the 68000 and delayed-render 68020 in
`sim60-boss-overflow-a500/020`; mapped gameplay/projection state matches at
1500/3600 through native retry and matches the preceding terrain baseline.
These four additions validate every speed substep and full callback state at
native boundaries, without movement calls. Positive speed-word overflow in
coupled movement and curved exit trajectory pace require a different position
oracle from fixed-direction native endpoint agreement; BP60 provides the
specified continuous-path check described below.
B767 additionally passes eight coupled curved-exit sequences on both CPUs,
checking all 384 ticks for speed/pitch publication, spatial rollback, retained
rotation and full actor/record replay. Its overflow starts match the four
callback-only boundary speeds. The replay fixture restores angular inputs itself,
because native collision rollback retains the completed turn; spatial fractions
must be restored by the actual wrapper. An injected X rollback error fails all
eight new cases. Gameplay/HUD/fresh projection at tick 150 matches the preceding
build and across CPUs, and all 87 hooks pass. These consistency checks do not
establish curved position accuracy, full encounters or creation/removal.
See `tmp/boss-exit-spatial-validation.json`.

The optional BP60 recording retains every XYZ position from those eight exit
cases. `tools/boss_path_state.py` independently reconstructs native projection
from the original cosine table, including both arithmetic shifts, and derives
pitch/yaw from the state-4 increments. At each substep's orientation it projects
interval speeds V and wrapped V+50, then integrates a linear velocity function
of legacy-interval phase with exact rational arithmetic. Centering phase at 1/2
preserves the native move-before-AI distance for fixed orientation; current
angles are held within each substep. The host does not use the adapter's integer
remainders. All 1152 coordinates on each CPU remain strictly within one native
position unit of the continuous integral; maximum error is 287/288. This tests
the stated continuous interpolation, not exact equality to coarse native curved
positions, which use different orientation samples.

`sim60-boss-path-{a500,020}` also retain passing B767 checks and all 87 installed
hooks, with matching gameplay/HUD/fresh projection before/after instrumentation
and across CPUs. A model without the acceleration term fails 890 coordinates;
a two-unit corruption of the first X sample fails exactly that coordinate.
See `tmp/boss-path-validation.json`. Full encounter state transitions and broader
original-reference pace evidence remain separate requirements.

Boss projectile damage $111ac is reached through $41ba from $32a2 and remains
an immediate projectile impact. Boss contact $112cc is instead reached from
$3c96 via $3cb8 during the per-tick collision loop. The latter is independently
rate-limited as described below; it cannot inherit the slower AI cadence merely
because it lives in the boss code region.

### Contact-effect audit

The player-energy routine $3cc2 is not a signed heal/damage interface. It skips
all changes while hunk 1:$1e90 is nonzero. For a negative argument it adds four
times that negative value to energy, bypassing the shield test. For a positive
argument it subtracts four times the value unless the shield timer is active.
Thus the -25 calls at $373a and $382a each deal 100 energy damage; neither heals.
Both also invoke sound and set the flash timer at hunk 1:$026a to eight.

| Call site | Effect | Lifetime/cadence classification |
|---|---|---|
| $333a | Projectile damage from a type-indexed table, scaled by four | Projectile lifetime cleared at $330e, then removed; immediate impact |
| $36d6 | 200 energy damage from types 14–16 | Actor removed at $36c8; immediate impact |
| $372a | 20 energy damage from type 48 | Actor removed at $370e; immediate impact |
| $373a | 100 energy damage from type 4 before player separation | Repeated contact; independent N-tick clock |
| $382a | 100 energy damage from type 4 in the active-actor pass | Repeated contact; separate N-tick clock |
| $3874 | 128 energy damage from types 13/47 | Actor removed at $384e; immediate impact |
| $32ba | One/five actor-health damage from player projectile | Projectile lifetime cleared at $32f6; immediate impact |
| $35a8 | Five/fifteen actor-health damage from shield ramming | Repeated contact; independent N-tick clock |
| $38b2 | Ten actor-health damage when touching type 43 | Repeated contact; independent N-tick clock |
| $3902 | Damage equal to the actor's remaining health | Level-1 type-13/47 contact with type 47; destruction event |
| $3cb8 → $112cc | Level-zero actor-health damage and player energy damage on boss contact | Independent N-tick contact clock |

Actor-health damage is handled by $3f04, including death/removal, animations and
sounds. The five contact call-site wrappers now gate each actor/path independently: the first
contact applies immediately, then another effect is allowed after N ticks.
Unsigned elapsed subtraction tolerates tick wraparound; validity bits distinguish
an unused clock from a hit at tick zero. Suppressed actor-health calls return
zero, preventing spurious kill score. Movement, overlap checks, separation and
one-shot impacts still run every physics tick.

Each hook replaces the four-byte call plus its two-byte argument cleanup;
wrappers preserve the native arguments, result and stack balance. The shield
sound at $3590 previews the same clock without consuming the subsequent damage
call. Inside-call sound, flash and hit animation run only with their damage.
Contact clocks occupy five last-effect tick longs at
68/72/76/80/84 and validity bits at byte 88. Normal removal/reset clears them.
The boss-contact wrapper at $3cb8 retains the original four-byte actor argument
and cleanup, calling $112cc only when due. No direct branches into the six
replaced six-byte interiors were found.

The boss helpers also call these routines through tail stubs $116c6/$116cc.
Their caller sites include $10c58, $10c98, $10d1e, $10d86, $10dc6, $10e40,
$10fa0, $111ee, $11202, $112f6 and $1130c. These remain part of the boss audit;
main-loop contact changes must not silently alter their existing decision cadence.
Direct AI calls and projectile-impact helpers remain unmodified. The independent
collision callback is gated at $3cb8, before entering $112cc, so its combined
native effects stay together. A fixture on the 68000 and delayed-rendering 68020 checks four native effects against 48 substeps
per path (240 effect checks), including exact energy/health endpoints, negative
damage with a shield, independent paths/actors and tick wraparound. A sound
preview test checks call scheduling and stack cleanup. Fixture sound/animation
bodies are temporarily suppressed; lethal actor damage and full contact geometry
are not covered by this isolated oracle. Mapped gameplay matches at ticks 201,
600 and 1500 with 15 versus 43 renders. The enlarged records also pass collision,
special-enemy and flying oracles on the 68020. Both captures retain the original
six-byte sequences at all six audited immediate-impact sites. This does not
establish sustained 60 Hz performance or full encounter behavior.

Actual healing occurs in $3d2a: it restores energy to 680 during the type-31
pickup sequence. Its thirty-event countdown is kept at 5 Hz while rise and
yaw now integrate at 60 Hz as described below.

### Pickup rise and rotation

The simulation calls the pickup integrator every tick. A selected pickup gets
twelve ticks per native event, independently of the global legacy phase. It
samples native Y/yaw increments and distributes their integer remainders over
the first eleven substeps. At the twelfth tick it reverses only those applied
components, then calls the untouched $3d2a: the native full increment completes
the interval exactly once, retaining healing, counter and acceleration changes.
Other position changes during the interval are retained. The thirtieth interval
has no motion, matching the native removal branch; removal occurs at tick 360
from the start of an uninterrupted sequence, not at the start of that interval.

The dedicated sixteen-byte state holds the selected actor, remaining ticks,
Y/yaw increments and two signed remainders. A changed selection or inactive
pickup resets this integration state; native shared pickup counters are left
to the original routine. ABI version 8 exposes the state at offsets 82/84.
A four-case native oracle on both the 68000 and delayed-rendering 68020 checks
504 substeps and 42 complete actor/global boundaries. These include the full
360-tick normal sequence, signed increments, angle wrapping, healing deadlines
and the final removal interval. Mapped gameplay matches at ticks 201, 600 and
1500 (14 versus 43 renders); the ordinary route also matches the pre-pickup build
with the new integration state verified zero. This is not a sustained-rate test.
The isolated oracle stubs the fake actor's removal, inventory presentation and
audio helpers. Separate PE61 controlled-encounter coverage keeps those helpers
native: type-31 contact acquisition occurs at tick 837, all thirty callbacks
run at 849 through 1197, healing restores energy to 680, inventory rises from
one to three, and native removal unlinks the actor. Completed ticks 1198/1318
have no actor in world/active lists, no motion record and zero private pickup
state. All 65 mapped checkpoints match across normal 68020, A500 and delayed
68020, except deferred projection scratch. All 87 installed hooks pass.
PE61 explicitly supplies allocation, placement, initial energy and inventory;
selection remains unchanged. Separate A500 and normal 68020 runs without
native-event breakpoints match all mapped state exactly at completed ticks
200/201/1198/1318, including deferred projection scratch; all 87 hooks pass
(`tmp/pickup-plain-validation.json`). A separate input-only PICKUP_USE
sequence now exercises native second-button release selection and simultaneous
button activation. Completed tick 1402 selects index zero; tick 1403 has
inventory byte -2 (two remaining charges, active) and timer 900/phase 11.
Completed ticks 1414/1426 have timers 899/898 and phase 12. Ten snapshots
through 1500 match across all three configurations, allowing only deferred
projection scratch, and all 87 hooks pass. Selection, consumption, timer and
phase corruptions are rejected (`tmp/pickup-use-cross-validation.json`,
`tmp/pickup-use-negative-validation.json`). The extended route also verifies
native clone activation at completed tick 1882, 480 simulation ticks after
use. Timer 860 triggers active word 1 and the native mesh pointer switches
from data $4498 to $4598; tick 1881 remains inactive. All fourteen checkpoints
through 2000 match across all three configurations, allowing only deferred
projection scratch, and all 87 hooks pass. Early/missing activation, unchanged
mesh and incorrect timer controls are rejected
(`tmp/pickup-clone-cross-validation.json`,
`tmp/pickup-clone-negative-validation.json`). Other selections, active cycling,
depletion, natural spawning and audible/visible output remain outside
this encounter check. A separate expiry capture reaches completed tick 12202
on normal 68020, A500 and delayed 68020: timer 1→0, clone word 1→0, mesh
$4598→$4498 and inventory -2→2, with selection zero retained. All seven
checkpoints through 12203 match gameplay/HUD/fresh projection, allowing only
projection scratch, and all 87 hooks pass. This is 10800 simulation ticks after
activation; phase stays 12 once the timer expires. Five corrupt-copy controls
are rejected (`tmp/pickup-expiry-cross-validation.json`,
`tmp/pickup-expiry-negative-validation.json`). See
`tmp/pickup-encounter-cross-validation.json`; eight corrupt-copy controls
are rejected by the raw-snapshot checker.

### Player knockback

Native $2b0c–$2b32 assigns the pending impulse at hunk 1:$026c to player speed,
then halves it. Applying this only on the global legacy phase let per-tick
input alter speed during the following eleven ticks. The replacement applies
that speed override throughout its twelve-tick interval, while the normal
movement integrator advances position each tick. Native halving is preserved,
including its signed-word wrap at -32768; after the last nonzero impulse,
normal quantized input resumes. This preserves discrete native decay intervals,
not a newly fitted exponential drag curve.

The whole eight-byte collision store at $378c is replaced with a setter that
also restarts the interval, including same-value impacts. Its return is $3794;
no direct branch into the replaced interior was found. The simulation calls
$3d2a separately at its original decision cadence, then applies knockback and
enters the native movement/collision path at $2b38 every tick. Loop entry resets
the six-byte phase record: ticks remaining, applied speed and published pending
impulse. ABI version 6 exposes it at offsets 74/76.

Eight isolated cases pass on both the 68000 and a delayed-rendering 68020:
384 substeps and 32 native speed/impulse boundaries per CPU, covering positive,
negative, zero and signed-extreme impulses with input in both directions. The
same-value impact test restarts a fresh twelve-tick interval. Angular velocity
is unchanged by the isolated update. The existing four collision-separation
cases also pass on both CPUs. Ordinary gameplay matches at ticks 201, 600 and 1500. A separate -160 impulse
injected through the setter before tick 1206 matches mapped gameplay at all
seven boundaries through tick 1500 across CPUs/render costs. Speed remains
-160 through 1217, -80 through 1229, then reaches its final -1 interval through
1301 before input resumes at 1302. Final render counts are 13 versus 43; this
is not a sustained-rate measurement. The real-route injection bypasses impact
geometry, covered separately by the native collision fragment oracle.

### Flying-AI random fallback

Callback $f192 initializes local -1(A5) only in state 1 but reads it in state 3
at $f29e. A native fixture with identical actor inputs and stack bytes 0/255
produces decisions 5/3, proving a dependency on stack residue. The guarded
six-byte hook replaces whole instructions through $f2a3, returning to the native
comparison at $f2a4. During simulation it draws one byte from native RNG $116ec;
outside simulation it replays the original load. The unsigned threshold stays 2.

The VERIFY oracle restores identical RNG before each corrected call, tests both
stack bytes, and checks exactly one draw. The 68000 fixture gives 3/3; a 68020
fixture seeded for a low byte gives 5/5. Both restore the original gameplay RNG,
and mapped gameplay matches across their different render costs at ticks 201
and 1500. This deliberately defines previously undefined behavior: it changes
later RNG sequences and some enemy decisions compared with pre-correction runs.
Its height and bank increments are integrated separately, as described below.

### Flying-enemy integration

The $f192 dispatcher executes native decisions once per twelve active calls.
It captures the native Y increment from $f232/$f2e6 and bank increment from
$f31c, restores their starting values, and distributes both over twelve physics
ticks with signed integer remainders. Native steering, timers and projectile
creation still execute only once per interval. Decisions start immediately on
an actor's first callback; they no longer share the global legacy phase.

Flying actors use
word 4 for interval phase, word 6 for height increment, word 62 for its remainder,
and words 64/66 for bank increment/remainder. Other integration fields retain
their offsets. The stride is published at ABI offset 70, and all record clearing
uses that stride. Current ABI version 14 records are 144 bytes for 272 actor slots.

A twelve-case oracle on the 68000 and a delayed-rendering 68020 compares four
direct native callbacks with 48 physics ticks per case. It checks all XYZ/bank substeps and complete actor/RNG bytes at
each twelfth tick, including signed bank extremes, descent across the state
threshold, climb clamping, countdowns, steering, random decisions and contact
retreat. The reference uses the corrected random fallback too. Projectile
allocation and full encounter behavior require real gameplay coverage. Mapped
movement/firing-route state matches at ticks 201, 600 and 1500 across the CPUs
and render costs (14 versus 43 renders at tick 1500). The enlarged records also
pass the special-enemy and collision oracles on the 68020. Outstanding clock
debt is six versus sixteen ticks; this is not a sustained-rate measurement.

### Individual power phases

Each power counter has a two-word record: remaining ticks to its next decrement
and the last native counter value. Setters at $3e3e, $ec6a, $ec8e, $eca4 and $ecc0
reset that phase to N, including same-value refreshes. The corresponding
decrements at $3dcc, $ecd2, $ed38, $ed6c and $ed86 execute only when due. Native
expiry, blink, visibility and sound paths remain in place; inactive timer blocks
are skipped. Other initialization is detected by a changed counter value.

The native $3dc4/$ecca passes now run every tick, while their countdown units
remain 5 Hz for existing readers. The former native jump block is bypassed by
the separate continuous integrator. A shortened two-unit diagnostic verifies
expiry exactly 24 ticks after activation and identical mapped state with normal
versus delayed rendering. A native-duration 68000 test refreshes speed power five
ticks after activation while its word is still 200; it first decrements twelve
ticks after that refresh, at completed tick 1222. ABI version 4 exposes the five
timer phase records.

Full-duration 68020 captures with normal and twenty-field-delayed rendering
match at all seven boundaries through tick 12005. Activation at 1205 gives
expiry at 3605, 7205 and 12005 for 200-, 500- and 900-unit timers; clone activation
starts after 480 ticks and clears at expiry. The 10799 completed ticks span
10801/10798 native VBL fields, approximately 59.989/60.006 Hz. Scheduler credit
is conserved; boundary debt explains the small difference. Rendering counts
advance 110 to 2034 versus 34 to 353. The fixture sets the native damage-suppression
flag and bypasses acquisition, so it does not validate ordinary survival or
death. These retained captures precede the flying-AI RNG correction; they prove
the timer and elapsed-clock behavior of that build, not full-game equivalence.

### Jump, modal and sorting checks

The continuous jump retains an integer velocity scaled by N and a position
remainder modulo N². For a native launch velocity of 220, the reference curve
is `y(k) = (225*N*k - 5*k*k)/(N*N)`, with integer remainder accumulation. It passes
through the native 5 Hz samples and lands after 45*N ticks. Jump integration runs
before collision/projection. Retained N=12 normal and 20-field-delayed rendering match at
12, 24, 270 and 540 ticks after activation, including cooldown and RNG state.

The replacement wraps actual modal entry points $df32 (dialogs) and $d3a8
(preferences), not every Permit call. Entry accounts for active elapsed time;
return reanchors the field clock while retaining pre-pause credit. A modal-depth
flag makes the outermost wrapper own the excluded interval, so nested dialogs
cannot charge paused fields. ABI version 18 exposes that flag at entry+106.
The earlier wrapper cleared credit and therefore discarded existing simulation
debt. The delayed-rendering pause test exposed this: its clock origin shifted
by 97 fields for a 60-field pause, silently losing 37 owed ticks. The corrected
wrapper shifts the origin by only 60 fields. The private preferences fixture also checks the real nested-dialog return and
retention of nonzero pending credit; current rate coverage is listed above.

The pointer-walk sorter's `SORT_INLINE_DISTANCE=1` path evaluates the same
wrapped arithmetic directly using D0/D1/D2, the current actor and the view
position. Its outer save already preserves D2; ordering/fallback reinitializes
scratch A0 before use. Argument pushes, S60_CALL and the distance callee's
register saves are removed. Signed subtraction/absolute-value overflow, the
three-times-minimum shift and final addition remain identical. Selection,
zero/nonpositive fallback and the level-1 type-46 override are unchanged.
This adds 20 allocated code bytes, no persistent state and no patch site.
Explicit-off is byte-identical to the preceding SIM60 release.

Both CPUs pass 64 O761 cases and 214 native-order comparisons through tick 150.
The bit-8 key corruption control stops at the mismatch handler at tick 100,
after 32 synthetic cases and 132 successful comparisons. Positive captures
match gameplay/HUD/fresh projection at 150/4500/5400, across CPUs and against
the preceding build, apart from deferred projection scratch. All 87 hooks and
six level resets pass. Complete sort means fall 6380.91→4033.50 cycles on A500
and 3436.02→2060.07 on delayed 68020; update means improve 2.45%/2.70%.
The matched long A500 route improves 58.25→58.38 updates/s, presents 56→62
frames and grows pending updates by 144→133. It still misses sustained 60 Hz.
See `tmp/sort-inline-{twin,negative,cross,long}-validation.json` and
`tmp/sort-inline-profile-{a500,020}-validation.json`. The negative diagnostic is
byte-excluded without VERIFY; it does not change normal release arithmetic.

The extended default-build type-10 route (`sort-inline-extended-{a500,slow-020}`)
now matches all eight gameplay/HUD/fresh-projection snapshots through native
player death at tick 9212, allowing only deferred projection scratch. Energy
is still zero and gameplay active at tick 9000; the death snapshot has energy
−80, active zero and death one. All six requested transitions and 87 hooks pass.
No health/damage/death injection is used after level selection. The requested
10800 checkpoint explicitly records its earlier actual stop at 9212.
Across 600–9212, A500 averages 59.5917 updates/s (8671 fields, 98 presentations,
pending 23→82), while delayed 68020 averages 60.1047 (8597 fields, 270
presentations, pending 25→10). A500 recovers 74 pending ticks after 5400;
this does not cancel the preceding heavy-window throughput failure. The
repeated A500 state and clocks through 5400 exactly match the shorter capture.
See `tmp/sort-inline-extended-validation.json`.
Separate `sort-inline-death-{a500,slow-020}` hundred-field traces anchored at
9200 confirm the complete native death-entry sequence at completed tick 9212.
Negative energy, active clear, death marking, final update, SIM60 exit, input
restoration, native cleanup and the native death branch occur in that order,
without any later SIM60 update/render in the trace. A500 spans recorded fields
11–12; delayed 68020 spans 2–3. Both anchor states match except deferred
projection scratch. Six resets and 87 hooks pass; normal builds are restored.
Guarded D0 values after the level fixture's tick load identify 9200–9211 on
A500 and 9201–9211 on 68020, followed by their completed-tick boundaries.
The field trace need not start at the snapshot's tick boundary; counting only
observed update entries undercounts a partially recorded first update.
`tmp/sort-inline-death-validation.json` records these direct observations.
The Continue answer and retry for this specific level-6 death are untested.

Depth sorting at $43de recomputes the same $4388 view distance during every
selection scan. The replacement caches each distance once and swaps the cache
along with the pointer list. It preserves the level-1 type-46 override, strict
greater-than comparisons and the original retained selection index when only
zero distances remain. An all-nonpositive list falls back to the native routine
because its first selection depends on incoming D5. A VERIFY twin has compared
every actual call through tick 1745 on the fast 68020. This does not establish
all-level/edge-case coverage or sustained 60 Hz performance on the 68000.
The 68000 twin also completes through tick 1222 with native-duration powers.
A ten-NTSC-field profile anchored at tick 300 measures about 6127 cycles per
completed cached sort, versus 13992 in the pre-cache profile of the same scene.
This is a 56% reduction in that routine's measured cost. The new window completes
13 catch-up ticks with no presentation; it does not establish sustained-rate FPS.
Projection now accounts for 27.5% of recorded cycles and remains a substantial
simulation cost. Mapped state at ticks 300 and 600 matches the older build,
excluding only the newly added, verified-zero power phase records.

## Original Kickstart patch list

The following entries are decoded from the shipped slave list at slave:$60.
Targets are offsets in the Kickstart image; replacement destinations are
slave-code offsets. There are no original game-hunk patches.

| Kick offset | Command | Argument |
|---|---|---|
| $000d2 | PL_S | 0x2c |
| $00106 | PL_L | 02390002 |
| $00132 | PL_CW | — |
| $0025a | PL_CW | — |
| $00286 | PL_PS | slave:01ca |
| $00422 | PL_PS | slave:021c |
| $004f4 | PL_L | ffffffff |
| $0050c | PL_S | 0x8 |
| $00546 | PL_P | slave:01d4 |
| $00592 | PL_P | slave:01c2 |
| $005f0 | PL_P | slave:0058 |
| $0061a | PL_P | slave:01a4 |
| $00ebc | PL_P | slave:01de |
| $01354 | PL_P | slave:01ea |
| $014b6 | PL_PS | slave:020c |
| $015b2 | PL_PS | slave:01f4 |
| $04964 | PL_S | 0x14 |
| $04adc | PL_P | slave:02a8 |
| $04cce | PL_S | 0x4 |
| $06d70 | PL_PS | slave:0226 |
| $06d86 | PL_PS | slave:023e |
| $06efe | PL_L | 08390005 |
| $06f02 | PL_L | 00dff01f |
| $0ad5e | PL_PS | slave:0266 |
| $0ad7a | PL_S | 0x6 |
| $0aecc | PL_S | 0x18 |
| $0af96 | PL_P | slave:0248 |
| $0b00c | PL_P | slave:024c |
| $0d5be | PL_PS | slave:0284 |
| $1b96c | PL_B | 0008 |
| $1b9d2 | PL_C | 0006 |
| $1b9da | PL_C | 0008 |
| $1b9d8 | PL_W | 0001 |
| $25290 | PL_PS | slave:02b2 |
| $253a2 | PL_PS | slave:030e |
| $28452 | PL_PS | slave:04c6 |
| $28f88 | PL_P | slave:033e |
| $2960c | PL_P | slave:0444 |
| $29cfa | PL_P | slave:036a |
| $2a0e2 | PL_P | slave:0406 |
| $2a3b4 | PL_P | slave:036a |
| $2a6d6 | PL_PS | slave:0412 |
| $33ef0 | PL_PS | slave:046c |
| $3568c | PL_PS | slave:0476 |
| $36e4c | PL_PS | slave:048c |
| $38748 | PL_PS | slave:04b6 |
| $3c9b6 | PL_PS | slave:0482 |


### Animation and explosion activation clocks

The native mesh callback $42b0 reloads/decrements actor byte $57 from $56 and
advances the byte array at actor $1e, wrapping each component by its model frame
count. The explosion callback $397e advances byte $55, draws its prior index,
and removes the actor when it reaches byte $58. Both callbacks previously used
the shared legacy phase in SIM60, shifting newly activated effects by up to eleven
ticks. They now use separate per-actor clocks in `animation60.s`: the first
simulation callback runs immediately and another is eligible after twelve elapsed
ticks. Duplicate callbacks in the same tick do not advance either effect.

The complete eight-byte LEA/store pairs at $4334 (mesh initialization) and $3a46
(explosion creation) are guarded and replaced with initializer wrappers. Each
replays the native callback assignment and clears that clock's validity, including
when the same callback is assigned again. No branch enters either replaced pair.
Outside a running simulation the wrappers simply replay the native assignments.
Rendering still draws the current explosion frame without advancing its lifetime;
mesh-animation updates remain suppressed during rendering. This does not change
the native active-object selection or introduce catch-up for off-screen effects.

ABI version 13 adds explosion/mesh last-tick longs at record 128/132 and validity
bits 0/1 in byte 136 (140-byte stride). Actor removal and loop reset clear these
with the rest of the record. VERIFY animation results are exposed at entry+90.
The fixture uses real type-11 animation (one eight-frame component) and type-41
animation (five- and two-frame components), plus progressing and expiring explosions.
It compares complete actor/animation-array bytes at every substep with four native
update intervals, also invoking duplicate simulation and extra render callbacks. It checks
same-callback refresh, two staggered actors and a tick-counter wrap. Temporary
returns isolate the initializer hooks and fake-actor removal; all words are restored
with a cache flush. Real unlinking, visible sprites and full encounters still need
coverage beyond these isolated timing checks.

The separate $394c oscillator cycles actor byte $56 through the 0..3 endpoints
using signed direction byte $59. Callers $3936/$3940 pass actors from hunk 1:$1e40/
$1e44. It now uses clock index 2, with last-tick long at record 140 and validity
bit 2 at 136 (ABI 14, 144-byte stride). Null actors return before record lookup;
rendering and duplicate calls do not advance the frame.

The complete twelve-byte MOVE.B pair at $92b6 initializes direction 1 and frame 2.
Its guarded wrapper resets only the oscillator clock, then replays both stores.
No branch enters the replaced instructions. The creation routine $922e can reuse
an existing actor after allocation failure, so resetting at the actual initializer
also handles reuse. Its placement call returning at $9308 remains outside the
fractional-motion whitelist, preserving full native separation strides.

A762 adds four native-reference oscillator cases to the animation fixture: normal
cycling, both endpoints and signed-byte extremes. A refresh check restarts the same
actor before its twelve ticks expire and verifies the mesh clock is untouched.
The fixture also calls the null-actor path. Native frame/direction transitions are
compared on every substep against the original body beginning at $3952.

The remaining shared-phase sites are generic AI dispatch and explicitly
periodic post-update work. Damage shake has a per-impact clock; death and
pending quit requests are checked every tick, as described below.

The generic AI table at data+$21b0 dispatches $eec4 and $f136, alongside the
separately adapted flying, special and boss callbacks. Retain the shared
five-Hz decision boundary for the generic callbacks: $eec4 selects states,
assigns speed/turn rates and advances decision counters; $f136 dispatches
steering/range/firing behavior for types 8–10. Continuous actor movement is
already integrated through $8682 each simulation tick. The firing helper
$f5e0 decrements cooldown byte 97 only when its caller reaches it, and weapon
slot counters only after alignment passes. Converting these to unconditional
elapsed-time countdowns would change behavior. Position and angle writes in
$f646 and the type-10 helper $f814 place/orient newly spawned projectiles;
they are discrete creation effects, not continuous parent movement.
Independent generic-actor decision phases could reorder shared RNG draws.
This is a reason to retain native decision ordering, not proof that all
spawn/target transitions are equivalent to the original game.

`tools/ai_dispatch.py` checks the loaded callback table, verifies the supplied
listing's sibling binary against the retained slave, and observes the actual
scheduler clear/set instructions. It compares ordered generic callback offers
and executions for each fully recorded update and checks twelve-update spacing
between decision boundaries. It does not infer the first traced tick from the
saved snapshot: profiling begins at a video-field boundary and can omit updates
between snapshot and trace. Partial edge updates are excluded.

The retained `sim60-record-cache-fast-a500` and `sim60-record-cache-fast-020`
traces pass: 29/64 complete updates offer 58/128 calls to $eec4 for two actors;
4/10 execute at the observed decision boundaries in offered actor order.
The latter capture adds twenty fields per rendering operation. Flying callback
$f192 is also observed, but its internal cadence is outside this check.
Neither capture offers $f136. In-memory negative controls that remove, duplicate,
change the actor of, or insert an extra generic call are rejected. Results are
in each capture's `ai-dispatch.json`, with negative-control results in the
68000 capture. This establishes dispatch behavior for these windows, not full
AI state/firing/spawn equivalence. The following level-1 captures extend
coverage to type 8; types 9/10 remain unobserved.

The level-1 `sim60-level-profile-a500` trace (LEVEL_TEST=200, SLOW_DRAW=20,
anchor tick 1500, sixty fields) extends dispatch coverage to $f136. Its 64
complete updates offer 192 calls for three type-8 enemies; 15 execute at
indices 11/23/35/47/59 in actor order. Five calls reach the cooldown helper,
but this window has no spawn attempt. Special callback $f328 is also offered
128 times; its internal timing is outside this generic check. Exact build
listing and sibling binary are `tmp/level-profile.{lst,slave}`.

Complete updates average 96849.75 cycles (64 calls), and the sixty-field
window contains 65 completions while catching up, with zero presentations.
Interrupt-context work consumes about 12% of recorded cycles. Complete
movement calls average 3017.24 cycles (520), collision scans 1889.45 (390),
projection 10591.02 (65), star updates 6926.68 (65), sorting 5647.48 (65),
and heading 548.09 (585). These inclusive costs overlap and must not be
summed as exclusive work. The full results are `complete-costs.json` in the
capture. This trace identifies remaining cost; it does not establish sustained
sixty-Hz gameplay or acceptable presentation latency.

The later `sim60-level-fire-a500` and `sim60-level-fire-020` captures use the
same retained build, both with twenty added fields per render, anchored at
tick 3700 with sixty-field traces and a checkpoint at 4200. A500/68020 offer
225/195 generic callbacks across 75/65 complete updates; 18/15 type-8 calls
execute for three enemies, at six/five decision boundaries twelve updates
apart. Cooldown helper calls number 12/10. Both traces include one successful
native $f646 projectile creation: the owner write at $f6ec names the executing
enemy and the returned projectile at $f630 is the same object. Partial edge
updates are excluded. Mapped gameplay plus projection matches at 3700 and
4200 across CPUs; native level-reset validation also passes. Different numbers
of complete updates reflect catch-up and differing trace windows, not a changed
simulation frequency.

`tools/ai_dispatch.py` now reports these type/cooldown/spawn observations after
checking the native instruction bytes. In-memory controls with a wrong owner,
omitted owner write or altered successful return are rejected. The prior
$eec4 traces still pass with unchanged cadence counts. Results are each
capture's `ai-dispatch.json`, the 68020 `ai-firing-negative-controls.json`,
and `tmp/level-firing-summary.json`. This validates one type-8 firing opportunity
and surrounding mapped gameplay, not all firing states, failed allocations,
type-9/10 behavior or a full original-game trajectory comparison.

Terrain damage is specifically the type-46 player-contact branch on level 5,
not a generic ground-height timer. Type is checked at $36de and level at $36ec;
$36f8 subtracts one directly from the energy word, then branches to $37a6. It
does not call $3cc2, so damage-helper shield/scaling behavior must not be added.
The earlier shared-phase wrapper delayed first contact by 0–11 simulation ticks;
`terrain-cadence-audit.json` records that static audit, not a live encounter.

The independent player clock now applies first contact immediately, then spaces
eligible effects at least twelve active simulation ticks apart using unsigned
elapsed subtraction. It belongs to the player rather than each terrain object:
alternating adjacent objects must not multiply the damage rate. Rendering cannot
consume the clock; inactive calls retain the native decrement and leave private
state untouched. Signed-word energy wrapping is retained. Session reset clears
the eight-byte valid/padding/last-tick state through s60_events_reset. ABI 25
exposes it at +120/+122; mapped state includes it and the native retry fixture
checks all eight bytes are zero.

TERRAIN_TEST copies the original six-byte decrement before installation, adding
RTS for its reference. It calls the installed game hook after temporarily making
its following unconditional branch return. TR60 compares 96 cases (twelve phases,
four energy words, normal/wrapping ticks), each with 36 substeps. Rendering calls
must preserve both energy and clock, alternating actor pointers must share one
clock, and duplicate calls must not add damage. Eight intermittent contacts,
four inactive-mode checks and 96 resets extend coverage. The copied instruction
must target native energy, and the following branch must be restored afterward.
The fixture saves/restores energy, tick/phase/mode and private clock state, runs
once per boot and is absent outside VERIFY. It does not test level-5 geometry
or a full encounter.

`sim60-terrain-final-a500` and `sim60-terrain-final-020` pass 96 cases and
3456 substeps per CPU with zero errors, including all additional checks. The
68020 adds twenty fields per render. Combining TERRAIN_TEST with DEATH_TEST
seeds a valid terrain clock at tick 200 before lethal energy injection completes;
the first captured boundary retains valid=1/last=200. Native death/Continue/retry
clears this populated clock on both CPUs. Subsequent mapped gameplay/projection
state matches at 1500/3600 across CPUs/render costs and the preceding route,
with the new state verified zero on resumed SOL. The earlier `terrain-clock-*`
captures verify the same fixture but do not seed the clock before retry. The
normal legacy build is restored, and final fixture/retry diagnostics are
byte-excluded without VERIFY. No performance claim is made from state-only
captures. A real level-5 contact/transition encounter remains unverified.

Retained A761 captures `sim60-animation-final-a500` and `sim60-animation-slow020`
pass all four cases, refresh and independence checks, and match mapped gameplay
at ticks 201/600/1500 (14/41 renders at the final boundary). The delayed run also
passes the existing boss, collision, special, flying, contact and pickup oracles
with 140-byte records. These correctness captures retain clock debt and do not
prove sustained simulation or rendering performance.

Retained A762 captures `sim60-oscillator-a500` and `sim60-oscillator-slow020` pass
all eight effect cases, refresh and independent-clock checks. Their mapped state
matches at ticks 201/600/1500 (13/41 renders), and all seven combined diagnostic
families pass in the delayed run. The normal build excludes these diagnostics.


### Damage-shake impact clock

Native $40ae decrements hunk 1:$026a, computes offsets $7156/$7158 while the
counter remains nonzero, then calls the display update at $4226. Its helper $4110
uses a separate one-byte RNG at hunk 1:$3558: next = (5*seed+1) modulo 256,
then a remainder by the requested bound. It does not consume the main gameplay
RNG at $2434. The new snapshot fields include this byte and both shake offsets;
the previous main-RNG hash alone did not cover it.

The complete eight-byte damage writes at $3ce6/$3d14 are guarded and replaced
with setters that replay counter 8 and clear the shake clock, even for the same
value. `s60_shake_update` runs each simulation tick: first sampling is immediate,
then native $40ae runs only after twelve ticks. A full eight-unit effect samples
at activation and every twelve ticks through +84, when native counter zero clears
the offsets. Duplicate calls and rendering do not consume additional random draws.
Externally changed counters start a fresh sample; zero clears the private clock.
The native $40ae body remains unchanged, including direct reset/menu calls that
write counter 1 and immediately clear the offsets without drawing random numbers.

ABI version 15 exposes the eight-byte shake state at entry+92/+94: last tick.l,
last counter.w, valid.w. Loop entry resets it. VERIFY results are at entry+96.
The native oracle compares counter, separate RNG, offsets and all 116 main-RNG
bytes on 384 substeps against eight native intervals per case. Cases use counters
8/8/2/1 and different byte seeds, including tick wraparound. Actual patched impact
sites test same-value clock refresh. The actual menu fragment $c57a tests immediate
reset while the private clock is pending. Temporary returns isolate these fragments
and suppress the display write; they are restored with a cache flush. These tests
cover timing/state, not on-screen shake or complete menu transitions. The contact
fixture also saves/restores shake phase now that its native damage effects reset it.

Retained captures `sim60-shake-a500` and `sim60-shake-slow020` pass all four
cases, impact refresh and menu reset checks. Mapped gameplay, including shake
phase/seed/offsets, matches at ticks 201/600/1500 (13/41 renders). Contact, animation
and all 48 boss cases pass in the delayed run. Both impact JSR/NOP hooks and all
four temporary-return restoration sites pass byte checks. SHAKE_TEST produces
byte-identical output when VERIFY is absent; the normal build is restored.
Outstanding clock credit means these captures do not establish sustained rate.

### Per-tick post-update events

The $2c58 block checks a pending **Quit to DOS** request ($1eb5), not level
completion: $4184 jumps to $101b0, whose dialog string is at data $233e. Its
native first-update guard at -6(a5) suppresses one call before being cleared.
Actual level exits clear $1e53 in collision code at $3610 or final-boss handling
at $3ff4; the scheduler already checks that flag before another simulation tick.

The post-update block now runs every tick. A guarded eight-byte hook at $2c96
replays MOVEQ/AND with their native flags on legacy-phase ticks, and otherwise
skips to the untouched signed-energy death check at $2cce. That check marks
negative energy as dead; zero remains alive. The cooldown dispatcher at $2ce6
returns directly on intervening ticks, leaving the native frame counter unchanged.
On legacy ticks it still reaches $2d4e. Enemy/boss spawn calls at $3c14/$9346 and
warning sound $9986 therefore retain the original frame masks 15/63. Outside
an active SIM60 loop the periodic and cooldown hooks retain their native paths.

ABI version 16 adds POST_TEST results at entry+98. Its native-fragment fixture
checks four signed-energy values across all twelve phases (48 cases), pending
quit dispatch with both first-update guard states (24 cases), and 64 native
periodic calls against 768 fractional calls across frame-counter wraparound.
Periodic callback counts, warning flag, energy, death/active flags and frame
counter are compared each substep. Temporary native-entry stubs count spawning,
warning sound and quit requests; these do not test the real dialog or transitions.
Real Forbid/Permit helpers are used for the request dispatch.

Retained `sim60-post-a500` and `sim60-post-slow020` captures pass all 48 death
cases, 24 quit cases and 768 periodic substeps on each CPU. Both match mapped
state at ticks 201/600/1500 (12/41 renders at the final boundary); the 68000 also
matches the preceding shake build at all three boundaries. The comparator now
includes the active-game flag at $1e53. Shake, contact, animation and all 48 boss
cases pass in the delayed run. The periodic hook, preserved branch and four
restored temporary entries pass byte checks on both CPUs; disassembly has no
static branch into the hook interior. POST_TEST is byte-excluded without VERIFY,
and the normal build is restored. These isolated tests do not establish full
death/level transitions or sustained performance; delayed-render credit remains.


### Native level-exit and loading lifecycle

ABI 28 adds the VERIFY-only LEVEL_TEST result offset at entry+130. Its W760
fixture requests exit by clearing data $1e53 when the pre-completion tick
counter is 200. The scheduler exits after completed tick 201 through native $2d7c; cleanup and
resource loading increment the level at $2e80 and reenter the patched loop.
The fixture does not change the level index or run reset routines itself.
A populated terrain-contact clock checks that private state is actually cleared.

`sim60-level-a500`, `sim60-level-slow-a500` and `sim60-level-slow-020`
advance level 0 to level 1 and session 1 to session 2, with zero fixture errors.
Delayed runs add twenty fields per render. Entry clears all 272 motion records plus stars,
jump, cooldown, powers, knockback, pickup, shake and terrain private state;
ticks, renders, phase and death flag are zero, energy is 680, and credit is
one update (60 units). Exit/reanchored-clock fields are 3016/6295 on A500,
3032/6312 on delayed A500 and 1349/2941 on 68020; loading time does not
become gameplay debt.
Mapped gameplay and projection match at resumed ticks 600, 1500 and 3600
across all three runs, including same-CPU differing render costs. Results are
retained in each capture's `level-validation.json` and
`tmp/level-validation-summary.json`.
Over resumed ticks 600–3600, normal A500, delayed A500 and delayed 68020
consume 3014/3053/2999 fields: 59.72/58.96/60.02 updates/s. They present
65/23/101 times, with pending ticks 21→35, 64→117 and 13→12. Delayed A500
accumulates 53 ticks of backlog over this interval; state equivalence does not
prove sustained throughput in the new scene.
The fixture is byte-excluded without VERIFY (`tmp/level-nonverify-{0,1}.slave`).
This validates one requested native transition, not the boss-kill/collision
trigger, mid-update exit, later transitions or the ending.

At tick 3600 a type-30 actor retains a collision link to inactive type-13
pool slot 4 at data $43f8. The comparator now resolves references through
native pool tables $43d8 (8), $43f8 (16), $4438 (16), and $4478 (8), allocated
by $8e58. Removal at $9492 drops world membership without freeing those
allocations. This preserves reference identity across memory layouts rather
than accepting raw-address differences. Null, another pool slot and unknown
address negative controls all report mismatches. Full inactive-pool contents
are not added to mapped-state coverage; their stale projection fields may
still differ with rendering.


### Chained native level transitions

LEVEL_LAST (default 1, range 1–6) extends LEVEL_TEST without modifying the
native level index. Each nonfinal session requests exit at completed tick 201;
normal cleanup/loading advances the level. W761 retains the W760 sixty-byte
result prefix, adds completed/target words at +60/+62, then stores six complete
sixty-byte result records at +64. Each resume checks all private reset regions
before saving its record; errors accumulate across the chain. The ABI result
pointer remains entry+130. LEVEL_TEST rejects simultaneous DEATH_TEST.
`tools/level_state.py` accepts both signatures and verifies every archived
transition, consecutive level/session numbers and the final target.

`sim60-level5-a500`, `sim60-level5-slow-a500` and `sim60-level5-slow-020`
reach level index 5/session 6 through five requested native transitions, with
zero errors at every reset. Delayed runs add twenty fields per render. Mapped gameplay plus projection
matches at final-session ticks 600/1500/3600, including natural energy changes
600/600/264 and the later enemy/projectile population. No natural death occurs
in those captures. The terrain contact clock remains zero at these samples;
this route does not exercise the level-5 type-46 contact branch. A separate
controlled level-5 boss-state setup now reaches native allocation and 25
consecutive contacts on A500, normal 68020 and delayed 68020. Allocation is
observed at $11472/$11476 and contacts at $36f8/$36fe. Damage occurs at ticks
3604/3616/3628 after the explicit state selection at 3600; raw energy and clock
checks plus mapped gameplay comparisons pass. See
`tmp/terrain-contact-cross-validation.json`. The random decision to select
that boss state is outside this controlled check.
The chain tests requested transitions, not their natural boss/collision
triggers, mid-update exit or the game ending.

For final-session ticks 600–3600:

| Configuration | Fields | Updates/s | Presentations | Pending ticks, start/end |
|---|---:|---:|---:|---:|
| A500, normal rendering | 2910 | 61.8557 | 72 | 117 / 27 |
| A500, twenty added fields/render | 2911 | 61.8344 | 18 | 184 / 95 |
| 68020, twenty added fields/render | 3006 | 59.8802 | 103 | 21 / 27 |

The rates above sixty are catch-up, not a changed timestep. This extends
render-independence evidence to the same CPU across markedly different
presentation counts and includes all five earlier reset records. It does not
bound peak debt or maximum presentation/input delay. Results are retained in
`level-chain-validation.json` per capture and `tmp/level5-summary.json`.

The delayed 68020 sixty-field trace at tick 600 has 51 complete updates.
It offers 51 $eec4 and 51 $f136 generic callbacks and executes eight, in actor
order at four boundaries twelve updates apart. Four observed type-9 decisions
reach the native cooldown helper; none attempts a new projectile in this
window. Another 204 offers go to $f328, outside this generic cadence audit.
Successful type-9 firing is covered by the approach route below; failed
allocation remains open. Type-10 firing and later-state coverage is described
below.
The input-only APPROACH_TYPE=9 route observes native return $f630 and the
channel-loop exit $f640 at ticks 2052/3396, firing channels 1/0 respectively.
The native allocator produces type-22 projectiles with owner, copied horizontal
position/yaw, +225 launch height and lifetime 500 preserved. Actor cooldown is
28; the fired channel is initialized to 84, and later nonzero channels decrement
as native code specifies. Normal 68020, A500 and twenty-field-delayed 68020
match both events and all six gameplay/HUD/fresh-projection checkpoints through
3600, allowing only deferred projection scratch. All five level-reset records
and 87 installed hooks pass. Four corrupt-copy controls are rejected; see
`tmp/type9-native-cross-validation.json` and
`tmp/type9-native-negative-validation.json`. Failed allocation, firing variant
5 and unseen routes are outside this check. The normal-68020 initial state
also matches the observer-free approach pilot at tick 1800.

Exact listing/binary: `tmp/level5-slow.{lst,slave}`. Non-VERIFY builds with and
without chain flags are byte-identical (`tmp/level-chain-nonverify-{0,1}.slave`).


### Final-level render-independence and timing

`sim60-level6-a500`, `sim60-level6-slow-a500` and
`sim60-level6-slow-020` use LEVEL_TEST=200, LEVEL_LAST=6 and current defaults
including MOVE_IDLE=1. All six requested native transitions pass W761 reset
checks. Mapped gameplay and fresh projection agree across all three at
final-session ticks 600/1500/3600; energy is 680/680/600, with no death or
session change. These captures reach level index 6/session 7; they do not
exercise a natural boss kill or the ending.

For final-session ticks 600–3600 (3000 updates):

| Configuration | Fields | Updates/s | Presentations | Pending ticks, start/end |
|---|---:|---:|---:|---:|
| A500, normal rendering | 3011 | 59.7808 | 47 | 29 / 40 |
| A500, twenty added fields/render | 3094 | 58.1771 | 18 | 81 / 175 |
| 68020, twenty added fields/render | 3007 | 59.8603 | 101 | 15 / 22 |

The delayed A500 preserves state but adds 94 pending updates in this interval.
The longer run below distinguishes this initial increase from its later recovery.
Results are in
`level6-validation.json` per capture and `tmp/level6-summary.json`. Exact
listings/binaries are `tmp/level6-{a500,slow-a500,slow-020}.{lst,slave}`.

Both hundred-field instruction traces pass ordered generic AI dispatch checks.
A500 has 100 complete updates, 300 generic offers and 24 calls; delayed 68020
has 94 complete updates, 282 offers and 24 calls. Each observes eight type-10
state-0 decisions, twelve updates apart, with no projectile attempt. The
extended audit checks native type-10 spawn returns at $f86e/$f8e4/$f912
against observed owner writes, but these branches are not exercised here.
The prior type-8 firing capture still passes; missing/wrong owner writes and
wrong returned projectile negative controls are rejected.

Complete-call mean update cost is 71006.36 cycles on A500 (100 samples) and
37793 on 68020 (94). A500 has three complete renders spanning 10/10/9 fields;
its largest observed update-start gap is ten fields (150–183 ms). Delayed
68020 has three three-field renders, with a 24-field update-start gap
(383–417 ms), including the artificial delay outside the render routine.
These windows do not establish whole-game maximum latency. Per-capture
`ai-dispatch.json`, `latency-costs.json` and `latency.json` retain the details.


`sim60-level6-slow-a500-long` extends the same delayed A500 build with
state-only checkpoints at 600/3600/7200/10800. The retained slave matches
`tmp/level6-slow-a500.slave` exactly; gameplay/projection at 600 and 3600
matches the earlier run. All six resets pass at every checkpoint, with no
session change. `tmp/validate_level6_long.py` writes `long-validation.json`.

| Tick interval | Fields | Updates/s | Presentations | Pending ticks, start/end |
|---|---:|---:|---:|---:|
| 600–3600 | 3094 | 58.1771 | 18 | 81 / 175 |
| 3600–7200 | 3621 | 59.6520 | 18 | 175 / 196 |
| 7200–10800 | 3562 | 60.6401 | 16 | 196 / 158 |
| 600–10800 | 10277 | 59.5505 | 52 | 81 / 158 |

The last interval recovers 38 updates; this run therefore does not demonstrate
continuously growing backlog. It also does not establish a tight bound: the
final debt is 158 updates (about 2.63 seconds), and the sparse checkpoints do
not bound the maximum. Later states at 7200/10800 still need comparison with
normal rendering and another CPU. Average presentation rate is only 0.304 Hz
with the artificial twenty-field delay. These results do not establish
acceptable input responsiveness or complete the performance goal.


### Input-only type-10 combat route

`sim60-type10-approach-pilot` uses SIM60, LEVEL_TEST=200, LEVEL_LAST=6 and
APPROACH_TYPE=10 on the 68020 configuration, with normal rendering. The
VERIFY/CUSTOM3 route changes only native joystick/key API return values;
player firing is disabled. All six requested native resets pass. The retained
slave matches `tmp/type10-approach.{lst,slave}` exactly.

At tick 600 the type-10 enemy is 25348 units away, outside its native 24576
firing range. By tick 1200 the route has reached distance 17999 and stops
accelerating. At tick 1800 the enemy is in native state 3 and three active
type-18 projectiles reference it as owner. Energy is 680 at 600/1200/1800 and
600 at 2400; these snapshots alone do not identify which enemy caused damage.
The route reaches live projectile creation, but snapshot ownership does not
replace the instruction-level owner/return audit. Results are retained in
`approach-validation.json`; the route and capture driver are documented in
development and `tmp/type10_combat_runs.py`.

`sim60-type10-combat-a500` and `sim60-type10-combat-slow-020` capture 100
instruction-trace fields from tick 1200, then state at 1800/2400. The latter
adds twenty fields per render. Both match the pilot's mapped gameplay and
projection at all three boundaries, including the three owned projectiles at
1800 and energy 600 at 2400. Every archived level reset passes.

A500 has 97 complete updates, 291 generic offers and 24 calls; delayed 68020
has 115 complete updates, 345 offers and 27 calls. Native decisions retain
ordered twelve-tick spacing. Both observe exactly one successful type-10 spawn
through $f86e, with its actual owner write and returned pointer verified.
A500 observes six state-0 and two state-1 decisions; 68020 observes six and
three. These short trace windows do not cover $f8e4/$f912.
Separate read-only native-return captures through tick 5400 now cover all three
sites: `sim60-type10-native-{observer,a500,slow-020}` records ten successful
type-18 shots (five at $f86e, three at $f8e4, two at $f912). The two $f912
shots change yaw 30720→6144. Full actor and projectile bytes match native
state/counter/yaw consequences, including owner and decision gate. All 22
mapped gameplay/HUD/fresh projection snapshots agree across configurations,
allowing only deferred projection scratch; all six resets and 87 hooks pass.
Observer-free A500 endpoints match. No failed allocations or nonpositive-yaw
$f912 cases occurred. These captures use requested level transitions and an
input-only approach, without enemy-state or allocation injection. Results are
in `tmp/type10-native-cross-validation.json`; corrupted owner/yaw/counter/gate
and omitted-branch controls are rejected by `tools/type10_firing_state.py`.
The A500 direct-return negative controls reject a wrong owner, missing owner
write and wrong returned pointer (`tmp/type10-direct-negative-controls.json`).

| Tick interval 1200–2400 | Fields | Updates/s | Presentations | Pending ticks, start/end |
|---|---:|---:|---:|---:|
| A500, normal rendering | 1373 | 52.4399 | 7 | 76 / 249 |
| 68020, twenty added fields/render | 1197 | 60.1504 | 35 | 27 / 24 |

The A500 gains 173 pending updates during combat, despite matching state. This
is a concrete performance failure over the measured interval; rendering
independence alone does not meet the full goal. The delayed 68020 catches up
three updates in the same simulated interval. Exact listings/binaries are
`tmp/type10-combat-{a500,slow-020}.{lst,slave}`. `tmp/validate_type10_combat.py`
writes `combat-validation.json` and `ai-dispatch.json` per capture plus
`tmp/type10-combat-summary.json`.


### Normal SIM60 patch-boundary inventory

`tools/audit_hooks.py` checks the exact compiled listing/slave pair against the
original executable. The default SIM60 build has 87 patch commands in 67 merged
ranges. All end on complete native instructions: the RTS entries at $2b96,
$2c50 and $2d54 now pad their original instruction tails with NOPs.
The conservative scan checks 9440 possible direct branch encodings at aligned
words, plus 663 relocated code pointers, with no potential interior entries.
It rejects the previous partial-instruction build and injected BRA, DBcc,
PC-relative JSR and relocated-pointer interior targets.

`tmp/boss-gate-release.{lst,slave}` and `tmp/boss-gate-release-audit.json`
retain the non-VERIFY audit.
`tmp/prof/sim60-boss-gate-{a500,slow-020}/boss-gate.json` additionally checks
all 87 installed patches and their exact jump destinations. Gameplay, HUD and
fresh actor projection match the preceding build at ticks 201/600/1500 on both
CPUs; deferred shared projection scratch is reported separately. The normal
legacy build remains 4986 code bytes and the SIM60 release is 16502 code bytes.
Computed indirect destinations and replacement semantics are outside this
static scan; it is not a whole-program control-flow proof. The disabled-option
code-preservation check is documented separately.


### Simulation-owned boss eligibility

Native radar drawing sets data $1efc at $c052 and clears it at $c07e if any
active actor has class byte $54 equal to $ff. Boss-carrier creation at $9348
reads this flag. Leaving its calculation in rendering makes boss arrival depend
on drawing cadence after the last enemy disappears. SIM60 now NOPs those two
complete writes and calculates the same predicate every update before the
native post-update block. It runs before ordinary periodic spawning, retaining
the original ordering between the predicate, normal enemy creation and the
boss check. Health and visibility are not part of the native predicate.

BOSS_GATE_TEST copies the guarded native $c074..$c083 predicate before patching
and compares all 256 class values, empty/negative counts, and a 256-entry list
with no enemy or an enemy first/last/middle. It deliberately supplies stale
opposite flag values to the replacement. Both CPUs pass all 262 cases and
restore the original active list/count and gate byte. BOSS_GATE_BAD compares
against $fe instead of $ff and yields five expected failures. Gameplay, HUD,
fresh projection, eligibility and spawn progress match the preceding build at
201/600/1500 on normal A500 and delayed 68020. These early comparisons contain
hostiles; they do not establish a complete boss encounter. The diagnostics are
byte-excluded without VERIFY. State snapshots now include data $1efc, the
spawn-progress word $1e70 and target byte $46b0.

The shortened-wave BOSS_ENCOUNTER setup plus JUMP_TEST=3500 now exercises a
native level-0 boss kill and exit. Read-only breakpoints in
`sim60-boss-native-hit`, with exact `tmp/boss-native-hit.{lst,slave}`, stop at
$10c58 and its $10c5c return. At simulation tick 3831, a type-23 projectile
owned by the player has height 2508; the type-44 boss has health 9 and the
native damage argument is 9. On return, health is zero and score rises
0→1000. At $3610, tick 4263, the colliding actor is type 25, active is one,
and death is zero. The native CLR.B clears active at $3616 while death stays
zero. `native-events.json` retains these observations. No debugger writes
are used. The completed exit update is tick 4264.

Paired `sim60-boss-exit-{a500,slow-020}` captures match mapped gameplay,
HUD and fresh projection at 3500/3600/3800/4100/4264, then session-2 ticks
600/1500. Deferred shared projection scratch is reported separately. Both
pass all 87 installed-hook checks and the passive level observer: one ordinary
level increment, zero errors, session 1→2, zeroed simulation/private state,
initial credit 60 and resume energy 528. Results are in
`tmp/boss-exit-cross-validation.json`. This validates the first boss-to-level
transition; it bypasses opening-wave completion and jump acquisition/selection,
and does not establish later boss or ending behavior.

The A500 boss profile at tick 3500 isolates a 26-field render stall while
simulation updates average 67524.07 cycles and catch up between pictures.
Native $1c84c swaps buffer indices at data $292a/$292c, conditionally rebuilds
both display lists using dirty count $2ee6, and loads the selected View. Its
$1c8d6 call reaches MrgCop through $1ce46/$250cc (graphics LVO -210). One
complete merge costs 538058 cycles within the 2334618-cycle render. Native
$1c9be stores user-copper pointer $2ee0 and sets dirty count two; shake changes
ViewPort offsets $7156/$7158 before calling that setter through $4226. A
pointer-only cache would therefore miss real viewport changes. Exact evidence
is in `sim60-boss-profile-a500/profile-details.json`; no copper replacement is
enabled. The model draw $13b96 is the larger measured component at
1168202 cycles. Call costs exclude interrupt execution and describe this one
render, not all scenes or guaranteed attainable savings.

The native CopList layout has cursor +16, output long/short starts +20/+24,
and count/capacity +28/+30. Captured display chains have 40/16/1 six-byte
instructions and one 497-entry user list. The compiled list contains 550 live
hardware instructions through $ffff/$fffe, with capacity 557; unused capacity
tail bytes are not output. MrgCop updates View.LOFCprList, advances the first
CopPtr by six and updates three CopLStart pointers. Native $1c88e frees the
previous cprlist through $1cae4/$252d8 before rebuilding, so its freed output
pointer cannot be retained. Post-merge palette work also changes the final
committed list. Captures and models remain in `sim60-copper-lifetime-a500`.

The content-checked merge-cache experiment is rejected and archived in
`tmp/copper-cache-prototype/`; no runtime cache or related fixture hooks remain
in active sources. The guarded key retained View/ViewPort, MaxDisplayRow and
all four CopList headers/instructions. Replay allocated a ten-byte public
cprlist and public/chip hardware storage, reconstructed headers and relocated
output pointers. It preserved native behavior in the tested replay twins,
allocation failures and the tick-3848 live display. Wide copies preserved d1,
handled odd pointers with bytes and passed 496 length/alignment cases plus
1440 unequal comparisons on both CPUs; the dropped-tail control failed eighty
cases as expected.

A complete wide-cache hit cost 96430 cycles. Miss observers cost
658782/657792 including native merges 537206/537622, giving added work
121576/120170. However, only eleven merge requests occur over the paired
4800-tick A500 combat interval, with five hits. Total fields change merely
5036→5030 and presentations remain 45; update rate changes 57.1882→57.2565 Hz,
with substantial growing debt in both. The cache is not promoted. Native,
cached A500 and delayed cached 68020 states match at five checkpoints through
5400, with six reset records and all hook checks passing. Evidence is retained
in `tmp/copper-long-validation.json` and the exact-build capture folders.

A read-only render-entry/return capture at tick 229 is retained in
`tmp/prof/sim60-render-writes-a500/{render-before,render-after}` with the exact
`tmp/render-writes-a500.{lst,slave}`. `render-writes.json` lists every changed
data-hunk byte (561 total); mapped gameplay/HUD/fresh actor projection stays
unchanged. Only the explicitly exposed deferred projection scratch differs.
`tools/render_write_inventory.py` now identifies guarded storage families for
all 561 bytes: one elapsed timer-counter byte, two display-buffer-index
bytes, twelve vertex-validity bytes, 312 transformed-coordinate bytes and 151
projected-coordinate bytes. Another 32 bytes are polygon screen coordinates
(15), clipped polygon coordinates (8), the projection-context pointer (2),
model transform input (4) and transformed model vector (3). Native polygon
writers at $14678/$1468e and clipping-array references at $14e20/$14e26
establish those buffer families. $12928 stores the current projection context;
$13a56 and $138b4/$138c6/$138d8 identify the temporary six-byte vectors.
An additional 29 bytes are projection translation vectors (6), the View
copper-list pointer (2), RasInfo/RastPort bitmap pointers (one each), AreaInfo
first-point coordinates (2) and the area-fill vector buffer (17). NDK
`graphics/view.i` and `graphics/rastport.i` define those structure fields;
native initialization at $1ccbc..$1cccc and the InitArea wrapper at $2518e
establish the 20-vector allocation, with live vector/flag pointers checked.
The final 22 bytes lie in the observed first nine model-sort key slots (18)
and face-pointer slots (4), whose native producers are guarded at
$13a80/$13a0a and consumers at $13ac0/$13bdc. Only that observed prefix is
identified; this is not a declaration of total array capacity.
Native model setup resets validity at $13b84;
$17b48/$17b56/$17b66/$17b76/$17d14/$17d34 establish the vertex-array bases.
This identifies storage, not every consumer's lifetime or gameplay safety.
This retained scene now has no unclassified changed bytes; any additional
unknown bytes remain explicit, and no comparator exclusion is added. All 561 original changed offsets are retained. Corrupted code and
energy are rejected, while an extra unknown byte remains visible as unknown.
Results are `tmp/render-write-inventory.json` and
`tmp/render-inventory-controls.json`. Changes during the interval can also
come from interrupts; the elapsed clock is not attributed to the renderer.
`tools/model_sort_lifetime.py` separately checks per-model initialization in
complete observed passes. Current heavy A500, first-boss A500 and delayed
68020 traces pass 3/1/9 model passes, covering 520 key reads and 129 pointer
reads; omitted key or pointer initialization is rejected. No incomplete pass
is included. Results: `tmp/model-sort-lifetime-validation.json`. This supports
scratch reuse within those passes, not static capacity or unseen callers.
Complete consumer-lifetime classification and other rendering paths remain
open; this single-scene inventory is not a whole-program independence proof.

### Native inactive-game bypass

After collision handling, native $2b4e tests the active-game flag and $2b54
branches to $2c50 when it is clear. SIM60 replaces $2c50 with RTS, but the
wrapper previously continued through projection, star integration and damage
shake after this early return. EXIT_GUARD (default 1) tests the active flag
after the $2b38 call and skips those three routines on the inactive path.
Cooldowns, clone and power timers, post-update death/quit handling and
recentering still run once. The change adds sixteen bytes to the SIM60 build.

VERIFY-only LEVEL_EARLY injects the exit at $2b4e by replacing the complete
six-byte TST with a call that requests exit and replays the test. Its native
BEQ remains intact. `tools/exit_audit.py` follows the actual branch destination
at the same stack depth, tolerating intervening interrupts, and counts calls
through a complete simulation update. It requires an exact retained slave
and assembly listing and verifies the native branch and patched return bytes.

`sim60-exit-unguarded` (EXIT_GUARD=0) takes the native bypass but still calls
all three forbidden routines once; the audit rejects it. With the default
guard, `sim60-exit-a500` and `sim60-exit-020` each contain one complete
inactive update, no forbidden calls, and exactly one call to each of the five
required post-update routines. The traces contain ten and nine complete
updates respectively. The 68020 adds twenty fields per render. Gameplay and
projection match at tick 190 and after native loading at resumed ticks
600/1500. Both W761 reset records have zero errors, level 1/session 2,
credit 60 and cleared private state. These are injected exits, not natural
boss kills or final-ending coverage. Results are in each capture's
`exit-audit.json` and `tmp/exit-validation-summary.json`; exact listings and
binaries are `tmp/exit-{a500,020}.{lst,slave}`. Non-VERIFY builds with and
without early-exit fixture flags are byte-identical
(`tmp/exit-nonverify-{0,1}.slave`).
The active-path regression `sim60-exit-normal-level5`, without LEVEL_EARLY,
passes all five native resets and matches the preceding `sim60-level5-a500`
gameplay/projection at ticks 600/1500/3600. Its results are retained in
`exit-regression.json`. The normal non-VERIFY slave rebuild also passes.


### Native death and retry lifecycle

ABI version 17 adds a persistent gameplay-entry count at entry+100 and a
VERIFY-only DEATH_TEST result offset at +104. Simulation ticks still reset on
entry; the session count distinguishes snapshots before and after native retry.
DEATH_TEST injects energy -1 once after completed tick 200, leaving the native
post-update death check, death screen, Continue dialog, cleanup and level reload
intact. The dialog hook recognizes the actual Continue text at data $2310 and
supplies Yes only after 60 fields in its native polling loop. The scheduler is
inactive throughout the death/Continue path.

`sim60-death-a500` and `sim60-death-slow020` both exit at completed tick 201 with
negative energy, inactive gameplay and death flag 1. Exactly one Continue dialog
is observed, held for exactly 60 fields in both captures. Native retry enters
session 2 with energy 680, level 0 and death flag 0. The complete motion-record
table, star remainders, jump, cooldown, power, knockback, pickup and shake states
are zero at reentry. Tick/render counters and phase reset to zero, and clock
credit is one 60 Hz tick. The new clock anchor follows the Continue answer;
none of the death/level-loading interval becomes simulation debt. This checks
real cleanup/allocation/reentry; lethal collision geometry and a visual review
of the death screen are not covered by the injected-energy fixture.

Mapped state matches across CPUs/render costs at dying tick 201 and resumed
ticks 600/1500. However, the restarted 68000 scene exposes a throughput failure:
from resumed tick 600 to 1500 it consumes 1070 NTSC fields, approximately 50.47
updates/second, while debt grows from 69 to 239 ticks. It renders zero times
through resumed tick 1500. The delayed 68020 consumes 895 fields over the same
900 updates (60.34 updates/second while reducing debt by five ticks), with 24
renders in that interval and 39 total. These are scheduler-field measurements;
small boundary sampling jitter does not explain the 68000's growing backlog.
The early 5 Hz reference pace and cross-render state equivalence do not establish
that the 60 Hz implementation is fast enough. Profiling and reducing this
simulation cost is required before release; dropping accumulated ticks would
violate gameplay pace.

DEATH_TEST is byte-excluded without VERIFY. The shared modal-test poll still
builds with the earlier PAUSE_TEST diagnostic. No-change preferences and the
explicit nested pause path are also covered. Actual preference changes, later
lives and natural level/ending transitions remain to validate.

`DEATH_DECLINE=1` extends this fixture through native No, menu return and Begin.
A500 and delayed 68020 both stop at tick 201, enter the menu exactly once with
simulation inactive and session still 1, then start session 2 at level 0 with
energy 680 and death flag zero. Tick/render counters, phase, all motion records,
star fractions and jump/cooldown/power/knock/pickup/shake/terrain/HUD private
states are zero at entry. Clock credit is exactly 60, one initial tick; death,
menu and loading time do not become catch-up debt.

The A500 dialog answer/menu/new-game clock fields are 5004/6488/7502;
the delayed 68020 records 2167/3000/3357. These intervals differ substantially,
yet mapped gameplay/HUD/fresh projection matches at resumed ticks 600/1500.
Deferred shared projection scratch is reported separately. The second new game
is not asserted equal to the first game after boot: native RNG and other game
history are retained by the original menu flow. Across 900 resumed ticks the
A500 takes 909 fields, presents thirty times and changes debt 26→35; the delayed
68020 takes 905 fields, presents thirty times and changes debt 18→23. These
short averages do not prove sustained real-time performance.

`DEATH_BAD_DECLINE=1` selects Yes instead: native retry completes, but no main
menu visit is observed, the fixture reports an error, and the decline validator
rejects it. Eight altered-result controls also reject wrong menu/session/clock
state. `tmp/death-decline-validation.json` retains both-CPU state/lifecycle/rate
checks and the native wrong-choice control; the exact listings/slaves accompany
each capture. The additional diagnostics are byte-excluded from non-VERIFY
SIM60, and the normal legacy slave remains identical and restored.


The retained `sim60-death-cost-a500` ten-field profile begins at resumed tick
600. It records nine completed updates, zero gameplay swaps, zero STOP cycles
and roughly 119665 cycles per NTSC field. The report attributes about 24.6% of
all captured cycles inclusively to projection ($12aa4) and 29.4% to the player
collision path ($352e); these are separate candidate costs within a short
sample, not proven optimization savings. Native overlap testing ($85f6) is
10.7% of self time. Interrupt context consumes 12.7% of recorded cycles. The
first captured image is black, consistent with the restarted scheduler never
reaching a presentation. This reproduces the failure independently of the
checkpoint-only run. Reproduce with DEATH_TEST=200, `--tick 600 --fields 10`.


### Catch-up batches and presentation

The scheduler snapshots elapsed time once before a catch-up batch, processes
that finite set of owed updates, then permits rendering. Elapsed fields during
updates and rendering are retained by the next clock poll. This prevents the
old loop from continually adding more updates ahead of presentation when the
CPU cannot keep up. There is no dropped-tick cap or time clamp. Death/quit flags
are still checked between each update, and a modal can reanchor its own excluded
interval while retaining debt. The implementation still needs sufficient CPU
throughput: a slow machine can accumulate large debt and long batches.

`sim60_state.py` now reports observed native VBL fields, fields not yet added by
the scheduler, and total pending ticks. Stored credit alone understates debt
while a batch is executing. The accounting identity remains
`last_field*60 - ticks*field_hz - credit`; without a modal or session restart it
must remain constant. Read total pending ticks when assessing throughput.

`sim60-batch-death-a500` renders eight times by resumed tick 1500, versus zero
in the continuously extended catch-up loop. Mapped state matches the old loop
at dying tick 201 and resumed ticks 600/1500. The batched run has 236 pending
ticks at 600 and 482 at 1500, so it is not a 60 Hz performance success. The
retained delayed-68020 run with PAUSE_TEST still matches mapped state but exposed
the discarded modal-credit bug described above.

After correcting the modal wrapper, `sim60-batch-pause-credit020` passes real
retry and matches the uninterrupted 68000 at resumed tick 1500. At ticks
1307/1308 the native field advances 60, completed simulation advances one,
pending ticks go from 35 to 34, modal resumes increments once, and the modal
flag is clear afterward. Clock origin changes by exactly 60*60 credit units,
excluding just the paused interval. The 68000 run `sim60-batch-pause-credit000`
passes the same check with 391 ticks already pending. It spans 61 observed fields
across the pause and one completed tick: 60 fields are excluded and the remaining
active field is retained, so pending ticks remain 391. Both clock origins advance
by exactly 3600 credit units. `tools/pause_state.py` checks this accounting with
an explicitly supplied 60-field modal interval.

Mapped state matches across the corrected CPU runs at resumed ticks 600, 1307,
1308 and 1500. The real death/retry checks still pass; eight versus 39 renders
occur by tick 1500. The 68000 gameplay screenshot at tick 600 now shows the SOL
cockpit and scene rather than the prior black screen. It still has 484 ticks
pending at 1500; presentation is possible but throughput and responsiveness
remain unacceptable for the requested final state. The normal build is restored.


### Collision-list scan optimization

The guarded eight-byte entry hook at $3a54 selects an inline replacement with
`SCAN_FAST=1`, the default within experimental SIM60. `SCAN_FAST=0` retains
the native baseline. It traverses the same active list in the same order, skips the
query itself and category bytes $fc/$fd, and inlines the native $85f6 overlap
calculation. Type 7 never collides. Radius addition, arithmetic halving, signed
coordinate subtraction/absolute value and inclusive signed comparisons retain
native long-word wrap behavior, including the negative absolute value of
$80000000. Every overlapping actor receives the query in its link at +$66;
the result is the last overlapping actor, not the first. Empty/negative counts
return zero; positive counts above 256 fall back to the native routine.

Static callers at $3548, $3880 and $92f8 use the returned actor pointer and do
not depend on the incidental A0 value. Preserved registers remain preserved.
No static branch enters the displaced prologue interior. Placement uses the
same scan; the original $85f6 remains untouched for other collision paths.

The VERIFY SCAN_TWIN captures pre-call links, runs the original routine, records
its result/links, restores all pre-call links in a separate pass, then runs the
replacement and compares. Separate passes support duplicate pointers. It
restores native outputs after comparison, counts errors rather than masking
them, and is not used for performance measurements. SCAN_TEST adds 68 cases:
16 geometric/radius cases with normal, multiple-hit, type-7-query and reversed
lists, plus empty/negative/full-capacity/self-only lists. The full list contains
duplicate non-overlapping pointers; duplicate-hit coverage is not established. Boundary contact, zero radius, signed extremes and radius
sum overflow are checked against native execution.

`sim60-scan-twin-a500` and `sim60-scan-twin-slow020` each report 6647 matched calls
through restarted tick 1500, including all 68 synthetic cases, with zero return
or link mismatches. Mapped gameplay and native death/retry match across CPUs,
and the 68000 matches the preceding build at resumed ticks 600/1500. ABI 19
adds the L760 result offset at entry+108. Broader encounter coverage remains open.

Fast-only measurements exclude the twin and synthetic scan cases. All captures
use DEATH_TEST=200, beginning the trace at restarted tick 600 and retaining a
checkpoint at 1500. The 68020 adds SLOW_DRAW=20; its trace spans 60 fields because
the ten-field fast capture contains only the artificial draw delay.

| CPU | Native mean cycles/call | Fast mean cycles/call | Reduction | Completed native/fast calls |
|---|---:|---:|---:|---:|
| 68000 | 4318 | 2226.75 | 48.43% | 36 / 40 |
| 68020 | 2037.76 | 908.03 | 55.44% | 196 / 144 |

The retained pairs are `sim60-scan-native-a500` / `sim60-scan-fast-a500`
(ten-field traces) and `sim60-scan-native020-long` / `sim60-scan-fast020-long`
(sixty-field traces). `routine-costs.json` in each capture retains all complete
call samples for $3a54 and scalar projection $16ff6. Different call counts reflect
fixed field windows; they are not presentation-rate measurements.

Across resumed ticks 600 to 1500, the 68000 requires 1146 native-baseline fields
versus 1079 fast-scan fields: 47.12 versus 50.05 updates/second, a 6.2% throughput
increase on this route. Both intervals contain three presentations. Pending ticks
rise from 236 to 482 in the baseline and 214 to 393 with the fast scan. Thus the
optimization helps but does not achieve sustained 60 Hz. The delayed 68020 spans
903 versus 910 fields (59.80 versus 59.34 updates/second); this short checkpoint
interval and differing draw phases do not establish an overall rate gain there.
Mapped gameplay at ticks 600/1500 matches between implementations and CPUs, and
real death/retry checks pass in these retained pairs. SCAN_FAST defaults on;
zero selects the native scan for comparisons. The normal build remains the
legacy-loop prototype.

### Scalar projection optimization

In `sim60-scan-fast-a500`, $16ff6 costs a mean 2982.49 cycles over 65 complete
calls, about 16.2% of the ten-field trace's nominal CPU budget. The delayed
68020 fast capture measures 1255.01 cycles over 273 complete calls. These are
native routine costs, not measured savings from a replacement.

The scalar entry supplies D1=0 to the two-component projector at $1724c. That
routine calculates both components using multiplication at $170f6 and division
at $171b8. The scalar specialization omits the second zero-component pair
while keeping the first native calculation, including its rounding and overflow
behavior. Both inspected callers ($12b4e and $134c6) consume D0; the two-component
entry used elsewhere remains unchanged. RADIUS_FAST=1 keeps that first native
calculation and is now the default within
experimental SIM60. RADIUS_FAST=0 retains the native scalar routine.
The native twin checks signed/extreme operands at shifts 0/1/8/16 and compares
projection results directly, since mapped gameplay snapshots omit projected
coordinates. Other shifts and division-by-zero exceptions are not fixture-tested. The wide division path calls $125d2,
which returns the remainder from signed division through $125f0/$24ac0; the
inspected helper writes only its stack and registers, not global state. Keeping
the first native division preserves this path. The omitted zero component uses
the narrow division path for nonzero denominators. A zero denominator must retain
the original exception behavior rather than silently return zero.

The scalar hook replaces the first eight bytes at $16ff6 (two whole
instructions), with a native trampoline resuming at $16ffe. Static branch search
finds no entries into the displaced interior. The replacement preserves D2/D3
and A1, and the native helpers preserve the other callee-saved registers. D0 is
the projected scalar and D1 remains zero. Both audited callers discard returned
flags and do not use the incidental stack pointer left in A0. The VERIFY twin
compares D0/D1 directly, covering the scalar output omitted by mapped-state
comparisons. Diagnostics are byte-excluded outside VERIFY.

`sim60-radius-twin-fixed-a500` and `sim60-radius-twin-slow020` pass 14008 and
14482 calls respectively through restarted tick 1500, including all 128 synthetic
cases, with zero D0/D1 mismatches. The 68020 adds twenty fields per render.
Mapped gameplay matches across CPUs at 1500; the 68000 also matches the preceding
fast-scan build at 600/1500. Its native death/retry checks pass. The displaced
boundary, untouched two-component projector and native arithmetic bodies pass
byte checks on both captures. Replacement-only gameplay and speed measurements
are described below. The first capture, `sim60-radius-twin-a500`, was stopped after
an installation failure: the installer did not reload A1 for resload_Patch.
It supplies no runtime equivalence evidence; the fixed capture above does.

Matched replacement-only captures `sim60-radius-ab-a500-0` / `-1` and
`sim60-radius-ab-020-0` / `-1` compare RADIUS_FAST=0/1 with DEATH_TEST=200.
The 68000 records ten fields from restarted tick 600, and the 68020 records
sixty fields with SLOW_DRAW=20. All retain a tick-1500 checkpoint and exact slave.
`radius-cost.json` preserves complete-call cycle samples, excluding interrupts
and boundary-partial calls.

| CPU | Native mean cycles/call | Fast mean cycles/call | Reduction | Completed native/fast calls |
|---|---:|---:|---:|---:|
| 68000 | 2982.49 | 1513.22 | 49.26% | 65 / 77 |
| 68020 | 1255.16 | 659.85 | 47.43% | 266 / 380 |

Mapped state at ticks 600 and 1500 matches across both implementations and CPUs.
Replacement-only native death/retry checks pass on both CPUs. The disabled
68000 capture retains the original eight entry bytes. Between those checkpoints,
900 updates take 1079 versus 1025 fields on the 68000: 50.05 versus 52.68 Hz.
Presentations increase from three to five. Pending debt increases from 214 to
393 in the baseline and from 163 to 288 with scalar projection enabled. This
is a throughput improvement, but still fails the sustained 60 Hz requirement.
The delayed 68020 spans 929 versus 911 fields (58.13 versus 59.28 Hz), with 26
presentations in each interval. These checkpoint averages include different
positions in the render cycle; complete-call costs establish the routine gain.

The new default build is byte-identical to the retained optimized 68020 slave
with matching VERIFY flags. Explicit RADIUS_FAST=0 reproduces its baseline.
The normal build remains the legacy prototype and has been restored.

### Zero-numerator integration divisions

The exact slave listing for `sim60-radius-ab-a500-1` maps $17da to s60_move,
$1edc to s60_stars_update and $25b4 to s60_sort. Its ten-field trace contains
372 divisions at the ordinary rotation/position and star X/Y integration sites;
282 have a zero numerator. Those zero divisions consume 44038 cycles, or 3.68%
of the full recorded CPU budget. `zero-divisions.json` retains operand counts
beside the capture. This is an opportunity bound, not total optimization savings.

S60_DIV12 performs TST.L/BEQ before DIVS #12. For zero, the unchanged register
already contains the exact packed quotient/remainder, and TST establishes the
same NZVC bits as division; neither instruction changes X. For nonzero inputs,
the original DIVS still executes, including native signed overflow behavior.
Only these four measured sites use the shortcut. No timestep, precision, record
layout, collision rollback or star respawn behavior is changed. DIV_ZERO defaults
to one within experimental SIM60; zero restores the preceding instructions.

The retained `sim60-divzero-a500` and `sim60-divzero-020` captures use DEATH_TEST=200
and ticks 600/1500. The 68000 records ten fields; the 68020 records sixty fields
with SLOW_DRAW=20. Their baselines are the corresponding `sim60-radius-ab-*-1`
captures, reproduced byte-identically with DIV_ZERO=0 before running the pair.
Mapped gameplay, motion remainders and stars match at both checkpoints across
implementations and CPUs. Native death/retry checks pass on both CPUs.

| CPU | Baseline movement cycles/call | Fast movement cycles/call | Completed baseline/fast calls |
|---|---:|---:|---:|
| 68000 | 5160.35 | 4417.59 | 40 / 44 |
| 68020 | 2187.88 | 2040.54 | 208 / 204 |

`movement-cost.json` retains complete-call samples at $8682, excluding interrupts
and boundary-partial calls. These are observed scene averages; moving and idle
calls have different savings. The 68000 completes 900 updates in 1019 fields
versus 1025 (52.99 versus 52.68 Hz), with six versus five presentations during
the interval. Pending debt still increases from 145 to 264. The delayed 68020
spans 908 versus 911 fields (59.47 versus 59.28 Hz), with 26 presentations in both
intervals. The optimization reduces measured work on both CPUs but still does
not establish sustained 60 Hz. Default binaries match the tested optimized
captures; the normal legacy build is restored.

### Pointer-walk depth sorting

The cached sorter still spends time rebuilding indexed addresses in each inner
iteration. SORT_WALK=1 advances pointers through the active list and cached
keys, uses byte offsets for swaps and counts the remaining suffix with DBF.
Distances still use native $4388, with the level-1 type-46 override. Strict signed
comparison retains tie order and the previous selected entry when a suffix has
no positive distance. If the entire list is nonpositive, the existing fallback
restores incoming registers and invokes the original routine, including its
incoming-D5 behavior. No new game hook or actor field is introduced.

`sim60-sortwalk-twin-a500` and `sim60-sortwalk-twin-020` complete 1778 native-order
comparisons per CPU through restarted tick 1500, including all 32 synthetic
cases. The 68020 adds SLOW_DRAW=20. Mapped state matches across CPUs and with
the preceding build at ticks 600/1500; native death/retry passes on the 68000.
The fixture includes counts 0/1/16/256, positive ascending/reversed/tied keys,
all-zero and mixed-zero keys, signed-long extrema that produce negative keys,
and level-1 type-46 overrides. Full lists contain duplicate pointers. All list,
view and level state is restored. Native sort output is compared entry by entry;
a mismatch aborts the guest. Incoming D5 is defined as zero for the isolated
all-nonpositive cases. Diagnostics are byte-excluded outside VERIFY.

Replacement-only paired captures are `sim60-sortwalk-ab-a500-0` / `-1` and
`sim60-sortwalk-ab-020-0` / `-1`, where the suffix selects SORT_WALK. All use
DEATH_TEST=200, starting at tick 600 and retaining tick 1500. Traces span ten
fields on the 68000 and sixty fields with SLOW_DRAW=20 on the 68020. Baseline
means the preceding indexed cached sorter, not the original uncached game code.

| CPU | Indexed mean cycles/call | Pointer mean cycles/call | Reduction | Complete indexed/pointer calls |
|---|---:|---:|---:|---:|
| 68000 | 8337.64 | 6910.36 | 17.12% | 11 / 11 |
| 68020 | 4318.56 | 3555.27 | 17.67% | 52 / 51 |

`sort-cost.json` retains complete-call samples at $43de with interrupt and
boundary-partial calls excluded. Mapped gameplay at 600/1500 matches across
implementations and CPUs. Replacement-only native death/retry passes on both.
The 68000 needs 1000 fields for 900 updates versus 1019 (54.00 versus 52.99 Hz),
with six presentations in each interval. Pending debt grows from 138 to 238
with the pointer walk, compared with 145 to 264 before. The delayed 68020 needs
906 versus 912 fields (59.60 versus 59.21 Hz), with 26 presentations in each.
Checkpoint rates depend on render phase; the complete-call measurement supports
the routine gain on each CPU. The 68000 still fails sustained 60 Hz.

SORT_WALK now defaults to one within SIM60. The default builds reproduce the
retained optimized slaves byte for byte; zero retains the indexed baseline.
The normal legacy-loop build is restored.

### Stationary star integration

STAR_IDLE bypasses arithmetic only if the player's speed and effective yaw
velocity (after native ASR #4) are both zero and the current star's two stored
remainders are exactly zero. Every skipped product, displacement and remainder
would then be zero regardless of its coordinates. The same bounds checks and
native $9bd4 respawn follow; out-of-bounds stars still consume the same RNG draws.
Nonzero remainders, including unusual values, always take the original path.
The cached zero-input flag uses saved D4, preserved by the audited native respawn
and RNG helpers. STAR_IDLE=0 reproduces the preceding slave byte for byte.

Captures `sim60-staridle-ab-a500-0` / `-1` and `sim60-staridle-ab-020-0` / `-1`
use DEATH_TEST=200 and checkpoints 600/1206/1300/1500. Mapped gameplay, all motion
and star remainders, and RNG match across implementations and CPUs at every
checkpoint. Native death/retry passes on both CPUs. The observed player speed/yaw
velocity pairs are (0,0), (15,0), (93,0) and (200,-474), exercising stationary,
moving and turning paths. These are state comparisons, not exhaustive star-input
or respawn fixtures.

| CPU | Baseline star cycles/call | Idle shortcut cycles/call | Complete baseline/shortcut calls |
|---|---:|---:|---:|
| 68000 | 4534.91 | 2037.64 | 11 / 11 |
| 68020 | 1834.62 | 864.12 | 52 / 51 |

Traces start at tick 600 and span ten fields on the 68000, sixty on the 68020
with SLOW_DRAW=20. These routine savings apply to the captured stationary scene.
`stars-cost.json` retains complete-call samples from the exact slave entry;
matched symbol-listing binaries establish its offset. The new slave-entry mode
of routine_cost.py was cross-checked on 45 movement calls: each sample equals
the existing game-entry measurement minus the recorded JMP cost, including bus
waits. Interrupt and boundary-partial calls remain excluded.

Across the full 900-update checkpoint interval, the 68000 requires 992 fields
versus 1000 (54.44 versus 54.00 Hz), with six presentations in each run. Pending
debt grows from 143 to 235 ticks, versus 138 to 238 before. The delayed 68020
requires 907 versus 906 fields (59.54 versus 59.60 Hz), with 26 presentations;
that phase-dependent interval does not show an overall rate gain. Idle routine
cost is lower on both CPUs. STAR_IDLE now defaults on within experimental SIM60;
default binaries match the tested slaves and the normal legacy build is restored.
Sustained 68000 60 Hz remains unmet.

### Native movement reuse audit

`motion_inputs.py` reconstructs native movement inputs from the retained
`sim60-staridle-ab-a500-1` and `sim60-staridle-ab-020-1` traces. Trigonometric
argument checks agree with the reconstructed pitch and yaw, including the
sine helper's quarter-turn offset. These are observations of the current idle
reference window, not a full-game reuse model.

The 68000 has 44 complete native calls and 34 distinct input tuples across four
actors. Only the all-zero stationary-player input repeats (eleven calls); each
moving actor changes inputs every call. A cold four-entry FIFO model gets five
hits, while a per-actor last-input model gets ten. The longer 68020 window has
200 calls, 151 distinct tuples, 25 FIFO hits and 49 per-actor hits; again only
the stationary input repeats. Native complete-call cost averages 1978.45 cycles
on the 68000 (minimum 430, maximum 3970) and 898.74 on the 68020 (253..1712).
A general displacement cache is not justified by this route: the reusable work
is the cheap stationary case, and lookup overhead would burden the moving cases.
No movement cache is installed.

One quarter of these calls instead have zero pitch and nonzero bank, causing
the native OR at $86ae to select the five-trigonometric-call path. Bank itself
is not used in that path's displacement expressions. Both captures have native
cos(0)=16384 and sin(0)=0. This suggests a zero-pitch specialization could use
the existing two-component path regardless of bank while preserving word-angle
updates and linear additions. The specialization and native comparisons are described below. General
cache reuse is not pursued on the basis of these traces.

### Zero-pitch movement specialization

FLAT_PITCH replaces the single word OR.W D0,D1 at $86ae with TST.W D0. D0 is
pitch after the native angular update, so zero pitch chooses the existing flat
path regardless of bank. Nonzero pitch retains the general path. With native
cos(0)=16384 and sin(0)=0, the general path's intermediate products reduce exactly
to the flat path before its final arithmetic shifts; native linear additions and
position wrap remain unchanged. Installation checks the original instruction,
following branch, those two table constants, and absence of -32768 in all 2049
reachable trig-table words (flat X uses a word negation). All other native movement
instructions remain intact. This applies to native placement and scripted calls
as well as the SIM60 wrapper. Inspected call sites treat the routine as a mutation
of actor state, not a returned scratch-register value.

The VERIFY fixture temporarily selects the original instruction, flushes caches,
runs native movement on one actor, selects the optimized instruction and repeats
on an identical actor. It compares all 110 actor bytes. Six signed speeds including
-32768/-32767/-1/0/1/32767 cross sixteen yaw values and four angular-update setups:
zero-bank control, nonzero bank at exact yaw boundaries/cardinal directions,
pitch becoming zero with bank wrap, and pitch becoming nonzero. Yaw advances/wraps
in the latter two variants; extreme linear components and near-limit
positions exercise the same signed arithmetic. These 384 cases do not constitute
full gameplay/encounter coverage.

`sim60-flat-final-a500` and `sim60-flat-final-020` pass all 384 cases with zero errors,
alongside 48 boss and four collision/rollback cases, through native death/retry and
resumed tick 1500. The 68020 adds twenty fields per render. Mapped gameplay matches
across CPUs and the preceding build. The patched word and untouched native tail
pass byte checks, and diagnostic flags have no effect outside VERIFY.

The earlier `sim60-flat-test-*` captures pass their first fixture executions but
expose an old diagnostic rerun bug after retry resets ticks: boss/collision counters
accumulate twice despite fixed-size result arrays. Once-only guards correct that
behavior, and the collision reader now bounds the count before reading records.
The `flat-once` captures first verify the counter fix; the `flat-final` captures
also strengthen the banked case to exercise exact cardinal yaw values without a
prior yaw increment. Use `flat-final` for the current post-retry fixture validation.

Replacement-only pairs `sim60-flat-ab-a500-0` / `-1` and `sim60-flat-ab-020-0` /
`-1` use FLAT_PITCH=0/1, DEATH_TEST=200, and checkpoints 600/1206/1300/1500.
Their traces span ten fields on the 68000 and sixty on the 68020 with SLOW_DRAW=20.
Mapped gameplay matches at every checkpoint across implementations and CPUs;
native death/retry passes. Byte checks show the native body differs only at $86ae.

| CPU | Baseline movement cycles/call | Optimized cycles/call | Complete baseline/optimized calls |
|---|---:|---:|---:|
| 68000 | 4480.23 | 4072.14 | 44 / 44 |
| 68020 | 2040.80 | 1832.19 | 184 / 180 |

`movement-cost.json` retains complete calls at $8682, including the SIM60 wrapper,
excluding interrupts and boundary-partial calls. The observed reductions are
9.11% and 10.22%; this scene mixes unaffected flat calls and newly shortened banked
calls. The 68000 completes 900 updates in 976 fields versus 992 (55.33 versus
54.44 Hz), with six presentations in both intervals. Pending debt still grows
from 134 to 210 ticks, versus 143 to 235 before. The delayed 68020 spans 903
versus 905 fields (59.80 versus 59.67 Hz), with 26 presentations in each.
These checkpoint averages depend on render phase; neither establishes sustained
68000 60 Hz. FLAT_PITCH now defaults on within experimental SIM60, and the default
builds are byte-identical to the retained optimized pair. The normal legacy build
is restored. Full encounters, transitions and broader pace validation remain open.


## Signed-distance specialization

`distance60.s` replaces the first eight bytes of $4388 with a jump and NOP.
The guarded native prologue is `48e70730 266f0018`; the native trampoline
replays it and resumes at $4390. The original body through $43dc remains
untouched. Static disassembly finds no branch target inside the displaced
instructions. The helper accepts two pointers to X/Z long pairs on the stack.
It returns the wrapped signed approximation in both D0 and D1, preserving all
other registers. The replacement saves three registers instead of five and
removes redundant temporary copies. It preserves signed subtraction/absolute
value, signed ordering, wrapped multiplication by three, ASR by three and the
final addition, including the native unusual MIN_LONG behavior. Final NZVC
comes from the same result MOVE and X from the final ADD.

The VERIFY twin compares D0 and D1 on each call and returns native outputs.
The 512-case fixture crosses sixteen signed X and Z deltas, including extrema
and rounding boundaries, with zero and near-wrap origins. It does not replace
the native arithmetic with an idealized mathematical distance. Retained
`sim60-distance-twin-a500` and `sim60-distance-twin-020` each record 471605
comparisons, all 512 cases and zero mismatches at tick 1500. The combined sort
oracle completes 1778 calls and 32 configurations on each CPU. Mapped gameplay
matches across CPUs after real death/retry. The 68020 adds twenty fields per
render. Diagnostic flags produce byte-identical non-VERIFY binaries with and
without the fixture; no fixture code enters normal builds.


Replacement-only pairs `sim60-distance-ab-a500-0` / `-1` and
`sim60-distance-ab-020-0` / `-1` use DISTANCE_FAST=0/1, DEATH_TEST=200,
checkpoints 600/1206/1300/1500, and traces of ten/sixty fields respectively.
The 68020 adds SLOW_DRAW=20. Mapped state matches at every checkpoint across
modes and CPUs, and both optimized captures pass real death/retry checks.
Hook/tail byte checks pass. `distance-cost.json` retains individual complete
calls, excluding interrupts and boundary-partial calls.

| CPU | Native cycles/call | Replacement cycles/call | Complete native/replacement calls |
|---|---:|---:|---:|
| 68000 | 401.49 | 334.77 | 168 / 158 |
| 68020 | 190.84 | 157.81 | 644 / 588 |

The reductions are 16.62% and 17.30%. The 68000 completes 900 updates in
965 fields versus 976 (55.96 versus 55.33 Hz), with six presentations in both
intervals. Pending debt grows from 129 to 194 ticks, versus 134 to 210 before.
The delayed 68020 spans 926 versus 902 fields (58.32 versus 59.87 Hz), with
27 versus 26 presentations; its extra presentation includes twenty artificial
delay fields. Debt grows from 13 to 39 versus 16 to 18. These differently phased
render intervals do not establish an overall 68020 speedup. The routine itself
is faster on both CPUs, so DISTANCE_FAST defaults on within experimental SIM60;
zero retains the original helper. Sustained 68000 60 Hz remains unachieved.


## Longer post-retry throughput and rendering-cost comparison

`sim60-distance-long-a500` and `sim60-distance-long-020` retain the
SIM60 defaults before RADIUS_SMALL, with DEATH_TEST=200, anchor tick 1500, and checkpoints 2400/3600.
The traces span thirty/sixty fields respectively; the 68020 uses SLOW_DRAW=20.
Mapped gameplay matches between CPUs at all three boundaries, extending the
render-cost comparison beyond the short startup route. The 68000 tick-1500
state also matches the preceding distance A/B capture. Gameplay remains active
in SOL; active-list counts are nine at 1500 and seven at 2400/3600. These runs
exercise the existing movement/firing input route, not new level transitions.
The 68000 image shows the cockpit and world being presented.

| CPU | Tick interval | Observed fields | Updates/s | Presentations | Presentations/s | Pending ticks before/after |
|---|---|---:|---:|---:|---:|---|
| 68000 | 1500–2400 | 1162 | 46.47 | 3 | 0.155 | 194 / 456 |
| 68000 | 2400–3600 | 1287 | 55.94 | 3 | 0.140 | 456 / 543 |
| Delayed 68020 | 1500–2400 | 885 | 61.02 | 22 | 1.492 | 36 / 21 |
| Delayed 68020 | 2400–3600 | 1203 | 59.85 | 33 | 1.646 | 21 / 24 |

`throughput.json` retains these measurements, reproduced by
`tools/simulation_rate.py`. The 61.02 figure is catch-up of previously owed
updates, not a change to the 60 Hz timestep. Clock origins and sessions remain
constant. Neither checkpoint average establishes worst-case frame latency.
The 68000 backlog and presentation rate are unacceptable for the target.

A listing-built slave is byte-identical to the retained 68000 binary before
interpreting its symbols. Complete update calls at slave offset $1572 average
137057 cycles (ten calls, range 133294–140306), excluding other task/interrupt
contexts. The simulation projection subroutine at slave offset $15e0 averages
40690 cycles (ten calls, range 37144–43550), about 29.69% of update cost.
`update-cost.json` retains samples. These are offsets of this exact retained
slave, not game-hunk hook offsets. An update already exceeds the approximately
119665 cycles per NTSC field before rendering and interrupt work; optimizing
only the renderer cannot meet 60 Hz in this scene. The trace includes one
incomplete render call, so its inclusive attribution is not a complete-render
cost measurement. Prioritize reducing update cost, especially projection while
preserving visibility/targeting and callback behavior, then remeasure this route.


## Guarded scalar shortcut

RADIUS_SMALL defaults to one within experimental SIM60. Its guarded path requires effective
scale 128 and unsigned radius <=65535. Both native multiply factors then fit
unsigned words and their product fits positive signed-long. A seven-bit shift
produces the same numerator, and native $171b8's narrow arm can be entered by
calling $1707c with that numerator and the original denominator. Native signed
and wide-denominator division behavior remains intact. Other radii/scales keep
the existing $170f6/$171b8 path; no new game hook is installed.

The broader fixture exposed why the bound must be narrower than merely fitting
the mathematical product in signed-long. Native $170f6's one-word-factor path
at $17124..$1713c discards part of the wider factor's contribution. Radius
16777214, scale 128, denominator 1073741824 returns native zero, whereas a plain
shift followed by division returns one. Preserve the native result through
fallback. The expanded baseline fixture passes all 384 cases with the shortcut
disabled (`sim60-radius-diagnose-0`); `sim60-radius-diagnose-1` records that first
mismatch from the overbroad experimental guard. The earlier `radius-small-twin`
captures have 22 failing cases on both CPUs and are not correctness evidence.

The current fixture tests radii 65534/65535/65536/65537 around the guarded range,
plus signed extrema and wider values, at five scales and four large signed
denominators. Another 64 cases use small signed nonzero denominators at scale
128. V762 records the first failure's radius, denominator, shift and native/fast
D0/D1 after the existing sixteen-byte result header. This is VERIFY-only; the
main SIM60 ABI offset remains unchanged. Corrected validation and performance
captures below justify enabling RADIUS_SMALL by default.


Corrected `sim60-radius-word-twin-a500` and `sim60-radius-word-twin-020`
captures pass all 384 cases with zero errors. Through restarted tick 3600 they
record 30166 and 31388 native comparisons respectively, with zero mismatches.
Mapped state matches the prior longer baseline at 1500/3600 and across CPUs;
real death/retry passes on both. The 68020 uses twenty added fields per render.
Non-VERIFY builds with and without the expanded diagnostic flags are identical.
RADIUS_SMALL=0 builds are byte-identical to the retained longer baseline slaves
on both configurations, allowing those captures to serve as performance baselines.


Replacement-only captures `sim60-radius-word-fast-a500` / `-020` use
RADIUS_SMALL=1 and match the `sim60-distance-long-*` baseline configuration,
with tick 1500 traces and checkpoints 2400/3600. Mapped state matches at all
three boundaries between modes and CPUs; real death/retry passes on both.
`radius-cost.json`, `update-cost.json` (68000) and `throughput.json` retain
complete-call samples and checkpoint intervals. Diagnostic twins are absent.

| CPU | Previous scalar cycles/call | Guarded scalar cycles/call | Complete previous/guarded calls |
|---|---:|---:|---:|
| 68000 | 1580.17 | 858.67 | 108 / 216 |
| 68020 | 659.24 | 353.07 | 702 / 504 |

Scalar cost falls 45.66% and 46.44%. In the 68000 trace, complete update calls
average 130769.57 cycles (23 complete, one partial excluded), versus 137057
(ten complete) in the baseline. Simulation projection averages 34225.83 cycles
(24 calls) versus 40690 (ten). Windows start at the same simulation tick but
contain different numbers of updates/renders; these are observed averages,
not identical per-call input sequences. The full update still exceeds the NTSC
field budget before interrupts/rendering.

| CPU | Tick interval | Observed fields | Updates/s | Presentations | Pending ticks before/after |
|---|---|---:|---:|---:|---|
| 68000 | 1500–2400 | 1115 | 48.43 | 3 | 167 / 382 |
| 68000 | 2400–3600 | 1229 | 58.58 | 3 | 382 / 411 |
| Delayed 68020 | 1500–2400 | 899 | 60.07 | 23 | 22 / 21 |
| Delayed 68020 | 2400–3600 | 1193 | 60.35 | 33 | 21 / 14 |

The 68000 intervals improve from 46.47/55.94 Hz but still accumulate debt and
present only about 0.16/0.15 images per second. The delayed 68020 remains near
the target while paying earlier debt; rates above sixty are catch-up, not a
changed timestep. Its first interval has one more presentation than the baseline.
The routine is faster on both CPUs, so the guard is now enabled by default
within experimental SIM60. Default builds match the retained optimized slaves;
the normal legacy build is restored. Full goal completion remains unproven.


## Omission of unused simulation geometry

PROJECT_SKIP defaults on within experimental SIM60. `projection_skip60.s` guards a jump at $12ae8,
replacing `202b0008 90acddc2`; its trampoline resumes at $12af0. The native
$12adc load leaves the view pointer in A0, A2 points to the current list entry,
D6 is its index, and D7 is the captured list count. The omitted span writes
only per-actor geometry scratch before the visibility branch at $12b72.
Native actor visibility/coordinate stores require bit 3. The native callback
and mesh ordering starts at $12bfc and is retained, with the existing simulation
draw suppression.

The guard requires active simulation, no rendering, bit 3 clear, and either no
callback or the audited $42b0 mesh-animation callback. That callback updates
animation state/arrays without reading projection scratch. Other callbacks
retain all geometry. The last list entry always retains its geometry, restoring
final shared scratch. If that entry is the view actor, native iteration skips
it; therefore the optimization falls back for the whole list in that case.
Earlier skipped null/animation callbacks cannot change the list. Unknown callbacks
still execute after complete geometry, and subsequent guards reread the last
pointer. Rendering and non-gameplay calls retain the original path.

The preserved numeric destinations are data-hunk $5d98..$5db1, $5db4..$5db7,
$5e16..$5e19 and $5e22..$5e29. Other projection scratch legitimately contains
last-render values and must not be used for cross-render-cadence equality.
The optional projection state comparison includes actor transformed coordinates
when bit 3 is set and screen coordinates when bits 3 and 2 are both set.
It does not claim every projection global or stale coordinate is simulation-owned.

In `sim60-radius-word-fast-a500`, all 216 completed actor projections have bit 3
clear; 192 callbacks are null and 24 are $42b0. Keeping each final actor leaves
192 candidates costing 574578 cycles (16.01% of the thirty-field trace), before
guard overhead. The corresponding delayed 68020 trace has 504 actors, nine
visibility paths and 440 candidates (3.94% of the whole trace). The analysis
is an upper bound and does not exclude rendering at candidate classification.
`projection-work.json` retains records. No generic transform cache was added.

`sim60-project-skip-a500` / `-020` use PROJECT_SKIP=1, DEATH_TEST=200, traces
at tick 1500 and checkpoints 2400/3600; the 68020 adds SLOW_DRAW=20.
Mapped state plus the simulation-written projection fields match at all three
boundaries against `sim60-radius-word-fast-*` and across CPUs. Native death/retry
passes. Hook bytes, the preceding view load and unchanged tail pass inspection;
static disassembly finds no entry into the displaced interior. The disabled
68000 build is byte-identical to its retained baseline.

| CPU | Previous update cycles/call | Experimental update | Previous projection | Experimental projection |
|---|---:|---:|---:|---:|
| 68000 | 130769.57 (23) | 110082.22 (27) | 34225.83 (24) | 12879.00 (28) |
| 68020 | 60419.26 (53) | 51666.56 (54) | 14980.83 (54) | 5860.65 (54) |

Parentheses give complete call counts; partial calls/other contexts are excluded.
Exact listing-built binaries match retained slaves before symbol-offset use.
Windows contain different numbers of updates/renders, so these are measured
averages rather than identical per-call input sequences. `update-cost.json`
retains samples. The 68000 update cost is now below the raw field budget, but
interrupts and drawing still need time.

| CPU | Tick interval | Fields | Updates/s | Presentations | Pending ticks before/after |
|---|---|---:|---:|---:|---|
| 68000 | 1500–2400 | 996 | 54.22 | 5 | 121 / 217 |
| 68000 | 2400–3600 | 1110 | 64.86 | 6 | 217 / 127 |
| Delayed 68020 | 1500–2400 | 893 | 60.47 | 24 | 25 / 18 |
| Delayed 68020 | 2400–3600 | 1205 | 59.75 | 35 | 18 / 23 |

Rates above sixty represent catch-up. The 68000 presents about 0.30/0.32 images
per second; full throughput/presentation requirements remain unmet. The route comparisons alone do not establish guard coverage; the native-reference
fixture below supplies the targeted checks. The normal build is restored.


### Native-reference projection guard fixture

The J762 fixture runs after real view preparation, using three isolated fake
actors and a private list. It compares calls through the original geometry
trampoline with the guarded entry. The callback boundary at $12bfc temporarily
returns to the fixture, so it can consume intermediate geometry without drawing
or invoking real callbacks. Both paths run a scratch-reading consumer for the
unknown callback and for rendering/inactive modes. That consumer writes transformed
coordinates into the fake actor, making wrong omissions observable even when
only the final actor's scratch would otherwise be checked. Actor visibility
stores also remain native. The comparison covers all 330 fake actor bytes and
all 170 bytes of data-hunk $5d98..$5e41, restored from the same input for each run.

The 240 cases cross running 0/1, rendering 0/1, visibility bit clear/set, callback
null/$42b0/unknown consumer, final entry ordinary/view actor, and list counts
0/1/2/3/256. The full list cycles the fake actors, checking duplicate pointers
and the maximum 1020-byte look-ahead. Native iteration and fixture iteration
both skip the view actor. The $42b0 body itself is not rerun by this geometry
fixture; existing real-route state checks cover animation behavior. This is
not pixel verification or proof of every gameplay encounter.

`sim60-project-final-a500` and `sim60-project-final-020` both pass all 240 cases
with zero failures through resumed tick 3600. The latter uses SLOW_DRAW=20.
Native callback-boundary bytes are restored, busy clears, and the once-only case
count survives real death/retry. State including simulation-written projection
fields matches across CPUs and the preceding opt-in implementation. Non-VERIFY
builds with and without PROJECT_TEST are identical. ABI 24 adds the result offset
at entry+118 without changing earlier offsets. Earlier `project-guard-*` captures
exercise the preliminary 192-case J760/J761 variants; final coverage uses J762.

Installation now also guards the native view load, view-actor comparison,
branch and callback-boundary instruction. With native guard coverage and the
measured reductions on both CPUs, PROJECT_SKIP is enabled by default inside
experimental SIM60. The normal legacy build remains separate.


Fresh `sim60-project-default-a500` / `-020` captures use the enabled default,
ABI 24 and the strengthened installer guards without PROJECT_TEST. Exact matching
listing builds locate update/projection entries. The 68000 reproduces the prior
110082.22 / 12879.00 cycle averages and both checkpoint intervals exactly.
The 68020 averages 51551.85 update cycles and 5926.63 projection cycles (54 complete
calls each); its intervals are 893/1208 fields, 60.47/59.60 updates per second,
24/35 presentations and pending ticks 25/18/26. State plus simulation-written
projection fields matches all 1500/2400/3600 boundaries across CPUs and against
the preceding opt-in builds. Native retry passes on both. Samples and intervals
are retained as `update-cost.json` and `throughput.json`; the normal legacy build
is restored. These checks enable the local optimization, not completion of the
full 60 Hz/presentation/encounter goal.


## Already-ordered depth sorting

SORT_ORDERED defaults to one within experimental SIM60. After gathering the same cached native distances
and applying the level-1 type-46 override, the pointer-walk sorter can return
immediately if every key is positive and the sequence is nonincreasing. In that
case every strict native selection chooses the current entry, including ties,
and no swaps occur. Any nonpositive key or increasing adjacent pair retains the
full cached selection path. All-nonpositive input still takes the original
fallback, preserving its dependence on incoming D5. SORT_WALK=0 is unchanged.

The check uses saved D2, retaining D0's last gathered distance on both exits.
For the successful path, A0/A1 and D1 match the full cached scan's final values;
its final equal-comparison flags and clear X are reproduced. Saved registers
are restored normally. No new game hook or simulation ABI field is added.

The preceding `sim60-project-default-a500` trace has 28 complete sort calls, all with
positive descending input keys. `sort-inputs.json` retains those exact keys,
read at the distance-cache store in an exact matching listing/binary. This is
an opportunity measurement. The expanded O761 fixture crosses sixteen patterns
with counts 0/1/16/256; its native twin compares the complete resulting pointer
list on every call. `sim60-sort-ordered-final-a500` and
`sim60-sort-ordered-twin-020` pass 3910 comparisons including all 64 cases through
tick 3600. Their mapped gameplay and fresh projection state match the preceding
build at 1500/3600, and native death/retry passes. Diagnostics remain byte-excluded
without VERIFY.

Replacement-only captures `sim60-sort-ordered-fast-a500` and
`sim60-sort-ordered-fast-020` use DEATH_TEST=200, with SLOW_DRAW=20 on the 68020.
Their exact retained binaries match listing builds; SORT_ORDERED=0 reproduces
the corresponding `sim60-project-default-*` baseline binaries. Complete-call
measurements exclude interrupts and boundary-partial calls:

| CPU | Sort before / after (calls) | Update before / after (calls) |
|---|---|---|
| 68000 | 8332.21 (28) / 6001.66 (29) | 110082.22 (27) / 107615.07 (28) |
| 68020 | 4361.72 (54) / 3013.74 (42) | 51551.85 (54) / 50253.44 (41) |

Sort costs fall 27.97%/30.91%; total update averages fall 2.24%/2.52%.
These are scene-window averages, not a claim about every list. Failed ordering
checks add work before the existing selection path. `sort-cost.json` retains
individual sort/update samples. Mapped gameplay plus fresh projection fields
match across both CPUs and the baseline at ticks 1500/2400/3600. Native retry
passes on both CPUs. Observed intervals, retained in `throughput.json`, are:

| CPU | Ticks | Fields | Updates/s | Presentations | Pending before / after |
|---|---|---|---|---|---|
| 68000 | 1500–2400 | 978 | 55.21 | 5 | 120 / 198 |
| 68000 | 2400–3600 | 1111 | 64.81 | 7 | 198 / 109 |
| 68020 | 1500–2400 | 915 | 59.02 | 25 | 14 / 29 |
| 68020 | 2400–3600 | 1203 | 59.85 | 35 | 29 / 32 |

The 68000 presents only 0.31/0.38 times per second, and its faster second
interval pays backlog. The delayed 68020 produces one more deliberately costly
render in the first interval than the baseline, so shorter routine costs do not
imply a better checkpoint update rate. Sustained simulation and acceptable
presentation speed remain unproven. Default builds reproduce these measured
binaries; the normal legacy build is restored afterward.


## Remaining simulation cost attribution

The profiler retains an observed original call entry even when it immediately
jumps to a replacement. This keeps later native continuation instructions from
being assigned to the previous function. Pending calls are tracked per stack
context, so an interrupt between a call and its target does not lose that call.
Two focused regression cases cover both behaviors. Retained reports named
`report-boundaries.txt` use the same `sim60-sort-ordered-fast-*` traces; no game
code or trace changed for this audit.

On the 68000, $85f6 self cost is 185468 cycles across 493 complete calls, exactly
matching independent complete-call and inclusive measurements. The preceding
report attributed 309096 cycles to it; 123628 belong to native movement at
$8682. On the 68020 the corrected call count is 697 rather than 422, restoring
calls previously lost at interrupted entries. Total recorded instruction cycles
are conserved. `sort-report-boundary-check.json` retains these cross-checks.
Self ranges remain heuristic where no entry is discovered; for example the
DEATH_TEST probe itself costs only 1934 cycles in the 68000 window, despite
other nearby code being grouped under its entry in the range report.

Complete-call measurements from exact matching 68000 listing/binary pairs are
retained in `remaining-update-costs.json`:

| Routine | Complete calls | Mean cycles | Total complete-call cycles |
|---|---|---|---|
| Movement wrapper, including native movement | 174 | 3922.64 | 682540 |
| Collision-list scan | 116 | 2322.59 | 269420 |
| Star update | 29 | 6647.24 | 192770 |
| Signed distance replacement | 521 | 314.89 | 164056 |
| Fractional record lookup | 290 | 303.37 | 87976 |

These include child calls and must not be summed as disjoint costs. Movement
uses about 19.0% of all recorded instruction cycles, and collision scans 7.5%.
Both are candidates for further optimization; this attribution correction does
not itself change gameplay speed or establish sustained 60 Hz.


## Collision scan query invariants

`SCAN_GEOMETRY_FIRST=1` defaults on within SIM60. Both actor and projectile
scans test the candidate's signed wrapped X distance before reading its
exclusion flags/type. Type-7 queries still exit before traversal. A candidate
must pass both the original X predicate and classification before any Z/Y test
or hit/link write, so rejection order changes without changing list order,
geometry arithmetic, owner exclusions or first/last-hit behavior. There is no
cache and no additional native hook. Zero restores the preceding ordering.
Both CPUs pass 23591 live scan twins, 68 synthetic actor-scan cases and 64
projectile cases. Separate paired profiles reduce whole-update means by
2.49% on A500 and 2.32% on delayed 68020; extended combat matches all eight
checkpoints through death at tick 9212. See `tmp/scan-order-profile-validation.json`
and `tmp/scan-order-extended-validation.json`. Heavy A500 throughput improves
58.70→59.11 updates/s but still accumulates debt. These fixtures do not establish
full-register/CCR equivalence or coverage of every unexecuted collision path.

SCAN_HOIST=1 defaults on within experimental SIM60 after validation and
measurement on both CPUs. The scan loads the query radius and X/Z/Y into saved D4–D7
once. Candidate traversal writes only owner links at actor+$66, so query geometry
is unchanged throughout a scan. Signed wrapped radius addition, arithmetic shift,
absolute-difference overflow, candidate exclusions, every owner-link write and
last-hit return are unchanged. A type-7 query returns zero before traversal,
retaining the final raw active-list slot in A0 and clear-X return flags.
Nonpositive counts retain the old result/flags path; counts above 256 still
restore registers and use the native fallback before reading cached geometry.
Extra registers are saved/restored on every exit. The current positive-count
return explicitly restores A0 to the last raw list slot, including self and
excluded tails; native `$85f6` leaves that pointer unchanged. The cache-off/on
A500 and 68020 comparisons in `tmp/scan-slot-validation.json` each pass 507
calls, checking A0, D0 and all owner-link writes. Full-register/CCR equivalence
is not established by this fixture. Scan diagnostics remain gated by VERIFY. The existing 68-case fixture covers type-7 queries,
exclusions, signed boundaries, ordering, self entries and duplicate 256-entry lists.


`sim60-scan-hoist-twin-a500` and `sim60-scan-hoist-twin-020` each pass 15047
native comparisons, including all 68 cases, with zero mismatches/failing cases.
Gameplay plus fresh projection state matches the preceding baseline and both
CPUs at ticks 1500/3600. Native death/retry passes on both.
Replacement-only `sim60-scan-hoist-fast-a500` and `sim60-scan-hoist-fast-020`
retain DEATH_TEST=200 and use SLOW_DRAW=20 on the 68020. They match baseline and
cross-CPU state at 1500/2400/3600, including native retry. Exact matching listings
locate the update entries; complete game-entry scan costs include the hook jump.

| CPU | Scan before / after (calls) | Update before / after (calls) |
|---|---|---|
| 68000 | 2336.57 (116) / 2137.79 (116) | 107615.07 (28) / 106816.21 (28) |
| 68020 | 1094.23 (164) / 1024.45 (164) | 50253.44 (41) / 49971.02 (41) |

Scan cost falls 8.51%/6.38%; total update averages fall 0.74%/0.56%. Extra
register saves and query loads can cost more for short or heavily excluded
lists; these gains describe the measured route, not every possible scan.
`scan-cost.json` retains full samples and `throughput.json` observed intervals:

| CPU | Ticks | Fields | Updates/s | Presentations | Pending before / after |
|---|---|---|---|---|---|
| 68000 | 1500–2400 | 970 | 55.67 | 5 | 109 / 179 |
| 68000 | 2400–3600 | 1123 | 64.11 | 8 | 179 / 102 |
| 68020 | 1500–2400 | 914 | 59.08 | 25 | 13 / 27 |
| 68020 | 2400–3600 | 1202 | 59.90 | 35 | 27 / 29 |

The 68000 still presents only 0.31/0.43 times per second. Its second interval
pays backlog; neither interval proves sustained 60 Hz with acceptable rendering.
Default builds reproduce the measured binaries; normal legacy build restored.


## Word-input movement products

MOVE_WORD_MUL=1 defaults on within experimental SIM60 after native-reference
validation and measured savings on both CPUs.
At $86cc/$8712/$875a/$8786/$87ac both operands are sign-extended signed words:
actor speed and a sine/cosine sample (possibly negated as a word first). Native
$fa0c jumps to $24aa0, which computes the low 32 bits using three unsigned word
products. For these inputs that result equals one signed MULS.W D1,D0. Each
four-byte call becomes MULS.W / NOP. D1 and the other registers are unchanged;
the following arithmetic shifts overwrite multiply flags, including X, before
any flag consumer. Installer guards check each original call, speed-stack load
and D0 sign extension before patching.

The calls at $86ea/$8730 remain wide: a preceding speed/trig product can produce
+32768 after shifting, which would change sign if truncated to a word. The F761
fixture now compares 480 complete actor results, adding pitch $8000 over all
existing yaw/speed combinations to cover this intermediate boundary. For each
reference it restores the native flat-path condition and all five wide calls;
for each candidate it restores the optimized condition/products and flushes
instruction caches. The reader verifies all five sites are consistently native
or optimized afterward, and both wider intermediate sites retain native calls.
The preceding F760/384-case captures remain readable.

`sim60-move-word-twin-a500` and `sim60-move-word-twin-020` each pass all 480
movement, 48 boss and four collision cases, plus native death/retry. Gameplay
and fresh projection state match the preceding scan-optimized baseline and each
other at ticks 1500/3600. MOVE_WORD_MUL=0 reproduces both preceding baseline
binaries, and movement diagnostics remain byte-excluded outside VERIFY.
No simulation ABI field changes.

Replacement-only `sim60-move-word-fast-a500` and `sim60-move-word-fast-020`
use DEATH_TEST=200 and SLOW_DRAW=20 on the 68020. Mapped gameplay and fresh
projection state match the baseline and across CPUs at 1500/2400/3600. Native
retry passes on both. Exact binary/listing comparisons establish update-entry
offsets; complete-call costs at native movement entry $8682 include the SIM60
wrapper and exclude interrupts/partial calls:

| CPU | Movement before / after (calls) | Update before / after (calls) |
|---|---|---|
| 68000 | 3902.44 (174) / 3625.42 (178) | 106816.21 (28) / 105148.64 (28) |
| 68020 | 1824.31 (246) / 1664.60 (432) | 49971.02 (41) / 49035.07 (72) |

Movement window averages fall 7.10%/8.75%; update averages fall 1.56%/1.87%.
The sample counts differ because the fixed field windows include different
amounts of rendering/catch-up work. These are route-window averages, not a
claim of uniform savings across every movement input. Samples are retained in
`movement-cost.json` and observed intervals in `throughput.json`:

| CPU | Ticks | Fields | Updates/s | Presentations | Pending before / after |
|---|---|---|---|---|---|
| 68000 | 1500–2400 | 953 | 56.66 | 5 | 108 / 161 |
| 68000 | 2400–3600 | 1123 | 64.11 | 9 | 161 / 84 |
| 68020 | 1500–2400 | 885 | 61.02 | 24 | 36 / 21 |
| 68020 | 2400–3600 | 1200 | 60.00 | 35 | 21 / 21 |

The 68000 still presents only 0.31/0.48 times per second; above-sixty intervals
pay backlog. The delayed 68020's second interval holds its existing debt steady.
These measurements do not establish sustained performance across all encounters.
Default builds reproduce the measured binaries, and the normal legacy build
is restored afterward.


## Fractional record lookup cache

RECORD_CACHE=1 defaults on within experimental SIM60 after validation and
measurements on both CPUs.
It retains the existing 272-record table and deterministic first-free allocation.
Thirty-two cached record pointers use index `(actor >> 5) & 31` by default;
RECORD_CACHE_SLOTS=16 retains the earlier capacity. A hit requires the
record's current actor tag to equal the requested actor. Clearing/removing or
reusing a record invalidates that check without touching the cache. Reset clears
both the record table and all cache pointers. The record-table allocation lives
for the installed slave's lifetime; cached pointers never refer to separately
freed actor memory. Misses retain the full search past holes and original full-
table failure. Hashing uses ROR plus a word mask to preserve X; callers retain
the existing D0/A0 scratch and A6 result contract. No simulation ABI changes.

In `sim60-move-word-fast-*`, six distinct actors generate 297/721 record lookups.
A cold cache with this index predicts 291/715 hits; the prediction does not model
record invalidations and is not a measured implementation saving. Results are
retained in `record-inputs.json`; a simple last-record cache would hit only
89/216 times. The considered idle-rotation shortcut was rejected: only 60 of
179 sampled rotation groups have all-zero rates/remainders, making the extra
check unattractive relative to the remaining work.

VERIFY-only RECORD_COLLIDE forces index zero at both lookup and insertion,
exercising repeated collisions without altering the underlying record search.
Combined fixtures revealed pre-existing duplicate test execution after native
Continue resets ticks. Animation, special, flying, contact and pickup fixtures
now guard their completed count like the boss/collision fixtures, running once
per boot. Preliminary `record-cache-twin-a500` and `record-cache-collide-a500`
captures predate these guards and must not be treated as final fixture evidence.
The first also predates the ROR index correction. Use final captures below.
RECORD_CACHE=0 reproduces both preceding baseline binaries.

`sim60-record-cache-final-a500` (forced one-slot collisions) and
`sim60-record-cache-twin-020` (normal cache, SLOW_DRAW=20) pass 48 boss, four
collision, eight animation, twelve special, twelve flying, five contact and four
pickup cases each. Animation refresh/independence, collision watchdog/rollback,
504 pickup substeps/42 boundaries and native death/retry checks pass. Counts
remain correct through tick 3600 after retry. Gameplay plus fresh projection
state matches the baseline, normal-cache build and cross-CPU at 1500/3600.
These fixtures cover isolated actor effects; full encounters remain open.

Replacement-only `sim60-record-cache-fast-a500` and
`sim60-record-cache-fast-020` retain DEATH_TEST=200, with SLOW_DRAW=20 on the
68020. State matches the baseline and across CPUs at 1500/2400/3600, including
native retry. Exact binary/listing matches locate each measured entry:

| CPU | Record lookup before / after (calls) | Update before / after (calls) |
|---|---|---|
| 68000 | 314.48 (297) / 135.79 (300) | 105148.64 (28) / 103447.79 (29) |
| 68020 | 155.80 (721) / 64.21 (640) | 49035.07 (72) / 47993.64 (64) |

Lookup averages fall 56.82%/58.79%; update averages fall 1.62%/2.12%. The cache
adds overhead on misses and can be slower than a first-record hit in the old
search; these are measured route-window results, not universal savings. Samples
are retained in `record-cost.json`, observed intervals in `throughput.json`:

| CPU | Ticks | Fields | Updates/s | Presentations | Pending before / after |
|---|---|---|---|---|---|
| 68000 | 1500–2400 | 964 | 56.02 | 6 | 101 / 165 |
| 68000 | 2400–3600 | 1117 | 64.46 | 9 | 165 / 82 |
| 68020 | 1500–2400 | 883 | 61.16 | 24 | 32 / 15 |
| 68020 | 2400–3600 | 1196 | 60.20 | 35 | 15 / 11 |

The first 68000 interval now presents one additional frame, so its lower update
average does not contradict cheaper individual updates. Presentation remains
only 0.37/0.48 times per second; above-sixty intervals pay existing debt. Default
binaries match these measurements, diagnostics including forced cache collisions
are byte-excluded without VERIFY, and the normal legacy build is restored.

### Arithmetic cost audit

A separate audit of the four S60_DIV12 macro sites finds only 69/134 nonzero
numerators with magnitude below twelve. Their native divisions total
10838/6992 cycles, below 0.4% of the respective thirty/sixty-field captures even
if eliminated entirely. Guard and remainder-packing costs would reduce the
saving, so no small-numerator shortcut was added. The retained
`division-inputs.json` records site counts and costs. The existing zero shortcut
already removes zero-numerator divisions.

The current collision-order combat audit includes all executed slave DIVS #12
sites, not just the four original macros. A500/delayed-68020 execute 1828/1892
divisions. Nonzero numerators below twelve account for 177590/61190 cycles;
removing those divisions entirely would save at most 1.484%/0.256% of recorded
field cycles. Extending the bound to magnitudes below 24 gives 1.891%/0.326%,
still before replacement and guard costs. These bounds include capture-edge
partial calls and are not measured speedups (`tmp/current-arithmetic-budget.json`).

### Guarded heading replacement

`HEADING_FAST=1` defaults on within experimental SIM60 and replaces the complete eight-byte prologue at $893a with a
jump/NOP and retains a guarded trampoline to the original body. The native
arctangent-table pointer is captured from $89a4. The fast path handles unequal,
nonzero coordinate magnitudes whose maximum is at most 65535. Its numerator
is min*512, so a single DIVU gives a quotient below 512 without overflow.
Axes, equal magnitudes, wider values and wrapped abs(MIN_LONG) use the original
routine. Both paths preserve native D0/D1 and A0/A1 scratch results as well as
callee-saved registers. Guards leave D0/D1/A0/A1 untouched; only D2/D3
need saving. Original signs are read from argument bytes instead of extra flag
registers, and the two octant paths avoid direction bookkeeping. The fast path finishes with native ASL.W #4 after
restoring saved registers, preserving the final condition-code calculation.
No static branch targets the replaced prologue's interior.

H761 compares all fifteen register outputs for 4217 cases: an 11-by-11 matrix
covering signs, axes, equality and the 65535/65536 boundary, then every used
lookup-table index in all eight octants. It does not compare CCR directly or
claim arbitrary full-game encounter coverage. `sim60-heading-lean-twin-{a500,020}-1`
pass all cases, native death/Continue/retry, and mapped gameplay/projection
comparisons at 1500/3600 against each other and the preceding baseline. The
68020 adds twenty fields per render. ABI 26 adds the optional fixture offset
at entry+126; the eight-byte H761 result contains signature, case and error
words. Non-VERIFY binaries with/without HEADING_TEST and DEATH_TEST are identical.

Matched fixture-free captures `sim60-heading-lean-measure-{a500,020}-{0,1}`
retain exact binaries and listings. On the 68000, complete heading calls average
1063.04 (270 calls) to 614.97 cycles (279 calls); updates average 103447.79
(29 calls) to 99343.20 (30 calls), 3.97% lower. On the 68020, heading calls
average 494.65 (549 calls) to 246.93 (507 calls); updates average 48008.59
(61 calls) to 45723.64 (56 calls), 4.76% lower. Heading costs fall 42.15%/50.08%.
These are observed-window averages; inclusive heading/update costs are not
additive. All mapped gameplay/projection checkpoints at 1500/2400/3600 match
across options and CPUs, and native retry passes. Per-capture
`heading-lean-measure.json` contains counts, costs and observed-field intervals.
The disabled capture retains the original eight prologue bytes.

With the replacement on, the 68000 spans 935/1122 fields over 900/1200 updates,
57.75/64.17 updates/s, six/eleven presentations and pending debt 106/141/63.
The 68020 spans 896/1205 fields, 60.27/59.75 updates/s, 25/36 presentations
and debt 26/22/27. Above-sixty intervals pay backlog; these do not establish
sustained throughput. Default builds match the exact explicitly enabled builds
used for measurement on both CPUs. HEADING_FAST=0 retains the original game
entry bytes; normal development builds still use the legacy timing prototype.

### First projectile collision scan

`SHOT_FAST=1` defaults on within experimental SIM60 and replaces $34d6's
complete eight-byte prologue. Its two static callers are $3266 and $3344;
no static branch targets the overwritten interior. The guarded trampoline
retains native behavior for positive counts above 256. Nonpositive counts
return zero without changing incoming A0 or X. The ordinary path traverses
the same active-list order and inlines native $85f6 geometry: categories
$fc/$fd and type-7 actors are excluded, radius addition/ASR and signed coordinate
wrapping are preserved, and overlap boundaries are inclusive. Unlike $3a54,
self is not excluded, first eligible hit wins, and no owner links are written.
The projectile's owner at +$6a is excluded only after the overlap test, retaining
native scratch A0 even when the last overlapping actor is the owner.

Query geometry is constant within this read-only scan, so it is loaded once.
The candidate-minus-query subtraction order preserves native X on successful
hits; a positive-length miss explicitly clears X like the native index increment.
D1 and all saved registers remain unchanged. A type-7 query skips the predicates
but returns the native last-list-entry A0. The native predicate entry is guarded
alongside the replaced prologue. SHOT_FAST=0 retains the original eight bytes.

Q760 compares all fifteen register outputs across 64 configurations: counts
0/1/4/256, first-hit/owner/duplicate ordering, self, query/candidate type 7,
category exclusions, final-only hits, odd-radius inclusive edges, misses,
negative/wrapped radius sums and MIN_LONG differences on each axis. It does
not directly capture flags or validate a full projectile encounter. Both
`sim60-shot-probe-a500` and `sim60-shot-twin-020-1` pass, including native
DEATH_TEST/Continue/retry and mapped gameplay/projection agreement through
1500/3600 against the preceding heading baseline. ABI 27 adds the optional
result offset at entry+128; its eight bytes contain Q760, cases.w and errors.w.
Fixture flags have no effect on non-VERIFY binaries.

Matched fixture-free `sim60-shot-measure-{a500,020}-{0,1}` captures retain
exact listings and binaries. On the 68000, complete scan means fall from
4839.81 (62 calls) to 2200.58 cycles (66 calls), 54.53%; complete updates fall
99343.20 (30 calls) to 94297.69 (32 calls), 5.08%. On the 68020, scans fall
2244.00 to 1039.39 (112 calls each), 53.68%; updates fall 45685.64 (56 calls)
to 43275.95 (55 calls), 5.27%. These are window averages; inclusive scan and
update costs must not be added. All mapped gameplay/projection checkpoints
1500/2400/3600 match across options and CPUs, and native retry passes.
Per-capture `shot-measure.json` holds costs and observed-field intervals.

With the replacement enabled, A500 intervals span 906/1164 fields over
900/1200 updates: 59.60/61.86 updates/s, six/thirteen presentations, and
pending debt 97/103/67. The delayed 68020 spans 888/1208 fields:
60.81/59.60 updates/s, 25/36 presentations, and debt 24/12/20. Later catch-up
does not establish sustained throughput or a maximum presentation delay.
Default binaries match the explicitly enabled measurement builds on both CPUs.

The separate recentering routine $3ab8 remains per-tick physics: it subtracts
player X/Z from active actors, applies native world wrapping and clears the
player origin. Moving it into presentation would change gameplay coordinates.

### Longer default-build timing and damage route

`sim60-long-a500`, `sim60-long-slow-a500` and `sim60-long-slow-020` retain the
same default binaries proven by the projectile-scan measurements. Slow runs
add twenty display fields per render. Each boots through DEATH_TEST=200 and
native Continue, then runs the existing movement/firing input route to tick
10800. The measured interval starts at tick 3600, after the first simulated
minute, and covers a further 7200 ticks. All captures remain active in session
2 on level 0, with nine mapped objects at the five sampled boundaries.

| Configuration | Fields, ticks 3600–10800 | Updates/s | Presentations | Pending ticks, start/end |
|---|---:|---:|---:|---:|
| A500, normal rendering | 7188 | 60.1002 | 90 | 67 / 55 |
| A500, twenty extra fields/render | 7208 | 59.9334 | 40 | 159 / 167 |
| 68020, twenty extra fields/render | 7201 | 59.9917 | 219 | 20 / 21 |

Mapped gameplay plus simulation-written projection fields match at ticks
3600, 5400, 7200, 9000 and 10800 across all three configurations. Natural
energy values are 680, 480, 264, 264 and 144 respectively; this extends the
comparison through actual damage during gameplay. The native retry validator
passes, and observed session/clock origins remain unchanged over each interval.
No later natural death or level transition occurs in this range. Results are
retained in each capture's `long-run.json` and `tmp/long-run-summary.json`.

The four 1800-tick interval rates are 58.03/60.81/62.65/59.11 Hz on normal
A500, 58.63/60.50/63.12/57.75 Hz on delayed A500, and
59.93/59.77/60.61/59.67 Hz on delayed 68020. Sampled debt ranges are
28–128, 97–201 and 11–29 ticks. These ranges do not bound peaks between
samples. Aggregate presentation rates are 0.7513/0.3330/1.8247 per second;
state-only captures do not establish maximum inter-presentation delay.
The near-sixty aggregate rates and matching damage/motion state support this
route's render independence, including a same-CPU comparison. They do not
prove full-machine equivalence, a heavier-scene budget or maximum input latency.

### Zero-forward-speed movement

MOVE_ZERO defaults on within experimental SIM60. The level-1 baseline profile contains 325
zero-forward-speed calls among 520 native movement calls. Their native bodies
consume 325582 cycles over sixty fields, averaging 1001.79 cycles each before
prologue/epilogue. Zero forward speed does not imply an idle actor: rotations
and three independent linear velocity terms still need integration.

The shortcut branches inside s60_move after boss speed preparation, while all
caller registers are saved. With forward-speed word $40 equal to zero,
s60_move_zero reproduces native rotations $868e..$86a2 and linear additions
$87c4..$87de. Only products whose forward-speed operand is zero are omitted.
The ordinary division/remainder and rollback path is unchanged, as is the
second native projection used by accelerating type-7 actors. Nonzero speeds
still call native movement. The shortcut's scratch registers differ from the
native routine, so it is only used inside the register-saving wrapper.

`sim60-move-zero-twin-a500` and `sim60-move-zero-twin-020` pass 480 native
full-actor comparisons (F762), including 80 zero-speed shortcut cases with
angle/position wrap and signed extreme linear terms. Both also pass 52 boss
cases, four collision/separation/rollback cases and native death/Continue/retry.
Mapped gameplay and projection match the preceding build and across CPUs at
resumed ticks 1500/3600. The 68020 adds twenty fields per render. With MOVE_ZERO=0,
`tmp/move-zero-disabled.slave` is byte-identical to the retained level-profile
baseline. Non-VERIFY builds with and without fixture flags are byte-identical
(`tmp/move-zero-nonverify-{0,1}.slave`).

Matched measurements use `sim60-move-zero-measure-a500` against
`sim60-level-profile-a500` at tick 1500 and `sim60-move-zero-measure-020`
against `sim60-level-fire-020` at tick 3700, all with SLOW_DRAW=20 and native
level transition. Baseline/candidate listings and binaries are
`tmp/level-profile.{lst,slave}` and `tmp/move-zero-measure.{lst,slave}`.
Mapped gameplay/projection match at each anchor and final checkpoint
(3600 on A500, 4200 on 68020). Level reset and generic-AI cadence pass;
the 68020 still creates the observed type-8 shot with the correct owner.

| Complete-call mean | A500 baseline → enabled | 68020 baseline → enabled |
|---|---:|---:|
| Movement | 3017.24 → 2470.41 (18.12% lower) | 1603.76 → 1350.36 (15.80% lower) |
| Update | 96849.75 → 92420.93 (4.57% lower) | 42694.31 → 41183.80 (3.54% lower) |

Sample counts are 520/546 movement and 64/67 updates on A500; 431/426 movement
and 65/64 updates on 68020. These are complete-call window averages, not paired
identical instruction sequences or additive exclusive costs. A500 ticks
1500–3600 consume 2093→2074 fields, draw 13→15 times, and change pending ticks
124→117 versus 120→94. Rates are 60.20→60.75 updates/s while catching up.
The shorter 68020 interval 3700–4200 consumes 501→511 fields, draws 17→18
times, and changes pending ticks 25→26 versus 16→27. Rates are 59.88→58.71;
no whole-interval throughput gain is claimed there. Routine savings support
enabling the shortcut on both CPUs; neither window proves sustained sixty-Hz
performance or acceptable maximum presentation latency. Full results are in
`move-zero-measure.json` per candidate capture and `tmp/move-zero-summary.json`.
Default compilation reproduces the measured enabled binary.

### Later-level update and presentation gaps

A retained N=12 A500 reference build is profiled in
`sim60-latency-level5-a500`: LEVEL_TEST=200, LEVEL_LAST=5, no SLOW_DRAW,
100 fields starting after the tick-600 snapshot. The retained slave matches
`tmp/latency-level5-a500.{lst,slave}` and the starting gameplay/projection
matches `sim60-exit-normal-level5`. There are 106 observed completion markers,
but only 105 fully observed update calls; boundary partials are excluded from
routine averages. Catch-up produces 63.6 completions/s in this short window,
which is not a sustained-rate claim.

Complete updates average 80302.90 cycles (105 samples), movement 2409.38
(763), motion-record lookup 120.18 (1315), simulation projection 9579.03
(105), stars 1794.43 (106), and sort 4862.11 (106). These costs are inclusive
and not additive. One complete rendering call consumes 1168400 main-task
cycles. Interrupt contexts occupy roughly 18.9% of the full window including
interrupt entry; their cost is excluded from complete-call routine figures.
Movement and collision scanning remain major simulation targets. The native
and slave inclusive profile identifies 742 collision-scan calls averaging
approximately 1859 cycles; use complete-call measurement before changing it.

`tools/simulation_latency.py` measures trace-observed update starts and native
presentation entries at field resolution. The A500's largest complete update
start gap is 15 fields, or between 233 and 267 ms accounting for endpoint
position within fields. Its one complete render phase also spans 15 fields.
Only one presentation occurs, in field 99: the first 99 full fields have no
presentation, but the capture contains no complete inter-presentation pair.
This directly demonstrates a responsiveness limitation of the cooperative
loop even though its catch-up update count exceeds sixty per second.

For comparison, retained `sim60-level5-slow-020` with SLOW_DRAW=20 has a
27-field update-start gap (433–467 ms), one complete six-field render phase,
and one presentation. Its complete update mean is 43984.47 cycles (51);
one complete render costs 968015 cycles and a second is truncated. The
artificial wait is outside s60_render but included in the update gap. This
is a different machine and a different instruction window, not a paired
optimization measurement. Results are retained as `latency.json` and
`latency-costs.json` in both captures. Presentation marker fields agree with
the existing frame reports. Empty/single-event and repeated-same-field
interval checks pass; boundary gaps remain lower bounds, not whole-game
maxima. No game logic changes are made by this measurement tool.

### Fully stationary movement

MOVE_IDLE defaults on within experimental SIM60. Set MOVE_IDLE=0 for the
preceding integration path. In the level-5 A500 opportunity trace, 424 of
763 movement calls have zero forward speed, all six velocity words and all
six motion remainder words zero, and ordinary non-type-7 movement. The
existing MOVE_ZERO shortcut alone still performs their integration work.

The guard follows the usual position, original rotation and remainder
backups. It checks speed, three longwords spanning the six velocity words,
three longwords spanning the six remainders, and excludes type 7. On success
it clears displacement longs +20/+24/+28 and X, then uses the common register
restore. Every nonzero case retains the existing path. This preserves stale
rollback replacement even when the actor does not move. Type 7 retains its
acceleration/vector bookkeeping. The shortcut adds seventy bytes.

VERIFY-only IDLE_TEST compares the entire movement wrapper with the existing
integration path selected by a fixture-only gate. It restores the full actor
and 144-byte motion record between calls, then compares every word and all
five CCR bits. Its 64 cases cover incoming flags, stale rollback/snapshot
contents, each velocity word and remainder (including out-of-normal-range
magnitudes), nonzero forward speed and type-7 fallback. Fixture records are
cleared afterward. Gameplay ABI remains 28; tools/idle_state.py locates I760
results through the exact build listing and requires its matching slave.

`sim60-idle-twin-a500` and `sim60-idle-twin-020` pass all 64 cases and match
gameplay/projection at tick 150. The isolated negative control changes only
ADD.W D0,D0 to NOP. `sim60-idle-negative-a500` then reports eight expected
CCR errors while actor and record comparisons still pass. Exact listings and
binaries are `tmp/idle-twin.{lst,slave}` and `tmp/idle-negative.{lst,slave}`;
results are `idle-validation.json` in each capture.

`sim60-idle-regression-a500` and `sim60-idle-regression-020` additionally pass
480 native movement comparisons, 52 boss cases, four native collision/rollback
cases and native death/Continue/retry. Both include IDLE_TEST. The 68020 adds
twenty fields per render. Gameplay and projection match the preceding build
and each other at resumed ticks 1500/3600. Results are `idle-regression.json`
per capture and `tmp/idle-regression-summary.json`. These fixtures do not
replace full encounter coverage.

Matched measurements use current code with only MOVE_IDLE changed. A500
baseline is `sim60-latency-level5-a500`, with `sim60-exit-normal-level5` for
later checkpoints; 68020 baseline is `sim60-idle-baseline-020`. Candidates
are `sim60-idle-corrected-a500` and `sim60-idle-corrected-020`. All request
five native level transitions and profile at final-session tick 600 (100
fields A500, 60 fields 68020). The 68020 adds twenty fields per render.
Each baseline/candidate matches gameplay/projection at 600/1500/3600, with
all five resets passing. Corrected candidates also match each other.

| Complete-call mean, cycles | A500 baseline → enabled | 68020 baseline → enabled |
|---|---:|---:|
| Update | 80302.90 → 76928.84 (4.20% lower) | 44001.92 → 42654.22 (3.06% lower) |
| Movement | 2409.38 → 1946.68 (19.20% lower) | 1280.01 → 1021.93 (20.16% lower) |

Update sample counts are 105/110 on A500 and 51/41 on 68020. Movement samples
are 763/798 and 386/323. These are inclusive window averages, not paired
identical calls or additive costs. Across 3000 ticks, A500 consumes
2910→2927 fields, presents 72→83 times, and changes backlog 118→28 versus
99→26. The 68020 consumes 2995→3018 fields, presents 102→104 times, and
changes backlog 21→16 versus 9→27. Different catch-up phases prevent treating
these intervals as universal throughput gains. The one observed A500 render
still spans 15 fields; this shortcut reduces update work, not that render
pause. Full results are `idle-comparison.json`, `latency-costs.json` and
`latency.json` in the measurement captures. Exact listings/binaries are
`tmp/latency-level5-a500`, `tmp/idle-baseline-020`, and
`tmp/idle-corrected-{a500,020}` with `.lst`/`.slave` extensions.

Non-VERIFY builds with/without IDLE_TEST are byte-identical
(`tmp/idle-nonverify-{0,1}.slave`). With the fixture absent, the corrected
measurement binary is unchanged by adding its source. MOVE_IDLE=0 is
byte-identical to the preceding default A500 measurement. Default-on builds
are checked against the measured enabled binaries; the normal non-VERIFY
slave still uses the legacy timing prototype until the full SIM60 goal is
validated for normal play.


## Heavy type-10 combat cost and cache capacity

`sim60-type10-heavy-a500` captures 100 fields at tick 1800 with the unchanged
combat build. Its mapped gameplay/projection matches the prior A500 combat
checkpoint, and its retained binary matches `tmp/type10-shared-env.slave`.
The new shared-toolchain build is byte-identical to the preceding capture.

There are 83 completed simulation steps and no presentation in this window.
The complete-call cost instrument observes 82 full update calls, averaging
119867.20 cycles (median 119397). Thus this scene can fall behind even without
render work in the measured window. Mean movement cost is 2532.05 cycles over
914 calls; record lookup is 303.20 cycles over 1582 calls (median 120), and
simulation projection averages 12598.10 cycles over 83 complete calls. These
inclusive costs overlap and must not be summed. Full measurements are in
`latency-costs.json` and `latency.json` in the capture.

The earlier tick-1200 trace has 291 complete zero-speed helper calls: 97 have
nonzero angular quanta, and 194 have zero angular/linear quanta. This does not
inspect pending position fractions and does not prove an idle shortcut safe.
No rotation-only shortcut was added. `tmp/rotation-opportunity.json` retains
that audit. In the heavier window, 329 of 416 complete native movement calls
repeat the previous input for their actor; a four-entry global FIFO gets only
16 hits. Any vector-cache proposal needs its own equivalence and cost checks.

A cold replay of the actual record-lookup actor sequence gives 506 misses with
16 slots and 176 with 32 or 64 slots in the heavy window. At tick 1200 it gives
57 versus 9; the earlier level-6 and level-5 windows are unchanged. These are
lookup-distribution models, not measured cycle savings; they do not model
record invalidation or allocation changes from a larger binary. Results are in
`tmp/record-cache-capacity.json`. Changing address-bit selection alone did not
improve the heavy trace materially without regressing other inspected traces.

RECORD_CACHE_SLOTS defaults to 32 after validation on both CPUs; 16 retains
the baseline. It changes only cache allocation size, clearing count and both
index masks; tag checks and full-table fallback are unchanged. It adds 64 bytes
without adding per-lookup instructions. `tmp/cache_capacity_runs.py` uses the
shared makefile for exact binaries/listings and captures at 1800/2400.

Candidate A500 and baseline/candidate delayed 68020 match original combat
mapped gameplay/projection at both ticks, with every one of the six archived
resets passing. The two CPUs share the same gameplay states. Completed-call
mean costs in the hundred-field heavy windows are:

| Routine | A500, 16 → 32 slots | 68020, 16 → 32 slots |
|---|---:|---:|
| Update | 119867.20 → 117479.52 (1.99% lower) | 63315.65 → 61994.28 (2.09% lower) |
| Record lookup | 303.20 → 176.17 (41.90% lower) | 160.88 → 92.54 (42.48% lower) |

Update sample counts are 82/84 on A500 and 88/89 on 68020; lookup counts are
1582/1615 and 1683/1698. These are window averages, not paired identical calls.
Neither A500 trace renders during its hundred fields. The change is retained
despite its modest overall gain because it adds no lookup instructions and
requires only 64 bytes. It does not resolve the A500 performance shortfall.

Across ticks 1800–2400, A500 uses 626→619 fields and two presentations in each
run; debt changes 223→249 versus 211→230. Delayed 68020 uses 600→597 fields
and eighteen presentations in each, with debt 22→22 versus 14→11. Clock-phase
and actor-population changes prevent generalizing these short intervals into
whole-game throughput claims. Cache allocation can change heap layout, which
is why the lookup replay alone was insufficient validation.

Exact listings/binaries are `tmp/cache32-combat-a500` and
`tmp/cache{16,32}-combat-slow-020`, with `.lst`/`.slave` extensions. A500
baseline is `sim60-type10-heavy-a500` with `tmp/type10-shared-env.{lst,slave}`;
its later timing boundary is the matching original combat run.
`tmp/validate_cache_capacity.py` writes `cache-validation.json` per capture and
`tmp/cache-capacity-validation-3.json`. Complete cost/latency reports accompany
each trace; `tmp/cache-capacity-comparison.json` contains the paired summary.

Default-on builds are byte-identical to the measured 32-slot candidates.
Explicit 16-slot builds remain byte-identical to the preceding baseline.
Non-VERIFY SIM60 builds with/without the combat diagnostic flags match exactly
(`tmp/cache32-nonverify-{0,1}.slave`, 15264-byte hunk files). The normal slave
remains the legacy-loop build and has been restored after validation.

## Guarded simulation callback pass (experimental)

PROJECT_BATCH defaults to one within experimental SIM60. When enabled, `project_batch60.s` replaces
simulation projection only after checking the complete world list. The game
must be running outside rendering, native pre/post-list callbacks must be
null, count must be 1..256, and every non-view actor must have visibility bit 3
clear and either no callback or native mesh animation at $42b0. Any rejection
returns to native $12aa4 before executing a callback. Accepted lists preserve
actor/index order and call the installed animation clock at $42b0. The view
actor is skipped. Native mesh drawing already has no simulation side effects.
The native animation routine updates actor counters and mesh-frame bytes;
it does not consume projection scratch or change world-list membership.

This is stronger separation than PROJECT_SKIP: accepted passes deliberately
leave derived shared geometry scratch stale. They cannot skip an actor whose
visibility/projected coordinates require updating. Rendering calls native
camera preparation $12920 before background drawing, then retains the native
actor projection pass. Existing animation suppression during rendering and
restoration of gameplay RNG remain active. The direct-reference scratch audit
is not a complete proof against indirect consumers; native fallback and visual
checks below support enabling this guarded option within experimental SIM60;
broader game coverage remains part of the full-goal validation.

`sim60-project-batch-combat-a500` uses the current 32-slot-cache combat route,
with exact `tmp/project-batch-combat-a500.{lst,slave}`. Mapped gameplay and
fresh actor projection match `sim60-cache32-combat-a500` at ticks 1800/2400,
and all six archived resets pass. Shared `projection_scratch` is the only
mapped difference. The trace audit observes 92 accepted passes, 92 correctly
ordered animation callbacks and no fallback. This validates the observed
eligible scene, not the guard's rejected cases. Enemy AI cadence checks pass.

Complete updates average 108110.68 cycles (91 samples), versus 117479.52
(84) in the cache32 baseline: 7.98% lower. Projection averages 3242.70 cycles
(92 samples). Costs are inclusive window averages, not paired identical calls
or additive totals. The hundred-field candidate window has 92 update starts
and no presentation, so even this reduction does not establish sustained
60 Hz simulation with rendering. Across ticks 1800–2400, the candidate uses
588 fields, presents three times and reduces debt 163→151; the baseline uses
619 fields, presents twice and increases debt 211→230. Different scheduling
phases limit interpretation of these short intervals.

`tmp/validate_project_batch.py` retains state/reset comparisons and checks
that every observed accepted pass completes its preflight and calls exactly
the eligible callbacks in index order. It writes `project-batch-validation.json`
inside each capture. Complete cost and latency reports use the existing exact
listing instruments. Full-pass native twins cover the cases below; held rendering and level-5
cross-render checks are documented in the following sections. The existing J762
per-actor fixture does not cover this whole-list replacement.

The delayed 68020 candidate `sim60-project-batch-combat-slow-020` also matches
its cache32 baseline and the A500 candidate for gameplay/fresh actor projection
at both ticks, with all six resets passing. Its 96 accepted passes execute 96
callbacks in the expected order, with no fallback. AI cadence checks pass.
Mean update cost falls 61994.28→57298.88 cycles (7.57%, 89→95 complete calls).
Three complete render calls average 788055 cycles; this includes the added
camera preparation. Across 600 ticks it uses 585 fields, presents eighteen
times and reduces debt 22→7. Above-sixty throughput here pays existing debt;
it is not a change to the target timestep. Exact listing and binary are
`tmp/project-batch-combat-slow-020.{lst,slave}`. The normal slave is restored.
Both combat captures exercise eligible lists only; rejected cases are covered
by the full-pass native fixtures below.

### Whole-pass projection fixture

VERIFY-only BATCH_TEST uses private actors, frame arrays and preseeded motion
records. It saves/restores the full world list/count, both list hooks, camera
and projection scratch, motion-table pointer and cache, and simulation modes.
Both sides temporarily return at the native mesh entry; its original word and
instruction cache are restored before gameplay continues. This suppresses
rasterization without replacing camera preparation, projection, visibility,
callbacks or the installed animation clocks. The reader checks the restored
mesh instruction and original motion-table pointer in the resumed snapshot.

Each of 64 cases resets identical state, runs native $12aa4, resets again and
runs the actual `s60_project` entry. Comparisons cover all private actor bytes,
mesh-frame bytes, callback observations and motion records. Fallback cases
also compare all 178 bytes of camera/projection scratch. A VERIFY-only marker
checks actual acceptance/rejection against the case's independent expectation.
Cases combine sixteen scenarios with callback-before/after-mesh ordering and
fresh/already-current animation clocks. Scenarios include null/animation and
unknown scratch-reading callbacks, first/last visibility actors, pre/post-list
hooks, counts 0/1/2/3/256, duplicate actors, view-only/final-view lists, and
inactive/rendering states. Out-of-range malformed lists are not exercised.

`sim60-batch-twin-a500` disables PROJECT_SKIP for full native geometry;
`sim60-batch-twin-020` retains it to test composition and adds twenty fields
per render. Both pass all 64 Q760 cases with no actor, record, scratch or path
errors, busy zero and successful restoration checks. At resumed tick 150,
gameplay and fresh actor projection match across CPUs. Shared drawing scratch
can differ because PROJECT_BATCH intentionally defers it between presentations.
Exact listings and binaries are `tmp/batch-twin-{a500,020}.{lst,slave}`.

VERIFY-only BATCH_BAD_VISIBILITY removes just the new visibility guard.
`sim60-batch-negative-a500` produces eight actor errors, eight scratch errors
and eight path errors, with zero record errors and restored state. This confirms
that the fixture detects the missing guard instead of merely accepting both
implementations. The exact negative build is `tmp/batch-negative-a500.{lst,slave}`.
The native twins suppress mesh drawing and therefore do not prove final-image
equivalence. The option remains disabled pending that check and broader scenes.

Both positive fixtures also match the fixture-free PROJECT_BATCH=0 baseline
`sim60-batch-baseline-a500` at tick 150 for mapped gameplay and fresh actor
projection. Results are in `batch-validation.json` per capture and
`tmp/batch-twin-validation.json`. Rebuilding the original enabled combat flags
without BATCH_TEST remains byte-identical to the measured candidate. Non-VERIFY
SIM60/PROJECT_BATCH builds with and without both diagnostic flags are identical
(`tmp/batch-nonverify-{0,1}.slave`); the normal legacy slave is restored.

### Matched-tick images expose a remaining render clock

FRAME_TEST=1800 draws the actual combat state once after that completed tick,
then holds gameplay with display interrupts running. `tools/frame_state.py`
requires the exact binary/listing, one native presentation, the post-render hold
loop and at least twenty settled fields whose entire RGBA images are identical.
This diagnostic is not used for performance claims. The profile begins at a
field boundary and can omit the render entry, but presentation and hold must
both be observed. Images and verification reports remain inside each capture.

`sim60-frame-native-a500`, `sim60-frame-batch-a500` and
`sim60-frame-batch-slow-020` all match mapped gameplay/fresh actor projection at
1800 and pass all six archived resets. They retain 86/86/94 identical settled
fields respectively. Exact builds are `tmp/frame-native-a500`,
`tmp/frame-batch-a500` and `tmp/frame-batch-slow-020`, with `.lst`/`.slave`
extensions. The normal build is restored after the captures.

Their full images do **not** match. The A500 candidate differs in 1797 pixels:
903 in the moving cockpit indicator and 894 in a three-pixel strip at the far
right. The delayed 68020 differs in 71764 pixels, including the indicator and a
large bottom-border region. The border causes are not yet established; no crop
or mask is used to claim equivalence. Results are in
`tmp/frame-batch-comparison.json`; each capture retains `settled.png` and
`frame-validation.json` for its local stability check.

In the HUD_CLOCK=0 baseline, native $c35a draws the cockpit panel. When data $1e72 exceeds 50, instructions
$c3ba..$c3e4 update a bouncing indicator: data $1f5c is its position and $1f5e
its signed step. Positions below 132 select +4; positions above 176 select -4;
then the step is added as a word. This occurs on every rendering call, so the
indicator's phase depends on prior render count. Pre-render position/step pairs
are 154/-4, 166/+4 and 134/-4 in the three captures. The sprite at $c402 uses
the resulting position. The differing indicator is therefore a real render-rate
dependency that the earlier mapped gameplay comparison omitted.

`simulation_state.py --presentation` now includes these two words explicitly.
Its default still compares mapped gameplay; earlier gameplay-equality results
must not be read as full visual or full-memory equivalence. HUD_CLOCK now moves this animation off the render clock as described below.
The host-border differences are addressed by the guarded lossless display-DMA comparison below. PROJECT_BATCH now defaults on within experimental SIM60 after the checks below.

### Simulation-owned cockpit indicator

HUD_CLOCK defaults on within experimental SIM60; zero retains the former path.
Installation checks every instruction and relocated operand in $c3ba..$c3e9,
copies those 48 bytes into a callable native-arithmetic body, and replaces only
the complete six-byte entry instruction. All copied relative branches remain
inside that body. The active render hook continues at $c3ea without advancing
the indicator. Inactive callers execute the native arithmetic before continuing.

The simulation update requires active gameplay, no rendering and signed data
$1e72 > 50. First activation is immediate; subsequent changes require twelve
completed simulation ticks. Unsigned tick subtraction handles wrapping. Hidden
indicators clear clock validity, so reappearance is immediate. New gameplay
sessions reset only this private clock; native position/step state is retained.
Rendering never consumes a clock step. The HU60 header at the installed hook
exposes last-tick/validity for `simulation_state.py --presentation`, alongside
position/step, without changing the main capture ABI.

HUD_TEST temporarily returns at $c3ea to exercise the actual installed render
hook without rasterization. It compares against the native arithmetic body at
reference twelve-tick boundaries across 64 cases and 2304 substeps. Cases cover
signed extreme positions/steps, bounds 132/176, zero steps, threshold 50/51,
tick wrap, duplicate calls, repeated rendering, inactive callers and immediate
reappearance. It restores the native continuation, private clock, game words,
modes and simulation tick before returning.

`sim60-hud-twin-a500` and `sim60-hud-twin-slow-020` pass all checks with zero
errors: 2304 substeps/render checks and 64 inactive/reappearance checks each.
They also match fixture-free `sim60-hud-boot-a500` for gameplay, indicator phase
and private clock at tick 150. Exact builds are `tmp/hud-twin-a500`,
`tmp/hud-twin-slow-020` and `tmp/hud-boot-a500`, with `.lst`/`.slave` extensions.
VERIFY-only HUD_BAD_RENDER deliberately lets rendering advance the indicator;
`sim60-hud-negative-a500` then reports 6174 errors, demonstrating that the
fixture detects the original dependency. Results are retained in
`hud-validation.json` per fixture capture and `tmp/hud-twin-validation.json`.

The image reader now reports the source encoding: multi-field profiler captures
contain JPEG, so equality concerns decoded recorded images, not a lossless
framebuffer. `settled.png` is a PNG encoding of those decoded pixels. Upstream
[Barto screenshot code](https://github.com/grahambates/fs-uae/blob/remote_debugger_barto/src/barto_gdbserver.cpp)
exports the entire frame buffer; its
[video backend](https://github.com/grahambates/fs-uae/blob/remote_debugger_barto/src/od-fs/fsvideo.cpp)
allocates that buffer with malloc and separately tracks display limits. This
supports a capture-buffer explanation for edge differences, but does not yet
establish exact valid bounds for the local binary. No masking is used to claim
full-image equivalence.

The HUD-fixed heavy-combat images are `sim60-hud-frame-native-a500`,
`sim60-hud-frame-batch-a500` and `sim60-hud-frame-batch-slow-020`, with exact
`tmp/hud-frame-{native-a500,batch-a500,batch-slow-020}.{lst,slave}` builds.
All match gameplay, HUD position/step 138/+4 and private clock 1788/valid at
tick 1800, with all six archived reset checks passing. They have 87/86/94
stable recorded fields. Every decoded pixel in the visually identified game
rectangle (74,46)–(714,446) matches; the former indicator discrepancy is gone.

Full recorded images still differ by 74511/71840 pixels against the native
projection baseline. All differences are confined to x>=744 or y>=472; this
is a localization observation, not proof that those bounds define valid local
video output. `tmp/hud-frame-comparison.json` preserves both the full-image
failures and the scoped rectangle counts. Lossless guest display-buffer checks
or verified local output bounds are still needed before claiming full rendering
equivalence. None of these held-display captures measures throughput.

HUD_CLOCK=0 reproduces the prior enabled-PROJECT_BATCH combat binary exactly.
Non-VERIFY SIM60 builds with and without HUD_TEST/HUD_BAD_RENDER/FRAME_TEST are
byte-identical (`tmp/hud-nonverify-{0,1}.slave`). The HUD code adds 410 bytes to
that non-VERIFY build. The normal legacy slave is restored. Earlier cycle
measurements predate HUD_CLOCK and are not measurements of this new default.

### Lossless guest-display verification

`tools/display_dma.py` uses the existing held-frame traces rather than host
screenshots. The packed 58-byte DMA record exposes register, fetched value,
transfer size, bus owner, conflict and beam slot. The 520-byte full custom-state
record begins with a chipset mask and register words at offset 4; the parser
also retains AGA palette snapshots. These layouts follow the upstream
[DMA record definition](https://github.com/grahambates/fs-uae/blob/remote_debugger_barto/src/include/debug.h)
and [custom-state/color implementation](https://github.com/grahambates/fs-uae/blob/remote_debugger_barto/src/custom.cpp).

The checker requires exactly four low-resolution planes, twenty fetched words
per plane on each of lines 44–243, zero scrolling, no sprites, no conflicting
transactions, and no CPU display writes. It guards display modes/limits and
checks AGA palette values against the corresponding OCS-compatible colors.
Every fetched word and beam position contributes to a lossless digest together
with effective palette/control state. All control writes and background-color
write timings are preserved. Other palette writes before the first fetch are
represented by the effective palette: the checker verifies that those fetches
precede horizontal display start, so these early non-background colors cannot
affect visible pixels. Later palette-write timings remain exact.

This distinction matters on the 68020: two non-background palette writes occur
two bus slots later before any pixel fetch, while the effective displayed colors
match. Copper instruction-fetch scheduling and allocation addresses are not
compared as pixel values. Unsupported display modes fail instead of being
silently normalized. The checker makes no claim about host screenshot padding.

The three HUD-fixed combat captures match all 16000 fetched words and effective
display state per field across 87/86/94 settled fields. Their bitplane digest is
`bef73e36daf6d703ea5c6b54b28b084b1153b3cfc1889ba11e18a205096bbd98`; effective
display digest is `e38776ed669ac911c7a34f813c2906303bbc8e91803dca812e8203347d4b0138`.
Reports are `display-dma.json` in each capture. This establishes lossless equality
of the guarded guest display for this scene despite differing host-image edges.
It does not generalize to untested game scenes or other display modes.

The same checker detects different raw bitplane/display digests in the two
pre-HUD-fix captures, where the actual cockpit indicator differed. Additional
negative controls detect a changed fetched pixel word and palette word, reject
an unsupported plane mode, and reject a changed AGA low color nibble. Results
are in `tmp/display-dma-negative-controls.json`. Existing trace-report tests
also pass after retaining AGA palette data. No emulator run was needed for
these checks; the recorded DMA already contained the lossless evidence.

The current HUD-enabled level-index-5 comparison uses PROJECT_BATCH=0/1
through ticks 600/1500/3600. Captures `sim60-batch-level5-baseline-a500` and
`sim60-batch-level5-a500` match mapped gameplay, HUD position/step/clock, and
fresh actor projection at every checkpoint; only deferred shared projection
scratch differs. All five requested native level transitions pass reset checks.
Each trace is paired with its exact retained slave and listing.

In their hundred-field windows, complete A500 update means are 77214.92 cycles
(109 calls) versus 70237.30 (120), a 9.04% reduction. Projection means are
9585.44 versus 2758.25 cycles. These are observed windows with different numbers
of updates, not paired per-tick samples. Both contain one complete render and
one presentation, insufficient to measure a complete presentation-to-presentation
gap. The largest complete update gaps are 15 versus 14 fields, respectively;
rendering still blocks simulation for roughly a quarter of a second.

Over ticks 600–3600, baseline fields/presentations/debt are 2926/84/98→24;
the candidate records 2938/119/79→17. Rates above 60 during parts of these
intervals pay existing debt. This is improved presentation headroom, not a
claim of responsive rendering or a solved heavy-combat budget.

The delayed 68020 capture `sim60-batch-level5-slow-020` also matches the A500
baseline at all three checkpoints for gameplay, HUD state and fresh actor
projection, with all five resets passing. Over the 3000 ticks it takes 2988
fields, presents 105 times and reduces pending updates 30→18. Its hundred-field
trace contains 121 complete updates (37420.56 mean cycles) and three complete
renders/presentations. The largest complete update gap is 25 fields (0.40–0.43
seconds); the largest complete presentation gap is 31 fields (0.50–0.53 seconds).
These observations include deliberately delayed rendering and are not bounds
outside the trace or raw-cycle comparisons against the differently clocked A500.

`tmp/batch-level5-validation.json` records all six comparisons and interval
measurements; per-capture `latency-costs.json` and `latency.json` retain the
routine and gap evidence. All captures finished and the normal build was
restored. PROJECT_BATCH now defaults on within experimental SIM60; the
measured benefit does not resolve heavy-combat overload or cooperative
rendering latency.

## Current HUD-enabled combat and default projection pass

`sim60-hud-combat-baseline-a500` (PROJECT_BATCH=0) and
`sim60-hud-combat-batch-a500` (1) retain exact matching listings/slaves in tmp.
Mapped gameplay, HUD position/step/clock and fresh actor projection match at
1800/2400; only the intentionally deferred shared scratch differs. All six
requested native transitions pass reset checks. Results are retained in
`tmp/hud-combat-validation.json`.

Complete update means are 117800.88 cycles (84) versus 108427.04 (79), a 7.96%
reduction. Projection means are 12610.33 versus 3236.30 cycles. The baseline
hundred-field window presents nothing; the candidate includes one complete
render (1031048 cycles, 13 fields) and one presentation. Its largest complete
update gap is 14 fields, bounded by 0.217–0.250 seconds. These window averages
are not paired per-tick measurements; different scheduling changes the number
of calls observed.

Across ticks 1800–2400, baseline fields/presentations/debt are 621/2/218→239;
the candidate records 602/4/154→156 (59.80 updates/s). The candidate's lower
cost helps, but debt remains roughly 2.6 seconds and presentation is still slow.
`tools/project_batch_trace.py` observes 80 accepted passes and 80 correctly
ordered callbacks, with no fallback or incomplete pass. It verifies emitted
listing bytes and does not depend on source line numbers. Altered callback
index, actor and target controls are rejected; the older combat trace still
reports 92 accepted passes and callbacks. Each capture retains cost, latency
and callback-order reports.

PROJECT_BATCH now defaults on within experimental SIM60. The default VERIFY
combat build is byte-identical to this measured explicit-on candidate.
Non-VERIFY SIM60 builds with and without BATCH_TEST/BATCH_BAD_VISIBILITY,
HUD_TEST/HUD_BAD_RENDER and FRAME_TEST are identical (15830 code bytes).
The normal legacy slave remains byte-identical (4986 code bytes) and has been
restored. This change does not enable SIM60 in normal builds or claim complete
gameplay coverage; natural transitions, further encounters and responsiveness
remain open requirements.

## Current combat movement and collision cost audit

The current PROJECT_BATCH/HUD-enabled A500 combat trace contains 401 complete
native movement calls averaging 1147.48 cycles. Four actors repeat constant
flat movement inputs (317 per-actor repeats), unlike the earlier route whose
repeats were already cheap stationary motion. A guarded yaw/speed vector cache
was measured and is not retained: complete update means were 108427.04 versus
105305.15 cycles (2.88% lower), insufficient to establish the required 3% full
frame saving after rendering/interrupts and extra guard/validation complexity.
Do not add this cache based only on the input-reuse count.

The retained corrected experiment `sim60-vector-fixed-combat-a500` matches
gameplay, HUD and fresh actor projection at 1800/2400, with six resets passing.
Its diagnostic twin `sim60-vector-twin-combat-a500` passes 4703 full-actor
comparisons against native movement through tick 2400. A wrong bank-for-yaw
key in `sim60-vector-combat-a500` is rejected by both checkpoint comparisons;
`tmp/vector-bad-key-validation.json` retains the differences. The corrected
prototype source is ignored at `tmp/vector60-prototype.s`; exact listings,
binaries and reports remain paired with the captures. No cache flag or hook
remains in production sources, and the restored default combat binary matches
the preceding measured build exactly.

`tmp/combat-collision-costs.json` measures complete calls in the same baseline:
world scan 2057.17 cycles (564), projectile scan 2104.19 (321), heading 547.15
(880), and signed distance 279.03 (1760). These inclusive costs can overlap;
do not add them to self-time percentages. Collision scanning is a larger next
target than another small movement shortcut. Enemy-loop distance/heading
fields also have collision, audio and AI consumers; they cannot simply be
updated only on AI decision ticks without a consumer audit.

## Combat rejection and AI geometry audit

`tmp/combat-scan-rejections.json` counts the current baseline's collision tests.
The world scan rejects 3303 of 3464 tested candidates on X; all 161 survivors
reject on Z. Projectile scanning rejects 2167 of 2247 on X and the remaining
80 on Z. The flag checks also reject many projectiles before geometry. Moving
X testing ahead of those checks would add geometry work to these cheap rejects;
these counts do not establish a worthwhile optimization or justify changing
native filter order.

An exact-output cache for native AI block $ee44–$ee8e is also not retained.
The trace has 474 repeated per-actor relative-coordinate pairs among 880 calls,
and a 32-slot direct map retains all those opportunities. Nevertheless, the
cache's hit/miss average is 1062.73 cycles versus 1142.93 for the original
block. Whole update means are 107516.08 versus 108427.04 cycles, only 0.84%
lower. The cache's guards, result preservation and miss work offset most of
the apparent reuse. Do not reintroduce it based on hit count alone.

The diagnostic run `sim60-ai-geometry-fixed-twin-combat-a500` passes 14419
native-output comparisons through tick 2400, including actor distance/heading,
D0/D1/D5/D6/A0/A1 and CCR, and matches mapped state at 1800/2400. The separate
`sim60-ai-geometry-fixed-combat-a500` timing run does **not** pass the existing
whole-state comparator: at 2400, actors 4/5 differ only in their second flag
byte (8080 versus 8000), apart from deferred projection scratch. Exact
results remain in `tmp/ai-geometry-state-differences.json`. This distinction
must not be silently hidden or described as full-state equality.

The native radar renderer writes actor byte 1 from byte 0 at $bfe2, temporarily
sets byte 0 to $88 at $bfe6, then restores byte 0 from byte 1 at $c0d2. Thus the
second byte retains the flags from the last radar draw. Other direct +1 reads
in the disassembly include non-actor structures (level text, camera, graphics
records). The state comparer now separates the live byte from this saved copy, as
validated below. No broader rendering-equivalence claim follows from that
classification.

The prototype source remains ignored at `tmp/ai_geometry60-prototype.s` with
its exact-build captures/listings. Its flag and hook have been removed. The
restored default combat build matches the preceding binary exactly, and the
normal legacy build is restored. The initial failed installation guard was
corrected to derive data addresses from the loaded hunk's relocation, rather
than assuming the gameplay A4 register already existed during installation.

## Shared AI distance and heading setup

`AI_GEOMETRY_FUSED` defaults to one within SIM60 in `ai_geometry60.s`. It reads current target/actor X/Z coordinates once and
shares their full signed-long differences between distance and heading setup.
It has no cache. The distance calculation preserves the native wrapped
absolute-value, signed ordering and three-eighths approximation, including
signed-long overflow. Heading inputs still narrow to signed words and call
native $893a; actor offsets $50/$5e receive the distance/heading results.
D2 is preserved, D5/D6 retain the full deltas, and execution resumes at $ee8e
with the original callback/decision schedule.

Installation guards all 74 bytes of $ee44–$ee8c, validates the two relocated
view-pointer operands are identical, and replaces the six-byte instruction
at $ee44 with an absolute jump. The shared helper retains a BSR/RTS pair and
an absolute continuation jump. Performance measurements include that overhead
in whole-update costs; helper-only measurements do not.

Under VERIFY, GEOMETRY_TWIN compares all fifteen registers, CCR and both actor
outputs with the original setup sequence. GEOMETRY_TEST adds 128 coordinate
boundary cases, and GEOMETRY_BAD is a rejected distance-corruption control.
These diagnostic flags are excluded from release bytes. Development documents
the measured windows and exact-build reports. Eight matched checkpoints through
native death pass across render costs and against the preceding build; the
default release is byte-identical to the audited explicit candidate. This
optimization does not eliminate heavy-scene A500 backlog.

## Radar flag lifetime and mapped-state scope

Actor byte 0 remains live flags; byte 1 is the save slot used by $bf8a's radar
pass. The copy at $bfe2 precedes temporary flags at $bfe6, and the reverse copy
at $c0d2 restores the live byte before returning to simulation. The save slot
then retains the flags from the most recent draw. This is why two otherwise
matching tick-2400 states can contain 8080 versus 8000 in the first actor word.

`tools/radar_flags.py` guards those native instructions and audits observed
save/temporary/restore order. The current combat baseline and removed AI-cache
candidate each contain one complete pass over 11 unique actors. The delayed
68020 level-5 trace contains three passes over 24 actor visits. Every saved actor
is restored in order; none of these traces has a partial pass. The eight audited
direct +1 read sites in level text, camera, graphics and sound code execute
27/27/101 times and never alias the radar actors. This dynamic alias result is
limited to those traces and direct sites; it is not a global proof about all
indirect memory references.

The state mapper checks the native save/restore opcodes, compares byte 0 as
`flags`, and exposes byte 1 with `--render-scratch` under
`render_scratch.radar_flag_backups`. It does not discard changes to any live
flag bit. Negative controls reject an omitted restore and detect a changed live
flag; a changed backup byte appears only in the explicit scratch comparison.
Results are retained in `tmp/radar-flags-validation.json` and per-capture
`radar-flags.json`.

`tmp/radar-classified-state.json` reports matching mapped gameplay/HUD state at
1800/2400 for the two combat runs, while still listing the two backup differences
at 2400. The earlier full-word failure remains in its original report. The
removed AI cache remains removed for its inadequate measured benefit. No game
binary changed for this state-model correction.


## Straight-motion integration

`MOVE_LINEAR=1` defaults on within experimental SIM60; zero selects the
ordinary wrapper. The normal movement wrapper first
saves every actor/record rollback field. The helper then accepts non-type-7
actors with zero pitch, zero angular and linear velocities, zero angular/Y
remainders, X/Z remainders in -11..11 and nonzero forward speed. FLAT_PITCH is
required. Its flat native calculation is independent of bank under those
conditions. All other callers and cases retain the ordinary wrapper.

Sixteen direct slots hold a yaw/speed key and native X/Z DIVS quotient/remainder
pairs. A cold slot calls the original movement calculation, measures wrapped
coordinate deltas, and restores X/Z before publication. Both deltas must lie
in -32768..32768. Keys and values contain no actor pointers; the guarded native
trigonometric table and arithmetic determine them across session resets.
Cache hits combine old remainders with the stored native remainder, correcting
the signed quotient when crossing twelve or crossing zero with the opposite
sign. Exact displacement and new remainder are written to the same rollback
record fields as the ordinary path. Y displacement is zero. The outer wrapper
preserves all registers and the ordinary final zero-Y CCR, including X=0.

The arithmetic oracle passes 1,507,351 combinations. Full-wrapper native twins
pass 6144 actor/record/CCR comparisons on A500 and delayed 68020, including cold
and repeated keys, signed extremes, coordinate wrap, bank, exclusion guards
and stale backups. Omitting a signed carry correction causes 602 actor/record
mismatches. Fixture-free tick-150 gameplay/HUD matches on both CPUs. Diagnostic
flags are byte-excluded from non-VERIFY builds, and the disabled/legacy builds
match their preceding binaries.

At the heavy tick-1800 A500 window, complete updates average 103557.23 versus
108427.04 cycles (4.49% lower). Across ticks 1800–9000, the candidate takes
7208 fields and presents 39 times, versus 7288 fields/32 presentations with the
ordinary wrapper. Pending updates change 142→150 versus 154→242. Gameplay,
HUD timing and fresh actor projection match at 1800/2400/3600/5400/7200/9000,
with all six requested native level resets passing. Deferred shared projection
scratch is reported separately. The delayed 68020 matches all six boundaries,
takes 7190 fields, presents 219 times and changes pending updates 24→14.
Reports are `tmp/linear-validation.json` and `tmp/linear-long-validation.json`;
exact builds are retained alongside each capture listing.

These averages do not establish sustained real-time responsiveness. The A500
3600–5400 interval runs at 54.63 Hz and adds 177 pending updates, reaching 271
at its endpoint. Its short trace contains a fourteen-field update-start gap.
The delayed 68020 trace contains a twenty-five-field gap including the injected
render delay. The approach route naturally kills the player at tick 9212;
the interrupted 68020 snapshot has energy -80, native death flag 1 and both
active/running clear. It is not a completed tick-10800 capture. Use tick 9000
as the last completed boundary for this route. The matched 68020 baseline
also passes state and reset checks at 1800/2400. Complete update cost falls
3.60% (57474.49→55403.43 cycles); both builds take 586 fields and present
eighteen times over the next 600 ticks. This supports enabling MOVE_LINEAR
within SIM60 while retaining the full performance and encounter limitations.


## Natural death entry and late-combat budget

The tick-9190 captures `sim60-linear-natural-death-{a500,slow-020}` have matching
gameplay/HUD/fresh projection. `tools/natural_death_trace.py` guards the native
energy load at $2cce, signed test/branch at $2cd4/$2cd6, active clear at $2cd8,
death flag write at $2ce0 and native cleanup/death branch at $2d7c/$2d88.
Both traces observe energy -80, active clear, death mark, one completed update,
SIM60 exit, input restoration and the native death path in that order. No
simulation update or simulation render follows in the captured window. The
transition spans fields 22–24 on A500 and 29–30 with delayed 68020 rendering.
Missing active clear, wrong store order, nonnegative energy and a post-exit
update are rejected by altered-event controls. This establishes natural death
entry, not the subsequent Continue answer, retry or new-game behavior.

The tick-4500 A500 trace contains 92 complete updates averaging 107589.65 cycles
and no presentation in 100 fields. Main-context work occupies 83.5% of recorded
cycles; the other principal execution context occupies 16.4%. Record lookup
averages 248.38 cycles, movement 2307.24 and sorting 6508.69. Inclusive routine
costs overlap and must not be summed as independent shares. Tick-5400 mapped
state matches the long run including fresh projection and HUD.

A cold-cache model of its 1758 record requests/eleven distinct actor addresses
has 377 misses with the current `(actor >> 5) & 31` index. Capacities 64 and
128 do not fix those aliases. `(actor >> 4) & 31` yields eleven misses, with
the same allocation and two fewer 68000 rotate cycles on each index operation.
`RECORD_CACHE_SHIFT=4` now defaults on; 5 retains the old index. Both choices
retain the actor-tag check and original search/allocation fallback. The matched
A500/68020 captures pass gameplay/HUD/fresh projection and six resets at
4500/5400. Complete updates fall 107589.65→105029.13 cycles on A500
(2.38%) and 57240.05→55980.75 on 68020 (2.20%). Record lookup means fall
248.38→116.97 and 129.38→62.54 cycles. Only the two rotate opcodes differ
in the matched binaries; no memory or instructions are added. Across 900 ticks
A500 takes 921 instead of 929 fields, presents three times in either build and
adds 21 instead of 29 pending updates. Both 68020 builds take 897 fields and
present 27 times. This free local saving does not complete the timing goal.


## Preferences and nested-modal timing

`PREFERENCES_TEST=200` enters the actual preferences screen through $d3a8,
invokes the native P handler at $10268 from its input poll, answers the nested
pause dialog, and selects the preferences Done button without changing settings.
Native drawing and return paths execute. The diagnostic substitutes only the
poll answers at $d43a and the existing $e1f6 dialog hook. Its exact-build PF60
record is read by `tools/preferences_state.py`.

On A500, tick 200 remains unchanged while the outer clock anchor moves from
field 3026 to 3323. Credit remains 1920 (32 owed updates). The nested dialog
spans fields 3137–3180 and leaves the outer anchor/credit untouched. The delayed
68020 preserves tick 200 and credit 1800 (30 owed updates), with the outer
anchor moving 1347→1518 and the nested interval 1404–1434. Both restore
modal depth/render state to zero and increment the resume count exactly once.
Gameplay/HUD/fresh projection match the fixture-free run at 201/600/1500;
only deferred shared projection scratch differs. The VERIFY-only
PREFERENCES_BAD_CREDIT control clears the 1920-credit A500 debt and is rejected.
Both flags are byte-excluded without VERIFY. This covers no-change preferences
and explicit nested modal entry, not every preference choice or UI flow.


### Stationary star arithmetic bound

The retained shift-4 tick-4500 A500 trace has six stars and zero effective
star velocities. Four stars retain nonzero signed fractions within -11..11.
All 380 observed full arithmetic integrations have those stationary inputs;
the arithmetic bodies total 269186 cycles, averaging 708.38 each. A conservative
102-cycle range guard would save approximately 230426 cycles per hundred-field
window (1.93% of recorded field cycles). A standalone range shortcut therefore
does not establish the playbook's three-percent full-frame gain and has not been
implemented. The bound is retained in `tmp/star-idle-range-opportunity.json`.
Any larger star optimization must retain bounds/respawn/RNG behavior and account
for external position, fraction, count and allocation changes.


## Content-checked stationary star experiment

The content-checked stationary-star experiment is not retained in active code.
Its source, fixture and checker are preserved in ignored
`tmp/stable-stars-prototype/`, with exact-build captures and results alongside.
The experimental 412-byte private cache records the star allocation, count, every live X/Y
coordinate and every fractional word. Only zero effective player velocities
and counts 1..50 are eligible. A miss runs the ordinary integration and bounds
checks. A complete pass without respawns establishes in-bounds coordinates
and fractions within -11..11; a later identical stationary tuple cannot change
star or RNG state. Respawns prevent publication, reset invalidates the cache,
and changed allocation/count/coordinates/fractions force the ordinary path.
D1/A1 and the enclosing helper's D2-D7/A2-A3 preservation are retained; D0/A0
remain private scratch. This is not an all-register/CCR-equivalence claim.

The VERIFY-only `STABLE_STARS_TEST=100` fixture compares 240 full star-array,
fraction, allocation/count and RNG outcomes with the ordinary update on both
A500 and delayed 68020. Both report zero errors and 39 cache hits. Cases cover
cold/repeated calls, six counts including invalid values, eight signed fraction
seeds, coordinate/fraction mutations, replacement allocation, movement and
reset. `STABLE_STARS_BAD_FRACTION=1` deliberately ignores fraction changes and
produces eighteen star and eighteen fraction errors. Exact-build results are
read by `tools/stable_stars_state.py`. These diagnostic flags produce identical
non-VERIFY binaries with or without their definitions (17006 code bytes);
STAR_STABLE=0 reproduces the existing 16354-byte SIM60 release.

The paired tick-4500 A500 captures match mapped gameplay, HUD timing and fresh
actor projection at 4500/5400, with all six requested resets passing. Deferred
shared projection scratch is reported separately. Complete update means fall
105049.94 to 101476.41 cycles (3.40%), and star-update means fall 4638.15 to
1036.91 cycles. The hundred-field windows contain 94 versus 78 complete updates;
the candidate also renders once, whereas the baseline does not. These are
window means, not paired per-tick or full-frame savings. Over 900 ticks, fields
fall 921 to 903 and presentations increase three to four; pending updates
change 233→254 versus 192→195. Rates are 58.63 and 59.80 Hz. The candidate
therefore still accumulates debt in this interval.

The paired delayed-68020 captures also match gameplay/HUD/fresh projection and
all six resets at 4500/5400, including cross-CPU comparisons. Update means fall
55981.28→54619.70 cycles (2.43%); star update means fall 1896.13→511.84.
Over 900 ticks, fields change 897→891 with 27 presentations in either build;
pending updates change 23→20 versus 18→9. Neither CPU pair establishes the
playbook's required three-percent full-frame gain, so the extra 652 bytes and
cache complexity are not adopted. The candidate and diagnostic hooks have
been removed from active sources. Evidence remains in
`tmp/stable-stars-validation.json` and the paired exact-build captures.


## Disabled simulation code audit

`tools/check_disabled.py` reconstructs both original executable hunks, including
the uninitialized tail of the data allocation, and applies all 4833 code-hunk
long relocations using the capture's loaded bases. The A500 and 68020 captures
`disabled-sim60-{a500,020}` build SIM60 but leave CUSTOM1 off. Both match every
checked byte at legacy frame 90. The retained slave must exactly match the
listing's sibling binary. Only the three decoded VERIFY menu-fixture JSRs at
$4582/$b1f4/$b8c4 are permitted, with their exact loaded destinations checked.

Of 152416 hunk bytes, 151969 are checked byte-for-byte. The remaining 447 bytes
are native mutable data inside HUNK_CODE, guarded by their native address
formation/store instructions and relocation targets:

| Offset | Bytes | Native data and writer evidence |
| --- | ---: | --- |
| $28ce | 12 | Runtime bases; PC-relative address formation and stores at $2514/$2548/$25e6 |
| $14c78 | 4 | Clipping bounds; stores at $14e00/$14e0a |
| $1d318 | 400 | Twenty 20-byte edge records; base at $1d89e, stores through $1d97a and 20-byte stride at $1d980 |
| $1d4a8 | 7 | Edge/blitter state; stores at $1d8a8/$1d5e8/$1d52c |
| $1e948 | 10 | Span pointer and words; stores at $1e986/$1ea1a/$1ea20/$1ea26 |
| $20004 | 14 | Decompression state word and twelve-byte input buffer; $2019a and read call at $20244 |

All 82 compiled simulation patch ranges must be within the hunk and disjoint
from those data objects. Unknown relocation formats, patch commands or fixture
sites fail closed. Altered entry/return instructions, an unrelated function,
a wrong fixture target and the static byte immediately after mutable blitter
state are rejected. A synthetic patch into an excluded native data object is
also rejected. Results are in per-capture `disabled-check.json` and
`tmp/disabled-negative-controls.json`.

This establishes disabled-code preservation for the captured default SIM60
build on both CPUs. It does not validate the values of excluded native data,
all optional diagnostic configurations, enabled-hook instruction boundaries or
interior branch targets. The normal loader remains identical to its retained
reference. Current SIM60
release identities and optional-rendering reference checks are recorded in the
rendering validation section; the normal build is restored after captures.


### World recenter loop

`RECENTER_FAST=1` replaces only SIM60's call to native $3ab8; the native entry
and all other callers remain intact. It builds the same native stack frame,
walks the active pointer list, and holds player X/Z and the wrapping phase in
registers. Player entries and type-7 actors are excluded before subtraction.
Duplicate entries still receive repeated subtraction, in order. Signed long
arithmetic, inclusive +/-32768 boundaries and single 65536 corrections match
the native loop. The routine retains native D1 scratch behavior and clears X
where the native positive loop's final increment does. It restores its extra
working registers before resuming untouched native code at $3b5e, including
secondary-object handling and the final player X/Z reset. It adds no persistent
state or geometry cache. RECENTER_FAST defaults on within SIM60.

The RC60 fixture passes 128 native-reference cases on both CPUs, covering
counts 0/1/16/256, duplicate pointers, excluded actors, wrapping enabled/disabled,
signed arithmetic boundaries, secondary-object aliases (including the player),
and both incoming X values. It compares all 112 bytes of 18 actors, D1, CCR,
returned A0 and preservation of D2/D3/A1/A2. Original globals and list entries
are restored. Corrupting a candidate actor's X position fails all 128 cases.
`sim60-recenter-twin-{a500,020}` match preceding gameplay/HUD/fresh projection
at tick 150; only deferred projection scratch differs. Both install all 87
existing hooks correctly. Results: `tmp/recenter-twin-validation.json`.

Matched heavy-combat captures at 4500/5400 (`sim60-recenter-late-{a500,020}`)
match the preceding movement-trim build and each other for gameplay/HUD/fresh
projection, with all six resets and 87 hooks passing. Complete A500 update
cost falls 98406.08 -> 96608.98 cycles (1.83%); recenter cost falls
3783.74 -> 2013.41. On delayed 68020, update cost falls 51516.95 -> 50676.35
(1.63%) and recenter cost 1810.19 -> 1004.51. These small gains do not prove
sustained 60 Hz or the playbook's three-percent full-frame threshold.
Over the 900-tick A500 window, both builds present four times; fields fall
891 -> 876 and pending growth is -9 -> -24. The delayed 68020 adds one
presentation (27 -> 28), each deliberately delayed twenty fields, so its
882 -> 902 fields do not directly measure update-cost regression.
Results: `tmp/recenter-profile-{a500,020}-validation.json`.

The longer A500 comparison covers ticks 600–5400 with five matched checkpoints.
Both builds pass gameplay/HUD/fresh projection, six reset records and all 87
installed hooks. The preceding movement-trim baseline completes 4800 updates
in 4969 fields (57.9593 Hz), presenting 52 times and growing pending debt
31 -> 200. The recenter loop takes 4944 fields (58.2524 Hz), presents 56 times
and grows debt 23 -> 167. Thus throughput improves 0.51%, while average
presentation rate rises from 0.6279 to 0.6796 Hz. Mean elapsed fields per
presentation falls 95.56 -> 88.29 (7.61%) over this same route. This measured
presentation gain, alongside the smaller per-update costs and absence of new
persistent state, supports retaining the loop despite its modest update saving.
It is not a maximum-latency bound or proof of sustained 60 Hz; the last 900
ticks repay 24 owed updates but earlier debt remains. Exact paired captures are
`sim60-recenter-{off,on}-long-a500`; results are in
`tmp/recenter-long-validation.json`. The enabled release adds 156 allocated
code bytes and 16 temporary stack bytes within this call, with no new game
patch site. `RECENTER_FAST=0` reproduces the preceding release; test flags have
no effect without VERIFY (`tmp/recenter-build-validation.json`).

The DEATH_NATURAL observation fixture arms at final-level tick 9000 without
writing player energy. On normal 68020, A500 and delayed 68020, native combat
kills the player at tick 9212 (energy -80). The fixture answers Continue after
60 fields in the native dialog. Level 6 resumes as session 8 with energy 680,
credit 60, zero ticks/renders/phase and cleared motion and private timing regions.
Both post-retry gameplay/HUD/fresh-projection checkpoints 600/1500 match, allowing
only deferred projection scratch. Six preceding requested level transitions and
88 installed hooks pass on each configuration. Nine corrupted reset/death record
controls are rejected. Results: `tmp/natural-retry-cross-validation.json` and
`tmp/natural-retry-020-validation.json`. This covers final-level Continue after
natural combat death, not every possible modal/death combination.

## Vertex cache lifetimes

Model validity reset $13b84–$13b92 calls guarded native byte-fill code through
$13d88. Each observed reset begins a new cache lifetime with the vertex count
captured at $13b70. `tools/vertex_cache_lifetime.py` checks named reads of the
three transformed-coordinate arrays ($484c/$4c48/$5044) and two projected
arrays ($5440/$583c) against writes since that reset. It validates alignment
and the current model's vertex bounds using actual trace address/index registers.
Besides the word-transform writers, the full-width native transform writes
$17f84/$17f96/$17fa8 before the projection inputs at $17fe4/$17fee/$17ff8.

Four combat/boss traces pass 3614 reads across 27 cache lifetimes, including
1060 projected-coordinate reads; missing projected writes are rejected. The
report retains actual executed sites and no pre-reset accesses are excluded in
these traces. Merely listing a clipping site in the checker does not establish
its execution or behavior. This is observed producer/consumer evidence, not a
whole-program proof and not a new gameplay-state comparison exclusion.


## Native input braking and terrain damping

Neutral directional input with analogue fallback disabled uses additional
80-unit braking constants at $1004e/$1006a/$10072. All three now use the same
80/12 remainder schedule as active steering. The input table has sixteen sites.
The fifteen signed-velocity native-fragment comparisons at all twelve phases
pass on both CPUs; the old timing fails sixty cases. A native Joystick preference
toggle followed by direction release confirms gradual braking through tick 497,
with matching gameplay across A500 and delayed 68020. Toggling Mouse alone does
not disable the analogue fallback at data $293e and exercises a different path.

The terrain flag at data $46d8 is cleared by the player collision pass at $353c
and set by type-46 contact at $36e6. Input $100a8 tests it before quartering both
turn and forward velocity. The replacement changes only this
six-byte test with a guarded call; the native conditional branch and arithmetic
remain unchanged. A separate valid/last-tick clock permits immediate first
contact and subsequent damping at least twelve simulation ticks apart. It is
independent of the level-five terrain damage clock because the contact flag is
set before the native level check. Rendering suppresses damping without changing
the clock; inactive calls retain the original test. Session reset clears it.
The gate preserves registers and the incoming X flag. ABI 29 exposes the eight-byte
clock at offsets 132/134, and state comparisons include it and the contact flag.
Both CPUs pass 2592 native-fragment observations, including unsigned clock
rollover, interrupted contact and inactive calls. The old-timing control fails
2064 observations. A controlled native type-46 encounter applies damping at
3605/3617/3629 on both CPUs and skips 24 intervening calls with nontrivial
velocities. Full gameplay and private clocks match across 59 observations;
only deferred projection scratch differs. This proves the observed contact
route, not the boss decision to create that terrain. See
`tmp/terrain-friction-contact-validation.json`.


### Input write inventory

`tools/input_write_audit.py` decodes the complete native input routine
$fcf4–$100dc and classifies every destination at the two player velocity offsets.
There are 23 writes: thirteen incremental changes, three zero clamps, three speed
limits, two direct assignments, and two terrain-damping writes. Each incremental
change and its three braking thresholds maps to one of the sixteen guarded
MOVEQ sites, with exact 80/10/40-over-twelve quanta. Limits and direct device
assignments retain native units. This static audit does not establish hardware
input behavior or keyboard callback coverage; the native braking and terrain
encounters provide separate runtime evidence. `tmp/input-write-audit.json`
retains the complete inventory.


### Unrolled input constant stores

`INPUT_QUANTA_UNROLL` defaults to one within SIM60. `S60_INPUT_ENTRIES` is the
single list of sixteen immediate sites. With `S60_INPUT_EMIT_STORES=0` it emits
the existing guard/restore table; with one it emits byte stores using three
quantum registers. The updater loads each phase's 80/10/40-unit quantum once,
writes the same native immediate bytes, and still flushes the instruction cache.
It preserves every register it changes. No native patch sites are added. The
opt-out release with `SCAN_GEOMETRY_FIRST=0` is byte-identical to the
preceding input-fixed release.

QI60 compares all 558 bytes of the native input region against the preceding
updater at all twelve phases, restoring native constants before candidate calls.
Both CPUs pass this differential check and 180 independent native neutral-braking
cases; a changed immediate fails all twelve phases. Complete-call means fall
2394.60→1162.06 A500 cycles and 1253.59→571.21 68020 cycles. Complete update means
fall about 1.3% in both paired profiles. Matched-tick gameplay and timing state
agree in the short profiles and through the extended tick-9212 encounter.
The longer A500 run renders 115 frames versus 106, while its heavy-section
simulation rate remains 58.70 updates/s. This is a rendering-budget improvement,
not proof of sustained real-time simulation in every heavy scene. See
`tmp/quanta-perf-validation.json` and `tmp/quanta-extended-validation.json`.
