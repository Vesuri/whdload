#!/usr/bin/env python3
"""Execute native immediate-control commands, including their shared tail."""
import itertools,json
from unicorn_b import *
from layout import locate
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks'];p=h[6]+0x3b88
c=CPU();c.put(0x200000,mem)
view={0x4c:0,0x4d:0,0x4e:32,0x4f:224};collect={0x50:4,0x5a:4,0x51:1,0x5b:1,0x52:-1,0x5c:-1,0x53:-4,0x5d:-4}
keys=list(view)+list(collect)+[0x38,0x39,0x3a,0x7f]
# Modified controls must not be mistaken for their unmodified primary effects.
keys += [k|0x800 for k in keys]
count=0;writes={}
CB=C.CFUNCTYPE(None,C.c_void_p,C.c_int,C.c_uint64,C.c_int,C.c_int64,C.c_void_p)
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
def observe(handle,kind,a,size,value,user):
 if not 0x8d000<=a<0x90000:writes.setdefault((a,size),set()).add(c.rr(18)-h[0])
cb=CB(observe);hook=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hook),1<<11,cb,None,1,0))
for key,collective,yaw,speed in itertools.product(keys,range(43),range(-4,5),[-128,-15,-1,0,1,15,127]):
 b=bytearray(86);b[0x1a]=19;b[0x39]=collective;b[0x3f]=yaw&255;b[0x50]=speed&255
 expected=bytearray(b)
 if key in view:expected[0x1a]=view[key]
 if key in collect:expected[0x39]=max(0,min(42,collective+collect[key]))
 if key==0x38:yaw-=1
 if key==0x39:yaw=0
 if key==0x3a:yaw+=1
 expected[0x3f]=(max(-4,min(4,yaw)) if speed==0 else 0)&255
 c.put(p,b);c.rw(8,0x8f000);c.rw(6,p);c.rw(16,key);c.rw(17,0x2000)
 c.call(h[0]+0x4ed4)
 assert c.rr(18)==0x90000 and c.rr(8)==0x8f004
 assert c.get(p,86)==expected,(key,collective,yaw,speed,c.get(p,86).hex(),expected.hex())
 count+=1
r=dict(cases=count,scope='native command handler for view/collective/yaw/no-op and modified variants; no stubs',writes=[dict(address=f'{a:08x}',size=s,pcs=[f'{x:05x}' for x in sorted(pcs)]) for (a,s),pcs in sorted(writes.items())])
(root/'tmp/c/player-command-audit.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2));c.close()
