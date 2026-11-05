from unicorn_b import *
import random
c=CPU();c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/endpoint-motion.hunk')).get_segments()[0].get_data()))
lst=(root/'tmp/c/endpoint-motion.lst').read_text();entry=base+int(re.search(r'^([0-9A-F]{8}) endpoint_motion_step$',lst,re.M)[1],16)
rng=random.Random(0x1360);S=0x330000;A=0x340000;T=0x350000;P=0x360000;cases=0
specs=[(0,2,False,True),(2,2,False,True),(28,2,False,False),(42,2,True,False),(27,1,False,False),(53,1,False,True),(61,1,False,True),(54,1,True,False),(55,1,True,False),(62,1,True,False)]
def check(anchor,target,player,residues,span):
 global cases
 state=struct.pack('>10I',*[x&0xffffffff for x in residues]);c.put(S,state);c.put(A,anchor);c.put(T,target);c.put(P,player)
 regs={r:rng.randrange(0x1000000) for r in range(1,17) if r!=8};regs.update({1:S,2:A,3:T,4:P,9:span&0xffffffff})
 for r,v in regs.items():c.rw(r,v)
 c.rw(8,0x8f000);c.call(entry);cases+=1
 assert c.rr(18)==0x90000 and c.rr(8)==0x8f004
 assert all(c.rr(r)==v for r,v in regs.items() if r!=9)
 assert c.get(A,86)==anchor and c.get(T,86)==target
 valid=span in [1,16,17,20] and all(0<=r<1360 for r in residues)
 if not valid:
  assert c.rr(9)==0xffffffff and c.get(S,40)==state and c.get(P,86)==player
  return
 expected=bytearray(player);new=[]
 for (off,width,sgn,circ),rem in zip(specs,residues):
  delta=int.from_bytes(target[off:off+width],'big',signed=sgn)-int.from_bytes(anchor[off:off+width],'big',signed=sgn)
  modulus=1<<(8*width)
  if circ:delta=(delta+modulus//2)%modulus-modulus//2
  inc,rem=divmod(delta*(1360//span)+rem,1360);new.append(rem)
  value=int.from_bytes(player[off:off+width],'big')+inc
  expected[off:off+width]=(value%modulus).to_bytes(width,'big')
 assert c.rr(9)==0 and c.get(P,86)==expected and c.get(S,40)==struct.pack('>10I',*new),(span,c.get(P,86).hex(),expected.hex())
 return bytes(expected),new
random_record=lambda:bytes(rng.randrange(256) for _ in range(86))
for _ in range(1024):check(random_record(),random_record(),random_record(),[rng.randrange(1360) for _ in specs],rng.choice([1,16,17,20]))
# Extreme unsigned/signed differences and wrap crossings in both directions.
for span in [1,16,17,20]:
 for pattern in [0,1,127,128,254,255]:
  a=bytes([pattern])*86;t=bytes([255-pattern])*86;p=a;r=[0]*10
  for _ in range(span):p,r=check(a,t,p,r,span)
  for off,width,_,_ in specs:assert p[off:off+width]==t[off:off+width]
  assert r==[0]*10
# Intervals with fresh per-field candidates and retained fractions across PAL cadence.
p=random_record();r=[0]*10
for span in [17,17,16,17,17,16,20,20]:
 a=p
 for _ in range(span):p,r=check(a,random_record(),p,r,span)
for span in [0,2,15,18,19,21,65552,-1]:check(random_record(),random_record(),random_record(),[0]*10,span)
for i in range(10):
 for invalid in [-1,1360,2**31]:
  r=[0]*10;r[i]=invalid;check(random_record(),random_record(),random_record(),r,17)
# Zero deltas must leave arbitrary valid fractional residues untouched.
for span in [1,16,17,20]:
 for rem in [0,1,679,1359]:
  a=random_record();check(a,a,random_record(),[rem]*10,span)
print(dict(cases=cases,native_field_endpoints=True,coordinate_wraps=True,other_player_bytes_preserved=True,invalid_inputs_atomic=True))
c.close()
