#!/usr/bin/env python3
"""Bounded native simulator and room timing checks."""
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
from amigaxdev.gdbserve import Server
from amigaxdev import barto
from ocs_reconstruct import ROOT, new_output
from variants import get


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('variant',choices=('ocs','cd32'));p.add_argument('build',type=Path)
    p.add_argument('--output',required=True)
    p.add_argument('--simulator-only',action='store_true',help='check explosion sampling and stop at name entry')
    p.add_argument('--skip-turn',action='store_true',help='Return during intro pitch; check simulator star stability')
    a=p.parse_args();out=new_output(a.output);out.mkdir(parents=True)
    v=get(a.variant)
    if a.variant=='ocs':
        from ocs_runtime import locate
        slave=a.build/'WingCommander.Slave'
    else:
        from cd32_runtime import locate
        slave=a.build/'WingCommanderCD32.Slave'
    length=0x400000 if a.variant=="ocs" else 0x800000
    env=dict(os.environ,SLAVE=str(slave.resolve()),WC_VARIANT=a.variant,
             FSUAE_RUN='../'+str(out.relative_to(ROOT))+'/run',WARP='1',NTSC='0',WINDOW='front',
             JOY0='none',JOY1='none',DETERMINISTIC='1',AMIGA_SETUP='a1200-030',
             WHD_ARGS='CUSTOM5=1 DCACHE' if a.variant=='ocs' else 'CUSTOM5=0 DCACHE',
             EXTRA_ARGS='--fast_memory=4096' if a.variant=='ocs' else '',OCS_STOCK_CLOCK='0',INTRO_STOCK_CLOCK='0',
             WC_BASELINE_CACHE_MODEL='1')
    g=None
    def stop():
        nonlocal g
        if g:g.p.kill();g=None
        subprocess.run(['/bin/bash',str(ROOT/'amiga/run.sh'),'stop'],env=env,check=True)
    def boot():return Server('wc-cinematic',root=str(ROOT),run_dir='amiga/'+env['FSUAE_RUN'],profile_window=False).boot(env)
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
        for _ in range(12):
            g.cont();time.sleep(1);g.stop()
            cmd(f'dump binary memory {snapshot.relative_to(ROOT)} 0x200000 {0x200000+length:#x}')
            try:layout=locate(snapshot.read_bytes());break
            except ValueError:pass
        else:
            shot('boot-failure')
            raise ValueError('live segment chain not found')
        snapshot.unlink();stop()
        (out/'layout.json').write_text(json.dumps(layout,indent=2)+'\n')
        g=boot();h0,h1,_,_=layout['hunks']
        field=h1+v.A4_BASE+v.A4['field_clock']
        if a.skip_turn:
            # The opening's input polling is much more frequent than world
            # updates. Stop at the actual scripted camera tick, then use Return.
            until(h0+(0x6dcc if a.variant=='ocs' else 0x7056),
                  '*(short*)($a4+'+('0xd88' if a.variant=='ocs' else '0x15fa')+'+122) != 0')
            cmd('monitor key 44 1')
            until(h0+(0x1f396 if a.variant=='ocs' else 0x20164))
            cmd('monitor key 44 0')
        else:
            until(h0+(0x180c4 if a.variant=='ocs' else 0x1898a))
            cmd('monitor key 45 1')
            until(h0+(0x1edde if a.variant=='ocs' else 0x1fbba))
            cmd('monitor key 45 0')
            until(h0+(0x180c4 if a.variant=='ocs' else 0x1898a))
            cmd('monitor key 45 1')
            until(h0+(0x1f396 if a.variant=='ocs' else 0x20164))
            cmd('monitor key 45 0')
        until(h0+(0x1f43c if a.variant=='ocs' else 0x20214))
        if a.variant=='ocs':
            sy=json.loads((a.build/'build.json').read_text())['symbols']
            cmd('monitor key 4c 1')
            until(h0+0x1f43c,'*(short*)($a4+0x19e) <= 80')
            cmd('monitor key 4c 0')
        else:
            sy={n:int(o,16) for o,n in re.findall(r'^([0-9A-F]{8}) (\S+)$',(a.build/'slave.lst').read_text(),re.M)}
        sb=layout['slave']
        def number(expr):
            r=cmd('printf "VALUE %u\\n", '+expr)
            return int(re.search(r'VALUE (\d+)',r)[1])
        cmd('monitor key 44 1')
        until(h0+(0x1f44e if a.variant=='ocs' else 0x20226))
        cmd('monitor key 44 0')
        rows=[]
        for label in ('ready','game-over'):
            until(sb+sy['intro_start'])
            start=number(f'*(unsigned int*){field:#x}')
            effects=[]
            cameras=[]
            if a.skip_turn:
                offsets=(0x18d8,0x2a40,0x2d40) if a.variant=='ocs' else (0x214a,0x3452,0x3752)
                pitch=0xd88 if a.variant=='ocs' else 0x15fa
                x,y=(0x20f8,0x2178) if a.variant=='ocs' else (0x245e,0x2bea)
                def basis():
                    return [number(f'*(unsigned int*)($a4+{off+732+axis*4})')
                            for off in offsets for axis in range(3)]
                for i in range(24):
                    until(sb+sy['intro_draw'])
                    native=basis()
                    rate=number(f'*(unsigned short*)($a4+{pitch+122})')
                    until(sb+sy['intro_finish'])
                    shown=basis()
                    star=[number(f'*(unsigned short*)($a4+{off+84})') for off in (x,y)]
                    cameras.append(dict(native=native,shown=shown,stale_pitch=rate,star=star))
                assert all(r['stale_pitch']!=0 for r in cameras),'skip did not retain the triggering rate'
                assert all(r['shown']==r['native'] for r in cameras),'stale intro pitch reached simulator camera'
                assert len({tuple(r['star']) for r in cameras})==1,'fixed star oscillates'
            if a.simulator_only and label=='game-over':
                # Capture native size before staging, then the size actually
                # projected. No game-state injection or large trace files.
                kind,model,size,scale,tick=((0xe8e,0xf86,0x29ba,0x227c,0x8dc) if a.variant=='ocs' else
                                          (0x1700,0x17f8,0x33cc,0x2cee,0x114e))
                until(sb+sy['intro_draw'])
                slots=[i for i in range(61) if number(f'*(unsigned short*)($a4+{kind+2*i})')==5
                       and number(f'*(unsigned short*)($a4+{model+2*i})')==49]
                assert len(slots)==1,slots
                slot=slots[0]
                for i in range(55):
                    if i:until(sb+sy['intro_draw'])
                    row=dict(tick=number(f'*(unsigned short*)($a4+{tick})'),
                             native_size=number(f'*(unsigned short*)($a4+{size+2*slot})'))
                    until(sb+sy['intro_finish'])
                    row.update(shown_size=number(f'*(unsigned short*)($a4+{size+2*slot})'),
                               projected_scale=number(f'*(unsigned short*)($a4+{scale+2*slot})'))
                    effects.append(row)
                assert any(r['native_size']!=r['shown_size'] for r in effects),'no fractional size'
                assert any(len({r['shown_size'] for r in effects if r['tick']==t})>=3
                           for t in {r['tick'] for r in effects}),'size still held between ticks'
            until(sb+sy['intro_draw'],f'*(unsigned int*){field:#x} >= {start+(150 if label=='game-over' else 100)}')
            shot(label)
            until(sb+sy['intro_stop'])
            end=number(f'*(unsigned int*){field:#x}')
            assert 200<=end-start<=210,(label,start,end)
            rows.append(dict(scene=label,start=start,end=end,fields=end-start,effects=effects,cameras=cameras))
        until(h0+(0x16992 if a.variant=='ocs' else 0x16fc6))
        shot('name')
        if a.simulator_only:
            (out/'report.json').write_text(json.dumps(dict(complete=True,variant=a.variant,
                slave_sha256=hashlib.sha256(slave.read_bytes()).hexdigest(),samples=rows),indent=2)+'\n')
            return
        # Native name entry and room navigation; no save/load or campaign run.
        char_done=0x16a86 if a.variant=='ocs' else 0x17172
        input_loop=0x16992 if a.variant=='ocs' else 0x16fc6
        name_returns=(0x16c40,0x16c66) if a.variant=='ocs' else (0x17450,0x1746e)
        for index,ret in enumerate(name_returns):
            if index:until(h0+input_loop)
            for keycode in ('14','12','21','14'):
                cmd('monitor key '+keycode+' 1');until(h0+char_done)
                cmd('monitor key '+keycode+' 0');until(h0+input_loop)
            cmd('monitor key 44 1');until(h0+ret);cmd('monitor key 44 0')
        if a.variant=='ocs':
            until(h0+0x171c4)
            cmd('monitor key 45 1');until(h0+0x17228);cmd('monitor key 45 0')
            room_points=(0x24f28,0x26134)
        else:
            room_points=(0x25d56,0x2702a)
            until(h0+0x17a14)
            cmd('monitor key 45 1');until(h0+0x17a96);cmd('monitor key 45 0')
        for index,point in enumerate(room_points):
            until(h0+point)
            fields=[]
            for _ in range(12):
                until(h0+point);fields.append(number(f'*(unsigned int*){field:#x}'))
            assert all(4<=b-a<=7 for a,b in zip(fields,fields[1:])),fields
            # Check actual cursor sampling between animation ticks, not just
            # calls to the arithmetic helper. Holding a direction produces distinct
            # native pointer positions at the capped cursor polls.
            cursor=[]
            direction='4e' if index==0 else '4f'
            cmd('monitor key '+direction+' 1')
            for _ in range(8):
                until(sb+sy['modal_room_native_input'])
                cursor.append(dict(field=number(f'*(unsigned int*){field:#x}'),
                                   x=number(f'*(unsigned short*)($a4+{0x19c if a.variant=="ocs" else 0xa88})')))
            cmd('monitor key '+direction+' 0')
            assert len({r['x'] for r in cursor})>=4,cursor
            assert all(b['field']-a['field']>=2 for a,b in zip(cursor,cursor[1:])),cursor
            assert any(2<=b['field']-a['field']<5 and b['x']!=a['x'] for a,b in zip(cursor,cursor[1:])),cursor
            if index==0:
                # An intermediate publication exercises the restored foreground,
                # unlike a screenshot taken only on the native 10 Hz pass.
                until(sb+sy['modal_bar_publish'])
            shot('bar' if index==0 else 'barracks')
            rows.append(dict(scene='bar' if index==0 else 'barracks',fields=fields,cursor=cursor))
            if index==0:
                cmd('monitor key 4e 1');until(h0+point,f'*(short*)($a4+{0x19c if a.variant=="ocs" else 0xa88}) >= 300');cmd('monitor key 4e 0')
                cmd('monitor key 44 1');until(h0+(0x24ffe if a.variant=='ocs' else 0x25e2c));cmd('monitor key 44 0')
        (out/'report.json').write_text(json.dumps(dict(complete=True,variant=a.variant,slave_sha256=hashlib.sha256(slave.read_bytes()).hexdigest(),samples=rows),indent=2)+'\n')
    finally:stop()

if __name__=='__main__':main()
