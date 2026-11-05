"""Native split-object store ABI, X preservation and private-preview exclusion."""
from unicorn_b import *
from layout import locate
from functools import lru_cache
import json,random
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks'];p=h[6]+0x3b88
blob=bytes(BinFmt().load_image(str(build/'release/Gunship.Slave')).get_segments()[0].get_data());listing=(build/'release/Gunship.lst').read_text(encoding='latin1')
@lru_cache(None)
def sym(n):return int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
c=CPU();c.put(base,blob);c.put(0x200000,mem);arena=0x600000;private=0x650000;resload=0x740000;oracle=0x720000;rng=random.Random(0x7bd0)
generation=arena+sym('RT_SCRIPT_GENERATION');owner=arena+sym('RT_CAPTURE_OWNER');phase=arena+sym('RT_BOUNDARY_PHASE')
c.put(arena,struct.pack('>I',1));c.put(arena+sym('RT_HUNKS'),struct.pack('>9I',*h));c.put(base+sym('timing_runtime_arena'),struct.pack('>I',arena))
c.put(resload+0x64,bytes.fromhex('23c90075000023c8007500044e75'))
original=c.get(h[0]+0x7bd0,74)
assert c.get(base+sym('timing_script_native_store'),74)==original
c.put(oracle,original)
def run(entry,regs,flags=False):
 c.rw(17,regs.get(17,0x2000))
 for r,v in regs.items():
  if r!=17:c.rw(r,v)
 c.rw(8,0x8f000)
 if flags:c.put(0x90000,bytes.fromhex('40f900730000'))
 c.call(entry,end=0x90006 if flags else 0x90000)
 assert c.rr(18)==(0x90006 if flags else 0x90000)
 result={r:c.rr(r) for r in range(1,18)}
 if flags:result[17]=int.from_bytes(c.get(0x730000,2),'big')
 return result
rs={1:arena,3:resload}
for enabled in (0,1):
 c.put(base+sym('_custom1'),struct.pack('>I',enabled));c.put(0x750000,bytes(8));got=run(base+sym('timing_script_generation_install'),rs);assert got[9]==0
 if enabled:
  image,patch=struct.unpack('>II',c.get(0x750000,8));cmd,off,rel=struct.unpack('>HHh',c.get(patch,6));assert image==h[0] and (cmd,off)==(0x8002,0x7bd0) and patch+rel==base+sym('timing_script_store')
 else:assert c.get(0x750000,8)==bytes(8)
rejects=0
for off in range(74):
 c.put(h[0]+0x7bd0+off,bytes([original[off]^1]));c.put(0x750000,bytes(8));assert run(base+sym('timing_script_generation_install'),rs)[9]==0xffffffff and c.get(0x750000,8)==bytes(8)
 c.put(h[0]+0x7bd0+off,original[off:off+1]);rejects+=1
c.put(arena,bytes(4));assert run(base+sym('timing_script_generation_install'),rs)[9]==0xffffffff;c.put(arena,struct.pack('>I',1))
# Patch before executing this address; native oracle is a separate exact copy.
c.put(h[0]+0x7bd0,bytes.fromhex('4ef9')+struct.pack('>I',base+sym('timing_script_store')))
cases=tracked=0
for slot in (0,1,5,6,127,128,255):
 for incoming in range(32):
  for state in [(1,0,False),(0,0,False),(0,4,False),(1,4,False),(0,1,False),(1,0,True)]:
   own,ph,priv=state;context=private if priv else p
   data=rng.randbytes(1024);c.put(context,data);c.put(owner,struct.pack('>H',own));c.put(phase,struct.pack('>H',ph));c.put(generation,struct.pack('>6IH',123,0,0,0,0,0,0))
   regs={r:rng.randrange(0x1000000) for r in range(1,17) if r!=8};regs.update({6:context,9:0x87654300|slot,17:(0x2000 if incoming&1 else 0)|incoming})
   expected=run(oracle,regs,True);written=c.get(context,1024);c.put(context,data)
   got=run(h[0]+0x7bd0,regs,True)
   assert got==expected,(slot,incoming,state,[(r,hex(got[r]),hex(expected[r])) for r in got if got[r]!=expected[r]])
   assert c.get(context,1024)==written
   stamp=slot==5 and not priv and (own,ph) in ((1,0),(0,4))
   assert c.get(generation,26)==struct.pack('>6IH',123+stamp,0,0,0,0,0,0),(slot,incoming,state)
   cases+=1;tracked+=stamp
# A remove/recreate pair with identical final split state must still differ.
c.put(owner,b'\0\1');c.put(phase,bytes(2));c.put(generation,bytes(26));c.put(p,bytes(1024));c.put(p+0x1e,b'\x12\x34');c.put(p+0x20,b'\x56\x78')
run(h[0]+0x7bd0,{6:p,9:5});pose=c.get(p+0x56,0x206)
c.put(p+0x1e,bytes(2));run(h[0]+0x7bd0,{6:p,9:5});c.put(p+0x1e,b'\x12\x34');run(h[0]+0x7bd0,{6:p,9:5})
assert c.get(p+0x56,0x206)==pose and int.from_bytes(c.get(generation,4),'big')==3
for incoming in (0,16,31):
 c.put(generation,struct.pack('>6IH',0xffffffff,0,0,0,0,0,0));data=c.get(p,1024)
 regs={6:p,9:5,17:incoming};expected=run(oracle,regs,True);c.put(p,data);got=run(h[0]+0x7bd0,regs,True)
 assert got==expected and c.get(generation,4)==b'\xff'*4 and c.get(generation+24,2)==b'\0\1'
 run(h[0]+0x7bd0,regs,True);assert c.get(generation,4)==b'\xff'*4
# Every native JSR site routes through the patched common entry.
for site in (0x58d4,0x59ca,0x7cce,0x7d4c,0x98bc,0x9dd2,0x9ede,0xa144):
 c.put(generation,bytes(26));c.rw(17,0x2010);c.rw(6,p);c.rw(9,5);c.rw(8,0x8f000);c.call(h[0]+site,end=h[0]+site+6)
 assert c.rr(18)==h[0]+site+6 and int.from_bytes(c.get(generation,4),'big')==1
# Exercise native creation and removal setup, not just the final JSR.
def fragment(entry,end,regs):
 c.put(generation,bytes(26));c.rw(17,0x2000);c.rw(6,p)
 for r,v in regs.items():c.rw(r,v)
 c.rw(8,0x8f000);c.call(h[0]+entry,end=h[0]+end)
 assert c.rr(18)==h[0]+end and int.from_bytes(c.get(generation,4),'big')==1
c.put(p,bytes(1024));c.put(h[6]+0x157b,b'\6');c.put(p+0x56+6,b'\x44');c.put(p+0xd6+6,b'\x55');c.put(p+0x256+6,b'\1')
fragment(0x59a0,0x59d0,{})
assert c.get(p+0x5b,1)==b'\x44' and c.get(p+0xdb,1)==b'\x55'
fragment(0x58c6,0x58da,{})
assert c.get(p+0x5b,1)==c.get(p+0xd5,1)==b'\0'
c.put(p+0x5b,b'\x44');fragment(0x7cb2,0x7cd4,{12:5})
assert c.get(p+0x5b,1)==c.get(p+0xd5,1)==c.get(p+0xdb,1)==c.get(p+0x155,1)==b'\0'
print(json.dumps(dict(status='passed' ,native_abi_cases=cases,tracked_writes=tracked,signature_rejections=rejects,all_ccr_combinations=True,private_preview_excluded=True,same_pose_recreation_stamped=True,overflow_cases=3,native_store_call_sites=8,native_spawn_removal_fragments=3)));c.close()
