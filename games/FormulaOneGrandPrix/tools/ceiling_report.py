#!/usr/bin/env python3
"""Audit all four repeated A8 arms and report emulator ceilings.
Usage: ceiling_report.py DIRECTORY MACHINE
"""
import json
from pathlib import Path
import sys
from matrix_compare import compare
from matrix_report import report
from race_profile import image
from check_disabled import relocated_original
from slave_inputs import verify


def audit(root, machine):
    verify()
    root = Path(root)
    errors, rows, controls = [], {}, None
    for variant, custom3, instant in [('control', 0, '0'), ('no-wait', 1, '0'),
                                      ('no-fill', 3, '0'), ('instant', 1, '1')]:
        pair = [root/f'{machine}-{variant}-{repeat}' for repeat in ('a', 'b')]
        repeated = compare(*pair)
        errors += [f'{variant}: {e}' for e in repeated['errors']]
        for p in pair:
            capture = json.loads((p/'capture.json').read_text())
            meta = json.loads((p/'meta.json').read_text())
            identity = {key: capture[key] for key in ('machine', 'setup', 'caches', 'build', 'runtime', 'fields', 'effective_cpu_report')}
            identity['hunk_bases'] = meta['hunk_bases']
            identity['whd_control_options'] = [v for v in capture['whd_args'].split() if not v.startswith('CUSTOM3=')]
            config = dict(line.split('=', 1) for line in (p/'debug.uae').read_text().splitlines() if '=' in line)
            identity['waiting_blits'] = config.get('waiting_blits')
            if controls is None:
                controls = identity
            if identity != controls:
                errors.append(f'{p.name}: unmatched control layout/build/configuration')
            if (capture.get('custom3'), capture.get('instant_blitter'), meta.get('anchor_method')) != (custom3, instant, 'start-state'):
                errors.append(f'{p.name}: wrong options or anchor')
            if config.get('immediate_blits') != ('true' if instant == '1' else 'false'):
                errors.append(f'{p.name}: effective instant-blitter setting differs')
            h0 = meta['hunk_bases'][0]
            read = lambda name: (p/name).read_bytes() if (p/name).exists() else b''
            memory = image(read('chip.bin'), read('fast.bin'), read('slow.bin'))
            base = h0
            original = relocated_original(meta['hunk_bases'])[0]
            expected = ((0x1288, bytes.fromhex('4e714e71') if custom3 & 1 else original[0x1288:0x128c]),
                        (0x1f388, bytes.fromhex('4e75') if custom3 & 2 else original[0x1f388:0x1f38a]))
            for offset, value in expected:
                if memory[base+offset:base+offset+len(value)] != value:
                    errors.append(f'{p.name}: wrong hook at h0+{offset:x}')
        rows[variant] = report(pair[0])
        if rows[variant]['fps'] is None:
            errors.append(f'{variant}: no measured frame rate')
    return dict(status='FAIL' if errors else 'PASS', errors=errors, machine=machine, arms=rows)


if __name__ == '__main__':
    result = audit(*sys.argv[1:3])
    print(json.dumps(result, indent=2))
    sys.exit(result['status'] != 'PASS')
