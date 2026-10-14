#!/usr/bin/env python3
"""P13A3 OCS original/reconstructed boots, with native input and state waits.
No game patches, performance instrumentation or CD32 layout assumptions.
"""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import subprocess
import time
import _amigaxdev
from amigaxdev.gdbserve import Server
from amigaxdev import barto
from ocs_runtime import BASE, LENGTH, SIZES, ROOT, locate


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', required=True)
    p.add_argument('--layout', help='calibrated layout.json from the same slave build')
    p.add_argument('--calibrate', action='store_true')
    p.add_argument('--simulator', action='store_true', help='continue from the menu to the first name prompt')
    a = p.parse_args()
    out = (ROOT/a.output).resolve()
    if (ROOT/'tmp').resolve() not in out.parents or out.exists():
        raise ValueError('choose a new output below tmp/')
    if not a.calibrate and (os.environ.get('WARP','0') != '0' or os.environ.get('AMIGA_SETUP','a500') != 'a500'):
        raise ValueError('P13A3 gate requires real-speed A500/Fast')
    if any(c.isspace() for c in str(out.relative_to(ROOT))):
        raise ValueError('GDB requires a scratch directory name without whitespace')
    if os.environ.get('EXTRA_ARGS'):
        raise ValueError('EXTRA_ARGS is not allowed in the fixed P13A3 gate')
    if os.environ.get('NTSC', '0') != '0' or os.environ.get('WHD_ARGS'):
        raise ValueError('P13A3 requires PAL and the original default options')
    for option in ('INTRO_STOCK_CLOCK', 'WC_NOMMU_CORE', 'WC_BASELINE_CACHE_MODEL',
                   'WC_CPU_SPEED', 'WC_INSTANT_BLITTER'):
        if os.environ.get(option, '0') not in ('', '0'):
            raise ValueError('diagnostic override not allowed: '+option)
    if not os.environ.get('FSUAE'):
        raise ValueError('set FSUAE to the local --ocs-pixels debugger build')
    out.mkdir(parents=True)
    os.chdir(ROOT)
    run = '../'+str(out.relative_to(ROOT))+'/run'
    env = dict(os.environ, FSUAE_RUN=run, WARP=os.environ.get('WARP','0') if a.calibrate else '0', WINDOW='front',
               JOY0='none', JOY1='none',
               DETERMINISTIC=os.environ.get('DETERMINISTIC', '1') if a.calibrate else '1',
               AMIGA_SETUP='a500', WC_VARIANT='ocs', WHD_ARGS='')
    server = Server('wc-gate',root=str(ROOT),run_dir='amiga/'+run,profile_window=False)
    g = None
    actions = []
    def command(text, timeout=60):
        answer = g.cmd(text,timeout=timeout)
        if any(x in answer for x in ('Invalid hex','Protocol error','Cannot access','Error')):
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
        key(1)
        until(h0+0x1f396, 'campaign menu entry O:1f396')
        key(0)
        until(h0+0x1f43c, 'menu ready O:1f43c')
        capture('menu')
        if a.simulator:
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
            until(h0+0x16c1a, 'pilot name prompt O:16c1a')
            until(h0+0x16992, 'name input loop O:16992')
            flag = command(f'x/bx {h0+0x3291c:#x}')
            if int(flag.rsplit(':', 1)[1].strip(), 16):
                until(h0+0x32e2c, 'name conversion published O:32e2c')
                until(h0+0x16992, 'name input after publication O:16992')
            capture('name')
        logfile = out/'run/fsuae/Cache/Logs/fs-uae.log.txt'
        options = dict(re.findall(r'Set option (\w+) = "([^"]*)"', logfile.read_text(errors='replace')))
        expected = dict(cpu_model='68000', chipset='ocs', chipmem_size='1', fastmem_size='4',
                        bogomem_size='0', cpu_speed='real', cpu_frequency='7093790',
                        cpu_cycle_exact='true', cpu_memory_cycle_exact='true', blitter_cycle_exact='true')
        for name, value in expected.items():
            if options.get(name) != value:
                raise ValueError('effective machine differs: '+name)
        boot = next((out/'run').glob('boot.*'))
        slave = (boot/'dh1/WingCommander/WingCommander.Slave').read_bytes()
        metadata = dict(layout, actions=actions, slave_sha256=hashlib.sha256(slave).hexdigest(),
                        whd_args=env['WHD_ARGS'], fsuae_sha256=hashlib.sha256(Path(env['FSUAE']).read_bytes()).hexdigest(),
                        machine='a500-ocs-512k-chip-4m-fast', warp=False, variant='ocs', effective=expected,
                        checkpoints=['origin', 'title', 'credits', 'menu'] +
                        (['simulator', 'name'] if a.simulator else []))
        (out/'result.json').write_text(json.dumps(metadata, indent=2)+'\n')
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
        subprocess.run(['/bin/bash',str(ROOT/'amiga/run.sh'),'stop'],env=env,check=True)

if __name__ == '__main__': main()
