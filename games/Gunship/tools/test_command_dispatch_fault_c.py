"""Native command classification and retained player-reader effects."""
import json,random
from unicorn_b import *
from layout import locate
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks']
c=CPU();c.put(0x200000,mem);c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/command-dispatch.hunk')).get_segments()[0].get_data()))
listing=(root/'tmp/c/command-dispatch.lst').read_text()
def sym(n):return base+int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
Q=0x300000;P=0x310000;M=0x320000;CTX=0x330000;O=0x340000;REF=0x350000
rng=random.Random(0x4ed4);calls=0
classes={}
for cls,keys in [(1,[0x4c,0x4d,0x4e,0x4f,0x50,0x5a,0x51,0x5b,0x52,0x5c,0x53,0x5d,0x38,0x39,0x3a]),(2,[3]),(3,[1,2,4,5,6,7,8,9,10,11,0x804,0x805,0x806]),(4,[0x45,0x833,0x40,0x1c,0x41,0x37,0x21,0x22,0x34,0x42,0x46])]:
 for key in keys:assert key not in classes;classes[key]=cls
native_keys={int.from_bytes(c.get(h[0]+off+2,2),'big') for off in range(0x4ed4,0x5334,2) if c.get(h[0]+off,2)==bytes.fromhex('0c47')}
assert native_keys==set(classes)|{12} and len(classes)==40

def call(name,args):
 global calls
 regs={r:rng.randrange(0x1000000) for r in range(1,17) if r not in [8,9]};regs.update(args)
 for r,v in regs.items():c.rw(r,v)
 c.rw(8,0x8f000);c.call(sym(name));calls+=1
 assert c.rr(8)==0x8f004 and all(c.rr(r)==v for r,v in regs.items() if r!=9),name
 return c.rr(9)
def setup(flags=16,epoch=0):
 assert call('commands_init',{1:Q,9:epoch})==0
 b=bytearray(86);b[57]=26;b[66]=flags;c.put(P,b);c.put(REF,b)
 assert call('control_mode_init',{1:M,2:P})==0
 c.put(CTX,struct.pack('>III',Q,P,M)+bytes(12))
CODE=C.CFUNCTYPE(None,C.c_void_p,C.c_uint64,C.c_uint32,C.c_void_p)
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
@CODE
def interrupt(handle,a,n,user):c.put(Q+8,struct.pack('>H',1))
hook=C.c_size_t();addr=sym('commands_ack');ok(u.uc_hook_add(c.h,C.byref(hook),1<<2,interrupt,None,addr,addr))
setup();assert call('commands_publish',{1:Q,9:1,10:0x51})==1
assert call('control_player_next',{1:CTX,9:1})==0xffffffff
assert c.get(P+57,1)==bytes([27]) and c.get(Q+2,4)==bytes(4) and c.get(Q+8,2)==bytes.fromhex('0001')
assert c.get(CTX+18,6)==struct.pack('>HI',1,1)
before=c.get(P,86);assert call('control_player_next',{1:CTX,9:1})==0xffffffff
assert c.get(P,86)==before and c.get(CTX+18,6)==struct.pack('>HI',0,1)
r=dict(cases=1,calls=calls,scope='effect-before-ack producer fault: retained command, committed marker/count, blocked retry without duplicate effect')
(root/'tmp/c/command-dispatch-fault-tests.json').write_text(json.dumps(r,indent=2)+'\n');print(r);c.close()
