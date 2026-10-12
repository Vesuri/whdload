#!/usr/bin/env python3
"""Phase 4 scene diagnostics; optional oracle stops independently read chunky input."""
import argparse,hashlib,json,os,re,subprocess
from pathlib import Path
import _amigaxdev
from amigaxdev.gdbserve import Server
from amigaxdev import barto
from cd32_runtime import ROOT,BASE,locate
from intro_capture import SCENES
from ceiling_fixture import load as load_ceiling_fixture


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',required=True);p.add_argument('--layout',required=True)
    p.add_argument('--ceiling-slave',help='equal-size VERIFY ceiling fixture built by reconstruct.py')
    p.add_argument('--audit',required=True);p.add_argument('--options',default='')
    p.add_argument('--machine',default='a1200-fast',choices=['a1200-fast','a1200-030','a1200-040','a1200-060'])
    cores=p.add_mutually_exclusive_group()
    cores.add_argument('--nommu-core',action='store_true')
    cores.add_argument('--mmu-core',action='store_true',help='030 MMU-interpreter counter capture; no instruction profiling')
    p.add_argument('--instant-blitter',action='store_true',help='VERIFY ceiling: complete blits immediately; requires audit readback')
    p.add_argument('--dma',action='store_true',help='experimental DMA summary, requires a --matrix-dma debugger build')
    p.add_argument('--warp',action='store_true',help='collect faster in host time; report all durations in emulated time')
    p.add_argument('--chunky-oracle', action='store_true', help='six independent GDB source snapshots; diagnostic run only')
    p.add_argument('--raw-chunky', action='store_true', help='retain every observed source buffer for independent census recomputation')
    p.add_argument('--no-profiles', action='store_true', help='counter/census control with aggregate profiling disabled')
    a=p.parse_args();out=(ROOT/a.output).resolve()
    if (ROOT/'tmp').resolve() not in out.parents or out.exists():raise ValueError('new tmp output required')
    if os.environ.get('EXTRA_ARGS'):raise ValueError('fixed measurement configuration required')
    if a.mmu_core and (a.machine!='a1200-030' or not a.no_profiles):
        raise ValueError('--mmu-core requires 030 and --no-profiles')
    if (a.nommu_core or a.mmu_core) != (a.machine!='a1200-fast'):
        raise ValueError('accelerated scene captures require an explicit core selector')
    if a.nommu_core and 'MMU' in a.options.upper().split():
        raise ValueError('WHDLoad MMU needs a separate MMU-core capture')
    if a.machine in ('a1200-040','a1200-060') and not a.no_profiles:
        raise ValueError('040/060 require --no-profiles; instruction costs are unavailable')
    audit=json.loads((ROOT/a.audit).read_text())
    if audit['machine']!=a.machine or audit.get('nommu_core',False)!=a.nommu_core or audit['options']!=a.options or not audit['complete']:
        raise ValueError('matching completed cache audit required')
    ceiling=None;slave=''
    if a.ceiling_slave:
        target,fixture=load_ceiling_fixture(a.ceiling_slave)
        ceiling=fixture['ceiling'];slave=str(target)
    if a.instant_blitter and ceiling!='control':raise ValueError('instant blitter requires the verified control slave')
    m=json.loads((ROOT/a.layout).read_text());layout={k:m[k] for k in ('hunks','slave')};h=layout['hunks']
    cuts=[(0xf800d2,0),(h[3],1)]+[(h[n]+pc,i+2) for i,(n,pc,name) in enumerate(SCENES)]
    cuts += [(h[0]+0x1fdd6,100),(h[0]+0x1fe48,33),(h[0]+0x20214,34)]
    names=['reset','game-startup']+[name for _,_,name in SCENES]+[f'credits-{i:02d}' for i in range(18)]+['cycle-complete','menu']
    assert len(names)==35
    out.mkdir(parents=True);os.chdir(ROOT)
    config=out/'matrix.cfg';config.write_text(f'{h[0]:x} {len(cuts)}\n'+''.join(f'{pc:x} {index}\n' for pc,index in cuts))
    run='../'+str(out.relative_to(ROOT))+'/run'
    env=dict(os.environ,FSUAE_RUN=run,AMIGA_SETUP=a.machine,INTRO_STOCK_CLOCK='1' if a.machine=='a1200-fast' else '0',
        WC_NOMMU_CORE='1' if a.nommu_core else '0',WC_INSTANT_BLITTER='1' if a.instant_blitter else '0',SLAVE=slave,
        WHD_ARGS='CUSTOM5=0 '+a.options,WARP='1' if a.warp else '0',NTSC='0',WINDOW='front',JOY0='none',JOY1='none',
        DETERMINISTIC='1',WC_MATRIX_DMA='1' if a.dma else '0',WC_MATRIX_CONFIG=str(config),WC_MATRIX_DIR=str(out),WC_MATRIX_RAW='1' if a.raw_chunky else '0',WC_MATRIX_PROFILES='0' if a.no_profiles else '1')
    for key in ('WC_OBSERVER_CONFIG','WC_OBSERVER_OUTPUT'):env.pop(key,None)
    g=None; chunky_oracle=[]
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
        fields=dict(re.findall(r'(\w+)=(\w+)',cpu))
        model={'a1200-fast':'68020','a1200-030':'68030','a1200-040':'68040','a1200-060':'68060'}[a.machine]
        expected=dict(model=model,mmu='68030' if a.mmu_core else '0',exact='1',memory_exact='1')
        if a.instant_blitter or 'immediate_blits' in fields:expected['immediate_blits']='1' if a.instant_blitter else '0'
        if a.machine=='a1200-fast':expected['unit']='128'
        if any(fields.get(k)!=v for k,v in expected.items()):raise ValueError('unexpected backend/clock: '+cpu)
        if a.chunky_oracle:
            until(h[3]+0xee0)
            for index in range(6):
                until(h[0]+0x32028)
                raw=cmd('printf "WC_CHUNK %u %u %x\\n", $d0 & 65535, $d3 & 65535, $a0')
                match=re.search(r'WC_CHUNK (\d+) (\d+) ([0-9a-f]+)',raw)
                if not match:raise ValueError('chunky source registers missing')
                width,height,address=int(match[1]),int(match[2]),int(match[3],16)
                if (width,height)!=(320,128):raise ValueError('unexpected Origin geometry')
                name=f'chunky-{index:02d}.bin'
                cmd(f'dump binary memory {out.relative_to(ROOT)}/{name} {address:#x} {address+width*height:#x}')
                chunky_oracle.append(dict(scene=4,index=index,width=width,height=height,file=name))
            print('captured six independent chunky-source snapshots',flush=True)
        until(h[0]+0x1fe48)
        print('all credits pages complete',flush=True)
        until(h[0]+0x1898a);cmd('monitor key 45 1')
        until(h[0]+0x20164);cmd('monitor key 45 0')
        until(h[0]+0x20214)
        live=cmd('monitor wc-audit')
        if int(re.search(r'cacr=([0-9a-f]+)',live)[1],16)!=audit['cacr']:raise ValueError('live/audit CACR mismatch')
        live_fields=dict(re.findall(r'(\w+)=(\w+)',live))
        if 'immediate_blits' in expected and live_fields.get('immediate_blits')!=expected['immediate_blits']:
            raise ValueError('live instant-blitter state mismatch')
        cmd('monitor trace-window-all')
        cmd(f'monitor profile 1 "" "{out}/menu.bin"',180)
        trace=barto.load(str(out/'menu.bin'));(out/'menu.png').write_bytes(trace.fields[-1].shot)
        cmd(f'dump binary memory {out.relative_to(ROOT)}/fast.bin {BASE:#x} {BASE+0x800000:#x}')
        if locate((out/'fast.bin').read_bytes())!=layout:raise ValueError('layout mismatch')
        for i in range(34):
            if not a.no_profiles and not (out/f'scene-{i:02d}.aprof').is_file():raise ValueError('missing scene profile '+str(i))
        if a.dma and not (out/'dma-events.txt').is_file():raise ValueError('DMA observer unavailable')
        boot=next((out/'run').glob('boot.*'))
        result=dict(layout,complete=True,names=names,machine=a.machine,nommu_core=a.nommu_core,mmu_core=a.mmu_core,ceiling=ceiling,instant_blitter=a.instant_blitter,dma=a.dma,host_warp=a.warp,clock_validated=a.machine=='a1200-fast',options=a.options,chunky_oracle=chunky_oracle,diagnostic_stops=a.chunky_oracle,raw_chunky=a.raw_chunky,profiles=not a.no_profiles,
            boot_cpu=cpu,live_cpu=live,audit_cacr=audit['cacr'],
            slave_sha256=hashlib.sha256((boot/'dh1/WingCommanderCD32/WingCommanderCD32.Slave').read_bytes()).hexdigest(),
            emulator_sha256=hashlib.sha256(Path(env['FSUAE']).read_bytes()).hexdigest())
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    finally:
        if g:g.p.kill()
        subprocess.run(['/bin/bash','amiga/run.sh','stop'],env=env,check=True)

if __name__=='__main__':main()
