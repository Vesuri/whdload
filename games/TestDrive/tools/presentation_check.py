#!/usr/bin/env python3
"""Correlate TD LoadView, displayed plane DMA and visible picture changes."""
import argparse,collections,hashlib,io,json,struct
from pathlib import Path
from PIL import Image
from td_report import regions,Memory
from amigaxdev import barto
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);a=p.parse_args();out=a.capture
meta=json.loads((out/'capture.json').read_text());t=barto.load(str(out/'trace.bin'));dump=(out/'code.bin').read_bytes();mem=Memory(t,dump,meta['base']);rr=meta['regions'];hb=rr['td'];a4=rr['td-data']+0x7ffe
views={}
for off in (-22208,-22190):
 view=a4+off;vp=mem.long(view);ras=mem.long(vp+36);bm=mem.long(ras+4);depth=mem.read(bm+5,1)[0]
 assert depth==5, (hex(view),depth)
 views[view]=[mem.long(bm+8+4*i) for i in range(depth)]
rows=[]
for f in t.fields:
 hits=[]
 for pc,c,r in t.instructions(f):
  if pc==hb+0x7aae:hits.append(r[9])
 dma=collections.Counter()
 for j in range(0,len(f.dma),f.dma_size):
  typ=struct.unpack_from('<h',f.dma,j+29)[0]
  if typ==6:
   addr=struct.unpack_from('<I',f.dma,j+12)[0]
   for view,planes in views.items():
    if any(p<=addr<p+8000 for p in planes):dma[hex(view)]+=1
 im=Image.open(io.BytesIO(f.shot)).convert('RGB')
 rows.append(dict(field=f.index,present=[hex(x) for x in hits],plane_dma=dict(dma),display_sha256=hashlib.sha256(im.crop((74,36,714,436)).tobytes()).hexdigest()))
checks=[]
for row in rows:
 if row['present'] and row['field']+1<len(rows):
  assert len(row['present'])==1
  nxt=rows[row['field']+1]
  assert set(nxt['plane_dma'])==set(row['present']), (row,nxt)
  assert list(nxt['plane_dma'].values())==[20000], nxt
  checks.append(row['field'])
assert checks, 'no presentations checked'
result=dict(validated_next_field_dma=checks,views={hex(k):[hex(x) for x in v] for k,v in views.items()},fields=rows)
(out/'presentation.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result['views']))
for r in rows:
 if r['present']:print(r)
