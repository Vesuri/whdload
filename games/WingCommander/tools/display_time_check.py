#!/usr/bin/env python3
"""C1: compare each recorded prediction to the actual VBL display field."""
import argparse
import json
import struct
from pathlib import Path


def check(raw):
    magic,hz,count,size=struct.unpack_from('>4sIII',raw)
    assert magic==b'WCDS' and hz in (50,60) and size==32 and len(raw)==16+count*size
    assert count>=100, 'insufficient display coverage'
    fractions=set(); saturated=0; missed=0; wrong=[]
    for i in range(count):
        field,line,index,plane,copper,target,clock,debt,fraction=struct.unpack_from('>IHHIIIIII',raw,16+i*size)
        age=(field-clock)&0xffffffff
        expected=debt+age*10
        missed+=field!=target
        if fraction!=expected:wrong.append(dict(index=i,field=field,target=target,fraction=fraction,expected=expected))
        fractions.add(fraction);saturated+=debt+age*10>hz
    assert not wrong, f'prediction differs from display time: {wrong[:5]}'
    assert not missed, f'{missed} display deadlines missed'
    # Two-field lookahead must cover the full interval, including > one tick.
    assert set(range(20,hz+11,10)) <= fractions, 'world-time phases not covered'
    return dict(pictures=count,field_hz=hz,fractions=sorted(fractions),beyond_one_tick_pictures=saturated,
                missed_deadlines=missed,mismatched_fractions=len(wrong),passed=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run',type=Path);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    root=Path(__file__).resolve().parents[1]
    if a.output.exists() or (root/'tmp').resolve() not in a.output.resolve().parents:
        p.error('choose a new output below tmp/')
    raw=(a.run/'displaystats.bin').read_bytes();result=check(raw)
    negatives=[]
    for name,offset in [('wrong-fraction',44),('wrong-target',32)]:
        broken=bytearray(raw);value=struct.unpack_from('>I',broken,offset)[0];struct.pack_into('>I',broken,offset,value+1)
        try:check(broken)
        except AssertionError:negatives.append(name)
        else:raise AssertionError('negative control passed')
    result['negative_controls']=negatives
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':main()
