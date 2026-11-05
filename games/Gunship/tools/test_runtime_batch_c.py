"""Assembly batch driver versus independently delivered field/world sequence."""
source=open(__file__.replace('test_runtime_batch_c.py','test_timing_runtime_c.py')).read()
exec(source.split('# Loader-facing lookup')[0])
CODE=C.CFUNCTYPE(None,C.c_void_p,C.c_uint64,C.c_uint32,C.c_void_p)
trace=[];inject=False
@CODE
def completed(handle,a,n,user):
 global inject
 trace.append((c.get(p,86),c.get(ptr('ENDPOINT'),164)))
 if inject:
  inject=False
  # Simulate producer publication after the snapshot, payload before cursor.
  history=ptr('HISTORY');index=word(history);record=bytearray(c.get(SAMPLE,40));struct.pack_into('>I',record,0,1002)
  c.put(history+20+(index%128)*40,record);c.put(history+16,struct.pack('>I',1002));c.put(history,struct.pack('>H',(index+1)&65535))
entry=base+sym('scheduler_player_done');codehook=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(codehook),1<<2,completed,None,entry,entry))
def setup(rate):
 c.put(low,initial);c.put(ARENA-16,b'\xa5'*(size+32))
 b=bytearray(86);struct.pack_into('>HH',b,0,0x7000,0x8000);struct.pack_into('>H',b,28,4096);b[27]=128;b[57]=26;b[66]=28;b[65]=1;b[17]=2;c.put(p,b)
 prepare(rate)
 for off in [0xaf36,0xa150,0xb4e4,0xb57c,0xb0a6,0xb2e0]:c.put(h[0]+off,bytes.fromhex('4e75'))
 c.put(h[0]+0xc654,bytes.fromhex('70054e75'));c.put(h[0]+0x7fa4,bytes.fromhex('70004e75'))
 c.put(h[4]+0x1c5,bytes(2));c.put(h[4]+0x440,bytes(2));c.put(h[0]+0x9c42,bytes(1));c.put(h[0]+0xba08,bytes(4));c.put(h[0]+0xba0c,b'\xff\xff\xff\xff');c.put(h[6]+0x1558,bytes([99]*6));c.put(p+0x256+5,b'\1');c.put(h[0]+0xa44d,b'\xff\0\0');c.put(h[0]+0xa436,bytes(1))
 c.put(h[2]+0x1c,struct.pack('>I',1000));c.put(h[2]+0x0c,bytes(4));c.put(ptr('CAPTURE')+24,struct.pack('>I',500))
 call('timing_runtime_activate',{1:ARENA});trace.clear()
def publish(n,key=None):
 call('commands_publish',{1:ptr('COMMANDS'),9:500+n,10:[0x51,1,2,0x38][n%4] if key is None else key},1)
 c.put(SAMPLE,struct.pack('>6IHhhHII',1000+n,[0,1,0,255][n%4],0,0,0,500+n,8,0,0,0,10,n))
 call('history_publish',{1:ptr('HISTORY'),2:SAMPLE},1)
def pump(fields=128,worlds=8,commands=128):
 rs={r:rng.randrange(0x1000000) for r in range(1,17) if r!=8};rs.update({1:ARENA,9:fields,10:worlds,11:commands})
 for r,v in rs.items():c.rw(r,v&0xffffffff)
 c.rw(8,0x8f000);c.call(base+sym('timing_runtime_batch'))
 assert c.rr(8)==0x8f004 and all(c.rr(r)==v&0xffffffff for r,v in rs.items() if r!=9)
 return c.rr(9)
runs=[];yields=0
for rate in (50,60):
 baseline=None
 for batch in (0,1,3,10,25):
  setup(rate)
  for start in range(1,121,batch or 1):
   for n in range(start,min(start+(batch or 1),121)):publish(n)
   if not batch:
    call('scheduler_begin',{1:ptr('SCHEDULER'),9:128,10:8});call('scheduler_next',{1:ptr('SCHEDULER'),2:ptr('RECORD')},1)
    call('timing_flight_consume',{1:ptr('CONSUMER'),9:128},n*3//rate-(n-1)*3//rate)
   else:
    result=pump(commands=1 if batch in (3,25) else 128)
    while result==1:
     yields+=1;assert yields<10000;result=pump(commands=1 if batch in (3,25) else 128)
    assert result==0,(rate,batch,start,result)
  state=(list(trace),c.get(p,86),c.get(ptr('ENDPOINT'),164),long(ptr('SCHEDULER')+32),long(ptr('SCHEDULER')+36))
  if baseline is None:baseline=state
  else:assert state==baseline,(rate,batch)
  assert len(trace)==120 and state[-2:]==(120,360//rate)
  runs.append((rate,batch))
# Invalid public admission is atomic.
setup(50)
for offset,width,value in [(0,4,0),(sym('RT_CAPTURE_OWNER'),2,0),(sym('RT_BATCH'),2,7),(sym('RT_SCHEDULER')+12,2,1),(sym('RT_SCHEDULER')+16,2,1),(sym('RT_SCHEDULER')+20,2,1)]:
 saved=c.get(ARENA+offset,width);c.put(ARENA+offset,value.to_bytes(width,'big'));before=c.get(ARENA,size)
 assert pump()==0xfffffffd and c.get(ARENA,size)==before;c.put(ARENA+offset,saved)
for fields,worlds,commands in [(0,8,128),(129,8,128),(128,0,128),(128,9,128),(128,8,0),(128,8,129)]:
 before=c.get(ARENA,size);assert pump(fields,worlds,commands)==0xfffffffd and c.get(ARENA,size)==before
# Publication during consumption belongs to the next snapshot.
setup(50);publish(1);inject=True;assert pump()==0
assert long(ptr('SCHEDULER')+32)==1 and word(ptr('HISTORY'))-word(ptr('HISTORY')+2)==1
assert pump()==0 and long(ptr('SCHEDULER')+32)==2
# Field and world limits stay latched; no silent new batch or dropped records.
for fields,worlds,want_fields in [(7,8,7)]:
 setup(50)
 for n in range(1,41):publish(n)
 assert pump(fields,worlds)==0xfffffffe
 assert long(ptr('SCHEDULER')+32)==want_fields and word(ptr('BATCH'))==6
 before=c.get(ARENA,size),c.get(low,length)
 assert pump()==0xfffffffe and (c.get(ARENA,size),c.get(low,length))==before
 call('timing_runtime_suspend',{1:ARENA});c.put(h[2]+0x1c,struct.pack('>I',2000));c.put(ptr('CAPTURE')+24,struct.pack('>I',540))
 call('timing_runtime_activate',{1:ARENA});assert word(ptr('BATCH'))==0 and pump()==0
# World-budget yields retain unread fields, phase, commands and motion.
for rate in (50,60):
 results=[]
 for bound in (8,1):
  setup(rate)
  for n in range(1,61):publish(n)
  status=pump(128,bound)
  if bound==1:
   assert status==5 and word(ptr('BATCH'))==0
   assert word(ptr('SCHEDULER')+16)==0 and word(ptr('SCHEDULER')+18)==0
   assert long(ptr('SCHEDULER')+36)==1
   assert word(ptr('HISTORY'))-word(ptr('HISTORY')+2)>0
   while status==5:status=pump(128,bound)
  assert status==0 and long(ptr('HISTORY')+12)==0
  results.append((list(trace),c.get(p,86),c.get(ptr('ENDPOINT'),164),c.get(ptr('CLOCK'),28)))
 assert results[0]==results[1],rate
# Lifecycle command retained on exactly the same delivered field.
setup(50);publish(1,0x42);assert pump()==2
assert word(ptr('BATCH'))==2 and word(ptr('SCHEDULER')+12)==1 and long(ptr('SCHEDULER')+32)==0
before=c.get(ARENA,size),c.get(low,length);assert pump()==2 and (c.get(ARENA,size),c.get(low,length))==before
# Committed geometry ends the flight once; a repeated call cannot clean up twice.
setup(50);c.put(p,struct.pack('>HH',0x7fff,0x7fff));c.put(p+28,bytes(2));c.put(p+27,bytes(1));c.put(p+57,bytes(1));c.put(p+66,bytes(1));c.put(p+26,bytes(1))
call('control_mode_init',{1:ptr('MODE'),2:p})
for off,v in zip([0x3be3,0x3c5d,0x3c63,0x3cdd,0x3ddd,0x3d5d],struct.pack('>HHH',0x7fff,0x7fff,24)):c.put(h[6]+off,bytes([v]))
for n in range(1,18):publish(n,0)
assert pump()==4 and word(ptr('BATCH'))==4 and long(ptr('SCHEDULER')+36)==1
before=c.get(ARENA,size),c.get(low,length);assert pump()==4 and (c.get(ARENA,size),c.get(low,length))==before
# Upstream failure cannot resume even if someone clears the upstream flag.
setup(50);c.put(ptr('HISTORY')+6,b'\0\1');assert pump()==0xffffffff and word(ptr('BATCH'))==5
c.put(ptr('HISTORY')+6,bytes(2));before=c.get(ARENA,size),c.get(low,length)
assert pump()==0xffffffff and (c.get(ARENA,size),c.get(low,length))==before
print(json.dumps(dict(status='passed',runs=runs,fields=1200,command_yields=yields,limits_latched=True,boundary_retained=True)));c.close()
