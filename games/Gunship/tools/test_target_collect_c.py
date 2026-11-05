"""Candidate filtering and capacity against original native collector."""
from unicorn_b import *
from layout import locate
from functools import lru_cache
import random,json,struct,itertools
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks']
blob=bytes(BinFmt().load_image(str(build/'release/Gunship.Slave')).get_segments()[0].get_data());listing=(build/'release/Gunship.lst').read_text(encoding='latin1')
@lru_cache(None)
def sym(n):return int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
def addr(n):return base+sym(n)
c=CPU();c.put(base,blob);c.put(0x200000,mem);scene=0x110000;target=0x120000;collector=0x130000;context=0x140000;model=0x150000
state=target+sym('WT_STATE');native=h[0]+0xa99e;rng=random.Random(0xa450)
for r,v in {1:h[0],2:h[4],3:h[6],4:scene,5:target,6:collector,8:0x8f000}.items():c.rw(r,v)
c.call(addr('target_collect_prepare'));assert c.rr(9)==0
c.put(model,struct.pack('>3H',0,0,64));c.put(context,rng.randbytes(100));c.put(context+0x5a,struct.pack('>II',model,h[6]+0x15dc))
c.put(h[4]+0x430,struct.pack('>HH',320,200));c.put(h[0]+0xa998,struct.pack('>3H',68,252,1000))
MEM=C.CFUNCTYPE(None,C.c_void_p,C.c_int,C.c_uint64,C.c_int,C.c_int64,C.c_void_p)
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
checking=False;bad=[]
@MEM
def write(handle,kind,a,n,v,user):
 if checking and not(state<=a and a+n<=state+168 or 0x8e000<=a and a+n<=0x8f004):bad.append((a,n))
hook=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hook),1<<11,write,None,1,0))
cases=0;added=0;saturated=0
for count,variant in itertools.product(range(6),range(256)):
 data=bytearray(rng.randbytes(168));struct.pack_into('>H',data,2,count)
 for i,off in enumerate((0,18,36,54,72)):struct.pack_into('>H',data,8+2*i,off)
 obj=rng.choice((65535,0,1,7));cell=rng.randrange(32)
 if variant&1:struct.pack_into('>HH',data,4,obj,cell)
 c.put(h[6]+0x1d72,struct.pack('>H',variant%4));c.put(h[6]+0x3ba2,bytes([1 if variant%7==0 else 0]))
 for off,value in [(0x6ac6,obj),(0x6ac8,variant%8),(0x5b00,cell),(0x76e2,rng.choice((65535,0,67,68,160,251,252,320,321))),(0x770c,rng.choice((65535,0,100,200,201))),(0x768e,rng.choice((0,1000,2000,2002,65535)))]:
  b=struct.pack('>H',value);c.put(h[0]+off,b);c.put(scene+off-sym('SCENE_START'),b)
 c.put(native,data);c.rw(6,context);c.rw(8,0x8f000);c.call(h[0]+0xa450);want=c.get(native,168)
 if count==5:assert want==data;saturated+=1
 added+=want[2:4]!=data[2:4]
 c.put(state,data);before=c.get(0x97ee00,0x21200);bad.clear();checking=True;c.rw(6,context);c.rw(8,0x8f000);c.call(collector);checking=False
 assert c.get(state,168)==want and not bad and c.get(0x97ee00,0x21200)==before,(count,variant,bad)
 cases+=1
assert added>0
print(json.dumps(dict(status='passed',native_cases=cases,appends=added,saturated_cases=saturated,native_writes=0)));c.close()
