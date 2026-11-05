#!/usr/bin/env python3
"""Connect scaled response/linear rates to native stages; prove h=1 and fractions."""
import json,random
from fractions import Fraction as F
from unicorn_b import *
from layout import locate
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks']
c=CPU();c.put(0x200000,mem);c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/player-boundary.hunk')).get_segments()[0].get_data()))
listing=(root/'tmp/c/player-boundary.lst').read_text()
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


shadow=0x330000;refstate=0x331000;packet=0x332000;candidate=0x340000
fields=0
for rate in [3,50,60]:
 for config in [0,2]:
  b=bytearray(86);struct.pack_into('>HH',b,0,0x7000,0x8000);struct.pack_into('>H',b,28,1024);struct.pack_into('>H',b,12,65535)
  b[16]=config;b[27]=128;b[57]=26;b[66]=28;c.put(p,b);c.put(out,b)
  for state_addr in [shadow,refstate]:assert call('player_step_init',{1:state_addr,9:rate,10:0})==0
  for f in range(rate*6):
   x,y=[(1,1),(-1,-1),(0,0),(-1,1),(1,-1),(0,0)][f//rate]
   impulses=(rng.choice([-4,0,4]),rng.randrange(-1,2),rng.randrange(-2,3)) if (f*3//rate)!=((f-1)*3//rate) else (0,0,0)
   c.put(packet,struct.pack('>hhhhh',x,y,*impulses));tick=(f*3//rate+1)&65535
   assert call('player_step_interval',{1:refstate,2:out,3:stages,4:h[0]+0x7a44,5:packet,9:tick})==0
   before=(c.get(p,86),c.get(shadow,76));args={1:shadow,2:p,3:stages,4:h[0]+0x7a44,5:packet,6:candidate,9:tick}
   assert call('player_boundary_prepare',args)==0
   assert before==(c.get(p,86),c.get(shadow,76))
   assert call('player_boundary_complete',args)==0
   assert c.get(p,86)==c.get(out,86) and c.get(shadow,76)==c.get(refstate,76),(rate,config,f)
   assert c.get(p+12,2)==bytes.fromhex('ffff');fields+=1
# Complete native clamp + attitude + motion including ground, RNG eligibility disabled.
ground=0x360000;counter=0x370000;event=0x3a0000;clamp=0x3c0000
c.put(clamp,c.get(h[0]+0x5756,0x24)+bytes.fromhex('4e75'))
c.put(h[0]+0xa150,bytes.fromhex('52b9')+struct.pack('>I',counter)+bytes.fromhex('4e75'))
assert call('ground_deferred_prepare',{1:h[0],2:ground,3:h[6],4:event})==0
# Use a distinct never-executed reference clone with native ground restored.
whole_ground=0x3d0000;assert call('motion_preview_prepare',{1:h[0],2:whole_ground})==0
c.put(whole_ground+0x224,c.get(h[0]+0x95a0,4))
resets=notifications=0
for n in range(4096):
 b=bytearray.fromhex(fixtures[n%len(fixtures)]['input']);b[15]=0;struct.pack_into('>H',b,42,0)
 struct.pack_into('>H',b,28,32767 if n%17==0 else n%5)
 if n%17==0:b[16]=1;b[24]=0;b[82]=0;b[62]=100
 b[54]=n&255;b[55]=rng.randrange(-20,21)&255
 x,y,previous=[rng.randrange(-1,2) for _ in range(3)];tick=int.from_bytes(b[12:14],'big')
 c.put(p,b);c.put(h[6]+0x4294,bytes([x&255,y&255]));c.put(h[0]+0x5524,bytes([previous&255]));c.put(counter,bytes(4));c.put(h[6]+0x42f6,bytes(1))
 c.rw(6,p);c.rw(8,0x8f000);c.call(clamp);c.rw(8,0x8f000);c.call(h[0]+0x5376)
 call('motion_preview',{1:p,2:out,3:whole_ground,9:0});expected=(c.get(out,86),c.get(counter,4),c.get(h[6]+0x42f6,1))
 c.put(p,b);c.put(counter,bytes(4));c.put(h[6]+0x42f6,bytes(1));c.put(event,bytes(4));c.put(packet,struct.pack('>hhhhh',x,y,0,0,0))
 assert call('player_step_init',{1:shadow,9:3,10:previous&0xffffffff})==0
 args={1:shadow,2:p,3:stages,4:h[0]+0x7a44,5:packet,6:candidate,9:tick};before=c.get(p,86),c.get(shadow,76)
 assert call('player_boundary_prepare',args)==0
 was=int.from_bytes(c.get(candidate+72,2),'big')
 applied=call('ground_deferred_step',{1:candidate,2:candidate+76,3:ground,4:event,9:was});assert applied in [0,1];resets+=applied
 assert before==(c.get(p,86),c.get(shadow,76)) and c.get(counter,4)==bytes(4)
 assert call('player_boundary_complete',args)==0
 assert call('ground_deferred_commit',{1:event,2:h[0]+0xa150,3:h[6]+0x42f6}) in [0,1]
 assert expected==(c.get(p,86),c.get(counter,4),c.get(h[6]+0x42f6,1)),n
 notifications+=int.from_bytes(expected[1],'big');before=c.get(p,86),c.get(shadow,76)
 assert call('player_boundary_complete',args)==0xffffffff and before==(c.get(p,86),c.get(shadow,76))
# Invalid interval, controls and late fractional state never publish.
bad=0
for kind in ['interval','control','late']:
 assert call('player_step_init',{1:shadow,9:50,10:0})==0;c.put(packet,bytes(10));before=c.get(p,86),c.get(shadow,76)
 args[9]=65536 if kind=='interval' else 1
 if kind=='control':c.put(packet,struct.pack('>h',2))
 result=call('player_boundary_prepare',args)
 if kind=='late':
  assert result==0;c.put(candidate+20,struct.pack('>i',32767))
 else:assert result==0xffffffff
 assert call('player_boundary_complete',args)==0xffffffff
 assert before==(c.get(p,86),c.get(shadow,76));bad+=1
r=dict(native_combined_ground_cases=4096,field_equivalence_steps=fields,ground_resets=resets,notifications=notifications,rollback_cases=bad,calls=calls,scope='combined clamp/attitude/split motion/deferred ground; native disturbance RNG disabled, notification UI stubbed; no world scheduler installation')
(root/'tmp/c/player-boundary-tests.json').write_text(json.dumps(r,indent=2)+'\n');print(r);c.close()
