"""Private scripted motion versus full native steering/RNG/damage sequence."""
from unicorn_b import *
from layout import locate
from functools import lru_cache
import random,json
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks'];p=h[6]+0x3b88
blob=bytes(BinFmt().load_image(str(build/'release/Gunship.Slave')).get_segments()[0].get_data());listing=(build/'release/Gunship.lst').read_text(encoding='latin1')
@lru_cache(None)
def sym(n):return int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
c=CPU();c.put(base,blob);c.put(0x200000,mem);spv=0x110000;bitmap=0x120000;palette=0x121000;planes=[0x130000+i*0x10000 for i in range(5)];rng=random.Random(0x9fb0)
size=sym('SP_PREFIX')+0x38;private=spv+sym('SP_PLAYER');code=spv+sym('SP_CODE');low=0x97ee00;length=0x21200
# Native RNG and hit arithmetic run. Only sound/indicator callbacks are stubbed.
for off in [0xa150,0xb4e4,0x7c56]:c.put(h[0]+off,bytes.fromhex('4e75'))
for a in planes:c.put(a,bytes(65536))
c.put(bitmap,struct.pack('>HHBBH5I',80,512,0,5,0,*planes));c.put(palette,b'\x1e\x1f')
def call(name,args,want=None):
 regs={r:rng.randrange(0x1000000) for r in range(1,17) if r!=8};regs.update(args);c.rw(17,0x2000)
 for r,v in regs.items():c.rw(r,v)
 c.rw(8,0x8f000);c.call(base+sym(name));assert c.rr(18)==0x90000,(name,hex(c.rr(18)))
 if want is not None:assert c.rr(9)==want,(name,c.rr(9),want)
 assert all(c.rr(r)==v for r,v in regs.items() if r!=9),(name,'registers')
 return c.rr(9)
call('script_preview_prepare',{1:h[0],2:h[6],3:spv},0)
# Install the new common store hook before either lane executes it. Private
# A5 must bypass identity stamping, including through actual preview helpers.
arena=0x600000;c.put(arena,struct.pack('>I',1));c.put(arena+sym('RT_HUNKS'),struct.pack('>9I',*h));c.put(arena+sym('RT_CAPTURE_OWNER'),b'\0\1')
c.put(base+sym('timing_runtime_arena'),struct.pack('>I',arena));c.put(h[0]+0x7bd0,bytes.fromhex('4ef9')+struct.pack('>I',base+sym('timing_script_store')))

MEM=C.CFUNCTYPE(None,C.c_void_p,C.c_int,C.c_uint64,C.c_int,C.c_int64,C.c_void_p)
CODE=C.CFUNCTYPE(None,C.c_void_p,C.c_uint64,C.c_uint32,C.c_void_p)
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
checking=False;bad=[];effects=[]
@MEM
def write(handle,kind,a,n,v,user):
 if checking and not(spv<=a and a+n<=code or 0x8e000<=a and a+n<=0x8f004):bad.append((a,n))
@CODE
def effect(handle,a,n,user):effects.append((checking,a-h[0]))
hooks=[]
for kind,cb,start,end in [(1<<11,write,1,0)]+[(1<<2,effect,h[0]+off,h[0]+off) for off in (0x7a5c,0x7d92,0xa150)]:
 hook=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hook),kind,cb,None,start,end));hooks.append(hook)
pose_offsets=[0x5b,0xd5,0xdb,0x155,0x255,0x1d5,0x15b,0x1db,0x25b]
matched=unknown=inactive=0;changed=0;scripted=0
initial=c.get(low,length)
for case in range(1800):
 c.put(low,initial);ps=bytearray(rng.randbytes(0x2d6))
 x=rng.choice([8000,10000,12000]);y=rng.randrange(20000,50000)
 px=x+rng.randrange(-8,9) if case%4==0 else rng.randrange(6000,18000);py=y+rng.randrange(-8,9) if case%4==0 else rng.randrange(20000,50000)
 struct.pack_into('>HH',ps,0,px,py);struct.pack_into('>H',ps,28,rng.choice([0,24,31,32,100,32767,65535]));struct.pack_into('>H',ps,12,case)
 ps[0x11]=rng.randrange(4);ps[0x13]=0;ps[0x16]=case%2;ps[0x2c]=0 if case%3 else 1
 for hi,lo,value in [(0x5b,0xd5,0 if case%101==0 else x),(0xdb,0x155,y),(0x255,0x1d5,300)]:ps[hi]=value>>8;ps[lo]=value&255
 ps[0x15b]=rng.randrange(256)
 if case%16==0 and case%101:
  # Exact axial target gives zero division remainder in native atan and
  # guarantees its tick-gated attack decision is reached, with clear terrain.
  struct.pack_into('>HH',ps,0,x,y+256);ps[0x2c]=0;ps[0x11]=3;ps[0x16]=0
  c.rw(9,0);c.rw(10,64);c.rw(8,0x8f000);c.call(h[0]+0x7ac8);ps[0x15b]=(-c.rr(9))&255
 c.put(p,ps);c.put(h[6]+0x157b,bytes([rng.randrange(128)]));c.put(h[6]+0x47c4,struct.pack('>I',bitmap))
 colors=b'\x00\x1f' if case%5==0 and case%16 else b'\x1e\x1f';c.put(palette,colors);c.put(h[6]+0x16dc+ps[0x16]*256+24,colors)
 before=c.get(low,length);bad.clear();checking=True
 got=call('script_preview_step',{1:spv,2:p,3:bitmap,4:palette});checking=False
 assert c.get(low,length)==before and not bad,(case,bad)
 if not got:
  if not x or case%101==0:inactive+=1
  else:unknown+=1
  continue
 assert c.get(spv+sym('SP_VALID'),1)==b'\1'
 predicted=bytes(c.get(private+off,1)[0] for off in pose_offsets)
 c.rw(6,p);c.rw(8,0x8f000);c.call(h[0]+0x9fb0);assert c.rr(18)==0x90000,(case,hex(c.rr(18)))
 actual=bytes(c.get(p+off,1)[0] for off in pose_offsets)
 assert actual==predicted,(case,actual.hex(),predicted.hex(),ps[0x2c])
 matched+=1;scripted+=bool(ps[0x2c]);changed+=actual!=bytes(ps[off] for off in pose_offsets)
assert not any(flag for flag,off in effects),effects
# Unknown/null planes and an invalid target index never produce a candidate.
c.put(p,ps);c.put(h[6]+0x157b,b'\x80');call('script_preview_step',{1:spv,2:p,3:bitmap,4:palette},0)
c.put(h[6]+0x157b,b'\x05');c.put(bitmap+8,bytes(4));call('script_preview_step',{1:spv,2:p,3:bitmap,4:palette},0)
# Scripted mode ignores the first terrain result entirely. Its pose remains
# certifiable even if that irrelevant query is outside the bitmap.
c.put(p+0x2c,b'\1');call('script_preview_step',{1:spv,2:p,3:bitmap,4:palette},1)
ignored_pose=bytes(c.get(private+off,1)[0] for off in pose_offsets)
c.put(bitmap+8,struct.pack('>I',planes[0]));call('script_preview_step',{1:spv,2:p,3:bitmap,4:palette},1)
assert bytes(c.get(private+off,1)[0] for off in pose_offsets)==ignored_pose
# Validate all relocation operands and changed instruction boundaries atomically.
relocs=c.get(base+sym('script_preview_relocs'),sym('script_preview_relocs_end')-sym('script_preview_relocs'))
rejects=0
for off in [int.from_bytes(relocs[i:i+2],'big') for i in range(0,len(relocs),8)]+[0,0x11a,0x19a]:
 address=h[0]+0x9fb0+off;old=c.get(address,2);c.put(address,bytes(v^1 for v in old));before=c.get(spv,size)
 call('script_preview_prepare',{1:h[0],2:h[6],3:spv},0xffffffff);assert c.get(spv,size)==before;c.put(address,old);rejects+=1
counts={hex(off):sum(o==off for flag,o in effects) for off in (0x7a5c,0x7d92,0xa150)}
assert matched>500 and changed and scripted and unknown and counts['0x7a5c'] and counts['0x7d92'],(matched,changed,scripted,unknown,counts)
print(json.dumps(dict(status='passed',native_pose_matches=matched,scripted_mode_matches=scripted,changed_poses=changed,unknown_candidates=unknown,inactive_cases=inactive,native_effect_calls=counts,preview_effect_calls=0,signature_rejections=rejects,native_writes=0,context_bytes=size)));c.close()
