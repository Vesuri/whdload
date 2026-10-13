#!/usr/bin/env python3
"""Native timing-install guards and exact option-off game/register preservation."""
import argparse
import json
import re
import struct
from pathlib import Path
from timing_audit_check import CPU, BASE, ck, u
from cd32_runtime import locate, ROOT


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('build',type=Path)
    p.add_argument('--memory',type=Path,default=Path('tmp/phase7-combat-controls/start-fast.bin'))
    p.add_argument('--output',required=True,type=Path)
    a=p.parse_args();out=a.output.resolve()
    if (ROOT/'tmp').resolve() not in out.parents or out.exists():raise ValueError('new tmp output required')
    memory=a.memory.read_bytes();layout=locate(memory)
    blob=(a.build/'payload.bin').read_bytes()
    sym={name:int(off,16) for off,name in re.findall(r'^([0-9A-F]{8}) (\S+)$',(a.build/'slave.lst').read_text(),re.M)}
    cases=[]
    for model in (2,4):
        for custom in (0,1,2,3):
            c=CPU(memory,layout,model);s=0x180000;resload=0x190000
            c.write(s,blob)
            c.write(s+0x1de4,struct.pack('>I',custom))
            c.write(resload+116,bytes.fromhex('4e75')) # existing PatchSeg already applied in retained dump
            c.write(resload+32,bytes.fromhex('4e75')) # cache flush has no CPU-only semantic effect
            # Beam reads are separately exercised by the live capture. Isolate
            # installer semantics with a 50 Hz result, not a fake timing claim.
            c.write(s+sym['timing_rate'],bytes.fromhex('70324e75'))
            c.write(0x1f0000,struct.pack('>I',0x1000))
            c.reg(17,0x2715)
            for r in range(1,17):c.reg(r,0x12340000+r)
            c.reg(3,resload);c.reg(8,0x1f0000);c.reg(16,(layout['hunks'][0]-4)//4)
            before=[c.reg(r) for r in range(1,18)]
            game_before=c.read(c.code,0x35ea4)
            ck(u.uc_emu_start(c.h,s+sym['timing_patchseg'],0x1000,1000000,10000))
            assert c.reg(18)==0x1000
            after=[c.reg(r) for r in range(1,18)]
            assert before[:7]+before[8:]==after[:7]+after[8:]
            assert after[7]==before[7]+4
            want=bytearray(game_before)
            if custom==3:
                for off,label,op in [(0x698,'timing_loop',0x4ef9),(0x176,'timing_pause',0x4eb9),(0x24c,'timing_pause',0x4eb9),(0x2571c,'timing_pause',0x4eb9),(0x18eee,'timing_throttle_gate',0x4eb9),(0x18f00,'timing_throttle_gate',0x4eb9),(0x18f3a,'timing_fire_gate',0x4eb9),(0x7bc2,'timing_world_rotation',0x4eb9)]:
                    want[off:off+6]=struct.pack('>HI',op,s+sym[label])
                want[0x7bc8:0x7bca]=bytes.fromhex('4e71')
                assert c.read(s+sym['timing_hz'],4)==struct.pack('>I',50)
            assert c.read(c.code,0x35ea4)==want
            cases.append(dict(model=model,custom=custom,exact=True));c.close()
        # A changed instruction operand must be rejected before any patch write.
        c=CPU(memory,layout,model);s=0x180000;resload=0x190000
        c.write(s,blob);c.write(s+0x1de4,struct.pack('>I',3))
        c.write(s+0x121e,struct.pack('>I',resload))
        c.write(resload+116,bytes.fromhex('4e75'))
        c.write(resload+4,bytes.fromhex('70094ef900001000'))
        c.write(c.code+0x69a,bytes.fromhex('0000'))
        before=c.read(c.code,0x35ea4)
        c.reg(17,0x2700);c.reg(8,0x1f0000)
        c.write(0x1f0000,struct.pack('>I',0x1000))
        c.reg(3,resload);c.reg(16,(c.code-4)//4)
        ck(u.uc_emu_start(c.h,s+sym['timing_patchseg'],0x1000,1000000,10000))
        assert c.reg(18)==0x1000 and c.reg(9)==9
        assert c.read(c.code,0x35ea4)==before
        c.close()
    out.mkdir(parents=True);(out/'report.json').write_text(json.dumps(dict(cases=cases,changed_operand_rejected=True,scope='installer and option-off semantics; beam timing tested live'),indent=2)+'\n')
    print('PASS: eight native installer/option cases, whole code-hunk and register/CCR checks')


if __name__=='__main__':main()
