#!/usr/bin/env python3
"""Read phase-4 instruction evidence, retaining phase-5 selected PCs/registers."""
import json,collections
from pathlib import Path
import _amigaxdev
from amigaxdev import barto
from harness import ROOT
pcs=[0x130,0x134,0x152,0x156,0x16a,0x192,0x24d6,0x256e,0x3e78,0x3ed2,0x3f3c,0x3f6c,0x3fde,0x3ff4,0x4372,0x4458,0x5ce,0x5e8,0x5ee,0x3af8,0x476,0x47e,0xb04,0xc18,0x1236,0x14ea,0x1ed2]
out=ROOT/'tmp/phase5';out.mkdir(exist_ok=True)
for preset in ('a500','a1200'):
 p=ROOT/'tmp/phase4'/('base-'+preset+'-1');m=json.loads((p/'capture.json').read_text());h4=m['regions']['h4'];t=barto.load(str(p/'trace.bin'));events=[]
 for f in t.fields:
  for pc,c,r in t.instructions(f):
   if pc-h4 in pcs:events.append(dict(field=f.index,pc=f'{pc-h4:04x}',d=list(r[:8]),a=list(r[8:])))
 (out/(preset+'-trace-events.json')).write_text(json.dumps(events,indent=2)+'\n')
 counts=collections.Counter(x['pc'] for x in events);print(preset,counts)
 for pc in ('24d6','3f6c','3fde','4458','256e','05ce','3af8'):
  print(pc,[(x['field'],x['d'][0],x['a'][7]) for x in events if x['pc']==pc])
