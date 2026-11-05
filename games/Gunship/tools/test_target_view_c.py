"""Current-view capture preserves world identity and uses native projection."""
from unicorn_b import *
from layout import locate
from functools import lru_cache
import random,json,struct
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks']
blob=bytes(BinFmt().load_image(str(build/'release/Gunship.Slave')).get_segments()[0].get_data());listing=(build/'release/Gunship.lst').read_text(encoding='latin1')
@lru_cache(None)
def sym(n):return int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
c=CPU();c.put(base,blob);c.put(0x200000,mem);tv=0x110000;out=0x120000;context=0x140000;model=0x150000
state=tv+sym('TPV_STATE');native=h[0]+0xa99e;rng=random.Random(0xa450);low=0x97ee00;length=0x21200
calls=0
def call(name,args,want):
 global calls
 regs={r:rng.randrange(0x1000000) for r in list(range(1,8))+list(range(10,17))};regs.update(args);c.rw(17,0x2000)
 for r,v in regs.items():c.rw(r,v)
 c.rw(8,0x8f000);c.call(base+sym(name));calls+=1
 assert c.rr(18)==0x90000 and c.rr(9)==want,(name,c.rr(9),want)
 assert all(c.rr(r)==v for r,v in regs.items() if r!=9),(name,'registers')
call('target_view_prepare',{1:h[0],2:h[4],3:h[6],4:tv},0)
c.put(model,struct.pack('>3H',0,0,64));c.put(context,rng.randbytes(100));c.put(context+0x5a,struct.pack('>II',model,h[6]+0x15dc))
c.put(h[4]+0x430,struct.pack('>HH',320,200));c.put(h[0]+0xa998,struct.pack('>3H',68,252,1000))
MEM=C.CFUNCTYPE(None,C.c_void_p,C.c_int,C.c_uint64,C.c_int,C.c_int64,C.c_void_p)
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
checking=False;bad=[]
@MEM
def write(handle,kind,a,n,v,user):
 if checking and not(state<=a and a+n<=tv+sym('TPV_CODE') or out<=a and a+n<=out+168 or 0x8e000<=a and a+n<=0x8f004):bad.append((a,n))
hook=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hook),1<<11,write,None,1,0))
matched=0;ignored=0
for variant in range(1024):
 data=bytearray(rng.randbytes(168));data[0]=rng.choice((2,2,2,0,255));struct.pack_into('>H',data,2,5)
 offsets=rng.sample((0,18,36,54,72),5)
 for i,off in enumerate(offsets):struct.pack_into('>H',data,8+2*i,off)
 obj=rng.choice((65535,0,1,7));cell=rng.randrange(32)
 selected=obj if variant&1 else 9;subtype=cell if variant&2 else 42
 struct.pack_into('>HH',data,4,selected,subtype)
 c.put(h[6]+0x1d72,struct.pack('>H',variant%4));c.put(h[6]+0x3ba2,bytes([1 if variant%7==0 else 0]))
 for off,value in [(0x6ac6,obj),(0x6ac8,variant%8),(0x5b00,cell),(0x76e2,rng.choice((65535,0,67,68,160,251,252,320,321))),(0x770c,rng.choice((65535,0,100,200,201))),(0x768e,rng.choice((0,1000,2000,2002,65535)))]:c.put(h[0]+off,struct.pack('>H',value))
 # Native collector oracle has a fresh list; only the committed identity may
 # reach it. It may retain a target outside the acquisition horizontal strip.
 seed=bytearray(data);seed[2:4]=bytes(2);c.put(native,seed)
 eligible=data[0]==2 and obj==selected and (obj>=32768 or cell==subtype)
 if eligible:
  c.rw(6,context);c.rw(8,0x8f000);c.call(h[0]+0xa450)
 expected=c.get(native,168);accepted=eligible and expected[2:4]==b'\0\1'
 c.put(native,data);before=c.get(low,length);bad.clear();checking=True
 call('target_view_reset',{1:tv,2:native},0)
 call('target_view_capture',{1:tv,6:context},int(accepted))
 c.put(out,b'\xa5'*168);call('target_view_build',{1:tv,2:out},int(accepted));checking=False
 assert c.get(low,length)==before and not bad,(variant,bad)
 if accepted:
  want=bytearray(expected);want[2:4]=bytes(2);want[18:36]=expected[18+offsets[0]:36+offsets[0]]
  assert c.get(out,168)==want and c.get(out,2)==data[:2] and c.get(out+4,4)==data[4:8]
  matched+=1
 else:assert c.get(out,168)==b'\xa5'*168;ignored+=1
# Six unrelated projected objects cannot saturate the capture before selected.
data[0]=2;struct.pack_into('>HH',data,4,7,3);c.put(native,data);call('target_view_reset',{1:tv,2:native},0)
for obj in range(6):
 c.put(h[0]+0x6ac6,struct.pack('>H',obj));call('target_view_capture',{1:tv,6:context},0)
for off,value in ((0x6ac6,7),(0x5b00,3),(0x6ac8,8),(0x76e2,160),(0x770c,100),(0x768e,1000)):c.put(h[0]+off,struct.pack('>H',value))
call('target_view_capture',{1:tv,6:context},1);call('target_view_build',{1:tv,2:out},1)
# Next frame has no accepted projection: no stale output, same identity retained.
call('target_view_reset',{1:tv,2:native},0);c.put(out,b'\xa5'*168);call('target_view_build',{1:tv,2:out},0);assert c.get(out,168)==b'\xa5'*168
for off in (1,73,65534):
 c.put(native+8,struct.pack('>H',off));before=c.get(tv,(sym('TPV_CODE')+sym('WTC_CODE_SIZE')));call('target_view_reset',{1:tv,2:native},0xfffffffd);assert c.get(tv,(sym('TPV_CODE')+sym('WTC_CODE_SIZE')))==before
rejects=0
relocs=c.get(base+sym('target_collect_relocs'),sym('target_collect_relocs_end')-sym('target_collect_relocs'))
for off in [int.from_bytes(relocs[i:i+2],'big') for i in range(0,len(relocs),8)]+[0,sym('WTC_CODE_SIZE')-2]:
 address=h[0]+0xa450+off;old=c.get(address,2);c.put(address,bytes(v^1 for v in old));before=c.get(tv,sym('TPV_CODE')+sym('WTC_CODE_SIZE'))
 call('target_view_prepare',{1:h[0],2:h[4],3:h[6],4:tv},0xffffffff)
 assert c.get(tv,sym('TPV_CODE')+sym('WTC_CODE_SIZE'))==before;c.put(address,old);rejects+=1
assert matched>0
print(json.dumps(dict(status='passed',native_cases=1024,captured=matched,ignored=ignored,saturation_bypassed=True,stale_projection_rejected=True,atomic_invalid_offsets=3,preparation_rejections=rejects,native_writes=0,calls=calls)));c.close()
