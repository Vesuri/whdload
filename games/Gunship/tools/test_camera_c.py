#!/usr/bin/env python3
"""Connect scaled response/linear rates to native stages; prove h=1 and fractions."""
import json,random
from fractions import Fraction as F
from unicorn_b import *
from layout import locate
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks']
c=CPU();c.put(0x200000,mem);c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/camera.hunk')).get_segments()[0].get_data()))
listing=(root/'tmp/c/camera.lst').read_text()
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



shadow=0x330000;camera=0x340000;gauges=0x350001;packet=0x360000
native_cases=field_cases=0
for pitch in range(256):
 for heading in range(256):
  b=bytearray(rng.randbytes(86));b[54]=pitch;b[53]=heading;c.put(p,b)
  c.put(camera-2,b'XX'+rng.randbytes(12)+b'YY');assert call('player_step_init',{1:shadow,9:3,10:0})==0
  call('presentation_build',{1:p,2:gauges,3:camera,4:h[4]+0x1c8,9:0})
  expected=c.get(camera-2,16);before=c.get(p,86),c.get(shadow,76)
  assert call('player_camera_angles',{1:p,2:shadow,3:camera})==0
  assert c.get(camera-2,16)==expected and before==(c.get(p,86),c.get(shadow,76))
  native_cases+=1
for rate in [50,60]:
 for _ in range(6000):
  b=bytearray(rng.randbytes(86));c.put(p,b);raw=rng.randbytes(16);c.put(camera-2,raw)
  assert call('player_step_init',{1:shadow,9:rate,10:0})==0
  roll,pitch,conv=[rng.randrange(-rate+1,rate) for _ in range(3)];main=rng.randrange(-32766,32767)
  for off,value in [(4,roll),(8,pitch),(40,main),(44,conv)]:c.put(shadow+off,struct.pack('>i',value))
  before=c.get(p,86),c.get(shadow,76)
  headfrac=trunc((main*rate+conv)*256,32767*rate)
  expected=bytearray(raw);struct.pack_into('>HHH',expected,8,(-(((b[53]+b[26])&255)*256+headfrac))&65535,(sb(-b[54])*128-trunc(pitch*128,rate))&65535,(-b[55]*256-trunc(roll*256,rate))&65535)
  assert call('player_camera_angles',{1:p,2:shadow,3:camera})==0
  assert c.get(camera-2,16)==expected
  assert before==(c.get(p,86),c.get(shadow,76));field_cases+=1
# The first field of either stick direction must already alter camera angles.
first_fields=0
for rate in [50,60]:
 for x,y in [(-1,-1),(-1,1),(1,-1),(1,1)]:
  b=bytearray(86);struct.pack_into('>H',b,28,1024);b[27]=128;b[57]=26;b[66]=28;c.put(p,b)
  assert call('player_step_init',{1:shadow,9:rate,10:0})==0
  c.put(packet,struct.pack('>hhhhh',x,y,0,0,0));assert call('player_step',{1:shadow,2:p,3:stages,4:h[0]+0x7a44,5:packet})==0
  before=c.get(p,86),c.get(shadow,76),c.get(h[4]+0x3cc,4)
  assert call('player_camera_angles',{1:p,2:shadow,3:camera})==0
  angles=struct.unpack('>hhh',c.get(camera+6,6));assert angles[1]!=0 and angles[2]!=0,(rate,x,y,angles)
  assert (angles[1]>0)==(y>0) and (angles[2]>0)==(x<0)
  for _ in range(100):
   assert call('player_camera_angles',{1:p,2:shadow,3:camera})==0
   assert angles==struct.unpack('>hhh',c.get(camera+6,6))
  assert before==(c.get(p,86),c.get(shadow,76),c.get(h[4]+0x3cc,4));first_fields+=1
bad=0
for rate,off,value,size in [(50,0,49,2),(50,36,60,2),(50,4,50,4),(50,8,-50,4),(50,40,32767,4),(50,44,50,4),(3,40,1,4),(3,4,1,4)]:
 assert call('player_step_init',{1:shadow,9:rate,10:0})==0;c.put(shadow+off,(value&((1<<(size*8))-1)).to_bytes(size,'big'));before=c.get(camera-2,16),c.get(p,86),c.get(shadow,76)
 assert call('player_camera_angles',{1:p,2:shadow,3:camera})==0xffffffff
 assert before==(c.get(camera-2,16),c.get(p,86),c.get(shadow,76));bad+=1
r=dict(native_angle_cases=native_cases,fractional_model_cases=field_cases,first_field_control_cases=first_fields,invalid_states=bad,calls=calls,scope='camera angle words only; native h=1 and fractional field pitch policy; no live display latency claim')
(root/'tmp/c/camera-tests.json').write_text(json.dumps(r,indent=2)+'\n');print(r);c.close()
