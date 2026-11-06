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
import machines

ROOT = Path(__file__).resolve().parent.parent
MACHINES = machines.MACHINES
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
HEAVY_ROUTES = {
    'type10-heavy': (600, 5400, ROUTES['type10-early'][2]),
}
CAPTURE_ROUTES = {**ROUTES, **NATIVE_COMBAT_ROUTES, **HEAVY_ROUTES}


def route_window(route, substeps):
    """Convert the N=12 schedule to the first tick at/after the same game time."""
    start, end, fixture = CAPTURE_ROUTES[route]
    if route.startswith('native-'):
        return start, end, fixture, []
    scale = lambda tick: (tick * substeps + 11) // 12
    # LEVEL_TEST=T runs inside update T+1, before its completion counter advances.
    fixture = re.sub(r'-DLEVEL_TEST=(\d+)',
                     lambda match: '-DLEVEL_TEST='+str(scale(int(match[1])+1)-1), fixture)
    checkpoints = ([scale(tick) for tick in range(900, 5401, 300)]
                   if route == 'type10-heavy' else [scale(end)])
    return scale(start), scale(end), fixture, checkpoints


def run(args):
    os.chdir(ROOT)
    if args.substeps is not None:
        source = (ROOT/'src/sim60.s').read_text()
        if not re.search(r'^S60_SUBSTEPS\s*=', source, re.M):
            raise ValueError('This source does not implement S60_SUBSTEPS; finish step 1 before measuring another rate')
    default_match = re.search(r'^S60_SUBSTEPS\s*=\s*(\d+)',
                              (ROOT/'src/sim60.s').read_text(), re.M)
    substeps = args.substeps if args.substeps is not None else int(default_match[1])
    prefix = args.prefix.resolve()
    prefix.relative_to(ROOT/'tmp')
    prefix.mkdir(parents=True, exist_ok=True)
    # Build-source identity, independent of documentation/report edits.
    source = hashlib.sha256()
    for path in sorted((ROOT/'src').glob('*.s')):
        source.update(path.name.encode()+path.read_bytes())
    source.update((ROOT/'game.conf').read_bytes())
    source_id = source.hexdigest()
    with (ROOT/'tmp/rate-matrix.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        results = {}
        try:
            for machine in args.machines:
                spec = machines.resolve(machine)
                cpu = spec['cpu']
                if getattr(args, 'selected_rates', False):
                    substeps = 3 if cpu == '68000' else 12
                env = machines.env(machine)
                for route in args.routes:
                    start, end, fixture, checkpoints = route_window(route, substeps)
                    native = route.startswith('native-')
                    name = machine+'-'+route
                    cell = prefix/name
                    listing = prefix/(name+'.lst')
                    flags = fixture if native else '-DSIM60=1 '+fixture
                    if not native and (args.substeps is not None or getattr(args, 'selected_rates', False)):
                        flags += f' -DS60_SUBSTEPS={substeps}'
                    # Match the playable CPU-specific rendering path. Explicit
                    # route flags retain the reference arm for paired tests.
                    if not native and cpu == '68000' and '-DPOLYGON_BLIT_IRQ=' not in flags:
                        flags += ' -DPOLYGON_BLIT_IRQ=1'
                    # The build runs in the game directory, so the listing path is relative to it.
                    flags += ' -L '+str(listing.relative_to(ROOT))
                    env['VERIFY_FLAGS'] = flags
                    env['WHD_ARGS'] = ('CUSTOM3=1' if route in NATIVE_COMBAT_ROUTES else '') if native else 'CUSTOM1=1 CUSTOM3=1'
                    config = dict(machine=machine, route=route, source_id=source_id,
                                  setup_args=spec['args'], cpu=cpu, model=spec['model'],
                                  chip_kb=spec['chip_kb'], fast_kb=spec['fast_kb'],
                                  slow_kb=spec['slow_kb'], ntsc_mode=spec['ntsc_mode'],
                                  substeps=substeps, start=start, end=end, checkpoints=checkpoints, flags=flags,
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
                        command += ['--tick', str(start), '--tick-checkpoints', *map(str, checkpoints),
                                    '--state-only', '--latency-listing', str(listing.relative_to(ROOT))]
                    if route.startswith('type10-'):
                        command += ['--level', '6']
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
                        if route == 'type10-heavy':
                            boundaries = [cell]+[cell/'checkpoints'/str(tick) for tick in checkpoints]
                            measurement['segments'] = [simulation_rate.interval(a,b)
                                                       for a,b in zip(boundaries,boundaries[1:])]
                    report = dict(config=config, measurement=measurement, latency=latency,
                                  slave_sha256=hashlib.sha256((cell/'slave.slave').read_bytes()).hexdigest(),
                                  cache_policy='Loader SetCPU value 0x393d/mask 0x7f3f; see separate live CACR observations in docs/internals.md.')
                    report_path.write_text(json.dumps(report, indent=2)+'\n')
                    results[name] = report
                    (prefix/'matrix.json').write_text(json.dumps(results, indent=2)+'\n')
                    print('Completed '+name+': '+json.dumps(measurement), flush=True)
        finally:
            with (prefix/'restore.log').open('w') as log:
                subprocess.run(['make','-s','slave'], stdout=log, stderr=subprocess.STDOUT, check=True)
        return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('prefix', type=Path)
    parser.add_argument('--machines', nargs='+', choices=MACHINES, default=list(MACHINES))
    parser.add_argument('--routes', nargs='+', choices=CAPTURE_ROUTES, default=list(ROUTES))
    rates = parser.add_mutually_exclusive_group()
    rates.add_argument('--substeps', type=int, choices=(1,2,3,4,6,12))
    rates.add_argument('--selected-rates', action='store_true', help='use playable N=3 on 68000 and N=12 on 68020+')
    parser.add_argument('--boot-timeout', type=float, default=1800)
    run(parser.parse_args())
