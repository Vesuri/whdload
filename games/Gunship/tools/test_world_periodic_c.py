"""Native periodic housekeeping with deadline-bound RNG; audio endpoints stubbed."""
import json,random
from unicorn_b import *
from layout import locate
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks'];p=h[6]+0x3b88
c=CPU();c.put(0x200000,mem);c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/world-periodic.hunk')).get_segments()[0].get_data()))
listing=(root/'tmp/c/world-periodic.lst').read_text()
def sym(n):return base+int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
clone=0x330000;rc=0x340000;record=0x350000;rng=random.Random(0x598a);calls=0
for off in [0xb4e4,0xb57c]:c.put(h[0]+off,bytes.fromhex('4e75'))
def call(name,args):
 global calls
 regs={r:rng.randrange(0x1000000) for r in range(1,17) if r not in [8,9]};regs.update(args)
 for r,v in regs.items():c.rw(r,v)
 c.rw(8,0x8f000);c.call(sym(name));calls+=1
 assert c.rr(18)==0x90000 and c.rr(8)==0x8f004
 assert all(c.rr(r)==v for r,v in regs.items() if r!=9),name
 return c.rr(9)
assert call('world_rng_prepare',{1:h[0]+0x7a5c,2:rc,3:record,4:h[2]})==0
assert call('world_periodic_prepare',{1:h[0],2:clone,3:rc,4:h[6]})==0
regions=[(p,0x300),(h[4]+0x3cc,4),(h[6]+0x1560,24),(h[4]+0x1c4,3),(h[0]+0xa99e,1),(h[1]+0x180,22)]
CODE=C.CFUNCTYPE(None,C.c_void_p,C.c_uint64,C.c_uint32,C.c_void_p)
MEM=C.CFUNCTYPE(None,C.c_void_p,C.c_int,C.c_uint64,C.c_int,C.c_int64,C.c_void_p)
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
trace=[];writes=[];checking=False;draws=0
@CODE
def callback(handle,a,n,user):
 global draws
 if a in [h[0]+0x7a6a,rc+14]:draws+=1
 else:trace.append((a-h[0],c.rr(9)&255))
@MEM
def write(handle,kind,a,n,value,user):
 if checking and not(any(start<=a and a+n<=start+size for start,size in regions) or 0x8e000<=a and a+n<=0x8f004):writes.append((hex(a),n))
hooks=[]
for a in [h[0]+0x7a6a,rc+14]+[h[0]+off for off in [0x7b7e,0x7bd0,0x8036,0x7fbe,0x46de,0xb4e4,0xb57c]]:
 hook=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hook),1<<2,callback,None,a,a));hooks.append(hook)
hook=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hook),1<<11,write,None,1,0));hooks.append(hook)
paths=set()
for n in range(512):
 b=bytearray(rng.randbytes(0x300));b[17]=[0,127,255,63][n%4];b[13]=0 if n&4 else 16
 b[0x56+5]=0 if n&8 else 1;b[0xd0+5]=0;b[0x256+5]=n&1
 b[15]=(b[15]&~64)|(64 if n&16 else 0)
 initial=[bytes(b),rng.randbytes(4),rng.randbytes(24),bytes([rng.choice([0,6,255]),rng.choice([0,1,2]),0]),bytes([rng.choice([0,255])]),rng.randbytes(22)]
 stamp=rng.randbytes(8);live=rng.randbytes(8)
 c.put(record+32,stamp);c.put(h[6]+0x45cc,bytes([n%2]));c.put(h[6]+0x395c,bytes([0 if n&32 else 1]));c.put(h[6]+0x157b,bytes([n&1]))
 results=[]
 for patched in [False,True]:
  for (a,size),value in zip(regions,initial):c.put(a,value)
  c.put(h[2]+0x14,live if patched else stamp);trace.clear();writes.clear();draws=0;checking=True
  if patched:assert call('world_periodic_step',{1:p,2:clone})==0
  else:c.rw(6,p);c.rw(8,0x8f000);c.call(h[0]+0x598a,end=h[0]+0x5a0c)
  checking=False
  assert not writes,writes
  results.append(([c.get(a,size) for a,size in regions],list(trace),draws))
 assert results[0]==results[1],n
 assert draws==1 and c.get(h[2]+0x14,8)==live and c.get(record+32,8)==stamp
 paths.add(tuple(off for off,value in trace))
before=[c.get(a,size) for a,size in regions]
assert call('world_periodic_step',{1:p+2,2:clone})==0xffffffff
assert before==[c.get(a,size) for a,size in regions]
original=c.get(h[0]+0x598a,130);rejects=0
for off in [0,0x12,0x26,0x28,0x5a,0x5c]+[i+j for i in [4,0x18,0x30,0x40,0x48,0x64,0x6c,0x7c] for j in [0,2]]:
 corrupt=bytearray(original);corrupt[off]^=1;c.put(h[0]+0x598a,corrupt);c.put(0x370000,b'Z'*136)
 assert call('world_periodic_prepare',{1:h[0],2:0x370000,3:rc,4:h[6]})==0xffffffff
 assert c.get(0x370000,136)==b'Z'*136
 rejects+=1
c.put(h[0]+0x598a,original)
print(json.dumps(dict(status='passed',native_cases=512,paths=[list(x) for x in sorted(paths)],signature_rejections=rejects,calls=calls)))
c.close()
