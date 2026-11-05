"""Native weapon arithmetic with private fire/timestamps; target/UI stubs explicit."""
import json,random
from unicorn_b import *
from layout import locate
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks'];p=h[6]+0x3b88
c=CPU();c.put(0x200000,mem);c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/scheduled-guidance.hunk')).get_segments()[0].get_data()))
listing=(root/'tmp/c/scheduled-guidance.lst').read_text()
def sym(n):return base+int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
clone=0x330000;rc=0x340000;record=0x350000;fire=0x360000;rng=random.Random(0x979c);calls=0
# Target fixture selects slot 5. Actor updates, allocation, launch, recoil and
# resource accounting remain native; notification/UI/audio endpoints are stubs.
c.put(h[0]+0xc654,bytes.fromhex('70054e75'))
for off in [0xa150,0xaf36,0xb4e4,0xb57c]:c.put(h[0]+off,bytes.fromhex('4e75'))
def call(name,args):
 global calls
 regs={r:rng.randrange(0x1000000) for r in range(1,17) if r not in [8,9]};regs.update(args)
 for r,v in regs.items():c.rw(r,v)
 c.rw(8,0x8f000);c.call(sym(name));calls+=1
 assert c.rr(18)==0x90000 and c.rr(8)==0x8f004,(name,hex(c.rr(18)))
 assert all(c.rr(r)==v for r,v in regs.items() if r!=9),name
 return c.rr(9)
assert call('world_rng_prepare',{1:h[0]+0x7a5c,2:rc,3:record,4:h[2]})==0
assert call('world_weapons_prepare',{1:h[0],2:clone,3:rc,4:fire,5:h[6]})==0

TS=0x400000;TC=0x401000;TH=0x402000;CQ=0x404000;S=0x405000;SG=0x406000;FG=0x407000;PENDING=0x408000;START=0x409000
assert call('field_guidance_prepare',{1:h[0],2:FG,3:h[4],4:PENDING})==0
assert call('world_start_prepare',{1:h[0],2:START,3:h[6],4:p})==0
low=0x97ee00;length=0x21200;initial=c.get(low,length)
CODE=C.CFUNCTYPE(None,C.c_void_p,C.c_uint64,C.c_uint32,C.c_void_p)
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
trace=[]
@CODE
def event(handle,a,n,user):trace.append(a-h[0])
hooks=[]
for off in [0xbade,0xbf34,0xc3e0]:
 hook=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hook),1<<2,event,None,h[0]+off,h[0]+off));hooks.append(hook)
runs=[]
for rate in [50,60]:
 for weapon in [1,3]:
  baseline=None
  for batch in [1,3,10,25]:
   c.put(low,initial);c.put(h[4]+0x1c5,b'\0\0');c.put(h[0]+0x9c42,b'\0')
   c.put(p+0x41,bytes([weapon]));c.put(p+0x48,b'\0');c.put(p+0x36,b'\0');c.put(p+0x1c,struct.pack('>H',1024));c.put(p+0x11,b'\x02');c.put(p+0x0e,b'\0\0');c.put(p+12,b'\0\0')
   c.put(p+4,struct.pack('>HH',30000,30000));c.put(h[6]+0x1558,bytes([99]*6));c.put(h[0]+0xba08,bytes(4));c.put(h[0]+0xba0c,b'\xff\xff\xff\xff');c.put(p+0x256+5,b'\x01')
   c.put(h[0]+0xa44d,b'\xff\0\0');c.put(h[0]+0xa436,b'\0');c.put(PENDING,b'\0')
   assert call('clock_init',{1:TC,9:0,10:rate})==0
   assert call('history_init',{1:TH,9:0})==0
   assert call('commands_init',{1:CQ,9:0})==0
   assert call('scheduler_init',{1:TS,2:TC,3:TH,4:CQ})==0
   c.put(SG,struct.pack('>II',TS,FG)+bytes(8))
   fields=[];worlds=[];releases=[];launches=[];active=0
   for first in range(1,241,batch):
    for f in range(first,min(first+batch,241)):
     b=bytearray(40);struct.pack_into('>I',b,0,f);struct.pack_into('>H',b,30,1 if f in [3,83,163] else 0);struct.pack_into('>II',b,32,10+f//rate,f*17003%1000000)
     c.put(S,b);assert call('history_publish',{1:TH,2:S})==1
    assert call('scheduler_begin',{1:TS,9:128,10:8})==0
    while True:
     got=call('scheduler_next',{1:TS,2:record})
     if not got:break
     assert got==1
     f=int.from_bytes(c.get(record,4),'big')
     c.put(h[0]+0xc757,bytes([(f+batch)&255]))
     c.put(h[2]+0x14,struct.pack('>II',batch,f+batch))
     old=int.from_bytes(c.get(h[0]+0xba0c,2),'big')
     assert call('scheduled_guidance_step',{1:SG}) in [0,1]
     assert c.get(SG+14,2)==b'\0\1'
     after=c.get(h[0]+0xba0c,2)
     if int.from_bytes(after,'big')!=old:releases.append(f)
     before=c.get(low,length),c.get(PENDING,1)
     assert call('scheduled_guidance_step',{1:SG})==0xfffffffd
     assert before==(c.get(low,length),c.get(PENDING,1))
     fields.append((after,c.get(h[0]+0xa44d,3),c.get(PENDING,1)))
     # Fixed-player fixture: motion is deliberately absent in this composition.
     if call('scheduler_player_done',{1:TS})==1:
      assert call('world_fire_prepare',{1:TS,2:fire})==0
      assert call('world_start_step',{1:p,2:START})==0
      trace.clear();assert call('world_weapons_step',{1:p,2:clone})==0
      if 0xbade in trace:launches.append(f)
      active+=trace.count(0xbf34)
      state=bytearray(c.get(low,length))
      for a,size in [(h[2]+0x14,8),(h[0]+0xc757,1)]:state[a-low:a-low+size]=bytes(size)
      worlds.append((f,bytes(state),list(trace)))
      assert call('scheduler_world_done',{1:TS})==0
   result=(fields,worlds,releases,launches)
   if baseline is None:baseline=result
   else:assert result==baseline,(rate,weapon,batch)
   assert launches and releases and active and releases[0]==launches[0]+7,(launches,releases,active)
   runs.append(dict(rate=rate,weapon=weapon,batch=batch,fields=240,worlds=len(worlds),launches=launches,releases=releases,active_visits=active))
print(json.dumps(dict(status='passed',runs=runs,calls=calls)))
c.close()
