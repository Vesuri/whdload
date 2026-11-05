"""Native tick/cooldown/engine prefix against extracted world opening."""
import json,random
from unicorn_b import *
from layout import locate
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks']
c=CPU();c.put(0x200000,mem)
c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/world-start.hunk')).get_segments()[0].get_data()))
listing=(root/'tmp/c/world-start.lst').read_text()
def sym(n):return base+int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
P=0x300000;CLONE=0x310000;BAD=0x320000;native=h[6]+0x3b88;lamps=h[6]+0x1581
rng=random.Random(0x5640);calls=0
# Keep native inventory/cooldown indicator dispatch; stub only its final UI call.
c.put(h[0]+0xaf36,bytes.fromhex('4e75'))
trace=[]
CODE=C.CFUNCTYPE(None,C.c_void_p,C.c_uint64,C.c_uint32,C.c_void_p)
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
@CODE
def indicator(handle,a,n,user):trace.append((c.rr(9)&65535,c.rr(10)&255))
hook=C.c_size_t();entry=h[0]+0xaf36
ok(u.uc_hook_add(c.h,C.byref(hook),1<<2,indicator,None,entry,entry))
def call(name,args):
 global calls
 regs={r:rng.randrange(0x1000000) for r in range(1,17) if r not in [8,9]};regs.update(args)
 for r,v in regs.items():c.rw(r,v)
 c.rw(8,0x8f000);c.call(sym(name));calls+=1
 assert c.rr(18)==0x90000 and c.rr(8)==0x8f004
 assert all(c.rr(r)==v for r,v in regs.items() if r!=9),name
 return c.rr(9)
assert call('world_start_prepare',{1:h[0],2:CLONE,3:h[6],4:P})==0
c.put(h[0]+0xc756,bytes(1))
cases=0
for tick in [0,15,16,65535]:
 for cooldown in [0,1,2,36,255]:
  for flags in [0,4,8,12,16,28,255]:
   for reserve in [0,1,256,65535]:
    b=bytearray(rng.randbytes(86));struct.pack_into('>H',b,12,tick)
    struct.pack_into('>HH',b,4,reserve,0);b[66]=flags;b[68]=cooldown;b[69]=1 if cooldown&1 else 0;b[74]=cooldown
    # Include zero-altitude crash initialization paths with both clear and set status.
    if cases%3==0:b[24]=0;b[28:30]=bytes(2);b[82]=0
    original_lamps=bytes([123,45,67]);c.put(native,b);c.put(lamps,original_lamps)
    trace.clear();c.rw(6,native);c.rw(8,0x8f000);c.call(h[0]+0x5640,end=h[0]+0x56d8)
    expected=c.get(native,86),c.get(lamps,3),list(trace)
    trace.clear()
    c.put(P,b);c.put(lamps,original_lamps)
    assert call('world_start_step',{1:P,2:CLONE})==0
    assert (c.get(P,86),c.get(lamps,3),list(trace))==expected,(tick,cooldown,flags,reserve)
    assert int.from_bytes(c.get(P+12,2),'big')==(tick+1)&65535
    cases+=1
before=c.get(P,86),c.get(lamps,3)
assert call('world_start_step',{1:P+2,2:CLONE})==0xffffffff
assert before==(c.get(P,86),c.get(lamps,3))
# Signature failures must leave clone storage untouched.
original=c.get(h[0]+0x5640,152)
for off in [0,0x36,0x38,0x3c,0x3e,0x6e,0x70,0x74,0x76,0x8c,0x8e,0x92,0x94]:
 corrupt=bytearray(original);corrupt[off]^=1;c.put(h[0]+0x5640,corrupt);c.put(BAD,b'\xa5'*154)
 assert call('world_start_prepare',{1:h[0],2:BAD,3:h[6],4:P})==0xffffffff,off
 assert c.get(BAD,154)==b'\xa5'*154
c.put(h[0]+0x5640,original)
print(json.dumps(dict(status='passed',native_cases=cases,signature_rejections=13,binding_rejection=1,calls=calls)))
c.close()
# Real pending missile results: native bridge versus extracted opening.
rows=[]
seed=CPU();seed.put(0x200000,mem);player=seed.get(native,0x2d6);alive=int.from_bytes(seed.get(h[6]+0x45e2,4),'big');flags=seed.get(alive,256)
targets=[i for i in range(6,128) if player[0x256+i] and flags[player[0x156+i]]&(1<<(player[0x1d6+i]&7))];seed.close()
for idx in targets:
 results=[]
 for extracted in (False,True):
  c=CPU();c.put(0x200000,mem);c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/world-start.hunk')).get_segments()[0].get_data()))
  for off in (0xaf36,0xa150,0xb4e4,0xb57c,0xb0a6,0xb2e0,0x7fbe,0x7fce,0xb2e6):c.put(h[0]+off,b'\x4e\x75')
  c.put(h[0]+0xc756,bytes([idx]));c.rw(6,native);c.rw(8,0x8f000)
  if extracted:
   assert call('world_start_prepare',{1:h[0],2:CLONE,3:h[6],4:native})==0
   assert call('world_start_step',{1:native,2:CLONE})==0
  else:
   c.call(h[0]+0x5640,h[0]+0x56d8);c.rw(8,0x8f000);c.call(h[0]+0x5874,h[0]+0x5884)
  result=c.get(alive,256),c.get(native,0x2d6)
  assert not result[0][player[0x156+idx]]&(1<<(player[0x1d6+idx]&7)),idx
  results.append(result);c.close()
 assert results[0]==results[1],idx
 rows.append(idx)
print(dict(pending_missile_kills=len(rows),native_target_and_alive_state_equal=True))
