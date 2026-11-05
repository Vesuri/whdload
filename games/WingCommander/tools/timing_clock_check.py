#!/usr/bin/env python3
"""Execute the D scheduler assembly against an independent elapsed-time ledger."""
import argparse
import json
import os
import random
import struct
import subprocess
from pathlib import Path
from c2p_check import CPU, BASE, STACK, STOP, u, ck

ROOT = Path(__file__).resolve().parents[1]
STATE = 0x30000


def invoke(c, field, hz, active):
    c.write(STACK, struct.pack('>I', STOP))
    c.reg(8, STACK)
    c.reg(1, STATE)
    c.reg(9, field & 0xffffffff)
    c.reg(10, hz)
    c.reg(11, active)
    ck(u.uc_emu_start(c.h, BASE, STOP, 100000, 1000))
    assert c.reg(18) == STOP
    return c.reg(9), struct.unpack('>6IH', c.read(STATE,26))


def check(blob):
    cases=0
    for model in (2,4):
        for hz in (50,60):
            for schedule in ([1], [2,3], [5], [7,11], [1,9,3,2]):
                c=CPU(blob,model)
                c.write(STATE,bytes(28))
                origin=0xfffffff0
                assert invoke(c,origin,hz,1)[0] == 0
                fields=issued=0
                for i in range(hz*4):
                    fields+=schedule[i%len(schedule)]
                    n,s=invoke(c,origin+fields,hz,1)
                    issued+=n
                    expected=fields*10//hz
                    assert issued==expected, (hz,schedule,fields,issued,expected)
                    assert s[1]==fields*10%hz and s[2]==fields and s[3]==issued and s[4]==0
                    cases+=1
                # Native modal exit + resume excludes all paused time and debt.
                invoke(c,origin+fields,hz,0)
                assert invoke(c,origin+fields+10000,hz,1)[0]==0
                assert invoke(c,origin+fields+10000+hz//10,hz,1)[0]==1
                c.close()
            c=CPU(blob,model);c.write(STATE,bytes(28));invoke(c,0,hz,1)
            n,s=invoke(c,hz,hz,1)
            assert n==4 and s[4]==6*hz and s[1]==0
            n,s=invoke(c,3*hz,hz,1)
            assert n==0 and s[4]==26*hz and s[5]==2
            c.close()
    return cases


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',required=True,type=Path)
    a=p.parse_args();out=a.output.resolve()
    if (ROOT/'tmp').resolve() not in out.parents or out.exists():
        raise ValueError('new tmp output required')
    out.mkdir(parents=True)
    subprocess.run([os.environ['VASM'],'-m68020','-spaces','-no-opt','-Fbin','-o',str(out/'clock.bin'),str(ROOT/'src/timing_clock.s')],check=True)
    blob=(out/'clock.bin').read_bytes();cases=check(blob)
    # A wrong world rate must fail the independent ledger, not share its oracle.
    needle=bytes.fromhex('c6fc000a')
    assert blob.count(needle)==1
    damaged=blob.replace(needle,bytes.fromhex('c6fc0009'))
    try:check(damaged)
    except AssertionError:pass
    else:raise AssertionError('wrong-rate sabotage passed')
    report=dict(cases=cases,models=[68020,68040],hz=[50,60],wrap=True,modal=True,bounded_debt=True,wrong_rate_rejected=True)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))


if __name__=='__main__':main()
