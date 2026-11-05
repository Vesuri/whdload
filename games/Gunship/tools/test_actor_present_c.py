"""Generation-certified actor predictions: real capture, pure fraction, barriers."""
from pathlib import Path
prefix=Path(__file__).with_name('test_actor_preview_c.py').read_text().split('for case in range(1200):')[0]
exec(compile(prefix,__file__,'exec'))
ac=0x130000;ag=0x140000;out=0x150000;acsize=sym('AC_SIZE')
# Read-only native source: six flying actors with no nearby impact candidates.
ps=bytearray(0x2d6);struct.pack_into('>HH',ps,0,15000,15000);struct.pack_into('>H',ps,28,4000);c.put(p,ps)
data=bytearray(0xc2)
for slot in range(6):
 for off,v in [(0,1000+100*slot),(12,2000),(24,3000),(36,0)]:struct.pack_into('>H',data,off+2*slot,v)
 for off,v in [(0,64),(6,8),(18,slot*40),(24,240),(30,16),(36,0),(42,2),(48,64),(66,5)]:data[0x30+off+slot]=v
c.put(h[0]+0xc6a0,data);c.put(h[0]+0xba08,struct.pack('>4H',63,0,63,0));c.put(ag,struct.pack('>6IH',*range(6),0))
before=c.get(0x97ee00,0x21200)
call('actor_present_capture',{1:ac,2:ap,3:ag,4:p,9:123,10:1},0)
assert c.get(0x97ee00,0x21200)==before
assert c.get(ac+sym('AC_CURRENT'),48)==data[:48] and c.get(ac+sym('AC_BYTES'),90)==data[48:138]
assert c.get(ac+sym('AC_NEXT'),36)==data[:36]
assert int.from_bytes(c.get(ac+sym('AC_SAFE'),2),'big')==0
# Advance the existing six-slot fixture by one native tick before capture.
old=bytes(data)
for slot in range(6):
 for axis in (0,12,24):
  off=axis+2*slot;struct.pack_into('>H',data,off,(int.from_bytes(data[off:off+2],'big')+10)&65535)
 data[48+slot]-=1
c.put(h[0]+0xc6a0,data)
call('actor_present_capture',{1:ac,2:ap,3:ag,4:p,9:124,10:1},0)
assert c.get(ac+sym('AC_NEXT'),36)==struct.pack('>18H',*[(v+20)&65535 for v in struct.unpack('>18H',old[:36])])
c.put(ac+sym('AC_TICK'),struct.pack('>I',123))
assert c.get(ac+sym('AC_GENERATIONS'),26)==c.get(ag,26)

assert int.from_bytes(c.get(ac+sym('AC_SAFE'),2),'big')==63
saved=c.get(ac,acsize);capture_rejects=0
for phase in (60,65536,0xffffffff):
 call('actor_present_capture',{1:ac,2:ap,3:ag,4:p,9:123,10:phase},0xfffffffd);assert c.get(ac,acsize)==saved;capture_rejects+=1
# Use explicit wrapped endpoints to cover signs and wrap independently of
# the particular projectile speeds present in the captured native fixture.
values=[0,1,32767,32768,65534,65535]*3
next_values=[65535,32768,32768,32767,0,1]*3
current=struct.pack('>18H',*values);nxt=struct.pack('>18H',*next_values)
c.put(h[0]+0xc6a0,current);c.put(ac+sym('AC_CURRENT'),current);c.put(ac+sym('AC_NEXT'),nxt)
world=c.get(0x97ee00,0x21200);cached=c.get(ac,acsize);generations=c.get(ag,26)
# Track writes for presentation; it must touch only the separate output/stack.
violations=[];present_check=False
@MEM
def present_write(handle,kind,a,n,v,user):
 if present_check and not(out<=a and a+n<=out+36 or 0x8e000<=a and a+n<=0x8f004):violations.append((a,n))
hook2=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hook2),1<<11,present_write,None,1,0))
fractions=0
for rate in (50,60):
 for anchor in range(rate):
  c.put(ac+sym('AC_PHASE'),struct.pack('>H',anchor));interval=(rate-anchor+2)//3
  for phase in range(anchor,rate,3):
   elapsed=(phase-anchor)//3;want=[]
   for v,n in zip(values,next_values):delta=((n-v+32768)&65535)-32768;want.append((v+delta*elapsed//interval)&65535)
   violations.clear();present_check=True
   call('actor_present_build',{1:ac,2:ag,3:out,9:123,10:phase,11:rate},63);present_check=False
   assert c.get(out,36)==struct.pack('>18H',*want),(rate,anchor,phase,c.get(out,36).hex())
   assert not violations and c.get(0x97ee00,0x21200)==world
   # Calling twice cannot advance a visual timeline.
   call('actor_present_build',{1:ac,2:ag,3:out,9:123,10:phase,11:rate},63)
   assert c.get(out,36)==struct.pack('>18H',*want)
   fractions+=1
c.put(ac,cached)
def reset():
 c.put(0x97ee00,world);c.put(ac,cached);c.put(ag,generations)
def check_barrier(slot):
 mask=63^(1<<slot);call('actor_present_build',{1:ac,2:ag,3:out,9:123,10:25,11:50},mask)
 for axis in range(3):assert c.get(out+axis*12+slot*2,2)==c.get(h[0]+0xc6a0+axis*12+slot*2,2)
barriers=0
for slot in range(6):
 for address,width in [(ag+4*slot,4),(ag+24,2),(ac+sym('AC_GENERATIONS')+24,2),(h[0]+0xba08,2),(h[0]+0xba0c,2)]:
  reset();old=int.from_bytes(c.get(address,width),'big')
  value=(old+1)&0xffffffff if width==4 else old^(1<<slot)
  c.put(address,value.to_bytes(width,'big'));check_barrier(slot);barriers+=1
 for axis in range(4):
  reset();addr=h[0]+0xc6a0+12*axis+2*slot;c.put(addr,struct.pack('>H',(int.from_bytes(c.get(addr,2),'big')+1)&65535));check_barrier(slot);barriers+=1
 for array in range(15):
  reset();addr=h[0]+0xc6d0+6*array+slot;c.put(addr,bytes([c.get(addr,1)[0]^1]))
  if array in (2,14):call('actor_present_build',{1:ac,2:ag,3:out,9:123,10:25,11:50},63)
  else:check_barrier(slot);barriers+=1
# Selector changes invalidate homing slots only, including every captured
# dependency byte. The shared preview workspace is not the cache's authority.
selector_barriers=0
for slot in range(6):
 for offset in range(12):
  reset()
  c.put(h[0]+0xc6d6+slot,b'\x80')
  c.put(ac+sym('AC_BYTES')+6+slot,b'\x80')
  call('actor_present_build',{1:ac,2:ag,3:out,9:123,10:25,11:50},63)
  address=h[0]+0xaa0a+offset
  c.put(address,bytes([c.get(address,1)[0]^1]))
  c.put(ap+sym('AP_SELECTED'),c.get(h[0]+0xaa0a,12))
  violations.clear();present_check=True
  call('actor_present_build',{1:ac,2:ag,3:out,9:123,10:25,11:50},63);present_check=False
  assert not violations
  selector_barriers+=1
# Native bit-3/4 branches precede bit 7; these modes do not read selection.
for kind in (8,16,0x88,0x90):
 reset()
 c.put(h[0]+0xc6d6,bytes([kind]))
 c.put(ac+sym('AC_BYTES')+6,bytes([kind]))
 c.put(h[0]+0xaa0a,bytes([c.get(h[0]+0xaa0a,1)[0]^1]))
 call('actor_present_build',{1:ac,2:ag,3:out,9:123,10:25,11:50},63)
# Same final allocation/eligibility/pose cannot hide constructor generation.
reset();c.put(ag+20,struct.pack('>I',7));check_barrier(5);barriers+=1
for tick,phase,valid in [(124,25,1),(122,25,1),(123,0,1),(123,2,1),(123,25,0)]:
 reset();c.put(ac+sym('AC_VALID'),struct.pack('>H',valid));call('actor_present_build',{1:ac,2:ag,3:out,9:tick,10:phase,11:50},0);assert c.get(out,36)==current
for rate,phase in [(49,0),(61,0),(50,50),(60,60),(50,0xffffffff)]:
 reset();c.put(out,b'\xa5'*36);call('actor_present_build',{1:ac,2:ag,3:out,9:123,10:phase,11:rate},0xfffffffd);assert c.get(out,36)==b'\xa5'*36
print(json.dumps(dict(status='passed',capture_last_displacement=True,fraction_frames=fractions,repeated_frames=fractions,slot_barriers=barriers,selector_independence=selector_barriers,capture_atomic_rejections=capture_rejects,clock_atomic_rejections=5,stale_cache_cases=5,native_writes=0,context_size=acsize)));c.close();minus.close()
