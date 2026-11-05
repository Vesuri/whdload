from pathlib import Path
import json
root=Path(__file__).resolve().parents[1]
w=json.loads((root/'tmp/prof/drive-a500-jump1/windows.json').read_text());a,b=w['A'],w['B']
p=root/'docs/internals.md';s=p.read_text();s=s.replace('state and functional output sequence are the acceptance evidence so far.','state and functional output sequence establish functional attract equivalence; use the\nrebuilt baseline for subsequent patch comparisons. This is not a claim that the\nshipped and rebuilt slaves have identical per-field execution.')
s+='''
## VERIFY_DRIVE input tape and gameplay windows

Step 1 items 1–3 are complete for the fixed A500 baseline. The only committed
changes are the VERIFY_DRIVE hooks and source input fixture; no performance patch
is included. The normal binary matches the rebuild used for equivalence exactly,
and VERIFY_ATTRACT matches the previous attract capture binary exactly.

`HardDrivinVerify.s` is included only with VERIFY_DRIVE. Both VERIFY modes together
are rejected at assembly time. Only SPS 0126 (`_pl0_v1`) is patched; the second
variant is unchanged. Hook ranges are marked with PERF_RANGE in the main source.
The native VBL input accumulation is followed by absolute X/Y/button publication
at game $003d8. The keyboard hook at $01382 is the return from $01212, and supplies
a pending decoded key only when the native reader has no key. Native title entry
at $08520 arms the menu tape; $10ecc establishes the first-race epoch after its
displaced native button reset and mouse centring calls.

Fixture state layout: phase.w, key-overflow.b, reserved.b, field.l, next-record.l,
X.w, Y.w, buttons.w, pending-key.w (20 bytes). Phase 0 is idle, 1 menus, 2 gameplay.
Field 1 is the first VBL after arming an epoch. The gameplay counter is never reset
by crash/replay recovery. Each 12-byte record contains field.l, X/Y.w, buttons.w and
decoded-key.w. Values hold until the next record; field $ffffffff ends the tape.
A nonzero overflow byte fails acceptance. The 97 gameplay records are field-indexed,
not rendering-pass-indexed. No guest code, car pose, speed, gear, checkpoint,
collision or replay state is injected during replay of the frozen fixture.

Controls: X=320 is centred, Y=200 held; native button word 4 increases throttle,
1 decreases throttle, 5 brakes, and 0 releases buttons. Releasing buttons does
not cut the throttle, but it is necessary before instant replay because a held
button skips playback. Menus use one decoded space then a held native click to
select automatic transmission. The fixture runs with both host input ports off.

The route first reaches the main checkpoint at field 1198. An initial approach
crash (2095–2254) and full replay (2255–2917) position the car by native recovery;
this transition is deliberately outside both benchmark windows. The successful
second approach stays on the ramp, reaches its lip at field 4364 (position
31873,189,17363), and becomes airborne beyond it with zero wheel contacts and
height above 190. The landing collision begins at field 4553. All countdown
values 25 through 1 are observed, followed by replay 4749–5504 (90 iterations),
then native recovery. The acceptance script checks the road geometry at the lip
and airborne motion; passing beside the ramp does not qualify.

Windows are half-open intervals between AFTER-publication VBL samples at $003f2:
'''
s+=f'''
| Window | Fields [first,end) | Duration | Swaps | Physics returns | Replay iterations |
|---|---|---:|---:|---:|---:|
| A: straight/checkpoint | [1,1251) | {a['seconds']:.6f} s | {a['swaps']} | {a['physics_calls']} | 0 |
| B: stunt/jump/crash/replay | [3000,5600) | {b['seconds']:.6f} s | {b['swaps']} | {b['physics_calls']} | 90 |

These are fixture baselines ({a['fps']:.4f} and {b['fps']:.4f} whole-window FPS),
not performance improvements. Physics counts are returns at $0cdae; they include
native passes during crash/recovery and are not a count of independent fixed ticks.
A swap at $000b4 precedes input publication in the next VBL; its logged counter
still names the interval that started at the previous $003f2 boundary.
'''
s+='''
`tmp/prof/drive-a500-jump1` and `drive-a500-jump2` are the accepted fresh-boot pair.
All 6,000 per-field global dumps (a4-$7100 through a4+$100, end exclusive), complete
32,000-byte front buffers and 20-byte fixture states match exactly. All swap,
physics-return and replay-iteration event sequences match too. Globals include
pose, controls, velocities, clocks, crash/replay state and replay-ring contents;
this is not an assertion that all Chip/slow memory or instruction traces match.
Each window's concatenated-state/image/tape SHA-256 is in `windows.json`.
`state-summary.json`, `capture.json`, `capture.log`, source-matched slave copies,
and decoded front-buffer images retain the evidence. Input/output paths are local
and ignored. Calibration directories, `drive-a500-run{1,2}` (side-of-ramp departure)
and `drive-a500-ramp1` (opposite-side departure) are NOT accepted jump evidence.

The original physics is still rendering-pass-dependent. Identical field-indexed
inputs on another CPU can produce a different route. These windows have only been
validated on deterministic PAL A500/68000, 512K Chip + 1536K slow, no Fast RAM,
PRELOAD and CUSTOM2=0. Full machine-matrix/menu calibration, slowed-drawing tests,
per-physics-step state capture and timing decoupling remain future work.
'''
p.write_text(s)
p=root/'docs/development.md';s=p.read_text().replace('Rebuilt-slave gameplay equivalence and profiling remain unvalidated.','The attract benchmark and rebuilt-slave comparison are documented below and in\n`internals.md`; real-gameplay verification uses the separate VERIFY_DRIVE fixture.')
s+='''
## Repeatable gameplay windows (step 1, items 1–3)

From the game directory, with the existing local harness:

```sh
. tools/env.sh
OUTPUT_SLAVE="$PWD/tmp/build/HardDrivin-drive.slave" /bin/bash tools/build.sh -DVERIFY_DRIVE=1 -L "$PWD/tmp/build/drive.lst"
python3 tools/capture_drive_fields.py NEW-DRIVE-RUN1 6000
python3 tools/capture_drive_fields.py NEW-DRIVE-RUN2 6000
python3 tools/analyse_drive_fields.py tmp/prof/NEW-DRIVE-RUN1 tmp/prof/NEW-DRIVE-RUN2
python3 tools/analyse_drive_fields.py tmp/prof/NEW-DRIVE-RUN2
python3 tools/validate_drive_windows.py tmp/prof/NEW-DRIVE-RUN1 tmp/prof/NEW-DRIVE-RUN2
```

Run names must be new directories. The tool is intentionally limited to the fixed
A500 layout and asserts the game address and a4 at native race entry. It locates
fixture state from the slave publication and assembly listing; never reuse a listing
from another build. Captures run sequentially using only this harness's owned PIDs.
No LLDB memory injection is needed for the frozen tape. Source comments define A
[1,1251) and B [3000,5600); both require the full preceding tape from a fresh boot.
The accepted pair is `drive-a500-jump1` / `drive-a500-jump2`. See `internals.md` for
counts, event evidence, exact equality scope and the rebuilt-versus-shipped caveat.

`render_drive_frame.py RUN FIELD...` decodes captured front buffers for visual
review using the retained palette. `drive_session.py`, `record_route.py`,
`host_poke.py` and `freeze_drive.py` are calibration tools, not required for replay.
Do not rerun the freezer casually: it reconstructs the calibrated inputs and would
replace the curated source comments. The input tape in source is authoritative.
'''
p.write_text(s)
p=root/'docs/open-work.md';p.write_text('''# Current status and next work

Performance plan step 1, items 1–3 are complete for the fixed A500 baseline:

1. Shipped-versus-normal-rebuilt attract comparison: same game/global addresses
   and file size; identical sequences of 130 pose states and 129 stable planar
   images. Per-field transient state differs (pose observed at most one field
   apart); this is functional equivalence, not cycle-exact equality. Details and
   evidence limits are in `internals.md` and `equivalence-outcomes.json`.
2. VERIFY_DRIVE drives the native menus and race with a 97-record field-indexed
   input tape. Normal and VERIFY_ATTRACT binaries remain byte-for-byte unchanged.
3. Window A [1,1251) reaches the first checkpoint. Window B [3000,5600) reaches
   the jump lip, becomes airborne, collides, counts down the crash, plays all
   90 replay records and recovers natively. Two fresh boots match every captured
   field and all counted event timings. Accepted evidence: `drive-a500-jump1` and
   `drive-a500-jump2`; `windows.json` contains window-specific hashes and counts.

The existing 1,000-field attract baseline remains valid: 129 swaps, 6.4397 FPS,
20.031887 seconds, matching instruction/DMA traces and before/after memory from
two fresh boots. See `tmp/prof/benchmark-report.txt` and the tracked PERFORMANCE.md.

Next work is step 1 item 4 onward in the tracked PERFORMANCE_PLAN.md: add the
VERIFY slowed-drawing switch, generalise machine profiles, capture state at each
physics return and port the disabled-patch checker. Then establish full baselines
and validate the game-time model before performance patches. VERIFY_DRIVE input
is indexed by real fields, but native physics remains frame-stepped; do not assume
the same route on faster CPUs. Clock gating during crash/replay also needs the
step 3 audit; sampling clocks does not itself prove a time model.

Only source verification fixtures and PERF_RANGE comments belong in this commit.
Local tools, game/ROM bytes, built slaves, screenshots and traces remain ignored.
No optimization, GitHub operation or push has been performed. The unrelated root
`.DS_Store` is left alone. Intro optimization remains explicitly deferred.
''')
print('Updated local development, internals and open-work documentation.')
