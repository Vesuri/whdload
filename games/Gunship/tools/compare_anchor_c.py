from unicorn_b import *
import os,hashlib
trace=hashlib.sha256()
from layout import locate
from functools import lru_cache
import json
listing=(build/(os.environ['COMPARE_SLAVE']+'.lst')).read_text(encoding='latin1')
@lru_cache(None)
def sym(n):return int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
c=CPU();c.put(base,bytes(BinFmt().load_image(str(build/os.environ['COMPARE_SLAVE'])).get_segments()[0].get_data()));mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks'];c.put(0x200000,mem)
STAGES=0x310000;PS=[0x320000,0x321000];EP=[0x330000,0x331000];PACKET=0x340000;CACHE=0x350000
count=0
@C.CFUNCTYPE(None,C.c_void_p,C.c_uint64,C.c_uint32,C.c_void_p)
def entered(*args):
 global count
 count+=1
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
hook=C.c_size_t();entry=base+sym('player_step_interval');ok(u.uc_hook_add(c.h,C.byref(hook),1<<2,entered,None,entry,entry))
def call(name,args,expected=0):
 regs={r:0x4000+r for r in list(range(1,8))+list(range(10,17))};regs.update(args)
 for r,v in regs.items():c.rw(r,v)
 c.rw(8,0x8f000);c.call(base+sym(name));assert c.rr(18)==0x90000 and c.rr(9)==expected,(name,c.rr(9))
 assert all(c.rr(r)==v for r,v in regs.items() if r!=9)
call('motion_stages_prepare',{1:h[0],2:STAGES})
fields=0;native_calls=0;cached_calls=0;rejects=0
for rate in [50,60]:
 for config in [0,1,2,3]:
  c.put(CACHE,bytes(sym('PC_PLAYER')+86));p=bytearray(86);struct.pack_into('>HH',p,0,0x7000,0x8000);struct.pack_into('>H',p,28,1024);p[16]=config;p[27]=128;p[57]=30;p[66]=28
  for ep,ps in zip(EP,PS):
   c.put(ps,p);call('endpoint_player_init',{1:ep,9:rate,10:0})
  last=0
  for field in range(1,rate*4+1):
   interval=(field-1)*3//rate+1
   if interval!=last:
    span=(interval*rate+2)//3-((interval-1)*rate+2)//3
    for ep,ps in zip(EP,PS):call('endpoint_player_begin',{1:ep,2:ps,9:span,10:interval})
    last=interval
   # Short pulses and command changes between world boundaries.
   x=1 if field%41 in range(5,10) else -1 if field%59 in range(19,24) else 0
   y=-1 if field%47 in range(6,13) else 0
   due=field*3//rate>(field-1)*3//rate
   packet=struct.pack('>hhhhh',x,y,4 if due and interval%3==0 else 0,-1 if due and interval%4==0 else 0,2 if due and interval%5==0 else 0);c.put(PACKET,packet)
   if field%37==0:
    for ps in PS:c.put(ps+57,bytes([20+field%20]))
   for idx,name in enumerate(['endpoint_player_step','endpoint_player_step_cached']):
    args={1:EP[idx],2:PS[idx],3:STAGES,4:h[0]+0x7a44,5:PACKET,6:CACHE,9:field}
    before=count;call(name,args)
    if idx:cached_calls+=count-before
    else:native_calls+=count-before
   assert c.get(PS[0],86)==c.get(PS[1],86),(rate,config,field,'player')
   assert c.get(EP[0],sym('EP_SIZE'))==c.get(EP[1],sym('EP_SIZE')),(rate,config,field,'state')
   assert c.get(PACKET,10)==packet
   if field%31==0:
    before=(c.get(EP[1],sym('EP_SIZE')),c.get(PS[1],86));call('endpoint_player_step_cached',{1:EP[1],2:PS[1],3:STAGES,4:h[0]+0x7a44,5:PACKET,6:CACHE,9:field},0xffffffff)
    assert before==(c.get(EP[1],sym('EP_SIZE')),c.get(PS[1],86));rejects+=1
   trace.update(c.get(PS[0],86));trace.update(c.get(EP[0],sym('EP_SIZE')))
   fields+=1
report=dict(trace_sha256=trace.hexdigest(),fields=fields,native_calls=native_calls,cached_calls=cached_calls,avoided=native_calls-cached_calls,duplicate_field_rejects=rejects,all_player_and_owner_bytes_equal=True)
(root/'tmp/c/endpoint-cache-test.json').write_text(json.dumps(report,indent=2)+'\n');print(report);c.close()
