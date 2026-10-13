#!/usr/bin/env python3
"""Native renderer-only pose prediction, signed arithmetic and isolation checks."""
import argparse,json,re,struct,random,hashlib
from pathlib import Path
from timing_audit_check import CPU
from cd32_runtime import ROOT,locate
S=0x180000
POSES=(0x919a,0xa148,0xb450,0xb750,0x9d6c)
def trunc(n,d):return (abs(n)//d)*(-1 if n<0 else 1)
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('build',type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--flame-run',type=Path,default=ROOT/'tmp/phase10-isolated-turn-ntsc');a=p.parse_args()
    out=a.output.resolve()
    if (ROOT/'tmp').resolve() not in out.parents or out.exists():raise ValueError('new tmp output required')
    memory=(ROOT/'tmp/phase7-combat-controls/start-fast.bin').read_bytes();layout=locate(memory)
    blob=(a.build/'payload.bin').read_bytes();sy={n:int(o,16) for o,n in re.findall(r'^([0-9A-F]{8}) (\S+)$',(a.build/'slave.lst').read_text(),re.M)}
    count=0;scale_count=0
    for model in (2,4):
        c=CPU(memory,layout,model);c.write(S,blob)
        def put(n,f,v):c.write(S+sy[n],struct.pack('>'+f,v))
        def run(n,regs=None):c.run(S+sy[n]-c.code,registers=regs)
        put('timing_game','I',c.code)
        if 'timing_scene_velocity' in sy:c.write(c.code+0x807a,struct.pack('>HI',0x4ef9,S+sy['translation_velocity']))
        if 'timing_scene_allocate' in sy:c.write(c.code+0x2b648,struct.pack('>HI',0x4ef9,S+sy['timing_scene_allocate']))
        rng=random.Random(10)
        for hz in (50,60):
            for f in (0,1,hz//2,hz-1,hz,hz+10,hz+20):
                for value in (-2147483648,-5121,-1,0,1,5121,2147483647)+tuple(rng.randint(-2**31,2**31-1) for _ in range(8)):
                    run('timing_scene_scale',{9:value&0xffffffff,15:f,16:hz})
                    got=struct.unpack('>i',struct.pack('>I',c.reg(9)))[0]
                    expected=(trunc(value*f,hz)+2**31)%2**32-2**31
                    assert got==expected,(model,hz,f,value,got)
                    scale_count+=1
        for hz in (50,60):
            for view in range(4):
                c.reset();put('timing_active','H',1);put('timing_hz','I',hz);put('timing_scene_valid','H',0)
                c.data_value(0x9566,'h',-1);c.data_value(0xba54,'h',0)
                c.data_value(0x3896,'h',view);c.data_value(0xae4,'h',0);c.data_value(0x9564,'h',-1)
                c.write(c.data+0x96fe,bytes(128))
                for slot,kind in ((0,12),(1,12),(2,4),(3,2),(60,8)):
                    c.data_value(0x96fe+2*slot,'h',kind)
                    c.write(c.data+0x919a+12*slot,struct.pack('>3i',1000,2000,3000))
                    c.write(c.data+0x9d6c+12*slot,struct.pack('>3i',5121,-513,-1))
                    for off,vec in ((0xa148,(0,0,-256)),(0xb450,(0,256,0)),(0xb750,(-256,0,0))):c.write(c.data+off+12*slot,struct.pack('>3i',*vec))
                    for off in (0x9578,0x95f8,0x9678):c.data_value(off+2*slot,'h',8)
                run('timing_scene_snapshot');run('timing_scene_snapshot')
                run('timing_player_camera')
                c.data_value(0x7f02,'I',100)
                before=c.read(c.data,0xfda0)
                for fraction in (0,1,hz//2,hz-1,hz,hz+20):
                    put('timing_clock' ,'I',100)
                    c.write(S+sy['timing_clock']+4,struct.pack('>I',fraction))
                    run('timing_scene_begin')
                    effective=min(fraction+10,hz+20) if 'release_predict' in sy else min(fraction,hz)
                    for slot in (0,1,2,60):
                        got=struct.unpack('>3i',c.read(c.data+0x919a+12*slot,12))
                        want=tuple(p+trunc(v*effective,hz) for p,v in zip((1000,2000,3000),(5121,-513,-1)))
                        if slot!=1 or 'timing_scene_velocity' not in sy:
                            assert got==want,(model,hz,view,fraction,slot,got,want)
                    assert c.read(c.data+0x919a+36,12)==before[0x919a+36:0x919a+48] # star direction
                    if fraction>=hz//2:
                        assert c.read(c.data+0xa148+12,12)!=before[0xa148+12:0xa148+24]
                    if 'timing_scene_velocity' in sy or (fraction and view==0):
                        ref=CPU(memory,layout,model);ref.write(ref.data,before)
                        for slot in (1,2,60):
                            for entry in (0x2acb2,0x2acf2,0x2ad32):
                                angle=trunc(8*effective,hz)
                                if angle:ref.run(entry,struct.pack('>hh',angle,slot))
                            for off in POSES[1:4]:assert c.read(c.data+off+12*slot,12)==ref.read(ref.data+off+12*slot,12)
                            if slot==1 and 'timing_scene_velocity' in sy:
                                ref.run(0x7d1a,struct.pack('>h',slot))
                                future=struct.unpack('>3i',ref.read(ref.data+0x9d6c+12*slot,12))
                                velocity=tuple(v+trunc((n-v)*effective,hz) for v,n in zip((5121,-513,-1),future))
                                want=tuple(p+trunc(v*effective,hz) for p,v in zip((1000,2000,3000),velocity))
                                got=struct.unpack('>3i',c.read(c.data+0x919a+12*slot,12))
                                assert got==want,('native heading forecast',model,hz,effective,got,want)
                        ref.close()
                    run('timing_scene_end')
                    assert c.read(c.data,0xfda0)==before,('authoritative leak',model,hz,view,[hex(i) for i,(x,y) in enumerate(zip(before,c.read(c.data,0xfda0))) if x!=y][:20])
                    count+=1
                # A view cut invalidates until a fresh snapshot; a jump, reused
                # slot or lifecycle/action change must suppress prediction.
                c.data_value(0x3896,'h',(view+1)%4);run('timing_scene_begin');run('timing_scene_end')
                assert c.read(S+sy['timing_scene_valid'],2)==bytes(2)
                run('timing_scene_snapshot');run('timing_scene_snapshot')
                c.data_value(0x919a+12,'i',10000000);run('timing_scene_snapshot')
                assert c.read(S+sy['timing_scene_predictable']+1,1)==b'\0'
                c.data_value(0x96fe+4,'h',8);run('timing_scene_snapshot')
                assert c.read(S+sy['timing_scene_predictable']+2,1)==b'\0'
        # Explicit script/death/external-view and option-off boundaries.
        for field,value in ((0xae4,1),(0x3896,8),(0x96fe,0),(0x9564,5)):
            c.reset();put('timing_active','H',1);put('timing_hz','I',50)
            c.data_value(0xae4,'h',0);c.data_value(0x3896,'h',0)
            c.data_value(0x96fe,'h',12);c.data_value(0x9564,'h',-1)
            run('timing_scene_snapshot');run('timing_scene_snapshot')
            c.data_value(field,'h',value);before=c.read(c.data,0xfda0)
            run('timing_scene_begin');run('timing_scene_end')
            assert c.read(c.data,0xfda0)==before
            assert c.read(S+sy['timing_scene_valid'],2)==bytes(2)
        put('timing_active','H',0);before=c.read(c.data,0xfda0)
        run('timing_scene_begin');run('timing_scene_end');assert c.read(c.data,0xfda0)==before
        # Negative control: corrupt the saved authoritative position; the same
        # whole-data oracle must reject a bad restoration.
        c.reset();put('timing_active','H',1);run('timing_player_camera')
        before=c.read(c.data,0xfda0);run('timing_scene_begin')
        c.write(S+sy['timing_scene_saved'],bytes.fromhex('deadbeef'))
        run('timing_scene_end');assert c.read(c.data,0xfda0)!=before
        c.close()
    # The native renderer allocates class-7 engine flames in otherwise free
    # world slots. Exercise its actual constructor/attachment code, not a stub.
    flight=a.flame_run
    live=json.loads((flight/'result.json').read_text())
    flame_state=next((flight/(stem+'-data.bin')).read_bytes() for stem in live['scene_samples'] if 7 in struct.unpack_from('>61h',(flight/(stem+'-data.bin')).read_bytes(),0x96fe))
    for model in (2,4):
        c=CPU((flight/'end-fast.bin').read_bytes(),live,model);c.write(S,blob)
        c.write(S+sy['timing_game'],struct.pack('>I',c.code));c.write(S+sy['timing_active'],b'\0\1')
        if 'timing_scene_allocate' in sy:c.write(c.code+0x2b648,struct.pack('>HI',0x4ef9,S+sy['timing_scene_allocate']))
        c.write(c.data,flame_state)
        c.write(c.data+0x96fe+20,bytes(102))
        c.run(S+sy['timing_player_camera']-c.code)
        before=c.read(c.data,0xfda0)
        c.run(S+sy['timing_scene_begin']-c.code)
        c.run(0x2914c)
        assert any(c.data_value(0x96fe+2*i,'h')==7 for i in range(10,61)), 'flame path not exercised'
        # Real render wrapper owns this RNG save/restore separately.
        c.write(c.data+0x6f18,before[0x6f18:0x6f1c])
        c.run(S+sy['timing_scene_end']-c.code)
        after=c.read(c.data,0xfda0)
        assert after==before,('flame allocation leak',[hex(i) for i,(x,y) in enumerate(zip(before,after)) if x!=y][:30])
        c.close()
    out.mkdir(parents=True);(out/'report.json').write_text(json.dumps(dict(pose_cases=count,signed_scale_cases=scale_count,whole_data_restored=True,flame_cases=2,corrupted_restore_rejected=True,models=[68020,68040],build_sha256=hashlib.sha256(blob).hexdigest(),flame_state_sha256=hashlib.sha256(flame_state).hexdigest()),indent=2)+'\n')
    print(f'PASS: {count} pose/isolation cases, {scale_count} signed scaling cases')
if __name__=='__main__':main()
