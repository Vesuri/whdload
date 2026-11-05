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


shadow=0x330000;refstate=0x331000;packet=0x332000
c.put(0x370000,c.get(h[0]+0x5756,0x24)+bytes.fromhex('4e75'))

cases=0
for rate in [3,50,60]:
 for pitch in range(256):
  for rem in [-rate+1,-1,0,1,rate-1]:
   b=bytearray(rng.randbytes(86));b[54]=pitch;c.put(p,b);c.rw(6,p);c.rw(8,0x8f000);c.call(0x370000);expected=c.get(p,86)
   c.put(p,b);assert call('attitude_init',{1:shadow,9:rate,10:1})==0;c.put(shadow+8,struct.pack('>i',rem));before=c.get(shadow,12)
   wantrem=0 if expected[54]!=pitch or expected[54]==244 and rem<0 or expected[54]==20 and rem>0 else rem
   assert call('attitude_pitch_clamp',{1:shadow,2:p})==0
   assert c.get(p,86)==expected and c.get(shadow,8)==before[:8] and c.get(shadow+8,4)==struct.pack('>i',wantrem)
   # Applying it again at the same state must be idempotent.
   after=c.get(p,86),c.get(shadow,12)
   assert call('attitude_pitch_clamp',{1:shadow,2:p})==0
   assert after==(c.get(p,86),c.get(shadow,12));cases+=1
bad=0
for rate,rem in [(49,0),(50,50),(50,-50),(60,2147483647),(60,-2147483648)]:
 c.put(shadow,struct.pack('>HHii',rate,0,0,rem));before=c.get(p,86),c.get(shadow,12)
 assert call('attitude_pitch_clamp',{1:shadow,2:p})==0xffffffff
 assert before==(c.get(p,86),c.get(shadow,12));bad+=1
r=dict(native_clamp_fraction_cases=cases,invalid_cases=bad,calls=calls)
(root/'tmp/c/pitch-clamp-tests.json').write_text(json.dumps(r,indent=2)+'\n');print(r);c.close()
