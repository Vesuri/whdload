"""Retained-owner held-control player endpoint and private next-view candidate experiment."""
from unicorn_b import *
from capstone import *
import json,sys
from functools import lru_cache
base=0x100000
listing=(root/'tmp/c/runtime.lst').read_text();sym=lambda n:int(re.search(r'^([0-9A-F]{8}) '+n+'$',listing,re.M)[1],16)
sym=lru_cache(None)(sym)
live=(build/'selector-combat.slave.lst').read_text(encoding='latin1');ls=lambda n:int(re.search(r'^([0-9A-F]{8}) '+n+'$',live,re.M)[1],16)
folder=Path(sys.argv[1]);reports=[];dependency_reports=[]
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
 trace=[];reading=[False];shared_reads=set()
 CODE=C.CFUNCTYPE(None,C.c_void_p,C.c_uint64,C.c_uint32,C.c_void_p)
 u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
 @CODE
 def record(handle,addr,n,user):
  trace.append(addr)
  if len(trace)>30:del trace[0]
 hk=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hk),1<<2,record,None,base,base+0x20000))
 def call(name,regs):
  for r,v in regs.items():c.rw(r,v)
  reading[0]=name=='forecast_player_build'
  before={r:c.rr(r) for r in range(1,17) if r not in (8,9)}
  c.rw(8,0x8f000);c.call(base+sym(name));
  reading[0]=False
  if name=='forecast_player_build':assert all(c.rr(r)==v for r,v in before.items()),'ABI'
  assert c.rr(18)==0x90000,(name,hex(c.rr(18)))
  if c.rr(9) not in (0,1):
   md=Cs(CS_ARCH_M68K,CS_MODE_BIG_ENDIAN|CS_MODE_M68K_000)
   print([(hex(v-base),next(md.disasm(c.get(v,12),v)).mnemonic,next(md.disasm(c.get(v,12),v)).op_str) for v in trace])
  assert c.rr(9) in (0,1),(name,c.rr(9))
 call('target_select_prepare',{1:h[0],2:h[6],3:target})
 call('scene_target_player_prepare',{1:h[0],2:h[4],3:h[6],4:scene,5:target,6:collector,7:player})
 call('motion_stages_prepare',{1:h[0],2:stages})
 call('ground_deferred_prepare',{1:h[0],2:ground,3:h[6],4:event})
 tape=0x330000;work=0x332000;context=0x333000
 writes=[];bad_writes=[]
 MEM=C.CFUNCTYPE(None,C.c_void_p,C.c_int,C.c_uint64,C.c_int,C.c_int64,C.c_void_p)
 allowed=[(tape,tape+(sym("FCT_RECORDS")+20*254)),(work,work+sym("FB_SIZE")),(scene,scene+(sym('SCT_SELECTION')+168)),(target,target+sym('WT_SIZE')),(state,state+sym('EP_SIZE')),(player,player+86),(camera,camera+12),(event,event+4),(0x8e000,0x8f004)]
 @MEM
 def written(handle,kind,addr,n,value,user):
  if not any(lo<=addr and addr+n<=hi for lo,hi in allowed):bad_writes.append((hex(addr),n))
 mh=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(mh),1<<11,written,None,1,0))
 @MEM
 def read(handle,kind,addr,n,value,user):
  if reading[0] and not (base<=addr and addr+n<=base+0x20000 or 0x300000<=addr and addr+n<=0x334000 or 0x8d000<=addr and addr+n<=0x8f004):shared_reads.update(range(addr,addr+n))
 rh=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(rh),1<<10,read,None,1,0))
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
 c.put(context,struct.pack('>6I',1,world,stages,h[0]+0x7a44,ground,0))
 source=(c.get(state,sym('EP_SIZE')),c.get(player,86),c.get(packet,10),c.get(context,24))
 c.put(event,bytes(4))
 call('forecast_player_build',{1:tape,2:state,3:player,4:packet,5:context,6:work,9:event})
 assert source==(c.get(state,sym('EP_SIZE')),c.get(player,86),c.get(packet,10),c.get(context,24))
 built=c.get(tape+sym('FCT_RESULT'),86)
 assert c.get(tape,4)==struct.pack('>HH',1,span-done)
 c.put(event,bytes(4))
 checkpoints=[]
 for field in range(1,span-done+1):
  call('endpoint_player_step',{1:state,2:player,3:stages,4:h[0]+0x7a44,5:packet,9:last+field})
  checkpoints.append(dict(field=last+field,owner=c.get(state,sym('EP_SIZE')).hex(),player=c.get(player,86).hex()))
 c.put(event,bytes(4));call('endpoint_ground_resolve',{1:state,2:player,3:stages,4:ground,5:event})
 forecast=c.get(player,86)
 assert built==forecast,(world,frame)
 native={i:c.get(h[i],len((d/f'h{i}.bin').read_bytes())) for i in (0,2,4,5,6)}
 call('native_camera_build',{1:player,3:camera})
 c.put(target+sym('WT_STATE'),native[0][0xa99e:0xaa46])
 call('scene_target_candidates_step',{1:scene,2:camera,3:h[0]+0xc6a0})
 result=c.get(target+sym('WT_STATE'),168);count=int.from_bytes(result[2:4],'big')
 assert all(c.get(h[i],len(v))==v for i,v in native.items()) and not bad_writes,bad_writes
 reports.append(dict(source_field=last,source_owner=owner.hex(),source_player=current.hex(),checkpoints=checkpoints,frame=frame['frame'],world=world,completed=done,span=span,held=held.hex(),forecast_player=forecast.hex(),camera=c.get(camera,12).hex(),candidate_state=result.hex(),count=count,identities=result[108:108+count*2].hex()))
 # Every tape checkpoint must equal the independent per-field replay.
 expected=[(source[0],source[1])]+[(bytes.fromhex(x['owner']),bytes.fromhex(x['player'])) for x in checkpoints[:-1]]
 for j,(o,p) in enumerate(expected):
  assert c.get(tape+sym('FCT_RECORDS')+j*254,254)==o+p+held
 # Reject both admission errors and a failure after initial append.
 for case in ('epoch','policy','event','complete','packet'):
  c.put(state,source[0]);c.put(player,source[1]);c.put(packet,source[2]);c.put(context,source[3]);c.put(event,bytes(4))
  if case=='epoch':c.put(context,bytes(4))
  if case=='policy':c.put(context+20,struct.pack('>I',1))
  if case=='event':c.put(event,struct.pack('>I',1))
  if case=='complete':c.put(state+sym('EP_DONE'),c.get(state+sym('EP_SPAN'),2))
  if case=='packet':c.put(packet,struct.pack('>h',3))
  inputs=(c.get(state,sym('EP_SIZE')),c.get(player,86),c.get(packet,10),c.get(context,24))
  for r,v in {1:tape,2:state,3:player,4:packet,5:context,6:work,9:event}.items():c.rw(r,v)
  before={r:c.rr(r) for r in range(1,17) if r not in (8,9)}
  c.rw(8,0x8f000);c.call(base+sym('forecast_player_build'))
  assert c.rr(9)==0xfffffffd and c.get(tape,4)==bytes(4),(case,c.rr(9))
  assert all(c.rr(r)==v for r,v in before.items())
  assert inputs==(c.get(state,sym('EP_SIZE')),c.get(player,86),c.get(packet,10),c.get(context,24))
 assert not bad_writes,bad_writes
 ranges=[]
 for address in sorted(shared_reads):
  if ranges and ranges[-1][1]==address:ranges[-1][1]+=1
  else:ranges.append([address,address+1])
 normalized=[]
 for lo,hi in ranges:
  owner=next((i for i in (0,2,4,5,6) if h[i]<=lo and hi<=h[i]+len((d/f'h{i}.bin').read_bytes())),None)
  normalized.append(dict(hunk=owner,start=hex(lo-h[owner] if owner is not None else lo),end=hex(hi-h[owner] if owner is not None else hi),bytes=hi-lo))
 dependency_reports.append(dict(frame=frame['frame'],world=world,reads=normalized))
 c.close()
pairs=[]
for a,b in zip(reports,reports[1:]):
 if a['world']!=b['world']:continue
 checkpoint=next(x for x in a['checkpoints'] if x['field']==b['source_field'])
 pairs.append(dict(checkpoint_owner_equal=checkpoint['owner']==b['source_owner'],checkpoint_player_equal=checkpoint['player']==b['source_player'],world=a['world'],before=a['frame'],after=b['frame'],camera_equal=a['camera']==b['camera'],candidates_equal=a['candidate_state']==b['candidate_state'],player_equal=a['forecast_player']==b['forecast_player'],held_equal=a['held']==b['held']))
report=dict(run=folder.name,frames=len(reports),pairs=pairs,reports=reports)
(folder/'forecast-builder-dependencies.json').write_text(json.dumps(report,indent=2)+'\n')
print(dict(run=folder.name,frames=len(reports),pairs=len(pairs),camera_mismatches=[p for p in pairs if not p['camera_equal']],candidate_mismatches=[p for p in pairs if not p['candidates_equal']],player_mismatch_pairs=sum(not p['player_equal'] for p in pairs),checkpoint_owner_mismatches=sum(not p['checkpoint_owner_equal'] for p in pairs),checkpoint_player_mismatches=sum(not p['checkpoint_player_equal'] for p in pairs)))

(folder/'forecast-builder-dependencies.json').write_text(json.dumps(dependency_reports,indent=2)+'\n')
print(dependency_reports[0])
