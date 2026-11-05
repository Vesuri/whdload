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
Q=0x390000;CTX=0x3a0000
@CODE
def fault(handle,a,n,user):c.put(Q+8,struct.pack('>H',1))
hook=C.c_size_t();addr=sym('commands_ack');ok(u.uc_hook_add(c.h,C.byref(hook),1<<2,fault,None,addr,addr));hooks.append(hook)
assert call('commands_init',{1:Q,9:0})==0
b=bytearray(86);struct.pack_into('>H',b,4,1);c.put(p,b)
c.put(CTX,struct.pack('>4I',Q,p,clone,h[0]+0xaf36)+bytes(12))
assert call('commands_publish',{1:Q,9:1,10:1})==1
assert call('control_world_next',{1:CTX,9:1})==0xffffffff
assert c.get(p+66,1)==bytes([4]) and c.get(Q+2,4)==bytes(4)
assert c.get(CTX+22,6)==struct.pack('>HI',1,1)
before=c.get(p,86);event_count=len(events)
assert call('control_world_next',{1:CTX,9:1})==0xffffffff
assert c.get(p,86)==before and len(events)==event_count and c.get(CTX+22,6)==struct.pack('>HI',0,1)
r=dict(cases=1,scope='world engine action before ack fault, retained cursor and committed accounting, no duplicate action/callback on retry')
(root/'tmp/c/world-command-fault-tests.json').write_text(json.dumps(r,indent=2)+'\n');print(r);c.close()
