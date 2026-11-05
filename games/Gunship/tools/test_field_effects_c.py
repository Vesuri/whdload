"""Native effect countdown/animation comparison and ownership ABI."""
from unicorn_b import *
from layout import locate
import json,random
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks']
blob=bytes(BinFmt().load_image(str(build/'release/Gunship.Slave')).get_segments()[0].get_data());listing=(build/'release/Gunship.lst').read_text(encoding='latin1')
def addr(n):return base+int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
c=CPU();c.put(0x200000,mem);c.put(base,blob);table=h[0]+0xc6d0;ARENA=0x300000
c.put(addr('timing_runtime_arena'),struct.pack('>I',ARENA));c.put(ARENA+addr('RT_HUNKS')-base,struct.pack('>9I',*h))
c.put(addr('timing_render_native_animation'),struct.pack('>I',h[0]+0xbe5a))
owner=ARENA+addr('RT_CAPTURE_OWNER')-base;phase=ARENA+addr('RT_BOUNDARY_PHASE')-base
rng=random.Random(0xbe5a)
def run(entry,rs):
 c.rw(17,rs[17])
 for r,v in rs.items():
  if r!=17:c.rw(r,v)
 c.put(0x90000,bytes.fromhex('40f900730000'));c.call(entry,end=0x90006)
 out={r:c.rr(r) for r in range(1,18)};out[17]=int.from_bytes(c.get(0x730000,2),'big');return out
# All frame/timer byte pairs, packed into six distinct slots per invocation.
pairs=[(f,t) for f in range(256) for t in range(256)];cases=0
for i in range(0,len(pairs),6):
 data=bytearray(rng.randbytes(90))
 for slot,(f,t) in enumerate(pairs[i:i+6]):data[6+slot]|=1;data[12+slot]=f;data[84+slot]=t
 c.put(table,data);c.rw(8,0x8f000)
 ok(u.uc_emu_start(c.h,h[0]+0x4c3e,h[0]+0x4c64,0,1000));c.call(h[0]+0xbe5a);want=c.get(table,90)
 c.put(table,data);rs={r:rng.randrange(0x1000000) for r in range(1,17)};rs.update({1:table,8:0x8f000,17:0x2000})
 got=run(addr('field_effects_step'),rs)
 assert c.get(table,90)==want,(i,bytes(data),c.get(table,90),want)
 assert all(got[r]==(0x8f004 if r==8 else rs[r]) for r in range(1,17))
 cases+=len(pairs[i:i+6])
# Mixed inactive slots, all incoming CCRs, native hook ABI and frozen modes.
abi=0
for flags in range(32):
 for n in range(16):
  data=rng.randbytes(90);rs={r:rng.randrange(0x1000000) for r in range(1,17)};rs.update({8:0x8f000,17:0x2000|flags})
  c.put(table,data);c.put(owner,bytes(2));c.put(phase,bytes(2));want=run(h[0]+0xbe5a,rs);wantmem=c.get(table,90)
  c.put(table,data);assert run(addr('timing_render_animation'),rs)==want and c.get(table,90)==wantmem
  # Native countdown reference uses supplied D0, not an assumed constant.
  ref=0x700000
  if flags==0 and n==0:c.put(ref,c.get(h[0]+0x4c40,36)+bytes.fromhex('4e75'))
  c.put(table,data);want=run(ref,rs);wantmem=c.get(table,90)
  c.put(table,data);assert run(addr('timing_vbl_effect_timers'),rs)==want and c.get(table,90)==wantmem
  for own,boundary in [(1,0)]+[(0,k) for k in range(1,7)]:
   c.put(owner,struct.pack('>H',own));c.put(phase,struct.pack('>H',boundary));c.put(table,data)
   assert run(addr('timing_vbl_effect_timers'),rs)==want and c.get(table,90)==data
   got=run(addr('timing_render_animation'),rs)
   assert all(got[r]==(0x8f004 if r==8 else rs[r]) for r in range(1,17)) and c.get(table,90)==data
   abi+=2
  c.put(owner,bytes(2));c.put(phase,bytes(2));c.put(table,data)
  ok(u.uc_emu_start(c.h,h[0]+0x4c3e,h[0]+0x4c64,0,1000));c.rw(8,0x8f000);c.call(h[0]+0xbe5a);wantmem=c.get(table,90)
  c.put(table,data);rs[1]=table;run(addr('field_effects_step'),rs);assert c.get(table,90)==wantmem
print(json.dumps(dict(status='passed',frame_timer_pairs=cases,suppressed_abi_cases=abi,mixed_slot_cases=512)))
c.close()
