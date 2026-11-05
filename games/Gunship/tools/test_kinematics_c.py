#!/usr/bin/env python3
"""Connect scaled response/linear rates to native stages; prove h=1 and fractions."""
import json,random
from fractions import Fraction as F
from unicorn_b import *
from layout import locate
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks']
c=CPU();c.put(0x200000,mem);c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/kinematics.hunk')).get_segments()[0].get_data()))
listing=(root/'tmp/c/kinematics.lst').read_text()
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
for n in range(4096):
 b=bytearray.fromhex(fixtures[n%len(fixtures)]['input'])
 if n>=384:struct.pack_into('>H',b,28,n%34)
 c.put(p,b);call('motion_preview',{1:p,2:out,3:whole,9:0});expected=c.get(out,86)
 c.put(p,b);c.put(terms,bytes(12));assert call('flight_rates_init',{1:state,9:3})==0
 assert call('heading_init',{1:0x320400,9:3})==0
 assert call('movement_init',{1:0x320500,9:3})==0
 for stage in [0,1,2,3,5,6]:
  oldh=c.get(p+0x35,1)[0];oldt=c.get(p+0x3d,1)[0]
  oldrpm=c.get(p+0x1b,1)[0]
  if stage==2:assert call('movement_height',{1:0x320500,2:p})==0
  elif stage==5:assert call('movement_horizontal',{1:0x320500,2:p,3:h[0]+0x7a44})==0
  else:assert call('motion_stage',{1:p,2:stages,3:terms,9:stage})==0
  if stage==0:assert call('heading_step',{1:0x320400,2:p,9:oldh,10:oldt,11:0})==0
  if stage==1:assert call('flight_vertical_step',{1:state,2:p,3:terms})==0
  if stage==3:assert call('flight_forward_step',{1:state,2:p,3:terms})==0
  if stage==6:assert call('flight_rpm_step',{1:state,2:p,9:oldrpm})==0
 assert c.get(p,86)==expected,(n,c.get(p,86).hex(),expected.hex())
 assert c.get(state,24)==struct.pack('>H',3)+bytes(22)
# Exact linear conversion into a shared response fraction, no canonical-sign assumption.
for n in range(20000):
 rate=rng.choice([3,50,60,32767]);delta=rng.randrange(-32768,32768);main=rng.randrange(-32766,32767);conv=rng.randrange(-rate+1,rate)
 c.put(state,struct.pack('>ii',main,conv))
 value=signed(call('fraction_add_rate',{1:state,2:state+4,9:delta&0xffffffff,11:rate}))
 assert c.rr(10)==0
 assert F(value)+F(long(0),32767)+F(long(4),rate*32767)==F(main,32767)+F(conv,rate*32767)+F(delta*3,rate)
 assert abs(long(0))<32767 and abs(long(4))<rate
# Independent full-shadow model for each connected field-rate operation.
gains={(50,2):0x230bc42,(50,3):0x10579fe,(50,4):0x7ea380,(60,2):0x1d3f349,(60,3):0xda0adf,(60,4):0x6990f7}
def response_change(error,rem,rate,shift):
 if sw(error+(1<<(shift-1)))>>shift==0:return F(0)
 gain=gains[rate,shift]
 return F(trunc(error*gain,65536)-trunc(trunc(rem*gain,65536),32767),32767)
field_checks=0
for n in range(6000):
 rate=rng.choice([50,60]);q=[rng.randrange(-32766,32767) for _ in range(3)];conv=[rng.randrange(-rate+1,rate) for _ in range(2)]
 c.put(state,struct.pack('>HHiiiii',rate,0,q[0],q[1],conv[0],q[2],conv[1]))
 b=bytearray(86)
 if n%3==0:
  old=rng.randrange(-128,128);target=rng.randrange(-128,128);b[0x3e]=rng.randrange(256);c.put(p,b)
  c.put(terms,struct.pack('>iii',target,old,0))
  expected=F(old)+F(q[0],32767)+response_change(target-old,q[0],rate,2)
  assert call('flight_vertical_step',{1:state,2:p,3:terms})==0
  assert F(sb(c.get(p+0x3e,1)[0]))+qvalue(4,rate)==expected
 elif n%3==1:
  old=rng.randrange(-512,513);error=rng.randrange(-1024,1025);slew=rng.choice([-1,0,1]);struct.pack_into('>h',b,0x2a,old);c.put(p,b)
  c.put(terms,struct.pack('>iii',error,slew,0))
  expected=F(old)+F(q[1],32767)+F(conv[0],rate*32767)+response_change(error,q[1],rate,4)+F(slew*3,rate)
  assert call('flight_forward_step',{1:state,2:p,3:terms})==0
  assert F(sw(int.from_bytes(c.get(p+0x2a,2),'big')))+qvalue(8,rate,12)==expected
 else:
  old=rng.randrange(256);target=rng.randrange(157);powered=rng.randrange(2);collect=rng.randrange(43);speed=rng.randrange(-128,128);height=rng.choice([0,128])
  b[0x40]=target;b[0x42]=16*powered;b[0x39]=collect;b[0x50]=speed&255;struct.pack_into('>H',b,0x1c,height);c.put(p,b)
  expected=F(old)+F(q[2],32767)+F(conv[1],rate*32767)
  if powered:expected+=response_change(target-old,q[2],rate,3)
  else:
   interim=old-(collect>>2)
   delta=-(collect>>2)-(int(interim!=0 and height==0))+(speed>>3)
   expected=max(F(0),min(F(156),expected+F(delta*3,rate)))
  assert call('flight_rpm_step',{1:state,2:p,9:old})==0
  assert F(c.get(p+0x1b,1)[0])+qvalue(16,rate,20)==expected,(old,target,powered,expected,c.get(p+0x1b,1),qvalue(16,rate,20))
 field_checks+=1
# Native stopping ranges must not erase the shared additive-slew fraction.
slew_fields=0
for rate in [50,60]:
 for direction in [-1,1]:
  assert call('flight_rates_init',{1:state,9:rate})==0
  c.put(p,bytes(86));c.put(terms,struct.pack('>iii',0,direction,0))
  for field in range(1,rate*4+1):
   assert call('flight_forward_step',{1:state,2:p,3:terms})==0
   actual=F(sw(int.from_bytes(c.get(p+42,2),'big')))+qvalue(8,rate,12)
   assert actual==F(direction*field*3,rate)
   slew_fields+=1
# Corrupt fractions, including INT_MIN, must fail before any component writes.
invalid=0
for offset,bad in [(4,32767),(8,-32767),(16,2147483647),(12,-2147483648),(20,50)]:
 assert call('flight_rates_init',{1:state,9:50})==0;c.put(state+offset,struct.pack('>i',bad));c.put(terms,bytes(12))
 for name,args in [('flight_vertical_step',{3:terms}),('flight_forward_step',{3:terms}),('flight_rpm_step',{9:20})]:
  before=(c.get(state,24),c.get(p,86));assert call(name,{1:state,2:p,**args})==0xffffffff
  assert before==(c.get(state,24),c.get(p,86));invalid+=1
r=dict(sustained_slew_fields=slew_fields,native_h1_motion_cases=4096,exact_linear_conversion_cases=20000,field_rate_model_cases=field_checks,invalid_state_cases=invalid,calls=calls,scope='connected continuous motion h=1 including height, coordinates and wind; world effects still excluded')
(root/'tmp/c/kinematics-tests.json').write_text(json.dumps(r,indent=2)+'\n');print(r);c.close()
