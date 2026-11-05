"""Native raster prefix/state/ABI checks. Unicorn does NOT emulate blitter DMA."""
from unicorn_b import *
from layout import locate
from functools import lru_cache
import json
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();chip=(root/'tmp/prof/flight1-mem/chip.bin').read_bytes();h=locate(mem)['hunks']
blob=bytes(BinFmt().load_image(str(build/'release/Gunship.Slave')).get_segments()[0].get_data());listing=(build/'release/Gunship.lst').read_text(encoding='latin1')
@lru_cache(None)
def sym(n):return int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
def addr(n):return base+sym(n)
c=CPU();vr=0x110000;wt=0x120000;camera=0x130000;state=wt+sym('WT_STATE');target=h[0]+0xa99e;size=sym('VR_SAVED_TARGET')+168
c.put(base,blob)
def call(entry,regs={},end=0x90000):
 c.rw(17,0x2000)
 for r,v in regs.items():c.rw(r,v)
 c.rw(8,0x8f000);c.call(entry,end=end)
 assert c.rr(18)==end,(hex(entry),hex(c.rr(18)))
 return c.rr(9)
def reset():
 c.put(0,chip);c.put(base,blob);c.put(0x200000,mem)
 c.put(h[0]+0x825e,bytes.fromhex('4e75'))
 c.put(0xdff000,bytes(512))
CODE=C.CFUNCTYPE(None,C.c_void_p,C.c_uint64,C.c_uint32,C.c_void_p)
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
queries=[]
injected=None
@CODE
def inject(handle,a,n,user):
 if injected is not None:c.put(target,injected)
ih=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(ih),1<<2,inject,None,vr+0x6c,vr+0x6c))
@CODE
def pixel(handle,a,n,user):
 x,y=c.rr(9)&65535,c.rr(10)&65535;queries.append((x,y));c.rw(9,(x*3+y*7)&255)
hook=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hook),1<<2,pixel,None,h[0]+0x825e,h[0]+0x825e))
reset();assert call(addr('visibility_raster_prepare'),{1:h[0],2:h[6],3:vr})==0
assert c.get(vr,0x7a)==c.get(h[0]+0x5c04,0x74)+bytes.fromhex('4cdf78f84e75')
relocs=[struct.unpack('>3H',c.get(addr('visibility_raster_relocs')+6*i,6)) for i in range(14)]
rejects=0
for off in [0,2,0xb4,0xb6,0xb8]+[off+d for off,_,_ in relocs for d in (0,2)]:
 a=h[0]+0x5c04+off;old=c.get(a,2);c.put(a,bytes(v^1 for v in old));c.put(vr-2,b'Z'*(size+4))
 assert call(addr('visibility_raster_prepare'),{1:h[0],2:h[6],3:vr})==0xffffffff
 assert c.get(vr-2,size+4)==b'Z'*(size+4)
 c.put(a,old);rejects+=1
reset();assert call(addr('visibility_raster_prepare'),{1:h[0],2:h[6],3:vr})==0
cases=0;nonempty=0;sample_count=0
for xy in [(0x7fff,0x7fff),(0x8000,0x8000),(0x7800,0x8800)]:
 for height in (64,512):
  for heading in range(0,256,32):
   reset();assert call(addr('target_select_prepare'),{1:h[0],2:h[6],3:wt})==0
   initial=bytearray(c.get(target,168));initial[2:4]=bytes(2)
   for i,o in enumerate((0,18,36,54,72)):struct.pack_into('>H',initial,8+2*i,o)
   cam=struct.pack('>6H',*xy,height+24,(-heading*256)&65535,0,0);c.put(camera,cam)
   special=struct.pack('>3H',xy[0]+128,xy[1]+128,height+24)
   for off,v in zip([0x3be3,0x3c5d,0x3c63,0x3cdd,0x3ddd,0x3d5d],special):c.put(h[6]+off,bytes([v]))
   coords=struct.pack('>18H',*[xy[0]+(i-2)*128 for i in range(6)],*[xy[1]+(i-2)*128 for i in range(6)],*[height+32]*6)
   c.put(h[0]+0xc6a0,coords);c.put(h[0]+0xba08,b'\0\x3f');c.put(target,initial);c.put(state,initial)
   mode=cases%2;c.put(h[6]+0x3b9e,bytes([mode]));palette=bytes([17+cases,93+cases]);c.put(h[6]+0x16dc+mode*256+24,palette)
   before=c.get(0x97ee00,0x21200);chipbefore=c.get(0,0x80000)
   call(addr('scene_state_build'),{1:camera,2:h[0]+0xc6a0,3:h[6],4:h[6]+0x3904})
   call(h[0]+0x5c04,end=h[0]+0x5c78)
   want=c.get(target,168);count=int.from_bytes(want[2:4],'big');assert count<=5
   expected_queries=[(int.from_bytes(want[0x80+2*i:0x82+2*i],'big'),int.from_bytes(want[0x8a+2*i:0x8c+2*i],'big')) for i in range(count)]
   expected_pixels=bytes([(x*3+y*7)&255 for x,y in expected_queries])+bytes(6-count)
   native_after=bytearray(c.get(0x97ee00,0x21200));native_after[target-0x97ee00:target-0x97ee00+168]=initial
   native_custom=c.get(0xdff000,512)
   c.put(0x97ee00,before);c.put(0,chipbefore);c.put(0xdff000,bytes(512));queries.clear()
   regs={r:0x1100+r for r in list(range(1,8))+list(range(10,17))};regs.update({1:vr,2:wt,3:camera,4:h[0]+0xc6a0})
   assert call(addr('visibility_raster_step'),regs)==0
   assert all(c.rr(r)==v for r,v in regs.items()),[(r,c.rr(r),v) for r,v in regs.items() if c.rr(r)!=v]
   assert c.get(state,168)==want,(xy,height,heading)
   assert c.get(wt+sym('WT_PIXELS'),6)==expected_pixels
   assert c.get(wt+sym('WT_PALETTE')+24,2)==palette
   assert queries==expected_queries,(queries,expected_queries)
   actual=c.get(0x97ee00,0x21200)
   assert actual==native_after,[(hex(0x97ee00+i),a,b) for i,(a,b) in enumerate(zip(actual,native_after)) if a!=b][:20]
   assert c.get(0xdff000,512)==native_custom
   assert c.get(target,168)==initial
   cases+=1;nonempty+=count>0;sample_count+=count
assert nonempty
# Exercise all five pixel indices independently of sparse scene candidates.
# Injection is exactly after native collection and before the prefix returns.
for count in range(6):
 reset();assert call(addr('target_select_prepare'),{1:h[0],2:h[6],3:wt})==0
 c.put(state,initial);native_before=c.get(target,168)
 injected=bytearray(initial);struct.pack_into('>H',injected,2,count)
 for i in range(5):
  struct.pack_into('>H',injected,0x80+2*i,33+i*9)
  struct.pack_into('>H',injected,0x8a+2*i,11+i*7)
 queries.clear()
 assert call(addr('visibility_raster_step'),{1:vr,2:wt,3:camera,4:h[0]+0xc6a0})==0
 expected_queries=[(33+i*9,11+i*7) for i in range(count)]
 assert queries==expected_queries and c.get(state,168)==injected
 assert c.get(wt+sym('WT_PIXELS'),6)==bytes([(x*3+y*7)&255 for x,y in expected_queries])+bytes(6-count)
 assert c.get(target,168)==native_before
injected=None
for value in (1,74,65534):
 c.put(state+8,struct.pack('>H',value));before=(c.get(0x97ee00,0x21200),c.get(wt,sym('WT_SIZE')),c.get(vr,size))
 assert call(addr('visibility_raster_step'),{1:vr,2:wt,3:camera,4:h[0]+0xc6a0})==0xfffffffd
 assert before==(c.get(0x97ee00,0x21200),c.get(wt,sym('WT_SIZE')),c.get(vr,size))
print(json.dumps(dict(status='passed',scenes=cases,nonempty=nonempty,pixel_calls=sample_count,signature_rejections=rejects,injected_counts=6,blitter_dma_emulated=False)));c.close()
