from unicorn_b import *
from layout import locate
from functools import lru_cache
import random,json
listing=(build/'verify/Gunship.lst').read_text(encoding='latin1')
@lru_cache(None)
def sym(n):return int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
blob=bytes(BinFmt().load_image(str(build/'verify/Gunship.Slave')).get_segments()[0].get_data())
c=CPU();c.put(base,blob);mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks'];c.put(0x200000,mem)
PS=0x170000;P=0x171000;PACKET=0x172000;CACHE=0x173000;STAGES=0x180000
sizes=[sym('PS_SIZE'),86,10];rng=random.Random(719)
def call(name,args):
 regs={r:0x4000+r for r in list(range(1,8))+list(range(10,17))};regs.update(args)
 c.rw(17,0x2000)
 for r,v in regs.items():c.rw(r,v)
 c.rw(8,0x8f000);c.call(base+sym(name));assert c.rr(18)==0x90000
 assert all(c.rr(r)==v for r,v in regs.items() if r!=9),(name,[(r,c.rr(r),v) for r,v in regs.items() if r!=9 and c.rr(r)!=v])
 return c.rr(9)
assert call('motion_stages_prepare',{1:h[0],2:STAGES})==0
count=0
intercept=False
u.uc_emu_stop.argtypes=[C.c_void_p]
@C.CFUNCTYPE(None,C.c_void_p,C.c_uint64,C.c_uint32,C.c_void_p)
def entered(*args):
 global count
 count+=1
 if intercept:ok(u.uc_emu_stop(c.h))
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
hook=C.c_size_t();entry=base+sym('player_step_interval');ok(u.uc_hook_add(c.h,C.byref(hook),1<<2,entered,None,entry,entry))
params={1:PS,2:P,3:STAGES,4:h[0]+0x7a44,5:PACKET,6:CACHE,9:1}
def inputs(state,player,packet):
 for a,b in [(PS,state),(P,player),(PACKET,packet)]:c.put(a-2,b'\xaa\x55'+b+b'\x55\xaa')
def outputs():return c.get(PS,sizes[0]),c.get(P,86)
def guards():
 for a,n in zip([PS,P,PACKET],sizes):assert c.get(a-2,2)==b'\xaa\x55' and c.get(a+n,2)==b'\x55\xaa'
comparisons=0;hits=0;misses=0
for i in range(160):
 c.put(PS,bytes(sizes[0]));assert call('player_step_init',{1:PS,9:3,10:(i%3-1)&0xffffffff})==0;state=c.get(PS,sizes[0])
 p=bytearray(86);struct.pack_into('>HH',p,0,0x7000+i,0x8000-i);struct.pack_into('>H',p,28,1000+i);p[16]=i%4;p[27]=128;p[57]=30;p[66]=28;p[53]=i%256;p[54]=(i%21-10)&255;p[55]=(i%31-15)&255
 packet=struct.pack('>hhhhh',i%3-1,i//3%3-1,[-4,0,4][i//9%3],i//27%3-1,i//7%5-2);params[9]=i+1
 inputs(state,p,packet);assert call('player_step_interval',params)==0;expected=outputs();guards()
 inputs(state,p,packet);before=count;assert call('player_step_cached_interval',params)==0;assert count==before+1;assert outputs()==expected;guards();misses+=1
 cache=c.get(CACHE,(sym('PC_PLAYER')+86))
 for repeat in range(3):
  inputs(state,p,packet);before=count;assert call('player_step_cached_interval',params)==0;assert count==before;assert outputs()==expected;assert c.get(CACHE,(sym('PC_PLAYER')+86))==cache;guards();hits+=1
 comparisons+=4
# Every input byte must participate in the key, even unused player/state bytes.
# Entry interception stops before executing potentially invalid modified state.
original=(state,bytes(p),packet);snapshot=c.get(CACHE,(sym('PC_PLAYER')+86))
intercept=True
for block,n in enumerate(sizes):
 for offset in range(n):
  parts=list(original);b=bytearray(parts[block]);b[offset]^=1;parts[block]=bytes(b);inputs(*parts)
  for r,v in params.items():c.rw(r,v)
  c.rw(8,0x8f000);c.call(base+sym('player_step_cached_interval'));assert c.rr(18)==entry,(block,offset)
  assert c.get(CACHE,(sym('PC_PLAYER')+86))==snapshot
for r in [3,4,9]:
 inputs(*original)
 for reg,v in params.items():c.rw(reg,v+(2 if reg==r else 0))
 c.rw(8,0x8f000);c.call(base+sym('player_step_cached_interval'));assert c.rr(18)==entry
intercept=False
# Failure is atomic for player/state/cache; bypass executes original each time.
inputs(*original);bad=dict(params);bad[9]=65536;before=count
assert call('player_step_cached_interval',bad)==0xffffffff;assert count==before+1;assert outputs()==original[:2];assert c.get(CACHE,(sym('PC_PLAYER')+86))==snapshot;guards()
badstate=bytearray(state);badstate[0:2]=b'\x00\x00';inputs(badstate,p,packet)
assert call('player_step_cached_interval',params)==0xffffffff;assert outputs()==(bytes(badstate),bytes(p));assert c.get(CACHE,(sym('PC_PLAYER')+86))==snapshot;guards()
inputs(*original);before=count;assert call('player_step_cached_interval',{**params,6:0})==0;assert count==before+1;assert outputs()==expected;assert c.get(CACHE,(sym('PC_PLAYER')+86))==snapshot
inputs(*original);c.put(CACHE,b'\0\0');before=count;assert call('player_step_cached_interval',params)==0;assert count==before+1;assert outputs()==expected
report=dict(comparisons=comparisons,cache_hits=hits,cache_misses=misses,every_key_byte_checked=sum(sizes),tick_and_code_pointer_misses=3,failure_cases=2,bypass_and_reset=True,registers_and_guards=True)
(root/'tmp/c/player-cache-test.json').write_text(json.dumps(report,indent=2)+'\n');print(report);c.close()
