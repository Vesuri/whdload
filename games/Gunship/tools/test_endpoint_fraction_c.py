from unicorn_b import *
import random
c=CPU();c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/endpoint-fraction.hunk')).get_segments()[0].get_data()))
rng=random.Random(1360);state=0x330000;cases=0
signed=lambda v:v-2**32 if v&2**31 else v
def check(delta,span,remainder):
 global cases
 c.put(state,struct.pack('>I',remainder&0xffffffff))
 regs={r:rng.randrange(0x1000000) for r in range(1,17) if r!=8};regs.update({1:state,9:delta&0xffffffff,10:span&0xffffffff})
 for r,v in regs.items():c.rw(r,v)
 c.rw(8,0x8f000);c.call(base);cases+=1
 assert c.rr(18)==0x90000 and c.rr(8)==0x8f004
 assert all(c.rr(r)==v for r,v in regs.items() if r not in [9,10])
 valid=span in [1,16,17,20] and 0<=remainder<1360 and -65535<=delta<=65535
 if valid:
  numerator=remainder+delta*(1360//span);inc,rem=divmod(numerator,1360)
  assert signed(c.rr(9))==inc and c.rr(10)==0 and int.from_bytes(c.get(state,4),'big')==rem,(delta,span,remainder,c.rr(9),inc)
  return inc,rem
 assert c.rr(9)==0 and c.rr(10)==0xffffffff and c.get(state,4)==struct.pack('>I',remainder&0xffffffff)
for span in [1,16,17,20]:
 for delta in [-65535,-32769,-32768,-1,0,1,32767,32768,65535]:
  for rem in [0,1,679,1359]:check(delta,span,rem)
for span in [1,16,17,20]:
 for rem in range(1360):check(0,span,rem)
for span in [0,2,15,18,19,21,65552,-1]:check(0,span,0)
for rem in [-1,1360,2**31]:check(0,17,rem)
for _ in range(4096):check(rng.randint(-65535,65535),rng.choice([1,16,17,20]),rng.randrange(1360))
for span in [0,2,15,18,19,21,65552,-1]:check(1,span,0)
for rem in [-1,1360,2**31]:check(1,17,rem)
for delta in [-65536,65536,-2**31,2**31-1]:check(delta,17,0)
# Carry arbitrary fractions across PAL interval-length changes, then NTSC.
rem=971;total=0;expected=0
for span in [17,17,16,17,17,16,20,20]:
 delta=rng.randint(-65535,65535);expected+=delta
 for _ in range(span):inc,rem=check(delta,span,rem);total+=inc
 assert total==expected and rem==971
print(dict(cases=cases,zero_delta_all_remainders=True,exact_interval_endpoints=True,invalid_inputs_atomic=True,registers_preserved=True))
c.close()
