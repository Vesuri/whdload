#!/usr/bin/env python3
"""Run the finite completion-plan Phase B matrix, sequentially, from frozen slaves.

Source amiga/env.sh first. Outputs and resumed captures stay under tmp/.
Use --only for a subset; a completed capture is reused, never silently overwritten.
"""
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import re
import subprocess

MACHINES = {
    'M1': ('A500', '68000', 512, 0, 1536, None),
    'M2': ('A500', '68000', 512, 4096, 1536, None),
    'M3': ('A1200', '68EC020', 2048, 0, 0, None),
    'M4': ('A1200', '68EC020', 2048, 4096, 0, None),
    'M5': ('A1200', '68030', 2048, 4096, 0, 25000000),
    'M6': ('A1200', '68040-NOMMU', 2048, 4096, 0, 25000000),
    'M7': ('A1200', '68060-NOMMU', 2048, 4096, 0, 50000000),
}
# Exact published native Practice references. The A500 calibration gives
# 104 updates / 9.12 seconds. M3 has no published reference to compare.
REFERENCES = {'M1': (104, 456), 'M2': (106, 468), 'M4': (154, 491), 'M5': (194, 496),
              'M6': (178, 497), 'M7': (178, 497)}


def frame_result(path):
    text = (path / 'frames.txt').read_text()
    seq = re.search(r'completions per field: ([0-9]+)', text)[1]
    points = [i for i, n in enumerate(seq) for _ in range(int(n))]
    assert len(seq) == 500 and len(points) >= 2
    intervals, fields = len(points)-1, points[-1]-points[0]
    counts = Counter(min(3, b-a) for a, b in zip(points, points[1:]))
    return dict(intervals=intervals, fields=fields, fps=50*intervals/fields,
                histogram={str(n) if n < 3 else '3+': counts[n] for n in (1, 2, 3)})


def jobs():
    for machine in MACHINES:
        caches = ('NoCache', 'CACHE') if machine in ('M5', 'M6', 'M7') else ('NoCache',)
        for cache in caches:
            for route in ('practice', 'race'):
                for mode in ('native', 'fast', 'full'):
                    yield machine, cache, route, mode, False, False
                if machine in ('M4', 'M5', 'M6', 'M7'):
                    yield machine, cache, route, 'full', True, False
    for machine in ('M5', 'M6', 'M7'):
        yield machine, 'NoCache', 'practice', 'full', False, True


def run(root, job):
    machine, cache, route, mode, phase, sanity = job
    key = '-'.join(job[:4]) + ('-phase' if phase else '') + ('-8mhz' if sanity else '')
    path = root / key
    model, cpu, chip, fast, slow, hz = MACHINES[machine]
    if sanity:
        hz = 8000000
    extra = f'--slow_memory={slow}'
    if hz:
        extra += f' --uae_cpu_speed=real --uae_cpu_multiplier=0 --uae_cpu_frequency={hz} --uae_cpu_cycle_exact=true'
    args = f'CUSTOM5={2 if route == "practice" else 4} {cache}'
    if mode != 'native':
        args += ' CUSTOM1=1'
    if mode == 'full':
        args += ' CUSTOM3=1'
    env = dict(os.environ, AMIGA_MODEL=model, CPU=cpu, CHIP_KB=str(chip), FAST_KB=str(fast),
               EXTRA_ARGS=extra, WHD_ARGS=args, FIELDS='500', SWAP_ONLY='1', ANCHOR='0xbc7c')
    if model == 'A1200':
        env['KICKSTART'] = env['KICKSTART_A1200']
    slave = root / ('full-phase.slave' if phase else
                    ('full-' if mode == 'full' else '') + ('verify.slave' if route == 'practice' else 'coverage.slave'))
    if not (path / 'final-code.bin').exists():
        assert not path.exists(), f'Incomplete capture: {path}; inspect before retrying under a new output root'
        root.mkdir(parents=True, exist_ok=True)
        with (root / (key + '.log')).open('w') as log:
            subprocess.run(['tools/fixed_window.sh', str(path), str(slave)], env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    result = dict(name=key, machine=machine, cache=cache, route=route, mode=mode,
                  phase=phase, sanity=sanity, **frame_result(path))
    if phase:
        from phase_report import report
        result['phase_report'] = report(path)
    if mode == 'native' and route == 'practice' and cache == 'NoCache' and machine in REFERENCES:
        intervals, fields = REFERENCES[machine]
        error = abs(result['intervals']/result['fields'] - intervals/fields)*500
        result['reference_error_intervals_per_500'] = error
        result['reference_gate_passed'] = error <= 1
    (path / 'baseline.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result), flush=True)
    if result.get('reference_gate_passed') is False:
        raise SystemExit(f'Native reproduction gate failed: {key}; inspect and allow only one retry')


def table(root):
    rows = [json.loads(p.read_text()) for p in root.glob('*/baseline.json')]
    phases = {(r['machine'], r['cache'], r['route'], r['mode']): r['phase_report']
              for r in rows if r['phase']}
    print('| Machine | Cache | Route | Configuration | Intervals/fields | fps | Fields 1/2/3+ | Phase mean/p95 ms (W/R/V/C/H/T/P/O) |')
    print('| --- | --- | --- | --- | ---: | ---: | --- | --- |')
    order = {'native': 0, 'fast': 1, 'full': 2}
    for row in sorted((r for r in rows if not r['phase']),
                      key=lambda r: (r['machine'], r['sanity'], r['cache'], r['route'], order[r['mode']])):
        key = tuple(row[k] for k in ('machine', 'cache', 'route', 'mode'))
        values = phases.get(key, {}).get('phases_ms') if not row['sanity'] else None
        costs = '—'
        if values:
            costs = '; '.join(f"{values[n]['mean']:.2f}/{values[n]['p95']:.2f}" for n in
                              ('world', 'render', 'wait', 'copy', 'hud', 'timer', 'present', 'other'))
        machine = row['machine'] + (' @ 8 MHz' if row['sanity'] else '')
        hist = '/'.join(str(row['histogram'][n]) for n in ('1', '2', '3+'))
        print(f"| {machine} | {row['cache']} | {row['route']} | {row['mode']} | {row['intervals']}/{row['fields']} | {row['fps']:.3f} | {hist} | {costs} |")


def gates(root):
    rows = {p.parent.name: json.loads(p.read_text()) for p in root.glob('*/baseline.json')}
    expected = {'-'.join(j[:4]) + ('-phase' if j[4] else '') + ('-8mhz' if j[5] else '') for j in jobs()}
    missing = sorted(expected - rows.keys())
    references = {}
    for machine, (intervals, fields) in REFERENCES.items():
        key = f'{machine}-NoCache-practice-native'
        if key in rows:
            row = rows[key]
            error = abs(row['intervals']/row['fields'] - intervals/fields)*500
            references[machine] = dict(error_intervals_per_500=error, passed=error <= 1)
    sanity = {}
    for machine in ('M5', 'M6', 'M7'):
        key = f'{machine}-NoCache-practice-full'
        if key in rows and key+'-8mhz' in rows:
            normal, slow = rows[key]['fps'], rows[key+'-8mhz']['fps']
            sanity[machine] = dict(normal_fps=normal, eight_mhz_fps=slow, passed=slow < normal)
    passed = (not missing and len(references) == len(REFERENCES) and len(sanity) == 3
              and all(r['passed'] for r in [*references.values(), *sanity.values()]))
    result = dict(passed=passed, missing=missing, references=references, sanity=sanity,
                  no_historical_reference=['M3'])
    print(json.dumps(result, indent=2))
    return passed


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('out', type=Path)
    parser.add_argument('--gates', action='store_true', help='evaluate the finite B2 completion gates without running captures')
    parser.add_argument('--report', action='store_true', help='print the measured Markdown table, without running captures')
    parser.add_argument('--only', help='regular expression selecting job names')
    args = parser.parse_args()
    if args.gates:
        raise SystemExit(0 if gates(args.out) else 1)
    if args.report:
        table(args.out)
        raise SystemExit
    for job in jobs():
        name = '-'.join(job[:4]) + ('-phase' if job[4] else '') + ('-8mhz' if job[5] else '')
        if not args.only or re.search(args.only, name):
            run(args.out, job)
