"""Show native effect slot reuse depends on render cadence, without FS-UAE."""
from unicorn_b import *
from layout import locate
import json
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks']
c=CPU();c.put(0x200000,mem)

def run(period):
 c.put(0x200000,mem)
 c.put(h[0]+0xba08,struct.pack('>H',1))
 c.put(h[0]+0xc6d0,bytes([64])+bytes(5)+bytes([9])+bytes(5)+bytes(6))
 c.put(h[0]+0xc724,bytes([12])*6)
 # Native release branch skips optional score bookkeeping for this fixture.
 c.put(h[0]+0xc6d0+0x4e,bytes([2]))
 frames=[];freed=None;phase=0;tick=0
 for field in range(1,101):
  # Execute actual six-byte VBL decrement block, ending before OS work.
  ok(u.uc_emu_start(c.h,h[0]+0x4c3e,h[0]+0x4c64,0,1000))
  if field%period==0:
   c.rw(8,0x8f000);c.call(h[0]+0xbe5a)
  phase+=3
  if phase>=50:
   phase-=50;tick+=1
   # The native world's active-effect branch goes straight to this lifetime
   # decrement. Stop before unrelated score/aggregate calculations.
   c.rw(2,h[0]+0xc6d0);c.rw(14,0)
   ok(u.uc_emu_start(c.h,h[0]+0xc456,h[0]+0xc4d2,0,1000))
   if c.get(h[0]+0xba08,2)==bytes(2):
    freed=dict(field=field,world_tick=tick);break
  frames.append(c.get(h[0]+0xc6dc,1)[0])
 assert freed
 return dict(render_every_fields=period,released=freed,animation=frames)
fast=run(1);slow=run(10)
assert fast['released']!=slow['released']
print(json.dumps(dict(status='confirmed',fast=fast,slow=slow)))
c.close()
