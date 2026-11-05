from pathlib import Path
import json
r=Path(__file__).resolve().parents[1];m=json.loads((r/'manifest/step4-measurements.json').read_text());runs=m['runs'];profiles=(('a500','68000'),('a1200','68020'),('a1200-fast','68020 + Fast'))
p=r/'docs/GAME_TIME.md';s=p.read_text().replace('Final validation is in progress.','Complete within the analysis scope described below.').replace('race h160+$f86..$1050','file:$22f30 h160+$986..$a50').replace('race h160+$f4c..$f80','file:$22f30 h160+$96c..$982')
measurement='''## Measured coupling and capacity

All 21 accepted driving runs advance both native clocks by exactly **100 tenths
for 100 completed loops**. Twelve paired comparisons pass at 51 checkpoints:
CUSTOM1 on/off, normal/delayed drawing, normal/corrected drawing omission, and
rendered/omitted drawing after the synthetic wall contact, on all three profiles.
The six ordinary-release anchors are byte-identical across the full 512 KiB dump
to their previously validated step-3 anchors. The comparator also detects a
changed speed byte, a later tick and the rejected first omission experiment.

Each value below is emulated elapsed milliseconds per complete loop, averaged
from loops 125 to 225. These are elapsed costs with interrupts, DMA contention
and residual synchronization, not exclusive CPU timings. The field-counter
endpoints have roughly one field of phase uncertainty over the entire 100-loop
window (about 0.20 ms per mean loop). Capacity arms have one fresh boot per cell;
the repeated breakpoint-free performance baselines remain in step 3.

| CPU | Ordinary fix on | Ordinary fix off | Diagnostic control | Delayed drawing | Corrected drawing omission |
| --- | ---: | ---: | ---: | ---: | ---: |
'''
for p,label in profiles:
 vals=[runs[f'{p}-{arm}']['ms_per_update'] for arm in ('c0','c1','control-v2','slow-v2','logic-v2')]
 measurement+='| '+label+' | '+' | '.join(f'{v:.2f}' for v in vals)+' |\n'
measurement+='''
The three diagnostic arms use CUSTOM1=1 and equal-size slaves, differing in one
mode byte. Their initialization is matched to each other; do not pair their
states or seeds with a differently sized ordinary slave. Slower drawing changes
elapsed time, but leaves the sampled logical state, clocks and RNG identical at
the same completed loop. The normal/slow comparisons also preserve the original
mixed state/projection block; only drawing-omission comparisons exclude the
proven rendering workspace.

Conversely, the ordinary-release step-3 windows give different clock advancement
in the same **1,000 fields = 20.0319 emulated seconds**:

| CPU | Fix on: game seconds | Fix off: game seconds |
| --- | ---: | ---: |
| 68000 | 7.0 | 8.0 |
| 68020 | 11.1 | 14.0 |
| 68020 + Fast | 11.1 | 14.3 |

These windows begin at completed car update 125, not the completed whole-loop
boundary. The Fast fix-off endpoint includes a clock increment in a partially
completed loop; its 143 tenths and 142 completed car calls are not evidence of
clock corruption. Together the matched-loop and equal-field observations prove
that the current driving clocks follow work completed, not elapsed real time.
No elapsed-field input tape is needed for this autonomous demo; human controls
will require one for scheduler acceptance.

For the contact pair, tick 126 supplies player 0's working lateral coordinate
as `-left_track_width - 80`, at the original collision input boundary. Each run
is required to hit the native wall handler at $6988c; hitting the pit route is
rejected. Five checkpoints, including immediately after that tick, match.

| CPU | Rendered contact arm, mean ms/tick | Omission contact arm, mean ms/tick | First contact tick: rendered / omitted fields |
| --- | ---: | ---: | ---: |
'''
for p,label in profiles:
 a=runs[p+'-contact3-control'];b=runs[p+'-contact3-logic']
 measurement+=f"| {label} | {a['ms_per_update']:.2f} | {b['ms_per_update']:.2f} | {a['first_contact_tick_fields']} / {b['first_contact_tick_fields']} |\n"
measurement+='''
The first-tick field measurement is coarse (about ±1 field); this is one native
wall response amid eight-car traffic, not a worst-case guarantee for all crashes.
The condition, speed, positions, progress, clock and RNG comparisons continue
for the following 99 ticks.

Let `L` be the corrected omission cost and `R = control - L` the estimated
incremental presentation cost. At 10 ticks/s, `(1000 - 10L) / R` estimates the
remaining drawing rate. This subtraction is a planning approximation: omitting
drawing also changes contention and interrupt timing, and still retains some UI
work. It is not a measured shipping scheduler or a proof of additive CPU costs.

| CPU | Tick demand at 10 Hz | Estimated remaining presentations/s | Existing fix-on FPS floor |
| --- | ---: | ---: | ---: |
'''
for p,label in profiles:
 l=runs[p+'-logic-v2']['ms_per_update'];c=runs[p+'-control-v2']['ms_per_update'];fps=(1000-10*l)/(c-l)
 measurement+=f"| {label} | {l:.1f}% | {fps:.2f} | {3.494 if p=='a500' else 5.541:.3f} |\n"
measurement+='''
The 68000 fails this combined real-time-and-rendering budget by a large margin.
The 68020 profiles have substantially more tick headroom but also fail the
current rendering floor in this conservative projection and lack a measured
worst-case margin. **Do not enable a 10 Hz mode on any profile yet.** First split
the residual UI work, recover measured arithmetic/blitter cost, and demonstrate
sustained bounded debt together with the rendering floor. Reducing tick frequency
to fit the CPU would knowingly slow the clocks, not solve correct game speed.

## Native pause and startup observations

The pause check uses a new, balanced key-consumer fixture, separately built from
the ordinary release. It supplies raw ESC ($45) to the native decoder after the
settled demo, then supplies a second ESC after 120 native VBL counts. The native
decoder handles demo takeover, maps ESC to space and enters the actual pause loop.
On both 68000 and 68020 + Fast, all compared logical state blocks—including both
clocks and RNG—remain identical over a breakpoint-free **100-field (2.0032 s)**
paused window. Resuming completes one native update and advances both clocks by
exactly one tenth; the paused time is not caught up. Demo becomes driving mode 3
through the native takeover path. This validates the consumer/pause boundary,
not physical keyboard delivery. The earlier host-injected ESC attempt timed out
and is excluded; the old step-1 input fixture is not reused as evidence.

The no-input startup runs trace the accelerated clock helper and ordinary menu
clock call site, then turn warp off and capture 600 fields (12.0191 s). During
settling, startup has already moved into loading/countdown: active overlay
file:$0dc70 at the anchor becomes race overlays file:$22f30/$30a30. On 68000 the
calendar stays at 13:00:00.2 and session remains zero throughout this window.
On 68020 + Fast, driving starts soon enough to add 17 tenths to both clocks.
These are **startup-transition measurements, not a steady-menu clock-rate test**.
The ordinary six-field menu gate remains static evidence. Do not turn the
startup delay or suppressed countdown increments into simulation debt.

Other modal domains remain native. The accelerated helper accepts amounts in
tenths, including 150 (15 seconds), 6000 (10 minutes), 18000 (30 minutes) and
36000 (one hour); some branches advance in batches of 13. The identified callers
are file:$0f7bc h160+$3b4/$3ce/$129a/$12dc/$12f6 and h176+$eae (repair-table charge).
The full relocation reference inventory includes clock reset/copy consumers in
resident and overlay code. Preserve each native call, rounding and transition;
a race-only scheduler must neither intercept these jumps nor replay them as car
updates. Garage/repair, tow, transport, results and save/load have static boundary
coverage here, not fresh interactive-route acceptance. Runtime route validation
is required before releasing a scheduler whose entry/exit hooks touch them.

'''
s=s.replace('## Selected design and acceptance gates',measurement+'## Selected design and acceptance gates')
s=s.replace('The capacity projection below is a','The capacity projection above is a')
s+='''
## Reproduction and scope of completion

`profiling.md` lists the commands. `manifest/step4-validation.json` records the
asserted gates, exact run/input/tool/build hashes, startup/pause observations and
excluded experiments. `manifest/step4-measurements.json` contains the state-block
inventory, checkpoint hashes and measured field counts. `step4-static-audit.json`
and `step4-clock-refs.json` preserve the hunk/relocation evidence. Per-overlay
annotated disassembly and raw snapshots remain under `tmp/step4/`.

Early per-run `result.json` files inherited unused `requested_fields: 1000` and
`observer: survey` defaults. The actual step-4 driving protocol is completed loops
125–225, with elapsed fields read from snapshots; the validation manifest labels
this explicitly. Only the reused step-3 runs are 1,000-field driving windows.

Step 4 is complete as an analysis/design gate for SPS 0481 and the three selected
PAL profiles. It establishes the native clock quantum, state ownership, measured
coupling, a conservative capacity envelope, and a conditional implementation
choice. It does not certify gameplay at 10 Hz, real-hardware performance, every
modal route, physical input, Irek or the deferred CPUs. Step 5 must retain a
working legacy path and satisfy the measured capacity and transition gates before
the new mode can be enabled. No production code or normal slave changed.
'''
(r/'docs/GAME_TIME.md').write_text(s)
p=r/'docs/PERFORMANCE_PLAN.md';s=p.read_text().replace('change has been made; step 4 is next.','change has been made. Step 4 is complete as an analysis/design gate for the same\nprofiles; see `GAME_TIME.md` and `manifest/step4-validation.json`. The candidate\n100 ms native tick preserves arithmetic, but current capacity does not yet meet\nthe combined real-time/rendering budget. Step 5 is next, with optimization\nprerequisites before enabling the new mode. Modal routes beyond startup and\npause have static coverage; their runtime release gates remain explicit.')
s=s.replace('## Step 4 Establish the game time model','## Step 4 Establish the game time model — complete in documented analysis scope')
# Actual heading can include a hyphen; add status once immediately after it if needed.
lines=s.splitlines()
for i,line in enumerate(lines):
 if line.startswith('## Step 4') and 'complete' not in line:lines[i]=line+' — complete in documented analysis scope'
s='\n'.join(lines)+'\n'
s=s.replace('## Step 5 Implement correct speed and smooth presentation\n','## Step 5 Implement correct speed and smooth presentation\n\nStep-4 decision: retain native 100 ms ticks and a default-off race-only scheduler.\nThe measured 68000 budget is insufficient for real time plus the existing drawing\nrate; 68020 also needs measured margin. Bring forward the blocking exact-output\noptimizations from step 6 as needed, then remeasure before enabling any profile.\nKeep all native modal code and validate every touched transition at runtime.\n')
p.write_text(s)
p=r/'manifest/project.json';x=json.loads(p.read_text());x['validation']='Steps 1–4 complete within documented SPS 0481 scope. Step 4: no-input demo coupling and corrected drawing omission agree at matched loops on 68000, 68020 and 68020 + Fast; synthetic native contact and consumer-level pause checks pass. Native clock quantum is 0.1 s; a conditional unchanged-tick design is documented, but current capacity does not justify enabling it. Other modal clock boundaries are statically audited, not interactively accepted. 030/040/060 deferred. Source and ordinary release unchanged; no playable improvement claimed. Old step-1 input acceptance remains withdrawn.'
x['next_steps']=['Step 5: implement a default-off race-only native-tick scheduler with exact disabled-path comparisons.','Recover sufficient capacity using measured exact-output optimizations from step 6 before enabling any profile; preserve the native 68000 fallback.','Validate historical inputs and every touched modal transition; retain demo-first measurements on 68000, 68020 and 68020 + Fast.','Defer 030/040/060, Irek and real-hardware acceptance until scope/inputs permit.'];x['step4_report']='tmp/dev/docs/GAME_TIME.md';x['step4_validation']='tmp/dev/manifest/step4-validation.json';p.write_text(json.dumps(x,indent=2)+'\n')
(r/'docs/open-work.md').write_text('''# Ferrari Formula One current work

Steps 1–4 are complete within their documented scope. Focus remains 68000,
68020 and 68020 + Fast; 030/040/060 are deferred. See `GAME_TIME.md`,
`PERFORMANCE.md`, `profiling.md` and `manifest/step4-validation.json`.
No tracked source or ordinary release changed.

Next: step 5. The selected design retains the exact native logical tick with a
candidate 100 ms quantum, scheduled only during active driving. Clock and lap
formats independently establish tenths; current rendering throughput is not the
intended tick rate. The real-time mode must remain off until it meets both
capacity and drawing-rate gates. Bring forward exact-output arithmetic/blitter
optimizations from step 6 as necessary; preserve the native 68000 fallback.

Drawing currently mutates boost-related state and audio parameters. The corrected
omission diagnostic retains that work and matches normal logical state/RNG in
traffic and after a synthetic wall contact. Approximate tick demand at 10 Hz is
87% on 68000 and 52–53% on 68020, leaving inadequate drawing headroom in the current
conservative projection. Fix-on rendering floors remain 3.494/5.541 FPS.

Use warp through startup and the automatic demo for performance comparisons.
The native pause consumer was tested over 100 fields on 68000 and 68020 + Fast;
physical keyboard delivery was not established. Startup has loading/countdown
clock suppression. Ordinary menu, repair, tow, transport, results and save/load
boundaries have static coverage; validate touched native routes before releasing
scheduler changes. Do not interpret calendar jumps or paused time as driving debt.

Irek, NTSC, a full season, global contact worst cases and real hardware remain
unvalidated. The old step-1 input-fixture acceptance remains withdrawn. Diagnostic
builds and omitted drawing are not playable performance improvements.
''')
p=r/'docs/profiling.md';s=p.read_text();s+='''

## Step 4: native game time and capacity

Report: `GAME_TIME.md`. Scope: SPS 0481 PAL, 68000 / 68020 / 68020 + Fast.
All paths below are from the worktree root. Run capture batches sequentially;
they share the harness's debugger port and disposable game drawer. Completed
named runs are skipped. Preserve old evidence before intentionally repeating.

```sh
. tmp/dev/amiga/env.sh
python3 tmp/dev/tools/audit_step4.py
python3 tmp/dev/tools/matrix_step4.py
python3 tmp/dev/tools/build_step4.py
python3 tmp/dev/tools/diagnostics_step4.py
python3 tmp/dev/tools/build_step4_contact.py
python3 tmp/dev/tools/contact_step4.py
python3 tmp/dev/tools/build_step4_pause.py
python3 tmp/dev/tools/modal_step4.py
python3 tmp/dev/tools/check_step4.py
```

The checker regenerates `step4-measurements.json`, asserts the accepted state,
clock, fixture, anchor and modal gates, and writes `step4-validation.json` with
hashes. Its scope limitations are intentional: the report distinguishes direct
measurement, static modal evidence, capacity projections and release gates.
`finalize_step4_docs.py` was the one-time report assembly helper; do not rerun it
against the completed document because it inserts report sections.

The matrix captures complete loops 125, 150, 175 and 225 after warp exits at car
update 120 and settles to 125. It uses the frozen step-3 observer and native field
counter, not host/debugger duration. The contact arm also records handler entry
and completed loop 126. Earlier unused `requested_fields:1000` metadata is not the
capture length; observed elapsed fields come from loop snapshots. The reused
step-3 fixed-field windows are identified separately in the validation manifest.

The equal-size v2 controls differ by one mode byte. The logic arm retains the
boost/audio mutation found in drawing and some UI drawing, so its elapsed cost
is a conservative prototype, not a finished CPU-only tick kernel. Contact v3
injects one left-wall penetration at the native collision input boundary and
requires the wall handler rather than the pit path. No user input is needed.

Modal captures are two startup transitions (600 fields each) and two new
ESC-consumer pause fixtures (100 paused fields each). The pause fixture injects
two raw ESC events through native decoding, preserves its saved registers and
enters the native pause loop; this does not test physical host input. Startup
captures cross loading/countdown and do not establish steady-menu clock rate.
Rejected v1 omission/contact trials and host-ESC attempts are retained and
excluded. The normal slave and authoritative source hashes are asserted unchanged.
''';p.write_text(s)
