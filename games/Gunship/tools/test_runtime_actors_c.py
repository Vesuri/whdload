"""Post-world actor capture and renderer-only prediction in the runtime."""
__file__=__file__.replace('test_runtime_actors_c.py','test_runtime_batch_c.py')
s=open(__file__).read();exec(s.split('runs=[];yields=0')[0])
# The native world oracle uses the known clear-terrain result. Preview never
# calls it. Positive-height actor trajectory is identical for either result.
runs=[];views=0;moving_views=0;captures=[];maskwrites=[]
@MEM
def mask_watch(handle,kind,a,n,v,user):
 if a<=h[0]+0xba08<a+n:maskwrites.append((hex(c.rr(18)),v))
mh=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(mh),1<<11,mask_watch,None,h[0]+0xba08,h[0]+0xba09))
@CODE
def captured(handle,a,n,user):captures.append((long(ptr('CLOCK')+sym('TC_TICKS')),word(ptr('CLOCK')+sym('TC_PHASE'))))
ch=C.c_size_t();entry=base+sym('timing_runtime_actors_seed');ok(u.uc_hook_add(c.h,C.byref(ch),1<<2,captured,None,entry,entry))
for rate in (50,60):
 baseline=None
 for batch in (1,3,10):
  captures.clear();setup(rate);c.put(h[0]+0xb3b2,bytes.fromhex('70004e75'))
  # A new unguided actor is introduced after the activation seed. Until the
  # next completed world tick, no previous slot endpoint may be borrowed.
  data=bytearray(0xc2)
  for off,v in [(0,0x6000),(12,0x7000),(24,4096),(36,0)]:struct.pack_into('>H',data,off,v)
  for off,v in [(0,64),(6,8),(18,32),(24,240),(30,16),(36,0),(42,2),(48,64),(66,5)]:data[0x30+off]=v
  c.put(h[0]+0xc6a0,data);c.put(h[0]+0xba08,struct.pack('>H',1));c.put(ptr('ACTOR_GENERATIONS'),struct.pack('>I',1))
  for start in range(1,101,batch):
   for field in range(start,min(start+batch,101)):publish(field,0)
   assert pump()==0
   tick=long(ptr('CLOCK')+sym('TC_TICKS'));phase=word(ptr('CLOCK')+sym('TC_PHASE'));cache=ptr('ACTOR_PRESENT')
   actor_before=c.get(h[0]+0xba08,8),c.get(h[0]+0xc6a0,0xc2),c.get(ptr('ACTOR_GENERATIONS'),26)
   original=c.get(h[0]+0xc6a0,36);want=bytearray(original)
   if tick:
    assert long(cache+sym('AC_TICK'))==tick and word(cache+sym('AC_SAFE'))&1,(rate,batch,field,tick,long(cache+sym('AC_TICK')),word(cache+sym('AC_SAFE')),c.get(h[0]+0xba08,8).hex(),c.get(h[0]+0xc6d0,90).hex(),captures,maskwrites[-20:])
    anchor=word(cache+sym('AC_PHASE'));elapsed=(phase-anchor)//3;interval=(rate-anchor+2)//3
    for axis in range(3):
     off=axis*12;v=word(cache+sym('AC_CURRENT')+off);n=word(cache+sym('AC_NEXT')+off);delta=((n-v+32768)&65535)-32768
     struct.pack_into('>H',want,off,(v+delta*elapsed//interval)&65535)
   call('timing_runtime_present_state',{1:ARENA})
   assert c.get(ptr('PRESENT_SCENE')+12,36)==want,(rate,batch,field,tick,phase,word(cache+sym('AC_PHASE')),c.get(ptr('PRESENT_SCENE')+12,36).hex(),want.hex(),[(i,c.get(cache+sym('AC_BYTES')+i,1).hex(),c.get(h[0]+0xc6d0+i,1).hex()) for i in range(90) if c.get(cache+sym('AC_BYTES')+i,1)!=c.get(h[0]+0xc6d0+i,1)])
   for dest in (h[4]+12,h[5]+22,h[6]+0x3910):assert c.get(dest,36)==want
   assert (c.get(h[0]+0xba08,8),c.get(h[0]+0xc6a0,0xc2),c.get(ptr('ACTOR_GENERATIONS'),26))==actor_before
   moving_views+=want!=original;views+=1
  assert len(captures)==1+300//rate and captures[0]==(0,0)
  assert captures[1:]==[(t,((t*rate+2)//3*3)%rate) for t in range(1,300//rate+1)],captures
  final=c.get(h[0]+0xc6a0,0xc2),c.get(cache+sym('AC_CURRENT'),48),c.get(cache+sym('AC_NEXT'),36),c.get(p,86)
  if baseline is None:baseline=final
  else:assert final==baseline,(rate,batch)
  # A same-pose allocation reuse must fall back to the committed scene.
  c.put(ptr('ACTOR_GENERATIONS'),struct.pack('>I',2));call('timing_runtime_present_state',{1:ARENA})
  assert c.get(ptr('PRESENT_SCENE')+12,36)==c.get(h[0]+0xc6a0,36)
  runs.append((rate,batch))
# Direct callback admission failures must leave every byte unchanged.
setup(50)
for n in range(1,18):publish(n,0)
assert pump()==0
before=c.get(ARENA,size),c.get(low,length);call('timing_runtime_actors',{1:ARENA},0xfffffffd);assert (c.get(ARENA,size),c.get(low,length))==before
# Suspend/activate resets the prediction epoch along with generation stamps.
call('timing_runtime_suspend',{1:ARENA});c.put(ptr('ACTOR_GENERATIONS'),b'\xff'*26);c.put(ptr('ACTOR_PRESENT')+sym('AC_TICK'),b'\xff'*4)
c.put(h[2]+0x1c,struct.pack('>I',2000));call('timing_runtime_activate',{1:ARENA})
assert c.get(ptr('ACTOR_GENERATIONS'),26)==bytes(26)
assert c.get(ptr('ACTOR_PRESENT')+sym('AC_GENERATIONS'),26)==bytes(26)
assert long(ptr('ACTOR_PRESENT')+sym('AC_TICK'))==long(ptr('CLOCK')+sym('TC_TICKS'))
assert moving_views>0
print(json.dumps(dict(status='passed',runs=runs,fields=600,views=views,predicted_views=moving_views,capture_once_per_tick=True,batch_invariant=True,generation_reuse_falls_back=True,lifecycle_reseed=True,arena_bytes=size)));c.close()
