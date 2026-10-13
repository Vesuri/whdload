#!/usr/bin/env python3
"""Bounded flight captures of the experimental hybrid scheduler; no acceptance implied."""
import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
import _amigaxdev
from amigaxdev.gdbserve import Server
from cd32_runtime import ROOT, BASE, locate


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fixture',required=True)
    p.add_argument('--layout',required=True)
    p.add_argument('--output',required=True)
    p.add_argument('--windows',type=int,default=4)
    p.add_argument('--machine',choices=('a1200-fast','a1200-030'),default='a1200-fast')
    p.add_argument('--ntsc',action='store_true')
    p.add_argument('--off',action='store_true')
    p.add_argument('--held-key',default='40',help='raw key held during flight; hexadecimal')
    p.add_argument('--presentation-states',action='store_true',help='snapshot on publication instead of world return')
    p.add_argument('--trace',action='store_true',help='retain full instruction profiles as well as observer events')
    p.add_argument('--schedule',choices=('normal','slow','one-field'),default='normal')
    p.add_argument('--pause',action='store_true',help='include a real native pause and resume')
    a=p.parse_args()
    if not 0<=int(a.held_key,16)<128:p.error('invalid raw key')
    out=(ROOT/a.output).resolve();slave=(ROOT/a.fixture).resolve()
    if (ROOT/'tmp').resolve() not in out.parents or out.exists() or not 1<=a.windows<=30:
        raise ValueError('new bounded output in tmp required')
    fixture=json.loads((slave.parent/'build.json').read_text())
    if not fixture.get('timing') or fixture['sha256']!=hashlib.sha256(slave.read_bytes()).hexdigest():
        raise ValueError('verified timing fixture required')
    if fixture.get('schedule','normal')!=a.schedule:raise ValueError('schedule must match the pinned fixture')
    if a.schedule!='normal' and not fixture.get('timing_verify'):raise ValueError('diagnostic schedule requires a VERIFY build')
    layout=json.loads((ROOT/a.layout).read_text());h=layout['hunks'];s=layout['slave']
    symbols={name:int(off,16) for off,name in re.findall(r'^([0-9A-F]{8}) (\S+)$',(slave.parent/'slave.lst').read_text(),re.M)}
    out.mkdir(parents=True);os.chdir(ROOT)
    pcs=[h[0]+i for i in (0x698,0x2a8,0x2da,0x3378e,0x34162,0x878)]
    pcs += [s+symbols[k] for k in ('timing_loop','timing_world_done','timing_leave','timing_rebase')]
    config=out/'observer.cfg';config.write_text(' '.join(f'{v:x}' for v in [h[0],h[1],h[3]]+pcs)+'\n')
    env={k:v for k,v in os.environ.items() if not k.startswith(('WC_OBSERVER_','WC_MATRIX_','WC_STATE_'))}
    run='../'+str(out.relative_to(ROOT))+'/run'
    env.update(FSUAE_RUN=run,SLAVE=str(slave),AMIGA_SETUP=a.machine,INTRO_STOCK_CLOCK='1' if a.machine=='a1200-fast' else '0',
        WC_NOMMU_CORE='0',WHD_ARGS=f'CUSTOM1={0 if a.off else 3} CUSTOM2=2 CUSTOM3=1 CUSTOM4=0 CUSTOM5=0',
        WARP='1',NTSC='1' if a.ntsc else '0',WINDOW='front',JOY0='none',JOY1='none',DETERMINISTIC='1',WC_INSTANT_BLITTER='0',
        WC_OBSERVER_CONFIG=str(config),WC_OBSERVER_OUTPUT=str(out/'events.txt'),WC_STATE_OUTPUT=str(out/'states.bin'),WC_STATE_PC=f'{h[0]+(0x3378e if a.presentation_states else 0x2da):x}')
    # Match the established phase-8 instrument configuration. Shared presets
    # now enable emulated 030 data caching, which was off in that baseline.
    if a.machine=='a1200-030':env['WC_BASELINE_CACHE_MODEL']='1'
    g=None;windows=[]
    def cmd(text,timeout=180):
        r=g.cmd(text,timeout=timeout)
        if any(e in r for e in ('Error','Cannot access','Invalid hex','Protocol error','Remote connection closed','E01')):raise RuntimeError(r)
        return r
    def dump(name):
        cmd(f'dump binary memory {out.relative_to(ROOT)}/{name}.bin {BASE:#x} {BASE+0x800000:#x}')
        if locate((out/(name+'.bin')).read_bytes())!=layout:raise ValueError('live layout mismatch')
    def window(name,fields=100):
        first=len((out/'events.txt').read_text().splitlines())-1
        if a.trace:cmd(f'monitor profile {fields} "" "{out}/{name}.bin"')
        else:
            cmd(f'break *{h[0]+0x34162:#x}')
            number=re.search(r'(\d+)\s+breakpoint',cmd('info breakpoints')).group(1)
            cmd(f'ignore {number} {fields-1}\ncontinue\ndelete')
        end=len((out/'events.txt').read_text().splitlines())-1
        windows.append(dict(name=name,first_event=first,end_event=end,fields=fields))
        print(f'{out.name}: {name}',flush=True)
    try:
        g=Server('wc-timing',root=str(ROOT),run_dir='amiga/'+run,profile_window=False).boot(env)
        pc=h[0]+0x698
        cmd(f'break *{pc:#x}\ncontinue\ndelete')
        if f'0x{pc:x}' not in cmd('info registers pc'):raise ValueError('flight not reached')
        dump('start-fast')
        live=cmd('monitor wc-audit')
        audit=dict(re.findall(r'(\w+)=(\w+)',live))
        expected=dict(model='68020' if a.machine=='a1200-fast' else '68030',
                      mmu='0' if a.machine=='a1200-fast' else '68030',
                      exact='1',memory_exact='1',blitter_exact='1',immediate_blits='0',
                      unit='128' if a.machine=='a1200-fast' else '36')
        if any(audit.get(k)!=v for k,v in expected.items()):raise ValueError('CPU timing configuration mismatch: '+live)
        config_text=(out/'run/fsuae/Cache/Logs/debug.uae').read_text()
        if 'cpu_data_cache=false' not in config_text:raise ValueError('emulated data cache differs from established baseline')
        cmd(f'monitor key {a.held_key} 1')
        for i in range(a.windows):window(f'window-{i}')
        if a.pause:
            cmd(f'monitor key {a.held_key} 0')
            cmd('monitor key 19 1')
            cmd(f'break *{h[0]+0x878:#x}\ncontinue\ndelete')
            cmd('monitor key 19 0')
            dump('pause-start')
            window('pause',20)
            dump('pause-end')
            cmd('monitor key 40 1')
            endpoint=h[0]+0x2da if a.off else s+symbols['timing_world_done']
            cmd(f'break *{endpoint:#x}\ncontinue\ndelete')
            cmd('monitor key 40 0')
            window('resume',100)
        dump('end-fast')
        result=dict(layout,fixture=fixture,symbols=symbols,windows=windows,live_cpu=live,ntsc=a.ntsc,off=a.off,held_key=a.held_key,pause=a.pause,presentation_states=a.presentation_states,schedule=a.schedule,trace=a.trace,emulator_data_cache=False,fsuae_sha256=hashlib.sha256(Path(env['FSUAE']).read_bytes()).hexdigest(),complete=True)
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    finally:
        if g:g.p.kill()
        subprocess.run(['/bin/bash','amiga/run.sh','stop'],env=env,check=True)


if __name__=='__main__':main()
