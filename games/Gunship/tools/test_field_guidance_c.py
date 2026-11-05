"""Native field guidance state versus extracted update-only routine."""
import json,random,itertools
from unicorn_b import *
from layout import locate
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks'];p=h[6]+0x3b88
c=CPU();c.put(0x200000,mem);c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/field-guidance.hunk')).get_segments()[0].get_data()))
listing=(root/'tmp/c/field-guidance.lst').read_text()
def sym(n):return base+int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
clone=0x330000;private=0x340000;rng=random.Random(0xa1c8);calls=0
# Omit graphics callbacks on the reference, retaining native state progression.
for off in [0xa2f0,0xa35a]:c.put(h[0]+off,bytes.fromhex('4e75'))
def call(name,args):
 global calls
 regs={r:rng.randrange(0x1000000) for r in range(1,17) if r not in [8,9]};regs.update(args)
 for r,v in regs.items():c.rw(r,v)
 c.rw(8,0x8f000);c.call(sym(name));calls+=1
 assert c.rr(18)==0x90000 and c.rr(8)==0x8f004
 assert all(c.rr(r)==v for r,v in regs.items() if r!=9),name
 return c.rr(9)
assert call('field_guidance_prepare',{1:h[0],2:clone,3:h[4],4:private})==0
phase=h[0]+0xa44d;hidden=h[0]+0xa436;busy=h[0]+0xc757;mask=h[0]+0xba0c;quit=h[4]+0x1c6
regions=[(phase,3),(hidden,1),(busy,1),(mask,4)]
MEM=C.CFUNCTYPE(None,C.c_void_p,C.c_int,C.c_uint64,C.c_int,C.c_int64,C.c_void_p)
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
checking=False;bad=[]
@MEM
def write(handle,kind,a,n,value,user):
 if checking and not(any(start<=a and a+n<=start+size for start,size in regions) or a==private and n==1 or 0x8e000<=a and a+n<=0x8f004):bad.append((hex(a),n))
hook=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hook),1<<11,write,None,1,0))
cases=0
for state,pending,view,hide,slot in itertools.product([0,4,5,29,30,31,127,255],[0,255],[0,32],[0,255],[0,1,5,15,16,31,32,65535]):
 initial=[bytes([state,1,rng.choice([0,5,6])]),bytes([hide]),bytes([pending]),struct.pack('>HH',0x1020,slot)]
 results=[];c.put(quit,b'\0');c.put(p+26,bytes([view]))
 for patched in [False,True]:
  for (a,size),value in zip(regions,initial):c.put(a,value)
  c.put(private,bytes([pending]));c.put(busy,b'\x55' if patched else bytes([pending]))
  checking=True;bad.clear()
  if patched:assert call('field_guidance_step',{1:clone})==1
  else:c.rw(8,0x8f000);c.call(h[0]+0xa1c8)
  checking=False;assert not bad,bad
  results.append([c.get(private if patched and a==busy else a,size) for a,size in regions])
  if patched:assert c.get(busy,1)==b'\x55'
 assert results[0]==results[1],(state,pending,view,hide,slot)
 cases+=1
for ended,enabled in [(0,0),(1,1),(255,1)]:
 c.put(quit,bytes([ended]));c.put(phase+1,bytes([enabled]));before=[c.get(a,size) for a,size in regions]
 assert call('field_guidance_step',{1:clone})==0
 assert before==[c.get(a,size) for a,size in regions]
# Constructor and completion events replayed in order, including slot replacement.
baseline=None
for batch in [1,3,10,25]:
 c.put(quit,b'\0');c.put(p+26,b'\0');c.put(hidden,b'\0');c.put(private,b'\0');c.put(mask,struct.pack('>HH',0,1));c.put(phase,b'\0\1\0')
 states=[]
 for first in range(1,56,batch):
  for field in range(first,min(first+batch,56)):
   if field==16:
    c.put(mask,struct.pack('>HH',0,2));c.put(phase,b'\0\1\0');c.put(private,b'\0')
   if field==50:c.put(private,b'\0')
   call('field_guidance_step',{1:clone})
   states.append((c.get(mask,4),c.get(phase,2),c.get(private,1)))
 assert all(v[0][:2]==b'\0\0' for v in states[:5]) and states[5][0][:2]==b'\0\2'
 assert all(v[0][:2]==b'\0\0' for v in states[15:20]) and states[20][0][:2]==b'\0\4'
 assert states[49][0][2:]==b'\xff\xff' and states[49][1]==b'\xff\0'
 if baseline is None:baseline=states
 else:assert states==baseline
# Hybrid acknowledgement matches a native swap before each active field and
# is unaffected by arbitrary actual swap-byte changes.
lanes=[]
for patched in [False,True]:
 c.put(quit,b'\0');c.put(p+26,b'\0');c.put(hidden,b'\0');c.put(mask,struct.pack('>HH',0,1));c.put(phase,b'\xff\1\0');c.put(private,b'\0');c.put(busy,b'\0')
 states=[]
 for field in range(1,73):
  if patched:
   c.put(busy,bytes([(field*17)&255]));call('field_guidance_advance',{1:clone})
  elif c.get(phase+1,1)!=b'\0':
   c.put(busy,b'\0');c.rw(8,0x8f000);c.call(h[0]+0xa1c8)
  states.append([c.get(private if patched and a==busy else a,size) for a,size in regions])
 lanes.append(states)
assert lanes[0]==lanes[1]
assert lanes[1][6][3][:2]==b'\0\2' and lanes[1][32][0][:2]==b'\xff\0'
original=c.get(h[0]+0xa1c8,296);rejects=0
for off in [0,4,294,0x44,0x46,0xc2,0xc4,0xf6,0xf8,0x114,0x116,0x22,0x24,0x28,0x2a,0x4c,0x4e,0x5a,0x5c]:
 corrupt=bytearray(original);corrupt[off]^=1;c.put(h[0]+0xa1c8,corrupt);c.put(0x370000,b'Z'*308)
 assert call('field_guidance_prepare',{1:h[0],2:0x370000,3:h[4],4:private})==0xffffffff
 assert c.get(0x370000,308)==b'Z'*308;rejects+=1
c.put(h[0]+0xa1c8,original)
print(json.dumps(dict(status='passed',native_cases=cases,inactive_cases=3,ordered_fields=220,hybrid_fields=72,signature_rejections=rejects,calls=calls)))
c.close()
