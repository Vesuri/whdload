#!/usr/bin/env python3
"""Connect scaled response/linear rates to native stages; prove h=1 and fractions."""
import json,random
from fractions import Fraction as F
from unicorn_b import *
from layout import locate
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks']
c=CPU();c.put(0x200000,mem);c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/field-pipeline.hunk')).get_segments()[0].get_data()))
listing=(root/'tmp/c/field-pipeline.lst').read_text()
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
runs=[]
def word(a):return int.from_bytes(c.get(a,2),'big')
for rate in [50,60]:
 baseline=None
 for batch in [1,3,10,25]:
  assert call('clock_init',{1:TC,9:0,10:rate})==0
  assert call('history_init',{1:TH,9:0})==0
  assert call('commands_init',{1:CQ,9:0})==0
  assert call('scheduler_init',{1:TS,2:TC,3:TH,4:CQ})==0
  assert call('player_step_init',{1:shadow,9:rate,10:0})==0
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
    assert call('player_step_interval',{1:shadow,2:p,3:stages,4:h[0]+0x7a44,5:packet,9:(tick+1)&65535})==0
    assert word(p+12)==tick
    completed+=1;poses.append((c.get(p,86),c.get(shadow,76)))
    due=call('scheduler_player_done',{1:TS});assert due in [0,1]
    if due:
     assert call('scheduler_next',{1:TS,2:sample})==0xfffffffd
     assert word(TS+44)==edges
     tick=(tick+1)&65535;c.put(p+12,struct.pack('>H',tick))
     # Observer substitutes for world effects; not a native-world test.
     worlds.append((completed,c.get(p,86),word(TS+44),int.from_bytes(c.get(TS+40,4),'big'),c.get(rec+32,8)))
     assert call('scheduler_world_done',{1:TS})==0;edges=0
   before=c.get(p,86),c.get(shadow,76)
   assert call('player_camera_angles',{1:p,2:shadow,3:camera})==0
   assert before==(c.get(p,86),c.get(shadow,76))
  result=(poses,worlds,c.get(p,86),c.get(shadow,76),c.get(camera+6,6))
  if baseline is None:baseline=result
  else:assert result==baseline,(rate,batch)
  assert completed==240 and len(worlds)==240*3//rate
  assert int.from_bytes(c.get(TS+32,4),'big')==240 and int.from_bytes(c.get(TS+36,4),'big')==len(worlds)
  runs.append(dict(rate=rate,batch=batch,fields=completed,world_observations=len(worlds),clock=tick))
# Compare interval override directly with the ordinary player entry point.
parity_cases=0
for rate in [3,50,60]:
 for original_tick in [0,42,65535]:
  for interval in [0,1,65535]:
   b=bytearray(86);struct.pack_into('>H',b,28,1023);struct.pack_into('>H',b,12,original_tick);b[16]=2;b[27]=128;b[57]=26;b[62]=254;b[66]=28
   c.put(p,b);c.put(out,b);c.put(out+12,struct.pack('>H',interval));c.put(packet,bytes(10))
   assert call('player_step_init',{1:shadow,9:rate,10:0})==0
   assert call('player_step_init',{1:0x40b000,9:rate,10:0})==0
   assert call('player_step',{1:0x40b000,2:out,3:stages,4:h[0]+0x7a44,5:packet})==0
   c.put(out+12,struct.pack('>H',original_tick))
   assert call('player_step_interval',{1:shadow,2:p,3:stages,4:h[0]+0x7a44,5:packet,9:interval})==0
   assert c.get(p,86)==c.get(out,86) and c.get(shadow,76)==c.get(0x40b000,76)
   parity_cases+=1
# Interval overflow and late invalid input must preserve clock, player and shadow.
for interval,raw in [(65536,bytes(10)),(0xffffffff,bytes(10)),(1,struct.pack('>hhhhh',1,1,0,0,3))]:
 c.put(packet,raw);before=c.get(p,86),c.get(shadow,76)
 assert call('player_step_interval',{1:shadow,2:p,3:stages,4:h[0]+0x7a44,5:packet,9:interval})==0xffffffff
 assert before==(c.get(p,86),c.get(shadow,76))
r=dict(parity_cases=parity_cases,runs=runs,calls=calls,scope='history/scheduler/player/camera composition, world observer only; no native commands/world effects or live interrupts')
(root/'tmp/c/field-pipeline-tests.json').write_text(json.dumps(r,indent=2)+'\n');print(r);c.close()
