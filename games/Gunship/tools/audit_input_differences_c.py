import os
from pathlib import Path
import json,re,sys
l=Path(os.environ.get('LISTING','tmp/build/collision.slave.lst')).read_text(encoding='latin1');h=int(re.search(r'^([0-9A-F]{8}) RT_HISTORY$',l,re.M)[1],16)
folders=[Path(x) for x in sys.argv[1:3]]
def records(p):
 e=json.loads((p/'input-events.json').read_text())['epoch'];d={}
 for f in list(p.glob('input-*-arena.bin'))+list(p.glob('world-*/arena.bin')):
  if f.parent.name.startswith('world-') and int(f.parent.name.split('-')[1])>int(os.environ.get('MAX_WORLD','2147483647')):continue
  a=f.read_bytes()
  for i in range(128):
   b=a[h+20+40*i:h+60+40*i];field=int.from_bytes(b[:4],'big')-e
   if field>0:d[field]=b
 return d
x,y=[records(p) for p in folders];common=sorted(x.keys()&y.keys());offsets={};pairs=set();fields=[]
for field in common:
 diff=tuple(i for i in range(4,32) if x[field][i]!=y[field][i])
 if not diff:continue
 fields.append(field);offsets[str(diff)]=offsets.get(str(diff),0)+1;pairs.add((x[field][16:20].hex(),y[field][16:20].hex()))
 assert set(diff)<=set(range(16,20)),(field,diff)
r=dict(common_fields=len(common),raw_differing_fields=len(fields),offset_counts=offsets,relative_word_pairs=sorted(pairs),other_control_bytes_equal=True,scope='Only TR_RELATIVE is omitted from the consumed-control claim; raw comparisons remain unchanged.')
(Path(os.environ.get('REPORT_DIR',str(folders[1])))/'input-difference-audit.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
