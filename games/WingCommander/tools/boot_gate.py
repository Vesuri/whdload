#!/usr/bin/env python3
"""Phase 2 state-tape boot, adapted from Legends of Valour's A/B workflow.
Menu and optional simulator/name checkpoints; no phase 3 frame counter or profile.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import _amigaxdev
import wc_run
from amigaxdev import barto
from cd32_runtime import BASE, SIZES, ROOT, locate


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
    if not a.calibrate and (os.environ.get('WARP','0') != '0' or os.environ.get('AMIGA_SETUP','a1200-fast') != 'a1200-fast'):
        raise ValueError('phase 2 gate requires real-speed A1200-fast')
    if any(c.isspace() for c in str(out.relative_to(ROOT))):
        raise ValueError('GDB requires a scratch directory name without whitespace')
    if os.environ.get('EXTRA_ARGS'):
        raise ValueError('EXTRA_ARGS is not allowed in the fixed phase 2 gate')
    out.mkdir(parents=True)
    os.chdir(ROOT)
    env = wc_run.run_env(out, WARP=os.environ.get('WARP','0') if a.calibrate else '0', WINDOW='front',
               JOY0='none', JOY1='none',
               DETERMINISTIC=os.environ.get('DETERMINISTIC', '1') if a.calibrate else '1',
               AMIGA_SETUP=os.environ.get('AMIGA_SETUP','a1200-fast') if a.calibrate else 'a1200-fast')
    server = wc_run.server('wc-gate', env, profile_window=False)
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
    def until(address,label):
        command(f'break *{address:#x}')
        print('waiting for '+label,flush=True)
        answer = command('continue',timeout=600)
        g.running = False
        command('delete')
        pc = command('info registers pc')
        if f'0x{address:x}' not in pc or 'Breakpoint' not in answer:
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
                memory = dump(f'calibration-{attempt}.bin',BASE,BASE+0x800000)
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
        until(h0+0x1898a,'intro skip-input poll E:1898a')
        key(1)
        until(h0+0x1fbba,'credits entry E:1fbba')
        key(0)
        until(h0+0x1898a,'credits skip-input poll E:1898a')
        key(1)
        until(h0+0x20164,'campaign menu entry E:20164')
        key(0)
        until(h0+0x20214,'menu ready E:20214')
        memory = dump('fast.bin',BASE,BASE+0x800000)
        actual = locate(memory)
        if actual != layout: raise ValueError('calibration changed')
        for n,(base,size) in enumerate(zip(layout['hunks'],SIZES)):
            (out/f'h{n}.bin').write_bytes(memory[base-BASE:base-BASE+size])
        (out/'registers.txt').write_text(command('info registers'))
        trace = out/'screen.bin'
        command(f'monitor profile 1 "" "{trace}"',timeout=120)
        shot = barto.load(str(trace)).fields[-1].shot
        if not shot: raise ValueError('empty screenshot')
        (out/'menu.png').write_bytes(shot)
        boot = wc_run.drawer(env)
        slave = (boot/'WingCommanderCD32.Slave').read_bytes()
        metadata = dict(layout, actions=actions, slave_sha256=hashlib.sha256(slave).hexdigest(),
                        whd_args=env.get('WHD_ARGS',''),fsuae_sha256=hashlib.sha256(Path(env['FSUAE']).read_bytes()).hexdigest(),
                        machine='a1200-fast',warp=False)
        (out/'result.json').write_text(json.dumps(metadata,indent=2)+'\n')
        print('captured menu state and picture: '+str(out.relative_to(ROOT)),flush=True)
        if a.simulator:
            key(1,'44')
            until(h0+0x20226,'menu selection accepted E:20226')
            key(0,'44')
            until(h0+0x1744c,'name prompt E:1744c')
            until(h0+0x16fc6,'name input loop E:16fc6')
            memory = dump('name-fast.bin',BASE,BASE+0x800000)
            for n,(base,size) in enumerate(zip(layout['hunks'],SIZES)):
                (out/f'name-h{n}.bin').write_bytes(memory[base-BASE:base-BASE+size])
            trace = out/'name-screen.bin'
            command(f'monitor profile 1 \"\" \"{trace}\"',timeout=120)
            shot = barto.load(str(trace)).fields[-1].shot
            if not shot: raise ValueError('empty name screenshot')
            (out/'name.png').write_bytes(shot)
            metadata['actions'] = actions
            metadata['endpoint'] = 'name input loop E:16fc6'
            (out/'name-result.json').write_text(json.dumps(metadata,indent=2)+'\n')
            print('captured name prompt',flush=True)
    finally:
        (out/'actions.json').write_text(json.dumps(actions,indent=2)+'\n')
        if g: g.p.kill()
        wc_run.stop(env)

if __name__ == '__main__': main()
