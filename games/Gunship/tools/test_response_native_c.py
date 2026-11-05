#!/usr/bin/env python3
"""Native rounded responses and rational r^h field response with feedback."""
import json,random,math
from decimal import Decimal,localcontext,ROUND_HALF_UP
from unicorn_b import *
from layout import locate
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks'];p=h[6]+0x3b88;S=0x320000
c=CPU();c.put(0x200000,mem);c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/response.hunk')).get_segments()[0].get_data()))
listing=(root/'tmp/c/response.lst').read_text()
def sym(n):return int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
gains={};rng=random.Random(9572);calls=0
with localcontext() as ctx:
 ctx.prec=60
 for rate in (50,60):
  for shift in (2,3,4):
   a=1-(1-Decimal(1)/(2**shift))**(Decimal(3)/rate)
   gains[rate,shift]=int((a*32767*65536).to_integral_value(rounding=ROUND_HALF_UP))
assert c.get(base+sym('response_gains'),24)==struct.pack('>6I',*(gains[k] for k in gains))
signed=lambda v:v-2**32 if v&2**31 else v
sw=lambda v:(v&65535)-65536 if v&32768 else v&65535
trunc=lambda n,d:-(abs(n)//d) if n<0 else n//d
def call(error,shift,rate,rem=0):
 global calls
 c.put(S,struct.pack('>i',rem));regs={r:rng.randrange(0x1000000) for r in range(1,17) if r not in (8,9,10)};regs.update({1:S,11:rate&0xffffffff})
 for r,v in regs.items():c.rw(r,v)
 c.rw(8,0x8f000);c.rw(9,error&0xffffffff);c.rw(10,shift&0xffffffff);c.call(base+sym('response_step_native'));calls+=1
 assert c.rr(18)==0x90000 and c.rr(8)==0x8f004
 assert all(c.rr(r)==v for r,v in regs.items())
 result=signed(c.rr(9));status=signed(c.rr(10));after=struct.unpack('>i',c.get(S,4))[0]
 valid=-32768<=error<=32767 and shift in (2,3,4) and rate in (3,50,60) and -32767<rem<32767 and (rate!=3 or rem==0)
 if not valid:assert result==0 and status==-1 and after==rem
 elif rate==3:assert status==0 and result==sw(error+(1<<(shift-1)))>>shift and after==0
 elif sw(error+(1<<(shift-1)))>>shift==0:
  assert status==0 and result==0 and after==rem
 else:
  gain=gains[rate,shift];total=trunc(error*gain,65536)+rem-trunc(trunc(rem*gain,65536),32767);q=trunc(total,32767)
  assert status==0 and result==q and after==total-q*32767
 return result,after

for rate in (50,60):
 for shift in (2,3,4):
  for error in range(-20,21):
   for rem in [-32766,-123,0,123,32766]:call(error,shift,rate,rem)
for _ in range(10000):call(rng.randrange(-32768,32768),rng.choice([2,3,4]),rng.choice([50,60]),rng.randrange(-32766,32767))
for error in [-32768,-32767,-9,-8,-4,-3,-2,-1,0,1,2,3,4,7,8,32766,32767]:
 for shift in [2,3,4]:call(error,shift,3)
settled=0
for rate in (50,60):
 for shift,target,initial in [(2,-4,0),(2,32,0),(2,-32,0),(3,156,128),(3,32,156),(4,64,0),(4,-64,0)]:
  native=initial
  for _ in range(90):native+=sw(target-native+(1<<(shift-1)))>>shift
  value=initial;rem=0
  for _ in range(rate*30):
   q,rem=call(target-value,shift,rate,rem);value+=q
  assert value==native,(rate,shift,target,value,native)
  before=(value,rem)
  for _ in range(rate):
   q,rem=call(target-value,shift,rate,rem);value+=q
  assert (value,rem)==before
  settled+=1
for args in [(32768,2,50,0),(-32769,2,50,0),(0,1,50,0),(0,5,50,0),(0,2,49,0),(0,2,50,32767),(0,2,50,-32767),(0,2,3,1)]:call(*args)
r=dict(calls=calls,settled_trajectories=settled,scope='native stopping ranges preserve existing fractions; outside uses unchanged exponential law; h=1 boundaries and invalid inputs')
(root/'tmp/c/response-native-tests.json').write_text(json.dumps(r,indent=2)+'\n');print(r);c.close()
