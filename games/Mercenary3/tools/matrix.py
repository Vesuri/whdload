"""Run the A3 matrix through fps.py; preserve partial evidence on failure."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent


def cells():
    base = [
        ('a500-1.5m', 'a500-1.5m', '', '68000', '0', 7093790, 1, 0, 6),
        ('a1200', 'a1200', '', '68020', '0', 14187580, 4, 0, 0),
        ('a1200-fast', 'a1200-fast', '', '68020', '0', 14187580, 4, 8, 0),
        ('030-default', 'a1200-030', '', '68030', '68030', 50000000, 4, 8, 0),
        ('030-mmu', 'a1200-030', 'MMU', '68030', '68030', 50000000, 4, 8, 0),
        ('040-25', 'a1200-030', '', '68040', '0', 25000000, 4, 8, 0),
        ('060-50', 'a1200-030', '', '68060', '0', 50000000, 4, 8, 0),
        ('040-8-sanity', 'a1200-030', '', '68040', '0', 8000000, 4, 8, 0),
    ]
    result = []
    for name, setup, whd, cpu, mmu, hz, chip, fast, slow in base:
        extra = ''
        if cpu in ('68040', '68060'):
            extra = f'--cpu={cpu}-NOMMU --uae_cpu_frequency={hz}'
        expected = dict(cpu_model=cpu, mmu_model=mmu, cpu_frequency=str(hz),
                        chipmem_size=str(chip), fastmem_size=str(fast), bogomem_size=str(slow),
                        cpu_cycle_exact='true', cpu_memory_cycle_exact='true',
                        blitter_cycle_exact='true', cachesize='0', ntsc='false',
                        cpu_compatible='true', cpu_speed='real',
                        chipset='ocs' if cpu == '68000' else 'aga',
                        cpu_data_cache='true' if setup == 'a1200-030' else 'false')
        if setup == 'a1200-030':
            expected['uaeboard'] = 'full+indirect'
        result.append(dict(name=name, setup=setup, whd=whd, extra=extra,
                           deterministic='0' if setup == 'a1200-030' else '1',
                           expected=expected))
    return result


def validate(result, cell, slave_hash, whd):
    for key, expected in cell['expected'].items():
        # UAE omits the MMU line when its model is zero.
        actual = result['machine'].get(key, '0' if key == 'mmu_model' else None)
        if actual != expected:
            raise ValueError(f'{key}: expected {expected}, got {actual}')
    if result['setup'] != cell['setup'] or result['extra_args'] != cell['extra']:
        raise ValueError('setup or CPU overrides do not match the cell')
    if result['slave_sha256'] != slave_hash or result['whd_args'] != whd:
        raise ValueError('build or WHDLoad options do not match the requested cell')
    if (result['per_frame'] or result['fields'] != 500 or
            result['route'] != [[175, []], [185, ['JOY2_UP']], [140, ['JOY2_RIGHT']]]):
        raise ValueError('measurement did not use the exact 500-field reference route')
    if result['deterministic'] != cell['deterministic']:
        raise ValueError('boot I/O mode differs from the cell definition')


def frequency_sanity(rows):
    by_name = {row['name']: row for row in rows}
    slow, fast = by_name['040-8-sanity'], by_name['040-25']
    if slow['status'] != 'ok' or fast['status'] != 'ok':
        return False, 'unavailable: a 040 cell failed'
    checked = slow['result']['frames'] < fast['result']['frames']
    text = (f"8 MHz {slow['result']['frames']} frames; "
            f"25 MHz {fast['result']['frames']} frames. "
            '8 MHz must publish fewer frames than 25 MHz.')
    return checked, ('PASS: ' if checked else 'FAIL: ') + text


def render(rows, sanity):
    lines = ['# Machine matrix', '',
             'Counter frames / 500 route fields at nominal PAL 50 Hz. No instruction tracing.', '',
             '| Cell | Setup | WHDLoad options | CPU overrides | Frames | fps | Status |',
             '| --- | --- | --- | --- | ---: | ---: | --- |']
    for row in rows:
        r = row.get('result', {})
        values = [row['name'], row['setup'], row['options'] or '(none)',
                  row['extra'] or '(preset)', str(r.get('frames', '—')),
                  f"{r['fps']:.2f}" if 'fps' in r else '—', row['status']]
        lines.append('| ' + ' | '.join(str(v).replace('|', '\\|').replace('\n', ' ') for v in values) + ' |')
    return '\n'.join(lines) + '\n\n040 frequency sanity (advisory; known emulator limitation accepted): ' + sanity + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report-only', action='store_true',
                        help='validate existing cell JSONs and rebuild the table without booting')
    parser.add_argument('slave', type=Path)
    parser.add_argument('whd_args', help='quoted WHDLoad arguments, or an empty string')
    parser.add_argument('outdir', type=Path)
    args = parser.parse_args()
    slave, out = args.slave.resolve(), args.outdir.resolve()
    if not slave.is_file():
        parser.error('slave must be a readable file')
    if not out.is_relative_to(ROOT / 'tmp'):
        parser.error('OUTDIR must be under tmp/')
    if out.exists() != args.report_only or (args.report_only and not out.is_dir()):
        parser.error('OUTDIR must be new (or an existing directory with --report-only)')
    if any(c in args.whd_args for c in '\r\n'):
        parser.error('WHDLoad arguments must be a single line')
    if any(t.upper().split('=')[0] in ('MMU', 'NOMMU') for t in shlex.split(args.whd_args)):
        parser.error('MMU/NoMMU are controlled by the matrix cells')
    # Refuse hidden overrides rather than silently measuring a different matrix.
    controlled = ('EXTRA_ARGS', 'CPU', 'AMIGA_SETUP', 'AMIGA_MODEL', 'CHIP_KB',
                  'FAST_KB', 'SLOW_KB', 'NTSC', 'RECORD', 'DETERMINISTIC', 'ROUTE',
                  'PER_FRAME', 'ANCHOR', 'WHD_DEFAULTS', 'GAME_DIR', 'SLAVE_FILE')
    conflicts = [key for key in controlled if os.environ.get(key)]
    if conflicts:
        parser.error('unset matrix-controlled variables: ' + ', '.join(conflicts))
    if not args.report_only:
        out.mkdir(parents=True)
    slave_hash = hashlib.sha256(slave.read_bytes()).hexdigest()
    rows = []
    identities = None
    for cell in cells():
        whd = ' '.join(v for v in (args.whd_args.strip(), cell['whd']) if v)
        env = dict(os.environ, SLAVE=str(slave), WHD_ARGS=whd, AMIGA_SETUP=cell['setup'],
                   EXTRA_ARGS=cell['extra'], DETERMINISTIC=cell['deterministic'])
        row = dict(cell, options=whd, status='pending')
        rows.append(row)
        if not args.report_only:
            print(f"Running {cell['name']} ({cell['setup']}, {whd or 'no extra WHDLoad options'})", flush=True)
            with (out / (cell['name'] + '.log')).open('x') as log:
                process = subprocess.run([sys.executable, str(ROOT / 'tools/fps.py'),
                                          str(out / (cell['name'] + '.json'))],
                                         env=env, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        try:
            if not args.report_only and process.returncode:
                raise ValueError(f'fps.py exited {process.returncode}; see cell log')
            result = json.loads((out / (cell['name'] + '.json')).read_text())
            validate(result, cell, slave_hash, whd)
            identity = [result[k] for k in ('emulator_sha256', 'whdload_sha256', 'launcher_sha256')]
            if identities is not None and identity != identities:
                raise ValueError('runtime changed between cells')
            identities = identity
            row.update(result=result, status='ok')
            print(f"  {result['frames']} frames, {result['fps']:.2f} fps", flush=True)
        except (ValueError, KeyError, OSError) as error:
            row['status'] = 'FAILED: ' + str(error)
            print('  ' + row['status'], flush=True)
        (out / 'table.md').write_text(render(rows, 'pending'))
    passed = all(row['status'] == 'ok' for row in rows)
    checked, sanity = frequency_sanity(rows)
    # User accepts the known 040 timing limitation; retain it as advisory evidence.
    (out / 'table.md').write_text(render(rows, sanity))
    (out / 'matrix.json').write_text(json.dumps(dict(rows=rows, sanity=sanity, sanity_passed=checked, sanity_advisory=True, passed=passed), indent=2) + '\n')
    print((out / 'table.md').read_text())
    return 0 if passed else 1


if __name__ == '__main__':
    sys.exit(main())
