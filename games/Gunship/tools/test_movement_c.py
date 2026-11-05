#!/usr/bin/env python3
"""Native height/coordinate equivalence and field-rate boundary ordering."""
import json,random,itertools
from unicorn_b import *
from layout import locate
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks'];p=h[6]+0x3b88;S=0x320000
c=CPU();c.put(0x200000,mem);c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/movement.hunk')).get_segments()[0].get_data()))
listing=(root/'tmp/c/movement.lst').read_text()
def sym(n):return int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
for addr,start,end in [(0x330000,0x9576,0x959c),(0x330100,0x9672,0x96fe)]:c.put(addr,c.get(h[0]+start,end-start)+bytes.fromhex('4e75'))
sine=struct.unpack('>256h',c.get(h[4]+0x1c8,512));rng=random.Random(0x969a);calls=0
sb=lambda x:(x&255)-256 if x&128 else x&255
sw=lambda x:(x&65535)-65536 if x&32768 else x&65535
trunc=lambda n,d:-(abs(n)//d) if n<0 else n//d
def call(name,d0=0):
 global calls
 regs={r:rng.randrange(0x1000000) for r in range(1,17) if r!=8};regs.update({1:S,2:p,3:h[0]+0x7a44,9:d0&0xffffffff})
 for r,v in regs.items():c.rw(r,v)
 c.rw(8,0x8f000);c.call(base+sym(name));calls+=1
 assert c.rr(18)==0x90000 and c.rr(8)==0x8f004
 assert all(c.rr(r)==v for r,v in regs.items() if r!=9)
 return c.rr(9)
height_cases=0
for vertical,parity,height in itertools.product(range(256),[0,1],[0,1,7,127,256,32760,32767,32768,65535]):
 b=bytearray(86);b[0x3e]=vertical;struct.pack_into('>H',b,12,parity);struct.pack_into('>H',b,28,height);c.put(p,b)
 c.rw(8,0x8f000);c.rw(6,p);c.call(0x330000);expected=c.get(p,86)
 c.put(p,b);assert call('movement_init',3)==0 and call('movement_height')==0
 assert c.get(p,86)==expected
 newheight=int.from_bytes(expected[28:30],'big');assert int.from_bytes(c.get(S+16,2),'big')==int(height!=0)
 assert int.from_bytes(c.get(S+2,2),'big')==int(height!=0 and newheight==0)
 height_cases+=1
coord_cases=0;edges=[0,0x17ff,0x1800,0x1801,0xd7ff,0xd800,0xd801,0xffff]
for coarse,angle in itertools.product(range(-128,128),range(256)):
 b=bytearray(86);speed=coarse*4+rng.randrange(4);struct.pack_into('>h',b,0x2a,speed);b[0x3d]=angle
 struct.pack_into('>HH',b,0,edges[angle%8],edges[coarse%8]);struct.pack_into('>H',b,0x1c,128 if angle&1 else 0)
 b[0x14]=rng.randrange(256);b[0x15]=rng.randrange(256);c.put(p,b)
 c.rw(8,0x8f000);c.rw(6,p);c.rw(9,speed&0xffffffff);c.call(0x330100);expected=c.get(p,86)
 c.put(p,b);assert call('movement_init',3)==0 and call('movement_horizontal')==0
 assert c.get(p,86)==expected,(coarse,angle,c.get(p,86).hex(),expected.hex())
 coord_cases+=1
# Independent native-width arithmetic with rational scaling and shared axis debt.
field_cases=0
for rate in [50,60]:
 for _ in range(4000):
  b=bytearray(rng.randbytes(86));height=int.from_bytes(b[28:30],'big');contact=rng.randrange(2);rh,rx,ry=[rng.randrange(-rate+1,rate) for _ in range(3)]
  c.put(p,b);c.put(S,struct.pack('>HHiiiHH',rate,contact,rh,rx,ry,rng.randrange(2),0))
  def scale(delta,rem):
   total=delta*3+rem;q=trunc(total,rate);return q,total-q*rate
  delta=sb(b[0x3e]+(int.from_bytes(b[12:14],'big')&1)+1)>>2
  q,rh=scale(delta,rh);nh=sw(height+q)
  if nh<0 or nh==0 and rh<0:nh=0;rh=0
  if rh<0:nh-=1;rh+=rate
  struct.pack_into('>H',b,28,nh);contact|=int(height!=0 and nh==0)
  assert call('movement_height')==0 and c.get(p,86)==b
  assert c.get(S,20)==struct.pack('>HHiiiHH',rate,contact,rh,rx,ry,int(height!=0),0)
  coarse=sb(sw(int.from_bytes(b[42:44],'big'))>>2);b[0x50]=coarse&255
  def coord(off,angle,rem):
   q,rem=scale((coarse*sine[angle&255])>>15,rem);v=(int.from_bytes(b[off:off+2],'big')+q)&65535
   if v<0x1800:v=0x1800;rem=0
   elif v>0xd800:v=0xd800;rem=0
   elif v==0x1800 and rem<0 or v==0xd800 and rem>0:rem=0
   struct.pack_into('>H',b,off,v);return rem
  rx=coord(0,b[0x3d],rx);ry=coord(2,b[0x3d]+64,ry)
  if nh:
   for off,wind,rem in [(0,b[0x14],rx),(2,b[0x15],ry)]:
    q,rem=scale(sb(wind),rem);struct.pack_into('>H',b,off,(int.from_bytes(b[off:off+2],'big')+q)&65535)
    if off==0:rx=rem
    else:ry=rem
  assert call('movement_horizontal')==0 and c.get(p,86)==b
  assert c.get(S,20)==struct.pack('>HHiiiHH',rate,contact,rh,rx,ry,int(height!=0),0)
  before=c.get(S,20);call('movement_ack_contact');assert c.get(S,20)==before[:2]+bytes(2)+before[4:]
  field_cases+=1
invalid=0
for off,val in [(4,50),(8,-50),(12,-2147483648)]:
 assert call('movement_init',50)==0;c.put(S+off,struct.pack('>i',val))
 for name in ['movement_height','movement_horizontal']:
  before=(c.get(p,86),c.get(S,20));assert call(name)==0xffffffff
  assert before==(c.get(p,86),c.get(S,20));invalid+=1
r=dict(native_height_cases=height_cases,native_horizontal_cases=coord_cases,field_model_cases=field_cases,invalid_state_cases=invalid,calls=calls,scope='native-quantized movement scaled per field; contact flags only, no world contact decisions')
(root/'tmp/c/movement-tests.json').write_text(json.dumps(r,indent=2)+'\n');print(r);c.close()
