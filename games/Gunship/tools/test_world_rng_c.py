"""Native RNG equivalence with private deadline timestamps and changing live input."""
import json,random,itertools
from unicorn_b import *
from layout import locate
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks'];p=h[6]+0x3b88;seed=h[4]+0x3cc
c=CPU();c.put(0x200000,mem);c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/world-rng.hunk')).get_segments()[0].get_data()))
listing=(root/'tmp/c/world-rng.lst').read_text();entry=base+int(re.search(r'^([0-9A-F]{8}) world_rng_prepare$',listing,re.M)[1],16)
native=h[0]+0x7a5c;clone=0x330000;record=0x340000;copy=0x350000;dest=0x360000
rng=random.Random(0x715c);calls=0

def prepare(src,target):
 global calls
 regs={r:rng.randrange(0x1000000) for r in range(1,17) if r!=8};regs.update({1:src,2:target,3:record,4:h[2]})
 for r,v in regs.items():c.rw(r,v)
 c.rw(8,0x8f000);c.call(entry);calls+=1
 assert c.rr(8)==0x8f004 and all(c.rr(r)==v for r,v in regs.items() if r!=9)
 return c.rr(9)
assert prepare(native,clone)==0
expected=bytearray(c.get(native,108));struct.pack_into('>I',expected,0x22,record+36);struct.pack_into('>I',expected,0x34,record+32)
assert c.get(clone,108)==expected
# Rejections must leave all destination bytes untouched.
for off in [0,4,8,12,0x20,0x22,0x32,0x34,0x6a]:
 b=bytearray(c.get(native,108));b[off]^=1;c.put(copy,b);before=rng.randbytes(112);c.put(dest-2,before)
 assert prepare(copy,dest)==0xffffffff and c.get(dest-2,112)==before
MEM=C.CFUNCTYPE(None,C.c_void_p,C.c_int,C.c_uint64,C.c_int,C.c_int64,C.c_void_p)
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
checking=False;bad=[]
@MEM
def write(handle,kind,a,n,value,user):
 if checking and not(seed<=a and a+n<=seed+4 or 0x8e000<=a and a+n<=0x8f004):bad.append((a,n))
hook=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hook),1<<11,write,None,1,0))
cases=0
for mode,offset,bound,variant in itertools.product([0,1,255],[0,10,14],[1,3,256,32767,65535],range(64)):
 stamp=rng.randbytes(8);initialseed=rng.randbytes(4);live=rng.randbytes(8);b=bytearray(rng.randbytes(40));b[32:40]=stamp;c.put(record,b)
 c.put(h[6]+0x45cc,bytes([mode]));c.put(p+12,rng.randbytes(2))
 regs={r:rng.randrange(0x1000000) for r in range(1,17) if r!=8};regs[10]=(rng.randrange(65536)<<16)|bound;results=[]
 for useclone in [False,True]:
  c.put(seed,initialseed);c.put(h[2]+0x14,live if useclone else stamp)
  for r,v in regs.items():c.rw(r,v)
  c.rw(17,0x2000);c.rw(8,0x8f000);c.put(0x8f004,struct.pack('>I',bound));checking=useclone
  c.call((clone if useclone else native)+offset);checking=False;calls+=1
  results.append(([c.rr(r) for r in range(1,17)],c.get(seed,4)))
 assert results[0]==results[1],(mode,offset,bound,variant)
 assert c.get(h[2]+0x14,8)==live and c.get(record,40)==b and not bad
 cases+=1
report=dict(native_cases=cases,prepare_rejections=9,calls=calls,unexpected_writes=bad,scope='all three native RNG entry points and modes; private timestamps with unrelated live input; standalone, no native call redirection')
(root/'tmp/c/world-rng-tests.json').write_text(json.dumps(report,indent=2)+'\n');print(report);c.close()
