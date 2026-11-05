from unicorn_b import *
from functools import lru_cache
import json,sys,collections,os
from capstone import *
folder=Path(sys.argv[1]);listing=Path(sys.argv[2]).read_text(encoding='latin1');where=json.loads((folder/'addresses.json').read_text());runtime=where['base'];arena=where['arena']
@lru_cache(None)
def sy(n):return int(re.search(r'^([0-9A-F]{8}) '+n+'$',listing,re.M)[1],16)
names=['timing_runtime_forecast_overlay','timing_runtime_forecast_present','timing_runtime_forecast_actors','timing_runtime_forecast_certify','timing_runtime_forecast_candidates','timing_runtime_forecast_get','forecast_player_get','forecast_player_build','timing_runtime_forecast_collect','scene_target_candidates_step','endpoint_player_step','endpoint_player_step_cached','endpoint_ground_resolve','actor_preview_selected_step','actor_present_build_forecast']
entries={runtime+sy(n):n for n in names};rows=[]
CODE=C.CFUNCTYPE(None,C.c_void_p,C.c_uint64,C.c_uint32,C.c_void_p);MEM=C.CFUNCTYPE(None,C.c_void_p,C.c_int,C.c_uint64,C.c_int,C.c_int64,C.c_void_p)
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
for frame in json.loads((folder/'frames.json').read_text())[20:21]:
 c=CPU();c.put(0x200000,(folder/'fast.bin').read_bytes());d=folder/f"frame-{frame['frame']:03d}";a=(d/'arena.bin').read_bytes();c.put(arena,a);h=struct.unpack_from('>9I',a,sy('RT_HUNKS'))
 for i in (0,2,4,5,6):c.put(h[i],(d/f'h{i}.bin').read_bytes())
 pointer=json.loads((d/'object-records-address.json').read_text())['pointer'];c.put(pointer,(d/'object-records.bin').read_bytes())
 if os.environ.get('FORECAST_COLD')=='1':c.put(arena+sy('RT_FORECAST')+sy('RF_TAPE')+sy('FCT_VALID'),bytes(2))
 pc_counts=collections.Counter();scene=arena+sy("RT_FORECAST")+sy("RF_SCENE")
 count=[0];stack=[];totals=collections.Counter();calls=collections.Counter();bad=[]
 @CODE
 def instruction(handle,addr,n,user):
  while stack and stack[-1][1]==addr:
   name,ret,start=stack.pop();totals[name]+=count[0]-start
  if addr in entries:
   name=entries[addr];ret=int.from_bytes(c.get(c.rr(8),4),'big');stack.append((name,ret,count[0]));calls[name]+=1
  if scene<=addr<scene+sy("SCENE_CODE_SIZE"):pc_counts[addr-scene+sy("SCENE_START")]+=1
  count[0]+=1
 @MEM
 def write(handle,kind,addr,n,v,user):
  allowed=[(arena+sy('RT_FORECAST'),arena+sy('RT_ARENA_SIZE')),(arena+sy('RT_ACTOR_PREVIEW'),arena+sy('RT_ACTOR_PREVIEW')+sy('AP_SIZE')),(arena+sy('RT_ACTOR_COORDS'),arena+sy('RT_ACTOR_COORDS')+36),(0x8d000,0x8f004)]
  if not any(lo<=addr and addr+n<=hi for lo,hi in allowed):bad.append((hex(addr),n))
 ch=C.c_size_t();mh=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(ch),1<<2,instruction,None,1,0));ok(u.uc_hook_add(c.h,C.byref(mh),1<<11,write,None,1,0))
 c.rw(1,arena);c.rw(8,0x8f000);c.call(runtime+sy('timing_runtime_forecast_overlay'))
 while stack:
  name,ret,start=stack.pop();assert ret==0x90000;totals[name]+=count[0]-start
 assert c.rr(9)==0 and not bad,bad
 start=sy('RT_ACTOR_COORDS');assert c.get(arena+start,36)==a[start:start+36],frame
 md=Cs(CS_ARCH_M68K,CS_MODE_BIG_ENDIAN|CS_MODE_M68K_000)
 top=[]
 for off,n in pc_counts.most_common(45):
  i=next(md.disasm(c.get(scene+off-sy('SCENE_START'),12),off));top.append(dict(offset=hex(off),count=n,op=i.mnemonic+' '+i.op_str))
 print(top)
 rows.append(dict(frame=frame['frame'],world=frame['world'],instructions=count[0],inclusive=dict(totals),calls=dict(calls)));c.close()
report=dict(frames=len(rows),total=sum(r['instructions'] for r in rows),mean=sum(r['instructions'] for r in rows)/len(rows),inclusive={n:sum(r['inclusive'].get(n,0) for r in rows) for n in names},calls={n:sum(r['calls'].get(n,0) for r in rows) for n in names},rows=rows)
(folder/'scene-hotspot-profile.json').write_text(json.dumps(report,indent=2)+'\n');print({k:v for k,v in report.items() if k!='rows'})
