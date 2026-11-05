#!/usr/bin/env python3
"""Bounded live intro contact-pose and screenshot check; no performance claim."""
import argparse
import json
import os
import re
import struct
import subprocess
import time
from pathlib import Path
import _amigaxdev
import wc_run
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
    env=wc_run.run_env(out,variant=a.variant,SLAVE=str(slave.resolve()),
             WARP='1',NTSC='0',WINDOW='front',DEBUG_PORT=a.port,
             JOY0='none',JOY1='none',DETERMINISTIC='1',AMIGA_SETUP='a1200-030',
             WHD_ARGS='CUSTOM5=1 DCACHE' if a.variant=='ocs' else 'CUSTOM5=0 CUSTOM3=1 CUSTOM4=0 DCACHE',
             EXTRA_ARGS='--fast_memory=4096',OCS_STOCK_CLOCK='0',INTRO_STOCK_CLOCK='0',
             WC_BASELINE_CACHE_MODEL='1')
    g=None
    def stop():
        nonlocal g
        if g:g.p.kill();g=None
        wc_run.stop(env)
    def boot():return wc_run.server('wc-cinematic', env, profile_window=False).boot(env)
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
        condition=f'*(unsigned char*){sb+sy["timing_intro_shot_targets"]+10:#x} == 1 && *(unsigned char*){sb+sy["timing_intro_shot_steps"]+10:#x} == 0'
        until(sb+sy['intro_draw'],condition)
        rows=[]
        for _ in range(3):
            before=read(h1,v.HUNKS[1][2])
            until(sb+sy['intro_finish'])
            shown=read(h1,v.HUNKS[1][2])
            def pos(raw,slot):return struct.unpack_from('>3i',raw,v.A4_BASE+v.A4['position']+slot*12)
            contact=read(sb+sy['timing_intro_shot_targets']+10,1)[0]
            assert contact==1,'impact interval ended before sampling'
            want=tuple(x-y for x,y in zip(pos(before,10),pos(before,1)))
            got=tuple(x-y for x,y in zip(pos(shown,10),pos(shown,1)))
            assert got==want,('bolt passed its native contact',got,want)
            rows.append(dict(bolt=pos(shown,10),target=pos(shown,1),relative=got))
            if len(rows)<3:until(sb+sy['intro_draw'])
        shot('contact')
        assert len({tuple(r['target']) for r in rows})>1,'contact target did not move between renders'
        (out/'report.json').write_text(json.dumps(dict(passed=True,variant=a.variant,layout=layout,samples=rows),indent=2)+'\n')
        print('PASS',a.variant,'live moving contact',flush=True)
    finally:stop()

if __name__=='__main__':main()
