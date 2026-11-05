"""Native world command primary effects, excluding already-applied controls."""
import json,random,itertools
from unicorn_b import *
from layout import locate
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks']
c=CPU();c.put(0x200000,mem);c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/world-commands.hunk')).get_segments()[0].get_data()))
listing=(root/'tmp/c/world-commands.lst').read_text()
def sym(n):return base+int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
p=0x320000;clone=0x330000;rng=random.Random(0x50aa);calls=0;events=[]
callbacks=[0xa150,0xaf36,0x7eee,0x7c56]
CODE=C.CFUNCTYPE(None,C.c_void_p,C.c_uint64,C.c_uint32,C.c_void_p)
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
@CODE
def event(handle,a,n,user):
 off=a-h[0];events.append((off,c.rr(9)&65535,c.rr(10)&255) if off in [0xa150,0xaf36] else (off,))
hooks=[]
for off in callbacks:
 c.put(h[0]+off,bytes.fromhex('4e75'));hook=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hook),1<<2,event,None,h[0]+off,h[0]+off));hooks.append(hook)
def call(name,args):
 global calls
 regs={r:rng.randrange(0x1000000) for r in range(1,17) if r not in [8,9]};regs.update(args)
 for r,v in regs.items():c.rw(r,v)
 c.rw(8,0x8f000);c.call(sym(name));calls+=1
 assert c.rr(8)==0x8f004 and all(c.rr(r)==v for r,v in regs.items() if r!=9),name
 return c.rr(9)
assert call('world_commands_prepare',{1:h[0],2:clone})==0
expected=bytearray(c.get(h[0]+0x4ed4,0x462));expected[0x3f8:0x3fc]=bytes.fromhex('6000002c');assert c.get(clone,0x462)==expected
regions=[(h[6]+0x1558,0x30),(h[6]+0x42e8,2)]
keys=[1,2,3,4,5,6,7,8,9,10,11,0x804,0x805,0x806];cases=0
for key,damage,reserve,variant in itertools.product(keys,[0,0xffff,0x0020,0x2000,0x0080],[0,1],range(16)):
 b=bytearray(rng.randbytes(86));struct.pack_into('>H',b,14,damage);struct.pack_into('>HH',b,4,reserve,0);b[66]=variant*17
 resources=[rng.randbytes(n) for a,n in regions]
 if variant%2==0:resources[0]=bytes(len(resources[0]))
 initial_regs={r:rng.randrange(0x1000000) for r in range(1,17) if r!=8};initial_regs.update({6:p,9:key,16:key})
 c.put(p,b)
 for (a,n),data in zip(regions,resources):c.put(a,data)
 for r,v in initial_regs.items():c.rw(r,v)
 events.clear();c.rw(8,0x8f000);c.call(h[0]+0x4ed4)
 want=bytearray(c.get(p,86));want[63]=b[63]
 if key==3:want[57]=b[57] # field reader already resolved the reset
 expected_globals=[c.get(a,n) for a,n in regions];expected_events=list(events)
 c.put(p,b)
 for (a,n),data in zip(regions,resources):c.put(a,data)
 # Match native non-argument register inputs for callback arguments.
 for r,v in initial_regs.items():c.rw(r,v)
 c.rw(1,p);c.rw(2,clone);c.rw(3,h[0]+0xaf36);c.rw(9,key);events.clear();c.rw(8,0x8f000);c.call(sym('world_command_step'))
 assert c.rr(9)==1 and c.rr(8)==0x8f004
 assert c.get(p,86)==want,(key,damage,reserve,variant,c.get(p,86).hex(),want.hex())
 assert [c.get(a,n) for a,n in regions]==expected_globals
 # Notification D1 is unspecified; indicator D1.b is meaningful.
 normalize=lambda log:[(x[0],x[1]) if x[0]==0xa150 else x for x in log]
 assert normalize(events)==normalize(expected_events),(key,events,expected_events)
 cases+=1
# Boundaries and field/unknown commands cannot enter the native clone.
for key,result in [(0x45,2),(0x833,2),(0x46,2),(0xc,0),(0x51,0),(0x38,0),(0x803,0),(0xffff,0)]:
 before=c.get(p,86),[c.get(a,n) for a,n in regions];events.clear()
 assert call('world_command_step',{1:p,2:clone,3:h[0]+0xaf36,9:key})==result
 assert before==(c.get(p,86),[c.get(a,n) for a,n in regions]) and not events
rejects=0
for off in [0,0x3f8,0x426,0x460]:
 addr=h[0]+0x4ed4+off;old=c.get(addr,1);c.put(addr,bytes([old[0]^1]));before=c.get(clone,0x462)
 assert call('world_commands_prepare',{1:h[0],2:clone})==0xffffffff and c.get(clone,0x462)==before
 c.put(addr,old);rejects+=1
r=dict(native_primary_cases=cases,blocked_or_noop_cases=8,signature_rejections=rejects,scope='native reserves/damage/resource/engine/weapon primaries; field yaw/collective not replayed; UI/indicator/weapon-display callbacks stubbed, callback order checked')
(root/'tmp/c/world-commands-tests.json').write_text(json.dumps(r,indent=2)+'\n');print(r);c.close()
