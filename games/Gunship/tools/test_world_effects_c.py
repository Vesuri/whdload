"""Native effect allocation and pose equivalence with private world inputs."""
import json,random,itertools
from unicorn_b import *
from layout import locate
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks'];p=h[6]+0x3b88
c=CPU();c.put(0x200000,mem);c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/world-effects.hunk')).get_segments()[0].get_data()))
listing=(root/'tmp/c/world-effects.lst').read_text()
def sym(n):return base+int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
clone=0x330000;rc=0x340000;record=0x350000;heading=0x360000
for name,regs in [('world_rng_prepare',{1:h[0]+0x7a5c,2:rc,3:record,4:h[2]}),('world_effect_prepare',{1:h[0],2:clone,3:rc,4:heading})]:
 for r,v in regs.items():c.rw(r,v)
 c.rw(8,0x8f000);c.call(sym(name));assert c.rr(9)==0,name
expected=bytearray(c.get(h[0]+0x9b9a,164));struct.pack_into('>I',expected,0x32,heading)
for off in [0x6c,0x82,0x92]:struct.pack_into('>I',expected,off,rc+14)
assert c.get(clone,164)==expected
original=c.get(h[0]+0x9b9a,164);rejects=0
for off in [0,2,6,0x30,0xa2,0x6a,0x6c,0x80,0x82,0x90,0x92]:
 corrupt=bytearray(original);corrupt[off]^=1;c.put(h[0]+0x9b9a,corrupt);c.put(0x370000,b'Z'*168)
 for r,v in {1:h[0],2:0x370002,3:rc,4:heading}.items():c.rw(r,v)
 c.rw(8,0x8f000);c.call(sym('world_effect_prepare'))
 assert c.rr(9)==0xffffffff and c.get(0x370000,168)==b'Z'*168
 c.put(h[0]+0x9b9a,original);rejects+=1
regions=[(h[4]+0x3cc,4),(h[0]+0xba08,4),(h[0]+0xc6a0,0x90)]
CODE=C.CFUNCTYPE(None,C.c_void_p,C.c_uint64,C.c_uint32,C.c_void_p)
MEM=C.CFUNCTYPE(None,C.c_void_p,C.c_int,C.c_uint64,C.c_int,C.c_int64,C.c_void_p)
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
draws=0;checking=False;bad=[]
@CODE
def count(handle,a,n,user):
 global draws
 draws+=1
@MEM
def write(handle,kind,a,n,value,user):
 if checking and not(any(start<=a and a+n<=start+size for start,size in regions) or 0x8e000<=a and a+n<=0x8f004):bad.append((a,n))
hooks=[]
for a in [h[0]+0x7a6a,rc+14]:
 hook=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hook),1<<2,count,None,a,a));hooks.append(hook)
hook=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hook),1<<11,write,None,1,0));hooks.append(hook)
rng=random.Random(0x9b9a);cases=0;counts=set()
for mode,mask,variant in itertools.product([0,1],range(64),range(8)):
 inputs=rng.randbytes(8);angle=rng.randbytes(2);live=rng.randbytes(8);liveangle=rng.randbytes(2);b=rng.randbytes(86)
 c.put(p,b);c.put(record+32,inputs);c.put(heading,angle);c.put(h[6]+0x45cc,bytes([mode]));initial=[rng.randbytes(n) for a,n in regions];initial[1]=struct.pack('>HH',mask,rng.randrange(65536));results=[]
 regs={r:rng.randrange(0x1000000) for r in range(1,17) if r!=8};regs[6]=p
 for patched in [False,True]:
  for (a,n),data in zip(regions,initial):c.put(a,data)
  c.put(h[2]+0x14,live if patched else inputs);c.put(h[6]+0x390a,liveangle if patched else angle)
  for r,v in regs.items():c.rw(r,v)
  c.rw(17,0x2000);c.rw(8,0x8f000);draws=0;checking=patched;c.call(clone if patched else h[0]+0x9b9a);checking=False
  results.append(([c.rr(r) for r in range(1,17)],[c.get(a,n) for a,n in regions],draws))
 assert results[0]==results[1],(mode,mask,variant)
 assert draws==(0 if mask==63 else 3) and not bad
 assert c.get(p,86)==b and c.get(record+32,8)==inputs and c.get(heading,2)==angle
 assert c.get(h[2]+0x14,8)==live and c.get(h[6]+0x390a,2)==liveangle
 counts.add(draws);cases+=1
report=dict(native_cases=cases,prepare_rejections=rejects,draw_counts=sorted(counts),unexpected_writes=bad,scope='native effect constructor/allocator, all occupancy masks, private heading/timestamp; no renderer removal or countdown migration')
(root/'tmp/c/world-effects-tests.json').write_text(json.dumps(report,indent=2)+'\n');print(report);c.close()
