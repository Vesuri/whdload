from unicorn_b import *
from layout import locate
import json
from functools import lru_cache
folder=root/'tmp/c/live-loop-collision-diag';mem=(folder/'fast.bin').read_bytes();addr=json.loads((folder/'addresses.json').read_text());h=locate(mem)['hunks'];listing=(build/'diag.slave.lst').read_text(encoding='latin1')
@lru_cache(None)
def sym(n):return int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
slave=addr['base'];arena=addr['arena'];clone=arena+sym('RT_SCENE');p=h[6]+0x3b88
probe=mem.index(b'GSCOLL01');player=mem[probe+20:probe+106]
CODE=C.CFUNCTYPE(None,C.c_void_p,C.c_uint64,C.c_uint32,C.c_void_p)
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
for mode in range(2):
 c=CPU();c.put(0x200000,mem);c.put(p,player);rows=[];hooks=[];ctx=clone+sym('SCENE_CONTEXT') if mode else h[6]+0x38f6
 @CODE
 def observe(handle,a,n,user):
  off=a-(clone-0x5a24 if mode else h[0])
  if off==0x5c5c:print('transform',mode,c.get(ctx,0x64).hex(),flush=True)
  elif off==0x63dc:rows.append([hex(c.rr(3)),c.get(ctx+0x50,6).hex()])
  elif off==0x6818:rows[-1]+=[hex(c.rr(2)),c.get(c.rr(2),1).hex()]
  elif off==0x6922:rows[-1]+=[c.get(ctx+0x62,1).hex()]
 for off in (0x5c5c,0x63dc,0x6818,0x6922):
  at=(clone-0x5a24 if mode else h[0])+off;hk=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hk),1<<2,observe,None,at,at));hooks.append(hk)
 def call(entry,end=0x90000):
  c.rw(8,0x8f000);c.call(entry,end);assert c.rr(18)==end,hex(c.rr(18))
 c.rw(1,p);c.rw(3,0x710000);call(slave+sym('native_camera_build'))
 if mode:
  c.put(clone+sym('SCENE_COORD'),c.get(h[6]+0x18dc,0xb8))
  c.rw(1,clone);c.rw(2,0x710000);c.rw(3,h[0]+0xc6a0);call(slave+sym('scene_private_step'))
 else:
  for site,op in ((0x5d20,'1239'),(0x68a2,'1439'),(0x68d2,'1439')):c.put(h[0]+site,bytes.fromhex(op)+struct.pack('>I',h[6]+0x3ce3))
  c.put(h[0]+0x63f8,bytes.fromhex('4e75'));c.put(h[0]+0xa450,bytes.fromhex('4e75'));c.put(h[0]+0x6372,bytes.fromhex('6000ffe8'))
  for r,v in {1:0x710000,2:h[0]+0xc6a0,3:h[6],4:ctx+14}.items():c.rw(r,v)
  call(slave+sym('scene_state_build'));c.put(ctx+0x5e,struct.pack('>I',h[6]+0x15dc));c.put(ctx+0x62,b'\0');c.rw(6,ctx)
  call(h[0]+0x5c2e,h[0]+0x5c5c);print('transform',mode,c.get(ctx,0x64).hex(),flush=True);call(h[0]+0x60a8);call(h[0]+0x6224)
 print('mode',mode,'flag',c.get(ctx+0x62,1).hex(),'rows',rows,flush=True)
 c.close()
