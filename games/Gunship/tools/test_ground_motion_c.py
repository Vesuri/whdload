#!/usr/bin/env python3
"""Connect scaled response/linear rates to native stages; prove h=1 and fractions."""
import json,random
from fractions import Fraction as F
from unicorn_b import *
from layout import locate
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks']
c=CPU();c.put(0x200000,mem);c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/ground-motion.hunk')).get_segments()[0].get_data()))
listing=(root/'tmp/c/ground-motion.lst').read_text()
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

ground=0x360000;counter=0x370000
c.put(h[0]+0xa150,bytes.fromhex('52b9')+struct.pack('>I',counter)+bytes.fromhex('4e75'))
assert call('ground_prepare',{1:h[0],2:ground,3:h[6]})==0
# Restore native ground block in the whole-motion reference BEFORE execution.
# Heading RNG remains excluded, identical to the continuous stage fixtures.
c.put(whole+0x224,c.get(h[0]+0x95a0,4))
resets=notifications=0
for n in range(4096):
 b=bytearray.fromhex(fixtures[n%len(fixtures)]['input'])
 struct.pack_into('>H',b,28,32767 if n%17==0 else n%5)
 if n%17==0:
  b[0x10]=1;b[0x18]=0;b[0x52]=0;b[0x3e]=100
  struct.pack_into('>h',b,0x2a,0)
 c.put(p,b);c.put(counter,bytes(4));c.put(h[6]+0x42f6,bytes(1))
 call('motion_preview',{1:p,2:out,3:whole,9:0})
 expected=(c.get(out,86),c.get(counter,4),c.get(h[6]+0x42f6,1))
 c.put(p,b);c.put(counter,bytes(4));c.put(h[6]+0x42f6,bytes(1));c.put(terms,bytes(12))
 assert call('flight_rates_init',{1:state,9:3})==0
 assert call('heading_init',{1:0x320400,9:3})==0
 assert call('movement_init',{1:0x320500,9:3})==0
 for stage in [0,1,2,3,5,6]:
  oldh=c.get(p+0x35,1)[0];oldt=c.get(p+0x3d,1)[0];oldrpm=c.get(p+0x1b,1)[0]
  if stage==2:
   assert call('movement_height',{1:0x320500,2:p})==0
   was=int.from_bytes(c.get(0x320500+16,2),'big')
   applied=call('ground_step',{1:p,2:ground,9:was});assert applied in [0,1];resets+=applied
   # h=1 fixture has zero fractional state; production must clear it explicitly.
  elif stage==5:assert call('movement_horizontal',{1:0x320500,2:p,3:h[0]+0x7a44})==0
  else:assert call('motion_stage',{1:p,2:stages,3:terms,9:stage})==0
  if stage==0:assert call('heading_step',{1:0x320400,2:p,9:oldh,10:oldt,11:0})==0
  if stage==1:assert call('flight_vertical_step',{1:state,2:p,3:terms})==0
  if stage==3:assert call('flight_forward_step',{1:state,2:p,3:terms})==0
  if stage==6:assert call('flight_rpm_step',{1:state,2:p,9:oldrpm})==0
 assert expected==(c.get(p,86),c.get(counter,4),c.get(h[6]+0x42f6,1)),n
 notifications+=int.from_bytes(expected[1],'big')
assert notifications>0
r=dict(native_motion_cases=4096,ground_resets=resets,notifications=notifications,calls=calls,scope='h=1 motion including native ground at original boundary; heading RNG excluded, notification UI stubbed')
(root/'tmp/c/ground-motion-tests.json').write_text(json.dumps(r,indent=2)+'\n');print(r);c.close()
