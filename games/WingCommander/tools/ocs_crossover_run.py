#!/usr/bin/env python3
"""P13C2 experimental bounded converter comparison; no release output."""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import subprocess
import time
import _amigaxdev
import wc_run
from amigaxdev import barto
from ocs_crossover import fixture, install
import ocs_runtime
from ocs_runtime import SIZES, ROOT, locate


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', required=True)
    modes = p.add_mutually_exclusive_group()
    modes.add_argument('--arm', choices=('native','chip-word','fast-word','chip-long','fast-long'), default='native')
    p.add_argument('--scene', choices=('asteroids','fire'),default='asteroids')
    p.add_argument('--memory', choices=('fast','slow'),default='fast')
    p.add_argument('--cpu', choices=('68000','68020'),default='68000')
    p.add_argument('--layout', help='calibrated layout.json from the same slave build')
    p.add_argument('--calibrate', action='store_true')
    p.add_argument('--baseline', choices=('on', 'off'), default='on', help='read-only observer control')
    modes.add_argument('--backend', choices=('auto','native','cpu'), help='C3 one-time selection; do not combine with --arm')
    p.add_argument('--profile', choices=('measured','unknown'), default='measured')
    p.add_argument('--unavailable', action='store_true', help='C3 required-Fast reservation failure injection')
    a = p.parse_args()
    if not a.backend and (a.profile != 'measured' or a.unavailable): p.error('selection controls require --backend')
    BASE,LENGTH=(0x200000,0x400000) if a.memory=='fast' else (0xc00000,0x1c0000)
    ocs_runtime.BASE,ocs_runtime.LENGTH=BASE,LENGTH
    if a.memory=='slow' and a.arm.startswith('fast'): raise ValueError('no true Fast RAM')
    out = (ROOT/a.output).resolve()
    if (ROOT/'tmp').resolve() not in out.parents or out.exists():
        raise ValueError('choose a new output below tmp/')
    if os.environ.get('AMIGA_SETUP','a500') != 'a500':
        raise ValueError('P13C2 uses the A500/OCS base preset')
    if any(c.isspace() for c in str(out.relative_to(ROOT))):
        raise ValueError('GDB requires a scratch directory name without whitespace')
    if os.environ.get('EXTRA_ARGS'):
        raise ValueError('EXTRA_ARGS is not allowed in the fixed P13C2 gate')
    if os.environ.get('NTSC', '0') != '0' or os.environ.get('WHD_ARGS'):
        raise ValueError('P13C2 requires PAL and the original default options')
    for option in ('INTRO_STOCK_CLOCK', 'WC_NOMMU_CORE', 'WC_BASELINE_CACHE_MODEL',
                   'WC_CPU_SPEED', 'WC_INSTANT_BLITTER'):
        if os.environ.get(option, '0') not in ('', '0'):
            raise ValueError('diagnostic override not allowed: '+option)
    if not os.environ.get('FSUAE'):
        raise ValueError('set FSUAE to the local --ocs-pixels debugger build')
    out.mkdir(parents=True)
    fixture(out)
    os.chdir(ROOT)
    env = wc_run.run_env(out, WARP=os.environ.get('WARP','0'), WINDOW='front',
               JOY0='none', JOY1='none', SLAVE=str(out/'WingCommander.Slave'),
               EXTRA_ARGS=('--uae_cpu_model=68020 ' if a.cpu=='68020' else '')+('--fast_memory=0 --slow_memory=1792' if a.memory=='slow' else ''),
               DETERMINISTIC=os.environ.get('DETERMINISTIC', '1') if a.calibrate else '1',
               AMIGA_SETUP='a500', VARIANT=wc_run.VARIANTS['ocs'], WHD_ARGS='', OCS_STOCK_CLOCK='1')
    server = wc_run.server('wc-gate', env, profile_window=False)
    g = None
    actions = []
    def command(text, timeout=60):
        answer = g.cmd(text,timeout=timeout)
        if any(x in answer for x in ('Invalid hex','Protocol error','Cannot access','Error')) or re.search(r'\bE0[1-4]\b',answer):
            raise RuntimeError(answer)
        return answer
    def dump(name, start, end):
        path = out/name
        command(f'dump binary memory {path.relative_to(ROOT)} {start:#x} {end:#x}')
        data = path.read_bytes()
        if len(data) != end-start: raise ValueError('incomplete dump')
        return data
    def until(address,label, condition=None):
        command(f'break *{address:#x}')
        if condition:
            command('condition $bpnum '+condition)
        print('waiting for '+label,flush=True)
        answer = command('continue',timeout=600)
        g.running = False
        command('delete')
        pc = command('info registers pc')
        if int(pc.split()[1],16) != address or 'Breakpoint' not in answer:
            raise ValueError('checkpoint was not reached: '+answer+' '+pc)
        actions.append({'checkpoint':label,'pc':address})
        print('reached '+label,flush=True)
    def key(state, code='45'):
        command(f'monitor key {code} {state}')
        actions.append({'key':code,'pressed':state})
    try:
        g = server.boot(env)
        if a.calibrate:
            for attempt in range(90):
                g.cont(); time.sleep(1); g.stop()
                try: memory = dump(f'calibration-{attempt}.bin',BASE,BASE+LENGTH)
                except RuntimeError: continue
                try: layout = locate(memory)
                except ValueError: continue
                (out/'layout.json').write_text(json.dumps(layout,indent=2)+'\n')
                print('calibrated live patched segment chain',flush=True)
                return
            raise TimeoutError('game segments did not load')
        if not a.layout: raise ValueError('--layout or --calibrate is required')
        layout = json.loads((ROOT/a.layout).read_text())
        h0 = layout['hunks'][0]
        if 'key-raw-v1' not in g.cmd('monitor inputcaps'):
            raise ValueError('native key route unavailable; build the local debugger or supply a capable FSUAE')
        def capture(label):
            memory = dump(label+'-fast.bin', BASE, BASE+LENGTH)
            actual = locate(memory)
            if actual != layout:
                raise ValueError('calibrated layout changed')
            a4 = int(command('info registers a4').split()[1], 16)
            if a4 != layout['a4']:
                raise ValueError('live A4 differs from startup relocation')
            for n, (base, size) in enumerate(zip(layout['hunks'], SIZES)):
                (out/f'{label}-h{n}.bin').write_bytes(memory[base-BASE:base-BASE+size])
            dump(label+'-chip.bin', 0, 0x80000)
            (out/(label+'-registers.txt')).write_text(command('info registers'))
            trace = out/(label+'-screen.bin')
            command(f'monitor profile {2 if label == "name" else 1} "" "{trace}"', timeout=120)
            shot = barto.load(str(trace)).fields[-1].shot
            if not shot or not shot.startswith(b'\x89PNG\r\n\x1a\n'):
                raise ValueError('lossless screenshot required; use build_debugger.py --ocs-pixels')
            (out/(label+'.png')).write_bytes(shot)
            print('captured '+label, flush=True)

        def baseline(label):
            # At a new conversion entry the previous asynchronous conversion may
            # still own its destination. Stop only after its native retirement.
            until(h0+0x3260e, 'retired previous conversion')
            (out/'install-audit.txt').write_text(command('monitor wc-audit'))
            selection = dict(option=a.backend,cpu=a.cpu,profile=a.profile,unavailable=a.unavailable) if a.backend else None
            installation=install(out,layout,a.arm,command,dump,BASE,LENGTH,selection)
            a.arm=installation['arm']
            path=out/(label+'-events.txt')
            print('measuring '+label+' (250 fields)',flush=True)
            command(f'monitor ocs-window 250 {int(a.baseline != "off")} {h0:x} {layout["hunks"][1]:x} "{path}"',timeout=180)
            dump('end-fast.bin',BASE,BASE+LENGTH)
            dump('end-chip.bin',0,0x80000)
            (out/'audit.txt').write_text(command('monitor wc-audit'))
            logfile=out/'run/fsuae/Cache/Logs/fs-uae.log.txt'
            options=dict(re.findall(r'Set option (\w+) = "([^\"]*)"',logfile.read_text(errors='replace')))
            metadata=dict(layout,installation=installation,cpu=a.cpu,scene=label,arm=a.arm,
                          memory=a.memory,memory_base=BASE,memory_length=LENGTH,
                          effective=options,observer=a.baseline,actions=actions,
                          slave_sha256=hashlib.sha256((out/'WingCommander.Slave').read_bytes()).hexdigest(),
                          fsuae_sha256=hashlib.sha256(Path(env['FSUAE']).read_bytes()).hexdigest())
            (out/'result.json').write_text(json.dumps(metadata,indent=2)+'\n')

        # Leave the Origin animation running to its input poll, then use its
        # native Escape handling. The world title/credits run is not skipped
        # until the first completed credit picture has been captured.
        until(h0+0x180c8, 'Origin input poll O:180c8')
        capture('origin')
        key(1)
        until(h0+0x1edde, 'world intro entry O:1edde')
        key(0)
        until(h0+0x1efb0, 'title update 100 O:1efb0', '$d2 == 100')
        capture('title')
        until(h0+0x1f03c, 'credit picture submitted O:1f03c')
        capture('credits')
        if a.scene=='asteroids':
            baseline('asteroids')
            return
        key(1)
        until(h0+0x1f396, 'campaign menu entry O:1f396')
        key(0)
        until(h0+0x1f43c, 'menu ready O:1f43c')
        capture('menu')
        # OCS starts at (159,99), over the absent Secret Missions option.
        # Native Up moves the pointer into Vega's rectangle (45,51)-(279,89).
        key(1, '4c')
        until(h0+0x1f43c, 'pointer over Vega O:1f43c', '*(short*)($a4+0x19e) <= 80')
        key(0, '4c')
        key(1, '44')
        until(h0+0x1f44e, 'menu selection accepted O:1f44e')
        key(0, '44')
        if int(command('info registers d2').split()[1], 16) != 0:
            raise ValueError('Vega campaign was not selected')
        until(h0+0x0694, 'simulator flight loop O:0694')
        until(h0+0x06c2, 'simulator first iteration O:06c2')
        capture('simulator')
        if a.baseline:
            key(1, '40')  # Native Space: fire, no artificial game writes.
            baseline('fire')
            return
    except Exception:
        if g:
            try:
                if g.running:
                    g.stop()
                (out/'failure-registers.txt').write_text(g.cmd('info registers', timeout=10))
                trace = out/'failure-screen.bin'
                g.cmd(f'monitor profile 1 "" "{trace}"', timeout=30)
                (out/'failure.png').write_bytes(barto.load(str(trace)).fields[-1].shot)
            except Exception:
                pass
        raise
    finally:
        (out/'actions.json').write_text(json.dumps(actions,indent=2)+'\n')
        if g: g.p.kill()
        wc_run.stop(env)

if __name__ == '__main__': main()
