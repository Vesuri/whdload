#!/usr/bin/env python3
"""Capture one --frame-stats flight window (phase 11b A1/A3).

The slave records frame parts itself and saves framestats.bin through WHDLoad,
so the emulator binary and CPU preset are free choices: the shared release-style
presets, the project's cycle-exact timing cores, or a debugger build. With
--debugger a raw key can be held through the window and the observer can log
publication PCs for the A1 cross-check. No emulator state is changed.
"""
import argparse
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path
import _amigaxdev
from cd32_runtime import ROOT


def listing_address(lst, needle):
    """Address of the unique listing instruction line containing needle."""
    rows = [l for l in lst if needle in l and re.match(r'00:[0-9A-F]{8} ', l)]
    if len(rows) != 1:
        raise ValueError('listing anchor not unique: '+needle)
    return int(rows[0][3:11], 16)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fixture', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--machine', choices=('a1200-fast', 'a1200-030', 'a1200-040', 'a1200-060'), required=True)
    p.add_argument('--timing-core', action='store_true', help='project cycle-exact timing core (WC_NOMMU_CORE / stock 020 clock)')
    p.add_argument('--baseline-cache-model', action='store_true', help='030 phase-8 emulated cache model')
    p.add_argument('--custom5', type=int, choices=(0, 1, 2, 3, 4), default=None)
    p.add_argument('--options', default='', help='extra WHDLoad options, e.g. NoMMU or DCache')
    p.add_argument('--debugger', action='store_true', help='boot through the gdb stub (FSUAE must be a debugger build)')
    p.add_argument('--held-key', help='raw key held through the window; requires --debugger')
    p.add_argument('--observer', action='store_true', help='log publication/VBL PCs; requires an observer build and --debugger')
    p.add_argument('--layout', help='boot_gate layout of this fixture; required with --debugger')
    p.add_argument('--ntsc', action='store_true')
    p.add_argument('--cpu-speed', choices=('real', 'max'), help='non-cycle-exact CPU speed bracket')
    p.add_argument('--timeout', type=int, default=3600)
    a = p.parse_args()
    if (a.held_key or a.observer) and not a.debugger:
        p.error('--held-key/--observer require --debugger')
    if a.debugger and not a.layout:
        p.error('--debugger requires --layout')
    out = (ROOT/a.output).resolve()
    slave = (ROOT/a.fixture).resolve()
    if (ROOT/'tmp').resolve() not in out.parents or out.exists():
        raise ValueError('new output below tmp/ required')
    fixture = json.loads((slave.parent/'build.json').read_text())
    if not fixture.get('frame_stats') or fixture['sha256'] != hashlib.sha256(slave.read_bytes()).hexdigest():
        raise ValueError('verified --frame-stats fixture required')
    if not re.fullmatch(r'[A-Za-z ]*', a.options):
        raise ValueError('unexpected WHDLoad options')
    if a.custom5 is None:
        a.custom5=0 if fixture.get('release') else 1
    if fixture.get('release') and a.custom5!=0:
        p.error('public-option frame recorder requires enhanced CUSTOM5=0')
    if not fixture.get('release') and a.custom5==4:
        p.error('experimental timing build does not support CUSTOM5=4')
    language=0 if fixture.get('release') else 3
    out.mkdir(parents=True)
    os.chdir(ROOT)
    lst = (slave.parent/'slave.lst').read_text().splitlines()
    symbols = {name: int(off, 16) for off, name in re.findall(r'^([0-9A-F]{8}) (\S+)$', '\n'.join(lst), re.M)}
    save_call = listing_address(lst, 'jsr     12(a2)           ; resload_SaveFile')
    run = '../'+str(out.relative_to(ROOT))+'/run'
    env = {k: v for k, v in os.environ.items() if not k.startswith(('WC_OBSERVER_', 'WC_MATRIX_', 'WC_STATE_'))}
    env.update(FSUAE_RUN=run, SLAVE=str(slave), AMIGA_SETUP=a.machine,
        INTRO_STOCK_CLOCK='1' if a.timing_core and a.machine == 'a1200-fast' else '0',
        WC_NOMMU_CORE='1' if a.timing_core and a.machine != 'a1200-fast' else '0',
        WHD_ARGS=f'CUSTOM1={language} CUSTOM2=2 CUSTOM3=1 CUSTOM4=0 CUSTOM5={a.custom5} NOWRITECACHE {a.options}'.strip(),
        WARP='1', NTSC='1' if a.ntsc else '0', WINDOW='front', JOY0='none', JOY1='none',
        DETERMINISTIC='1', WC_INSTANT_BLITTER='0')
    if a.baseline_cache_model:
        env['WC_BASELINE_CACHE_MODEL'] = '1'
    if a.cpu_speed:
        env['WC_CPU_SPEED'] = a.cpu_speed
    if a.observer:
        layout = json.loads((ROOT/a.layout).read_text())
        h, s = layout['hunks'], layout['slave']
        pcs = [h[0]+0x3378e, h[0]+0x34162] + [s+save_call]
        cfg = out/'observer.cfg'
        cfg.write_text(' '.join(f'{v:x}' for v in [h[0], h[1], h[3]]+pcs)+'\n')
        env.update(WC_OBSERVER_CONFIG=str(cfg), WC_OBSERVER_OUTPUT=str(out/'events.txt'))
    live = None
    started = time.time()
    g = None
    try:
        if a.debugger:
            from amigaxdev.gdbserve import Server
            g = Server('wc-frames', root=str(ROOT), run_dir='amiga/'+run, profile_window=False).boot(env)
            def cmd(text, timeout=600):
                r = g.cmd(text, timeout=timeout)
                if any(e in r for e in ('Error', 'Cannot access', 'Remote connection closed', 'E01')):
                    raise RuntimeError(r)
                return r
            layout = json.loads((ROOT/a.layout).read_text())
            h, s0 = layout['hunks'], layout['slave']
            cmd(f'break *{h[0]+0x698:#x}\ncontinue\ndelete')
            live = cmd('monitor wc-audit')
            if a.held_key:
                cmd(f'monitor key {a.held_key} 1')
            # Run uninterrupted until the slave calls resload_SaveFile, then
            # step over that call so the file is complete.
            cmd(f'break *{s0+save_call:#x}\ncontinue\ndelete', a.timeout)
            # The flush runs only from the loop, so the next visit to the
            # following instruction is the return from resload_SaveFile.
            cmd(f'break *{s0+save_call+4:#x}\ncontinue\ndelete', 600)
        else:
            subprocess.run(['/bin/bash', 'amiga/run.sh'], env=env, check=True, capture_output=True, text=True)
            deadline = started+a.timeout
            while time.time() < deadline:
                files = glob.glob(str(out/'run/boot.*/dh1/WingCommanderCD32/**/framestats.bin'), recursive=True)
                if files and os.path.getsize(files[0]) == 16+4*16384:
                    break
                time.sleep(5)
        files = glob.glob(str(out/'run/boot.*/dh1/WingCommanderCD32/**/framestats.bin'), recursive=True)
        if not files or os.path.getsize(files[0]) != 16+4*16384:
            raise TimeoutError('frame statistics were not saved')
        time.sleep(2)
        shutil.copyfile(files[0], out/'framestats.bin')
        config = glob.glob(str(out/'run/fsuae/Cache/Logs/debug.uae')) or glob.glob(str(out/'run/**/debug.uae'), recursive=True)
        result = dict(fixture=fixture, machine=a.machine, timing_core=a.timing_core,
            baseline_cache_model=a.baseline_cache_model, custom5=a.custom5, options=a.options, cpu_speed=a.cpu_speed,
            ntsc=a.ntsc, held_key=a.held_key, debugger=a.debugger, observer=a.observer, live_cpu=live,
            emulator=os.path.basename(env.get('FSUAE', '')),
            emulator_sha256=hashlib.sha256(Path(env['FSUAE']).read_bytes()).hexdigest() if env.get('FSUAE') else None,
            emulator_config=config[0] if config else None, host_seconds=time.time()-started,
            framestats_sha256=hashlib.sha256((out/'framestats.bin').read_bytes()).hexdigest(), complete=True)
        (out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
        print(f'{out.name}: saved after {time.time()-started:.0f} host s', flush=True)
    finally:
        if g:
            g.p.kill()
        subprocess.run(['/bin/bash', 'amiga/run.sh', 'stop'], env=env, check=True)


if __name__ == '__main__':
    main()
