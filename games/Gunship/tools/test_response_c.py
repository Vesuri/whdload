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
 c.rw(8,0x8f000);c.rw(9,error&0xffffffff);c.rw(10,shift&0xffffffff);c.call(base+sym('response_step'));calls+=1
 assert c.rr(18)==0x90000 and c.rr(8)==0x8f004
 assert all(c.rr(r)==v for r,v in regs.items())
 result=signed(c.rr(9));status=signed(c.rr(10));after=struct.unpack('>i',c.get(S,4))[0]
 valid=-32768<=error<=32767 and shift in (2,3,4) and rate in (3,50,60) and -32767<rem<32767 and (rate!=3 or rem==0)
 if not valid:assert result==0 and status==-1 and after==rem
 elif rate==3:assert status==0 and result==sw(error+(1<<(shift-1)))>>shift and after==0
 else:
  gain=gains[rate,shift];total=trunc(error*gain,65536)+rem-trunc(trunc(rem*gain,65536),32767);q=trunc(total,32767)
  assert status==0 and result==q and after==total-q*32767
 return result,after
# Execute native rounding instructions as independent returning snippets.
for address,start,end in [(0x330000,0x956e,0x9572),(0x330100,0x9664,0x9668),(0x330200,0x9738,0x974a)]:
 c.put(address,c.get(h[0]+start,end-start)+bytes.fromhex('4e75'))
for shift,entry,reg in [(2,0x330000,11),(4,0x330100,9)]:
 for error in range(-32768,32768):
  c.rw(8,0x8f000);c.rw(reg,error&0xffffffff);c.call(entry);native=sw(c.rr(reg))
  q,rem=call(error,shift,3);assert q==native
for target in range(256):
 for old in range(256):
  c.put(p+0x40,bytes([target]));c.put(p+0x1b,bytes([old]));c.rw(8,0x8f000);c.rw(6,p);c.call(0x330200)
  native=sw(c.rr(10));q,rem=call(target-old,3,3);assert q==native
for _ in range(20000):call(rng.randrange(-32768,32768),rng.choice([2,3,4]),rng.choice([50,60]),rng.randrange(-32766,32767))
# Constant-target accuracy, including full fractional state rather than output bytes only.
max_error={};near_error={}
for rate in (50,60):
 for shift in (2,3,4):
  maximum=near=0.0
  for target in (-32768,-2048,-256,-1,0,1,256,2048,32760):
   value=rem=0;r=(1-2**(-shift))**(3/rate)
   for field in range(1,rate*10+1):
    q,rem=call(target-value,shift,rate,rem);value+=q
    ideal=target*(1-r**field);error=abs(value+rem/32767-ideal)
    maximum=max(maximum,error)
    if abs(target)<=256:near=max(near,error)
  max_error[f'{rate}/{shift}']=maximum;near_error[f'{rate}/{shift}']=near
for args in [(32768,2,50,0),(1,1,50,0),(1,5,50,0),(1,2,49,0),(1,2,50,32767),(1,2,60,-32767),(1,2,3,1)]:call(*args)
r=dict(calls=calls,native_h1_cases=196608,random_field_cases=20000,gains={f'{a}/{b}':v for (a,b),v in gains.items()},max_10_second_error_full_word_range=max_error,max_10_second_error_targets_within_256=near_error,scope='scalar constant-target response only; excludes slew, clamps, wrapping state and coupled flight dynamics')
(root/'tmp/c/response-tests.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2));c.close()
