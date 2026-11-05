"""Resolve retained fields after UI, including exits and another boundary."""
__file__=__file__.replace('test_runtime_boundary_finish_c.py','test_runtime_batch_c.py')
s=open(__file__).read();exec(s.split('runs=[];yields=0')[0])
_setup_without_ui_stub=setup
def setup(rate):
 _setup_without_ui_stub(rate);c.put(h[0]+0x46de,bytes.fromhex("4e75"))
@CODE
def field_arrival(handle,a,n,user):c.put(h[2]+0x1c,struct.pack('>I',long(h[2]+0x1c)+1))
vh=C.c_size_t();entry=h[0]+0x8188;ok(u.uc_hook_add(c.h,C.byref(vh),1<<2,field_arrival,None,entry,entry))
fault_enabled=False
@CODE
def post_motion_fault(handle,a,n,user):
 if fault_enabled:c.put(ptr('COMMANDS')+8,b'\0\1')
fh=C.c_size_t();entry=base+sym('scheduler_player_done');ok(u.uc_hook_add(c.h,C.byref(fh),1<<2,post_motion_fault,None,entry,entry))
def snap():return c.get(ARENA,size),c.get(low,length)
def finish(want,budget=128):call('timing_runtime_boundary_finish',{1:ARENA,9:budget},want)
def ui(key=0x42,resume_key=1):
 call('timing_runtime_boundary_suspend',{1:ARENA});c.put(h[6]+0x1f0,bytes(4));fifo=h[6]+0x4c68;c.put(fifo,bytes(26))
 if key==0x42:c.put(fifo,struct.pack('>H',resume_key));c.put(fifo+22,struct.pack('>I',1))
 call('timing_runtime_boundary_run',{1:ARENA},4 if key in (0x45,0x833) or resume_key==0x45 else 0)
def rebase(epoch=2000,sequence=600):
 c.put(h[2]+0x1c,struct.pack('>I',epoch));c.put(ptr('CAPTURE')+24,struct.pack('>I',sequence))
 call('timing_runtime_activate',{1:ARENA});assert word(ptr('BOUNDARY_PHASE'))==0
 c.put(SAMPLE,struct.pack('>6IHhhHII',epoch+1,0,0,0,0,sequence,8,0,0,0,10,1));call('history_publish',{1:ptr('HISTORY'),2:SAMPLE},1);assert pump()==0
cases=0
for rate in (50,60):
 for at in (1,(rate+2)//3):
  # Reference completes this same field without a blocking UI interval.
  setup(rate)
  for n in range(1,at+1):publish(n,0);assert pump()==0
  reference=(c.get(p,86),c.get(ptr('ENDPOINT'),164),c.get(ptr('GAUGES'),16),c.get(ptr('ACTOR_PRESENT'),sym('AC_SAFE')+2),long(ptr('SCHEDULER')+32),long(ptr('SCHEDULER')+36))
  setup(rate)
  for n in range(1,at):publish(n,0);assert pump()==0
  publish(at,0x42);assert pump()==2;ui()
  before=snap();finish(0xfffffffd,0);assert snap()==before
  # Budget 1 repeatedly resumes the current reader, including the world reader.
  for i in range(130):
   rs={1:ARENA,9:1}
   for r,v in rs.items():c.rw(r,v)
   c.rw(8,0x8f000);c.call(base+sym('timing_runtime_boundary_finish'));result=c.rr(9)
   assert result in (0,1),(rate,at,result)
   assert word(ptr('CLOCK')+24)==word(ptr('HISTORY')+4)==word(ptr('COMMANDS')+6)==0
   if result==0:break
  else:raise AssertionError('unbounded command retries')
  assert (c.get(p,86),c.get(ptr('ENDPOINT'),164),c.get(ptr('GAUGES'),16),c.get(ptr('ACTOR_PRESENT'),sym('AC_SAFE')+2),long(ptr('SCHEDULER')+32),long(ptr('SCHEDULER')+36))==reference
  before=snap();finish(0xfffffffd);assert snap()==before
  rebase();assert long(ptr('SCHEDULER')+32)==at+1;cases+=1
# Two retained boundary commands in one delivered field, never a new delivery.
setup(50)
for seq,key in ((501,0x40),(502,0x42)):call('commands_publish',{1:ptr('COMMANDS'),9:seq,10:key},1)
c.put(SAMPLE,struct.pack('>6IHhhHII',1001,0,0,0,0,502,8,0,0,0,10,1));call('history_publish',{1:ptr('HISTORY'),2:SAMPLE},1)
assert pump()==2;ui(0x40);finish(1,1);finish(2,1)
assert long(ptr('SCHEDULER')+32)==0 and word(ptr('BOUNDARY_PHASE'))==4
ui();finish(0);assert long(ptr('SCHEDULER')+32)==1;rebase();cases+=1
# Native exit cancels the delivered field rather than reporting motion/world work.
for at in (1,17):
 for key,resume in ((0x45,1),(0x833,1),(0x42,0x45)):
  setup(50)
  for n in range(1,at):publish(n,0);assert pump()==0
  publish(at,key);assert pump()==2;before_steps=long(ptr('SCHEDULER')+32);before_worlds=long(ptr('SCHEDULER')+36)
  ui(key,resume);finish(4)
  assert long(ptr('BOUNDARY_ABORTS'))==1 and long(ptr('SCHEDULER')+32)==before_steps and long(ptr('SCHEDULER')+36)==before_worlds
  assert word(ptr('SCHEDULER')+12)==0 and word(ptr('CONSUMER')+60)==6 and word(ptr('BATCH'))==4
  before=snap();finish(0xfffffffd);assert snap()==before
  c.put(p+24,bytes(1));rebase();assert long(ptr('BOUNDARY_ABORTS'))==1;cases+=1
# A script modal reached while finishing is suspended before returning to caller.
setup(50);c.put(p+83,b'\2\1');c.put(h[2]+16,bytes(4))
for n in range(1,17):publish(n,0);assert pump()==0
publish(17,0x42);assert pump()==2;ui();finish(3)
assert word(ptr('MODAL')+12)==1 and word(ptr('CONSUMER')+60)==5
call('timing_runtime_modal_run',{1:ARENA});assert long(ptr('SCHEDULER')+36)==1
rebase();cases+=1
# A producer-style fault after committed motion is never retried.
setup(50)
for n in range(1,17):publish(n,0);assert pump()==0
publish(17,0x40);assert pump()==2;ui(0x40);fault_enabled=True;finish(0xffffffff)
assert long(ptr('SCHEDULER')+32)==17 and long(ptr('SCHEDULER')+36)==0
assert word(ptr('BOUNDARY_PHASE'))==6 and word(ptr('BATCH'))==5
assert word(ptr('CLOCK')+24)==word(ptr('HISTORY')+4)==word(ptr('COMMANDS')+6)==0
before=snap();finish(0xfffffffd);assert snap()==before
print(json.dumps(dict(status='passed',completion_cases=cases,paused_and_uninterrupted_states_equal=True,manual_exits_counted_separately=True,nested_keyboard_and_script_boundaries=True)));c.close()
