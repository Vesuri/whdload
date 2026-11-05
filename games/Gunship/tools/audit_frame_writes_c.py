"""Native frame write inventory; no DMA emulation, display swap stubbed."""
from unicorn_b import *
from layout import locate
from functools import lru_cache
import json,collections
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();chip=(root/'tmp/prof/flight1-mem/chip.bin').read_bytes();h=locate(mem)['hunks']
blob=bytes(BinFmt().load_image(str(build/'release/Gunship.Slave')).get_segments()[0].get_data());listing=(build/'release/Gunship.lst').read_text(encoding='latin1')
@lru_cache(None)
def addr(n):return base+int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
c=CPU();c.put(0,chip);c.put(0x200000,mem);c.put(base,blob)
# Already-extracted effect ownership, plus display handoff. This is a write
# audit, not a correct picture or visibility reference (there is no blitter).
for off in (0x4496,0x9b9a,0xbe5a):c.put(h[0]+off,bytes.fromhex('4e75'))
c.put(h[0]+0x825e,bytes.fromhex('70004e75'))
def call(entry,args={},end=0x90000):
 for r,v in args.items():c.rw(r,v)
 c.rw(8,0x8f000);c.call(entry,end=end)
 assert c.rr(18)==end,(hex(entry),hex(c.rr(18)))
call(h[0]+0x57e2,{6:h[6]+0x3b88},h[0]+0x5830)
call(addr('scene_state_build'),{1:h[4],2:h[0]+0xc6a0,3:h[6],4:h[6]+0x3904})
MEM=C.CFUNCTYPE(None,C.c_void_p,C.c_int,C.c_uint64,C.c_int,C.c_int64,C.c_void_p)
CODE=C.CFUNCTYPE(None,C.c_void_p,C.c_uint64,C.c_uint32,C.c_void_p)
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
writes=collections.Counter();tail=collections.deque(maxlen=32)
@MEM
def write(handle,kind,a,n,value,user):
 if not(0x8e000<=a and a+n<=0x8f004):writes[(c.rr(18),a,n)]+=1
@CODE
def block(handle,a,n,user):tail.append(hex(a))
hooks=[]
for kind,fn in ((1<<11,write),(1<<3,block)):
 hook=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hook),kind,fn,None,1,0));hooks.append(hook)
try:call(h[0]+0x5c04)
finally:
 rows=[dict(pc=hex(pc),address=hex(a),size=n,count=count) for (pc,a,n),count in sorted(writes.items())]
 report=dict(pc=hex(c.rr(18)),writes=rows,last_blocks=list(tail))
 (root/'tmp/c/frame-writes.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(dict(pc=report['pc'],write_sites=len(rows),last_blocks=list(tail))));c.close()
