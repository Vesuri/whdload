import json,struct,sys
from pathlib import Path
for tag in sys.argv[1:]:
 rows=json.loads((Path('tmp')/('visibility-'+tag)/'trace.json').read_text()); counts={'far_band':0,'mirror_band':0}; examples=[]
 for r in rows:
  b=bytes.fromhex(r['state']);cam=struct.unpack_from('>I',b,0x1e)[0];objs=bytes.fromhex(r['objects']);records=[struct.unpack_from('>10H',objs,i) for i in range(0,len(objs),20)]
  for p in [0xa6460,0xa64e0,0xa6260]:
   o=p-0xa5d00;pos=struct.unpack_from('>I',b,o+4)[0];gap=(pos-cam)/65536
   if 30<gap<31 and p in r['active'] and 600<r['field']<750:
    assert len(records)==6,(tag,r['field'],records)
    counts['far_band']+=1
    if len(examples)<8:examples.append([r['field'],hex(p),gap,records])
   if p==0xa6260 and -2<gap<-1 and b[o+0x71]==10 and p in r['active'] and 1000<r['field']<1200:
    counts['mirror_band']+=1
    # This rider uses native mirror graphic 0x154; no lateral clipping here.
    assert any(x[4]==0x154 for x in records),(tag,r['field'],gap,records)
 print(tag,len(rows),counts)
 (Path('tmp')/('visibility-'+tag)/'fix-check.json').write_text(json.dumps(dict(counts=counts,examples=examples),indent=2))
