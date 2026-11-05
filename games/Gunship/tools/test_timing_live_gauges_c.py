"""Gauge installer/native passthrough and private drawing ownership."""
from unicorn_b import *
from layout import locate
from functools import lru_cache
import random,json
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks']
blob=bytes(BinFmt().load_image(str(build/'release/Gunship.Slave')).get_segments()[0].get_data());listing=(build/'release/Gunship.lst').read_text(encoding='latin1')
@lru_cache(None)
def addr(n):return base+int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
c=CPU();c.put(0x200000,mem);c.put(base,blob);arena=0x300000;resload=0x740000;low=0x97ee00;length=0x21200;desc=h[6]+0x9bc;raw=h[6]+0x157d
c.put(addr('timing_runtime_arena'),struct.pack('>I',arena));c.put(arena,struct.pack('>I',1));c.put(arena+addr('RT_HUNKS')-base,struct.pack('>9I',*h))
c.put(resload+0x64,bytes.fromhex('23c90075000023c8007500044e75'));c.put(h[0]+0x828a,bytes.fromhex('4e75'))
rng=random.Random(0xadb6);owner=arena+addr('RT_CAPTURE_OWNER')-base;phase=arena+addr('RT_BOUNDARY_PHASE')-base;gauges=arena+addr('RT_GAUGES')-base
initial=c.get(desc,84)
def run(entry,rs):
 c.rw(17,rs[17])
 for r,v in rs.items():
  if r!=17:c.rw(r,v)
 c.put(0x90000,bytes.fromhex('40f900730000'));c.call(entry,end=0x90006)
 assert c.rr(18)==0x90006
 out={r:c.rr(r) for r in range(1,18)};out[17]=int.from_bytes(c.get(0x730000,2),'big');return out
rs={r:0 for r in range(1,18)};rs.update({1:arena,3:resload,8:0x8f000,17:0x2000})
for enabled in (0,1):
 c.put(addr('_custom1'),struct.pack('>I',enabled));c.put(0x750000,bytes(8));assert run(addr('timing_gauges_install'),rs)[9]==0
 if enabled:
  image,patch=struct.unpack('>II',c.get(0x750000,8));cmd,off,rel=struct.unpack('>HHh',c.get(patch,6));assert image==h[0] and (cmd,off)==(0x8002,0xadb6) and patch+rel==addr('timing_render_gauges') and c.get(patch+6,2)==bytes(2)
 else:assert c.get(0x750000,8)==bytes(8)
rejects=0
for off in range(0xadb6,0xadc6,2):
 old=c.get(h[0]+off,2);c.put(h[0]+off,bytes(v^1 for v in old));c.put(0x750000,bytes(8));assert run(addr('timing_gauges_install'),rs)[9]==0xffffffff and c.get(0x750000,8)==bytes(8);c.put(h[0]+off,old);rejects+=1
c.put(arena,bytes(4));assert run(addr('timing_gauges_install'),rs)[9]==0xffffffff;c.put(arena,struct.pack('>I',1))
cases=0;enhanced=0
for slot in (0,1):
 for flags in range(32):
  c.put(desc,initial);c.put(raw,rng.randbytes(16));c.put(h[6]+0x4bb0,struct.pack('>H',slot));native=c.get(low,length)
  rs={r:rng.randrange(0x1000000) for r in range(1,17)};rs.update({8:0x8f000,17:(0x2000 if flags&1 else 0)|flags})
  want=run(h[0]+0xadb6,rs);wantmem=c.get(low,length)
  c.put(low,native);c.put(owner,bytes(2));c.put(phase,bytes(2))
  assert run(addr('timing_render_gauges'),rs)==want and c.get(low,length)==wantmem;cases+=1
  for own,boundary in [(1,0)]+[(0,k) for k in range(1,7)]:
   c.put(low,native);c.put(owner,struct.pack('>H',own));c.put(phase,struct.pack('>H',boundary));c.put(gauges,b'\0\1'+bytes([3,8])*7)
   before=c.get(gauges,16);raw_before=c.get(raw,16)
   got=run(addr('timing_render_gauges'),rs)
   assert all(got[r]==(0x8f004 if r==8 else rs[r]) for r in range(1,17))
   assert c.get(raw,16)==raw_before and c.get(gauges,16)==before
   for i in range(7):
    assert c.get(desc+12*i+8+slot,1)==b'\3'
    assert c.get(desc+12*i+9-slot,1)==initial[12*i+9-slot:12*i+10-slot]
   enhanced+=1
print(json.dumps(dict(status='passed',native_cases=cases,enhanced_cases=enhanced,signature_rejections=rejects)));c.close()
