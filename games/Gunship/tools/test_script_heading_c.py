"""Renderer heading hook ABI and committed-world exclusion."""
from pathlib import Path
exec(Path(__file__).with_name('test_script_generation_c.py').read_text().split('rs={')[0])
rs={1:arena,3:resload}
for enabled in (0,1):
 c.put(base+sym('_custom1'),struct.pack('>I',enabled));c.put(0x750000,bytes(8))
 assert run(base+sym('timing_script_heading_install'),rs)[9]==0
 assert bool(c.get(0x750000,8)!=bytes(8))==bool(enabled)
 if enabled:
  image,patch=struct.unpack('>II',c.get(0x750000,8));assert image==h[0]
  for i,(off,dst) in enumerate([(0x5d20,1),(0x68a2,2),(0x68d2,2)]):
   cmd,got,rel=struct.unpack('>HHh',c.get(patch+6*i,6));assert (cmd,got)==(0x8003,off) and patch+rel==base+sym('timing_script_heading_d'+str(dst))
  assert c.get(patch+18,2)==bytes(2)
originals={off:c.get(h[0]+off,6) for off in (0x5d20,0x68a2,0x68d2)}
rejects=0
for off,data in originals.items():
 for byte in range(6):
  c.put(h[0]+off+byte,bytes([data[byte]^1]));c.put(0x750000,bytes(8))
  assert run(base+sym('timing_script_heading_install'),rs)[9]==0xffffffff and c.get(0x750000,8)==bytes(8)
  c.put(h[0]+off,data);rejects+=1
c.put(arena,bytes(4));assert run(base+sym('timing_script_heading_install'),rs)[9]==0xffffffff;c.put(arena,struct.pack('>I',1))
pose=arena+sym('RT_SCRIPT_POSE')+6
cases=0
states=[(1,1,0,2,1),(1,1,0,1,1),(1,1,0,2,0),(1,1,0,2,2),(1,0,0,2,1),(1,0,4,1,1),(1,1,4,2,1),(0,1,0,2,1)]
for dst in (1,2):
 oracle=0x720000+dst*32
 # Separate native and predicted-byte oracle loads preserve all flags exactly.
 c.put(oracle,struct.pack('>HIH',0x1039+dst*0x200,p+0x15b,0x4e75))
 c.put(oracle+16,struct.pack('>HIH',0x1039+dst*0x200,pose,0x4e75))
 for state in states:
  ready,own,bound,target,view=state
  c.put(arena,struct.pack('>I',ready));c.put(owner,struct.pack('>H',own));c.put(phase,struct.pack('>H',bound))
  c.put(arena+sym('RT_TARGET_PHASE'),struct.pack('>H',target));c.put(arena+sym('RT_VIEW_PHASE'),struct.pack('>H',view))
  for heading in (0,1,127,128,255):
   c.put(p+0x15b,bytes([heading]));c.put(pose,bytes([heading^128]))
   before=c.get(p,0x2d6)
   for incoming in range(32):
    regs={r:rng.randrange(0xffffffff) for r in range(1,17) if r!=8};regs[17]=(0x2000 if incoming&1 else 0)|incoming
    expected=run(oracle+(16 if state==states[0] else 0),regs,True)
    actual=run(base+sym('timing_script_heading_d'+str(dst)),regs,True)
    assert actual==expected,(dst,state,heading,incoming,actual,expected)
    assert c.get(p,0x2d6)==before;cases+=1
print(json.dumps(dict(status='passed',native_abi_cases=cases,signature_rejections=rejects,all_ccr=True,world_player_writes=0)))
c.close()
