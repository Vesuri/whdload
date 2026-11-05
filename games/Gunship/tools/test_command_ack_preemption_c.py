#!/usr/bin/env python3
"""Interrupt real history_pop at each instruction boundary with a publication."""
import json
from unicorn_b import *
blob=bytes(BinFmt().load_image(str(build/'input/Gunship.Slave')).get_segments()[0].get_data())
listing=(build/'input/Gunship.lst').read_text(encoding='latin1')
def sym(n):return int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
H=0x310000;R=0x320000;O=0x330000;END=0x90000
c=CPU();c.put(base,blob)
def call(name,d0=0,a1=R):
 c.rw(8,0x8e000);c.rw(1,H);c.rw(2,a1);c.rw(9,d0);c.call(base+sym(name));return c.rr(9)
def payload(f):return struct.pack('>IHH',f,0x800|f,0)
def setup(count,other,role):
 c.put(H,bytes(sym('CQ_SIZE')));call('commands_init')
 for f in range(1,count+1):
  c.rw(10,0x800|f);assert call('commands_publish',f)==1
 c.rw(10,role);assert call('commands_peek',count,a1=O)==1
 c.put(H+2+(1-role)*2,struct.pack('>H',other))
 c.rw(17,0x2000);c.rw(8,0x8f000);c.put(0x8f000,struct.pack('>I',END))
 c.rw(1,H);c.rw(2,O);c.rw(10,role);c.rw(18,base+sym('commands_ack'))
u.uc_context_alloc.argtypes=[C.c_void_p,C.POINTER(C.c_void_p)]
u.uc_context_save.argtypes=[C.c_void_p,C.c_void_p]
u.uc_context_restore.argtypes=[C.c_void_p,C.c_void_p]
u.uc_context_free.argtypes=[C.c_void_p]
def interrupt(count):
 # Preserve lazy arithmetic flags as well as public registers.
 context=C.c_void_p();ok(u.uc_context_alloc(c.h,C.byref(context)));ok(u.uc_context_save(c.h,context))
 c.rw(10,0x800|count+1);result=call('commands_publish',count+1)
 ok(u.uc_context_restore(c.h,context));ok(u.uc_context_free(context))
 return result
def consume(count,at=None):
 pcs=[];published=None
 while c.rr(18)!=END:
  if len(pcs)==at:published=interrupt(count)
  pc=c.rr(18);pcs.append(pc);ok(u.uc_emu_start(c.h,pc,END,0,1));assert len(pcs)<100
 if len(pcs)==at:published=interrupt(count)
 return pcs,c.rr(9),published
cases=late=0
for role in [0,1]:
 for count,other in [(1,0),(127,0),(128,0),(128,1)]:
  setup(count,other,role);pcs,_,_=consume(count)
  for at in range(len(pcs)+1):
   setup(count,other,role);trace,result,published=consume(count,at)
   read=int.from_bytes(c.get(H+2+role*2,2),'big');write=int.from_bytes(c.get(H,2),'big');fault=int.from_bytes(c.get(H+8,2),'big')
   assert c.get(O,8)==payload(1) and result in [1,0xffffffff],(role,count,other,at,c.get(O,8).hex(),hex(result))
   assert read==int(result==1)
   if published==1:
    assert write==count+1 and fault==0
    assert c.get(H+24+(count%128)*8,8)==payload(count+1)
    if count==128:assert read==1 and other==1
   else:
    assert published==0xffffffff and count==128 and write==128 and fault==1
    assert c.get(H+24,1024)==b''.join(payload(f) for f in range(1,129))
   late+=int(result==1 and fault==1);cases+=1
report=dict(cases=cases,acknowledged_with_late_fault=late,scope='producer at every ack instruction boundary, both readers, full-ring reuse after both release')
(root/'tmp/c/command-ack-preemption.json').write_text(json.dumps(report,indent=2)+'\n');print(report);c.close()
