import struct,json,sys
from pathlib import Path
import numpy as np
root=Path(__file__).resolve().parents[1]
p=Path(sys.argv[1]);d=(p/'horizon.bin').read_bytes();c=(p/'chip-horizon.bin').read_bytes();base=0x880000
i=d.find(b'GPCVERIFY\0');h=struct.unpack_from('>I',d,i+10)[0];db=struct.unpack_from('>I',d,h-base-4)[0]*4+4;a=db+32766-base
bitmap=struct.unpack_from('>I',d,a+3590)[0];ptrs=struct.unpack_from('>5I',d,bitmap-base+8)
actual=sum(np.unpackbits(np.frombuffer(c[x:x+8000],dtype=np.uint8)).reshape(200,320)*(1<<j) for j,x in enumerate(ptrs))
b=(root/'tmp/game/GrandPrixCircuit_v1.0_0008/GrandPrixCircuit/data/italian.shp').read_bytes();n=struct.unpack_from('>H',b,4)[0];shapes={}
for j in range(n):
 name=b[6+4*j:10+4*j].decode();off=6+n*8+struct.unpack_from('>I',b,6+4*n+4*j)[0];w,h,x,y=struct.unpack_from('>4H',b,off)
 pic=np.full((h,w*8),b[off+13],dtype=np.uint8);data=off+20
 for mask in b[off+14:off+20]:
  if not mask:break
  pic|=np.unpackbits(np.frombuffer(b[data:data+w*h],dtype=np.uint8)).reshape(h,w*8)*mask;data+=w*h
 shapes[name]=(pic,y)
expected=actual.copy();mask=np.zeros_like(actual,dtype=bool)
for name,x in [('scen',-8),('sce2',312)]:
 pic,y=shapes[name];top=72-y;l=max(0,x);r=min(320,x+pic.shape[1]);expected[top:top+pic.shape[0],l:r]=pic[:,l-x:r-x];mask[top:top+pic.shape[0],l:r]=True
bad=mask&(actual!=expected);ys,xs=np.where(bad);result=dict(pixels_checked=int(mask.sum()),mismatch_count=int(bad.sum()),bad_x=sorted(set(map(int,xs))),bad_y=sorted(set(map(int,ys))))
print(json.dumps(result));(p/'pixel-result.json').write_text(json.dumps(result,indent=2)+'\n')
np.savez(p/'pixels.npz',actual=actual,expected=expected,mask=mask)
