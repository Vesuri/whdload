#!/usr/bin/env python3
"""Interrupt real history_pop at each instruction boundary with a publication."""
import json
from unicorn_b import *
blob=bytes(BinFmt().load_image(str(root/'tmp/c/cores.bin')).get_segments()[0].get_data())
listing=(root/'tmp/c/cores.lst').read_text()
def sym(n):return int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
H=0x310000;R=0x320000;O=0x330000;END=0x90000
c=CPU();c.put(base,blob)
def call(name,d0=0,a1=R):
 c.rw(8,0x8e000);c.rw(1,H);c.rw(2,a1);c.rw(9,d0);c.call(base+sym(name));return c.rr(9)
def payload(f):return struct.pack('>10I',f,*[f*100+i for i in range(9)])
def setup(count):
 c.put(H,bytes(sym('TH_SIZE')));call('history_init')
 for f in range(1,count+1):
  c.put(R,payload(f));assert call('history_publish')==1
 c.put(O,b'\xcc'*40);c.put(R,payload(count+1))
 c.rw(17,0x2000);c.rw(8,0x8f000);c.put(0x8f000,struct.pack('>I',END))
 c.rw(1,H);c.rw(2,O);c.rw(18,base+sym('history_pop'))
u.uc_context_alloc.argtypes=[C.c_void_p,C.POINTER(C.c_void_p)]
u.uc_context_save.argtypes=[C.c_void_p,C.c_void_p]
u.uc_context_restore.argtypes=[C.c_void_p,C.c_void_p]
u.uc_context_free.argtypes=[C.c_void_p]
def interrupt():
 # Full CPU context also preserves deferred arithmetic flags.
 context=C.c_void_p();ok(u.uc_context_alloc(c.h,C.byref(context)));ok(u.uc_context_save(c.h,context))
 result=call('history_publish')
 ok(u.uc_context_restore(c.h,context));ok(u.uc_context_free(context))
 return result
def consume(at=None):
 pcs=[];published=None
 while c.rr(18)!=END:
  if len(pcs)==at:published=interrupt()
  pc=c.rr(18);pcs.append(pc)
  ok(u.uc_emu_start(c.h,pc,END,0,1))
  assert len(pcs)<100
 if len(pcs)==at:published=interrupt()
 return pcs,c.rr(9),published
results=[]
for count in (0,1,127,128):
 setup(count);pcs,_,_=consume()
 for at in range(len(pcs)+1):
  setup(count);trace,result,published=consume(at)
  read=int.from_bytes(c.get(H+2,2),'big');write=int.from_bytes(c.get(H,2),'big')
  fault=int.from_bytes(c.get(H+6,2),'big')
  assert result in (0,1,0xffffffff)
  if result==1:
   assert c.get(O,40)==payload(1),(count,at,'torn payload')
   assert read==1
  else:assert read==0
  if published==1:
   assert write==count+1 and fault==0
   assert c.get(H+20+(count%128)*40,40)==payload(count+1)
  else:
   assert published==0xffffffff and count==128
   assert write==128 and fault==1
   assert c.get(H+20,5120)==b''.join(payload(f) for f in range(1,129))
  results.append(dict(occupancy=count,boundary=at,consumer=result,producer=published,fault=fault))
report=dict(cases=len(results),late_fault_returns=sum(x['consumer']==1 and x['fault']==1 for x in results),cases_detail=results)
(root/'tmp/c/history-preemption.json').write_text(json.dumps(report,indent=2)+'\n')
print({k:v for k,v in report.items() if k!='cases_detail'})
c.close()
