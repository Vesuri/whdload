"""Native weapon arithmetic with private fire/timestamps; target/UI stubs explicit."""
import json,random
from unicorn_b import *
from layout import locate
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks'];p=h[6]+0x3b88
c=CPU();c.put(0x200000,mem);c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/world-weapons.hunk')).get_segments()[0].get_data()))
listing=(root/'tmp/c/world-weapons.lst').read_text()
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
low=0x97ee00;length=0x21200;initial=c.get(low,length)
CODE=C.CFUNCTYPE(None,C.c_void_p,C.c_uint64,C.c_uint32,C.c_void_p)
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
trace=[];checking=False;badwrites=[];hardware=[]
@CODE
def event(handle,a,n,user):trace.append(0x7a5c if a==rc else a-h[0])
hooks=[]
for a in [rc]+[h[0]+off for off in [0x7a5c,0x7c1c,0xbea8,0xbade,0xbed4,0xa150,0xbf34,0xc3e0,0xc3c8,0xc444,0xc45e]]:
 hook=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hook),1<<2,event,None,a,a));hooks.append(hook)
MEM=C.CFUNCTYPE(None,C.c_void_p,C.c_int,C.c_uint64,C.c_int,C.c_int64,C.c_void_p)
@MEM
def write(handle,kind,a,n,value,user):
 if checking and 0xdff040<=a and a+n<=0xdff076:
  hardware.append((a,n,value));return
 if checking and not(low<=a and a+n<=low+length or 0x8e000<=a and a+n<=0x8f004 or fire<=a and a+n<=fire+2):badwrites.append((hex(a),n))
hook=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hook),1<<11,write,None,1,0));hooks.append(hook)

runs=[]
for mode in [0,1]:
 for weapon in [0,1,2,3]:
  stamps=[rng.randbytes(8) for _ in range(64)];lives=[rng.randbytes(8) for _ in range(64)]
  lanes=[]
  for patched in [False,True]:
   c.put(low,initial);c.put(h[6]+0x45cc,bytes([mode]));c.put(h[4]+0x3cc,struct.pack('>I',0x12345678))
   c.put(h[4]+0x1c5,b'\0\0');c.put(h[0]+0x9c42,b'\0')
   c.put(p+0x41,bytes([weapon]));c.put(p+0x48,b'\0');c.put(p+0x36,b'\0');c.put(p+0x35,b'\x20');c.put(p+0x1c,struct.pack('>H',1024));c.put(p+0x11,b'\x02');c.put(p+0x0e,b'\0\0')
   c.put(h[6]+0x1558,bytes([99]*6));c.put(h[0]+0xba08,bytes(4));c.put(h[0]+0xba0c,b'\xff\xff\xff\xff')
   c.put(p+0x256+5,b'\x01')
   observations=[];active=0;launches=0;hits=0;moving=0;ground=0;expired=0;released=False
   for tick in range(64):
    # Exercise the real guided-projectile release fragment at its state-5 gate.
    # Full control-state evolution is deliberately outside this fixture.
    if tick==4 and weapon in [1,3]:
     c.put(h[0]+0xa44d,b'\x05');c.rw(8,0x8f000);c.call(h[0]+0xa22a,end=h[0]+0xa248)
     released=True
    flags=bytes([1 if tick%8==0 else 0,0]);c.put(record+32,stamps[tick]);c.put(h[2]+0x14,lives[tick] if patched else stamps[tick])
    c.put(p+0x0c,struct.pack('>H',32+tick));c.put(h[6]+0x4292,b'\x77\x88' if patched else flags);c.put(fire,flags)
    trace.clear();hardware.clear();badwrites.clear();checking=True
    pose=c.get(h[0]+0xc6a0,36)
    if patched:assert call('world_weapons_step',{1:p,2:clone})==0
    else:c.rw(6,p);c.rw(8,0x8f000);c.call(h[0]+0x979c)
    checking=False
    assert c.rr(18)==0x90000 and not badwrites,(mode,weapon,tick,badwrites[:8])
    ground+=trace.count(0xc444);expired+=trace.count(0xc45e);active+=trace.count(0xbf34);launches+=trace.count(0xbade);hits+=trace.count(0xc3e0)
    if 0xbf34 in trace and pose!=c.get(h[0]+0xc6a0,36):moving+=1
    state=bytearray(c.get(low,length))
    for a,size in [(h[2]+0x14,8),(h[6]+0x4292,2)]:state[a-low:a-low+size]=bytes(size)
    observations.append((bytes(state),c.get(fire if patched else h[6]+0x4292,2),list(trace),list(hardware)))
    if patched:assert c.get(h[6]+0x4292,2)==b'\x77\x88'
   lanes.append(observations)
  for tick,(left,right) in enumerate(zip(*lanes)):
   assert left==right,(mode,weapon,tick,[hex(low+i) for i,(a,b) in enumerate(zip(left[0],right[0])) if a!=b][:15],left[2],right[2])
  runs.append(dict(mode=mode,weapon=weapon,ticks=64,active_visits=active,launch_calls=launches,impact_calls=hits,moving_ticks=moving,ground_contacts=ground,expiry_visits=expired,guided_release=released))
assert sum(x['active_visits'] for x in runs)>0 and sum(x['moving_ticks'] for x in runs)>0
report=dict(status='passed',runs=runs,calls=calls,scope='successive native weapon/actor ticks plus explicit native guided-release fragment; target/UI stubs, no full control state machine/damage/scripts/VBL effect timers')
(root/'tmp/c/world-actor-sequence-tests.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report));c.close()
