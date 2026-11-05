#!/usr/bin/env python3
"""Connect scaled response/linear rates to native stages; prove h=1 and fractions."""
import json,random
from fractions import Fraction as F
from unicorn_b import *
from layout import locate
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks']
c=CPU();c.put(0x200000,mem);c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/player-ground.hunk')).get_segments()[0].get_data()))
listing=(root/'tmp/c/player-ground.lst').read_text()
def sym(n):return int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
whole=0x300000;stages=0x310000;p=0x320000;out=0x320100;terms=0x320200;shadow=0x380000;state=shadow+12;rng=random.Random(9636);calls=0
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
 assert call('player_step_init',{1:shadow,9:3,10:0})==0
 candidate=0x39000c;c.put(candidate-12,c.get(shadow,12));original=(c.get(p,86),c.get(shadow,76))
 assert call('kinematics_prepare',{1:shadow+12,2:p,3:stages,4:h[0]+0x7a44,5:candidate,9:0})==0
 assert original==(c.get(p,86),c.get(shadow,76))
 was=int.from_bytes(c.get(candidate+44+16,2),'big')
 applied=call('player_ground_step',{1:candidate-12,2:candidate+64,3:ground,9:was});assert applied in [0,1];resets+=applied
 assert call('kinematics_complete',{1:shadow+12,2:p,3:stages,4:h[0]+0x7a44,5:candidate})==0
 c.put(shadow,c.get(candidate-12,12))
 committed=(c.get(p,86),c.get(shadow,76))
 assert call('kinematics_complete',{1:shadow+12,2:p,3:stages,4:h[0]+0x7a44,5:candidate})==0xffffffff
 assert committed==(c.get(p,86),c.get(shadow,76))
 assert expected==(c.get(p,86),c.get(counter,4),c.get(h[6]+0x42f6,1)),n
 notifications+=int.from_bytes(expected[1],'big')
assert notifications>0
# Failed preparation and failed completion cannot publish or be resumed.
phase=sym('KN_PHASE');failure_cases=0
for kind in ['mismatched-rate','late-forward-fraction']:
 assert call('player_step_init',{1:shadow,9:50,10:0})==0
 if kind=='mismatched-rate':c.put(shadow+12+24,struct.pack('>H',60))
 before=(c.get(p,86),c.get(shadow,76))
 prepared=call('kinematics_prepare',{1:shadow+12,2:p,3:stages,4:h[0]+0x7a44,5:candidate,9:0})
 if kind=='mismatched-rate':assert prepared==0xffffffff
 else:
  assert prepared==0;c.put(candidate+8,struct.pack('>i',32767))
 assert call('kinematics_complete',{1:shadow+12,2:p,3:stages,4:h[0]+0x7a44,5:candidate})==0xffffffff
 assert c.get(candidate+phase,2)==bytes(2)
 assert before==(c.get(p,86),c.get(shadow,76));failure_cases+=1
r=dict(failure_cases=failure_cases,native_motion_cases=4096,ground_resets=resets,notifications=notifications,calls=calls,scope='h=1 split coordinator with combined player ground hand-off at native boundary; heading RNG excluded, notification UI stubbed')
(root/'tmp/c/split-ground-motion-tests.json').write_text(json.dumps(r,indent=2)+'\n');print(r);c.close()
