#!/usr/bin/env python3
"""Connect scaled response/linear rates to native stages; prove h=1 and fractions."""
import json,random
from fractions import Fraction as F
from unicorn_b import *
from layout import locate
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks']
c=CPU();c.put(0x200000,mem);c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/scheduled-endpoint.hunk')).get_segments()[0].get_data()))
listing=(root/'tmp/c/scheduled-endpoint.lst').read_text()
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



TS=0x400000;TC=0x401000;TH=0x402000;CQ=0x404000;rec=0x405000;sample=0x406000;shadow=0x408000;packet=0x409000;context=0x420000
word=lambda a:int.from_bytes(c.get(a,2),'big')
GR=0x430000;EVENT=0x431000;COUNT=0x432000
c.put(h[0]+0xa150,bytes.fromhex('52b9')+struct.pack('>I',COUNT)+bytes.fromhex('4e75'))
assert call('ground_deferred_prepare',{1:h[0],2:GR,3:h[6],4:EVENT})==0
runs=[]
for rate in [50,60]:
 baseline=None
 for batch in [1,25]:
  assert call('clock_init',{1:TC,9:0,10:rate})==0
  assert call('history_init',{1:TH,9:0})==0
  assert call('commands_init',{1:CQ,9:0})==0
  assert call('scheduler_init',{1:TS,2:TC,3:TH,4:CQ})==0
  assert call('endpoint_player_init',{1:shadow,9:rate,10:0})==0
  c.put(context,struct.pack('>6I',shadow,p,stages,h[0]+0x7a44,packet,TS)+bytes(6)+struct.pack('>II',GR,EVENT))
  c.put(EVENT,bytes(4));c.put(COUNT,bytes(4));c.put(h[6]+0x42f6,bytes(1))
  b=bytearray(86);struct.pack_into('>HH',b,0,0x7000,0x8000);struct.pack_into('>H',b,28,1);struct.pack_into('>H',b,12,65532);b[27]=128;b[57]=26;b[66]=28;b[62]=236;b[16]=1;c.put(p,b)
  tick=65532;poses=[];worlds=[];spans=[]
  for first in range(1,241,batch):
   for f in range(first,min(first+batch,241)):
    x=[1,0,-1,0][(f//15)%4];y=[0,1,0,-1][(f//20)%4]
    c.put(sample,struct.pack('>6IHhhHII',f,x&255,y&255,0,0,0,8,0,0,0,0,0))
    assert call('history_publish',{1:TH,2:sample})==1
   assert call('scheduler_begin',{1:TS,9:128,10:8})==0
   while True:
    got=call('scheduler_next',{1:TS,2:rec})
    if got==0:break
    assert got==1
    assert call('controls_from_history',{1:rec,2:packet})==0
    if int.from_bytes(c.get(rec,4),'big')%7==0:c.put(p+63,b'\x02')
    yaw_before=c.get(p+63,1)
    due=call('scheduled_endpoint_ground_step',{1:context,2:rec,9:(tick+1)&65535})
    assert due in [0,1],(rate,batch,len(poses),hex(due))
    if not due:assert c.get(p+63,1)==yaw_before
    assert word(context+28)==1 and word(p+12)==tick
    poses.append((c.get(p,86),c.get(shadow,164)))
    assert call('scheduled_endpoint_ground_step',{1:context,2:rec,9:(tick+1)&65535})==0xfffffffd
    if word(shadow+160)==1:spans.append(word(shadow+158))
    if not due:assert c.get(EVENT,4)==bytes(4)
    if due:
     assert c.get(EVENT+3,1)==b'\x01'
     assert call('ground_deferred_commit',{1:EVENT,2:h[0]+0xa150,3:h[6]+0x42f6}) in [0,1]
     assert call('ground_deferred_commit',{1:EVENT,2:h[0]+0xa150,3:h[6]+0x42f6})==0xffffffff
     tick=(tick+1)&65535;c.put(p+12,struct.pack('>H',tick));worlds.append(len(poses))
     assert call('scheduler_world_done',{1:TS})==0
  result=(poses,worlds,spans,c.get(COUNT,4),c.get(h[6]+0x42f6,1))
  if baseline is None:baseline=result
  else:assert result==baseline,(rate,batch)
  assert len(poses)==240 and len(worlds)==240*3//rate
  assert all(n==([17,17,16][i%3] if rate==50 else 20) for i,n in enumerate(spans)),spans
  assert int.from_bytes(c.get(TS+32,4),'big')==240
  runs.append(dict(rate=rate,batch=batch,fields=len(poses),worlds=len(worlds),spans=spans,notifications=int.from_bytes(c.get(COUNT,4),'big')))
print(dict(runs=runs,calls=calls))
c.close()
