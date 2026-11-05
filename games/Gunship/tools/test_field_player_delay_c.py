#!/usr/bin/env python3
"""Connect scaled response/linear rates to native stages; prove h=1 and fractions."""
import json,random
from fractions import Fraction as F
from unicorn_b import *
from layout import locate
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks']
c=CPU();c.put(0x200000,mem);c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/field-player.hunk')).get_segments()[0].get_data()))
listing=(root/'tmp/c/field-player.lst').read_text()
def sym(n):return int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
whole=0x300000;stages=0x310000;p=0x320000;out=0x320100;terms=0x320200;state=0x320300;rng=random.Random(9636);calls=0
trunc=lambda n,d:-(abs(n)//d) if n<0 else n//d
signed=lambda n:n-2**32 if n&2**31 else n
sb=lambda n:(n&255)-256 if n&128 else n&255
sw=lambda n:(n&65535)-65536 if n&32768 else n&65535
def call(name,ptrs):
 global calls
 regs={r:rng.randrange(0x1000000) for r in range(1,17) if r!=8};regs.update(ptrs)
 for r,v in regs.items():c.rw(r,v)
 c.rw(8,0x8f000);c.call(base+sym(name));calls+=1
 assert c.rr(18)==0x90000 and c.rr(8)==0x8f004
 for r,v in regs.items():
  if r==9 or r==10 and name=='fraction_add_rate':continue
  assert c.rr(r)==v,(name,r)
 return c.rr(9)
def long(off):return struct.unpack('>i',c.get(state+off,4))[0]
def qvalue(off,rate,conversion=None):return F(long(off),32767)+(F(long(conversion),rate*32767) if conversion else 0)
assert call('motion_preview_prepare',{1:h[0],2:whole})==0
assert call('motion_stages_prepare',{1:h[0],2:stages})==0
fixtures=json.loads((root/'tmp/c/player-motion-fixtures.json').read_text())



TS=0x400000;TC=0x401000;TH=0x402000;CQ=0x404000;rec=0x405000;sample=0x406000;shadow=0x408000;packet=0x409000;camera=0x40a000
context=0x420000;candidate=0x421000;delay=0x422000
runs=[]
def word(a):return int.from_bytes(c.get(a,2),'big')
for rate in ([] if os.environ.get('GS_QUICK') else [50,60]):
 baseline=None
 for batch in [1,3,10,25]:
  assert call('clock_init',{1:TC,9:0,10:rate})==0
  assert call('history_init',{1:TH,9:0})==0
  assert call('commands_init',{1:CQ,9:0})==0
  assert call('scheduler_init',{1:TS,2:TC,3:TH,4:CQ})==0
  assert call('player_step_init',{1:shadow,9:rate,10:0})==0
  assert call('control_delay_init',{1:delay,9:rate,10:0})==0
  c.put(context,struct.pack('>6I',shadow,p,stages,h[0]+0x7a44,packet,candidate)+bytes(16)+struct.pack('>I',delay))
  b=bytearray(86);struct.pack_into('>HH',b,0,0x7000,0x8000);struct.pack_into('>H',b,28,1024);struct.pack_into('>H',b,12,65532);b[27]=128;b[57]=26;b[66]=28;c.put(p,b)
  tick=65532;completed=0;worlds=[];poses=[];lastheld=0;edges=0
  for first in range(1,241,batch):
   for f in range(first,min(first+batch,241)):
    x=[1,0,-1,0][(f//15)%4];y=[0,1,0,-1][(f//20)%4];held=(f//7)%4;edge=held&~lastheld;lastheld=held
    raw=struct.pack('>6IHhhHII',f,0xffff0000|(x&255),0x12340000|(y&255),held,0,0,8,77,-91,edge,123+f//50,f*17003%1000000)
    c.put(sample,raw);assert call('history_publish',{1:TH,2:sample})==1
   assert call('scheduler_begin',{1:TS,9:128,10:8})==0
   while True:
    got=call('scheduler_next',{1:TS,2:rec})
    if got==0:break
    assert got==1
    sample_field=int.from_bytes(c.get(rec,4),'big')
    assert c.get(rec+32,8)==struct.pack('>II',123+sample_field//50,sample_field*17003%1000000)
    assert call('scheduler_next',{1:TS,2:sample})==0xfffffffd
    assert call('controls_from_history',{1:rec,2:packet})==0
    edges|=word(rec+30)
    before=c.get(p,86),c.get(shadow,76),c.get(delay,32)
    assert call('field_player_prepare_delayed',{1:context,2:TS,3:rec,9:(tick+1)&65535})==0
    assert before==(c.get(p,86),c.get(shadow,76),c.get(delay,32)) and word(context+38)==0
    assert call('scheduler_next',{1:TS,2:sample})==0xfffffffd
    due=call('field_player_complete',{1:context});assert due in [0,1]
    assert word(context+38)==1 and word(context+36)==0
    assert call('field_player_complete',{1:context})==0xfffffffd
    assert word(p+12)==tick
    assert int.from_bytes(c.get(delay+8,4),'big')==sample_field
    completed+=1;poses.append((c.get(p,86),c.get(shadow,76),c.get(delay,32)))
    assert word(TS+12)==(2 if due else 0)
    if due:
     assert call('scheduler_next',{1:TS,2:sample})==0xfffffffd
     assert word(TS+44)==edges
     tick=(tick+1)&65535;c.put(p+12,struct.pack('>H',tick))
     # Observer substitutes for world effects; not a native-world test.
     worlds.append((completed,c.get(p,86),word(TS+44),int.from_bytes(c.get(TS+40,4),'big'),c.get(rec+32,8)))
     assert call('scheduler_world_done',{1:TS})==0;edges=0
   before=c.get(p,86),c.get(shadow,76),c.get(delay,32)
   assert call('player_camera_angles',{1:p,2:shadow,3:camera})==0
   assert before==(c.get(p,86),c.get(shadow,76),c.get(delay,32))
  result=(poses,worlds,c.get(p,86),c.get(shadow,76),c.get(delay,32),c.get(camera+6,6))
  if baseline is None:baseline=result
  else:assert result==baseline,(rate,batch)
  assert completed==240 and len(worlds)==240*3//rate
  assert int.from_bytes(c.get(TS+32,4),'big')==240 and int.from_bytes(c.get(TS+36,4),'big')==len(worlds)
  runs.append(dict(rate=rate,batch=batch,fields=completed,world_observations=len(worlds),clock=tick))
def ready():
 assert call('clock_init',{1:TC,9:0,10:50})==0
 assert call('history_init',{1:TH,9:0})==0
 assert call('commands_init',{1:CQ,9:0})==0
 assert call('scheduler_init',{1:TS,2:TC,3:TH,4:CQ})==0
 assert call('player_step_init',{1:shadow,9:50,10:0})==0
 assert call('control_delay_init',{1:delay,9:50,10:0})==0
 c.put(context,struct.pack('>6I',shadow,p,stages,h[0]+0x7a44,packet,candidate)+bytes(16)+struct.pack('>I',delay))
 b=bytearray(86);struct.pack_into('>H',b,28,1024);b[27]=128;b[57]=26;b[66]=28;c.put(p,b)
 c.put(sample,struct.pack('>10I',1,1,0,0,0,0,0,0,0,0))
 assert call('history_publish',{1:TH,2:sample})==1
 assert call('scheduler_begin',{1:TS,9:128,10:8})==0
 assert call('scheduler_next',{1:TS,2:rec})==1
 assert call('controls_from_history',{1:rec,2:packet})==0
failures=0
for kind in ['wrong-field','wrong-command','wrong-rate','invalid-control','invalid-interval']:
 ready();before=c.get(p,86),c.get(shadow,76),c.get(delay,32)
 if kind=='wrong-field':c.put(rec,struct.pack('>I',2))
 if kind=='wrong-command':c.put(rec+20,struct.pack('>I',1))
 if kind=='wrong-rate':c.put(TC+22,struct.pack('>H',60))
 if kind=='invalid-control':c.put(packet,struct.pack('>h',2))
 result=call('field_player_prepare_delayed',{1:context,2:TS,3:rec,9:65536 if kind=='invalid-interval' else 1})
 assert result==(0xfffffffd if kind in ['wrong-field','wrong-command','wrong-rate'] else 0xffffffff),kind
 assert before==(c.get(p,86),c.get(shadow,76),c.get(delay,32)) and word(TS+12)==1 and c.get(TS+32,4)==bytes(4)
 failures+=1
for kind in ['upstream-fault','changed-binding','late-fraction','changed-history']:
 ready();before=c.get(p,86),c.get(shadow,76),c.get(delay,32)
 assert call('field_player_prepare_delayed',{1:context,2:TS,3:rec,9:1})==0
 if kind=='upstream-fault':c.put(TH+6,struct.pack('>H',1))
 if kind=='changed-binding':c.put(TS+28,struct.pack('>I',1))
 if kind=='late-fraction':c.put(candidate+20,struct.pack('>i',32767))
 if kind=='changed-history':c.put(delay+20,b'\x01');before=c.get(p,86),c.get(shadow,76),c.get(delay,32)
 result=call('field_player_complete',{1:context})
 assert result==(0xfffffffd if kind=='changed-binding' else 0xffffffff),kind
 assert before==(c.get(p,86),c.get(shadow,76),c.get(delay,32)) and word(TS+12)==1 and c.get(TS+32,4)==bytes(4)
 assert word(context+36)==0 and word(context+38)==0 and word(candidate+184)==0
 failures+=1
# Retained lifecycle and ordinary commands block motion; future commands do not.
for key,cutoff in [(0x45,1),(0x51,1),(0x45,0)]:
 ready()
 assert call('commands_publish',{1:CQ,9:1,10:key})==1
 c.put(TS+28,struct.pack('>I',cutoff));c.put(rec+20,struct.pack('>I',cutoff))
 before=c.get(p,86),c.get(shadow,76),c.get(delay,32),c.get(CQ,1048)
 result=call('field_player_prepare_delayed',{1:context,2:TS,3:rec,9:1})
 assert result==(0xfffffffd if cutoff else 0)
 assert before==(c.get(p,86),c.get(shadow,76),c.get(delay,32),c.get(CQ,1048))
 assert word(context+36)==(0 if cutoff else 2)
 failures+=1
# Fresh CPU: hooks added after a cached translation may not instrument it.
c.close();c=CPU();c.put(0x200000,mem)
c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/field-player.hunk')).get_segments()[0].get_data()))
assert call('motion_stages_prepare',{1:h[0],2:stages})==0
# Inject a producer fault after publication, at acknowledgement entry.
ready();before=c.get(p,86),c.get(shadow,76),c.get(delay,32)
assert call('field_player_prepare_delayed',{1:context,2:TS,3:rec,9:1})==0
CODE=C.CFUNCTYPE(None,C.c_void_p,C.c_uint64,C.c_uint32,C.c_void_p)
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
@CODE
def fault(handle,a,n,user):c.put(TH+6,struct.pack('>H',1))
hook=C.c_size_t();entry=base+sym('scheduler_player_done');ok(u.uc_hook_add(c.h,C.byref(hook),1<<2,fault,None,entry,entry))
result=call('field_player_complete',{1:context})
assert result==0xffffffff,(hex(result),word(TH+6),word(TS+22),word(context+38))
assert word(context+38)==1 and c.get(TS+32,4)==struct.pack('>I',1) and word(TS+22)==1
assert before!=(c.get(p,86),c.get(shadow,76),c.get(delay,32))
assert c.get(delay+8,4)==struct.pack('>I',1)
after=c.get(delay,32)
assert call('field_player_complete',{1:context})==0xfffffffd and c.get(delay,32)==after
r=dict(runs=runs,rejected_cases=failures,post_publication_fault=True,calls=calls,scope='scheduler binding and combined player boundary; world observer only, commands/impulse policy/world contact selection not installed')
(root/'tmp/c/field-player-delay-tests.json').write_text(json.dumps(r,indent=2)+'\n');print(r);c.close()
