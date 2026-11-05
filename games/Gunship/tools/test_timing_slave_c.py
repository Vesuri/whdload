from unicorn_b import *
from layout import locate
import random,json
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks']
c=CPU();c.put(0x200000,mem)
c.put(base,bytes(BinFmt().load_image(str(root/'tmp/build/release/Gunship.Slave')).get_segments()[0].get_data()))
listing=(root/'tmp/build/release/Gunship.lst').read_text(encoding='latin1')
def sym(n):return int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
def addr(n):return base+sym(n)
ARENA=0x600000;EXEC=0x150000;size=sym('RT_ARENA_SIZE');calls=0;rng=random.Random(112);allocations=[];frees=[];allocate=True
c.put(4,struct.pack('>I',EXEC));c.put(EXEC+sym('VBlankFrequency'),b'\x32')
CODE=C.CFUNCTYPE(None,C.c_void_p,C.c_uint64,C.c_uint32,C.c_void_p)
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
aalloc=EXEC-198;afree=EXEC-210
c.put(aalloc,bytes.fromhex('4e75'));c.put(afree,bytes.fromhex('4e75'))
@CODE
def allocation(handle,a,n,user):
 if a==aalloc:
  allocations.append((c.rr(9),c.rr(10)));assert c.rr(9)==size and c.rr(10)==0x10001
  if allocate:c.put(ARENA,bytes(size));c.rw(9,ARENA)
  else:c.rw(9,0)
 else:frees.append((c.rr(2),c.rr(9)));assert frees[-1]==(ARENA,size)
hooks=[]
for a in (aalloc,afree):
 hh=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hh),1<<2,allocation,None,a,a));hooks.append(hh)
def long(a):return int.from_bytes(c.get(a,4),'big')
def word(a):return int.from_bytes(c.get(a,2),'big')
def call(name,args={}):
 global calls
 regs={r:rng.randrange(0x1000000) for r in range(1,17) if r!=8};regs.update(args)
 for r,v in regs.items():c.rw(r,v)
 c.rw(8,0x8f000);c.call(addr(name));calls+=1
 assert c.rr(18)==0x90000 and c.rr(8)==0x8f004,name
 assert all(c.rr(r)==v for r,v in regs.items()),(name,'registers')
RESLOAD=0x160000
c.put(RESLOAD+0x64,bytes.fromhex('4e75'))
def dispatch(pl='pl_gamemule_658'):call('timing_runtime_dispatch',{1:addr(pl),2:h[0],3:RESLOAD})
low=0x97ee00;length=0x21200;native=c.get(low,length)
# Disabled and other executables do not allocate or prepare anything.
c.put(addr('_custom1'),bytes(4));dispatch();assert not allocations and long(addr('timing_runtime_arena'))==0
c.put(addr('_custom1'),struct.pack('>I',1))
for pl in ('pl_gamemule_1489','pl_gamemule_german','pl_scrnmule_658'):dispatch(pl)
assert not allocations
# Unsupported rates and allocation failure remain explicit, inactive states.
c.put(EXEC+sym('VBlankFrequency'),b'\x31');dispatch();assert long(addr('timing_runtime_status'))==0xfffffffd and not allocations
c.put(EXEC+sym('VBlankFrequency'),b'\x32');allocate=False;dispatch();assert long(addr('timing_runtime_status'))==0xfffffffe and long(addr('timing_runtime_arena'))==0
allocate=True;dispatch();assert long(addr('timing_runtime_status'))==0 and long(addr('timing_runtime_arena'))==ARENA and long(ARENA)==1
assert word(ARENA+sym('RT_CLOCK')+24)==0 and word(ARENA+sym('RT_DRAW_READY'))==1
assert long(ARENA+sym('RT_DRAW_ENTRY'))==h[0]+0x5c04
# A rejected preparation must not admit the renderer.
original=c.get(h[0]+0x68d2,2);c.put(h[0]+0x68d2,b'\0\0')
dispatch();assert long(addr('timing_runtime_status'))==0xffffffff and word(ARENA+sym('RT_DRAW_READY'))==0
c.put(h[0]+0x68d2,original);dispatch();assert word(ARENA+sym('RT_DRAW_READY'))==1
# This instruction is validated by the VBL installer, after preparation.
original=c.get(h[0]+0x4ba8,2);c.put(h[0]+0x4ba8,b'\0\0')
dispatch();assert long(addr('timing_runtime_status'))==0xffffffff and long(ARENA)==1 and word(ARENA+sym('RT_DRAW_READY'))==0
c.put(h[0]+0x4ba8,original);dispatch();assert word(ARENA+sym('RT_DRAW_READY'))==1
allocated=len(allocations)
# New module load can reuse a paused allocation; never erase active/pending work.
dispatch();assert len(allocations)==allocated
for off in ('RT_CLOCK','RT_HISTORY','RT_COMMANDS','RT_SCHEDULER'):
 field={'RT_CLOCK':24,'RT_HISTORY':4,'RT_COMMANDS':6,'RT_SCHEDULER':12}[off]
 a=ARENA+sym(off)+field;c.put(a,b'\0\1');before=c.get(ARENA,size);dispatch();assert long(addr('timing_runtime_status'))==0xfffffffc and c.get(ARENA,size)==before;c.put(a,bytes(2))
c.put(EXEC+sym('VBlankFrequency'),b'\x3c');dispatch();assert word(ARENA+sym('RT_CLOCK')+22)==60
assert c.get(low,length)==native
call('timing_runtime_release');assert long(addr('timing_runtime_arena'))==0 and len(frees)==1
call('timing_runtime_release');assert len(frees)==1
print(json.dumps(dict(status='passed',calls=calls,allocation_attempts=len(allocations),frees=len(frees),native_unchanged=True)));c.close()
