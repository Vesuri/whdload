#!/usr/bin/env python3
"""Connect scaled response/linear rates to native stages; prove h=1 and fractions."""
import json,random
from fractions import Fraction as F
from unicorn_b import *
from layout import locate
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks']
c=CPU();c.put(0x200000,mem);c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/player-step.hunk')).get_segments()[0].get_data()))
listing=(root/'tmp/c/player-step.lst').read_text()
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


state=0x330000;packet=0x350000
cases=0
for rate in [50,60]:
 for pitch in range(-128,128):
  for y in [-1,0,1]:
   for previous in [-1,0,1]:
    for remainder in [1-rate,0,rate-1]:
     c.put(p,bytes(86));c.put(p+54,bytes([pitch&255]));c.put(packet,struct.pack('>hhhhh',0,y,0,0,0))
     assert call('attitude_init',{1:state,9:rate,10:previous&0xffffffff})==0
     c.put(state+8,struct.pack('>i',remainder))
     delta=-(y+previous) if y else 0
     lower=-12*rate+min(delta,0)*(rate-3);upper=20*rate+max(delta,0)*(rate-3)
     old=pitch*rate+remainder;expected=max(lower,min(upper,old))
     assert call('attitude_pitch_clamp_control',{1:state,2:p,3:packet})==0
     actual=sb(c.get(p+54,1)[0])*rate+int.from_bytes(c.get(state+8,4),'big',signed=True)
     assert actual==expected,(rate,pitch,y,previous,remainder,actual,expected)
     if lower<=old<=upper:assert c.get(p+54,1)==bytes([pitch&255]) and c.get(state+8,4)==struct.pack('>i',remainder)
     cases+=1
# Whole-tick byte wrap/BMI behavior stays exactly the legacy clamp.
for pitch in range(256):
 c.put(p+54,bytes([pitch]));assert call('attitude_init',{1:state,9:3,10:0})==0
 assert call('attitude_pitch_clamp',{1:state,2:p})==0
 expected=c.get(p+54,1),c.get(state,12)
 c.put(p+54,bytes([pitch]));assert call('attitude_init',{1:state,9:3,10:0})==0
 assert call('attitude_pitch_clamp_control',{1:state,2:p,3:packet})==0
 assert expected==(c.get(p+54,1),c.get(state,12))
print(dict(field_models=cases,native_clamp_cases=256,calls=calls))
