#!/usr/bin/env python3
"""Prospective common-time steering comparison against native 10/20 Hz."""
import argparse
import hashlib
import json
import struct
from pathlib import Path
from simulation_fixture import read_fixture


def read(directory):
    path = Path(directory)
    anchor = json.loads((path / 'anchor.json').read_text())
    blob = (path / 'memory.bin').read_bytes()
    a4 = anchor['data_base'] + 0x7ffe - anchor['memory_base']
    hz, count = anchor['active_simulation_word'], anchor['simulation_tick']
    pointer = struct.unpack_from('>I', blob, a4 - 0x1770)[0] - anchor['memory_base']
    expected = bytes(1 if t < hz or t >= 2*hz else 5 if 2*t < 3*hz else 9 for t in range(count))
    assert blob[pointer:pointer+count] == expected, 'Recorded input schedule differs'
    rows = []
    heading, previous = 0, 0
    for tick, rate, state in read_fixture(path):
        assert rate == hz
        x, y, z = struct.unpack_from('>iii', state, 0x152)
        raw_heading = struct.unpack_from('>H', state, 0x16a)[0]
        heading += (raw_heading - previous + 512) % 1024 - 512
        previous = raw_heading
        rows.append(dict(time=tick/rate, x=x, y=y, z=z, heading=heading,
                         steering=struct.unpack_from('>h', state, 0x172)[0], crash=state[0x21b]))
    assert len(rows) == 32 and [r['time'] for r in rows] == [t/10 for t in range(32)]
    assert all(r['crash'] == 0 and r['y'] == 512 for r in rows)
    def at(time):
        return next(r for r in rows if r['time'] == time)
    assert at(1.5)['steering'] > 0 and at(2)['steering'] < 0
    centered = next(r for r in rows if r['time'] > 2 and r['steering'] == 0)
    assert all(r['steering'] == 0 for r in rows if r['time'] >= centered['time'])
    metrics = dict(right_steering=at(1.5)['steering'], left_steering=at(2)['steering'],
                   centered_sample=centered['time'], minimum_heading=min(r['heading'] for r in rows),
                   final_heading=rows[-1]['heading'],
                   lateral_displacement=rows[-1]['x']-rows[0]['x'],
                   forward_displacement=rows[-1]['z']-rows[0]['z'])
    return dict(metrics=metrics, rows=rows, slave_sha256=hashlib.sha256((path/'slave.slave').read_bytes()).hexdigest())


p = argparse.ArgumentParser(description=__doc__)
p.add_argument('native10'); p.add_argument('native20'); p.add_argument('criteria'); p.add_argument('--candidate')
a = p.parse_args()
left, right = read(a.native10), read(a.native20)
path = Path(a.criteria)
if not a.candidate:
    assert not path.exists(), 'Never overwrite prospective criteria'
    limits = {k:max(abs(left['metrics'][k]-v), 0.1 if k == 'centered_sample' else 1) for k,v in right['metrics'].items()}
    result = dict(native10=left, native20=right, limits=limits,
                  rationale='Per-metric native10/20 disagreement with one-unit quantization floor; centering has 0.1s sample floor. Heading unwrapped modulo1024. Exact controls, flat/crash-free outcome, steering signs and stable centering required. Low-speed weave only; no general cornering claim.')
    path.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(dict(native10=left['metrics'], native20=right['metrics'], limits=limits), indent=2))
else:
    criteria = json.loads(path.read_text())
    assert criteria['native10'] == left and criteria['native20'] == right
    candidate = read(a.candidate)
    checks = {k:dict(reference=v, actual=candidate['metrics'][k], tolerance=criteria['limits'][k],
                     passed=abs(candidate['metrics'][k]-v) <= criteria['limits'][k]+1e-8) for k,v in right['metrics'].items()}
    result = dict(candidate=candidate, checks=checks, passed=all(c['passed'] for c in checks.values()),
                  criteria_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    (Path(a.candidate)/'steering-handling.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(checks, indent=2))
    raise SystemExit(0 if result['passed'] else 1)
