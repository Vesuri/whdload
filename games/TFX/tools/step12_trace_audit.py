#!/usr/bin/env python3
"""Check complete observed SetPal calls against their actual RGB operands."""
import sys,json
from pathlib import Path
from replay_flight import barto
p=Path(sys.argv[1]);base=json.loads((p/'segments.json').read_text())[0];complete=[];partial=0
for file in sorted(p.glob('*.trace')):
 t=barto.load(file);call=None;expected=None;high=None
 for f in t.fields:
  for pc,cost,r in t.instructions(f):
   off=pc-base
   if off==0x4c32c:call=dict(frame=file.stem,colors=[],writes=0)
   if call is None:continue
   if off==0x4c354:expected=tuple(r[i]&255 for i in range(3))
   if off==0x4c390:
    assert expected is not None
    index=((r[1]>>13)&7)*32+(r[9]-0xdff180)//2
    assert index==len(call['colors'])
    high=r[0]&0xfff;call['writes']+=1
   if off==0x4c39c:
    low=r[3]&0xfff
    actual=tuple((((high>>s)&15)<<4)|((low>>s)&15) for s in (8,4,0))
    assert actual==expected,(file,index,actual,expected)
    assert r[1]&0x200
    call['colors'].append(list(actual));call['writes']+=1;expected=None;high=None
   if off==0x4c3ac:
    assert len(call['colors'])==256 and call['writes']==512
    complete.append(call);call=None
 if call:partial+=1
assert complete,'no complete observed palette call'
result=dict(complete_calls=len(complete),partial_calls=partial,rgb_entries=sum(len(x['colors']) for x in complete),all_cpu_colour_writes_match_rgb=True,calls=complete,limitation='CPU operand/nibble/bank audit, not proof of physical hardware behaviour or other palette call sites.')
(p/'palette-trace-audit.json').write_text(json.dumps(result,indent=2))
print({k:v for k,v in result.items() if k!='calls'})
