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

cases=0
for rate,height,vertical,parity,rindex in itertools.product([50,60],[0,1,255,256,1023,1024],range(256),[0,1],[-1,0,1]):
 rem=rindex*(rate-1);delta=sb(vertical+parity+1)>>2
 # All tested heights avoid native word overflow: exact rational height,
 # floor at ground, then Euclidean quotient gives the integer/frac pair.
 total=max(0,height*rate+rem+3*delta);want,frac=divmod(total,rate)
 b=bytearray(86);b[62]=vertical;struct.pack_into('>H',b,12,parity);struct.pack_into('>H',b,28,height)
 c.put(p,b);c.put(S,struct.pack('>HHiiiHH',rate,0,rem,0,0,0,0))
 assert call('movement_height')==0
 assert int.from_bytes(c.get(p+28,2),'big')==want
 assert int.from_bytes(c.get(S+4,4),'big',signed=True)==frac
 assert int.from_bytes(c.get(S+2,2),'big')==int(height!=0 and want==0)
 cases+=1
r=dict(cases=cases,scope='exact rational height preserved, nonnegative fraction, integer and high-byte crossings, ground clamp/contact flags')
(root/'tmp/c/height-normalization-tests.json').write_text(json.dumps(r,indent=2)+'\n');print(r);c.close()
