"""Actual native scene projection feeds private current-view capture hooks."""
from unicorn_b import *
from layout import locate
from functools import lru_cache
import json
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks'];p=h[6]+0x3b88
blob=bytes(BinFmt().load_image(str(build/'release/Gunship.Slave')).get_segments()[0].get_data());listing=(build/'release/Gunship.lst').read_text(encoding='latin1')
@lru_cache(None)
def sym(n):return int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
def addr(n):return base+sym(n)
c=CPU();c.put(base,blob);arena=0x180000;table=0x170000;out=0x160000;native=h[0]+0xa99e;ctx=h[6]+0x38f6
c.put(addr('timing_runtime_arena'),struct.pack('>I',arena))
def rt(n):return arena+sym('RT_'+n)
def call(entry,rs={},end=0x90000):
 c.rw(17,0x2000)
 for r,v in rs.items():c.rw(r,v)
 c.rw(8,0x8f000);c.call(entry,end=end);assert c.rr(18)==end
 return c.rr(9)
cases=0;nonempty=0;projections=set()
for height in (64,512):
 for heading in range(0,256,8):
  c.close();c=CPU();c.put(base,blob);c.put(addr('timing_runtime_arena'),struct.pack('>I',arena))
  c.put(0x200000,mem);c.put(table,struct.pack('>9I',*h));assert call(addr('timing_runtime_prepare'),{1:arena,2:table,9:50})==0
  c.put(h[0]+0x63f8,bytes.fromhex('4e75'))
  for off in (0x63b0,0x63c4,0x63ce):c.put(h[0]+off,bytes.fromhex('4e714e714e71'))
  xy=(0x7fff,0x7fff);c.put(p,struct.pack('>HH',*xy));c.put(p+28,struct.pack('>H',height));c.put(p+53,bytes([heading,0,0]));c.put(p+26,b'\0')
  special=struct.pack('>3H',xy[0]+128,xy[1]+128,height+24)
  for off,v in zip([0x3be3,0x3c5d,0x3c63,0x3cdd,0x3ddd,0x3d5d],special):c.put(h[6]+off,bytes([v]))
  coords=[xy[0]+(i-2)*128 for i in range(6)]+[xy[1]+(i-2)*128 for i in range(6)]+[height+32]*6
  c.put(h[0]+0xc6a0,struct.pack('>18H',*coords));c.put(h[0]+0xba08,b'\0\x3f')
  call(h[0]+0x57e2,{6:p},h[0]+0x5830);call(addr('scene_state_build'),{1:h[4],2:h[0]+0xc6a0,3:h[6],4:ctx+14});c.put(ctx+0x5e,struct.pack('>I',h[6]+0x15dc))
  seed=bytearray(c.get(native,168));seed[2:4]=bytes(2)
  for i,o in enumerate((0,18,36,54,72)):struct.pack_into('>H',seed,8+2*i,o)
  before_projection=c.get(0x97ee00,0x21200)
  c.put(native,seed);call(h[0]+0x5c2e,{6:ctx},h[0]+0x5c5c);call(h[0]+0x60a8,{6:ctx});candidates=c.get(native,168)
  count=int.from_bytes(candidates[2:4],'big')
  if count:
   seed[0]=2;seed[4:6]=candidates[0x6c:0x6e];seed[6:8]=candidates[0x76:0x78]
  else:seed[0]=255
  c.put(0x97ee00,before_projection);c.put(native,seed);call(h[0]+0x5c2e,{6:ctx},h[0]+0x5c5c);call(h[0]+0x60a8,{6:ctx});reference=c.get(native,168)
  match=[]
  for i in range(int.from_bytes(reference[2:4],'big')):
   obj=reference[0x6c+2*i:0x6e+2*i];sub=reference[0x76+2*i:0x78+2*i]
   if obj==seed[4:6] and (obj[0]&128 or sub==seed[6:8]):match.append(i)
  c.put(0x97ee00,before_projection);c.put(native,seed);assert call(addr('target_view_reset'),{1:rt('VIEW'),2:native})==0
  c.put(rt('CAPTURE_OWNER'),b'\0\1');c.put(rt('TARGET_PHASE'),b'\0\2');c.put(rt('VIEW_PHASE'),b'\0\1')
  # Native reference already compiled collector call sites. Recreate the CPU
  # before changing them so no old translated block can bypass the hook.
  saved_native=c.get(0x97ee00,0x21200);saved_arena=c.get(arena,sym('RT_ARENA_SIZE'))
  c.close();c=CPU();c.put(base,blob);c.put(0x200000,mem);c.put(0x97ee00,saved_native);c.put(arena,saved_arena);c.put(addr('timing_runtime_arena'),struct.pack('>I',arena))
  for off in (0x6356,0x63d4):c.put(h[0]+off,bytes.fromhex('4eb9')+struct.pack('>I',addr('timing_render_collect')))
  call(h[0]+0x5c2e,{6:ctx},h[0]+0x5c5c);call(h[0]+0x60a8,{6:ctx})
  assert c.get(native,168)==seed,(height,heading,[(i,a,b) for i,(a,b) in enumerate(zip(seed,c.get(native,168))) if a!=b],c.get(rt('VIEW_PHASE'),2).hex(),c.get(rt('CAPTURE_OWNER'),2).hex())
  found=call(addr('target_view_build'),{1:rt('VIEW'),2:out});assert found==bool(match),(height,heading,match,found)
  if found:
   i=match[-1];offset=int.from_bytes(reference[8+2*i:10+2*i],'big');got=c.get(out,168)
   assert got[18:36]==reference[18+offset:36+offset]
   for dst,src,n in ((0x80,0x80+2*i,2),(0x8a,0x8a+2*i,2),(0x94,0x94+4*i,4)):assert got[dst:dst+n]==reference[src:src+n]
   projections.add(got[0x80:0x82]+got[0x8a:0x8c]);nonempty+=1
  cases+=1
assert nonempty and len(projections)>1
print(json.dumps(dict(status='passed',native_scene_views=cases,nonempty=nonempty,distinct_projections=len(projections),world_target_unchanged=True,scope='native geometry; rasterization omitted')));c.close()
