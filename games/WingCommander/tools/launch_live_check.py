#!/usr/bin/env python3
"""Bounded native exterior/tunnel launch fixture and render sampling."""
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
    p.add_argument('--exterior-samples',action='store_true',help='check and capture five incoming-ship pictures')
    p.add_argument('--autopilot',action='store_true',help='continue through the native waypoint fly-by after launch')
    p.add_argument('--ejection',action='store_true',help='continue through all three native ejection stages')
    p.add_argument('--landing',action='store_true',help='continue through native carrier return and hangar arrival')
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
             FSUAE_RUN='../'+str(out.relative_to(ROOT))+'/run',WARP='1',NTSC='0',WINDOW='front',
             JOY0='none',JOY1='none',DETERMINISTIC='1',AMIGA_SETUP='a1200-030',
             WHD_ARGS='CUSTOM5=1 DCACHE' if a.variant=='ocs' else 'CUSTOM5=0 DCACHE',
             EXTRA_ARGS='--fast_memory=4096',OCS_STOCK_CLOCK='0',INTRO_STOCK_CLOCK='0',
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
    def until(addr,condition=None,timeout=60):
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
        # A bounded native setup/launch fixture, not a briefing/campaign replay.
        sb=layout['slave']
        sy=(json.loads((a.build/'build.json').read_text())['symbols'] if a.variant=='ocs' else
            {n:int(o,16) for o,n in re.findall(r'^([0-9A-F]{8}) (\S+)$',(a.build/'slave.lst').read_text(),re.M)})
        ocs=a.variant=='ocs'
        stub=h0+((0x1a2dc if ocs else 0x1b024) if a.ejection else (0x19e9e if ocs else 0x1ab76)) # unused cinematic entry, saved/restored
        callsite=h0+(0x1f440 if ocs else 0x20218);ret=callsite+6
        routines=(0x1ac60,0x13fbc,0x1d8b6,0x2029c,0x1a454) if ocs else (0x1b9a8,0x14246,0x1e5ec,0x2106c,0x1b19c)
        load,pack,exterior,mission,tunnel=routines
        src=out/'fixture.s';binary=out/'fixture.bin'
        src.write_text('\n'.join([' movem.l d0-d7/a0-a6,-(sp)',
            ' clr.w -28796(a4)' if ocs else ' clr.w -28820(a4)',
            ' clr.w $87a(a4)' if ocs else ' clr.b $110f(a4)',
            ' clr.w -(sp)',f' jsr ${h0+load:x}',' move.w #1,-(sp)',f' jsr ${h0+pack:x}',
            ' addq.l #4,sp',f' jsr ${h0+exterior:x}',
            ' move.w #1,-(sp)',' move.w #1,-(sp)',f' jsr ${h0+mission:x}',' addq.l #4,sp',
            f' jsr ${h0+tunnel:x}',
            *([f' jsr ${h0+(0xf56 if ocs else 0x101c):x}'] if a.autopilot else []), *([f' jsr ${h0+(0x19e9e if ocs else 0x1ab76):x}'] if a.ejection else []), *([f' jsr ${h0+(0x2a6a6 if ocs else 0x2b632):x}',' move.w d0,d2',' move.w #-1,-(sp)',' move.w #8,-(sp)',' move.w d2,-(sp)',f' jsr ${h0+(0x9868 if ocs else 0x9af2):x}',' addq.l #6,sp',' move.w d2,-(sp)',f' jsr ${h0+(0x1ab60 if ocs else 0x1b8a8):x}',' addq.l #2,sp'] if a.landing else []), ' movem.l (sp)+,d0-d7/a0-a6',' rts'])+'\n')
        subprocess.run([os.environ['VASM'],'-m68020','-Fbin','-o',str(binary),str(src)],check=True)
        old=out/'original-stub.bin';cmd(f'dump binary memory {old.relative_to(ROOT)} {stub:#x} {stub+binary.stat().st_size:#x}')
        original=out/'original-call.bin';cmd(f'dump binary memory {original.relative_to(ROOT)} {callsite:#x} {callsite+6:#x}')
        fixture=out/'call.bin';fixture.write_bytes(struct.pack('>HI',0x4eb9,stub))
        cmd(f'monitor ocs-load {stub:x} "{binary}"');cmd(f'monitor ocs-load {callsite:x} "{fixture}"')
        rows=[]
        def number(expr):
            r=cmd('printf "VALUE %u\\n", '+expr)
            return int(re.search(r'VALUE (\d+)',r)[1])
        for stage,steps in enumerate((10,27,23)):
            until(sb+sy['launch_exterior_wait'],'$d2 == 0')
            first=number(f'*(unsigned int*){field:#x}')
            if a.exterior_samples and stage == 0:
                until(sb+sy['launch_exterior_wait'],'$d2 == 4')
                incoming=[]
                for i in range(5):
                    until(sb+sy['launch_exterior_native'])
                    pose=h1+v.A4_BASE+(0x407e if ocs else 0x488e)
                    x=number(f'*(unsigned short*){pose:#x}')
                    y=number(f'*(unsigned short*){pose+2:#x}')
                    incoming.append([x if x<32768 else x-65536,
                                     y if y<32768 else y-65536,
                                     number(f'*(unsigned int*){field:#x}')])
                    shot('incoming-'+str(i))
                # Profiling/debugger round trips can skip rendered fields. Bound
                # motion by elapsed game fields, not by screenshot count.
                assert all(0<=q[0]-p[0]<=4*((q[2]-p[2]+4)//5)
                           and -2*((q[2]-p[2]+4)//5)<=q[1]-p[1]<=0
                           for p,q in zip(incoming,incoming[1:])),incoming
                (out/'incoming.json').write_text(json.dumps(incoming)+'\n')
            until(sb+sy['launch_exterior_wait'],f'$d2 == {steps-1}')
            last=number(f'*(unsigned int*){field:#x}')
            assert (steps-1)*5<=last-first<=(steps-1)*5+10,(stage,first,last)
            shot('exterior-'+str(stage));rows.append(dict(stage=stage,first=first,last=last,steps=steps))
        until(sb+sy['launch_loop'])
        start=number(f'*(unsigned int*){field:#x}')
        until(sb+sy['intro_draw'],'$d2 >= 2')
        shot('tunnel')
        samples=[]
        for _ in range(8):
            until(sb+sy['launch_zoom'],'$d3 == 3')
            sample=cmd(f'printf "SAMPLE %u %u %u\\n", *(unsigned int*){field:#x}, (unsigned short)$d2, *(unsigned short*)($sp+18)')
            samples.append(list(map(int,re.search(r'SAMPLE (\d+) (\d+) (\d+)',sample).groups())))
        until(sb+sy['launch_resume'])
        end=number(f'*(unsigned int*){field:#x}')
        assert 125<=end-start<=135,(start,end)
        assert any(len({scale for _,t,scale in samples if t==tick})>1 for tick in {r[1] for r in samples}),samples
        tunnel_samples=samples
        autopilot=None
        if a.autopilot:
            until(sb+sy['autopilot_scene'])
            first=number(f'*(unsigned int*){field:#x}')
            until(sb+sy['intro_world'])
            samples=[]
            counter='ocs_intro_completed' if ocs else 'timing_completed'
            projected=[]
            for i in range(20):
                until(sb+sy['intro_finish'])
                position=h1+v.A4_BASE+(0x92a if ocs else 0x119c)
                sample=cmd(f'printf "AUTO %u %u %d %d %d\\n", *(unsigned int*){field:#x}, *(unsigned int*){sb+sy[counter]:#x}, *(int*){position:#x}, *(int*){position+4:#x}, *(int*){position+8:#x}')
                samples.append(list(map(int,re.search(r'AUTO (\d+) (\d+) (-?\d+) (-?\d+) (-?\d+)',sample).groups())))
                sx=h1+v.A4_BASE+(0x20f8 if ocs else 0x245e)
                sypos=h1+v.A4_BASE+(0x2178 if ocs else 0x2bea)
                screen=cmd(f'printf "AIM %d %d\\n", *(short*){sx:#x}, *(short*){sypos:#x}')
                projected.append(list(map(int,re.search(r'AIM (-?\d+) (-?\d+)',screen).groups())))
                if i==3:shot('autopilot')
            until(sb+sy['autopilot_resume'])
            last=number(f'*(unsigned int*){field:#x}')
            assert 240<=last-first<=250,(first,last)
            assert any(x[1]==y[1] and x[2:]!=y[2:] for x,y in zip(samples,samples[1:])),samples
            assert all(abs(x)<=3 and abs(y)<=3 for x,y in projected),('fly-by aim jumps',projected)
            autopilot=dict(first=first,last=last,samples=samples,projected=projected)
        ejection=[]
        if a.ejection:
            for stage, ticks in enumerate((10,10,200)):
                until(sb+sy[f'ejection_entry{stage}'])
                first=number(f'*(unsigned int*){field:#x}')
                slot=number(f'*(unsigned short*){h1+v.A4_BASE+(-0x478a if ocs else -0x4764):#x}') if stage==2 else 0
                position=h1+v.A4_BASE+(0x92a if ocs else 0x119c)+slot*12
                samples=[]
                camera_samples=[]
                for i in range(8):
                    until(sb+sy['ejection_draw'+str(stage)], '$d2 >= 75' if stage==2 else '$d2 >= 3',timeout=180)
                    sample=cmd(f'printf "EJECT %u %u %d %d %d %d %d\\n", *(unsigned int*){field:#x}, (unsigned short)$d2, (short)$d4, (short)$d6, *(int*){position:#x}, *(int*){position+4:#x}, *(int*){position+8:#x}')
                    samples.append(list(map(int,re.search(r'EJECT (\d+) (\d+) (-?\d+) (-?\d+) (-?\d+) (-?\d+) (-?\d+)',sample).groups())))
                    if stage==2:
                        basis=h1+v.A4_BASE+(0x18d8 if ocs else 0x214a)+61*12
                        camera_samples.append([number(f'*(unsigned int*){basis+j*4:#x}') for j in range(3)])
                    if i==3:shot('ejection-'+str(stage))
                until(sb+sy[f'ejection_resume{stage}'],timeout=180)
                last=number(f'*(unsigned int*){field:#x}')
                assert ticks*5<=last-first<=ticks*5+12,(stage,first,last)
                if stage==2:
                    assert any(x[1]==y[1] and p!=q for x,y,p,q in zip(samples,samples[1:],camera_samples,camera_samples[1:])),camera_samples
                    assert any(x[1]==y[1] and x[4:]!=y[4:] for x,y in zip(samples,samples[1:])),samples
                else:
                    assert any(x[1]==y[1] and x[2:]!=y[2:] for x,y in zip(samples,samples[1:])),samples
                ejection.append(dict(stage=stage,first=first,last=last,samples=samples,camera=camera_samples))
        landing=[]
        if a.landing:
            for stage,steps in enumerate((100,85)):
                until(sb+sy[f'landing_entry{stage}'],'$d2 == 0',timeout=180)
                first=number(f'*(unsigned int*){field:#x}')
                slot=number('(unsigned short)$d3' if stage==0 else '(unsigned short)$d7')
                assert slot<61,('carrier slot',stage,slot)
                if stage==0:
                    assert number(f'*(unsigned short*){h1+v.A4_BASE+(0xf86 if ocs else 0x17f8)+slot*2:#x}')==8
                    carrier_slot=slot
                else:assert slot==carrier_slot,('carrier argument',slot,carrier_slot)
                actor_frames=[]
                if stage==1:
                    # Slot 1 is the scripted foreground crew member. Check the
                    # native committed image against its extra redraws directly.
                    actor=h1+v.A4_BASE+(-0x5a44 if ocs else -0x5a2c)+24
                    expected=None
                    for _ in range(20):
                        until(h0+(0x1d422 if ocs else 0x1e150),f'$a2 == {actor}',timeout=180)
                        frame=number('(unsigned short)$d2')
                        caller=number('*(unsigned int*)($a5+4)')
                        native=h0<=caller<h0+v.HUNKS[0][1]
                        if native:expected=frame
                        else:assert expected is not None and frame==expected,('foreground frame',frame,expected)
                        actor_frames.append(dict(native=native,frame=frame))
                    assert any(not x['native'] for x in actor_frames),actor_frames
                    assert len({x['frame'] for x in actor_frames})>1,actor_frames
                samples=[];fractions=[]
                for i in range(8):
                    until(sb+sy[f'landing_draw{stage}'],'$d2 >= 10',timeout=180)
                    sample=cmd(f'printf "LAND %u %u %d %d\\n", *(unsigned int*){field:#x}, (unsigned short)$d2, (short)$d4, (short)$d5')
                    samples.append(list(map(int,re.search(r'LAND (\d+) (\d+) (-?\d+) (-?\d+)',sample).groups())))
                    fractions.append(number(f'*(unsigned short*){sb+sy["landing_elapsed"]:#x}'))
                    if i==3:shot('landing-'+str(stage))
                until(sb+sy['landing_wait'],f'$d2 == {steps-1}',timeout=180)
                last=number(f'*(unsigned int*){field:#x}')
                assert (steps-1)*5<=last-first<=(steps-1)*5+15,(stage,first,last)
                assert all(0<=f<5 for f in fractions) and any(f>0 for f in fractions),fractions
                landing.append(dict(stage=stage,first=first,last=last,samples=samples,fractions=fractions,actor_frames=actor_frames,
                    multiple_pictures_per_tick=any(x[1]==y[1] and x[2:]!=y[2:] for x,y in zip(samples,samples[1:]))))
        until(ret)
        cmd(f'monitor ocs-load {callsite:x} "{original}"');cmd(f'monitor ocs-load {stub:x} "{old}"')
        (out/'report.json').write_text(json.dumps(dict(complete=True,variant=a.variant,
            slave_sha256=hashlib.sha256(slave.read_bytes()).hexdigest(),exterior=rows,
            tunnel=dict(start=start,end=end,fields=end-start,samples=tunnel_samples),autopilot=autopilot,ejection=ejection,landing=landing,
            scope='native first-mission setup/launch fixture; not a briefing or campaign traversal'),indent=2)+'\n')
    finally:stop()

if __name__=='__main__':main()
