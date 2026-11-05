#!/usr/bin/env python3
"""Connect scaled response/linear rates to native stages; prove h=1 and fractions."""
import json,random
from fractions import Fraction as F
from unicorn_b import *
from layout import locate
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks']
c=CPU();c.put(0x200000,mem);c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/player-delay.hunk')).get_segments()[0].get_data()))
listing=(root/'tmp/c/player-delay.lst').read_text()
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
  if r==9 or r==10 and name in ['fraction_add_rate','control_delay_step']:continue
  assert c.rr(r)==v,(name,r)
 return c.rr(9)
def long(off):return struct.unpack('>i',c.get(state+off,4))[0]
def qvalue(off,rate,conversion=None):return F(long(off),32767)+(F(long(conversion),rate*32767) if conversion else 0)
assert call('motion_preview_prepare',{1:h[0],2:whole})==0
assert call('motion_stages_prepare',{1:h[0],2:stages})==0
fixtures=json.loads((root/'tmp/c/player-motion-fixtures.json').read_text())


delaystate=0x370000;shadow=0x380000;packet=0x390000;other=0x3a0000;otherplayer=0x3b0000
samples=0
for rate in [3,50,60]:
 for seed in [-1,0,1]:
  assert call('control_delay_init',{1:delaystate,9:rate,10:seed&0xffffffff})==0
  history=[seed]*((rate+2)//3)
  for i in range(120):
   field=(0xfffffff0+i)&0xffffffff;y=rng.randrange(-1,2)
   got=call('control_delay_step',{1:delaystate,9:field,10:y&0xffffffff})
   assert c.rr(10)==0 and got==history.pop(0)&0xffffffff,(rate,seed,i)
   history.append(y);samples+=1
   before=c.get(delaystate,32)
   for wrong in [field,(field+2)&0xffffffff]:
    assert call('control_delay_step',{1:delaystate,9:wrong,10:0})==0 and c.rr(10)==0xffffffff
    assert c.get(delaystate,32)==before
# Whole-tick delay wrapper equals direct player entry, including previous y.
b=bytearray(86);struct.pack_into('>HH',b,0,0x7000,0x8000);struct.pack_into('>H',b,28,1024);b[27]=128;b[57]=30;b[66]=28
for a in [p,otherplayer]:c.put(a,b)
for a in [shadow,other]:assert call('player_step_init',{1:a,9:3,10:0})==0
assert call('control_delay_init',{1:delaystate,9:3,10:0})==0
for i in range(32):
 x,y=[rng.randrange(-1,2) for _ in range(2)];c.put(packet,struct.pack('>hhhhh',x,y,0,0,0))
 for a in [p,otherplayer]:c.put(a+12,struct.pack('>H',i))
 assert call('player_step_delayed',{1:shadow,2:p,3:stages,4:h[0]+0x7a44,5:packet,6:delaystate,9:i})==0
 assert call('player_step',{1:other,2:otherplayer,3:stages,4:h[0]+0x7a44,5:packet})==0
 assert c.get(p,86)==c.get(otherplayer,86) and c.get(shadow,76)==c.get(other,76)
# Failures after private history advance must publish none of the three states.
for failure in ['packet','late','rate','duplicate']:
 c.put(p,b);assert call('player_step_init',{1:shadow,9:50,10:0})==0
 assert call('control_delay_init',{1:delaystate,9:60 if failure=='rate' else 50,10:0})==0
 c.put(packet,struct.pack('>hhhhh',2 if failure=='packet' else 1,1,0,0,0))
 if failure=='late':c.put(shadow+20,struct.pack('>i',32767))
 if failure=='duplicate':assert call('player_step_delayed',{1:shadow,2:p,3:stages,4:h[0]+0x7a44,5:packet,6:delaystate,9:1})==0
 before=c.get(p,86),c.get(shadow,76),c.get(delaystate,32)
 assert call('player_step_delayed',{1:shadow,2:p,3:stages,4:h[0]+0x7a44,5:packet,6:delaystate,9:1})==0xffffffff
 assert before==(c.get(p,86),c.get(shadow,76),c.get(delaystate,32))
for rate in [50,60]:
 c.put(p,b);assert call('player_step_init',{1:shadow,9:rate,10:0})==0
 assert call('control_delay_init',{1:delaystate,9:rate,10:0})==0
 c.put(packet,struct.pack('>hhhhh',0,1,0,0,0))
 assert call('player_step_delayed',{1:shadow,2:p,3:stages,4:h[0]+0x7a44,5:packet,6:delaystate,9:1})==0
 assert sb(c.get(p+54,1)[0])*rate+int.from_bytes(c.get(shadow+8,4),'big',signed=True)==-3
print(dict(history_samples=samples,stamp_rejections=2*samples,whole_tick_comparisons=32,rollback_cases=4,first_field_responses=2,calls=calls))
