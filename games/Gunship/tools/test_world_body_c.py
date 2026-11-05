"""Composed native post-motion world sequence; modal interpreter and UI excluded."""
import json,random
from unicorn_b import *
from layout import locate
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks'];p=h[6]+0x3b88
c=CPU();c.put(0x200000,mem);c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/world-body.hunk')).get_segments()[0].get_data()))
listing=(root/'tmp/c/world-body.lst').read_text()
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
 if checking and not(low<=a and a+n<=low+length or ctx<=a and a+n<=ctx+30 or fire<=a and a+n<=fire+2 or 0xdff040<=a and a+n<=0xdff078 or 0x8e000<=a and a+n<=0x8f004):badwrites.append((hex(a),n))
hook=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hook),1<<11,write,None,1,0));hooks.append(hook)
outcomes={0:0,2:0,3:0};drawcounts=set();resumes=0
chained=0
for n in range(512):
 stamp=rng.randbytes(8);live=rng.randbytes(8);c.put(record+32,stamp);seed=rng.randrange(2**32);results=[]
 resume=n>=384
 for patched in [False,True]:
  c.put(low,initial);c.put(h[6]+0x45cc,bytes([n%2]));c.put(h[4]+0x3cc,struct.pack('>I',seed));c.put(h[2]+0x14,live if patched else stamp)
  c.put(p,struct.pack('>HH',0x7000,0x8000));c.put(p+12,struct.pack('>H',(n//4)%32));c.put(p+17,bytes([1+n%4]));c.put(p+28,struct.pack('>H',1024));c.put(p+44,b'\0')
  c.put(p+83,bytes([[0,1,2,3,4,5,127,128,255][n//2%9],[0,1,2,15,255][n//18%5]]))
  c.put(h[4]+0x440,b'\0\1');c.put(h[1]+0x1d8,b'\x70');c.put(h[1]+0x1dc,b'\x80');c.put(h[6]+0x395c,bytes([3 if n//90%2 else 0]));c.put(h[6]+0x157b,b'\x05')
  for off,val in [(0x56,0x70),(0xd0,0x80),(0xd6,0x80),(0x150,0),(0x156,(n*11)&255),(0x256,3)]:c.put(p+off+5,bytes([val]))
  c.put(ctx+28,struct.pack('>H',1 if resume else 0))
  c.put(p+24,bytes([1 if n%64==0 else 0]))
  c.put(h[0]+0xba08,bytes(2));c.put(h[0]+0xba0a,bytes(2));c.put(h[0]+0xba0c,b'\xff\xff')
  fireval=bytes([1 if n%7==0 else 0,1 if n%11==0 else 0]);c.put(fire,fireval)
  c.put(h[6]+0x4292,b'\x77\x88' if patched else fireval)
  c.put(heading,c.get(h[6]+0x390a,2))
  trace.clear();badwrites.clear();blocked=False;checking=True
  if patched:got=call('world_body_resume' if resume else 'world_body_step',{1:ctx})
  else:
   c.rw(6,p);c.rw(8,0x8f000);
   if resume:
    c.call(h[0]+0x9fb0);c.rw(8,0x8f000);c.rw(6,p);c.call(h[0]+0x58a6)
   else:c.call(h[0]+0x5894)
   expected=2 if blocked else (3 if c.rr(18)==0x90000 else 0)
  checking=False;assert not badwrites,(n,badwrites[:8])
  state=bytearray(c.get(low,length));state[h[2]+0x14-low:h[2]+0x1c-low]=bytes(8)
  state[h[6]+0x4292-low:h[6]+0x4294-low]=bytes(2)
  results.append((bytes(state),list(trace),c.get(fire,2) if patched else c.get(h[6]+0x4292,2)))
 assert got==expected and results[0]==results[1],(n,got,expected,[hex(low+i) for i,(a,b) in enumerate(zip(results[0][0],results[1][0])) if a!=b][:12],results[0][1],results[1][1])
 phase={0:2,2:1,3:3}[got];assert c.get(ctx+28,2)==struct.pack('>H',phase)
 before=c.get(low,length)
 assert call('world_body_step',{1:ctx})==0xfffffffd
 if got!=2:assert call('world_body_resume',{1:ctx})==0xfffffffd
 assert c.get(low,length)==before
 outcomes[got]+=1;drawcounts.add(sum(e[0]=='bound' for e in trace));resumes+=resume
 if got==2:
  # Use the real boundary state from this step. Simulate interpreter completion
  # by clearing its script state; compare only the continuation, not the modal UI.
  boundary=c.get(low,length);continuations=[]
  for patched in [False,True]:
   c.put(low,boundary);c.put(p+83,bytes(2));c.put(h[2]+0x14,live if patched else stamp)
   trace.clear();badwrites.clear();checking=True
   if patched:assert call('world_body_resume',{1:ctx}) in [0,3]
   else:
    c.rw(6,p);c.rw(8,0x8f000);c.call(h[0]+0x9fb0)
    c.rw(6,p);c.rw(8,0x8f000);c.call(h[0]+0x58a6)
   checking=False;assert not badwrites,badwrites
   state=bytearray(c.get(low,length));state[h[2]+0x14-low:h[2]+0x1c-low]=bytes(8)
   continuations.append((bytes(state),list(trace)))
  assert continuations[0]==continuations[1],('continuation',n)
  before=c.get(low,length)
  assert call('world_body_resume',{1:ctx})==0xfffffffd
  assert c.get(low,length)==before
  chained+=1

assert outcomes[2] and max(drawcounts)>0,(outcomes,drawcounts)

# All four bindings must reject before effects, including periodic binding.
for phase in [0,1]:
 for address in [weapons+0x3fe,damage+0x316,clone+0x1d4,periodic+0x84]:
  old=c.get(address,4);c.put(address,struct.pack('>I',p+2));c.put(ctx+28,struct.pack('>H',phase));before=c.get(low,length)
  assert call('world_body_resume' if phase else 'world_body_step',{1:ctx})==0xffffffff
  assert c.get(low,length)==before and c.get(ctx+28,2)==struct.pack('>H',phase)
  c.put(address,old)
print(json.dumps(dict(cases=512,outcomes=outcomes,drawcounts=sorted(drawcounts),resumes=resumes,chained=chained,calls=calls)))
