"""Compare split command 03 with the native decoder and ordered control tapes."""
import json,random,itertools
from unicorn_b import *
from layout import locate
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks']
c=CPU();c.put(0x200000,mem);c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/control-mode.hunk')).get_segments()[0].get_data()))
listing=(root/'tmp/c/control-mode.lst').read_text()
def sym(n):return base+int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
p=0x320000;ref=0x321000;shadow=0x330000;rng=random.Random(0x5132);calls=0;events=[]
callback=h[0]+0xaf36;c.put(callback,bytes.fromhex('4e75'))
CODE=C.CFUNCTYPE(None,C.c_void_p,C.c_uint64,C.c_uint32,C.c_void_p)
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
@CODE
def event(handle,a,n,user):events.append((c.rr(9),c.rr(10)&255))
hook=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hook),1<<2,event,None,callback,callback))
def call(name,ptrs):
 global calls
 regs={r:rng.randrange(0x1000000) for r in range(1,17) if r not in [8,9]};regs.update(ptrs)
 for r,v in regs.items():c.rw(r,v)
 c.rw(8,0x8f000);c.call(sym(name));calls+=1
 assert c.rr(8)==0x8f004 and all(c.rr(r)==v for r,v in regs.items() if r!=9),name
 return c.rr(9)
def native(key):
 c.rw(6,ref);c.rw(16,key);c.rw(8,0x8f000);c.call(h[0]+0x4ed4)
def field(key):
 handled=call('control_mode_command',{1:shadow,2:p,9:key})
 assert handled==int(key==3)
 if not handled:call('control_target_command',{1:p,9:key})
 call('control_target_tail',{1:p})
def world(key):assert call('control_mode_world',{1:p,2:callback,9:key})==int(key==3)
cases=0
for flags,collective,key in itertools.product(range(256),[0,1,42,43,127,128,255],[3,0x803]):
 b=bytearray(rng.randbytes(86));b[66]=flags;b[57]=collective;c.put(p,b);c.put(ref,b)
 assert call('control_mode_init',{1:shadow,2:p})==0
 events.clear();native(key);expected=c.get(ref,86);expected_events=list(events);events.clear()
 field(key);assert c.get(p+66,1)==bytes([flags]);world(key)
 assert c.get(p,86)==expected and events==expected_events,(flags,collective,key)
 assert call('control_mode_check',{1:shadow,2:p})==0;cases+=1
# Later collective changes must survive a delayed world-side command 03.
tapes=[[3,0x51],[3,0x51,3,0x50,3,0x52],[0x50,3,0x53,3,0x51,0x803],
       [3,0x38,0x4e,0x51,3,0x3a,0x4f,0x52]*4]
sequences=0
for flags,batch,tape in itertools.product([0,16,255],[1,3,10,25],tapes):
 b=bytearray(86);b[66]=flags;b[57]=26;c.put(p,b);c.put(ref,b);assert call('control_mode_init',{1:shadow,2:p})==0
 expected_events=[];actual_events=[]
 for start in range(0,len(tape),batch):
  for key in tape[start:start+batch]:
   events.clear();native(key);expected_events.extend(events);events.clear();field(key);assert not events
   expected=bytearray(c.get(ref,86));expected[66]=c.get(p+66,1)[0]
   assert c.get(p,86)==expected,(flags,batch,tape,key)
  for key in tape[start:start+batch]:
   events.clear();world(key);actual_events.extend(events)
  assert c.get(p,86)==c.get(ref,86) and actual_events==expected_events
  assert call('control_mode_check',{1:shadow,2:p})==0
 sequences+=1
for invalid in [2,255,65535]:
 c.put(shadow,struct.pack('>H',invalid));before=c.get(p,86),c.get(shadow,2)
 assert call('control_mode_command',{1:shadow,2:p,9:3})==0xffffffff
 assert call('control_mode_check',{1:shadow,2:p})==0xffffffff
 assert before==(c.get(p,86),c.get(shadow,2))
assert call('control_mode_init',{1:shadow,2:p})==0;c.put(p+66,bytes([c.get(p+66,1)[0]^16]))
assert call('control_mode_check',{1:shadow,2:p})==0xffffffff
r=dict(native_cases=cases,ordered_tapes=sequences,invalid_states=3,divergence_detection=True,calls=calls,scope='command 03 split with view/collective/yaw/modified commands; native indicator callback stubbed, arguments/order checked; no queue dispatcher or live timing claim')
(root/'tmp/c/control-mode-tests.json').write_text(json.dumps(r,indent=2)+'\n');print(r);c.close()
