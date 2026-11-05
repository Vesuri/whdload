"""Real decoy contacts through capture, fraction publication and scene assembly."""
from pathlib import Path
prefix=Path(__file__).with_name('test_actor_preview_c.py').read_text().split('for case in range(1200):')[0]
exec(compile(prefix,__file__,'exec'))
from itertools import combinations
ac=0x130000;ag=0x140000;out=0x150000;scene=0x160000;camera=0x170000
c.put(ag,struct.pack('>6IH',*range(6),0));c.put(camera,bytes.fromhex('123456780100000000000000'))
ps=bytearray(0x2d6);struct.pack_into('>HH',ps,0,12000,14000);struct.pack_into('>H',ps,28,3000);ps[0x44:0x46]=bytes([1,1])
for hi,lo,v in [(0x56,0xd0,1000),(0xd6,0x150,1000),(0x250,0x1d0,500)]:ps[hi+1]=v>>8;ps[lo+1]=v&255
views=0;moving=0;captures=0
publishing=False;allowed=None;publication_writes=[]
@MEM
def publication_write(handle,kind,a,n,v,user):
 if publishing and not(allowed[0]<=a and a+n<=allowed[1] or 0x8e000<=a and a+n<=0x8f004):publication_writes.append((a,n))
publication_hook=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(publication_hook),1<<11,publication_write,None,1,0))
for hits in [(i,) for i in range(6)]+list(combinations(range(6),2))+[tuple(range(6))]:
 hitmask=sum(1<<i for i in hits);safe=63^hitmask
 data=bytearray(0xc2)
 for slot in range(6):
  for off,v in [(0,1000 if slot in hits else 6000+slot*300),(12,1000 if slot in hits else 7000),(24,500 if slot in hits else 3000)]:struct.pack_into('>H',data,off+2*slot,v)
  for off,v in [(0,64),(6,0 if slot in hits else 8),(18,0),(24,240),(30,16),(36,1 if slot in hits else 0),(42,0),(48,255 if slot in hits else 16),(66,5)]:data[0x30+off+slot]=v
 c.put(p,ps);c.put(h[0]+0xc6a0,data);c.put(h[0]+0xba08,struct.pack('>4H',63,0,63,0));c.put(h[6]+0x42e8,bytes(2))
 original=c.get(0x97ee00,0x21200)
 # The independent native routine supplies the reference movement endpoints.
 c.rw(6,p);c.rw(8,0x8f000);c.call(h[0]+0xbed4);assert c.rr(18)==0x90000
 expected=c.get(h[0]+0xc6a0,36);assert c.get(h[0]+0xc754,1)==bytes([len(hits)])
 c.put(0x97ee00,original)
 for rate in (50,60):
  # Normal world remainders and a partial guided-release interval.
  for anchor in (0,1,2,22):
   call('actor_present_capture',{1:ac,2:ap,3:ag,4:p,9:123,10:anchor},0);captures+=1
   assert int.from_bytes(c.get(ac+sym('AC_SAFE'),2),'big')==safe
   saved=c.get(ac,sym('AC_SIZE'));generation=c.get(ag,26)
   interval=(rate-anchor+2)//3
   for phase in range(anchor,rate,3):
    elapsed=(phase-anchor)//3
    want=bytearray(data[:36])
    for slot in range(6):
     if slot in hits:continue
     for axis in range(3):
      off=axis*12+slot*2;v=int.from_bytes(data[off:off+2],'big');n=int.from_bytes(expected[off:off+2],'big');delta=((n-v+32768)&65535)-32768
      struct.pack_into('>H',want,off,(v+delta*elapsed//interval)&65535)
    for repeat in range(2):
     allowed=(out,out+36);publishing=True
     call('actor_present_build',{1:ac,2:ag,3:out,9:123,10:phase,11:rate},safe)
     assert c.get(out,36)==want,(hits,rate,anchor,phase)
     allowed=(scene,scene+54)
     call('scene_state_build',{1:camera,2:out,3:h[6],4:scene},0)
     publishing=False;assert not publication_writes,publication_writes[:8]
     assert c.get(scene,12)==c.get(camera,12) and c.get(scene+12,36)==want
     assert c.get(0x97ee00,0x21200)==original
     assert c.get(ac,sym('AC_SIZE'))==saved and c.get(ag,26)==generation
    views+=1;moving+=want!=data[:36]
assert moving and views
print(json.dumps(dict(status='passed',contact_sets=22,captures=captures,views=views,repeated_builds=2*views,moving_views=moving,native_endpoint_reference=True,contacted_slots_fixed=True,scene_coordinates_verified=True,world_cache_generation_writes=0,unexpected_publication_writes=0)))
c.close();minus.close()
