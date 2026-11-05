"""Native guided release and first-interval prediction."""
__file__=__file__.replace('test_runtime_actor_release_c.py','test_runtime_batch_c.py')
s=open(__file__).read();exec(s.split('runs=[];yields=0')[0])
events=[]
@CODE
def capture(handle,a,n,user):
 events.append((long(ptr('CLOCK')+sym('TC_LAST')),word(ptr('CLOCK')+sym('TC_PHASE')),word(h[0]+0xba0c),word(h[0]+0xba0e)))
ch=C.c_size_t();entry=base+sym('actor_present_capture');ok(u.uc_hook_add(c.h,C.byref(ch),1<<2,capture,None,entry,entry))
def publish_fire(n):
 call('commands_publish',{1:ptr('COMMANDS'),9:500+n,10:0},1)
 c.put(SAMPLE,struct.pack('>6IHhhHII',1000+n,0,0,0,0,500+n,8,0,0,1 if n==3 else 0,10,n))
 call('history_publish',{1:ptr('HISTORY'),2:SAMPLE},1)
runs=[]
def release_setup(rate,weapon):
 setup(rate);c.put(p+0x41,bytes([weapon]))
 # The synthetic scene has no target pixels. Native target selection therefore
 # calls the map-panel fallback, which consumes fire as a UI action. Stub only
 # that panel transition; retain target selection, weapon admission, allocation,
 # launch, guidance/release and actor prediction. Terrain is explicitly clear.
 c.put(h[0]+0x46de,bytes.fromhex('4e75'))
 c.put(h[0]+0xb3b2,bytes.fromhex('70004e75'))

for rate in (50,60):
 for weapon in (1,3):
  baseline=None
  for batch in (1,3,10):
   events.clear();release_setup(rate,weapon)
   # Independent in-flight actor: its fraction must not restart on release.
   data=bytearray(0xc2)
   for off,v in [(0,0x6000),(12,0x7000),(24,4096),(36,0)]:struct.pack_into('>H',data,off,v)
   for off,v in [(0,200),(6,8),(18,32),(24,240),(30,16),(36,0),(42,2),(48,64),(66,5)]:data[0x30+off]=v
   c.put(h[0]+0xc6a0,data);c.put(h[0]+0xba08,struct.pack('>H',1))
   views=0;moved=0
   for start in range(1,81,batch):
    for n in range(start,min(start+batch,81)):publish_fire(n)
    assert pump()==0
    rc=ptr('RELEASE_PRESENT')
    if word(rc+sym('AC_VALID')):
     phase=word(ptr('CLOCK')+sym('TC_PHASE'));anchor=word(rc+sym('AC_PHASE'));safe=word(rc+sym('AC_SAFE'));slot=word(h[0]+0xba0e)
     original=c.get(h[0]+0xc6a0,36);world_cache=c.get(ptr('ACTOR_PRESENT'),sym('AC_SIZE'))
     call('timing_runtime_present_state',{1:ARENA})
     assert c.get(h[0]+0xc6a0,36)==original and c.get(ptr('ACTOR_PRESENT'),sym('AC_SIZE'))==world_cache
     if safe:
      for axis in range(3):
       off=axis*12+slot*2;v=word(rc+sym('AC_CURRENT')+off);end=word(rc+sym('AC_NEXT')+off);delta=((end-v+32768)&65535)-32768
       want=(v+delta*((phase-anchor)//3)//((rate-anchor+2)//3))&65535
       assert word(ptr('PRESENT_SCENE')+12+off)==want,(rate,weapon,batch,n,phase,anchor,slot)
      moved+=any(c.get(ptr('PRESENT_SCENE')+12+axis*12+slot*2,2)!=original[axis*12+slot*2:axis*12+slot*2+2] for axis in range(3))
     wc=ptr('ACTOR_PRESENT');wa=word(wc+sym('AC_PHASE'))
     assert word(wc+sym('AC_SAFE'))&1
     for axis in range(3):
      off=axis*12;v=word(wc+sym('AC_CURRENT')+off);end=word(wc+sym('AC_NEXT')+off);delta=((end-v+32768)&65535)-32768
      want=(v+delta*((phase-wa)//3)//((rate-wa+2)//3))&65535
      assert word(ptr('PRESENT_SCENE')+12+off)==want,('unrelated actor jumped',rate,weapon,batch,n)
     views+=1
   release_events=[e for e in events if e[1]>2]
   assert len(release_events)==1 and release_events[0][0]==1000+(rate+2)//3+7,(rate,weapon,batch,events,views,moved)
   assert views and moved,(rate,weapon,batch,events,views,moved)
   assert word(ptr('RELEASE_PRESENT')+sym('AC_VALID'))==0
   state=(c.get(p,86),c.get(h[0]+0xc6a0,0xc2),list(events))
   if baseline is None:baseline=state
   else:assert state==baseline,(rate,weapon,batch)
   runs.append(dict(rate=rate,weapon=weapon,batch=batch,release=release_events[0][0]-1000,views=views,moving_views=moved))
# Identity loss before the real native release must suppress its cache.
barriers=0
for kind in ('generation','exhaustion','captured_exhaustion','missing_allocation'):
 release_setup(50,1)
 for n in range(1,24):publish_fire(n);assert pump()==0
 slot=word(h[0]+0xba0e);assert slot==5
 wc=ptr('ACTOR_PRESENT')
 if kind=='generation':c.put(ptr('ACTOR_GENERATIONS')+4*slot,struct.pack('>I',1))
 elif kind=='exhaustion':c.put(ptr('ACTOR_GENERATIONS')+24,struct.pack('>H',1<<slot))
 elif kind=='captured_exhaustion':c.put(wc+sym('AC_GENERATIONS')+24,struct.pack('>H',1<<slot))
 else:c.put(wc+sym('AC_MASKS'),bytes(2))
 publish_fire(24);assert pump()==0
 assert word(h[0]+0xba0c)&(1<<slot)
 assert word(ptr('RELEASE_PRESENT')+sym('AC_VALID'))==0,kind
 barriers+=1
print(json.dumps(dict(status='passed' ,runs=runs,fields=1056,identity_barriers=barriers,unrelated_prediction_unchanged=True,batch_invariant=True)));c.close()
