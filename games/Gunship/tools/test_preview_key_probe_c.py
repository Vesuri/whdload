from unicorn_b import *
from functools import lru_cache
import random,json
blob=bytes(BinFmt().load_image(str(build/'preview-key.slave')).get_segments()[0].get_data());listing=(build/'preview-key.slave.lst').read_text(encoding='latin1')
@lru_cache(None)
def sym(n):return int(re.search(r'^([0-9A-F]{8}) '+n+'$',listing,re.M)[1],16)
c=CPU();c.put(base,blob);rng=random.Random(918);ps=0x170000;p=0x171000;packet=0x172000
for address,size in [(ps,sym('PS_SIZE')),(p,86),(packet,10)]:c.put(address,rng.randbytes(size))
data=base+sym('preview_key_probe_data');calls=0;hits=0;last=None
for i in range(200):
 if i%3==1:
  address,size=[(ps,sym('PS_SIZE')),(p,86),(packet,10)][i//3%3];offset=i%size;v=c.get(address+offset,1)[0];c.put(address+offset,bytes([v^1]))
 regs={r:0x4000+r for r in list(range(1,8))+list(range(9,17))};regs.update({1:ps,2:p,3:0x173000,4:0x174000,5:packet,9:19})
 key=c.get(p,86)+c.get(ps,sym('PS_SIZE'))+c.get(packet,10)+struct.pack('>III',regs[9],regs[3],regs[4])
 c.rw(17,0x2000|(16 if i&1 else 0))
 for r,v in regs.items():c.rw(r,v)
 c.rw(8,0x8f000);c.call(base+sym('preview_key_probe'))
 assert c.rr(18)==0x90000
 assert all(c.rr(r)==v for r,v in regs.items())
 assert c.rr(17)&16==(16 if i&1 else 0)
 calls+=1;hits+=int(key==last);last=key
 assert struct.unpack('>II',c.get(data+8,8))==(calls,hits)
 assert c.get(base+sym('preview_key_probe_previous'),len(key))==key
 assert c.get(p,86)+c.get(ps,sym('PS_SIZE'))+c.get(packet,10)==key[:-12]
print(json.dumps(dict(calls=calls,hits=hits,registers_and_x_preserved=True,inputs_unchanged=True)));c.close()
