#!/usr/bin/env python3
"""Native player-preview isolation and signed angular-fraction checks against real-number rotation."""
import argparse
import json
import re
import struct
from pathlib import Path
from timing_audit_check import CPU
from cd32_runtime import ROOT, locate
from player_basis_check import IDENTITY, turn

S=0x180000


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('build',type=Path)
    p.add_argument('--memory',type=Path,default=Path('tmp/phase7-combat-controls/start-fast.bin'))
    p.add_argument('--output',required=True,type=Path)
    a=p.parse_args();out=a.output.resolve()
    if (ROOT/'tmp').resolve() not in out.parents or out.exists():raise ValueError('new tmp output required')
    memory=a.memory.read_bytes();layout=locate(memory);blob=(a.build/'payload.bin').read_bytes()
    sym={name:int(off,16) for off,name in re.findall(r'^([0-9A-F]{8}) (\S+)$',(a.build/'slave.lst').read_text(),re.M)}
    checks=0
    for model in (2,4):
        def setup():
            c=CPU(memory,layout,model);c.write(S,blob)
            c.write(S+sym['timing_game'],struct.pack('>I',c.code))
            for off,label in [(0x18eee,'timing_throttle_gate'),(0x18f00,'timing_throttle_gate'),(0x18f3a,'timing_fire_gate')]:
                c.write(c.code+off,struct.pack('>HI',0x4eb9,S+sym[label]))
            c.data_value(0x3896,'h',0);c.data_value(0x9564,'h',-1);c.data_value(0x96fe,'h',12)
            c.write(c.data+0xc642,bytes(128));c.write(c.data+0xc6c2,bytes(6))
            for off in (0x9578,0x95f8,0x9678,0x96f8,0x96fa,0x96fc):c.data_value(off,'h',0)
            return c
        def own(c,name):c.run(S+sym[name]-c.code)
        for direction in range(64):
            for ramp in (-9,-2,0,2,9):
                c=setup()
                for bit in range(6):c.data_value(0xc6c2+bit,'B',(direction>>bit)&1)
                for off in (0x96f8,0x96fa,0x96fc):c.data_value(off,'h',ramp)
                before=c.read(c.data,0xfda0)
                own(c,'timing_preview_controls')
                assert c.read(c.data,0xfda0)==before,('preview side effect',model,direction,ramp)
                got=struct.unpack('>3h',c.read(S+sym['timing_angles'],6))
                # Run original control/rate mapping with only the action calls
                # suppressed: the oracle is the native controller, not a copy.
                for off in (0x18eee,0x18f00,0x18f3a):c.write(c.code+off,bytes.fromhex('4e714e714e71'))
                c.run(0x18daa);c.run(0x742)
                want=tuple(c.data_value(off,'h') for off in (0x95f8,0x9578,0x9678))
                assert got==want,(got,want)
                c.close();checks+=1
        for hz in (50,60):
            for axis in range(3):
                for sign in (-1,1):
                    c=setup()
                    for off,vec in zip((0xa148,0xb450,0xb750),IDENTITY):
                        c.write(c.data+off,struct.pack('>3i',*vec))
                    c.write(S+sym['timing_hz'],struct.pack('>I',hz))
                    rates=[0,0,0];rates[axis]=sign
                    c.write(S+sym['timing_angles'],struct.pack('>3h',*rates))
                    for _ in range(hz):own(c,'timing_player_field')
                    expected=turn(IDENTITY,axis,sign*10)
                    for off,vec in zip((0xa148,0xb450,0xb750),expected):
                        got=struct.unpack('>3i',c.read(c.data+off,12))
                        assert max(abs(x-y) for x,y in zip(got,vec))<2,(axis,sign,got,vec)
                    assert c.read(S+sym['timing_angle_remainder'],12)==bytes(12)
                    c.close();checks+=1
    out.mkdir(parents=True);(out/'report.json').write_text(json.dumps(dict(checks=checks,models=[68020,68040],preview_state_unchanged=True,signed_fraction_rotation=True),indent=2)+'\n')
    print(f'PASS: {checks} native preview/isolation and signed-rate cases')


if __name__=='__main__':main()
