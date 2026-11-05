#!/usr/bin/env python3
"""Price native CD32 world updates in one bounded Nav 1 combat window per cell."""
import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
import _amigaxdev
import wc_run
from cd32_runtime import ROOT, BASE, locate


def cpu(text):
    return dict(re.findall(r'(\w+)=(\w+)', text))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reference', required=True, help='retained matrix bare/result.json')
    p.add_argument('--fixture', required=True)
    p.add_argument('--output', required=True)
    a = p.parse_args()
    out = (ROOT/a.output).resolve()
    slave = (ROOT/a.fixture).resolve()
    if (ROOT/'tmp').resolve() not in out.parents or out.exists():
        raise ValueError('new tmp output required')
    if (ROOT/'tmp').resolve() not in slave.parents:
        raise ValueError('fixture must be in tmp')
    fixture = json.loads((slave.parent/'build.json').read_text())
    if not fixture.get('direct_flight') or fixture.get('nav') != 1 or fixture['sha256'] != hashlib.sha256(slave.read_bytes()).hexdigest():
        raise ValueError('verified Nav 1 fixture required')
    ref = json.loads((ROOT/a.reference).read_text())
    h = ref['hunks']
    if os.environ.get('EXTRA_ARGS'):
        raise ValueError('fixed configuration required')
    out.mkdir(parents=True)
    os.chdir(ROOT)
    config = out/'observer.cfg'
    config.write_text(' '.join(f'{v:x}' for v in [h[0], h[1], h[3]] + [h[0]+x for x in (0x698, 0x2a8, 0x6bc, 0x6c0, 0x3378e)])+'\n')
    env = {k:v for k,v in os.environ.items() if not k.startswith(('WC_OBSERVER_', 'WC_MATRIX_', 'WC_STATE_'))}
    env = wc_run.run_env(out, env, SLAVE=str(slave), AMIGA_SETUP=ref['machine'],
        INTRO_STOCK_CLOCK='1' if ref['machine']=='a1200-fast' else '0',
        WC_NOMMU_CORE='1' if ref['nommu_core'] else '0',
        WHD_ARGS='CUSTOM2=2 CUSTOM3=1 CUSTOM4=0 CUSTOM5=0 '+ref['options'],
        WARP='1', NTSC='0', WINDOW='front', JOY0='none', JOY1='none', DETERMINISTIC='1', WC_INSTANT_BLITTER='0',
        WC_OBSERVER_CONFIG=str(config), WC_OBSERVER_OUTPUT=str(out/'events.txt'),
        WC_STATE_PC=f'{h[0]+0x698:x}', WC_STATE_OUTPUT=str(out/'states.bin'))
    g = None
    windows = []
    def cmd(text, timeout=120):
        result = g.cmd(text, timeout=timeout)
        if any(x in result for x in ('Error', 'Cannot access', 'Invalid hex', 'Protocol error', 'Remote connection closed', 'E01')):
            raise RuntimeError(result)
        return result
    try:
        g = wc_run.server('wc-simulation', env, profile_window=False).boot(env)
        pc = h[0]+0x698
        cmd(f'break *{pc:#x}\ncontinue\ndelete')
        if f'0x{pc:x}' not in cmd('info registers pc'):
            raise ValueError('flight entry not reached')
        dump = out/'start-fast.bin'
        cmd(f'dump binary memory {dump.relative_to(ROOT)} {BASE:#x} {BASE+0x800000:#x}')
        layout = locate(dump.read_bytes())
        if layout['hunks'] != h:
            raise ValueError('unexpected layout')
        live = cmd('monitor wc-audit')
        if cpu(live) != cpu(ref['live_cpu']):
            raise ValueError(f'CPU/cache mismatch: {live}')
        cmd('monitor key 40 1')
        # One continuous held-fire input; stops only at outer field-window edges.
        # Default profiler PC window is retained: no full instruction census needed.
        for i in range(3):
            first = len((out/'events.txt').read_text().splitlines())-1
            cmd(f'monitor profile 100 "" "{out}/combat-{i}.bin"', 180)
            end = len((out/'events.txt').read_text().splitlines())-1
            windows.append(dict(first_event=first, end_event=end, fields=100))
            print(f'{out.name}: combat window {i+1}/3', flush=True)
        result = dict(layout, reference=a.reference, fixture=fixture, live_cpu=live,
            windows=windows, complete=True, emulator_sha256=hashlib.sha256(Path(env['FSUAE']).read_bytes()).hexdigest())
        (out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    finally:
        if g:
            g.p.kill()
        wc_run.stop(env)


if __name__ == '__main__':
    main()
