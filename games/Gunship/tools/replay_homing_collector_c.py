"""Trace original target collector decisions on captured pre-collection inputs."""
from unicorn_b import *
from capstone import *
import json,sys
listing=(build/'selector-combat.slave.lst').read_text(encoding='latin1');sym=lambda n:int(re.search(r'^([0-9A-F]{8}) '+n+'$',listing,re.M)[1],16)
CODE=C.CFUNCTYPE(None,C.c_void_p,C.c_uint64,C.c_uint32,C.c_void_p)
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
reports=[]
for folder in map(Path,sys.argv[1:]):
 for world in (27,28,45,46):
  d=folder/f'world-{world}';h=struct.unpack_from('>9I',(d/'arena.bin').read_bytes(),sym('RT_HUNKS'));c=CPU()
  for i in (0,2,4,5,6):c.put(h[i],(d/f'h{i}.bin').read_bytes())
  a5=int(re.search(r'^a5\s+0x([0-9a-f]+)',(d/'registers.txt').read_text(),re.M)[1],16)
  path=[]
  @CODE
  def trace(handle,a,n,user):path.append(a-h[0])
  hk=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hk),1<<2,trace,None,h[0]+0xa450,h[0]+0xa58a))
  before=c.get(h[0]+0xa99e,168);c.rw(6,a5);c.rw(8,0x8f000);c.call(h[0]+0xa450);assert c.rr(18)==0x90000
  after=c.get(h[0]+0xa99e,168);accepted=0xa500 in path
  assert int.from_bytes(after[2:4],'big')==int.from_bytes(before[2:4],'big')+accepted
  ins={i.address:i for i in Cs(CS_ARCH_M68K,CS_MODE_BIG_ENDIAN|CS_MODE_M68K_000).disasm((d/'h0.bin').read_bytes()[0xa450:0xa58c],0xa450)}
  decision=ins[path[-2]]
  reads=[]
  for off in path:
   i=ins[off]
   for address in re.findall(r'\$([0-9a-f]+)\.l',i.op_str):
    a=int(address,16)
    if h[0]<=a<h[0]+len((d/'h0.bin').read_bytes()):reads.append(dict(instruction=hex(off),hunk=0,offset=hex(a-h[0]),word=int.from_bytes((d/'h0.bin').read_bytes()[a-h[0]:a-h[0]+2],'big')))
    elif h[6]<=a<h[6]+len((d/'h6.bin').read_bytes()):reads.append(dict(instruction=hex(off),hunk=6,offset=hex(a-h[6]),word=int.from_bytes((d/'h6.bin').read_bytes()[a-h[6]:a-h[6]+2],'big')))
  original_path=list(path)
  depth=int.from_bytes((d/'h0.bin').read_bytes()[0x768e:0x7690],'big')//2
  boundary=[]
  for limit in (depth-1,depth):
   c.put(h[0]+0xa99e,before);c.put(h[0]+0xa99c,struct.pack('>H',limit));path.clear();c.rw(6,a5);c.rw(8,0x8f000);c.call(h[0]+0xa450)
   assert c.rr(18)==0x90000
   got=0xa500 in path;assert got==(limit==depth),(world,limit,path)
   boundary.append(dict(limit=limit,accepted=got))
  post=folder.parent/'homing-selection-pal-060'/f'world-{world}'/'h0.bin'
  post_limit=int.from_bytes(post.read_bytes()[0xa99c:0xa99e],'big')
  reports.append(dict(world=world,depth_half=depth,post_world_limit=post_limit,boundary_controls=boundary,accepted=accepted,terminal_instruction=hex(decision.address),terminal_operation=decision.mnemonic+' '+decision.op_str,path=[hex(v) for v in original_path],operands=reads));c.close()
(root/'tmp/c/homing-collector-decisions.json').write_text(json.dumps(reports,indent=2)+'\n')
print(json.dumps([dict(world=r['world'],accepted=r['accepted'],terminal=r['terminal_instruction'],operation=r['terminal_operation']) for r in reports],indent=2))
