#!/usr/bin/env python3
"""Connect scaled response/linear rates to native stages; prove h=1 and fractions."""
import json,random
from fractions import Fraction as F
from unicorn_b import *
from layout import locate
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks']
c=CPU();c.put(0x200000,mem);c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/kinematics-step.hunk')).get_segments()[0].get_data()))
listing=(root/'tmp/c/kinematics-step.lst').read_text()
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

shadow=0x330000
for n in range(4096):
 b=bytearray.fromhex(fixtures[n%len(fixtures)]['input'])
 if n>=384:struct.pack_into('>H',b,28,n%34)
 c.put(p,b);call('motion_preview',{1:p,2:out,3:whole,9:0});expected=c.get(out,86)
 assert call('kinematics_init',{1:shadow,9:3})==0
 assert call('kinematics_step',{1:shadow,2:p,3:stages,4:h[0]+0x7a44,9:0})==0
 assert c.get(p,86)==expected,n
# Compare sustained field sequences with the separately called component chain.
# This proves assembly ordering/state plumbing, not a trajectory error bound.
fields=0
for rate in [50,60]:
 for scenario in range(12):
  b=bytearray.fromhex(fixtures[scenario]['input']);struct.pack_into('>H',b,28,256)
  c.put(p,b);c.put(out,b)
  assert call('kinematics_init',{1:shadow,9:rate})==0
  assert call('flight_rates_init',{1:state,9:rate})==0
  assert call('heading_init',{1:0x320400,9:rate})==0
  assert call('movement_init',{1:0x320500,9:rate})==0
  for field in range(rate*2):
   # Matching logical tick parity, held collective and attitude.
   tick=field*3//rate
   c.put(p+12,struct.pack('>H',tick));c.put(out+12,struct.pack('>H',tick))
   impulse=rng.randrange(-2,3) if field%20==0 and c.get(p+28,2)!=bytes(2) else 0
   c.put(terms,bytes(12))
   for stage in [0,1,2,3,5,6]:
    oldh=c.get(p+0x35,1)[0];oldt=c.get(p+0x3d,1)[0];oldrpm=c.get(p+0x1b,1)[0]
    if stage==2:assert call('movement_height',{1:0x320500,2:p})==0
    elif stage==5:assert call('movement_horizontal',{1:0x320500,2:p,3:h[0]+0x7a44})==0
    else:assert call('motion_stage',{1:p,2:stages,3:terms,9:stage})==0
    if stage==0:assert call('heading_step',{1:0x320400,2:p,9:oldh,10:oldt,11:impulse&0xffffffff})==0
    if stage==1:assert call('flight_vertical_step',{1:state,2:p,3:terms})==0
    if stage==3:assert call('flight_forward_step',{1:state,2:p,3:terms})==0
    if stage==6:assert call('flight_rpm_step',{1:state,2:p,9:oldrpm})==0
   assert call('kinematics_step',{1:shadow,2:out,3:stages,4:h[0]+0x7a44,9:impulse&0xffffffff})==0
   assert c.get(out,86)==c.get(p,86),(rate,scenario,field)
   assert c.get(shadow,64)==c.get(state,24)+c.get(0x320400,20)+c.get(0x320500,20)
   fields+=1
# Late validation failures must discard earlier successful private stages.
bad=0
for offset,value in [(0,51),(24,60),(4,32767),(28,-32767),(48,50),(46,2),(60,2)]:
 assert call('kinematics_init',{1:shadow,9:50})==0
 if offset in [0,24,46,60]:c.put(shadow+offset,struct.pack('>H',value))
 else:c.put(shadow+offset,struct.pack('>i',value))
 before=c.get(shadow,64),c.get(p,86)
 assert call('kinematics_step',{1:shadow,2:p,3:stages,4:h[0]+0x7a44,9:0})==0xffffffff
 assert before==(c.get(shadow,64),c.get(p,86));bad+=1
for impulse in [-3,3]:
 assert call('kinematics_init',{1:shadow,9:50})==0
 before=c.get(shadow,64),c.get(p,86)
 assert call('kinematics_step',{1:shadow,2:p,3:stages,4:h[0]+0x7a44,9:impulse&0xffffffff})==0xffffffff
 assert before==(c.get(shadow,64),c.get(p,86));bad+=1
before=c.get(shadow,64)
assert call('kinematics_init',{1:shadow,9:49})==0xffffffff
assert c.get(shadow,64)==before
r=dict(native_h1_cases=4096,composed_field_steps=fields,transaction_failures=bad,calls=calls)
(root/'tmp/c/kinematics-step-tests.json').write_text(json.dumps(r,indent=2)+'\n');print(r);c.close()
