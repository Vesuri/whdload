"""Native/field/world target permissions and exact skip register behavior."""
from unicorn_b import *
import random,json,struct
blob=bytes(BinFmt().load_image(str(build/'release/Gunship.Slave')).get_segments()[0].get_data());listing=(build/'release/Gunship.lst').read_text(encoding='latin1')
def sym(n):return int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
c=CPU();c.put(base,blob);arena=0x300000;counter=0x750000;stub=0x740000
c.put(base+sym('timing_runtime_arena'),struct.pack('>I',arena))
c.put(stub,bytes.fromhex('52b900750000203c123456784e75'))
for n in ('collect','select'):c.put(base+sym('timing_render_native_'+n),struct.pack('>I',stub))
rng=random.Random(231);cases=0
for n in ('collect','select'):
 for owner in (0,1):
  for boundary in range(7):
   for phase in range(4):
    for sr in (0,0x1f,0x2000,0x201f):
     c.put(arena+sym('RT_CAPTURE_OWNER'),struct.pack('>H',owner));c.put(arena+sym('RT_BOUNDARY_PHASE'),struct.pack('>H',boundary));c.put(arena+sym('RT_TARGET_PHASE'),struct.pack('>H',phase));c.put(counter,bytes(4))
     regs={r:rng.randrange(0x1000000) for r in range(1,17)};regs[8]=0x8f000
     c.rw(17,sr)
     for r,v in regs.items():c.rw(r,v)
     c.put(0x90000,bytes.fromhex('40f900730000'));c.call(base+sym('timing_render_'+n),end=0x90006)
     native=boundary==0 and (owner==0 or n=='collect' and phase==1) or n=='collect' and boundary==4 and owner==0 and phase==1
     assert int.from_bytes(c.get(counter,4),'big')==int(native),(n,owner,boundary,phase)
     assert all(c.rr(r)==(0x8f004 if r==8 else 0x12345678 if r==9 and native else v) for r,v in regs.items())
     if not native:assert int.from_bytes(c.get(0x730000,2),'big')&16==sr&16
     cases+=1
print(json.dumps(dict(status='passed',ownership_and_abi_cases=cases)));c.close()
