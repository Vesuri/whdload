#!/usr/bin/env python3
"""Connect scaled response/linear rates to native stages; prove h=1 and fractions."""
import json,random
from fractions import Fraction as F
from unicorn_b import *
from layout import locate
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks']
c=CPU();c.put(0x200000,mem);c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/endpoint-ground-preview.hunk')).get_segments()[0].get_data()))
listing=(root/'tmp/c/endpoint-ground-preview.lst').read_text()
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


shadow=0x330000;packet=0x332000;binding=0x340000
# Complete native clamp + attitude + motion including ground, RNG eligibility disabled.
ground=0x360000;counter=0x370000;event=0x3a0000;clamp=0x3c0000
c.put(clamp,c.get(h[0]+0x5756,0x24)+bytes.fromhex('4e75'))
c.put(h[0]+0xa150,bytes.fromhex('52b9')+struct.pack('>I',counter)+bytes.fromhex('4e75'))
assert call('ground_deferred_prepare',{1:h[0],2:ground,3:h[6],4:event})==0
# Use a distinct never-executed reference clone with native ground restored.
whole_ground=0x3d0000;assert call('motion_preview_prepare',{1:h[0],2:whole_ground})==0
c.put(whole_ground+0x224,c.get(h[0]+0x95a0,4))
resets=notifications=0
for n in range(512):
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
 c.put(binding,struct.pack('>II',ground,event))
 args={1:shadow,2:p,3:stages,4:h[0]+0x7a44,5:packet,7:binding,9:tick}
 assert call('endpoint_ground_preview',args)==0
 assert c.get(counter,4)==bytes(4) and c.get(h[6]+0x42f6,1)==bytes(1)
 # A retained successful decision cannot be overwritten by another preview.
 before=c.get(p,86),c.get(shadow,76),c.get(event,4)
 assert call('endpoint_ground_preview',args)==0xffffffff
 assert before==(c.get(p,86),c.get(shadow,76),c.get(event,4))
 resets+=int(int.from_bytes(c.get(p+28,2),'big')==0)
 assert call('ground_deferred_commit',{1:event,2:h[0]+0xa150,3:h[6]+0x42f6}) in [0,1]
 assert expected==(c.get(p,86),c.get(counter,4),c.get(h[6]+0x42f6,1)),n
 notifications+=int.from_bytes(expected[1],'big');before=c.get(p,86),c.get(shadow,76)

# Invalid rate/control/tick and a late failure after private ground evaluation.
for kind in ['rate','control','tick','component']:
 c.put(event,bytes(4));c.put(packet,bytes(10));assert call('player_step_init',{1:shadow,9:50 if kind=='rate' else 3,10:0})==0
 if kind=='control':c.put(packet,struct.pack('>h',2))
 if kind=='component':c.put(shadow+12+24,struct.pack('>H',50)) # HG_RATE mismatch rejects private preparation
 before=c.get(p,86),c.get(shadow,76)
 assert call('endpoint_ground_preview',args|{9:65536 if kind=='tick' else 1})==0xffffffff,kind
 assert before==(c.get(p,86),c.get(shadow,76)) and c.get(event,4)==bytes(4)
print(dict(native_ground_previews=512,notifications=notifications,zero_height_endpoints=resets,rejection_cases=4,calls=calls))
c.close()
