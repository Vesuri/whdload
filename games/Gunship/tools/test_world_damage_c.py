"""Native weapon arithmetic with private fire/timestamps; target/UI stubs explicit."""
import json,random
from unicorn_b import *
from layout import locate
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks'];p=h[6]+0x3b88
c=CPU();c.put(0x200000,mem);c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/world-damage.hunk')).get_segments()[0].get_data()))
listing=(root/'tmp/c/world-damage.lst').read_text()
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

hit=0x370000;effect=0x380000;heading=0x390000
for off in [0x7fa4,0xb2e0,0xb0a6]:c.put(h[0]+off,bytes.fromhex('70004e75') if off==0x7fa4 else bytes.fromhex('4e75'))
assert call('world_rng_prepare',{1:h[0]+0x7a5c,2:rc,3:record,4:h[2]})==0
assert call('world_effect_prepare',{1:h[0],2:effect,3:rc,4:heading})==0
assert call('world_hit_prepare',{1:h[0],2:hit,3:rc})==0
assert call('world_damage_prepare',{1:h[0],2:clone,3:rc,4:effect,5:hit,6:h[6]})==0
low=0x97ee00;length=0x21200;initial=c.get(low,length)
CODE=C.CFUNCTYPE(None,C.c_void_p,C.c_uint64,C.c_uint32,C.c_void_p)
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
trace=[]
@CODE
def event(handle,a,n,user):
 if a in [rc,h[0]+0x7a5c]:trace.append(('rng',256))
 elif a in [rc+14,h[0]+0x7a6a]:trace.append(('bound',c.rr(10)&65535))
 else:trace.append((a-h[0],c.rr(9)&255,None if a==h[0]+0xa150 else c.rr(10)&255))
hooks=[]
for a in [rc,rc+14]+[h[0]+off for off in [0x7a5c,0x7a6a,0xa150,0xaf36,0xb0a6]]:
 hook=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hook),1<<2,event,None,a,a));hooks.append(hook)
def normalized():
 state=bytearray(c.get(low,length))
 for a,size in [(h[2]+0x14,8),(h[6]+0x390a,2)]:state[a-low:a-low+size]=bytes(size)
 return bytes(state)
MEM=C.CFUNCTYPE(None,C.c_void_p,C.c_int,C.c_uint64,C.c_int,C.c_int64,C.c_void_p)
checking=False;badwrites=[];hardware=[]
@MEM
def write(handle,kind,a,n,value,user):
 if checking and 0xdff040<=a and a+n<=0xdff076:
  hardware.append((a,n,value));return
 if checking and not(low<=a and a+n<=low+length or 0x8e000<=a and a+n<=0x8f004):badwrites.append((hex(a),n))
hook=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hook),1<<11,write,None,1,0));hooks.append(hook)
hit_draws=set();damage_draws=set();damaged=0
for kind,count in [('hit',1024),('scan',128)]:
 for n in range(count):
  stamp=rng.randbytes(8);live=rng.randbytes(8);angle=rng.randbytes(2);c.put(record+32,stamp);c.put(heading,angle)
  seed=rng.randrange(2**32);results=[]
  for patched in [False,True]:
   c.put(low,initial);c.put(h[6]+0x45cc,bytes([n%2]));c.put(h[4]+0x3cc,struct.pack('>I',seed));c.put(h[2]+0x14,live if patched else stamp);c.put(h[6]+0x390a,b'\x55\xaa' if patched else angle)
   c.put(p+12,struct.pack('>H',(n//2)%4));c.put(p+14,struct.pack('>H',(1<<(n%14)) if n&8 else 0));c.put(p+17,bytes([(n//8)%4]));c.put(p+19,bytes([n%8]));c.put(p+78,bytes([(n//2)%8]));c.put(h[6]+0x1558,bytes([99]*6))
   if kind=='scan':
    c.put(p,struct.pack('>HH',0x7000,0x8000));c.put(p+28,struct.pack('>H',2048));c.put(p+42,bytes(2));c.put(p+23,b'\0');c.put(p+67,b'\1');c.put(p+66,b'\0');c.put(p+68,bytes(2));c.put(p+74,b'\0')
    for slot in [6,11,16]:
     c.put(p+0x56+slot,b'\x70');c.put(p+0xd6+slot,b'\x80');c.put(p+0x1d6+slot,bytes([0x10 if n&2 else 0]));c.put(p+0x256+slot,bytes([3 if n&4 else 1]))
    c.put(h[0]+0xba08,struct.pack('>H',63 if n&16 else 0))
   trace.clear();badwrites.clear();hardware.clear();checking=True
   if kind=='hit':
    c.rw(6,p);c.rw(9,7);c.rw(8,0x8f000);c.call(hit+8 if patched else h[0]+0x7d92)
   elif patched:assert call('world_damage_step',{1:p,2:clone})==0
   else:c.rw(6,p);c.rw(8,0x8f000);c.call(h[0]+0x9c5c)
   checking=False
   assert c.rr(18)==0x90000 and not badwrites,(kind,n,hex(c.rr(18)),badwrites[:8])
   results.append((normalized(),list(trace),list(hardware)))
  assert results[0]==results[1],(kind,n,[hex(low+i) for i,(a,b) in enumerate(zip(results[0][0],results[1][0])) if a!=b][:12],results[0][1],results[1][1])
  draws=sum(1 for e in trace if e[0]=='bound') # default entry falls through register entry
  (hit_draws if kind=='hit' else damage_draws).add(draws)
  if kind=='scan' and draws:damaged+=1
assert hit_draws=={1,2} and max(damage_draws)>=4,(hit_draws,damage_draws)
before=c.get(low,length)
assert call('world_damage_step',{1:p+2,2:clone})==0xffffffff
assert c.get(low,length)==before
rejects=0
for name,start,size,offsets,args in [
 ('world_hit_prepare',0x7d8a,318,[0,4,0x24,8,10,14,16,0x3c,0x3e,316],{1:h[0],2:0x3a0000,3:rc}),
 ('world_damage_prepare',0x9c5c,790,[0,788,0x1ce,0x1d0,0x1d4,0x1d6,0x1e6,0x1e8,0x1fa,0x1fc],{1:h[0],2:0x3a0000,3:rc,4:effect,5:hit,6:h[6]})]:
 original=c.get(h[0]+start,size)
 for off in offsets:
  corrupt=bytearray(original);corrupt[off]^=1;c.put(h[0]+start,corrupt);c.put(0x3a0000,b'Z'*800)
  assert call(name,args)==0xffffffff,(name,off)
  assert c.get(0x3a0000,800)==b'Z'*800
  rejects+=1
 c.put(h[0]+start,original)
print(json.dumps(dict(status='passed',signature_rejections=rejects,hit_cases=1024,damage_cases=128,hit_draws=sorted(hit_draws),scan_draws=sorted(damage_draws),scans_with_rng=damaged,calls=calls)))
c.close()
