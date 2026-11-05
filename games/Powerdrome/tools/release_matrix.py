#!/usr/bin/env python3
"""Run the finite release matrix sequentially against frozen slave inputs.

Source ../../common/env.sh first. Supply normal.slave, verify.slave and coverage.slave
in a new tmp/ directory. Completed matching captures are reused; incomplete ones
are preserved and rejected. Stop on any failed gate and inspect before a retry.
"""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

MACHINES = {
    'M1': ('A500', '68000', 512, 0, 1536, None),
    'M2': ('A500', '68000', 512, 4096, 1536, None),
    'M3': ('A1200', '68EC020', 2048, 0, 0, None),
    'M4': ('A1200', '68EC020', 2048, 4096, 0, None),
    'M5': ('A1200', '68030', 2048, 4096, 0, 25000000),
    'M6': ('A1200', '68040-NOMMU', 2048, 4096, 0, 25000000),
    'M7': ('A1200', '68060-NOMMU', 2048, 4096, 0, 50000000),
}


def frame_result(path):
    text = (path/'frames.txt').read_text()
    sequence = re.search(r'completions per field: ([0-9]+)', text)[1]
    points = [i for i, n in enumerate(sequence) for _ in range(int(n))]
    assert len(sequence) == 500 and len(points) >= 2
    intervals, fields = len(points)-1, points[-1]-points[0]
    counts = Counter(min(3, b-a) for a, b in zip(points, points[1:]))
    return dict(intervals=intervals, fields=fields, fps=50*intervals/fields,
                histogram={str(n) if n < 3 else '3+': counts[n] for n in (1, 2, 3)})


def jobs():
    for machine in ('M3', 'M1', 'M2', 'M4', 'M5', 'M6', 'M7'):
        caches = ('CACHE', 'NoCache') if machine in ('M5', 'M6', 'M7') else ('NoCache',)
        for cache in caches:
            for route in ('practice', 'race'):
                yield machine, cache, route, 'performance'
    for machine in ('M4', 'M5', 'M7'):
        # The 060 native twin reference rewrites branch instructions without a
        # cache flush. Keep that diagnostic reference uncached; production CACHE
        # routes are measured separately and use the installed static rasterizer.
        yield machine, 'NoCache' if machine in ('M4', 'M7') else 'CACHE', 'practice', 'twins'
    yield 'M6', 'CACHE', 'practice', 'smoke'


def run(root, reference, job):
    machine, cache, route, kind = job
    name = f'{machine}-{cache}-{route}' + ('' if kind == 'performance' else '-'+kind)
    path = root/name
    slave = root/('coverage.slave' if route == 'race' else 'verify.slave')
    model, cpu, chip, fast, slow, hz = MACHINES[machine]
    extra = f'--slow_memory={slow}'
    if hz:
        extra += f' --uae_cpu_speed=real --uae_cpu_multiplier=0 --uae_cpu_frequency={hz} --uae_cpu_cycle_exact=true'
    options = f'CUSTOM1=1 CUSTOM5={4 if route == "race" else 2} {cache}'
    if kind == 'twins':
        options += ' CUSTOM4=1'
    env = dict(os.environ, AMIGA_MODEL=model, CPU=cpu, CHIP_KB=str(chip), FAST_KB=str(fast),
               EXTRA_ARGS=extra, WHD_ARGS=options, FIELDS='500' if kind == 'performance' else '100',
               SWAP_ONLY='1', SWAP_MARKER='0xbc7c', ANCHOR='0xbc7c', SERVE_WAIT='600')
    # Do not inherit probes or instrumentation from an unrelated shell session.
    for key in ('COVERAGE_STATE', 'COVERAGE_PROBES', 'TIMING_STATE', 'TIMING_EARLY',
                'OPPONENT_STATE', 'REPAIR_BUFFER_STATE', 'PROBE_OFFSETS'):
        env.pop(key, None)
    if kind == 'smoke':
        env['PROBE_OFFSETS'] = '0x13c50 0x14764'
    if model == 'A1200':
        env['KICKSTART'] = env['KICKSTART_A1200']
    if not (path/'final-code.bin').exists():
        assert not path.exists(), f'Incomplete capture: {path}; preserve it and inspect before retrying'
        with (root/(name+'.log')).open('w') as log:
            subprocess.run(['bash', 'tools/fixed_window.sh', str(path), str(slave)],
                           env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    config = json.loads((path/'configuration.json').read_text())
    assert config['slave_sha256'] == hashlib.sha256(slave.read_bytes()).hexdigest()
    for key in ('AMIGA_MODEL', 'CPU', 'CHIP_KB', 'FAST_KB', 'EXTRA_ARGS', 'WHD_ARGS',
                'FIELDS', 'SWAP_ONLY', 'SWAP_MARKER', 'ANCHOR', 'PROBE_OFFSETS'):
        assert config.get(key) == env.get(key), f'{path}: configuration differs: {key}'
    if kind == 'performance':
        native = json.loads((reference/(name+'-native')/'baseline.json').read_text())
        result = dict(machine=machine, cache=cache, route=route, **frame_result(path))
        result.update(native_intervals=native['intervals'], native_fields=native['fields'],
                      no_regression=result['intervals']*native['fields'] >= native['intervals']*result['fields'])
        # User accepted this specific, twice-reproduced stock A1200 result.
        # Preserve the failed strict comparison; do not introduce a general tolerance.
        result['accepted_exception'] = (
            name == 'M3-NoCache-practice'
            and (result['intervals'], result['fields'], native['intervals'], native['fields'])
            == (153, 497, 153, 496))
        (path/'release-result.json').write_text(json.dumps(result, indent=2)+'\n')
        print(json.dumps(result), flush=True)
        assert result['no_regression'] or result['accepted_exception'], f'Release regression: {name}'
    else:
        with (path/'renderer.json').open('w') as output:
            subprocess.run([sys.executable, 'tools/perf_status.py', str(path)],
                           stdout=output, check=True)
        result = json.loads((path/'renderer.json').read_text())
        assert result['captured']['staged_frames'] > 0, 'No completed staged scenes'
        if kind == 'smoke':
            for offset in ('0x13c50', '0x14764'):
                assert (path/f'probe-{offset}-chip.bin').stat().st_size == chip*1024
        label = 'twins' if kind == 'twins' else 'staged scenes (production-path smoke)'
        print(f'{name}: {result["captured"]["staged_frames"]} clean completed {label}', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--reference', type=Path, default=Path('tmp/phase-b'))
    parser.add_argument('--only', help='Regular expression selecting job names')
    args = parser.parse_args()
    assert args.output.resolve().is_relative_to(Path('tmp').resolve()), 'Output must be under ignored tmp/'
    for name in ('normal.slave', 'verify.slave', 'coverage.slave'):
        assert (args.output/name).is_file(), f'Freeze {name} before running'
    for job in jobs():
        name = '-'.join(job[:3]) + ('' if job[3] == 'performance' else '-'+job[3])
        if not args.only or re.search(args.only, name):
            run(args.output, args.reference, job)


if __name__ == '__main__':
    main()
