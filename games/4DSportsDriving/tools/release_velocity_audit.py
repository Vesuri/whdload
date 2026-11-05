#!/usr/bin/env python3
"""Audit current takeoff gravity/reset history against full saved states."""
import hashlib
import json
import struct
from fractions import Fraction
from pathlib import Path
from simulation_fixture import read_fixture

root = Path('tmp/prof')
report = {'rates': [], 'scope': 'Recorded natural crest only; event timing evidence, not a proposed impulse or handling acceptance.'}
for hz, baseline in ((20, 'natural-crest20'), (50, 'crest-d9e7903')):
    cap = root / f'crest-release-d9-{hz}'
    trace = json.loads((cap/'takeoff-plane.json').read_text())
    samples = read_fixture(cap, 'release-end.bin')
    reference = {t: s for t, m, s in read_fixture(root/baseline, 'bridge-end.bin')}
    assert all(s == reference[t] for t, m, s in samples)
    target = hz * 58 // 5
    state = dict((t, s) for t, m, s in samples)[target]
    result = {'hz': hz, 'matching_full_states': len(samples), 'target_tick': target,
              'trace_sha256': hashlib.sha256((cap/'takeoff-plane.json').read_bytes()).hexdigest(), 'wheels': []}
    for wheel in range(4):
        rows = [r for r in trace['rows'] if r['wheel'] == wheel and r['tick'] <= target]
        velocity = Fraction(0)
        increments = 0
        resets = []
        gravity_ticks = []
        acceleration = 21 if wheel < 2 else 15
        for r in rows:
            observed = Fraction(r['velocity']) + (Fraction(r['velocity_fraction'], 5) if hz == 50 else 0)
            if r['event'] in ('SELECT', 'GRAVITY', 'AFTER'):
                assert observed == velocity, (hz, wheel, r, str(velocity))
            if r['event'] == 'GRAVITY':
                velocity += Fraction(acceleration * 20, hz)
                increments += 1
                gravity_ticks.append(r['tick'])
            elif r['event'] in ('ZERO', 'PENETRATION_ZERO'):
                velocity = Fraction(0)
                resets.append((r['tick'], r['event']))
        saved = Fraction(struct.unpack_from('>h', state, 0x152+0x4c+2*wheel)[0])
        if hz == 50:
            saved += Fraction(struct.unpack_from('>h', state, 0x466+8+4*wheel)[0], 5)
        assert saved == velocity
        assert gravity_ticks == list(range(gravity_ticks[0], target+1))
        result['wheels'].append({'wheel': wheel, 'last_reset': resets[-1],
            'first_gravity_tick': gravity_ticks[0], 'first_gravity_time': str(Fraction(gravity_ticks[0], hz)),
            'increments': increments, 'integrated_gravity_seconds': str(Fraction(increments, hz)),
            'effective_start_time': str(Fraction(gravity_ticks[0]-1, hz)),
            'acceleration_per_second': acceleration*20, 'completed_velocity': str(saved)})
    report['rates'].append(result)
# A geometric diagnostic, not a swept-collision solver: intersect each
# observed old-to-new SELECT segment with the newly selected plane.
report['plane_segment_crossings'] = []
for hz in (20, 50):
    trace = json.loads((root/f'crest-release-d9-{hz}'/'takeoff-plane.json').read_text())
    rate_result = next(r for r in report['rates'] if r['hz'] == hz)
    for wheel_result in rate_result['wheels']:
        wheel = wheel_result['wheel']
        tick = wheel_result['first_gravity_tick']
        r = next(r for r in trace['rows'] if r['wheel'] == wheel and r['tick'] == tick and r['event'] == 'SELECT')
        assert r['plane'] >= 4
        def signed_word(n): return (n+32768)%65536-32768
        origin = [signed_word(r['base_'+a]+r['node_'+a]) for a in 'xyz']
        normal = [r['normal_'+a] for a in 'xyz']
        distances = [Fraction(sum((r[prefix+a]-64*o)*n for a,o,n in zip('xyz',origin,normal)),8192)
                     for prefix in ('old_world_', 'world_')]
        old, new = distances
        assert old < 0 < new
        fraction = -old/(new-old)
        time = (tick-1+fraction)/hz
        report['plane_segment_crossings'].append(dict(hz=hz,wheel=wheel,plane=r['plane'],
            old_distance=str(old),new_distance=str(new),fraction=str(fraction),time_seconds=float(time)))
report['plane_segment_crossing_scope'] = 'Secant intersection of recorded pre-gravity wheel motion with the selected plane. Does not establish the actual topology transition or include coupled body/contact response.'
report['deficits'] = []
for native, fast in zip(report['rates'][0]['wheels'], report['rates'][1]['wheels']):
    age = Fraction(native['integrated_gravity_seconds']) - Fraction(fast['integrated_gravity_seconds'])
    deficit = Fraction(native['completed_velocity']) - Fraction(fast['completed_velocity'])
    assert deficit == age * native['acceleration_per_second']
    report['deficits'].append({'wheel': native['wheel'], 'gravity_age_difference_seconds': str(age), 'velocity_difference': str(deficit)})
output = root/'crest-release-d9-velocity-audit.json'
output.write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2))
