"""Native tick/cooldown/engine prefix against extracted world opening."""
import json,random
from unicorn_b import *
from layout import locate
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks']
c=CPU();c.put(0x200000,mem)
c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/scheduled-world-start.hunk')).get_segments()[0].get_data()))
listing=(root/'tmp/c/scheduled-world-start.lst').read_text()
def sym(n):return base+int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
P=0x300000;CLONE=0x310000;BAD=0x320000;native=h[6]+0x3b88;lamps=h[6]+0x1581
rng=random.Random(0x5640);calls=0
# Keep native inventory/cooldown indicator dispatch; stub only its final UI call.
c.put(h[0]+0xaf36,bytes.fromhex('4e75'))
trace=[]
CODE=C.CFUNCTYPE(None,C.c_void_p,C.c_uint64,C.c_uint32,C.c_void_p)
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
@CODE
def indicator(handle,a,n,user):trace.append((c.rr(9)&65535,c.rr(10)&255))
hook=C.c_size_t();entry=h[0]+0xaf36
ok(u.uc_hook_add(c.h,C.byref(hook),1<<2,indicator,None,entry,entry))
def call(name,args):
 global calls
 regs={r:rng.randrange(0x1000000) for r in range(1,17) if r not in [8,9]};regs.update(args)
 for r,v in regs.items():c.rw(r,v)
 c.rw(8,0x8f000);c.call(sym(name));calls+=1
 assert c.rr(18)==0x90000 and c.rr(8)==0x8f004
 assert all(c.rr(r)==v for r,v in regs.items() if r!=9),name
 return c.rr(9)
assert call('world_start_prepare',{1:h[0],2:CLONE,3:h[6],4:P})==0
TS=0x400000;TC=0x401000;TH=0x402000;CQ=0x404000;record=0x405000;sample=0x406000;SW=0x407000
runs=[]
def ready(rate=50,epoch=0):
 assert call('clock_init',{1:TC,9:epoch,10:rate})==0
 assert call('history_init',{1:TH,9:epoch})==0
 assert call('commands_init',{1:CQ,9:0})==0
 assert call('scheduler_init',{1:TS,2:TC,3:TH,4:CQ})==0
 c.put(SW,struct.pack('>III',TS,P,CLONE)+bytes(8))
 b=bytearray(86);struct.pack_into('>HH',b,4,4096,4096);struct.pack_into('>H',b,12,65532);struct.pack_into('>H',b,28,1024);b[66]=28;b[74]=255;c.put(P,b)
for rate in [50,60]:
 for epoch in [0,0xfffffff0]:
  baseline=None
  for batch in [1,25]:
   ready(rate,epoch);states=[];count=0
   for first in range(1,121,batch):
    for f in range(first,min(first+batch,121)):
     c.put(sample,struct.pack('>I',(epoch+f)&0xffffffff)+bytes(36));assert call('history_publish',{1:TH,2:sample})==1
    assert call('scheduler_begin',{1:TS,9:128,10:8})==0
    while True:
     got=call('scheduler_next',{1:TS,2:record})
     if got==0:break
     assert got==1
     due=int.from_bytes(c.get(TS+14,2),'big');before=c.get(P,86)
     assert call('scheduled_world_start',{1:SW})==(0 if due else 0xfffffffd)
     if due:
      count+=1;assert c.get(P+12,2)==struct.pack('>H',(65532+count)&65535) and c.get(P+74,1)==bytes([255-count])
      assert c.get(SW+18,2)==b'\0\1'
      committed=c.get(P,86)
      assert call('scheduled_world_start',{1:SW})==0xfffffffd and c.get(P,86)==committed
     else:assert c.get(P,86)==before
     states.append(c.get(P,86))
     assert call('scheduler_player_done',{1:TS})==due
     if due:assert call('scheduler_world_done',{1:TS})==0
   if baseline is None:baseline=states
   else:assert baseline==states
   assert count==120*3//rate
   runs.append(dict(rate=rate,epoch=epoch,batch=batch,deadlines=count))
# Fresh CPU for instruction hook before any cached scheduler_check execution.
c.close();c=CPU();c.put(0x200000,mem);c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/scheduled-world-start.hunk')).get_segments()[0].get_data()))
c.put(h[0]+0xaf36,bytes.fromhex('4e75'))
assert call('world_start_prepare',{1:h[0],2:CLONE,3:h[6],4:P})==0
ready();c.put(TS+12,struct.pack('>HH',1,1));c.put(TS+24,struct.pack('>I',123))
checks=0;armed=True
CODE=C.CFUNCTYPE(None,C.c_void_p,C.c_uint64,C.c_uint32,C.c_void_p)
@CODE
def fault(handle,a,n,user):
 global checks
 checks+=1
 if armed and checks==2:c.put(TH+6,b'\0\1')
hook=C.c_size_t();entry=sym('scheduler_check');ok(u.uc_hook_add(c.h,C.byref(hook),1<<2,fault,None,entry,entry))
assert call('scheduled_world_start',{1:SW})==0xffffffff
assert c.get(P+12,2)==b'\xff\xfd' and c.get(SW+12,8)==struct.pack('>IHH',123,1,1)
assert c.get(TS+32,8)==bytes(8)
after=c.get(P,86)
assert call('scheduled_world_start',{1:SW})==0xffffffff and c.get(P,86)==after
armed=False;c.put(TH+6,bytes(2));c.put(TS+22,bytes(2))
assert call('scheduled_world_start',{1:SW})==0xfffffffd and c.get(P,86)==after
for kind in ['not-due','ready','world','fault','binding']:
 ready();c.put(TS+12,struct.pack('>HH',1,1))
 if kind=='not-due':c.put(TS+14,bytes(2))
 if kind=='ready':c.put(TS+12,bytes(2))
 if kind=='world':c.put(TS+12,b'\0\2')
 if kind=='fault':c.put(TH+6,b'\0\1')
 if kind=='binding':c.put(SW+4,struct.pack('>I',P+2))
 before=c.get(P,86)
 assert call('scheduled_world_start',{1:SW})==(0xffffffff if kind in ['fault','binding'] else 0xfffffffd)
 assert before==c.get(P,86) and c.get(SW+16,4)==bytes(4)
print(dict(runs=runs,post_opening_fault=True,rejections=5,calls=calls))
