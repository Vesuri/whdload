"""Private native actor preview: exact endpoints, no world writes, barriers."""
from unicorn_b import *
from layout import locate
from functools import lru_cache
import json,random
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks']
blob=bytes(BinFmt().load_image(str(build/'release/Gunship.Slave')).get_segments()[0].get_data());listing=(build/'release/Gunship.lst').read_text(encoding='latin1')
@lru_cache(None)
def sym(n):return int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
c=CPU();c.put(base,blob);c.put(0x200000,mem);ap=0x110000;p=h[6]+0x3b88;rng=random.Random(0xbed4)
size=sym('AP_CODE')+0xc69e-0xbed4;actors=sym('AP_ACTORS');player=sym('AP_PLAYER');code=sym('AP_CODE')
groups=[(0xba08,sym('AP_MASKS'),8),(0xaa0a,sym('AP_SELECTED'),12),(0xb92c,sym('AP_CLOSE'),1),(0x9c52,sym('AP_LOOKUP'),1),(0xc6a0,actors,0xc2)]
# Oracle stubs only: no actual sound or raster access. Both terrain returns
# are exercised below; positive-height preview must agree with either.
c.put(h[0]+0xa150,bytes.fromhex('4e75'));c.put(h[0]+0xb3b2,bytes.fromhex('70004e75'))
def call(name,args,want=None):
 regs={r:rng.randrange(0x1000000) for r in list(range(1,8))+list(range(10,17))};regs.update(args);c.rw(17,0x2000)
 for r,v in regs.items():c.rw(r,v)
 c.rw(8,0x8f000);c.call(base+sym(name));assert c.rr(18)==0x90000,(name,hex(c.rr(18)))
 if want is not None:assert c.rr(9)==want,(name,c.rr(9),want)
 assert all(c.rr(r)==v for r,v in regs.items() if r!=9),(name,'registers')
 return c.rr(9)
call('actor_preview_prepare',{1:h[0],2:h[6],3:ap},0)
MEM=C.CFUNCTYPE(None,C.c_void_p,C.c_int,C.c_uint64,C.c_int,C.c_int64,C.c_void_p)
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
checking=False;bad=[]
minus=CPU();minus.put(0x200000,mem);minus.put(h[0]+0xa150,bytes.fromhex('4e75'));minus.put(h[0]+0xb3b2,bytes.fromhex('70ff4e75'))
@MEM
def write(handle,kind,a,n,v,user):
 if checking and not(ap<=a and a+n<=ap+code or 0x8e000<=a and a+n<=0x8f004):bad.append((a,n))
hook=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hook),1<<11,write,None,1,0))
counts=dict(safe=0,rejected=0,terrain=0,decoy=0,expired=0,morphed=0)
for case in range(1200):
 ps=bytearray(rng.randbytes(0x2d6));ps[0x44:0x46]=bytes([case%2,case%3]);struct.pack_into('>HH',ps,0,12000,14000);struct.pack_into('>H',ps,28,3000);c.put(p,ps)
 data=bytearray(rng.randbytes(0xc2))
 mask=rng.randrange(64);eligible=rng.randrange(64)
 for slot in range(6):
  near=case%4==0
  for off,value in [(0,12000+rng.randrange(-128,128) if near else rng.randrange(30000)),(12,14000+rng.randrange(-128,128) if near else rng.randrange(30000)),(24,rng.choice([0,1,50,3000,32700])),(36,rng.randrange(-128,128)&65535)]:struct.pack_into('>H',data,off+2*slot,value)
  for off,value in [(0,rng.choice([0,1,2,64,200])),(6,rng.randrange(256)),(18,rng.randrange(256)),(24,240),(30,16),(36,0 if near else rng.randrange(128)),(42,rng.randrange(7)),(48,64),(54,rng.randrange(8)),(60,rng.randrange(8))]:data[0x30+off+slot]=value
 c.put(h[0]+0xc6a0,data);c.put(h[0]+0xba08,struct.pack('>4H',mask,0,eligible,0));c.put(h[0]+0xaa0a,struct.pack('>6H',rng.choice([0,1,65535]),0,0,0,0,rng.randrange(8)))
 c.put(h[6]+0x42e8,bytes([case%2,(case//2)%2]));before=c.get(0x97ee00,0x21200)
 c.rw(6,p);c.rw(8,0x8f000);c.call(h[0]+0xbed4);assert c.rr(18)==0x90000
 expected=[c.get(h[0]+off,n) for off,dst,n in groups];expected_p=c.get(p,0x2d6)
 c.put(0x97ee00,before);bad.clear();checking=True
 safe=call('actor_preview_step',{1:ap,2:p});checking=False
 assert not bad and c.get(0x97ee00,0x21200)==before,(case,bad)
 for (off,dst,n),want in zip(groups,expected):assert c.get(ap+dst,n)==want,(case,hex(off),c.get(ap+dst,n).hex(),want.hex())
 assert c.get(ap+player,0x2d6)==expected_p,(case,'player')
 uncertain=int.from_bytes(c.get(ap+sym('AP_UNCERTAIN'),2),'big');assert not safe&uncertain
 wantmask=mask&eligible&int.from_bytes(expected[0][:2],'big')&~uncertain&63
 for slot in range(6):
  oldtype=data[0x36+slot];newtype=expected[4][0x36+slot]
  if oldtype&1 or oldtype!=newtype or data[0x30+slot]<=1 or expected[4][0x30+slot]!=data[0x30+slot]-1:wantmask&=~(1<<slot)
  if mask&eligible&(1<<slot):
   counts['expired']+=data[0x30+slot]==1;counts['morphed']+=oldtype!=newtype
 if expected[4][0xc754-0xc6a0]:counts['decoy']+=1
 assert safe==wantmask,(case,safe,wantmask)
 # Separate emulator avoids changing already translated oracle code.
 minus.put(0x97ee00,before);minus.put(h[0]+0xb3b2,bytes.fromhex('70ff4e75'))
 minus.rw(6,p);minus.rw(8,0x8f000);minus.call(h[0]+0xbed4);assert minus.rr(18)==0x90000
 for slot in range(6):
  if safe&(1<<slot):
   for off in (0,12,24,36):assert minus.get(h[0]+0xc6a0+off+2*slot,2)==c.get(ap+actors+off+2*slot,2),(case,slot,'terrain -1')
   assert minus.get(h[0]+0xc6d0+18+slot,1)==c.get(ap+actors+0x30+18+slot,1)
 counts['safe']+=safe.bit_count();counts['rejected']+=(mask&eligible&~safe).bit_count();counts['terrain']+=uncertain.bit_count()
# A decoy hit leaves allocation/type intact but skips lifetime decrement.
ps=bytearray(0x2d6);struct.pack_into('>HH',ps,0,12000,14000);struct.pack_into('>H',ps,28,3000);ps[0x44:0x46]=bytes([1,1])
for hi,lo,v in [(0x56,0xd0,1000),(0xd6,0x150,1000),(0x250,0x1d0,500)]:ps[hi+1]=v>>8;ps[lo+1]=v&255
c.put(p,ps);data=bytearray(0xc2)
for off,v in [(0,1000),(12,1000),(24,500)]:struct.pack_into('>H',data,off,v)
for off,v in [(0,64),(6,0),(18,0),(24,240),(30,16),(36,1),(42,0),(48,255),(66,5)]:data[0x30+off]=v
c.put(h[0]+0xc6a0,data);c.put(h[0]+0xba08,struct.pack('>4H',1,0,1,0));c.put(h[6]+0x42e8,bytes(2))
before=c.get(0x97ee00,0x21200);checking=True
call('actor_preview_step',{1:ap,2:p},0);checking=False
assert c.get(ap+actors+0xc754-0xc6a0,1)==b'\1' and c.get(ap+sym('AP_MASKS'),2)==b'\0\1' and c.get(ap+actors+0x36,1)==b'\0'
assert c.get(0x97ee00,0x21200)==before and not bad
# Put the same real decoy-contact case in each slot, with five independent
# free-flight actors. Their native endpoints must remain available.
mixed_cases=0;retained=0
from itertools import combinations
for hits in [(i,) for i in range(6)]+list(combinations(range(6),2))+[tuple(range(6))]:
 hitmask=sum(1<<i for i in hits)
 data=bytearray(0xc2)
 for slot in range(6):
  for off,v in [(0,1000 if slot in hits else 6000+slot*300),(12,1000 if slot in hits else 7000),(24,500 if slot in hits else 3000)]:struct.pack_into('>H',data,off+2*slot,v)
  for off,v in [(0,64),(6,0 if slot in hits else 8),(18,0),(24,240),(30,16),(36,1 if slot in hits else 0),(42,0),(48,255 if slot in hits else 16),(66,5)]:data[0x30+off+slot]=v
 c.put(p,ps);c.put(h[0]+0xc6a0,data);c.put(h[0]+0xba08,struct.pack('>4H',63,0,63,0));c.put(h[6]+0x42e8,bytes(2))
 before=c.get(0x97ee00,0x21200)
 c.rw(6,p);c.rw(8,0x8f000);c.call(h[0]+0xbed4);expected=c.get(h[0]+0xc6a0,0xc2)
 assert expected[0xb4]==len(hits) and all(expected[0x30+hit]==64 for hit in hits)
 c.put(0x97ee00,before);bad.clear();checking=True
 call('actor_preview_step',{1:ap,2:p},63^hitmask);checking=False
 assert not bad and c.get(0x97ee00,0x21200)==before
 assert c.get(ap+actors,0xc2)==expected
 mixed_cases+=1;retained+=6-len(hits)
# Test the terrain stub independently across all six slots, both sides of
# zero, and the signed-word extrema. Positive height accepts either native
# terrain result; all other queries are explicitly unsafe.
for slot in range(6):
 for z in [-32768,-1,0,1,32767]:
  c.put(ap+sym('AP_UNCERTAIN'),bytes(2));c.put(0x120000+24,struct.pack('>h',z));call('actor_preview_terrain',{3:0x120000,7:ap,14:slot},0)
  assert int.from_bytes(c.get(ap+sym('AP_UNCERTAIN'),2),'big')==(1<<slot if z<=0 else 0)
# Every relocation is checked before any destination write.
relocs=c.get(base+sym('actor_preview_relocs'),sym('actor_preview_relocs_end')-sym('actor_preview_relocs'))
rejects=0
for off in [int.from_bytes(relocs[i:i+2],'big') for i in range(0,len(relocs),8)]+[0,0xc69e-0xbed4-2]:
 address=h[0]+0xbed4+off;old=c.get(address,2);c.put(address,bytes(v^1 for v in old));before=c.get(ap,size)
 call('actor_preview_prepare',{1:h[0],2:h[6],3:ap},0xffffffff);assert c.get(ap,size)==before
 c.put(address,old);rejects+=1
assert counts['safe'] and counts['terrain'] and counts['expired'] and counts['morphed']
print(json.dumps(dict(status='passed',native_steps=1200,slots=7200,counts=counts,terrain_stub_cases=30,signature_rejections=rejects,native_writes=0,context_size=size,unchanged_type_decoy_barrier=True,mixed_decoy_cases=mixed_cases,unrelated_slots_retained=retained,terrain_minus_one_steps=1200)));c.close();minus.close()
