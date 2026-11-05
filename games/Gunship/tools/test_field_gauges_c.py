"""Compare field gauge state and catch-up codes with native +ADB6."""
from unicorn_b import *
from layout import locate
from functools import lru_cache
import random,json
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks']
blob=bytes(BinFmt().load_image(str(build/'release/Gunship.Slave')).get_segments()[0].get_data());listing=(build/'release/Gunship.lst').read_text(encoding='latin1')
@lru_cache(None)
def sym(n):return int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
c=CPU();c.put(base,blob);c.put(0x200000,mem);c.put(h[0]+0x828a,bytes.fromhex('4e75'))
g=0x180000;raw=0x181000;out=0x182000;desc=h[6]+0x9bc;targets=h[6]+0x157d;rng=random.Random(582);calls=0
initial=c.get(desc,84)
def call(name,regs={},want=0):
 global calls
 saved={r:rng.randrange(0x1000000) for r in list(range(1,8))+list(range(10,17))};saved.update(regs)
 c.rw(17,0x2000)
 for r,v in saved.items():c.rw(r,v)
 c.rw(8,0x8f000);c.call(base+sym(name));calls+=1
 assert c.rr(18)==0x90000 and c.rr(8)==0x8f004
 assert c.rr(9)==want,(name,c.rr(9))
 assert all(c.rr(r)==v for r,v in saved.items() if r!=9),(name,'registers')
def native(slot,t):
 c.put(h[6]+0x4bb0,struct.pack('>H',slot));c.put(targets,t);c.rw(8,0x8f000);c.call(h[0]+0xadb6)
 assert c.rr(18)==0x90000
 return bytes(v for i in range(7) for v in c.get(desc+12*i+8,2))
steps=0;draws=0
for first in (0,1):
 for cadence in (1,3,10,25):
  c.put(desc,initial);call('gauge_field_init',{1:g,2:desc,9:first})
  physical=initial
  for field in range(250):
   t=bytes(rng.randrange(256) for i in range(7));c.put(raw,t)
   # Native reference draws every field, alternately to each buffer.
   expected=native((first+field)%2,t);reference=c.get(desc,84)
   call('gauge_field_step',{1:g,2:raw,3:desc})
   assert c.get(g+2,14)==expected,(first,cadence,field)
   assert c.get(desc,84)==reference and c.get(raw,7)==t
   steps+=1
   if field%cadence==0:
    private=c.get(g,16);c.put(out,b'\xa5'*7)
    call('gauge_field_targets',{1:g,2:desc,3:out});codes=c.get(out,7)
    latest=(first+field)%2
    for i,v in enumerate(codes):assert (v&31)*int.from_bytes(reference[12*i+6:12*i+8],'big')//32==expected[2*i+latest]
    # A skipped-render physical buffer catches all the way up in one draw.
    c.put(desc,physical);slot=draws%2;before=c.get(desc,84);native(slot,codes)
    for i in range(7):
     assert c.get(desc+12*i+8+slot,1)==bytes([expected[2*i+latest]])
     assert c.get(desc+12*i+9-slot,1)==before[12*i+9-slot:12*i+10-slot]
    physical=c.get(desc,84);c.put(desc,reference)
    assert c.get(g,16)==private
    draws+=1
# Every supported scale/height round trips; all seven slots checked.
roundtrips=0
for scale in range(1,33):
 for height in range(scale):
  for i in range(7):c.put(desc+12*i+6,struct.pack('>H',scale))
  c.put(g,b'\0\0'+bytes([height])*14)
  call('gauge_field_targets',{1:g,2:desc,3:out})
  assert all((v&31)*scale//32==height and v&128 for v in c.get(out,7));roundtrips+=1
# Invalid inputs preserve the whole output and state (including late failure).
invalid=0
for phase,scale,height in ((2,18,0),(65535,18,0),(0,0,0),(1,33,0),(0,65535,0),(0,18,18),(1,18,255)):
 c.put(desc,initial);c.put(g,struct.pack('>H',phase)+bytes(12)+bytes([height,height]));c.put(desc+6*12+6,struct.pack('>H',scale));c.put(out,b'\xa5'*7)
 state=c.get(g,16);d=c.get(desc,84)
 call('gauge_field_targets',{1:g,2:desc,3:out},0xfffffffd)
 assert c.get(out,7)==b'\xa5'*7 and c.get(g,16)==state and c.get(desc,84)==d;invalid+=1
for phase in (2,65535,0xffffffff):
 state=c.get(g,16);call('gauge_field_init',{1:g,2:desc,9:phase},0xfffffffd);assert c.get(g,16)==state;invalid+=1
for phase in (2,65535):
 c.put(g,struct.pack('>H',phase));state=c.get(g,16)
 call('gauge_field_step',{1:g,2:raw,3:desc},0xfffffffd);assert c.get(g,16)==state;invalid+=1
print(json.dumps(dict(status='passed',native_steps=steps,catchup_draws=draws,scale_height_roundtrips=roundtrips,atomic_rejections=invalid,calls=calls,scope='native gauge state; pixel writer stubbed')));c.close()
