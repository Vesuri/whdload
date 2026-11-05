"""Retained-owner held-control player endpoint and private next-view candidate experiment."""
from unicorn_b import *
from capstone import *
import json,sys,os
cached=os.environ.get("FORECAST_CACHE")=="1"
only=os.environ.get('CANDIDATES_ONLY')=='1'
base=0x100000
listing=(root/'tmp/c/runtime.lst').read_text();sym=lambda n:int(re.search(r'^([0-9A-F]{8}) '+n+'$',listing,re.M)[1],16)
live=(build/'selector-combat.slave.lst').read_text(encoding='latin1');ls=lambda n:int(re.search(r'^([0-9A-F]{8}) '+n+'$',live,re.M)[1],16)
folder=Path(sys.argv[1]);reports=[]
for world in range(20,47):
 d=folder/f'world-{world}';n=folder/f'world-{world+1}';a=(d/'arena.bin').read_bytes();h=struct.unpack_from('>9I',a,ls('RT_HUNKS'))
 c=CPU();c.put(0x200000,(folder/'fast.bin').read_bytes());c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/runtime.hunk')).get_segments()[0].get_data()))
 for i in (0,2,4,5,6):c.put(h[i],(d/f'h{i}.bin').read_bytes())
 # Restore only the three presentation heading loads in the offline source.
 for off,opcode in ((0x5d20,0x1239),(0x68a2,0x1439),(0x68d2,0x1439)):
  c.put(h[0]+off,struct.pack('>HI',opcode,h[6]+0x3ce3))
 for off in (0x6356,0x63d4):c.put(h[0]+off,struct.pack('>HI',0x4eb9,h[0]+0xa450))
 scene=0x300000;target=0x320000;collector=0x321000;stages=0x322000;state=0x324000;player=0x325000;packet=0x326000;camera=0x327000;ground=0x328000;event=0x329000;cache=0x32a000
 instructions=[0];costs={};reading=[False];shared_reads=set()
 CODE=C.CFUNCTYPE(None,C.c_void_p,C.c_uint64,C.c_uint32,C.c_void_p)
 u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
 @CODE
 def record(handle,addr,n,user):instructions[0]+=1
 hk=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hk),1<<2,record,None,1,0))
 def call(name,regs):
  if only and name=='scene_target_step':name='scene_target_candidates_step'
  if cached and name=='endpoint_player_step':name='endpoint_player_step_cached';regs=dict(regs,**{}) ;regs[6]=cache
  for r,v in regs.items():c.rw(r,v)
  reading[0]=name=='scene_target_candidates_step'
  start=instructions[0]
  c.rw(8,0x8f000);c.call(base+sym(name));assert c.rr(18)==0x90000,(name,hex(c.rr(18)))
  reading[0]=False
  costs[name]=costs.get(name,0)+instructions[0]-start
  assert c.rr(9) in (0,1),(name,c.rr(9))
 call('target_select_prepare',{1:h[0],2:h[6],3:target})
 call('scene_target_prepare',{1:h[0],2:h[4],3:h[6],4:scene,5:target,6:collector})
 call('motion_stages_prepare',{1:h[0],2:stages})
 call('ground_deferred_prepare',{1:h[0],2:ground,3:h[6],4:event})
 writes=[];bad_writes=[]
 MEM=C.CFUNCTYPE(None,C.c_void_p,C.c_int,C.c_uint64,C.c_int,C.c_int64,C.c_void_p)
 allowed=[(scene,scene+(sym('SCT_SELECTION')+168)),(target,target+sym('WT_SIZE')),(state,state+sym('EP_SIZE')),(player,player+86),(camera,camera+12),(event,event+4),(cache,cache+sym('PC_SIZE')),(0x8e000,0x8f004)]
 @MEM
 def written(handle,kind,addr,n,value,user):
  if not any(lo<=addr and addr+n<=hi for lo,hi in allowed):bad_writes.append((hex(addr),n))
 mh=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(mh),1<<11,written,None,1,0))
 @MEM
 def read(handle,kind,addr,n,value,user):
  if reading[0] and not(0x300000<=addr and addr+n<=0x32b000 or 0x8e000<=addr and addr+n<=0x8f004):shared_reads.update(range(addr,addr+n))
 rh=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(rh),1<<10,read,None,1,0))
 current=c.get(h[6]+0x3b88,86);c.put(player,current)
 owner=a[ls('RT_ENDPOINT'):ls('RT_ENDPOINT')+sym('EP_SIZE')];c.put(state,owner)
 held=a[ls('RT_PACKET'):ls('RT_PACKET')+4];c.put(packet,held+bytes(6))
 phase=int.from_bytes(a[ls('RT_CLOCK')+20:ls('RT_CLOCK')+22],'big');rate=int.from_bytes(a[ls('RT_CLOCK')+22:ls('RT_CLOCK')+24],'big')
 span=(rate-phase+2)//3
 last=int.from_bytes(owner[sym('EP_DELAY')+sym('CD_FIELD'):sym('EP_DELAY')+sym('CD_FIELD')+4],'big')
 assert int.from_bytes(owner[sym('EP_DONE'):sym('EP_DONE')+2],'big')==int.from_bytes(owner[sym('EP_SPAN'):sym('EP_SPAN')+2],'big')
 call('endpoint_player_begin',{1:state,2:player,9:span,10:world+1})
 for field in range(1,span+1):call('endpoint_player_step',{1:state,2:player,3:stages,4:h[0]+0x7a44,5:packet,9:last+field})
 c.put(event,bytes(4));call('endpoint_ground_resolve',{1:state,2:player,3:stages,4:ground,5:event})
 forecast=c.get(player,86)
 next_arena=(n/'arena.bin').read_bytes()
 c.put(state,owner);c.put(player,current);c.put(cache,bytes(sym('PC_SIZE')))
 call('endpoint_player_begin',{1:state,2:player,9:span,10:world+1})
 for field in range(1,span+1):
  c.put(packet,held+(next_arena[ls('RT_PACKET')+4:ls('RT_PACKET')+10] if field==span else bytes(6)))
  call('endpoint_player_step',{1:state,2:player,3:stages,4:h[0]+0x7a44,5:packet,9:last+field})
 c.put(event,bytes(4));call('endpoint_ground_resolve',{1:state,2:player,3:stages,4:ground,5:event})
 impulse_oracle=c.get(player,86)
 expected=(n/'h6.bin').read_bytes()[0x3b88:0x3bde]
 target_input=(n/'before-target-arena.bin').read_bytes();want=target_input[ls('RT_TARGET')+sym('WT_STATE'):ls('RT_TARGET')+sym('WT_STATE')+168]
 original={i:c.get(h[i],len((d/f'h{i}.bin').read_bytes())) for i in (0,2,4,5,6)}
 rows=[]
 for variant,pose in [('current',current),('forecast',forecast),('next_impulse_oracle',impulse_oracle),('next_player_oracle',expected)]:
  c.put(player,pose);call('native_camera_build',{1:player,3:camera})
  c.put(target+sym('WT_STATE'),original[0][0xa99e:0xaa46])
  call('scene_target_step',{1:scene,2:camera,3:h[0]+0xc6a0})
  result=c.get(target+sym('WT_STATE'),168)
  if only:
   c.put(target+sym('WT_STATE'),original[0][0xa99e:0xaa46])
   for reg,value in {1:scene,2:camera,3:h[0]+0xc6a0}.items():c.rw(reg,value)
   c.rw(8,0x8f000);c.call(base+sym('scene_target_step'));assert c.rr(18)==0x90000
   assert c.get(target+sym('WT_STATE'),168)==result,(world,variant)
  count=int.from_bytes(result[2:4],'big');wc=int.from_bytes(want[2:4],'big')
  rows.append(dict(variant=variant,camera=c.get(camera,12).hex(),count=count,identities=result[108:108+2*count].hex(),expected_count=wc,expected_identities=want[108:108+2*wc].hex(),candidate_identity_match=count==wc and result[108:108+2*count]==want[108:108+2*wc]))
  assert all(c.get(h[i],len(v))==v for i,v in original.items())
  assert not bad_writes,bad_writes[:10]
 assert rows[2]['camera']==rows[3]['camera'],(world,rows)
 ranges=[]
 for address in sorted(shared_reads):
  if ranges and ranges[-1][1]==address:ranges[-1][1]+=1
  else:ranges.append([address,address+1])
 mapped=[]
 for start,end in ranges:
  label='external';offset=start
  for i in (0,2,4,5,6):
   if h[i]<=start and end<=h[i]+len((d/f'h{i}.bin').read_bytes()):label=f'h{i}';offset=start-h[i];break
  mapped.append(dict(source=label,offset=hex(offset),length=end-start))
 reports.append(dict(shared_read_bytes=len(shared_reads),shared_read_ranges=mapped,instructions=costs,forecast_player=forecast.hex(),impulse_oracle_player=impulse_oracle.hex(),world=world,span=span,held_packet=held.hex(),next_impulses=next_arena[ls('RT_PACKET')+4:ls('RT_PACKET')+10].hex(),player_differences=[dict(offset=hex(i),predicted=x,native=y) for i,(x,y) in enumerate(zip(forecast,expected)) if x!=y],variants=rows,native_memory_unchanged=True));c.close()
totals={}
for row in reports:
 for name,count in row['instructions'].items():totals[name]=totals.get(name,0)+count
report=dict(candidates_only=only,cached=cached,worlds=len(reports),instruction_totals=totals,reports=reports)
(root/('tmp/c/homing-forecast-reads-'+('candidates-only' if only else 'cached' if cached else 'uncached')+'.json')).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='reports'},indent=2))
