"""Native allocation ABI plus generation stamping, lifecycle ownership, wrap."""
from unicorn_b import *
from layout import locate
from functools import lru_cache
import random,json
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks']
blob=bytes(BinFmt().load_image(str(build/'release/Gunship.Slave')).get_segments()[0].get_data());listing=(build/'release/Gunship.lst').read_text(encoding='latin1')
@lru_cache(None)
def sym(n):return int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
def addr(n):return base+sym(n)
c=CPU();c.put(base,blob);c.put(0x200000,mem);arena=0x300000;resload=0x740000;mask=h[0]+0xba08;gen=arena+sym('RT_ACTOR_GENERATIONS');rng=random.Random(0xc6b)
c.put(addr('timing_runtime_arena'),struct.pack('>I',arena));c.put(arena,struct.pack('>I',1));c.put(arena+sym('RT_HUNKS'),struct.pack('>9I',*h));c.put(resload+0x64,bytes.fromhex('23c90075000023c8007500044e75'))
def regs():return {**{r:rng.randrange(0x1000000) for r in range(1,17)},8:0x8f000,17:rng.choice((0,31,0x2000,0x201f))}
def run(entry,rs):
 c.rw(17,rs[17])
 for r,v in rs.items():
  if r!=17:c.rw(r,v)
 c.put(0x90000,bytes.fromhex('40f900730000'));c.call(entry,end=0x90006);assert c.rr(18)==0x90006
 result={r:c.rr(r) for r in range(1,18)};result[17]=int.from_bytes(c.get(0x730000,2),'big');return result
rs=regs();rs.update({1:arena,3:resload})
for enabled in (0,1):
 c.put(addr('_custom1'),struct.pack('>I',enabled));c.put(0x750000,bytes(8));assert run(addr('timing_actor_generation_install'),rs)[9]==0
 if enabled:
  image,patch=struct.unpack('>II',c.get(0x750000,8));command,off,rel=struct.unpack('>HHh',c.get(patch,6));assert (image,command,off,patch+rel)==(h[0],0x8002,0xbea8,addr('timing_actor_allocate'))
 else:assert c.get(0x750000,8)==bytes(8)
rejects=0
for off in range(44):
 address=h[0]+0xbea8+off;saved=c.get(address,1);c.put(address,bytes([saved[0]^1]));before=c.get(addr('timing_actor_native_allocator'),44);c.put(0x750000,bytes(8))
 assert run(addr('timing_actor_generation_install'),rs)[9]==0xffffffff
 assert c.get(addr('timing_actor_native_allocator'),44)==before and c.get(0x750000,8)==bytes(8)
 c.put(address,saved);rejects+=1
c.put(arena,bytes(4));assert run(addr('timing_actor_generation_install'),rs)[9]==0xffffffff;c.put(arena,struct.pack('>I',1))
cases=0
for occupied in range(64):
 for owner,boundary,tracked in ((0,0,False),(1,0,True),(0,4,True),(1,4,False),(0,2,False),(0,6,False)):
  for flags in (0,31,0x2000,0x201f):
   rs=regs();rs[17]=flags;c.put(mask,struct.pack('>HH',occupied,0x1357));want=run(h[0]+0xbea8,rs);want_mask=c.get(mask,4)
   c.put(mask,struct.pack('>HH',occupied,0x1357));c.put(arena+sym('RT_CAPTURE_OWNER'),struct.pack('>H',owner));c.put(arena+sym('RT_BOUNDARY_PHASE'),struct.pack('>H',boundary))
   generations=[rng.randrange(10000) for _ in range(6)];before=struct.pack('>6IH',*generations,0);c.put(gen,before)
   got=run(addr('timing_actor_allocate'),rs)
   assert got==want and c.get(mask,4)==want_mask,(occupied,owner,boundary,flags,got,want)
   if tracked and got[9]:generations[got[9]-1]+=1
   assert c.get(gen,26)==struct.pack('>6IH',*generations,0)
   cases+=1
# Never recycle a generation number on arithmetic overflow; stop prediction
# for the exhausted slot until lifecycle resets both stamps and history.
c.put(arena+sym('RT_CAPTURE_OWNER'),b'\0\1');c.put(arena+sym('RT_BOUNDARY_PHASE'),bytes(2))
for slot in range(6):
 c.put(gen,bytes(26));c.put(gen+slot*4,b'\xff'*4)
 for repeat in range(2):
  c.put(mask,struct.pack('>HH',63^(1<<slot),0));rs=regs();got=run(addr('timing_actor_allocate'),rs)
  assert got[9]==slot+1 and c.get(gen+slot*4,4)==b'\xff'*4
  assert c.get(gen+24,2)==struct.pack('>H',1<<slot)
# A complete native free/reuse inside one interval gets two generations.
c.put(gen,bytes(26));c.put(mask,bytes(4));rs=regs();assert run(addr('timing_actor_allocate'),rs)[9]==6;before=c.get(mask,2)
c.rw(17,0x2000);c.rw(14,5);c.rw(8,0x8f000);c.call(h[0]+0xc45e,end=h[0]+0xc46c)
assert run(addr('timing_actor_allocate'),rs)[9]==6 and c.get(mask,2)==before and c.get(gen+20,4)==struct.pack('>I',2)
# Standalone helper must ignore failed/out-of-domain results without writes.
for value in (0,7,65535,0xffffffff):
 before=c.get(gen,26);rs=regs();rs.update({1:gen,9:value});got=run(addr('actor_generation_record'),rs)
 assert all(got[r]==(0x8f004 if r==8 else rs[r]) for r in range(1,17)) and c.get(gen,26)==before
# Execute each actual constructor's JSR through a patched allocator entry.
# Fresh CPU avoids reusing a translation of the earlier native reference.
saved_code=c.get(base,len(blob));saved_arena=c.get(arena,sym('RT_ARENA_SIZE'));c.close();c=CPU();c.put(base,saved_code);c.put(0x200000,mem);c.put(arena,saved_arena)
c.put(h[0]+0xbea8,bytes.fromhex('4ef9')+struct.pack('>I',addr('timing_actor_allocate')))
c.put(gen,bytes(26));c.put(mask,bytes(4))
for index,site in enumerate((0x9a1e,0x9b9a,0xbade)):
 c.rw(17,0x2000);c.rw(8,0x8f000);c.call(h[0]+site,end=h[0]+site+6)
 assert c.rr(18)==h[0]+site+6 and c.rr(9)==6-index
 assert c.get(gen+4*(5-index),4)==struct.pack('>I',1)
print(json.dumps(dict(status='passed' ,native_abi_cases=cases,signature_rejections=rejects,overflow_cases=12,same_mask_reuse_stamped=True,invalid_results_ignored=4,constructor_call_sites=3)));c.close()
