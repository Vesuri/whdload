"""Compare read-only plane reduction with actual native instructions."""
from unicorn_b import *
from layout import locate
import random
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks']
c=CPU();c.put(0x200000,mem)
c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/face-planes.hunk')).get_segments()[0].get_data()))
rng=random.Random(0x6818);planes=0x330000;out=0x340000;flag=h[6]+0x3958
writes=[]
WRITE=C.CFUNCTYPE(None,C.c_void_p,C.c_int,C.c_uint64,C.c_int,C.c_int64,C.c_void_p)
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
@WRITE
def observe(handle,kind,address,size,value,user):writes.append((address,size))
hook=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hook),1<<11,observe,None,1,0))
def helper(n,xyz):
 regs={r:rng.randrange(0x1000000) for r in range(1,17) if r!=8}
 regs.update({1:planes,9:n,10:xyz[0]&0xffffffff,11:xyz[1]&0xffffffff,12:xyz[2]&0xffffffff})
 for r,v in regs.items():c.rw(r,v)
 c.rw(8,0x8f000);writes.clear();c.call(base)
 assert c.rr(18)==0x90000 and c.rr(8)==0x8f004
 assert all(c.rr(r)==v for r,v in regs.items() if r!=9)
 assert all(0x8ef00<=a and a+s<=0x8f004 for a,s in writes),writes
 return c.rr(9)
count=0;overflow=0
for trial in range(1100):
 n=([1,2,3,127,254,255][trial%6] if trial<100 else rng.randrange(1,256))
 xyz=tuple(rng.choice([-32768,-1,0,1,32767]) if trial<100 else rng.randrange(-32768,32768) for _ in range(3))
 records=[tuple(rng.choice([-32768,-1,0,1,32767]) if trial<100 else rng.randrange(-32768,32768) for _ in range(4)) for _ in range(n)]
 c.put(planes,b''.join(struct.pack('>hhhh',*r) for r in records))
 expected=[]
 for nx,ny,nz,d in records:
  dot=(nx*xyz[0]+ny*xyz[1]+nz*xyz[2])&0xffffffff
  negative=((d-dot)&0x80000000)!=0
  signed=dot if dot<0x80000000 else dot-0x100000000
  overflow+=negative!=(d<signed)
  expected.append(255 if negative else 0)
 c.put(flag,b'\x55');c.rw(1,out);c.rw(2,planes);c.rw(12,n-1);c.rw(13,0)
 c.rw(15,xyz[0]&0xffffffff);c.rw(16,xyz[1]&0xffffffff);c.rw(10,xyz[2]&0xffffffff)
 c.rw(8,0x8f000);c.call(h[0]+0x68f8)
 assert c.get(out,n)==bytes(expected)
 native=c.get(flag,1)[0]
 assert helper(n,xyz)==(1 if native else 0)==int(not any(expected))
 count+=1
# Zero planes leaves native flag untouched; helper signals no decision.
for prior in [0,1,85,255]:
 c.put(planes,b'\0');c.put(flag,bytes([prior]));c.rw(2,planes);c.rw(8,0x8f000);c.call(h[0]+0x6818)
 assert c.get(flag,1)==bytes([prior]);assert helper(0,(0,0,0))==2
for n,xyz in [(256,(0,0,0)),(0xffffffff,(0,0,0)),(1,(32768,0,0)),(1,(0,-32769,0)),(1,(0,0,65535))]:
 assert helper(n,xyz)==0xffffffff
assert overflow>0
print(dict(native_cases=count,overflow_comparisons=overflow,zero_plane_cases=4,invalid_cases=5,read_only_and_register_preservation=True))
c.close()
