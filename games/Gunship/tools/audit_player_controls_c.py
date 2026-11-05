#!/usr/bin/env python3
"""Native attitude tail: exhaustive direction pairs and representative damage/height states."""
import json,collections
from unicorn_b import *
from layout import locate
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks'];p=h[6]+0x3b88
c=CPU();c.put(0x200000,mem);writes=collections.defaultdict(set);count=0
CB=C.CFUNCTYPE(None,C.c_void_p,C.c_int,C.c_uint64,C.c_int,C.c_int64,C.c_void_p)
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
def write(handle,kind,address,size,value,user):
 if not 0x8d000<=address<0x90000:writes[(address,size)].add(c.rr(18)-h[0])
cb=CB(write);handle=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(handle),1<<11,cb,None,1,0))
for damage in (0,1):
 for height in (0,1,128,255,256,512):
  for x in (-1,0,1):
   for y in (-1,0,1):
    for previous_y in (-1,0,1):
     for roll in (-20,0,20):
      b=bytearray(0x56);b[15]=damage;struct.pack_into('>H',b,28,height);struct.pack_into('>H',b,42,160)
      b[54]=4;b[55]=roll&255;c.put(p,b)
      c.put(h[6]+0x4294,bytes([x&255,y&255]));c.put(h[0]+0x5524,bytes([previous_y&255]))
      c.rw(8,0x8f000);c.rw(6,p);c.rw(17,0x2000);c.call(h[0]+0x5376)
      assert c.rr(18)==0x90000 and c.rr(8)==0x8f004
      out=c.get(p,86)
      if not damage:
       assert out[55]==max(-20,min(20,roll+4*x))&255
       # High-altitude cases cannot take the low-height random pitch branch.
       if height>=256:assert out[54]==(4-(y+previous_y if y else 0))&255
      count+=1
report=dict(cases=count,scope='native +05376 attitude tail, not navigation prefix',writes=[dict(address=f'{a:08x}',size=s,pcs=[f'{pc:05x}' for pc in sorted(pcs)]) for (a,s),pcs in sorted(writes.items())])
(root/'tmp/c/player-control-accesses.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));c.close()
