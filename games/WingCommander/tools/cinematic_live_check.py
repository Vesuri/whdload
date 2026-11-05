#!/usr/bin/env python3
"""Bounded running-pilot scene fixture and native pixel-replay inputs."""
import argparse
import hashlib
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
    p.add_argument('--timing',action='store_true',help='sample field-paced running motion')
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
             WARP='1',NTSC='0',WINDOW='front',
             JOY0='none',JOY1='none',DETERMINISTIC='1',AMIGA_SETUP='a1200-030',
             WHD_ARGS='CUSTOM5=1 DCACHE' if a.variant=='ocs' else 'CUSTOM5=0 DCACHE',
             EXTRA_ARGS='--fast_memory=4096',OCS_STOCK_CLOCK='0',INTRO_STOCK_CLOCK='0',
             WC_BASELINE_CACHE_MODEL='1')
    g=None
    def stop():
        nonlocal g
        if g:g.p.kill();g=None
        wc_run.stop(env)
    def boot():return wc_run.server('wc-cinematic', env, profile_window=False).boot(env)
    def cmd(s,timeout=60):
        r=g.cmd(s,timeout=timeout)
        if any(x in r for x in ('Remote connection closed','Cannot access','Error','Invalid hex','Protocol error')):raise RuntimeError(r)
        return r
    def until(addr,condition=None):
        print("checkpoint",hex(addr),condition,flush=True)
        if condition:
            r=cmd(f'break *{addr:#x}\ncondition $bpnum {condition}\ncontinue\ndelete',60)
        else:r=cmd(f'break *{addr:#x}\ncontinue\ndelete',60)
        if 'Breakpoint' not in r:raise ValueError('checkpoint missed: '+r)
    def shot(name):
        path=out/(name+'.bin')
        cmd(f'monitor profile 1 "" "{path}"',60)
        (out/(name+'.png')).write_bytes(barto.load(str(path)).fields[-1].shot)
        path.unlink() # Keep the screenshot; no large instruction capture is needed.
    try:
        g=boot()
        snapshot=out/'calibration.bin'
        for _ in range(60):
            g.cont();time.sleep(1);g.stop()
            cmd(f'dump binary memory {snapshot.relative_to(ROOT)} 0x200000 {0x200000+length:#x}')
            try:layout=locate(snapshot.read_bytes());break
            except ValueError:pass
        else:raise ValueError('live segment chain not found')
        snapshot.unlink();stop()
        (out/'layout.json').write_text(json.dumps(layout,indent=2)+'\n')
        g=boot();h0,h1,_,_=layout['hunks']
        field=h1+v.A4_BASE+v.A4['field_clock']
        until(h0+(0x180c4 if a.variant=='ocs' else 0x1898a))
        cmd('monitor key 45 1')
        until(h0+(0x1edde if a.variant=='ocs' else 0x1fbba))
        cmd('monitor key 45 0')
        until(h0+(0x180c4 if a.variant=='ocs' else 0x1898a))
        cmd('monitor key 45 1')
        until(h0+(0x1f396 if a.variant=='ocs' else 0x20164))
        cmd('monitor key 45 0')
        until(h0+(0x1f43c if a.variant=='ocs' else 0x20214))
        # Bounded scene fixture: invoke its real entry after frontend setup.
        # Does not claim a campaign transition or change the scene instructions.
        entry=0x1d2b0 if a.variant=='ocs' else 0x1dfde
        callsite=h0+(0x1f440 if a.variant=='ocs' else 0x20218)
        ret=callsite+6
        fixture=out/'scene-call.bin';fixture.write_bytes(struct.pack('>HI',0x4eb9,h0+entry))
        original=out/'menu-call.bin'
        cmd(f'dump binary memory {original.relative_to(ROOT)} {callsite:#x} {callsite+6:#x}')
        raw=(ROOT/v.GAME).read_bytes();site=callsite-h0
        expected=raw[v.HUNKS[0][0]+site:v.HUNKS[0][0]+site+6]
        assert expected[:2]==bytes.fromhex('4eb9')
        assert original.read_bytes()==expected[:2]+struct.pack('>I',h0+int.from_bytes(expected[2:],'big'))
        cmd(f'monitor ocs-load {callsite:x} "{fixture}"')
        shift=0xd2e if a.variant=='ocs' else 0
        until(h0+0x1de20-shift)
        for label,start,end in (('fast',0x200000,0x600000),('chip',0,0x200000)):
            cmd(f'dump binary memory {(out/(label+".bin")).relative_to(ROOT)} {start:#x} {end:#x}')
        (out/'registers.txt').write_text(cmd('info registers'))
        rows=[]
        for name,point,reg in (('upper',0x1dec2,'d7'),('feet',0x1dfa4,'d2')):
            epoch=None
            for n in ((0,25,50,75) if a.timing else (0,15,30,45)):
                condition=(None if epoch is None else f'*(unsigned int*){field:#x} >= {epoch+n}') if a.timing else f'(short)${reg} <= {-12*n}'
                until(h0+point-shift, condition)
                r=cmd(f'printf "SCENE %u %d\\n", *(unsigned int*){field:#x}, (short)${reg}')
                field_value,x=map(int,re.search(r'SCENE (\d+) (-?\d+)',r).groups())
                if epoch is None:epoch=field_value;epoch_x=x
                if a.timing and n:
                    elapsed=field_value-epoch
                    assert abs(x-epoch_x+elapsed*120//50)<6, (name,n,elapsed,x)
                rows.append(dict(scene=name,frame=n,field=field_value,x=x))
                shot(name+'-'+str(n))
                print(name,n,r,flush=True)
        until(ret)
        cmd(f'monitor ocs-load {callsite:x} "{original}"')
        (out/'report.json').write_text(json.dumps(dict(complete=True,variant=a.variant,slave_sha256=hashlib.sha256(slave.read_bytes()).hexdigest(),samples=rows,scope='menu-call fixture; native scene body, assets and publication; not a campaign traversal'),indent=2)+'\n')
    finally:stop()

if __name__=='__main__':main()
