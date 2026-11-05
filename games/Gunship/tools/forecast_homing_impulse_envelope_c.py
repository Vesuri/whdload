"""Retained-owner held-control player endpoint and private next-view candidate experiment."""
from unicorn_b import *
from capstone import *
import json,sys
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
 scene=0x300000;target=0x320000;collector=0x321000;stages=0x322000;state=0x324000;player=0x325000;packet=0x326000;camera=0x327000;ground=0x328000;event=0x329000
 trace=[]
 CODE=C.CFUNCTYPE(None,C.c_void_p,C.c_uint64,C.c_uint32,C.c_void_p)
 u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
 @CODE
 def record(handle,addr,n,user):
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
 call('target_select_prepare',{1:h[0],2:h[6],3:target})
 call('scene_target_prepare',{1:h[0],2:h[4],3:h[6],4:scene,5:target,6:collector})
 call('motion_stages_prepare',{1:h[0],2:stages})
 call('ground_deferred_prepare',{1:h[0],2:ground,3:h[6],4:event})
 writes=[];bad_writes=[]
 MEM=C.CFUNCTYPE(None,C.c_void_p,C.c_int,C.c_uint64,C.c_int,C.c_int64,C.c_void_p)
 allowed=[(scene,scene+(sym('SCT_SELECTION')+168)),(target,target+sym('WT_SIZE')),(state,state+sym('EP_SIZE')),(player,player+86),(camera,camera+12),(event,event+4),(0x8e000,0x8f004)]
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
 assert int.from_bytes(owner[sym('EP_DONE'):sym('EP_DONE')+2],'big')==int.from_bytes(owner[sym('EP_SPAN'):sym('EP_SPAN')+2],'big')
 call('endpoint_player_begin',{1:state,2:player,9:span,10:world+1})
 for field in range(1,span):call('endpoint_player_step',{1:state,2:player,3:stages,4:h[0]+0x7a44,5:packet,9:last+field})
 prefix_owner=c.get(state,sym('EP_SIZE'));prefix_player=c.get(player,86)
 original={i:c.get(h[i],len((d/f'h{i}.bin').read_bytes())) for i in (0,2,4,5,6)}
 target_input=(n/'before-target-arena.bin').read_bytes();want=target_input[ls('RT_TARGET')+sym('WT_STATE'):ls('RT_TARGET')+sym('WT_STATE')+168]
 rows=[]
 height=int.from_bytes(prefix_player[28:30],'big');speed=int.from_bytes(prefix_player[42:44],'big');damage=int.from_bytes(prefix_player[14:16],'big')
 roll_options=(-4,0,4) if prefix_player[15]&1 else (0,)
 pitch_options=(-1,0,1) if prefix_player[28]==0 and speed>=8 and prefix_player[29]<prefix_player[43] else (0,)
 heading_options=(-2,-1,0,1,2) if height and damage&3 else (0,)
 for roll in roll_options:
  for pitch in pitch_options:
   for heading in heading_options:
    c.put(state,prefix_owner);c.put(player,prefix_player);c.put(packet,held+struct.pack('>hhh',roll,pitch,heading))
    call('endpoint_player_step',{1:state,2:player,3:stages,4:h[0]+0x7a44,5:packet,9:last+span})
    c.put(event,bytes(4));call('endpoint_ground_resolve',{1:state,2:player,3:stages,4:ground,5:event})
    call('native_camera_build',{1:player,3:camera})
    c.put(target+sym('WT_STATE'),original[0][0xa99e:0xaa46])
    call('scene_target_step',{1:scene,2:camera,3:h[0]+0xc6a0})
    result=c.get(target+sym('WT_STATE'),168);count=int.from_bytes(result[2:4],'big');wc=int.from_bytes(want[2:4],'big')
    rows.append(dict(impulses=[roll,pitch,heading],candidate_state=result.hex(),camera=c.get(camera,12).hex(),count=count,identities=result[108:108+2*count].hex(),expected_count=wc,expected_identities=want[108:108+2*wc].hex(),candidate_identity_match=count==wc and result[108:108+2*count]==want[108:108+2*wc]))
    assert all(c.get(h[i],len(v))==v for i,v in original.items())
    assert not bad_writes,bad_writes[:10]
 distinct=sorted(set((v['count'],v['identities']) for v in rows))
 reports.append(dict(world=world,span=span,eligibility_player=prefix_player.hex(),roll_options=roll_options,pitch_options=pitch_options,heading_options=heading_options,variants=rows,candidate_sets=distinct,all_match=all(v['candidate_identity_match'] for v in rows),native_memory_unchanged=True));c.close()
 print('world',world,'candidate sets',distinct,flush=True)
(root/'tmp/c/homing-impulse-envelope.json').write_text(json.dumps(reports,indent=2)+'\n')
print(json.dumps(dict(worlds=len(reports),cases=sum(len(r['variants']) for r in reports),stable_worlds=[r['world'] for r in reports if len(r['candidate_sets'])==1],uncertain_worlds=[r['world'] for r in reports if len(r['candidate_sets'])>1],native_memory_unchanged=True),indent=2))
