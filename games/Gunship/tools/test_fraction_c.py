#!/usr/bin/env python3
"""Signed fractional increments: 68000 execution against integer arithmetic."""
import itertools,json,random
from unicorn_b import *
listing=(root/'tmp/c/fraction.lst').read_text();entry=int(re.search(r'^([0-9A-F]{8}) fraction_scale$',listing,re.M)[1],16)
c=CPU();c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/fraction.hunk')).get_segments()[0].get_data()));S=0x300000;rng=random.Random(35060);checks=0
signed=lambda x:x-(1<<32) if x>>31 else x
trunc=lambda n,d: -(abs(n)//d) if n<0 else n//d
def call(delta,num,den,rem):
 global checks
 c.put(S,struct.pack('>i',rem));regs={r:rng.randrange(0x1000000) for r in range(1,17) if r not in (8,9,10)};regs.update({1:S,11:den&0xffffffff})
 for r,v in regs.items():c.rw(r,v)
 c.rw(8,0x8f000);c.rw(9,delta&0xffffffff);c.rw(10,num&0xffffffff);c.call(base+entry)
 assert all(c.rr(r)==v for r,v in regs.items())
 assert c.rr(18)==0x90000 and c.rr(8)==0x8f004
 valid=(-32768<=delta<=32767 and 1<=den<=32767 and 0<=num<=den and -den<rem<den)
 q=signed(c.rr(9));r=struct.unpack('>i',c.get(S,4))[0];status=signed(c.rr(10));checks+=1
 if valid:
  total=delta*num+rem;expected=trunc(total,den)
  assert status==0 and q==expected and r==total-expected*den,(delta,num,den,rem,q,r)
 else:assert status==-1 and q==0 and r==rem
 return q,r
for den in [1,2,3,50,60,32767]:
 for delta,num,rem in itertools.product([-32768,-32767,-256,-1,0,1,255,32766,32767],sorted(set([0,1,den//2,den])),sorted(set([-den+1,-1,0,1,den-1]))):call(delta,num,den,rem)
for i in range(30000):
 den=rng.randrange(1,32768);call(rng.randrange(-32768,32768),rng.randrange(den+1),den,rng.randrange(-den+1,den))
# Constant signed rates over an exact second must retain exactly 3 native ticks.
for den in [50,60]:
 for delta in [-32768,-257,-1,0,1,257,32767]:
  rem=out=0
  for field in range(den):
   q,rem=call(delta,3,den,rem);out+=q
  assert out==3*delta and rem==0
# Identical changing input replayed in different render-sized batches.
for den in [50,60]:
 tape=[rng.randrange(-256,257) for _ in range(600)]
 runs=[]
 for batch in [1,3,10,25]:
  out=rem=0
  for start in range(0,len(tape),batch):
   for value in tape[start:start+batch]:
    q,rem=call(value,3,den,rem);out+=q
  assert out*den+rem==sum(tape)*3
  runs.append((out,rem))
 assert len(set(runs))==1
for args in [(-32769,3,50,0),(32768,3,50,0),(1,-1,50,0),(1,51,50,0),(1,1,0,0),(1,1,-1,0),(1,1,32768,0),(1,3,50,50),(1,3,50,-50),(1,3,50,2147483647),(1,3,50,-2147483648)]:call(*args)
r=dict(calls=checks,scope='signed rational increment, exact PAL/NTSC constant-rate accumulation, mixed signs, batching and invalid inputs; not a player integrator')
(root/'tmp/c/fraction-tests.json').write_text(json.dumps(r,indent=2)+'\n');print(r);c.close()
