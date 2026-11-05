"""Retained boundary suspension and once-only native UI execution."""
__file__=__file__.replace('test_runtime_boundary_c.py','test_runtime_batch_c.py')
s=open(__file__).read();exec(s.split('runs=[];yields=0')[0])
_setup_without_ui_stub=setup
def setup(rate):
 _setup_without_ui_stub(rate);c.put(h[0]+0x46de,bytes.fromhex("4e75"))
def snapshot():return c.get(ARENA,size),c.get(low,length)
def reject(name):
 before=snapshot();call(name,{1:ARENA},0xfffffffd);assert snapshot()==before
fault_enabled=False
@CODE
def fail_mark(handle,a,n,user):
 if fault_enabled:c.put(ptr('COMMANDS')+8,b'\0\1')
hh=C.c_size_t();entry=base+sym('boundary_command_mark');ok(u.uc_hook_add(c.h,C.byref(hh),1<<2,fail_mark,None,entry,entry))
cases=0
for at in (1,17):
 for key,resume_key in ((0x40,None),(0x42,1),(0x42,0x45),(0x45,None),(0x833,None)):
  setup(50)
  for n in range(1,at):publish(n,0);assert pump()==0
  publish(at,key);assert pump()==2
  # Later fields are unread debt, not part of the suspended delivered field.
  publish(at+1,0);publish(at+2,0)
  done_before=long(ptr('SCHEDULER')+32);field_before=long(ptr('SCHEDULER')+24);tick_before=c.get(p+12,2)
  call('timing_runtime_boundary_suspend',{1:ARENA})
  assert word(ptr('BOUNDARY_PHASE'))==1 and word(ptr('CAPTURE_OWNER'))==0
  assert word(ptr('CLOCK')+24)==word(ptr('HISTORY')+4)==word(ptr('COMMANDS')+6)==0
  assert long(ptr('HISTORY')+12)==2 and word(ptr('SCHEDULER')+12)==1
  reject('timing_runtime_boundary_suspend');reject('timing_runtime_activate')
  c.put(h[6]+0x1f0,bytes(4));fifo=h[6]+0x4c68;c.put(fifo,bytes(26))
  if resume_key is not None:c.put(fifo,struct.pack('>H',resume_key));c.put(fifo+22,struct.pack('>I',1))
  # Native fields can elapse while private owners remain paused.
  c.put(h[2]+0x1c,struct.pack('>I',1500))
  ended=key in (0x45,0x833) or resume_key==0x45
  call('timing_runtime_boundary_run',{1:ARENA},4 if ended else 0)
  assert word(ptr('BOUNDARY_PHASE'))==(5 if ended else 4)
  assert word(ptr('CLOCK')+24)==word(ptr('HISTORY')+4)==word(ptr('COMMANDS')+6)==0
  assert long(ptr('SCHEDULER')+32)==done_before and long(ptr('SCHEDULER')+24)==field_before and c.get(p+12,2)==tick_before
  index=word(ptr('COMMANDS')+2)&127;assert word(ptr('COMMANDS')+24+index*8+6)==1
  if resume_key is not None:assert long(fifo+22)==0
  reject('timing_runtime_boundary_run');reject('timing_runtime_activate');cases+=1
# Admission failures are atomic even when a boundary is otherwise retained.
setup(50);publish(1,0x40);assert pump()==2
for address,width,value in [(ARENA,4,0),(ptr('CAPTURE_OWNER'),2,0),(ptr('BOUNDARY_PHASE'),2,1),(ptr('BOUNDARY'),4,0),(ptr('BATCH'),2,1),(ptr('SCHEDULER')+12,2,2),(ptr('CONSUMER')+60,2,2),(ptr('PLAYER_READER')+18,2,1),(ptr('PLAYER_READER')+12,4,0),(ptr('PLAYER_READER')+16,2,0x42),(ptr('CLOCK')+24,2,0),(ptr('HISTORY')+6,2,1),(ptr('COMMANDS')+8,2,1)]:
 saved=c.get(address,width);c.put(address,value.to_bytes(width,'big'));reject('timing_runtime_boundary_suspend');c.put(address,saved)
call('timing_runtime_boundary_suspend',{1:ARENA})
for address,width,value in [(ARENA,4,0),(ptr('BOUNDARY_PHASE'),2,2),(ptr('CAPTURE_OWNER'),2,1),(ptr('CLOCK')+24,2,1),(ptr('HISTORY')+4,2,1),(ptr('COMMANDS')+6,2,1),(ptr('SCHEDULER')+12,2,2),(ptr('CONSUMER')+60,2,2),(h[5]+0x60,4,h[6]+2)]:
 saved=c.get(address,width);c.put(address,value.to_bytes(width,'big'));reject('timing_runtime_boundary_run');c.put(address,saved)
# A failure after native effects retains applied/unmarked state and blocks replay.
setup(50);publish(1,0x40);assert pump()==2;call('timing_runtime_boundary_suspend',{1:ARENA});fault_enabled=True
call('timing_runtime_boundary_run',{1:ARENA},0xffffffff)
assert word(ptr('BOUNDARY_PHASE'))==3;reject('timing_runtime_boundary_run')
c.put(ptr('SCHEDULER')+12,bytes(2));c.put(ptr('CONSUMER')+60,b'\0\4');reject('timing_runtime_activate')
print(json.dumps(dict(status='passed',native_boundary_cases=cases,atomic_suspend_rejections=13,pending_tick_preserved=True,post_effect_failure_retained=True)));c.close()
