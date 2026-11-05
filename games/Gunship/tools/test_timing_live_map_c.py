"""Native map-prefix preservation and field-owner exclusion."""
from unicorn_b import *
from layout import locate
import random,json
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks']
blob=bytes(BinFmt().load_image(str(build/'release/Gunship.Slave')).get_segments()[0].get_data());listing=(build/'release/Gunship.lst').read_text(encoding='latin1')
def addr(n):return base+int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
c=CPU();c.put(0x200000,mem);c.put(base,blob);arena=0x300000;resload=0x740000
c.put(addr('timing_runtime_arena'),struct.pack('>I',arena));c.put(arena,struct.pack('>I',1));c.put(arena+addr('RT_HUNKS')-base,struct.pack('>9I',*h))
c.put(resload+0x64,bytes.fromhex('23c90075000023c8007500044e75'))
rng=random.Random(0x489a);owner=arena+addr('RT_CAPTURE_OWNER')-base;phase=arena+addr('RT_BOUNDARY_PHASE')-base
# Sprite drawing intentionally stubbed; count calls without modifying flags.
c.put(h[0]+0x44dc,bytes.fromhex('4e75'));draws=0
CODE=C.CFUNCTYPE(None,C.c_void_p,C.c_uint64,C.c_uint32,C.c_void_p)
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
@CODE
def drawing(handle,a,n,user):
 global draws
 draws+=1
hook=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hook),1<<2,drawing,None,h[0]+0x44dc,h[0]+0x44dc))
def run(entry,rs,native=False):
 c.rw(17,rs[17])
 for r,v in rs.items():
  if r!=17:c.rw(r,v)
 c.put(0x90000,bytes.fromhex('40f900730000'))
 if native:
  c.call(entry,end=h[0]+0x48b6);ok(u.uc_emu_start(c.h,0x90000,0x90006,0,100));c.rw(8,0x8f004)
 else:c.call(entry,end=0x90006)
 out={r:c.rr(r) for r in range(1,18)};out[17]=int.from_bytes(c.get(0x730000,2),'big');return out
rs={r:0 for r in range(1,18)};rs.update({1:arena,3:resload,8:0x8f000,17:0x2000})
for enabled in (0,1):
 c.put(addr('_custom1'),struct.pack('>I',enabled));c.put(0x750000,bytes(8));assert run(addr('timing_map_install'),rs)[9]==0
 if enabled:
  image,patch=struct.unpack('>II',c.get(0x750000,8));cmd,off,rel,nops=struct.unpack('>HHhH',c.get(patch,8));assert image==h[0] and (cmd,off,nops)==(0x8010,0x489a,22) and patch+rel==addr('timing_map_frame') and c.get(patch+8,2)==bytes(2)
 else:assert c.get(0x750000,8)==bytes(8)
rejects=0
for off in range(0x489a,0x48b6,2):
 old=c.get(h[0]+off,2);c.put(h[0]+off,bytes(v^1 for v in old));c.put(0x750000,bytes(8));assert run(addr('timing_map_install'),rs)[9]==0xffffffff and c.get(0x750000,8)==bytes(8);c.put(h[0]+off,old);rejects+=1
c.put(arena,bytes(4));assert run(addr('timing_map_install'),rs)[9]==0xffffffff;c.put(arena,struct.pack('>I',1))
cases=0;suppressed=0
for counter in (0,1,6,7,8,32767,32768,65534,65535):
 for flags in range(32):
  c.put(h[5]+0x48,struct.pack('>H',counter));c.put(h[5]+0x4a,rng.randbytes(20));c.put(h[6]+0x3b88,rng.randbytes(4));initial=c.get(h[5]+0x48,22)
  rs={r:rng.randrange(0x1000000) for r in range(1,17)};rs.update({8:0x8f000,17:(0x2000 if flags&1 else 0)|flags})
  draws=0;want=run(h[0]+0x489a,rs,True);wantmem=c.get(h[5]+0x48,22);assert draws==1
  c.put(h[5]+0x48,initial);c.put(owner,bytes(2));c.put(phase,bytes(2));draws=0
  assert run(addr('timing_map_frame'),rs)==want and c.get(h[5]+0x48,22)==wantmem and draws==1
  cases+=1
  for own,boundary in [(1,0)]+[(0,k) for k in range(1,7)]:
   c.put(h[5]+0x48,initial);c.put(owner,struct.pack('>H',own));c.put(phase,struct.pack('>H',boundary));draws=0
   got=run(addr('timing_map_frame'),rs)
   assert c.get(h[5]+0x48,22)==initial and draws==1
   assert all(got[r]==(0x8f004 if r==8 else rs[r]) for r in range(1,17));suppressed+=1
print(json.dumps(dict(status='passed',native_cases=cases,suppressed_cases=suppressed,signature_rejections=rejects)));c.close()
