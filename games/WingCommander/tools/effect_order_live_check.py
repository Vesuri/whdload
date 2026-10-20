#!/usr/bin/env python3
"""Bounded natural-intro explosion ordering check; no performance claim."""
import argparse
import json
import os
import re
import struct
import subprocess
import time
from pathlib import Path
import _amigaxdev
from amigaxdev.gdbserve import Server
from amigaxdev import barto
from ocs_reconstruct import ROOT, new_output
from variants import get


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('variant',choices=('ocs','cd32'));p.add_argument('build',type=Path)
    p.add_argument('--output',required=True)
    p.add_argument('--port',default='2495')
    a=p.parse_args();out=new_output(a.output);out.mkdir(parents=True)
    v=get(a.variant)
    if a.variant=='ocs':
        from ocs_runtime import locate
        slave=a.build/'WingCommander.Slave'
    else:
        from cd32_runtime import locate
        slave=a.build/'WingCommanderCD32.Slave'
    length=0x400000
    env=dict(os.environ,SLAVE=str(slave.resolve()),WC_VARIANT=a.variant,
             FSUAE_RUN='../'+str(out.relative_to(ROOT))+'/run',WARP='1',NTSC='0',WINDOW='front',DEBUG_PORT=a.port,
             JOY0='none',JOY1='none',DETERMINISTIC='1',AMIGA_SETUP='a1200-030',
             WHD_ARGS='CUSTOM5=1 DCACHE' if a.variant=='ocs' else 'CUSTOM5=0 CUSTOM3=1 CUSTOM4=0 DCACHE',
             EXTRA_ARGS='--fast_memory=4096',OCS_STOCK_CLOCK='0',INTRO_STOCK_CLOCK='0',
             WC_BASELINE_CACHE_MODEL='1')
    g=None
    def stop():
        nonlocal g
        if g:g.p.kill();g=None
        subprocess.run(['/bin/bash',str(ROOT/'amiga/run.sh'),'stop'],env=env,check=True)
    def boot():return Server('wc-cinematic',root=str(ROOT),run_dir='amiga/'+env['FSUAE_RUN'],profile_window=False).boot(env)
    def cmd(s,timeout=180):
        r=g.cmd(s,timeout=timeout)
        if any(x in r for x in ('Remote connection closed','Cannot access','Error','Invalid hex','Protocol error')):raise RuntimeError(r)
        return r
    def until(addr,condition=None,timeout=180):
        print("checkpoint",hex(addr),condition,flush=True)
        if condition:
            r=cmd(f'break *{addr:#x}\ncondition $bpnum {condition}\ncontinue\ndelete',timeout)
        else:r=cmd(f'break *{addr:#x}\ncontinue\ndelete',timeout)
        if 'Breakpoint' not in r:raise ValueError('checkpoint missed: '+r)
    def shot(name):
        path=out/(name+'.bin')
        cmd(f'monitor profile 1 "" "{path}"',60)
        (out/(name+'.png')).write_bytes(barto.load(str(path)).fields[-1].shot)
        path.unlink() # Keep the screenshot; no large instruction capture is needed.
    try:
        g=boot()
        snapshot=out/'calibration.bin'
        for _ in range(12):
            g.cont();time.sleep(1);g.stop()
            cmd(f'dump binary memory {snapshot.relative_to(ROOT)} 0x200000 {0x200000+length:#x}')
            try:layout=locate(snapshot.read_bytes());break
            except ValueError:pass
        else:raise ValueError('live segment chain not found')
        snapshot.unlink();stop()
        (out/'layout.json').write_text(json.dumps(layout,indent=2)+'\n')
        g=boot();h0,h1,_,_=layout['hunks']
        # Enter loaded game code before placing a conditional slave breakpoint.
        # Let the opening play naturally; no input or world-state edits.
        until(h0+(0x180c4 if a.variant=='ocs' else 0x1898a))
        sb=layout['slave'];ocs=a.variant=='ocs'
        sy=(json.loads((a.build/'build.json').read_text())['symbols'] if ocs else
            {n:int(o,16) for o,n in re.findall(r'^([0-9A-F]{8}) (\S+)$',(a.build/'slave.lst').read_text(),re.M)})
        def read(addr,n):
            p=out/'scratch.bin';cmd(f'dump binary memory {p.relative_to(ROOT)} {addr:#x} {addr+n:#x}');return p.read_bytes()
        condition=f'*(unsigned short*){h1+v.A4_BASE+v.A4["world_count"]:#x} >= 62'
        until(sb+sy['intro_draw'],condition)
        rows=[];ties=0
        for i in range(40):
            before=read(h1,v.HUNKS[1][2])
            until(sb+sy['intro_finish'])
            shown=read(h1,v.HUNKS[1][2])
            (out/f'{i:02d}-before.bin').write_bytes(before)
            (out/f'{i:02d}-shown.bin').write_bytes(shown)
            def state(raw):
                a4=v.A4_BASE
                kinds=struct.unpack_from('>64h',raw,a4+v.A4['object_class'])
                models=struct.unpack_from('>64h',raw,a4+(0xf86 if ocs else 0x17f8))
                return [(j,k,models[j]) for j,k in enumerate(kinds) if k]
            draw_off=v.A4_BASE+(-4326 if ocs else -4456)
            order=list(struct.unpack_from('>65h',shown,draw_off))
            order=order[:order.index(-1)]
            depth_off=v.A4_BASE+(0x252e if ocs else 0x24de)
            depths=struct.unpack_from('>64h',shown,depth_off)
            objects=dict((slot,(kind,model)) for slot,kind,model in state(shown))
            owners=v.A4_BASE+(0x3058 if ocs else 0x3a6a)
            for slot,(kind,model) in objects.items():
                parent=shown[owners+slot]
                if (kind,model)!=(5,49) or parent>=10 or objects.get(parent,(0,0))[0]!=12:continue
                if slot*2 not in order or parent*2 not in order or depths[slot]!=depths[parent]:continue
                ties+=1
                if order.index(parent*2)>order.index(slot*2):raise ValueError('ship drawn over tied death explosion')
            rows.append(dict(frame=i,order=order))
            if i%2==0:shot(f'{i:02d}')
            if i<39:until(sb+sy['intro_draw'])
        if not ties:raise ValueError('no visible explosion/ship depth ties observed')
        (out/'report.json').write_text(json.dumps(dict(passed=True,variant=a.variant,ties=ties,samples=rows),indent=2)+'\n')
    finally:stop()

if __name__=='__main__':main()
