"""A marked boundary resumes the same delivered field and later world reader."""
__file__=__file__.replace('test_boundary_mark_runtime_c.py','test_runtime_batch_c.py')
s=open(__file__).read();exec(s.split('runs=[];yields=0')[0])
tails=[]
@CODE
def tail(handle,a,n,user):tails.append(long(ptr('SCHEDULER')+24))
hh=C.c_size_t();entry=base+sym('control_target_tail');ok(u.uc_hook_add(c.h,C.byref(hh),1<<2,tail,None,entry,entry))
setup(50);publish(1,1);assert pump()==0
publish(2,12);assert pump()==2 and len(tails)==1
call('commands_peek',{1:ptr('COMMANDS'),2:SAMPLE+64,9:502,10:0},1)
record=SAMPLE+64
call('commands_pause',{1:ptr('COMMANDS')})
call('boundary_command_step',{1:p,2:ptr('BOUNDARY'),3:h[6],9:12})
assert len(tails)==2
call('boundary_command_mark',{1:ptr('COMMANDS'),2:record},1)
c.put(ptr('COMMANDS')+6,b'\0\1')
assert pump()==0 and len(tails)==2 and long(ptr('SCHEDULER')+32)==2
for n in range(3,18):publish(n,0)
assert pump()==0 and len(tails)==17 and long(ptr('SCHEDULER')+32)==17 and long(ptr('SCHEDULER')+36)==1
assert c.get(ptr('COMMANDS')+2,2)==c.get(ptr('COMMANDS')+4,2)==c.get(ptr('COMMANDS'),2)
print(json.dumps(dict(status='passed',fields=17,worlds=1,yaw_tail_calls=len(tails),both_readers_retired=True)));c.close()
