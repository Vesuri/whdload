#!/usr/bin/env python3
"""Native intro clock, camera/object prediction and authoritative restoration."""
import argparse,json,re,struct
from pathlib import Path
from timing_audit_check import CPU
from cd32_runtime import ROOT,locate
from timing_scene_check import trunc


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('build',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if (ROOT/'tmp').resolve() not in a.output.resolve().parents or a.output.exists():raise ValueError('new tmp output required')
    memory=(ROOT/'tmp/phase7-combat-controls/start-fast.bin').read_bytes();layout=locate(memory)
    blob=(a.build/'payload.bin').read_bytes();sy={n:int(o,16) for o,n in re.findall(r'^([0-9A-F]{8}) (\S+)$',(a.build/'slave.lst').read_text(),re.M)}
    s=0x180000;cases=[];schedules=[]
    for model in (2,4):
        c=CPU(memory,layout,model);c.write(s,blob)
        def put(n,f,v):c.write(s+sy[n],struct.pack('>'+f,v))
        def run(n,regs=None):c.run(s+sy[n]-c.code,registers=regs)
        put('timing_game','I',c.code)
        c.write(c.code+0x807a,struct.pack('>HI',0x4ef9,s+sy['translation_velocity']))
        for hz in (50,60):
            for gaps in ((1,),(2,),(3,7,1,4)):
                c.reset();put('timing_hz','I',hz);run('intro_start');start=c.data_value(0x7f02,'I');ticks=0;elapsed=0;i=0
                while elapsed<10*hz:
                    elapsed=min(10*hz,elapsed+gaps[i%len(gaps)]);i+=1
                    c.data_value(0x7f02,'I',(start+elapsed)&0xffffffff);run('intro_due');ticks+=c.reg(9)
                assert ticks==100,(model,hz,gaps,ticks)
                assert c.read(s+sy['timing_active'],2)==b'\0\0'
                c.data_value(0x7f02,'I',start+elapsed+hz*2);run('intro_due');assert c.reg(9)==0
                assert int.from_bytes(c.read(s+sy['timing_clock']+16,4),'big')>=hz*20
                run('intro_stop');assert c.read(s+sy['intro_active'],2)==b'\0\0'
                schedules.append(dict(model=model,hz=hz,gaps=gaps,ticks=ticks))
            for view in (0,8,15):
                c.reset();put('timing_hz','I',hz);put('timing_active','H',0);put('intro_active','H',1);put('timing_scene_valid','H',0)
                c.data_value(0x3896,'h',view);c.data_value(0xae4,'h',1)
                c.write(c.data+0x96fe,bytes(128));c.write(c.data+0x94c6,bytes(128))
                for slot,kind in ((0,4),(1,4),(10,3),(61,0)):
                    c.data_value(0x96fe+2*slot,'h',kind)
                    c.write(c.data+0x919a+12*slot,struct.pack('>3i',1000,2000,3000))
                    c.write(c.data+0x9d6c+12*slot,struct.pack('>3i',5121,-513,-1))
                    for off,vec in ((0xa148,(0,0,-256)),(0xb450,(0,256,0)),(0xb750,(-256,0,0))):c.write(c.data+off+12*slot,struct.pack('>3i',*vec))
                    for off in (0x9578,0x95f8,0x9678):c.data_value(off+slot*2,'h',8)
                run('timing_scene_snapshot');run('timing_scene_snapshot')
                for pending in (0,1):
                    for frac in (0,10,hz-10,hz+100):
                        c.data_value(0x7f02,'I',100);put('timing_clock','I',100);c.write(s+sy['timing_clock']+4,struct.pack('>I',frac));put('release_pending','H',pending)
                        before=c.read(c.data,0xfda0);run('timing_scene_begin');f=min(frac+10*(1+pending),hz+20)
                        for slot in (0,1,10,61):
                            got=struct.unpack('>3i',c.read(c.data+0x919a+12*slot,12));want=tuple(p+trunc(v*f,hz) for p,v in zip((1000,2000,3000),(5121,-513,-1)))
                            assert got==want,(model,hz,view,slot,got,want)
                            ref=CPU(memory,layout,model);ref.write(ref.data,before)
                            for entry in (0x2acb2,0x2acf2,0x2ad32):ref.run(entry,struct.pack('>hh',trunc(8*f,hz),slot))
                            for off in (0xa148,0xb450,0xb750):assert c.read(c.data+off+12*slot,12)==ref.read(ref.data+off+12*slot,12)
                            ref.close()
                        run('timing_scene_end');assert c.read(c.data,0xfda0)==before
                        cases.append(dict(model=model,hz=hz,view=view,pending=pending,fraction=frac))
                put('release_pending','H',0)
                c.data_value(0x3896,'h',view+1);run('timing_scene_begin');run('timing_scene_end');assert c.read(s+sy['timing_scene_valid'],2)==b'\0\0'
                run('intro_stop')
        # Emission masks consume world time; repeated draws cannot consume
        # the intro flash countdown. Native non-intro behavior remains.
        c.reset();put('timing_in_world','H',0)
        c.data_value(0x914c,'H',17);c.data_value(0x9150,'H',22)
        for enabled,expected in ((0,2),(1,1)):
            put('intro_active','H',enabled);run('timing_emission_clock');assert c.reg(9)&0xffff==expected
            c.data_value(0x99a,'B',8);run('intro_flash_draw')
            assert c.data_value(0x99a,'B')==(8 if enabled else 7)
        # Execute the real title scheduler with display/asset/sound work
        # replaced by a one-field renderer. Count native-update dispatches.
        c.reset();put('timing_hz','I',50);put('release_pending','H',0)
        c.write(s+sy['intro_world'],bytes.fromhex('52b9000011004e75'))
        c.write(s+sy['intro_draw'],bytes.fromhex('52acff044e75'))
        c.write(s+sy['intro_finish'],bytes.fromhex('4e75'))
        for off in (0x13f50,0x2ec98,0x2d746):c.write(c.code+off,bytes.fromhex('4e75'))
        c.write(c.code+0x1898a,bytes.fromhex('70004e75'))
        c.write(0x1100,bytes(4));c.data_value(0x7f02,'I',0)
        c.run(s+sy['intro_title']-c.code,end=0x1fd90,registers={6:0x1e0000,4:90,15:200})
        assert int.from_bytes(c.read(0x1100,4),'big')==296
        assert c.data_value(0x7f02,'I')==1480
        assert c.reg(11)==296 and c.reg(15)==138
        assert int.from_bytes(c.read(0x1dfffe,2),'big')==366
        assert c.read(s+sy['intro_active'],2)==bytes(2)
        # Both the repeated cycle and skip exits must land on intact native
        # instructions, restore prediction state, and retain the skip flag.
        for skip,end in ((0,0x1fc8e),(1,0x1fe4c)):
            put('intro_active','H',1)
            c.run(s+sy['intro_credits_end']-c.code,end=end,registers={12:skip})
            assert c.reg(12)==skip and c.read(s+sy['intro_active'],2)==bytes(2)
        c.close()
    a.output.write_text(json.dumps(dict(passed=True,schedules=schedules,prediction_cases=cases,title_scheduler_ticks=296,title_scheduler_fields=1480,credit_exit_cases=4,emission_flash_cases=4,scope='native arithmetic and restoration, not performance'),indent=2)+'\n')
    print(f'PASS: {len(schedules)} clock schedules; {len(cases)} intro pose/camera/restoration cases')

if __name__=='__main__':main()
