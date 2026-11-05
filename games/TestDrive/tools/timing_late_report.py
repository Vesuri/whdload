#!/usr/bin/env python3
import collections,json
from pathlib import Path
import _amigaxdev
from amigaxdev import barto
from harness import ROOT
result={}
for preset in ['a500','a1200']:
 p=ROOT/'tmp/phase5'/(preset+'-late-1')
 if not (p/'capture.json').exists():continue
 m=json.loads((p/'capture.json').read_text());rr=m['regions'];h4=rr['h4'];t=barto.load(str(p/'trace.bin'));ev=[];counts=collections.Counter()
 for f in t.fields:
  for pc,c,r in t.instructions(f):
   if pc in [h4+x for x in [0x1294,0x130c,0x1eee,0x1f00,0x1f10,0x1f76,0x130,0x134,0x1cfa,0x1d00,0x184c,0x18ec,0x181e,0x183e]]:
    name=f'h4:{pc-h4:04x}';counts[name]+=1;ev.append(dict(pc=name,field=f.index,sp=r[15]))
 result[preset]=dict(counts=dict(counts),events=ev)
 print(preset,counts)
(ROOT/'tmp/phase5/late-contexts.json').write_text(json.dumps(result,indent=2)+'\n')
