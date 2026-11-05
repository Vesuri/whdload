"""Native target selector equivalence with explicit visibility samples."""
from unicorn_b import *
from layout import locate
import random,json,itertools
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks']
blob=bytes(BinFmt().load_image(str(build/'release/Gunship.Slave')).get_segments()[0].get_data());listing=(build/'release/Gunship.lst').read_text(encoding='latin1')
def sym(n):return int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
def addr(n):return base+sym(n)
c=CPU();c.put(0x200000,mem);c.put(base,blob);ctx=0x330000;pixels=0x340000;colors=0x350000;state=ctx+sym('WT_STATE');native=h[0]+0xa99e;size=sym('WT_SIZE');rng=random.Random(0xa58c)
def call(name,args):
 rs={r:rng.randrange(0x1000000) for r in range(1,17)};rs.update({8:0x8f000});rs.update(args)
 c.rw(17,0x2000)
 for r,v in rs.items():c.rw(r,v)
 c.call(addr(name));assert all(c.rr(r)==(0x8f004 if r==8 else v) for r,v in rs.items() if r!=9),name
 return c.rr(9)
assert call('target_select_prepare',{1:h[0],2:h[6],3:ctx})==0
# All relocation operands reject before any destination byte is changed.
relocs=[]
for i in range(30):relocs.append(struct.unpack('>4H',c.get(addr('target_select_relocs')+8*i,8)))
rejects=0
for off in [0,0x156]+[off+d for off,_,_,_ in relocs for d in (0,2)]:
 a=h[0]+0xa58c+off;saved=c.get(a,2);c.put(a,bytes(v^1 for v in saved));c.put(ctx-2,b'Z'*(size+4))
 assert call('target_select_prepare',{1:h[0],2:h[6],3:ctx})==0xffffffff and c.get(ctx-2,size+4)==b'Z'*(size+4)
 c.put(a,saved);rejects+=1
assert call('target_select_prepare',{1:h[0],2:h[6],3:ctx})==0
c.put(h[0]+0x825e,bytes.fromhex('4e75'))
CODE=C.CFUNCTYPE(None,C.c_void_p,C.c_uint64,C.c_uint32,C.c_void_p)
MEM=C.CFUNCTYPE(None,C.c_void_p,C.c_int,C.c_uint64,C.c_int,C.c_int64,C.c_void_p)
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
samples=bytes(5);queries=[];checking=False;bad=[]
@CODE
def pixel(handle,a,n,user):
 start=native if a==h[0]+0x825e else state
 index=(c.rr(1)-(start+0x6c))//2
 assert 0<=index<5
 queries.append((index,c.rr(9)&0xffffffff,c.rr(10)&0xffffffff))
 if a==h[0]+0x825e:c.rw(9,samples[index])
@MEM
def write(handle,kind,a,n,value,user):
 if checking and not(ctx<=a and a+n<=ctx+size or 0x8e000<=a and a+n<=0x8f004):bad.append((a,n))
hooks=[]
for kind,fn,start,end in [(1<<2,pixel,h[0]+0x825e,h[0]+0x825e),(1<<2,pixel,addr('target_select_pixel'),addr('target_select_pixel')),(1<<11,write,1,0)]:
 hook=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hook),kind,fn,None,start,end));hooks.append(hook)
cases=0
specs=[(1,0,mode,bytes([color])*5) for mode in (0,1) for color in range(256)]
specs += [(count,status,variant&1,rng.randbytes(5)) for count,status,variant in itertools.product(range(6),(0,1,2,255),range(64))]
for count,status,mode,samples in specs:
 b=bytearray(rng.randbytes(168));b[0]=status;struct.pack_into('>H',b,2,count)
 for i,off in enumerate(rng.sample([0,18,36,54,72],5)):struct.pack_into('>H',b,8+2*i,off)
 ids=[rng.choice([0xffff,0,1,2,3]) for _ in range(5)]
 for i,val in enumerate(ids):struct.pack_into('>H',b,0x6c+2*i,val)
 chosen=rng.randrange(5);struct.pack_into('>H',b,4,ids[chosen]);b[6:8]=b[0x76+2*chosen:0x78+2*chosen]
 palette=bytes([24,25]) if cases<512 else rng.randbytes(2);c.put(h[6]+0x3b9e,bytes([mode]));c.put(h[6]+0x16dc+24+256*mode,palette)
 c.put(native,b);queries.clear();c.rw(8,0x8f000);c.call(h[0]+0xa58c);want=c.get(native,168);want_queries=list(queries)
 if cases<512:assert len(want_queries)==1 and want[0]==(255 if samples[0] in (24,25) else 2)
 c.put(state,b);c.put(pixels,samples);c.put(colors,palette);native_before=c.get(0x97ee00,0x21200);queries.clear();bad.clear();checking=True
 result=call('target_select_step',{1:ctx,2:pixels,3:colors});checking=False
 assert result==0 and c.get(state,168)==want and queries==want_queries,(cases,count,status,mode)
 assert not bad and c.get(0x97ee00,0x21200)==native_before
 cases+=1
# Invalid input rejection is atomic, including signed/odd/out-of-range offsets.
invalid=0
for off,value in [(2,6),(2,65535),(8,1),(8,74),(8,65534)]:
 c.put(state,bytes(168));c.put(state+off,struct.pack('>H',value));before=c.get(ctx,size)
 assert call('target_select_step',{1:ctx,2:pixels,3:colors})==0xfffffffd and c.get(ctx,size)==before;invalid+=1
print(json.dumps(dict(status='passed',native_cases=cases,signature_rejections=rejects,invalid_state_rejections=invalid,query_order_equal=True,native_writes=0)));c.close()
