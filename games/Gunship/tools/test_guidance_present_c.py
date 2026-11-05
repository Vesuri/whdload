"""Retained guidance sprites versus native library-call arguments."""
import json,random,itertools
from unicorn_b import *
from layout import locate
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks']
blob=bytes(BinFmt().load_image(str(root/'tmp/c/runtime.hunk')).get_segments()[0].get_data());listing=(root/'tmp/c/runtime.lst').read_text()
def addr(n):return base+int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
FG=0x330000;GP=0x340000;PENDING=0x350000;c=CPU();c.put(0x200000,mem);c.put(base,blob)
trace=[];rng=random.Random(321);calls=0
CODE=C.CFUNCTYPE(None,C.c_void_p,C.c_uint64,C.c_uint32,C.c_void_p)
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
@CODE
def observe(handle,a,n,user):
 sp=c.rr(8)+4
 trace.append(('move' if a==h[0]+0xf048 else 'change',struct.unpack('>5I' if a==h[0]+0xf048 else '>3I',c.get(sp,20 if a==h[0]+0xf048 else 12))))
hooks=[]
for off in (0xf048,0xf02c):
 c.put(h[0]+off,bytes.fromhex('4e75'));hook=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hook),1<<2,observe,None,h[0]+off,h[0]+off));hooks.append(hook)
def call(name,args):
 global calls
 rs={r:rng.randrange(0x1000000) for r in range(1,17) if r not in (8,9)};rs.update(args)
 for r,v in rs.items():c.rw(r,v)
 c.rw(8,0x8f000);c.call(addr(name));calls+=1
 assert c.rr(8)==0x8f004 and all(c.rr(r)==v for r,v in rs.items() if r!=9),name
 return c.rr(9)
assert call('field_guidance_prepare',{1:h[0],2:FG,3:h[4],4:PENDING})==0
call('guidance_present_init',{1:GP,2:h[0],3:h[6]})
for offset in (0x44,0x48,0xc2,0xc6,0xf6,0xfa,0x114,0x118):
 saved=c.get(FG+offset,2);c.put(FG+offset,bytes(2));before=c.get(FG,312);presentation=c.get(GP,58)
 assert call('guidance_present_bind',{1:FG,2:GP})==0xffffffff
 assert c.get(FG,312)==before and c.get(GP,58)==presentation
 c.put(FG+offset,saved)
assert call('guidance_present_bind',{1:FG,2:GP})==0
bound=c.get(FG,312);assert call('guidance_present_bind',{1:FG,2:GP})==0xffffffff and c.get(FG,312)==bound
# Exercise native position/image selection with safe positive/negative image offsets.
for off in (0x3984,0x3a38):
 for i in range(96):c.put(h[6]+off+i*2,struct.pack('>h',(i*7)%300-80))
for i in range(128):c.put(h[6]+0x3b28+i*2,struct.pack('>h',(-4,0,4,8)[i%4]))
for i in range(40):c.put(h[6]+0x3aec+i*2,struct.pack('>h',i*3-25))
for i in range(-1,4):c.put(h[6]+0x4d54+i*4,struct.pack('>I',0x500000+i*256))
c.put(h[0]+0xa42c,struct.pack('>I',4));c.put(h[0]+0xa430,struct.pack('>I',2))
c.put(h[6]+0x47b8,struct.pack('>I',0x600000));c.put(h[4]+0x1c6,b'\0')
regions=[(h[0]+0xa44d,3),(h[0]+0xa436,1),(h[0]+0xba0c,4)]
def initialize(phase,mode,view,hidden,pending):
 c.put(h[0]+0xa44d,bytes([phase,1,mode]));c.put(h[0]+0xa436,bytes([hidden]));c.put(h[0]+0xba0c,struct.pack('>HH',0,1));c.put(h[6]+0x3b88+26,bytes([view]));c.put(h[0]+0xc757,bytes([pending]));c.put(PENDING,bytes([pending]))
def compact(events):
 out={}
 for kind,args in events:
  if kind=='move':out[args[1]]=args
  else:assert args==(out[args[1]][0],args[1],out[args[1]][4])
 return out
cases=0
for phase,mode,view,hidden,pending in itertools.product((0,5,29,30,31,255),(0,1,5,6,7),(0,32),(0,255),(0,255)):
 initialize(phase,mode,view,hidden,pending);trace.clear();c.rw(8,0x8f000);c.call(h[0]+0xa1c8)
 want=compact(trace);state=[c.get(a,n) for a,n in regions]+[c.get(h[0]+0xc757,1)]
 initialize(phase,mode,view,hidden,pending);c.put(GP+56,bytes(2));trace.clear()
 assert call('field_guidance_step',{1:FG})==1
 assert not trace,'capture called graphics'
 assert [c.get(a,n) for a,n in regions]+[c.get(PENDING,1)]==state,(phase,mode,view,hidden,pending)
 native_before=c.get(0x97ee00,0x21200)
 assert call('guidance_present',{1:GP})==len(want)
 assert compact(trace)==want,(phase,mode,view,hidden,pending,trace,want)
 assert c.get(0x97ee00,0x21200)==native_before
 trace.clear();assert call('guidance_present',{1:GP})==0 and not trace
 cases+=1
# Retain latest request for each sprite across skipped renders, including hide.
latest={};c.put(GP+56,bytes(2))
for phase,mode in [(0,0),(5,6),(12,1),(29,7),(31,0)]:
 initialize(phase,mode,0,0,0);trace.clear();c.rw(8,0x8f000);c.call(h[0]+0xa1c8);latest.update(compact(trace))
 initialize(phase,mode,0,0,0);trace.clear();call('field_guidance_step',{1:FG});assert not trace
trace.clear();assert call('guidance_present',{1:GP})==len(latest);assert compact(trace)==latest
call('guidance_present_reset',{1:GP});trace.clear();assert call('guidance_present',{1:GP})==2
assert all(v[2:4]==(0xffffffe0,0xffffffe0) for v in compact(trace).values())
print(json.dumps(dict(status='passed',native_cases=cases,coalesced_fields=5,calls=calls,native_state_read_only_on_render=True)));c.close()
