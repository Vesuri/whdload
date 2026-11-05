#!/usr/bin/env python3
"""Native h=1 attitude equivalence and field-rate input/saturation behavior."""
import itertools,json,random
from fractions import Fraction
from unicorn_b import *
from layout import locate
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks'];p=h[6]+0x3b88;S=0x320000
c=CPU();c.put(0x200000,mem);c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/attitude.hunk')).get_segments()[0].get_data()))
listing=(root/'tmp/c/attitude.lst').read_text()
def sym(n):return int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
rng=random.Random(5376);calls=0
sbyte=lambda n:(n&255)-256 if n&128 else n&255
trunc=lambda n,d:-(abs(n)//d) if n<0 else n//d
def call(name,d0,d1):
 global calls
 regs={r:rng.randrange(0x1000000) for r in range(1,17) if r not in (8,9)};regs.update({1:S,2:p,10:d1&0xffffffff})
 for r,v in regs.items():c.rw(r,v)
 c.rw(8,0x8f000);c.rw(9,d0&0xffffffff);c.call(base+sym(name));calls+=1
 assert c.rr(18)==0x90000 and c.rr(8)==0x8f004
 assert all(c.rr(r)==v for r,v in regs.items()),name
 return c.rr(9)
count=0
for x,y,previous,roll,pitch in itertools.product([-1,0,1],[-1,0,1],[-1,0,1],range(256),[-128,-13,-12,-1,0,20,21,127]):
 b=bytearray(86);b[28]=1;b[54]=pitch&255;b[55]=roll
 c.put(p,b);c.put(h[6]+0x4294,bytes([x&255,y&255]));c.put(h[0]+0x5524,bytes([previous&255]))
 c.rw(8,0x8f000);c.rw(6,p);c.rw(17,0x2000);c.call(h[0]+0x5376);assert c.rr(18)==0x90000
 expected=c.get(p,86);c.put(p,b)
 assert call('attitude_init',3,previous)==0 and call('attitude_step',x,y)==0
 assert c.get(p,86)==expected,(x,y,previous,roll,pitch)
 assert struct.unpack('>h',c.get(S+2,2))[0]==y and c.get(S+4,8)==bytes(8)
 count+=1
# Independent rational model, changing controls, retained signed debt and bounds.
field_cases=0
for rate in [50,60]:
 tape=[(1,1)]*(rate*3)+[(-1,-1)]*rate+[(0,0)]*rate+[(rng.choice([-1,0,1]),rng.choice([-1,0,1])) for _ in range(rate*4)]
 states=[]
 for batch in [1,3,10,25]:
  c.put(p,bytes(86));assert call('attitude_init',rate,0)==0
  roll=pitch=previous=rr=pr=0
  for start in range(0,len(tape),batch):
   for x,y in tape[start:start+batch]:
    total=4*x*3+rr;q=trunc(total,rate);rr=total-q*rate
    raw=sbyte(roll+q);roll=max(-20,min(20,raw))
    if raw!=roll or roll==20 and rr>0 or roll==-20 and rr<0:rr=0
    total=(-(y+previous) if y else 0)*3+pr;q=trunc(total,rate);pr=total-q*rate
    pitch=sbyte(pitch+q);previous=y
    assert call('attitude_step',x,y)==0
    assert c.get(p+54,2)==bytes([pitch&255,roll&255])
    assert c.get(S,12)==struct.pack('>Hhii',rate,previous,rr,pr)
    field_cases+=1
  states.append((c.get(p,86),c.get(S,12)))
 assert len(set(states))==1
# Quantify the changed history window against whole-tick held controls.
transition_bounds={}
for rate in [50,60]:
 errors=[]
 for y,previous in itertools.product([-1,1],[-1,0,1]):
  c.put(p,bytes(86));assert call('attitude_init',3,previous)==0
  for _ in range(3):assert call('attitude_step',0,y)==0
  native=sbyte(c.get(p+54,1)[0])
  c.put(p,bytes(86));assert call('attitude_init',rate,previous)==0
  for _ in range(rate):assert call('attitude_step',0,y)==0
  actual=Fraction(sbyte(c.get(p+54,1)[0]))+Fraction(struct.unpack('>i',c.get(S+8,4))[0],rate)
  errors.append(abs(actual-native))
 expected=Fraction(2*(rate-3),rate)
 assert max(errors)==expected
 transition_bounds[str(rate)]=str(max(errors))
# Invalid input/state cannot partially commit attitude or fractions.
invalid=0
for rate,previous,x,y,rr,pr in [(50,0,2,0,0,0),(50,0,0,-2,0,0),(49,0,0,0,0,0),(50,2,0,0,0,0),(50,0,1,1,50,0),(60,0,1,1,0,-60)]:
 c.put(S,struct.pack('>Hhii',rate,previous,rr,pr));before=(c.get(S,12),c.get(p,86))
 assert call('attitude_step',x,y)==0xffffffff
 assert before==(c.get(S,12),c.get(p,86));invalid+=1
r=dict(native_h1_cases=count,field_cases=field_cases,invalid_cases=invalid,calls=calls,held_transition_pitch_bounds=transition_bounds,scope='deterministic attitude controls only; no world RNG, no HUD pitch clamp, no motion integration')
(root/'tmp/c/attitude-tests.json').write_text(json.dumps(r,indent=2)+'\n');print(r);c.close()
