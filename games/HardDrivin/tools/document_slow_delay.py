from pathlib import Path
import json
root=Path(__file__).resolve().parents[1];prof=root/'tmp/prof'
zero=json.loads((prof/'slow-drive-zero/state-summary.json').read_text())
one=json.loads((prof/'slow-drive-four1/state-summary.json').read_text())
two=json.loads((prof/'slow-drive-four2/state-summary.json').read_text())
assert one['summary']['repeat_mismatches']=={'state':[],'front':[],'tape':[]}
assert one['events']==two['events'] and one['per_field']==two['per_field']
counts=lambda d:{hex(pc):sum(p==pc and 1<=f<1251 for p,f in d['events']) for pc in [0xb4,0xcdae,0x10bb6]}
z,c=counts(zero),counts(one);assert c['0xb4']<z['0xb4']
results={str(n):json.loads((prof/f'slow-unit-{n}/result.json').read_text()) for n in [0,1,4,255,256]}
report=dict(unit_checks=results,zero_window=counts(zero),four_window=counts(one),repeat_fields=1251,repeat_events_equal=True)
(prof/'slow-delay-results.json').write_text(json.dumps(report,indent=2)+'\n')
p=root/'docs/internals.md';s=p.read_text().replace('Full machine-matrix/menu calibration, slowed-drawing tests,','Full machine-matrix/menu calibration, controlled timing-coupling tests,')
s+=f'''
## VERIFY_SLOW / CUSTOM4 delay instrument (step 1 item 4)

Build with `-DVERIFY_SLOW=1`; combine with VERIFY_DRIVE or VERIFY_ATTRACT, or use
manually. CUSTOM4=0 installs neither hook. Nonzero CUSTOM4 values add that many
VBL transitions before each completed frame is marked ready, saturating at 255.
The option is developer-only and is absent from the normal build and user option
list. CUSTOM2 retains its original meaning. Only SPS 0126 is instrumented; the
other code lengths skip installation. The existing final cache flush follows the
additional patch writes.

The independent 32-bit counter increments at $003e2, replacing three palette
writes that are faithfully re-executed. This is separate from VERIFY_DRIVE's title
and race epochs. The $00756 hook runs after the original $00740 wait and before
the ready-byte store. It polls counter changes, using DBF for the bounded count,
then executes the displaced `move.b #$ff,-$69ff(a4)`. No STOP, host-time sleep,
physics/state mutation or field-counter reset is used. Input and clocks continue
through native VBL processing. CMP/DBF preserve X, and the native final MOVE sets
NZVC. Counter equality polling handles the 32-bit wrap without signed arithmetic.
All callers of $00750 are slowed, including menus, attract, gameplay and replay.

Native emulator checks (`slow-unit-*`) cover CUSTOM4=0, 1, 4, 255 and 256.
Zero retains the original six bytes at both patch ranges. Six submissions each
at 1 and 4 waited exactly N counter transitions; two each at 255 and 256 waited
255. The ready byte remained zero until publication and became 255 afterward.
D0–D7, A0–A6 and the expected stack balance match across the call. Raw SR readings
are retained but are not used as CCR evidence: debugger SR observations differ
from the final MOVE's expected flags. CCR preservation is established by the
instruction sequence, not by these SR snapshots.

Gameplay evidence covers [1,1251), the same 1,250-field measurement interval:
CUSTOM4=0 produced {z['0xb4']} swaps and {z['0xcdae']} physics returns; CUSTOM4=4
produced {c['0xb4']} swaps and {c['0xcdae']} physics returns. Two fresh slowed boots
(`slow-drive-four1`, `slow-drive-four2`) match all 1,251 captured per-field global,
front-buffer and fixture-state snapshots, plus every recorded event and timing.
`slow-drive-zero` is the off run. See `tmp/prof/slow-delay-results.json` for counts
and hook checks. The existing normal, VERIFY_DRIVE-only and VERIFY_ATTRACT-only
binaries are byte-identical to their accepted pre-instrument baselines. Manual
VERIFY_SLOW and VERIFY_SLOW+VERIFY_ATTRACT build successfully as well.

These checks validate the slowdown instrument, not frame-independent physics or
the full step 3 timing model. A field-indexed tape delivers a different sequence
of inputs per physics step when drawing is slowed; per-step comparisons must
account for that. Do not require the unchanged tape to reach the same checkpoint
or jump at the original field number when CUSTOM4 is nonzero.
''';p.write_text(s)
p=root/'docs/development.md';s=p.read_text()+'''
## Slowed-drawing instrument (step 1 item 4)

```sh
. tools/env.sh
OUTPUT_SLAVE="$PWD/tmp/build/HardDrivin-slow.slave" /bin/bash tools/build.sh -DVERIFY_DRIVE=1 -DVERIFY_SLOW=1 -L "$PWD/tmp/build/slow.lst"
python3 tools/check_slow_delay.py 4 NEW-HOOK-CHECK
DELAY_FIELDS=0 python3 tools/capture_slow_drive.py NEW-ZERO 1251
DELAY_FIELDS=4 python3 tools/capture_slow_drive.py NEW-FOUR1 1251
DELAY_FIELDS=4 python3 tools/capture_slow_drive.py NEW-FOUR2 1251
python3 tools/analyse_drive_fields.py tmp/prof/NEW-FOUR1 tmp/prof/NEW-FOUR2
```

For manual launching, use the VERIFY_SLOW slave and `WHD_ARGS="CUSTOM4=4"` with
the existing launcher. Values 1–255 select extra VBLs; larger values saturate at
255, and zero leaves the two game ranges unpatched. The two VERIFY input fixtures
remain mutually exclusive. Large delays can invalidate their fixed menu timings;
use the hook checker (which anchors before menu input) for boundary tests.
''';p.write_text(s)
p=root/'docs/open-work.md';s=p.read_text().replace('step 1, items 1–3 are complete','step 1, items 1–4 are complete')
s=s.replace('The existing 1,000-field attract baseline remains valid:',f'''4. VERIFY_SLOW/CUSTOM4 now delays publication by 0–255 additional VBLs.
   Off leaves both hook ranges untouched. Settings 1, 4 and the 255 cap pass
   native delay/ready/register checks; two CUSTOM4=4 gameplay runs match every
   sampled field. Window A swaps drop from {z['0xb4']} to {c['0xb4']}. Normal and existing
   input-fixture-only builds are unchanged. See `slow-delay-results.json`.

The existing 1,000-field attract baseline remains valid:''')
s=s.replace('Next work is step 1 item 4 onward in the tracked PERFORMANCE_PLAN.md: add the\nVERIFY slowed-drawing switch, generalise machine profiles, capture state at each','Next work is step 1 item 5 onward in the tracked PERFORMANCE_PLAN.md: generalise\nmachine profiles, capture state at each')
p.write_text(s)
print(json.dumps(dict(zero=z,four=c,repeat_fields=1251),indent=2))
