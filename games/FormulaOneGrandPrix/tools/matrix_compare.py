#!/usr/bin/env python3
"""Compare two fresh captures of one matrix cell; never compare on against off.
Usage: matrix_compare.py FIRST SECOND
"""
import hashlib
import json
from pathlib import Path
import sys


def compare(first, second):
    roots = [Path(first), Path(second)]
    captures = [json.loads((p/'capture.json').read_text()) for p in roots]
    errors = []
    for i, c in enumerate(captures):
        if c['status'] != 'CAPTURED' or c.get('quit') != 'OK':
            errors.append(f'capture {i}: incomplete or unclean quit')
    for key in ('machine', 'caches', 'command', 'setup', 'extra_args', 'whd_args',
                'build', 'runtime', 'fields', 'effective_cpu_report'):
        if captures[0].get(key) != captures[1].get(key):
            errors.append(f'different {key}')
    clock = captures[0]['command'] == 'clock'
    # Compare capture dependencies, not unrelated tools added during collection.
    dependencies = ('machine_matrix.py', 'f1gp.py', '_amigaxdev.py', 'slave_inputs.py',
                    'slave_compare.py', 'race_clock.py' if clock else 'race_profile.py')
    for tool in dependencies:
        hashes = [c['tools'].get(tool) for c in captures]
        if None in hashes or hashes[0] != hashes[1]:
            errors.append(f'different or missing capture dependency: {tool}')
    name = 'samples.json' if clock else 'meta.json'
    data = [json.loads((p/name).read_text()) for p in roots]
    keys = ('status', 'setup', 'hunk_bases', 'route', 'green', 'results', 'samples') if clock else (
        'phase', 'fields', 'setup', 'fast_kb', 'leads', 'anchors', 'route', 'shot_digests', 'hunk_bases')
    if clock and any(d.get('status') != 'COMPLETE' for d in data):
        errors.append('whole race not complete')
    for key in keys:
        if data[0].get(key) != data[1].get(key):
            errors.append(f'different {name}: {key}')
    def images(root):
        return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(root.glob('*.png'))}
    shots = [images(p) for p in roots]
    if not shots[0] or shots[0] != shots[1]:
        errors.append('different or missing screenshots')
    return dict(status='FAIL' if errors else 'PASS', errors=errors,
                screenshots=len(shots[0]), machine=captures[0]['machine'],
                caches=captures[0]['caches'], command=captures[0]['command'])


if __name__ == '__main__':
    result = compare(*sys.argv[1:3])
    print(json.dumps(result, indent=2))
    sys.exit(result['status'] != 'PASS')
