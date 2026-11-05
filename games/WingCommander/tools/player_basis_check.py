#!/usr/bin/env python3
"""Native CPU steering precision, independent floating rotation and owner resets."""
import argparse,json,math,struct
from pathlib import Path
from field_objects_check import machine
from ocs_display_check import CODE,DATA,word,long
from ocs_clock_check import SLAVE
from ocs_reconstruct import new_output,require
from variants import get

IDENTITY=((0,0,256),(0,256,0),(256,0,0))

def turn(basis,axis,degrees):
    # Independent real-number rotation of the same local pair (F, U, R).
    pairs=((1,0,1),(2,0,-1),(1,2,1))
    i,j,sign=pairs[axis];c=math.cos(math.radians(degrees));s=sign*math.sin(math.radians(degrees))
    result=[list(v) for v in basis]
    result[i]=[c*x-s*y for x,y in zip(basis[i],basis[j])]
    result[j]=[c*y+s*x for x,y in zip(basis[i],basis[j])]
    return result


def check(build,variant,model):
    c,sy=machine(build,variant,model);a4=DATA+get(variant).A4_BASE;ocs=variant=='ocs'
    offsets=(0x18d8,0x2a40,0x2d40) if ocs else (0x214a,0x3452,0x3752)
    def call(name,registers=None):c.run(SLAVE-CODE+sy[name],registers=registers)
    def read():return [struct.unpack('>3i',c.read(a4+o,12)) for o in offsets]
    def seed(basis):
        call('player_basis_reset')
        for o,vec in zip(offsets,basis):c.write(a4+o,struct.pack('>3i',*(round(x) for x in vec)))
        call('player_basis_sync')
    def field(rates,hz):
        c.write(SLAVE+sy['ocs_clock_hz' if ocs else 'timing_hz'],long(hz))
        c.write(SLAVE+sy['timing_angles'],struct.pack('>3h',*rates))
        call('timing_player_field')
    maximum=0;samples=0
    try:
        # Both hemispheres, arbitrary tilted orientations, PAL/NTSC. No pitch
        # command during alternating yaw; the up axis must remain stationary.
        for hz in (50,60):
            for pitch,roll in ((-30,0),(30,0),(-45,25),(60,-40)):
                initial=turn(turn(IDENTITY,0,pitch),2,roll);seed(initial)
                c.write(SLAVE+sy['timing_angle_remainder'],bytes(12))
                initial=read();start_up=initial[1]
                for n in range(hz*10):
                    sign=1 if (n//(hz//2))%2==0 else -1
                    field((0,sign*10,0),hz)
                    got=read();drift=max(abs(x-y) for x,y in zip(got[1],start_up))
                    maximum=max(maximum,drift)
                    require(drift<=2,('yaw vertical drift',hz,pitch,roll,n,drift))
                    samples+=1
        # Mixed pitch/yaw/roll reference, including sign changes and field
        # fractions. The oracle has no Q14 tables, cross products or rounding.
        seed(IDENTITY);ref=[list(v) for v in IDENTITY];fraction=[0,0,0];max_error=0
        c.write(SLAVE+sy['timing_angle_remainder'],bytes(12))
        for n in range(1200):
            rates=(7 if n%200<100 else -7,11 if n%150<75 else -11,3 if n%80<40 else -3)
            for axis,rate in enumerate(rates):
                total=fraction[axis]+rate*10;angle=math.trunc(total/60);fraction[axis]=total-angle*60
                ref=turn(ref,axis,angle)
            field(rates,60);got=read()
            error=max(abs(x-y) for u,v in zip(got,ref) for x,y in zip(u,v));max_error=max(max_error,error)
            require(error<2,('mixed orientation',n,error))
        # Native/script replacement wins over the retained fractional pose.
        for o,vec in zip(offsets,IDENTITY):c.write(a4+o,struct.pack('>3i',*vec))
        field((0,0,0),50)
        require(read()==list(IDENTITY),'idle reseed changed native pose')
        require(struct.unpack('>9h',c.read(SLAVE+sy['player_basis_values'],18))==tuple(x*64 for v in IDENTITY for x in v),'native replacement not adopted')
        call('timing_prediction_reset');require(c.get(SLAVE+sy['player_basis_valid'])==0,'scene reset retained orientation')
        call('player_basis_sync');c.write(a4+get(variant).A4['object_class'],word(0))
        call('timing_preview_controls');require(c.get(SLAVE+sy['player_basis_valid'])==0,'inactive steering retained orientation')
        # Full field entry preserves its register ABI.
        regs={r:0x12340000+r for r in range(1,17) if r not in (5,8)}
        c.write(SLAVE+sy['timing_angles'],struct.pack('>3h',10,-10,5))
        call('timing_player_field',regs)
        require(all(c.reg(r)==v for r,v in regs.items()),'field register contract')
        # Negative control: original native small yaw turns reproduce the bug.
        seed(turn(IDENTITY,0,-30));up=read()[1]
        for n in range(150):c.run(0x29d66 if ocs else 0x2acf2,struct.pack('>hh',2 if (n//25)%2==0 else -2,0))
        native_drift=max(abs(x-y) for x,y in zip(up,read()[1]))
        require(native_drift>20,'native drift negative control failed')
        return dict(model=model,yaw_fields=samples,max_up_component_drift=maximum,mixed_fields=1200,max_basis_error=max_error,native_drift=native_drift,scene_and_native_reset=True,registers_preserved=True)
    finally:c.close()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('variant',choices=('cd32','ocs'));p.add_argument('build',type=Path);p.add_argument('--output',required=True)
    a=p.parse_args();out=new_output(a.output);out.mkdir(parents=True)
    rows=[check(a.build,a.variant,m) for m in ((1,2) if a.variant=='ocs' else (2,4))]
    (out/'report.json').write_text(json.dumps(rows,indent=2)+'\n');print(rows)

if __name__=='__main__':main()
