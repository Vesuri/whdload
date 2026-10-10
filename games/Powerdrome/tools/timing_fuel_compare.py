#!/usr/bin/env python3
"""Compare bounded fuel use over matching timed-input intervals against native A500."""
import argparse
import json
from pathlib import Path
import re
import struct
from coverage_status import fixture

def consumption(root,lo,hi):
    config=json.loads((root/'configuration.json').read_text())
    route=next(word for word in config['WHD_ARGS'].split() if word.startswith('CUSTOM5='))
    assert route in ('CUSTOM5=7','CUSTOM5=9')
    game=int((root/'game-base.txt').read_text(),0)
    initial_vbl=struct.unpack_from('>I',(root/'chip.bin').read_bytes(),game+0x48fe)[0]
    offset=initial_vbl-fixture(root/'code.bin')['epoch']
    rows=[]
    for line in re.findall(r'^PDRESOURCE (.+)$',(root/'swaps-gdb.txt').read_text(),re.M):
        field,speed,before,scale,boost,gear,target,engine,disabled,after=map(int,line.split())
        assert engine and not disabled and before>=after>0, 'Use an eligible route without exhaustion/refills'
        rows.append((field+offset,after))
    def bracket(field):
        before=[fuel for when,fuel in rows if when<field]
        after=[fuel for when,fuel in rows if when>=field]
        assert before and after, 'Capture must bracket both interval endpoints'
        # Include one boundary update instead of claiming sub-field timing precision.
        return after[0],before[-1]
    start=bracket(lo);end=bracket(hi)
    return route,dict(fields=[lo,hi],seconds=(hi-lo)/50,
                      units=[start[0]-end[1],start[1]-end[0]],
                      start_fuel=list(start),end_fuel=list(end))
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('reference',type=Path)
p.add_argument('captures',type=Path,nargs='+')
p.add_argument('--from-field',type=int,default=20)
p.add_argument('--to-field',type=int,default=240)
a=p.parse_args()
assert a.from_field<a.to_field
route,reference=consumption(a.reference,a.from_field,a.to_field)
out=dict(reference=reference,candidates={})
lo,hi=reference['units'];tolerance=(lo+hi)*.05
for root in a.captures:
    candidate_route,result=consumption(root,a.from_field,a.to_field)
    assert candidate_route==route
    x,y=result['units'];least=max(0,x-hi,lo-y);most=max(abs(x-hi),abs(y-lo))
    result.update(allowed_error_units=tolerance,error_bound_units=[least,most],
                  status='pass' if most<=tolerance else 'fail' if least>tolerance else 'needs finer sampling')
    out['candidates'][root.name]=result
print(json.dumps(out,indent=2))
