import struct,json,sys,hashlib
from pathlib import Path
import numpy as np
root=Path(__file__).resolve().parents[1]
p=Path(sys.argv[1])
b=(root/'tmp/game/GrandPrixCircuit_v1.0_0008/GrandPrixCircuit/data/italian.shp').read_bytes();n=struct.unpack_from('>H',b,4)[0];shapes={}
for j in range(n):
 name=b[6+4*j:10+4*j].decode();off=6+n*8+struct.unpack_from('>I',b,6+4*n+4*j)[0];w,h,x,y=struct.unpack_from('>4H',b,off)
 pic=np.full((h,w*8),b[off+13],dtype=np.uint8);data=off+20
 for mask in b[off+14:off+20]:
  if not mask:break
  pic|=np.unpackbits(np.frombuffer(b[data:data+w*h],dtype=np.uint8)).reshape(h,w*8)*mask;data+=w*h
 shapes[name]=(pic,y)

samples=json.loads((p/'samples.json').read_text());assert len(samples)==64
assert set(x['pan'] for x in samples)=={base+i for base in [0,320,512,832] for i in range(16)}
results=[]
for s in samples:
 c=(p/('pan-%02d.bin'%s['index'])).read_bytes()
 actual=sum(np.unpackbits(np.frombuffer(c[x:x+8000],dtype=np.uint8)).reshape(200,320)*(1<<j) for j,x in enumerate(s['planes']))
 expected=actual.copy();mask=np.zeros_like(actual,dtype=bool)
 for name,offset in [('scen',0),('sce2',320),('sce3',512),('sce4',832),('scen',1024)]:
  pic,y=shapes[name];x=offset-s['pan'];top=72-y;l=max(0,x);r=min(320,x+pic.shape[1])
  if l>=r:continue
  expected[top:top+pic.shape[0],l:r]=pic[:,l-x:r-x];mask[top:top+pic.shape[0],l:r]=True
 bad=mask&(actual!=expected)
 assert not bad.any(),(s['pan'],int(bad.sum()),sorted(set(map(int,np.where(bad)[1]))))
 changed=actual.copy();y,x=np.argwhere(mask)[0];changed[y,x]^=1;assert (mask&(changed!=expected)).any()
 results.append(dict(pan=s['pan'],pixels=int(mask.sum()),mismatches=int(bad.sum())))
r=dict(samples=64,pixels=sum(x['pixels'] for x in results),exact=True,negative_control='changed scenery pixel rejected',slave_sha256=hashlib.sha256((p/'slave.slave').read_bytes()).hexdigest(),results=results)
(p/'pixel-result.json').write_text(json.dumps(r,indent=2)+'\n');print(p.name,r['samples'],r['pixels'],'pixels exact')
