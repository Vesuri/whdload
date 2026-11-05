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


shadow=0x330000;candidate=0x340000
cases=0
for rate in [50,60]:
 for pitch in [-5,-4,-3,-1,0,1,2]:
  for fraction in [1-rate,-1,0,1,rate-1]:
   for roll in [-1,0,1]:
    b=bytearray(86);struct.pack_into('>H',b,28,1024);b[27]=128;b[57]=30;b[66]=28;b[53]=11;b[61]=23;b[54]=pitch&255;b[55]=roll&255;b[63]=2
    c.put(p,b);assert call('kinematics_init',{1:shadow,9:rate})==0
    before=c.get(p,86),c.get(shadow,64)
    assert call('kinematics_prepare_fractional',{1:shadow,2:p,3:stages,4:h[0]+0x7a44,5:candidate,9:0,10:fraction&0xffffffff})==0
    assert before==(c.get(p,86),c.get(shadow,64))
    private=c.get(candidate+64,86)
    assert private[54]==b[54],('pitch leak',rate,pitch,fraction)
    hover=-4*rate<pitch*rate+fraction<=0
    assert private[63]==(2 if hover else 0),(rate,pitch,fraction,hover,private[63])
    if hover:
     def angle(byte,main,conv):return F(private[byte])+F(int.from_bytes(c.get(candidate+main,4),'big',signed=True),32767)+F(int.from_bytes(c.get(candidate+conv,4),'big',signed=True),rate*32767)
     heading=angle(53,28,32);track=angle(61,36,40)
     assert (heading-11)%256==F(12,rate)
     assert (track-heading)%256==({-1:192,0:0,1:64}[roll])
    cases+=1
for rate,fraction in [(50,50),(50,-50),(60,60),(60,-60),(3,1)]:
 assert call('kinematics_init',{1:shadow,9:rate})==0
 before=c.get(p,86),c.get(shadow,64)
 assert call('kinematics_prepare_fractional',{1:shadow,2:p,3:stages,4:h[0]+0x7a44,5:candidate,9:0,10:fraction&0xffffffff})==0xffffffff
 assert before==(c.get(p,86),c.get(shadow,64)) and c.get(candidate+172,2)==bytes(2)
print(dict(branch_cases=cases,invalid_fraction_cases=5,calls=calls))
