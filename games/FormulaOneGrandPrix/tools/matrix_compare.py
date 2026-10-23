#!/usr/bin/env python3
"""Compare two fresh captures of one matrix cell; never compare on against off.
Usage: matrix_compare.py FIRST SECOND
"""
import hashlib
import json
import re
from pathlib import Path
import sys


def compare(first, second):
    roots = [Path(first), Path(second)]
    captures = [json.loads((p/'capture.json').read_text()) for p in roots]
    errors = []
    for i, c in enumerate(captures):
        if c['status'] != 'CAPTURED' or c.get('quit') != 'OK':
            errors.append(f'capture {i}: incomplete or unclean quit')
    for root, capture in zip(roots, captures):
        if capture['build']['build'] != 'verify':
            errors.append('VERIFY cache audit missing')
            continue
        logs = list(root.glob('.whdl*'))
        text = '\n'.join(p.read_text(errors='replace') for p in logs if p.is_file())
        values = re.findall(r'F1GP VERIFY CACR=([0-9a-fA-F]{8})', text)
        cpu = capture['effective_cpu_report'][0]
        mask = {68000: 0, 68020: 1, 68030: 0x101,
                68040: 0x80008000, 68060: 0xa0008000}[cpu]
        expected = mask if capture['caches'] == 'on' else 0
        if capture['caches'] == 'off' and 'NoCache' not in capture['whd_args'].split():
            errors.append(f'uncached control lacks NoCache: {root.name}')
        if len(values) != 1 or int(values[0], 16) & mask != expected:
            errors.append(f'cache-register audit failed: {root.name}')
    for key in ('machine', 'caches', 'command', 'setup', 'extra_args', 'whd_args',
                'build', 'runtime', 'fields', 'effective_cpu_report',
                'custom3', 'instant_blitter', 'anchor_method', 'skip_intro'):
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
        'phase', 'fields', 'setup', 'fast_kb', 'leads', 'anchors', 'route', 'shot_digests', 'hunk_bases', 'windows')
    if clock and any(d.get('status') != 'COMPLETE' for d in data):
        errors.append('whole race not complete')
    for key in keys:
        if data[0].get(key) != data[1].get(key):
            errors.append(f'different {name}: {key}')
    if not clock:
        from race_profile import StackReduction
        windows = ('green', 'tow', 'follow') if captures[0]['command'] == 'all' else ('',)
        for window in windows:
            profiles = [StackReduction.load(p/window/'profile.pkl.gz') for p in roots]
            for key in ('fields', 'self', 'counts', 'stacks', 'events', 'tallied'):
                if getattr(profiles[0], key) != getattr(profiles[1], key):
                    errors.append(f'different profile reduction: {window}/{key}')
    def images(root):
        return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(root.rglob('*.png'))}
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
