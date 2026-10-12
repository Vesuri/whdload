#!/usr/bin/env python3
"""Phase 6 full intro ledger, converter latencies and optional native twin check."""
import argparse, hashlib, json, os, re, subprocess
from pathlib import Path
import _amigaxdev
from amigaxdev.gdbserve import Server
from cd32_runtime import ROOT, BASE, locate
from intro_capture import SCENES
from render_fixture import load as load_render_fixture
from amigaxdev import barto


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',required=True); p.add_argument('--layout',required=True)
    p.add_argument('--machine',choices=('a1200-fast','a1200-030','a1200-040','a1200-060'),default='a1200-fast')
    p.add_argument('--fixture',required=True)
    p.add_argument('--options',default='CUSTOM1=2')
    p.add_argument('--mmu',action='store_true')
    a=p.parse_args(); out=(ROOT/a.output).resolve()
    if (ROOT/'tmp').resolve() not in out.parents or out.exists(): raise ValueError('new tmp output required')
    if os.environ.get('EXTRA_ARGS'): raise ValueError('fixed timing configuration required')
    if a.mmu and a.machine!='a1200-030': raise ValueError('MMU capture requires 030')
    if any(x.startswith('CUSTOM5') for x in a.options.upper().split()): raise ValueError('capture fixes CUSTOM5=0')
    slave,fixture=load_render_fixture(a.fixture)
    syms={name:int(off,16) for off,name in re.findall(r'^([0-9A-F]{8}) (\S+)$',(slave.parent/'slave.lst').read_text(),re.M)}
    meta=json.loads((ROOT/a.layout).read_text()); layout={k:meta[k] for k in ('hunks','slave')}; h=layout['hunks']; s=layout['slave']
    pcs=[0xf800d2,h[3]]+[h[n]+pc for n,pc,_ in SCENES]
    pcs += [h[0]+pc for pc in (0x3378e,0x3379a,0x33ce2,0x34162,0x27810,0x1fd00,0x1fdd6,0x1fe48,0x20214)]
    pcs += [s+pc for pc in (0x1774,0x1784,0x178e,0x1792,0x17b8,0x17e6)]
    pcs += [s+off for name,off in syms.items() if name.startswith('kalms_') or name in ('render_converted','render_wait','render_wait_done')]
    pcs += [s+off for off in (0x17f6,0x195e,0x1ac6,0x17a6)]
    out.mkdir(parents=True); os.chdir(ROOT)
    config=out/'observer.cfg'; config.write_text(' '.join(f'{v:x}' for v in [h[0],h[1],h[3]]+pcs)+'\n')
    run='../'+str(out.relative_to(ROOT))+'/run'
    env=dict(os.environ,FSUAE_RUN=run,FSUAE=os.environ['FSUAE'],SLAVE=str(slave),
             AMIGA_SETUP=a.machine,INTRO_STOCK_CLOCK='1' if a.machine=='a1200-fast' else '0',WC_NOMMU_CORE='0' if a.machine=='a1200-fast' or a.mmu else '1',
             WHD_ARGS='CUSTOM5=0 '+a.options+(' MMU' if a.mmu else ''),
             WARP='1',NTSC='0',WINDOW='front',JOY0='none',JOY1='none',DETERMINISTIC='1',
             WC_INSTANT_BLITTER='0',WC_OBSERVER_CONFIG=str(config),WC_OBSERVER_OUTPUT=str(out/'events.txt'))
    for key in list(env):
        if key.startswith('WC_MATRIX_'): del env[key]
    g=None
    def cmd(text,timeout=60):
        r=g.cmd(text,timeout=timeout)
        if any(x in r for x in ('Remote connection closed','Cannot access','Error','Invalid hex','Protocol error')): raise RuntimeError(r)
        return r
    def until(pc):
        r=cmd(f'break *{pc:#x}\ncontinue\ndelete',900)
        if 'Breakpoint' not in r or f'0x{pc:x}' not in cmd('info registers pc'): raise ValueError('endpoint missed')
    try:
        g=Server('wc-intro-timing',root=str(ROOT),run_dir='amiga/'+run,profile_window=False).boot(env)
        boot=cmd('monitor wc-audit')
        fields=dict(re.findall(r'(\w+)=(\w+)',boot))
        expected=dict(model={'a1200-fast':'68020','a1200-030':'68030','a1200-040':'68040','a1200-060':'68060'}[a.machine],mmu='68030' if a.mmu else '0',unit='128' if a.machine=='a1200-fast' else '72' if a.machine=='a1200-040' else '36',exact='1',memory_exact='1',immediate_blits='0')
        if any(fields.get(k)!=v for k,v in expected.items()): raise ValueError('unexpected timing backend: '+boot)
        until(h[0]+0x1fe48)
        print('full title/credits cycle complete',flush=True)
        until(h[0]+0x1898a); cmd('monitor key 45 1')
        until(h[0]+0x20164); cmd('monitor key 45 0')
        until(h[0]+0x20214)
        live=cmd('monitor wc-audit')
        cmd('monitor trace-window-all')
        cmd(f'monitor profile 1 \"\" \"{out}/menu.bin\"',180)
        trace=barto.load(str(out/'menu.bin')); (out/'menu.png').write_bytes(trace.fields[-1].shot)
        cmd(f'dump binary memory {out.relative_to(ROOT)}/fast.bin {BASE:#x} {BASE+0x800000:#x}')
        if locate((out/'fast.bin').read_bytes())!=layout: raise ValueError('live layout differs')
        actual=next((out/'run').glob('boot.*'))/'dh1/WingCommanderCD32/WingCommanderCD32.Slave'
        sha=hashlib.sha256(actual.read_bytes()).hexdigest()
        if fixture and sha!=fixture['sha256']: raise ValueError('boot fixture mismatch')
        verified=0
        if fixture.get('render_verify'):
            verified=int.from_bytes((out/'fast.bin').read_bytes()[s-BASE+syms['render_verified']:s-BASE+syms['render_verified']+4],'big')
            if verified<100: raise ValueError('native twin did not execute')
        selected=int.from_bytes((out/'fast.bin').read_bytes()[s-BASE+syms['render_selected']:s-BASE+syms['render_selected']+2],'big') if 'render_selected' in syms else None
        result=dict(layout,selected_converter=selected,verified_frames=verified,options=a.options,mmu=a.mmu,symbols=syms,complete=True,machine=a.machine,fixture=fixture,custom5=0,boot_cpu=boot,live_cpu=live,slave_sha256=sha,emulator_sha256=hashlib.sha256(Path(env['FSUAE']).read_bytes()).hexdigest())
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    finally:
        if g: g.p.kill()
        subprocess.run(['/bin/bash','amiga/run.sh','stop'],env=env,check=True)

if __name__=='__main__': main()
