#!/usr/bin/env python3
"""Unskipped English CD32 intro: read-only publication ledger and state milestones."""
import argparse, hashlib, json, os, subprocess
from pathlib import Path
import _amigaxdev
from amigaxdev.gdbserve import Server
from amigaxdev import barto
from cd32_runtime import ROOT, BASE, locate

# Scene entries in hunk 3, followed by the main title/credits state machine.
SCENES = [(3,0xd12,'origin-load'), (3,0xeb0,'origin-reveal'),
          (3,0xee0,'origin-animation'), (3,0xfb4,'origin-expression'),
          (3,0x10cc,'origin-separation'), (3,0x11a8,'origin-flight'),
          (3,0x12c0,'origin-particles'), (3,0xde0,'origin-fade'),
          (0,0x1fbba,'title-load'), (0,0x1fcfc,'title-animation'),
          (0,0x1fd3a,'title-arrival'), (0,0x1fd46,'title-departure'),
          (0,0x1fd96,'credits-load')]


def check_clock(out):
    import re
    log=(out/'run/fsuae/Cache/Logs/fs-uae.log.txt').read_text()
    units=re.findall(r'CPU cycleunit: (\d+)',log)
    if not units or set(units)!={'128'}:
        raise ValueError('stock A1200 clock was not applied: '+str(units))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',required=True);p.add_argument('--layout',required=True)
    p.add_argument('--trace-fields',type=int,default=20)
    a=p.parse_args()
    out=(ROOT/a.output).resolve()
    if (ROOT/'tmp').resolve() not in out.parents or out.exists(): raise ValueError('new output below tmp/ required')
    if os.environ.get('EXTRA_ARGS') or os.environ.get('WARP','0')!='0': raise ValueError('fixed real-speed preset required')
    if not 1 <= a.trace_fields <= 100: raise ValueError('trace fields must be 1..100')
    if any(c.isspace() for c in str(out.relative_to(ROOT))): raise ValueError('scratch name cannot contain whitespace')
    os.chdir(ROOT)
    out.mkdir(parents=True)
    layout=json.loads((ROOT/a.layout).read_text());h=layout['hunks'];h0,h1,h3=h[0],h[1],h[3]
    pcs=[h0+x for x in (0x3378e,0x3379a,0x33ce2,0x34162,0x1fdd6,0x1fe48,0x20214)]
    pcs += [0xf800d2, h3]
    pcs += [h[n]+offset for n,offset,_ in SCENES]
    config=out/'observer.cfg'; config.write_text(' '.join(f'{v:x}' for v in [h0,h1,h3]+pcs)+'\n')
    run='../'+str(out.relative_to(ROOT))+'/run'
    env=dict(os.environ, FSUAE_RUN=run, WARP='0', NTSC='0', WINDOW='front', JOY0='none',JOY1='none',
             DETERMINISTIC='1', AMIGA_SETUP='a1200-fast', WHD_ARGS='CUSTOM5=0', SLAVE='',
             INTRO_STOCK_CLOCK='1',
             WC_OBSERVER_CONFIG=str(config), WC_OBSERVER_OUTPUT=str(out/'events.txt'))
    g=None; milestones=[]
    def cmd(s,timeout=60):
        r=g.cmd(s,timeout=timeout)
        if any(x in r for x in ('Remote connection closed','Cannot access','Error','Invalid hex','Protocol error')): raise RuntimeError(r)
        return r
    def until(addr, condition=None):
        commands=f'break *{addr:#x}\n'
        if condition: commands += 'condition $bpnum '+condition+'\n'
        r=cmd(commands+'continue\ndelete',600)
        if 'Breakpoint' not in r or f'0x{addr:x}' not in cmd('info registers pc'): raise ValueError('checkpoint missed')
    def capture(name, fields=1):
        # Native observer remains active across debugger screenshot intervals.
        regs=cmd('info registers');(out/(name+'-registers.txt')).write_text(regs)
        cmd(f'dump binary memory {out.relative_to(ROOT)}/{name}-fast.bin {BASE:#x} {BASE+0x800000:#x}')
        mem=(out/(name+'-fast.bin')).read_bytes()
        if locate(mem)!=layout: raise ValueError('live layout changed')
        path=out/(name+'.bin')
        cmd(f'monitor profile {fields} "" "{path}"',240)
        t=barto.load(str(path))
        if len(t.fields)!=fields or not t.fields[-1].shot: raise ValueError('incomplete trace')
        (out/(name+'.png')).write_bytes(t.fields[-1].shot)
        milestones.append(name)
        (out/'milestones.json').write_text(json.dumps(milestones,indent=2)+'\n')
        print('captured '+name,flush=True)
    try:
        g=Server('wc-intro',root=str(ROOT),run_dir='amiga/'+run,profile_window=False).boot(env)
        check_clock(out)
        if 'profile-window 00000000 7fffffff' not in cmd('monitor trace-window-all'): raise ValueError('explicit profiler window unavailable')
        for n,offset,name in SCENES:
            until(h[n]+offset, '($d2 & 65535) == 185' if name=='title-arrival' else None)
            if not (out/'events.txt').is_file() or (out/'events.txt').stat().st_size==0:
                raise ValueError('read-only observer is unavailable')
            if name == 'credits-load': continue
            # Capture the first completed publication belonging to the new scene.
            until(h0+0x3379a)
            capture(name,a.trace_fields if name=='origin-animation' else 1)
        for page in range(18):
            until(h0+0x1fdd6)
            # d5 is the title/credits page index; don't silently skip a page.
            r=cmd('printf "PAGE %u\\n", $d5 & 65535')
            if f'PAGE {page}' not in r: raise ValueError('credits page mismatch: '+r)
            until(h0+0x3379a)
            capture(f'credits-{page:02d}',a.trace_fields if page==0 else 1)
        until(h0+0x1fe48) # all eighteen timed pages finished; about to repeat
        print('complete title/credits cycle; pressing Escape at next input poll',flush=True)
        until(h0+0x1898a)
        cmd('monitor key 45 1')
        until(h0+0x20164)
        cmd('monitor key 45 0')
        until(h0+0x20214)
        capture('menu')
        boot=next((out/'run').glob('boot.*'))
        slave=boot/'dh1/WingCommanderCD32/WingCommanderCD32.Slave'
        report=dict(layout,milestones=milestones,trace_fields=a.trace_fields,
                    slave_sha256=hashlib.sha256(slave.read_bytes()).hexdigest(),
                    emulator_sha256=hashlib.sha256(Path(env['FSUAE']).read_bytes()).hexdigest(),
                    machine='a1200-fast',cpu_multiplier=4,cpu_frequency=0,custom5=0,warp=False,complete=True,
                    input='Escape only after all 18 credits pages complete')
        (out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    finally:
        if g:g.p.kill()
        subprocess.run(['/bin/bash',str(ROOT/'amiga/run.sh'),'stop'],env=env,check=True)

if __name__=='__main__':main()
