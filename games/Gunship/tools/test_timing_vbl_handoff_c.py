"""Native VBL versus installed ownership switch followed by field replay."""
import json
from unicorn_b import *
from layout import locate
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks']
blob=bytes(BinFmt().load_image(str(build/'release/Gunship.Slave')).get_segments()[0].get_data())
listing=(build/'release/Gunship.lst').read_text(encoding='latin1')
def addr(n):return base+int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
ARENA=0x300000;FG=0x330000;PENDING=0x340000
regions=[(h[6]+o,1) for o in (0x4296,0x42f6,0x42f7)]+[(h[0]+0xa44d,3),(h[0]+0xa436,1),(h[0]+0xba0c,4)]
lanes=[]
for lane in ('native','native_owner','runtime_owner'):
 c=CPU();c.put(0x200000,mem);c.put(base,blob)
 for off in (0xa88,0xb22,0x45b0,0xa2f0,0xa35a):c.put(h[0]+off,bytes.fromhex('4e75'))
 c.put(addr('timing_runtime_arena'),struct.pack('>I',ARENA));c.put(ARENA+addr('RT_HUNKS')-base,struct.pack('>9I',*h))
 c.put(addr('timing_vbl_native_guidance'),struct.pack('>I',h[0]+0xa1c8))
 def call(entry,regs):
  c.rw(17,0x2000)
  for r,v in regs.items():c.rw(r,v)
  c.rw(8,0x8f000);c.call(entry)
 if lane=='runtime_owner':
  call(addr('field_guidance_prepare'),{1:h[0],2:FG,3:h[4],4:PENDING});assert c.rr(9)==0
  c.put(ARENA+addr('RT_CAPTURE_OWNER')-base,b'\0\1')
 if lane!='native':
  for off,name in [(0x4ba8,'timer_weapon'),(0x4bba,'timer_ground'),(0x4c32,'timer_hit'),(0x4c12,'guidance')]:
   c.put(h[0]+off,bytes.fromhex('4eb9')+struct.pack('>I',addr('timing_vbl_'+name)))
 results=[]
 for quit in (0,1,2,127,128,255):
  for phase in (0,5,29,30,31,255):
   for value in (0,1,127,128,255):
    c.put(h[4]+0x1c6,bytes([quit]));c.put(h[6]+0x3b88+26,b'\0')
    for a,n in regions[:3]:c.put(a,bytes([value]))
    c.put(h[0]+0xa44d,bytes([phase,1,0]));c.put(h[0]+0xa436,b'\0');c.put(h[0]+0xba0c,struct.pack('>HH',0,1))
    c.put(h[0]+0xc757,b'\0');c.put(PENDING,b'\0')
    before=[c.get(a,n) for a,n in regions]
    c.rw(17,0x2000);c.rw(8,0x8f000);c.rw(6,h[6]+0x3b88)
    c.call(h[0]+0x4b48,end=h[0]+(0x4c3e if quit>=128 else 0x4c38))
    if lane=='runtime_owner':
     assert [c.get(a,n) for a,n in regions]==before,(quit,phase,value)
     call(addr('field_vbl_state'),{1:h[6],2:h[4],3:FG,6:h[6]+0x3b88})
    results.append([c.get(a,n) for a,n in regions]+[c.get(PENDING if lane=='runtime_owner' else h[0]+0xc757,1)])
 lanes.append(results);c.close()
assert lanes[0]==lanes[1]==lanes[2]
print(json.dumps(dict(status='passed',native_cases=len(lanes[0]),lanes=3,runtime_native_writes_suppressed=True)))
