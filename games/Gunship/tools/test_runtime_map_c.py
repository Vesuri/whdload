"""Map coordinate refresh follows consumed fields, independently of batches."""
__file__=__file__.replace('test_runtime_map_c.py','test_runtime_batch_c.py')
s=open(__file__).read();exec(s.split('runs=[];yields=0')[0])
maptrace=[]
@CODE
def coordinates_done(handle,a,n,user):
 maptrace.append((long(ptr('SCHEDULER')+24),c.get(p,4),c.get(h[5]+0x48,22)))
mh=C.c_size_t();entry=h[0]+0x487a;ok(u.uc_hook_add(c.h,C.byref(mh),1<<2,coordinates_done,None,entry,entry))
runs=[]
for rate in (50,60):
 baseline=None
 for batch in (1,3,10,25):
  setup(rate);c.put(p+42,struct.pack('>H',2048));c.put(h[4]+0x1c5,b'\1');c.put(h[5]+0x48,bytes(22));maptrace.clear()
  assert long(ptr('CONSUMER')+sym('TF_MAP_ENTRY'))==h[0]+0x475a
  for start in range(1,101,batch):
   for n in range(start,min(start+batch,101)):publish(n)
   assert pump()==0
  assert len(maptrace)==100 and [t[0] for t in maptrace]==list(range(1001,1101))
  assert len({t[1] for t in maptrace})>1
  assert all(t[2][:2]==bytes(2) for t in maptrace) # native map counter reset
  if baseline is None:baseline=list(maptrace)
  else:assert maptrace==baseline,(rate,batch)
  runs.append((rate,batch))
for mode in (0,2,255):
 setup(50);c.put(h[4]+0x1c5,bytes([mode]));maptrace.clear();before=c.get(h[5]+0x48,22)
 for n in range(1,6):publish(n);assert pump()==0
 assert not maptrace and c.get(h[5]+0x48,22)==before
print(json.dumps(dict(status='passed',fields=800,runs=runs,inactive_modes=3,pose_and_coordinates_equal=True)))
c.close()
