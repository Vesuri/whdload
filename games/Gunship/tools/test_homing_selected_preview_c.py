"""Compose private candidate certificate and selector-fed projectile preview."""
from unicorn_b import *
import json
base=0x100000;l=(root/'tmp/c/runtime.lst').read_text();sym=lambda n:int(re.search(r'^([0-9A-F]{8}) '+n+'$',l,re.M)[1],16)
live=(build/'selector-combat.slave.lst').read_text(encoding='latin1');ls=lambda n:int(re.search(r'^([0-9A-F]{8}) '+n+'$',live,re.M)[1],16)
folder=root/'tmp/c/homing-selection-pal-060';rows=json.loads((root/'tmp/c/homing-impulse-envelope.json').read_text());reports=[]
MEM=C.CFUNCTYPE(None,C.c_void_p,C.c_int,C.c_uint64,C.c_int,C.c_int64,C.c_void_p)
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
for row in rows:
 if row['world']<27:continue
 world=row['world'];d=folder/f'world-{world}';a=(d/'arena.bin').read_bytes();h=struct.unpack_from('>9I',a,ls('RT_HUNKS'));c=CPU();c.put(0x200000,(folder/'fast.bin').read_bytes());c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/runtime.hunk')).get_segments()[0].get_data()))
 for i in (0,2,4,5,6):c.put(h[i],(d/f'h{i}.bin').read_bytes())
 ap=0x300000;target=0x310000;selected=0x320000
 def call(name,args):
  regs={r:0x1700+r for r in range(1,17) if r!=8};regs.update(args)
  for r,v in regs.items():c.rw(r,v)
  c.rw(8,0x8f000);c.call(base+sym(name));assert c.rr(18)==0x90000
  assert all(c.rr(r)==v for r,v in regs.items() if r!=9),name
  return c.rr(9)
 assert call('actor_preview_prepare',{1:h[0],2:h[6],3:ap})==0
 native={i:c.get(h[i],len((d/f'h{i}.bin').read_bytes())) for i in (0,2,4,5,6)};bad=[]
 @MEM
 def write(handle,kind,addr,n,value,user):
  if not(ap<=addr and addr+n<=ap+sym('AP_SIZE') or selected<=addr and addr+n<=selected+12 or 0x8e000<=addr and addr+n<=0x8f004):bad.append((hex(addr),n))
 hk=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hk),1<<11,write,None,1,0))
 legacy=call('actor_preview_step',{1:ap,2:h[6]+0x3b88});legacy_state=c.get(ap,sym('AP_SIZE'))
 c.put(selected,native[0][0xaa0a:0xaa16]);same=call('actor_preview_selected_step',{1:ap,2:h[6]+0x3b88,3:selected})
 assert same==legacy and c.get(ap,sym('AP_SIZE'))==legacy_state
 results=[]
 for branch in row['variants']:
  c.put(target+sym('WT_STATE'),bytes.fromhex(branch['candidate_state']))
  assert call('target_selector_single',{1:target,2:selected})==0
  sel=c.get(selected,12);mask=call('actor_preview_selected_step',{1:ap,2:h[6]+0x3b88,3:selected})
  assert c.get(selected,12)==sel
  assert mask&32,(world,mask)
  pose=[c.get(ap+sym('AP_ACTORS')+12*axis+10,2).hex() for axis in range(3)]
  n=(folder/f'world-{world+1}'/'h0.bin').read_bytes();want=[n[0xc6a0+12*axis+10:0xc6a0+12*axis+12].hex() for axis in range(3)]
  assert pose==want,(world,pose,want)
  assert all(c.get(h[i],len(v))==v for i,v in native.items()) and not bad,bad
  results.append(dict(impulses=branch['impulses'],selector=sel.hex(),pose=pose))
 reports.append(dict(world=world,branches=results,legacy_pose=[legacy_state[sym('AP_ACTORS')+12*axis+10:sym('AP_ACTORS')+12*axis+12].hex() for axis in range(3)]));c.close()
report=dict(status='passed',worlds=len(reports),branches=sum(len(r['branches']) for r in reports),native_writes=0,legacy_equal_with_native_selector=True,reports=reports)
(root/'tmp/c/homing-selected-preview-test.json').write_text(json.dumps(report,indent=2)+'\n');print({k:v for k,v in report.items() if k!='reports'})
