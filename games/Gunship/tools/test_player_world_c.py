"""Composed native post-motion world sequence; modal interpreter and UI excluded."""
import json,random,sys
from unicorn_b import *
from layout import locate
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks'];p=h[6]+0x3b88
c=CPU();c.put(0x200000,mem);c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/player-world.hunk')).get_segments()[0].get_data()))
listing=(root/'tmp/c/player-world.lst').read_text()
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


hit=0x370000
for off in [0x7fa4,0xb0a6]:c.put(h[0]+off,bytes.fromhex('70004e75') if off==0x7fa4 else bytes.fromhex('4e75'))
assert call('world_rng_prepare',{1:h[0]+0x7a5c,2:rc,3:record,4:h[2]})==0
assert call('world_hit_prepare',{1:h[0],2:hit,3:rc})==0
assert call('world_script_prepare',{1:h[0],2:clone,3:rc,4:hit,5:h[6]})==0
weapons=0x380000;damage=0x390000;effects=0x3a0000;heading=0x3b0000
reserves=0x3c0000;periodic=0x3d0000;cleanup=0x3e0000;ctx=0x3f0000
assert call('world_effect_prepare',{1:h[0],2:effects,3:rc,4:heading})==0
assert call('world_weapons_prepare',{1:h[0],2:weapons,3:rc,4:fire,5:h[6]})==0
assert call('world_damage_prepare',{1:h[0],2:damage,3:rc,4:effects,5:hit,6:h[6]})==0
assert call('world_reserves_prepare',{1:h[0],2:reserves})==0
assert call('world_periodic_prepare',{1:h[0],2:periodic,3:rc,4:h[6]})==0
assert call('world_cleanup_prepare',{1:h[0],2:cleanup,3:h[4]})==0
c.put(ctx,struct.pack('>7IH',p,weapons,damage,clone,reserves,periodic,cleanup,0))
c.put(h[0]+0xb2e0,bytes.fromhex('4e75'))
stages=0x400000;shadow=0x410000;packet=0x420000;candidate=0x430000
opening=0x440000;ground=0x450000;groundevent=0x460000;clamp=0x470000
assert call('motion_stages_prepare',{1:h[0],2:stages})==0
assert call('world_start_prepare',{1:h[0],2:opening,3:h[6],4:p})==0
assert call('ground_deferred_prepare',{1:h[0],2:ground,3:h[6],4:groundevent})==0
c.put(clamp,c.get(h[0]+0x5756,0x24)+bytes.fromhex('4e75'))
low=0x97ee00;length=0x21200;initial=c.get(low,length)
CODE=C.CFUNCTYPE(None,C.c_void_p,C.c_uint64,C.c_uint32,C.c_void_p)
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
u.uc_emu_stop.argtypes=[C.c_void_p]
trace=[];blocked=False
@CODE
def event(handle,a,n,user):
 global blocked
 if a==h[0]+0x5a0c:ok(u.uc_emu_stop(handle));return
 if a==h[0]+0x8050:
  state=c.get(p+83,1)[0];delay=c.get(p+84,1)[0]
  if 0<state<128 and delay==1:blocked=True;ok(u.uc_emu_stop(handle))
 elif a in [rc,h[0]+0x7a5c]:trace.append(('rng',256))
 elif a in [rc+14,h[0]+0x7a6a]:trace.append(('bound',c.rr(10)&65535))
 else:trace.append((a-h[0],c.rr(9)&255,None if a==h[0]+0xa150 else c.rr(10)&255))
hooks=[]
for a in [rc,rc+14]+[h[0]+off for off in [0x5a0c,0x8050,0x7a5c,0x7a6a,0xa150,0xaf36,0xb0a6]]:
 hook=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hook),1<<2,event,None,a,a));hooks.append(hook)
MEM=C.CFUNCTYPE(None,C.c_void_p,C.c_int,C.c_uint64,C.c_int,C.c_int64,C.c_void_p)
checking=False;badwrites=[]
@MEM
def write(handle,kind,a,n,value,user):
 if checking and 0xdff040<=a and a+n<=0xdff078:trace.append(('hw',a,n,value))
 if checking and not(low<=a and a+n<=low+length or shadow<=a and a+n<=shadow+76 or packet<=a and a+n<=packet+10 or candidate<=a and a+n<=candidate+350 or groundevent<=a and a+n<=groundevent+4 or ctx<=a and a+n<=ctx+30 or fire<=a and a+n<=fire+2 or 0xdff040<=a and a+n<=0xdff078 or 0x8e000<=a and a+n<=0x8f004):badwrites.append((hex(a),n))
hook=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hook),1<<11,write,None,1,0));hooks.append(hook)

fixtures=json.loads((root/'tmp/c/player-motion-fixtures.json').read_text())
outcomes={0:0,2:0,3:0};resets=0;motiondraws=set()
sequential="--sequential" in sys.argv
carry=initial;terminal=False;starts=0
for n in range(512):
 restart=not sequential or n%16==0 or terminal
 starts+=restart
 stamp=rng.randbytes(8);live=rng.randbytes(8);seed=rng.randrange(2**32)
 b=bytearray.fromhex(fixtures[n%len(fixtures)]['input'])
 b[0:4]=struct.pack('>HH',0x7000,0x8000);b[83:85]=bytes(2)
 b[24]=0;b[17]=1+n%4;b[44]=0
 struct.pack_into('>H',b,12,[0,15,65535,127][n%4])
 struct.pack_into('>H',b,28,[0,1,4,1024,32767][n%5])
 # Vary damage, flight mode and speed so all three impulse gates occur.
 b[15]=n%4
 x,y,previous=[rng.randrange(-1,2) for _ in range(3)]
 if not restart:
  b=bytearray(c.get(p,86));previous=int.from_bytes(c.get(shadow+2,2),'big',signed=True)
  seed=int.from_bytes(c.get(h[4]+0x3cc,4),'big')
  carry=c.get(low,length)
 elif sequential:carry=initial
 fireval=bytes([int(n%7==0),int(n%11==0)])
 results=[]
 for patched in [False,True]:
  c.put(low,carry if sequential else initial);c.put(p,b);c.put(h[6]+0x45cc,bytes([(n//16)%2 if sequential else n%2]));c.put(h[4]+0x3cc,struct.pack('>I',seed));c.put(h[2]+0x14,live if patched else stamp)
  c.put(record+32,stamp);c.put(h[0]+0x5524,bytes([previous&255]))
  c.put(h[6]+0x4294,bytes([x&255,y&255]));c.put(h[6]+0x4292,b'\x77\x88' if patched else fireval);c.put(fire,fireval)
  if restart:c.put(h[0]+0xba08,bytes(2));c.put(h[0]+0xba0a,bytes(2));c.put(h[0]+0xba0c,b'\xff\xff')
  c.put(h[6]+0x157b,b'\x05');c.put(h[4]+0x440,bytes(2))
  c.put(heading,c.get(h[6]+0x390a,2));c.put(ctx+28,bytes(2));c.put(groundevent,bytes(4))
  c.put(packet,struct.pack('>hhhhh',x,y,0,0,0))
  if restart:assert call('player_step_init',{1:shadow,9:3,10:previous&0xffffffff})==0
  trace.clear();badwrites.clear();blocked=False;checking=True
  if patched:
   assert call('world_start_step',{1:p,2:opening})==0
   assert call('world_motion_impulses',{1:p,2:packet,3:rc})==0
   motiondraws.add(sum(e[0]=='rng' for e in trace))
   tick=int.from_bytes(c.get(p+12,2),'big')
   args={1:shadow,2:p,3:stages,4:h[0]+0x7a44,5:packet,6:candidate,9:tick}
   assert call('player_boundary_prepare',args)==0
   was=int.from_bytes(c.get(candidate+72,2),'big')
   applied=call('ground_deferred_step',{1:candidate,2:candidate+76,3:ground,4:groundevent,9:was});assert applied in [0,1];resets+=applied
   assert call('player_boundary_complete',args)==0
   assert call('ground_deferred_commit',{1:groundevent,2:h[0]+0xa150,3:h[6]+0x42f6}) in [0,1]
   got=call('world_body_step',{1:ctx})
   prev=c.get(shadow+2,2)[1:]
  else:
   c.rw(6,p);c.rw(8,0x8f000);c.call(h[0]+0x5640,end=h[0]+0x56d8)
   for entry in [clamp,h[0]+0x5376,h[0]+0x937c,h[0]+0x5894]:
    c.rw(6,p);c.rw(8,0x8f000);c.call(entry)
   expected=2 if blocked else (3 if c.rr(18)==0x90000 else 0)
   prev=bytes([y&255]) # next-sample history is owned by field state
  checking=False;assert not badwrites,(n,badwrites[:10])
  state=bytearray(c.get(low,length))
  for addr,size in [(h[2]+0x14,8),(h[6]+0x4292,2),(h[0]+0x5524,1)]:state[addr-low:addr-low+size]=bytes(size)
  results.append((bytes(state),list(trace),prev,c.get(fire,2) if patched else c.get(h[6]+0x4292,2)))
 assert got==expected and results[0]==results[1],(n,got,expected,[hex(low+i) for i,(a,b) in enumerate(zip(results[0][0],results[1][0])) if a!=b][:16],results[0][1:],results[1][1:])
 outcomes[got]+=1;terminal=got!=0
print(json.dumps(dict(sequential=sequential,starts=starts,cases=512,outcomes=outcomes,ground_resets=resets,motion_draws=sorted(motiondraws),calls=calls)))
