#!/usr/bin/env python3
"""Compare timed control response with sampling bounds, normalized to the fixture epoch."""
import argparse
import json
from pathlib import Path
import struct
import re
from coverage_status import fixture
from timing_report import samples, NAMES, SIGNED

THRESHOLDS=(('accelerate_120',10,120,True),('accelerate_130',10,130,True),
            ('brake_100',100,100,False),('brake_50',100,50,False),('brake_stop',100,0,False))

def response(root):
    config=json.loads((root/'configuration.json').read_text())
    assert any(route in config['WHD_ARGS'] for route in ('CUSTOM5=7','CUSTOM5=9')),'Requires a timing control input route'
    game=int((root/'game-base.txt').read_text(),0)
    anchor_vbl=struct.unpack_from('>I',(root/'chip.bin').read_bytes(),game+0x48fe)[0]
    epoch=fixture(root/'code.bin')['epoch']
    offset=(anchor_vbl-epoch)&0xffffffff
    rows=samples(root)
    events=[]
    text=(root/'swaps-gdb.txt').read_text()
    for field,event_offset,values in re.findall(r'^PDTIME_EVENT (-?\d+) (0x[0-9a-f]+) (.+)$',text,re.M):
        if int(event_offset,16) not in (0xd058,0xccee):continue
        vals=[int(field)]+list(map(int,values.split()))
        assert len(vals)==len(NAMES)
        event=dict(zip(NAMES,vals))
        for key in SIGNED:event[key]=(event[key]^0x8000)-0x8000
        events.append(event)
    # Boundary samples narrow crossing intervals; keep source explicit in the report.
    source='boundaries and presentations' if events else 'presentations'
    if events:rows=sorted(rows+events,key=lambda row:row['field'])
    # Input tape tests the native field counter before its VBL increment.
    # pd_field=0 is the next callback, whose pre-increment counter equals anchor_vbl.
    for row in rows:row['fixture_field']=offset+row['field']
    result={}
    for name,start,target,rising in THRESHOLDS:
        end=100 if rising else 150
        previous=None
        result[name]=None
        for row in rows:
            field=row['fixture_field']
            met=row['speed']>=target if rising else row['speed']<=target
            if field>=start and field<=end and met:
                lo=max(start,previous['fixture_field'] if previous else start)
                result[name]=dict(milliseconds=[(lo-start)*20,(field-start+1)*20],speed=row['speed'],source=source)
                break
            previous=row
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('reference',type=Path)
    p.add_argument('captures',type=Path,nargs='+')
    a=p.parse_args()
    def route(root):
        return next(word for word in json.loads((root/'configuration.json').read_text())['WHD_ARGS'].split() if word.startswith('CUSTOM5='))
    assert all(route(root)==route(a.reference) for root in a.captures), 'Compare matching input routes'
    ref=response(a.reference)
    out={'reference':ref,'candidates':{}}
    for root in a.captures:
        measured=response(root)
        checks={}
        for key,baseline in ref.items():
            item=measured[key]
            if baseline is None or item is None:
                checks[key]={'status':'missing threshold','reference':baseline,'candidate':item}
                continue
            lo,hi=baseline['milliseconds'];x,y=item['milliseconds']
            tolerance=max(90,(lo+hi)*.05)
            least=max(0,x-hi,lo-y)
            most=max(abs(x-hi),abs(y-lo))
            checks[key]={'candidate_ms':[x,y],'allowed_error_ms':tolerance,
                         'error_bound_ms':[least,most],
                         'status':'pass' if most<=tolerance else 'fail' if least>tolerance else 'needs finer sampling'}
        out['candidates'][root.name]=checks
    print(json.dumps(out,indent=2))
