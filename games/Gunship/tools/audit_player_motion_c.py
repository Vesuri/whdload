#!/usr/bin/env python3
"""Execute native airborne flight arithmetic and inventory real memory accesses."""
import json,random,collections
from unicorn_b import *
from layout import locate
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();layout=locate(mem)
h=layout['hunks'];p=h[6]+0x3b88;c=CPU();c.put(0x200000,mem)
rng=random.Random(3060);access=collections.defaultdict(set);outside=collections.defaultdict(set)
CALLBACK=C.CFUNCTYPE(None,C.c_void_p,C.c_int,C.c_uint64,C.c_int,C.c_int64,C.c_void_p)
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
def observe(handle,kind,address,size,value,user):
 pc=c.rr(18)-h[0]
 if p<=address<p+0x56:access[(kind,address-p,size)].add(pc)
 elif kind==17 and not 0x8d000<=address<0x90000:outside[(address,size)].add(pc)
cb=CALLBACK(observe);hook=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hook),(1<<10)|(1<<11),cb,None,1,0))
cases=[]
for n in range(384):
 b=bytearray(0x56)
 def word(off,val):struct.pack_into('>H',b,off,val&65535)
 def byte(off,val):b[off]=val&255
 word(0,rng.choice([0x1800,0x7000,0xd800]));word(2,rng.choice([0x1800,0x8000,0xd800]))
 word(4,rng.choice([0,0x4000,0x8000]));word(6,rng.choice([0,0x4000,0x8000]))
 word(12,n);word(14,n%4);byte(16,rng.choice([0,2]));byte(18,rng.randrange(8))
 byte(20,rng.randrange(-8,9));byte(21,rng.randrange(-8,9));byte(27,rng.randrange(157))
 word(28,rng.randrange(128,2000));word(42,rng.randrange(-128,256))
 byte(53,rng.randrange(256));byte(54,rng.choice([-12,-1,0,1,20]));byte(55,rng.choice([-20,0,20]))
 byte(57,rng.randrange(43));byte(59,rng.randrange(64));byte(61,rng.randrange(256))
 byte(62,rng.randrange(-64,65));byte(63,rng.randrange(-4,5));byte(66,rng.choice([0,4,8,12,16,28]));byte(80,rng.randrange(-32,64))
 c.put(p,b);c.rw(8,0x8f000);c.rw(6,p);c.rw(5,h[6]);c.rw(17,0x2000)
 c.call(h[0]+0x937c)
 assert c.rr(18)==0x90000 and c.rr(8)==0x8f004,n
 assert c.rr(6)==p,n
 after=c.get(p,0x56)
 cases.append(dict(input=b.hex(),output=after.hex()))
report=dict(cases=len(cases),scope='native airborne +0937c only; excludes contact, control routine and initialization',
 accesses=[dict(kind='write' if k==17 else 'read',offset=f'{off:02x}',size=size,pcs=[f'{pc:05x}' for pc in sorted(pcs)]) for (k,off,size),pcs in sorted(access.items())],
 outside_writes=[dict(address=f'{a:08x}',size=size,pcs=[f'{pc:05x}' for pc in sorted(pcs)]) for (a,size),pcs in sorted(outside.items())])
(root/'tmp/c/player-motion-accesses.json').write_text(json.dumps(report,indent=2)+'\n')
(root/'tmp/c/player-motion-fixtures.json').write_text(json.dumps(cases,indent=2)+'\n')
print(json.dumps(report,indent=2));c.close()
