"""Composed native post-motion world sequence; modal interpreter and UI excluded."""
import json,random
from unicorn_b import *
from layout import locate
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks'];p=h[6]+0x3b88
c=CPU();c.put(0x200000,mem);c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/modal.hunk')).get_segments()[0].get_data()))
listing=(root/'tmp/c/modal.lst').read_text()
def sym(n):return base+int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
clone=0x330000;rc=0x340000;record=0x350000;fire=0x360000;rng=random.Random(0x979c);calls=0
# Target fixture selects slot 5. Actor updates, allocation, launch, recoil and
# resource accounting remain native; notification/UI/audio endpoints are stubs.
c.put(h[0]+0xc654,bytes.fromhex('70054e75'))
for off in [0xa150,0xaf36,0xb4e4,0xb57c]:c.put(h[0]+off,bytes.fromhex('4e75'))
def call(name,args):
 global calls
 regs={r:rng.randrange(0x1000000) for r in range(1,17) if r not in [8,9]};regs.update(args)
 for r,v in regs.items():c.rw(r,v)
 c.rw(8,0x8f000);c.call(sym(name));calls+=1
 assert c.rr(18)==0x90000 and c.rr(8)==0x8f004,(name,hex(c.rr(18)))
 assert all(c.rr(r)==v for r,v in regs.items() if r!=9),name
 return c.rr(9)


hit=0x370000
for off in [0x7fa4,0xb0a6]:c.put(h[0]+off,bytes.fromhex('70004e75') if off==0x7fa4 else bytes.fromhex('4e75'))
assert call('world_rng_prepare',{1:h[0]+0x7a5c,2:rc,3:record,4:h[2]})==0
assert call('world_hit_prepare',{1:h[0],2:hit,3:rc})==0
assert call('world_script_prepare',{1:h[0],2:clone,3:rc,4:hit,5:h[6]})==0
weapons=0x380000;damage=0x390000;effects=0x3a0000;heading=0x3b0000
reserves=0x3c0000;periodic=0x3d0000;cleanup=0x3e0000;ctx=0x3f0000
assert call('world_effect_prepare',{1:h[0],2:effects,3:rc,4:heading})==0
assert call('world_weapons_prepare',{1:h[0],2:weapons,3:rc,4:fire,5:h[6]})==0
assert call('world_damage_prepare',{1:h[0],2:damage,3:rc,4:effects,5:hit,6:h[6]})==0
assert call('world_reserves_prepare',{1:h[0],2:reserves})==0
assert call('world_periodic_prepare',{1:h[0],2:periodic,3:rc,4:h[6]})==0
assert call('world_cleanup_prepare',{1:h[0],2:cleanup,3:h[4]})==0
c.put(ctx,struct.pack('>7IH',p,weapons,damage,clone,reserves,periodic,cleanup,0))
c.put(h[0]+0xb2e0,bytes.fromhex('4e75'))
low=0x97ee00;length=0x21200;initial=c.get(low,length)
# Execute the native interpreter, fixture only its external UI and field arrival.
T=0x400000;H=0x410000;Q=0x420000;S=0x430000;TM=0x440000
c.put(h[0]+0x496e,bytes.fromhex('4e75'))
for off in (0x46de,0x487c):c.put(h[0]+off,bytes.fromhex('4e75'))
c.put(h[0]+0x3526,bytes.fromhex('700d4e75'))
initial=c.get(low,length)
CODE=C.CFUNCTYPE(None,C.c_void_p,C.c_uint64,C.c_uint32,C.c_void_p)
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
trace=[];break_binding=False
@CODE
def hook(handle,a,n,user):
 trace.append(a-h[0])
 if break_binding and a==h[0]+0x8050:c.put(clone+sym('SC_PLAYER')-base,struct.pack('>I',p+2))
 if a==h[0]+0x8188:
  # A real VBL advances this counter during the native blocking wait.
  c.put(h[2]+0x1c,struct.pack('>I',int.from_bytes(c.get(h[2]+0x1c,4),'big')+1))
hooks=[]
for off in (0x8050,0x8188,0xb4e4,0x496e,0x7d92):
 hh=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hh),1<<2,hook,None,h[0]+off,h[0]+off));hooks.append(hh)
def w(a):return int.from_bytes(c.get(a,2),'big')
def l(a):return int.from_bytes(c.get(a,4),'big')
def pw(a,v):c.put(a,struct.pack('>H',v))
def snapshot():return [c.get(a,n) for a,n in [(low,length),(ctx,30),(T,28),(H,5140),(Q,1048),(S,48),(TM,14)]]
def reject(name,status=0xfffffffd):
 before=snapshot();assert call(name,{1:TM})==status;assert snapshot()==before
results=[]
for rate in (50,60):
 for variant in range(20):
  state=variant%5+1;ended=(variant//5)%2;prompt=variant//10
  final=[];traces=[]
  for wrapped in (False,True):
   c.put(low,initial);c.put(p,struct.pack('>HH',0x7000,0x8000));c.put(p+24,bytes([ended]));c.put(p+12,struct.pack('>H',16 if ended else 17));c.put(p+28,struct.pack('>H',1024));c.put(p+83,bytes([state,1]))
   c.put(h[4]+0x1c6,bytes([1-prompt]));c.put(h[4]+0x1c5,b'\2');c.put(h[2]+0x10,bytes(4));c.put(h[2]+0x1c,bytes(4));pw(ctx+28,1)
   assert call('clock_init',{1:T,9:17,10:rate})==0
   assert call('history_init',{1:H,9:17})==0
   assert call('commands_init',{1:Q,9:0})==0
   assert call('scheduler_init',{1:S,2:T,3:H,4:Q})==0
   pw(S+12,2);pw(S+14,1);pw(S+18,3)
   assert call('timing_modal_prepare',{1:TM,2:S,3:ctx,4:h[0]})==0
   trace.clear()
   if wrapped:
    reject('timing_modal_run')
    assert call('timing_modal_suspend',{1:TM})==0
    assert w(T+24)==w(H+4)==w(Q+6)==0 and w(S+12)==2 and w(TM+12)==1
    reject('timing_modal_suspend')
    if variant==0 and rate==50:
     for addr,value in ((S+12,1),(S+14,0),(ctx+28,2)):
      saved=c.get(addr,2);pw(addr,value);reject('timing_modal_run');c.put(addr,saved)
     for addr,value in ((p+83,0),(p+84,2)):
      saved=c.get(addr,1);c.put(addr,bytes([value]));reject('timing_modal_run');c.put(addr,saved)
     for clonebase,offset in ((weapons,'WW_CODE_SIZE'),(damage,'WD_CODE_SIZE'),(clone,'SC_PLAYER'),(periodic,'WP_CODE_SIZE')):
      addr=clonebase+sym(offset)-base;saved=c.get(addr,4);c.put(addr,struct.pack('>I',p+2));reject('timing_modal_run',0xffffffff);c.put(addr,saved)
    for addr in (T+24,H+4,Q+6):
     pw(addr,1);reject('timing_modal_run');pw(addr,0)
    got=call('timing_modal_run',{1:TM})
    assert got==(3 if ended else 0),got
    assert l(S+36)==1 and w(S+12)==0 and w(S+22)==1
    assert w(TM+12)==(5 if got==3 else 4)
    assert w(T+24)==w(H+4)==w(Q+6)==0
    reject('timing_modal_run');reject('timing_modal_suspend')
   else:
    c.rw(6,p);c.rw(8,0x8f000);c.call(h[0]+0x8050);assert c.rr(18)==0x90000
    got=call('world_body_resume',{1:ctx})
   final.append((c.get(low,length),c.get(ctx,30),got));traces.append(list(trace))
  assert final[0]==final[1],(rate,state,'state')
  assert traces[0]==traces[1],(rate,state,traces)
  assert traces[1].count(0x8050)==1
  results.append(dict(rate=rate,state=state,prompt=prompt,ended=ended,result=final[1][2],field_waits=traces[1].count(0x8188)))
# Failure after interpreter entry retains progress and never retries the interpreter.
c.put(low,initial);c.put(p+83,bytes([2,1]));c.put(h[2]+0x10,bytes(4));c.put(h[2]+0x1c,bytes(4));pw(ctx+28,1)
assert call('clock_init',{1:T,9:0,10:50})==0
assert call('history_init',{1:H,9:0})==0
assert call('commands_init',{1:Q,9:0})==0
assert call('scheduler_init',{1:S,2:T,3:H,4:Q})==0
pw(S+12,2);pw(S+14,1);pw(S+18,3)
assert call('timing_modal_prepare',{1:TM,2:S,3:ctx,4:h[0]})==0
assert call('timing_modal_suspend',{1:TM})==0
break_binding=True;trace.clear()
assert call('timing_modal_run',{1:TM})==0xffffffff
break_binding=False
assert w(TM+12)==3 and w(S+12)==2 and l(S+36)==0 and trace.count(0x8050)==1
reject('timing_modal_run');assert trace.count(0x8050)==1
c.put(clone+sym('SC_PLAYER')-base,struct.pack('>I',p))
# Reject changed interpreter bytes without overwriting prepared state.
before=c.get(TM,14);native=c.get(h[0]+0x8050,16)
for off in (0,4,8,12):
 c.put(h[0]+0x8050+off,b'\0\0\0\0');assert call('timing_modal_prepare',{1:TM,2:S,3:ctx,4:h[0]})==0xffffffff;assert c.get(TM,14)==before;c.put(h[0]+0x8050,native)
print(json.dumps(dict(status='passed',calls=calls,runs=results)));c.close()
