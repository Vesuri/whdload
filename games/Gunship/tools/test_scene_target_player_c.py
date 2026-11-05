"""Native projected candidate collection versus fully private projection."""
from unicorn_b import *
from layout import locate
import json,struct
from functools import lru_cache
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks'];p=h[6]+0x3b88
blob=bytes(BinFmt().load_image(str(build/'release/Gunship.Slave')).get_segments()[0].get_data());listing=(build/'release/Gunship.lst').read_text(encoding='latin1')
@lru_cache(None)
def sym(n):return int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
def addr(n):return base+sym(n)
c=CPU();c.put(base,blob);scene=0x110000;target=0x120000;collector=0x130000
native_target=h[0]+0xa99e;state=target+sym('WT_STATE');ctx=h[6]+0x38f6
MEM=C.CFUNCTYPE(None,C.c_void_p,C.c_int,C.c_uint64,C.c_int,C.c_int64,C.c_void_p)
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
checking=False;bad=[]
@MEM
def write(handle,kind,a,n,v,user):
 if checking and not(scene<=a and a+n<=scene+sym('SCT_SELECTION')+168 or state<=a and a+n<=state+168 or 0x8e000<=a and a+n<=0x8f004):bad.append((hex(a),n))
wh=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(wh),1<<11,write,None,1,0))
def call(entry,regs={},end=0x90000):
 c.rw(17,0x2000)
 for r,v in regs.items():c.rw(r,v)
 c.rw(8,0x8f000);c.call(entry,end=end)
 assert c.rr(18)==end,(hex(entry),hex(c.rr(18)))
 return c.rr(9)
CODE=C.CFUNCTYPE(None,C.c_void_p,C.c_uint64,C.c_uint32,C.c_void_p)
late_calls=0
late_enabled=False
@CODE
def late_overlay(handle,a,n,user):
 global late_calls
 if not late_enabled:return
 late_calls+=1
 c.put(state+2,b'\0\5');c.put(state+0x6c,b'\x55\x55')
 c.put(scene+sym('SCENE_CONTEXT')+0x62,b'\1')
lh=C.c_size_t();entry=scene+0x625a-sym('SCENE_START');ok(u.uc_hook_add(c.h,C.byref(lh),1<<2,late_overlay,None,entry,entry))

cases=0;counts=set();nonempty=0;positive=0
positions=[(0x7fff,0x7fff)] if os.environ.get('TARGET_QUICK') else [(0x7fff,0x7fff),(0x8000,0x8000),(0x7800,0x8800)]
for xy in positions:
 for height in (64,512):
  for heading in range(0,256,32):
   c.put(0x200000,mem)
   assert call(addr('target_select_prepare'),{1:h[0],2:h[6],3:target})==0
   assert call(addr('scene_target_player_prepare'),{1:h[0],2:h[4],3:h[6],4:scene,5:target,6:collector,7:0x140000})==0
   assert call(addr('target_select_prepare'),{1:h[0],2:h[6],3:0x160000})==0
   assert call(addr('scene_target_prepare'),{1:h[0],2:h[4],3:h[6],4:0x150000,5:0x160000,6:0x170000})==0
   # Both lanes omit only rasterization. Projection and target collection are native.
   c.put(h[0]+0x63f8,bytes.fromhex('4e75'))
   for off in (0x63b0,0x63c4,0x63ce):c.put(h[0]+off,bytes.fromhex('4e714e714e71'))
   c.put(p,struct.pack('>HH',*xy));c.put(p+28,struct.pack('>H',height));c.put(p+53,bytes([heading,0,0]));c.put(p+26,b'\0')
   special=struct.pack('>HHH',xy[0]+128,xy[1]+128,height+24)
   for off,v in zip([0x3be3,0x3c5d,0x3c63,0x3cdd,0x3ddd,0x3d5d],special):c.put(h[6]+off,bytes([v]))
   coords=[xy[0]+(i-2)*128 for i in range(6)]+[xy[1]+(i-2)*128 for i in range(6)]+[height+32]*6
   c.put(h[0]+0xc6a0,struct.pack('>18H',*coords));c.put(h[0]+0xba08,b'\0\x3f')
   call(h[0]+0x57e2,{6:p},h[0]+0x5830)
   # Build the same direct scene endpoint used by the private path.
   call(addr('scene_state_build'),{1:h[4],2:h[0]+0xc6a0,3:h[6],4:ctx+14})
   c.put(ctx+0x5e,struct.pack('>I',h[6]+0x15dc));c.put(ctx+0x62,b'\0')
   initial=bytearray(c.get(native_target,168));initial[2:4]=bytes(2)
   for i,o in enumerate((0,18,36,54,72)):struct.pack_into('>H',initial,8+2*i,o)
   c.put(native_target,initial);c.put(state,initial)
   call(h[0]+0x5c2e,{6:ctx},h[0]+0x5c5c);call(h[0]+0x60a8,{6:ctx})
   want=c.get(native_target,168)
   call(h[0]+0x6224,{6:ctx})
   wantflag=c.get(ctx+0x62,1);counts.add(int.from_bytes(want[2:4],'big'));nonempty+=want[2:4]!=bytes(2)
   c.put(0x140000,c.get(p,86))
   for offset in (0,2,26):c.put(p+offset,bytes([c.get(p+offset,1)[0]^255]))
   before=c.get(0x97ee00,0x21200);bad.clear();checking=True
   result=call(addr('scene_target_step'),{1:scene,2:h[4],3:h[0]+0xc6a0});checking=False
   assert c.get(state,168)==want,(xy,height,heading,c.get(state,168).hex(),want.hex())
   assert result==int.from_bytes(wantflag,'big')&1 and not bad,(result,wantflag,bad[:10])
   assert c.get(0x97ee00,0x21200)==before
   # A reused workspace must reset its previous candidate count.
   checking=True;result2=call(addr('scene_target_step'),{1:scene,2:h[4],3:h[0]+0xc6a0});checking=False
   assert result2==result and c.get(state,168)==want and not bad
   checking=True;candidate_result=call(addr('scene_target_candidates_step'),{1:scene,2:h[4],3:h[0]+0xc6a0});checking=False
   assert candidate_result==0 and c.get(state,168)==want and not bad
   assert c.get(0x97ee00,0x21200)==before
   c.put(0x160000+sym('WT_STATE'),initial)
   assert call(addr('scene_target_candidates_step'),{1:0x150000,2:h[4],3:h[0]+0xc6a0})==0
   positive+=c.get(0x160000+sym('WT_STATE'),168)!=want
   assert c.get(0x97ee00,0x21200)==before
   cases+=1
assert nonempty,'no candidates exercised'
assert positive,'poison did not affect legacy binding'
# A late overlay may change scratch candidates, but cannot replace this view's
# pre-overlay selection snapshot. It still contributes to the plane result.
late_enabled=True
assert call(addr('scene_target_step'),{1:scene,2:h[4],3:h[0]+0xc6a0})==1
assert c.get(state,168)==want and late_calls==1
assert call(addr('scene_target_candidates_step'),{1:scene,2:h[4],3:h[0]+0xc6a0})==0
assert c.get(state,168)==want and late_calls==1

for value in (1,74,65534):
 c.put(state+8,struct.pack('>H',value));before=(c.get(scene,(sym('SCT_SELECTION')+168)),c.get(target,sym('WT_SIZE')))
 assert call(addr('scene_target_step'),{1:scene,2:h[4],3:h[0]+0xc6a0})==0xfffffffd
 assert (c.get(scene,(sym('SCT_SELECTION')+168)),c.get(target,sym('WT_SIZE')))==before
 assert call(addr('scene_target_candidates_step'),{1:scene,2:h[4],3:h[0]+0xc6a0})==0xfffffffd
 assert (c.get(scene,(sym('SCT_SELECTION')+168)),c.get(target,sym('WT_SIZE')))==before
print(json.dumps(dict(status='passed',poisoned_native_player_bytes=[0,2,26],legacy_positive_controls=positive,scenes=cases,nonempty=nonempty,candidate_counts=sorted(counts),native_writes=0)));c.close()
