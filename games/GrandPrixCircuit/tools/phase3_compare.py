#!/usr/bin/env python3
import argparse,json,collections
from pathlib import Path
from compare_state import differences
from phase3_decode import decode
p=argparse.ArgumentParser();p.add_argument('a',type=Path);p.add_argument('b',type=Path);p.add_argument('--out',type=Path);a=p.parse_args();ma,mb=[json.loads((r/'metadata.json').read_text()) for r in (a.a,a.b)]
files=sorted((a.a/'state').glob('[0-9]*.bin'));assert files and len(files)==len(list((a.b/'state').glob('[0-9]*.bin')))
counts=collections.Counter();first={};offsets=collections.Counter();equal=0
for f in files:
 x,y=f.read_bytes(),(a.b/'state'/f.name).read_bytes();ds=differences(x,y,ma,mb);equal+=not ds;offsets.update(ds)
 X,Y=decode(x,ma),decode(y,mb)
 for k in X:
  if X[k]!=Y[k]:counts[k]+=1;first.setdefault(k,dict(sample=int(f.stem),a=X[k],b=Y[k]))
result=dict(samples=len(files),whole_data_equal=equal,differing_offsets=dict(offsets),decoded_differing_fields=dict(counts),first_differences=first)
for root,m in [(a.a,ma),(a.b,mb)]:
 d=decode((root/'state'/files[-1].name).read_bytes(),m);cs=json.loads((root/'state/counts.json').read_text());result[str(root)]=dict(epoch=m['epoch'],last=d,counts=cs[-1])
if a.out:a.out.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='differing_offsets'},indent=2))
