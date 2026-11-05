"""Native allocator/release/morph evidence for prediction identity barriers."""
from unicorn_b import *
from layout import locate
import json,random
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks'];c=CPU();c.put(0x200000,mem)
mask=h[0]+0xba08;secondary=mask+2;actors=h[0]+0xc6d0;rng=random.Random(0xbea8)
def call(off,rs={},end=0x90000):
 c.rw(17,0x2000)
 for r,v in rs.items():c.rw(r,v)
 c.rw(8,0x8f000);c.call(h[0]+off,end=end);assert c.rr(18)==end
 return c.rr(9)
cases=0
for occupied in range(64):
 for initial_secondary in (0,0xffff):
  c.put(mask,struct.pack('>HH',occupied,initial_secondary));c.put(0x90000,bytes.fromhex('40f900730000'))
  got=call(0xbea8,end=0x90006)
  free=[i for i in range(6) if not occupied&(1<<i)];slot=max(free) if free else -1
  assert got==slot+1,(occupied,got,slot)
  want=occupied|(1<<slot) if free else occupied
  assert int.from_bytes(c.get(mask,2),'big')==want
  # Slot zero bypasses the secondary-mask update; full failure stores no
  # changed low-word bit despite the register BSET using index -1.
  want_secondary=initial_secondary|(1<<slot) if slot>0 else initial_secondary
  assert int.from_bytes(c.get(secondary,2),'big')==want_secondary
  flags=int.from_bytes(c.get(0x730000,2),'big')&31
  assert flags==(0 if free else 0x15),(occupied,flags)
  cases+=1
# Complete native release fragment followed by reuse: both snapshots can have
# the same allocation word even though a new lifetime has begun.
c.put(mask,bytes(4));first=call(0xbea8);before=c.get(mask,2)
call(0xc45e,{14:first-1},end=h[0]+0xc46c)
assert c.get(mask,2)==bytes(2)
second=call(0xbea8)
assert first==second==6 and c.get(mask,2)==before
# Native impact changes representation in place without allocation changes.
morphs=0
for slot in range(6):
 for typ in range(0,256,2):
  c.put(mask,struct.pack('>H',1<<slot));c.put(actors,bytes(90));c.put(actors+6+slot,bytes([typ]));before=c.get(mask,2)
  call(0xc3e8,{2:actors+slot},end=h[0]+0xc3fa)
  assert c.get(mask,2)==before and c.get(actors+6+slot,1)==bytes([typ|1])
  assert c.get(actors+slot,1)==b'\x40' and c.get(actors+84+slot,1)==b'\x0c'
  morphs+=1
print(json.dumps(dict(status='passed',allocator_cases=cases,same_mask_release_reuse=True,in_place_impact_cases=morphs,full_allocator_ccr=0x15)));c.close()
