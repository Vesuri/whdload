#!/usr/bin/env python3
"""Bounded unskipped opening gate, with read-only motion samples and screenshots."""
import argparse
import hashlib
import json
import os
import re
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
    p.add_argument('--title-only',action='store_true',help='skip opening and sample Wing Commander logo zoom/rotation')
    a=p.parse_args();out=new_output(a.output);out.mkdir(parents=True)
    v=get(a.variant)
    if a.variant=='ocs':
        from ocs_runtime import locate
        sy=json.loads((a.build/'build.json').read_text())['symbols']
        slave=a.build/'WingCommander.Slave';length=0x400000
    else:
        from cd32_runtime import locate
        sy={n:int(o,16) for o,n in re.findall(r'^([0-9A-F]{8}) (\S+)$',(a.build/'slave.lst').read_text(),re.M)}
        slave=a.build/'WingCommanderCD32.Slave';length=0x800000
    env=dict(os.environ,SLAVE=str(slave.resolve()),WC_VARIANT=a.variant,
             FSUAE_RUN='../'+str(out.relative_to(ROOT))+'/run',WARP='1',NTSC='0',WINDOW='front',
             JOY0='none',JOY1='none',DETERMINISTIC='1',AMIGA_SETUP='a500' if a.variant=='ocs' else 'a1200-fast',
             WHD_ARGS='CUSTOM5=1 DCACHE' if a.variant=='ocs' else 'CUSTOM5=0 DCACHE',
             EXTRA_ARGS='--uae_cpu_model=68020 --fast_memory=4096' if a.variant=='ocs' else '',
             OCS_STOCK_CLOCK='1' if a.variant=='ocs' else '0',INTRO_STOCK_CLOCK='0')
    g=None
    def stop():
        nonlocal g
        if g:g.p.kill();g=None
        subprocess.run(['/bin/bash',str(ROOT/'amiga/run.sh'),'stop'],env=env,check=True)
    def boot():return Server('wc-opening',root=str(ROOT),run_dir='amiga/'+env['FSUAE_RUN'],profile_window=False).boot(env)
    def cmd(s,timeout=60):
        r=g.cmd(s,timeout=timeout)
        if any(x in r for x in ('Remote connection closed','Cannot access','Error','Invalid hex','Protocol error')):raise RuntimeError(r)
        return r
    def until(addr,condition=None):
        if condition:
            r=cmd(f'break *{addr:#x}\ncondition $bpnum {condition}\ncontinue\ndelete',60)
        else:r=cmd(f'break *{addr:#x}\ncontinue\ndelete',60)
        if 'Breakpoint' not in r:raise ValueError('checkpoint missed: '+r)
    def values():
        r=cmd(f'printf "VALUES %u %u %u\\n", *(unsigned int*){field:#x}, $d2 & 65535, $d3 & 65535')
        return [int(x) for x in re.search(r'VALUES (\d+) (\d+) (\d+)',r).groups()]
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
        g=boot();h0,h1,_,h3=layout['hunks'];base=layout['slave'];shift=0xba if a.variant=='ocs' else 0
        field=h1+v.A4_BASE+v.A4['field_clock']
        if a.title_only:
            until(h0+(0x180c4 if a.variant=='ocs' else 0x1898a))
            cmd('monitor key 45 1')
            until(h0+(0x1edde if a.variant=='ocs' else 0x1fbba))
            cmd('monitor key 45 0')
            until(base+sy['intro_title'])
            samples={}
            for name,off,minimum in (('approach',0x2f3a0 if a.variant=='ocs' else 0x2ec98,165),('rotation',0x2d0de if a.variant=='ocs' else 0x2d746,236)):
                rows=[]
                condition=f'($d2 & 65535) >= {minimum} && *(unsigned int*)$sp >= {base+sy["intro_title"]} && *(unsigned int*)$sp < {base+sy["intro_title_sample"]}'
                for i in range(20):
                    until(h0+off,condition)
                    scale=18 if name=='approach' else 20
                    angle='0' if name=='approach' else '*(unsigned short*)($sp+18)'
                    r=cmd(f'printf "TITLE %u %u %u %u %u %u\\n", *(unsigned int*){field:#x}, $d2 & 65535, $d6 & 65535, *(unsigned short*)($a5-2), *(unsigned short*)($sp+{scale}), {angle}')
                    rows.append([int(x) for x in re.search(r'TITLE (\d+) (\d+) (\d+) (\d+) (\d+) (\d+)',r).groups()])
                # Intermediate samples must reach the real bitmap renderer,
                # with unchanged authoritative geometry within the same tick.
                groups={}
                for row in rows:groups.setdefault(tuple(row[1:4]),set()).add(row[4 if name=='approach' else 5])
                if not any(len(v)>1 for v in groups.values()):raise ValueError('title still renders only tick positions: '+name)
                samples[name]=rows;shot('title-'+name)
                print('verified intermediate title '+name,flush=True)
            until(h0+(0x1efb4 if a.variant=='ocs' else 0x1fd90))
            (out/'report.json').write_text(json.dumps(dict(complete=True,variant=a.variant,title_samples=samples,slave_sha256=hashlib.sha256(slave.read_bytes()).hexdigest()),indent=2)+'\n')
            print('PASS: title zoom/rotation render samples and script exit',flush=True)
            return
        stages=[];samples={}
        for off,name in ((0xee0,'orchestra'),(0xfb4,'expression'),(0x10cc,'separation'),(0x11a8,'flight'),(0x12c0,'fireworks'),(0xde0,'fade')):
            until(h3+off-shift);stages.append(dict(name=name,values=values()))
            print('reached '+name,flush=True)
            if name in ('separation','flight'):
                rows=[]
                for i in range(20):
                    until(h3+(0x10d8 if name=='separation' else 0x11ca)-shift)
                    rows.append(values())
                samples[name]=rows;shot(name)
            elif name in ('orchestra','fireworks'):
                until(h3+(0xf20 if name=='orchestra' else 0x13e4)-shift);shot(name)
        until(h0+(0x1edde if a.variant=='ocs' else 0x1fbba))
        active=cmd(f'printf "ACTIVE %u\\n", *(unsigned short*){base+sy["opening_active"]:#x}')
        if 'ACTIVE 0' not in active:raise ValueError('opening state leaked into title')
        for name,rows in samples.items():
            column=1 if name=='separation' else 2
            if len(set(row[column] for row in rows))<3:raise ValueError('motion stalled')
            if name=='flight' and not any(row[2]%100 for row in rows):raise ValueError('zoom lacks intermediate depths')
        report=dict(complete=True,variant=a.variant,slave_sha256=hashlib.sha256(slave.read_bytes()).hexdigest(),
                    stages=stages,samples=samples,warp=True,scope='unskipped opening through native world intro; read-only field/motion samples')
        (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
        print('PASS: complete opening and intermediate zoom positions',flush=True)
    finally:stop()


if __name__=='__main__':main()
