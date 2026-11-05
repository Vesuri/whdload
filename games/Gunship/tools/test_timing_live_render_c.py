"""Native render effect ownership: exact baseline, no enhanced allocation/RNG."""
from unicorn_b import *
from layout import locate
import random,json,itertools
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks']
blob=bytes(BinFmt().load_image(str(build/'release/Gunship.Slave')).get_segments()[0].get_data());listing=(build/'release/Gunship.lst').read_text(encoding='latin1')
def addr(n):return base+int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
c=CPU();c.put(0x200000,mem);c.put(base,blob);ARENA=0x300000;low=0x97ee00;length=0x21200
c.put(addr('timing_runtime_arena'),struct.pack('>I',ARENA));c.put(addr('timing_render_native_effect'),struct.pack('>I',h[0]+0x9b9a))
owner=ARENA+addr('RT_CAPTURE_OWNER')-base;phase=ARENA+addr('RT_BOUNDARY_PHASE')-base
rng=random.Random(0x5c92);draws=0;checking=False;writes=[]
CODE=C.CFUNCTYPE(None,C.c_void_p,C.c_uint64,C.c_uint32,C.c_void_p)
MEM=C.CFUNCTYPE(None,C.c_void_p,C.c_int,C.c_uint64,C.c_int,C.c_int64,C.c_void_p)
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
@CODE
def draw(handle,a,n,user):
 global draws
 draws+=1
@MEM
def write(handle,kind,a,n,v,user):
 if checking and not(0x8e000<=a and a+n<=0x8f004 or a==0x730000 and n==2):writes.append((a,n))
hooks=[]
for kind,fn,start,end in [(1<<2,draw,h[0]+0x7a6a,h[0]+0x7a6a),(1<<11,write,1,0)]:
 hook=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hook),kind,fn,None,start,end));hooks.append(hook)
def run(entry,rs):
 c.rw(17,rs[17])
 for r,v in rs.items():
  if r!=17:c.rw(r,v)
 c.put(0x90000,bytes.fromhex('40f900730000'));c.call(entry,end=0x90006)
 out={r:c.rr(r) for r in range(1,18)};out[17]=int.from_bytes(c.get(0x730000,2),'big');return out
cases=0;suppressed=0
for mode,mask in itertools.product((0,1),range(64)):
 c.put(h[6]+0x45cc,bytes([mode]));c.put(h[0]+0xba08,struct.pack('>HH',mask,0));c.put(h[4]+0x3cc,rng.randbytes(4));c.put(h[0]+0xc6a0,rng.randbytes(0x90));c.put(h[2]+0x14,rng.randbytes(8))
 initial=c.get(low,length);rs={r:rng.randrange(0x1000000) for r in range(1,17)};rs.update({6:h[6]+0x38f6,8:0x8f000,17:(0x2000 if mode else 0)|(mask&31)})
 c.put(owner,bytes(2));c.put(phase,bytes(2));draws=0;want=run(h[0]+0x9b9a,rs);want_memory=c.get(low,length);want_draws=draws
 c.put(low,initial);draws=0;got=run(addr('timing_render_effect'),rs)
 assert got==want and c.get(low,length)==want_memory and draws==want_draws,(mode,mask)
 assert draws==(0 if mask==63 else 3);cases+=1
 for own,boundary in [(1,0)]+[(0,n) for n in range(1,7)]:
  c.put(low,initial);c.put(owner,struct.pack('>H',own));c.put(phase,struct.pack('>H',boundary));draws=0;writes.clear();checking=True
  got=run(addr('timing_render_effect'),rs);checking=False
  assert all(got[r]==(0x8f004 if r==8 else rs[r]) for r in range(1,17))
  assert got[17]&16==rs[17]&16 and c.get(low,length)==initial and draws==0 and not writes
  suppressed+=1
# Installer validates the call and following animation before touching code.
c.put(ARENA,struct.pack('>I',1));c.put(ARENA+addr('RT_HUNKS')-base,struct.pack('>I',h[0]));resload=0x740000
c.put(resload+0x64,bytes.fromhex('23c90075000023c8007500044e75'))
for enabled in (0,1):
 c.put(addr('_custom1'),struct.pack('>I',enabled));c.put(0x750000,bytes(8));rs.update({1:ARENA,3:resload})
 assert run(addr('timing_render_install'),rs)[9]==0
 if enabled:
  image,patch=struct.unpack('>II',c.get(0x750000,8));cmd,off,rel=struct.unpack('>HHh',c.get(patch,6))
  assert image==h[0] and cmd==0x8003 and off==0x5c92 and patch+rel==addr('timing_render_effect') 
  cmd,off,rel=struct.unpack('>HHh',c.get(patch+6,6));assert cmd==0x8003 and off==0x5c98 and patch+rel==addr('timing_render_animation') 
  for i,(off,name) in enumerate([(0x6356,'collect'),(0x63d4,'collect'),(0x468c,'select')],2):
   cmd,got,rel=struct.unpack('>HHh',c.get(patch+6*i,6));assert cmd==0x8003 and got==off and patch+rel==addr('timing_render_'+name)
  assert c.get(patch+30,2)==bytes(2)
 else:assert c.get(0x750000,8)==bytes(8)
rejects=0
for off in (0x5c92,0x5c94,0x5c96,0x5c98,0x5c9a,0x5c9c,0xbe5a,0x6356,0x6358,0x635a,0x63d4,0x63d6,0x63d8,0x468c,0x468e,0x4690):
 old=c.get(h[0]+off,2);c.put(h[0]+off,bytes(v^1 for v in old));c.put(0x750000,bytes(8))
 assert run(addr('timing_render_install'),rs)[9]==0xffffffff and c.get(0x750000,8)==bytes(8);c.put(h[0]+off,old);rejects+=1
c.put(ARENA,bytes(4));assert run(addr('timing_render_install'),rs)[9]==0xffffffff
print(json.dumps(dict(status='passed',native_cases=cases,suppressed_cases=suppressed,signature_rejections=rejects,zero_enhanced_rng_or_state_writes=True)));c.close()
