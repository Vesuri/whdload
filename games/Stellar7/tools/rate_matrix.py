#!/usr/bin/env python3
"""Run and resume the serial performance-plan matrix, retaining exact builds.

PREFIX is a directory under tmp/. Completed cells are reused only when their
configuration and source revision/diff identity match. --machines/--routes
select subsets for recovery; no capture runs in parallel.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import simulation_rate
import simulation_latency
import native_scene_state

ROOT = Path(__file__).resolve().parent.parent
MACHINES = {
    'a500': ('68000', 'A500', 512, 0, 1536, None, 1),
    'a1200-stock': ('68EC020', 'A1200', 2048, 0, 0, None, 1),
    'a1200-fast': ('68EC020', 'A1200', 2048, 4096, 0, None, 1),
    '030-50': ('68030', 'A1200', 2048, 4096, 0, 50000000, 1),
    '040-25': ('68040-NOMMU', 'A1200', 2048, 4096, 0, 25000000, 1),
    '060-50': ('68060-NOMMU', 'A1200', 2048, 4096, 0, 50000000, 1),
    'a500-pal': ('68000', 'A500', 512, 0, 1536, None, 0),
    '060-50-pal': ('68060-NOMMU', 'A1200', 2048, 4096, 0, 50000000, 0),
}
ROUTES = {
    'sol': (600, 1500, ''),
    'type10-early': (1800, 2400, '-DLEVEL_TEST=200 -DLEVEL_LAST=6 -DAPPROACH_TYPE=10'),
    'type10-late': (4500, 5400, '-DLEVEL_TEST=200 -DLEVEL_LAST=6 -DAPPROACH_TYPE=10'),
    'boss': (3500, 4100, '-DBOSS_ENCOUNTER=1 -DAPPROACH_TYPE=0 -DAPPROACH_FIRE=1 -DLEVEL_TEST=200 -DLEVEL_OBSERVE=1'),
    'native-90': (90, None, ''),
    'native-240': (240, None, ''),
}


NATIVE_COMBAT_ROUTES = {
    'native-type10-early': (150, None, '-DSIM60=1 -DNATIVE_SCENE=6 -DAPPROACH_TYPE=10'),
    'native-type10-late': (375, None, '-DSIM60=1 -DNATIVE_SCENE=6 -DAPPROACH_TYPE=10'),
    'native-boss': (292, None, '-DSIM60=1 -DNATIVE_SCENE=0 -DBOSS_ENCOUNTER=1 -DAPPROACH_TYPE=0 -DAPPROACH_FIRE=1'),
}
CAPTURE_ROUTES = {**ROUTES, **NATIVE_COMBAT_ROUTES}


def run(args):
    os.chdir(ROOT)
    if args.substeps is not None:
        source = (ROOT/'whdload/sim60.s').read_text()
        if not re.search(r'^S60_SUBSTEPS\s*=', source, re.M):
            raise ValueError('This source does not implement S60_SUBSTEPS; finish step 1 before measuring another rate')
    prefix = args.prefix.resolve()
    prefix.relative_to(ROOT/'tmp')
    prefix.mkdir(parents=True, exist_ok=True)
    # Build-source identity, independent of documentation/report edits.
    source = hashlib.sha256()
    for path in sorted((ROOT/'whdload').glob('*.s')):
        source.update(path.name.encode()+path.read_bytes())
    source.update((ROOT/'whdload/makefile').read_bytes())
    source_id = source.hexdigest()
    with (ROOT/'tmp/rate-matrix.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        results = {}
        try:
            for machine in args.machines:
                cpu, model, chip, fast, slow, frequency, ntsc = MACHINES[machine]
                extra = f'--slow_memory={slow}'
                if frequency:
                    extra += (' --uae_cpu_speed=real --uae_cpu_multiplier=0'
                              f' --uae_cpu_frequency={frequency} --uae_cpu_cycle_exact=true')
                env = dict(os.environ, CPU=cpu, AMIGA_MODEL=model, CHIP_KB=str(chip),
                           FAST_KB=str(fast), EXTRA_ARGS=extra, NTSC_MODE=str(ntsc))
                if model == 'A1200':
                    env['KICKSTART'] = os.environ['KICKSTART_A1200']
                for route in args.routes:
                    start, end, fixture = CAPTURE_ROUTES[route]
                    native = route.startswith('native-')
                    name = machine+'-'+route
                    cell = prefix/name
                    listing = prefix/(name+'.lst')
                    flags = fixture if native else '-DSIM60=1 '+fixture
                    if not native and args.substeps is not None:
                        flags += f' -DS60_SUBSTEPS={args.substeps}'
                    flags += ' -L '+str(listing.relative_to(ROOT))
                    # make runs in whdload, so the listing path is relative to it.
                    flags = flags.replace(' -L tmp/', ' -L ../tmp/')
                    env['VERIFY_FLAGS'] = flags
                    env['WHD_ARGS'] = ('CUSTOM3=1' if route in NATIVE_COMBAT_ROUTES else '') if native else 'CUSTOM1=1 CUSTOM3=1'
                    config = dict(machine=machine, route=route, source_id=source_id,
                                  cpu=cpu, model=model, chip_kb=chip, fast_kb=fast,
                                  slow_kb=slow, extra_args=extra, ntsc_mode=ntsc,
                                  substeps=args.substeps, flags=flags,
                                  whd_args=env['WHD_ARGS'])
                    report_path = prefix/(name+'.json')
                    if report_path.exists():
                        report = json.loads(report_path.read_text())
                        if report['config'] != config:
                            raise ValueError(f'{name}: existing result has a different configuration')
                        results[name] = report
                        continue
                    if cell.exists() and any(cell.iterdir()):
                        raise ValueError(f'{name}: incomplete capture retained; choose a fresh prefix or move this cell aside')
                    command = [sys.executable, 'tools/fixed_window.py', str(cell.relative_to(ROOT)),
                               '--boot-timeout', str(args.boot_timeout), '--fields', '100']
                    if native:
                        command += ['--frame', str(start), '--swaps-only']
                    else:
                        command += ['--tick', str(start), '--tick-checkpoints', str(end),
                                    '--state-only', '--latency-listing', str(listing.relative_to(ROOT))]
                    print('Capturing '+name, flush=True)
                    with (prefix/(name+'.log')).open('w') as log:
                        subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
                    listing.with_suffix('.slave').write_bytes((cell/'slave.slave').read_bytes())
                    events = json.loads((cell/'field-events.json').read_text())
                    hz, fields = events['field_hz'], events['fields']
                    frames = events['events']['presentations']
                    if native:
                        complete = len(frames)-1
                        span = frames[-1]-frames[0] if complete else 0
                        measurement = dict(updates_hz=len(events['events']['updates'])*hz/fields,
                                           presentation_hz=complete*hz/span if span else None,
                                           pending_growth=None,
                                           scope='Native complete inter-presentation intervals; update count over the fixed field window.')
                        latency = simulation_latency.inspect_fields(cell)
                        if route in NATIVE_COMBAT_ROUTES:
                            native_scene_state.inspect(cell, listing, 'boss' if route == 'native-boss' else 'type10')
                    else:
                        measurement = simulation_rate.interval(cell, cell/'checkpoints'/str(end))
                        latency = simulation_latency.inspect(cell, listing)
                    report = dict(config=config, measurement=measurement, latency=latency,
                                  slave_sha256=hashlib.sha256((cell/'slave.slave').read_bytes()).hexdigest(),
                                  cache_policy='Loader SetCPU value 0x393d/mask 0x7f3f; live CACR not yet independently observed.')
                    report_path.write_text(json.dumps(report, indent=2)+'\n')
                    results[name] = report
                    (prefix/'matrix.json').write_text(json.dumps(results, indent=2)+'\n')
                    print('Completed '+name+': '+json.dumps(measurement), flush=True)
        finally:
            with (prefix/'restore.log').open('w') as log:
                subprocess.run(['make','-s','-C','whdload'], stdout=log, stderr=subprocess.STDOUT, check=True)
        return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('prefix', type=Path)
    parser.add_argument('--machines', nargs='+', choices=MACHINES, default=list(MACHINES))
    parser.add_argument('--routes', nargs='+', choices=CAPTURE_ROUTES, default=list(ROUTES))
    parser.add_argument('--substeps', type=int, choices=(1,2,3,4,6,12))
    parser.add_argument('--boot-timeout', type=float, default=1800)
    run(parser.parse_args())
