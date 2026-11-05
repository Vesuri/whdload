"""Native flight entry installation, Exec wrapper ABI and fault exit."""
from pathlib import Path
exec(Path(__file__).with_name('test_script_generation_c.py').read_text().split('rs={')[0])
EXEC=0x150000;c.put(4,struct.pack('>I',EXEC));c.put(base+sym('_resload'),struct.pack('>I',resload))
c.put(arena+sym('RT_DRAW_READY'),b'\0\1')
rs={1:arena,3:resload}
for enabled in (0,1):
 c.put(base+sym('_custom1'),struct.pack('>I',enabled));c.put(0x750000,bytes(8))
 assert run(base+sym('timing_loop_install'),rs)[9]==0
 if enabled:
  image,patch=struct.unpack('>II',c.get(0x750000,8));cmd,off,rel=struct.unpack('>HHh',c.get(patch,6))
  assert image==h[0] and (cmd,off)==(0x8003,0x561c) and patch+rel==base+sym('timing_flight_entry')
 else:assert c.get(0x750000,8)==bytes(8)
rejects=0
for off in range(0x561c,0x5628):
 old=c.get(h[0]+off,1);c.put(h[0]+off,bytes([old[0]^1]));c.put(0x750000,bytes(8))
 assert run(base+sym('timing_loop_install'),rs)[9]==0xffffffff and c.get(0x750000,8)==bytes(8)
 c.put(h[0]+off,old);rejects+=1
c.put(arena+sym('RT_DRAW_READY'),bytes(2));assert run(base+sym('timing_loop_install'),rs)[9]==0xffffffff;c.put(arena+sym('RT_DRAW_READY'),b'\0\1')
CODE=C.CFUNCTYPE(None,C.c_void_p,C.c_uint64,C.c_uint32,C.c_void_p)
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
disable=EXEC-120;enable=EXEC-126
for a in (disable,enable):c.put(a,bytes.fromhex('4e75'))
level=0;exec_calls=[];errors=[]
@CODE
def exec_call(handle,a,n,user):
 global level
 exec_calls.append(a)
 level+=1 if a==disable else -1
 if level not in (0,1):errors.append(level)
 # Deliberately clobber every allowed register to check the wrapper contract.
 for r in range(1,17):
  if r!=8:c.rw(r,rng.randrange(0xffffffff))
hooks=[]
for a in (disable,enable):
 hh=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hh),1<<2,exec_call,None,a,a));hooks.append(hh)
for value in (0,4,0xffffffff,0xfffffffd):
 for name in ('timing_flight_exclude','timing_flight_include'):
  regs={r:rng.randrange(0xffffffff) for r in range(1,17) if r!=8};regs[9]=value
  got=run(base+sym(name),regs)
  assert all(got[r]==v for r,v in regs.items())
assert level==0 and not errors and len(exec_calls)==8
loop_result=4;loop_calls=0
@CODE
def loop(handle,a,n,user):
 global loop_calls
 loop_calls+=1
 if (c.rr(1),c.rr(2),c.rr(3))!=(arena,base+sym('timing_flight_exclude'),base+sym('timing_flight_include')):errors.append('bindings')
 c.rw(9,loop_result&0xffffffff)
a=base+sym('timing_runtime_loop');c.put(a,bytes.fromhex('4e75'));hh=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hh),1<<2,loop,None,a,a));hooks.append(hh)
regs={r:rng.randrange(0xffffffff) for r in range(1,17) if r!=8}
got=run(base+sym('timing_flight_entry'),regs)
assert all(got[r]==v for r,v in regs.items()) and int.from_bytes(c.get(base+sym('timing_flight_status'),4),'big')==4
for loop_result in (-1,-3):
 c.rw(17,0x2000);c.rw(8,0x8f000)
 c.call(base+sym('timing_flight_entry'),end=resload+4)
 assert c.rr(18)==resload+4
 sp=c.rr(8);reason,message=struct.unpack('>II',c.get(sp,8));assert reason==43 and c.get(message,64).startswith(b'Enhanced framerate: flight timing failed'),(hex(sp),reason,hex(message),c.get(message,45))
 assert int.from_bytes(c.get(base+sym('timing_flight_status'),4),'big')==loop_result&0xffffffff
assert loop_calls==3 and not errors
print(json.dumps(dict(status='passed',signature_rejections=rejects,exec_wrapper_cases=8,entry_return=1,abort_cases=2,custom_off_bypass=True)))
c.close()
