#!/usr/bin/env python3
"""Native steering inertia regression at flight ownership boundaries."""
import argparse,json,struct
from pathlib import Path
from field_objects_check import machine
from ocs_display_check import CODE,DATA,word,long
from ocs_clock_check import SLAVE
from ocs_reconstruct import new_output,require
from variants import get


def check(build,variant,model):
    c,sy=machine(build,variant,model);v=get(variant);ocs=variant=='ocs';a4=DATA+v.A4_BASE
    def call(n):c.run(SLAVE-CODE+sy[n])
    ramp=0xe88 if ocs else 0x16fa
    pad=a4+(0x3ed4 if ocs else 0x46c4)
    rates=(0xd08,0xd88,0xe08) if ocs else (0x157a,0x15fa,0x167a)
    try:
        c.write(a4+v.A4['object_class'],word(12))
        c.write(a4+(0xcf4 if ocs else 0x1566),word(-1))
        c.write(a4+(-18318 if ocs else -18280),word(0))
        c.write(DATA+(0xbe52 if ocs else 0xc642),bytes(128));c.write(pad,bytes(6))
        ship=c.get(a4+(0x89d if ocs else 0x110f),1)
        spec=a4+(-11224 if ocs else -11354)+ship*104
        for off in (34,36,38):c.write(spec+off,word(16))
        for off,label in zip((0x18528,0x1853a,0x18574) if ocs else (0x18eee,0x18f00,0x18f3a),('timing_throttle_gate','timing_throttle_gate','timing_fire_gate')):
            c.write(CODE+off,word(0x4eb9)+long(SLAVE+sy[label]))
        c.write(a4+ramp,struct.pack('>3h',9,-9,9))
        call('timing_preview_controls')
        require(c.read(SLAVE+sy['timing_angles'],6)!=bytes(6),'negative control did not reproduce residual turn')
        # Prediction reset alone was insufficient: native ramps remain live.
        call('timing_prediction_reset');call('timing_preview_controls')
        require(c.read(SLAVE+sy['timing_angles'],6)!=bytes(6),'old boundary unexpectedly removed inertia')
        for off in rates:c.write(a4+off,word(18))
        for name,size in (('timing_angle_remainder',12),('translation_remainders',24)):
            c.write(SLAVE+sy[name],bytes([1])*size)
        velocity=a4+(0x14fc if ocs else 0x1d6e)
        c.write(velocity,struct.pack('>3i',123,-456,789))
        before=c.read(velocity,12)
        call('timing_player_reset')
        require(c.read(a4+ramp,6)==bytes(6),'native ramps retained')
        require(all(c.get(a4+o)==0 for o in rates),'native angles retained')
        for name,size in (('timing_angles',6),('timing_angle_remainder',12),('translation_remainders',24)):
            require(c.read(SLAVE+sy[name],size)==bytes(size),name)
        require(c.read(velocity,12)==before,'mission velocity erased')
        call('timing_preview_controls')
        require(c.read(SLAVE+sy['timing_angles'],6)==bytes(6),'neutral mission starts turning')
        c.write(pad,bytes([0,1,0,0,0,0]));call('timing_preview_controls')
        require(c.read(SLAVE+sy['timing_angles'],6)!=bytes(6),'fresh held right ignored')
        # Verify the generated flight entry/exit actually call this boundary.
        for name in (('ocs_clock_loop','ocs_clock_leave_label') if ocs else ('timing_loop','timing_leave')):
            start=sy[name];found=False
            for off in range(start,start+64,2):
                if c.read(SLAVE+off,2)==bytes.fromhex('6100'):
                    delta=struct.unpack('>h',c.read(SLAVE+off+2,2))[0]
                    found |= off+2+delta==sy['timing_player_reset']
            require(found,('missing flight boundary',name))
        return dict(variant=variant,model=model,stale_control_reproduced=True,neutral_start=True,fresh_input=True,mission_velocity_preserved=True)
    finally:c.close()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('build',type=Path);p.add_argument('--variant',choices=('cd32','ocs'),required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    out=new_output(a.output);rows=[check(a.build,a.variant,m) for m in ((1,2) if a.variant=='ocs' else (2,4))]
    out.mkdir(parents=True)
    (out/'report.json').write_text(json.dumps(rows,indent=2)+'\n');print('PASS',rows)
if __name__=='__main__':main()
