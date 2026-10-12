#!/usr/bin/env python3
"""Whole-scene phase 4 profiles and change census; no stops inside scene windows."""
import argparse,hashlib,json,os,re,subprocess
from pathlib import Path
import _amigaxdev
from amigaxdev.gdbserve import Server
from amigaxdev import barto
from cd32_runtime import ROOT,BASE,locate
from intro_capture import SCENES


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',required=True);p.add_argument('--layout',required=True)
    p.add_argument('--audit',required=True);p.add_argument('--options',default='')
    a=p.parse_args();out=(ROOT/a.output).resolve()
    if (ROOT/'tmp').resolve() not in out.parents or out.exists():raise ValueError('new tmp output required')
    if os.environ.get('EXTRA_ARGS'):raise ValueError('fixed measurement configuration required')
    audit=json.loads((ROOT/a.audit).read_text())
    if audit['machine']!='a1200-fast' or audit['options']!=a.options or not audit['complete']:
        raise ValueError('matching completed cache audit required')
    m=json.loads((ROOT/a.layout).read_text());layout={k:m[k] for k in ('hunks','slave')};h=layout['hunks']
    cuts=[(0xf800d2,0),(h[3],1)]+[(h[n]+pc,i+2) for i,(n,pc,name) in enumerate(SCENES)]
    cuts += [(h[0]+0x1fdd6,100),(h[0]+0x1fe48,33),(h[0]+0x20214,34)]
    names=['reset','game-startup']+[name for _,_,name in SCENES]+[f'credits-{i:02d}' for i in range(18)]+['cycle-complete','menu']
    assert len(names)==35
    out.mkdir(parents=True);os.chdir(ROOT)
    config=out/'matrix.cfg';config.write_text(f'{h[0]:x} {len(cuts)}\n'+''.join(f'{pc:x} {index}\n' for pc,index in cuts))
    run='../'+str(out.relative_to(ROOT))+'/run'
    env=dict(os.environ,FSUAE_RUN=run,AMIGA_SETUP='a1200-fast',INTRO_STOCK_CLOCK='1',SLAVE='',
        WHD_ARGS='CUSTOM5=0 '+a.options,WARP='0',NTSC='0',WINDOW='front',JOY0='none',JOY1='none',
        DETERMINISTIC='1',WC_MATRIX_CONFIG=str(config),WC_MATRIX_DIR=str(out))
    for key in ('WC_OBSERVER_CONFIG','WC_OBSERVER_OUTPUT'):env.pop(key,None)
    g=None
    def cmd(s,timeout=60):
        result=g.cmd(s,timeout=timeout)
        if any(x in result for x in ('Remote connection closed','Cannot access','Error','Invalid hex','Protocol error')):raise RuntimeError(result)
        return result
    def until(pc):
        result=cmd(f'break *{pc:#x}\ncontinue\ndelete',900)
        if 'Breakpoint' not in result or f'0x{pc:x}' not in cmd('info registers pc'):raise ValueError('scene endpoint not reached')
    try:
        g=Server('wc-matrix',root=str(ROOT),run_dir='amiga/'+run,profile_window=False).boot(env)
        cpu=cmd('monitor wc-audit')
        if not all(word in cpu for word in ('model=68020','mmu=0','exact=1','unit=128')):raise ValueError('unvalidated backend/clock: '+cpu)
        until(h[0]+0x1fe48)
        print('all credits pages complete',flush=True)
        until(h[0]+0x1898a);cmd('monitor key 45 1')
        until(h[0]+0x20164);cmd('monitor key 45 0')
        until(h[0]+0x20214)
        live=cmd('monitor wc-audit')
        if int(re.search(r'cacr=([0-9a-f]+)',live)[1],16)!=audit['cacr']:raise ValueError('live/audit CACR mismatch')
        cmd('monitor trace-window-all')
        cmd(f'monitor profile 1 "" "{out}/menu.bin"',180)
        trace=barto.load(str(out/'menu.bin'));(out/'menu.png').write_bytes(trace.fields[-1].shot)
        cmd(f'dump binary memory {out.relative_to(ROOT)}/fast.bin {BASE:#x} {BASE+0x800000:#x}')
        if locate((out/'fast.bin').read_bytes())!=layout:raise ValueError('layout mismatch')
        for i in range(34):
            if not (out/f'scene-{i:02d}.aprof').is_file():raise ValueError('missing scene profile '+str(i))
        boot=next((out/'run').glob('boot.*'))
        result=dict(layout,complete=True,names=names,machine='a1200-fast',options=a.options,
            boot_cpu=cpu,live_cpu=live,audit_cacr=audit['cacr'],
            slave_sha256=hashlib.sha256((boot/'dh1/WingCommanderCD32/WingCommanderCD32.Slave').read_bytes()).hexdigest(),
            emulator_sha256=hashlib.sha256(Path(env['FSUAE']).read_bytes()).hexdigest())
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    finally:
        if g:g.p.kill()
        subprocess.run(['/bin/bash','amiga/run.sh','stop'],env=env,check=True)

if __name__=='__main__':main()
