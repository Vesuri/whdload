"""Compare complete native periodic branch selection and reserve arithmetic."""
import json,random
from unicorn_b import *
from layout import locate
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks']
c=CPU();c.put(0x200000,mem);c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/world-reserves.hunk')).get_segments()[0].get_data()))
listing=(root/'tmp/c/world-reserves.lst').read_text()
def sym(n):return base+int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
P=0x300000;REF=0x301000;CLONE=0x310000;BAD=0x320000
rng=random.Random(0x590c);calls=0
CODE=C.CFUNCTYPE(None,C.c_void_p,C.c_uint64,C.c_uint32,C.c_void_p)
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
u.uc_emu_stop.argtypes=[C.c_void_p]
@CODE
def boundary(handle,a,n,user):ok(u.uc_emu_stop(handle))
hooks=[]
for off in [0x58c6,0x5a0c]:
 hook=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hook),1<<2,boundary,None,h[0]+off,h[0]+off));hooks.append(hook)
def call(name,args):
 global calls
 regs={r:rng.randrange(0x1000000) for r in range(1,17) if r not in [8,9]};regs.update(args)
 for r,v in regs.items():c.rw(r,v)
 c.rw(8,0x8f000);c.call(sym(name));calls+=1
 assert c.rr(18)==0x90000 and c.rr(8)==0x8f004
 assert all(c.rr(r)==v for r,v in regs.items() if r!=9),name
 return c.rr(9)
assert call('world_reserves_prepare',{1:h[0],2:CLONE})==0
outcomes={0:0,1:0,2:0}
for n in range(4096):
 b=bytearray(rng.randbytes(86))
 tick=[0,16,65520,65535,1,15,32,48][n%8]
 struct.pack_into('>H',b,12,tick);b[24]=0 if n%3 else rng.choice([1,2,255])
 b[66]=rng.choice([0,4,8,12,16,28,255]);b[57]=rng.choice([0,1,2,21,41,42,127,255]);b[14]=rng.randrange(4)
 b[27]=rng.choice([0,31,32,128,255]);struct.pack_into('>H',b,28,rng.choice([0,1,256,65535]));b[82]=rng.choice([0,1,2,255])
 struct.pack_into('>HH',b,4,rng.choice([0,1,21,64,256,32767,32768,65535]),rng.choice([0,1,63,256,32767,65535]))
 c.put(REF,b);c.rw(6,REF);c.rw(8,0x8f000);c.rw(9,rng.randrange(2**32));c.call(h[0]+0x58ac,end=h[0]+0x598a)
 pc=c.rr(18);expected={h[0]+0x58c6:2,h[0]+0x5a0c:0,h[0]+0x598a:1}[pc]
 want=c.get(REF,86);c.put(P,b)
 got=call('world_reserves_step',{1:P,2:CLONE})
 assert got==expected and c.get(P,86)==want,(n,got,expected)
 outcomes[got]+=1
# Every source word is checked before any clone destination write.
rejects=0
for start,size in [(0x7f80,0x24),(0x590c,0x7e)]:
 original=c.get(h[0]+start,size)
 for off in range(0,size,2):
  corrupt=bytearray(original);corrupt[off]^=1;c.put(h[0]+start,corrupt);c.put(BAD,b'\xa5'*164)
  assert call('world_reserves_prepare',{1:h[0],2:BAD})==0xffffffff
  assert c.get(BAD,164)==b'\xa5'*164
  rejects+=1
 c.put(h[0]+start,original)
assert all(outcomes.values())
print(json.dumps(dict(status='passed',native_cases=4096,outcomes=outcomes,signature_rejections=rejects,calls=calls)))
c.close()
