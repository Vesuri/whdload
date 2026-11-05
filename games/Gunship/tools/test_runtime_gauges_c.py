"""Gauges advance on consumption, native painter repairs only selected buffer."""
__file__=__file__.replace('test_runtime_gauges_c.py','test_runtime_batch_c.py')
exec(open(__file__).read().split('runs=[];yields=0')[0])
desc=h[6]+0x9bc;raw=h[6]+0x157d;draws=0;fields=0
for rate in (50,60):
 baseline=None
 for batch in (1,3,10,25):
  setup(rate);c.put(h[0]+0x828a,bytes.fromhex('4e75'))
  # Only gauge drawing pixel writer is stubbed; world path remains bound.
  for start in range(1,101,batch):
   for n in range(start,min(start+batch,101)):publish(n)
   result=pump(commands=1)
   while result==1:result=pump(commands=1)
   assert result==0,(rate,batch,start,result)
   assert word(ptr('GAUGE_PHASE'))==2 and long(ptr('GAUGE_FIELD'))==1000+n
   before=c.get(ptr('GAUGES'),16);private=c.get(ARENA,size);native_raw=c.get(raw,16)
   c.put(h[6]+0x4bb0,struct.pack('>H',draws%2));physical=c.get(desc,84)
   call('timing_runtime_gauge_draw',{1:ARENA})
   assert c.get(raw,16)==native_raw and c.get(ARENA,size)==private
   latest=1-int.from_bytes(before[:2],'big');slot=draws%2
   for i in range(7):
    assert c.get(desc+12*i+8+slot,1)==before[2+2*i+latest:3+2*i+latest]
    assert c.get(desc+12*i+9-slot,1)==physical[12*i+9-slot:12*i+10-slot]
   again=c.get(desc,84);call('timing_runtime_gauge_draw',{1:ARENA});assert c.get(desc,84)==again and c.get(raw,16)==native_raw
   draws+=1
  state=c.get(ptr('GAUGES'),16),c.get(p,86),c.get(ptr('ENDPOINT'),164)
  if baseline is None:baseline=state
  else:assert state==baseline,(rate,batch)
  fields+=100
# Duplicate callback, invalid ownership/phase/state must be atomic.
c.put(ptr('CONSUMER')+sym('TF_PHASE'),b'\0\3')
state=c.get(ARENA,size);native=c.get(low,length)
call('timing_runtime_gauges',{1:ARENA},0xfffffffd);assert c.get(ARENA,size)==state and c.get(low,length)==native
for name,value in [('CAPTURE_OWNER',0),('BOUNDARY_PHASE',2),('GAUGES',2)]:
 saved=c.get(ptr(name),2);c.put(ptr(name),struct.pack('>H',value));state=c.get(ARENA,size)
 call('timing_runtime_gauges',{1:ARENA},0xfffffffd);assert c.get(ARENA,size)==state;c.put(ptr(name),saved)
print(json.dumps(dict(status='passed',fields=fields,draws=draws,repeated_draws=draws,rates=[50,60],batches=[1,3,10,25],raw_targets_restored=True)));c.close()
