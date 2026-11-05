#!/usr/bin/env python3
"""Connect scaled response/linear rates to native stages; prove h=1 and fractions."""
import json,random
from fractions import Fraction as F
from unicorn_b import *
from layout import locate
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks']
c=CPU();c.put(0x200000,mem);c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/player-step.hunk')).get_segments()[0].get_data()))
listing=(root/'tmp/c/player-step.lst').read_text()
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


shadow=0x330000;refstate=0x331000;packet=0x332000
c.put(0x370000,c.get(h[0]+0x5756,0x24)+bytes.fromhex('4e75'))
for n in range(4096):
 b=bytearray.fromhex(fixtures[n%len(fixtures)]['input']);struct.pack_into('>H',b,28,1024);b[15]=0
 b[54]=n&255;b[55]=rng.randrange(-20,21)&255
 x,y,previous=[rng.randrange(-1,2) for _ in range(3)]
 c.put(p,b);c.put(h[6]+0x4294,bytes([x&255,y&255]));c.put(h[0]+0x5524,bytes([previous&255]))
 c.rw(6,p);c.rw(8,0x8f000);c.call(0x370000)
 c.rw(8,0x8f000);c.call(h[0]+0x5376)
 call('motion_preview',{1:p,2:out,3:whole,9:0});expected=c.get(out,86)
 c.put(p,b);c.put(packet,struct.pack('>hhhhh',x,y,0,0,0))
 assert call('player_step_init',{1:shadow,9:3,10:previous&0xffffffff})==0
 assert call('player_step',{1:shadow,2:p,3:stages,4:h[0]+0x7a44,5:packet})==0
 assert c.get(p,86)==expected,n
 assert int.from_bytes(c.get(shadow+2,2),'big',signed=True)==y
fields=0
for rate in [50,60]:
 for config in [0,2]:
  b=bytearray(86);struct.pack_into('>HH',b,0,0x7000,0x8000);struct.pack_into('>H',b,28,1024)
  b[16]=config;b[27]=128;b[57]=26;b[66]=28
  c.put(p,b);c.put(out,b)
  assert call('player_step_init',{1:shadow,9:rate,10:0})==0
  assert call('attitude_init',{1:refstate,9:rate,10:0})==0
  assert call('kinematics_init',{1:refstate+12,9:rate})==0
  for f in range(rate*6):
   x,y=[(1,1),(-1,-1),(0,0),(-1,1),(1,-1),(0,0)][f//rate]
   rollimp,pitchimp,headimp=(rng.choice([-4,0,4]),rng.randrange(-1,2),rng.randrange(-2,3)) if (f*3//rate)!=((f-1)*3//rate) else (0,0,0)
   raw=struct.pack('>hhhhh',x,y,rollimp,pitchimp,headimp);c.put(packet,raw)
   for addr in [p,out]:c.put(addr+12,struct.pack('>H',f*3//rate+1))
   assert call('attitude_pitch_clamp_control',{1:refstate,2:p,3:packet})==0
   assert call('attitude_step_impulses',{1:refstate,2:p,9:x&0xffffffff,10:y&0xffffffff,11:rollimp&0xffffffff,12:pitchimp&0xffffffff})==0
   assert call('kinematics_step_fractional',{1:refstate+12,2:p,3:stages,4:h[0]+0x7a44,9:headimp&0xffffffff,10:int.from_bytes(c.get(refstate+8,4),'big')})==0
   assert call('player_step',{1:shadow,2:out,3:stages,4:h[0]+0x7a44,5:packet})==0
   assert c.get(p,86)==c.get(out,86) and c.get(shadow,76)==c.get(refstate,76),(rate,config,f)
   assert c.get(packet,10)==raw
   fields+=1
bad=0
for words in [(2,0,0,0,0),(0,-2,0,0,0),(0,0,1,0,0),(0,0,0,2,0),(1,1,0,0,3)]:
 assert call('player_step_init',{1:shadow,9:50,10:0})==0;c.put(packet,struct.pack('>hhhhh',*words));before=c.get(p,86),c.get(shadow,76)
 assert call('player_step',{1:shadow,2:p,3:stages,4:h[0]+0x7a44,5:packet})==0xffffffff
 assert before==(c.get(p,86),c.get(shadow,76));bad+=1
for offset,data in [(0,struct.pack('>H',60)),(4,struct.pack('>i',50)),(16,struct.pack('>i',32767)),(40,struct.pack('>i',32767)),(60,struct.pack('>i',50))]:
 assert call('player_step_init',{1:shadow,9:50,10:0})==0;c.put(packet,struct.pack('>hhhhh',1,1,0,0,0));c.put(shadow+offset,data);before=c.get(p,86),c.get(shadow,76)
 assert call('player_step',{1:shadow,2:p,3:stages,4:h[0]+0x7a44,5:packet})==0xffffffff
 assert before==(c.get(p,86),c.get(shadow,76));bad+=1
for rate,previous in [(49,0),(50,2),(60,-2)]:
 before=c.get(shadow,76)
 assert call('player_step_init',{1:shadow,9:rate,10:previous&0xffffffff})==0xffffffff
 assert c.get(shadow,76)==before
r=dict(native_attitude_motion_cases=4096,composed_fields=fields,rollback_cases=bad,invalid_initializations=3,calls=calls,scope='continuous attitude plus flight only; scheduled pitch clamp included; world eligibility/contact and command decoding excluded')
(root/'tmp/c/player-step-tests.json').write_text(json.dumps(r,indent=2)+'\n');print(r);c.close()
