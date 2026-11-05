from unicorn_b import *
from layout import locate
import random,json
from functools import lru_cache
# Captured chip bitmap addresses include $174xx. Keep synthetic code out of
# that native drawing surface; otherwise geometry-exit plotting corrupts it.
base=0x100000
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks'];p=h[6]+0x3b88
c=CPU();c.put(0x200000,mem);c.put(base,bytes(BinFmt().load_image(str(Path(os.environ.get('RUNTIME_FIXTURE',str(root/'tmp/c/runtime'))).with_suffix('.hunk'))).get_segments()[0].get_data()))
listing=(Path(os.environ.get('RUNTIME_FIXTURE',str(root/'tmp/c/runtime'))).with_suffix('.lst')).read_text()
@lru_cache(None)
def sym(n):return int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
ARENA=0x600000;TABLE=0x580000;SAMPLE=0x590000;size=sym('RT_ARENA_SIZE');rng=random.Random(803);calls=0
c.put(TABLE,struct.pack('>9I',*h));low=0x97ee00;length=0x21200
initial=c.get(low,length)
def ptr(n):return ARENA+sym('RT_'+n)
def word(a):return int.from_bytes(c.get(a,2),'big')
def long(a):return int.from_bytes(c.get(a,4),'big')
def call(n,args,expected=0):
 global calls
 regs={r:rng.randrange(0x1000000) for r in range(1,17) if r!=8};regs.update(args)
 for r,v in regs.items():c.rw(r,v&0xffffffff)
 c.rw(8,0x8f000);c.call(base+sym(n));calls+=1
 assert c.rr(18)==0x90000 and c.rr(8)==0x8f004,n
 assert c.rr(9)==expected,(n,c.rr(9),expected)
 assert all(c.rr(r)==v&0xffffffff for r,v in regs.items() if r!=9),(n,'registers')
MEM=C.CFUNCTYPE(None,C.c_void_p,C.c_int,C.c_uint64,C.c_int,C.c_int64,C.c_void_p)
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
checking=False;badwrites=[]
@MEM
def watch(handle,kind,a,n,value,user):
 if checking and not(ARENA<=a and a+n<=ARENA+size or 0x8e000<=a and a+n<=0x8f004):badwrites.append((a,n))
hook=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hook),1<<11,watch,None,1,0))
def prepare(rate,expected=0):
 global checking
 before=c.get(low,length);badwrites.clear();checking=True
 call('timing_runtime_prepare',{1:ARENA,2:TABLE,9:rate},expected)
 checking=False
 assert not badwrites,badwrites[:10]
 assert c.get(low,length)==before
 assert c.get(ARENA-16,16)==b'\xa5'*16 and c.get(ARENA+size,16)==b'\xa5'*16
 if expected==0:
  assert long(ptr('CONSUMER')+sym('TF_TARGET_ENTRY'))==base+sym('timing_runtime_target')
  assert long(ptr('CONSUMER')+sym('TF_TARGET_CONTEXT'))==ARENA
  # Execution fixtures cover the real callback/control flow. Unicorn has no
  # blitter; real pixel correctness is covered by the compiled guest probe.
# Loader-facing lookup publishes no partial table on invalid chain length.
c.put(TABLE,b'\xa5'*36)
call('timing_runtime_hunks',{1:h[0],2:TABLE})
assert c.get(TABLE,36)==struct.pack('>9I',*h)
for first in (0,h[0]+2):
 before=c.get(TABLE,36);call('timing_runtime_hunks',{1:first,2:TABLE},0xffffffff);assert c.get(TABLE,36)==before
for addr,value in ((h[0]-4,0),(h[8]-4,h[0]//4),(h[0]-4,0xc0000000)):
 saved=c.get(addr,4);before=c.get(TABLE,36);c.put(addr,struct.pack('>I',value))
 call('timing_runtime_hunks',{1:h[0],2:TABLE},0xffffffff);assert c.get(TABLE,36)==before;c.put(addr,saved)
c.put(ARENA-16,b'\xa5'*(size+32))
for rate in (0,3,49,61,0xffffffff):
 before=c.get(ARENA,size);prepare(rate,0xffffffff);assert c.get(ARENA,size)==before
for off in (0x7a5c,0x8050):
 saved=c.get(h[0]+off,4);c.put(h[0]+off,bytes(4));prepare(50,0xffffffff)
 assert long(ARENA)==0 and word(ptr('CLOCK')+24)==word(ptr('HISTORY')+4)==word(ptr('COMMANDS')+6)==0
 c.put(h[0]+off,saved)
runs=[]
for rate in (50,60):
 baseline=None
 for location in (0x600000,0x700000):
  ARENA=location;c.put(ARENA-16,b'\xa5'*(size+32));c.put(low,initial)
  b=bytearray(86);struct.pack_into('>HH',b,0,0x7000,0x8000);struct.pack_into('>H',b,28,4096);b[27]=128;b[57]=26;b[66]=28;b[65]=1;b[17]=2;c.put(p,b)
  prepare(rate)
  assert long(ARENA)==1
  assert word(ptr('CLOCK')+24)==word(ptr('HISTORY')+4)==word(ptr('COMMANDS')+6)==0
  # Every relative binding points into this arena, not the preparation fixture.
  for field,target in [('TF_SCHEDULER','SCHEDULER'),('TF_RECORD','RECORD'),('TF_ENDPOINT','PLAYER'),('TF_BODY','BODY')]:assert long(ptr('CONSUMER')+sym(field))==ptr(target)
  for off in [0xaf36,0xa150,0xb4e4,0xb57c,0xb0a6,0xb2e0]:c.put(h[0]+off,bytes.fromhex('4e75'))
  c.put(h[0]+0xc654,bytes.fromhex('70054e75'));c.put(h[0]+0x7fa4,bytes.fromhex('70004e75'))
  c.put(h[4]+0x1c5,bytes(2));c.put(h[4]+0x440,bytes(2));c.put(h[0]+0x9c42,bytes(1));c.put(h[0]+0xba08,bytes(4));c.put(h[0]+0xba0c,b'\xff\xff\xff\xff');c.put(h[6]+0x1558,bytes([99]*6));c.put(p+0x256+5,b'\1');c.put(h[0]+0xa44d,b'\xff\0\0');c.put(h[0]+0xa436,bytes(1))
  call('timing_resume',{1:ptr('SCHEDULER'),2:ptr('ENDPOINT'),9:1000,10:500,11:0})
  c.put(ptr('CAPTURE_OWNER'),b'\0\1')
  poses=[]
  for n in range(1,61):
   call('commands_publish',{1:ptr('COMMANDS'),9:500+n,10:[0x51,1,2,0x38][n%4]},1)
   c.put(SAMPLE,struct.pack('>6IHhhHII',1000+n,[0,1,0,255][n%4],0,0,0,500+n,8,0,0,0,10,n))
   call('history_publish',{1:ptr('HISTORY'),2:SAMPLE},1)
   call('scheduler_begin',{1:ptr('SCHEDULER'),9:128,10:8})
   call('scheduler_next',{1:ptr('SCHEDULER'),2:ptr('RECORD')},1)
   due=n*3//rate-(n-1)*3//rate
   call('timing_flight_consume',{1:ptr('CONSUMER'),9:128},due)
   poses.append((c.get(p,86),c.get(ptr('ENDPOINT'),164)))
  assert long(ptr('SCHEDULER')+32)==60 and long(ptr('SCHEDULER')+36)==180//rate
  if baseline is None:baseline=poses
  else:assert poses==baseline
  runs.append(dict(rate=rate,arena=hex(ARENA),fields=60,worlds=180//rate))
print(json.dumps(dict(status='passed',arena_bytes=size,calls=calls,runs=runs)));c.close()
