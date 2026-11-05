"""Real field/world pipeline under loop ownership versus explicit dispatch."""
__file__=__file__.replace('test_runtime_loop_c.py','test_runtime_batch_c.py')
exec(open(__file__).read().split('runs=[];yields=0')[0])
_setup_without_ui_stub=setup
def setup(rate):
 _setup_without_ui_stub(rate);c.put(h[0]+0x46de,bytes.fromhex("4e75"))
ENTER=0x750000;LEAVE=0x750010;c.put(ENTER,bytes.fromhex('4e75'));c.put(LEAVE,bytes.fromhex('4e75'))
level=0;errors=[];draws=0;generated=0;chunk=1;exits=0
@CODE
def exclude(handle,a,n,user):
 global level
 if a==ENTER:
  if level:errors.append('nested')
  level+=1
 else:
  if level!=1:errors.append('unbalanced')
  level-=1
@CODE
def drawing(handle,a,n,user):
 global draws,generated
 if level:errors.append('draw excluded')
 draws+=1
 hist=ptr('HISTORY');cmd=ptr('COMMANDS');seq=long(cmd+sym('CQ_LAST'))
 count=chunk if generated<120 else 1
 for i in range(count):
  field=long(hist+sym('TH_LAST'))+1
  if generated>=120 or (generated==29 and chunk<80):
   key=0x833 if generated>=120 else 0x40
   seq+=1;idx=word(cmd);c.put(cmd+sym('CQ_RECORDS')+(idx%128)*8,struct.pack('>IHH',seq,key,0));c.put(cmd+sym('CQ_LAST'),struct.pack('>I',seq));c.put(cmd,struct.pack('>H',(idx+1)&65535))
  idx=word(hist);record=struct.pack('>6IHhhHII',field,0,0,0,0,seq,8,0,0,0,10,generated)
  c.put(hist+sym('TH_RECORDS')+(idx%128)*40,record);c.put(hist+sym('TH_LAST'),struct.pack('>I',field));c.put(hist,struct.pack('>H',(idx+1)&65535))
  c.put(h[2]+0x1c,struct.pack('>I',field));c.put(ptr('CAPTURE')+24,struct.pack('>I',seq));generated+=1
@CODE
def ui(handle,a,n,user):
 global exits
 if level:errors.append('native UI excluded')
 exits+=1
hooks=[]
for addr,cb in [(ENTER,exclude),(LEAVE,exclude),(h[0]+0x5c04,drawing),(base+sym('timing_runtime_boundary_run'),ui)]:
 hh=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hh),1<<2,cb,None,addr,addr));hooks.append(hh)
def critical(name):
 global level
 assert level==0;level=1;call(name,{1:ARENA});level=0
runs=[]
for rate in (50,60):
 for chunk in (1,3,10,80):
  results=[]
  for mode in ('reference','loop'):
   setup(rate);call('timing_runtime_suspend',{1:ARENA})
   c.put(h[6]+0x1f0,bytes(4));c.put(h[6]+0x4c68,bytes(26));c.put(h[0]+0x5c04,bytes.fromhex('4e75'));c.put(ptr('DRAW_READY'),b'\0\1')
   level=0;errors=[];draws=0;generated=0;exits=0
   if mode=='loop':call('timing_runtime_loop',{1:ARENA,2:ENTER,3:LEAVE},4)
   else:
    critical('timing_runtime_activate')
    while True:
     result=pump(64,4,128)
     if result in (0,5):call('timing_runtime_draw',{1:ARENA})
     elif result==0xfffffffe:
      critical('timing_runtime_suspend');critical('timing_runtime_activate')
     elif result==2:
      critical('timing_runtime_boundary_suspend')
      end=word(ptr('BOUNDARY_RECORD')+4)==0x833
      call('timing_runtime_boundary_run',{1:ARENA},4 if end else 0)
      call('timing_runtime_boundary_finish',{1:ARENA,9:128},4 if end else 0)
      if end:critical('timing_runtime_suspend');critical('timing_runtime_retire');break
      critical('timing_runtime_activate')
     else:raise AssertionError((rate,chunk,result))
   assert not errors and level==0 and exits==(1 if chunk==80 else 2) and not word(ptr('CAPTURE_OWNER')),(errors,level,exits)
   assert c.get(ptr('ENDPOINT'),sym('EP_SIZE'))==bytes(sym('EP_SIZE'))
   for block,off in [('PLAYER_CACHE',sym('PC_VALID')),('ACTOR_PRESENT',sym('AC_VALID')),('RELEASE_PRESENT',sym('AC_VALID')),('SCRIPT_PRESENT',sym('SPC_VALID'))]:assert word(ptr(block)+off)==0
   result=(c.get(p,86),c.get(h[0]+0xc6a0,0xc2),c.get(ptr('CLOCK'),28),c.get(ptr('SCHEDULER'),48),long(ptr('HISTORY')+sym('TH_DISCARDED')),draws,generated)
   results.append(result)
  assert results[0]==results[1],(rate,chunk)
  assert bool(results[1][4])==(chunk==80),(rate,chunk,results[1][4])
  runs.append(dict(rate=rate,batch=chunk,draws=draws,generated=generated,discarded=results[1][4]))
print(json.dumps(dict(status='passed',runs=runs,native_exit_once=True,balanced_exclusion=True,native_draw_stubbed=True)))
c.close()
