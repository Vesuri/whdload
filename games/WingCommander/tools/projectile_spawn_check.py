#!/usr/bin/env python3
"""Execute native player/AI weapon construction and first-picture prediction.

Original native routines are the constructor oracle. Sound enqueue is stubbed in
both arms; no simulated execution time is used as a performance measurement.
"""
import argparse, hashlib, json, re, struct
from pathlib import Path
from timing_audit_check import CPU, ck, u
from cd32_runtime import ROOT, locate

S=0x180000
HOOKS={0xc912:'projectile_gun_return',0xca5e:'projectile_missile_return',
       0xc316:'projectile_effect_return',0x9a52:'projectile_init_return'}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('build',type=Path);p.add_argument('--output',required=True,type=Path)
    a=p.parse_args()
    if a.output.exists() or (ROOT/'tmp').resolve() not in a.output.resolve().parents:
        p.error('new output below tmp/ required')
    memory=(ROOT/'tmp/phase7-combat-controls/start-fast.bin').read_bytes();layout=locate(memory)
    blob=(a.build/'payload.bin').read_bytes()
    sy={n:int(o,16) for o,n in re.findall(r'^([0-9A-F]{8}) (\S+)$',(a.build/'slave.lst').read_text(),re.M)}
    results=[];guards=[];mounts=[]
    for model in (2,4):
        for shooter in (0,1):
            for weapon in tuple(range(24,34))+(48,):
                c=CPU(memory,layout,model);ref=CPU(memory,layout,model)
                c.write(S,blob)
                c.write(c.code+0x807a,struct.pack('>HI',0x4ef9,S+sy['translation_velocity']))
                for off,name in HOOKS.items():c.write(c.code+off,struct.pack('>HI',0x4ef9,S+sy[name]))
                def put(n,f,v):c.write(S+sy[n],struct.pack('>'+f,v))
                def run(n):c.run(S+sy[n]-c.code)
                def vec(off,slot):return struct.unpack('>3i',c.read(c.data+off+12*slot,12))
                put('timing_game','I',c.code);put('timing_active','H',1);put('timing_hz','I',50)
                c.data_value(0x3896,'h',0);c.data_value(0xae4,'h',0)
                c.data_value(0x9564,'h',-1);c.data_value(0x9566,'h',-1);c.data_value(0xba54,'h',0)
                c.data_value(0x94c6,'h',-1)
                # Two stable ships, empty projectile and missile slots.
                c.write(c.data+0x96fe+4,bytes(118))
                c.data_value(0x96fe+2,'h',12);c.data_value(0x9564+2,'h',-1)
                c.data_value(0x94c6+2,'h',-1)
                for off in (0x919a,0x9d6c,0xa148,0xb450,0xb750):
                    c.write(c.data+off+12,c.read(c.data+off,12))
                c.write(c.data+0xa9ce+42,c.read(c.data+0xa9ce,42))
                c.data_value(0xa9ce+42*shooter+2,'h',weapon)
                c.data_value(0x9546+2*shooter,'h',100)
                # Sound is not part of the pose/weapon-state comparison.
                for cpu in (c,ref):cpu.write(cpu.code+0x14958,bytes.fromhex('4e75'))
                run('timing_scene_snapshot');run('timing_scene_snapshot')
                ref.write(ref.data,c.read(c.data,0xfda0))
                if weapon==48:
                    entry=0xc1e4
                    args=struct.pack('>hhI',shooter,400,c.data+0x919a)
                else:
                    entry=0xc458;args=struct.pack('>hh',shooter,0)
                ref.run(entry,args);c.run(entry,args)
                slot=c.reg(9)&0xffff
                assert slot<=60,(model,shooter,weapon,'allocation failed')
                assert c.read(c.data,0xfda0)==ref.read(ref.data,0xfda0),('constructor state',weapon)
                assert [c.reg(i) for i in range(1,17)]==[ref.reg(i) for i in range(1,17)],('constructor registers',weapon)
                # Materialize Unicorn's lazy flags with a guest CCR read.
                for cpu in (c,ref):
                    cpu.write(0x1000,bytes.fromhex('42f81100'))
                    ck(u.uc_ctl(cpu.h,10|(1<<30)))
                    ck(u.uc_emu_start(cpu.h,0x1000,0x1004,1000000,10))
                assert c.read(0x1100,2)==ref.read(0x1100,2),('constructor CCR',weapon,c.read(0x1100,2).hex(),ref.read(0x1100,2).hex())
                kind=c.data_value(0x96fe+2*slot,'h')
                assert kind in (5,8,10,11),(weapon,kind)
                assert int.from_bytes(c.read(S+sy['projectile_types']+slot*2,2),'big')==kind
                if weapon==24:
                    # Counterfactual: either original guard alone reproduces the defect.
                    saved=c.read(S,len(blob));data=c.read(c.data,0xfda0)
                    for remove in ('birth','cooldown'):
                        c.write(S,saved);c.write(c.data,data)
                        key='projectile_types' if remove=='birth' else 'projectile_cooldown_valid'
                        c.write(S+sy[key]+(2*slot if remove=='birth' else shooter),bytes(2 if remove=='birth' else 1))
                        run('timing_scene_snapshot')
                        target=slot if remove=='birth' else shooter
                        assert c.read(S+sy['timing_scene_predictable']+target,1)==bytes(1)
                        guards.append(dict(model=model,shooter=shooter,missing=remove,rejected=True))
                    # Two mounts in one world interval retain both birth records.
                    c.write(S,saved);c.write(c.data,data)
                    c.run(entry,args)
                    second=c.reg(9)&0xffff
                    assert second<=60 and second!=slot
                    assert c.read(S+sy['projectile_types']+2*slot,2)==struct.pack('>H',kind)
                    assert c.read(S+sy['projectile_types']+2*second,2)==struct.pack('>H',kind)
                    run('timing_scene_snapshot')
                    for target in (slot,second,shooter):
                        assert c.read(S+sy['timing_scene_predictable']+target,1)==b'\1'
                    mounts.append(dict(model=model,shooter=shooter,slots=[slot,second]))
                    # Certified births never override identity/death/camera cuts.
                    for cut in ('dead','model','expired','view','first-snapshot',
                                'cooldown-mismatch','player-jump','reused'):
                        c.write(S,saved);c.write(c.data,data)
                        target=slot
                        if cut=='dead':c.data_value(0x96fe+2*slot,'h',0)
                        elif cut=='model':c.data_value(0x97f6+2*slot,'h',25)
                        elif cut=='expired':c.data_value(0x94c6+2*slot,'h',0)
                        elif cut=='view':c.data_value(0x3896,'h',1)
                        elif cut=='first-snapshot':put('timing_scene_valid','H',0)
                        elif cut=='cooldown-mismatch':
                            c.data_value(0x94c6+2*shooter,'h',99);target=shooter
                        elif cut=='player-jump':
                            c.data_value(0x919a,'i',0x40000000);target=0
                        elif cut=='reused':
                            # The shared native initializer revokes even a same-model birth.
                            c.run(0x9a0a,struct.pack('>hhh',slot,24,0))
                            assert c.read(S+sy['projectile_types']+2*slot,2)==bytes(2)
                        run('timing_scene_snapshot')
                        assert c.read(S+sy['timing_scene_predictable']+target,1)==bytes(1),cut
                        assert c.read(S+sy['projectile_types'],128)==bytes(128),cut
                        guards.append(dict(model=model,shooter=shooter,cut=cut,rejected=True))
                    for cut in ('inactive','staged','failed-slot','modal-rebase'):
                        c.write(S,saved);c.write(c.data,data)
                        if cut=='modal-rebase':run('timing_rebase')
                        else:
                            run('projectile_reset')
                            if cut=='inactive':put('timing_active','H',0)
                            if cut=='staged':put('timing_scene_staged','H',1)
                            c.run(S+sy['projectile_created']-c.code,
                                  registers={9:0xffff if cut=='failed-slot' else slot,12:shooter})
                        assert c.read(S+sy['projectile_types'],128)==bytes(128),cut
                        assert c.read(S+sy['projectile_cooldown_valid'],64)==bytes(64),cut
                        guards.append(dict(model=model,shooter=shooter,cut=cut,rejected=True))
                    c.write(S,saved);c.write(c.data,data)
                # Native countdown and movement subset; excludes collisions/AI.
                c.run(0x76a8,struct.pack('>h',shooter))
                if kind==11:c.run(0x7808,end=0x78d8,registers={11:slot})
                elif kind in (8,10):c.run(0x76a8,struct.pack('>h',slot))
                if kind in (5,8,10):c.run(0x7d1a,struct.pack('>h',slot))
                birth_debug=(slot,kind,c.data_value(0x94c6+slot*2,'h'),c.data_value(0x3896,'h'),c.read(S+sy['timing_scene_valid'],4).hex(),c.read(S+sy['projectile_types']+slot*2,2).hex(),c.read(S+sy['projectile_models']+slot*2,2).hex(),c.data_value(0x97f6+slot*2,'h'))
                run('timing_scene_snapshot')
                assert c.read(S+sy['timing_scene_predictable']+slot,1)==b'\1',(weapon,'birth not predictable',birth_debug)
                assert c.read(S+sy['timing_scene_predictable']+shooter,1)==b'\1',(weapon,'shooter cut')
                assert c.read(S+sy['projectile_types'],128)==bytes(128)
                assert c.read(S+sy['projectile_cooldown_valid'],64)==bytes(64)
                c.data_value(0x7f02,'I',100);put('timing_clock','I',100)
                run('timing_player_camera')
                authoritative=c.read(c.data,0xfda0);pos=vec(0x919a,slot);vel=vec(0x9d6c,slot);samples=[]
                for debt in (0,10,20,30,40):
                    c.write(S+sy['timing_clock']+4,struct.pack('>I',debt))
                    run('timing_scene_begin');got=vec(0x919a,slot)
                    if kind in (5,8,10):
                        want=tuple(x+(abs(v)*(debt+10)//50)*(-1 if v<0 else 1) for x,v in zip(pos,vel))
                        assert got==want,(weapon,debt,got,want)
                    samples.append(got)
                    run('timing_scene_end')
                    assert c.read(c.data,0xfda0)==authoritative,('render state leak',weapon,[(hex(i),x,y) for i,(x,y) in enumerate(zip(authoritative,c.read(c.data,0xfda0))) if x!=y][:25])
                if kind==11:
                    assert len(set(samples))==5,(weapon,"guided launch still holds")
                results.append(dict(model=model,shooter=shooter,weapon=weapon,slot=slot,kind=kind,
                                    velocity=vel,first_interval_positions=samples,constructor_identical=True))
                c.close();ref.close()
    a.output.write_text(json.dumps(dict(payload_sha256=hashlib.sha256(blob).hexdigest(),
        memory_sha256=hashlib.sha256(memory).hexdigest(),cases=results,negative_controls=guards,simultaneous_mounts=mounts),indent=2)+'\n')
    print(f'PASS: {len(results)} native constructors, {len(results)*5} first-interval renders, {len(guards)} rejecting controls, {len(mounts)} simultaneous-mount cases')

if __name__=='__main__':main()
