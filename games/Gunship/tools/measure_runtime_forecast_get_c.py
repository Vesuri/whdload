"""Retained-owner held-control player endpoint and private next-view candidate experiment."""
from unicorn_b import *
from capstone import *
import json,sys,os
from functools import lru_cache
base=0x100000
listing=(root/'tmp/c/runtime.lst').read_text();sym=lambda n:int(re.search(r'^([0-9A-F]{8}) '+n+'$',listing,re.M)[1],16)
sym=lru_cache(None)(sym)
live=(build/'selector-combat.slave.lst').read_text(encoding='latin1');ls=lambda n:int(re.search(r'^([0-9A-F]{8}) '+n+'$',live,re.M)[1],16)
folder=Path(sys.argv[1]);reports=[];previous=None;hits=0;rebuilt=0
for frame in json.loads((folder/'frames.json').read_text()):
 world=frame['world']
 d=folder/f"frame-{frame['frame']:03d}";a=(d/'arena.bin').read_bytes();h=struct.unpack_from('>9I',a,ls('RT_HUNKS'))
 c=CPU();c.put(0x200000,(folder/'fast.bin').read_bytes());c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/runtime.hunk')).get_segments()[0].get_data()))
 for i in (0,2,4,5,6):c.put(h[i],(d/f'h{i}.bin').read_bytes())
 # Restore only the three presentation heading loads in the offline source.
 for off,opcode in ((0x5d20,0x1239),(0x68a2,0x1439),(0x68d2,0x1439)):
  c.put(h[0]+off,struct.pack('>HI',opcode,h[6]+0x3ce3))
 for off in (0x6356,0x63d4):c.put(h[0]+off,struct.pack('>HI',0x4eb9,h[0]+0xa450))
 pointer=json.loads((d/'object-records-address.json').read_text())['pointer'];c.put(pointer,(d/'object-records.bin').read_bytes())
 scene=0x300000;target=0x320000;collector=0x321000;stages=0x322000;state=0x324000;player=0x325000;packet=0x326000;camera=0x327000;ground=0x328000;event=0x329000
 arena=0x400000;rf=arena+sym('RT_FORECAST')
 for n in ('RT_ENDPOINT','RT_CLOCK','RT_PACKET','RT_HUNKS','RT_SCHEDULER','RT_CAPTURE_OWNER','RT_READY'):
  assert sym(n)==ls(n),(n,sym(n),ls(n))
 c.put(arena,a)
 trace=[];instructions=[0]
 CODE=C.CFUNCTYPE(None,C.c_void_p,C.c_uint64,C.c_uint32,C.c_void_p)
 u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
 @CODE
 def record(handle,addr,n,user):
  instructions[0]+=1
  trace.append(addr)
  if len(trace)>30:del trace[0]
 hk=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hk),1<<2,record,None,base,base+0x20000))
 def call(name,regs):
  for r,v in regs.items():c.rw(r,v)
  c.rw(8,0x8f000);c.call(base+sym(name));assert c.rr(18)==0x90000,(name,hex(c.rr(18)))
  if c.rr(9) not in (0,1):
   md=Cs(CS_ARCH_M68K,CS_MODE_BIG_ENDIAN|CS_MODE_M68K_000)
   print([(hex(v-base),next(md.disasm(c.get(v,12),v)).mnemonic,next(md.disasm(c.get(v,12),v)).op_str) for v in trace])
  assert c.rr(9) in (0,1),(name,c.rr(9))
 call('timing_runtime_forecast_prepare',{1:arena})
 if previous is not None:c.put(rf,previous)
 call('target_select_prepare',{1:h[0],2:h[6],3:target})
 call('scene_target_player_prepare',{1:h[0],2:h[4],3:h[6],4:scene,5:target,6:collector,7:player})
 call('motion_stages_prepare',{1:h[0],2:stages})
 call('ground_deferred_prepare',{1:h[0],2:ground,3:h[6],4:event})
 writes=[];bad_writes=[]
 MEM=C.CFUNCTYPE(None,C.c_void_p,C.c_int,C.c_uint64,C.c_int,C.c_int64,C.c_void_p)
 allowed=[(rf,arena+sym("RT_ARENA_SIZE")),(scene,scene+(sym('SCT_SELECTION')+168)),(target,target+sym('WT_SIZE')),(state,state+sym('EP_SIZE')),(player,player+86),(camera,camera+12),(event,event+4),(0x8e000,0x8f004)]
 @MEM
 def written(handle,kind,addr,n,value,user):
  if not any(lo<=addr and addr+n<=hi for lo,hi in allowed):bad_writes.append((hex(addr),n))
 mh=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(mh),1<<11,written,None,1,0))
 current=c.get(h[6]+0x3b88,86);c.put(player,current)
 owner=a[ls('RT_ENDPOINT'):ls('RT_ENDPOINT')+sym('EP_SIZE')];c.put(state,owner)
 held=a[ls('RT_PACKET'):ls('RT_PACKET')+4];c.put(packet,held+bytes(6))
 phase=int.from_bytes(a[ls('RT_CLOCK')+20:ls('RT_CLOCK')+22],'big');rate=int.from_bytes(a[ls('RT_CLOCK')+22:ls('RT_CLOCK')+24],'big')
 span=(rate-phase+2)//3
 last=int.from_bytes(owner[sym('EP_DELAY')+sym('CD_FIELD'):sym('EP_DELAY')+sym('CD_FIELD')+4],'big')
 done=int.from_bytes(owner[sym('EP_DONE'):sym('EP_DONE')+2],'big')
 existing_span=int.from_bytes(owner[sym('EP_SPAN'):sym('EP_SPAN')+2],'big')
 if done==existing_span:
  call('endpoint_player_begin',{1:state,2:player,9:span,10:world+1});done=0
 else:
  span=existing_span
  assert int.from_bytes(owner[sym('EP_TICK'):sym('EP_TICK')+2],'big')==world+1
 checkpoints=[]
 for field in range(1,span-done+1):
  call('endpoint_player_step',{1:state,2:player,3:stages,4:h[0]+0x7a44,5:packet,9:last+field})
  checkpoints.append(dict(field=last+field,owner=c.get(state,sym('EP_SIZE')).hex(),player=c.get(player,86).hex()))
 c.put(event,bytes(4));call('endpoint_ground_resolve',{1:state,2:player,3:stages,4:ground,5:event})
 forecast=c.get(player,86)
 native_before={i:c.get(h[i],len((d/f'h{i}.bin').read_bytes())) for i in (0,2,4,5,6)}
 authoritative=c.get(arena,sym('RT_FORECAST'))
 for r,v in {1:arena}.items():c.rw(r,v)
 regs={r:c.rr(r) for r in range(1,17) if r not in (8,9)}
 start=instructions[0]
 c.rw(8,0x8f000);c.call(base+sym('timing_runtime_forecast_get'))
 cost=instructions[0]-start
 status=c.rr(9)
 assert status in (0,1),(frame,status)
 assert all(c.rr(r)==v for r,v in regs.items())
 hits+=status==0;rebuilt+=status==1
 assert c.get(rf+sym('RF_PLAYER'),86)==forecast,frame
 assert c.get(arena,sym('RT_FORECAST'))==authoritative
 assert all(c.get(h[i],len(v))==v for i,v in native_before.items())
 previous=c.get(rf,sym('RT_ARENA_SIZE')-sym('RT_FORECAST'))
 native={i:c.get(h[i],len((d/f'h{i}.bin').read_bytes())) for i in (0,2,4,5,6)}
 call('native_camera_build',{1:player,3:camera})
 c.put(target+sym('WT_STATE'),native[0][0xa99e:0xaa46])
 call('scene_target_candidates_step',{1:scene,2:camera,3:h[0]+0xc6a0})
 result=c.get(target+sym('WT_STATE'),168);count=int.from_bytes(result[2:4],'big')
 assert all(c.get(h[i],len(v))==v for i,v in native.items()) and not bad_writes,bad_writes
 reports.append(dict(forecast_instructions=cost,forecast_status=status,source_field=last,source_owner=owner.hex(),source_player=current.hex(),checkpoints=checkpoints,frame=frame['frame'],world=world,completed=done,span=span,held=held.hex(),forecast_player=forecast.hex(),camera=c.get(camera,12).hex(),candidate_state=result.hex(),count=count,identities=result[108:108+count*2].hex()))
 c.close()
pairs=[]
for a,b in zip(reports,reports[1:]):
 if a['world']!=b['world']:continue
 checkpoint=next(x for x in a['checkpoints'] if x['field']==b['source_field'])
 pairs.append(dict(checkpoint_owner_equal=checkpoint['owner']==b['source_owner'],checkpoint_player_equal=checkpoint['player']==b['source_player'],world=a['world'],before=a['frame'],after=b['frame'],camera_equal=a['camera']==b['camera'],candidates_equal=a['candidate_state']==b['candidate_state'],player_equal=a['forecast_player']==b['forecast_player'],held_equal=a['held']==b['held']))
report=dict(run=folder.name,frames=len(reports),pairs=pairs,reports=reports)
(folder/('runtime-forecast-cost-'+os.environ.get('COST_LABEL','current')+'.json')).write_text(json.dumps(report,indent=2)+'\n')
print(dict(run=folder.name,frames=len(reports),pairs=len(pairs),camera_mismatches=[p for p in pairs if not p['camera_equal']],candidate_mismatches=[p for p in pairs if not p['candidates_equal']],player_mismatch_pairs=sum(not p['player_equal'] for p in pairs),checkpoint_owner_mismatches=sum(not p['checkpoint_owner_equal'] for p in pairs),checkpoint_player_mismatches=sum(not p['checkpoint_player_equal'] for p in pairs)))

assert hits==len(pairs),(hits,len(pairs))
print(dict(hits=hits,rebuilt=rebuilt))

print(dict(total_instructions=sum(x["forecast_instructions"] for x in reports),build_instructions=sum(x["forecast_instructions"] for x in reports if x["forecast_status"]==1)))
