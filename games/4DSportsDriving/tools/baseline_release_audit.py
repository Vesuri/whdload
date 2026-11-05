#!/usr/bin/env python3
"""Audit actual baseline release arithmetic; spatial alignment is analysis only."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'tmp/prof'
reports = {}
series = {}
for hz in (20, 50):
    cap = P / f'baseline-second{hz}'
    data = json.loads((cap / 'takeoff-plane.json').read_text())
    assert data['rate'] == hz
    events = {}
    for row in data['rows']:
        events.setdefault((row['tick'], row['wheel']), {})[row['event']] = row
    wheels = {}
    series[hz] = {}
    for wheel in range(4):
        records = []
        checks = []
        for (tick, w), stages in sorted(events.items()):
            if w != wheel:
                continue
            before, after = stages['SELECT'], stages['AFTER']
            velocity = lambda r: r['velocity'] + (r['velocity_fraction'] / 5 if hz == 50 else 0)
            reset = any(k in stages for k in ('ZERO', 'PENETRATION_ZERO'))
            if 'GRAVITY' in stages:
                dv = velocity(after) - velocity(stages['GRAVITY'])
                acceleration = 21 if wheel < 2 else 15
                assert abs(dv - acceleration * 20 / hz) < 1e-8, (hz, tick, wheel, dv)
                checks.append(dict(tick=tick,delta_velocity=dv,nominal_acceleration=acceleration,reset_afterwards=reset))
            records.append(dict(tick=tick,time=tick/hz,z=after['world_z'],y=after['world_y'],velocity=0 if reset else velocity(after),reset=reset))
        series[hz][wheel] = records
        wheels[str(wheel)] = dict(gravity_checks=checks,final_velocity=records[-1]['velocity'])
    reports[str(hz)] = dict(slave_sha256=hashlib.sha256((cap/'slave.slave').read_bytes()).hexdigest(),trace_sha256=hashlib.sha256((cap/'takeoff-plane.json').read_bytes()).hexdigest(),wheels=wheels)

# Compare each wheel at a matching Z inside the measured range only. Linear
# interpolation of saved measurements is descriptive, never used by the game.
aligned = {}
for wheel in range(4):
    native = series[20][wheel]
    candidate = series[50][wheel]
    assert all(b['z'] > a['z'] for a,b in zip(candidate,candidate[1:]))
    result = []
    for row in native:
        for a,b in zip(candidate,candidate[1:]):
            if a['z'] <= row['z'] <= b['z']:
                fraction = (row['z']-a['z'])/(b['z']-a['z'])
                at = {k:a[k]+fraction*(b[k]-a[k]) for k in ('time','velocity','y')}
                result.append(dict(native_time=row['time'],matched_time=at['time'],delay=at['time']-row['time'],native_velocity=row['velocity'],matched_velocity=at['velocity'],velocity_error=at['velocity']-row['velocity'],height_error=at['y']-row['y'],bracketing_ticks=[a['tick'],b['tick']],brackets_reset_boundary=a['reset']!=b['reset']))
                break
    aligned[str(wheel)] = result
report = dict(captures=reports,spatial_alignment=aligned,
    conclusions=['All captured gravity increments match the implemented 20-to-50 conversion exactly, including native acceleration 21 front / 15 rear.',
    'At native times 14.25..14.35, equal-Z A4000 measurements lag approximately 32 ms; front velocity error is approximately -3.4 and rear approximately +3.7.',
    'This removes much of the common-time velocity deficit but retains an approximately 7-unit front-minus-rear difference. It is not evidence that pitch acceptance can be waived.',
    'Different starting heights, release/contact quantization and subsequent suspension/body feedback remain unresolved. No physics change follows from this audit alone.'],
    scope='Recorded committed-baseline wheel paths only. Reset events override pre-reset AFTER velocity. Equal-Z samples are interpolated offline within measured brackets, with reset-boundary crossings flagged. No game interpolation, extrapolation, resimulation, or changed acceptance criteria.')
out = P/'baseline-release-audit.json'
out.write_text(json.dumps(report,indent=2)+'\n')
print(out)
print('Verified gravity increments:',sum(len(w['gravity_checks']) for r in reports.values() for w in r['wheels'].values()))
for wheel in (0,2):
    print('wheel',wheel,[(r['native_time'],round(r['delay'],6),round(r['velocity_error'],6)) for r in aligned[str(wheel)] if r['native_time']>=14.25])
