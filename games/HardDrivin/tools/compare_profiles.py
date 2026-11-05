#!/usr/bin/env python3
"""Compare every recorded field of two fresh-boot captures, excluding host snapshots."""
import hashlib,json,sys
from pathlib import Path
import barto_mmap as barto
left,right=map(Path,sys.argv[1:3]);a=barto.load(left/'trace.bin');b=barto.load(right/'trace.bin')
assert len(a.fields)==len(b.fields)
result={'fields':len(a.fields),'differences':{},'snapshot_differences':{}}
for name in ('cycles','instructions','dma','screenshot'):
 bad=[]
 for x,y in zip(a.fields,b.fields):
  if name=='cycles':u,v=x.cycles,y.cycles
  elif name=='instructions':u,v=a.data[x.insn_off:x.insn_end],b.data[y.insn_off:y.insn_end]
  elif name=='dma':u,v=x.dma,y.dma
  else:u,v=x.shot,y.shot
  if u!=v:bad.append(x.index)
 result['differences'][name]=bad
names=sorted(p.name for p in left.glob('anchor-*.bin'))+sorted(p.name for p in left.glob('after-*.bin'))
if names:
 assert names==sorted(p.name for p in right.glob('anchor-*.bin'))+sorted(p.name for p in right.glob('after-*.bin')), 'different memory-bank snapshots'
 ma,mb=[json.loads((d/'metadata.json').read_text()) for d in (left,right)]
 assert ma['layout']==mb['layout'], 'trace repeatability requires the same layout; use compare_state --relocate for relocated state'
else:names=['chip-before.bin','chip-after.bin','slow-before.bin','slow-after.bin']
for name in names:
 x=(left/name).read_bytes();y=(right/name).read_bytes()
 result['snapshot_differences'][name]=sum(u!=v for u,v in zip(x,y))+abs(len(x)-len(y))
result['all_recorded_fields_identical']=not any(result['differences'].values())
(left/'repeatability.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))

raise SystemExit(0 if result['all_recorded_fields_identical'] and not any(result['snapshot_differences'].values()) else 1)
