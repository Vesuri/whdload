"""Native weapon arithmetic with private fire/timestamps; target/UI stubs explicit."""
import json,random
from unicorn_b import *
from layout import locate
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks'];p=h[6]+0x3b88
c=CPU();c.put(0x200000,mem);c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/scheduled-guidance.hunk')).get_segments()[0].get_data()))
listing=(root/'tmp/c/scheduled-guidance.lst').read_text()
def sym(n):return base+int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
clone=0x330000;rc=0x340000;record=0x350000;fire=0x360000;rng=random.Random(0x979c);calls=0
# Target fixture selects slot 5. Actor updates, allocation, launch, recoil and
# resource accounting remain native; notification/UI/audio endpoints are stubs.
c.put(h[0]+0xc654,bytes.fromhex('70054e75'))
for off in [0xa150,0xaf36,0xb4e4,0xb57c]:c.put(h[0]+off,bytes.fromhex('4e75'))
def call(name,args):
 global calls
 regs={r:rng.randrange(0x1000000) for r in range(1,17) if r not in [8,9]};regs.update(args)
 for r,v in regs.items():c.rw(r,v)
 c.rw(8,0x8f000);c.call(sym(name));calls+=1
 assert c.rr(18)==0x90000 and c.rr(8)==0x8f004,(name,hex(c.rr(18)))
 assert all(c.rr(r)==v for r,v in regs.items() if r!=9),name
 return c.rr(9)
assert call('world_rng_prepare',{1:h[0]+0x7a5c,2:rc,3:record,4:h[2]})==0
assert call('world_weapons_prepare',{1:h[0],2:clone,3:rc,4:fire,5:h[6]})==0

TS=0x400000;TC=0x401000;TH=0x402000;CQ=0x404000;S=0x405000;SG=0x406000;FG=0x407000;PENDING=0x408000;START=0x409000
assert call('field_guidance_prepare',{1:h[0],2:FG,3:h[4],4:PENDING})==0
assert call('world_start_prepare',{1:h[0],2:START,3:h[6],4:p})==0
low=0x97ee00;length=0x21200;initial=c.get(low,length)
CODE=C.CFUNCTYPE(None,C.c_void_p,C.c_uint64,C.c_uint32,C.c_void_p)
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
trace=[]
@CODE
def event(handle,a,n,user):trace.append(a-h[0])
hooks=[]
for off in [0xbade,0xbf34,0xc3e0]:
 hook=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hook),1<<2,event,None,h[0]+off,h[0]+off));hooks.append(hook)

def ready():
 assert call('clock_init',{1:TC,9:0,10:50})==0
 assert call('history_init',{1:TH,9:0})==0
 assert call('commands_init',{1:CQ,9:0})==0
 assert call('scheduler_init',{1:TS,2:TC,3:TH,4:CQ})==0
 c.put(TS+12,b'\0\1');c.put(TS+24,struct.pack('>I',1));c.put(SG,struct.pack('>II',TS,FG)+bytes(8))
 c.put(h[4]+0x1c6,b'\0');c.put(h[0]+0xa44d,b'\0\1\0');c.put(h[0]+0xa436,b'\0');c.put(p+26,b'\0');c.put(PENDING,b'\xff')
ready();checks=0
@CODE
def fault(handle,a,n,user):
 global checks
 checks+=1
 if checks==2:c.put(TH+6,b'\0\1')
hook=C.c_size_t();entry=sym('scheduler_check');ok(u.uc_hook_add(c.h,C.byref(hook),1<<2,fault,None,entry,entry))
assert call('scheduled_guidance_step',{1:SG})==0xffffffff
assert c.get(SG+8,8)==struct.pack('>IHH',1,1,1) and c.get(h[0]+0xa44d,1)==b'\1'
assert call('scheduled_guidance_step',{1:SG})==0xffffffff
assert c.get(h[0]+0xa44d,1)==b'\1' and c.get(SG+14,2)==b'\0\0'
for kind in ['ready','world','fault']:
 ready()
 if kind=='fault':c.put(TH+6,b'\0\1')
 else:c.put(TS+12,struct.pack('>H',0 if kind=='ready' else 2))
 assert call('scheduled_guidance_step',{1:SG})==(0xffffffff if kind=='fault' else 0xfffffffd)
 assert c.get(SG+8,8)==bytes(8) and c.get(h[0]+0xa44d,1)==b'\0' and c.get(PENDING,1)==b'\xff'
print(json.dumps(dict(status='passed',post_effect_fault=True,retry_without_reapply=True,rejections=3,calls=calls)))
c.close()
