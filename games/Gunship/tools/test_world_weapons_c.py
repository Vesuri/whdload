"""Native weapon arithmetic with private fire/timestamps; target/UI stubs explicit."""
import json,random
from unicorn_b import *
from layout import locate
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks'];p=h[6]+0x3b88
c=CPU();c.put(0x200000,mem);c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/world-weapons.hunk')).get_segments()[0].get_data()))
listing=(root/'tmp/c/world-weapons.lst').read_text()
def sym(n):return base+int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
clone=0x330000;rc=0x340000;record=0x350000;fire=0x360000;rng=random.Random(0x979c);calls=0
# Target fixture selects slot 5. Actor updates, allocation, launch, recoil and
# resource accounting remain native; notification/UI/audio endpoints are stubs.
c.put(h[0]+0xc654,bytes.fromhex('70054e75'))
for off in [0xa150,0xaf36,0xb4e4,0xb57c]:c.put(h[0]+off,bytes.fromhex('4e75'))
def call(name,args):
 global calls
 regs={r:rng.randrange(0x1000000) for r in range(1,17) if r not in [8,9]};regs.update(args)
 for r,v in regs.items():c.rw(r,v)
 c.rw(8,0x8f000);c.call(sym(name));calls+=1
 assert c.rr(18)==0x90000 and c.rr(8)==0x8f004,(name,hex(c.rr(18)))
 assert all(c.rr(r)==v for r,v in regs.items() if r!=9),name
 return c.rr(9)
assert call('world_rng_prepare',{1:h[0]+0x7a5c,2:rc,3:record,4:h[2]})==0
assert call('world_weapons_prepare',{1:h[0],2:clone,3:rc,4:fire,5:h[6]})==0
low=0x97ee00;length=0x21200;initial=c.get(low,length)
CODE=C.CFUNCTYPE(None,C.c_void_p,C.c_uint64,C.c_uint32,C.c_void_p)
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
trace=[];checking=False;badwrites=[];hardware=[]
@CODE
def event(handle,a,n,user):trace.append(0x7a5c if a==rc else a-h[0])
hooks=[]
for a in [rc]+[h[0]+off for off in [0x7a5c,0x7c1c,0xbea8,0xbade,0xbed4,0xa150]]:
 hook=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hook),1<<2,event,None,a,a));hooks.append(hook)
MEM=C.CFUNCTYPE(None,C.c_void_p,C.c_int,C.c_uint64,C.c_int,C.c_int64,C.c_void_p)
@MEM
def write(handle,kind,a,n,value,user):
 if checking and 0xdff040<=a and a+n<=0xdff076:
  hardware.append((a,n,value));return
 if checking and not(low<=a and a+n<=low+length or 0x8e000<=a and a+n<=0x8f004 or fire<=a and a+n<=fire+2):badwrites.append((hex(a),n))
hook=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hook),1<<11,write,None,1,0));hooks.append(hook)
paths=set();draws=0;launches=0
for n in range(256):
 stamp=rng.randbytes(8);live=rng.randbytes(8);flags=bytes([n&1,(n>>1)&1]);c.put(record+32,stamp)
 results=[]
 for patched in [False,True]:
  c.put(low,initial)
  c.put(h[6]+0x45cc,bytes([(n>>2)&1]));c.put(h[4]+0x3cc,struct.pack('>I',0x12345678+n))
  c.put(h[4]+0x1c5,b'\0\0');c.put(h[0]+0x9c42,b'\0')
  c.put(p+0x41,bytes([(n>>3)%4]));c.put(p+0x48,b'\0');c.put(p+0x36,bytes([((n%25)-12)&255]));c.put(p+0x35,bytes([(n*7)&255]));c.put(p+0x1c,struct.pack('>H',512+n*3));c.put(p+0x11,b'\x02')
  c.put(p+0x0e,b'\0\0');c.put(p+0x0c,struct.pack('>H',32+n))
  c.put(h[6]+0x1558,bytes([0 if n//64==1 else 99]*6));c.put(h[0]+0xba08,bytes(6));c.put(h[0]+0xba0e,b'\0\0' if n//64==3 else b'\xff\xff')
  if n//64==2:c.put(h[0]+0xba08,struct.pack('>H',63))
  # Make selected object live, with a nonzero target type.
  c.put(p+0x256+5,b'\x01')
  c.put(h[2]+0x14,live if patched else stamp)
  c.put(h[6]+0x4292,b'\x77\x88' if patched else flags);c.put(fire,flags)
  trace.clear();badwrites.clear();hardware.clear();checking=True
  if patched:assert call('world_weapons_step',{1:p,2:clone})==0
  else:c.rw(6,p);c.rw(8,0x8f000);c.call(h[0]+0x979c)
  checking=False
  assert not badwrites,(n,badwrites[:10])
  assert c.rr(18)==0x90000
  remaining=c.get(fire if patched else h[6]+0x4292,2)
  if patched:assert c.get(h[6]+0x4292,2)==b'\x77\x88'
  state=bytearray(c.get(low,length))
  for a,size in [(h[2]+0x14,8),(h[6]+0x4292,2)]:state[a-low:a-low+size]=bytes(size)
  results.append((bytes(state),remaining,list(trace),list(hardware)))
 assert results[0]==results[1],(n,[hex(low+i) for i,(a,b) in enumerate(zip(results[0][0],results[1][0])) if a!=b][:20],results[0][1:],results[1][1:])
 draws+=trace.count(0x7a5c);launches+=trace.count(0xbade);paths.add(tuple(trace))
assert draws and launches,(draws,launches)
before=c.get(low,length),c.get(fire,2)
assert call('world_weapons_step',{1:p+2,2:clone})==0xffffffff
assert before==(c.get(low,length),c.get(fire,2))
original=c.get(h[0]+0x979c,1022);rejects=0
for off in [0,2,0x1a,0x1c,0x25e,0x260,0x3fc]+[i+j for i in [0x16,0x5e,0x96,0x1be,0x2f6,0x3de,0xa0,0xb8] for j in [-2,0]]:
 corrupt=bytearray(original);corrupt[off]^=1;c.put(h[0]+0x979c,corrupt);c.put(0x370000,b'Z'*1026)
 assert call('world_weapons_prepare',{1:h[0],2:0x370000,3:rc,4:fire,5:h[6]})==0xffffffff,hex(off)
 assert c.get(0x370000,1026)==b'Z'*1026
 rejects+=1
c.put(h[0]+0x979c,original)
print(json.dumps(dict(status='passed',signature_rejections=rejects,native_cases=256,callback_paths=len(paths),rng_draws=draws,launch_calls=launches,calls=calls)))
c.close()
