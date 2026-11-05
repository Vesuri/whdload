#!/usr/bin/env python3
"""Bounded CD32 direct-flight windows using the shared key route and profiler."""
import argparse,hashlib,json,os,re,subprocess
from pathlib import Path
import _amigaxdev
from amigaxdev.gdbserve import Server
from amigaxdev import barto
from cd32_runtime import ROOT,BASE,locate


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',required=True);p.add_argument('--layout',required=True)
    p.add_argument('--fixture',required=True)
    p.add_argument('--machine',choices=('a1200-fast','a1200-030'),default='a1200-fast')
    p.add_argument('--controls',action='store_true',help='additional fire, turn, afterburner and pause windows')
    p.add_argument('--no-states',action='store_true',help='observer overhead control')
    a=p.parse_args();out=(ROOT/a.output).resolve();slave=(ROOT/a.fixture).resolve()
    if (ROOT/'tmp').resolve() not in out.parents or out.exists():raise ValueError('new tmp output required')
    if (ROOT/'tmp').resolve() not in slave.parents:raise ValueError('fixture must be below tmp')
    fixture=json.loads((slave.parent/'build.json').read_text())
    if not fixture.get('direct_flight') or hashlib.sha256(slave.read_bytes()).hexdigest()!=fixture['sha256']:raise ValueError('unverified fixture')
    if os.environ.get('EXTRA_ARGS'):raise ValueError('fixed configuration required')
    meta=json.loads((ROOT/a.layout).read_text());layout={k:meta[k] for k in ('hunks','slave')};h=layout['hunks'];s=layout['slave']
    if any(c.isspace() for c in str(out.relative_to(ROOT))):raise ValueError('GDB requires a scratch name without whitespace')
    out.mkdir(parents=True);os.chdir(ROOT)
    pcs=[h[0]+x for x in (0x698,0x2a8,0x2da,0x2f4,0x3378e,0x34162,0x27810,0x32028,0x7b4e,0x680e,0x1568,0x16084,0x2cb56,0x80e6,0x7d18,0xa76,0x878)]
    pcs += [s+x for x in (0x178e,0x1792,0x17b8,0x17e6)]
    config=out/'observer.cfg';config.write_text(' '.join(f'{v:x}' for v in [h[0],h[1],h[3]]+pcs)+'\n')
    matrix=out/'matrix.cfg';matrix.write_text(f'{h[0]:x} 1\n{h[0]+0x698:x} 0\n')
    run='../'+str(out.relative_to(ROOT))+'/run'
    env={k:v for k,v in os.environ.items() if not k.startswith(('WC_OBSERVER_','WC_MATRIX_','WC_STATE_'))}
    env.update(FSUAE_RUN=run,SLAVE=str(slave),AMIGA_SETUP=a.machine,
        INTRO_STOCK_CLOCK='1' if a.machine=='a1200-fast' else '0',WC_NOMMU_CORE='0' if a.machine=='a1200-fast' else '1',
        WHD_ARGS='CUSTOM2=2 CUSTOM3=1 CUSTOM4=0 CUSTOM5=0',WARP='1',NTSC='0',WINDOW='front',JOY0='none',JOY1='none',DETERMINISTIC='1',WC_INSTANT_BLITTER='0',
        WC_OBSERVER_CONFIG=str(config),WC_OBSERVER_OUTPUT=str(out/'events.txt'),WC_MATRIX_CONFIG=str(matrix),WC_MATRIX_DIR=str(out),WC_MATRIX_PROFILES='0')
    if not a.no_states:env.update(WC_STATE_PC=f'{h[0]+0x698:x}',WC_STATE_OUTPUT=str(out/'states.bin'))
    g=None;windows=[];actions=[]
    def cmd(text,timeout=60):
        r=g.cmd(text,timeout=timeout)
        if any(x in r for x in ('Error','Cannot access','Invalid hex','Protocol error','Remote connection closed')):raise RuntimeError(r)
        return r
    def dump(name):
        path=out/name;cmd(f'dump binary memory {path.relative_to(ROOT)} {BASE:#x} {BASE+0x800000:#x}')
        if locate(path.read_bytes())!=layout:raise ValueError('live layout changed')
    def key(code,pressed):
        cmd(f'monitor key {code} {pressed}');actions.append(dict(key=code,pressed=pressed,after_window=len(windows)))
    def window(name,fields=100):
        before=len((out/'events.txt').read_text().splitlines())-1
        reply=cmd('monitor aprof start');aprof='E01' not in reply and 'E02' not in reply
        trace=out/(name+'.bin');cmd(f'monitor profile {fields} "" "{trace}"',180)
        if aprof:cmd(f'monitor aprof stop {out}/{name}.aprof')
        after=len((out/'events.txt').read_text().splitlines())-1
        t=barto.load(str(trace))
        if len(t.fields)!=fields or not t.fields[-1].shot:raise ValueError('incomplete trace')
        (out/(name+'.png')).write_bytes(t.fields[-1].shot)
        windows.append(dict(name=name,first_event=before,end_event=after,fields=len(t.fields),aprof=aprof))
        print(f'captured {name}: {len(t.fields)} fields',flush=True)
    try:
        g=Server('wc-flight',root=str(ROOT),run_dir='amiga/'+run,profile_window=False).boot(env)
        boot=cmd('monitor wc-audit');audit=dict(re.findall(r'(\w+)=(\w+)',boot))
        expected=dict(model='68020' if a.machine=='a1200-fast' else '68030',mmu='0',unit='128' if a.machine=='a1200-fast' else '36',exact='1',memory_exact='1',immediate_blits='0')
        if any(audit.get(k)!=v for k,v in expected.items()):raise ValueError(boot)
        if 'key-raw-v1' not in cmd('monitor inputcaps'):raise ValueError('native keys unavailable')
        pc=h[0]+0x698
        reply=cmd(f'break *{pc:#x}\ncontinue\ndelete',120)
        if 'Breakpoint' not in reply or f'0x{pc:x}' not in cmd('info registers pc'):raise ValueError('flight not reached')
        dump('start-fast.bin');live=cmd('monitor wc-audit')
        cmd('monitor trace-window-all')
        for i in range(3):window(f'coast-{i}')
        if a.controls:
            key('40',1);window('fire');key('40',0)
            key('4e',1);window('turn');key('4e',0)
            key('42',1);window('afterburner');key('42',0)
            key('19',1)
            pause=h[0]+0x878
            reply=cmd(f'break *{pause:#x}\ncontinue\ndelete',60)
            if 'Breakpoint' not in reply:raise ValueError('pause not reached')
            key('19',0);dump('pause-start-fast.bin');window('pause',10);dump('pause-end-fast.bin')
            key('40',1)
            reply=cmd(f'break *{pc:#x}\ncontinue\ndelete',60)
            if 'Breakpoint' not in reply:raise ValueError('resume not reached')
            key('40',0);window('resume',20)
        dump('end-fast.bin')
        result=dict(layout,fixture=fixture,machine=a.machine,boot_cpu=boot,live_cpu=live,windows=windows,actions=actions,
                    state_snapshots=not a.no_states,complete=True,emulator_sha256=hashlib.sha256(Path(env['FSUAE']).read_bytes()).hexdigest())
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    finally:
        (out/'actions.json').write_text(json.dumps(actions,indent=2)+'\n')
        if g:g.p.kill()
        subprocess.run(['/bin/bash','amiga/run.sh','stop'],env=env,check=True)

if __name__=='__main__':main()
