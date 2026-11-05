"""Native weapon arithmetic with private fire/timestamps; target/UI stubs explicit."""
import json,random
from unicorn_b import *
from layout import locate
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks'];p=h[6]+0x3b88
c=CPU();c.put(0x200000,mem);c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/world-script.hunk')).get_segments()[0].get_data()))
listing=(root/'tmp/c/world-script.lst').read_text()
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


hit=0x370000
for off in [0x7fa4,0xb0a6]:c.put(h[0]+off,bytes.fromhex('70004e75') if off==0x7fa4 else bytes.fromhex('4e75'))
assert call('world_rng_prepare',{1:h[0]+0x7a5c,2:rc,3:record,4:h[2]})==0
assert call('world_hit_prepare',{1:h[0],2:hit,3:rc})==0
assert call('world_script_prepare',{1:h[0],2:clone,3:rc,4:hit,5:h[6]})==0
low=0x97ee00;length=0x21200;initial=c.get(low,length)
CODE=C.CFUNCTYPE(None,C.c_void_p,C.c_uint64,C.c_uint32,C.c_void_p)
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
u.uc_emu_stop.argtypes=[C.c_void_p]
trace=[];blocked=False
@CODE
def event(handle,a,n,user):
 global blocked
 if a==h[0]+0x8050:
  state=c.get(p+83,1)[0];delay=c.get(p+84,1)[0]
  if 0<state<128 and delay==1:blocked=True;ok(u.uc_emu_stop(handle))
 elif a in [rc,h[0]+0x7a5c]:trace.append(('rng',256))
 elif a in [rc+14,h[0]+0x7a6a]:trace.append(('bound',c.rr(10)&65535))
 else:trace.append((a-h[0],c.rr(9)&255,None if a==h[0]+0xa150 else c.rr(10)&255))
hooks=[]
for a in [rc,rc+14]+[h[0]+off for off in [0x8050,0x7a5c,0x7a6a,0xa150,0xaf36,0xb0a6]]:
 hook=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hook),1<<2,event,None,a,a));hooks.append(hook)
MEM=C.CFUNCTYPE(None,C.c_void_p,C.c_int,C.c_uint64,C.c_int,C.c_int64,C.c_void_p)
checking=False;badwrites=[]
@MEM
def write(handle,kind,a,n,value,user):
 if checking and not(low<=a and a+n<=low+length or 0x8e000<=a and a+n<=0x8f004):badwrites.append((hex(a),n))
hook=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hook),1<<11,write,None,1,0));hooks.append(hook)
outcomes={0:0,2:0};drawcounts=set();resumes=0
for n in range(1024):
 stamp=rng.randbytes(8);live=rng.randbytes(8);c.put(record+32,stamp);seed=rng.randrange(2**32);results=[]
 resume=n>=768
 for patched in [False,True]:
  c.put(low,initial);c.put(h[6]+0x45cc,bytes([n%2]));c.put(h[4]+0x3cc,struct.pack('>I',seed));c.put(h[2]+0x14,live if patched else stamp)
  c.put(p,struct.pack('>HH',0x7000,0x8000));c.put(p+12,struct.pack('>H',(n//4)%8));c.put(p+17,bytes([1+n%4]));c.put(p+28,struct.pack('>H',1024));c.put(p+44,b'\0')
  c.put(p+83,bytes([[0,1,2,3,4,5,127,128,255][n//2%9],[0,1,2,15,255][n//18%5]]))
  c.put(h[4]+0x440,b'\0\1');c.put(h[1]+0x1d8,b'\x70');c.put(h[1]+0x1dc,b'\x80');c.put(h[6]+0x395c,bytes([3 if n//90%2 else 0]));c.put(h[6]+0x157b,b'\x05')
  for off,val in [(0x56,0x70),(0xd0,0x80),(0xd6,0x80),(0x150,0),(0x156,(n*11)&255),(0x256,3)]:c.put(p+off+5,bytes([val]))
  trace.clear();badwrites.clear();blocked=False;checking=True
  if patched:got=call('world_script_resume' if resume else 'world_script_step',{1:p,2:clone})
  else:
   c.rw(6,p);c.rw(8,0x8f000);c.call(h[0]+(0x9fb0 if resume else 0x9f74));expected=2 if blocked else 0
  checking=False;assert not badwrites,(n,badwrites[:8])
  state=bytearray(c.get(low,length));state[h[2]+0x14-low:h[2]+0x1c-low]=bytes(8)
  results.append((bytes(state),list(trace)))
 assert got==expected and results[0]==results[1],(n,got,expected,[hex(low+i) for i,(a,b) in enumerate(zip(results[0][0],results[1][0])) if a!=b][:12],results[0][1],results[1][1])
 outcomes[got]+=1;drawcounts.add(sum(e[0]=='bound' for e in trace));resumes+=resume
assert outcomes[2] and max(drawcounts)>0,(outcomes,drawcounts)
before=c.get(low,length)
for name in ['world_script_step','world_script_resume']:
 assert call(name,{1:p+2,2:clone})==0xffffffff
 assert c.get(low,length)==before
rejects=0
for start,size,offsets in [(0x9f74,472,[0,0x32,0x36,0x38,0x3c,0x176,0x178,0x18a,0x18c,0x1d6]),(0x8050,16,[0,4,8,12])]:
 original=c.get(h[0]+start,size)
 for off in offsets:
  corrupt=bytearray(original);corrupt[off]^=1;c.put(h[0]+start,corrupt);c.put(0x3a0000,b'Z'*600)
  assert call('world_script_prepare',{1:h[0],2:0x3a0000,3:rc,4:hit,5:h[6]})==0xffffffff
  assert c.get(0x3a0000,600)==b'Z'*600
  rejects+=1
 c.put(h[0]+start,original)
print(json.dumps(dict(status='passed',signature_rejections=rejects,cases=1024,outcomes=outcomes,resume_cases=resumes,draw_counts=sorted(drawcounts),calls=calls)))
c.close()
