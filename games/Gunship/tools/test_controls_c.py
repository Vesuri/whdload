import json,random,itertools
from unicorn_b import *
from layout import locate
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks'];c=CPU();c.put(0x200000,mem)
c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/controls.hunk')).get_segments()[0].get_data()))
listing=(root/'tmp/c/controls.lst').read_text();entry=base+int(re.search(r'^([0-9A-F]{8}) controls_from_history$',listing,re.M)[1],16)
record=0x310000;packet=0x320000;rng=random.Random(0x544a);count=bad=0
for x,y,upper in itertools.product([-1,0,1],[-1,0,1],[0,0xffffff,0xffff00,0x123456]):
 b=bytearray(rng.randbytes(40));struct.pack_into('>II',b,4,(upper<<8)|(x&255),(upper<<8)|(y&255));c.put(record,b)
 c.put(h[2]+8,b[4:12]);c.rw(8,0x8f000);c.call(h[0]+0x544a)
 expected=c.get(h[6]+0x4294,2);assert expected==bytes([x&255,y&255])
 c.put(packet-2,b'XX'+b'\xa5'*10+b'YY')
 regs={r:rng.randrange(0x1000000) for r in range(1,17) if r!=8};regs.update({1:record,2:packet})
 for r,v in regs.items():c.rw(r,v)
 c.rw(8,0x8f000);c.call(entry);assert c.rr(9)==0 and c.rr(8)==0x8f004
 assert all(c.rr(r)==v for r,v in regs.items() if r!=9)
 assert c.get(packet-2,14)==b'XX'+struct.pack('>hh',x,y)+bytes(6)+b'YY'
 assert c.get(record,40)==b;count+=1
for axis in [4,8]:
 for value in [2,127,128,254]:
  b=bytearray(40);b[axis+3]=value;c.put(record,b);before=c.get(packet-2,14)
  c.rw(1,record);c.rw(2,packet);c.rw(8,0x8f000);c.call(entry)
  assert c.rr(9)==0xffffffff and c.get(packet-2,14)==before and c.get(record,40)==b;bad+=1
r=dict(native_cases=count,invalid_direction_cases=bad,scope='native low-byte directions, upper-bit tolerance, zero impulses, read-only history and output guards')
(root/'tmp/c/controls-tests.json').write_text(json.dumps(r,indent=2)+'\n');print(r);c.close()
