"""Loop ownership and once-only control flow, with child statuses injected."""
__file__=__file__.replace('test_runtime_loop_control_c.py','test_timing_runtime_c.py')
exec(open(__file__).read().split('# Loader-facing lookup')[0])
ENTER=0x750000;LEAVE=0x750010;c.put(ENTER,bytes.fromhex('4e75'));c.put(LEAVE,bytes.fromhex('4e75'))
CODE=C.CFUNCTYPE(None,C.c_void_p,C.c_uint64,C.c_uint32,C.c_void_p)
names=['activate','batch','draw','boundary_suspend','boundary_run','boundary_finish','modal_suspend','modal_run','suspend']
addresses={base+sym('timing_runtime_'+n):n for n in names}
for a in addresses:c.put(a,bytes.fromhex('4e75'))
plan=[];events=[];level=0;errors=[];arrivals=[];world_add=[];budgets=[]
@CODE
def event(handle,a,n,user):
 global level
 if a==ENTER:
  if level:errors.append('nested exclusion')
  level+=1;return
 if a==LEAVE:
  if level!=1:errors.append('unbalanced leave')
  level-=1;return
 name=addresses[a];events.append(name)
 if not plan:errors.append(('unexpected',name));c.rw(9,0xffffffff);return
 expected,result=plan.pop(0)
 if name!=expected:errors.append(('order',name,expected))
 critical=name in ('activate','boundary_suspend','modal_suspend','suspend')
 if level!=int(critical):errors.append(('exclusion',name,level))
 if c.rr(1)!=ARENA:errors.append(('arena',name))
 if name=='batch':
  expected_budget=budgets.pop(0) if budgets else 4
  if (c.rr(9),c.rr(10),c.rr(11))!=(64,expected_budget,128):errors.append(('budgets',c.rr(10),expected_budget))
  if world_add:
   address=ptr('SCHEDULER')+36
   c.put(address,struct.pack('>I',(int.from_bytes(c.get(address,4),'big')+world_add.pop(0))&0xffffffff))
 if name=='boundary_finish' and c.rr(9)!=128:errors.append('finish budget')
 if name=='batch' and arrivals:
  write,read=arrivals.pop(0);c.put(ptr('HISTORY'),struct.pack('>HH',write,read))
 c.rw(9,result&0xffffffff)
hooks=[]
for a in [ENTER,LEAVE,*addresses]:
 hh=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hh),1<<2,event,None,a,a));hooks.append(hh)
def trial(seq,result,pending=(),advances=(),limits=(),initial=0):
 global plan,events,level,errors,arrivals,world_add,budgets
 plan=list(seq);events=[];level=0;errors=[];arrivals=list(pending);world_add=list(advances);budgets=list(limits)
 c.put(ptr('SCHEDULER')+36,struct.pack('>I',initial))
 c.put(ptr('HISTORY'),bytes(4))
 c.put(ARENA,struct.pack('>I',1));c.put(ptr('DRAW_READY'),b'\0\1')
 call('timing_runtime_loop',{1:ARENA,2:ENTER,3:LEAVE},result&0xffffffff)
 assert not plan and not errors and level==0,(plan,errors,level)
trial([('activate',0),('batch',0),('draw',0),('batch',1),('batch',2),('boundary_suspend',0),('boundary_run',0),('boundary_finish',1),('boundary_finish',2),('boundary_suspend',0),('boundary_run',0),('boundary_finish',3),('modal_run',0),('activate',0),('batch',3),('modal_suspend',0),('modal_run',0),('activate',0),('batch',-2),('suspend',0),('activate',0),('batch',4),('suspend',0)],4)
trial([('activate',0),('batch',2),('boundary_suspend',0),('boundary_run',4),('boundary_finish',4),('suspend',0)],4)
trial([('activate',0),('batch',3),('modal_suspend',0),('modal_run',3),('suspend',0)],4)
trial([('activate',0),('batch',5),('draw',0),('batch',4),('suspend',0)],4)
trial([('activate',-3)],-3)
trial([('activate',0),('batch',-1),('suspend',0)],-1)
trial([('activate',0),('batch',0),('draw',-3),('suspend',0)],-3)
trial([('activate',0),('batch',2),('boundary_suspend',0),('boundary_run',-1),('suspend',0)],-1)
trial([('activate',0),('batch',2),('boundary_suspend',0),('boundary_run',0),('boundary_finish',-1),('suspend',0)],-1)
trial([('activate',0),('batch',3),('modal_suspend',0),('modal_run',-1),('suspend',0)],-1)
trial([('activate',0),('batch',-2),('suspend',0),('activate',-3),('suspend',0)],-3)
for pending in ([(1,0),(1,1)],[(0,65535),(0,0)]):
 trial([('activate',0),('batch',0),('batch',0),('draw',0),('batch',4),('suspend',0)],4,pending)
for initial in (0,0xfffffffe):
 trial([('activate',0)]+[('batch',0)]*4+[('draw',0),('batch',4),('suspend',0)],4,[(1,0)]*4,[1]*4,[4,3,2,1,4],initial)
for args in ({1:ARENA,2:0,3:LEAVE},{1:ARENA,2:ENTER,3:0}):
 before=c.get(ARENA,size);call('timing_runtime_loop',args,0xfffffffd);assert c.get(ARENA,size)==before
print(json.dumps(dict(status='passed',control_scenarios=15,bounded_worlds_between_draws=True,world_counter_wrap=True,producer_arrival_before_draw=True,cursor_wrap_covered=True,invalid_callbacks=2,balanced_exclusion=True,once_only_modal_continuation=True,child_statuses_injected=True)))
c.close()
