"""Native lifecycle command effects and stack returns through safe adapter."""
from unicorn_b import *
from layout import locate
import random,json,itertools
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks'];p=h[6]+0x3b88
blob=bytes(BinFmt().load_image(str(root/'tmp/c/runtime.hunk')).get_segments()[0].get_data());listing=(root/'tmp/c/runtime.lst').read_text()
def addr(n):return base+int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
c=CPU();c.put(0x200000,mem);c.put(base,blob);BIND=0x300000;REF=0x310000;low=0x97ee00;length=0x21200;rng=random.Random(42)
c.put(REF,bytes.fromhex('4eb9')+struct.pack('>I',h[0]+0x4ed4)+bytes.fromhex('4e75'))
trace=[];keys=[]
CODE=C.CFUNCTYPE(None,C.c_void_p,C.c_uint64,C.c_uint32,C.c_void_p)
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
@CODE
def callback(handle,a,n,user):
 trace.append((a-h[0],c.rr(9),c.rr(5),c.rr(6)))
 if a==h[0]+0x34e8:
  assert keys,'unexpected keyboard retry'
  c.rw(9,keys.pop(0))
hooks=[]
for off in (0x46de,0x496e,0x1576,0x1594,0x7ec8,0x7eee,0xb4da,0x34e8):
 # Keyboard TST materializes native zero flags for the pause loop.
 c.put(h[0]+off,bytes.fromhex('4a404e75' if off==0x34e8 else '4e75'))
 hook=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hook),1<<2,callback,None,h[0]+off,h[0]+off));hooks.append(hook)
def call(name,args,expected):
 rs={r:rng.randrange(0x1000000) for r in range(1,17) if r!=8};rs.update(args)
 for r,v in rs.items():c.rw(r,v&0xffffffff)
 c.rw(8,0x8f000);c.call(addr(name));assert c.rr(8)==0x8f004 and c.rr(18)==0x90000
 assert c.rr(9)==expected,(name,c.rr(9),expected)
 assert all(c.rr(r)==v&0xffffffff for r,v in rs.items() if r!=9),(name,'registers')
call('boundary_commands_prepare',{1:h[0],2:BIND},0)
initial=c.get(low,length);cases=0
for key,sound,yaw,speed,pause_keys in itertools.product((0x45,0x833,0x40,0x1c,0x41,0x37,0x21,0x22,0x34,0x42,0x46),(0,0x520000),(0,6,250),(0,20),((1,),(0,0,1),(0x45,))):
 results=[]
 for patched in (False,True):
  c.put(low,initial);c.put(p+24,bytes(1));c.put(p+63,bytes([yaw]));c.put(p+80,bytes([speed]));c.put(h[6]+0x1f0,struct.pack('>I',sound));trace.clear();keys=list(pause_keys)
  if patched:call('boundary_command_step',{1:p,2:BIND,3:h[6],9:key},4 if key in (0x45,0x833) or key==0x42 and pause_keys[-1]==0x45 else 0)
  else:
   c.rw(5,h[6]);c.rw(6,p);c.rw(16,key);c.rw(8,0x8f000);c.call(REF);assert c.rr(8)==0x8f004
  # Callback d0 is meaningful for view arguments; other callbacks may inherit scratch.
  events=[(off,d0 if off==0x496e else None) for off,d0,a4,a5 in trace]
  results.append((c.get(low,length),events))
 assert results[0]==results[1],(key,sound,yaw,speed,pause_keys)
 cases+=1
# Retired key 12 is not admitted to the lifecycle adapter.
for key in (12,0,1,3,0x51,0x080c,0x0842,0x1045):
 before=c.get(low,length);call('boundary_command_step',{1:p,2:BIND,3:h[6],9:key},0xfffffffd);assert c.get(low,length)==before
c.put(BIND,bytes(4));before=c.get(low,length);call('boundary_command_step',{1:p,2:BIND,3:h[6],9:0x42},0xfffffffd);assert c.get(low,length)==before
for off in (0x4ed4,0x4ed6,0x4eec,0x4eee,0x4ef0,0x5334):
 saved=c.get(h[0]+off,2);c.put(h[0]+off,bytes(2));c.put(BIND,b'Z'*4)
 call('boundary_commands_prepare',{1:h[0],2:BIND},0xffffffff);assert c.get(BIND,4)==b'Z'*4;c.put(h[0]+off,saved)
print(json.dumps(dict(status='passed',native_cases=cases,retired_speed_rejected=True,invalid_keys=8,signature_rejections=6,pause_escape_stack=True)));c.close()
