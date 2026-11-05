"""Field consumer invokes visibility once before weapons, never on redraw/fields."""
from pathlib import Path
__file__=str(Path(__file__).with_name('test_runtime_batch_c.py'));source=Path(__file__).read_text();exec(source.split('runs=[]')[0])
stub=0x760000;c.put(stub,bytes.fromhex('70004e75'));seen=[];world=[]
@CODE
def target_call(handle,a,n,user):
 assert c.rr(1)==ARENA and word(ptr('CONSUMER')+sym('TF_PHASE'))==3
 assert word(ptr('SCHEDULER')+sym('TS_DUE'))==1
 assert word(ptr('SCHEDULER')+sym('TS_STATE'))==2
 assert word(ptr('PLAYER')+sym('SE_COMMITTED'))==1
 seen.append(long(ptr('SCHEDULER')+sym('TS_FIELD')))
@CODE
def weapons_call(handle,a,n,user):
 field=long(ptr('SCHEDULER')+sym('TS_FIELD'));assert seen and seen[-1]==field
 world.append(field)
for fn,entry in [(target_call,stub),(weapons_call,base+sym('world_weapons_step'))]:
 hook=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hook),1<<2,fn,None,entry,entry))
for rate in (50,60):
 for batch in (1,10,25):
  setup(rate);c.put(ptr('CONSUMER')+sym('TF_TARGET_ENTRY'),struct.pack('>II',stub,ARENA));seen.clear();world.clear()
  for start in range(1,101,batch):
   for n in range(start,min(start+batch,101)):publish(n)
   result=pump(commands=1)
   while result==1:result=pump(commands=1)
   assert result==0
  expected=[1000+n for n in range(1,101) if n*3//rate!=(n-1)*3//rate]
  assert seen==world==expected,(rate,batch,seen,world)
print(json.dumps(dict(status='passed',fields=600,configurations=6,ordering='committed player -> visibility -> weapons')));c.close()
