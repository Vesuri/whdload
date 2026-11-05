"""Native final scene endpoint versus direct committed-state construction."""
from unicorn_b import *
from layout import locate
import random
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks'];c=CPU();c.put(0x200000,mem)
c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/scene-state.hunk')).get_segments()[0].get_data()))
# Omit actual rendering, retaining native interpolation and endpoint arithmetic.
c.put(h[0]+0x5c04,bytes.fromhex('4e75'))
rng=random.Random(0x4288);dest=0x330000;writes=[];renders=[]
WRITE=C.CFUNCTYPE(None,C.c_void_p,C.c_int,C.c_uint64,C.c_int,C.c_int64,C.c_void_p)
CODE=C.CFUNCTYPE(None,C.c_void_p,C.c_uint64,C.c_uint32,C.c_void_p)
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
@WRITE
def write(handle,kind,a,n,v,user):writes.append((a,n))
@CODE
def draw(handle,a,n,user):renders.append(c.get(h[6]+0x3904,54))
hooks=[]
for kind,fn,start,end in [(1<<11,write,1,0),(1<<2,draw,h[0]+0x5c04,h[0]+0x5c04)]:
 hook=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hook),kind,fn,None,start,end));hooks.append(hook)
frames=0
for trial in range(512):
 camera=bytes(rng.randrange(256) for _ in range(12));objects=bytes(rng.randrange(256) for _ in range(36));special=bytes(rng.randrange(256) for _ in range(6))
 c.put(h[4],camera);c.put(h[0]+0xc6a0,objects)
 for off,v in zip([0x3be3,0x3c5d,0x3c63,0x3cdd,0x3ddd,0x3d5d],special):c.put(h[6]+off,bytes([v]))
 c.put(dest-2,b'\xa5'*58)
 regs={r:rng.randrange(0x1000000) for r in range(1,17) if r!=8};regs.update({1:h[4],2:h[0]+0xc6a0,3:h[6],4:dest})
 for r,v in regs.items():c.rw(r,v)
 c.rw(8,0x8f000);writes.clear();c.call(base)
 assert c.rr(18)==0x90000 and c.rr(9)==0 and c.rr(8)==0x8f004
 assert all(c.rr(r)==v for r,v in regs.items() if r!=9)
 assert all((dest<=a and a+n<=dest+54) or (0x8ef00<=a and a+n<=0x8f004) for a,n in writes)
 assert c.get(dest-2,2)==c.get(dest+54,2)==b'\xa5\xa5'
 expected=c.get(dest,54);assert expected==camera+objects+special
 # Vary prior endpoint, active-slot mask and number of intermediate images.
 c.put(h[5]+10,bytes(rng.randrange(256) for _ in range(54)))
 c.put(h[0]+0xba0a,struct.pack('>H',trial&63))
 period=[1,3,20,50][trial%4];c.put(h[6]+0x1548,struct.pack('>HHH',period,1,0))
 renders.clear();c.rw(8,0x8f000);c.call(h[0]+0x4288,end=h[0]+0x444a)
 assert c.rr(18)==h[0]+0x444a
 assert c.get(h[6]+0x3904,54)==expected,(trial,c.get(h[6]+0x3904,54).hex(),expected.hex())
 assert len(renders)==period-1,(trial,len(renders),period)
 frames+=len(renders)
print(dict(native_endpoint_cases=512,intermediate_images=frames,register_and_write_checks=True))
c.close()
