"""World target publication vs native prefix/selector; explicit pixel oracle."""
from unicorn_b import *
from layout import locate
from functools import lru_cache
import json
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();chip=(root/'tmp/prof/flight1-mem/chip.bin').read_bytes();h=locate(mem)['hunks'];p=h[6]+0x3b88
blob=bytes(BinFmt().load_image(str(build/'release/Gunship.Slave')).get_segments()[0].get_data());listing=(build/'release/Gunship.lst').read_text(encoding='latin1')
@lru_cache(None)
def sym(n):return int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
def addr(n):return base+sym(n)
c=CPU();arena=0x180000;table=0x170000;target=h[0]+0xa99e;size=sym('RT_ARENA_SIZE');native_lo=0x97ee00;native_len=0x21200
CODE=C.CFUNCTYPE(None,C.c_void_p,C.c_uint64,C.c_uint32,C.c_void_p)
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
queries=[];fallbacks=[]
@CODE
def fallback(handle,a,n,user):
 fallbacks.append(1);c.put(h[4]+0x1c5,b"\1")
fallback_hook=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(fallback_hook),1<<2,fallback,None,h[0]+0x46de,h[0]+0x46de))
@CODE
def pixel(handle,a,n,user):
 x,y=c.rr(9)&65535,c.rr(10)&65535;queries.append((x,y));c.rw(9,(x*3+y*7)&255)
hook=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hook),1<<2,pixel,None,h[0]+0x825e,h[0]+0x825e))
def call(entry,regs={},end=0x90000):
 c.rw(17,0x2000)
 for r,v in regs.items():c.rw(r,v)
 c.rw(8,0x8f000);c.call(entry,end=end)
 assert c.rr(18)==end,(hex(entry),hex(c.rr(18)))
 return c.rr(9)
def put(name,v,n=2):c.put(arena+sym(name),v.to_bytes(n,'big'))
def admission(field):
 put('RT_CAPTURE_OWNER',1)
 for owner,flag in [('RT_CLOCK','TC_ACTIVE'),('RT_HISTORY','TH_ACTIVE'),('RT_COMMANDS','CQ_ACTIVE')]:c.put(arena+sym(owner)+sym(flag),b'\0\1')
 c.put(arena+sym('RT_CONSUMER')+sym('TF_PHASE'),b'\0\3')
 c.put(arena+sym('RT_CONSUMER')+sym('TF_FIELD'),struct.pack('>I',field))
 c.put(arena+sym('RT_SCHEDULER')+sym('TS_STATE'),b'\0\2\0\1')
 c.put(arena+sym('RT_SCHEDULER')+sym('TS_FIELD'),struct.pack('>I',field))
 c.put(arena+sym('RT_RECORD')+sym('TR_FIELD'),struct.pack('>I',field))
cases=0;nonempty=0
for mode in (0,1):
 for heading in range(0,256,32):
  c.put(0,chip);c.put(base,blob);c.put(0x200000,mem);c.put(table,struct.pack('>9I',*h));c.put(0xdff000,bytes(512))
  assert call(addr('timing_runtime_prepare'),{1:arena,2:table,9:50})==0
  c.put(h[0]+0x825e,bytes.fromhex('4e75'));c.put(h[0]+0x46de,bytes.fromhex('4e75'))
  c.put(h[4]+0x1c5,bytes([cases%3]))
  c.put(p,struct.pack('>HH',0x7fff,0x7fff));c.put(p+28,struct.pack('>H',512));c.put(p+53,bytes([heading,0,0]));c.put(p+26,b'\0');c.put(p+22,bytes([mode]))
  special=struct.pack('>3H',0x807f,0x807f,536)
  for off,v in zip([0x3be3,0x3c5d,0x3c63,0x3cdd,0x3ddd,0x3d5d],special):c.put(h[6]+off,bytes([v]))
  coords=struct.pack('>18H',*[0x7fff+(i-2)*128 for i in range(6)],*[0x7fff+(i-2)*128 for i in range(6)],*[544]*6)
  c.put(h[0]+0xc6a0,coords);c.put(h[0]+0xba08,b'\0\x3f')
  initial=bytearray(c.get(target,168));initial[2:4]=bytes(2)
  for i,o in enumerate((0,18,36,54,72)):struct.pack_into('>H',initial,8+2*i,o)
  c.put(target,initial);before=c.get(native_lo,native_len);chipbefore=c.get(0,0x80000)
  camera=arena+sym('RT_CAMERA')
  call(addr('native_camera_build'),{1:p,3:camera})
  call(addr('scene_state_build'),{1:camera,2:h[0]+0xc6a0,3:h[6],4:h[6]+0x3904})
  call(h[0]+0x5c04,end=h[0]+0x5c78)
  candidates=c.get(target,168);nonempty+=candidates[2:4]!=bytes(2)
  call(h[0]+0xa58c);want=c.get(target,168)
  c.put(native_lo,before);c.put(0,chipbefore);admission(100+cases)
  regs={r:0x1200+r for r in list(range(1,8))+list(range(10,17))};regs[1]=arena
  fallbacks.clear()
  assert call(addr('timing_runtime_target'),regs)==0
  assert len(fallbacks)==int(cases%3==0 and bool(want[0]&128)),(cases,want[0],fallbacks)
  assert c.get(h[4]+0x1c5,1)==bytes([1 if fallbacks else cases%3])
  assert all(c.rr(r)==v for r,v in regs.items())
  assert c.get(target,168)==want,(mode,heading,c.get(target,168).hex(),want.hex())
  assert c.get(arena+sym('RT_TARGET_PHASE'),6)==struct.pack('>HI',2,100+cases)
  native=c.get(native_lo,native_len);private=c.get(arena,size)
  assert call(addr('timing_runtime_target'),{1:arena})==0xfffffffd
  assert c.get(native_lo,native_len)==native and c.get(arena,size)==private
  cases+=1
assert nonempty
# Fresh field with corrupt descriptor must reject before publication or stamping.
admission(999);c.put(target+8,b'\0\1');native=c.get(native_lo,native_len);private=c.get(arena,size)
assert call(addr('timing_runtime_target'),{1:arena})==0xfffffffd
assert c.get(native_lo,native_len)==native and c.get(arena,size)==private
print(json.dumps(dict(status='passed',native_selection_cases=cases,nonempty_views=nonempty,replay_rejections=cases,scope='explicit pixel oracle; no DMA claim')));c.close()
