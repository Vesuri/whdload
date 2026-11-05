"""Effects in real runtime batches: every field, renders independent, spawn order."""
__file__=__file__.replace('test_runtime_effects_c.py','test_runtime_batch_c.py')
s=open(__file__).read();exec(s.split('runs=[];yields=0')[0])
# Trace the newly integrated field effect owner, before the deadline world path.
effects=[]
@CODE
def effect_done(handle,a,n,user):
 effects.append((long(ptr('SCHEDULER')+24),c.get(h[0]+0xc6d0,90),c.get(h[0]+0xba08,4)))
eh=C.c_size_t();entry=base+sym('scheduler_player_done');ok(u.uc_hook_add(c.h,C.byref(eh),1<<2,effect_done,None,entry,entry))
runs=[]
for rate in (50,60):
 reference=None
 for batch in (1,3,10,25):
  setup(rate);effects.clear()
  # Native world effect spawn is selected by the hit countdown. It is consumed
  # on field time; this triggers real construction on the first deadlines.
  c.put(h[6]+0x42f7,bytes([120]));c.put(h[0]+0xc6d0,bytes(90))
  for start in range(1,121,batch):
   for n in range(start,min(start+batch,121)):publish(n,0)
   assert pump()==0
  state=(list(effects),c.get(h[0]+0xc6d0,90),c.get(h[0]+0xba08,4),c.get(h[4]+0x3cc,4))
  first=next(row for row in effects if any(row[1][6:12]))
  assert first[0]==1000+(rate+2)//3+1,(rate,first[0])
  assert first[1][11]==9 and first[1][17]==0 and first[1][89]==11,(rate,first) # slot 5: first post-spawn field
  if reference is None:reference=state
  else:assert state==reference,(rate,batch)
  runs.append((rate,batch))
print(json.dumps(dict(status='passed',fields=960,runs=runs,compared='per-field slot state, masks and final RNG seed')))
c.close()
